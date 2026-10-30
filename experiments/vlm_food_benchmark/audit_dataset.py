"""Audit the local VLM Food Benchmark source and freeze its group split."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datasets/raw/portion/vlm-food-benchmark"
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.csv"
AUDIT = HERE / "DATA_AUDIT.md"
SPLIT = {
    "participant_1": "train",
    "participant_2": "train",
    "participant_3": "dev",
    "participant_4": "train",
    "participant_5": "train",
    "participant_6": "test",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    with (DATA / "GT_Mensa_2025/image_participants.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        participant_rows = list(csv.DictReader(stream))
    participant_by_image = {
        row["resized_filename"]: row["participant_id"]
        for row in participant_rows
    }
    if len(participant_by_image) != len(participant_rows):
        raise RuntimeError("duplicate image in participant map")

    labels_by_image: dict[str, list[tuple[str, float]]] = defaultdict(list)
    with (DATA / "structured_food_labels.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        for row in csv.DictReader(stream):
            match = re.search(r"-(\d{3}\.jpg)$", Path(row["image"]).name)
            if not match:
                raise RuntimeError(f"cannot map annotation image: {row['image']}")
            image_name = match.group(1)
            food = row["food"].strip()
            grams = float(row["portion"])
            if not food or grams <= 0:
                raise RuntimeError(f"invalid label row: {row}")
            labels_by_image[image_name].append((food, grams))

    rows = []
    missing_images = []
    file_hashes = Counter()
    for image_name, participant in sorted(participant_by_image.items()):
        image_path = DATA / "GT_Mensa_2025/resized_images" / image_name
        if not image_path.is_file():
            missing_images.append(image_name)
            continue
        items = labels_by_image.get(image_name, [])
        if not items:
            raise RuntimeError(f"no ground-truth items for {image_name}")
        if participant not in SPLIT:
            raise RuntimeError(f"unassigned participant {participant}")
        digest = sha256(image_path)
        file_hashes[digest] += 1
        rows.append({
            "image": image_name,
            "participant_id": participant,
            "split": SPLIT[participant],
            "item_count": len(items),
            "total_food_g": round(sum(grams for _, grams in items), 6),
            "image_sha256": digest,
        })

    if missing_images:
        raise RuntimeError(f"missing source images: {missing_images}")
    if set(labels_by_image) != set(participant_by_image):
        raise RuntimeError("label and participant image keys differ")
    if len(rows) != 200 or sum(row["item_count"] for row in rows) != 870:
        raise RuntimeError(
            f"unexpected source size: images={len(rows)}, "
            f"items={sum(row['item_count'] for row in rows)}"
        )

    HERE.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    participant_counts = Counter(row["participant_id"] for row in rows)
    split_counts = Counter(row["split"] for row in rows)
    duplicate_image_count = sum(count - 1 for count in file_hashes.values())
    lines = [
        "# VLM Food Benchmark data audit", "",
        "Source revision: `d715df0c0debe65da805618431e67f6d0fa01c71`.",
        f"Manifest SHA-256: `{sha256(MANIFEST)}`.",
        f"Images: {len(rows)}; food-item labels: {sum(r['item_count'] for r in rows)}.",
        f"Image hash duplicates: {duplicate_image_count}.",
        ("Ground truth is sourced from the repository's `structured_food_labels.csv`; "
         "the repository states item weights are scale-measured with empty-plate tare subtracted."),
        "",
        "| Participant group | Images | Split |",
        "|---|---:|---|",
    ]
    for participant in sorted(participant_counts):
        lines.append(
            f"| {participant} | {participant_counts[participant]} | "
            f"{SPLIT[participant]} |"
        )
    lines.extend(["", "| Split | Images |", "|---|---:|"])
    for split in ("train", "dev", "test"):
        lines.append(f"| {split} | {split_counts[split]} |")
    lines.extend(["", "## Split composition", "",
                  "| Split | Images | Mean items/image | Mean total g | Median total g | Total range g |",
                  "|---|---:|---:|---:|---:|---:|"])
    split_summaries = {}
    for split in ("train", "dev", "test"):
        split_rows = [row for row in rows if row["split"] == split]
        totals = [float(row["total_food_g"]) for row in split_rows]
        item_counts = [int(row["item_count"]) for row in split_rows]
        split_summaries[split] = {
            "images": len(split_rows),
            "mean_items_per_image": statistics.mean(item_counts),
            "mean_total_g": statistics.mean(totals),
            "median_total_g": statistics.median(totals),
            "minimum_total_g": min(totals),
            "maximum_total_g": max(totals),
        }
        summary = split_summaries[split]
        lines.append(
            f"| {split} | {summary['images']} | "
            f"{summary['mean_items_per_image']:.2f} | "
            f"{summary['mean_total_g']:.1f} | {summary['median_total_g']:.1f} | "
            f"{summary['minimum_total_g']:.1f}–{summary['maximum_total_g']:.1f} |"
        )
    lines.extend([
        "", ("Participant groups are disjoint by construction. The test set is "
             "participant_6 (60 images) and is reserved for the one-shot comparison "
             "in `PROTOCOL.md`. The primary paper describes participant 3's 34-image "
             "subset as home-prepared lunches, while the repository README broadly "
             "describes the dataset as university-canteen meals; participant-level "
             "split composition therefore confounds setting with the dev partition. "
             "See https://doi.org/10.3390/nu18213582."), "",
    ])
    AUDIT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "source_revision": "d715df0c0debe65da805618431e67f6d0fa01c71",
        "images": len(rows),
        "food_item_labels": sum(row["item_count"] for row in rows),
        "participant_counts": dict(sorted(participant_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "split_summaries": split_summaries,
        "duplicate_image_hashes": duplicate_image_count,
        "manifest_sha256": sha256(MANIFEST),
        "missing_images": len(missing_images),
    }, indent=2))
    print(f"wrote {MANIFEST}")
    print(f"wrote {AUDIT}")


if __name__ == "__main__":
    main()
