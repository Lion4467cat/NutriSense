# 025 — Synthetic card-position replication with detectable placements

- **id**: 025
- **branch**: `codex/iter-synthetic-card-homography-check`
- **date**: 2026-10-30
- **status**: completed; preregistered criterion met

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

All 18 fixed placements returned measured anchors and homographies. Food masks
and food-pixel depth were invariant within each scene; the maximum mean
absolute marker-corner error was **0.897921 px**. The anchor detector's
fallback intrinsics matched the renderer configuration (4.0 mm focal length,
6.17 mm sensor width).

The mechanism criterion was met:

- Planted-global-scale spread was **65.964327–70.735419%** of the per-scene
  median in all 6/6 scenes.
- Homography-area spread was **1.377700–3.273272%**; it was at most 2% in
  4/6 scenes, all of which also had global spread above 5%.
- Across all 18 positions, planted-global signed error was **−35.090787% to
  +53.044918%**; detected-global signed error was **−33.620460% to
  +57.924275%**; homography-area scaled signed error was **−4.600079% to
  −0.706182%**.

The planted and detected global-scale estimates both show the position
effect, so it is not solely a renderer-planted-scale artifact. The homography
result remains conditional on exact synthetic masks and matching camera
intrinsics. These are the same six base scenes used by prior synthetic
diagnostics, with new card placements; this is not independent scene or
real-photo validation.

Reproduction:

```bash
.venv/bin/python -m experiments.oracle_ablation.synthetic_card_position_replication
```

Raw output is in
`experiments/oracle_ablation/synthetic_card_position_replication.jsonl`,
`experiments/oracle_ablation/synthetic_card_position_replication.stdout.txt`,
and the exact-range audit is in
`experiments/oracle_ablation/synthetic_card_position_replication.audit.txt`.

## Decision

**Keep as synthetic mechanism evidence; no serving change.** Independent
weighed captures are still required before evaluating any serving candidate.
