# Existing-pipeline investigation (2026-11-02)

## Guardrails

All real-image debugging uses only the fixed 108-view WED DEV carve from WED TRAIN physical groups (seed 42). Generator, corpus, and synthetic model training remain paused. No WED LOCKED image or ArUco evaluation image was opened. Renderer scenes were used only as ephemeral metric-depth probes; no rendered corpus was generated.

## Segmentation and detection

### Root cause

The old detector had nine prompts and returned at most nine candidate regions; on the WED DEV plate, duplicate/overlap handling often left only 1–8 items. WED images have a mean 11.58 semantic food regions per view. These class masks identify foods within one plate, while SAM2 prompts identify generic local objects/portions. They are related targets but not equivalent instances.

The old foreground single-mask SAM2 call was not a food-union segmenter on these images: on the first six DEV views its mean IoU against the WED food union was 0.043. The old multi-item union was better but still imperfect. Its all-DEV mean union IoU was 0.192; its 0.164 item-coverage metric was strict IoU>=0.5 matching against semantic class regions, not vessel recall.

### Candidate change and matched DEV probe

The detector now has an experimental 5x5 inward point grid, batched four prompts at a time, with 34% local crops. It retains small proposals down to 0.1% of the image, removes the nine-item output truncation, and reports the number of proposals and zero truncation. An OOM catch recursively halves a batch. The strategy is named `dense_grid_box`; production preserves the existing coverage-unverified verdict behavior for this detector.

On the first six views of one DEV group, the inward-grid candidate produced a mean 12.17 regions for 12 semantic regions, foreground union IoU 0.274, per-region IoU>=0.5 coverage 0.444, and GT-region-area recall>=0.5 of 0.528. The old detector on those same six views had mean union IoU 0.331 and per-region IoU coverage 0.319. The candidate raises proposal recall while reducing union-mask overlap; it is not promoted as an overall segmentation improvement until full-DEV and end-to-end results are reviewed.

The end-to-end 6-view smoke with the inward grid returned an average of 12.17 items, but meal MAE was 410.47 g versus 262.42 g for the old report’s same six views. Repeated classifier outputs (especially `curd`, `wheat_product`, `vegetable_rice`, and `Watermelon`) indicate that more proposals also create duplicates and false positives. The full 108-view corrected run is underway. Its completeness gate now compares canonical serving-class multisets as well as item count, labels, portions, and pipeline failures; count equality alone is insufficient.

### Interpretation

The proposal-count limit is fixed in the candidate, but SAM2 alone does not produce WED-aligned class regions reliably enough for mass aggregation. Existing dense proposals do not yet make the pipeline reliable. A semantic food-region model trained/evaluated against WED masks is the likely next modeling change, but model training remains paused until the corrected baselines are reviewed.

## Depth

The prior renderer benchmark omitted `fov_x`, although production passes it. The corrected baseline derives horizontal FOV from exact renderer camera intrinsics and reruns all 246 matched card/no-card views. Exact FOV reduces raw no-card all-visible AbsRel from 5.289 to 4.576; it does not resolve absolute-scale error.

On food pixels with exact FOV, raw no-card MoGe has MAE 2.082 m, AbsRel 5.119, SILog 1.595%, and median prediction/target ratio 6.135. Raw card MoGe has MAE 3.567 m, AbsRel 8.765, SILog 1.239%, and ratio 9.781. Low SILog alongside high scale ratios indicates that relative depth shape is substantially better than the absolute scale on these renderer scenes.

Applying the production card-size global-scale calibration using renderer-known marker corners reduces card food AbsRel to 0.266, MAE to 0.107 m, δ1.25 to 0.980; median calibrated prediction/target ratio is 1.258. Median scale factor is 0.115 (10th–90th percentile 0.076–0.199). The renderer baseline exposes raw and calibrated results separately; the ArUco evaluation images were not used. This points to raw monocular global scale as the main renderer discrepancy, with residual scale error after marker calibration. No-card geometry remains uncalibrated; for mapped WED classes the deployed pipeline uses the learned weight head on that tier.

## Existing component results and limits

The WED DEV weight-head report (`baseline_weight_dev.json`) measures 15.03 g MAE (group-bootstrap 95% CI 12.23–18.89 g), 18.3% MAPE, and 85.2% nominal 90% interval coverage over 1,218 regions from 108 views / 21 plates. This is a teacher-forced component result: it uses ground-truth dish regions/crops and class identity, so it does not include detector misses, duplicate proposals, or classifier mistakes. It is not evidence that meal-level mass is accurate. The full-pipeline DEV report demonstrates the gap: absolute meal error is over 500 g and every meal fails the complete-component gate.

The prior no-card geometry/weight stress report has 1,524.33 g per-region MAE and 4,618.70 g merged-plate MAE, with 33 geometry failures. It mixes MoGe scale and footprint/base assumptions, which is why the single 9 g chutney trace above varies those factors independently. Classification on isolated WED DEV regions is 76.2% top-1 and 67.7% macro-F1 (1,218 oracle crops; group-bootstrap top-1 CI 71.9%–79.2%); it also excludes detector and crop errors. These component scores are useful diagnostics only, not interchangeable with end-to-end accuracy.

## Geometry and 9 g chutney

The saved one-factor-at-a-time DEV trace uses `20250512_set14`, WED's 9 g chutney semantic mask, exact production fallback FOV, and no-card prior anchor. MoGe median depth in the region is 2.112 m (p10–p90 2.095–2.154 m). The geometry estimator returns 1,186.45 g from 286.38 cm² × 41.43 mm / 10 × 1.0 g/ml.

- **Depth scale:** multiplying the full depth by 0.25 reduces the estimate to 82.1 g; factors 0.5 and 2.0 produce 442.1 g and 2,684.9 g. There is no WED per-pixel depth truth to select a valid correction for this photograph.
- **Base plane:** the ring fit is rejected at 10.8 mm RMS (limit 5 mm), so the estimator uses `table_prior`. Changing the assumed food-base height from 8 mm to 0, 25, and 45 mm yields 1,397.4 g, 761.7 g, and 332.3 g. The 8 mm assumption is not the dominant source of the error.
- **Food height:** the computed 41.43 mm contributes linearly to volume. A 0.25 height multiplier alone still gives 296.6 g at the current footprint.
- **Area/shape prior:** the generic 170 mm food-diameter prior creates 286.38 cm². Changing diameter to 30, 60, 100, or 210 mm gives 8.92, 35.67, 99.09, or 436.99 cm² and corresponding estimates 36.95, 147.79, 410.54, and 1,810.46 g. This is the largest direct assumed-geometry term for this small condiment.
- **Density/conversion:** chutney uses 1.0 g/ml; 0.7–1.3 g/ml changes the result linearly to 830.5–1,542.4 g. The unit conversion is internally consistent; density uncertainty cannot explain the thousand-gram error.

The mass path is physically underdetermined on this no-card image: the generic size prior and uncalibrated depth cannot recover a 9 g mass. The deployed no-card path for mapped WED classes uses the WED-trained weight head rather than this geometry estimate. No geometry prior was tuned against DEV labels. For measured-card geometry, marker scale fixes a global depth factor but does not validate base plane, portion shape, or vessel floor assumptions.

## End-to-end and final test status

The full dense-grid candidate run completed on all 108 DEV views from 21 physical groups. It produced a mass for every view, but no view had a complete item list under the exact canonical serving-class multiset gate. The returned meal-mass MAE was 567.51 g (group-bootstrap 95% CI 462.03–686.29 g), with +525.90 g signed bias; critical item-list failure was 108/108. The earlier 108-view report had MAE 611.35 g and −607.53 g bias, also 108/108 critical failures. Thus the candidate reduces MAE by 43.84 g but flips the large bias and does not improve the complete-meal gate. It is not a reliable end-to-end fix.

The 108-view segmentation summary for the candidate has foreground union IoU 0.151 (95% group-bootstrap CI 0.132–0.169), mean 13.69 predicted regions versus 11.28 WED semantic regions, per-region IoU≥0.5 coverage 0.260 (CI 0.229–0.288), and GT-region area recall≥0.5 of 0.358 (CI 0.331–0.385). The original proposal baseline's corresponding union IoU was 0.192 and strict item coverage 0.164. The candidate therefore improves semantic-region overlap/recall while reducing foreground union IoU; its extra regions also cause duplicates and incorrect class assignments. Equal count is not treated as complete: the final gate compares the predicted and expected canonical class multisets.

This establishes that removing the point/output cap alone is insufficient. SAM2's object proposals are not WED's semantic food regions. The strongest next fix is a WED-supervised semantic region model trained only from permitted TRAIN groups (with the DEV carve reserved for model selection), or a class-conditioned proposal assignment that is validated against the same region masks. The current candidate must not be described as promoted. No LOCKED or ArUco evaluation data were accessed.

### Test status

The focused regression suite passed: 59 passed, 2 deselected. It covered detector proposal count/deduplication, pipeline seams, end-to-end metric definitions, and the renderer FOV helper. Ruff passed on touched Python files. The two deselected tests are existing HTTP TestClient cases that hang in the current Starlette/httpx AnyIO portal setup; they were not part of the segmentation/depth/evaluation paths exercised here. No generator, corpus-generation, GAN/diffusion, or synthetic model-training run was started.
