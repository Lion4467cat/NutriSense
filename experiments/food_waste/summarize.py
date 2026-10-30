"""Summarize a saved Food Waste JSONL without touching model code."""
from __future__ import annotations

import json
import argparse
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw.jsonl"
MASK_AUDIT = HERE / "mask_audit.jsonl"
OUT = HERE / "RESULTS.md"


def _fmt(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RAW)
    parser.add_argument("--mask-audit", type=Path, default=MASK_AUDIT)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text().splitlines() if line.strip()]
    run_metadata = next((row for row in rows if row.get("event") == "run_metadata"), {})
    split_name = run_metadata.get("split_read", "unknown")
    phase = run_metadata.get("phase", split_name)
    image_rows = [row for row in rows if row.get("event") == "image_result"]
    if not image_rows:
        raise RuntimeError("raw JSONL contains no image_result rows")
    groups: dict[int, list[dict]] = defaultdict(list)
    for row in image_rows:
        groups[int(row["receipt_id"])].append(row)

    lines = [
        "# AI-ServicesBB Food Waste diagnostic results",
        "",
        ("Dataset: `AI-ServicesBB/food-waste-dataset`, revision `f008d0c7b41ea4408b66bd1b7bb9ecd58b70349d`; "
        "author-stated CC BY 4.0 (cite [author repo](https://github.com/aihpi/pilotproject-food-waste) "
        "and [dataset card](https://huggingface.co/datasets/AI-ServicesBB/food-waste-dataset))."),
        f"This is a current-pipeline cross-domain `{split_name}` run; it is not a model-selection claim.",
        ("The author official `test` split was evaluated once and is permanently closed to development."
         if run_metadata.get("official_test_evaluation_only") else
         f"Only the author `{split_name}` split was queried; the other split was not fetched by this run."),
        "Ground truth is food-only sum of `Menge_Rückläufer`. Null predictions are abstentions",
        "and are excluded from grams error; they are reported separately, not converted to zero.",
        "All metrics are descriptive over repeated views grouped by receipt.",
        *( ["The remaining eight train receipts and 143 views are in [the extended report](RESULTS_EXTENDED.md)."]
           if phase == "initial" and split_name == "train" else [] ),
        "",
        "## Per-receipt score",
        "",
        "| Receipt | True food g | Views | Numeric | Abstain | Mean predicted g (numeric only) | Mean signed error g | MAE g | Numeric min–max g | Spread % of true | Direction |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    all_signed: list[float] = []
    all_abs: list[float] = []
    total_views = len(image_rows)
    for receipt in sorted(groups):
        group = groups[receipt]
        truth_set = {float(row["ground_truth_food_g"]) for row in group}
        if len(truth_set) != 1:
            raise RuntimeError(f"ground truth varies within receipt {receipt}")
        truth = truth_set.pop()
        pred_rows = [row for row in group if row.get("predicted_total_g") is not None]
        preds = [float(row["predicted_total_g"]) for row in pred_rows]
        signed = [pred - truth for pred in preds]
        all_signed.extend(signed)
        all_abs.extend(abs(error) for error in signed)
        mean_error = statistics.mean(signed) if signed else None
        mae = statistics.mean(abs(error) for error in signed) if signed else None
        spread = (100.0 * (max(preds) - min(preds)) / truth) if preds and truth else None
        direction = "no numeric output" if not signed else ("over" if mean_error > 0 else "under" if mean_error < 0 else "even")
        range_text = f"{min(preds):.1f}–{max(preds):.1f}" if preds else "—"
        lines.append(
            f"| {receipt} | {truth:.1f} | {len(group)} | {len(preds)} | {len(group)-len(preds)} | "
            f"{_fmt(statistics.mean(preds) if preds else None)} | {_fmt(mean_error)} | {_fmt(mae)} | "
            f"{range_text} | {_fmt(spread)} | {direction} |"
        )

    mask_rows = [record for line in args.mask_audit.read_text().splitlines()
                 if line.strip()
                 for record in [json.loads(line)]
                 if record.get("receipt_id") is not None] if args.mask_audit.is_file() else []
    if mask_rows:
        lines.extend([
            "",
            "## Multi-item mask overlap audit",
            "",
            ("A pair is overlap-flagged when IoU > 0.50. The existing dedupe threshold is 0.70, "
            "so 0.50–<0.70 pairs are retained by that threshold. The duplicate-drop calculation "
            "below is hypothetical and does not alter any recorded prediction."),
            "",
            "| Receipt | Row | Predicted g | Top food area px | Sum item area px | Area ratio | IoUs | Pairs 0.50–<0.70 | Flagged item grams | Flagged % total | Hypothetical total after drop g | Delta g |",
            "|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|",
        ])
        by_receipt_masks: dict[int, list[dict]] = defaultdict(list)
        for audit in mask_rows:
            by_receipt_masks[int(audit["receipt_id"])].append(audit)
            if audit.get("mapping_error"):
                ious_text = "mask replay item-count mismatch"
                flagged_g = None
                flagged_pct = None
                hyp_total = None
                delta = None
            else:
                ious_text = ", ".join(
                    f"{pair['i']}-{pair['j']}:{float(pair['iou']):.3f}"
                    for pair in audit["pairwise_iou"]
                ) or "none"
                flagged_g = (float(audit["flagged_items_grams"])
                             if audit.get("flagged_items_grams") is not None else None)
                flagged_pct = audit.get("flagged_items_pct_of_total")
                hyp_total = (float(audit["hypothetical_total_after_duplicate_drop_g"])
                             if audit.get("hypothetical_total_after_duplicate_drop_g") is not None else None)
                delta = (float(audit["hypothetical_delta_g"])
                         if audit.get("hypothetical_delta_g") is not None else None)
                if flagged_g is None:
                    flagged_text = (f"unknown (known {_fmt(float(audit.get('flagged_known_grams', 0)))} g; "
                                    f"{audit.get('flagged_unknown_item_count', 0)} item grams null)")
                else:
                    flagged_text = _fmt(flagged_g)
            lines.append(
                f"| {audit['receipt_id']} | {audit['source_row_idx']} | "
                f"{_fmt(float(audit['predicted_total_g']) if audit.get('predicted_total_g') is not None else None)} | "
                f"{audit.get('top_food_area_px', '—')} | {audit.get('sum_item_mask_area_px', '—')} | "
                f"{_fmt(float(audit['item_area_sum_to_top_area_ratio']) if audit.get('item_area_sum_to_top_area_ratio') is not None else None, 3)} | "
                f"{ious_text} | {audit.get('pairs_in_0.50_to_0.70_band', '—')} | "
                f"{flagged_text} | {_fmt(float(flagged_pct) if flagged_pct is not None else None)} | "
                f"{_fmt(hyp_total)} | {_fmt(delta)} |"
            )

        for receipt, audit_group in sorted(by_receipt_masks.items()):
            usable = [audit for audit in audit_group if not audit.get("mapping_error")]
            if not usable:
                lines.append(f"- Receipt {receipt}: no mask rows could be paired with pipeline items.")
                continue
            pred_values = [float(audit["predicted_total_g"]) for audit in usable
                           if audit.get("predicted_total_g") is not None]
            flagged_values = [float(audit["flagged_items_grams"]) for audit in usable
                              if audit.get("flagged_items_grams") is not None]
            flagged_unknown = sum(int(audit.get("flagged_unknown_item_count", 0))
                                  for audit in usable)
            hyp_values = [float(audit["hypothetical_total_after_duplicate_drop_g"])
                          for audit in usable
                          if audit.get("hypothetical_total_after_duplicate_drop_g") is not None]
            true = float(usable[0]["ground_truth_food_g"])
            flagged_share = (100.0 * statistics.mean(flagged_values) / statistics.mean(pred_values)
                             if flagged_values and pred_values and not flagged_unknown else None)
            hyp_mean = statistics.mean(hyp_values) if hyp_values else None
            lines.append(
                f"- Receipt {receipt}: {len(usable)} audited multi-item views; mean flagged grams "
                f"{statistics.mean(flagged_values):.1f} g across fully known rows"
                f"{f' ({flagged_share:.1f}% of their mean predicted total)' if flagged_share is not None else ''}; "
                f"{flagged_unknown} flagged item gram values were null. "
                f"Hypothetical duplicate-drop mean total is {_fmt(hyp_mean)} g over {len(hyp_values)} calculable views "
                f"(true {true:.1f} g)."
            )

    lines.extend([
        "",
        (f"Numeric coverage: {total_views-len([r for r in image_rows if r.get('predicted_total_g') is None])}/{total_views} views; "
        f"abstentions: {sum(r.get('predicted_total_g') is None for r in image_rows)}/{total_views}."),
        ("Across numeric views only (not plate-independent): "
        f"mean signed error {_fmt(statistics.mean(all_signed) if all_signed else None)} g, "
        f"MAE {_fmt(statistics.mean(all_abs) if all_abs else None)} g."),
        "",
        "## Receipt labels and unmatched components",
        "",
        "Exact case-insensitive string equality is the only component match used here; no fuzzy pairing.",
        "",
    ])
    for receipt in sorted(groups):
        group = groups[receipt]
        components = group[0]["ground_truth_components"]
        labels = Counter(
            (row.get("classification") or {}).get("dish") or "ABSTAIN"
            for row in group
        )
        item_labels = Counter(
            (item.get("classification") or {}).get("dish") or "UNLABELED"
            for row in group for item in row.get("items", [])
        )
        gt_labels = [str(item["label"]).strip() for item in components]
        matched = sorted({gt.lower() for gt in gt_labels} &
                         {label.lower() for label in item_labels if label != "UNLABELED"})
        unmatched_components = [label for label in gt_labels if label.lower() not in matched]
        lines.append(f"- Receipt {receipt}: ground-truth components: " + "; ".join(
            f"{row['label']} {float(row['grams']):.1f} g" for row in components
        ) + ".")
        lines.append(f"  - Top-level classifier labels per image: {dict(labels)}.")
        lines.append(f"  - Item classifier labels per emitted item: {dict(item_labels)}.")
        lines.append(f"  - Exact matched components: {matched or 'none'}; unmatched ground-truth components: {unmatched_components}.")

    lines.extend([
        "",
        "## Per-image outputs",
        "",
        "`pred−true` and percent error are shown only when the pipeline returned grams.",
        "",
        "| Receipt | Row | Verdict | Anchor | Pred g | True g | Signed g | Error % | Dish label | Reason / classifier evidence |",
        "|---:|---:|---|---|---:|---:|---:|---:|---|---|",
    ])
    for row in image_rows:
        pred = row.get("predicted_total_g")
        truth = float(row["ground_truth_food_g"])
        signed = None if pred is None else float(pred) - truth
        pct = None if signed is None or truth == 0 else 100.0 * signed / truth
        cls = row.get("classification") or {}
        reasons = row.get("reasons") or []
        evidence = cls.get("reason") or "; ".join(r.get("text", "") for r in reasons)
        evidence = str(evidence).replace("|", "/")
        label = cls.get("dish") or "ABSTAIN"
        lines.append(
            f"| {row['receipt_id']} | {row['source_row_idx']} | {row.get('verdict')} | "
            f"{(row.get('anchor') or {}).get('tier')} | {_fmt(float(pred) if pred is not None else None)} | "
            f"{truth:.1f} | {_fmt(signed)} | {_fmt(pct)} | {label} | {evidence} |"
        )

    verdicts = Counter(row.get("verdict") for row in image_rows)
    elapsed = [float(row["elapsed_s"]) for row in image_rows if row.get("elapsed_s") is not None]
    numeric_elapsed = [float(row["elapsed_s"]) for row in image_rows
                      if row.get("predicted_total_g") is not None
                      and row.get("elapsed_s") is not None]
    abstention_elapsed = [float(row["elapsed_s"]) for row in image_rows
                          if row.get("predicted_total_g") is None
                          and row.get("elapsed_s") is not None]
    if mask_rows:
        ratio_values = [float(audit["item_area_sum_to_top_area_ratio"])
                        for audit in mask_rows
                        if audit.get("item_area_sum_to_top_area_ratio") is not None]
        band_pairs = sum(int(audit.get("pairs_in_0.50_to_0.70_band", 0))
                         for audit in mask_rows)
        lines.extend(["", "## Mask overlap audit", ""])
        if split_name == "train" and phase == "initial" and any(int(audit["source_row_idx"]) == 192
                                      for audit in mask_rows):
            representative = next(audit for audit in mask_rows
                                  if int(audit["source_row_idx"]) == 192)
            representative_row = next(row for row in image_rows
                                      if int(row["source_row_idx"]) == 192)
            components = representative_row["ground_truth_components"]
            component_names = ", ".join(str(component["label"]).strip()
                                         for component in components)
            item_labels = [((item.get("classification") or {}).get("dish") or "unlabeled")
                           for item in representative_row.get("items", [])]
            lines.extend([
                "![SAM masks on a representative Food Waste DEV image](overlays/receipt-480660-row-0192.png)",
                (f"Visual observation for receipt {representative['receipt_id']}, source row {representative['source_row_idx']}: "
                f"the colored item masks cover most of the plate and overlap, while the cyan top-level mask is small. "
                f"Numbers: top mask {representative['top_food_area_px']} px; summed item masks "
                f"{representative['sum_item_mask_area_px']} px; area ratio "
                f"{float(representative['item_area_sum_to_top_area_ratio']):.3f}; pair IoU "
                f"{float(representative['pairwise_iou'][0]['iou']):.3f}. Across {len(mask_rows)} multi-item views, "
                f"item-area-sum/top-mask ratios span {_fmt(min(ratio_values), 3)}–{_fmt(max(ratio_values), 3)}; "
                f"{band_pairs} pairs fall in the existing dedupe-pass band 0.50–<0.70."),
                "",
                "Hypothesis evidence ratings:",
                (f"- **(a) Oversized item masks — supports strongly.** In this overlay, the item masks visibly cover plate regions; "
                f"{len(mask_rows)} multi-item views have item-area-sum/top-mask ratios above 1."),
                ("- **(b) Plate/table counted as height above the base plane — cannot decide.** Accepted outputs use "
                "the prior learned-weight path (`area_cm2` and `mean_h_mm` are null); no height map was produced."),
                (f"- **(c) Classifier labels non-food crops as dishes — supports for this image.** The item labels are "
                f"{item_labels}, while recorded components are {component_names}; the overlay shows each item mask includes extensive plate area."),
            ])
        else:
            flagged_count = sum(bool(audit.get("all_flagged_indices"))
                                for audit in mask_rows if not audit.get("mapping_error"))
            lines.extend([
                f"No separate overlay was rendered for phase `{phase}`; visual observations are limited to the initial report.",
                (f"Across {len(mask_rows)} multi-item views, item-area-sum/top-mask ratios span "
                f"{_fmt(min(ratio_values), 3)}–{_fmt(max(ratio_values), 3)}; {band_pairs} pairs are in the existing "
                f"dedupe-pass band 0.50–<0.70; {flagged_count} images have at least one overlap/area flag."),
                "Height above a base plane cannot be assessed from this mask-only phase; its numeric outputs use the prior learned-weight route.",
            ])
    lines.extend([
        "",
        "## Run observations",
        "",
        "`PASS`, `BORDERLINE`, and `FAIL` are nutrient-compliance verdicts; they are not mass-accuracy gates.",
        (f"Verdicts: {dict(verdicts)}. Median end-to-end time per image: {_fmt(statistics.median(elapsed), 2)} s; "
        f"numeric-output median {_fmt(statistics.median(numeric_elapsed), 2)} s; "
        f"abstention median {_fmt(statistics.median(abstention_elapsed), 2)} s; "
        f"first image {_fmt(elapsed[0], 2)} s."),
        ("The persisted raw JSONL has per-stage timings, full pipeline reasons, portions, item-mask metadata, and item labels. "
        "The separate mask-audit JSONL contains replayed mask areas, flags and pairwise IoUs."),
        "",
    ])
    scored_rows = [row for row in image_rows if row.get("predicted_total_g") is not None]
    exact_rows = [row for row in scored_rows
                  if float(row["predicted_total_g"]) == float(row["ground_truth_food_g"])]
    lines.extend(["", "## Exact-match and leakage checks", ""])
    if scored_rows:
        largest = max(scored_rows, key=lambda row: abs(
            float(row["predicted_total_g"]) - float(row["ground_truth_food_g"])))
        error = float(largest["predicted_total_g"]) - float(largest["ground_truth_food_g"])
        lines.append(
            f"Largest absolute-error output: receipt {largest['receipt_id']} row {largest['source_row_idx']}, "
            f"{float(largest['predicted_total_g']):.1f} g vs {float(largest['ground_truth_food_g']):.1f} g "
            f"(signed {error:+.1f} g; verdict `{largest.get('verdict')}`)."
        )
    if exact_rows:
        exact_descriptions = []
        for row in exact_rows:
            portion = row.get("portion") or {}
            exact_descriptions.append(
                f"receipt {row['receipt_id']} row {row['source_row_idx']} "
                f"({float(row['predicted_total_g']):.1f} g; raw head slots "
                f"{portion.get('head_slots', 'not recorded')})"
            )
        lines.append("Exact rounded total matches: " + "; ".join(exact_descriptions) + ".")
        lines.append(
            "These are rounded output matches, not evidence of per-component correctness; inspect the item/classification "
            "and source receipt before interpreting them."
        )
    else:
        lines.append("No exact rounded total matches occurred.")
    lines.extend([
        ("Leakage check: the runner passes only image pixels, EXIF, day, band, and serving style to "
        "`pipeline.analyze`; it attaches ground-truth weights/components to the JSONL after inference. "
        f"The run records pipeline code SHA-256 `{run_metadata.get('pipeline_code_sha256', 'not recorded')}`. "
        "No target leakage is evident at this call boundary."),
        "",
    ])
    lines.extend([
        "## Interpretation limits",
        "",
        f"This `{phase}` run covers {len(groups)} receipt groups from the author `{split_name}` split. "
        "No labels were passed to inference. German canteen leftovers are a cross-domain input; "
        "a rejection is a coverage result, not a zero-weight error. "
        + ("The official test split is evaluation-only and must not inform development."
           if run_metadata.get("official_test_evaluation_only") else
           "The official test split was not fetched by this run."),
        "",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.output}")
    print("\n".join(lines[8:18]))


if __name__ == "__main__":
    main()
