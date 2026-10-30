# Research memo: improving food-portion estimation and serving reliability

**Updated:** 2026-10-30

**Scope:** methods compatible with NutriSense's current single-RGB-photo pipeline, its 60 mm ArUco scale anchor, SAM2.1 masks, monocular depth, class-conditional weight head, and multi-item meal aggregation. This is a research plan, not an experiment result or a model recommendation supported by new benchmark measurements.

## Recommendation

The highest-value next step is **new, independently grouped, tare-corrected Indian meal data**, not another model swap. NutriSense already has a geometric estimator and a learned mass head. Its current evidence says those approaches have not yet demonstrated reliable mixed-meal performance on fresh Indian plates. Improving a leaderboard MAE without resolving the target, repeated-view leakage, and the abstention/coverage path would not establish production accuracy.

Use a paired comparison of three estimators on the *same new plates*: (1) current geometry, (2) a direct RGB mass regressor, and (3) a geometry estimate with a learned residual correction. Keep dish recognition and masks fixed in the first mass experiment. Then separately test mask quality, classification, component aggregation, calibration, and runtime. The 2024 SimpleFood45 work demonstrates a physical-reference plus 3D-template route and reports its own limited-dataset results; it supports considering that route for rigid, well-represented foods, not assuming it generalizes to biryani, rice, sambar, or mixed Indian servings. [Paper](https://arxiv.org/abs/2404.12257)

## What the existing system suggests

The current geometric estimate is approximately `footprint area × mean height above base plane × effective density`; scale is measured from the marker when possible, while prior scale is less certain. This makes the error sources separable in principle: scale/pose, mask footprint, depth and base plane, density, dish identity, and missed or duplicated items. A model trained to predict grams directly can learn appearance priors, but it cannot make a single 2D projection reveal physically unobservable height or hidden ingredients without suitable training examples.

Nutrition5k is a useful example of *capture-time* supervision: the authors describe incremental ingredient weighing and release per-ingredient mass, total mass, RGB-D, and multi-angle video. Their study also found visual portion estimates to be a weak substitute for measuring portions during data capture. Its US cafeteria domain is not an Indian validation set. [CVPR 2021 paper](https://openaccess.thecvf.com/content/CVPR2021/html/Thames_Nutrition5k_Towards_Automatic_Nutritional_Understanding_of_Generic_Food_CVPR_2021_paper.html) · [official dataset repository](https://github.com/google-research-datasets/Nutrition5k)

## Techniques worth evaluating

### 1. Make the card anchor a measured geometric input

OpenCV's ArUco documentation notes that marker pose estimation needs camera calibration parameters and that multiple markers can be combined as a board. NutriSense currently estimates scale from marker pixel size and estimates tilt using EXIF-derived or fallback camera intrinsics. A controlled calibration study should compare the current scale against (a) per-phone/per-lens camera intrinsics, (b) the existing EXIF pose path, and (c) a planar homography/rectified footprint when the food base and card occupy a sufficiently similar plane. Log marker corners, pose, reprojection residual, and local scale at the food location. [OpenCV ArUco pose tutorial](https://docs.opencv.org/4.13.0/d5/dae/tutorial_aruco_detection.html) · [OpenCV camera calibration](https://docs.opencv.org/5.0/main_modules/calib.html)

The plane condition is material: a card beside a raised plate may be at table height while food rests above the table. Therefore, a homography from the card must not be treated as exact food-plane geometry unless the physical capture setup validates that assumption. Use measured plate/floor plane and card-plane offset where possible; otherwise expose this as anchor uncertainty.

MoGe predicts an affine-invariant point map, rather than true globally scaled scene geometry. The paper's formulation supports using a known reference to resolve scale, but it does not establish that a single card corrects local depth/height bias for food on every plate. Keep metric scale calibration and base-plane/height validation as separate checks. [MoGe paper](https://arxiv.org/abs/2410.19115)

### 2. Separate footprint, height, and density errors

Instrument each portion estimate with per-item mask area, calibrated footprint in cm², base-plane method and fit residual, mean and upper-quantile food height, estimated volume, effective density, and resulting grams. On newly weighed plates, compare each observable with manual annotation or a calibrated depth/side view. This reveals whether the dominant error is area, height, or density before changing the estimator.

Run controlled checks for base-plane contamination: an empty plate with card, plate plus known-height rigid spacers, and single foods with known tare-corrected mass and independently measured volume. These are calibration fixtures, not held-out food accuracy evidence. Evaluate multiple plate shapes, rim heights, reflective steel, and card placement. The primary endpoint remains weighed food grams; inferred volume is a diagnostic because density can vary with recipe and water content.

For foods with known, stable shape templates, compare reference-scaled 3D models as a separate candidate. The SimpleFood45 paper uses a physical reference, camera/object pose, a food mask, and a matched 3D model. It explicitly frames template mismatch as a limitation; this is a plausible narrow route for egg/chapati-like rigid shapes, not a general mixed-dish solution. [CVPR Workshop paper](https://openaccess.thecvf.com/content/CVPR2024W/MTF/papers/Vinod_Food_Portion_Estimation_via_3D_Object_Scaling_CVPRW_2024_paper.pdf)

### 3. Test a data-supported hybrid mass model

Nutrition5k demonstrates direct RGB/RGB-D mass and nutrition regression, while NutriSense already has a DINOv2 feature-based class-conditional mass head. With fresh Indian weights, compare:

- current geometric mass;
- frozen visual features with a small dish-conditioned regressor;
- a residual regressor that corrects the geometric estimate using image features plus mask area, height, pose, density prior, and classifier evidence;
- a simple class/serving-size median baseline.

Keep all views of a physical meal together. Report meal-total MAE and signed bias, plus item MAE only for manually weighed components. Use median/MAE-oriented loss as a primary objective if MAE is the product target; record error by dish family, mass range, camera, and measured/prior anchor. Do not choose a model on an image-random split: the same plate photographed at several angles can otherwise appear in both train and validation. [Nutrition5k paper](https://openaccess.thecvf.com/content/CVPR2021/html/Thames_Nutrition5k_Towards_Automatic_Nutritional_Understanding_of_Generic_Food_CVPR_2021_paper.html) · [DINOv2 paper](https://arxiv.org/abs/2304.07193)

### 4. Treat mask quality and item identity as separate gates

SAM2 supports point/box/mask prompts and propagates object masks across video frames; its authors describe it as promptable image/video segmentation, not a food-weight estimator. A guided short capture can therefore be used to keep item identities/masks consistent over views, or to let a user correct a bad mask. It does not add metric scale or guarantee a correct food boundary. [SAM2 paper](https://arxiv.org/abs/2408.00714) · [official SAM2 project](https://ai.meta.com/research/sam2/)

Before any portion-model comparison, evaluate top-level food-mask containment and per-item masks against manually annotated *new development* frames. Log item-pair IoU, mask area ratio to top-level food, duplicate count, omitted food, and crop contents. For multi-item estimates, state the semantic unit: one edible component, one vessel region, or one classifier assignment. Prevent repeated views from increasing the meal total: aggregate one image's item estimates only, and aggregate across views only via a predeclared view-fusion method. Low-confidence/unknown dish crops should stay unknown or be confirmed by the user rather than receiving an unsupported nutrient mapping.

### 5. Calibrate uncertainty at the physical-meal level

NutriSense's Monte Carlo layer can propagate uncertainty, but its existing WED interval coverage is documented as under target; the nominal interval must not be described as calibrated. Split conformal regression can wrap a fixed point estimator and provide finite-sample *marginal* coverage under exchangeability. However, repeated photos/ROIs from the same plate are clustered, so ordinary row-level calibration violates the intended independent-unit design. Hierarchical conformal methods explicitly address grouped observations; their assumptions and coverage unit must be declared. [Lei et al., regression conformal prediction](https://arxiv.org/abs/1604.04173) · [Dunn et al., hierarchical conformal prediction](https://arxiv.org/abs/1809.07441)

Use a dedicated calibration cohort of plates from groups not used for fitting, and a different sealed test cohort. Calibrate total-meal intervals at the plate level; if component intervals are required, calibrate them on independently weighed component labels. Report empirical coverage and interval width with sample counts, and do not claim conditional coverage for every cuisine, device, or mass subgroup from a small sample. Distribution shift from a new school/camera is not repaired by conformal calibration alone.

## Proposed experiment and release sequence

| Order | Work | Evidence needed | Decision rule |
|---|---|---|---|
| 0 | Preregister target (`food-only plate total`, plus item grams), grouping, metrics, model candidates, and rights review. Build a manifest validator that rejects repeated-meal cross-split leakage. | No new weights; documentation and metadata checks. | Protocol is fixed before model comparison. |
| 1 | Add synthetic diagnostic coverage for card pose/scale, plane tilt, depth scale/offset, plate rim, mask spill/holes, overlap, and multi-item aggregation. Keep synthetic findings labelled as renderer evidence. | Existing synthetic renderer; no real evaluation images. | Detect arithmetic/contract regressions only; no MAE claim. |
| 2 | Profile each current GPU stage and record cold/warm latency, peak VRAM, failures, and output parity. PyTorch documents `inference_mode` as reducing autograd overhead, with the caveat that `.eval()` is separate; consider precision/compile alternatives only as benchmarked candidates. | No weighed data for profiling; quality parity requires a frozen golden set of synthetic and approved development images. | Meet stated service budget without changing numerical outputs beyond preregistered tolerances. [PyTorch inference mode](https://docs.pytorch.org/docs/stable/generated/torch.autograd.grad_mode.inference_mode.html) |
| 3 | Capture fresh Indian mixed plates with tare-corrected total and per-component grams, repeated angles, card/camera metadata, and independently grouped participants/sessions/recipes. | **Required new weighed data.** | Data QA reconciles `sum(component grams)` with food-only total and verifies scale records. |
| 4 | Compare current geometry, direct RGB head, geometry-residual head, and simple baselines on grouped train/dev. Keep masks/class labels fixed first; then evaluate mask/class errors as separate experiments. | **Required new weighed data** for model selection; manual masks/labels on a subset for perception diagnosis. | Choose only by preregistered plate-level dev metrics and coverage/abstention, not by old tests. |
| 5 | Fit uncertainty calibration and run one-time external evaluation on a sealed group/site/device cohort. | **Required new independent calibration and test plates.** | Release only if mass error, bias, interval coverage/width, recognition coverage, and item omission gates all pass. |
| 6 | Stage deployment: bounded GPU admission, model warmup/readiness, timeouts, observability, versioned artifacts, shadow traffic, rollback. | No new weights for load testing; real operating acceptance needs consented representative captures. | No false numeric output on failed/uncertain stages; meet p95/VRAM/concurrency budgets under sustained load. |

### Minimum new capture schema

For each physical meal: opaque meal/session/site IDs; participant group where consented; timestamp; device/lens and original EXIF; card size, marker ID/corners and placement; original full-resolution image or short capture burst; vessel tare; each edible component's name and net grams; total food-only grams; scale model/resolution and scale checks; recipe/preparation notes; and mask/item annotation status. Keep multiple angles of one unchanged plate under one meal ID. Partition by meal first and reserve participants, sessions, or sites for evaluation; keep a fresh holdout inaccessible during candidate selection. Nutrition5k's incremental weighing protocol is a precedent for measuring components during image capture rather than asking annotators to guess grams from pixels. [Dataset paper](https://openaccess.thecvf.com/content/CVPR2021/html/Thames_Nutrition5k_Towards_Automatic_Nutritional_Understanding_of_Generic_Food_CVPR_2021_paper.html)

## Frozen evidence boundaries

This memo authorizes no reuse of closed evidence. WED DEV, WED grouped CV, and WED LOCKED are spent for their documented purposes; the ArUco weighed plates remain EVAL-ONLY; GTMensa participant 6 and the already-used MetaFood3D, AI-ServicesBB Food Waste, and LeFood-Set tests remain closed. Do not tune thresholds, choose models, calibrate uncertainty, or fix a bug using those sets. Use their frozen reports only as historical diagnostics. New work can use synthetic renderer checks and properly permitted training/development data that were not part of any closed holdout, but every new supervised mass claim needs fresh independent weighed evidence.

## Limitations

The cited results come from different foods, capture rigs, target definitions, and splits; none establishes NutriSense accuracy on Indian canteen plates. Physical references constrain scale but do not reveal hidden food, density, or the correct base plane automatically. Monocular depth is not direct food volume. Better segmentation is useful only if it improves item inclusion/area and the component labels remain reliable. A lower MAE on one new cohort would support that cohort's prediction target and capture population only; production readiness also requires coverage, abstention behavior, nutrition provenance, device variation, latency, memory, and failure handling.

## Primary sources

- Thames et al., [Nutrition5k, CVPR 2021](https://openaccess.thecvf.com/content/CVPR2021/html/Thames_Nutrition5k_Towards_Automatic_Nutritional_Understanding_of_Generic_Food_CVPR_2021_paper.html) and [official dataset repository](https://github.com/google-research-datasets/Nutrition5k).
- Vinod et al., [Food Portion Estimation via 3D Object Scaling, CVPRW 2024](https://openaccess.thecvf.com/content/CVPR2024W/MTF/papers/Vinod_Food_Portion_Estimation_via_3D_Object_Scaling_CVPRW_2024_paper.pdf).
- Wang et al., [MoGe, arXiv:2410.19115](https://arxiv.org/abs/2410.19115).
- Ravi et al., [SAM 2, arXiv:2408.00714](https://arxiv.org/abs/2408.00714) and [Meta project page](https://ai.meta.com/research/sam2/).
- OpenCV, [ArUco detection and pose tutorial](https://docs.opencv.org/4.13.0/d5/dae/tutorial_aruco_detection.html) and [camera calibration tutorial](https://docs.opencv.org/5.0/main_modules/calib.html).
- Lei et al., [Distribution-Free Predictive Inference for Regression](https://arxiv.org/abs/1604.04173); Dunn et al., [Distribution-Free Prediction Sets for Two-Layer Hierarchical Models](https://arxiv.org/abs/1809.07441).
- Oquab et al., [DINOv2: Learning Robust Visual Features without Supervision](https://arxiv.org/abs/2304.07193).
- PyTorch, [`torch.inference_mode` reference](https://docs.pytorch.org/docs/stable/generated/torch.autograd.grad_mode.inference_mode.html).
