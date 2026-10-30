"""Merge the frozen candidate and serving-pipeline test outputs."""
from __future__ import annotations

import json
import statistics
import csv
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_results(name: str) -> list[dict]:
    rows = [json.loads(line) for line in (HERE / name).read_text().splitlines()]
    return [row for row in rows if row.get("event") == "image_result"]


def main() -> None:
    candidate = {row["image"]: row for row in read_results("raw_candidate_test.jsonl")}
    pipeline = {row["image"]: row for row in read_results("raw_pipeline_test.jsonl")}
    if set(candidate) != set(pipeline) or not candidate:
        raise RuntimeError("candidate and pipeline image sets differ or are empty")
    if any(candidate[name]["ground_truth_total_g"] != pipeline[name]["ground_truth_total_g"]
           for name in candidate):
        raise RuntimeError("ground-truth totals differ between frozen runs")

    names = sorted(candidate)
    truth = [candidate[name]["ground_truth_total_g"] for name in names]
    estimates = [candidate[name]["predicted_total_g"] for name in names]
    errors = [estimate - target for estimate, target in zip(estimates, truth, strict=True)]
    with (HERE / "manifest.csv").open(newline="", encoding="utf-8") as stream:
        manifest = list(csv.DictReader(stream))
    train_dev = [row for row in manifest if row["split"] in {"train", "dev"}]
    median = statistics.median(float(row["total_food_g"]) for row in train_dev)
    split_summaries = {}
    for split in ("train", "dev", "test"):
        split_rows = [row for row in manifest if row["split"] == split]
        totals = [float(row["total_food_g"]) for row in split_rows]
        items = [int(row["item_count"]) for row in split_rows]
        split_summaries[split] = {
            "images": len(split_rows),
            "mean_items": statistics.mean(items),
            "mean_total_g": statistics.mean(totals),
            "median_total_g": statistics.median(totals),
        }
    numeric_pipeline = [
        row for row in (pipeline[name] for name in names)
        if row.get("predicted_total_g") is not None
    ]
    verdicts = Counter(str(pipeline[name].get("verdict")) for name in names)
    scores = [float(pipeline[name]["classification"]["match_score"])
              for name in names
              if pipeline[name].get("classification", {}).get("match_score") is not None]
    anchor_tiers = Counter(pipeline[name]["anchor"]["tier"] for name in names)
    labels = Counter(str(pipeline[name].get("dish")) for name in names)
    latencies = [float(pipeline[name].get("elapsed_s", 0)) for name in names]
    first_latency = float(next(row for row in pipeline.values() if row.get("index") == 1)
                          .get("elapsed_s", 0))
    report = {
        "test_images": len(names),
        "true_total_min_g": min(truth), "true_total_max_g": max(truth),
        "candidate_mae_g": statistics.fmean(abs(error) for error in errors),
        "candidate_bias_g": statistics.fmean(errors),
        "candidate_median_g": statistics.median(estimates),
        "candidate_prediction_min_g": min(estimates),
        "candidate_prediction_max_g": max(estimates),
        "pipeline_numeric_count": len(numeric_pipeline),
        "pipeline_abstention_count": len(names) - len(numeric_pipeline),
        "pipeline_verdicts": dict(verdicts),
        "pipeline_dish_labels": dict(labels),
        "pipeline_anchor_tiers": dict(anchor_tiers),
        "gallery_match_score_min": min(scores),
        "gallery_match_score_max": max(scores),
        "gallery_scores_below_080": sum(score < 0.80 for score in scores),
        "pipeline_latency_median_s": statistics.median(latencies),
        "pipeline_latency_p95_s": sorted(latencies)[int(0.95 * (len(latencies) - 1))],
        "pipeline_first_request_s": first_latency,
        "pipeline_latency_max_s": max(latencies),
        "split_summaries": split_summaries,
    }
    report["train_dev_global_median_g"] = median
    report["train_dev_median_baseline_mae_g"] = statistics.fmean(abs(median - y) for y in truth)
    lines = [
        "# VLM Food Benchmark frozen comparison", "",
        ("60 meals from participant_6 were the only test group. Candidate and "
         "serving-pipeline outputs are from the same images; ground truth was "
         "not supplied to inference."), "",
        "## Plate-total results", "",
        "| Method | Numeric coverage | MAE g | Signed bias g |",
        "|---|---:|---:|---:|",
        (f"| DINOv2-S research candidate | 60/60 | {report['candidate_mae_g']:.1f} | "
         f"{report['candidate_bias_g']:+.1f} |"),
        (f"| Train+dev median ({median:.1f} g) | 60/60 | "
         f"{report['train_dev_median_baseline_mae_g']:.1f} | "
         f"{statistics.fmean(median-y for y in truth):+.1f} |"),
        f"| Current serving pipeline | {len(numeric_pipeline)}/60 | — | — |", "",
        (f"Candidate predictions ranged from {min(estimates):.1f} to "
         f"{max(estimates):.1f} g; ground-truth totals ranged from "
         f"{min(truth):.1f} to {max(truth):.1f} g."), "",
        ("The serving pipeline returned no numeric totals, so its plate-total "
         "MAE and signed bias are undefined on this test group. Abstentions are "
         "not counted as zero error."), "",
        "## Pipeline coverage and timing", "",
        f"Verdicts: `{dict(verdicts)}`. Dish labels: `{dict(labels)}`.",
        (f"Anchors: `{dict(anchor_tiers)}`. Gallery best-match scores ranged "
         f"from {min(scores):.3f} to {max(scores):.3f}; "
         f"{sum(score < 0.80 for score in scores)}/{len(scores)} were below the "
         "existing 0.80 acceptance score."),
        (f"Median latency: {report['pipeline_latency_median_s']:.3f} s; "
         f"p95 latency: {report['pipeline_latency_p95_s']:.3f} s; "
         f"first request: {first_latency:.3f} s; max: {max(latencies):.3f} s."),
        "Per-image reasons are preserved in `raw_pipeline_test.jsonl`.", "",
        "## Split-composition caveat", "",
        "| Split | Images | Mean items/image | Mean total g | Median total g |",
        "|---|---:|---:|---:|---:|",
    ]
    for split in ("train", "dev", "test"):
        summary = split_summaries[split]
        lines.append(
            f"| {split} | {summary['images']} | {summary['mean_items']:.2f} | "
            f"{summary['mean_total_g']:.1f} | {summary['median_total_g']:.1f} |"
        )
    lines.extend([
        "", ("The primary paper describes participant 3's 34-image development "
             "subset as home-prepared lunches; the source README broadly describes "
             "university-canteen meals. Development is therefore lower-mass and mostly "
             "single-item, unlike the train/test groups. This split-composition mismatch "
             "may have influenced epoch selection and candidate bias; it is a hypothesis, "
             "not a demonstrated cause. No test result was used to retune."), "",
        "## Per-image plate totals", "",
        "| Image | Items | True g | Candidate g | Candidate signed error g | Pipeline g | Verdict |",
        "|---|---:|---:|---:|---:|---:|---|",
    ])
    for name in names:
        cand, pipe = candidate[name], pipeline[name]
        pipeline_g = pipe.get("predicted_total_g")
        lines.append(
            f"| {name} | {cand['item_count']} | {cand['ground_truth_total_g']:.1f} | "
            f"{cand['predicted_total_g']:.1f} | {cand['signed_error_g']:+.1f} | "
            f"{'—' if pipeline_g is None else f'{float(pipeline_g):.1f}'} | "
            f"{pipe.get('verdict')} |"
        )
    lines.extend([
        "", "## Interpretation", "",
        (f"On this one participant-held-out group, the research candidate's MAE "
         f"was {report['candidate_mae_g']:.1f} g versus "
         f"{report['train_dev_median_baseline_mae_g']:.1f} g for the train+dev "
         f"median ({report['candidate_mae_g'] - report['train_dev_median_baseline_mae_g']:+.1f} g), "
         f"with {report['candidate_bias_g']:+.1f} g signed bias. This is a modest "
         "single-cluster result with substantial underprediction. The current "
         "serving path had zero numeric coverage. The candidate is not integrated "
         "and does not establish Indian mixed-meal accuracy or production readiness."),
        "",
    ])
    (HERE / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"wrote {HERE / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
