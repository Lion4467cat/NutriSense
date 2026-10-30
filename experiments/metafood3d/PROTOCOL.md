# MetaFood3D single-object mass benchmark

## Scope

This is a non-commercial research benchmark on isolated MetaFood3D objects. It
does not alter serving code and does not test mixed plated meals. The official
dataset terms limit use to non-commercial purposes; do not use these results
or weights for a commercial product without separate permission.

## Frozen cohort and split

- Join the workbook to folders only by exact case-folded
  `(Object_name, Food_Type)`; exclude unmatched names rather than correcting
  them by guesswork.
- Exclude objects with missing `Weight (g)`.
- Require at least one frame shared by `original`, `masks`, and `segmented`.
- Use one frame per physical object: the middle numerically sorted shared
  frame. All frames from an object remain in that object's partition.
- Sort category and object keys, then shuffle object keys within each category
  with Python `random.Random(20261030)`. Assign one object per category to
  test; assign a second to dev when category support is at least three; assign
  all remaining objects to train. Categories with two objects have no dev
  object. This is a known-category, unseen-object split.
- The generated `split_manifest.jsonl` is written before features or metrics
  are computed and is the authoritative split record.

## Baseline and single candidate

- Baseline: category median of training-partition object weights.
- Candidate: frozen cached ImageNet-V2 ResNet-50 features from the full RGB
  frame, plus ground-truth mask area/bounding-box descriptors and workbook
  category one-hot features; fit a ridge regressor on `log1p(weight)`.
- The RGB, category, and mask inputs are oracle-assisted relative to the app:
  the category is supplied from the workbook and the mask includes bowl and
  food. This cannot be presented as application-path performance.
- Select one ridge alpha on dev by object-weighted MAE in grams, tie-breaking
  toward the smaller alpha. Refit on train+dev and evaluate test once.
- All feature extraction and ridge solves require CUDA; abort if CUDA is
  unavailable. Do not fall back to CPU.

## Decision rule

Candidate passes this MetaFood3D-only benchmark only when test object-weighted
MAE is at least 10% below baseline, the paired 10,000-resample category
bootstrap 95% interval for candidate-minus-baseline MAE has upper endpoint
below zero, macro-category MAE is no more than 5% worse, and absolute signed
bias is no more than 5 g worse. If any condition fails, record failure and do
not retune on this test split.

Outputs are written under the Git-ignored
`datasets/raw/marker/metafood3d/experiment_outputs/` directory. No derived
weights or predictions are committed by the script.
