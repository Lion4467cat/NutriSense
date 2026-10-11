"""Single owner of every data/ read.

Absolute paths derive from the repo root — never the CWD — so the API,
tools and tests resolve the same files from any working directory.
One cache dict for parsed artifacts; reset_caches() is the explicit
reset tests call after chdir or fixture edits.
"""
import json
from pathlib import Path

import numpy as np
import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"

MENU_PATH = DATA_DIR / "menu.yaml"
STANDARDS_PATH = DATA_DIR / "standards.yaml"
PARAMS_PATH = DATA_DIR / "params_status.yaml"
NUTRIENTS_PATH = DATA_DIR / "nutrients.yaml"
YIELDS_PATH = DATA_DIR / "conversions.yaml"
ANCHOR_CONFIG_PATH = DATA_DIR / "anchor_config.json"
GALLERY_PATH = DATA_DIR / "gallery.npz"
WED_DISHES_PATH = DATA_DIR / "wed_dishes.yaml"
WED_INDEX_PATH = DATA_DIR / "wed" / "index_map.json"
WED_SIGMA_PATH = DATA_DIR / "weight_head_sigma.yaml"

_CACHE: dict = {}


def reset_caches() -> None:
    """Drop every parsed artifact (tests: call after chdir or fixture edits)."""
    _CACHE.clear()


def load_menu() -> dict:
    if "menu" not in _CACHE:
        with open(MENU_PATH) as f:
            _CACHE["menu"] = yaml.safe_load(f)
    return _CACHE["menu"]


def load_standards() -> dict:
    if "standards" not in _CACHE:
        with open(STANDARDS_PATH) as f:
            _CACHE["standards"] = yaml.safe_load(f)
    return _CACHE["standards"]


def load_params(path=None) -> dict:
    """params_status.yaml's `params` ledger; an explicit path bypasses the cache."""
    if path is not None:
        with open(path) as f:
            return yaml.safe_load(f)["params"]
    if "params" not in _CACHE:
        with open(PARAMS_PATH) as f:
            _CACHE["params"] = yaml.safe_load(f)["params"]
    return _CACHE["params"]


def load_nutrients(path=None) -> dict:
    """nutrients.yaml's `foods` table; an explicit path bypasses the cache."""
    if path is not None:
        with open(path) as f:
            return yaml.safe_load(f)["foods"]
    if "nutrients" not in _CACHE:
        with open(NUTRIENTS_PATH) as f:
            _CACHE["nutrients"] = yaml.safe_load(f)["foods"]
    return _CACHE["nutrients"]


def load_yields() -> dict:
    if "yields" not in _CACHE:
        with open(YIELDS_PATH) as f:
            _CACHE["yields"] = yaml.safe_load(f)["yields"]
    return _CACHE["yields"]


def load_anchor_config(path=None) -> dict:
    if path is not None:
        with open(path) as f:
            return json.load(f)
    if "anchor_config" not in _CACHE:
        with open(ANCHOR_CONFIG_PATH) as f:
            _CACHE["anchor_config"] = json.load(f)
    return _CACHE["anchor_config"]


def load_gallery(path=None) -> dict:
    """gallery.npz arrays; an explicit path bypasses the cache (build/verify)."""
    if path is None:
        if "gallery" not in _CACHE:
            with np.load(GALLERY_PATH, allow_pickle=False) as z:
                _CACHE["gallery"] = {k: z[k] for k in z.files}
        return _CACHE["gallery"]
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def load_wed_dishes() -> dict:
    """WED <-> menu mapping (data/wed_dishes.yaml). Missing file -> {}."""
    if "wed_dishes" not in _CACHE:
        if WED_DISHES_PATH.is_file():
            with open(WED_DISHES_PATH) as f:
                _CACHE["wed_dishes"] = yaml.safe_load(f) or {}
        else:
            _CACHE["wed_dishes"] = {}
    return _CACHE["wed_dishes"]


def load_wed_index() -> dict:
    """WED dish name -> 0-based regression slot (index_map id - 1). {} if absent."""
    if "wed_index" not in _CACHE:
        if WED_INDEX_PATH.is_file():
            with open(WED_INDEX_PATH) as f:
                raw = json.load(f)
            _CACHE["wed_index"] = {
                name: int(cid) - 1 for cid, name in raw.items()
                if str(name).lower() != "background"
            }
        else:
            _CACHE["wed_index"] = {}
    return _CACHE["wed_index"]


def load_wed_sigma() -> dict:
    """WED dish name -> relative sigma from the trained head's val residuals.
    Empty dict before the first training run (learned path then assumes)."""
    if "wed_sigma" not in _CACHE:
        if WED_SIGMA_PATH.is_file():
            with open(WED_SIGMA_PATH) as f:
                doc = yaml.safe_load(f) or {}
            _CACHE["wed_sigma"] = {k: float(v) for k, v in
                                   (doc.get("sigma_rel") or {}).items()}
        else:
            _CACHE["wed_sigma"] = {}
    return _CACHE["wed_sigma"]
