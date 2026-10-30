# 014 — Real-photo segmentation: refuse degenerate masks

- **id**: 014
- **branch**: `spec-002-integration`
- **date**: 2026-10-29
- **author**: agent (spec 002 follow-up, task 2)

## Hypothesis

The M1/M3 blocker ("SAM2 produces tiny/garbage masks on real canteen
phone photos") is not a prompt-strategy gap first: the deployed point
prompt is allowed to *keep* a mask that covers a fraction of a percent
of the frame when SAM's own IoU score is high. The existing area
invariant only rejects masks that are **too large** (`AREA_MAX`), so a
sliver passes straight through to area × height × density.

If the chosen mask is required to sit inside `[AREA_MIN, AREA_MAX]`
before it is accepted, a point prompt that lands on a sliver falls back
to the coarse centre box — which on the same frames returns a
plate-sized, high-score mask.

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| chosen `area_frac` on real captures | 0.0008 / 0.0018 on 2 of 6 | ≥ 0.005 on all 6 | no pixel GT: area + SAM score only |
| `centre_box` use | only when area > `AREA_MAX` | also when area < `AREA_MIN` | synthetic path unchanged in shape |
| shadow tests | 243 passed | 243 passed | no LOCKED read |

## Success criterion (written BEFORE coding)

On the six sampled canteen photos (`DATASET/*/`, two per class), no photo
returns a chosen mask below `AREA_MIN` (0.5 % of the frame), the
degenerate frames are served by the `centre_box` strategy instead, and
the whole pytest suite stays green.

## Change

`models/dish_segmenter.py`:

- `segment_food` now treats a point-prompt result smaller than
  `AREA_MIN` as a failed query and retries with the centre-box prompt
  (previously only `> AREA_MAX` triggered the fallback).
- The box-prompted result is validated against the same closed interval;
  a box prompt that still returns a speck (or the whole frame) raises
  `RuntimeError("SAM2 produced no usable food mask")` so the stage
  degrades honestly instead of reporting a plausible-looking portion.

Measurement tool: `tools/diag_real_segmentation.py` (new) — runs three
prompt strategies against the same checkpoint and records area, SAM IoU
score, distinct-vessel count and runtime per photo.

## Sources

- `DATASET/pepper_rasam_rice`, `DATASET/tomato_rasam_rice`,
  `DATASET/vegetable_rice` — real canteen captures, no ArUco card, no
  pixel ground truth (they were not captured under the protocol).
- `models/dish_segmenter.py` — `AREA_MIN`, `AREA_MAX`, `_select`
  fallback to `argmax(score)` when no solid candidate exists (the path
  that let a sliver win).
- `data/reports/real_segmentation_diag.json` — the six-photo run.

## Result

DEV-style diagnostic on 6 photos, `facebook/sam2.1-hiera-large`, one
GPU, no LOCKED read:

| photo | centre_point area / score | centre_box area / score | grid9_box area / vessels / score |
| --- | --- | --- | --- |
| pepper…131408 | **0.0008** / 0.950 | 0.458 / 0.689 | 0.514 / 1 / 0.849 |
| pepper…131418 | 0.117 / 0.843 | 0.319 / 0.957 | 0.548 / 3 / 0.842 |
| tomato…131456 | **0.0018** / 0.333 | 0.246 / 0.980 | 0.421 / 2 / 0.949 |
| tomato…131457 | 0.185 / 0.719 | 0.361 / 0.908 | 0.408 / 2 / 0.923 |
| vegetable…130507 | 0.365 / 0.417 | 0.357 / 0.961 | 0.369 / 1 / 0.970 |
| vegetable…130516 | 0.326 / 0.772 | 0.358 / 0.906 | 0.427 / 2 / 0.850 |

Two of six point-prompt masks were slivers, one of them with SAM IoU
0.950 — the score cannot be used to reject them, only the area
invariant can. On both, the box prompt returned a plate-sized mask at
0.689 / 0.980. `grid9_box` finds 1–3 distinct vessels per frame (the
multi-dish signal) but the engine's portion path still consumes a single
mask, so it is not wired in.

After the change, a re-run of the same 6 photos returns `centre_box` on
the two degenerate frames (0.458 and 0.246) and `centre_point` on the
rest; full suite: **243 passed** (`.venv/bin/pytest -q`), ruff clean,
pyright at baseline (209).

## Decision

- **keep** — the guard removes both degenerate masks on the sampled real
  captures without touching the synthetic prompt path, and it converts an
  unusable mask into an explicit stage failure instead of a silent
  mis-measurement.

## Follow-ups

1. **As of 2026-10-30, multi-vessel portioning is implemented** (ledger
   016, spec 003), with combo component restriction added in spec 004. It
   still needs stability measurement across card-bearing repeated views and
   per-component weighed ground truth for these canteen captures; current
   real-photo results are diagnostics, not accuracy claims. The separate
   weighed ArUco plates are EVAL-ONLY and cannot be used to develop or tune a
   candidate.
2. **No pixel GT for canteen photos.** A card-bearing capture pass would
   let this become an IoU gate instead of an area/sanity gate.
3. **Box prompt as the primary strategy?** It returns plate-sized masks
   on every sampled frame and higher scores than the point prompt on 5/6.
   Switching default needs a synthetic parity run first (the renderer's
   single-vessel scenes are what the current selection logic was tuned on).
