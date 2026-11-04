"""WED class registry and explicit, uncertainty-tagged renderer assumptions."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
import json
from pathlib import Path
import random
import re
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX_MAP = ROOT / "data" / "wed" / "index_map.json"
DEFAULT_MANIFEST = ROOT / "data" / "wed_manifest.jsonl"
DEFAULT_DISH_CONFIG = ROOT / "data" / "wed_dishes.yaml"
DEFAULT_MENU = ROOT / "data" / "menu.yaml"


@dataclass(frozen=True)
class ClassParameters:
    class_id: int
    class_name: str
    material: str
    color_rgb: tuple[int, int, int]
    density_g_ml: float
    density_uncertainty_g_ml: float
    density_source: str
    assumption_status: str
    shape: str = "radial_height_field"
    density_evidence: tuple[dict[str, Any], ...] = ()

    def mass_provenance(self) -> dict[str, Any]:
        return {
            "measurement_kind": "synthetic_physical",
            "density_g_ml": self.density_g_ml,
            "density_source": self.density_source,
            "density_source_ref": self.density_source,
            "assumption_status": self.assumption_status,
            "uncertainty_range": [
                max(0.01, self.density_g_ml - self.density_uncertainty_g_ml),
                self.density_g_ml + self.density_uncertainty_g_ml,
            ],
            "shape": self.shape,
            "uncertainty_range_kind": "project_assumption_around_prior_not_a_published_statistical_interval",
            "density_evidence": list(self.density_evidence),
        }


# Fallback values are explicitly labeled assumptions, never measurements.
_ASSUMED_DENSITY = 0.85
_ASSUMED_UNCERTAINTY = 0.30
_PALETTE = (
    (220, 180, 120), (174, 104, 58), (218, 197, 152), (132, 151, 83),
    (238, 226, 207), (190, 73, 50), (234, 196, 88), (111, 88, 61),
)


@lru_cache(maxsize=1)
def _density_table() -> dict[str, tuple[float, str]]:
    wed = yaml.safe_load(DEFAULT_DISH_CONFIG.read_text(encoding="utf-8"))
    menu = yaml.safe_load(DEFAULT_MENU.read_text(encoding="utf-8"))
    densities: dict[str, tuple[float, str]] = {}
    for name, record in wed.get("off_menu", {}).items():
        components = record.get("components", {}).values()
        values = [float(item["density_g_ml"]) for item in components
                  if item.get("density_g_ml") is not None]
        if values:
            densities[name] = (sum(values) / len(values), f"data/wed_dishes.yaml#off_menu.{name}")
    for class_name, serving in wed.get("serving", {}).items():
        if class_name in densities:
            continue
        dish_key = serving.get("dish")
        dish = menu.get("dishes", {}).get(dish_key, {})
        values = [float(item["density_g_ml"]) for item in dish.get("components", {}).values()
                  if item.get("density_g_ml") is not None]
        if values:
            densities[class_name] = (sum(values) / len(values),
                                     f"data/menu.yaml#dishes.{dish_key}.components")
    return densities


@lru_cache(maxsize=1)
def _density_evidence_by_class() -> dict[str, tuple[dict[str, Any], ...]]:
    """Attach FAO direct/analogue evidence without promoting it to class truth."""
    wed = yaml.safe_load(DEFAULT_DISH_CONFIG.read_text(encoding="utf-8"))
    menu = yaml.safe_load(DEFAULT_MENU.read_text(encoding="utf-8"))
    density_path = ROOT / "data" / "ingredient_densities.yaml"
    density_data = yaml.safe_load(density_path.read_text(encoding="utf-8"))
    audit_by_generic = {str(item["serving_id"]): item
                       for item in density_data.get("audit", {}).get("entries", [])}
    evidence: dict[str, tuple[dict[str, Any], ...]] = {}
    for class_name, serving in wed.get("serving", {}).items():
        dish_key = serving.get("dish")
        dish = wed.get("off_menu", {}).get(dish_key) or menu.get("dishes", {}).get(dish_key, {})
        entries = []
        for component in dish.get("components", {}).values():
            generic_id = component.get("generic_id")
            audit = audit_by_generic.get(str(generic_id))
            if audit is None:
                continue
            state = density_data.get("states", {}).get(str(audit.get("state")), {})
            reference_rows = state.get("reference_rows", [])
            reference_values = [float(item["density_g_ml"]) for item in reference_rows
                                if item.get("density_g_ml") is not None]
            entries.append({
                "generic_id": str(generic_id),
                "state": str(audit.get("state")),
                "evidence_status": str(audit.get("value_status", "assumed")),
                "reference_density_g_ml": audit.get("fao_density_g_ml"),
                "reference_rows": reference_rows,
                "reference_range_g_ml": ([min(reference_values), max(reference_values)]
                                          if reference_values else None),
                "provenance": state.get("provenance", "no FAO/INFOODS match"),
                "source": "data/ingredient_densities.yaml",
            })
        evidence[class_name] = tuple(entries)
    return evidence


@lru_cache(maxsize=4)
def load_class_registry(index_map: Path = DEFAULT_INDEX_MAP) -> dict[int, ClassParameters]:
    if not index_map.is_file():
        raise FileNotFoundError(f"WED index map not found: {index_map}")
    names = json.loads(index_map.read_text(encoding="utf-8"))
    densities = _density_table()
    density_evidence = _density_evidence_by_class()
    entries: dict[int, ClassParameters] = {}
    for raw_id, name in names.items():
        class_id = int(raw_id)
        if class_id == 0 or not name or name.lower() == "background":
            continue
        color = _PALETTE[(class_id - 1) % len(_PALETTE)]
        density, density_ref = densities.get(
            name, (_ASSUMED_DENSITY, "project-wide fallback pilot assumption"))
        uncertainty = max(0.08, density * 0.20) if name in densities else _ASSUMED_UNCERTAINTY
        entries[class_id] = ClassParameters(
            class_id=class_id,
            class_name=name,
            material=f"wed_class_{class_id:02d}",
            color_rgb=color,
            density_g_ml=density,
            density_uncertainty_g_ml=uncertainty,
            density_source=density_ref,
            assumption_status="assumed_not_measured",
            density_evidence=density_evidence.get(name, ()),
        )
    if len(entries) != 41:
        raise ValueError(f"Expected 41 WED food classes, found {len(entries)}")
    return entries


def observed_portion_ranges(manifest: Path = DEFAULT_MANIFEST) -> dict[str, tuple[float, float]]:
    """Read TRAIN-only empirical net-weight bounds by WED class."""
    if not manifest.is_file():
        raise FileNotFoundError(f"WED manifest not found: {manifest}")
    by_name: dict[str, list[float]] = {}
    rows = read_wed_train_manifest(manifest)
    for row in eligible_wed_train_rows(rows):
        for dish in row.get("dishes", []):
            weight = float(dish["weight_g"])
            if weight > 0:
                by_name.setdefault(str(dish["name"]), []).append(weight)
    return {name: (min(values), max(values)) for name, values in by_name.items()}


def wed_group_id(row: dict[str, Any]) -> str:
    return f"{row.get('date_key', row.get('date'))}_{row.get('set')}"


def read_wed_train_manifest(manifest: Path = DEFAULT_MANIFEST) -> list[dict[str, Any]]:
    """Parse only TRAIN JSONL records; never deserialize LOCKED rows."""
    train_marker = re.compile(r'"split"\s*:\s*"train"')
    rows = []
    with manifest.open(encoding="utf-8") as stream:
        for line in stream:
            if train_marker.search(line):
                row = json.loads(line)
                if row.get("split") == "train":
                    rows.append(row)
    return rows


def wed_dev_group_ids(rows: list[dict[str, Any]], *, seed: int = 42,
                      fraction: float = 0.10) -> set[str]:
    """Reproduce the existing WED DEV plate carve; ignore all LOCKED rows."""
    groups = sorted({wed_group_id(row) for row in rows if row.get("split") == "train"})
    random.Random(seed).shuffle(groups)
    count = max(1, int(len(groups) * fraction)) if groups else 0
    return set(groups[:count])


def eligible_wed_train_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dev_groups = wed_dev_group_ids(rows)
    return [row for row in rows if row.get("split") == "train"
            and wed_group_id(row) not in dev_groups]


def portion_is_supported(class_name: str, grams: float,
                         bounds: dict[str, tuple[float, float]]) -> bool:
    low_high = bounds.get(class_name)
    return low_high is not None and low_high[0] <= grams <= low_high[1]


def class_parameters_as_dict() -> list[dict[str, Any]]:
    return [asdict(item) for item in load_class_registry().values()]
