# AI-ServicesBB Food Waste cross-domain diagnostic

Status: pre-registered diagnostic of the current, unchanged NutriSense pipeline.
This is a development diagnostic, not a model-selection claim or a serving
change. Dataset terms on the original author repository and dataset card state
CC BY 4.0 for photographs and structured records; attribution is required.

## Data and target

- Source: `AI-ServicesBB/food-waste-dataset`, revision
  `f008d0c7b41ea4408b66bd1b7bb9ecd58b70349d` (dataset-card license CC BY 4.0).
- Read only the source's `train` split (215 rows, 12 receipts / `bonid`). Do not
  fetch, inspect, or evaluate its official `test` split in this diagnostic.
- One receipt is one physical meal after consumption and has repeated images
  (12–23 each). Split and score by receipt, never by image.
- Food-only target per receipt is the sum of the `Menge_Rückläufer` values
  (grams, ingredient-level returned food). Do not use `Gewicht_nachher` as food
  truth because that field includes the plate tare.
- No target, dish label, or ground-truth-derived value is passed to
  `engine.pipeline.analyze`.

## Fixed split

The 12 receipt IDs in the author-published train split are sorted by
`SHA256("nutrisense-food-waste-dev-20261030:" + bonid)`; the first four are
diagnostic DEV and the remaining eight are excluded from this inference run.
All views of a receipt stay together. At the time of this train-split run,
the author's four-receipt official test split was unopened and untouched. It
was later evaluated once under the separate frozen protocol in
`OFFICIAL_TEST_PROTOCOL.md`; that test is closed to development. This
diagnostic DEV cannot support a final generalization claim.

## Run and metrics

Run `./.venv/bin/python experiments/food_waste/run_diagnostic.py` from the
repository root. Require CUDA and fail rather than falling back to CPU. Use the
current `day=mon`, `band=1-5`, `serving_style=mixed`. Keep the serving pipeline,
weights, models, thresholds, and configs unchanged. Save one raw JSONL row per
image, including receipt ID, source image index, food-only target, complete
pipeline result, timing, and environment.

Report every diagnostic receipt separately: image count, target grams, each
image's predicted total and signed/absolute error, receipt-level min/max/range,
and mean absolute and signed error across its views. These repeated views do
not count as independent plates. Also report dish labels/verdicts and empty or
unmatched outputs. No pass/fail gate or tuning decision is defined by this
small development diagnostic.

## Guardrails

Never use the user's ArUco EVAL-only plates or WED LOCKED for development.
Do not tune this pipeline on the official Food Waste test split. Do not modify
pipeline models, thresholds, configs, or checkpoints. Raw downloaded images
stay under git-ignored `datasets/raw/`; generated logs stay in this experiment
directory. Cite the dataset and author code when redistributing derived
reports.
