# 028 — Synthetic food corpus and stage-wise model evaluation

- **id**: 028
- **branch**: `009-synthetic-training-data`
- **date**: 2026-11-02
- **status**: protocol preregistered; baseline freeze pending

## Question

Can a renderer-backed, provenance-preserving synthetic corpus improve one or more real WED evaluation stages under matched training budgets?

## Fixed decisions

- Preserve the WED 41-class taxonomy. Train generators from WED TRAIN groups only, excluding the seed-42 10% DEV carve that shares the manifest's `train` label; DEV selects/tunes; LOCKED stays untouched until one final report.
- Exclude all 23 ArUco captures from training and tuning. Use the six user-labeled groups only for one post-freeze exploratory net-mass report.
- Generate isolated dishes before composed thalis. Balance coverage across classes only where distinct TRAIN groups support it.
- Pair card-present and no-card renders exactly; within each pair only card presence changes. Use the deployed DICT_4X4_50 ID 7, 60 mm marker.
- Renderer volume and explicitly assumed/cited class densities define synthetic physical mass. Model-inferred mass remains a separate experimental value.
- Compare renderer, WED TRAIN mask-conditioned GAN, and a provenance-reviewed spatial diffusion candidate at 0%, 25%, 50%, 75%, and 100% synthetic fractions with matched total budgets and per-class quotas.
- Tune classification → segmentation → depth/geometry → weight → end-to-end. Promote only with a target-stage gain, group uncertainty, and no critical regression.
- Human review and automated task-label checks are required; realism/discriminator scores cannot promote data or a model.

## Run gate

The current repo has no complete all-stage baseline freeze. The saved classifier report overlaps some DEV gallery sources, WED masks exist but a SAM2 IoU/Dice run has not been recorded, synthetic depth metrics have not been frozen, and end-to-end metrics still need to be gathered. The existing weight DEV report is available as a reference. The new preflight records these limits. Do not generate a candidate training corpus until all five stages are reviewed and frozen.

## Reproduction artifacts

- Protocol: `experiments/synthetic_food/protocol.md`
- Requirements and task plan: `specs/009-synthetic-training-data/`
- Local-only generated artifacts: `datasets/processed/synthetic_food_v1/`
