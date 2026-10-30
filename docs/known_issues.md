# Known issues

Open defects and degraded measurements, with where they come from and what
is planned. Newest first.

## Multi-item meal estimates fail the weighed-plate pilot (2026-10-30)

The multi-item path and combo component restriction are implemented (specs
003/004). A 23-image / six-plate weighed pilot now supplies plate totals but
no per-component ground truth. Item-mask area sums reached 2.84–7.71 times
the top-level food-mask area; outputs varied substantially by angle, and
some frames still assign repeated labels to multiple vessels. A paired
card-versus-forced-prior comparison had 14 valid same-image pairs and showed
larger card-path error on this cohort. These are EVAL-ONLY findings: the
plates must not be used for tuning or validating candidate fixes. The masks
are not pixel-level food ground truth, and plate/table height cannot be
isolated from the saved overlays. Multi-item mass accuracy remains
unestablished beyond this pilot; per-component accuracy is unmeasured.

The follow-up synthetic diagnostics are recorded in ledger entries 022–024.
Mask spill alone failed its registered criterion, local surface-area
integration regressed the fixed synthetic scenes, and the card-position test
had only two detectable positions per scene. The latter is a mechanism lead,
not a serving correction or independent validation. See
[`docs/agentic-improvement-loop.md`](agentic-improvement-loop.md).

## Weight head: 90% interval covers only 85.1% of val (2026-10-11, STAGE 1C; measured honestly 2026-10-29)

The per-class lognormal intervals implied by `data/weight_head_sigma.yaml`
are nominal 90% intervals, but they contain only **85.1% of the 1,218 VAL
samples** — and those samples are the same split the sigmas were fitted on,
so coverage on unseen data is likely lower (the one-time test read saw
**82.0%**, see below). Two causes: the residuals are not exactly
lognormal, and `sigma_g` is a plain per-class standard deviation, so class
bias and heteroscedasticity are absorbed rather than modelled.

**2026-10-29 — conformal calibration (ticket 03, ledger 004) measured the
defect honestly and FAILED its pre-registered gate; the σ artifact is
unchanged.** Leave-one-plate-out over the 21 DEV plates (fold-refit σ
layer, head never retrained): nominal out-of-fold coverage at multiplier
1.0 is **0.8103** (worse than the in-sample 0.8522, as expected). Stage C
(one global multiplier) reaches 0.9007 only at **T = 1.47 → +47% mean
width**, past the pre-registered +25% cap. Stage B (per-class multipliers)
fails both criteria: 20/38 classes cannot reach 0.90 on their own OOF
scores even at the 1.50 grid ceiling (tiny per-class calibration sets,
n = 7–15), pooled 0.8736 at +27.1% width. Root cause — it is a
**point-estimate robustness problem, not a width problem**: standardized
residuals have overall std 2.09 (want 1.0) and kurtosis 48.8, and the
excess variance is **between-plate**: per-plate mean standardized residual
has std **0.700 vs 0.131 expected under iid** (5.3×), 51.8% of samples sit
on plates with |mean| > 0.3σ, and 81% of the >1.5σ tail samples live on
those plates. Worst cases are whole plates mis-predicted in one direction
(20250517_set30 beans-curry: predicted 60–77 g vs GT 300 g on 5 views).
No width scaling of a per-class σ layer can honestly cover a plate-level
−240 g offset.

Plan: this is now a **point-model robustness** issue (plate/session-level
systematic mis-estimation in WED capture sessions), not an interval-width
issue — per-plate calibration is impossible at serving (no plate identity),
so the fix belongs to model features/training, tracked separately. Width
scaling stays off the table until the point estimates improve: the honest
90% interval would need +47% width to reach 0.90 OOF coverage, which was
rejected by the pre-registered cap (ledger 004).

## Weight head training takes ~70 minutes per run (2026-10-11) — RESOLVED

~~Proposed early speed fix: cache the frozen encoder's features once per
dataset.~~ **Landed (spec 002 decision 10):** `tools/train_weight_head.py`
prepares the frozen encoder's per-view features once per run and caches them
on disk (`data/cache/`, one blob per encoder + recipe + dataset fingerprint;
`--features-cache none` opts out); every epoch trains the head on the
prepared tensors. Verified 2026-10-29: the cache is implemented and covered
by tests/test_weight_head_cache.py — the remaining weight-head robustness
issue is the plate-level bias above, which is data-bound (P4, spec 007), not
training-speed-bound.

## Stale artifact: `data/reports/weight_head_train.json` (2026-10-11)

Still holds the pre-STAGE-1B numbers (in-process val 19.73 g, test
19.32 g) from the train-mode-BN run — i.e. it documents the run whose
deployed checkpoint actually scored 24.65 g on val. The training script
writes this report only as the side effect of a full retrain (and only when
the test split is evaluated), so it **cannot be regenerated without
retraining**, and retraining just to refresh a JSON is not worth an extra
test-split read. Left stale on purpose; regenerate on the next training run.

## WED test split: read exactly once (2026-10-11, STAGE 1C)

The test split (248 views / 48 plates) has been read **once** in this
project's history — STAGE 1C step 3, deployable path (`WeightHead.load`),
purely for reporting:

| metric | value |
|---|---|
| test MAE | **20.03 g** (2,793 ROI residuals) |
| 90% interval coverage | **82.0%** (2,711 samples; 82 samples of dishes without a val-fitted sigma skipped) |
| in-process vs deployed val | 20.30 g == 20.30 g (BN mismatch fixed) |

**No decision was based on these numbers, and the split must not be read
again in this session or for any future gate** — model selection uses the
VAL split only.

### Per-dish test MAE (g)

| dish | n | MAE g |
|---|---|---|
| veg-dum-briyani | 20 | 57.16 |
| aloo-curry | 20 | 49.99 |
| steamed-rice | 245 | 37.24 |
| Watermelon | 104 | 30.88 |
| rajma | 71 | 30.03 |
| non-spicy-dal | 115 | 28.35 |
| Muskmelon | 20 | 27.79 |
| veg-pulao | 73 | 26.71 |
| Bottle-gourd-curry | 23 | 25.43 |
| non-spicy-curry | 55 | 25.35 |
| pachi-pulusu | 54 | 25.05 |
| beetroot-kobari | 51 | 24.56 |
| tomato-pappu | 54 | 23.38 |
| leaf-dal | 15 | 22.01 |
| kofta-curry | 55 | 20.59 |
| channa-brinjal | 54 | 20.58 |
| curd | 244 | 20.04 |
| cabbage-dry | 63 | 20.03 |
| masoor-dal | 29 | 19.99 |
| chicken-dum-biryani | 20 | 19.92 |
| phulka | 194 | 19.33 |
| Papaya | 45 | 19.17 |
| payasam | 45 | 18.77 |
| sambar | 126 | 18.2 |
| beans-curry | 55 | 17.95 |
| aloo-capsicum | 20 | 16.86 |
| bisi-bele-bath | 15 | 16.41 |
| muddha-pappu | 30 | 15.27 |
| salad | 243 | 15.1 |
| raita | 20 | 13.93 |
| rasam | 30 | 13.54 |
| beetroot-poriyal | 29 | 13.22 |
| Banana | 70 | 13.21 |
| aloo-fry | 47 | 12.35 |
| mirchi-ka-salan | 20 | 11.82 |
| dondakaya-fry | 14 | 8.58 |
| chutney | 150 | 5.7 |
| kakarakaya-fry | 15 | 3.51 |
| mango-pickle | 50 | 3.17 |
| papad | 175 | 3.06 |
| boondi | 15 | 1.93 |

Median dish: phulka 19.33 g. Worst: veg-dum-briyani 57.16 g (n=20).

## How the old numbers arose (19.32 g / 19.73 g / 24.65 g)

Before STAGE 1B the frozen ResNet-50 encoder was put in `train()` mode
during training, so its BatchNorm running statistics adapted to WED — but
those adapted stats lived only in the training process and were never
saved. The training script therefore *reported* the adapted-stats numbers
(val 19.73 g, test 19.32 g), while `WeightHead.load()` rebuilt the encoder
with stock ImageNet stats and scored **24.65 g** on the same val split: a
~4 g train/deploy gap that was invisible until measured through the reload
path. STAGE 1A compared fixing it by saving the adapted stats (option B)
vs keeping stock ImageNet stats by pinning the encoder to `eval()` during
training (option A); A won the stress gate (B's perspective-warp MAE blew
up 74.7 g vs 24.7 g) and was adopted. After the retrain, in-process and
deployable val MAE are identical (20.30 g == 20.30 g) and regression tests
`test_encoder_bn_matches_stock_imagenet` + `test_golden_val_subset_mae`
guard the fix.
