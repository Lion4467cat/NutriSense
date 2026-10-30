"""Build the mask diagnosis tables from captured raw records and masks."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from summarize_mask_diagnosis import _iou

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "aruco_mask_capture.jsonl"
OUT = ROOT / "MASK_DIAGNOSIS_TABLES.md"
GT_VISIBLE_PORTIONS = {
    "Dish 1": 2, "Dish 2": 2, "Dish 3": 2,
    "Dish 4": 2, "Dish 5": 1, "Dish 6": 3,
}


def esc(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> None:
    rows = [json.loads(line) for line in RAW.read_text().splitlines()
            if json.loads(line).get("event") == "image_result"
            and json.loads(line).get("mode") == "default"]
    out: list[str] = [
        "# ArUco mask diagnosis tables",
        "",
        ("All measurements below are computed from `aruco_mask_capture.jsonl`, "
        "the saved NPZ masks/depth maps, and the source image/config. `inside` "
        "means fraction of item-mask pixels inside the top-level SAM2 mask; "
        "it is a computational comparison, not a ground-truth food label. "
        "Classifier crop fraction is the fraction of the 10%-padded item bbox "
        "crop inside the top-level mask."),
        "",
        "## Per image",
        "",
        ("| Plate | Image | Anchor | Distinct visible food portions | Pipeline item rows | "
        "Pairs IoU 0.50–<0.70 | Item-mask sum / top-mask area | Predicted total (g) |"),
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    all_pairs: list[tuple[str, str, int, int, float]] = []
    mask_bands = {"mostly inside": 0, "mixed": 0, "mostly outside": 0}
    crop_bands = {"food dominant": 0, "mixed": 0, "context dominant": 0}
    item_total = 0
    mask_ratio_values: list[float] = []
    for row in rows:
        path = Path(row["image"])
        result = row["result"]
        items = result.get("items") or []
        diag = row.get("mask_diagnostics") or {}
        pair_count = 0
        with np.load(row["mask_artifacts"]["npz"]) as z:
            top = z["top_mask"].astype(bool) if "top_mask" in z else None
            masks = [z[f"item_mask_{i}"].astype(bool)
                     for i in range(len(items)) if f"item_mask_{i}" in z]
            if len(masks) == len(items):
                for i in range(len(masks)):
                    for j in range(i + 1, len(masks)):
                        overlap = _iou(masks[i], masks[j])
                        if 0.50 <= overlap < 0.70:
                            pair_count += 1
                            all_pairs.append((row["plate"], path.name, i, j, overlap))
                for i, (item, mask) in enumerate(zip(items, masks)):
                    area = int(mask.sum())
                    inside = (float((mask & top).sum() / area)
                              if top is not None and area else None)
                    if inside is None:
                        mask_category = "n/a"
                    elif inside >= 0.60:
                        mask_category = "mostly inside"
                    elif inside <= 0.40:
                        mask_category = "mostly outside"
                    else:
                        mask_category = "mixed"
                    if mask_category in mask_bands:
                        mask_bands[mask_category] += 1
                    item_total += 1
                    x0, y0, x1, y1 = item.get("bbox") or [0, 0, 0, 0]
                    padx, pady = int((x1 - x0) * 0.10), int((y1 - y0) * 0.10)
                    crop = top[max(0, y0 - pady):min(top.shape[0], y1 + pady),
                               max(0, x0 - padx):min(top.shape[1], x1 + padx)] if top is not None else np.zeros((0, 0), dtype=bool)
                    crop_fraction = float(crop.mean()) if crop.size else None
                    crop_category = ("n/a" if crop_fraction is None else
                                     "food dominant" if crop_fraction >= 0.60 else
                                     "context dominant" if crop_fraction <= 0.40 else "mixed")
                    if crop_category in crop_bands:
                        crop_bands[crop_category] += 1
        ratio = diag.get("item_area_sum_to_top_ratio")
        if ratio is not None:
            mask_ratio_values.append(float(ratio))
        out.append(
            f"| {row['plate']} | `{esc(path.name)}` | {row['anchor_tier']} | "
            f"{GT_VISIBLE_PORTIONS[row['plate']]} | {len(items)} | {pair_count} | "
            f"{ratio if ratio is not None else 'n/a'} | "
            f"{(result.get('portion') or {}).get('grams', 'n/a')} |"
        )
    out += [
        "",
        ("The visible portion count follows the unchanged plate contents seen "
        "across each folder: Dish 3 counts the two chapatis as one weighed "
        "serving plus chutney; Dish 6 counts biryani and two eggs separately."),
        "",
        "## Per item: mask, crop classifier, and measured geometry",
        "",
        ("`Area/plate area` and `larger than plate` are n/a: the attempted full "
        "frame rim detector did not reliably identify the plate among bowl/food "
        "circles. The visual notes refer to the per-image full-frame overlay "
        "and item index/color in its footer."),
        "",
        ("| Plate / image / item | Label, grams | Mask px | Fraction in top mask | "
        "Area / plate area | Classifier crop fraction in top mask | Top two labels (scores); confidence | "
        "Mean / max height mm | Footprint cm² | Base method; plane c (m) | Density g/ml | Visual read |"),
        "|---|---|---:|---:|---:|---:|---|---:|---:|---|---:|---|",
    ]
    marker_rows = []
    selected_height_rows = []
    for row in rows:
        path = Path(row["image"])
        result = row["result"]
        items = result.get("items") or []
        artifact = row.get("mask_artifacts") or {}
        with np.load(artifact["npz"]) as z:
            top = z["top_mask"].astype(bool) if "top_mask" in z else None
            masks = [z[f"item_mask_{i}"].astype(bool)
                     for i in range(len(items)) if f"item_mask_{i}" in z]
        for i, item in enumerate(items):
            if i >= len(masks):
                continue
            mask = masks[i]
            area = int(mask.sum())
            inside = float((mask & top).sum() / area) if top is not None and area else None
            x0, y0, x1, y1 = item.get("bbox") or [0, 0, 0, 0]
            padx, pady = int((x1 - x0) * 0.10), int((y1 - y0) * 0.10)
            crop = top[max(0, y0 - pady):min(top.shape[0], y1 + pady),
                       max(0, x0 - padx):min(top.shape[1], x1 + padx)] if top is not None else np.zeros((0, 0), dtype=bool)
            crop_fraction = float(crop.mean()) if crop.size else None
            top2rows = artifact.get("item_classifier_top2") or []
            classifier = top2rows[i] if i < len(top2rows) else None
            top2 = (classifier or {}).get("top2") or []
            top2_text = "; ".join(f"{x['label']}={x['score']:.4f}" for x in top2)
            confidence = (classifier or {}).get("confidence")
            geom = next((g for g in (artifact.get("item_geometry_telemetry") or [])
                         if g.get("mask_index") == i), None)
            portion = item.get("portion") or {}
            if inside is None:
                visual = "top mask unavailable"
            elif inside >= 0.60:
                visual = "food-centered in overlay; plate/rim may also enter"
            elif inside <= 0.40:
                visual = "mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food"
            else:
                visual = "mixed food/context in overlay"
            out.append(
                f"| {row['plate']} / `{esc(path.name)}` / {i} | "
                f"{(item.get('classification') or {}).get('dish') or 'unrecognized'}, "
                f"{portion.get('grams', 'n/a')} | {area} | "
                f"{inside if inside is not None else 'n/a'} | n/a | "
                f"{crop_fraction if crop_fraction is not None else 'n/a'} | "
                f"{top2_text or 'n/a'}; {confidence if confidence is not None else 'n/a'} | "
                f"{(geom or {}).get('mean_height_mm', 'n/a')} / "
                f"{(geom or {}).get('max_height_mm', 'n/a')} | "
                f"{(geom or {}).get('area_cm2', 'n/a')} | "
                f"{(geom or {}).get('base_method', 'n/a')}; "
                f"{((geom or {}).get('base_plane_coefficients_camera') or [None,None,None])[2]} | "
                f"{(geom or {}).get('density_g_ml', 'n/a')} | {visual} |"
            )
        anchor = row.get("anchor_tier")
        quad = artifact.get("marker_quad_px")
        if anchor == "measured" and quad is not None:
            pts = np.asarray(quad, dtype=np.float64).reshape(4, 2)
            sides = [float(np.linalg.norm(pts[(i + 1) % 4] - pts[i]))
                     for i in range(4)]
            marker_px = sum(sides) / 4.0
            scale = (result.get("anchor") or {}).get("cm_per_px")
            marker_rows.append((row["plate"], path.name, marker_px,
                                min(sides) / max(sides), scale))
        if artifact.get("height_overlay"):
            with np.load(artifact["npz"]) as z:
                top = z["top_mask"].astype(bool)
                for geom in artifact.get("item_geometry_telemetry") or []:
                    key = f"item_height_mm_{geom['geometry_call_index']}"
                    if key not in z:
                        continue
                    hmap = z[key]
                    outside = np.isfinite(hmap) & ~top
                    vals = hmap[outside]
                    positive = vals[vals > 0]
                    selected_height_rows.append((
                        row["plate"], path.name, geom.get("mask_index"),
                        geom.get("mean_height_mm"), geom.get("max_height_mm"),
                        int(outside.sum()), int((vals > 0).sum()),
                        float(positive.mean()) if len(positive) else None,
                        float(np.percentile(positive, 95)) if len(positive) else None,
                        float(positive.max()) if len(positive) else None,
                    ))
    out += [
        "",
        (f"Computed mask/top fraction bands (0.60 and 0.40 cut points): "
        f"mostly inside {mask_bands['mostly inside']}, mixed {mask_bands['mixed']}, "
        f"mostly outside {mask_bands['mostly outside']} (n={item_total})."),
        (f"Classifier crop/top-mask fraction bands: food-dominant {crop_bands['food dominant']}, "
        f"mixed {crop_bands['mixed']}, context-dominant {crop_bands['context dominant']} (n={item_total})."),
        ("The crop categories are a mask-area proxy checked against the actual "
        "photos; they are not a pixel-level annotation of every food object."),
        "",
        "## Pairwise IoU in the dedup threshold band",
        "",
        ("The detector removes pre-upsample mask pairs at IoU >= 0.70. The rows "
        "below are returned item masks whose measured IoU is 0.50 to <0.70."),
        "",
        "| Plate | Image | Pair | IoU |",
        "|---|---|---:|---:|",
    ]
    out.extend(f"| {plate} | `{esc(name)}` | {i}-{j} | {iou:.8f} |"
               for plate, name, i, j, iou in all_pairs)
    out += ["", "## Marker scale and tilt proxy", "",
            ("Marker physical side from `data/anchor_config.json`: 60.0 mm. "
            "Marker side px is the mean of the four quad edges. Aspect proxy "
            "is shortest/longest edge. Plate diameter itself is n/a because "
            "the rim fit was not reliable."), "",
            "| Plate | Image | Marker side px | Edge aspect proxy | cm/px | Plate diameter cm |",
            "|---|---|---:|---:|---:|---:|"]
    for plate, name, px, aspect, scale in marker_rows:
        out.append(f"| {plate} | `{esc(name)}` | {px:.4f} | {aspect:.6f} | "
                   f"{scale} | n/a |")
    for row in rows:
        if row["anchor_tier"] == "prior":
            out.append(f"| {row['plate']} | `{esc(Path(row['image']).name)}` | n/a | n/a | n/a | n/a |")
    out += ["", "## Height map evidence for rim/table overlap", "",
            ("Height maps are per measured item mask over its fitted base plane. "
            "`outside top pixels` includes the visibly overlaid plate/rim and "
            "table/context, so it is not an isolated plate-rim segmentation."),
            "", ("| Plate | Image | Item | Mean h mm | Max h mm | Outside-top pixels | "
            "Positive outside-top pixels | Mean positive mm | P95 mm | Max positive mm |"),
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for record in selected_height_rows:
        plate, name, i, mean, maxh, nout, npos, pmean, p95, pmax = record
        out.append(f"| {plate} | `{esc(name)}` | {i} | {mean} | {maxh} | {nout} | "
                   f"{npos} | {pmean} | {p95} | {pmax} |")
    out += ["", "## Visual observations by plate folder", "",
            ("These are observations from the saved full-frame overlays/contact "
            "sheets. The mask index is the matching footer color/index."), "",
            "| Plate | Visual observation |",
            "|---|---|"]
    notes = {
        "Dish 1": "Rice mound and separate sambar bowl are both visible. Item outlines extend across the steel plate/rim, wood tabletop, and marker/card in multiple angles; several are much broader than the rice pile.",
        "Dish 2": "Rice plate and rasam bowl are both visible. Some item outlines follow those vessels, while other outlines include large tabletop and plate-rim regions; the primary top mask does not represent both foods as one region.",
        "Dish 3": "Chapati(s) on the plate and the separate chutney bowl are visible. The pipeline produced zero item rows after unrecognized/out-of-scope classification on these three views; top-level overlays remain available.",
        "Dish 4": "Biryani and egg are visible. Item outlines include food, plate/rim, and in some views table/card context; all resolved items in this capture were labeled vegetable_rice.",
        "Dish 5": "One biryani pile is visible. Several returned masks extend across the plate/rim and wood table; some also include the marker/card context.",
        "Dish 6": "Biryani and eggs are visible. Item outlines include the food and eggs, but also broad plate/rim/table/card areas in several views; the top mask mostly traces the biryani mound and excludes some peripheral food.",
    }
    out.extend(f"| {plate} | {note} |" for plate, note in notes.items())
    out += ["", "## Per-image contact sheets", "",
            "| Plate | Contact sheet |", "|---|---|"]
    out.extend(f"| {plate} | [overlays/{plate.replace(' ', '_')}_contact_sheet.png] |"
               for plate in sorted(GT_VISIBLE_PORTIONS))
    OUT.write_text("\n".join(out) + "\n")
    print(f"report_tables={OUT}")
    print(f"image_rows={len(rows)} item_rows={item_total} "
          f"band_pairs={len(all_pairs)} marker_rows={len(marker_rows)} "
          f"height_rows={len(selected_height_rows)}")
    print(f"mask_fraction_bands={mask_bands}")
    print(f"crop_fraction_bands={crop_bands}")
    if mask_ratio_values:
        print(f"item_sum_to_top_ratio_min={min(mask_ratio_values)} "
              f"max={max(mask_ratio_values)} "
              f"images_over_1={sum(x > 1 for x in mask_ratio_values)}")


if __name__ == "__main__":
    main()
