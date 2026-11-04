# Integrated real-data NutriSense pipeline

## Architecture and implementation path

| Stage | Reused implementation | Integrated behavior |
| --- | --- | --- |
| Food pixels and classes | Frozen WED DeepLabV3 in `models/wed_semantic_segmenter.py` and `experiments/wed_native_segmentation/model_wed_semantic_baseline.pt` | The API lazily loads the frozen checkpoint through `models/wed_inference.py`; it does not initialize SAM2 for WED semantic food masks. |
| Region extraction | OpenCV 8-connected components | Each connected class region is retained for segmentation diagnostics. Disconnected components with the same predicted class are unioned into one ROI for mass inference because WED provides class-level gram totals, not serving IDs. |
| Food recognition | Existing SigLIP2 gallery classifier | The existing full-image classifier remains the meal-level recognition and scope signal. For class-specific WED regions, DeepLabV3's predicted 41-class label selects the WED weight-head slot; the SigLIP region candidate is retained as a cross-check in the response reason. No classifier or gallery weights are changed. |
| Marker calibration | Existing ID 7 / 60 mm ArUco implementation in `models/scale_anchor.py` | A measured marker is required before metric-depth geometry is used. Calibration failure cannot silently become a metric estimate. |
| Metric depth and geometry | Existing MoGe provider, depth-scale calibration, and `models/portion_estimator.py` | MoGe loads only after a measured marker is found. Its relative depth is calibrated from that marker before geometry or volume is computed. |
| No-marker mass | Existing `data/weight_head.pt` learned WED head | Mapped WED classes use the learned head when no marker is present. The pipeline skips MoGe in this path; uncalibrated relative depth is not passed as metric depth. Unmapped classes abstain from absolute geometry mass. |
| Uncertainty and client response | Existing pipeline wire contract, `engine/mc.py`, and frontend result components | Existing API keys, demo mode, and uncertainty presentation stay in place. The semantic model strategy and item bounding boxes flow through existing fields. |

The API uses the `pipeline_deps(image)` adapter to share one semantic forward
pass between whole-food masking and region extraction. It is lazy and has no
effect at module import. The adapter leaves the original checkpoint and all
training artifacts untouched.

## Data and label semantics

WED labels per-pixel food classes and one measured net mass per food class in a
meal image. It does not label serving instances. Therefore:

- Pixel IoU and class-aware connected-region metrics are directly measurable.
- A connected component is a provisional semantic-region candidate. Two same-
  class servings may merge; one serving may fragment across annotation gaps.
- The learned weight head is evaluated at WED's class-total granularity by
  aggregating predicted head slots by class. Its output is not a validated
  weight for each connected island.
- Plate and bowl tare are not part of WED food mass targets. Evaluation compares
  the sum of net food grams only.
- Literature/config density values and geometry-derived mass remain separately
  marked assumptions. They are used only on the marker-calibrated geometry
  route and are not substituted for learned mass when scale is absent.

## Evaluation procedure

`tools/evaluate_integrated_wed_pipeline.py` calls the production
`engine.pipeline.analyze()` on original DEV images. It loads only the
seed-42, 10% physical-group carve from WED TRAIN through
`tools.run_eval.dev_rows()`. The evaluator reads each annotation after
inference returns and records that ground truth was not passed to the model.
It writes a JSON report, Markdown summary, and representative overlays under
`experiments/real_pipeline_baseline/`.

The report measures pixel class accuracy/IoU, class-aware connected-region
precision/recall/F1, exact predicted semantic class-set coverage, per-class
mass error at WED's class-total granularity, meal total MAE/bias, uncertainty
interval coverage/width, abstentions, complete class coverage, inference time,
and peak process memory. Renderer-only metric-depth/geometry validation stays
separate from WED DEV.

The already completed renderer checks establish the calibrated route without
using protected captures: on 41 paired analytic scenes, raw MoGe depth with a
card had median predicted/target scale 8.39 and AbsRel 7.32; after ID 7 / 60 mm
scale calibration, the all-visible AbsRel was 0.0304 and MAE 0.0183 m across
82 card scenes. No-card raw MoGe had median scale 4.94 and AbsRel 3.92, which
supports the production decision to abstain from absolute depth without a
marker. With exact renderer depth, mask, and anchor, the 123-scene geometry
check had 5.67 g mass MAE, +2.85 g bias, and nominal 90% interval coverage of
100%. These are renderer-controlled results, not real-capture accuracy claims.

## Guardrails

- No classifier or segmentation training is performed.
- No synthetic corpus or generator training is performed.
- No LOCKED split, ArUco evaluation image, or WED test image is used.
- The frontend demo mode remains a clearly labeled demo; real predictions use
  the existing `/analyze` response contract.
- A no-marker result is an estimated learned-weight result, not a calibrated
  geometric measurement. A missing/invalid model or failed route abstains.

## Current known limitations

The DeepLabV3 semantic mask is strong at pixel segmentation, but it cannot
separate physical servings without instance labels. The SigLIP2 classifier and
WED weight head may disagree with semantic classes, especially for small or
visually similar foods. Current uncertainty values are model/config-derived
and need to be judged by their DEV coverage; a confidence interval is not a
scale measurement. WED images have no ArUco card, so this DEV evaluation cannot
validate marker calibration or real metric depth. The renderer provides that
controlled validation, while six weighed ArUco groups remain reserved for the
previously agreed final exploratory report after model freeze.

## Class-to-weight routing check

The first image-only DEV pass used SigLIP's per-crop label to choose the WED
weight slot after DeepLabV3 had already produced a class-specific semantic
region. That mismatch yielded 53.56 g class-total MAE, 133.81 g meal-total
MAE, and exact class coverage on only 2/108 meals. The run is preserved at
`experiments/real_pipeline_baseline/siglip_region_labels/dev_report.md`.
The corrected route uses each predicted WED semantic class for its weight-head
slot and retains SigLIP's region candidate as a cross-check. On the same DEV
carve this yielded 16.95 g class-total MAE, 80.24 g meal-total MAE, and exact
weighted class coverage on 77/108 meals. No weights were retrained between
these runs; the difference is label routing in the integrated pipeline.

