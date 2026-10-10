"""config: single owner of every data/ read.

Covers the item-2 invariants: repo-root absolute paths (CWD-independent),
one cache with an explicit reset, full params-ledger coverage against
production source, and a frozen policy_version digest.
"""
from pathlib import Path

import config
from engine.contract import load_policy

REPO = Path(__file__).resolve().parents[1]

# Keys with no production reader, deliberately kept in the ledger (review
# decision: allowlist, not delete). The first three are consumed via copies
# in other data files; the rest are planned/superseded hooks. The ledger
# test below fails on any unread key NOT in this set.
LEDGER_EXEMPT = {
    # consumed via anchor_config.json (whose note cross-references this ledger)
    "camera_sensor_width_mm",
    "plane_height_interval_mm",
    # consumed via conversions.yaml (identical value + interval)
    "rice_yield",
    # planned/superseded: no reader anywhere in production code
    "anchor_corner_sigma_px",
    "base_plane_ring_sigma_pct",
    "base_plane_prior_sigma_pct",
    "thickness_prior_sigma_pct",
    "shape_kappa_dome",
    "shape_kappa_layered",
}


def test_paths_derive_from_repo_root_not_cwd():
    assert config.DATA_DIR == REPO / "data"
    for p in (config.MENU_PATH, config.STANDARDS_PATH, config.PARAMS_PATH,
              config.NUTRIENTS_PATH, config.YIELDS_PATH,
              config.ANCHOR_CONFIG_PATH, config.GALLERY_PATH):
        assert p.is_absolute()
        assert p.exists()


def test_every_loader_survives_chdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config.reset_caches()
    try:
        menu = config.load_menu()
        standards = config.load_standards()
        params = config.load_params()
        nutrients = config.load_nutrients()
        yields = config.load_yields()
        anchor = config.load_anchor_config()
        gallery = config.load_gallery()
        assert menu["dishes"] and "bands" in standards
        assert "temperature_scale" in params
        assert "kcal_per_100g" in next(iter(nutrients.values()))
        assert yields and anchor["tiers"] == ["card", "prior"]
        assert "emb" in gallery and "labels" in gallery
    finally:
        config.reset_caches()


def test_every_params_status_key_is_read_by_production_code():
    keys = set(config.load_params()) - LEDGER_EXEMPT
    py_files = sorted(
        p for d in ("engine", "models", "geo", "tools")
        for p in (REPO / d).glob("*.py")
    ) + [REPO / "main.py", REPO / "config.py"]
    source = "\n".join(p.read_text() for p in py_files)
    unread = sorted(k for k in keys if f'"{k}"' not in source
                    and f"'{k}'" not in source)
    assert not unread, f"params_status keys no production code reads: {unread}"


def test_policy_version_frozen_to_current_digest():
    assert load_policy().policy_version == "c65df5efee0f"
