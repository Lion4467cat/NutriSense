# 012 — Nutrition5k ingredient-conditional teacher head (ticket 07b)

- **id**: 012
- **branch**: `general-mode-calibration`
- **date**: 2026-10-29
- **author**: Buffy (agent)

## Hypothesis

The frozen-encoder + ROI + MLP family (same skeleton as
`models/weight_head.py`, encoder config from ledger 002) can learn
**per-ingredient grams** from Nutrition5k overhead RGB: one head, K
ingredient-state slots, SmoothL1 on sqrt(grams) over present slots. This is
the ingredient teacher the general-mode design needs; the F2
(geometry-floor residual) fusion on WED frames is downstream work this
entry does NOT claim.

Route note (data step): the public GCS bucket now holds only the 194.8 GB
tarball; overhead plates + metadata come from the ungated HF mirror
`mmathys/food-nutrients`, pull via `tools/pull_nutrition5k_overhead.py`
(--limit 600 of 1,000 verified-matching dish ids).

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| per-ingredient grams MAE (test, macro over slots) | none (no teacher exists) | ≤ 80 g in-domain | RGB-only, ~600 dishes; reference 29.4 g paper-baseline (4.7k dishes, dish-level, RGB+volume) |
| leave-ingredient-out transfer | n/a | held-ingredient MAE ≤ 2× its in-domain MAE | transfer-not-memorisation check |

## Success criterion (written BEFORE any run)

KEEP if: in-domain test macro per-ingredient grams MAE ≤ 80 g AND every
pre-registered LIO ingredient's held-MAE ≤ 2× that same ingredient's
in-domain test MAE. REVERT otherwise. No LOCKED read anywhere; val is used
only for model selection (best-epoch by val grams-MAE, val/test untouched
by augmentation beyond feature-grid hflip on train only).

## Change

- `tools/prep_n5k_ingredient_table.py` → `data/n5k_ingredient_table.yaml`:
  slot table (top-48 cooked ingredients by frequency; water excluded),
  fixed dish-hash split (seed 42; 0.8/0.1/0.1), LIO picks across
  categories: white rice, broccoli, olive oil, mixed greens.
- `tools/train_ingredient_head.py`: frozen DINOv2-S (resnet50 flag),
  full-frame ROI, one encode per image (feature-cache pattern),
  feature-grid hflip augmentation, AdamW+OneCycle, head-only training,
  head-only checkpoint `data/ingredient_head.pt` (versioned by slots list
  + encoder + seed), `--lio <name>` retrains with all dishes containing
  the ingredient removed from train (impurity counted) and reports
  held-ingredient MAE on untouched val+test dishes.

## Sources

- Nutrition5k https://arxiv.org/html/2103.03375v2 (CC BY 4.0) — per-
  ingredient grams + 29.4 g reference
- HF mirror https://huggingface.co/datasets/mmathys/food-nutrients —
  ungated overhead plates; attribution chain recorded in the puller doc
- `docs/research/general-indian-dish-method.md` §4a — design seam

## Result

Run provenance: a first pass ran on a 231-dish table during an HF-mirror
stall (duplicate concurrent pulls tripped the rate limit) and was SUPERSEDED
by the 603-image pull (555 labelled dishes; fixed dish-hash split 450/58/47).
All numbers below are from the 555-dish rerun (`data/*_train_report.json`).
A trainer bug discovered during the first read — `load_table` dropped
ingredient-containing dishes from ALL splits instead of train only, making
every held set empty — was fixed BEFORE any gate read; the four LIO runs were
then re-run (two of them only became evaluable with an non-empty held set).

| run | val grams-MAE (best) | test macro grams-MAE | LIO held-MAE | decision |
| --- | --- | --- | --- | --- |
| in-domain | 28.4 | 32.4 | n/a | gate: ≤80 met |
| LIO white rice | 28.4 | n/a (--skip-test) | 7.2 g on 1 held dish (val) | not evaluable — no test-dish coverage for the slot, so its in-domain test MAE does not exist |
| LIO broccoli | 28.4 | n/a | 20.8 g on 2 held test dishes vs in-domain slot 35.8 g → ≤2× met | PASS |
| LIO olive oil | 28.4 | n/a | held set EMPTY (all 10 dishes hash to train) | not evaluable |
| LIO mixed greens | 28.4 | n/a | 20.1 g on 3 held dishes vs in-domain slot 6.2 g (1 dish) → 20.1 > 12.4 | FAIL |

Reference: Nutrition5k paper 29.4 g (13.7%) dish-level mass MAE, RGB+volume
fusion on 4.7k dishes — our 32.4 g is per-ingredient, RGB-only, 555 dishes.

## Decision

- **revert** — the in-domain gate is met comfortably (32.4 g ≤ 80 g), but the
  pre-registered transfer criterion requires EVERY LIO ingredient to pass:
  mixed greens fails (20.1 g vs its 2×6.2 g bound, on 3 held dishes vs a
  1-dish in-domain read) and white rice + olive oil have no held-out test
  coverage at all. The checkpoint is therefore NOT adopted for serving:
  `data/ingredient_head.pt` is renamed `ingredient_head_candidate.pt` so the
  ledger-013 route stays genuinely checkpoint-absent (byte-identical
  fallback). No serving numbers are claimed from this entry.

## Follow-ups

- Raise the pull cap toward the full 1,000 (~×1.8 more held-out dishes per
  ingredient) and RE-PICK the LIO set so every chosen ingredient has ≥2 test
  dishes (the current four were chosen by frequency across categories, which
  left three of four gates unmeasurable at 555 dishes); then write a fresh
  pre-registered entry (candidate checkpoint + reports kept on disk).
- F2 residual fusion on WED measured-tier frames (geometry floor +
  bounded learned correction) — its own pre-registered entry.
