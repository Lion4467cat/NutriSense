# MetaFood3D benchmark result

## Decision

**Failed the preregistered criterion. No production change.** The candidate did
not reduce error against the category-median baseline, so the test split is
closed and must not be used for another tuning attempt.

## Run

Command from the repository root:

```bash
./.venv/bin/python experiments/metafood3d/run_benchmark.py
```

The run used CUDA on an NVIDIA GeForce RTX 4060 Laptop GPU, PyTorch
`2.13.0+cu130`, and cached ResNet-50 ImageNet-V2 weights (SHA-256
`11ad3fa62ca79e40addfd354a8ec4b7c75143b3038b8d2a807fbc68deab379ca`). It
refused CPU fallback by construction.

## Cohort and split

The run included 630 objects with an exact case-folded workbook/folder join, a
nonmissing weight, and at least one aligned RGB/mask/segmented frame. Six
unmatched workbook/folder name pairs (12 unmatched keys) and the one missing
weight were excluded. Split by physical object and category:

| Split | Objects |
| --- | ---: |
| Train | 416 |
| Dev | 106 |
| Test | 108 |

There is one test object per category. Every test category has training
support. The held-out test identities and selected frame stems are in the
Git-ignored local `split_manifest.jsonl`.

## Results

| Metric | Category-median baseline | Image + mask candidate |
| --- | ---: | ---: |
| Test MAE | 55.8318 g | 71.7766 g |
| Signed bias (prediction − truth) | −0.1929 g | −8.6770 g |
| Test MAE change | — | +15.9449 g (+28.56%) |

The candidate-minus-baseline paired category-bootstrap 95% interval for MAE
was `[-14.3625 g, 43.7691 g]`, which crosses zero. With one test object per
category, macro-category MAE equals object-weighted MAE. Dev selected ridge
alpha `100.0`; dev MAE across the fixed alpha grid was 147.7266, 147.6933,
147.3625, 144.1881, and 121.9945 g for alpha 0.01, 0.1, 1, 10, and 100.
The train-only category-median baseline had 83.7421 g dev MAE, so the selected
candidate was already 38.2524 g worse on dev.

The candidate used the workbook category as an oracle, the dataset mask (which
includes bowl and food together), full RGB, and four mask geometry features.
The baseline used only training-partition category medians. This was a
known-category, unseen-object research benchmark, not the app's serving path.

## Integrity checks and limits

The saved manifest has 630 unique object keys; split counts are 416/106/108;
there is no object overlap between splits, every test category has train
support, all 108 test predictions are finite and unique, and independently
recomputed MAEs match the run summary. The prediction records and full summary
are retained locally at
`datasets/raw/marker/metafood3d/experiment_outputs/` (Git-ignored).

This negative result does not establish performance on plated meals. The
benchmark used known categories and supplied masks; the latter include the
vessel. The dataset is licensed for non-commercial research, so neither these
results nor any derived weights are cleared for commercial product use without
separate permission. No ArUco plate or WED LOCKED data was used.
