"""NutriSense API (S6): /health, /menu, /analyze."""
import tempfile
from pathlib import Path

import cv2
import numpy as np
import yaml
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from engine.pipeline import analyze, load_menu
from models.scale_anchor import read_exif

app = FastAPI(title="NutriSense API", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "NutriSense is running", "phase": "built"}


@app.get("/health")
def health():
    return {"status": "ok", "phase": "built"}


@app.get("/menu")
def menu():
    m = load_menu()
    with open(Path(__file__).parent / "data" / "standards.yaml") as f:
        standards = yaml.safe_load(f)
    return {
        "dishes": m["dishes"],
        "days": m["days"],
        "bands": {k: {"kcal": v["kcal"], "protein_g": v["protein_g"]}
                  for k, v in standards["bands"].items()},
        "capture_fields": m["capture_fields"],
        "remarks": m["remarks"],
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
            return {"verdict": "cannot_verify", "reasons": ["unreadable image"]}
        exif = read_exif(path)
        result = analyze(image, day=day, band=band, exif=exif,
                         serving_style=serving_style)
        return result
    finally:
        Path(path).unlink(missing_ok=True)
