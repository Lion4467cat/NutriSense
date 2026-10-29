# 008 — Trained 41-way recognizer head vs the SigLIP gallery argmax (held-out DEV)

- **id**: 008
- **branch**: `spec-002-integration` (recognition line; ticket 02 follow-up + ticket 07b template)
- **date**: 2026-10-29
- **author**: agent (Buffy / Codebuff)

## Hypothesis

The deployable recognizer is a training-free nearest-neighbour gallery
(SigLIP2 embeddings, top-3-mean per class). Its recorded LOO accuracy is
**0.7803** at crop granularity (ledger 003) — and it is *optimistic as a
deployment estimate* twice over: (1) LOO shares sibling crops from the same
view/plate with the query, and (2) `tools.build_gallery.scan_wed_crops` draws
from ALL `split == "train"` manifest rows, which contains the DEV plate carve
(seed 42) — so DEV plates have crops inside the gallery.

A trained linear head over the FROZEN DINOv2-S ROI features (the same encoder
the weight head uses) should beat it on fine-grained, texture-dominant food
classes — the LOO misses concentrate exactly there (Banana→curd,
Muskmelon→muddha-pappu, Bottle-gourd-curry→non-spicy-curry) — because it
learns a decision boundary instead of comparing to crops. The experiment is
nearly free: feature-cache blob `wed-dinov2-strong-ea6900cebc7c.pt` already
holds per-view 7×7 features + ROI boxes + class ids for every train-manifest
row (augmented) and val (clean), so training touches head-level parameters
only, never the encoder.

## Expected effect

| metric | baseline (gallery) | expected after | note |
| --- | --- | --- | --- |
| DEV-plate per-ROI closed-set accuracy | measured this entry first (honest held-out number, class granularity) | beats it | paired plate-bootstrap 95% CI |

## Success criterion (written BEFORE coding)

On DEV-plate ROI crops (the 21 DEV plates' per-ROI ground truths, WED-class
granularity, DEV carve seed 42 identical to `tools/run_eval.py`), the trained
41-way DINOv2-linear head's closed-set accuracy exceeds the SigLIP-gallery
argmax accuracy computed on the SAME held-out crops, with a paired
plate-bootstrap 95% CI (2,000 reps, seed 42) excluding 0 in the improving
direction. The comparison tool + report land in the repo and stay clean
(ruff 0 findings, pyright at baseline 212, hermetic suite green). **No
serving change in this entry** — `models/food_classifier.py`, the gallery,
and `params_status.yaml` are untouched; wiring a kept head into the serving
argmax is its own pre-registered entry after this decision. No LOCKED read
anywhere.

If the gallery baseline is itself measured to be *over 0.95* on honest
held-out crops (the contamination hypothesis wrong), the criterion still
applies literally — beat that number or revert nothing but the timeline.

## Change

- `tools/eval_classifier_41way.py` (new) — the whole experiment:
  1. **Held-out eval set:** DEV-plate views via the seed-42 plate carve
     (same arithmetic as `tools/run_eval.dev_rows`); per-ROI mask-bbox crops.
  2. **Baseline:** SigLIP2 embeddings of the crops scored against
     `data/gallery.npz` WED-class entries; argmax at WED-class granularity
     (gallery labels include all 41 class names).
  3. **Candidate:** ROIAlign mean-pool of the cached DINOv2-S 7×7 features
     per crop → linear 41-way classifier (seed 42, SmoothCrossEntropy,
     class-balanced sampling; a small LR sweep over DEC-val accuracy), then
     final per-ROI accuracy on the same held-out crops.
  4. **Report:** overall + per-class accuracy both methods, top confusion
     pairs, paired plate-bootstrap Δaccuracy CI (2,000 reps, seed 42), the
     eval-plate crop/known-frequency caveats — written to
     `data/reports/classifier_41way_dev.json`; figures quoted here.
- No changes to serving models, params, eval-lock code, or the checkpoint.

## Sources

- `docs/ledger/003-serve-all-41-classes.md` — gallery LOO 0.7803, threshold
  0.80, gallery build details (incl. the all-train-rows crop pool).
- `tools/run_eval.py` `dev_rows` / `tools/train_weight_head.py`
  `prepare_features` — the DEV carve and the cache blob layout this tool
  reuses (arithmetic must match exactly).
- `docs/research/general-indian-dish-method.md` §4a — the same
  frozen-feature discipline this head rehearses for the 07b ingredient
  teacher; a kept linear head here is the template.
- Tencent/DINOv2 vs CLIP-features fine-grained gap: the weight head already
  chose DINOv2-S for grams (ledger 002) — same-family evidence here.

## Result

The experiment ran end-to-end in one pass (feature pool from the existing
strong-recipe cache blob, SigLIP embeds of all 1,218 DEV ROI crops, 6-point
(lr × wd) sweep selected on a 10% train-plate carve; 400 epochs full batch).
Report: `data/reports/classifier_41way_dev.json` (n_crops 1,218, 21 DEV
plates).

| method | DEV-plate per-ROI closed-set accuracy |
| --- | --- |
| gallery argmax (41-class granularity) | **0.8103** |
| trained linear head (DINOv2 ROI, 384-d) | 0.7217 |
| paired Δacc (cand − base) | **−0.0885 [−0.1221, −0.0545]** (2,000 reps, seed 42) — CI excludes 0 in the WORSENING direction |

Honest-baseline findings beyond the gate number:

- The contamination hypothesis was directionally right: **41 of 108** DEV
  views are gallery crop sources (`gallery.npz` `sources`), yet the gallery
  still scores 0.8103 on crops of those very plates.
- Top confusions are the same visually-near block for both methods:
  muddha-pappu→non-spicy-dal (15), veg-pulao→steamed-rice (11),
  masoor-dal→sambar (10), phulka→papad (10) — i.e. the dal/curry/flatbread
  block shares low-level texture statistics.
- The failure is diagnosable: the candidate pooled **7×7 features over a
  16×16 patch grid with a mean pool** into a 384-d vector — a coarse global
  texture summary thrown at a linear boundary. The gallery's per-embedding
  geometry is doing the discrimination better than that summary.

## Decision

- **revert** — the pre-committed gate required the trained head to beat the
  gallery argmax with the paired CI excluding 0 in the improving direction;
  it lost by −8.9pp with the CI excluding 0 in the worsening direction, so
  no serving change is made. The tool (`tools/eval_classifier_41way.py`),
  the report, and this entry stand as the honest held-out baseline record
  (`0.8103`) that every stronger recognizer must beat.

## Follow-ups

- Next-lever protocol (new pre-registered entry, 009): keep the same held-out
  crops and plates — (a) spatial pooling from the FULL 16×16 grid (ROIAlign
  max+mean concat, C≈768), (b) a 2-layer MLP (dropout) instead of linear,
  (c) feature-level horizontal-flip augmentation (the 16×16 map flips
  h-losslessly — doubles data without an encoder pass), (d) optionally a
  rank-average hybrid of head logits + gallery scores. Must beat 0.8103
  with the same paired protocol.
- If no learned head beats the gallery, the serving answer is "the gallery
  is the recognizer" — then accuracy gains must come from gallery expansion
  (multi-crop, per-class cap raised) or embedding upgrades, not training.