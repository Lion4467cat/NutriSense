# WED evaluation protocol — learned weight head

How the no-card learned weight head (`data/weight_head.pt`) is scored, what
each number means, and what protects the evaluation from drifting.

Owner tool: `tools/run_eval.py` · protection: `tools/check_locked.py` +
`docs/locked_manifest.txt` · stress copy: `tools/stress_suite.py`.

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
.venv/bin/pytest tests/test_locked_eval.py -q                  # guards
```

`--seed` (default 42) seeds the bootstrap only; the split carve seed is
locked at 42. `--limit N` is a smoke switch and is recorded in the report so
a truncated run can never be mistaken for a real one.

## Protecting the evaluation

`docs/locked_manifest.txt` pins a SHA-256 for:

- **(a) eval code** — `tools/run_eval.py`, `tools/stress_suite.py`,
  `tools/check_locked.py`, `tools/build_wed_manifest.py`,
  `tools/train_weight_head.py` (split + ROI scoring), `models/weight_head.py`
  (deployable load path);
- **(b) eval data** — `data/wed_manifest.jsonl` (the split definition),
  `data/weight_head_sigma.yaml` (interval widths);
- **(c) locked images** — every file under `data/wed/test/` (git-ignored, so
  present locally only; CI sees none and skips them).

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
