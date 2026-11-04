"""Production API End-to-End Integration Smoke Test.

Validates /health, /menu, /goals, and full multipart /analyze with real plate captures
against the 19-key wire contract schema.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.contract import WIRE_KEYS


def get_test_client():
    """Return an HTTP client pointing to live server or in-process TestClient."""
    live_url = os.environ.get("NUTRISENSE_API_URL", "http://localhost:8000")
    try:
        r = httpx.get(f"{live_url}/health", timeout=1.5)
        if r.status_code == 200:
            print(f"[Smoke Test] Connected to live API at {live_url}")
            return httpx.Client(base_url=live_url, timeout=120.0)
    except Exception:
        pass

    print("[Smoke Test] Live server not detected; using in-process TestClient...")
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


def make_jpeg_with_exif(image_path: Path) -> bytes:
    """Ensure image carries DigitalZoomRatio 1.0 in EXIF for gate admission."""
    with Image.open(image_path) as im:
        ex = im.getexif()
        ex.get_ifd(0x8769)[41988] = 1.0  # digital zoom = 1.0
        buf = io.BytesIO()
        im.save(buf, format="JPEG", exif=ex)
        return buf.getvalue()


def run_smoke_test() -> None:
    client = get_test_client()

    print("\n--- 1. Testing GET /health ---")
    r_health = client.get("/health")
    assert r_health.status_code == 200, f"/health returned {r_health.status_code}"
    health_data = r_health.json()
    assert health_data.get("status") == "ok", f"Health payload: {health_data}"
    print(f"✓ /health passed (version: {health_data.get('version')})")

    print("\n--- 2. Testing GET /menu ---")
    r_menu = client.get("/menu")
    assert r_menu.status_code == 200, f"/menu returned {r_menu.status_code}"
    menu_data = r_menu.json()
    assert "days" in menu_data and "dishes" in menu_data
    print(f"✓ /menu passed ({len(menu_data['dishes'])} configured dishes)")

    print("\n--- 3. Testing GET /goals ---")
    r_goals = client.get("/goals")
    assert r_goals.status_code == 200, f"/goals returned {r_goals.status_code}"
    goals_data = r_goals.json()
    assert "daily" in goals_data and "age_bands" in goals_data
    print(f"✓ /goals passed ({len(goals_data.get('age_bands', []))} age bands)")

    print("\n--- 4. Testing POST /analyze (Dish 5 Biryani capture) ---")
    dish5_path = ROOT.parent / "Aruco_7ID_60mm_with_food" / "Dish 5" / "127g plate 150 g biryani rice.jpg"
    if not dish5_path.is_file():
        # Fallback search
        matches = list((ROOT.parent / "Aruco_7ID_60mm_with_food").glob("**/127g plate 150 g biryani rice.jpg"))
        if matches:
            dish5_path = matches[0]
        else:
            raise FileNotFoundError(f"Test image not found at {dish5_path}")

    jpeg_bytes = make_jpeg_with_exif(dish5_path)
    files = {"file": ("dish5.jpg", jpeg_bytes, "image/jpeg")}
    data = {
        "day": "mon",
        "band": "1-5",
        "mode": "school",
    }

    r_analyze = client.post("/analyze", data=data, files=files)
    assert r_analyze.status_code == 200, f"/analyze failed with {r_analyze.status_code}: {r_analyze.text}"
    analyze_json = r_analyze.json()

    print(f"✓ /analyze returned HTTP 200 (verdict: {analyze_json.get('verdict')})")

    # Validate 19-key wire contract schema
    missing_keys = set(WIRE_KEYS) - set(analyze_json.keys())
    assert not missing_keys, f"Response missing wire contract keys: {missing_keys}"
    print(f"✓ All {len(WIRE_KEYS)} wire contract keys verified present.")

    # Validate portion and nutrition values
    portion = analyze_json.get("portion")
    assert portion is not None, "Portion block is null"
    grams = float(portion.get("grams", 0.0))
    assert grams > 0.0, f"Expected positive grams, got {grams}"
    print(f"✓ Portion estimated: {grams:.1f} g (components: {portion.get('components_g')})")

    nutrition = analyze_json.get("nutrition")
    assert nutrition is not None, "Nutrition block is null"

    def _extract_num(val):
        if isinstance(val, dict):
            return float(val.get("p50", val.get("mean", val.get("median", val.get("point", 0.0)))))
        return float(val or 0.0)

    kcal = _extract_num(nutrition.get("kcal"))
    protein = _extract_num(nutrition.get("protein_g"))
    assert kcal > 0.0 and protein > 0.0, f"Expected positive kcal and protein, got {kcal} kcal, {protein} g"
    print(f"✓ Nutrition estimated: {kcal:.1f} kcal, {protein:.1f} g protein")

    print("\n=======================================================")
    print("🎯 ALL PRODUCTION INTEGRATION SMOKE TESTS PASSED!")
    print("=======================================================\n")


if __name__ == "__main__":
    run_smoke_test()
