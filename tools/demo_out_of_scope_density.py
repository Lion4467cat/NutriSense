"""07c demo: an out-of-scope dish served through the EXISTING measured tier,
with per-component densities from the FAO-derived density table
(data/ingredient_densities.yaml) instead of ad-hoc assumptions.

This rides the production seam — models.portion_estimator.estimate_portion
on a measured anchor (reference-card cm/px facts) — with a synthetic 640x480
overhead-looking capture: flat depth + a round food dome on a flat table.
Nothing about serving behavior changes: the demo exists to show the
out-of-scope dish path and where each density value comes from.

Run: .venv/bin/python -m tools.demo_out_of_scope_density
"""
from __future__ import annotations

import numpy as np

from config import load_densities, load_params
from models.portion_estimator import estimate_portion

# Out-of-scope thali dish: NOT a WED class and NOT a menu dish — its
# components are resolved through the density table's generic_id audit pairs.
COMPONENTS = {  # name -> (share, serving generic_id)
    "rice":    (0.55, "rice_boiled"),
    "dal":     (0.25, "sambar"),
    "curd":    (0.10, "curd"),
    "veg_fry": (0.07, "vegetable_fry"),
    "papad":   (0.03, "papad_type"),
}


def component_densities() -> list[tuple[str, str, float | None, str]]:
    """Cite-backed density per demo component; None -> fallthrough to assumed."""
    doc = load_densities()
    audit = {e["serving_id"]: e for e in doc["audit"]["entries"]}
    out = []
    for name, (share, gid) in COMPONENTS.items():
        e = audit.get(gid)
        if e and e.get("value_status") == "literature":
            out.append((name, gid, e["fao_density_g_ml"], "FAO literature row"))
        elif e and e.get("value_status") == "analogue_transfer":
            out.append((name, gid, e["fao_density_g_ml"],
                        "nearest-analogue FAO row (audit-only)"))
        elif e:
            out.append((name, gid, e["served_density_g_ml"],
                        "serving assumed (no FAO row)"))
        else:
            out.append((name, gid, None, "no audit entry"))
    return out


def main() -> int:
    H, W = 480, 640
    params = load_params()

    # --- synthetic capture: plate on a flat table, food dome on the plate ---
    yy, xx = np.mgrid[0:H, 0:W]
    plate_r_px, food_r_px = 150.0, 112.0
    r = np.sqrt((yy - 240.0) ** 2 + (xx - 320.0) ** 2)
    in_plate = r <= plate_r_px
    image = np.zeros((H, W, 3), np.uint8)
    image[in_plate] = (40, 40, 40)

    # measured-tier facts (as the reference-card anchor produces):
    # plate diameter 28 cm -> cm/px
    cm_px = 28.0 / (2 * plate_r_px)
    anchor = {"label": "measured", "method": "card_demo", "cm_per_px": cm_px,
              "interval": (cm_px * 0.997, cm_px * 1.003), "tilt_deg": 0.0}

    # flat depth at Z0 with an 8 cm food dome (camera z: food is nearer)
    z0, dome_peak = 0.60, 0.080
    dome = dome_peak * np.clip(1.0 - np.clip(r, 0, None) / food_r_px, 0, 1)
    depth = np.full((H, W), z0)
    depth[in_plate] -= dome[in_plate]
    mask = r <= food_r_px
    image[mask] = (90, 140, 80)

    rows = component_densities()
    missing = [name for name, _gid, d, _s in rows if d is None]
    if missing:
        print(f"can't run: no density for {missing}")
        return 1
    dish = {"components": {}}
    for name, (share, gid) in COMPONENTS.items():
        d = next(d for n, g, d, _s in rows if g == gid)
        dish["components"][gid] = {"share": share, "density_g_ml": d}

    out = estimate_portion(
        image, mask, depth, anchor,
        {"K": np.array([[615.0, 0, W / 2], [0, 615.0, H / 2], [0, 0, 1.0]])},
        dish, params=params)

    print("== out-of-scope thali through the measured tier (07c demo) ==")
    print(f"footprint {out['area_cm2']:.0f} cm^2, mean height {out['mean_h_mm']:.1f} mm, "
          f"volume {out['volume_ml']:.0f} ml")
    print(f"effective density {out['density_eff']:.3f} g/ml -> grams {out['grams']:.0f} g "
          f"(base_method={out['base_method']}, tier={out['scale_tier']})")
    for name, gid, d, src in rows:
        share = COMPONENTS[name][0]
        print(f"  {name:>8}: share {share:.2f} x density {d:.3f} g/ml "
              f"[{src}] -> {share * out['grams']:.0f} g")
    print(f"flags={out['flags']} sigma_grams_rel={out['sigma_grams_rel']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
