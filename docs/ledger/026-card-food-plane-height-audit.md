# 026 — Synthetic card-plane versus food-base-plane audit

- **id**: 026
- **branch**: `codex/iter-synthetic-card-homography-check`
- **date**: 2026-10-30
- **status**: preregistered; outcome pending

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

Pending.

## Decision

Pending. No serving change is authorized by this audit.
