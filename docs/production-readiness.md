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
  WED remains the only source with verified labels compatible with the
  deployed class-conditional plate-mass head. GTMensa adds tare-corrected
  mixed-meal totals for a separate scalar research task; its candidate is not
  compatible with the serving head or promoted.
- A separate research-only MetaFood3D benchmark used 630 exact-join weighted
  single objects with a grouped 416/106/108 split. The image-plus-supplied-mask
  candidate was worse than the category-median baseline on both dev (121.994
  vs 83.742 g MAE) and test (71.777 vs 55.832 g MAE); the paired test interval
  crossed zero. No serving change was made. This is not mixed-plate evidence,
  and MetaFood3D's CC BY-NC terms do not clear commercial product use. Details:
  `experiments/metafood3d/RESULTS.md`.
- The AI-ServicesBB Food Waste author `test` split was evaluated once, grouped
  by its four receipts (160 repeated post-meal views; food-only returned grams).
  The frozen WED-trained pipeline returned numeric totals on 67/160 views and
  abstained on 93/160. Three receipt means with numeric output overpredicted
  by 25.6–80.1 g; the fourth receipt had no numeric outputs. Every numeric
  top-level classification was `vegetable_rice`, with no exact component-name
  matches against the German labels. In 30 multi-item views, item-area sums
  were 1.046–99.575 times the top-level food-mask area; 28 views had an
  overlap/area flag. This is a small, cross-domain post-meal diagnostic, not a
  serving accuracy claim; the official test split is closed to development.
  Per-receipt and per-view scores, raw JSONL, and replayed mask audit:
  `experiments/food_waste/RESULTS_OFFICIAL_TEST.md` and adjacent artifacts.
- LeFood-Set V1 supplied 524 complete before/after pairs in 34 Indonesian food
  categories. The frozen pipeline abstained on all 143 images in six held-out
  categories, so it produced no numeric serving estimates on that split. One
  preregistered, research-only scalar image regressor was tested once: 69.050 g
  MAE versus 75.168 g for a train-only global-median baseline, but predictions
  had −60.061 g signed bias and collapsed mostly near 50 g, with 307 g absolute
  error on the single 343 g Bubur example. This is not a production breakthrough
  or evidence for mixed Indian meals. The test categories are closed to further
  development. The source calls its targets food weights, while its paper
  describes weighing a plate containing food without documenting tare handling.
  Protocol, data audit, raw rows, and reports: `experiments/lefoodset/`.
- The VLM Food Benchmark provides 200 mixed canteen meals and 870 manually
  checked item weights; its source states empty-plate tare was subtracted.
  We froze participant groups before inference (106 train / 34 dev / 60 test;
  participant 6 held out). On that one photographer/device test group, the
  unchanged serving path returned `cannot_verify` on 60/60 images. One
  research-only DINOv2-S total-mass head scored 148.018 g MAE versus 172.017 g
  for the train+dev median, a 23.999 g reduction, with −106.880 g signed bias.
  All 60 serving-path images used the prior anchor and abstained at
  classification; best gallery scores ranged 0.599–0.765, below the current
  0.80 acceptance score.
  The dev split averaged 1.06 items and 320.2 g per image, versus 5.06 / 712.4 g
  in train and 4.97 / 761.9 g in test; the paper describes the dev participant's
  images as home-prepared, unlike the canteen setting. This may have affected
  epoch selection and bias, but is only a hypothesis.
  In the same sequential in-process pipeline run, per-image latency was 0.439 s
  median / 0.467 s p95 after a first call of 18.571 s (model load included).
  This is not an HTTP or sustained-load benchmark.
  The candidate is not integrated; this modest gain on one non-Indian canteen
  cluster does not validate Indian meals. Full per-image outputs, timing,
  scripts, source revision, and split manifest are in
  `experiments/vlm_food_benchmark/`.

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
- `/analyze` now has a per-process admission cap, default two requests, before
  multipart parsing and the explicit temporary-file copy. An excess request
  gets 503 plus `Retry-After: 1`; CORS remains on this response. The focused
  concurrency check holds one fake inference, admits one waiter, rejects a
  third request without creating a temp copy, keeps `/health` responsive, and
  verifies cleanup. This bounds one worker's admitted requests; deployment
  concurrency and resource budgets remain open, and worker count multiplies
  the cap.
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
- On 2026-10-30, a six-call sequential `/analyze` run on an AI-ServicesBB
  development image measured p50 4,569.8 ms and p95 4,600.7 ms; all seven
  requests returned HTTP 200 and verdict `FAIL` (a compliance verdict, not an
  inference exception). Peak Uvicorn RSS was 4,550.9 MiB; peak system GPU use
  was 5,276.9 MiB. The report and image hash are in
  `experiments/food_waste/api_benchmark.json`.
- A separate warmed one-worker test with two synchronized requests returned
  HTTP 200 for both, with request times 4,514.4 and 9,082.8 ms and joint wall
  time 9,087.7 ms. Peak Uvicorn RSS was 4,543.6 MiB and sampled system GPU use
  was 5,276.9 MiB. This is a two-request smoke check, not sustained-load
  evidence; see `experiments/food_waste/api_concurrency.json`.
- **Provisional local operational target chosen for the RTX 4060 Laptop GPU
  (8 GB):** one Uvicorn worker per GPU; at most two admitted `/analyze`
  requests per worker; warm sequential p95 ≤6 s; two simultaneous requests
  complete within 10 s each; system GPU use ≤7 GiB; cold first request ≤35 s.
  These are local acceptance budgets, not measured deployment guarantees.
  Current one-run observations fit those bounds (cold first request 31,860 ms),
  but repeated cold-start, sustained-load, remote-network, and target-container
  behavior are still unmeasured.
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
| SC-007 agreed operational budgets | **Open (local target chosen)** | Provisional RTX 4060 budgets are documented; repeated cold-start, sustained, remote and deployment-container validation remain. |
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
- A prior local verification record reports the full backend suite as
  **281 passed** in 109.46 s. The 2026-10-30 verification attempt below did
  not reproduce that full-suite pass in the restricted environment.
- API integration suite: **9 passed** (also included in the full backend
  count). The happy-wire check passed separately with optional nutrition
  provenance.
- Frontend: **70 tests passed** across 11 files; `npm run build` succeeded.
  Vite reported existing dependency-comment and >500 kB bundle advisories.
- Repository Ruff check, `git diff --check`, WED evaluation lock guard, and
  three exact-image-hash dataset audits passed.

## Verification attempt for the current branch (2026-10-30)

Commands were run from the project checkout with its `.venv` activated.

- `pytest --collect-only -q`: **281 collected** (271 non-GPU, 10 GPU-marked).
- `pytest -q`: did not complete; interrupted after it stopped making progress.
  The isolated `tests/test_contract_gen.py::test_unreadable_fixture_matches_wire`
  attempt timed out at 25 seconds after app startup logged
  `torch.cuda.is_available()=False` and selected CPU inference. The no-GPU
  suite with `tests/test_api.py` excluded also stopped making progress, so no
  passing full-suite claim is made for this environment.
- Frontend: **70 Vitest tests passed**; `npm run build` succeeded. Vite emitted
  its existing dependency-comment and >500 kB bundle advisories.
- `.venv/bin/python -m tools.check_locked`: **502 ok, 0 skipped, 0 failed**.
- `UV_CACHE_DIR=/tmp/nutrisense-uv-cache uv lock --check`: passed.
- `ruff check .`: failed with **18 findings**, concentrated in
  `experiments/oracle_ablation/` diagnostic scripts.
- `.venv/bin/python -m tools.pyright_gate`: failed at **214 errors vs baseline
  209** (five above the recorded baseline). The baseline was not changed.
- GitHub Actions run [41075108677](https://github.com/Lion4467cat/NutriSense/actions/runs/41075108677)
  for PR #3: frontend job passed; backend job failed at the Ruff lint gate
  before the Pyright and pytest steps ran.

These are verification outcomes, not changes to the evaluation protocol. The
ArUco plates remain permanently EVAL-ONLY; none of these results authorize
tuning or promotion of a serving-path candidate.

## Continued work (2026-10-30)

- Rechecked CUDA in `.venv`: PyTorch 2.13.0+cu130 and RTX 4060 were available.
- MetaFood3D candidate benchmark used 630 group-disjoint weighted objects and
  failed against its category-median baseline; no serving change was made.
  See `experiments/metafood3d/RESULTS.md`.
- Bounded `/analyze` admission as described above. Verification:
  `.venv/bin/python -m pytest -q tests/test_api.py` — 9 passed;
  `.venv/bin/python -m ruff check main.py tests/test_api.py` — passed;
  `.venv/bin/python -m py_compile main.py tests/test_api.py` — passed;
  `git diff --check` — passed.
- The API overload policy is now explicit and bounded, but its cap has not
  been validated against deployment concurrency, latency, or resource budgets.
- Added an attributed, CC BY 4.0 cross-domain development source from
  AI-ServicesBB. The unchanged pipeline was run on all 215 images across the
  12 receipts in its author `train` split and then on its 160-image,
  four-receipt official `test` split once; both are now closed for their
  respective development/evaluation roles. It abstained on 144/215 train
  views. Seven train receipts had
  numeric output: six were over the food-only return weight and one was under;
  five receipts had no numeric output at any angle. The mask audit found
  plate-sized overlapping item masks across both phases. Hypothetical duplicate
  drops did not recover measured totals. No pipeline change or candidate
  promotion was made. The initial and extended protocols, scripts, raw JSONL,
  and per-view reports are in `experiments/food_waste/`.
  The largest error in this split was 679.6 g vs 218.0 g while verdict was
  `PASS`; its reason says all mandatory nutrients were in the pass zone. The
  runner attaches food-weight truth after inference, and no target leakage is
  evident at the `pipeline.analyze` call boundary. `PASS` is not a mass-accuracy
  claim.
- LeFood-Set V1 was downloaded under its CC BY 4.0 terms and audited as a
  category-grouped source: 524 complete pairs, 34 categories, with 154
  workbook rows absent from the archive. The current pipeline's one-shot
  held-out evaluation abstained on 143/143 images. A single preregistered
  research candidate lowered MAE by 6.118 g versus the train-only median
  baseline, but had −60.061 g signed bias and severely underestimated high-mass
  portions. It is not integrated into serving. The held-out categories are
  closed; no production model or accuracy claim follows. See
  `experiments/lefoodset/`.
- The CC BY 4.0 VLM Food Benchmark was selectively downloaded at pinned source
  commit `d715df0c0debe65da805618431e67f6d0fa01c71`; code under the source repo
  is MIT. Its 200 photos have 870 item weights with tare subtracted. A
  participant-held-out scalar DINOv2-S candidate reduced test MAE by 23.999 g
  against the train+dev median, but retained −106.880 g bias; the serving path
  abstained on all 60 test images. This is the clearest measured mixed-meal
  transfer lead found so far, but it is still one non-Indian participant
  cluster and not a serving candidate. See `experiments/vlm_food_benchmark/`.

## Final repository and application verification (2026-10-30)

Commands ran from the project root. Python commands used the project `.venv`;
the full pytest run included the GPU-marked model tests.

| Command | Result |
|---|---|
| `.venv/bin/pytest -q` | `281 passed in 107.83s (0:01:47)` |
| `npx tsc --noEmit` (from `frontend/`) | Passed, no diagnostics. |
| `npm test` (from `frontend/`) | `11` files passed; `70` tests passed. |
| `npm run build` (from `frontend/`) | Passed in `2.16s`; Vite emitted dependency-comment advisories and a `562.80 kB` JS chunk warning. |
| `uv lock --check` | Passed; `Resolved 93 packages in 24ms`. |
| `.venv/bin/ruff check main.py tests/test_api.py` | Passed. |
| `.venv/bin/ruff check .` | Failed: `Found 48 errors`; most are in diagnostic/research scripts. No autofix was run. |
| `.venv/bin/python -m tools.pyright_gate` | Failed: `214 errors (baseline 209)`, five over baseline. `pyright.baseline` was not changed. |
| `.venv/bin/python -m tools.check_locked` | `502 ok, 0 skipped, 0 failed (502 pinned)`. |
| `git diff --check` | Passed. |

The protected-path diff against `4f313fd` is limited to the known existing
changes in `docs/locked_manifest.txt` and `tools/compare_runs.py` (4 and 121
changed lines respectively). Neither file was edited in this cleanup.

### Two-mode UI smoke test

The live UI and backend were opened locally with the RTX 4060 Laptop GPU
available (`torch 2.13.0+cu130`, CUDA available). One ordinary gallery image,
`../DATASET/vegetable_rice/IMG20260825130507.jpg` (SHA-256
`443de7da6c7b16aa941d6d811a601104be0d44ab9e316e5cb0ee74728affb838`), was
analyzed once with `Monday`, `Classes 1-5`, and `mixed`, then the same stored
result was viewed in both modes:

- **School:** prior anchor, `vegetable_rice`, `90.6 g`, `FAIL`.
- **General:** same `90.6 g` estimate; `136 kcal`, `3.2 g` protein; displayed
  shares were `9%` of the `1450 kcal` default daily goal and `15%` of the
  `21.4 g` default protein goal. No personal profile was entered, so these
  are first-served defaults, not personalized targets.
- **Observed UI discrepancy:** the dish card shows `Confidence 35%`, while its
  measurement details report gallery match `0.9451655745506287` (about `95%`).
  This was recorded without changing code.

Uvicorn logged CUDA as available and selected `cuda` for segmentation,
classification, and depth. The `/analyze` request returned HTTP 200. Its
reported stage times were input `0 ms`, anchor `62 ms`, segmentation
`11,526 ms`, classification `10,563 ms`, depth `7,619 ms`, portion `311 ms`,
nutrition `9 ms`, and compliance `0 ms`. First-request logs also showed
Transformers compatibility/configuration warnings for model loading; inference
still completed and returned the result above. These are timings for one cold
local request, not a latency distribution or deployment benchmark.

This gallery-photo run is an application smoke test only; it has no weighed
truth and supports no accuracy claim. The UI stored one analysis in local
browser history. The app smoke output and complete cross-dataset limitations
do not make the product production-ready: global Ruff and Pyright gates remain
red, and independent representative Indian mixed-meal evidence is still
missing.
