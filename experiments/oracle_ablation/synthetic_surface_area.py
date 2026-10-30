"""Compare global area scaling with local metric surface-area integration.

This candidate uses only the deterministic synthetic renderer's depth and
ground-truth food mask. It does not change the serving estimator.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from config import load_params
from experiments.oracle_ablation.synthetic_mask_spill import SCENES, _measure
from tests.synth.scene import render_scene


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("synthetic_surface_area.jsonl")


def _render(spec: dict) -> dict:
    return render_scene({
        "vessel": spec["vessel"],
        "seed": spec["seed"],
        "camera": spec["camera"],
        "food": {
            "radius_mm": spec["radius_mm"],
            "grams": spec["grams"],
            "density_g_ml": 0.95,
            "kappa": spec["kappa"],
            "layout": "whole",
            "components": [{"name": "synthetic_food", "material": "rice",
                            "share_g": spec["grams"]}],
        },
    })


def _world_surface_points(scene: dict) -> np.ndarray:
    depth = scene["depth_m"].astype(np.float64)
    h, w = depth.shape
    v, u = np.mgrid[0:h, 0:w]
    K = scene["camera"]["K"]
    points_camera_m = np.stack([
        (u - K[0, 2]) / K[0, 0] * depth,
        (v - K[1, 2]) / K[1, 1] * depth,
        depth,
    ], axis=-1)
    camera = scene["camera"]
    return points_camera_m @ camera["R_wc"] + camera["C"] / 1000.0


def _axis_derivative(points: np.ndarray, mask: np.ndarray, axis: int) -> np.ndarray:
    prev = np.zeros_like(points)
    nxt = np.zeros_like(points)
    has_prev = np.zeros_like(mask)
    has_next = np.zeros_like(mask)
    if axis == 1:
        prev[:, 1:] = points[:, :-1]
        nxt[:, :-1] = points[:, 1:]
        has_prev[:, 1:] = mask[:, :-1]
        has_next[:, :-1] = mask[:, 1:]
    else:
        prev[1:] = points[:-1]
        nxt[:-1] = points[1:]
        has_prev[1:] = mask[:-1]
        has_next[:-1] = mask[1:]
    center = points
    both = mask & has_prev & has_next
    only_prev = mask & has_prev & ~has_next
    only_next = mask & ~has_prev & has_next
    derivative = np.zeros_like(points)
    derivative[both] = (nxt[both] - prev[both]) * 0.5
    derivative[only_prev] = center[only_prev] - prev[only_prev]
    derivative[only_next] = nxt[only_next] - center[only_next]
    return derivative


def _surface_integral_grams(scene: dict, mask: np.ndarray, plane: list[float]) -> dict:
    """Integrate vertical height times local horizontal pixel area."""
    points = _world_surface_points(scene)
    a, b, c = (float(x) for x in plane)
    normal_camera = np.array([-a, -b, 1.0])
    normal_world = scene["camera"]["R_wc"].T @ normal_camera
    point_on_plane_world = scene["camera"]["C"] / 1000.0
    plane_offset = c + float(np.dot(normal_world, point_on_plane_world))
    if normal_world[2] < 0:
        normal_world = -normal_world
        plane_offset = -plane_offset
    z_base = (
        plane_offset - normal_world[0] * points[..., 0]
        - normal_world[1] * points[..., 1]
    ) / normal_world[2]
    height_m = np.maximum(points[..., 2] - z_base, 0.0)

    du = _axis_derivative(points, mask, axis=1)
    dv = _axis_derivative(points, mask, axis=0)
    pixel_area_m2 = np.abs(du[..., 0] * dv[..., 1] - du[..., 1] * dv[..., 0])
    volume_m3 = float(np.sum(height_m[mask] * pixel_area_m2[mask]))
    density = float(scene["cfg"]["food"]["density_g_ml"])
    volume_ml = volume_m3 * 1_000_000.0
    return {
        "grams": volume_ml * density,
        "volume_ml": volume_ml,
        "mean_height_mm": float(np.mean(height_m[mask]) * 1000.0),
        "sum_pixel_area_cm2": float(np.sum(pixel_area_m2[mask]) * 10_000.0),
    }


def run() -> list[dict]:
    params = load_params()
    records = []
    for spec in SCENES:
        scene = _render(spec)
        mask = np.asarray(scene["mask_food"], dtype=bool)
        baseline = _measure(scene, mask, params)
        candidate = _surface_integral_grams(
            scene, mask, baseline["ring_fit_plane_camera"],
        )
        truth = float(scene["grams_gt_total"])
        base_error = 100.0 * (baseline["grams"] - truth) / truth
        candidate_error = 100.0 * (candidate["grams"] - truth) / truth
        records.append({
            "scene": spec["name"],
            "vessel": spec["vessel"],
            "truth_g": truth,
            "baseline": {
                "grams": float(baseline["grams"]),
                "signed_error_pct": base_error,
                "area_cm2": float(baseline["area_cm2"]),
                "mean_height_mm": float(baseline["mean_h_mm"]),
            },
            "surface_integral": {
                **candidate,
                "signed_error_pct": candidate_error,
            },
            "absolute_error_improvement_pp": abs(base_error) - abs(candidate_error),
        })
    OUTPUT.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    return records


def main() -> None:
    records = run()
    improvements = [r["absolute_error_improvement_pp"] for r in records]
    pass_count = sum(v >= 5.0 for v in improvements)
    max_regression = max(max(-v, 0.0) for v in improvements)
    print(f"scenes={len(records)}")
    print(f"improvement_ge_5pp={pass_count}/{len(records)}")
    print(f"max_absolute_error_regression_pp={max_regression:.2f}")
    print(f"preregistered_criterion_met={pass_count >= 4 and max_regression <= 2.0}")
    for r in records:
        b, c = r["baseline"], r["surface_integral"]
        print(
            f"{r['scene']}: truth={r['truth_g']:.2f}g "
            f"baseline={b['grams']:.2f}g ({b['signed_error_pct']:+.2f}%) "
            f"candidate={c['grams']:.2f}g ({c['signed_error_pct']:+.2f}%) "
            f"abs_error_improvement={r['absolute_error_improvement_pp']:+.2f}pp"
        )
    print(f"raw_jsonl={OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
