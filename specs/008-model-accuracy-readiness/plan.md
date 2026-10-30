# Implementation Plan: Model Accuracy and Production Readiness

**Branch**: `008-model-accuracy-readiness` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-model-accuracy-readiness/spec.md`

## Summary

Create a reproducible path to lower food mass error and demonstrate production readiness. First strengthen the benchmark and target-domain data quality, then run source-aware training/geometry ablations, calibrate uncertainty, and validate the full API and downstream nutrition outputs. Use only currently available data until after the project review. The current 15.034 g WED DEV MAE is the baseline, not a cross-domain performance claim. FinnFoodPics is organized locally and reserved for a controlled snack/energy-density side experiment rather than being merged into WED gram labels.

## Technical Context

**Language/Version**: Python >=3.14 for backend and model/evaluation tooling; TypeScript frontend.

**Primary Dependencies**: FastAPI/AnyIO, PyTorch/Torchvision, OpenCV, DINOv2-S/14 encoder, current ROI-aligned class-conditional weight head; existing SAM2/SigLIP2/MoGe paths remain available for broader pipeline ablations.

**Storage**: Local filesystem datasets and manifests; WED/Nutrition5k remain at existing paths, public downloads and derived manifests live under `datasets/raw/` and `datasets/processed/`, checkpoints/reports remain in established `data/` locations and experiment ledger.

**Testing**: Existing pytest and project evaluation harness (`tools/run_eval.py`); grouped data/contract/integration checks to be specified in task generation. No test or training run is part of this planning change.

**Target Platform**: Current local GPU/CPU service path using FastAPI plus browser frontend; production device and deployment environment must be declared before setting latency budgets.

**Project Type**: Python inference API, model/evaluation tools, and TypeScript web frontend.

**Performance Goals**: Reduce WED DEV MAE from the recorded 15.034 g with paired plate-bootstrap evidence and pre-registered bias/subgroup guardrails; avoid a material regression on independent target-domain captures. Measure nutrition MAE and full-pipeline coverage separately. Establish p50/p95 latency/resource budgets on the intended deployment device before production claim.

**Constraints**: WED LOCKED remains unavailable for tuning; DEV is the routine tuning signal. Use only datasets and labels already available locally; no new capture, annotation, or acquisition work is assumed. Preserve API wire behavior unless explicitly revised. Respect dataset-specific access/license terms; keep raw datasets out of Git. Do not let repeated views, duplicate snack portions, or near-identical captures cross partitions.

**Scale/Scope**: Existing research prototype and local data: WED (267 plates / 16,211 ROIs), a Nutrition5k subset, ECUSTFD (2,978 image records upstream, currently downloaded locally), FinnFoodPics (72 snack identities × 10 calorie tiers; 3.9 GB across versions/archives), and local ArUco captures. No new external acquisition in this feature before review.

## Constitution Check

| Principle | Gate before implementation | Status |
|---|---|---|
| Evidence before claims | Freeze baseline; all claims cite source/ledger or independent measurements | PASS |
| Reproducible evaluation | DEV-only iteration, group bootstrap, locked-set procedure preserved | PASS |
| Honest uncertainty | Coverage/width and low-confidence behavior measured, with limits stated | PASS |
| Preserve public contracts | Keep `/analyze` and other API contracts unchanged in first implementation unless separately specified | PASS |
| Verify proportionately | Implementation tasks will use existing evaluator and focused tests; no runs in this planning phase | PASS |
| Data rights | Raw data stay ignored/local; FinnFoodPics noncommercial restrictions and dataset-specific provenance travel with derived manifests | PASS |

No constitutional violations are proposed.

## Phase 0: Research Conclusions

1. Use the recorded deployable WED DINOv2-S model as the baseline. Evaluate changes paired on identical DEV examples and resample plates/sessions, not individual views.
2. Audit current target-domain evidence: verify existing ArUco filename labels and image correspondence; score only records with clear tare/food-weight meaning. If existing records do not support a valid split, report the limitation instead of collecting more examples. The current 23-image set is exploratory QA, not a representative production test set.
3. Treat datasets according to labels they really provide. Nutrition5k supports explicit source-aware grams/nutrition/depth experiments; ECUSTFD supports controlled coin-scale mass/volume evaluation after license and records are verified; FinnFoodPics supports snack-specific calorie/energy-density checks and ordered portion analysis only. Do not pool their rows indiscriminately into one grams target.
4. Run baseline and one-source-at-a-time ablations before any joint training. A candidate must reduce WED DEV error with uncertainty and satisfy pre-registered bias, meal-total, and subgroup guardrails. External scores remain separately reported.
5. Measure all pipeline stages and downstream nutrition outputs; calibrate confidence on disjoint data, implement retry/confirmation/abstention, and benchmark the API on an explicitly named target device.

See [research.md](research.md) for source-by-source findings, [data-model.md](data-model.md) for provenance/targets/splits, and [quickstart.md](quickstart.md) for the proposed execution order.

## Phase 1: Design

### Data and training design

- Keep raw image paths immutable; create a versioned observation/target manifest with source release, license reference, sample group, original split, image/view metadata, target value/unit/meaning, and explicit loss eligibility.
- Assign splits by physical unit before augmentation: WED plate/session; Nutrition5k dish ID and official lists; ECUSTFD physical portion with top/side views together; FinnFoodPics snack identity across all calorie levels; existing ArUco dish/session groups when current labels support evaluation.
- Audit exact/near-duplicate records, missing labels, inconsistent units, calibration-marker availability, and source-specific license status before model training.
- Train only on semantically matching targets. Begin with WED-only baseline and compare WED+Nutrition5k, WED+ECUSTFD, and FinnFoodPics auxiliary task separately. Preserve source identity and use task-specific/masked losses. Any combined recipe follows only after individual transfer is validated.
- Use FinnFoodPics 2026 workbook for labels/analysis; derive portion tier only as supervision. Never expose filename or portion tier to the predictor. Report identity-held-out ordered portion/energy results separately from weighed-meal grams MAE.

### Evaluation design

- Freeze current baseline predictions, checkpoint/config/code hashes and data/split manifest before ablation.
- Report item-level and plate-level MAE, median absolute error, RMSE, mean signed bias, relative error and 95% grouped bootstrap intervals; stratify by food, portion size, session, marker status, single/multi-item and capture conditions.
- Track recognition precision/recall or item coverage, segmentation/ROI quality, mass errors for matched and full meal predictions, kcal/macronutrient errors, interval coverage/width, abstention/confirmation rate, and failure classes.
- Keep TRAIN descriptive only, DEV for iteration, separate calibration/evaluation groups for uncertainty, external datasets as independent transfer evidence, and WED LOCKED for one final report after model selection.
- Re-run benchmark after any source adapter or preprocessing change. Log every candidate and promotion decision in the existing run ledger.

### Serving and product design

- Preserve existing FastAPI schemas in the first implementation. Add internal metadata needed for traceability and confidence without removing current response fields.
- Route low-confidence, poor-quality, missing-marker, unsupported-food, or out-of-distribution cases to a clear retry/second-view/user-confirmation/cannot-verify response; do not return unsupported precision.
- Benchmark `/analyze` end-to-end p50/p95 latency, cold start, throughput/concurrency, CPU/GPU memory, upload limits, timeout/error behavior and cleanup on the intended deployment device; then set an explicit service budget.
- Trace calorie/macronutrient outputs through predicted identity, gram amount, food-composition source/version, density per 100 g, and final calculation.
- Track model/data/checkpoint versions, aggregate failure and confidence metrics, and domain drift without retaining raw user food images by default. Detailed telemetry/privacy policy is an implementation decision requiring product deployment context.

### Project Structure

```text
datasets/
├── README.md
├── registry.csv
├── finnfoodpics/README.md         # tracked provenance and use guidance
├── raw/                           # ignored source datasets
└── processed/                     # generated, versioned manifests/adapters
specs/008-model-accuracy-readiness/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
└── quickstart.md
models/                            # existing model code/checkpoint loaders
engine/                            # existing pipeline/API result assembly
tools/                             # evaluation, manifest, audit, and run tooling
tests/                             # focused data, metric, contract and failure checks
docs/ledger/                       # baseline, ablation, calibration and release evidence
```

**Structure Decision**: Extend the existing single Python model/API project. Dataset provenance belongs in `datasets/`, immutable experiment design in `specs/`, execution/evaluation in `tools/`, runtime behavior in existing `models/` and `engine/`, and measured decisions in `docs/ledger/`. Do not add a separate service or change wire contracts in the first increment.

## Complexity Tracking

No constitution violations or additional service boundaries are proposed.

## Open Decisions for Task Generation

- Choose deployment hardware and establish latency/memory budgets from a baseline run.
- Verify which existing ArUco filenames can be tied to food weights and tare values. If the current groups are insufficient for a held-out score, report marker-domain accuracy as unmeasured.
- Confirm ECUSTFD upstream usage terms before its images enter training or public reports.
- Define numeric non-inferiority margins for critical subgroups and the calibration-set size before opening candidate results.
- Decide whether the first release implements calibration/conformal intervals or another held-out residual calibration approach, based on actual sample size and operating assumptions.
