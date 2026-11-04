# Synthetic Food Data Evaluation

The renderer, provenance records, split audit, review queue, paired-scene checks, GAN training path, and promotion helper are implemented. Clean component baselines now run for classification and multi-item segmentation; the full all-stage freeze, diffusion adaptation/training, downstream ablation runner, and post-freeze ArUco inference report remain unfinished. Do not run candidate generation or training until a clean baseline freeze exists.

Generated images, label maps, caches, and checkpoints belong under the ignored `datasets/processed/` directory and must not be committed.

## 1. Check baseline readiness

```bash
.venv/bin/python -m tools.run_synthetic_baselines \
  --out data/reports/synthetic_baseline_preflight.json
```

The command builds a balanced gallery from WED TRAIN groups outside the fixed DEV carve, evaluates it on ground-truth DEV food crops, then scores the multi-item segmenter against WED DEV semantic masks. It records evidence gaps and returns exit code 2 while any stage remains missing or unreviewed. The current repository is in that state. A reviewed `experiments/synthetic_food/baseline_freeze.json` must contain `"frozen": true` and, for each of `classification`, `segmentation`, `depth_geometry`, `weight`, and `end_to_end`, non-empty metrics, a positive group count, uncertainty, and `model_sha256`, `data_sha256`, and `split_sha256` before corpus generation or generator training is permitted.

The 2026-11-02 WED DEV reports are under `experiments/synthetic_food/`; findings and caveats are recorded in `experiments/synthetic_food/baseline_findings.md`. Classification top-1 is 0.762 on ground-truth food crops. The multi-item segmenter has union-mask IoU 0.192 and an IoU-0.5 per-dish coverage proxy of 0.164; this proxy is not a vessel-recall score. The renderer-grounded raw MoGe metric-depth baseline is very poor (no-card food AbsRel 5.925, MAE 2.410 m; card food AbsRel 9.403, MAE 3.824 m). The original-image end-to-end DEV baseline returns a mass for all views but has meal MAE 611.35 g and 100% critical failure under the complete-item gate. The prior geometry mass diagnostic has 1,524.3 g per-region MAE, 4,618.7 g merged-meal MAE, and 33 failed ROI extractions. These results establish a measured starting point, not a passing quality gate. See `experiments/synthetic_food/protocol.md` for limitations and exact report paths.

## 2. Train the WED-only GAN (after baseline freeze)

```bash
.venv/bin/python -m tools.train_synthetic_methods \
  --method gan \
  --manifest data/wed_manifest.jsonl \
  --dataset-root data/wed \
  --output datasets/processed/synthetic_food_v1/models/gan.pt \
  --device cuda
```

This uses paired WED TRAIN images and label maps only, with a conditional generator/discriminator and no imported pretrained weights. Run it on the approved GPU host. The checkpoint receives a sidecar with its hash, dataset disclosure, split, and training configuration.

The diffusion adapter loads only local ControlNet/base directories and requires a `PROVENANCE.json` with hashes, revisions, license, training-data disclosure, and overlap review. No diffusion trainer or approved reviewed checkpoint is currently present; the adapter is not eligible for promotion until provenance review is recorded.

## 3. Generate the renderer or appearance-method corpus

After creating the reviewed baseline freeze:

```bash
.venv/bin/python -m tools.generate_synthetic_data \
  --method renderer --scene isolated_dish --samples-per-class 3

.venv/bin/python -m tools.generate_synthetic_data \
  --method renderer --scene composed_thali --samples-per-class 3
```

The generation command refuses to run without the five-stage frozen baseline. It reads only WED TRAIN rows, samples distinct physical groups and observed per-class portions, records the source image/mask hashes, and writes paired card/no-card samples. The class density comes from an explicit class assumption in `data/wed_dishes.yaml` / `data/menu.yaml`, or a clearly tagged fallback assumption. Broader portion ranges require a separately tagged experiment.

After training a local GAN state checkpoint, pass `--method gan --checkpoint <local-file> --revision <revision>`. For reviewed diffusion, pass its local model directory the same way. The appearance adapter edits only food pixels, restores renderer background and card pixels, and carries renderer labels forward; reviewers still judge class identity.

## 4. Complete human review and audit

```bash
.venv/bin/python -m tools.export_synthetic_review \
  --manifest datasets/processed/synthetic_food_v1/manifest.jsonl \
  --out datasets/processed/synthetic_food_v1/review_queue.csv
```

Fill the review columns by strata: class, observed portion range, method, card condition, and lighting. Then evaluate the review gate and save its summary:

```bash
.venv/bin/python -m tools.export_synthetic_review \
  --manifest datasets/processed/synthetic_food_v1/manifest.jsonl \
  --out datasets/processed/synthetic_food_v1/review_queue.csv \
  --apply-reviewed --min-acceptance 0.90

.venv/bin/python -m tools.audit_synthetic_manifest \
  --manifest datasets/processed/synthetic_food_v1/manifest.jsonl
```

Audit checks WED TRAIN lineage, output hashes, automatic geometry checks, complete card pairs, and a passing human-review summary. Samples with rejected class identity or geometry must be excluded from affected tasks.

## 5. Remaining experiment and final-report work

The condition planner validates the five ratios and equal total/per-class budgets after all three methods pass corpus review:

```bash
.venv/bin/python -m tools.run_synthetic_ablation \
  --stage classification --total-examples 4100 \
  --methods renderer gan diffusion
```

It writes an immutable plan but does not launch training. The runner that connects model-specific training/evaluation commands is not implemented yet. Tune classification, segmentation, depth/geometry, weight, then end-to-end behavior; do not substitute discriminator or visual-realism scores for real DEV task metrics.

Once candidate selection and thresholds are fixed, use the existing guarded WED LOCKED process exactly once. After freeze, run one exploratory mass evaluation for the six labeled ArUco meal groups, keeping tare separate from net component masses. No real depth accuracy claim is allowed without independent real depth ground truth.
