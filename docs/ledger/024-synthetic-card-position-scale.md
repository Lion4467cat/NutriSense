# 024 — Synthetic card-position scale sensitivity

- **id**: 024
- **branch**: `codex/synthetic-mask-spill-loop`
- **date**: 2026-10-30
- **author**: Codex
- **status**: preregistered

## Hypothesis

The measured card scale is a global mean-side cm/px value, while perspective
causes image scale to vary with image position and depth. Holding the rendered
food, vessel, camera, exact food mask, and metric depth fixed, moving only the
card may therefore change the measured-anchor gram estimate. The returned
card-plane homography may provide a position-specific scale estimate that
reduces this sensitivity.

## Expected effect

Use the six seeded scenes from ledger 022, each rendered with the card at three
fixed non-overlapping positions: `(0, -170)`, `(170, 15)`, and `(0, 180)` mm.
The same food truth and exact food mask are used for all three card positions
within each scene. Compare the production estimator using the renderer's
planted measured scale and the experimental estimator using the detected
card-plane homography to map the exact food-mask boundary to planar coordinates.

## Success criterion (written BEFORE coding)

The global-scale estimates exhibit at least 5% max-to-min spread relative to
their median in at least four of six scenes, and the homography-based estimates
reduce that spread to at most 2% in at least four of those same scenes. Also
report signed error against scene truth for every paired estimate. This is a
mechanism diagnostic only; it cannot authorize serving-path changes.

## Change boundary

Create an experiment-only harness and its raw JSONL/stdout under
`experiments/oracle_ablation/`. Do not modify serving code, parameters,
weights, checkpoints, tests, evaluation files, or protected files. Use only
renderer-generated synthetic scenes and the existing detected-anchor API.

## Result

Pending.
