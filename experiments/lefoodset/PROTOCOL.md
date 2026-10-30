# LeFood-Set external-food-mass experiment protocol

Registered before running NutriSense on any LeFood image. This protocol keeps
all views of a food category together and reserves the test categories for a
single final comparison. The benchmark is a cross-domain, single-food plate
task; it does not represent mixed Indian meals.

- Source: LeFood-Set V1, Mendeley Data DOI `10.17632/cchsk79jkt.1`, CC BY 4.0.
- The public description claims 524 before/after pairs. The workbook has more
  rows than the archive contains complete image pairs; include only rows for
  which both workbook filenames exist in the pinned archive. Record omitted
  workbook rows and source archive hash in the generated manifest audit.
- Group split: group by the workbook food-name field, SHA-256 order using the
  fixed seed string in `audit_dataset.py`; first 70% of food names to train,
  next 15% to dev, final 15% to test. Before and after images from a row share
  the same group/split. Never use test categories to train or select a model.
- Primary target for the single-image baseline: `Weight Before Eaten (g)`,
  which the Mendeley record describes as food weight. The paper describes
  weighing the plate containing food but does not state the tare procedure;
  therefore all grams results must retain this target-semantics caveat.
- Ground-truth labels, categories, and weights are not sent into
  `engine.pipeline.analyze`. Only the before image, its EXIF, `day=mon`,
  `band=1-5`, and `serving_style=mixed` are supplied.
- Run the unchanged current pipeline only on the preassigned test categories
  for its one-time baseline; do not inspect those results to modify a
  candidate. One research candidate is preregistered: a frozen DINOv2-S
  encoder with a scalar grams head trained on train-category images, using
  square-root grams targets and minimum dev-category MAE for epoch selection.
  Compare it on dev against the global median mass from train only. Candidate
  training/selection may use train/dev only. If retained, it may be evaluated
  once on test against that train-only global-median baseline and the already
  frozen pipeline coverage result. No test result may trigger another model
  attempt.
- Require CUDA and fail rather than using CPU. Run Python from `.venv`.
- Keep raw data ignored under `datasets/raw/`; keep manifests, protocol,
  reports and reproducible scripts under `experiments/lefoodset/`.

Rebuild the audit/manifest, then run the frozen baseline from the repository
root:

```bash
./.venv/bin/python experiments/lefoodset/audit_dataset.py --extract
./.venv/bin/python experiments/lefoodset/run_baseline.py
./.venv/bin/python experiments/lefoodset/train_candidate.py
./.venv/bin/python experiments/lefoodset/evaluate_candidate_test.py
```

This is a research transfer check. It cannot support production claims for
mixed Indian meals, and source tare correction remains unspecified by the
paper.
