# Feature Specification: Model Accuracy and Production Readiness

**Feature Branch**: `008-model-accuracy-readiness`  
**Created**: 2026-10-30  
**Status**: Draft  
**Input**: Improve portion mass accuracy and make NutriSense dependable in real use, using datasets already present. Do not acquire more datasets until after the project review.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy mass benchmark (Priority: P1)

As the project team, we need a reproducible estimate of how well the current food-mass model works on unseen plates, so we can make improvements without tuning to the final evaluation data.

**Why this priority**: The current DINOv2-S WED DEV MAE is 15.034 g over 108 views from 21 plates. The `dev` tier is the deterministic 10% plate carve from WED TRAIN and is also used for epoch selection. It is development/model-selection evidence, not an independent generalization estimate; views on the same plate are correlated.

**Independent Test**: Re-run a frozen baseline and each candidate on identical grouped DEV examples; report plate-bootstrap uncertainty and preserve the WED LOCKED split for one final, non-tuning report after candidate selection. Only the untouched LOCKED result may support a held-out WED generalization claim.

**Acceptance Scenarios**:

1. **Given** the current trained checkpoint and WED manifests, **When** the baseline report is generated, **Then** it identifies model/config/data revisions, split membership, per-view and per-plate counts, MAE, median absolute error, RMSE, signed bias, and a plate-bootstrap 95% interval.
2. **Given** a candidate checkpoint, **When** it is compared to the baseline, **Then** paired plate-level differences and confidence intervals are reported on the same DEV examples, and the LOCKED split is not read for tuning.
3. **Given** a split manifest, **When** leakage checks run, **Then** views/augmentations from one physical plate or capture session cannot appear in different splits.

### User Story 2 - Use available datasets without corrupting supervision (Priority: P1)

As a model developer, I need each local dataset mapped to only the labels it truly supports, so compatible data can improve the system while unrelated targets do not pollute the grams benchmark.

**Why this priority**: Available sources differ in cuisine, capture geometry, label unit, repeated-view structure, and license. Naively concatenating them would make a larger but less meaningful training set.

**Independent Test**: Build a provenance-preserving manifest and validate each source adapter against its source metadata; compare WED-only with one-source-at-a-time experiments.

**Acceptance Scenarios**:

1. **Given** WED, Nutrition5k, ECUSTFD, FinnFoodPics, and local ArUco captures, **When** the adapter manifest is generated, **Then** every row retains source/version, source record and split-group IDs, available targets and units, capture metadata, and license provenance.
2. **Given** an unavailable target such as measured grams for a FinnFoodPics image, **When** a batch is trained, **Then** the loss mask excludes that target rather than imputing or inferring it from a filename.
3. **Given** repeated views or calorie tiers of one physical sample/food identity, **When** splitting, **Then** the group remains in a single partition.
4. **Given** candidate source-aware training, **When** evaluated, **Then** it is compared with the same WED-only baseline and is promoted only if the pre-registered DEV improvement and safety guardrails pass.

### User Story 3 - Safe estimate in real capture conditions (Priority: P1)

As a user photographing food, I need the app to distinguish a well-supported estimate from an uncertain one and recover clearly when the image or scale reference is insufficient.

**Independent Test**: Audit and evaluate only already available ArUco images whose filename labels can be verified. Use existing WED DEV and downloaded external datasets for quantitative comparisons; use deterministic malformed-image and missing-marker cases for failure handling. Do not collect new examples.

**Acceptance Scenarios**:

1. **Given** an existing ArUco image with a verifiable weight label, **When** the pipeline estimates the food, **Then** its error is reported with sample count and limitations; the small pilot set is not presented as a generalization benchmark.
2. **Given** an estimate with uncertainty metadata, **When** empirical coverage is measured on held-out calibration/evaluation data, **Then** interval coverage and width are reported by source and relevant food/portion groups.
3. **Given** low-quality, missing-marker, unsupported-food, or low-confidence inputs, **When** analyzed, **Then** the user receives an actionable request for another view/confirmation or an explicit cannot-verify result rather than false precision.
4. **Given** production-shaped requests, **When** load and failure checks run, **Then** p50/p95 latency, memory/device, upload/error rates, and concurrency behavior are recorded against an agreed deployment budget.

### User Story 4 - Nutrition estimates are traceable (Priority: P2)

As a user reviewing calories and macros, I need the app to show values derived from an identified food and portion estimate, so nutrition quality can be evaluated separately from mass accuracy.

**Independent Test**: Evaluate classification/food mapping, mass, nutrient density, and end-to-end calories/macros separately where reference labels exist.

**Acceptance Scenarios**:

1. **Given** a recognized food and portion estimate, **When** nutrients are produced, **Then** provenance includes the food-composition record/version, estimated grams, per-100-g values, and resulting kcal/macros.
2. **Given** nutrition ground truth, **When** the model is evaluated, **Then** errors are reported in kcal and grams for protein/fat/carbohydrate and are not represented by grams MAE alone.
3. **Given** an uncertain food match or portion, **When** the output is rendered, **Then** uncertainty or a user confirmation step remains visible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST freeze a reproducible baseline using the current deployable WED model and existing DEV/LOCKED rules before candidate tuning.
- **FR-002**: System MUST treat physical plate/session/item identity as the statistical grouping unit and compute confidence intervals by group resampling.
- **FR-003**: System MUST report MAE in grams alongside median absolute error, RMSE, signed bias, relative error, plate-total error, and subgroup results.
- **FR-004**: System MUST preserve the existing WED LOCKED split and access protocol; locked results MUST NOT drive model selection or thresholds.
- **FR-005**: System MUST preserve source, release, label definition/unit, original split, group ID, preprocessing, and license in every derived training/evaluation record.
- **FR-006**: System MUST train only against targets present and semantically compatible for each source; absent targets MUST be masked, not fabricated.
- **FR-007**: System MUST split repeated samples before augmentation and group WED plates/sessions, Nutrition5k dish IDs, ECUSTFD physical portion pairs, FinnFoodPics snack identities, and local capture sessions appropriately.
- **FR-008**: System MUST use the local FinnFoodPics release for controlled snack/energy-density analysis only unless additional label correspondence is independently established; filenames MUST NOT become model input features.
- **FR-009**: System MUST compare WED-only and source-aware candidates one source at a time before considering combined-source training.
- **FR-010**: System MUST audit existing ArUco files for image-to-label correspondence and evaluate only labels verifiable from already available records; it MUST NOT require new capture or annotation work, and MUST disclose the small sample size.
- **FR-011**: System MUST calibrate uncertainty on data disjoint from training and final evaluation, report interval coverage/width, and define confirmation/abstention behavior before any production confidence claim.
- **FR-012**: System MUST measure recognition, segmentation/coverage, mass, nutrition, end-to-end meal errors, latency, resource use, and failure behavior separately.
- **FR-013**: System MUST keep existing `/analyze` API wire behavior backward-compatible unless a separately reviewed contract change is specified.
- **FR-014**: System MUST record run configuration, data/split/checkpoint hashes, environment, metrics, subgroup results, and promotion decision for every candidate.
- **FR-015**: System MUST not acquire additional external datasets before the project review; planning and experiments use only currently local assets.

### Key Entities

- **Observation**: one image or view, linked to the sample/plate/session and its source.
- **Physical sample**: the weighed food item or plate whose repeated views must remain in one split.
- **Target**: a value plus unit and meaning (item grams, total grams, volume, energy, or macro mass), source and measurement method.
- **Dataset provenance**: source release, original split, access/license terms, collection context, and source record identifier.
- **Evaluation run**: immutable model/config/data/split revision, metrics and uncertainty, runtime observations, and promotion state.
- **Prediction confidence**: interval or confidence estimate calibrated on a separate calibration partition, with the action taken for low confidence.

## Success Criteria *(mandatory)*

- **SC-001**: A frozen reproducible WED baseline can be regenerated with matching predictions and metrics within documented numerical tolerance.
- **SC-002**: At least one candidate lowers WED DEV MAE versus 15.034 g with the paired plate-bootstrap 95% interval for MAE change below zero, while passing pre-registered guardrails for bias, plate-level error, and critical subgroups.
- **SC-003**: No candidate is promoted using WED LOCKED results; one final locked report is made only after candidate and thresholds are fixed.
- **SC-004**: Every locally used image has valid provenance and group IDs; source label masks and split-leakage checks pass before training.
- **SC-005**: Existing ArUco images and filename labels are audited; any scored result reports verified sample/group counts and is explicitly exploratory when the sample is too small for a reliable generalization claim.
- **SC-006**: Uncertainty coverage/width and low-confidence action are measured on data not used to train or calibrate the model.
- **SC-007**: Production readiness has an agreed latency/resource budget and evidence for p95 performance, malformed/oversized image handling, and graceful failure.
- **SC-008**: Nutrition quality is reported with kcal and macro errors where ground truth supports it, with mass and food-recognition contributions distinguishable.

## Assumptions

- Existing local datasets remain available at their documented project paths; FinnFoodPics is now organized under `datasets/raw/portion/finnfoodpics/`.
- The current WED DINOv2-S result is the production baseline and DEV is the only routine tuning signal.
- “Improve MAE” means a paired improvement on the same WED DEV groups with uncertainty and guardrails, not merely a lower in-sample score or lower error on a different dataset.
- No new data collection, annotation, or dataset acquisition is assumed. This plan uses only data already present locally.
- An eventual product release requires separate deployment, privacy, and nutrition-content review; this feature establishes measurable engineering evidence and behavior.
