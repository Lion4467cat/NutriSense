"""Render score tables from the immutable ArUco raw JSONL."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_aruco_eval import GROUND_TRUTH


def _fmt(value: Any, digits: int = 1) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _signed(value: Any) -> str:
    return "null" if value is None else f"{float(value):+.1f}"


def _reason_codes(result: dict[str, Any]) -> str:
    reasons = [x.get("kind") for x in result.get("reasons") or [] if x.get("kind")]
    failures = [x.get("code") or x.get("stage") for x in result.get("failures") or []]
    return ", ".join(str(x) for x in reasons + failures) or "none"


def _truth(plate: str) -> float:
    return float(GROUND_TRUTH[plate]["total_g"])


def _score(total: Any, truth: float) -> tuple[float | None, float | None, str]:
    if total is None:
        return None, None, "null"
    err = float(total) - truth
    return err, 100.0 * err / truth, "over" if err > 0 else "under" if err < 0 else "exact"


def _print_table(headers: list[str], rows: list[list[Any]]) -> None:
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        print("| " + " | ".join(str(x).replace("|", "\\|").replace("\n", " ") for x in row) + " |")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw", type=Path, nargs="?",
                    default=Path(__file__).resolve().parent / "aruco_raw.jsonl")
    args = ap.parse_args()
    data = [json.loads(line) for line in args.raw.read_text().splitlines()]
    base = [r for r in data if r.get("mode") == "default"]
    forced = [r for r in data if r.get("mode") == "forced_prior_paired"]
    replay = next((r for r in data if r.get("mode") == "default_replay_flag_off"), None)
    replay_check = next((r for r in data if r.get("event") == "default_flag_off_replay_check"), {})

    print("## Per-image primary plate scores")
    rows = []
    for r in base:
        result = r["result"]
        total = (result.get("portion") or {}).get("grams")
        truth = _truth(r["plate"])
        err, pct, direction = _score(total, truth)
        rows.append([r["plate"], Path(r["image"]).name, r["anchor_tier"],
                     "; ".join(r["classification_score"].get("predicted_labels") or []) or "none",
                     _fmt(total), _fmt(truth), _signed(err), _fmt(pct), direction,
                     r["classification_score"].get("correct"), result.get("verdict"),
                     _reason_codes(result)])
    _print_table(["Plate", "Image", "Anchor", "Predicted labels", "Pred g", "True g",
                  "Signed g", "% err", "Direction", "Class correct", "Verdict", "Reason codes"], rows)

    print("\n## Anchor evidence and per-image item outputs")
    rows = []
    for r in base:
        result = r["result"]
        masks = r.get("mask_diagnostics") or {}
        mask_areas = masks.get("item_mask_areas") or []
        item_detail = []
        for i, item in enumerate(result.get("items") or []):
            label = (item.get("classification") or {}).get("dish")
            grams = (item.get("portion") or {}).get("grams")
            area = mask_areas[i].get("area_px") if i < len(mask_areas) else None
            item_detail.append({"i": i, "dish": label, "grams": grams,
                                "mask_area_px": area,
                                "reason": (item.get("reason") or {}).get("kind")})
        rows.append([r["plate"], Path(r["image"]).name, r["anchor_tier"],
                     r.get("detector_rejection_evidence") or "—",
                     json.dumps(item_detail, ensure_ascii=False, separators=(",", ":")),
                     _fmt(masks.get("top_food_area_px"), 0),
                     _fmt(r.get("elapsed_s"), 2),
                     json.dumps(r.get("pipeline_stage_timings_s") or {}, separators=(",", ":"))])
    _print_table(["Plate", "Image", "Anchor", "Detector rejection evidence (prior only)",
                  "Items: label/grams/mask px/reason", "Top mask px", "Elapsed s", "Stage timings s"], rows)

    print("\n## Per-component scores and unmatched labels")
    rows = []
    for r in base:
        for c in r["component_scores"].get("components") or []:
            rows.append([r["plate"], Path(r["image"]).name, c["component"],
                         _fmt(c["predicted_g"]), _fmt(c["true_g"]),
                         _signed(c["signed_error_g"]), _fmt(c["percent_error"]),
                         json.dumps(c["matched_items"], ensure_ascii=False)])
        unmatched = r["component_scores"].get("unmatched_items") or []
        unmatched_components = r["component_scores"].get("unmatched_ground_truth_components") or []
        rows.append([r["plate"], Path(r["image"]).name, "UNMATCHED ITEMS",
                     "—", "—", "—", "—", json.dumps(unmatched, ensure_ascii=False)])
        rows.append([r["plate"], Path(r["image"]).name, "UNMATCHED COMPONENTS",
                     "—", "—", "—", "—", ", ".join(unmatched_components) or "none"])
    _print_table(["Plate", "Image", "Component/status", "Pred g", "True g", "Signed g",
                  "% err", "Matched items / unmatched detail"], rows)

    print("\n## Plate direction and angle spread (default detected anchors only)")
    rows = []
    for plate, gt in GROUND_TRUTH.items():
        plate_rows = [r for r in base if r["plate"] == plate]
        measured = [float((r["result"].get("portion") or {})["grams"])
                    for r in plate_rows if r["anchor_tier"] == "measured"
                    and (r["result"].get("portion") or {}).get("grams") is not None]
        prior = [float((r["result"].get("portion") or {})["grams"])
                 for r in plate_rows if r["anchor_tier"] == "prior"
                 and (r["result"].get("portion") or {}).get("grams") is not None]
        scored = [float((r["result"].get("portion") or {})["grams"])
                  for r in plate_rows
                  if (r["result"].get("portion") or {}).get("grams") is not None]
        dirs = [_score(g, float(gt["total_g"]))[2] for g in scored]
        direction = "no grams" if not dirs else "over" if all(d == "over" for d in dirs) else "under" if all(d == "under" for d in dirs) else "mixed"
        def spread(values: list[float], total_g: float) -> str:
            if not values:
                return "n/a"
            low, high = min(values), max(values)
            return f"{low:.1f}–{high:.1f} g; range {high-low:.1f} g ({100 * (high - low) / total_g:.1f}% true)"
        total_g = float(gt["total_g"])
        rows.append([plate, _fmt(total_g), direction, spread(measured, total_g), spread(prior, total_g)])
    _print_table(["Plate", "True g", "Direction across available predictions", "Measured-anchor spread", "Prior-anchor spread"], rows)

    print("\n## Paired card versus forced-prior errors (same measured-anchor images)")
    base_by_image = {r["image"]: r for r in base if r["anchor_tier"] == "measured"}
    forced_by_image = {r["image"]: r for r in forced}
    rows = []
    for image, b in base_by_image.items():
        f = forced_by_image.get(image)
        if f is None:
            continue
        truth = _truth(b["plate"])
        card = (b["result"].get("portion") or {}).get("grams")
        no_card = (f["result"].get("portion") or {}).get("grams")
        card_err = _score(card, truth)[0]
        prior_err = _score(no_card, truth)[0]
        rows.append([b["plate"], Path(image).name, _fmt(card), _signed(card_err),
                     _fmt(no_card), _signed(prior_err),
                     "null" if card is None or no_card is None else f"{float(no_card)-float(card):+.1f}"])
    _print_table(["Plate", "Image", "Card pred g", "Card signed g", "Forced-prior pred g",
                  "Forced-prior signed g", "Prior minus card g"], rows)
    print("Flag-off replay check: " + json.dumps(replay_check, sort_keys=True))
    if replay:
        print("Replay result: " + json.dumps({"image": Path(replay["image"]).name,
              "anchor_tier": replay["anchor_tier"],
              "grams": (replay["result"].get("portion") or {}).get("grams")}, sort_keys=True))

    print("\n## Duplicate-mask and area checks (all default images with >1 output item)")
    rows = []
    for r in base:
        items = r["result"].get("items") or []
        if len(items) <= 1:
            continue
        md = r["mask_diagnostics"]
        max_iou = max((float(p["iou"]) for p in md.get("pairwise_iou") or []), default=0.0)
        total = (r["result"].get("portion") or {}).get("grams")
        flagged_idx = md.get("flagged_item_indices") or []
        item_grams = [((it.get("portion") or {}).get("grams"))
                      for it in items]
        flagged_known = sum(float(item_grams[i]) for i in flagged_idx
                            if i < len(item_grams) and item_grams[i] is not None)
        flagged_unknown = sum(i >= len(item_grams) or item_grams[i] is None
                              for i in flagged_idx)
        flagged_pct = (100.0 * flagged_known / float(total)
                       if total not in (None, 0) else None)
        rows.append([r["plate"], Path(r["image"]).name, len(items),
                     _fmt(md.get("top_food_area_px"), 0), _fmt(md.get("sum_item_mask_area_px"), 0),
                     _fmt(md.get("item_area_sum_to_top_ratio"), 3), _fmt(max_iou, 3),
                     json.dumps([{"i": p["i"], "j": p["j"], "iou": round(float(p["iou"]), 6)}
                                 for p in md.get("pairwise_iou") or []], separators=(",", ":")),
                     json.dumps(md.get("item_mask_areas"), separators=(",", ":")),
                     ",".join(map(str, md.get("flagged_item_indices") or [])) or "none",
                     f"{_fmt(flagged_known)} known g ({_fmt(flagged_pct)}% total; missing item grams={flagged_unknown})",
                     _fmt(total), _fmt(md.get("duplicate_dropped_total_g")),
                     _signed(md.get("duplicate_drop_delta_g"))])
    _print_table(["Plate", "Image", "Items", "Top area px", "Sum item px", "Sum/top", "Max IoU",
                  "All pairwise IoU", "Item mask areas/outside", "Flagged idx", "Flagged grams (% total)",
                  "Pred total", "If overlap duplicate dropped", "Delta g"], rows)

    print("\n## Per-plate direction counts")
    rows = []
    for plate, gt in GROUND_TRUTH.items():
        vals = [(r["result"].get("portion") or {}).get("grams") for r in base if r["plate"] == plate]
        scored = [v for v in vals if v is not None]
        over = sum(float(v) > float(gt["total_g"]) for v in scored)
        under = sum(float(v) < float(gt["total_g"]) for v in scored)
        exact = sum(float(v) == float(gt["total_g"]) for v in scored)
        missing = len(vals) - len(scored)
        rows.append([plate, f"over {over}; under {under}; exact {exact}; null {missing}"])
    _print_table(["Plate", "Image direction counts"], rows)
    print(f"\nRecords: default={len(base)} forced_prior_paired={len(forced)} flag_off_replay={int(replay is not None)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
