# 026 — Synthetic card-plane versus food-base-plane audit

- **id**: 026
- **branch**: `codex/iter-synthetic-card-homography-check`
- **date**: 2026-10-30
- **status**: completed; preregistered criterion not met

## Question and hypothesis

Does mapping the exact rendered food contour through a card-plane homography
introduce residual footprint-area bias because the food boundary is at the
vessel floor height rather than the card height? This is a geometry audit of
ledger 025, not a serving candidate.

## Fixed protocol

- Reuse exactly the six scenes and 18 card placements from ledger 025.
- Map each exact food-mask contour through (a) the detected marker homography,
  (b) a homography generated from renderer camera ground truth at card height,
  and (c) a homography generated from the same camera at the food's known base
  height. The latter is an oracle-only diagnostic, never available to serving
  code.
- Compare mapped areas with the analytic circular food footprint
  `π × radius_mm² / 100` cm². Also report per-scene and overall absolute area
  errors. Keep all per-position results in JSONL and stdout under
  `experiments/oracle_ablation/`.
- No weighed ArUco plates, WED DEV, or WED LOCKED. No production code,
  parameters, thresholds, model artifacts, or protected evaluation files.

## Success criterion (written before the audit harness)

Plane-height mismatch is supported as a material contributor in this
synthetic setup only if replacing the detected card-plane mapping with the
renderer-ground-truth food-base-plane mapping reduces mean absolute footprint
area error by at least 50% and brings the mean absolute area error to at most
2% in at least five of six scenes. Otherwise record that criterion as not met.
This oracle diagnostic cannot validate a deployable method or authorize a
serving change.

## Result

All 18 placements were measurable. Mean absolute analytic-footprint area error
was **1.326379%** using the detected card homography, **1.055537%** using the
renderer camera at card height, and **8.681966%** using the renderer camera at
the nominal food-base height. Food-base-plane mapping therefore worsened the
mean error by 554.56%; 0/6 scenes met the 2% per-scene threshold. The
preregistered criterion was **not met**.

This surprising result led to a source audit of `tests/synth/scene.py`: its
food support radius is computed from `P0`, the camera ray's intersection with
the table plane, before assigning the food height. A separate table-plane
projection of the six exact masks returned signed area errors from **−0.8994%
to −0.5662%**, close to the analytic footprint. This supports a renderer
coordinate inconsistency: its mask footprint is parameterized at the table
ray intersection even when the rendered food surface is elevated. The audit
does not establish how a real plate's food boundary should be projected.

Reproduction:

```bash
.venv/bin/python -m experiments.oracle_ablation.audit_card_food_plane_height
```

Raw per-position values and output are in
`experiments/oracle_ablation/audit_card_food_plane_height.jsonl` and
`experiments/oracle_ablation/audit_card_food_plane_height.stdout.txt`. The
table-plane spot-check output is in
`experiments/oracle_ablation/audit_renderer_food_mask_plane.stdout.txt`.

## Decision

**Revert the plane-height explanation for this renderer as preregistered; do
not change production or renderer code in this diagnostic.** The 025
card-position mechanism remains supported in this synthetic setup, while its
area/error figures must be interpreted alongside this renderer limitation.
