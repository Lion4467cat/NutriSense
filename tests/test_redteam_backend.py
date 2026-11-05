"""Regression tests for red-team backend edge-cases and fuzzing."""

import json
import pytest
import numpy as np
import cv2
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_redteam_health_and_menu():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = client.get("/menu")
    assert r.status_code == 200
    data = r.json()
    assert "dishes" in data and "policy" in data

    r = client.get("/goals")
    assert r.status_code == 200
    data = r.json()
    assert "daily" in data and "age_bands" in data


def test_redteam_form_validation():
    # Missing day
    r = client.post("/analyze", data={"band": "1-5"}, files={"file": ("test.jpg", b"fake", "image/jpeg")})
    assert r.status_code == 422

    # Missing band
    r = client.post("/analyze", data={"day": "mon"}, files={"file": ("test.jpg", b"fake", "image/jpeg")})
    assert r.status_code == 422

    # Invalid mode
    img = cv2.imencode(".jpg", np.zeros((100, 100, 3), dtype=np.uint8))[1].tobytes()
    r = client.post("/analyze", data={"day": "mon", "band": "1-5", "mode": "invalid"}, files={"file": ("test.jpg", img, "image/jpeg")})
    assert r.status_code == 422

    # Invalid serving style
    r = client.post("/analyze", data={"day": "mon", "band": "1-5", "serving_style": "unknown"}, files={"file": ("test.jpg", img, "image/jpeg")})
    assert r.status_code == 422


def test_redteam_malformed_images():
    # 0-byte file
    r = client.post("/analyze", data={"day": "mon", "band": "1-5"}, files={"file": ("empty.jpg", b"", "image/jpeg")})
    assert r.status_code in (415, 422)

    # Truncated JPEG
    r = client.post("/analyze", data={"day": "mon", "band": "1-5"}, files={"file": ("corrupt.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01", "image/jpeg")})
    assert r.status_code in (415, 422)

    # Plain text as JPEG
    r = client.post("/analyze", data={"day": "mon", "band": "1-5"}, files={"file": ("fake.jpg", b"hello world", "image/jpeg")})
    assert r.status_code == 415

    # Pure black image
    black = cv2.imencode(".jpg", np.zeros((100, 100, 3), dtype=np.uint8))[1].tobytes()
    r = client.post("/analyze", data={"day": "mon", "band": "1-5"}, files={"file": ("black.jpg", black, "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["verdict"] == "cannot_verify"

    # Pure white image
    white = cv2.imencode(".jpg", np.full((100, 100, 3), 255, dtype=np.uint8))[1].tobytes()
    r = client.post("/analyze", data={"day": "mon", "band": "1-5"}, files={"file": ("white.jpg", white, "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["verdict"] == "cannot_verify"


def test_redteam_critique_payload_limits():
    huge = {"items": [{"name": "A" * 1000} for _ in range(50)]}
    r = client.post("/meal-critique", json={"analysis": huge})
    assert r.status_code == 413

    r = client.post("/meal-chat", json={"message": "hi"})
    assert r.status_code == 422
