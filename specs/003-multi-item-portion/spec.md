# Spec 003: Multi-item portion path (P0)

- **Status:** implemented; mechanism retained, field accuracy pending
- **Date:** 2026-10-29
- **Source:** real-photo e2e report 2026-10-29 (docs/reports/real-photo-e2e-2026-10-29.md),
  ledger 014 follow-up 1, ledger 015 follow-ups. P0 of the vision-system improvement
  roadmap agreed in session.
- **Companion tasks:** this directory, per repo spec-kit convention

## Problem Statement

The deployed contract is **one mask = one serving = one meal**. Real canteen
meals are multi-item: rice+rasam, biryani+eggs. Measured consequences already
on record:

1. `grid9_box` finds 1–3 distinct vessels per real frame (ledger 014) but the
   portion path consumes a single mask, so a rice+rasam plate is measured as
   one blob of one dish.
2. The verdict judges the captured dish against a whole-meal standard, so a
   single 300 g rice+sambar plate FAILs a 450 kcal band minimum it was never
   meant to satisfy alone (e2e report, all six frames FAIL).
3. Recognition confusion (biryani ↔ vegetable rice) is partly a context
   problem: per-item crops classified independently remove plate-level
   ambiguity that a single full-frame classification cannot resolve
   (ledger 009: per-crop RGB evidence is the limit).

## Solution

Generalize the contract from one serving to **a list of servings**:

- `segment_items()` (models/dish_segmenter.py): 3x3 point grid + coarse box
  prompts against the same SAM2 checkpoint, masks deduped by IoU ≥ 0.70,
  area-gated to [AREA_MIN, AREA_MAX], capped at 4 items, largest first.
  `segment_food()` is **not** changed — synthetic parity is preserved.
- Pipeline: the existing single-mask segment + full-frame classify run first,
  unchanged. Multi-item detection then runs; when it finds **≥ 2 distinct
  vessels**, the multi-item path replaces the single-serving tail:
  - per item: bbox crop (10% padding) → `classify_dish(crop)` — the gallery
    was built from ROI crops, so crops are in-distribution;
  - per item portion: identical rules to the single path (prior tier +
    WED-mapped → learned head on the item mask; measured tier → geometry on
    the item mask; real-MoGe measured tier keeps the ledger-015 table_prior
    base). Depth is computed once per frame and reused.
  - aggregation: per-item MC sample arrays are summed elementwise
    (independent seeds per item; within-item correlations preserved) and the
    summaries recomputed — no change to engine/mc.py's sampling math.
  - compliance verdict is judged on the **aggregate meal**, which is the
    semantically correct scope for the band minima.
- Wire: one additive key `items` (list of per-item blocks: dish,
  classification, portion). Top-level `dish`/`portion`/`nutrition` become
  the aggregate. Single-vessel frames return a one-element `items` list
  mirroring the top-level blocks. `path_used` gains one closed-vocabulary
  value `multi_item`. WIRE_KEYS 18 → 19; TS contract regenerated.
- Items whose crop classification abstains are reported with
  `classification: null`, excluded from the aggregate, and surfaced via a
  reason — never silently measured as a guessed dish. If **every** item
  fails to classify, the pipeline falls back to the existing single-serving
  flow (today's behaviour, byte-identical).

## Decisions

1. **Additive contract, not a breaking one** (constitution IV): existing
   consumers keep reading top-level blocks; `items` is new information.
2. **Aggregate verdict scope**: the band minima are per-meal; a multi-item
   capture IS the meal. Verdict on the sum is the honest semantics.
3. **Independent per-item MC seeds**: cross-item shared terms (anchor, pose)
   are already correlated inside one item's sigma model; summing independent
   per-item samples is no worse than today's single-item treatment and keeps
   mc.py untouched.
4. **Item cap of 4**: grid9 on a thali can return 3 vessels; 4 gives headroom
   without letting prompt noise explode runtime (each item costs one
   classify + one portion).
5. **No LOCKED read; no accuracy claim.** There is no pixel GT and no
   per-component weighed GT for multi-item canteen photos. This spec delivers
   the mechanism; the accuracy gate waits for the P4 data-collection pass.

## Success criteria (written BEFORE serving code)

1. Hermetic suite green (all existing tests pass unmodified except the
   contract-key count updates), ruff clean, pyright ≤ baseline (209).
2. New seam tests: deps-injected two-item frame produces items[] of length 2,
   aggregate grams == sum of per-item grams, verdict computed on the
   aggregate; single-item frames produce a one-element items[] and output
   otherwise identical to the pre-change wire.
3. On the six DATASET canteen photos (no GT, diagnostic only): rice+rasam
   frames return ≥ 2 items; no stage failures; runtime recorded.
4. Ledger entry 016 records the result against these criteria honestly,
   including any criterion not met.

## Explicitly out of scope

- Pixel-accurate instance segmentation (FoodSeg-style mask training) — P-later.
- Per-item compliance verdicts; the verdict is per-meal by design.
- General classifier improvements beyond the component-restricted combo
  matching; biryani/veg-rice confusion remains a separate issue.

## Implementation result

Implemented in `engine/pipeline.py`, `engine/mc.py`, and
`models/dish_segmenter.py`; seam coverage is in `tests/test_multi_item.py`.
The six-photo diagnostic is recorded in ledger 016. It confirms the aggregate
path runs, but does not establish portion accuracy: repeated-view item counts
differ and per-item recognition initially over-counted combo meals. Spec 004
adds component-restricted matching; per-component weighed captures remain a
separate field-data gate (spec 007).
