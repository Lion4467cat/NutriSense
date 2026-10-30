"""Run the frozen single-object MetaFood3D benchmark from PROTOCOL.md.

This script is research-only, requires CUDA, and never changes serving code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from openpyxl import load_workbook
from torchvision import models


REPO = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO / "datasets/raw/marker/metafood3d"
WEIGHTS_PATH = Path.home() / ".cache/torch/hub/checkpoints/resnet50-11ad3fa6.pth"
SEED = 20261030
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
IMAGE_SIZE = 224
BATCH_SIZE = 24


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric_frame_key(stem: str) -> tuple[int, int | str, str]:
    try:
        return (0, int(stem), stem)
    except ValueError:
        return (1, stem.casefold(), stem)


def load_records() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    workbook = DATA_ROOT / "metadata/_MetaFood3D_new_complete_dataset_nutrition_v2.xlsx"
    sheet = load_workbook(workbook, read_only=True, data_only=True).active
    rows = list(sheet.values)
    headers = rows[0]
    category_idx = headers.index("Object_name")
    object_idx = headers.index("Food_Type")
    weight_idx = headers.index("Weight (g)")
    workbook_rows: dict[tuple[str, str], tuple[Any, Any, Any]] = {}
    for row in rows[1:]:
        if row[category_idx] is None or row[object_idx] is None:
            continue
        key = (str(row[category_idx]).casefold(), str(row[object_idx]).casefold())
        if key in workbook_rows:
            raise ValueError(f"duplicate workbook key: {key}")
        workbook_rows[key] = (row[category_idx], row[object_idx], row[weight_idx])

    root = DATA_ROOT / "extracted/RGBD_videos"
    directory_rows: dict[tuple[str, str], Path] = {}
    for directory in sorted(path for path in root.glob("*/*") if path.is_dir()):
        key = (directory.parent.name.casefold(), directory.name.casefold())
        if key in directory_rows:
            raise ValueError(f"duplicate RGBD directory key: {key}")
        directory_rows[key] = directory

    unmatched: list[dict[str, str]] = []
    for key in sorted(directory_rows.keys() ^ workbook_rows.keys()):
        if key in directory_rows:
            unmatched.append({"source": "rgbd_directory", "category": key[0], "object": key[1]})
        else:
            unmatched.append({"source": "workbook_row", "category": key[0], "object": key[1]})

    records: list[dict[str, Any]] = []
    for key in sorted(directory_rows.keys() & workbook_rows.keys()):
        category, object_name, weight = workbook_rows[key]
        if weight is None:
            continue
        folder = directory_rows[key]
        frame_sets = [
            {path.stem for path in (folder / modality).glob("*.jpg")}
            for modality in ("original", "masks", "segmented")
        ]
        shared_stems = sorted(set.intersection(*frame_sets), key=numeric_frame_key)
        if not shared_stems:
            continue
        stem = shared_stems[(len(shared_stems) - 1) // 2]
        records.append(
            {
                "category": str(category),
                "object": str(object_name),
                "weight_g": float(weight),
                "frame_stem": stem,
                "folder": folder,
                "rgb_path": folder / "original" / f"{stem}.jpg",
                "mask_path": folder / "masks" / f"{stem}.jpg",
            }
        )
    records.sort(key=lambda record: (record["category"].casefold(), record["object"].casefold()))
    return records, unmatched


def make_split(records: list[dict[str, Any]]) -> None:
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_category[record["category"]].append(record)
    rng = random.Random(SEED)
    for category in sorted(by_category, key=str.casefold):
        members = sorted(by_category[category], key=lambda r: r["object"].casefold())
        rng.shuffle(members)
        members[0]["split"] = "test"
        next_index = 1
        if len(members) >= 3:
            members[1]["split"] = "dev"
            next_index = 2
        for record in members[next_index:]:
            record["split"] = "train"


def image_tensor(path: Path) -> torch.Tensor:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        rgb.thumbnail((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.BILINEAR)
        canvas = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0, 0, 0))
        canvas.paste(rgb, ((IMAGE_SIZE - rgb.width) // 2, (IMAGE_SIZE - rgb.height) // 2))
        array = np.asarray(canvas, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(array).permute(2, 0, 1)
    mean = torch.tensor([0.485, 0.456, 0.406], dtype=tensor.dtype)[:, None, None]
    std = torch.tensor([0.229, 0.224, 0.225], dtype=tensor.dtype)[:, None, None]
    return (tensor - mean) / std


def mask_descriptors(path: Path) -> list[float]:
    with Image.open(path) as image:
        mask = np.asarray(image.convert("L")) > 127
    height, width = mask.shape
    ys, xs = np.nonzero(mask)
    if not len(xs):
        raise ValueError(f"empty mask: {path}")
    mask_area = float(mask.mean())
    bbox_width = float(xs.max() - xs.min() + 1) / width
    bbox_height = float(ys.max() - ys.min() + 1) / height
    return [mask_area, bbox_width, bbox_height, bbox_width * bbox_height]


@torch.inference_mode()
def extract_features(records: list[dict[str, Any]], device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    model = models.resnet50(weights=None)
    state = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    encoder = torch.nn.Sequential(*list(model.children())[:-1]).to(device).eval()
    image_features: list[np.ndarray] = []
    for start in range(0, len(records), BATCH_SIZE):
        batch_records = records[start : start + BATCH_SIZE]
        batch = torch.stack([image_tensor(record["rgb_path"]) for record in batch_records]).to(device)
        features = encoder(batch).flatten(1)
        image_features.extend(features.float().cpu().numpy())
    geometry = np.asarray([mask_descriptors(record["mask_path"]) for record in records], dtype=np.float32)
    return np.asarray(image_features, dtype=np.float32), geometry


def ridge_fit_predict(
    x_train: np.ndarray, y_train: np.ndarray, x_query: np.ndarray, alpha: float, device: torch.device
) -> np.ndarray:
    tx = torch.as_tensor(x_train, dtype=torch.float32, device=device)
    ty = torch.as_tensor(y_train, dtype=torch.float32, device=device)
    qx = torch.as_tensor(x_query, dtype=torch.float32, device=device)
    y_mean = ty.mean()
    centered_y = ty - y_mean
    gram = tx @ tx.T
    regularized = gram + alpha * torch.eye(gram.shape[0], device=device, dtype=gram.dtype)
    dual = torch.linalg.solve(regularized, centered_y)
    return (y_mean + qx @ tx.T @ dual).detach().cpu().numpy()


def build_design(
    records: list[dict[str, Any]], image_features: np.ndarray, geometry: np.ndarray,
    fit_indices: np.ndarray, category_names: list[str],
) -> np.ndarray:
    continuous = np.concatenate([image_features, geometry], axis=1)
    fit_values = continuous[fit_indices]
    mean = fit_values.mean(axis=0)
    std = fit_values.std(axis=0)
    std[std < 1e-6] = 1.0
    standardized = (continuous - mean) / std
    category_index = {name: idx for idx, name in enumerate(category_names)}
    one_hot = np.zeros((len(records), len(category_names)), dtype=np.float32)
    for idx, record in enumerate(records):
        one_hot[idx, category_index[record["category"]]] = 1.0
    return np.concatenate([standardized, one_hot], axis=1).astype(np.float32)


def mae(y: np.ndarray, prediction: np.ndarray) -> float:
    return float(np.mean(np.abs(prediction - y)))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    global BATCH_SIZE
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DATA_ROOT / "experiment_outputs")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()
    BATCH_SIZE = args.batch_size
    if not torch.cuda.is_available():
        raise SystemExit("CUDA unavailable; refusing CPU fallback")
    if not WEIGHTS_PATH.is_file():
        raise SystemExit(f"cached ResNet-50 weights missing: {WEIGHTS_PATH}; no download attempted")
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = torch.device("cuda:0")
    torch.cuda.set_device(device)

    records, unmatched = load_records()
    make_split(records)
    split_counts = {name: sum(record["split"] == name for record in records) for name in ("train", "dev", "test")}
    categories = sorted({record["category"] for record in records}, key=str.casefold)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = [
        {
            "category": record["category"],
            "object": record["object"],
            "weight_g": record["weight_g"],
            "split": record["split"],
            "frame_stem": record["frame_stem"],
            "rgb_path": str(record["rgb_path"].relative_to(REPO)),
            "mask_path": str(record["mask_path"].relative_to(REPO)),
        }
        for record in records
    ]
    write_jsonl(args.output / "split_manifest.jsonl", manifest)
    write_jsonl(args.output / "unmatched_keys.jsonl", unmatched)
    start = time.monotonic()
    image_features, geometry = extract_features(records, device)
    feature_seconds = time.monotonic() - start

    labels = np.asarray([record["weight_g"] for record in records], dtype=np.float32)
    train = np.asarray([i for i, r in enumerate(records) if r["split"] == "train"])
    dev = np.asarray([i for i, r in enumerate(records) if r["split"] == "dev"])
    test = np.asarray([i for i, r in enumerate(records) if r["split"] == "test"])
    design_for_dev = build_design(records, image_features, geometry, train, categories)
    category_train_weights: dict[str, list[float]] = defaultdict(list)
    for idx in train:
        category_train_weights[records[int(idx)]["category"]].append(float(labels[idx]))
    alpha_rows = []
    for alpha in ALPHAS:
        dev_log = ridge_fit_predict(
            design_for_dev[train], np.log1p(labels[train]), design_for_dev[dev], alpha, device
        )
        prediction = np.maximum(0.0, np.expm1(dev_log))
        alpha_rows.append({"alpha": alpha, "dev_mae_g": mae(labels[dev], prediction)})
    chosen_alpha = min(alpha_rows, key=lambda row: (row["dev_mae_g"], row["alpha"]))["alpha"]
    (args.output / "dev_alpha_selection.json").write_text(
        json.dumps({"selected_alpha": chosen_alpha, "scores": alpha_rows}, indent=2) + "\n",
        encoding="utf-8",
    )

    fit = np.concatenate([train, dev])
    design_final = build_design(records, image_features, geometry, fit, categories)
    final_category_weights: dict[str, list[float]] = defaultdict(list)
    for idx in fit:
        final_category_weights[records[int(idx)]["category"]].append(float(labels[idx]))
    baseline = np.asarray([
        statistics.median(final_category_weights[records[int(idx)]["category"]]) for idx in test
    ])
    test_log = ridge_fit_predict(
        design_final[fit], np.log1p(labels[fit]), design_final[test], chosen_alpha, device
    )
    candidate = np.maximum(0.0, np.expm1(test_log))
    truth = labels[test].astype(np.float64)
    baseline_error = baseline.astype(np.float64) - truth
    candidate_error = candidate.astype(np.float64) - truth
    category_diffs = candidate_error.__abs__() - baseline_error.__abs__()
    rng = np.random.default_rng(SEED)
    samples = rng.integers(0, len(category_diffs), size=(10_000, len(category_diffs)))
    bootstrap_means = category_diffs[samples].mean(axis=1)
    ci_low, ci_high = np.percentile(bootstrap_means, [2.5, 97.5]).tolist()
    baseline_mae = mae(truth, baseline)
    candidate_mae = mae(truth, candidate)
    baseline_bias = float(np.mean(baseline_error))
    candidate_bias = float(np.mean(candidate_error))
    summary = {
        "benchmark": "MetaFood3D single-object known-category, unseen-object",
        "scope": "research-only; oracle category and supplied mask; not serving-path evidence",
        "cuda_device": torch.cuda.get_device_name(device),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "resnet50_weights_sha256": sha256(WEIGHTS_PATH),
        "seed": SEED,
        "eligible_objects": len(records),
        "categories": len(categories),
        "split_counts": split_counts,
        "unmatched_keys": len(unmatched),
        "selected_alpha": chosen_alpha,
        "dev_alpha_scores": alpha_rows,
        "test_objects": len(test),
        "baseline_category_median_mae_g": baseline_mae,
        "candidate_mae_g": candidate_mae,
        "relative_mae_reduction": (baseline_mae - candidate_mae) / baseline_mae if baseline_mae else None,
        "baseline_signed_bias_g": baseline_bias,
        "candidate_signed_bias_g": candidate_bias,
        "paired_category_bootstrap_delta_mae_g_95ci": [float(ci_low), float(ci_high)],
        "macro_category_mae_baseline_g": baseline_mae,
        "macro_category_mae_candidate_g": candidate_mae,
        "feature_extraction_seconds": feature_seconds,
        "test_decision": "PASS" if (
            candidate_mae <= 0.9 * baseline_mae
            and ci_high < 0.0
            and candidate_mae <= 1.05 * baseline_mae
            and abs(candidate_bias) <= abs(baseline_bias) + 5.0
        ) else "FAIL",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    predictions = []
    for offset, idx in enumerate(test):
        record = records[int(idx)]
        predictions.append({
            "category": record["category"],
            "object": record["object"],
            "weight_g": float(truth[offset]),
            "baseline_g": float(baseline[offset]),
            "candidate_g": float(candidate[offset]),
            "frame_stem": record["frame_stem"],
        })
    write_jsonl(args.output / "test_predictions.jsonl", predictions)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
