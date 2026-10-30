---
description: "Implementation tasks for model accuracy and production readiness"
---

# Tasks: Model Accuracy and Production Readiness

**Input**: Design documents from `specs/008-model-accuracy-readiness/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, and `quickstart.md`

**Organization**: Tasks are grouped by user story. Tests are included because the user requested completion of the specification and production readiness.

## Phase 1: Setup and baseline freeze

**Purpose**: Preserve the active work, verify data paths, and capture a reproducible baseline before model changes.

- [X] T001 Verify ignored raw data/cache patterns and dataset provenance guidance in `.gitignore` and `datasets/README.md`
- [X] T002 Freeze the fresh WED baseline and record checkpoint, model/evaluator code and manifest hashes in `data/reports/run_eval_diagnostics_dev_008.json`
- [X] T003 [P] Record the exact current API schemas and deployment/config assumptions in `specs/008-model-accuracy-readiness/quickstart.md`

---

## Phase 2: Foundational data and evaluation safeguards

**Purpose**: Establish reusable provenance, grouped split and report contracts before model/data experiments.

- [X] T004 Implement dataset observation/target manifest validation and provenance checks in `tools/audit_dataset_manifest.py`
- [X] T005 [P] Add grouped split leakage checks for sample-group, plate/session, duplicate image paths and optional exact image hashes in `tools/audit_dataset_manifest.py`
- [X] T006 Add immutable run metadata and checkpoint/data/code hash capture through `tools/log_run.py` and `tools/eval_weight_diagnostics.py`; keep the pinned `tools/run_eval.py` unchanged
- [X] T007 Add regression coverage for manifest validation and group leakage in `tests/test_dataset_audit.py` and source manifest semantics in `tests/test_dataset_manifests.py`

---

## Phase 3: User Story 1 - Trustworthy mass benchmark (Priority: P1)

**Goal**: Measure WED mass errors reproducibly by plate and prevent model-selection results from being described as independent generalization.

**Independent Test**: Reproduce baseline metrics on the exact plate carve, compare a frozen candidate with paired plate bootstrap and verify all report metadata and split isolation. Keep LOCKED unopened until final model and thresholds are frozen.

- [X] T008 Add median absolute error, RMSE, signed bias and target-size/food subgroup metrics in the DEV-only sidecar `tools/eval_weight_diagnostics.py` (keeps pinned evaluator unchanged)
- [X] T009 Add plate-total and meal-total reporting with plate-cluster bootstrap intervals in `tools/eval_weight_diagnostics.py`
- [X] T010 Implement and run five-fold grouped outer cross-validation over WED TRAIN plates, excluding the fixed DEV carve from all fold train/selection data; report is `data/reports/cv_weight_head_s42_k5.json`
- [X] T011 [P] Add regression tests for metrics, plate aggregation and grouped bootstrap in `tests/test_eval_metrics.py`
- [X] T012 Run and record baseline and candidate comparisons; record source-ineligible/no-fusion decisions in ledgers 017–020 and `data/reports/`
- [X] T013 Freeze the retained baseline/configuration and perform the single final WED LOCKED report in `data/reports/run_eval_locked_final_008.json` and `docs/locked_access_log.txt`
- [X] T035 Preregister and compare one AdamW regularization candidate against baseline on identical outer TRAIN plates with paired plate bootstrap and class/plate-total/bias guardrails; reject it when the boondi guardrail fails (`docs/ledger/021-wed-weight-decay-cv.md`)

---

## Phase 4: User Story 2 - Use available datasets without corrupting supervision (Priority: P1)

**Goal**: Use only label-compatible source data, preserve source/split/license provenance, and test each data source independently before any fusion.

**Independent Test**: Build and audit manifests for local data; verify group uniqueness across splits and target masks/units; compare each eligible source separately against the same WED development baseline.

- [X] T014 Build a versioned Nutrition5k observation/target manifest with dish-ID grouping and an explicit nonofficial hash split in `tools/build_nutrition5k_manifest.py`
- [X] T015 [P] Build an ECUSTFD manifest grouping paired views by physical portion and marking absent scale labels ineligible for mass training in `tools/build_ecustfd_manifest.py`
- [X] T016 [P] Build an audit manifest for available ArUco image/weight correspondence without inferring missing labels in `tools/audit_aruco_dataset.py`
- [X] T017 Validate FinnFoodPics tier labels, missing workbook identities, snack-identity splits and noncommercial provenance in `tools/build_finnfoodpics_manifest.py`
- [X] T018 Reuse the existing source-specific missing-label mask in `tools/train_ingredient_head.py`; record why no multi-source mass trainer is valid while no other source has WED-compatible verified grams
- [X] T019 Run eligible source ablations and record decisions: Nutrition5k is a distinct ingredient task and its transfer gate failed (ledger 012); ECUSTFD, FinnFoodPics and ArUco have no eligible WED grams targets locally (ledger 020)
- [X] T020 Add tests for source adapters, missing-label semantics, units and group isolation in `tests/test_dataset_manifests.py`

---

## Phase 5: User Story 3 - Safe estimate in real capture conditions (Priority: P1)

**Goal**: Surface uncertainty and recover safely from poor-quality, unsupported or unscaled captures while measuring operational behavior.

**Independent Test**: Exercise existing labeled ArUco samples as exploratory evidence; exercise malformed, oversized, missing-marker and low-confidence cases; measure endpoint latency, memory and failure behavior on the available target device.

- [X] T021 Audit current ArUco filenames and image correspondence in `data/reports/aruco_audit.json`; after user confirmation, score six food-only plate totals as an EVAL-ONLY pilot in `experiments/oracle_ablation/REPORT.md` (never for tuning or candidate selection)
- [X] T022 Reuse group-disjoint leave-one-plate-out uncertainty calibration/reporting in `tools/calibrate_intervals.py`; retain the existing no-apply decision because coverage and width gates fail
- [X] T023 Preserve existing confidence/quality action metadata, retry/confirmation/cannot-verify behavior without breaking `/analyze` fields
- [X] T024 Cover malformed upload, size limit, marker fallback and unsupported/low-confidence behavior in `tests/test_api.py` and `tests/test_scale_anchor.py`
- [X] T025 Benchmark `/analyze` latency, server RSS, GPU-memory delta and response/failure counts on the local RTX 4060 in `tools/benchmark_api.py`; existing API test covers single-process inference serialization. Multi-worker/sustained load remains out of scope for this local run.
- [ ] T026 Define deployment-specific latency/resource budgets and record measured results/limitations in `docs/production-readiness.md` (open: intended deployment hardware and service SLO have not been specified; local RTX 4060 measurements and limitations are recorded)

---

## Phase 6: User Story 4 - Trace nutrition estimates (Priority: P2)

**Goal**: Preserve a traceable food-composition calculation and report nutrition errors separately from mass error.

**Independent Test**: For supported ground-truth records, recompute kcal/macros from the recorded food mapping, mass and per-100-g composition, then report food mapping, mass and nutrition error separately.

- [X] T027 Add additive nutrition composition source/version and gram-to-nutrient calculation trace to `engine/` response assembly while preserving `/analyze` compatibility
- [X] T028 Report held-out Nutrition5k kcal/protein/carbohydrate/fat errors in `data/reports/nutrition5k_test_nutrients.json`; separate the unusable all-slot candidate output from its non-deployable oracle-present diagnostic because no validated macro-capable serving artifact exists
- [X] T029 Add tests for nutrient calculation provenance, unit handling and backward-compatible API fields in `tests/test_nutrition_trace.py`
- [X] T030 Show existing uncertainty/recovery state and new nutrition provenance in the frontend estimate flow

---

## Phase 7: Polish and cross-cutting validation

**Purpose**: Verify the full spec, license boundaries, failure behavior and documentation without overstating evidence.

- [X] T031 [P] Document dataset version, source license, target semantics and no-fusion decisions in `datasets/README.md` and `datasets/registry.csv`
- [X] T032 Update the evaluation protocol and user-facing limitations in `docs/eval_protocol.md`, `docs/production-readiness.md` and `README.md`
- [X] T033 Run full backend and frontend suites, API contract checks, dataset audits and quickstart commands; record exact results in `docs/production-readiness.md`
- [X] T034 Confirm generated reports exclude raw licensed datasets, private image paths and ignored model caches using `git status` and repository ignore rules

---

## Dependencies and execution order

- Setup precedes all implementation. T004-T007 establish foundational audit/report behavior.
- US1 precedes the source ablations because every source candidate requires a stable grouped comparison. T013 is final-only and must wait until model/threshold selection is complete.
- US2 can begin manifest adapters after the foundation; actual ablations depend on US1 evaluation infrastructure.
- US3 depends on baseline evidence and available-data audits; calibration depends on a disjoint partition, not the tuning carve or final LOCKED set.
- US4 can proceed after current nutrition-path inspection; its evaluation depends on compatible source labels.
- Polish follows all relevant stories. LOCKED evaluation is a one-time report after freeze and is never a tuning task.

## Parallel opportunities

- T005 and T006 can proceed independently after T004 contracts are agreed.
- T014, T015 and T016 use separate adapters and can proceed independently.
- T021 and T027 can proceed independently after the API contract is recorded.
- Documentation tasks T031 and T032 can proceed independently after data decisions are stable.

## Implementation strategy

Complete foundation and User Story 1 first. Use grouped TRAIN cross-validation for robust experiment selection; treat DEV comparisons as development evidence only. Do not read LOCKED until a candidate and thresholds are frozen. Then complete each source adapter and one-source ablation, implement safe runtime behavior, trace nutrition calculations, and finish with focused tests and deployment measurements. Do not claim SC-002 if no candidate passes its pre-registered paired improvement and guardrails.
