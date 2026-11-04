# Depth and geometry integration plan

## Scope

This phase integrates the existing metric-depth, ID 7 / 60 mm marker, food
geometry, volume, density, and uncertainty modules into a defensible real-data
path. The classifier and frozen DeepLabV3 checkpoint are inputs to this work;
they are not being retrained or changed. LOCKED, ArUco evaluation, and WED test
data are excluded. Renderer-generated scenes are the controlled source of
depth, geometry, and mass ground truth. Synthetic corpus generation remains
out of scope.

## Existing modules and interfaces

| Module | Existing role | Current caller / contract |
| --- | --- | --- |
| `models/scale_anchor.py` | Detect configured `DICT_4X4_50` ID 7; use the 60 mm marker edges for measured image scale; optionally estimate pose/tilt; otherwise return a prior tier. | `engine/pipeline.py` runs the anchor stage before segmentation. A measured result contains `cm_per_px`, interval, pose, and marker corners. |
| `engine/depth.py` | Lazy MoGe-2 inference; returns `depth_m`, model id, and predicted intrinsics when present. `calibrate_depth_scale` applies one marker-derived global depth multiplier. | Pipeline calls depth with an `fov_x` derived from fallback/EXIF camera K, then passes that same K to marker calibration. |
| `models/portion_estimator.py` | Estimate a base plane, mean food height, footprint area, volume, and mass from depth, mask, camera K, scale anchor, and configured density. Returns named relative uncertainty terms. | `engine/pipeline.py` calls this for geometry portions and serializes through its existing portion block. |
| `data/wed_dishes.yaml`, `data/params_status.yaml` | Class/component density values and their declared evidence status / uncertainty. | Portion estimator requires a density for each component and computes the effective mixture density. |
| `engine/mc.py` | Propagates the portion estimate's relative gram uncertainty into downstream intervals. | Called after portioning; it is the existing interval owner. |
| `engine/pipeline.py` | Orchestrates anchor → segmentation/classification → depth → portion → nutrition and converts stage failures to the current response contract. | Dependency injection exists for CPU and renderer tests. |

## Initial audit (before the fixes below)

### Known failure points and evidence status

1. **Depth scale is not currently integrated consistently.** MoGe returns
   intrinsics, but the serving pipeline ignores them and uses fallback/EXIF K
   for `fov_x`, card calibration, and geometry unprojection. A prior renderer
   report recorded raw MoGe depth about 9.8× renderer depth in card scenes and
   6.4× without a card, but its card-calibrated result fields are absent. The
   older ~1.1% calibration statement is therefore not supported by that report
   and needs a reproducible rerun.
2. **The 9 g chutney sensitivity artifact is not a valid absolute-mass
   estimate.** It evaluates a no-card prior-tier geometry path, whose 170 mm
   size prior and uncalibrated MoGe scale produce 1,186 g. The production
   pipeline routes mapped WED dishes without a marker to the learned weight
   head; this diagnostic must not be presented as an active production
   prediction. The correct physical behavior when scale is unavailable is to
   withhold geometry-derived absolute grams, not to tune the prior to this one
   case.
3. **Base-plane assumptions are material.** The ring path fits the food-mask
   edge; real MoGe measured-card inference is explicitly routed to
   `table_prior`, which fits an outside table band and adds an assumed vessel
   floor offset. It flags `vessel_shape_uncertain`, but still emits point
   estimates. The estimator also fills invalid depth pixels with a median when
   their fraction is at most 5%; this needs explicit validation and uncertainty
   treatment.
4. **Density is partly assumed.** Class/component density values are not all
   measured and carry status notes in configuration. Their provenance and
   uncertainty must remain attached to any geometry-based mass result.
5. **Renderer geometry tests exist, but they do not establish the whole
   MoGe → marker calibration → geometry chain.** Existing tests validate
   portions on renderer depth and exercise pipeline wiring with injected
   depth. The model-backed renderer baseline is the missing controlled gate.

## Ranked hypotheses to test

1. MoGe and geometry use mismatched intrinsics; consistent predicted
   intrinsics will improve renderer depth/geometry alignment.
2. Marker-corner depth sampling or marker detection dominates calibration
   residual; renderer-ground-truth corners will outperform image-detected
   corners.
3. Unanchored depth and the size prior explain the chutney blow-up; with no
   physical scale, geometry mass must abstain, while card-calibrated renderer
   geometry should recover plausible scale.
4. Table/vessel base assumptions and food height, rather than density, drive
   the remaining mass error; one-at-a-time renderer perturbations will separate
   those terms.
5. Footprint tilt correction or class density is a systematic secondary
   error; exact renderer masks/depth and one-variable changes will expose it.

## Implementation sequence

1. **Baseline and reproducible diagnostics:** run a CPU-only MoGe smoke/eval on
   renderer card/no-card pairs; report raw and marker-calibrated depth metrics
   by object region. Keep model weights and training processes untouched.
2. **Metric camera seam:** define and validate the K used by MoGe depth,
   marker calibration, and 3D unprojection. Reject invalid/nonphysical
   calibration instead of silently treating it as metric. Add renderer
   regressions for exact and detected marker corners.
3. **Geometry validity:** check depth coverage, base-plane fit, scale tier,
   and physical height/area/volume before returning grams. Keep ring and
   table-prior assumptions explicit; propagate their uncertainty and
   provenance. Withhold absolute geometry mass when scale or base evidence is
   insufficient.
4. **Mass provenance and uncertainty:** preserve configured density source and
   status, combine scale/area/height/base/density uncertainty without
   overstating precision, and pass the result through the existing MC interval
   owner.
5. **Pipeline integration:** pass depth and its validated intrinsics as one
   result to portioning; retain current classifier/segmenter adapters and
   frontend/backend response shape. Convert failed geometry to the existing
   stage-failure / cannot-verify path rather than manufacturing a fallback
   value.
6. **Controlled acceptance and report:** evaluate varied renderer classes,
   portions, camera poses, and card/no-card pairs with fixed seeds; report
   metric depth, marker scale, base/height, volume, mass, uncertainty coverage,
   and failure/abstention rates. Re-run CPU-only seam tests. No WED test,
   LOCKED, or ArUco evaluation data is opened.

## Initial verification

- Focused existing tests: `tests/test_portion.py`, selected
  `tests/test_scale_anchor.py`, and selected `tests/test_pipeline_seams.py`:
  **11 passed**.
- Renderer ground-truth depth passed through marker calibration: image-detected
  marker corners produce factor **1.0115**; renderer-exact corners produce
  **0.9988**. This isolates about a 1.3% relative corner-detection/sampling
  residual on the default scene, before MoGe error is introduced.
- An earlier renderer depth report exists at
  `experiments/synthetic_food/renderer_depth_baseline.json`; it is read only in
  this audit. It is incomplete for calibration because the calibrated condition
  and marker-factor summary are missing.

These are audit findings, not a promotion decision or a real-world depth
accuracy claim.

## Incremental implementation and renderer evidence

- `engine/depth.py` now exposes one conversion helper for MoGe normalized
  intrinsics to pixel-coordinate K. The pipeline uses the converted MoGe K for
  marker depth calibration and portion geometry, with its existing EXIF/fallback
  K only when MoGe intrinsics are absent or invalid. This keeps predicted depth,
  calibration, marker pose/tilt, and 3D unprojection in the same camera frame.
  Pose is re-solved from the already detected marker corners; a failed pose
  drops tilt correction but retains the independent 2D scale measurement.
- MoGe FP16 inference is enabled only on CUDA. The CPU path had failed with a
  `Half` versus `float` convolution bias mismatch; the renderer CPU smoke now
  runs. The provider also preserves invalid depth values and reports a valid
  fraction instead of filling invalid pixels silently.
- A measured marker whose scale calibration declines now fails the depth
  stage. The pipeline therefore withholds geometry grams/nutrition instead of
  returning an uncalibrated absolute estimate under a `BORDERLINE` verdict.
- With no measured marker, mapped WED dishes continue to use their existing
  learned-weight head. An unmapped dish can no longer fall through to
  size-prior geometry: the pipeline returns `cannot_verify` without grams when
  there is no physical scale source and no eligible weight model.
- Geometry portions reject more than 5% invalid food-mask depth and reject a
  fitted surface that is behind its base plane. Smaller gaps are marked
  `depth_partial` and widen depth uncertainty; they are not hidden.
- Geometry mass keeps the response schema intact and adds an `assumptions`
  entry identifying configured class/component density and the declared
  density uncertainty source.
- A renderer-backed full-pipeline seam now injects only the WED-class
  classifier, segmentation mask, and analytic depth outputs. The production
  ID 7 detector/calibration and existing pipeline portion/MC path run normally;
  a 9 g chutney scene returns 9.5 g with `depth_scale_source=card` and density
  provenance in the existing assumptions list.
- `tools/run_renderer_geometry_baseline.py` evaluates 123 transient renderer
  scenes: all 41 classes at three portions sampled from observed WED TRAIN
  ranges. It uses exact renderer masks, depth, marker scale, and per-class
  density. The completed report is
  `experiments/real_pipeline_baseline/renderer_geometry.json`.

### Renderer geometry result (exact depth and anchor)

Across 123 scenes, volume and mass mean absolute relative error were **5.20%**;
mass MAE was **5.67 g** with **+2.85 g** mean bias. Median relative error was
4.51%, p90 9.97%, maximum 18.63%. All 123 point estimates fell inside their
configured nominal 90% intervals. These intervals are notably broad (mean
relative sigma 70.4%), so this is conservative coverage on renderer data, not
evidence of calibrated real-world uncertainty. The worst class mean relative
errors were boondi 10.11%, kakarakaya fry 9.40%, chutney 8.53%, and sambar
8.48%.

The generated 9 g chutney case produced **9.29 g** (3.2% error) with exact
renderer depth and measured renderer anchor. This supports the diagnosis that
the old 1,186 g chutney result came from the unanchored size-prior / raw-depth
case, not a demonstrated density conversion defect. It does not validate
real-world chutney mass.

The one-at-a-time diagnostic is reproducible at
`experiments/real_pipeline_baseline/renderer_geometry_sensitivity.json`. On the
same generated 9 g chutney scene:

- Baseline with exact depth, card scale, and ring base: **9.44 g**. Scaling
  depth by 0.5 / 0.75 / 1.25 / 1.5 changes mass to 4.72 / 7.08 / 11.80 /
  14.16 g, confirming the expected linear height-scale dependence.
- Changing the food height profile (`kappa` 0.35 to 0.75) kept mass between
  9.17 and 9.53 g. Changing footprint radius 55–85 mm kept mass between 9.32
  and 9.57 g when masks and metric scale were exact. Density conversion also
  remained mass-consistent when the renderer regenerated the same 9 g serving
  at each density.
- With the table-plane path, a 0 mm vessel-floor offset estimated 9.82 g. The
  configured 8 mm offset and a 25 mm offset put the inferred base above the
  thin chutney surface; the geometry path now abstains (`food surface lies
  behind the fitted base plane`) rather than returning a negative-height or
  fabricated positive mass. This is a real limitation of the current table
  prior for thin layers; plate/bowl floor height must be identified or the
  estimate withheld.
- No-card size-prior scale with exact renderer metric depth estimated 12.42 g
  (38% high). Combined with MoGe's separately measured ~4.94× no-card depth
  scale ratio, this confirms that no-card geometry is unsuitable for absolute
  mass. The production mapped-WED path uses the preserved learned-weight head
  for no-card meals.

### Renderer MoGe depth result (41 classes, CPU inference)

The completed paired run has 41 class/portion groups and 82 views (each group
holds every scene variable fixed except card presence). MoGe ran with the
renderer camera FoV; calibration used MoGe-predicted K and renderer-known ID 7
corners/60 mm size. Bootstrap intervals resample the 41 paired groups.

| Condition | All-visible MAE | AbsRel (95% group-bootstrap CI) | δ<1.25 |
| --- | ---: | ---: | ---: |
| Card, raw MoGe | 3.667 m | 7.324 [6.603, 8.107] | 0.000 |
| Card, calibrated | 0.0183 m | 0.0304 [0.0283, 0.0327] | 0.9997 |
| No card, raw MoGe | 1.975 m | 3.920 [3.277, 4.570] | 0.0244 |

The card correction factor had median **0.1299** (p10 0.0847, p90 0.1819),
which removes the large raw metric scale bias in these analytic scenes. On food
pixels after calibration, MAE was 0.0262 m and AbsRel 6.50%; on table pixels,
MAE was 0.0185 m and AbsRel 2.90%. The no-card result remains several times
too large and does not support absolute geometry mass. In the current
pipeline, mapped no-card WED portions use the existing learned-weight path;
this renderer result supports keeping no-card metric geometry disabled for
absolute gram claims.

Separately, running the actual ID 7 detector on three 1400×1100 generated
views and calibrating renderer GT depth produced factors 1.0110, 1.0123, and
1.0116. That isolates a roughly 1.2% detector/corner-sampling residual; it is
not mixed into the MoGe result above, which used exact renderer corners.

The reproducible report is
`experiments/real_pipeline_baseline/renderer_metric_depth.json` (SHA-256
`cc01722c05985ecb5502d447f56f6f1f09658b570fa0d4b937b609cc9480e5e5`). It is
renderer-only validation, not real-world depth evidence.

Reproduction commands from the repository root:

```bash
.venv/bin/python tools/run_renderer_depth_baseline.py --portion-levels 1 --device cpu --out experiments/real_pipeline_baseline/renderer_metric_depth.json
.venv/bin/python tools/run_renderer_geometry_baseline.py --portion-levels 3 --out experiments/real_pipeline_baseline/renderer_geometry.json
.venv/bin/python tools/run_renderer_geometry_sensitivity.py --out experiments/real_pipeline_baseline/renderer_geometry_sensitivity.json
```

### Verification state

- Focused combined suite covering renderer geometry, portion estimation,
  multi-item aggregation, marker calibration, failure/abstention paths and
  pipeline wiring: **46 passed**.
- `.venv/bin/ruff check` and Python compile checks on modified modules: passed.
- The full repository suite was not run. No LOCKED, WED test, or ArUco
  evaluation image was read.

The next validation step is to extend renderer evaluation to detector-derived
marker corners and the table-prior base path across more poses, then report
integrated failure/abstention rates. Before any real-data promotion, the team
must review these renderer results and agree on physical acceptance gates.
