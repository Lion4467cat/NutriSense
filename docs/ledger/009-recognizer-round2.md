# 009 — Recognizer round 2: spatial 16×16 pooling, MLP head, hybrid fusion

- **id**: 009
- **branch**: `spec-002-integration` (recognition line; follows ledger 008)
- **date**: 2026-10-29
- **author**: agent (Buffy / Codebuff)

## Hypothesis

Ledger 008's failed candidate pooled the frozen DINOv2-S patch grid (16×16,
384-d) down to a 7×7 mean pool → 384-d vector, then drew a linear boundary:
a coarse texture summary through a linear separator. The gallery at 0.8103
(embedding geometry per crop) beats that. Three cheap changes should flip
the result WITHOUT any new encoder pass:

1. **Spatial kernel:** ROIAlign on the full 16×16 grid with max+mean pooling
   (concats to 768-d) — keeps which parts of the ROI carry the texture.
2. **Capacity + data:** a 2-layer MLP (768→512→41, dropout 0.2) and
   feature-level horizontal-flip augmentation (the 16×16 patch map flips
   losslessly wherever the image pipeline could) — doubles the training
   draw from the existing one-aug-pass cache blob.
3. **Hybrid:** the fused decision rule rank-`mean` of the head's softmax and
   the gallery's per-class top-3-mean scores — two independent kernels
   (learned boundary vs nearest-neighbour geometry) ensembled.

Evaluation stays on the IDENTICAL held-out crops/plates and the identical
paired protocol as entry 008, against the identical gallery baseline
(0.8103) so all three gates compare like-for-like.

## Expected effect

| variant | expected after (same DEV crops) | note |
| --- | --- | --- |
| linear-7×7 (entry 008) | 0.7217 (recorded) | for continuity |
| MLP max+mean 16×16 + hflip | > 0.8103 | paired CI vs gallery |
| hybrid (MLP + gallery) | > 0.8103 | paired CI vs gallery |

## Success criterion (written BEFORE coding)

On the same 1,218 DEV-plate ROI crops (21 DEV plates, seed-42 carve), at
least one of the pre-listed candidates beats the gallery argmax baseline
(0.8103) with paired plate-bootstrap 95% CI (2,000 reps, seed 42) excluding
0 in the improving direction. If only the hybrid clears the gate, the
recorded recommendation is the hybrid; if only the MLP clears it, the
recommendation is the MLP. **No serving change in this entry either** — the
wiring entry follows with its own gate (open-set sanity: unchanged abstain
threshold semantics, synthetic-render abstain, menu-gold recognition). Tool
+ report land clean (ruff 0, pyright baseline 212, hermetic suite green).
No LOCKED read.

## Change

- `tools/eval_classifier_41way.py` — gains `--recipe {r8, mlp, both}` and
  n-aug-draw support for training items (hflip of the cached 16×16 map and
  ONE cached draw per view from ledger 008's blob), plus per-variant paired
  bootstrap Δacc reporting in the report JSON. The torch.tensor warning is
  silenced at the source (`.detach().clone()`).
- No other file touched. No serving, params, gallery, checkpoint change.

## Sources

- `docs/ledger/008-recognizer-41way.md` — held-out baseline 0.8103, failed
  linear 0.7217 CI [−0.1221, −0.0545], contamination audit 41/108.
- `models/weight_head.py` `encode()` — the 16×16 patch-grid layout the pool
  upgrade targets (DINOv2-S/14 @ 224²).
- `tools/train_weight_head.py` `prepare_features()` — cache blob layout the
  training items come from.

## Result

One clean run (report `data/reports/classifier_41way_dev.json`; n = 1,218
DEV crops, 21 plates; linear8 reproduces ledger 008 exactly — continuity
holds):

| variant | DEV-plate per-ROI accuracy | paired Δacc vs gallery [95% CI] |
| --- | --- | --- |
| gallery argmax | **0.8103** | — |
| linear8 (008 repro) | 0.7217 | −0.0885 [−0.1221, −0.0545] |
| mlp (max+mean 768-d, dropout, hflip aug) | 0.8120 | +0.0016 [−0.0277, +0.0330] |
| hybrid (MLP + gallery, softmax mean) | **0.8227** | +0.0123 [−0.0173, +0.0439] |

Gate status: **not met** — neither the MLP nor the hybrid clears the
requirement that the paired CI exclude 0 in the improving direction. Both
improve the point estimate minimally, but with 21 DEV plates the
plate-clustered CI is ~±3pp wide, so no variant is statistically
separable from the training-free gallery. The learned head has reached
parity, not superiority: the shared confusion structure (dal/curry block:
muddha-pappu↔non-spicy-dal, veg-pulao↔steamed-rice) survives all three
kernels — a limit of the per-crop RGB evidence itself, not of the head
choice. The contamination audit is unchanged (41/108 DEV views remain in
the gallery's crop pool — the gallery's 0.8103 is an UPPER bound on its
true untrained synthetic-plate accuracy).

## Decision

- **revert** — no variant met the pre-committed gate (paired CI excluding 0
  in the improving direction); the serving recognizer stays the gallery.
  The tool, report, and both entries stand as the honest record: per-photo
  41-class recognition sits at ~0.81 (gallery) with the trained head at
  parity, and further kernel work is not the accuracy lever.

## Follow-ups

- **Recognition is not the current accuracy bottleneck** — both kernels
  converge to the same confusions within visually-near classes, and the
  next real accuracy step for "any food, 41 classes or more" is the
  ingredient-compositional transfer (ticket 07b: per-ingredient grams from
  Nutrition5k), which replaces per-dish labels with a shared ingredient
  alphabet.
- If recognition ever needs a further push WITHOUT training: a per-class
  cap raise + multi-crop gallery expansion (the current 24-cap, 24-ish
  crops/class) is the cheapest gallery-side lever, then a wiring gate for
  the recorded hybrid if a later variant clears the CI parity gate.
- Plate-level decisions (multi-view majority vote) would lift per-PLATE
  accuracy but the serving API takes one photo — out of scope by design.
