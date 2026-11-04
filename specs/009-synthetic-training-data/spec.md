# Feature Specification: Synthetic Food Data and Model Evaluation

**Feature Branch**: `009-synthetic-training-data`  
**Created**: 2026-11-02  
**Status**: Draft  
**Input**: User description: Build a provenance-preserving synthetic food image corpus from WED and the existing renderer; compare procedural rendering, GAN, and diffusion approaches; use the corpus to improve the 41-class NutriSense pipeline without new physical data collection.

## User Scenarios & Testing

### User Story 1 - Reproducible stage baselines (Priority: P1)

As a model developer, I need comparable real-data baselines for classification, segmentation, geometry/depth, and mass estimation before generating candidate data, so I can tell whether synthetic data improves a model.

**Why this priority**: Without frozen baselines, a larger training set or a discriminator score could be mistaken for a real improvement.

**Independent Test**: Reproduce each deployable baseline using the fixed WED group splits and record data, model, configuration, subgroup, and metric details.

**Acceptance Scenarios**:

1. **Given** the current deployable models and WED manifests, **When** baseline evaluation runs, **Then** it records per-stage metrics on the same real WED DEV groups before any synthetic candidate is selected.
2. **Given** a baseline run, **When** its report is saved, **Then** the report identifies model/configuration revisions, data and split hashes, group counts, per-class results, and uncertainty.
3. **Given** an evaluation tier, **When** baseline evaluation runs, **Then** TRAIN is descriptive, DEV is the tuning signal, and LOCKED remains unavailable for candidate selection.

### User Story 2 - Labeled synthetic food scenes (Priority: P1)

As a model developer, I need synthetic examples for all 41 WED classes, first as isolated foods and then as composed thalis, with labels that remain valid for the tasks they supervise.

**Why this priority**: A useful synthetic corpus must expand controlled appearance and quantity variation without inventing class, geometry, or mass truth.

**Independent Test**: Generate a deterministic sample and verify its source group, class, scene parameters, annotations, split inheritance, and reproduction record.

**Acceptance Scenarios**:

1. **Given** a WED TRAIN source group and a supported WED class, **When** a synthetic scene is generated, **Then** it retains the existing class label and its source-group provenance.
2. **Given** a scene parameter set, **When** the scene is rendered again with the same recorded seed and parameters, **Then** the image and valid annotations are reproducible within documented numerical tolerance.
3. **Given** a generated scene with invalid class or task labels, **When** quality screening runs, **Then** the image is excluded from the affected task or excluded entirely.
4. **Given** a card-present scene, **When** its matched no-card scene is rendered, **Then** food, portion, camera, lighting, and capture parameters are identical; card presence is the only changed condition.

### User Story 3 - Fair generation-method comparison (Priority: P1)

As a model developer, I need renderer, GAN, and diffusion candidates compared under matched data and training conditions, so method selection reflects downstream usefulness rather than image realism alone.

**Why this priority**: Each generation method has different failure modes; equal budgets and real-data evaluation make the comparison interpretable.

**Independent Test**: Re-run the pre-registered candidate matrix and compare stage metrics on identical WED DEV groups.

**Acceptance Scenarios**:

1. **Given** a generation method, **When** a candidate corpus is prepared, **Then** the same class distribution, synthetic fractions, total example budget, and model-training procedure are used for every method.
2. **Given** a candidate training run, **When** its synthetic fraction is selected, **Then** the experiment matrix includes 0%, 25%, 50%, 75%, and 100% synthetic examples, with the same total training budget.
3. **Given** a generator discriminator or visual realism score, **When** a method is assessed, **Then** that score is diagnostic and cannot by itself satisfy a promotion criterion.
4. **Given** a task-targeted candidate, **When** it is compared with the real-only baseline, **Then** promotion requires a pre-registered improvement on its target-stage metric and no critical regression in other stages or end-to-end meal behavior.

### User Story 4 - Governed model improvement (Priority: P1)

As a project team, I need stage-specific evaluation and promotion gates that protect held-out data, so improvements in one model do not hide regressions elsewhere.

**Why this priority**: Synthetic data is useful only if it improves the real-input product while preserving honest evaluation boundaries.

**Independent Test**: Audit split lineage and review per-stage and end-to-end reports for a completed experiment matrix.

**Acceptance Scenarios**:

1. **Given** a synthetic sample derived from a WED source, **When** the training manifest is created, **Then** it inherits the source plate/session group and cannot enter a different evaluation partition.
2. **Given** a candidate model, **When** promotion is considered, **Then** it passes the target-stage gate, the non-regression guardrails, and the end-to-end critical-failure gate.
3. **Given** geometry/depth results, **When** reports are published, **Then** synthetic metric-depth accuracy and real marker/scale diagnostics are separate, and no real depth-accuracy claim is made without depth ground truth.
4. **Given** six manually labeled ArUco meal groups, **When** the final candidate is frozen, **Then** the groups are used only for one exploratory mass report and are not used for training or tuning.

## Edge Cases

- A class has too few distinct WED TRAIN groups to support the requested appearance or portion variation; synthetic output is capped and the coverage gap is reported.
- A requested mass lies outside the observed WED per-class range; the sample is tagged as a broader-range experiment and is not counted as WED-range evidence.
- Published density evidence is unavailable or does not describe a class; the value remains explicitly assumed, carries uncertainty metadata, and cannot be described as measured.
- An appearance-generation step changes food identity, object boundaries, depth, marker pose, or mass-relevant geometry; affected labels are invalidated and the sample is excluded from those tasks.
- A card-present sample is not exactly paired with its no-card counterpart; it cannot be used to attribute differences to card presence.
- Any file, crop, checkpoint, or generated derivative originates from WED DEV, WED LOCKED, or the ArUco evaluation set; it is excluded from generator training and candidate training.
- A class label is outside the initial WED 41-class taxonomy; it is excluded until independently labeled and explicitly added in a later scope.
- The six ArUco groups remain a small exploratory evaluation even when their tare and net component masses are documented.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST freeze real-data baselines for classification, segmentation, geometry/depth, and mass estimation before generating candidate training corpora.
- **FR-002**: The initial synthetic taxonomy MUST contain only the 41 WED classes; broader dish classification is out of scope.
- **FR-003**: The corpus MUST provide isolated-food scenes before composed multi-dish thali scenes.
- **FR-004**: The system MUST compare deterministic renderer, GAN, and diffusion generation approaches using the same WED TRAIN source groups and matched data/training budgets.
- **FR-005**: Generated examples MUST retain source dataset, source record, physical group, source split, generation method/version, seed, scene parameters, task labels, label provenance, and label confidence/assumption status.
- **FR-006**: Generators MUST use WED TRAIN groups only, excluding the repository’s fixed seed-42 10% plate-group DEV carve from manifest rows labeled `train`. Every synthetic derivative MUST inherit its source physical group and remain within that group’s training boundary. DEV MUST remain a tuning/evaluation set, and LOCKED MUST NOT be used as a generator or training input.
- **FR-007**: Synthetic sampling MUST balance coverage across the 41 classes where the available class evidence supports variation, without manufacturing unsupported variety.
- **FR-008**: Synthetic portion sizes MUST first match observed WED per-class ranges. Broader ranges MUST be tagged and reported separately.
- **FR-009**: Synthetic mass labels MUST be grounded in explicit class-level shape and density parameters, sourced from cited published ranges or documented assumptions. Assumptions and uncertainty MUST remain traceable; model-inferred weights MUST be stored only as experimental predictions, not as physical ground truth.
- **FR-010**: Appearance-generation methods MUST preserve renderer-backed class, mask, metric depth, marker geometry, and mass-relevant geometry to be eligible for the corresponding task. Invalid labels MUST be excluded or restricted to tasks whose labels remain valid.
- **FR-011**: Card-present scenes MUST use the deployed DICT_4X4_50 ID 7, 60 mm marker. Each card-present scene MUST have a paired no-card scene with all other scene conditions held constant. Scene pairs MAY vary across camera angle, distance, lighting, and capture conditions. The no-card path MUST receive no marker-derived scale.
- **FR-012**: Synthetic-to-real experiments MUST compare 0%, 25%, 50%, 75%, and 100% synthetic fractions with matched total training budgets, class distributions, and procedures across generation methods.
- **FR-013**: Synthetic quality screening MUST include automated task-label/geometry checks and stratified human review. Realism or discriminator scores MUST remain diagnostic and MUST NOT alone qualify data or a model for promotion.
- **FR-014**: Model improvement MUST proceed in this order: classification, segmentation, depth/geometry, weight estimation, then end-to-end pipeline evaluation.
- **FR-015**: Each candidate MUST have a pre-registered target-stage metric and guardrails. Promotion MUST require target-stage improvement and no critical regression in other stages or end-to-end behavior; numeric thresholds MUST be set after the real-data baselines are frozen.
- **FR-016**: Classification evaluation MUST report top-1 accuracy and macro F1 by class; segmentation MUST report mask IoU/Dice and item coverage; depth/geometry MUST report metric-depth accuracy on synthetic ground truth and marker/scale diagnostics on real images; mass MUST report item and meal errors in grams with grouped uncertainty.
- **FR-017**: The 23 existing ArUco captures MUST remain excluded from training and tuning. After candidate freeze, the six manually labeled meal groups MAY be used for one exploratory mass report; the report MUST preserve separate tare and net component masses and disclose the small sample size.
- **FR-018**: The system MUST NOT claim real depth accuracy from synthetic depth results, marker/scale diagnostics, or end-to-end mass changes without independent real depth ground truth.
- **FR-019**: The feature MUST NOT require new physical data collection or acquisition of new external datasets.
- **FR-020**: All evaluation runs MUST record model, data/split/checkpoint hashes, configuration, environment, class/subgroup metrics, uncertainty, and promotion decision.

### Key Entities

- **Source Group**: A physical WED plate/session or ArUco meal group, with source record, split, and identity that keeps repeated views together.
- **Synthetic Sample**: A generated image linked to its source group, generation method and version, seed, scene conditions, class, and valid task annotations.
- **Annotation Bundle**: Task-specific labels for class identity, food/item masks, metric depth, marker ID/corners/pose/size, mass, source, and confidence or assumption status.
- **Experiment Condition**: A generation method and synthetic fraction paired with a fixed model-training procedure, class distribution, and run configuration.
- **Evaluation Report**: Per-stage and end-to-end metrics, groups, split hashes, uncertainty, guardrail outcomes, and promotion decision.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A frozen baseline report exists for every stage before candidate corpus generation, with counts, group membership, per-class metrics, configuration, and reproducibility hashes.
- **SC-002**: Every synthetic sample has complete provenance and valid task annotations; no WED DEV, WED LOCKED, or ArUco evaluation source appears in generator or model-training inputs.
- **SC-003**: Each generation method is evaluated at all five synthetic fractions (0%, 25%, 50%, 75%, 100%) with equal total training budgets and class distributions.
- **SC-004**: Each retained method passes automated annotation/geometry checks and the agreed stratified human-review gate; methods failing the gate are excluded from affected tasks.
- **SC-005**: A promoted stage candidate meets its pre-registered improvement threshold on the same real WED DEV groups, with group-based uncertainty, and passes the agreed per-stage and end-to-end guardrails.
- **SC-006**: Depth reports separate synthetic metric-depth accuracy from real marker/scale diagnostics and contain no real depth-accuracy claim.
- **SC-007**: The one-time ArUco mass report includes only the six manually labeled groups, keeps tare separate from net food mass, and identifies itself as exploratory rather than a generalization estimate.
- **SC-008**: The initial deliverable covers the 41 WED classes; unsupported classes or unsupported within-class variation are not fabricated to meet a sample-count target.

## Assumptions

- The local WED TRAIN images and annotations, existing renderer, and current deployable model checkpoints remain available.
- A GPU runtime is available for generator and model experiments; the current development environment may be used for data preparation and CPU-feasible work.
- The existing six ArUco meal folders each represent one unchanged meal group. Plate/bowl measurements are tare values, and listed food values are net component totals.
- Published density ranges may inform synthetic parameters when the source and applicability are cited; otherwise parameters remain marked as assumptions.
- The project’s existing WED DEV and LOCKED protocol remains authoritative. One final WED LOCKED report may occur only after all candidates and thresholds are fixed.
- A future expansion beyond 41 classes or addition of new ArUco marker IDs requires a separate evaluation scope.
