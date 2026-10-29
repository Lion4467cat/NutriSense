# 006 — Stronger feature-prep-time augmentation for plate/session invariance

- **id**: 006
- **branch**: `spec-002-integration` (ticket `06-robustness-program`, spec 002 decision 11)
- **date**: 2026-10-29
- **author**: agent (implementer subagent, spec-002-integration)

## Hypothesis

Ledger 005 isolated the defect: DEV error carries **plate-level one-sided
bias** (per-plate mean standardized residual std 0.6997 vs iid 0.1327,
5.3×; 51.8% of samples on plates with |mean| > 0.3σ; tail-on-biased 68%),
while the |err| mass is spread across MANY plates (top-3 share 28.2%,
1.97× uniform — not a couple of catastrophic plates). Mechanism guess:
the head latches onto capture-session specifics (the photometry/geometry
of each capture set survives the modest ledger-001 augmentation, since
one plate/session provides ~5 views that share statistics and the train
corpus has only ~219 sessions), so whole plates slide together. A
stronger TRAIN-window recipe — a NEW geometric axis (joint image+mask
random rotation) plus stronger photometric/erasing pressure, applied at
feature-prep time (ticket 01 semantics: ONE fixed draw per train view)
— should decorrelate session appearance from grams and reduce the
systematic bias, moving DEV MAE down without a coverage regression.

## Expected effect

| metric | baseline (ledger-003 keep run, DEV) | expected after | note |
| --- | --- | --- | --- |
| DEV MAE (g) | 15.034 | paired-BETTER if the mechanism holds | plate-bootstrap paired CI |
| DEV coverage_90 | 0.8522 (deployed σ) | candidate's own refit σ (a keep regenerates the σ artifact, ledger-001 precedent) | guard band [0.80, 0.95] |
| DEV stress deltas | clean + 5 axes, fresh run recorded | each axis not-worse beyond its paired CI | "WED stress test, not real-world" |
| plate bias (ledger-005 statistic re-computed on the candidate) | plate-mean-std-resid std 0.6997 | reported, expected lower | diagnostic, not gated |
| train/val curve | in-training val MAE ≈ deployable val MAE | unchanged relationship | save→load symmetry |

## Success criterion (written BEFORE coding)

Single-variable change: ONLY the train-window augmentation recipe
differs from the deployed dinov2 head (same encoder, epochs 100, AdamW
1e-3 wd 1e-4, OneCycleLR pct_start 0.3, batch 4, seed 42, val split
seed 42 clean windows, `--skip-test`). The recipe (fixed here, at
pre-registration):

- joint random rotation ±20°, p = 0.7, drawn once per train view for
  image (bilinear, fill 0) and mask (nearest, fill 0) TOGETHER — new
  geometric axis, bboxes re-derived from the rotated mask;
- ColorJitter(brightness 0.4, contrast 0.4, saturation 0.4, hue 0.02),
  p = 0.8;
- GaussianBlur(kernel 5, σ (0.5, 2.0)), p = 0.4;
- RandomJpeg(p = 0.4, q (35, 95));
- RandomErasing(p = 0.35, scale (0.02, 0.15), ratio (0.3, 3.3), value 0);
- hflip p = 0.5 (unchanged); val/test windows stay the clean path.

Keep iff ALL hold, else revert:

1. **MAE paired CI improves.** `tools/compare_runs.py` (plate bootstrap,
   seed 42) of the candidate vs a FRESH baseline run of the deployed
   checkpoint on the same day/stress-run protocol — 95% CI of ΔMAE has
   upper bound < 0.
2. **No coverage regression.** Candidate coverage_90 (candidate's refit
   σ) within [0.80, 0.95] AND paired Δcoverage_90 CI lower bound ≥ −0.05.
3. **No stress regression.** Every stress perturbation shared by both
   fresh reports has ΔMAE paired CI lower bound ≤ 0 (a CI whose whole
   interval is above 0 - i.e. a significant worsening - fails).
4. **Gates.** Hermetic non-GPU suite green; ruff 0 findings; pyright at
   baseline; NO LOCKED read (test split never loaded anywhere;
   `--skip-test`); eval code (run_eval/stress_suite/compare_runs) untouched.
5. **On keep:** `data/weight_head.pt` + `data/weight_head_sigma.yaml`
   land together (candidate artifacts), the 30-view golden MAE in
   `tests/test_weight_head_load.py` is re-pinned with its documented
   reason, and the 4 GPU golden guards pass. **On revert:** the
   deployment files are restored byte-identical (sha-256 verified in the
   swap script) and recorded here.

Diagnostics recorded but not gated: the ledger-005 bias statistics
re-computed on the candidate (does the plate-mean-std-residual std move
down from 0.6997?), paired stress table direction, per-dish signed bias
on beans-curry / non-spicy-curry / aloo-curry.

## Change

- `tools/train_weight_head.py`: `--train-aug {ledger001,strong,none}`
  (default `ledger001` = current behaviour, bitwise); the `strong`
  recipe above as a second named transform block; joint image+mask
  rotation in `WedPlates` gated on the recipe (val/test paths and all
  other callers untouched); the feature-cache key + blob carry the
  recipe name so different recipes can never share a draw.
- Candidate artifacts written to non-deployment paths
  (`data/cache/aug006_weight_head.pt`, `data/cache/aug006_sigma.yaml`,
  `data/reports/weight_head_train_aug006.json`); the DEV candidate eval
  runs through the UNTOUCHED deployable instrument by a checked swap
  (backup → checksum → copy candidate in → `run_eval --tier dev
  --stress` → restore → checksum-verify), scripted under /tmp/opencode.
- No protected file touched; no eval-locked code touched.

## Sources

- `docs/ledger/005-cv-plate-profile.md` — this entry's defect evidence
  and the concentration/bias numbers it motivates.
- `docs/ledger/001-aug-run1.md` — the recipe being stepped up; the
  keep-or-revert discipline and the paired-CI precedents; the
  coverage-band guard provenance.
- `docs/ledger/002-dinov2-encoder.md` — the deployed encoder/checkpoint
  this experiment is a single variable away from.
- Spec 002 decision 11 — robustness plan: WED augmentation before any
  head re-calibration; interval re-calibration only after point
  estimates move (ledger 004 follow-up).

## Result

Training run `data/reports/weight_head_train_aug006.json` (seed 42, 100 epochs,
dinov2, feature cache `wed-dinov2-strong-ea6900cebc7c.pt`): in-process val MAE
16.45 g = deployable val MAE — save→load symmetry held, as in every prior
experiment. The candidate's DEV run through the untouched deployable
instrument is `data/reports/run_eval_dev_aug006.json`; the fresh same-day
baseline run is `data/reports/run_eval_dev_006_base.json`; the plate-bootstrap
paired comparison (seed 42, 2000 reps, 21 plates / 1,218 samples) is
`data/reports/compare_006_base_vs_aug006.json`.

**Every pre-registered gate FAILED:**

| gate | required | measured | verdict |
| --- | --- | --- | --- |
| 1. MAE paired CI | upper bound < 0 | ΔMAE **+1.414 g**, CI **[+0.615, +2.171]** | FAIL (worse) |
| 2. coverage | [0.80, 0.95] and Δ lower bound ≥ −0.05 | 0.8530 in band; ΔCI lower −0.0139 | PASS (not decisive alone) |
| 3. no stress regression | every ΔMAE CI lower bound ≤ 0 | all five axes' CIs **entirely above 0** (see below) | FAIL |
| 4. gates (suite/ruff/pyright/no LOCKED) | green | green during the run; re-checked after the revert | PASS |

Paired stress table (ΔMAE, all worse with CI above 0): clean +1.414
[0.615, 2.171]; brightness_contrast_0.7 +1.350 [0.641, 2.049];
gaussian_blur_k9 +1.483 [0.684, 2.278]; half_resolution +1.438 [0.638, 2.211];
jpeg_q30 +1.403 [0.659, 2.117]; perspective_30deg +1.730 [0.935, 2.593].

**Revert executed and verified:** deployment files restored from the eval-swap
backup; sha-256 recorded before the experiment
(`/tmp/opencode/aug006_backup/orig.sha256`) and re-verified immediately after:
`weight_head.pt` = `4ae02ef3…bae1a1`, `weight_head_sigma.yaml` =
`23248efd…55a7f9` — both match, byte-identical restoration.

**Diagnostic (recorded, not gated — ledger-005 profile tool re-run on the
candidate via the same checked swap, report
`data/reports/cv_plate_profile_aug006.json`):** the strong recipe did not
dissolve the plate-level bias defect while paying ~1.4 g of point-estimate
MAE. Measured on the candidate: per-plate mean standardized-residual std
**0.6333** vs ledger-005 baseline **0.6997** (iid expectation 0.1327 — still
4.8× biased; the −0.07 improvement is far too small to justify the +1.4 g);
top-3 share 26.47% (1.85× uniform, baseline 28.17%); Gini 0.2061 (baseline
0.2086); worst signed plates unchanged in direction and near in size
(20250523_set1 −23.48 g, 20250517_set30 −23.04, 20250517_set3 −13.94;
baseline −25.60 / −25.56 / −14.28). The session-invariance mechanism did
not materialize under a photometric/geometric step-up.

## Decision

**revert**, by the pre-registered rule: keep iff ALL gates hold; gate 1 and
gate 3 failed (the only passing gates — coverage in band, gate 4 — are not
sufficient under the all-hold rule). The deployed artifacts are the ledger-003 baseline (verified
sha-256 above). What survives from the experiment: (a) the strong recipe
itself is preserved in `tools/train_weight_head.py --train-aug strong` and is
reusable — it is a **negative result** the next attenuation trial (weaker
mixture of the two recipes) must start from; (b) the paired-CI instrument and
swap procedure are proven end-to-end; (c) coverage behaviour under a worsened
head stayed inside the guard band. Next direction per spec 002 decision 11:
recipe interpolation (e.g. strong's rotation axis at lower probability while
keeping ledger-001 photometrics) and transfer prep — augmentation alone has
now failed twice to move plate bias (ledger 001 was neutral, 006 is worse).
