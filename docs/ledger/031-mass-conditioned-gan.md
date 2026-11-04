# 031 — mass-conditioned appearance generator

- **date**: 2026-11-03
- **status**: implementation complete; training not yet run
- **scope**: WED TRAIN-derived appearance generation for the 41 WED classes

## Hypothesis

A semantic appearance generator conditioned on per-class measured grams can
produce controllable RGB variation for a requested meal composition and mass.
The generated image may improve robustness experiments, but the renderer or
measured WED record remains the source of task labels; the generator does not
author masks, depth, marker geometry, volume, or ground-truth mass.

## Change

The GAN condition is now versioned as
`semantic_unet_83ch_mass_conditioned_v2`:

- 42 WED semantic channels (background plus 41 classes)
- 41 log-scaled per-class gram channels

Depth is deliberately excluded from this version because WED does not provide
paired measured depth for GAN training. A depth-conditioned generator requires
a separate paired depth source and will be evaluated as a new architecture.

The WED TRAIN adapter supplies measured class-total grams. The renderer adapter
supplies renderer-owned class-total grams from the immutable scene
specification. The old 43-channel architecture is not accepted by the new
adapter.

## Data boundary

- WED TRAIN groups only, excluding the fixed DEV carve.
- WED LOCKED and ArUco captures are excluded.
- Generated labels remain renderer-owned and retain density provenance.
- WED labels are class-total meal labels, not serving-instance labels.

## Promotion criterion

No GAN checkpoint is promotable from image realism or discriminator loss. A
candidate can enter a matched synthetic-fraction experiment only after
automated label checks and stratified human review pass. It can affect serving
models only if a preregistered real WED DEV target improves with grouped
uncertainty and no critical regression in segmentation, class coverage, mass
bias, interval coverage, abstention, or end-to-end failures.

## Verification

The condition builder is deterministic, rejects invalid WED IDs and masses,
and the focused GAN/manifest/corpus test set passes. No GPU training or model
promotion has occurred under this entry.