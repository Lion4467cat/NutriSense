"""Generated TypeScript contract + parity fixtures stay in sync with the wire.

  test_gen_matches_committed   — contract.gen.ts is regenerated and diffed
  fixtures                     — one happy Analysis + one unreadable capture,
                                 validated by vitest (parity across languages)

Write mode: CONTRACT_FIXTURE_WRITE=1 .venv/bin/pytest tests/test_contract_gen.py
"""
import json
import math
import os
from pathlib import Path

FIXTURE_DIR = Path("frontend/src/fixtures")
HAPPY_PATH = FIXTURE_DIR / "contract.happy.json"
UNREADABLE_PATH = FIXTURE_DIR / "contract.unreadable.json"
MENU_PATH = FIXTURE_DIR / "contract.menu.json"
WRITE = os.environ.get("CONTRACT_FIXTURE_WRITE") == "1"


def _equal(a, b):
    """Structural compare: exact everywhere, isclose only where a float is.

    The committed fixture was generated on the dev box; CI runs the same MC
    code on a different CPU, which lands ~1e-14 relative (ULP) away on the
    Monte-Carlo stats. Exact float equality cannot hold across CPUs, so
    floats compare with math.isclose(rel_tol=1e-9, abs_tol=1e-12). Everything
    else — keys (set-equal, as plain dict == is), list lengths, strings,
    ints, bools, None — compares exactly. NaN equals only NaN, inf only
    itself. bool subclasses int, so bools are routed away from the numeric
    path: True is never equal to 1.
    """
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, float) or isinstance(b, float):
        if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
            return False
        if isinstance(a, float) and math.isnan(a):
            return isinstance(b, float) and math.isnan(b)
        if isinstance(b, float) and math.isnan(b):
            return False
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    return a == b



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
    assert _equal(committed, wire), (
        f"{label} fixture drifted from the wire — regenerate with "
        "CONTRACT_FIXTURE_WRITE=1 .venv/bin/pytest tests/test_contract_gen.py")


def test_equal_tolerates_cross_cpu_ulp_noise():
    # 1e-14 relative: the difference CI produced for the committed fixture.
    assert _equal({"mean": 100.0}, {"mean": 100.0 * (1 + 1e-14)})
    assert _equal(390.84665628768454, 390.84665628768795)


def test_equal_rejects_real_drift():
    # 1e-6 relative is far beyond the 1e-9 tolerance.
    assert not _equal({"mean": 100.0}, {"mean": 100.0 * (1 + 1e-6)})


def test_equal_rejects_changed_verdict():
    assert not _equal({"verdict": "PASS"}, {"verdict": "BORDERLINE"})


def test_equal_rejects_missing_key():
    assert not _equal({"verdict": "PASS", "reasons": []}, {"verdict": "PASS"})


def test_equal_bool_is_not_int():
    assert not _equal(True, 1)
    assert not _equal({"ok": True}, {"ok": 1})
    assert _equal(True, True)



def test_happy_fixture_matches_wire():
    _check(HAPPY_PATH, _happy_wire(), "happy")


def test_unreadable_fixture_matches_wire():
    _check(UNREADABLE_PATH, _unreadable_wire(), "unreadable")


def test_menu_fixture_matches_wire():
    _check(MENU_PATH, _menu_wire(), "menu")
