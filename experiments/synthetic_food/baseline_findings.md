# Baseline findings (2026-11-02)

## Scope and data safety

All WED evaluation below uses a deterministic 10% DEV carve by physical plate group from rows marked TRAIN, seed 42: 108 views from 21 groups. Gallery examples come from the remaining TRAIN groups only. No WED LOCKED images or ArUco evaluation images were read (`locked_accessed=false`, `aruco_accessed=false` in the reports). The six manually weighed ArUco meal groups remain reserved for the previously agreed one-time exploratory report after model and threshold freeze.

These measurements document the current system. They do not pass the generation gate: observed failures need investigation and numeric promotion thresholds still need registration. Do not start corpus generation, generator experiments, or synthetic model training yet.

## Stage references

| Stage | DEV result | Interpretation and limitation |
|---|---:|---|
| Classification | Top-1 0.762; macro-F1 0.677 over 1,218 food regions / 21 groups; group-bootstrap top-1 95% CI 0.720–0.792 | Ground-truth food crops are classified using a clean TRAIN-only gallery (up to 24 physical groups/class). This isolates the classifier and does not include localization or segmentation errors. |
| Segmentation | Mean union IoU 0.192 (95% CI 0.171–0.212); Dice 0.306 (0.275–0.333); item-coverage proxy 0.164 (0.145–0.184); 108/108 views returned masks | Multi-item SAM2 masks are compared with WED semantic food masks. The 16.4% value is the fraction of semantic class regions matched by some predicted region at IoU >= 0.5. It is not vessel recall or per-instance segmentation AP; class regions and detected vessel regions are not the same target. |
| Renderer metric depth | 246 renderer views: 123 matched card and 123 no-card; renderer camera-Z is truth. See metrics below. | Raw product MoGe output, before marker-derived calibration. Tests transfer from WED-trained monocular depth model to the current renderer, not real-world depth accuracy. |
| Existing weight head | 15.034 g MAE over 1,218 regions / 21 groups in the exposed WED DEV result | This result had prior model-selection exposure. It is a useful existing reference, not an independent, untouched baseline or promotion evidence. See `baseline_weight_dev.json`. |
| Geometry mass path | 1,524.3 g per-region MAE; 4,618.7 g merged-meal MAE; +1,513.8 g per-region bias; 33 failed ROI extractions | Current MoGe/prior geometry path is catastrophically mis-scaled for many portions. It is an error diagnostic, not a depth metric. See `baseline_depth_geometry_weight_dev.json`. |
| Original-image end-to-end | 108/108 net-mass predictions; meal MAE 611.35 g; mean signed error -607.53 g; group-bootstrap MAE 95% CI 526.07–702.99 g; 108/108 critical failures; 0 complete item outputs | Runs the current `general` production pipeline from original images. A returned total can be incomplete, so mass-return coverage (100%) must not be interpreted as a successful result. The critical gate requires every labeled component to have a classified portion output. |

The end-to-end run used the fixed pipeline context `day=mon`, `band=1-5` because current input gates require these fields even in General mode; those values do not enter food-mass calculation. It uses 64 Monte Carlo samples, deterministic seed base 42, the clean TRAIN gallery, the current SAM2/MoGe/weight head, and reports net food mass with tare excluded. Configuration, model/code/data hashes, group IDs, and per-view predictions are in `e2e_dev_baseline.json`.

### Metric-depth detail

Metrics are computed on rendered visible regions with valid camera-Z target and prediction; `AbsRel = mean(abs(pred-target)/target)`, `delta_1.25` is the fraction within a 1.25 ratio, and intervals bootstrap scene groups. On food pixels, no-card raw MoGe gives MAE 2.410 m, RMSE 2.412 m, AbsRel 5.925 (95% CI 5.226–6.675), `delta_1.25` 0.008, and median prediction/target scale 6.95. With the card visible but no ArUco calibration applied, food MAE is 3.824 m, RMSE 3.827 m, AbsRel 9.403 (8.689–10.161), `delta_1.25` 0, and median scale 10.42. The target food median depth is 0.405 m; predicted medians are 2.814 m and 4.219 m respectively. All-visible no-card and card AbsRel are 5.289 and 8.682. This is a poor renderer-transfer baseline. Card visibility here is only a matched scene condition; the MoGe output is raw and does not use marker scale. No real depth-accuracy claim follows from this result.

## Failure investigation

### Why the segmentation coverage proxy is 16.4%

1. The comparison is structurally mismatched: WED marks 10–14 semantic food regions per view (mean 11.58), while the product multi-item detector samples a nine-point grid and then returns at most eight regions in the full pipeline. Every DEV view has more food regions than the nine seed locations, so some components cannot be proposed by design.
2. The nine points target separated vessel/portion centers. WED images instead show many adjacent food portions on a single plate. Several semantic regions may lie within one proposal, or be missed when no seed falls inside them.
3. The coverage metric requires a predicted region to overlap a semantic food-class region by IoU >= 0.5. A valid vessel region that spans multiple WED class regions can have poor IoU against each individual region. Thus this score combines missed proposals, mask boundary quality, and target-definition mismatch.
4. Union-mask IoU of 0.192 confirms that target mismatch is not the entire issue: the combined predicted masks also cover the semantic food foreground poorly. The zero failed-view count only means the segmentation call returned; it does not mean its masks were good.

Next useful baseline work is to separate foreground food-union segmentation from instance/portion discovery, then report proposal recall by semantic region and mask IoU for matched regions. That creates interpretable measurements before choosing a segmentation fix.

### Why geometry mass is so far off

The portion estimator uses `volume_ml = area_cm2 * mean_height_mm / 10`, then multiplies by assumed class density. A DEV trace for `20250512_set14` shows MoGe median depths around 2.10–2.24 m while the meal is a close plate view; no card is present, so the scale anchor falls back to uncertain size priors (`cm_per_px` is absent, `depth_scale_source=none`). The resulting prior/table-plane subtraction yields 40–92 mm mean heights for tiny foods, combined with 180–286 cm² estimated areas. These imply roughly 1.2–1.8 litres for individual portions such as 9 g chutney or 23 g cabbage, explaining the multi-kilogram overestimates.

The dominant observable contributors are (a) monocular depth scale/domain mismatch, (b) fallback plane/base-height assumptions, and (c) size-prior area and vessel-shape assumptions. The current traces do not isolate each term causally, so these are supported failure mechanisms, not a quantified attribution. The renderer depth result confirms raw MoGe scale transfer is poor. Marker calibration may address scale when a usable card is present, but it cannot fix plane/portion shape errors by itself.

### End-to-end behavior and the prior DEV weight result

The complete production pipeline emits 1–8 items per view (most often 4–6) against 10–14 labeled components; no output contains all labeled food components. The classifier can be accurate on ground-truth crops, but end-to-end it receives detector-produced regions and is therefore exposed to localization/crop errors. Every output has `ESTIMATED` verdict and uses the learned weight head, but the total is strongly biased low because unseen components contribute no mass. The pipeline’s ability to return grams is not evidence of meal completeness.

The 15.034 g per-region DEV weight-head MAE conditions on WED semantic food regions and has previous model-selection exposure. It bypasses the production proposal and item-classification stages and therefore cannot estimate full-meal error. The new end-to-end 611.35 g MAE is a different metric over meal totals; do not compare those numbers as if they measured the same prediction unit.

## Test run

Focused tests cover the new metric-depth and end-to-end report helpers, baseline evaluators, production segmenter and multi-item logic, pipeline seams, portion logic, and weight-head cache/load behavior. Command: `pytest -q tests/test_synth_depth_baseline.py tests/test_synth_e2e.py tests/test_synth_baselines.py tests/test_dish_segmenter.py tests/test_multi_item.py tests/test_pipeline_seams.py tests/test_portion.py tests/test_weight_head_cache.py tests/test_weight_head_load.py -k 'not http'` -> **69 passed, 2 deselected** in 17.28s. Ruff passed for the changed Python modules. The deselected `test_http_missing_required_field_422` and `test_http_serving_style_echo` were each run separately and both hung in this environment while waiting on the Starlette/httpx2 AnyIO TestClient portal; each was stopped after the timeout without an assertion or pipeline exception. The other focused tests pass.
