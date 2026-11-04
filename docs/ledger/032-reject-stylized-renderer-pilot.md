# 032 — reject stylized renderer pilot for appearance training

- **date**: 2026-11-03
- **status**: rejected for production-model training
- **artifact**: `datasets/processed/synthetic_food_pilot_20261103/`

## Decision

Do not use the 88-image renderer pilot as appearance, classification, or
production robustness training data. Retain it only for deterministic renderer,
mask/depth/marker-label, card-pair, mass-integration, and geometry pipeline
tests.

## Reason

The pilot is procedurally valid but visually non-representative. Its food is
made from analytic radial height fields, coarse shape archetypes, low-frequency
appearance profiles, and renderer-owned vessel/background assumptions. It does
not capture real food texture, occlusion, serving boundaries, camera artifacts,
vessel variation, or measured food geometry. The class densities are partly
assumed rather than measured physical properties.

The 88 samples therefore test whether the renderer preserves its own labels;
they do not provide evidence that a model trained on them will recognize or
measure real meals. Passing automated pair and geometry checks is not a visual
realism or production-training approval.

## Revised direction

1. Use real WED images, masks, and measured class-total grams as the primary
   accuracy data.
2. Start with label-preserving image-space augmentation on real captures:
   lighting, color, blur, compression, crop/scale, and carefully bounded
   geometric transforms applied jointly to image and mask.
3. Use real-food cut-paste or masked appearance transfer only when source
   pixels and class/mask provenance remain auditable.
4. Treat any learned image generator as a separate domain-transfer experiment;
   generated images require human realism review and a real WED DEV gain before
   they can enter training.
5. Keep the analytic renderer out of appearance/classification promotion and
   retain it for depth, geometry, mass-label, and pipeline invariant tests.

## Evidence boundary

The existing frozen baseline remains unchanged. No WED LOCKED or ArUco data is
opened by this decision. No model is promoted and no production claim follows
from the pilot.