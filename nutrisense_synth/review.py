"""Stratified human-review queue for synthetic label and appearance checks."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import random
from typing import Any

from nutrisense_synth.manifest import read_jsonl


def _strata(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    annotation = (row.get("annotations") or [{}])[0]
    labels = annotation.get("labels", {})
    scene = row.get("scene_parameters", {})
    classes = sorted({str(item.get("class_name", "unknown"))
                      for item in row.get("annotations", [])})
    return (
        "+".join(classes) or str(annotation.get("class_name", "unknown")),
        str(labels.get("portion_range", "unknown")),
        str(row.get("method", "unknown")),
        "card" if row.get("card_present") else "no_card",
        str(scene.get("illumination", {}).get("profile", "default")),
    )


def build_review_queue(rows: list[dict[str, Any]], per_stratum: int = 3,
                       seed: int = 42) -> list[dict[str, Any]]:
    if per_stratum < 1:
        raise ValueError("per_stratum must be positive")
    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault(_strata(row), []).append(row)
    rng = random.Random(seed)
    result = []
    for stratum, members in sorted(buckets.items()):
        ordered = sorted(members, key=lambda item: item.get("sample_id", ""))
        rng.shuffle(ordered)
        for row in ordered[:per_stratum]:
            result.append({
                "sample_id": row.get("sample_id"),
                "image_path": row.get("output_path"),
                "stratum": dict(zip(("class", "portion_range", "method", "card", "lighting"), stratum)),
                "reviewer": "",
                "identity_correct": "",
                "mask_geometry_valid": "",
                "marker_valid": "",
                "appearance_plausible": "",
                "task_restrictions": "",
                "notes": "",
            })
    return result


def write_review_queue(manifest_path: Path, output_path: Path,
                       per_stratum: int = 3, seed: int = 42) -> int:
    rows = read_jsonl(manifest_path)
    queue = build_review_queue(rows, per_stratum=per_stratum, seed=seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["sample_id", "image_path", "stratum", "reviewer", "identity_correct",
              "mask_geometry_valid", "marker_valid", "appearance_plausible",
              "task_restrictions", "notes"]
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in queue:
            writer.writerow({**row, "stratum": json.dumps(row["stratum"], sort_keys=True)})
    return len(queue)


def review_gate(queue_path: Path, min_acceptance: float = 0.90,
                manifest_path: Path | None = None) -> dict[str, Any]:
    if not 0.0 <= min_acceptance <= 1.0:
        raise ValueError("min_acceptance must be between zero and one")
    with queue_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Human-review queue is empty")
    strata: dict[str, dict[str, int]] = {}
    individual: dict[str, dict[str, Any]] = {}
    for row in rows:
        try:
            stratum = json.loads(row["stratum"])
        except (KeyError, json.JSONDecodeError) as exc:
            raise ValueError("Review row has invalid stratum JSON") from exc
        key = json.dumps(stratum, sort_keys=True)
        result = strata.setdefault(key, {"reviewed": 0, "accepted": 0, "rejected": 0})
        required = ["reviewer", "identity_correct", "mask_geometry_valid", "appearance_plausible"]
        if any(not row.get(field, "").strip() for field in required):
            raise ValueError(f"Incomplete review response in stratum {key}")
        yes = all(row[field].strip().lower() == "yes" for field in required[1:])
        if stratum.get("card") == "card":
            if not row.get("marker_valid", "").strip():
                raise ValueError(f"Missing marker review in stratum {key}")
            yes = yes and row["marker_valid"].strip().lower() == "yes"
        result["reviewed"] += 1
        result["accepted" if yes else "rejected"] += 1
        identity_ok = row["identity_correct"].strip().lower() == "yes"
        geometry_ok = row["mask_geometry_valid"].strip().lower() == "yes"
        appearance_ok = row["appearance_plausible"].strip().lower() == "yes"
        marker_ok = (row.get("marker_valid", "").strip().lower() == "yes"
                     if stratum.get("card") == "card" else None)
        individual[row.get("sample_id", "")] = {
            "status": "accepted" if yes else "rejected",
            "reviewer": row["reviewer"].strip(),
            "identity_correct": identity_ok,
            "geometry_valid": geometry_ok,
            "appearance_plausible": appearance_ok,
            "marker_valid": marker_ok,
        }
    detail = []
    passed = True
    for key, counts in sorted(strata.items()):
        rate = counts["accepted"] / counts["reviewed"] if counts["reviewed"] else 0.0
        stratum_passed = rate >= min_acceptance
        passed &= stratum_passed
        detail.append({"stratum": json.loads(key), **counts,
                       "acceptance_rate": rate, "passed": stratum_passed})
    if manifest_path is not None:
        manifest_rows = read_jsonl(manifest_path)
        seen: set[str] = set()
        for sample in manifest_rows:
            sample_id = str(sample.get("sample_id", ""))
            review = individual.get(sample_id)
            if review is None:
                continue
            seen.add(sample_id)
            restrictions = {
                "classification": review["identity_correct"] and review["appearance_plausible"],
                "segmentation": review["geometry_valid"],
                "depth": review["geometry_valid"],
                "mass": review["geometry_valid"],
            }
            if review["marker_valid"] is not None:
                restrictions["marker"] = review["marker_valid"]
            for annotation in sample.get("annotations", []):
                validity = annotation.setdefault("task_valid", {})
                for task, allowed in restrictions.items():
                    validity[task] = bool(validity.get(task, False) and allowed)
            sample.setdefault("quality", {})["human_review"] = review
        missing_ids = set(individual) - seen
        if missing_ids:
            raise ValueError(f"Review queue contains unknown sample ids: {sorted(missing_ids)[:5]}")
        temp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as stream:
            for sample in manifest_rows:
                stream.write(json.dumps(sample, sort_keys=True) + "\n")
        temp.replace(manifest_path)
    return {"minimum_acceptance": min_acceptance, "passed": bool(passed),
            "strata": detail, "sample_count": len(rows),
            "individual_reviews_applied": len(individual) if manifest_path is not None else 0}
