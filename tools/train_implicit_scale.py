"""Train the card-free implicit scale and mass estimator with Leave-One-Dish-Out Cross-Validation (LODO-CV).

Supervised by ArUco metric ground-truth with marker-dropout domain randomization.
Produces:
  - data/implicit_scale_head.pt (Full production checkpoint)
  - data/reports/card_free_implicit_scale_eval.json (3-way evaluation report)
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine.pipeline as pipeline
from models.implicit_scale import (
    DEFAULT_CHECKPOINT,
    ImplicitScaleHead,
    RESIZE,
)
from models.scale_anchor import read_exif
from nutrisense_synth.measured import (
    ArucoSupervisedExample,
    load_aruco_supervised_examples,
    mask_out_marker,
)

REPORT_PATH = ROOT / "data" / "reports" / "card_free_implicit_scale_eval.json"


def _build_transform():
    return transforms.Compose([
        transforms.Resize(RESIZE),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])


def _extract_tensors(
    examples: list[ArucoSupervisedExample],
    device: torch.device,
    tf: Any,
    include_original: bool = True,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    images_list = []
    scale_targets_list = []
    mass_targets_list = []

    for ex in examples:
        img = cv2.imread(str(ex.image_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        max_dim = max(h, w)

        # 1. Image with card digitally erased (primary domain)
        masked_img = mask_out_marker(img, ex.marker_corners_px, expansion=2.5)

        s_224 = ex.cm_per_px * (max_dim / 224.0)
        d_scale = 0.1152
        mass_g = ex.ground_truth_total_g

        variants = [masked_img, img] if include_original else [masked_img]
        for variant in variants:
            rgb = Image.fromarray(variant[:, :, ::-1])
            images_list.append(tf(rgb))
            scale_targets_list.append([math.log(s_224), math.log(d_scale)])
            mass_targets_list.append([math.log(mass_g)])

    images_t = torch.stack(images_list).to(device)
    scale_targets_t = torch.tensor(scale_targets_list, dtype=torch.float32, device=device)
    mass_targets_t = torch.tensor(mass_targets_list, dtype=torch.float32, device=device)
    return images_t, scale_targets_t, mass_targets_t


def _train_single_model(
    train_examples: list[ArucoSupervisedExample],
    device: torch.device,
    tf: Any,
    epochs: int = 50,
    lr: float = 1e-3,
) -> ImplicitScaleHead:
    images_t, scale_targets_t, mass_targets_t = _extract_tensors(
        train_examples, device, tf, include_original=True
    )

    model = ImplicitScaleHead(pretrained=True).to(device)
    model.train()

    optimizer = torch.optim.AdamW(
        list(model.scale_mlp.parameters()) + list(model.mass_mlp.parameters()),
        lr=lr,
        weight_decay=1e-4,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.SmoothL1Loss()

    for _ in range(epochs):
        optimizer.zero_grad()
        scale_pred, mass_pred = model(images_t)
        loss_scale = criterion(scale_pred, scale_targets_t)
        loss_mass = criterion(mass_pred, mass_targets_t)
        loss = loss_scale + 0.5 * loss_mass
        loss.backward()
        optimizer.step()
        scheduler.step()

    model.eval()
    return model


def run_lodo_cv_and_eval(
    epochs: int = 50,
    out_path: Path = DEFAULT_CHECKPOINT,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("===========================================================")
    print(f"🚀 LEAVE-ONE-DISH-OUT CROSS-VALIDATION (LODO-CV) ON {device}")
    print("===========================================================")

    all_examples = load_aruco_supervised_examples()
    if not all_examples:
        raise RuntimeError("No ArUco supervised examples found in dataset directory!")

    tf = transforms.Compose([
        transforms.Resize(RESIZE),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    dish_groups: dict[str, list[ArucoSupervisedExample]] = defaultdict(list)
    for ex in all_examples:
        dish_groups[ex.dish_name].append(ex)

    dish_names = sorted(dish_groups.keys())
    print(f"Found {len(all_examples)} captures across {len(dish_names)} dishes: {dish_names}\n")

    fold_models: dict[str, ImplicitScaleHead] = {}
    fold_metrics: dict[str, Any] = {}

    # Step 1: Train 6 LODO fold models
    for held_out_dish in dish_names:
        train_pool = [ex for d, exs in dish_groups.items() if d != held_out_dish for ex in exs]
        val_pool = dish_groups[held_out_dish]

        print(f"--- Training Fold [Held-out: {held_out_dish}] ({len(train_pool)} train, {len(val_pool)} val) ---")
        model = _train_single_model(train_pool, device, tf, epochs=epochs)
        fold_models[held_out_dish] = model

        # Evaluate scale predictions on held-out dish (marker erased)
        scale_errors = []
        rel_scale_errors = []
        depth_scale_errors = []

        for ex in val_pool:
            img = cv2.imread(str(ex.image_path))
            if img is None:
                continue
            masked = mask_out_marker(img, ex.marker_corners_px, expansion=2.5)
            pred = model.predict(masked)
            s_pred = pred["cm_per_px"]
            d_pred = pred["depth_scale_factor"]

            s_err = abs(s_pred - ex.cm_per_px)
            rel_err = s_err / ex.cm_per_px * 100.0
            d_err = abs(d_pred - 0.1152)

            scale_errors.append(s_err)
            rel_scale_errors.append(rel_err)
            depth_scale_errors.append(d_err)

        fold_metrics[held_out_dish] = {
            "n_val": len(val_pool),
            "scale_mae_cm_px": float(np.mean(scale_errors)),
            "scale_mape_pct": float(np.mean(rel_scale_errors)),
            "depth_scale_mae": float(np.mean(depth_scale_errors)),
        }
        print(f"  Held-out {held_out_dish} Scale MAE: {fold_metrics[held_out_dish]['scale_mae_cm_px']:.5f} cm/px ({fold_metrics[held_out_dish]['scale_mape_pct']:.2f}%)")

    # Overall LODO scale metrics
    all_scale_maes = [m["scale_mae_cm_px"] for m in fold_metrics.values()]
    all_scale_mapes = [m["scale_mape_pct"] for m in fold_metrics.values()]
    lodo_scale_mae = float(np.mean(all_scale_maes))
    lodo_scale_mape = float(np.mean(all_scale_mapes))
    print(f"\n✓ Overall 6-Fold LODO Scale MAE: {lodo_scale_mae:.5f} cm/px ({lodo_scale_mape:.2f}%)")

    # Step 2: 3-Way Paired Pipeline Comparison Across All 23 Captures
    print("\n===========================================================")
    print("📊 RUNNING 3-WAY PAIRED EVALUATION ON FULL PIPELINE")
    print("   Mode A: Physical ArUco Marker Present (Measured Tier)")
    print("   Mode B: Marker Digitally Erased + LODO Out-of-Fold Implicit Head")
    print("   Mode C: Legacy Uncalibrated Prior Tier (No Fiducial, No Head)")
    print("===========================================================")

    per_image_results = []
    mode_a_errors, mode_a_apes = [], []
    mode_b_errors, mode_b_apes = [], []
    mode_c_errors, mode_c_apes = [], []

    dish_stats = {d: {"a_errs": [], "b_errs": [], "c_errs": [], "gt_mass": 0.0} for d in dish_names}

    for idx, ex in enumerate(all_examples, 1):
        img = cv2.imread(str(ex.image_path))
        if img is None:
            continue
        masked_img = mask_out_marker(img, ex.marker_corners_px, expansion=2.5)
        exif = read_exif(ex.image_path)
        gt_g = ex.ground_truth_total_g
        dish_stats[ex.dish_name]["gt_mass"] = gt_g

        # Mode A: Card Present
        res_a = pipeline.analyze(img, day="mon", band="1-5", exif=exif)
        grams_a = float(res_a.get("portion", {}).get("grams", 0.0))
        err_a = grams_a - gt_g
        ape_a = abs(err_a) / gt_g * 100.0
        mode_a_errors.append(err_a)
        mode_a_apes.append(ape_a)
        dish_stats[ex.dish_name]["a_errs"].append(abs(err_a))

        # Mode B: Card-Free (Out-of-Fold Model)
        oof_model = fold_models[ex.dish_name]
        res_b = pipeline.analyze(
            masked_img, day="mon", band="1-5", exif=exif, deps={"implicit_scale_head": oof_model}
        )
        grams_b = float(res_b.get("portion", {}).get("grams", 0.0))
        err_b = grams_b - gt_g
        ape_b = abs(err_b) / gt_g * 100.0
        mode_b_errors.append(err_b)
        mode_b_apes.append(ape_b)
        dish_stats[ex.dish_name]["b_errs"].append(abs(err_b))

        # Mode C: Legacy Uncalibrated Prior
        res_c = pipeline.analyze(
            masked_img, day="mon", band="1-5", exif=exif, deps={"implicit_scale_head": None}
        )
        grams_c = float(res_c.get("portion", {}).get("grams", 0.0))
        err_c = grams_c - gt_g
        ape_c = abs(err_c) / gt_g * 100.0
        mode_c_errors.append(err_c)
        mode_c_apes.append(ape_c)
        dish_stats[ex.dish_name]["c_errs"].append(abs(err_c))

        print(f"[{idx:2d}/23] {ex.dish_name} ({ex.filename[:20]}...) GT: {gt_g:5.1f}g | Mode A: {grams_a:5.1f}g (Δ{err_a:+5.1f}g) | Mode B: {grams_b:5.1f}g (Δ{err_b:+5.1f}g) | Mode C: {grams_c:5.1f}g (Δ{err_c:+5.1f}g)")

        per_image_results.append({
            "dish_name": ex.dish_name,
            "filename": ex.filename,
            "ground_truth_g": gt_g,
            "mode_a_card_present": {
                "grams": round(grams_a, 2),
                "error_g": round(err_a, 2),
                "ape_pct": round(ape_a, 2),
                "verdict": res_a.get("verdict"),
                "anchor_tier": res_a.get("anchor", {}).get("tier"),
            },
            "mode_b_card_free_oof": {
                "grams": round(grams_b, 2),
                "error_g": round(err_b, 2),
                "ape_pct": round(ape_b, 2),
                "verdict": res_b.get("verdict"),
                "anchor_tier": res_b.get("anchor", {}).get("tier"),
                "cm_per_px": res_b.get("anchor", {}).get("cm_per_px"),
            },
            "mode_c_uncalibrated_prior": {
                "grams": round(grams_c, 2),
                "error_g": round(err_c, 2),
                "ape_pct": round(ape_c, 2),
                "verdict": res_c.get("verdict"),
                "anchor_tier": res_c.get("anchor", {}).get("tier"),
            },
        })

    # Summary Statistics
    summary = {
        "mode_a_card_present": {
            "mae_g": float(np.mean([abs(e) for e in mode_a_errors])),
            "mape_pct": float(np.mean(mode_a_apes)),
            "signed_bias_g": float(np.mean(mode_a_errors)),
            "rmse_g": float(np.sqrt(np.mean(np.square(mode_a_errors)))),
        },
        "mode_b_card_free_oof": {
            "mae_g": float(np.mean([abs(e) for e in mode_b_errors])),
            "mape_pct": float(np.mean(mode_b_apes)),
            "signed_bias_g": float(np.mean(mode_b_errors)),
            "rmse_g": float(np.sqrt(np.mean(np.square(mode_b_errors)))),
        },
        "mode_c_uncalibrated_prior": {
            "mae_g": float(np.mean([abs(e) for e in mode_c_errors])),
            "mape_pct": float(np.mean(mode_c_apes)),
            "signed_bias_g": float(np.mean(mode_c_errors)),
            "rmse_g": float(np.sqrt(np.mean(np.square(mode_c_errors)))),
        },
    }

    per_dish_summary = {}
    for d in dish_names:
        per_dish_summary[d] = {
            "ground_truth_g": dish_stats[d]["gt_mass"],
            "mode_a_mae_g": float(np.mean(dish_stats[d]["a_errs"])),
            "mode_b_mae_g": float(np.mean(dish_stats[d]["b_errs"])),
            "mode_c_mae_g": float(np.mean(dish_stats[d]["c_errs"])),
        }

    # Step 3: Train Final Production Model on all 23 Captures
    print(f"\n--- Training Final Production ImplicitScaleHead on all {len(all_examples)} Captures ---")
    prod_model = _train_single_model(all_examples, device, tf, epochs=epochs)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    final_report = {
        "metadata": {
            "device": str(device),
            "epochs": epochs,
            "n_captures": len(all_examples),
            "n_folds": len(dish_names),
            "lodo_scale_mae_cm_px": round(lodo_scale_mae, 5),
            "lodo_scale_mape_pct": round(lodo_scale_mape, 2),
        },
        "summary": summary,
        "per_dish_summary": per_dish_summary,
        "fold_metrics": fold_metrics,
        "per_image_results": per_image_results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)
    print(f"✓ Saved 3-way evaluation report to: {report_path}")

    # Save final production weights with embedded LODO metadata
    prod_model.save(out_path, meta=final_report["metadata"])
    print(f"✓ Saved production model to: {out_path}")

    print("\n=======================================================")
    print("🏆 3-WAY COMPARISON BENCHMARK SUMMARY (N=23 CAPTURES)")
    print("=======================================================")
    print(f"Mode A (Card Present):     MAE: {summary['mode_a_card_present']['mae_g']:.1f}g | MAPE: {summary['mode_a_card_present']['mape_pct']:.1f}% | Bias: {summary['mode_a_card_present']['signed_bias_g']:+.1f}g")
    print(f"Mode B (Card-Free LODO):   MAE: {summary['mode_b_card_free_oof']['mae_g']:.1f}g | MAPE: {summary['mode_b_card_free_oof']['mape_pct']:.1f}% | Bias: {summary['mode_b_card_free_oof']['signed_bias_g']:+.1f}g")
    print(f"Mode C (Uncalibrated Prior): MAE: {summary['mode_c_uncalibrated_prior']['mae_g']:.1f}g | MAPE: {summary['mode_c_uncalibrated_prior']['mape_pct']:.1f}% | Bias: {summary['mode_c_uncalibrated_prior']['signed_bias_g']:+.1f}g")
    print("=======================================================\n")

    return final_report


if __name__ == "__main__":
    run_lodo_cv_and_eval()
