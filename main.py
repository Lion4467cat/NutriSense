"""NutriSense API (S6): /health, /menu, /analyze."""
import logging
import os
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from config import load_menu, load_standards
from engine.contract import load_policy, log_analysis, unreadable_analysis
from engine.pipeline import analyze
from models.scale_anchor import read_exif

app = FastAPI(title="NutriSense API", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
        from models import dish_segmenter, food_classifier
    except Exception as e:
        log.warning("startup device report unavailable: %s", e)
        return
    avail = torch.cuda.is_available()
    gpu = torch.cuda.get_device_name(0) if avail else "none"
    fallback = "cuda" if avail else "cpu"
    seg = dish_segmenter._STATE.get("device") or dish_segmenter._device()
    cls = food_classifier._STATE.get("device") or food_classifier._device()
    dep = MonocularDepth().device or fallback  # constructor is lazy
    loaded = bool(dish_segmenter._STATE or food_classifier._STATE)
    log.info(
        "startup torch.cuda.is_available()=%s gpu=%s | segment=%s classify=%s depth=%s%s",
        avail, gpu, seg, cls, dep,
        "" if loaded else " (selected; weights load lazily on first request)")


_log_startup_devices()


@app.get("/")
def root():
    return {"message": "NutriSense is running", "phase": "built"}


@app.get("/health")
def health():
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


@app.post("/analyze")
async def analyze_upload(
    file: UploadFile = File(...),
    day: str = Form(...),
    band: str = Form(...),
    serving_style: str | None = Form(None),
):
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        image = cv2.imread(path, cv2.IMREAD_COLOR)
        if image is None:
            arr = np.frombuffer(data, dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            analysis = unreadable_analysis()
            log.error("kind=%s stage=%s error=%s",
                      analysis.failures[0].kind,
                      analysis.failures[0].stage,
                      analysis.failures[0].error)
            log_analysis(str(analysis.verdict), day, band, {})
            return analysis.to_wire()
        exif = read_exif(path)
        result = analyze(image, day=day, band=band, exif=exif,
                         serving_style=serving_style)
        return result
    finally:
        Path(path).unlink(missing_ok=True)
