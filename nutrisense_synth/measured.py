"""Canonical measured WED examples for training and evaluation."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable, Literal

from nutrisense_synth.parameters import DEFAULT_MANIFEST, wed_group_id

MeasuredSplit = Literal["train", "dev", "locked"]
DEFAULT_WED_ROOT = Path(__file__).resolve().parents[1] / "data" / "wed"


@dataclass(frozen=True)
class MeasuredDish:
    """One WED class-total target as recorded for a physical meal image."""

    class_id: int
    class_name: str
    mass_g: float


@dataclass(frozen=True)
class MeasuredExample:
    """Image and net-mass supervision at WED's class-total granularity."""

    source_record_id: str
    source_group_id: str
    split: MeasuredSplit
    image_path: Path
    mask_path: Path | None
    dishes: tuple[MeasuredDish, ...]

    @property
    def mass_by_class(self) -> dict[int, float]:
        totals: dict[int, float] = {}
        for dish in self.dishes:
            totals[dish.class_id] = totals.get(dish.class_id, 0.0) + dish.mass_g
        return totals

    @property
    def total_mass_g(self) -> float:
        return sum(dish.mass_g for dish in self.dishes)

    @classmethod
    def from_row(cls, row: dict[str, Any], *, dataset_root: Path = DEFAULT_WED_ROOT,
                 require_files: bool = False) -> "MeasuredExample":
        split = row.get("split")
        if split not in {"train", "dev", "locked"}:
            raise ValueError(f"unsupported measured split: {split!r}")
        image_value = row.get("image")
        if not isinstance(image_value, str) or not image_value:
            raise ValueError("measured row requires an image path")
        mask_value = row.get("mask")
        if mask_value is not None and not isinstance(mask_value, str):
            raise ValueError("measured mask path must be a string or null")
        dishes_value = row.get("dishes")
        if not isinstance(dishes_value, list) or not dishes_value:
            raise ValueError("measured row requires at least one dish target")

        dishes: list[MeasuredDish] = []
        for dish in dishes_value:
            if not isinstance(dish, dict):
                raise TypeError("each measured dish target must be an object")
            class_id = dish.get("class_id")
            class_name = dish.get("name")
            mass = dish.get("weight_g")
            if not isinstance(class_id, int) or not 1 <= class_id <= 41:
                raise ValueError(f"invalid WED class id: {class_id!r}")
            if not isinstance(class_name, str) or not class_name:
                raise ValueError("measured dish requires a class name")
            if not isinstance(mass, (int, float)) or not math.isfinite(float(mass)):
                raise ValueError(f"invalid measured mass for class {class_id}")
            if float(mass) < 0:
                raise ValueError(f"measured mass must be positive for class {class_id}")
            if float(mass) == 0:
                continue
            dishes.append(MeasuredDish(class_id, class_name, float(mass)))
        if not dishes:
            raise ValueError("measured mass must be positive for at least one dish")

        image_path = dataset_root / image_value
        mask_path = dataset_root / mask_value if mask_value else None
        if require_files:
            if not image_path.is_file():
                raise FileNotFoundError(image_path)
            if mask_path is not None and not mask_path.is_file():
                raise FileNotFoundError(mask_path)

        source_record_id = image_value
        group = wed_group_id(row)
        if group in {"None_None", "_None", "None_"}:
            raise ValueError("measured row requires a physical group identity")
        return cls(source_record_id, group, split, image_path, mask_path,
                   tuple(dishes))


def read_measured_rows(manifest: Path = DEFAULT_MANIFEST) -> Iterable[dict[str, Any]]:
    """Read manifest rows without silently dropping non-TRAIN splits."""
    with manifest.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid WED manifest JSON at line {line_no}") from exc
            if not isinstance(row, dict):
                raise TypeError(f"WED manifest line {line_no} is not an object")
            yield row


def load_measured_examples(*, manifest: Path = DEFAULT_MANIFEST,
                           dataset_root: Path = DEFAULT_WED_ROOT,
                           split: MeasuredSplit | None = None,
                           exclude_groups: Iterable[str] = (),
                           require_files: bool = False) -> list[MeasuredExample]:
    """Load canonical measured examples with explicit split/group filtering."""
    excluded = set(exclude_groups)
    examples = []
    for row in read_measured_rows(manifest):
        if split is not None and row.get("split") != split:
            continue
        example = MeasuredExample.from_row(row, dataset_root=dataset_root,
                                           require_files=require_files)
        if example.source_group_id not in excluded:
            examples.append(example)
    return examples


DEFAULT_ARUCO_DIR = Path(__file__).resolve().parents[2] / "Aruco_7ID_60mm_with_food"

ARUCO_GROUND_TRUTH: dict[str, dict[str, Any]] = {
    "Dish 1": {"total_g": 450.0, "components": [
        {"name": "rice", "grams": 250.0},
        {"name": "keerai sambar", "grams": 200.0},
    ]},
    "Dish 2": {"total_g": 338.0, "components": [
        {"name": "rice", "grams": 211.0},
        {"name": "tomato rasam", "grams": 127.0},
    ]},
    "Dish 3": {"total_g": 191.0, "components": [
        {"name": "coconut chutney", "grams": 70.0},
        {"name": "chapati", "grams": 121.0},
    ]},
    "Dish 4": {"total_g": 250.0, "components": [
        {"name": "dum biryani", "grams": 206.0},
        {"name": "egg", "grams": 44.0},
    ]},
    "Dish 5": {"total_g": 150.0, "components": [
        {"name": "dum biryani", "grams": 150.0},
    ]},
    "Dish 6": {"total_g": 351.0, "components": [
        {"name": "dum biryani", "grams": 257.0},
        {"name": "egg", "grams": 94.0},
    ]},
}


@dataclass(frozen=True)
class ArucoSupervisedExample:
    """Supervised real meal capture with ArUco ground truth scale and verified mass."""

    dish_name: str
    image_path: Path
    filename: str
    ground_truth_total_g: float
    components: tuple[dict[str, Any], ...]
    cm_per_px: float
    marker_corners_px: tuple[tuple[float, float], ...]
    tilt_deg: float | None


def mask_out_marker(image_bgr: Any, corners: Any, expansion: float = 2.5) -> Any:
    """Digitally erase/mask the ArUco marker region using ambient table color."""
    import cv2
    import numpy as np
    masked = image_bgr.copy()
    c = np.asarray(corners, dtype=np.float32).reshape(4, 2)
    center = c.mean(axis=0, keepdims=True)
    expanded = center + expansion * (c - center)
    poly = np.round(expanded).astype(np.int32)

    h, w = image_bgr.shape[:2]
    xs = np.clip(poly[:, 0], 0, w - 1)
    ys = np.clip(poly[:, 1], 0, h - 1)
    x_min, x_max = max(0, int(xs.min()) - 10), min(w, int(xs.max()) + 10)
    y_min, y_max = max(0, int(ys.min()) - 10), min(h, int(ys.max()) + 10)

    patch = image_bgr[y_min:y_max, x_min:x_max]
    fill_color = (
        tuple(int(x) for x in np.median(patch, axis=(0, 1)))
        if patch.size > 0
        else (120, 100, 80)
    )

    cv2.fillConvexPoly(masked, poly, fill_color)
    return masked


def load_aruco_supervised_examples(
    dataset_dir: Path | None = None,
) -> list[ArucoSupervisedExample]:
    """Parse Aruco_7ID_60mm_with_food dataset and extract gold-standard ground truth scale targets."""
    import cv2
    from models.scale_anchor import estimate_anchor, read_exif

    data_dir = dataset_dir or DEFAULT_ARUCO_DIR
    if not data_dir.is_dir():
        return []

    examples: list[ArucoSupervisedExample] = []
    for dish_name, gt in sorted(ARUCO_GROUND_TRUTH.items()):
        dish_dir = data_dir / dish_name
        if not dish_dir.is_dir():
            continue
        for img_path in sorted(dish_dir.glob("*.jpg")):
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            exif = read_exif(img_path)
            anchor = estimate_anchor(img, exif=exif)
            if anchor.get("label") != "measured" or not anchor.get("cm_per_px"):
                continue
            corners = (anchor.get("extras") or {}).get("marker_corners_px")
            if not corners:
                continue
            corners_tuple = tuple((float(pt[0]), float(pt[1])) for pt in corners)
            examples.append(
                ArucoSupervisedExample(
                    dish_name=dish_name,
                    image_path=img_path,
                    filename=img_path.name,
                    ground_truth_total_g=float(gt["total_g"]),
                    components=tuple(gt["components"]),
                    cm_per_px=float(anchor["cm_per_px"]),
                    marker_corners_px=corners_tuple,
                    tilt_deg=anchor.get("tilt_deg"),
                )
            )
    return examples
