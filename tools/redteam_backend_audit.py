"""Pessimistic Red-Team Backend Chaos & Fuzzing Audit for NutriSense API."""

import concurrent.futures
import io
import json
import math
import os
import sys
import urllib.error
import urllib.request
import cv2
import numpy as np

BASE_URL = "http://127.0.0.1:8000"


def make_multipart(fields: dict[str, str], file_field: str, filename: str, file_bytes: bytes, mime: str = "image/jpeg"):
    boundary = "----WebKitFormBoundaryChaosAudit7x9"
    body = bytearray()
    for k, v in fields.items():
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8"))
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\nContent-Type: {mime}\r\n\r\n".encode("utf-8"))
    body.extend(file_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def send_post(endpoint: str, data: bytes, content_type: str):
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=data,
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, body, None
    except Exception as e:
        return 0, "", str(e)


def send_get(endpoint: str):
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body, None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, body, None
    except Exception as e:
        return 0, "", str(e)


def check_no_nans(obj, path=""):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise AssertionError(f"Illegal non-finite float at {path}: {obj}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            check_no_nans(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            check_no_nans(item, f"{path}[{idx}]")


def run_audit():
    print("=" * 70)
    print("NUTRISENSE RED-TEAM BACKEND CHAOS & FUZZING AUDIT")
    print("=" * 70)

    results = []

    def record(category: str, test_name: str, passed: bool, detail: str):
        symbol = "✓ PASS" if passed else "✗ FAIL"
        print(f"[{symbol}] {category}: {test_name} - {detail}")
        results.append({"category": category, "test": test_name, "passed": passed, "detail": detail})

    # 1. Base Endpoints Health & Goals
    code, body, err = send_get("/health")
    record("Endpoints", "/health", code == 200, f"HTTP {code}")
    code, body, err = send_get("/menu")
    menu_valid = False
    if code == 200:
        data = json.loads(body)
        check_no_nans(data)
        menu_valid = "dishes" in data and "policy" in data
    record("Endpoints", "/menu", menu_valid, f"HTTP {code}, dishes & policy present")

    code, body, err = send_get("/goals")
    goals_valid = False
    if code == 200:
        data = json.loads(body)
        check_no_nans(data)
        goals_valid = "daily" in data and "age_bands" in data
    record("Endpoints", "/goals", goals_valid, f"HTTP {code}, daily goals present")

    # 2. Form Parameter Validation
    # 2a. Missing day/band
    body_no_day, ct = make_multipart({"band": "1-5"}, "file", "test.jpg", b"fake", "image/jpeg")
    code, body, _ = send_post("/analyze", body_no_day, ct)
    record("Validation", "Missing day", code == 422, f"Expected 422, got {code}")

    body_no_band, ct = make_multipart({"day": "mon"}, "file", "test.jpg", b"fake", "image/jpeg")
    code, body, _ = send_post("/analyze", body_no_band, ct)
    record("Validation", "Missing band", code == 422, f"Expected 422, got {code}")

    # 2b. Invalid mode
    img_valid = cv2.imencode(".jpg", np.zeros((100, 100, 3), dtype=np.uint8))[1].tobytes()
    body_bad_mode, ct = make_multipart({"day": "mon", "band": "1-5", "mode": "hacker_mode"}, "file", "test.jpg", img_valid, "image/jpeg")
    code, body, _ = send_post("/analyze", body_bad_mode, ct)
    record("Validation", "Invalid mode", code == 422, f"Expected 422, got {code}")

    # 2c. Invalid serving_style
    body_bad_style, ct = make_multipart({"day": "mon", "band": "1-5", "serving_style": "buffet"}, "file", "test.jpg", img_valid, "image/jpeg")
    code, body, _ = send_post("/analyze", body_bad_style, ct)
    record("Validation", "Invalid serving_style", code == 422, f"Expected 422, got {code}")

    # 2d. JSON posted to /analyze instead of multipart
    code, body, _ = send_post("/analyze", b'{"day": "mon", "band": "1-5"}', "application/json")
    record("Validation", "JSON body to multipart endpoint", code == 422, f"Expected 422, got {code}")

    # 3. Image Edge-Cases & Fuzzing
    # 3a. 0-byte file
    body_0b, ct = make_multipart({"day": "mon", "band": "1-5"}, "file", "empty.jpg", b"", "image/jpeg")
    code, body, _ = send_post("/analyze", body_0b, ct)
    record("Image Fuzzing", "0-byte file", code in (415, 422), f"Expected 415/422, got {code}")

    # 3b. Corrupted JPEG (header only)
    body_corrupt, ct = make_multipart({"day": "mon", "band": "1-5"}, "file", "corrupt.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01", "image/jpeg")
    code, body, _ = send_post("/analyze", body_corrupt, ct)
    record("Image Fuzzing", "Truncated JPEG header", code in (415, 422), f"Expected 415/422, got {code}")

    # 3c. Plain text disguised as JPEG
    body_txt, ct = make_multipart({"day": "mon", "band": "1-5"}, "file", "fake.jpg", b"Hello World not an image", "image/jpeg")
    code, body, _ = send_post("/analyze", body_txt, ct)
    record("Image Fuzzing", "Text file as JPEG", code == 415, f"Expected 415, got {code}")

    # 3d. 16x16 thumbnail image
    thumb = cv2.imencode(".jpg", np.full((16, 16, 3), 128, dtype=np.uint8))[1].tobytes()
    body_thumb, ct = make_multipart({"day": "mon", "band": "1-5"}, "file", "thumb.jpg", thumb, "image/jpeg")
    code, body, _ = send_post("/analyze", body_thumb, ct)
    thumb_safe = False
    if code == 200:
        data = json.loads(body)
        check_no_nans(data)
        thumb_safe = data.get("verdict") in ("cannot_verify", "ESTIMATED", "FAIL", "BORDERLINE", "PASS")
    record("Image Fuzzing", "16x16 thumbnail image", thumb_safe or code in (400, 422), f"HTTP {code}, handled without crash")

    # 3e. Extreme aspect ratio (100x2000 banner)
    banner = cv2.imencode(".jpg", np.full((100, 2000, 3), 128, dtype=np.uint8))[1].tobytes()
    body_banner, ct = make_multipart({"day": "mon", "band": "1-5"}, "file", "banner.jpg", banner, "image/jpeg")
    code, body, _ = send_post("/analyze", body_banner, ct)
    banner_safe = False
    if code == 200:
        data = json.loads(body)
        check_no_nans(data)
        banner_safe = True
    record("Image Fuzzing", "100x2000 extreme aspect banner", banner_safe or code in (400, 422), f"HTTP {code}, handled cleanly")

    # 3f. Pure black image (all 0s)
    black = cv2.imencode(".jpg", np.zeros((300, 300, 3), dtype=np.uint8))[1].tobytes()
    body_black, ct = make_multipart({"day": "mon", "band": "1-5"}, "file", "black.jpg", black, "image/jpeg")
    code, body, _ = send_post("/analyze", body_black, ct)
    black_safe = False
    if code == 200:
        data = json.loads(body)
        check_no_nans(data)
        black_safe = data.get("verdict") == "cannot_verify" or "cannot_verify" in str(data.get("verdict"))
    record("Image Fuzzing", "Pure black image (all 0s)", black_safe, f"HTTP {code}, verdict={data.get('verdict') if code == 200 else 'error'}")

    # 3g. Pure white image (all 255s)
    white = cv2.imencode(".jpg", np.full((300, 300, 3), 255, dtype=np.uint8))[1].tobytes()
    body_white, ct = make_multipart({"day": "mon", "band": "1-5"}, "file", "white.jpg", white, "image/jpeg")
    code, body, _ = send_post("/analyze", body_white, ct)
    white_safe = False
    if code == 200:
        data = json.loads(body)
        check_no_nans(data)
        white_safe = data.get("verdict") == "cannot_verify" or "cannot_verify" in str(data.get("verdict"))
    record("Image Fuzzing", "Pure white image (all 255s)", white_safe, f"HTTP {code}, verdict={data.get('verdict') if code == 200 else 'error'}")

    # 3h. Grayscale PNG (single channel)
    gray = cv2.imencode(".png", np.full((200, 200), 128, dtype=np.uint8))[1].tobytes()
    body_gray, ct = make_multipart({"day": "mon", "band": "1-5"}, "file", "gray.png", gray, "image/png")
    code, body, _ = send_post("/analyze", body_gray, ct)
    gray_safe = False
    if code == 200:
        data = json.loads(body)
        check_no_nans(data)
        gray_safe = True
    record("Image Fuzzing", "Grayscale PNG", gray_safe, f"HTTP {code}, handled properly by imdecode")

    # 4. Meal Coach & Chat Torture
    # 4a. Oversized critique context (>30KB)
    huge_ctx = {"items": [{"name": "A" * 1000} for _ in range(50)]}
    code, body, _ = send_post("/meal-critique", json.dumps({"analysis": huge_ctx}).encode("utf-8"), "application/json")
    record("Meal Coach", "Oversized critique payload", code == 413, f"Expected 413, got {code}")

    # 4b. Missing analysis in chat
    code, body, _ = send_post("/meal-chat", b'{"message": "hello"}', "application/json")
    record("Meal Coach", "Missing analysis field in chat", code == 422, f"Expected 422, got {code}")

    # 5. Concurrency Torture (5 simultaneous requests to /analyze)
    print("\nExecuting Concurrency Torture: 5 simultaneous POST /analyze...")
    dish2_path = "/home/tinkerer/Desktop/Nutrisense/Aruco_7ID_60mm_with_food/Dish 2/Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg"
    with open(dish2_path, "rb") as f:
        real_img = f.read()
    c_body, c_ct = make_multipart({"day": "mon", "band": "1-5"}, "file", "dish2.jpg", real_img, "image/jpeg")

    def worker(idx):
        return idx, send_post("/analyze", c_body, c_ct)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(worker, i) for i in range(5)]
        concurrent_results = [f.result() for f in concurrent.futures.as_completed(futures)]

    codes = [r[1][0] for r in concurrent_results]
    print(f"Concurrent response status codes: {codes}")
    # Under AnalyzeAdmissionMiddleware and INFERENCE_LIMITER, requests either get 200 or 503 (capacity reached)
    concurrency_safe = all(c in (200, 503) for c in codes) and 200 in codes
    record("Concurrency", "5 parallel /analyze requests", concurrency_safe, f"Response codes: {codes} (all 200 or 503)")

    print("=" * 70)
    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"AUDIT FAILED: {len(failed)} tests failed!")
        for f in failed:
            print(f"  FAILED: {f['category']} - {f['test']}: {f['detail']}")
        return False
    else:
        print(f"ALL {len(results)} RED-TEAM BACKEND TESTS PASSED CLEANLY!")
        return True


if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)
