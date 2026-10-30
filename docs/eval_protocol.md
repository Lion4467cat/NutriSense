# WED evaluation protocol — learned weight head

How the no-card learned weight head (`data/weight_head.pt`) is scored, what
each number means, and what protects the evaluation from drifting.

## Current model-readiness baseline (2026-10-30)

The older snapshot below describes the earlier ResNet50 model and is kept
as historical context. The current deployable DINOv2-S model is measured in
`data/reports/run_eval_dev_008_baseline.json`: **15.034 g DEV MAE** over 108
views, 21 plates, and 1,218 ROIs; plate-bootstrap 95% CI [12.227, 18.889] g.
This DEV carve is made from WED TRAIN plates and is also used for epoch
selection. It is a repeated model-selection signal, not an independent
generalization result. Three later point-estimate candidates failed to show
an MAE improvement and were rejected (ledgers 017–019); see
`docs/ledger/020-model-readiness-source-decisions.md`.

After model/configuration and threshold freeze, the one-time final LOCKED
report measured 14.667 g MAE over 2,793 ROIs / 48 plates, with plate-bootstrap
95% CI [13.331, 16.029] g and nominal 90% coverage 0.8277. The result is in
`data/reports/run_eval_locked_final_008.json` and the access log. It is not a
tuning signal and must not be used to modify the frozen model or thresholds.

As a separate grouped generalization estimate, five outer folds over WED TRAIN
plates produced a pooled **16.421 g MAE** on 11,759 ROIs across 198 plates
(fold MAEs 16.184, 18.096, 15.684, 15.720 and 16.521 g). Each fold's held
plates were excluded from fitting and epoch selection; the fixed DEV plates
were excluded from every fold. This is variability evidence for the baseline
recipe, not a DEV improvement claim. The exact per-plate aggregate is
`data/reports/cv_weight_head_s42_k5_wd1e-4.json`.

## Real-capture weighed-plate pilot (EVAL-ONLY)

On 2026-10-30 the full pipeline was run on 23 angle views of six unchanged
plates with user-confirmed food-only totals. The 60 mm ArUco anchor was
measured on 20 views; three used the prior tier. Per-image plate totals,
classification, angle spread, paired forced-prior results, mask overlap,
geometry telemetry and the fixed dish-label rubric are recorded in
`experiments/oracle_ablation/REPORT.md`; raw JSONL and reproduction scripts
are beside that report.

The diagnostic found item-mask area sums of 2.84–7.71 times the top-level
food-mask area on multi-item records, with broad angle-to-angle mass changes.
The card path's valid paired subset had 805.4 g MAE versus 203.2 g for forced
prior on the same 14 images. These are pilot measurements from six plates,
one phone and one scale; they are not generalization estimates. The plates
are permanently EVAL-ONLY: do not use them for tuning, candidate selection,
threshold setting or fix validation. The 14-image card/prior subset is not
the full 20 measured-anchor views.

Owner tool: `tools/run_eval.py` · protection: `tools/check_locked.py` +
`docs/locked_manifest.txt` · stress copy: `tools/stress_suite.py` · paired
comparison: `tools/compare_runs.py`.

## The path that is measured

Only the **deployable path** is evaluated:

```python
head = WeightHead.load("data/weight_head.pt")   # torchvision encoder + trained head
head.eval()                                      # frozen BN running stats
feats = head.encode(images)                      # batched, no grad
pred  = head(feats, rois)[batch_idx, slot]       # ROI-align 7x7 head read
```

The in-process training model is never scored. ROI/mask handling is the same
`WedPlates` / `build_rois` arithmetic as `tools/train_weight_head.py`, so
`run_eval --tier dev` reproduces the training report's `val_mae_deployable_g`
(VERIFIED 2026-10-12: 20.298 g vs 20.30 g recorded at train time).

## Tiers

| tier | rows | what it is | gate |
|---|---|---|---|
| `train` | 1146 views / 219 plates | WED `train` split **in full** | in-sample; **contains the DEV carve**, so it is optimistic and never a tuning signal |
| `dev` | 108 views / 21 plates | WED `val` carve — 10% of train plates, `random.Random(42).shuffle`, same arithmetic as `tools/train_weight_head.py` (+ `data/dev_real/` as a separate block if that manifest ever exists) | the only tier any tuning decision may use |
| `locked` | 248 views / 48 plates | WED `test` split | requires `--i-know-this-is-locked`; every run appends a line to `docs/locked_access_log.txt`; `data/wed/test/` is chmod'd read-only |

The DEV carve is **fixed**: seed 42, 10% of plates, split by plate
(`date_key` + `set`), never by view.

## Metrics

- **`mae_g`** — mean |pred − gt| over every scored dish ROI.
- **`mape_pct`** — mean |pred − gt| / gt; ground truth below 1 g is excluded
  and counted (`n_mape_excluded_lt1g`) — WED ships a few `weight_g = 0` rows.
- **`per_dish_mae_g` / `worst3_dishes`** — per WED class slug.
- **`coverage_90`** — fraction of ROIs whose ground truth falls in
  `pred ± 1.6448536 · σ_dish`, with `σ_dish` from
  `data/weight_head_sigma.yaml` (`sigma_g`, the per-class residual σ measured
  on the DEV carve). Gaussian band around the point estimate — the product's
  lognormal MC in `engine/mc.py` is the interval owner at serving time; this
  is the calibration check of the same σ.
- **`n_skipped_no_sigma`** — ROIs whose dish has no `sigma_g` entry; they are
  excluded from coverage/width (never from MAE).
- **`mean_interval_width_g`** — mean of `hi − lo` over non-skipped ROIs.
- **`mae_g_bootstrap_95ci` / `coverage_bootstrap_95ci`** — percentile 95%
  CIs from **2000 replicates resampling PLATES** (not views) with
  replacement, `numpy.random.default_rng(--seed)`. Resampling views would
  pretend the 5–8 views of one plate are independent measurements.
- **`per_plate`** — per-plate aggregates (`n`, `sum_abs_err`, `n_sigma`,
  `n_covered`), the unit the bootstrap resamples and what
  `tools/compare_runs.py` pairs two reports by. Reports also carry
  **`wall_s`** and **`peak_vram_mb`** so a speed/memory claim needs no
  second instrument.

## Reference numbers (this tree, 2026-10-12)

| tier | samples | mae_g (95% CI, plate bootstrap) | mape_pct | coverage_90 (95% CI) | mean width | skipped |
|---|---|---|---|---|---|---|
| `train` | 12977 | **13.382** [12.609, 14.200] | 17.39 (5 excluded) | 0.9298 [0.921, 0.938] | 78.36 g | 335 |
| `dev` | 1218 | **20.298** [17.247, 24.295] | 24.14 (0 excluded) | 0.8645 [0.812, 0.907] | 82.06 g | 0 |
| `locked` | — | **not run** (2026-10-12) | — | — | — | — |

Full JSON (per-dish MAE included): `data/reports/run_eval_{train,dev}.json`.
Note the coverage shortfall on DEV (0.8645 < the nominal 0.90): the σ's are
residual standard deviations, not calibrated 90% quantiles.

### Stress (DEV only)

`--tier dev --stress` applies the five frozen perturbations
(`tools/stress_suite.py`) to the same 108 DEV views:

| perturbation | mae_g | vs clean |
|---|---|---|
| clean | 20.298 | — |
| brightness_contrast_0.7 | 21.034 | +0.74 |
| gaussian_blur_k9 | 20.929 | +0.63 |
| perspective_30deg | 25.933 | +5.64 |
| jpeg_q30 | 20.470 | +0.17 |
| half_resolution | 20.550 | +0.25 |

Every stress result carries the label **"WED stress test, not real-world"**
(`data/reports/run_eval_dev_stress.json`): these are corruptions of WED
photos, not measurements of canteen capture conditions.

## Commands

```bash
.venv/bin/python -m tools.run_eval --tier dev                  # tune here
.venv/bin/python -m tools.run_eval --tier dev --stress         # + frozen suite
.venv/bin/python -m tools.run_eval --tier train                # in-sample only
.venv/bin/python -m tools.run_eval --tier locked --i-know-this-is-locked
.venv/bin/python -m tools.check_locked                         # 0 = pins match
.venv/bin/python -m tools.check_locked --write                 # approved re-pin
.venv/bin/python -m tools.compare_runs base.json cand.json --out compare.json
.venv/bin/python -m tools.log_run data/reports/run_eval_dev.json --note "…"
.venv/bin/pytest tests/test_locked_eval.py tests/test_compare_runs.py -q
```

`--seed` (default 42) seeds the bootstrap only; the split carve seed is
locked at 42. `--limit N` is a smoke switch and is recorded in the report so
a truncated run can never be mistaken for a real one.

## Comparing two runs

Two reports are never compared by eye. `tools/compare_runs.py` takes a
baseline and a candidate JSON, refuses pairs from different tiers or
different plate sets (exit 2), and reports the **paired** plate-bootstrap
difference for MAE and coverage, plus each shared stress perturbation.
The CI is paired: the same plate multiset is drawn for both runs in every
replicate, so plate-to-plate difficulty cancels and a constant per-ROI
offset shows up as a CI excluding 0.

```bash
.venv/bin/python -m tools.run_eval --tier dev --out data/reports/cand.json
.venv/bin/python -m tools.compare_runs data/reports/run_eval_dev.json \
    data/reports/cand.json --out data/reports/compare.json
```

Every ledger entry in `docs/ledger/` records this paired difference — a
bare "MAE improved" is not a result.

## Protecting the evaluation

`docs/locked_manifest.txt` pins a SHA-256 for **only** what the evaluation
*is* — never for the thing it *measures*:

- **(a) eval code** — `tools/run_eval.py`, `tools/stress_suite.py`,
  `tools/compare_runs.py`, `tools/check_locked.py`,
  `tools/build_wed_manifest.py`;
- **(b) eval data** — `data/wed_manifest.jsonl` (the split definition);
- **(c) locked images** — every file under `data/wed/test/` (git-ignored, so
  present locally only; CI sees none and skips them).

Deliberately **outside** the pin set (`tools/check_locked.py` names them
`MODEL_ARTIFACTS` and *fails* the lock if any of them appears in the
manifest): `models/weight_head.py`, `tools/train_weight_head.py`,
`data/weight_head_sigma.yaml`, `data/weight_head.pt`. The model is the
variable under test — re-pinning the evaluation must never silently cover a
change to it. Model integrity is guarded separately (encoder checksum +
golden MAE in `tests/test_weight_head_load.py`); the σ file is an input
that every coverage number already reports its own skip count against.

`tools/check_locked.py` exits 1 on any changed, missing or **unpinned** file
in that scope. `docs/locked_manifest.txt` can only be regenerated by
`.venv/bin/python -m tools.check_locked --write`, which is a deliberate,
**approved** act — re-pinning the evaluation is a decision, not a fix.

`data/wed/test/` is also read-only on disk:

```bash
chmod -R a-w data/wed/test        # applied 2026-10-12 (locked tier = read)
chmod -R u+w data/wed/test        # exact undo, if we ever deliberately unlock
```

## Locked-tier rules

1. Never run `--tier locked` to make a tuning decision. DEV is the only
   tuning signal; TRAIN is in-sample context; LOCKED is a report.
2. The locked tier needs `--i-know-this-is-locked` (argparse exits 2 without
   it) and appends to `docs/locked_access_log.txt`:

   ```
   <utc> | git=<short sha> | tier=locked | seed=42 | flag=--i-know-this-is-locked
         | views=248 samples=… | mae_g=… mape_pct=… | coverage_90=…
         | n_skipped_no_sigma=… | out=data/reports/run_eval_locked.json
   ```

3. `tests/conftest.py`-style hermeticity does not apply here: the test split
   is only ever read through this path, and only deliberately.
