# Synthetic food corpus and model comparison protocol

**State:** protocol defined; component baselines measured; all-stage freeze and candidate runs pending.  
**Scope:** WED’s 41 classes, renderer/appearance methods, and the existing NutriSense stages.

## Source and split rules

- Generators read only WED TRAIN rows and their paired images/masks, excluding the fixed seed-42 10% DEV plate carve from manifest rows still labeled `train`. A source group is the WED physical plate identity (`date_key_set`); every derivative inherits it.
- DEV is the only candidate selection/tuning tier. WED LOCKED and all 23 ArUco frames are excluded from generator/model training and tuning.
- Six user-labeled ArUco meal groups are eligible only for one exploratory report after every candidate and threshold is frozen.
- Generated images, masks, depth maps, caches, and model checkpoints stay under ignored `datasets/processed/` paths.

## Baseline and model order

Before corpus generation, freeze per-stage real WED baselines and their source/model/configuration hashes. Report classification top-1 and macro F1; segmentation IoU/Dice and item coverage; synthetic metric-depth error and separately labeled real marker/scale diagnostics; weight item/meal error in grams with group intervals; and end-to-end critical failure rates. Tune in this order: classification, segmentation, depth/geometry, weight, end-to-end. Numeric promotion thresholds are registered after the baseline report is frozen.

`tools/run_synthetic_baselines.py` measures the clean TRAIN-gallery classifier and multi-item SAM2 segmenter on WED DEV, then writes a readiness report. `tools/run_renderer_depth_baseline.py` measures product MoGe against analytic renderer camera-Z truth; `tools/run_synthetic_e2e_baseline.py` runs the production pipeline on the original-image DEV carve. These commands cannot declare the baseline frozen. Corpus generation and generator training require a reviewed `baseline_freeze.json` with all five stage metrics and model/data/split hashes.

## Corpus and method matrix

1. Generate isolated dishes with WED-observed portion ranges and balanced coverage capped by distinct TRAIN groups.
2. Generate composed thalis from multiple labeled components in one WED TRAIN physical group.
3. For each scene, produce a paired ID 7 / 60 mm card render and a no-card render from the same scene configuration. Randomized camera, distance, lighting, vessel, and background vary between pairs only. The no-card context contains no marker-derived scale or pose.
4. Compare analytic rendering, a WED TRAIN mask-conditioned GAN, and a spatially conditioned diffusion candidate when its exact checkpoint/license/data provenance is reviewed. Appearance methods can edit food pixels only; the renderer retains backgrounds, marker pixels, masks, depth, volume, and mass. Identity remains subject to human review.
5. Compare 0%, 25%, 50%, 75%, and 100% synthetic data with equal total examples, per-class quotas, downstream steps, and resolution for every method. The 0% and 100% conditions are real-only and synthetic-only.

## Physical labels and quality gate

For component `i`, synthetic mass is the renderer-integrated volume times the class density. Density configuration is drawn from the existing class mapping in `data/wed_dishes.yaml` / `data/menu.yaml`, which marks these values as assumptions; a broad project fallback is also marked assumed. Every mass record keeps the density source, uncertainty range, and `synthetic_physical` type. Image-inferred mass predictions are stored separately and never substitute for this target.

Automated checks cover image/mask/depth dimensions and ranges, class slots, component mass, marker corners, output hashes, source lineage, and exact pair invariants. Export a review queue stratified by class, portion range, method, card condition, and lighting. The review summary reports a per-stratum acceptance gate; it must pass before any samples are used for model training. A discriminator score or visual realism score is descriptive only.

## Promotion and final reports

A method is retained only when it passes task-specific label checks and improves its pre-registered target metric on the same WED DEV groups, with group-based uncertainty and no critical regressions in other stages or full-meal behavior. Synthetic depth performance is reported only against renderer truth. Real marker/scale diagnostics and real mass error remain separate; no real depth-accuracy claim is allowed.

After selection is fixed, use the existing guarded process for at most one WED LOCKED report. Produce one separate, exploratory six-group ArUco mass report with tare separate from net component masses. Neither final report may change candidate selection or thresholds.

## Current run status

No valid all-stage baseline freeze, GAN checkpoint, reviewed diffusion checkpoint, stratified human review summary, ablation results, candidate freeze, or final ArUco inference report is present. Do not treat existing reused DEV reports as new frozen baselines.

### DEV component baseline run (2026-11-02)

The approved RTX 4060 runtime is available to this workspace. The clean classifier gallery was built from at most 24 TRAIN physical groups per class, excluding the fixed DEV carve. On 1,218 ground-truth food crops across 21 DEV groups, top-1 accuracy was 0.762 (group-bootstrap 95% CI 0.719–0.792) and macro-F1 was 0.677. This measures isolated crop classification, not full pipeline behavior.

The deployed multi-item segmenter scored mean union-mask IoU 0.192 (group-bootstrap 95% CI 0.171–0.212), Dice 0.306 (0.275–0.333), and per-dish item coverage at IoU >= 0.5 of 0.164 (0.145–0.184), with no failed views. These weak values are retained as measured references and need investigation during segmentation optimization.

The existing deployable weight head was rerun on WED DEV: 15.034 g MAE over 1,218 regions / 21 groups (the DEV set has prior model-selection exposure); this is not a fresh independent evaluation and must not be represented as one. The MoGe/prior-geometry mass path reported 1,524.3 g per-region MAE, 4,618.7 g merged-meal MAE, and 33 failed ROI extractions. This is a real-mass/geometry diagnostic, not a depth-accuracy metric. See `baseline_findings.md` and `baseline_weight_dev.json`, `baseline_depth_geometry_weight_dev.json`, `component_baselines_dev.json`, `renderer_depth_baseline.json`, and `e2e_dev_baseline.json`. Measured component and end-to-end baselines now exist, but the baseline gate remains open pending review, weight/depth evidence limitations, and root-cause fixes/threshold registration. Do not generate or train candidates yet.
