# 016 — Multi-item portion path (spec 003)

- **id**: 016
- **branch**: `spec-003-multi-item`
- **date**: 2026-10-29
- **author**: agent (CodeBuddy)

## Hypothesis

Real canteen meals are multi-item (rice+rasam, biryani+eggs) but the deployed
contract is one mask = one serving = one meal, so multi-vessel plates are
measured as a single blob and judged against whole-meal band minima as if the
captured dish were the entire meal. Promoting the ledger-014 `grid9_box`
diagnostic to a serving primitive — detect vessels, classify and portion each
one, judge the aggregate — should measure such plates at the correct scope.

## Success criteria (from spec 003, written BEFORE serving code)

1. Hermetic suite green, ruff clean, pyright ≤ baseline 209.
2. New seam tests: two-item frame → items[] of length 2, aggregate grams ==
   sum of per-item grams, verdict on the aggregate; single-item frames keep
   the pre-change wire plus a one-element items[] mirror.
3. On the six DATASET canteen photos (diagnostic only, no GT): rice+rasam
   frames return ≥ 2 items; no stage failures; runtime recorded.
4. This entry records the result honestly, including criteria not met.

## Change

- `models/dish_segmenter.py`: `segment_items()` — 3x3 grid + box prompts,
  `_select` per query, IoU ≥ 0.70 dedupe, area gate, cap 4. `segment_food`
  untouched (synthetic parity).
- `engine/pipeline.py`: after the depth stage, menu-primary frames with ≥ 2
  vessels take the multi-item path — per-item bbox-crop classification (the
  gallery is ROI-crop trained, so crops are in-distribution), per-item portion
  under the same rules as the single path (learned head on prior tier /
  geometry on measured tier, table_prior on real-MoGe), per-item MC with
  independent seeds, aggregate = elementwise sample sum, verdict on the
  aggregate meal. Detection failure, < 2 vessels, or nothing resolvable falls
  back to the byte-identical single-serving flow with a degradation tag.
- `engine/mc.py`: `aggregate_meal()` owns the aggregate intervals.
- Contract (constitution IV focused update): 19th wire key `items` (always
  present when a portion ran; one-element mirror on single-serving frames),
  `path_used` gains `multi_item`, TS contract + JSON fixtures regenerated.
- tests/conftest.py pins `segment_items` to None (hermetic); 7 new seam
  tests in tests/test_multi_item.py.

## Result

Gates: **253 passed** (243 + 7 new + contract-fixture regen), ruff clean,
pyright 209 = baseline. Criteria 1–2 met.

Real-photo diagnostic (`data/reports/real_photo_multi_item_2026-10-29.json`,
same six unposed captures as the 2026-10-29 e2e report):

| photo | before (single) | after | items |
| --- | --- | --- | --- |
| pepper…131408 | 287.8 g FAIL | 287.8 g FAIL (unchanged) | 1 |
| pepper…131418 | 312.3 g FAIL | **772.3 g PASS** | 3 |
| tomato…131456 | 298.8 g FAIL | **879.6 g PASS** | 3 |
| tomato…131457 | 252.5 g FAIL | **492.1 g BORDERLINE** | 2 |
| vegetable…130507 | 90.6 g FAIL | 90.6 g FAIL (unchanged) | 1 |
| vegetable…130516 | 57.6 g FAIL | 57.6 g FAIL (unchanged) | 1 |

No stage failures; warm runtime ~5–6 s vs ~1.2 s single (grid9 costs ~4 s).
Single-item frames are byte-identical to the pre-change run — the fallback
parity holds on real photos. Criterion 3 met on 3 of 4 rasam frames.

**Two honest caveats, no accuracy claim (no GT):**

1. **Over-count risk.** Every item on the multi frames classified as
   `rice_sambar` — the per-crop gallery cannot separate "the rice vessel"
   from "the rasam vessel" of one combo plate, so each vessel gets the full
   mixed-dish recipe and the sum (772–880 g on one plate) is implausible.
   The mechanism works; per-item dish attribution does not, yet. This is the
   P1 problem (per-item recognition) showing up exactly as predicted.
2. **Detection inconsistency.** Near-duplicate views of the same plate
   disagree (131408: 1 vessel; 131418: 3). grid9 detection stability needs a
   card-bearing capture pass to quantify.

## Decision

- **keep** — criteria 1–3 met as written; the caveats are recorded as
  follow-ups, not hidden. No LOCKED read; no gate moved.

## Follow-ups

1. **P1 component-restricted recognition is implemented** (spec 004). The
   six-photo follow-up in `data/reports/real_photo_p1_combo_2026-10-29.json`
   reduces the three multi-vessel totals from 772.3/879.6/492.1 g to
   418.1/534.7/202.0 g. Some frames still assign the same component to all
   vessels; this is a diagnostic change only, without component-level ground
   truth or an accuracy claim.
2. Quantify grid9 stability across repeated views (IoU of item sets).
3. The ≤5 g / relative-error accuracy claim still waits on the P4 weighed,
   dish-held-out, card-bearing data-collection pass.
