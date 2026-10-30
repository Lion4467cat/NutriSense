# Model and service readiness status

Status as of 2026-10-30. This records evidence for the current local build;
it is not a production deployment approval.

## Model quality and generalization

- Current deployable WED head: `data/weight_head.pt`; current DEV baseline:
  15.034 g MAE, 108 views, 21 plates, 1,218 ROIs. The paired plate
  bootstrap CI for the mean MAE is 12.227–18.889 g.
- The DEV carve is made from WED TRAIN plates and is also used for epoch
  selection. It is useful for development comparisons, but repeated tuning
  can overfit it; it is not an independent generalization estimate.
- After the frozen model and thresholds were selected, the one-time WED
  LOCKED report measured 14.667 g MAE over 2,793 ROIs / 48 plates (plate
  bootstrap 95% CI 13.331–16.029 g). Nominal 90% interval coverage was
  82.77%. The report is `data/reports/run_eval_locked_final_008.json`; access
  is recorded in `docs/locked_access_log.txt`. This is reporting evidence
  only and must not be used for tuning.
- DEV candidates from ledgers 017–019 and the stronger augmentation from
  ledger 006 were rejected. One preregistered TRAIN-only candidate (10x
  AdamW decay, ledger 021) lowered pooled outer-CV MAE by 0.148 g with paired
  plate-bootstrap CI [−0.281, −0.016], but it regressed the 62-ROI boondi
  class by 39.1%, failing its predefined subgroup guardrail. It was rejected;
  the deployed checkpoint and sigma remain unchanged.
- Five-fold outer cross-validation was run over WED TRAIN plates, with the
  fixed 21-plate DEV carve excluded from all fold training and epoch
  selection. The pooled held-out estimate is 16.421 g across 11,759 ROIs / 198
  plates; fold MAEs are 15.684, 15.720, 16.184, 16.521 and 18.096 g (fold
  standard deviation 0.884 g). This is a TRAIN-only grouped generalization
  estimate, not candidate-vs-baseline evidence and not a LOCKED comparison.
  Exact per-plate aggregation: `data/reports/cv_weight_head_s42_k5_wd1e-4.json`.
- WED plates remain grouped together. Dataset manifests preserve source,
  group, target meaning/unit, license and explicit training eligibility;
  exact-image/group audits pass for the locally generated manifests.
- Source decisions are in `docs/ledger/020-model-readiness-source-decisions.md`.
  Only WED has verified labels compatible with the deployed plate-mass head.

## Uncertainty and user-facing recovery

- Group-disjoint leave-one-plate-out calibration was measured in ledger 004.
  The global multiplier needed for 90% coverage grew interval width by 47%,
  beyond the pre-registered 25% cap. Per-class calibration also missed both
  the coverage and width gates. No calibration was applied; nominal intervals
  remain under-covered on the measured DEV carve (85.22%).
- Existing API behavior has deterministic handling for unreadable images,
  oversize uploads (413), invalid capture fields, missing/undersized scale
  markers, classifier abstention, and failed stages. Low-confidence or
  unsupported captures abstain/return `cannot_verify`; prior-scale estimates
  carry an explicit disclaimer. Inference is serialized per process and
  temporary uploads are removed in `finally`.
- `/analyze` preserves its existing top-level keys. Nutrition provenance is
  an additive optional field with the composition-table SHA-256, component
  grams, kcal/protein densities and point contributions. The current local
  table does not support fat/carbohydrate trace values.
- The exploratory Nutrition5k test report scores 47 dish-ID-held-out dishes.
  The candidate's unfiltered all-slot output has 3,208.595 g total-mass MAE,
  2,916.463 kcal MAE, 127.240 g fat MAE, 349.343 g carbohydrate MAE and
  126.724 g protein MAE. Because absent ingredient slots were masked during
  training, that full-head result is not a usable meal prediction. An
  oracle-present-ingredient diagnostic (which uses held-out ingredient labels
  and is therefore not deployable) has 88.262 g mass MAE, 116.261 kcal MAE,
  7.068 g fat MAE, 9.451 g carbohydrate MAE and 7.273 g protein MAE. Both
  outputs and hashes are in `data/reports/nutrition5k_test_nutrients.json`;
  neither is a serving claim or comparable to WED school-mode MAE.

## Runtime and deployment

- `docs/perf_baseline.md` records an older in-process RTX 4060 GPU profile;
  those stage timings are not HTTP endpoint timings.
- `data/reports/api_benchmark_rtx4060.json` measures the actual `/analyze` API
  through local Uvicorn on the NVIDIA GeForce RTX 4060 Laptop GPU (8 GB VRAM).
  On a real canteen photo, two sequential scored requests had p50 8.263 s and
  p95 8.338 s; all requests returned HTTP 200 and verdict `FAIL`. Uvicorn
  peaked at 4,880 MiB RSS; system GPU memory rose 5,413 MiB above its 142 MiB
  baseline. The two scored calls are insufficient for a stable percentile.
- Eight-call follow-ups on an existing WED image and the demo thali image
  measured p95 735 ms and 751 ms, respectively, but every request returned
  `cannot_verify`. These characterize the fast abstention path, not successful
  meal analysis. Reports: `api_benchmark_rtx4060_final.json` and
  `api_benchmark_rtx4060_thali.json`.
- `tools/benchmark_api.py` records the image hash rather than the local path.
- The only measured target is the local RTX 4060 development laptop. No
  deployment hardware, concurrency target, service SLO, request timeout, or
  memory budget has been agreed. Therefore production latency/resource
  acceptance is **not established**. Before deployment, agree those budgets
  and run the benchmark on the target container/device.
- Existing API tests cover malformed and oversized input and the single-
  process inference limiter. The benchmark is sequential; multi-worker
  concurrency, sustained load, cold-start distribution and remote network
  behavior remain unmeasured.

## Real-capture weighed-plate pilot (EVAL-ONLY)

The 2026-10-30 pilot covered 23 angle views of six unchanged plates. The
food-only plate totals were confirmed by the user; plate and bowl tares were
excluded. The run used `day=mon`, `band=1-5`, and `serving_style=mixed`, with
GPU-only sequential model loading. There were 20 measured-anchor views and
three prior-anchor views. Full per-image scores and diagnostic evidence are
in `experiments/oracle_ablation/REPORT.md`, with raw outputs and reproduction
scripts in `experiments/oracle_ablation/`.

The measured item-mask areas summed to 2.84–7.71 times the corresponding
top-level food-mask area on multi-item records. The card-versus-forced-prior
comparison had 14 same-image pairs with valid grams from both paths: card MAE
805.4 g, forced-prior MAE 203.2 g. This small pilot does not establish
generalization or production accuracy; the prior result may benefit from
error cancellation. The ArUco plates are permanently EVAL-ONLY and cannot be
used to tune models, thresholds or fixes. The overlays support mask spill
and non-zero height on plate/rim/table context as hypotheses; they do not
isolate food or plate ground-truth masks.

## Remaining release gates

1. **Model quality (SC-002 unmet):** the 10x-decay CV candidate improved the
   pooled outer mean but failed the preregistered boondi subgroup guardrail;
   no candidate passes promotion. Keep the 15.034 g baseline. The CV folds
   are now development evidence and must not be retuned. The one-time LOCKED
   evaluation cannot be repeated.
2. **Uncertainty (SC-006 unmet):** current nominal 90% intervals under-cover;
   the measured calibration methods exceed the pre-registered width budget or
   miss coverage. Do not present them as calibrated confidence intervals.
3. **Nutrition (SC-008 unmet for production):** the Nutrition5k candidate is
   rejected and its full-slot end-to-end test is unusable. A validated food
   presence/identity and portion model plus compatible ground truth are
   required before calorie/macro accuracy claims.
4. **Operations (SC-007 unmet):** deployment device and numeric latency,
   memory, timeout, concurrency and error-rate budgets need to be agreed;
   then test cold start, sustained and concurrent traffic on that target.
5. **System-level metrics:** report recognition, segmentation/coverage,
   matched-item and complete-meal mass error, nutrition error, abstention and
   failure rates separately on representative, independently grouped data.

## Specification success-criteria status

| Criterion | Status | Evidence / remaining condition |
|---|---|---|
| SC-001 reproducible frozen baseline | Met | Baseline report pins model, data, split and code hashes. |
| SC-002 lower DEV MAE with paired guardrails | **Not met** | No candidate passed; retain 15.034 g DEV baseline. |
| SC-003 LOCKED used only after freeze | Met | One final report exists; access logged; no tuning from it. |
| SC-004 provenance and group leakage audits | Met for audited local manifests | Exact-hash and group audits report zero cross-split collisions. |
| SC-005 ArUco correspondence audit | Met as an audit and exploratory pilot | 23 images / 6 plates; user-confirmed food-only totals support plate-level scoring only. EVAL-ONLY; not a tuning set and not a generalization benchmark. |
| SC-006 uncertainty calibration and action | **Not met for confidence claims** | Calibration measured but misses coverage/width gate; abstention/recovery paths are tested. |
| SC-007 agreed operational budgets | **Open** | Local benchmark exists; intended hardware/SLO and sustained/concurrent evidence are missing. |
| SC-008 measured nutrition quality | **Not met for serving** | Exploratory held-out report exists, but no validated macro-capable candidate passes transfer. |

## Commands

```bash
.venv/bin/python -m tools.run_eval --tier dev
.venv/bin/python -m tools.eval_weight_diagnostics --out data/reports/run_eval_diagnostics_dev.json
.venv/bin/python -m tools.benchmark_api --image /path/to/plate.jpg --runs 8
.venv/bin/python -m tools.check_locked
```

## Verification record

- Focused checks: **13 passed** across weight-head loading, evaluation
  metrics, grouped CV split isolation, and Nutrition5k nutrient evaluation;
  the paired-CV comparison suite passed **2 additional tests** after its final
  split-identity checks were tightened. Nutrition provenance/happy-wire
  fixture check: 1 passed.
- Passed frontend suite: 70 tests across 11 files. Production frontend build
  completed; Vite reported the existing >500 kB bundle-size advisory and
  dependency annotation warnings.
- Passed repository Ruff check and `.venv/bin/python -m tools.check_locked
  --quiet`.
- Passed exact-image-hash manifest audits: Nutrition5k 555 images/555 dish
  groups; ECUSTFD 2,978 views/160 physical groups; FinnFoodPics 720 images/72
  identities. All reported zero cross-split group/path/hash duplication.
- One API happy-wire contract fixture check passed. Starlette's supported
  `httpx2` dependency is declared, locked, and installed. API `TestClient`
  requests hung in the restricted sandbox; the full API suite passed in the
  supported execution context. The real Uvicorn benchmark required the
  elevated local-server run.
- Five-fold WED TRAIN cross-validation ran with group-disjoint outer plates
  and the fixed DEV carve excluded. Pooled held-out baseline MAE was 16.421 g over
  11,759 ROIs / 198 outer plates; fold MAE standard deviation was 0.884 g.
- The paired regularization experiment compared identical outer plates and
  rejected the candidate on its boondi subgroup guardrail despite a lower
  pooled mean (report `compare_cv_weight_decay_021.json`).
- Nutrition5k held-out nutrient evaluation: 47 dishes scored. The full-head
  output is severely over-predictive because absent ingredient slots have no
  negative supervision. The oracle-present decomposition is explicitly
  non-deployable; both are documented in the report and no candidate was
  promoted.
- Full backend suite: **281 passed** in 109.46 s. The final focused paired-CV
  tests were run again after the split-identity validation change.
- API integration suite: **9 passed** (also included in the full backend
  count). The happy-wire check passed separately with optional nutrition
  provenance.
- Frontend: **70 tests passed** across 11 files; `npm run build` succeeded.
  Vite reported existing dependency-comment and >500 kB bundle advisories.
- Repository Ruff check, `git diff --check`, WED evaluation lock guard, and
  three exact-image-hash dataset audits passed.
