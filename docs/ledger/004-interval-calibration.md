# 004 — Honest 90% intervals for learned-head grams: conformal calibration, leave-one-plate-out

- **id**: 004
- **branch**: `spec-002-integration` (ticket `03-interval-calibration`, spec 002 decisions 7+8+9)
- **date**: 2026-10-28
- **author**: agent (implementer subagent, spec-002-integration)

## Hypothesis

The nominal 90% weight intervals around learned-head grams under-cover:
the per-class σ in `data/weight_head_sigma.yaml` is a residual standard
deviation fitted on the whole DEV carve and then scored on that same carve
— STAGE 1C measured 85.1% val coverage, and the one-time 2026-10-11 test
read saw 82.0% (`docs/known_issues.md`). Split-conformal calibration with
a leave-one-plate-out fit should recover honest ≥ 0.90 coverage with ONE
global multiplier at a width cost well under +25%, while leaving the point
estimates (MAE) untouched: the head checkpoint is fixed (it was trained on
WED train, which excludes the DEV plates, so no per-fold retraining is
needed or allowed) and calibration touches only widths.

**Where the multiplier lands (declared before coding):** on the per-class
σ layer itself — `data/weight_head_sigma.yaml`: `sigma_g` and `sigma_rel`
are multiplied by the calibrated value (the documented invariant
`sigma_rel = sigma_g / mean GT` is preserved at the calibrated scale) and
`_meta.calibration` records provenance, `status: calibrated` like ticket
02's threshold. Reasons: (a) spec decision 7 scopes this ticket to
LEARNED-head grams intervals — `temperature_scale` is applied globally in
`engine/mc.py` (kcal/protein and geometry-path summaries too), so a
calibrated temperature would widen intervals outside this ticket's scope;
(b) `tools/run_eval.py` (the corroboration instrument, eval-locked and
untouched) reads its band from this file's `sigma_g`, so landing there
keeps the DEV instrument measuring the deployed widths with zero code
change; (c) one multiplier, applied once — `temperature_scale` stays 1.0
(applying the same multiplier there too would double-widen) and its
params note is updated to record this. This is the "learned-head path"
side of the ticket's existing-seam choice ("the widening hook /
learned-head path"); the deviation from the "widening hook" wording is
recorded here before coding.

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| OOF DEV coverage_90 (band shape) | nominal-σ, expected ≈ 0.85 | ≥ 0.90 | LOPO over 21 plates: fold-refit σ + one global multiplier |
| OOF DEV coverage_90 (wire lognormal shape) | — | ≈ band number, reported | secondary check at the same multiplier |
| DEV MAE (g) | 15.034 | unchanged — paired 95% CI vs ledger-003 keep run covers 0 | widths only; point path untouched |
| DEV coverage_90 (fresh run) | 0.8522 | ≈ OOF number, ≥ 0.90 expected | full-DEV σ × multiplier, corroborates the OOF estimate |
| mean DEV interval width (g) | 62.16 | growth ≤ +25% (multiplier ≤ 1.25) | gate cap; wire-shape growth also reported |

## Success criterion (written BEFORE coding)

Stage C gate — ALL must hold for `keep`, else the ticket fails
(investigate; Stage B per ticket, recorded):

1. **OOF coverage ≥ 0.90.** Leave-one-plate-out over the 21 DEV plates
   (108 views / 1,218 ROI samples): each fold refits ONLY the
   σ/calibration layer on the 20 in-fold plates (per-class residual std,
   classes with < 3 in-fold residuals fall back to the file's full-DEV σ —
   fallback count reported; the head checkpoint is never retrained) and
   scores the held-out plate; nonconformity = |y − ŷ| / (Z90 · σ_fold,cls);
   ONE global multiplier, identical in every fold. Gate: pooled
   out-of-fold coverage_90 at the deployed multiplier ≥ 0.90 on the band
   shape (the `coverage_90` of record, `tools/run_eval.py` semantics).
2. **MAE statistically unchanged.** Paired plate-bootstrap 95% CI of
   ΔMAE (fresh `tools/run_eval --tier dev` vs the ledger-003 keep run
   `data/reports/run_eval_dev_spec002_expansion.json` via
   `tools/compare_runs.py`) brackets 0.
3. **Width growth ≤ +25%.** Mean interval width growth at the deployed
   multiplier ≤ +25% — band shape (multiplier ≤ 1.25) measured by the
   fresh run's `mean_interval_width_g` ratio, wire shape (lognormal
   central interval with scaled `sigma_rel`) reported by the calibration
   tool. Growth above the cap ⇒ the ticket FAILS and we investigate
   rather than ship.
4. **No LOCKED read.** No `--tier locked`, no test-split access in any
   command of this ticket.
5. **Gates.** Hermetic non-GPU suite green; ruff 0 findings; pyright at
   baseline; GPU-marked golden guards stay green.

**Multiplier selection rule (pre-registered):** grid over
T ∈ [0.50, 1.50], step 0.005, of pooled out-of-fold coverage; deployed
multiplier = smallest grid T with OOF(T) ≥ 0.90 (tuned against
out-of-fold coverage — that is what makes the tuning honest). Reported
alongside: the full-DEV split-conformal quantile (the ⌈0.9·(n+1)⌉-th
smallest of the 1,218 file-σ scores) and the per-fold-procedure coverage
(each fold calibrated by its own in-fold conformal quantile). If the
smallest passing T exceeds 1.25 ⇒ criterion 3 fails ⇒ Stage B (per-dish
multipliers) is executed and measured with the same OOF machinery; Stage
C is kept only if the gate passes.

Decision `keep` only if 1–5 all hold with Stage C; `revert` otherwise
(the failed criterion names which element).

## Change

- `tools/calibrate_intervals.py` (new): the leave-one-plate-out conformal
  machinery — fold σ refit (per-class residual std, min 3 in-fold samples,
  else file fallback, counted), normalized-residual nonconformity
  |y − ŷ|/(Z90·σ_fold), both pre-registered stages (C: one global
  multiplier; B: per-class multipliers with grid-ceiling fallback, flagged),
  the analytic wire-shape OOF check at each stage's deployed layer, the
  full-DEV split-conformal quantile + per-fold-procedure corroboration, and
  the `--apply` lander (scales `sigma_g`/`sigma_rel` in
  `data/weight_head_sigma.yaml`, writes `_meta.calibration` provenance,
  refuses double-application and gate failures). Predictions come from the
  deployable path (`WeightHead.load` + `tools/run_eval.score`) computed
  ONCE — the head is never retrained, folds are array math on fixed
  predictions; the ticket-01 resnet50-keyed feature cache
  (`data/cache/wed-resnet50-*.pt`) is NOT consumed (checkpoint is dinov2,
  and folds need no per-fold forward passes).
- `tests/test_interval_calibration.py` (new, hermetic — 18 tests): finite-
  sample quantile position + marginal ≥ 0.90 guarantee (averaged over
  repetitions), coverage monotonicity, selection rule (smallest passing T,
  None past the grid), fold σ refit + fallback counting + missing-class
  refusal, wire-interval shape/monotonicity, end-to-end synthetic
  calibration (mixture-shaped residuals force T > 1), Stage B per-class
  behavior, and the artifact lander (scaling, provenance, stage refusal,
  double-apply refusal).
- `docs/known_issues.md`: the interval defect entry updated with this
  entry's honest measurement and root cause.
- No eval-locked or otherwise protected file was read or modified;
  `data/weight_head_sigma.yaml`, `data/params_status.yaml` and
  `temperature_scale` are UNTOUCHED — nothing landed (gate failed, below).
- Deviation from the ticket's "existing widening parameter / widening hook"
  wording: declared above (DESIGN-σ) before coding; moot in the end since
  no artifact landed, recorded for the next attempt.

## Result

All numbers from `data/reports/interval_calibration.json` (DEV, 21 folds,
1,218 ROI samples, 0 fallback samples; wall ~11 s on the RTX 4060):

| measurement | value |
| --- | --- |
| nominal OOF coverage at T = 1.0 (fold-refit σ) | **0.8103** |
| full-DEV in-sample coverage at file σ (cross-check vs run_eval 0.8522) | 0.8522 ✓ |
| full-DEV split-conformal quantile (file-σ scores) | 1.1989 |
| per-fold-procedure pooled OOF coverage | 0.9212 |
| **Stage C**: smallest passing global T | **1.47** → OOF 0.9007 ✓, wire OOF 0.9039, width growth **+47.0%** ✗ (cap +25%) |
| **Stage B**: per-class multipliers | 20/38 classes hit the 1.50 grid ceiling without reaching 0.90 (n = 7–15 OOF samples each) → pooled OOF **0.8736** ✗, wire 0.8612, width growth **+27.1%** ✗ |
| deployed stage | **none** — both stages fail the pre-registered gate |

Gate verdict (pre-registered criteria): 1 OOF ≥ 0.90 — Stage C ✓ at T=1.47,
Stage B ✗ (0.8736); 3 width ≤ +25% — Stage C ✗ (+47.0%), Stage B ✗
(+27.1%); 2 MAE-paired-CI — not run (no artifact change, point estimates
untouched by construction); 4 no LOCKED read ✓ (DEV rows only, throughout);
5 suite gates ✓ (hermetic suite, ruff, pyright, GPU golden guards — counts
below).

**Root cause (investigation mandated by the failed cap):** the residuals
are not heavy-tailed around an unbiased mean — they carry **plate-level
bias**. Standardized residuals (residual / fold-σ) have overall std 2.09
(want 1.0) and kurtosis 48.8; the per-plate mean standardized residual has
std **0.700 vs 0.131 expected under iid** (5.3× excess), 51.8% of samples
sit on plates with |mean nr| > 0.3σ, and **81% of the > 1.5σ tail samples
live on those plates**. Concrete worst cases: plate 20250517_set30
beans-curry predicted 60–77 g vs GT 300 g on all 5 views (−240 g, 4×
under-prediction); plate 20250517_set3 steamed-rice 208–246 g vs GT 355 g.
A per-class σ layer cannot express a per-plate offset: scaling it widens
every interval while the biased plates stay out of band — which is exactly
why Stage C needs +47% and Stage B's small classes cannot reach 0.90 even
at 1.5×. This is a point-estimate robustness defect (WED capture-session /
plate systematic mis-estimation), not an interval-width defect.

## Decision

**The ticket FAILS its pre-registered gate — no artifact change.** Stage C
fails criterion 3 (+47% > +25%); its pre-registered contingency Stage B was
executed and fails criteria 1 and 3 (0.8736 < 0.90, +27.1% > +25%).
`data/weight_head_sigma.yaml` is untouched (verified: no `_meta.calibration`
block), `temperature_scale` stays 1.0, no fresh eval run is warranted (the
point path is untouched by construction — criterion 2 is moot). The defect
stays open in `docs/known_issues.md`, now with an honest OOF measurement
(0.8103 at multiplier 1.0) and its root cause. The nominal-σ intervals
continue to serve as-is (DEV in-sample coverage 0.8522) with the defect
documented — shipping any of the measured multipliers would have violated
the pre-registered width/coverage contract.

## Follow-ups

- The real fix is upstream of widths: **plate/session-level systematic
  mis-estimation** in WED (whole plates predicted 4× low). Candidate
  directions, all model-side (per-plate calibration is impossible at
  serving — no plate identity): session-robust features, per-capture
  normalization, or bias-robust training objectives. This should become
  its own ticket with a DEV-tuned gate; the per-plate mean standardized
  residual table in the calibration report (`data/reports/
  interval_calibration.json`) is the starting diagnostic.
- If point estimates improve, re-run THIS ticket's machinery unchanged:
  `tools/calibrate_intervals.py` measures and lands the calibration with
  the same pre-registered gate (Stage C → Stage B fallback).
- The tiny-class calibration problem (n = 7–15 OOF samples per class)
  would persist even with better point estimates; if Stage B is ever
  revisited, consider hierarchical/partial pooling of per-class
  multipliers (shrunk toward the global one) — out of scope here.
- `data/reports/interval_calibration.json` (dry-run report, `applied:
  false`) and `data/reports/run_eval_dev_spec002_expansion.json` (ledger
  003 keep run) stay as the paired reference for any future attempt.

- `specs/002-general-mode-and-calibration/spec.md` — decisions 7 (scope:
  learned-head grams only), 8 (staged C→B, LOPO), 9 (this gate).
- `docs/known_issues.md` — the defect (85.1% val / 82.0% one-time test)
  and the conformal plan; the DEV σ fit is the reason folds are required.
- `docs/eval_protocol.md` — `coverage_90` definition (band =
  pred ± Z90·σ_dish), DEV = the only tuning tier, paired-comparison rules.
- `docs/ledger/003-serve-all-41-classes.md` — the keep run this entry
  pairs against (`data/reports/run_eval_dev_spec002_expansion.json`,
  15.034 g / 0.8522, width 62.16 g).
- `tools/run_eval.py` + `tools/compare_runs.py` — instrument and paired
  plate-bootstrap CI (eval-locked; untouched by this entry).
- Split conformal prediction (normalized-residual form): Papadopoulos,
  Proedrou, Vovk & Gammerman, "Inductive confidence machines for
  regression", ICANN 2002; Vovk, Gammerman & Shafer, "Algorithmic
  Learning in a Random World", Springer 2005;
  https://en.wikipedia.org/wiki/Conformal_prediction (finite-sample
  quantile ⌈(n+1)(1−α)⌉ of the calibration scores).
- `engine/mc.py` — the sole interval owner; `temperature_scale` is the
  M6 widening hook (stays 1.0, see landing note above).
- `models/weight_head.py` + `data/weight_head_sigma.yaml` — the σ layer
  the calibration rides (deliberately unpinned model artifact).
