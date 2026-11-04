"""Generator interface: methods receive a scene-owned condition and return RGB.

The interface deliberately does not let an appearance generator author labels.
Labels and marker geometry remain owned by the scene renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np


@dataclass(frozen=True)
class GenerationContext:
    scene_id: str
    seed: int
    condition_rgb: np.ndarray
    semantic_mask: np.ndarray
    depth_m: np.ndarray
    marker_mask: np.ndarray
    food_mask: np.ndarray
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        if self.food_mask.shape != self.condition_rgb.shape[:2]:
            raise ValueError("food_mask must match condition image dimensions")
        if self.marker_mask.shape != self.condition_rgb.shape[:2]:
            raise ValueError("marker_mask must match condition image dimensions")
        if not np.asarray(self.marker_mask).any() and any(
                key in self.metadata for key in ("marker_scale", "aruco_scale", "marker_pose")):
            raise ValueError("No-card generation context cannot receive marker-derived scale or pose")


class AppearanceMethod(Protocol):
    name: str
    revision: str

    def generate(self, context: GenerationContext) -> np.ndarray:
        """Return HxWx3 uint8 RGB; spatial labels are always renderer-owned."""


def validate_rgb(image: np.ndarray, expected_shape: tuple[int, int, int]) -> None:
    if image.shape != expected_shape or image.dtype != np.uint8:
        raise ValueError(f"Generator must return uint8 RGB with shape {expected_shape}")


def validate_semantic_mask(mask: np.ndarray) -> np.ndarray:
    labels = np.asarray(mask)
    if labels.ndim != 2 or not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("Semantic conditions must be a 2D integer WED class map")
    if labels.size and (int(labels.min()) < 0 or int(labels.max()) > 41):
        raise ValueError("Semantic condition contains a class outside WED IDs 0..41")
    return labels.astype(np.int64, copy=False)


def restore_scene_owned_pixels(generated_rgb: np.ndarray,
                               context: GenerationContext) -> np.ndarray:
    """Keep renderer-owned background and marker pixels byte-identical."""
    validate_rgb(generated_rgb, context.condition_rgb.shape)
    if context.food_mask.shape != generated_rgb.shape[:2]:
        raise ValueError("food_mask must align with the generated image")
    if context.marker_mask.shape != generated_rgb.shape[:2]:
        raise ValueError("marker_mask must align with the generated image")
    editable = np.asarray(context.food_mask, dtype=bool) & ~np.asarray(context.marker_mask, dtype=bool)
    out = context.condition_rgb.copy()
    out[editable] = generated_rgb[editable]
    return out
