# Quickstart: Accuracy and Readiness Baseline

This is the reproducible execution path for the local accuracy/readiness work. It does not acquire datasets or change model weights.

## Current deployment assumptions

- API: FastAPI `POST /analyze` multipart fields `file`, `day`, `band`, and optional `serving_style`; `GET /health`, `/menu`, `/goals` remain separate routes.
- Uploads are streamed to a temporary file and rejected above `NUTRISENSE_MAX_UPLOAD_BYTES` (default 12 MiB). Temporary files are removed in `finally`; inference runs in a worker thread behind a per-process limiter.
- Local measured profile device: NVIDIA GeForce RTX 4060 Laptop GPU, 8 GB VRAM, Python 3.14.7, torch 2.13.0+cu130. This is a development laptop profile, not a declared deployment target or service-level objective.
- The current wire contract is generated from `engine/contract.py` by `python -m tools.gen_contract_ts --write`. Nutrition trace is additive and optional for older clients.

1. Confirm local sources and licenses using `datasets/README.md`, `datasets/registry.csv`, and `datasets/finnfoodpics/README.md`. Keep WED/Nutrition5k at their existing paths.
2. Regenerate the existing deployable WED evaluation report on DEV only with `.venv/bin/python -m tools.run_eval --tier dev`. Note: this DEV tier is the deterministic 10% plate carve from WED TRAIN used for epoch selection, not a second independent holdout. DEV comparisons are development/model-selection evidence only; repeated iterations can overfit this signal. Save the checkpoint/config/revision and prediction-level output.
   Then generate the extended error profile with `.venv/bin/python -m tools.eval_weight_diagnostics --out data/reports/run_eval_diagnostics_dev_008.json`; it reports signed bias, RMSE, portion-size bands, plate totals, and a leave-one-plate-out affine-calibration analysis. The calibration analysis is exploratory and is not used in serving.
3. Build a group-aware manifest for currently local sources. FinnFoodPics uses `.venv/bin/python -m tools.build_finnfoodpics_manifest`, which groups all calorie tiers by snack identity and flags identities without workbook labels. Exclude incomplete ITD from training; do not treat gallery images as weighed data. Preserve Nutrition5k official split and hold out whole physical portions for ECUSTFD.
4. Audit leakage and label semantics; report row counts by source/group/split/target before training.
5. Run one-source-at-a-time ablations against the same WED DEV records: WED-only baseline, WED+Nutrition5k, WED+ECUSTFD if compatible labels are verified, then a FinnFoodPics auxiliary task/controlled snack analysis. Do not merge FinnFoodPics calorie values into WED gram targets.
6. Audit the existing 23 local ArUco captures and filenames. Score only existing labels that map unambiguously to the pictured food and tare-corrected weight. If current groups are too few for a held-out evaluation, use the set only for spot checks and say marker-domain accuracy is not established.
7. Use group-disjoint calibration data for uncertainty. The existing leave-one-plate-out calibration audit (`tools/calibrate_intervals.py`, ledger 004) found no calibration that meets both 90% coverage and the pre-registered +25% width cap; it did not alter deployed intervals. The existing API contract tests cover malformed and oversized files and inference serialization. `docs/perf_baseline.md` is an engine-stage profile, not a declared API latency budget.
8. After the candidate and thresholds are frozen using TRAIN-carve/DEV evidence, run one final WED LOCKED report under the repository's access protocol and record the access/report. Do not reuse it for tuning. Never use the LOCKED score to choose or revise a model, threshold, or claim.

The documented current reference is WED DEV MAE 15.034 g over 108 views / 21 plates, plate-bootstrap 95% CI [12.227, 18.889] g. This value is a baseline, not a promised result or a claim about LOCKED performance. This workflow uses existing local data only and does not require additional collection or annotation.
