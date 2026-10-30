# NutriSense technical project report

**Living report. Updated:** 2026-10-31
**Scope:** architecture, data and model provenance, measured quality, runtime,
known failure modes, and the gates for a defensible release. This is a
diagnostic synthesis; it does not promote a candidate or claim production
readiness.

## Executive status

NutriSense is a single-photo meal-analysis application aimed at Karnataka
PM POSHAN canteens. It combines reference-card scale detection, food-region
segmentation, dish recognition, portion estimation, nutrient lookup and a
policy-driven compliance verdict. A React client sends a capture to a FastAPI
service; the backend returns a structured analysis contract with intermediate
evidence and reason codes. General mode reuses some of the meal-analysis path
without the school-compliance policy.

The project has a reproducible, grouped WED weight-model workflow and an
unchanged serving checkpoint. Its strongest matching-domain point estimate is
**15.034 g DEV MAE** on the WED DEV carve (108 views, 21 plates, 1,218 ROIs),
but this carve also selects epochs and has already been used for candidate
selection. The one-time frozen WED LOCKED result is **14.667 g MAE** (2,793
ROIs, 48 plates); it is closed and is not a tuning signal. The five-fold,
plate-grouped WED TRAIN estimate is **16.421 g** pooled MAE over 11,759 held-out
ROIs and 198 plates. These are item/ROI-level WED numbers; they are not
whole-meal totals and should not be compared directly with scalar meal-total
benchmarks.

Transfer evidence is weaker. On the one-time participant-held-out GTMensa
comparison, a research-only scalar model reached **148.018 g plate-total MAE**
versus **172.017 g** for the train+dev median, with **−106.880 g signed bias**.
The unchanged serving path returned a numeric estimate for **0/60** test
images. This is not an Indian-meal result and the participant-6 group is
closed. The ArUco real-plate pilot is also EVAL-ONLY. No candidate currently
passes all quality, generalization, calibration, nutrition and operations
gates; therefore this project is **not production-ready for reliable
automated portion or nutrition claims**.

There is no defensible “lowest achievable MAE” yet. MAE depends on a declared
prediction target, population, grouping unit, capture protocol and frozen
test set. Existing WED evidence is spent for selecting another candidate; the
remaining local cross-domain tests are closed, mismatched, or do not provide
scale-ground-truth-compatible Indian mixed meals. The next meaningful step
for mass accuracy is a new, rights-cleared, independently grouped weighed
capture set, followed by preregistered development and a fresh holdout.

## Product and inference architecture

The current data path is documented in `README.md` and implemented primarily
in `engine/pipeline.py`:

1. **Capture/API boundary (`main.py`).** FastAPI exposes `/health`, `/menu`,
   `/goals` and `/analyze`. The upload path validates the image and capture
   fields, applies an upload-size limit, copies the image to a temporary file,
   runs inference through a per-process limiter and removes temporary files.
   An admission middleware bounds in-flight `/analyze` requests before
   multipart parsing. The middleware cap is per worker, not a global fleet
   limit.
2. **Scale anchor (`models/scale_anchor.py`).** A 60 mm ArUco reference card
   produces a measured tier when detected; otherwise the pipeline uses a
   prior tier. A prior anchor is disclosed as an estimate and degrades
   coverage. Card detection failure is not silently represented as a measured
   scale.
3. **Food segmentation (`models/dish_segmenter.py`).** SAM2.1 produces food
   regions. There is a separate multi-item path for detected vessels; each
   item is cropped/classified/portioned, then the meal result aggregates item
   portions. Real-capture diagnostics have shown unstable vessel counts and
   repeated component assignments.
4. **Dish identity (`models/food_classifier.py`).** SigLIP2 gallery similarity
   is the primary classifier, with text fallback. The wire carries distinct
   `classification.confidence` (top-1 softmax in gallery mode) and
   `classification.match_score` (best top-3-mean cosine gallery score); the
   UI labels them separately. Open-set acceptance is governed by the existing
   gallery threshold. Abstention is an intentional outcome when the match
   score is below that threshold.
5. **Depth/portion (`engine/depth.py`, `models/portion_estimator.py`,
   `models/weight_head.py`).** The measured-card geometry path estimates mass
   from scaled footprint × height above a fitted/prior base plane × effective
   density. Without a card, a mapped WED dish can use the frozen DINOv2-S
   class-conditional weight head; unavailable or failing mapped heads return
   `cannot_verify`, rather than silently swapping in geometry. Unmapped dishes
   use the explicitly uncertain geometry route when allowed.
6. **Nutrients/compliance (`engine/mc.py`, `engine/nutrients.py`,
   `engine/compliance.py`, `engine/gates.py`).** The pipeline propagates
   assumptions through Monte Carlo nutrient intervals and computes a
   PM POSHAN verdict from configured standards and coverage factors. Prior
   anchors and uncertain geometry constrain the verdict; nutrition-table
   values are not equivalent to independently measured nutrient ground truth.
7. **Wire/UI (`engine/contract.py`, `frontend/src`).** A Python-owned response
   contract carries verdict, reasons, failures, stage details, portion and
   nutrition provenance, model versions, policy digest and optional item
   results. The React UI presents the staged analysis and the uncertainty and
   abstention details.

Model instances are lazily loaded and shared via `models/registry.py`. The
service serializes GPU inference within one process. The current local test
hardware is an NVIDIA GeForce RTX 4060 Laptop GPU with 8,188 MiB reported
memory; CUDA is available in the project `.venv` as torch 2.13.0+cu130 / CUDA
13.0 (checked 2026-10-30).

## Task boundaries and current model inventory

| Subsystem | Current method/artifact | What its evidence supports | Main limitation |
|---|---|---|---|
| Anchor | ArUco card + prior fallback | Card scale can be measured when detected; tier is surfaced | Real-card mask/geometry contamination is not isolated by a valid broad test |
| Segmentation | SAM2.1 region masks | Synthetic and diagnostic capture behavior | Item masks may overlap or exceed the top-level food region; multi-item stability is not established |
| Classification | SigLIP2 gallery-first | Existing gallery classes on supported examples | Cross-domain labels may fall below acceptance; GTMensa test abstained on all images |
| Measured mass | Geometry from area, depth height and density | Synthetic behavior and WED ROI estimates | Depth/base plane, masks and density can contribute interacting errors |
| Prior-tier mass | Frozen DINOv2-S WED weight head for mapped dishes | WED DEV/CV and one final WED LOCKED report | Generalization to new dishes, phones, plates and Indian mixed meals is not established |
| Off-menu mass | Research ingredient/scalar candidates are gated or unpromoted | Experimental diagnostics only | No candidate passed an end-to-end transfer and nutrition gate |
| Nutrition | Composition-table arithmetic + Monte Carlo | Reproducible derived values and uncertainty propagation | No compatible independent nutrient ground truth demonstrates serving accuracy |
| Compliance | Rule/policy engine | Deterministic behavior under configured policy | A technically valid verdict does not prove portion/nutrient accuracy |

The deployed mass artifact and its provenance are described in ADR 0002 and
`docs/production-readiness.md`. The WED-derived checkpoint remains locally
usable, but its upstream dataset terms are unstated and a public release of
the trained artifact is gated pending written rights clarification (`M9` in
`docs/licenses.md`).

## Data inventory and eligibility

The working inventory is recorded in `datasets/registry.csv`, with detailed
target semantics, group definitions, licenses, and prior decisions in
`datasets/README.md`, `docs/licenses.md`, and the experiment folders. Main
families presently in the workspace include WED/ITD, Nutrition5k,
MetaFood3D, AI-ServicesBB Food Waste, LeFood-Set, ECUSTFD, FinnFoodPics and
the VLM Food Benchmark. The large raw directory is local research data and is
not a statement that every source is eligible for commercial training or
redistribution.

Eligibility differs by task:

- **WED** is the only local Indian plated-food source with per-item gram
  targets suitable for the current mass-head task. Its DEV, TRAIN-CV and
  LOCKED evidence have all been consumed for their documented purposes;
  LOCKED remains closed. Dataset terms are absent, and release rights for
  trained artifacts need written clarification.
- **ITD** supplies Indian multi-view images and segmentation masks, but no
  portion weights. The downloaded archive is 140 MiB. The dataset terms are
  unstated. It may inform segmentation research but cannot provide a mass
  training target or commercial-use clearance.
- **Nutrition5k** has measured American meal components and nutrient labels;
  its prior transfer experiments failed the serving promotion gate. The
  held-out outputs are closed to further tuning.
- **MetaFood3D** is a single-object marker/depth source. The grouped test
  candidate regressed against the baseline and its CC BY-NC terms do not
  clear commercial use.
- **AI-ServicesBB Food Waste** is post-meal data, not a full serving view; its
  official test is closed. **LeFood-Set** has a category-held-out test already
  used once and unresolved tare semantics. **GTMensa** is mixed-meal,
  tare-corrected cross-domain evidence; its participant-6 test is closed.
- **ECUSTFD** lacks verified usable portion mass in the local annotation
  copy. **FinnFoodPics** has identity/energy-tier data, not scale-weighed
  per-image grams. Neither should be converted into gram supervision by
  inference.
- **ArUco weighted plates** are user-confirmed real-plate EVAL-ONLY evidence.
  They must never be used for training, tuning, threshold selection, or fixes.

An external-source search on 2026-10-30 surfaced additional weighed datasets,
but none removes the Indian-domain evidence gap. Food Portion Benchmark has
measured grams and 14,083 images but is Central Asian and CC BY-NC 4.0; it is
research-only unless rights change. SimpleFood45 reports 513 smartphone
images with weight, volume and energy labels, but is a small collection of
single foods, not Indian mixed plates, and its terms need separate review.
The newer Weighed-Meal Reference Set mini-180 has weighed ingredients and an
open CC BY 4.0 tabular layer, but its photos are restricted by researcher-use
agreement and its cuisine buckets exclude South Asia. These can diagnose
transfer, not validate an Indian-serving claim. Source links and current
terms: [FPB dataset card](https://huggingface.co/datasets/issai/Food_Portion_Benchmark),
[SimpleFood45](https://lorenz.ecn.purdue.edu/~gvinod/simplefood45/),
[Weighed-Meal Reference Set](https://dietaryassessmentinitiative.org/datasets/weighed-meal-reference-set-180/).

## Evidence ledger: what the current numbers mean

| Evidence | Result | Valid interpretation | Not established |
|---|---|---|---|
| WED DEV | 15.034 g MAE; 108 views, 21 plates, 1,218 ROIs | Existing checkpoint point error on an already-used development carve | Independent generalization or a fresh candidate-selection opportunity |
| WED TRAIN grouped outer CV | 16.421 g pooled MAE; 11,759 ROIs, 198 plates | Plate-grouped estimate for the baseline recipe | Candidate improvement, because folds are now consumed development evidence |
| WED LOCKED | 14.667 g MAE; 2,793 ROIs, 48 plates; 82.77% nominal 90% interval coverage | One-time frozen-model reporting result | Retuning, recalibration, or repeated test claims |
| GTMensa participant-6 | Research scalar 148.018 g MAE vs median 172.017 g; bias −106.880 g; serving numeric coverage 0/60 | One external whole-meal transfer observation; current serving path abstained | Indian-domain performance, broad generalization, or production readiness |
| MetaFood3D grouped test | Candidate worse than category-median baseline | The attempted marker/depth transfer candidate did not show a useful gain | Mixed-plate accuracy |
| AI-ServicesBB official test | Numeric coverage 67/160; 93 abstentions; repeated post-meal views | Cross-domain failure/coverage diagnostic | Full-serving mass accuracy or independent image counts at the item level |
| LeFood-Set held-out categories | Pipeline abstained on all 143 images | Classification/coverage failure on those categories | Numeric mass accuracy or Indian-food performance |
| ArUco real-plate pilot | See `experiments/oracle_ablation/REPORT.md` | Per-image diagnostic on six user-weighed plates; EVAL-ONLY | Tuning evidence or a population accuracy estimate |

The current WED nominal 90% intervals under-cover on LOCKED (82.77%); existing
calibration attempts did not satisfy the width/coverage gates. Interval bounds
must not be presented as calibrated coverage until a fresh, suitable
calibration design passes its preregistered acceptance criteria.

## Current operational observations

The actual API timing reports and their caveats live in
`docs/production-readiness.md` and `experiments/food_waste/`. The measured
local RTX 4060 API examples include successful HTTP responses that still
returned abstentions or compliance failures. The report contains a two-call
real-canteen sample at p50 8.263 s / p95 8.338 s, faster abstention-path
samples around 0.7–0.8 s, and a separate development-image run near 4.6 s.
These inputs, output verdicts, and sample counts differ; do not compare their
latencies as if they were one distribution.

Provisional local operational targets are one Uvicorn worker per GPU, no more
than two admitted `/analyze` requests per worker, warm sequential p95 ≤6 s,
two concurrent requests each ≤10 s, system GPU use ≤7 GiB, and cold first
request ≤35 s. These are engineering budgets, not measured deployment
guarantees. Repeated cold starts, sustained load, network behavior,
multi-worker behavior, target-container tests, service-level failure rates
and memory headroom remain unverified.

## Failure modes and evidence-backed concerns

The following are observed or documented; the report does not rank them as
root causes:

- **Coverage / classification:** the GTMensa serving test abstained for every
  image, with best gallery scores below the existing threshold. Lowering the
  threshold based on this closed test would be invalid.
- **Item decomposition:** diagnostic multi-item photos assign the same
  component to multiple regions, and some item-mask areas exceed the
  top-level food region. Per-item gram output therefore needs duplicate and
  correspondence audits before it can be treated as an additive meal total.
- **Scale/depth/geometry:** synthetic card-placement trials show that the
  particular global-scale baseline was sensitive to card location, while
  homography-area estimates reduced synthetic spread. A later food-plane
  audit failed its registered criterion. These results do not validate a
  real-photo fix.
- **Base plane / vessel:** the ArUco overlays show non-zero estimated height
  in plate/rim/table context for selected frames. This is visual and
  diagnostic evidence on the EVAL-ONLY set, not isolated food-volume truth.
- **Nutrition:** density/composition lookups are arithmetic inputs; no
  compatible independent nutrient assay set has established end-to-end
  calorie or macro error for the serving path.
- **Uncertainty:** nominal intervals miss the existing coverage target; a
  verdict's compliance coverage is a policy gate, not a calibrated
  probability that grams are correct.

## Production-readiness gates

Current status is **not ready**. Close each gate with evidence matched to its
claim, not by substituting one benchmark for another.

1. **Rights:** obtain written terms for WED/ITD and any other data/model
   artifact intended for commercial distribution or deployment. Maintain
   source-specific attribution and artifact lineage.
2. **New ground truth:** collect permissioned, representative Indian
   mixed-meal images with per-component scale weights, empty-container tare,
   component labels, plate/session/device/person groups, repeated angles and
   documented camera metadata. Freeze a development partition and untouched
   independent holdout before any modeling.
3. **Target/metric contract:** declare whether each metric is per-item grams,
   per-plate total grams, component recall/coverage, or nutrients. Publish
   both unconditional errors and numeric coverage/abstention. Group uncertainty
   by physical plate and session; do not count repeated angles as independent
   plates.
4. **Quality:** register candidate criteria and subgroup limits before
   training; compare against the frozen baseline on identical plate groups.
   Require improvements in absolute error without unacceptable bias,
   abstention, class, angle, and portion-size regressions. Use a fresh final
   holdout once after candidate freeze.
5. **Recognition/decomposition:** measure dish top-k and abstention, mask
   quality, item duplication, item-to-component matching, and complete-meal
   coverage on the same grouped captures.
6. **Nutrition/calibration:** validate food mapping, nutrient composition,
   and mass-to-nutrient propagation against independent measurements; pass a
   preregistered interval coverage/width criterion on new calibration data.
7. **Runtime/reliability:** test the chosen device/container under cold,
   warm, sustained and concurrent load; record p50/p95/p99, memory, GPU use,
   admission behavior, timeout/error rates and cleanup. Confirm behavior at
   the actual deployment worker count.
8. **Human-facing safety:** ensure abstentions and assumptions are legible;
   distinguish estimated nutrition from verified compliance; provide a
   manual correction path and capture/data retention policy before launch.

## Recommended next work within the freeze

1. Keep serving weights, thresholds and configs frozen while the existing
   development evidence remains spent.
2. Close dataset rights questions before publishing WED-derived artifacts.
3. Prepare the new capture protocol, annotation schema, group-split manifest
   and a locked-set access procedure; capture real Indian meal examples with
   per-component tare-corrected grams.
4. In parallel, close non-model operational gaps using synthetic or ordinary
   API fixtures: production-container startup, cancellation/timeout handling,
   multi-worker resource limits and sustained-load telemetry. These checks
   cannot claim to improve mass MAE.
5. Only after new development data exists, preregister a candidate and a
   genuinely untouched grouped holdout. Keep the ArUco plates, WED LOCKED,
   GTMensa participant-6, MetaFood3D test, AI-ServicesBB official test and
   LeFood held-out categories closed.

## Research update: techniques with the strongest fit

The new [food-portion methods memo](research/food-portion-techniques.md)
reviews current primary sources and maps them to NutriSense. The most useful
result for prioritization is a recent arXiv preprint on single-image mass
estimation: its Nutrition5k-trained DINOv2 model transferred poorly to other
camera/food datasets; larger backbones did not recover the gram scale, while
training with images from the target setting improved results. Its per-food
calibration helped when one labeled photo and the remaining photos shared the
same camera, plate, angle and framing. The preprint also found near-duplicate
plate leakage under a random image split. Treat these as findings from that
study, not as measured NutriSense gains. [Paper](https://arxiv.org/abs/2610.29025)

That evidence changes the order of work:

1. **Collect same-setting weighed examples first.** Record food-only total and
   component grams, tare, dish identity, camera/capture metadata and physical
   meal/session groups. Reserve sites, participants or sessions for the fresh
   test split. Keep all angles of one plate together.
2. **Compare models while holding perception fixed.** On new grouped
   development plates, compare current geometry, direct image regression,
   and a geometry estimate plus learned residual. Include train-only global
   and dish-conditioned median baselines. Report signed bias, MAE, mass-range
   and dish slices, and numeric coverage.
3. **Test per-dish calibration only on new same-setting data.** A known-menu
   workflow could use one or more weighed examples per dish to estimate a
   multiplicative or residual correction. Ledger 018 already found no gain
   from its specific per-food additive correction on spent WED DEV, so that
   result cannot be repeated or generalized; a different setting requires
   fresh development and test groups.
4. **Then isolate upstream geometry and mask error.** Compare the current
   marker scale with calibrated camera/pose and planar correction, while
   measuring card-to-food plane offset. Separately audit top-level mask
   containment, item overlap/duplicates, height/base plane, and density. The
   fixed-placement homography result is synthetic mechanism evidence only;
   it does not justify enabling homography in production.
5. **Treat extra views as an optional capture mode.** A top view plus a
   guided oblique view may reduce height ambiguity and stabilize item
   segmentation. It adds user effort and needs to be evaluated against a
   single-image baseline on the same newly weighed plates.
6. **Calibrate uncertainty by meal group, after point-error selection.** Use a
   dedicated calibration cohort and a separate fresh holdout. Group-level
   coverage must be measured; an interval method cannot repair camera/menu
   distribution shift by itself.

The [physically guided mass-estimation preprint](https://arxiv.org/abs/2601.20303)
is a useful architecture reference for separating geometry-related and
material-semantic cues before fusion. Its reported experiments are on
household-object benchmarks, and it says the learned volume/density factors
are not identifiable as calibrated physical quantities under mass-only
supervision. It motivates a controlled ablation, not direct adoption for
Indian food.

**Safe work before new weighed meals:** strengthen synthetic checks for
arithmetic, camera/marker placement, depth/base-plane perturbations and
multi-item aggregation; build split/metadata validators; and profile model
startup, memory and sustained API behavior with approved fixtures. These can
improve confidence in mechanics and operations, but they cannot establish a
lower real-food MAE. The experiment sequence and measurement schema are in the
research memo.

## Update log

- **2026-10-31:** Audited active documentation against the API contract and
  implementation. Clarified classifier confidence versus gallery match score,
  corrected the no-card coverage description, updated current test counts,
  corrected runtime model-download wording, repaired a missing generated
  overlay reference, and cleared the configured Ruff and Pyright gates.
  Historical evaluation reports remain dated snapshots.
- **2026-10-30:** Added the primary-source methods review and prioritized
  same-setting calibration, fixed-perception model comparison, error
  decomposition, optional multi-view capture and grouped uncertainty work.
- **2026-10-30:** Initial technical synthesis created from the current
  architecture, dataset/rights inventory, frozen experiment reports,
  production-readiness record and locally verified GPU environment. Added a
  current external dataset scan. No model, threshold, config, checkpoint or
  protected evaluation data was changed by this report.

## Evidence index

- Architecture/contract: `README.md`, `GLOSSARY.md`, `AGENTS.md`,
  `docs/adr/0001-python-owned-wire-contract.md`, `docs/adr/0002-learned-weight-fallback.md`,
  `docs/adr/0003-two-app-modes.md`.
- Data/rights: `datasets/README.md`, `datasets/registry.csv`,
  `docs/licenses.md`, `docs/research/indian-food-datasets.md`.
- Methods research: `docs/research/food-portion-techniques.md`.
- Accuracy/release status: `docs/production-readiness.md`,
  `docs/agentic-improvement-loop.md`, `docs/ledger/020-model-readiness-source-decisions.md`,
  `experiments/vlm_food_benchmark/RESULTS.md`, `experiments/metafood3d/RESULTS.md`,
  `experiments/food_waste/RESULTS_OFFICIAL_TEST.md`,
  `experiments/lefoodset/RESULTS.md`,
  `experiments/oracle_ablation/REPORT.md`.
- Evaluation lock/protocol: `docs/eval_protocol.md`,
  `docs/locked_manifest.txt`, `docs/locked_access_log.txt`.
