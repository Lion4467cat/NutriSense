# 025 — Synthetic card-position replication with detectable placements

- **id**: 025
- **branch**: `codex/iter-synthetic-card-homography-check`
- **date**: 2026-10-30
- **status**: preregistered; outcome pending

## Question and hypothesis

Can the card-position sensitivity observed in ledger 024 be reproduced across
three fixed card placements when every marker is visible to the existing
detector? Does mapping the food mask through the detected card-plane
homography reduce the resulting spread?

## Fixed protocol

- Use the six renderer scenes and seeds from ledger 022, without changing the
  camera, vessel, food, density, depth, or food mask within each scene.
- Set card centers to exactly `(170, -80)`, `(170, 15)`, and `(170, 100)` mm
  in world XY, with the existing 10-degree card angle. These placements keep
  the card outside the vessel footprint while spanning near-to-far positions.
- Use the existing anchor detector and estimator unchanged. The planted
  renderer scale is the global-scale baseline; the detected homography is the
  experimental planar-area estimate.
- Record detector tier/reason, planted and detected corners, corner error,
  global-scale and homography-area grams and signed errors, and per-scene
  spreads. Preserve raw JSONL and command output in
  `experiments/oracle_ablation/`.
- If any of the 18 intended placements lacks a measured anchor and homography,
  mark the all-position criterion unassessable. Do not move cards, lower the
  existing detector gate, or substitute positions after seeing results.
- Do not read or use WED DEV, WED LOCKED, or any weighed ArUco plate. Do not
  change serving code, thresholds, configuration, model weights/checkpoints,
  evaluation files, or protected files.

## Success criterion (written before the harness)

The run is assessable only if all 18 placements are measured, return a
homography, and have mean absolute detected-versus-planted marker-corner error
at most 3 pixels. Given an assessable run, the mechanism criterion is met only
if at least four of six scenes have planted-global-scale max-to-min spread of
at least 5% of that scene's median, and at least four of those same scenes
have homography-area max-to-min spread no greater than 2% of that scene's
median. Report every signed error against renderer truth regardless of the
criterion result. No serving-path promotion follows from this synthetic
diagnostic.

## Result

Pending.

## Decision

Pending. No serving change is authorized by this diagnostic.
