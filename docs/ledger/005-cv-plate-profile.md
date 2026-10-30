# 005 — Plate-level cross-validation spread profile of the deployed head

- **id**: 005
- **branch**: `spec-002-integration` (ticket `06-robustness-program`, spec 002 decision 11)
- **date**: 2026-10-29
- **author**: agent (implementer subagent, spec-002-integration)

## Hypothesis

Ledger 004's failed calibration gate isolated a **point-estimate defect**:
the DEV residuals are plate-concentrated (per-plate mean standardized
residual std **0.700 vs 0.131 expected under iid**, 81% of the > 1.5σ tail
on biased plates; worst plate 20250517_set30 beans-curry predicted
60–77 g vs GT 300 g on all 5 views). This entry MEASURES the full profile —
a diagnostic, not a model change. Hypothesis being tested: a majority of
the DEV error mass sits on a small minority of plates, with whole plates
consistently biased in one direction across all their views.

## Expected effect

No artifact changes — the checkpoint, sigma file and every protected path
are untouched. Expected measurements (declared before coding):

| measurement | expected | source of expectation |
| --- | --- | --- |
| scored DEV MAE | 15.034 g (bitwise reproduction of ledger-003 keep run) | `data/reports/run_eval_dev_spec002_expansion.json` |
| nominal OOF band coverage at T = 1.0 (fold-refit σ, LOPO over 21 plates) | 0.8103 | ledger 004 / `data/reports/interval_calibration.json` |
| top-3 plates' share of Σ abs err | > 3× uniform (3/21 = 14.3% → > 42.9%) | ledger 004 concentration findings |
| per-plate mean standardized-residual std | > 2× iid expectation (≈ 0.131) | ledger 004: 0.700 measured |
| worst plates | 20250517_set30 (beans-curry), 20250517_set3 (steamed-rice) named | ledger 004 |

## Success criterion (written BEFORE coding)

The profile is valid (and the entry decisionable) iff ALL hold:

1. **Reproduction:** the tool's fresh scoring through the deployable path
   (`WeightHead.load` + `tools.run_eval.score` on `dev_rows()`)
   reproduces DEV MAE 15.034 g and OOF T=1.0 coverage 0.8103 (±0.0005 on
   coverage — reruns are deterministic; a mismatch means the machinery
   drifted, and the profile is invalid until fixed).
2. **Concentration table:** per-plate MAE + signed mean error + share of
   Σ|err| for all 21 plates; top-k cumulative shares for k = 1..5 with the
   uniform share for each k; Gini coefficient of per-plate |err| mass;
   per-plate mean standardized residual (fold-refit σ) with the iid
   expectation `sqrt(mean_j(1/n_j))` computed from the same plates.
3. **Sensitivity:** leave-one-plate-out (plate jackknife) DEV MAE for every
   plate — which plates inflate or deflate the headline. Every observed
   number must be reproducible from the saved per-sample table
   (`data/reports/cv_plate_profile.json`).
4. **Decision rule (pre-registered, written here):** if top-3 plates hold
   ≥ 42.9% of Σ|err| AND the per-plate mean standardized-residual std is
   ≥ 2× iid expectation, the plate-bias defect is **confirmed** and the
   augmentation entry (006) proceeds targeting plate/session invariance;
   if either concentration arm fails, aug 006 still runs (pre-registered)
   but its motivation note records the weaker concentration. Either way:
   no artifact change — the decision is `keep` (profile recorded as the
   robustness program's baseline diagnostic; a measurement carries nothing
   to revert).
5. **Gates:** no LOCKED read; hermetic non-GPU suite green; ruff 0;
   pyright at baseline.

## Change

- `tools/cv_plate_profile.py` (new): scores the deployable path once
  (DEV rows), then plate/dish concentration arithmetic, the plate
  jackknife, and the LOPO fold-refit-σ machinery of ticket 03
  (`tools.calibrate_intervals.fold_sigma_refit` + `normalized_scores`,
  imported — no copy) for the OOF coverage profile. Writes
  `data/reports/cv_plate_profile.json` including the full per-sample
  table. DEV rows only; no LOCKED access.
- `tests/test_cv_plate_profile.py` (new, hermetic — synthetic samples, no
  model/no dataset): concentration shares + uniform ratio, jackknife MAE,
  iid-expectation arithmetic, OOF coverage reproduction through the
  imported fold machinery, determinism of the report compiler.

## Result

All numbers from `data/reports/cv_plate_profile.json` (DEV, deployable
path, 1,218 samples / 21 plates; wall ~9 s on the RTX 4060). Machinery
cross-checks both reproduce exactly: scored MAE **15.0341** (ledger-003
keep run 15.034) and nominal OOF band coverage at T = 1.0 **0.8103**
(ledger 004).

**Concentration of error mass (Σ|err|, |err|-based, moderate — not the
dominant-plates picture the hypothesis branch expected):**

| k worst plates | share | uniform (k/21) | ratio |
|---|---|---|---|
| 1 | 11.86% | 4.76% | 2.49× |
| 2 | 22.19% | 9.52% | 2.33× |
| 3 | **28.17%** | 14.29% | **1.97× < 3× branch** |
| 4 | 33.80% | 19.05% | 1.77× |
| 5 | 38.98% | 23.81% | 1.64× |

Gini of per-plate |err| mass: **0.2086**.

**Signed plate bias (fold-σ standardized, confirmed):** per-plate mean
standardized residual std **0.6997 vs iid expectation 0.1327 (5.3×)**;
**51.8%** of samples sit on plates with |mean| > 0.3σ; the tail defined
as |err/σ_fold| > 1.5 has 258 samples, **68.2%** on those biased plates
(ledger 004's "81%" used a different tail definition — |conformal score|
> 1.5, i.e. |err| > 1.5·Z90·σ — same direction, stricter threshold).

**Which plates/dishes drive it:** worst plates by |mean err| are
20250523_set1 (−25.60 g mean, all 53 views one-sided low; e.g.
beetroot-kobari 63.8 vs 116) and 20250517_set30 (−25.56 g; beans-curry
60.1 vs 300 on all views — the ledger-004 worst case confirmed at sample
level), 20250517_set3 (−14.28); the biased tail then extends across many
plates at moderate size (20250515_set11 +0.79σ, 20250524_set15 +0.64σ,
20250515_set20 +0.60σ, 20250512_set14 +0.57σ, 20250519_set6 +0.53σ — five
more plates past +0.5σ in the HIGH direction). Worst dishes:
beans-curry (MAE 40.64 g, mean −30.86 — the 300 g plate alone contributes
−240 g × 5 views), non-spicy-curry (31.06, +25.10), steamed-rice (28.08,
−0.59 — large |err| but unbiased), aloo-curry (26.48, +26.48 — every
sample over-predicted), Papaya (25.81, +14.50), tomato-pappu (24.89,
−17.63).

**Sensitivity (plate jackknife):** the headline is defensible — no plate
moves it by more than |Δ| 1.18 g with excluded. Dropping the worst plate
20250523_set1 (53 samples, plate MAE 40.96) gives 13.8546 g (Δ −1.18);
dropping the mildest, 20250512_set22, gives 15.5705 g (Δ +0.54). The DEV
estimate is therefore not hostage to a single plate — but the per-plate
signed offsets are large relative to per-class σ (the defect ledger 004
isolated).

## Decision

**keep** (measurement recorded as the robustness program's baseline
diagnostic; nothing was changed, so there is nothing to revert). The
pre-registered decision rule resolves to the weaker-concentration branch:
the top-3 arm FAILED (28.17% < 42.9%) while the bias arm PASSED (0.6997 ≥
2 × 0.1327). Read: the defect is **not two or three catastrophic plates**
— it is a moderate-|err| plateau in which MOST plates carry a one-sided
systematic offset (5 of 21 plates sit past +0.5σ high, 2 past −1.3σ low),
and a few dish-cells (beans-curry on 20250517_set30, aloo-curry
everywhere) carry outliers. Ticket 06's augmentation experiment (ledger
006) proceeds targeting capture-session invariance, with the honest note
that plate re-estimation will mostly need to move the BIAS of many
mid-size-error plates, not just rescue the worst two. Signals for aug
006 to watch beyond paired ΔMAE: the signed-resource dishes
beans-curry/non-spicy-curry/aloo-curry and the OOF tail share.

## Sources

- `docs/ledger/004-interval-calibration.md` — root cause (plate-level
  bias), fold machinery and nominal OOF coverage this entry reproduces.
- `docs/known_issues.md` — updated follow-up direction (point-estimate
  robustness).
- `tools/calibrate_intervals.py` — `fold_sigma_refit` +
  `normalized_scores` (imported, unmodified) for the LOPO layer.
- `tools/run_eval.py` — deployable scoring path (`score`, `dev_rows`);
  eval-locked, untouched.
- `spec 002 decision 11` (specs/002-general-mode-and-calibration/spec.md)
  — robustness plan: WED cross-validation + augmentation.

