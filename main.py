"""NutriSense API (S6): /health, /menu, /goals, /analyze."""
import logging
import os
import tempfile
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

import anyio
import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from config import load_goals, load_menu, load_standards
from engine.contract import load_policy, log_analysis, unreadable_analysis
from engine.pipeline import analyze
from models.scale_anchor import read_exif

class AnalyzeAdmissionMiddleware:
    """Bound admitted /analyze requests before multipart parsing or disk copies."""

    def __init__(self, app, max_inflight: int):
        self.app = app
        self._slots = threading.BoundedSemaphore(max_inflight)

    async def __call__(self, scope, receive, send):
        if not (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"] == "/analyze"
        ):
            await self.app(scope, receive, send)
            return

        if not self._slots.acquire(blocking=False):
            response = JSONResponse(
                {"detail": "analysis capacity reached; retry shortly"},
                status_code=503,
                headers={"Retry-After": "1"},
            )
            await response(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        finally:
            self._slots.release()


app = FastAPI(title="NutriSense API", version="5.0")

# One GPU inference at a time per process. The limiter belongs to the
# threadpool call, so /health and other async endpoints remain responsive.
INFERENCE_LIMITER = anyio.CapacityLimiter(1)
MAX_UPLOAD_BYTES = int(os.environ.get("NUTRISENSE_MAX_UPLOAD_BYTES", str(12 * 1024 * 1024)))
MAX_INFLIGHT_ANALYSES = int(os.environ.get("NUTRISENSE_MAX_INFLIGHT_ANALYSES", "2"))
if MAX_INFLIGHT_ANALYSES < 1:
    raise ValueError("NUTRISENSE_MAX_INFLIGHT_ANALYSES must be at least 1")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "NUTRISENSE_CORS_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

# CORS stays outside admission so browser clients can read the overload response.
app.add_middleware(AnalyzeAdmissionMiddleware, max_inflight=MAX_INFLIGHT_ANALYSES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _configure_logging() -> None:
    """One stdlib logger for the whole backend: stderr + rotating file."""
    log = logging.getLogger("nutrisense")
    if log.handlers:
        return
    log.setLevel(logging.INFO)
    log.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    log.addHandler(stream)
    # tests redirect this to a temp dir so pytest never writes logs/nutrisense.log
    log_dir = Path(
        os.environ.get("NUTRISENSE_LOG_DIR")
        or (Path(__file__).resolve().parent / "logs")
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(log_dir / "nutrisense.log",
                                       maxBytes=5 * 1024 * 1024,
                                       backupCount=3)
    file_handler.setFormatter(fmt)
    log.addHandler(file_handler)


_configure_logging()
log = logging.getLogger("nutrisense.main")


def _log_startup_devices() -> None:
    """One line: CUDA availability + the device each model runs on."""
    try:
        import torch
        from engine.depth import MonocularDepth
        from models import dish_segmenter, food_classifier, registry
    except Exception as e:
        log.warning("startup device report unavailable: %s", e)
        return
    avail = torch.cuda.is_available()
    gpu = torch.cuda.get_device_name(0) if avail else "none"
    fallback = "cuda" if avail else "cpu"
    seg_state = registry.peek("sam2")
    cls_state = registry.peek("siglip2")
    seg = (seg_state or {}).get("device") or dish_segmenter._device()
    cls = (cls_state or {}).get("device") or food_classifier._device()
    dep = MonocularDepth().device or fallback  # constructor is lazy
    loaded = bool(seg_state or cls_state)
    log.info(
        "startup torch.cuda.is_available()=%s gpu=%s | segment=%s classify=%s depth=%s%s",
        avail, gpu, seg, cls, dep,
        "" if loaded else " (selected; weights load lazily on first request)")


_log_startup_devices()


@app.get("/")
def root():
    return {"message": "NutriSense is running", "phase": "built"}


@app.get("/health")
async def health():
    return {"status": "ok", "phase": "built"}


@app.get("/menu")
def menu():
    m = load_menu()
    standards = load_standards()
    return {
        "dishes": m["dishes"],
        "days": m["days"],
        "bands": {k: {"kcal": v["kcal"], "protein_g": v["protein_g"]}
                  for k, v in standards["bands"].items()},
        "capture_fields": m["capture_fields"],
        "remarks": m["remarks"],
        "policy": load_policy().to_wire(),
    }


@app.get("/goals")
def goals():
    """WHO daily-goal values (General mode, spec 002) — read-only like /menu.

    Shapes the data file's `bands` table as `daily`, with the vocabulary and
    activity-level lists the frontend renders as pickers. Provenance and
    status travel with each profile; /analyze is untouched (ADR 0003).
    """
    g = load_goals()
    return {
        "age_bands": list(g["bands"]),
        "sexes": g["vocabulary"]["sexes"],
        "activity_levels": list(g["activity_levels"]),
        "units": g["units"],
        "daily": g["bands"],
        "source": g["source"],
        "caveats": g["caveats"],
    }


def _analyze_path(path: str, day: str, band: str,
                  serving_style: str | None) -> dict:
    """Blocking decode + inference, run in the bounded threadpool."""
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        analysis = unreadable_analysis()
        log.error("kind=%s stage=%s error=%s",
                  analysis.failures[0].kind,
                  analysis.failures[0].stage,
                  analysis.failures[0].error)
        log_analysis(str(analysis.verdict), day, band, {})
        return analysis.to_wire()
    exif = read_exif(path)
    return analyze(image, day=day, band=band, exif=exif,
                   serving_style=serving_style)


@app.post("/analyze")
async def analyze_upload(
    file: UploadFile = File(...),
    day: str = Form(...),
    band: str = Form(...),
    serving_style: str | None = Form(None),
):
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            path = tmp.name
            total = 0
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"image exceeds the {MAX_UPLOAD_BYTES}-byte upload limit",
                    )
                tmp.write(chunk)
        return await anyio.to_thread.run_sync(
            _analyze_path, path, day, band, serving_style,
            limiter=INFERENCE_LIMITER,
        )
    finally:
        await file.close()
        if path is not None:
            Path(path).unlink(missing_ok=True)
