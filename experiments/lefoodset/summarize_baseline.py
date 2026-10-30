"""Summarize the frozen LeFood-Set pipeline baseline from its JSONL."""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw_baseline_test.jsonl"
OUT = HERE / "RESULTS_BASELINE.md"


def main() -> None:
    rows = [json.loads(line) for line in RAW.read_text().splitlines() if line.strip()]
    metadata = next(row for row in rows if row.get("event") == "run_metadata")
    images = [row for row in rows if row.get("event") == "image_result"]
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in images:
        groups[str(row["food_category_truth"])].append(row)
    numeric = [row for row in images if row.get("predicted_total_g") is not None]
    elapsed = [float(row["elapsed_s"]) for row in images if row.get("elapsed_s") is not None]
    labels = Counter((row.get("classification") or {}).get("dish") or "ABSTAIN"
                     for row in images)
    verdicts = Counter(row.get("verdict") for row in images)

    lines = [
        "# LeFood-Set frozen current-pipeline baseline",
        "",
        "This is the single pre-registered evaluation on six category-held-out test foods. "
        "No category or weight was sent to inference. This is single-food, cross-domain evidence, "
        "not a mixed-meal or production claim.",
        "",
        "Ground truth uses source `Weight Before Eaten (g)`, described by Mendeley as food mass. "
        "The paper says a plate containing food was weighed but does not document tare handling; "
        "this unresolved caveat applies to every gram target below.",
        "",
        f"Dataset split: `{metadata['split_read']}`; images: {len(images)}; "
        f"test food categories: {metadata['food_category_count']}; train split read: "
        f"{metadata['train_split_read']}; pipeline SHA-256: `{metadata['pipeline_code_sha256']}`.",
        "",
        "## Test-category results",
        "",
        "| Food category | True-mass range g | Images | Numeric totals | Abstentions | Dish label outcome |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for category in sorted(groups):
        group = groups[category]
        truth = [float(row["ground_truth_food_g"]) for row in group]
        preds = [float(row["predicted_total_g"]) for row in group
                 if row.get("predicted_total_g") is not None]
        best_labels = Counter(
            ((row.get("classification") or {}).get("reason") or "no classifier reason")
            for row in group
        )
        best_label_text = "; ".join(
            f"{label} ({count})" for label, count in best_labels.most_common(3))
        lines.append(
            f"| {category} | {min(truth):.1f}–{max(truth):.1f} | {len(group)} | "
            f"{len(preds)} | {len(group)-len(preds)} | {best_label_text} |"
        )
    lines.extend([
        "",
        f"Numeric coverage: {len(numeric)}/{len(images)}; abstentions: "
        f"{len(images)-len(numeric)}/{len(images)}. Dish label outcomes: {dict(labels)}. "
        f"Verdicts: {dict(verdicts)}.",
        "No numeric outputs means signed gram error and MAE are undefined on this split; "
        "do not convert abstentions to 0 g or score them as zero error.",
        f"Median elapsed time: {statistics.median(elapsed):.3f} s; first image: {elapsed[0]:.3f} s.",
        "",
        "## Per-image record",
        "",
        "| Row | Food | True g | Predicted g | Verdict | Anchor | Gallery rejection evidence |",
        "|---:|---|---:|---:|---|---|---|",
    ])
    for row in images:
        cls = row.get("classification") or {}
        reason = str(cls.get("reason") or "").replace("|", "/")
        lines.append(
            f"| {row['row_id']} | {row['food_category_truth']} | "
            f"{float(row['ground_truth_food_g']):.1f} | — | {row.get('verdict')} | "
            f"{(row.get('anchor') or {}).get('tier')} | {reason} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The current pipeline abstained on every test image because its gallery classifier did not "
        "reach the configured acceptance score for these unseen Indonesian foods. This is a complete "
        "coverage gap on the held-out categories. Since no numeric grams were returned, this run does "
        "not establish whether its mass regressor would be accurate on these foods if supplied a dish label.",
        "",
        "The held-out categories remain closed to development. Any later candidate may be compared once "
        "on this split only after training and epoch selection are frozen using train/dev categories.",
        "",
    ])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    print("images", len(images), "numeric", len(numeric),
          "abstentions", len(images)-len(numeric), "labels", dict(labels),
          "verdicts", dict(verdicts), "median_s", statistics.median(elapsed))


if __name__ == "__main__":
    main()
