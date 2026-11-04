---
description: "Dependency-ordered implementation tasks for synthetic food data and evaluation"
---

# Tasks: Synthetic Food Data and Model Evaluation

**Input**: Design documents in `/specs/009-synthetic-training-data/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`

**Tests**: Focused tests are included because annotation validity, data lineage, and paired-scene equality are explicit feature requirements.

## Phase 1: Setup

**Purpose**: Establish the reusable offline package and tracked experiment protocol.

- [X] T001 Create the reusable `nutrisense_synth/` package and package exports in `nutrisense_synth/__init__.py`
- [X] T002 [P] Add the pre-registered synthetic food experiment matrix and promotion protocol in `experiments/synthetic_food/protocol.md`
- [X] T003 [P] Add the synthetic-data decision ledger entry with baseline-first and split-protection rules in `docs/ledger/028-synthetic-food-data.md`

---

## Phase 2: Foundational Contracts

**Purpose**: Define stable sample lineage, annotation, split, and method interfaces used by all stories.

- [X] T004 Define immutable source-group, annotation-bundle, sample-record, and card-pair records in `nutrisense_synth/manifest.py`
- [X] T005 [P] Define the generator method interface and method metadata contract in `nutrisense_synth/methods/base.py`
- [X] T006 [P] Define quality findings and per-task validity states in `nutrisense_synth/quality.py`
- [X] T007 Add focused contract and serialization tests for manifest records in `tests/test_synth_manifest.py`
- [X] T008 Add focused split-lineage, hash, and forbidden-source tests in `tests/test_synth_lineage.py`

**Checkpoint**: Foundation ready; all methods must emit the same manifest and quality contract.

---

## Phase 3: User Story 1 - Reproducible stage baselines (Priority: P1)

**Goal**: Freeze and report real-data baselines before any candidate synthetic corpus is selected.

**Independent Test**: Run the baseline command on WED TRAIN/DEV manifests and inspect a report with model/config/data hashes, group counts, metrics, and uncertainty; confirm it does not open LOCKED or ArUco evaluation inputs.

### Tests for User Story 1

- [X] T009 [P] [US1] Add baseline report schema and protected-split input tests in `tests/test_synth_baselines.py`

### Implementation for User Story 1

- [ ] T010 Implement baseline aggregation, group bootstrap intervals, split hash capture, and per-class serialization in `nutrisense_synth/evaluation.py`
- [ ] T011 Implement the baseline CLI for current classifier, segmenter, depth/geometry diagnostics, and weight head in `tools/run_synthetic_baselines.py`
- [X] T012 Add baseline metric definitions, existing checkpoint discovery, and known-evidence limitations to `experiments/synthetic_food/protocol.md`

---

## Phase 4: User Story 2 - Labeled synthetic food scenes (Priority: P1)

**Goal**: Produce reproducible isolated-dish and thali scenes with task-valid physical labels and provenance.

**Independent Test**: Generate a small deterministic corpus from TRAIN-only sources; reproduce a sample from recorded seed/parameters; audit labels, source lineage, group split, marker, depth, and physical mass.

### Tests for User Story 2

- [X] T013 [P] [US2] Add renderer determinism, mass-provenance, and marker/no-marker pair tests in `tests/test_synth_scene.py`
- [X] T014 [P] [US2] Add task-specific geometry and annotation validity tests in `tests/test_synth_quality.py`
- [X] T015 [P] [US2] Add generated-corpus audit tests for forbidden splits and invalid task labels in `tests/test_synth_corpus.py`

### Implementation for User Story 2

- [X] T016 Move the existing analytic scene renderer into `nutrisense_synth/scene.py` while preserving the `tests.synth.scene` compatibility import
- [X] T017 Extend scene parameters and rendering for class-level appearance, portion, vessel/background, isolated foods, and composed thalis in `nutrisense_synth/scene.py`
- [X] T018 Add cited-or-assumed density ranges, uncertainty, mass provenance, and observed WED portion-range constraints in `nutrisense_synth/parameters.py`
- [X] T019 Implement exact paired card/no-card rendering from one immutable scene record; prevent marker-scale inputs in the no-card path in `nutrisense_synth/scene.py`
- [X] T020 Implement deterministic renderer/domain-randomization generation and split-inheriting sample manifests in `nutrisense_synth/methods/renderer.py`
- [X] T021 Implement automated class, mask, depth, marker, mass, and pair-consistency checks in `nutrisense_synth/quality.py`
- [X] T022 Implement stratified review queue export and per-task accept/reject decisions in `nutrisense_synth/review.py`
- [X] T023 Implement TRAIN-only corpus generation with isolated-first scheduling and class-coverage caps in `tools/generate_synthetic_data.py`
- [X] T024 Implement manifest and artifact audit CLI for hashes, source split, task validity, and card-pair completeness in `tools/audit_synthetic_manifest.py`
- [X] T025 Add local-only generated data paths, provenance schema, and deterministic regeneration instructions to `specs/009-synthetic-training-data/quickstart.md`

---

## Phase 5: User Story 3 - Fair generation-method comparison (Priority: P1)

**Goal**: Compare renderer, GAN, and diffusion under one annotation interface and matched downstream budgets.

**Independent Test**: Run the method-matrix dry run and verify each method produces the five fixed fractions, equal sample/class budgets, diagnostic-only realism scores, and task-gate records.

### Tests for User Story 3

- [X] T026 [P] [US3] Add generator adapter contract and unsupported-label invalidation tests in `tests/test_synth_methods.py`
- [X] T027 [P] [US3] Add matched fraction, total-budget, and class-distribution tests in `tests/test_synth_ablation.py`

### Implementation for User Story 3

- [X] T028 Implement the mask-conditioned GAN adapter with renderer-backed annotation restoration and no implicit pretrained checkpoint in `nutrisense_synth/methods/gan.py`
- [X] T029 Implement the spatially conditioned diffusion adapter with explicit local checkpoint configuration and task-validity requirements in `nutrisense_synth/methods/diffusion.py`
- [ ] T030 Implement local GAN and diffusion training entry points using TRAIN/renderer inputs only in `tools/train_synthetic_methods.py`
- [X] T031 Implement fixed 0%, 25%, 50%, 75%, and 100% real/synthetic ablation scheduling with constant total training examples and class distributions in `nutrisense_synth/ablation.py`
- [ ] T032 Implement downstream stage-run orchestration and diagnostic realism/diversity reporting in `tools/run_synthetic_ablation.py`
- [X] T033 Record matched-budget method setup, checkpoint provenance requirements, and GPU-runtime instructions in `experiments/synthetic_food/protocol.md`

---

## Phase 6: User Story 4 - Governed model improvement (Priority: P1)

**Goal**: Apply stage-specific evidence and promotion gates, then produce only the authorized final reports.

**Independent Test**: Evaluate a frozen candidate matrix and confirm per-stage gates, end-to-end critical guardrails, protected split checks, honest depth reporting, and one-time six-group ArUco mass reporting.

### Tests for User Story 4

- [X] T034 [P] [US4] Add promotion-gate tests for target gain, guardrails, and no real-depth claim in `tests/test_synth_promotion.py`
- [X] T035 [P] [US4] Add ArUco report tests for six labeled groups, tare/net separation, and no training/tuning use in `tests/test_aruco_pilot_report.py`

### Implementation for User Story 4

- [X] T036 Implement stage order, post-baseline threshold registration, non-regression gates, and end-to-end critical-failure gates in `nutrisense_synth/promotion.py`
- [X] T037 Implement report serialization separating synthetic metric-depth accuracy from real marker/scale diagnostics in `nutrisense_synth/evaluation.py`
- [X] T038 Implement the post-freeze exploratory mass report using only the six manually labeled ArUco meal groups in `tools/report_aruco_pilot.py`
- [X] T039 Add final LOCKED evaluation handoff and one-time ArUco report safeguards to `experiments/synthetic_food/protocol.md`

---

## Phase 7: Polish and Cross-Cutting Concerns

**Purpose**: Complete operator documentation and preserve model and dataset governance.

- [X] T040 [P] Document every offline command, inputs, outputs, GPU requirements, and clean-room run order in `specs/009-synthetic-training-data/quickstart.md`
- [X] T041 [P] Add code and data provenance/license recording instructions for generator implementations and checkpoints in `docs/licenses.md`
- [X] T042 Review `engine/contract.py`, `tools/run_eval.py`, `docs/locked_manifest.txt`, and the final working-tree status to confirm serving contracts, the protected evaluator/manifest, and unrelated user edits remain untouched

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup tasks have no prerequisites.
- Foundational contracts depend on Setup and block all story work.
- User Story 1 and User Story 2 begin after the foundation; synthetic candidate generation in practice waits for the User Story 1 baseline freeze.
- User Story 3 depends on the shared scene, manifest, and quality contracts from User Story 2.
- User Story 4 depends on baseline, corpus, and matched ablation outputs from User Stories 1–3.
- Polish depends on the desired stories being implemented.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; must freeze baselines before candidate corpora are generated.
- **US2 (P1)**: Starts after Phase 2; it may build scene foundations in parallel with baseline tooling, but generation execution waits for baseline freeze.
- **US3 (P1)**: Requires US2 generator and annotation contracts.
- **US4 (P1)**: Requires US1–US3 reports and frozen candidate selection.

### Parallel Opportunities

- T002 and T003 can proceed in parallel.
- T005–T006 and T007–T008 can proceed in parallel after T004 as appropriate.
- US1 report schema and baseline integration work can proceed alongside US2 renderer work after the shared contracts.
- Tests in each story can be authored independently before their corresponding implementations.
- GAN and diffusion adapters (T028–T029) can proceed in parallel after the method contract and scene-label contract exist.

## Implementation Strategy

Deliver the CPU-feasible, deterministic renderer and provenance path first. Freeze available stage baselines before generating candidate corpora. Add and compare GAN and diffusion methods only behind the same method contract and quality gate. Run GPU-bound model training and ablations on the approved remote GPU runtime; do not report those experiments as complete until their outputs and hashes are available. Promote no model until the real DEV and end-to-end gates pass; reserve LOCKED and the six ArUco groups for the single final reports described above.

## Notes

- `[P]` means tasks touch independent files and have no unfinished prerequisites.
- Every task includes a concrete repository path.
- The existing local workspace has no usable NVIDIA driver; GPU-dependent tasks require the separately approved runtime.
- Generated images, caches, and checkpoints remain local derived data and must not be committed.

## Phase 8: Convergence

**Purpose**: Close work that depends on complete metric runners, the approved GPU runtime, or the final frozen-candidate stage.

- [ ] T043 Run and freeze all five real WED DEV stage baselines with model/data/split hashes, group counts, per-class metrics, and uncertainty after T010–T011 are complete per FR-001, FR-016, FR-020, and SC-001 (missing; CRITICAL)
- [ ] T044 Complete the diffusion adaptation entry point and checkpoint provenance gate on the approved GPU runtime; keep the method research-only if license, training-data disclosure, or WED-overlap review cannot be established per FR-004, FR-005, FR-010, and FR-020 (partial; HIGH)
- [ ] T045 Execute the matched 0%, 25%, 50%, 75%, and 100% matrix for renderer, GAN, and eligible diffusion across classification → segmentation → depth/geometry → weight → end-to-end; record paired DEV metrics, group uncertainty, compute, realism diagnostics, and promotion decisions per FR-004, FR-012, FR-014, FR-015, FR-016, FR-020, and SC-003–SC-006 (partial; HIGH)
- [ ] T046 Run the frozen candidate once over all 23 ArUco frames, save the group-level component predictions with frame counts and hashes, then create the one-time six-group exploratory mass report per FR-017, FR-018, and SC-007 (missing; HIGH)
- [ ] T047 After all candidate choices and thresholds are fixed, run the existing guarded WED LOCKED report once, record its access and hashes, and do not use its results for further selection per FR-006, FR-017, FR-020, and the evaluation protocol (missing; HIGH)
