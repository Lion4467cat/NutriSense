# ADR 0002: Learned weight fallback and the ESTIMATED verdict

- **Status:** Accepted
- **Date:** 2026-10-10

## Context

The pipeline's grams number is only as good as its scale tier. With a
reference card in frame the anchor is measured and depth is calibrated
(~1.1% median error). Without one, the prior tier guessed a 170 mm food
diameter, an assumed 30° tilt, and fed MoGe's *uncalibrated* absolute scale —
on an out-of-domain plate this is not a small error. Measured on the WED
test split (Arora et al., ICVGIP 2025), the prior-tier path posts a per-ROI
MAE of **1,464 g** against kitchen-scale truth (median AE 917 g, bias
+1,454 g): a systematic overestimate, not noise. The prior tier's ±33%
sigma describes spread around a point estimate that was itself biased, so
intervals were centred on the wrong number.

The ICVGIP 2025 paper "What is there in an Indian Thali?" ships the Weight
Estimation Dataset (WED: 267 plates, 1,394 views, 41 dishes, per-dish grams
measured to ±1 g) and a published baseline — frozen ImageNet ResNet-50,
ROI-align over the dish mask, class-conditional gram regression — at
**14.51 g MAE** on the same test split. Their code is MIT-licensed; their
checkpoint is "Coming Soon", so we port the architecture and train it
ourselves on the public dataset.

## Decision

1. **Learned fallback, prior tier only.** When the anchor is `prior` (no
   reference card in frame) and a trained checkpoint exists
   (`data/weight_head.pt`), the portion step asks the head for grams
   (`models/weight_head.py`, `base_method: learned_weight`,
   `grams_source: learned_weight`). Any failure — missing checkpoint,
   unmapped dish, bad mask, non-positive output — silently degrades to the
   geometry path; the no-card case can never get worse than before. The
   measured/card path is untouched: a card always wins.
2. **ESTIMATED is a first-class verdict.** Every no-card plate now returns
   `ESTIMATED` instead of `BORDERLINE`: full numbers, intervals, coverage
   factors and P values are all computed and shown, but PASS/FAIL is never
   stamped. This is the honest rendering of "we did not measure this" and
   keeps the tier ladder intact: measured → scored (PASS/BORDERLINE/FAIL),
   estimated → ESTIMATED. Reasons carry `no_reference_card` with the grams
   source spelled out (learned model vs size prior).
3. **Capped until validated (graduation gate).** ESTIMATED stays
   non-scoring until Phase 5 evidence: WED test-split MAE against the
   paper's 14.51 g baseline, plus a local spot-check (≈10 plates with card
   + kitchen scale, M1 collection). If both clear the bar, graduation is a
   small, digest-re-pinning commit that lets the learned tier score.
4. **Mapping, not fine-tuning.** Training uses all 41 WED classes;
   `data/wed_dishes.yaml` maps menu dishes to WED slots at inference
   (`rice_sambar → [steamed-rice, sambar]` summed on the merged mask —
   merge behaviour validated on the WED test split in the training report;
   if the merge check ever regresses, composites keep the geometry path).
   Per-class residual sigma from the carved val split
   (`data/weight_head_sigma.yaml`) feeds the MC lognormal exactly like the
   geometry sigmas do.
5. **Dataset provenance.** WED + the two metadata JSONs are downloaded from
   the authors' project page/repository (MIT). The images live at
   `data/wed/{train,test}` but are git-ignored (citation-only dataset —
   never redistributed); the manifest, mapping, checkpoint
   and sigma assets are committed. Citation: Arora, Arun, Jawahar — "What
   is there in an Indian Thali?", ICVGIP 2025.

## Consequences

- Prior-tier plates show `ESTIMATED` everywhere (pill, History filter,
  streaks land in the neutral bucket, Dashboard's "other" segment).
- The digest rule set (`8e75c97be3e0`) does **not** move: ESTIMATED is a
  code-level short-circuit over unchanged yaml rules. Graduation will move
  it.
- `mean_h_mm` / `area_cm2` are `null` on the learned path (wire schema made
  them nullable); the frontend renders "—". No fake geometry numbers.
- The head runs only on no-card captures of WED-mapped dishes; unmapped or
  out-of-scope dishes behave exactly as before.
