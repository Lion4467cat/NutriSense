# 024 — Synthetic card-position scale sensitivity

- **id**: 024
- **branch**: `codex/synthetic-mask-spill-loop`
- **date**: 2026-10-30
- **author**: Codex
- **status**: completed; fixed three-position criterion not assessable

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

The fixed three-position criterion was **not met**: in every scene only two
of three card positions returned a measured anchor with a homography. The
third was unavailable because the marker was out of frame or below the
existing minimum-marker-size gate. This leaves no complete three-position
spread for any scene.

The paired two-position diagnostic is nevertheless strong mechanism evidence
in this synthetic renderer. The food mask and food-pixel depth were identical
at all positions. For each scene, the two available global-scale estimates
had 54.45–79.26% max-to-min spread relative to their pair median, while the
homography-area estimates had 0.17–1.84% spread. Detected marker corners were
compared to the renderer-planted corners in the raw output; the registered
baseline used the planted card scale, and the local-area candidate used the
detected anchor homography. Homography-area totals were −2.08% to −4.55% below
truth for the 150/250 g scenes and −3.07% to −3.36% for the 450 g scenes. These
paired results are incomplete and are not a serving candidate or validated
correction.

The first exploratory harness run accidentally used detected scale for its
baseline. It was superseded and is not used in the figures above; the final
script follows the preregistered planted-scale baseline.

Reproduction command:

```bash
.venv/bin/python -m experiments.oracle_ablation.synthetic_card_position
```

Command output is in
`experiments/oracle_ablation/synthetic_card_position.stdout.txt`; per-position
measurements, detected and planted marker corners, and unavailable-anchor
reasons are in `experiments/oracle_ablation/synthetic_card_position.jsonl`.

## Decision and next step

**No serving change.** Preregister a follow-up with card positions that all
remain visible and pass the existing detector unchanged. Even a complete
synthetic replication is insufficient to promote a correction; independent
new weighed captures are required. The ArUco evaluation plates remain
permanently excluded from tuning.
