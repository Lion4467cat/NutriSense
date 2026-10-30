"""S6: API + pipeline integration tests (real S1 anchor + S2 segmenter;
classifier stubbed for determinism, depth injected as GT)."""
import asyncio
import threading
from pathlib import Path

import cv2
import httpx
import pytest
from fastapi.testclient import TestClient

import main as main_module
import models.food_classifier as fc
from engine.pipeline import analyze as pipe_analyze
from main import app
from tests.synth.scene import render_scene

client = TestClient(app)


@pytest.fixture(scope="module")
def scene():
    return render_scene()


@pytest.fixture(scope="module")
def jpg_bytes(scene):
    ok, buf = cv2.imencode(".jpg", scene["image_bgr"], [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok
    return buf.tobytes()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["phase"] == "built"


def test_menu_endpoint():
    r = client.get("/menu")
    assert r.status_code == 200
    body = r.json()
    assert "rice_sambar" in body["dishes"]
    assert body["dishes"]["wheat_product"]["status"] == "out_of_scope"
    assert body["bands"]["1-5"]["kcal"]["value"] == 450
    assert set(body["capture_fields"]["band"]["values"]) == {"1-5", "6-8", "9-10"}
    # wire keys are the contract the frontend menuSchema decodes (C4):
    # tools/gen_contract_ts.py menuSchema must stay aligned with this set
    assert set(body) == {"dishes", "days", "bands", "capture_fields",
                         "remarks", "policy"}
    for band in body["bands"].values():
        assert set(band) == {"kcal", "protein_g"}
    assert set(body["capture_fields"]) == {"serving_style", "day", "band"}
    assert isinstance(body["remarks"], list)
    assert len(body["policy"]["policy_version"]) == 12


@pytest.mark.gpu
def test_analyze_upload_end_to_end(jpg_bytes, monkeypatch):
    # classifier stubbed (synthetic renders abstain at 0.67 < 0.82 by design)
    monkeypatch.setattr(fc, "classify_dish", lambda img, **kw: {
        "dish": "rice_sambar", "confidence": 1.0, "method": "stub",
        "match_score": 0.9, "margin": None, "scores": {}, "uncovered": [],
        "reason": "test stub"})
    r = client.post("/analyze", files={"file": ("plate.jpg", jpg_bytes, "image/jpeg")},
                    data={"day": "mon", "band": "1-5", "serving_style": "mixed"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in {"PASS", "FAIL", "BORDERLINE"}
    assert body["anchor"]["tier"] == "measured"
    assert body["portion"]["grams"] > 0
    assert body["portion"]["base_method"] in {"ring", "table_prior"}
    assert body["coverage"]["score"] > 0
    assert "kcal" in body["nutrition"] and "interval_90" in body["nutrition"]["kcal"]
    assert body["dish"]["id"] == "rice_sambar"
    assert body["classification"]["method"] == "stub"
    assert body["model_versions"]["segmenter"] == "facebook/sam2.1-hiera-large"


def test_analyze_bad_band(jpg_bytes):
    r = client.post("/analyze", files={"file": ("p.jpg", jpg_bytes, "image/jpeg")},
                    data={"day": "mon", "band": "99-100"})
    assert r.status_code == 200
    assert r.json()["verdict"] == "cannot_verify"


def test_analyze_unreadable_file():
    r = client.post("/analyze", files={"file": ("bad.jpg", b"not an image", "image/jpeg")},
                    data={"day": "mon", "band": "1-5"})
    assert r.status_code == 200
    assert r.json()["verdict"] == "cannot_verify"


def test_analyze_rejects_oversize_upload(monkeypatch):
    monkeypatch.setattr(main_module, "MAX_UPLOAD_BYTES", 8)
    r = client.post("/analyze", files={"file": ("big.jpg", b"123456789", "image/jpeg")},
                    data={"day": "mon", "band": "1-5"})
    assert r.status_code == 413
    assert "upload limit" in r.json()["detail"]


def test_inference_is_serialized_without_blocking_health(monkeypatch, tmp_path):
    async def exercise():
        entered = threading.Event()
        release = threading.Event()
        second_file_created = threading.Event()
        state_lock = threading.Lock()
        active = 0
        calls = 0
        created_paths = []
        real_named_temporary_file = main_module.tempfile.NamedTemporaryFile

        def track_temporary_file(*args, **kwargs):
            kwargs["dir"] = temp_dir
            tmp = real_named_temporary_file(*args, **kwargs)
            with state_lock:
                created_paths.append(tmp.name)
                if len(created_paths) == 2:
                    second_file_created.set()
            return tmp

        temp_dir = tmp_path

        def fake_analyze(*_args):
            nonlocal active, calls
            with state_lock:
                active += 1
                calls += 1
                if calls == 1:
                    entered.set()
            assert active == 1  # a second GPU call must wait for the limiter
            try:
                assert release.wait(2)
                return {"verdict": "cannot_verify"}
            finally:
                with state_lock:
                    active -= 1

        monkeypatch.setattr(main_module, "_analyze_path", fake_analyze)
        monkeypatch.setattr(main_module.tempfile, "NamedTemporaryFile", track_temporary_file)
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            kwargs = {
                "files": {"file": ("p.jpg", b"image", "image/jpeg")},
                "data": {"day": "mon", "band": "1-5"},
            }
            first = asyncio.create_task(ac.post("/analyze", **kwargs))
            second = asyncio.create_task(ac.post("/analyze", **kwargs))
            assert await asyncio.to_thread(entered.wait, 1)
            assert await asyncio.to_thread(second_file_created.wait, 1)
            try:
                overloaded = await ac.post(
                    "/analyze", **kwargs, headers={"Origin": "http://localhost:5173"}
                )
                assert overloaded.status_code == 503
                assert overloaded.headers["retry-after"] == "1"
                assert overloaded.headers["access-control-allow-origin"] == "http://localhost:5173"
                assert len(created_paths) == 2
                health = await asyncio.wait_for(ac.get("/health"), timeout=0.5)
                assert health.status_code == 200
                assert calls == 1
            finally:
                release.set()
            responses = await asyncio.gather(first, second)
            assert all(r.status_code == 200 for r in responses)
            assert all(not Path(path).exists() for path in created_paths)

    asyncio.run(exercise())


def test_pipeline_gates(scene, monkeypatch):
    deps = {
        "depth": lambda img, **_kw: {"depth_m": scene["depth_m"], "model": "gt"},
        "segment": lambda img: {"mask": scene["mask_food"], "strategy": "stub",
                                "sam_score": 1.0, "n_candidates": 1, "area_frac": 0.2},
        "classify": lambda img: {"dish": "rice_sambar", "confidence": 1.0,
                                 "method": "stub", "match_score": 0.9, "reason": "stub"},
    }
    # zoom gate
    exif2 = {"focal_mm": 4.0, "subject_distance_cm": None,
             "digital_zoom": 2.0, "camera": None}
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5", exif=exif2, deps=deps)
    assert out["verdict"] == "cannot_verify"
    # unknown day
    out = pipe_analyze(scene["image_bgr"], day="sunday", band="1-5", deps=deps)
    assert out["verdict"] == "cannot_verify"
    # out-of-scope dish (deps classify stub must be replaced, not the module attr)
    deps_oos = dict(deps)
    deps_oos["classify"] = lambda img: {"dish": "wheat_product", "confidence": 1.0,
                                        "method": "stub", "match_score": 0.9,
                                        "reason": "stub"}
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5", deps=deps_oos)
    assert out["verdict"] == "out_of_scope"


def test_pipeline_gt_depth_deterministic(scene, monkeypatch):
    monkeypatch.setattr(fc, "classify_dish", lambda img, **kw: {
        "dish": "rice_sambar", "confidence": 1.0, "method": "stub",
        "match_score": 0.9, "reason": "stub"})
    deps = {
        "depth": lambda img, **_kw: {"depth_m": scene["depth_m"], "model": "gt"},
        "segment": lambda img: {"mask": scene["mask_food"], "strategy": "stub",
                                "sam_score": 1.0, "n_candidates": 1,
                                "area_frac": 0.2},
        "classify": lambda img: {"dish": "rice_sambar", "confidence": 1.0,
                                 "method": "stub", "match_score": 0.9,
                                 "reason": "stub"},
    }
    a = pipe_analyze(scene["image_bgr"], day="mon", band="1-5", deps=deps, seed=5)
    b = pipe_analyze(scene["image_bgr"], day="mon", band="1-5", deps=deps, seed=5)
    assert a["nutrition"]["kcal"]["mean"] == b["nutrition"]["kcal"]["mean"]
    assert a["verdict"] == b["verdict"]
    assert a["portion"]["grams"] > 0
    # plan budget: ring path per-dish grams sigma ~26%
    assert 0.18 <= a["portion"]["sigma_grams_rel"] <= 0.45
