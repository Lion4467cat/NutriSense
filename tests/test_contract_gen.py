"""Generated TypeScript contract + parity fixtures stay in sync with the wire.

  test_gen_matches_committed   — contract.gen.ts is regenerated and diffed
  fixtures                     — one happy Analysis + one unreadable capture,
                                 validated by vitest (parity across languages)

Write mode: CONTRACT_FIXTURE_WRITE=1 .venv/bin/pytest tests/test_contract_gen.py
"""
import json
import os
from pathlib import Path

FIXTURE_DIR = Path("frontend/src/fixtures")
HAPPY_PATH = FIXTURE_DIR / "contract.happy.json"
UNREADABLE_PATH = FIXTURE_DIR / "contract.unreadable.json"
MENU_PATH = FIXTURE_DIR / "contract.menu.json"
WRITE = os.environ.get("CONTRACT_FIXTURE_WRITE") == "1"


def test_gen_matches_committed():
    from tools.gen_contract_ts import OUT_PATH, generate
    committed = OUT_PATH.read_text()
    got = generate()
    if got != committed:
        raise AssertionError(
            "frontend/src/types/contract.gen.ts is stale — run: "
            "python -m tools.gen_contract_ts --write")


def _happy_wire():
    from engine.pipeline import analyze
    from tests.synth.scene import render_scene
    from tests.test_pipeline_seams import make_deps
    scene = render_scene()
    return analyze(scene["image_bgr"], day="mon", band="1-5",
                   deps=make_deps(scene))


def _unreadable_wire():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    r = client.post("/analyze", files={"file": ("p.jpg", b"not an image")},
                    data={"day": "mon", "band": "1-5"})
    assert r.status_code == 200
    return r.json()


def _menu_wire():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    r = client.get("/menu")
    assert r.status_code == 200
    return r.json()


def _check(path: Path, wire: dict, label: str):
    # normalize: wire tuples/np-scalars vs JSON lists/floats
    wire = json.loads(json.dumps(wire, default=float))
    if WRITE:
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(wire, indent=2, sort_keys=True, default=float) + "\n")
        return
    assert path.exists(), f"{label} fixture missing — run with CONTRACT_FIXTURE_WRITE=1"
    committed = json.loads(path.read_text())
    assert committed == wire, (
        f"{label} fixture drifted from the wire — regenerate with "
        "CONTRACT_FIXTURE_WRITE=1 .venv/bin/pytest tests/test_contract_gen.py")


def test_happy_fixture_matches_wire():
    _check(HAPPY_PATH, _happy_wire(), "happy")


def test_unreadable_fixture_matches_wire():
    _check(UNREADABLE_PATH, _unreadable_wire(), "unreadable")


def test_menu_fixture_matches_wire():
    _check(MENU_PATH, _menu_wire(), "menu")
