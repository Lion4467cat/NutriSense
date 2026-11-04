# Implementation Plan: Synthetic Food Data and Model Evaluation

**Branch**: `009-synthetic-training-data` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification at `specs/009-synthetic-training-data/spec.md`

## Summary

Build a reproducible, offline synthetic-data and model-evaluation workflow around NutriSense’s current WED models. Freeze baselines first, then produce labeled scene variants with the existing renderer as geometry and mass authority. Compare the renderer, a mask-conditioned GAN, and a label/depth-conditioned diffusion candidate using the same 41-class training groups, image budget, class balance, downstream steps, and 0/25/50/75/100% synthetic ratios. Preserve the WED DEV/LOCKED boundaries and keep all generated artifacts local-only. Tune classification, segmentation, depth/geometry, weight, then end-to-end behavior.

## Technical Context

**Language/Version**: Python 3.14 (project environment is pinned through `uv`).

**Primary Dependencies**: Existing PyTorch 2.13, torchvision, Transformers 5.16, OpenCV 5, NumPy 2.5, Pillow, and current project model packages. A new generation dependency may be added only if the selected implementation requires it; record exact version and license in `pyproject.toml`/`uv.lock` and `docs/licenses.md`.

**Storage**: Source images remain in existing WED and ArUco paths. Generated images and per-sample manifests live under `datasets/processed/synthetic_food_v1/` (already git-ignored). Code, experiment protocol, aggregate reports, and decisions remain tracked.

**Testing**: Focused offline checks for deterministic rendering, manifest semantics, split lineage, label validity, and paired-scene equality; stage-specific model evaluation on WED DEV and synthetic ground truth. The one-time ArUco report is post-freeze and exploratory. Do not access WED LOCKED during iteration.

**Target Platform**: Linux GPU runtime for generation/model training; CPU remains sufficient for data preparation and offline manifest/render checks. An approved RTX 4060 Laptop GPU (8 GB VRAM) is now available to this workspace outside the sandbox; GPU runs require the explicit elevated execution path.

**Performance Goals**: No product-serving latency target is introduced. A GPU pilot records resolution, peak VRAM, throughput, training steps, generation time, and disk use; matched methods receive identical sample counts and downstream optimization budgets.

**Constraints**: No new physical data collection or external raw datasets. No generator receives WED DEV, WED LOCKED, or ArUco evaluation images. The deployed card stays DICT_4X4_50 ID 7 at 60 mm. Marker-derived scale is unavailable to the no-card path. Published density evidence is cited; otherwise density and shape are marked assumed. No depth-accuracy claim on real scenes without measured real depth.

**Scale/Scope**: 41 WED classes; 1,146 WED TRAIN views from 219 plate groups; DEV is 108 views from 21 plate groups. The existing ArUco collection has 23 frames in six meal groups, of which six groups have user-verified component masses for one final exploratory report. Initial training corpus has isolated dishes, then composed thalis; broader mass ranges are a separately tagged experiment.

## Constitution Check

- **I. Evidence Before Claims — PASS**: Keep renderer-derived labels, measured WED targets, and assumed density parameters distinct; cite each published range and report assumptions.
- **II. Reproducible Evaluation — PASS**: Freeze baselines and hashes; train generators from WED TRAIN only; tune on DEV; reserve LOCKED for one final report; keep the ArUco set out of training/tuning.
- **III. Honest Uncertainty — PASS**: Track density/shape uncertainty and invalid task labels; do not infer real depth accuracy from synthetic tests or mass results.
- **IV. Preserve Public Contracts — PASS**: This work is offline training/evaluation; no `/analyze` contract changes are planned.
- **V. Verify Proportionately — PASS WITH LIMIT**: Add focused quality checks and model-evaluation protocols; do not claim a GPU run succeeded unless run on the connected GPU runtime. Do not modify the locked evaluation code or manifest.

## Research Decisions

See [research.md](research.md) for primary-source references and alternatives. Key decisions:

1. Keep the analytic renderer/domain-randomization path as the geometry-truth and equal-budget control.
2. Compare one mask-conditioned GAN and one spatially conditioned diffusion method. The WED image/mask pairs supply training examples; renderer geometry supplies generation controls. Generic unpaired translation may be explored only as a restricted appearance-only comparator because it can alter shape.
3. Reinsert the exact rendered marker after appearance generation. Appearance models do not author marker patterns, corners, depth, masks, or mass.
4. Core experiments use local WED and renderer data. Any pretrained generator checkpoint is a separate, non-promotable research track until model provenance, license, training-data disclosure, and possible evaluation overlap are reviewed.
5. Realism/discriminator metrics and human review are diagnostic. Task validity and downstream real DEV results decide whether a method is retained.

## Project Structure

### Documentation (this feature)

```text
specs/009-synthetic-training-data/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
nutrisense_synth/
├── scene.py                 # reusable version of tests/synth scene geometry
├── manifest.py              # sample schema, stable IDs, provenance and split lineage
├── methods/                 # renderer, mask-conditioned GAN, diffusion candidate adapters
└── quality.py               # task-specific label/geometry checks
tools/
├── run_synthetic_baselines.py
├── generate_synthetic_data.py
├── audit_synthetic_manifest.py
├── train_synthetic_methods.py
├── run_synthetic_ablation.py
└── report_aruco_pilot.py
datasets/processed/synthetic_food_v1/  # local-only images, manifests, caches
experiments/synthetic_food/            # tracked protocol, configs, aggregate reports
docs/ledger/028-synthetic-food-data.md # pre-registered criteria and decision
```

**Structure Decision**: Reusable renderer and sample-validation logic belong in a top-level `nutrisense_synth/` package, not in `tests/`. Preserve the existing `tests.synth.scene` import path with a compatibility re-export. Keep generation/training/evaluation as offline `tools/` commands, not serving APIs. Store large image outputs and checkpoints in ignored derived-data locations; commit code and compact reports only.

## Architecture and Experiment Flow

1. **Baseline freeze**: Emit per-stage real WED DEV baselines before any generated candidate. Classification reports top-1 and macro F1; segmentation reports mask IoU/Dice and component coverage; weight reports item/meal MAE, bias, and plate-bootstrap intervals. The depth baseline records synthetic metric-depth metrics and real marker/scale diagnostics separately.
2. **Scene/label core**: Move the current renderer behind a reusable scene interface. Extend it with per-class appearance/material parameters, a class/portion parameter registry, multiple separated food items, vessel/background variation, and single-dish plus thali compositions. Integrate mass as the sum of scene volume × explicit density, with source and uncertainty metadata.
3. **Matched card conditions**: For each seed/configuration, render the card-present scene and the no-card scene from the same immutable scene record. Only card presence changes. Randomized camera, distance, illumination, and capture effects are sampled at the pair level. Verify the no-card code path never receives marker scale.
4. **Generation candidates**:
   - Renderer/domain randomization: deterministic texture/material, camera, lighting, vessel, and background variations while preserving labels.
   - GAN: a mask-conditioned semantic generator trained on WED TRAIN image/mask pairs; only food appearance may change, while scene boundaries and marker are restored from renderer layers.
   - Diffusion: a segmentation/depth-conditioned image-translation candidate trained or adapted only with allowed WED TRAIN/renderer assets; spatial control is approximate, so all outputs pass the same task-specific acceptance checks.
5. **Manifest and quality gate**: Store every candidate with source group, split, source hash, method/checkpoint revision, seed, scene parameters, task-valid labels, assumption/confidence fields, output hash, and QA status. Run automated label, mask-boundary, depth, marker-ID/corner, and mass-consistency checks, then stratified human review by class, portion, method, card condition, and lighting.
6. **Matched experiment matrix**: For every method, train/evaluate real-only (0%), 25%, 50%, 75%, and synthetic-only (100%) conditions at constant total training steps, class distribution, resolution, and model-training configuration. Record compute and output volume. Score on the same WED DEV groups and use grouped bootstrap intervals. Keep method-level realism and diversity metrics descriptive.
7. **Stage optimization order**: Classifier → segmenter → depth/geometry → weight head → end-to-end. Each candidate has a pre-registered target metric and non-regression gates; set numeric thresholds after baselines. Keep current deployable artifacts unchanged until a candidate passes its gate.
8. **Final evidence**: Once candidates/thresholds are fixed, run one WED LOCKED report only under the existing approval protocol. Run one separate exploratory mass report over the six manually labeled ArUco meal groups; use all 23 frames only for the predeclared final marker/scale diagnostic, never for training or tuning. Report counts and limits.

## Complexity Tracking

No constitution violations. The three generation methods are an explicit requirement and the renderer already exists; no extra application service or public API is planned.
