"""NutriSense API (S6): /health, /menu, /goals, /analyze."""
import logging
import asyncio
import os
import struct
import tempfile
import threading
import json
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

import anyio
import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from starlette.responses import JSONResponse

from config import load_goals, load_menu, load_standards
from engine.application import AnalysisRequest, AnalysisService
from engine.contract import load_policy, log_analysis, unreadable_analysis
from engine.meal_coach import MealCoachUnavailable, chat as meal_chat, critique as meal_critique
from engine.pipeline import analyze
from models.scale_anchor import read_exif
from models.inference_lock import inference_lock


def _production_pipeline_deps(image):
    """Lazy dependency provider; tests can replace it without loading models."""
    from models.wed_inference import pipeline_deps

    return pipeline_deps(image)


def _run_analysis_pipeline(image, *, day, band, exif=None,
                           serving_style=None, mode="school"):
    """Late-bound adapter keeps the API replaceable in mocked CPU tests."""
    return analyze(image, day=day, band=band, exif=exif,
                   serving_style=serving_style, mode=mode,
                   deps=_production_pipeline_deps(image))


analysis_service = AnalysisService(
    _run_analysis_pipeline,
    inference_guard=inference_lock,
)

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


class AnalyzeBodySizeMiddleware:
    """Cap the request before Starlette parses/spools its multipart body."""

    def __init__(self, app, max_bytes: int, max_seconds: float = 60.0):
        self.app = app
        self.max_bytes = max_bytes
        self.max_seconds = max_seconds

    async def __call__(self, scope, receive, send):
        if not (scope["type"] == "http" and scope["method"] == "POST"
                and scope["path"] == "/analyze"):
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    await JSONResponse(
                        {"detail": "analysis request exceeds the request-size limit"},
                        status_code=413,
                    )(scope, receive, send)
                    return
            except ValueError:
                await JSONResponse(
                    {"detail": "invalid Content-Length"}, status_code=400,
                )(scope, receive, send)
                return

        body = bytearray()
        deadline = time.monotonic() + self.max_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                await JSONResponse(
                    {"detail": "analysis request body timed out"},
                    status_code=408,
                )(scope, receive, send)
                return
            try:
                message = await asyncio.wait_for(receive(), timeout=remaining)
            except TimeoutError:
                await JSONResponse(
                    {"detail": "analysis request body timed out"},
                    status_code=408,
                )(scope, receive, send)
                return
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                await JSONResponse(
                    {"detail": "analysis request exceeds the request-size limit"},
                    status_code=413,
                )(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay_body():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body),
                        "more_body": False}
            return await receive()

        await self.app(scope, replay_body, send)


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1200)


class MealCoachRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysis: dict


class MealChatRequest(MealCoachRequest):
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)
    message: str = Field(min_length=1, max_length=1200)


app = FastAPI(title="NutriSense API", version="5.0")

# One GPU inference at a time per process. The limiter belongs to the
# threadpool call, so /health and other async endpoints remain responsive.
INFERENCE_LIMITER = anyio.CapacityLimiter(1)
MAX_UPLOAD_BYTES = int(os.environ.get("NUTRISENSE_MAX_UPLOAD_BYTES", str(12 * 1024 * 1024)))
MAX_ANALYZE_BODY_BYTES = MAX_UPLOAD_BYTES + 64 * 1024
MAX_ANALYZE_BODY_SECONDS = float(
    os.environ.get("NUTRISENSE_MAX_ANALYZE_BODY_SECONDS", "60")
)
if not np.isfinite(MAX_ANALYZE_BODY_SECONDS) or MAX_ANALYZE_BODY_SECONDS <= 0:
    raise ValueError("NUTRISENSE_MAX_ANALYZE_BODY_SECONDS must be positive")
MAX_IMAGE_PIXELS = int(os.environ.get("NUTRISENSE_MAX_IMAGE_PIXELS", "40000000"))
if MAX_IMAGE_PIXELS < 1:
    raise ValueError("NUTRISENSE_MAX_IMAGE_PIXELS must be at least 1")
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

# CORS stays outside admission/body checks so browser clients can read errors.
app.add_middleware(AnalyzeBodySizeMiddleware,
                   max_bytes=MAX_ANALYZE_BODY_BYTES,
                   max_seconds=MAX_ANALYZE_BODY_SECONDS)
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
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_dir / "nutrisense.log",
                                           maxBytes=5 * 1024 * 1024,
                                           backupCount=3)
    except OSError as exc:
        log.warning("file logging unavailable; continuing with stderr: %s",
                    type(exc).__name__)
    else:
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
    status travel with each profile; School and General analysis modes share
    the same portion and nutrient pipeline (ADR 0003).
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


@app.post("/meal-critique")
async def meal_critique_endpoint(request: MealCoachRequest):
    """Generate one advisory critique from a structured meal analysis."""
    if len(json.dumps(request.analysis, separators=(",", ":"))) > 30000:
        raise HTTPException(status_code=413, detail="analysis context is too large")
    try:
        return await meal_critique(request.analysis)
    except MealCoachUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/meal-chat")
async def meal_chat_endpoint(request: MealChatRequest):
    """Answer a bounded follow-up question about the supplied meal only."""
    if len(json.dumps(request.analysis, separators=(",", ":"))) > 30000:
        raise HTTPException(status_code=413, detail="analysis context is too large")
    try:
        reply = await meal_chat(
            request.analysis,
            [turn.model_dump() for turn in request.history],
            request.message,
        )
        return {"reply": reply}
    except MealCoachUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _analyze_path(path: str, day: str, band: str,
                  serving_style: str | None, mode: str = "school") -> dict:
    """Blocking decode + inference, run in the bounded threadpool."""
    encoded = Path(path).read_bytes()
    dimensions = _encoded_image_dimensions(encoded)
    if dimensions is None:
        status = 422 if encoded.startswith((b"\xff\xd8", b"\x89PNG\r\n\x1a\n")) else 415
        raise HTTPException(status_code=status, detail="upload a valid JPEG or PNG image")
    width, height = dimensions
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise HTTPException(
            status_code=413,
            detail=f"image exceeds the {MAX_IMAGE_PIXELS}-pixel limit",
        )
    image = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        analysis = unreadable_analysis()
        log.error("kind=%s stage=%s error=%s",
                  analysis.failures[0].kind,
                  analysis.failures[0].stage,
                  analysis.failures[0].error)
        log_analysis(str(analysis.verdict), day, band, {})
        return analysis.to_wire()
    exif = read_exif(path)
    return analysis_service.analyze(
        image,
        AnalysisRequest(day=day, band=band, mode=mode,
                        serving_style=serving_style),
        exif=exif,
    )


def _encoded_image_dimensions(data: bytes) -> tuple[int, int] | None:
    """Read JPEG/PNG dimensions before asking OpenCV to allocate decoded pixels."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if not data.startswith(b"\xff\xd8"):
        return None

    start_of_frame = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    offset = 2
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            break
        segment_length = int.from_bytes(data[offset:offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(data):
            break
        if marker in start_of_frame and segment_length >= 7:
            height = int.from_bytes(data[offset + 3:offset + 5], "big")
            width = int.from_bytes(data[offset + 5:offset + 7], "big")
            return width, height
        offset += segment_length
    return None


@app.post("/analyze")
async def analyze_upload(
    file: UploadFile = File(...),
    day: str = Form(...),
    band: str = Form(...),
    mode: str = Form("school"),
    serving_style: str | None = Form(None),
):
    if mode not in {"school", "general"}:
        raise HTTPException(status_code=422, detail="invalid analysis mode")
    if serving_style is not None:
        style_config = load_menu().get("capture_fields", {}).get("serving_style", {})
        allowed_styles = set(style_config.get("values") or [])
        if serving_style not in allowed_styles:
            raise HTTPException(status_code=422, detail="invalid serving_style")
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
            _analyze_path, path, day, band, serving_style, mode,
            limiter=INFERENCE_LIMITER,
        )
    finally:
        await file.close()
        if path is not None:
            Path(path).unlink(missing_ok=True)
