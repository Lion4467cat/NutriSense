# Known issues

Open defects and degraded measurements, with where they come from and what
is planned. Newest first.

## Weight head: 90% interval covers only 85.1% of val (2026-10-11, STAGE 1C)

The per-class lognormal intervals implied by `data/weight_head_sigma.yaml`
are nominal 90% intervals, but they contain only **85.1% of the 1,218 VAL
samples** — and those samples are the same split the sigmas were fitted on,
so coverage on unseen data is likely lower (the one-time test read saw
**82.0%**, see below). Two causes: the residuals are not exactly
lognormal, and `sigma_g` is a plain per-class standard deviation, so class
bias and heteroscedasticity are absorbed rather than modelled. Plan:
**conformal calibration** of the interval width, hooked into the
learned-weight fallback loop (the `temperature_scale` M6 hook already widens
central intervals, so the calibration can ride the same seam).

## Weight head training takes ~70 minutes per run (2026-10-11)

A full 100-epoch run of `tools.train_weight_head` takes about **70 minutes**
on the training box when the GPU is contended (~35 min when it is idle;
never run alongside pytest-with-GPU). The encoder is frozen and pinned to
`eval()`, so its output features are identical for every epoch and every
run. Proposed early speed fix: **cache the frozen encoder's 7×7 features
once per dataset** (one forward pass over the ~1.1k train + 108 val views)
and train the MLP head on the cache — the per-epoch cost then drops to
milliseconds and the whole run fits in a few minutes.

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
