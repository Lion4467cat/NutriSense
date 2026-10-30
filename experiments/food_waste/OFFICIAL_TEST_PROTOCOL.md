# AI-ServicesBB official test: frozen external evaluation

Registered before fetching test rows or images. This is an inference-only
external evaluation of the unchanged current pipeline. Its results are
evaluation-only and must not be used for tuning, training, threshold changes,
or candidate selection.

- Dataset: `AI-ServicesBB/food-waste-dataset`, pinned revision
  `f008d0c7b41ea4408b66bd1b7bb9ecd58b70349d`; author repository and dataset
  card state CC BY 4.0 with attribution.
- Split: fetch only the source's official `test` split (expected 160 rows / 4
  receipts). Do not access train rows in this run.
- Group: `bonid` identifies one meal; all repeated views stay together.
- Target: sum `Menge_Rückläufer` per receipt, food-only returned grams.
  `Gewicht_nachher` includes the plate tare and is not used as food truth.
- Pipeline receives only image bytes, EXIF, `day=mon`, `band=1-5`,
  `serving_style=mixed`; labels are attached after inference.
- Require CUDA; fail if unavailable, with no CPU fallback. Models are loaded
  sequentially and unloaded after inference.
- Save all per-image outputs and timing to `raw_official_test.jsonl`; score
  per receipt and report abstentions, dish labels, verdict, and mask evidence.
- Never re-use this official test split for model development. No tuning or
  production promotion is authorized from this evaluation.

Run from the repository root:

```bash
./.venv/bin/python experiments/food_waste/run_official_test.py
./.venv/bin/python experiments/food_waste/summarize.py \
  --input experiments/food_waste/raw_official_test.jsonl \
  --mask-audit experiments/food_waste/mask_audit_official_test.jsonl \
  --output experiments/food_waste/RESULTS_OFFICIAL_TEST.md
```
