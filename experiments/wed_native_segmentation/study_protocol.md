# Controlled WED semantic segmentation improvement study

Status: protocol fixed before candidate training. The frozen reference is `model_wed_semantic_baseline.pt` (SHA-256 recorded in `baseline_manifest.json`). No candidate will overwrite or modify it.

## Data and separation

- Parse only WED manifest rows marked TRAIN.
- Exclude the existing seed-42 10% DEV physical-group carve (108 views / 21 groups) from every training and checkpoint-selection operation.
- Reuse the existing deterministic internal group holdout from the eligible TRAIN remainder for checkpoint selection.
- Do not open WED LOCKED/test images or any ArUco evaluation images.
- Do not use synthetic images, labels, or generated samples.
- Run one final DEV evaluation after all checkpoints and inference settings are frozen. DEV will not drive additional training, thresholds, or augmentation changes.

## Training budget and primary selection metric

All candidate runs use the same internal group split, seed 42, 10 complete passes over 928 internal training views (928 sampled views per epoch for class-balanced sampling), 110 internal validation views, effective batch size 2, AdamW schedule, maximum epochs, and early-stopping patience. High-resolution runs may use physical batch 1 with gradient accumulation 2. The best checkpoint for each run is selected by internal-validation macro food IoU. Record actual optimizer updates, wall time, peak training VRAM, and any OOM/retry.

Original frozen checkpoint remains the reference. A fresh DeepLabV3 control trained under the matched 10-epoch budget distinguishes architecture/configuration effects from extra training time.

## Stage A: one-factor DeepLabV3 ablations

The control recipe is 768×1024 input, standard shuffled sampling, current horizontal flip and mild brightness/contrast augmentation, and the baseline weighted-CE + foreground soft-Dice loss.

Each candidate changes one factor from that control:

1. **Higher resolution:** 864×1152; all other settings fixed.
2. **Class-balanced meal sampling:** capped inverse-square-root class-presence weights for WED TRAIN meal groups/views; all other settings fixed. Report resulting class/view exposure counts.
3. **Food-appropriate augmentation:** add vertical flips and small rotations (±10°), with mask-safe nearest-neighbor geometry and mild saturation variation; all other settings fixed.
4. **Boundary-aware loss:** retain the baseline weighted CE + Dice and add a predeclared boundary-weighted CE term; all other settings fixed.

Do not combine these changes during Stage A. Select the recipe with the best internal-validation macro food IoU, using the target small-region and per-class metrics as diagnostics. The selection and tradeoffs are logged before architecture comparison.

## Stage B: architecture comparison

Train DeepLabV3, DeepLabV3+, and SegFormer-B0 with the Stage A selected recipe, identical data groups, 10-epoch budget, checkpoint criterion, and input resolution. DeepLabV3+ uses an ImageNet ResNet-50 encoder and an ASPP + low-level skip decoder. SegFormer-B0 uses a public ADE20K-pretrained MiT-B0 encoder/decoder with its class head replaced by 42 WED logits. Record pretrained weight revisions and hashes. If pretrained SegFormer weights cannot be fetched, stop that architecture comparison rather than silently compare a scratch model to pretrained CNNs.

## Metrics fixed before DEV evaluation

- **Pixels:** macro IoU over WED classes present in DEV, and foreground union IoU.
- **Classes:** per-class IoU for all 41 classes, explicitly noting classes absent from DEV.
- **Regions:** per-class 8-connected components, same-class Hungarian one-to-one matching at IoU ≥ 0.5, precision/recall/F1, unmatched duplicates and spurious regions.
- **Small regions:** same size bins as `error_analysis.md` (<0.1%, 0.1–0.25%, 0.25–0.5%, ≥0.5% of image pixels), with pixel recall, zero-overlap misses, and IoU≥0.5 region recall.
- **Merge/fragmentation proxies:** predicted components overlapping multiple GT semantic components of the same class; GT components touched by multiple predicted components. These remain raster-topology proxies, not physical-serving instance metrics.
- **Boundary quality:** class-wise boundary F1 with a fixed 3-pixel tolerance at original DEV resolution; report macro food boundary F1 and boundary precision/recall.
- **Efficiency:** per-image batch-1 inference latency after warmup, synchronized CUDA timing, peak allocated inference VRAM, model parameter count, and checkpoint size.
- Use the same frozen 108 DEV views, label files, component extraction, size bins, and metrics for every candidate and the original checkpoint. Bootstrap candidate-vs-reference differences by physical meal group.

## Recommendation gate

Recommend a candidate only if paired bootstrap resampling of physical DEV meal groups (10,000 resamples, fixed seed 42) gives a 95% confidence interval entirely above zero for both macro food IoU and the selected tiny-region target, and the point gains are at least +0.01 absolute macro food IoU and +5 percentage points in either tiny-bin pixel recall or tiny-bin IoU≥0.5 region recall. In addition, require the lower 95% confidence bound for foreground IoU and region F1 difference to be above −0.01; no named priority class may regress by more than 0.05 IoU; the upper 95% bound on the increase in mean merge or fragmentation proxy counts must be at most +0.25 per meal; macro boundary F1 may not fall by more than 0.01; and batch-1 inference latency must be at most 2× the frozen reference. Report all regressions and uncertainty; if no candidate passes, retain the frozen baseline without promotion. These thresholds are study decision rules, not claims of statistical power or serving-level instance accuracy.

## Scope limits

This study is segmentation-only. It does not change geometry, depth, portion, or weight estimation and does not claim serving-level instance segmentation.
