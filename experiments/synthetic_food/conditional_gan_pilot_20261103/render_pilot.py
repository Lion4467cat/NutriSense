"""Apply the local SPADE-style checkpoint to five frozen Blender layouts.

Only RGB is written. Blender masks and all physical-label artifacts are read
as immutable inputs and copied into the report by reference.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from experiments.synthetic_food.conditional_gan_pilot_20261103.spade_pilot import (  # noqa: E402
    LayoutGenerator, N_CLASSES, SIDE,
)
from models.wed_semantic_segmenter import load_checkpoint, predict_labels  # noqa: E402
from nutrisense_synth.methods.base import GenerationContext, restore_scene_owned_pixels  # noqa: E402

OUT = ROOT / "datasets/processed/conditional_gan_pilot_20261103"
SEGMENTER_CKPT = ROOT / "experiments/wed_native_segmentation/model_wed_semantic_baseline.pt"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boundary_f1(target: np.ndarray, prediction: np.ndarray, tolerance: int = 2) -> float:
    kernel = np.ones((2 * tolerance + 1, 2 * tolerance + 1), np.uint8)
    t = target.astype(np.uint8)
    p = prediction.astype(np.uint8)
    tb = t.astype(bool) & ~cv2.erode(t, np.ones((3, 3), np.uint8)).astype(bool)
    pb = p.astype(bool) & ~cv2.erode(p, np.ones((3, 3), np.uint8)).astype(bool)
    matched_p = np.count_nonzero(pb & (cv2.dilate(t.astype(np.uint8), kernel) > 0))
    matched_t = np.count_nonzero(tb & (cv2.dilate(p.astype(np.uint8), kernel) > 0))
    precision = matched_p / max(1, int(pb.sum()))
    recall = matched_t / max(1, int(tb.sum()))
    return float(2 * precision * recall / max(1e-8, precision + recall))


def metric_summary(target: np.ndarray, prediction: np.ndarray, classes: dict[int, str]):
    out = {"per_class": {}, "macro_target_iou": None,
           "predicted_food_class_pixels": {}, "predicted_background_pixels": int(np.count_nonzero(prediction == 0))}
    predicted_values, predicted_counts = np.unique(prediction, return_counts=True)
    out["predicted_food_class_pixels"] = {
        str(int(cid)): int(count) for cid, count in zip(predicted_values, predicted_counts)
        if 0 < int(cid) < N_CLASSES
    }
    out["top_predicted_food_class_id"] = (
        int(max(out["predicted_food_class_pixels"],
                key=lambda cid: out["predicted_food_class_pixels"][cid]))
        if out["predicted_food_class_pixels"] else None)
    ious = []
    for cid, name in classes.items():
        t, p = target == cid, prediction == cid
        intersection = int(np.count_nonzero(t & p))
        union = int(np.count_nonzero(t | p))
        iou = intersection / max(1, union)
        t_count, p_count = int(t.sum()), int(p.sum())
        out["per_class"][str(cid)] = {
            "name": name, "input_pixels": t_count, "predicted_pixels": p_count,
            "iou": iou, "area_ratio_pred_over_target": p_count / max(1, t_count),
            "precision": intersection / max(1, p_count),
            "recall": intersection / max(1, t_count),
            "boundary_f1_tolerance_2px": boundary_f1(t, p),
        }
        if t_count:
            ious.append(iou)
    out["macro_target_iou"] = float(np.mean(ious)) if ious else 0.0
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path,
                        default=OUT / "spade_epoch_020.pt")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if args.device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; use the approved runtime or --device cpu for diagnostics")
    device = torch.device(args.device)
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    if checkpoint.get("architecture") != LayoutGenerator.architecture:
        raise ValueError("Unexpected SPADE pilot checkpoint architecture")
    generator = LayoutGenerator().to(device)
    generator.load_state_dict(checkpoint["generator_state_dict"], strict=True)
    generator.eval()
    segmenter, seg_meta = load_checkpoint(SEGMENTER_CKPT, device="cpu")
    source = json.loads((OUT / "pilot_inputs.json").read_text(encoding="utf-8"))
    rendered = []
    class_names = {int(cid): item["name"] for cid, item in source["classes"].items()}
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    for raw_cid, item in source["classes"].items():
        cid = int(raw_cid)
        rgb_path = ROOT / item["blender"]["rgb_path"]
        mask_path = ROOT / item["blender"]["mask_path"]
        original_bgr = cv2.imread(str(rgb_path), cv2.IMREAD_COLOR)
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if original_bgr is None or mask is None:
            raise FileNotFoundError(f"Missing Blender input for {item['name']}")
        original_rgb = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB)
        if original_rgb.shape[:2] != mask.shape:
            raise ValueError("Blender RGB and mask dimensions differ")
        label_small = cv2.resize(mask, (SIDE, SIDE), interpolation=cv2.INTER_NEAREST)
        onehot = np.eye(N_CLASSES, dtype=np.float32)[label_small].transpose(2, 0, 1)
        condition = torch.from_numpy(onehot[None]).to(device)
        seed = 20261103 + cid
        z = torch.Generator(device=device).manual_seed(seed)
        noise = torch.randn((1, generator.noise_dim), generator=z, device=device)
        start = time.perf_counter()
        with torch.inference_mode():
            generated = generator(condition, noise)[0].float().cpu().numpy().transpose(1, 2, 0)
        elapsed = time.perf_counter() - start
        generated = np.clip((generated + 1) * 127.5, 0, 255).astype(np.uint8)
        generated = cv2.resize(generated, (mask.shape[1], mask.shape[0]), interpolation=cv2.INTER_CUBIC)
        food = mask > 0
        context = GenerationContext(
            scene_id=item["blender"]["sample_id"], seed=seed,
            condition_rgb=original_rgb, semantic_mask=mask,
            depth_m=np.load(rgb_path.parent / "metric_depth.npy"),
            marker_mask=np.zeros_like(mask, dtype=bool), food_mask=food,
            metadata={"class_name": item["name"]},
        )
        output_rgb = restore_scene_owned_pixels(generated, context)
        nonfood_exact = bool(np.array_equal(output_rgb[~food], original_rgb[~food]))
        baseline_start = time.perf_counter()
        baseline_prediction = predict_labels(segmenter, original_bgr, "cpu", size=(768, 1024))
        baseline_seconds = time.perf_counter() - baseline_start
        baseline_metrics = metric_summary(mask, baseline_prediction, class_names)
        output_dir = OUT / "generated" / f"class_{cid:02d}_{item['name']}"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "spade_rgb.png"
        cv2.imwrite(str(output_path), cv2.cvtColor(output_rgb, cv2.COLOR_RGB2BGR))
        prediction = predict_labels(segmenter, cv2.cvtColor(output_rgb, cv2.COLOR_RGB2BGR),
                                    "cpu", size=(768, 1024))
        metrics = metric_summary(mask, prediction, class_names)
        target_metrics = metrics["per_class"][str(cid)]
        machine_screen_pass = (
            target_metrics["iou"] >= 0.50
            and target_metrics["boundary_f1_tolerance_2px"] >= 0.60
            and metrics["top_predicted_food_class_id"] == cid
            and 0.70 <= target_metrics["area_ratio_pred_over_target"] <= 1.30
        )
        vis = np.zeros((*mask.shape, 3), dtype=np.uint8)
        target_pixels = mask == cid
        predicted_pixels = prediction == cid
        vis[target_pixels & predicted_pixels] = (39, 164, 89)
        vis[target_pixels & ~predicted_pixels] = (242, 179, 50)
        vis[~target_pixels & predicted_pixels] = (224, 63, 60)
        cv2.imwrite(str(output_dir / "mask_diagnostic_target_pred.png"), vis)
        rendered.append({"class_id": cid, "class_name": item["name"],
                         "blender_rgb": str(rgb_path.relative_to(ROOT)),
                         "semantic_mask": str(mask_path.relative_to(ROOT)),
                         "wed_train_reference": item["wed_train_reference"],
                         "generated_rgb": str(output_path.relative_to(ROOT)),
                         "non_food_rgb_exactly_preserved": nonfood_exact,
                         "blender_baseline_segmentation_metrics": baseline_metrics,
                         "blender_baseline_segmenter_seconds": baseline_seconds,
                         "frozen_segmentation_metrics": metrics,
                         "automated_consistency_screen": (
                             "HUMAN_REVIEW_REQUIRED" if machine_screen_pass else "REJECTED_FOR_TRAINING"),
                         "inference_seconds": elapsed})
    checkpoint_path = args.checkpoint.resolve()
    report = {"generator_checkpoint": str(checkpoint_path.relative_to(ROOT)),
              "generator_sha256": sha(args.checkpoint),
              "frozen_segmenter_checkpoint": str(SEGMENTER_CKPT.relative_to(ROOT)),
              "frozen_segmenter_sha256": sha(SEGMENTER_CKPT),
              "frozen_segmenter_revision": seg_meta.get("architecture"),
              "device": str(device), "peak_vram_mb": (
                  torch.cuda.max_memory_allocated(device) / (1024**2)
                  if device.type == "cuda" else 0),
              "automated_consistency_screen_rule": {
                  "target_class_iou_min": 0.50, "boundary_f1_tolerance_2px_min": 0.60,
                  "target_must_be_top_predicted_food_class": True,
                  "predicted_to_target_area_ratio_range": [0.70, 1.30],
                  "meaning": "Conservative research screening only; pass means human review is still required, never automatic approval."},
              "results": rendered,
              "label_provenance": "Blender masks/depth/geometry/mass/camera/marker remain immutable; only RGB within food-mask pixels is replaced.",
              "human_class_identity": "PENDING", "human_visual_review": "PENDING"}
    (OUT / "five_class_metrics.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    make_review_sheet(rendered)
    make_review_csv(rendered)
    print(json.dumps({"generated": len(rendered), "metrics": str(OUT / "five_class_metrics.json"),
                      "peak_vram_mb": report["peak_vram_mb"]}, indent=2))


def make_review_sheet(rendered):
    columns = ["Eligible WED TRAIN reference", "Existing Blender RGB", "GAN RGB",
               "Blender semantic mask", "Frozen segmenter diagnostic"]
    tw, th, gap, header = 240, 180, 12, 68
    row_h = th + 58
    sheet = Image.new("RGB", (gap + len(columns) * (tw + gap),
                               header + len(rendered) * row_h + gap), "#f4f1e8")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
        small = ImageFont.truetype("DejaVuSans.ttf", 11)
    except OSError:
        font = small = ImageFont.load_default()
    for col, title in enumerate(columns):
        draw.text((gap + col * (tw + gap), 14), title, fill="#24352c", font=font)
    inputs = json.loads((OUT / "pilot_inputs.json").read_text(encoding="utf-8"))
    for ridx, result in enumerate(rendered):
        cid = result["class_id"]
        item = inputs["classes"][str(cid)]
        y = header + ridx * row_h
        cls_metrics = result["frozen_segmentation_metrics"]["per_class"][str(cid)]
        blender_iou = result["blender_baseline_segmentation_metrics"]["per_class"][str(cid)]["iou"]
        draw.text((gap, y - 22),
                  f"{result['class_name']} · Blender IoU {blender_iou:.3f} → GAN {cls_metrics['iou']:.3f} · boundary F1 {cls_metrics['boundary_f1_tolerance_2px']:.3f}",
                  fill="#24352c", font=small)
        root_paths = [ROOT / item["wed_train_reference"],
                      ROOT / result["blender_rgb"],
                      ROOT / result["generated_rgb"],
                      ROOT / result["semantic_mask"],
                      OUT / "generated" / f"class_{cid:02d}_{result['class_name']}" / "mask_diagnostic_target_pred.png"]
        for col, path in enumerate(root_paths):
            image = Image.open(path)
            if col == 3:
                labels = np.asarray(image.convert("L"))
                color = np.zeros((*labels.shape, 3), dtype=np.uint8)
                color[labels == cid] = (39, 164, 89)
                image = Image.fromarray(color)
            else:
                image = image.convert("RGB")
            image.thumbnail((tw, th), Image.Resampling.LANCZOS)
            tile = Image.new("RGB", (tw, th), "white")
            tile.paste(image, ((tw - image.width) // 2, (th - image.height) // 2))
            sheet.paste(tile, (gap + col * (tw + gap), y))
    sheet.save(OUT / "five_class_comparison.png")


def make_review_csv(rendered):
    path = OUT / "human_review.csv"
    fields = ["class_id", "class_name", "automated_consistency_screen", "target_iou",
              "boundary_f1_tolerance_2px", "target_area_ratio", "top_predicted_food_class_id",
              "non_food_rgb_exactly_preserved", "wed_train_reference", "blender_rgb", "gan_rgb",
              "human_class_identity", "human_visual_realism", "human_label_validity", "reviewer_comments"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for result in rendered:
            cid = str(result["class_id"])
            metrics = result["frozen_segmentation_metrics"]
            target = metrics["per_class"][cid]
            writer.writerow({
                "class_id": cid,
                "class_name": result["class_name"],
                "automated_consistency_screen": result["automated_consistency_screen"],
                "target_iou": f"{target['iou']:.6f}",
                "boundary_f1_tolerance_2px": f"{target['boundary_f1_tolerance_2px']:.6f}",
                "target_area_ratio": f"{target['area_ratio_pred_over_target']:.6f}",
                "top_predicted_food_class_id": metrics["top_predicted_food_class_id"],
                "non_food_rgb_exactly_preserved": result["non_food_rgb_exactly_preserved"],
                "wed_train_reference": result["wed_train_reference"],
                "blender_rgb": result["blender_rgb"],
                "gan_rgb": result["generated_rgb"],
                "human_class_identity": "PENDING",
                "human_visual_realism": "PENDING",
                "human_label_validity": "PENDING",
                "reviewer_comments": "",
            })


if __name__ == "__main__":
    main()
