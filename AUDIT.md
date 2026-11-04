# NutriSense production-readiness audit

**Date:** 2026-11-02
**Scope:** The initial audit inspected the checked-out repository, application
paths, automated checks, documented experiments, and dependency state. The
implementation follow-ups below record subsequent code changes. No model,
checkpoint, protected evaluation file, or external dataset was changed. The
weighed ArUco plates remain EVAL-ONLY.

## Executive conclusion

NutriSense is **not production-ready for reliable automated food-mass,
nutrition, or compliance claims**. This is supported both by confirmed software
defects and by the project's own measured evidence. The real weighed-plate
pilot measured item-mask area sums of 2.84–7.71 times the corresponding
top-level food-mask area. The current branch now partitions overlapping pixels
before portioning, so a pixel is counted at most once. Whether the resulting
regions correspond to the correct foods remains unvalidated on independently
labeled real captures.

This document is an audit inventory, not a recommendation to tune on any
closed evaluation source. Findings are classified as:

- **Confirmed defect:** directly established from current code, a reproducible
  command, or a measured repository artifact.
- **Confirmed limitation / evidence gap:** a necessary production property has
  not been demonstrated, or documentation records it as unmet.
- **Risk:** source-supported concern that requires a deployment decision or
  threat model before it can be called a runtime defect.

## Implementation follow-up — 2026-11-02

The audit inventory below includes findings that have since been corrected in
the current working tree. This follow-up records the present status; it does
not change the accuracy or production-readiness conclusions.

| Finding | Current status |
| --- | --- |
| Multi-item regions | The 3×3 detector now queries overlapping local crops instead of prompting over the whole frame, which produced broad table/plate masks in a live WED development sample. It keeps the existing solidity filter, maps crop masks back to the original image, and deduplicates proposals. All shared pixels are then partitioned by distance to each proposal's exclusive region before portioning; output masks are disjoint, preserve the detector's input union, and refresh area/bounding-box evidence. Synthetic two- and three-way overlap cases pass. One real development-carve smoke check found five regions in a 12-label meal and underestimated its annotated mass by 56%; this is a functional improvement, not evidence of reliable meal coverage. |
| Repeated class across regions | Multiple distinct servings with the same non-combo food label are estimated separately and summed; the result notes the repeated label. Combo meals still require each expected component exactly once. |
| Automatic meal structure | The capture form no longer asks for `mixed`/`single`; recognized meals are checked for one or several food regions before School or General-mode serving logic runs. If region detection fails, the pipeline estimates from the top-level food mask and labels the result `ESTIMATED`, without a compliance verdict. A permitted WED development-carve smoke check reaches a five-item estimate, but its 12 annotated foods expose substantial under-detection; the detector cannot yet establish that a returned item list covers the whole meal. |
| School assessment scope | School mode supports scoring all 41 recognized WED food classes against the selected class-band energy/protein benchmark. Because whole-meal coverage is unvalidated, automatic multi-region results from the 3×3 detector now return `ESTIMATED` and withhold compliance while still showing tentative nutrition. The selected day remains menu context; generic nutrient rows, including cooked roti, remain explicitly assumed. The 23-image ArUco results predate these changes and were not rerun. |
| Combo component correspondence | Combo component matching still requires every expected component exactly once. Below-threshold, repeated, or unmatched components produce `ESTIMATED` without a compliance verdict. Even exact multi-region matches from the automatic 3×3 detector remain estimate-only because the full meal may contain unreturned regions. |
| Multi-item limit | The current 3×3 detector retains up to nine distinct regions, matching its nine grid prompts. If a future detector exceeds that limit, the pipeline uses the top-level food mask for a single `ESTIMATED` result rather than scoring a truncated item list. |
| Partial multi-item failures | If one or more regions cannot be classified, portioned, or assigned nutrition, the pipeline falls back to the top-level food mask and returns `ESTIMATED` with no compliance verdict. Portion or nutrition stage failures on that fallback still return `cannot_verify`; the pipeline does not fabricate grams. |
| Multi-item uncertainty aggregation | The previous elementwise sum of independent per-item draws has been replaced by rank-aligned marginal draws, a conservative perfect-positive-dependence assumption for shared image, scale, and pose errors. A synthetic regression verifies that opposing per-item ranks do not erase meal uncertainty. This is not empirically calibrated; the target-capture interval coverage gap remains open. |
| Below-threshold classifier scores | When the classifier provides ranked food scores but none clears its acceptance threshold, the top candidate may support a tentative nutrition estimate. The result is `ESTIMATED`, and no school compliance verdict is calculated. If there are no usable candidate scores, the result remains `cannot_verify`. |
| Item evidence and saved mode | Results show item-level evidence, and records retain the mode used at capture. |
| Request and input handling | Serving style is validated, missing zoom metadata permits food identification only as an estimate (no School verdict), image pixels are bounded before decode, and `/analyze` has a client timeout. A request-body byte cap and upload-duration timeout run before multipart parsing, including chunked uploads; the upload itself retains its smaller endpoint byte limit. |
| General-mode unexplained mass | Predicted ingredient mass that cannot be matched to the selected recipe is excluded from the displayed portion and nutrient total, called out in assumptions, and widens the uncertainty band. |
| Corrected base-plane orientation | `base_sign_flip` now applies the degraded-quality coverage factor. |
| Browser records | Malformed summaries are rejected, history recomputes when mode changes, startup tolerates unavailable local storage, and clear-local-data removes legacy records plus profile preferences. A failed record/chat write is surfaced on the result screen. The demo follow-up exchange persisted with its analysis and reappeared after opening the saved result in a fresh tab. |
| Analytics and accessibility | Analytics now scopes records to the mode saved with each analysis and hides School compliance metrics in General mode. The onboarding dialog traps keyboard focus and restores it to the opener. |
| Plate plausibility lint | The configured `plate_sanity_g` check now adds a non-blocking note when the estimated meal weight falls outside the documented ±25% range. |
| Transient model-load failures | Failed model factories now back off and retry automatically after the cooldown, with the retry delay increasing to a five-minute cap. This prevents immediate repeated downloads while allowing recovery without restarting the API. |
| Protected evaluation readers and lock | The prior-tier evaluator, deployable-path evaluator, and weight-head trainer require explicit flags before reading the protected WED test split; the trainer defaults to train/validation rows. A new `--write --code-only` path refreshes code/split hashes and preserves existing locked-image hash lines without opening image files. All 6 code/split pins match and all 496 existing image-hash entries remain preserved; the synthetic writer regression passed. The images were not opened, hashed, or evaluated, and the full lock checker was not run. |
| Same-host inference contention | A file lock serializes NutriSense inference across workers sharing the host filesystem and UID. It cannot detect or reserve GPU memory used by unrelated processes, containers, or other UIDs. |
| Health and readiness | `/health` remains a liveness response only. Models load lazily, and the service cannot promise that a future inference will fit alongside other GPU users; readiness, VRAM admission, and sustained multi-worker behavior remain deployment limitations. |
| Frontend dependencies | The lockfile now resolves the four previously reported packages to `zod@4.6.7`, `vite@6.4.5`, `undici@8.12.3`, and `source-map-js@1.2.2`. `npm audit fix` reported zero vulnerabilities when run; the registry could not be reached for a later audit refresh, so current advisory-database status was not independently rechecked. |
| Hosted workflow provenance | Checkout, setup-uv, and setup-node references now use full commit SHAs with release labels. The Actions jobs were not executed on GitHub during this update. |
| Model artifact drift | SigLIP 2, SAM 2.1, MoGe-2, and DINOv2 serving backbones now use immutable revision IDs from the local cache snapshot at project freeze. The required snapshots are cached here; a fresh machine still needs network access to fetch these exact revisions. |
| Inference error exposure | Client-facing stage failures use stable generic messages; detailed exceptions remain in server logs. Path redaction remains applied to wire errors and reasons. |
| Missing EXIF zoom metadata | Missing zoom metadata no longer blocks food identification. The result is estimate-only and the School-standard verdict is withheld; the UI now explains this limitation. A focused synthetic pipeline regression passed. Known digital zoom above 1.0 remains rejected. |
| High camera tilt | A measured card above the configured 60° capture-angle band can still produce a food/nutrition estimate, but the School-standard verdict is withheld because the footprint correction is outside its supported range. Regression coverage passed for both high-angle and low-angle capture behavior. |
| Student names with percent characters | The detail page uses the decoded route parameter directly and no longer decodes it twice, removing the `URIError` case documented below. |
| Evaluation artifact lineage | Each `tools/run_eval.py` report now records SHA-256 digests for the exact checkpoint and sigma file used. These digests identify artifacts; they do not add evaluation evidence. |
| Browser upload duration | `/analyze` now enforces a configurable 60-second request-body deadline before multipart parsing. Focused ASGI tests pass for both over-limit chunked bodies and slow uploads. Reverse-proxy limits are still required for externally reachable deployments. |
| Documentation evidence scope | README model claims now distinguish WED crop/gallery evidence, synthetic calibration, WED region metrics, and the pre-change EVAL-ONLY pilot; historical test counts are labeled as dated snapshots. |
| Nutrition5k license status | License documentation now records the existing local research/evaluation use, rejected candidate, and that Nutrition5k is not part of the serving pipeline. |
| Runtime logging | Failure to open the optional rotating log no longer prevents API startup; stderr logging remains available. |
| Recipe lookup | Recipe data is resolved from the module path rather than the current working directory. |

The sections below preserve evidence from the original audit snapshot. Where
the implementation follow-up above records a correction, the original code
description is historical and is not a claim about the current working tree.
Findings that require fresh data, rights decisions, or deployment validation
remain open. The lockfile advisory fixes do not establish a current advisory
database result. Model accuracy and calibration were not changed by these
fixes. No new meal data was collected.

### Current verification — 2026-11-02

| Check | Observed result |
| --- | --- |
| Earlier CPU-safe backend batch (before the latest structural guard and lint) | `210 passed, 9 deselected`; API-client-heavy files were run separately below. |
| Additional direct backend checks | Goals `14 passed`, contract generation `7 passed`, pipeline seams `24 passed`, direct pipeline cases `2 passed`, and the pre-parser chunked-body cap regression `1 passed`. Client-backed endpoint cases were deselected. |
| Earlier Ruff / Pyright / protected-file snapshot | Ruff passed; Pyright was `205` at that earlier check; `check_locked` reported `502 ok, 0 skipped, 0 failed`. The current type count is recorded in the row below. |
| Earlier frontend batch (before latest UI changes) | TypeScript passed, Vitest `88 passed`, and the production build passed. Vite still reports the 585.08 kB main JavaScript chunk warning. |
| Earlier host API snapshot | Client-backed tests were unverified: `TestClient` hung before entering even a minimal standalone FastAPI app in that virtual environment. At an earlier host run, `GET /health` returned `200` with `phase=built`; the Ollama key was present but not displayed. No fresh `/analyze` request was made because the original image upload was no longer available at full resolution. Separate earlier synthetic critique and follow-up requests returned HTTP 200; these confirm endpoint/model availability only, not answer quality. |
| 23-image ArUco evaluation (before post-evaluation changes) | Historical result from the host RTX 4060: 20 measured-card and 3 prior-anchor; 20 `cannot_verify`, 2 `out_of_scope`, and 1 `BORDERLINE`; only one image emitted grams, and the evaluator matched 0/23 top-level labels exactly. The 20 abstentions were attributed to overlapping regions (8), too many regions (3), repeated labels (3), component mismatch (1), and classifier scores below threshold (5). This set was not opened or rerun for this update. The result does not validate any later change. |
| Previous focused regression batch | Backend: `54 passed` across General/School mode, multi-item, detector, capture-lint, serving-map, gate, and compliance checks. Frontend: `95 passed`; TypeScript and production build passed. The production build retains the existing large-chunk warning (586.32 kB main JS) and dependency annotation warnings. |
| Earlier overlap and estimate-only check | Backend: `22 passed` across `tests/test_multi_item.py` and `tests/test_dish_segmenter.py`; focused Ruff and `git diff --check` passed. These synthetic tests verify the pixel partition invariant and fallback contract, not real-photo quality. At that point `/analyze` had not been exercised; later host and browser smoke checks are recorded below. |
| Current model-registry recovery check | `tests/test_model_registry.py`: `6 passed`; Ruff passed for the registry/test, and `git diff --check` passed. The test advances a fake clock through the load cooldown and does not load or download a model. |
| Earlier focused regression batch | `58 passed, 2 deselected` across gates, pipeline seams, overlap partitioning, region detection, and model-registry recovery. The two deselected tests exercise FastAPI `TestClient`; that client hangs before serving even a minimal app in this environment. No GPU inference or protected evaluation data was used. |
| Current static/frontend checks | Repository Ruff passed; Pyright reports `187` diagnostics against a recorded baseline of `187` (18 fewer than the previous baseline); frontend TypeScript passed and Vitest reported `95 passed`. The production build passed with existing Rollup comment-annotation warnings and a `586.29 kB` main JavaScript chunk warning. `git diff --check` passed. |
| Previous focused checks — 2026-11-02 | Combined backend regressions: `15 passed` across missing/known zoom, high camera tilt, nutrition aggregation, host inference lock, upload cap/timeout, code-only lock writing, and protected-reader CLI guards (two Python multiprocessing deprecation warnings). Frontend: TypeScript passed, Vitest `99 passed` across 15 files, and production build passed; Rollup emitted dependency annotation warnings and the main JavaScript bundle is `587.89 kB`. Repository Ruff passed. Pyright reports `187` diagnostics against baseline `187`. `git diff --check` passed. GitHub Actions were not run. |
| Earlier detector regressions — 2026-11-02 | `tests/test_dish_segmenter.py` and `tests/test_multi_item.py`: `24 passed`; focused Ruff passed. The crop-coordinate regression confirms that nine mocked local proposals map back to their expected positions in the full image; a separate regression verifies that automatic multi-region output is estimate-only without a compliance verdict. These tests verify coordinate projection and synthetic overlap behavior, not food-mask accuracy. |
| Current focused backend regression run — 2026-11-02 | `44 passed` across dish-region detection, multi-item pipeline behavior, nutrition aggregation, gates, and compliance. Focused Ruff and `git diff --check` passed. |
| Current frontend verification — 2026-11-02 | Vitest: `99 passed` across 15 files; `npx tsc --noEmit` passed; production build passed. Existing warnings remain: React `act(...)` warnings in onboarding tests, Rollup dependency annotation warnings, and a 587.89 kB main JavaScript chunk. |
| Host API smoke check — 2026-11-02 | On the host RTX 4060, offline `/analyze` returned HTTP 200 for the permitted development-carve image `data/wed/train/12-may/imgsFine/leftImg8bit/default/set14/20250512_160452_leftImg8bit.jpg`. The reference has 12 annotated food classes and 736 g total. The updated detector returned five regions: `vegetable_rice`, `steamed-rice`, `wheat_product`, `steamed-rice`, and `Watermelon`; the estimated total was 320.6 g (415.4 g / 56.4% below the reference). The response was `ESTIMATED`, with no school compliance verdict. This is one diagnostic smoke sample, not an accuracy metric; it was not from the 23-image ArUco set or WED test split. |
| Browser-to-model demo flow — 2026-11-02 | The running frontend uploaded the same permitted development-carve image to the CUDA API and displayed the result. It showed five detected regions, 320.6 g, 442 kcal, and 11.3 g protein as provisional estimates; the critique arrived from Ollama and suggested a protein-rich side and more vegetables. The app explained that meal estimates are shared with Ollama and that the photo and student name are not. The result remained `ESTIMATED` with compliance withheld. The 12-label reference and 56.4% mass underestimation make this a functioning demo path, not evidence of reliable recognition or nutrition accuracy. |
| Host runtime availability — 2026-11-02 | The API had stopped before the browser smoke attempt; it was restarted from this checkout, startup logged the RTX 4060 with CUDA selected, and the browser then completed `/analyze` and the Ollama critique. The backend is left running on `127.0.0.1:8731`; the frontend is reachable on `127.0.0.1:5173`. |
| Frontend dependency advisory recheck — 2026-11-02 | The installed lockfile tree now contains `zod@4.6.7`, `vite@6.4.5`, `undici@8.12.3`, and `source-map-js@1.2.2`. `npm audit --omit=dev` could not reach `registry.npmjs.org` (`EAI_AGAIN`), so current advisory status remains unverified; no dependency changes were made in this check. |

The completed evaluation predates the latest post-evaluation changes, and
the project **does not pass the 23-image acceptance set**: most images
abstained, and the sole scored estimate did not match a weighted meal
component. The overlap partition and estimate-only fallback paths remain
covered by synthetic unit seams; the crop detector also has one non-EVAL
development smoke check. The EVAL-ONLY images were not re-opened or used to
assess any change. Pixel partitioning prevents overlap double-counting but
does not prove that SAM's regions map to the correct servings. On one permitted
development-carve example, local-crop prompts yielded five regions but missed
most of a 12-food meal and underestimated its mass by 56.4%; no segmentation
precision/recall or meal-accuracy claim follows from this smoke check. The latest
broader focused regression batch passed 58 tests with the two hanging
client-backed cases deselected. A separate attempt to run those HTTP tests
stalled at `TestClient`; no pass is claimed for them. A broader backend batch
was also interrupted under host memory pressure. The narrower follow-up checks
are listed in the current verification table above.
Classifier and portion accuracy remain below a demonstrated 90% target, and
real region masks are unavailable for a valid segmentation score. The
API-client test environment remains unverified. Host-side `/analyze` now has a
single non-EVAL development smoke result; that result is visibly incomplete.
Ollama critique quality was not assessed in this detector check. The historical
23-image outcome remains unchanged and was not rerun.

## Prior project verification snapshot

The checks in this table were run for the 2026-10-31 audit snapshot; they were
not rerun as part of the 2026-11-01 independent review. Current review checks
are recorded after the table.

| Check | Observed result |
| --- | --- |
| `git status --short` | Clean before this audit file was added. |
| `.venv/bin/ruff check .` | Passed. |
| `.venv/bin/python -m tools.pyright_gate` | Passed its count gate at **205 existing errors**, baseline 205. |
| `.venv/bin/python -m tools.check_locked` | `502 ok, 0 skipped, 0 failed`. |
| `uv lock --check` | Passed. |
| Frontend TypeScript / Vitest / build | Passed; 71 Vitest tests; Vite warned about a 562.90 kB JavaScript chunk. |
| Focused non-GPU backend regression suite | `79 passed, 1 deselected`. |
| Full non-GPU collection | `271/281` tests collected; 10 are GPU-marked. |
| GPU API path during audit | Could not satisfy its success assertion because an existing Uvicorn process held 5,404 MiB of an 8,188 MiB GPU; `/analyze` returned structured `cannot_verify` after OOM retry. |
| `npm audit --omit=dev` | Four high-severity advisories: `zod`, `vite`, transitive `undici`, and transitive `source-map-js`. |
| Static source / secret scan | No plaintext secret pattern found in tracked source. This is not a substitute for a secrets-management review. |

The feature branch under audit is already an ancestor of `origin/main`.

## Assurance boundary

This audit has completed the source, contract, dependency, current-runtime,
test, and documented-evidence checks listed above. Within that stated method,
every issue discovered has been recorded here with its evidence and scope.

That is the strongest accurate completion claim. No finite code audit can prove
that every possible defect, security vulnerability, model failure, or future
deployment issue has been found. A future finding would be added to this
inventory rather than treated as evidence that the existing findings were
hidden or dismissed.

## Repository coverage matrix

The tracked audit inventory contains **248** code, configuration, workflow,
and documentation files under the product surfaces searched for the prior
audit. That count is scoped to `engine/`, `models/`, `frontend/src/`, `.github/`,
`data/`, and `docs/`; root entry points and project manifests were inspected
separately. Ten independent, domain-scoped audit passes then reviewed
architecture/release, API/security, image inputs, numeric behavior, frontend
state flows, data/configuration, data provenance, build/supply chain,
test design, and privacy/accessibility. Their source-backed additions are
included below. Static searches covered every source file in the listed roots;
high-risk paths also received manual control-flow and contract review.

| Surface | Files / paths examined | Failure classes checked |
| --- | --- | --- |
| API and process boundary | `main.py`, `engine/contract.py` | input validation, resource limits, error disclosure, concurrency, readiness, logging |
| Measurement and policy engine | `engine/`, `geo/` | gates, abstention, uncertainty, aggregation, data flow, numeric evidence |
| Vision/model lifecycle | `models/`, model config and artifacts | mask containment, duplicate handling, scale, model load/recovery, reproducibility |
| Product contracts and persistence | `frontend/src/`, generated contract | API decoding, timeout/cancellation, item evidence, mode history, local persistence |
| Configuration and data claims | `config.py`, `data/*.yaml`, `data/reports/` | load semantics, provenance, current-versus-historical metric consistency |
| Supply chain and delivery | `pyproject.toml`, `uv.lock`, `frontend/package*.json`, CI | dependency advisories, pinned runtime artifacts, CI and release controls |
| Evidence and governance | `README.md`, `docs/`, evaluation/ledger artifacts | claim scope, EVAL-only boundaries, quality/generalization/calibration/operations evidence |

Static checks included unsafe-call and plaintext-secret pattern scans,
exception-suppression and type-suppression scans, dependency audit, lockfile
validation, contract/build/test gates, protected-file verification, and the
targeted runtime checks recorded above. The absence of a finding in a row does
not mean a class is proven absent; it means the completed checks did not
produce a source-backed defect beyond those listed.

### Independent audit passes

Ten auditors reviewed separate areas without editing application code or
evaluation artifacts. Findings were consolidated below and cross-checked
against repository source and documentation.

| Pass | Focus | Findings added or corroborated |
| --- | --- | --- |
| 1 | Build and supply chain | Mutable runtime model revisions; unpinned workflow actions; CI scope |
| 2 | Documentation claims | MoGe/gallery evidence scope; conflicting Nutrition5k status |
| 3 | Data provenance | WED lock bypass; tracked artifacts versus release policy; artifact lineage gap |
| 4 | Test design | GPU/model skips, mock-based API checks, split/grouping and coverage limitations |
| 5 | Data and configuration logic | CWD-dependent recipe path; inert plate sanity setting; general-mode nutrition mismatch |
| 6 | Privacy and accessibility | Incomplete clear-all behavior, unscoped local records, local-storage startup and modal focus gaps |
| 7 | Numeric and domain behavior | Unexplained mass nutrition attribution; base sign flip policy gap; tilt sensitivity |
| 8 | API image inputs and security | Upload parsing/resource limits; decoded-pixel and request-time bounds; perimeter controls |
| 9 | Frontend state flows | Double-decoded student names; malformed record crash; mode-specific analytics concern |
| 10 | Architecture and release | Multipart parsing before size enforcement; logging write-path startup dependency |

The table does not imply that each pass found a unique issue; overlapping
findings were merged rather than counted twice.

**2026-11-01 review checks.** Confirmed all local evidence-link targets exist
(51 unique paths), checked the Markdown diff for whitespace errors, and
confirmed `git status --short` shows only the new `AUDIT.md`. No tests,
locked-data evaluation, or GPU inference was run for this update. The
protected evaluation files and ArUco images were not opened.

## Confirmed defects

The following entries preserve the evidence and impact from the initial
2026-11-01 baseline audit. Their findings describe that audited revision, not
necessarily the current working tree. Check the implementation-follow-up and
current-verification tables above for present status; unresolved items remain
open unless a follow-up explicitly says they were corrected.

### P0 — Multi-item masks could be double-counted into the meal total (fixed; coverage remains unvalidated)

**Evidence.** The detector retains masks whenever their pairwise IoU is below
0.70, with no requirement that the masks be disjoint, correspond to different
vessels, or be contained by the top-level food mask
([`models/dish_segmenter.py`](models/dish_segmenter.py#L182-L230)). The pipeline
then portions every resolved item and sums all grams
([`engine/pipeline.py`](engine/pipeline.py#L598-L636)).

The real-plate pilot documents item-mask sums of **2.84–7.71×** the top-level
food-mask area and repeated labels on multiple vessels
([`docs/known_issues.md`](docs/known_issues.md#L7-L27)). The paired measured
card result reported 805.4 g MAE over 14 valid same-image pairs
([`docs/production-readiness.md`](docs/production-readiness.md#L179-L189)).

**Impact.** A single food serving can become several independently estimated
servings. The displayed total, nutrients, and compliance verdict can therefore
be materially inflated. The repeated `Steamed Rice (standalone)` result seen in
the application is a direct symptom: aggregation deliberately joins each
accepted label ([`engine/pipeline.py`](engine/pipeline.py#L638-L667)).

### P0 — The detector silently capped a meal at four items (fixed)

**Evidence.** `MAX_ITEMS = 4`; candidates beyond the four largest masks are
discarded ([`models/dish_segmenter.py`](models/dish_segmenter.py#L182-L230)).
The returned segmentation count is only the count of resolved items, not the
number of candidates that were detected and then discarded
([`engine/pipeline.py`](engine/pipeline.py#L679-L705)).

**Impact.** A meal with more than four valid vessels can be undercounted with
no dedicated warning, reason, or coverage penalty.

### P0 — Partial multi-item failures could produce an aggregate verdict (fixed)

**Evidence.** Unrecognized, failed-classification, failed-portion, and
failed-nutrition items are skipped; all remaining items are added into a total
([`engine/pipeline.py`](engine/pipeline.py#L541-L596)). The seam test confirms
the resulting total equals only the measured item while an item was excluded
([`tests/test_multi_item.py`](tests/test_multi_item.py#L172-L197)).

**Impact.** A partial plate can receive PASS, FAIL, or BORDERLINE based on an
incomplete total. The generic assumption says items were excluded, but does not
make the final total safe to interpret as the whole meal.

### P1 — The UI hid item-level evidence needed to interpret multi-item results (fixed)

**Evidence.** `items` is present in the generated wire contract
([`frontend/src/types/contract.gen.ts`](frontend/src/types/contract.gen.ts#L104-L125),
[`frontend/src/types/contract.gen.ts`](frontend/src/types/contract.gen.ts#L210-L221)),
but no runtime frontend component reads `result.items`. The result screen renders
only the aggregate blocks ([`frontend/src/pages/Result.tsx`](frontend/src/pages/Result.tsx#L126-L158))
and measurement details renders the top-level portion/classification
([`frontend/src/result/MeasurementDetails.tsx`](frontend/src/result/MeasurementDetails.tsx#L17-L190)).

**Impact.** Users cannot see which item was skipped, which masks or crops were
used, each item's grams, or whether repeated labels caused an additive total.
This turns a machine-readable warning into an uninspectable aggregate result.

### P1 — Saved-result presentation changed with the current app mode (fixed)

**Evidence.** A saved `AnalysisRecord` stores the result, photo, timestamp,
and optional student data but no capture or display mode
([`frontend/src/services/records.ts`](frontend/src/services/records.ts#L33-L43),
[`frontend/src/services/records.ts`](frontend/src/services/records.ts#L237-L264)).
The result route chooses its school/general rendering branch from the mutable
current preference instead of record data
([`frontend/src/pages/Result.tsx`](frontend/src/pages/Result.tsx#L52-L55)).
The preference itself is a shared frontend setting
([`frontend/src/main.tsx`](frontend/src/main.tsx#L14-L33)). No test covers
opening an existing record after that setting changes.

**Impact.** Switching modes after a result has been saved can change the
meaning and presentation of the same historical analysis. A school-mode record
can lose its compliance view in general mode; a general-mode record can later
gain a school-mode presentation. The raw API result is unchanged, but the
user-facing interpretation is not stable.

### P1 — Multi-item uncertainty dependence is assumed, not calibrated (mitigated)

**Historical evidence.** The original aggregate summed per-item Monte Carlo
draws elementwise despite shared capture conditions. `aggregate_meal` now sorts
each marginal draw set and aligns ranks before summing
([`engine/mc.py`](engine/mc.py#L174-L206)).

**Current limitation.** Rank alignment assumes perfect positive dependence; it
is a conservative structural approximation, not a covariance model measured on
target meals. Single-item intervals also remain under-covered in the existing
evaluation. Fresh, representative measurements are still required for
calibration.

### P1 — `serving_style` was accepted without validation (fixed)

**Evidence.** The API accepts an arbitrary optional form string
([`main.py`](main.py#L195-L218)) and the pipeline echoes it into `dish`
([`engine/pipeline.py`](engine/pipeline.py#L395-L397)). A dependency-injected
pipeline run with `serving_style="not-a-valid-style"` returned `PASS` and echoed
that exact invalid value, although the menu exposes only `mixed` and `single`.

**Impact.** API clients can store and display invalid capture metadata. Unlike
day and band, it has no validation contract or rejection path.

### P1 — Raw inference exceptions were sent to API clients (fixed)

**Evidence.** `stage()` places exception class and message in `Failure.error`
([`engine/contract.py`](engine/contract.py#L283-L320)), and `Analysis.to_wire()`
serializes failures ([`engine/contract.py`](engine/contract.py#L347-L368)).
During this audit, a GPU OOM result exposed GPU capacity, free memory, and
process IDs. The existing redaction removes paths only.

**Impact.** Clients receive unnecessary infrastructure details and unstable
low-level text. This is an information-disclosure and API-contract-quality
defect.

### P1 — The zoom gate treated absent EXIF metadata as compliant (fixed)

**Evidence.** The gate returns no rejection when `digital_zoom` is absent or
equal to `1.0` ([`engine/gates.py`](engine/gates.py#L92-L96)). The EXIF reader
emits `None` when that metadata is unavailable
([`models/scale_anchor.py`](models/scale_anchor.py#L139-L163)). A direct gate
check produced `admitted=True` for `digital_zoom=None` and `1.0`, while `2.0`
was rejected. The capture UI asks users to use an original, non-zoomed image.

**Impact.** A screenshot, edited image, or any upload with stripped EXIF can
pass the zoom requirement without evidence that it is unzoomed. The gate only
enforces a known digital-zoom value; it does not establish the stated capture
property when metadata is missing.

### P1 — A small compressed upload could expand without a pixel limit (fixed)

**Evidence.** The endpoint limits bytes to 12 MiB but passes the temporary file
to `cv2.imread` without a dimension, pixel-count, or decoded-memory limit
([`main.py`](main.py#L55-L58), [`main.py`](main.py#L178-L222)).

**Impact.** If the endpoint is exposed, decompression bombs or very large valid
images can consume host RAM/CPU before inference admission helps.

### P1 — Frontend analysis requests lacked a timeout (fixed; cancellation remains unavailable)

**Evidence.** The browser client invokes `fetch` for `/analyze` without an
`AbortController`, timeout, or cancellation mechanism
([`frontend/src/services/api.ts`](frontend/src/services/api.ts#L84-L109)).

**Impact.** A network stall, model download, or stuck inference can leave a
user in a permanent loading state.

### P1 — Health reports liveness, not ability to analyze

**Evidence.** `/health` always returns `status: ok` and does not assess CUDA,
available VRAM, model readiness, or a pending model-load failure
([`main.py`](main.py#L138-L140)). During this audit it could report healthy
while the GPU lacked enough free memory for the depth stage.

**Impact.** Load balancers and the UI can route a user to a process that cannot
complete an analysis.

### P1 — GPU admission is process-local and does not prevent external contention

**Evidence.** The API uses an in-process `CapacityLimiter(1)` plus a separate
per-process request semaphore ([`main.py`](main.py#L18-L75)). The audit found a
running Uvicorn process using 5,404 MiB of the 8,188 MiB GPU; the GPU end-to-end
test then OOMed and produced `cannot_verify` after the one retry.

**Impact.** Multiple workers or any other GPU process can exhaust VRAM despite
the limiter. The documented two-request check is a one-worker smoke test, not
multi-worker or sustained-load evidence
([`docs/production-readiness.md`](docs/production-readiness.md#L151-L167)).

### P1 — Four high-severity frontend dependency advisories (versions updated; advisory status unverified)

**Evidence.** `npm audit --omit=dev` reported high-severity advisories for
direct `zod@4.6.5` and `vite@6.4.3`, plus transitive `undici@8.11.2` and
`source-map-js@1.2.1`. Audit metadata showed fixes available for all four.

**Impact.** `vite` exposure is chiefly the development server, while `zod`
ships in the client bundle. The full exposure depends on deployment topology,
but a production release should not carry known high-severity advisories
without an explicit risk decision.

### P2 — The application is not type-clean; the previous gate accepted 205 errors (187 remain)

**Baseline evidence.** The initial gate matched `pyright.baseline` at 205
errors. The raw report included 38 diagnostics in `engine/pipeline.py`,
including possible `None` access and wire-contract type mismatches.

**Impact.** This is not evidence of 205 runtime failures, but it suppresses
new-signal value in a critical inference module and raises regression risk.

**Current status.** Successful pipeline stages now assert their required
outputs before downstream use, including estimate-only fallbacks. The current
count is 187; the baseline was reduced to 187 after the gate passed at that
count. This is improvement, not type-cleanliness: 187 diagnostics remain.

### P2 — Model artifacts were loaded from mutable upstream revisions at runtime (fixed in current working tree)

**Evidence.** The serving code calls Hugging Face / MoGe `from_pretrained` with
model names but no immutable revision for classifier, segmenter, depth, and
the DINO backbone ([`models/food_classifier.py`](models/food_classifier.py#L110-L115),
[`models/dish_segmenter.py`](models/dish_segmenter.py#L39-L47),
[`engine/depth.py`](engine/depth.py#L70-L82),
[`models/weight_head.py`](models/weight_head.py#L79)).

**Impact.** A cold environment can download changed artifacts, fail because of
network availability, or diverge from measured behavior. This is a
reproducibility, availability, and supply-chain risk.

**Current status.** The four serving backbones now pass immutable revision
IDs matching snapshots cached at project freeze; see
[`models/model_revisions.py`](models/model_revisions.py). A cold machine still
needs network access to obtain those exact snapshots.

### P2 — A transient model-load failure remained sticky until process recovery (fixed in current working tree)

**Evidence.** The central registry records a failing factory name in `_failed`
and every later `get_or_create` for that name returns `None` without retrying
([`models/registry.py`](models/registry.py#L42-L63)). Model loading is lazy,
and several factories retrieve artifacts at first use. No readiness loop or
automatic retry clears a non-OOM failure; clearing occurs on explicit unload or
process restart.

**Impact.** A transient network, disk, or upstream artifact failure during one
first request can turn subsequent requests into persistent abstentions or
stage failures even after the original condition has recovered. This is a
production availability defect, although the sticky behavior is documented.

**Current status.** The registry now retries after an exponential cooldown,
capped at five minutes. The focused fake-clock regression passed without
loading a model or accessing the network.

### P2 — The UI could show an analysis as saved when browser persistence failed (fixed)

**Evidence.** `saveRecords` catches a second storage failure and silently gives
up ([`frontend/src/services/records.ts`](frontend/src/services/records.ts#L222-L234)).
`RecordsProvider.addRecord` still puts the record into React state regardless
([`frontend/src/context/records.tsx`](frontend/src/context/records.tsx#L37-L47)),
and the analysis page immediately navigates to that in-memory result
([`frontend/src/pages/Analyze.tsx`](frontend/src/pages/Analyze.tsx#L82-L99)).
The existing quota test verifies only the first fallback that removes old
thumbnails; it does not surface a second failure to the user.

**Impact.** A quota or storage-policy failure can make a new analysis look like
it was saved and included in history until refresh, after which it is gone.
This undermines the history, analytics, and audit-trail behavior presented by
the UI.

### P2 — Documentation mixes current and historical performance evidence without a single visible status boundary

**Evidence.** Current records say 71 Vitest tests pass
([`README.md`](README.md#L291-L300), [`docs/production-readiness.md`](docs/production-readiness.md#L351-L365)),
while retained historical sections say 70
([`docs/production-readiness.md`](docs/production-readiness.md#L270-L294)).

The current serving evidence identifies DINOv2 DEV MAE 15.034 g and one-time
LOCKED MAE 14.667 g ([`README.md`](README.md#L142-L152),
[`docs/technical-project-report.md`](docs/technical-project-report.md#L21-L29)),
while the prominent dated final report describes an older ResNet path at 20.30
g validation / 20.03 g test
([`docs/final-report.md`](docs/final-report.md#L121-L130)). The project does
explain the history elsewhere, and marks `weight_head_train.json` stale, but
that status is not visible wherever the old figures appear.

**Impact.** A reader can mistake old failed checks for current state, or vice
versa, and can report the wrong architecture or accuracy number. This is
documentation and release-governance debt, not a new model-quality result.

## Additional findings from ten independent audit passes

### P1 — The locked WED test split could be read without the lock protocol (fixed in guarded readers)

**Evidence.** `tools/train_weight_head.py` includes the WED test split by
default unless `--skip-test` is supplied ([`tools/train_weight_head.py`](tools/train_weight_head.py#L600-L611),
[`tools/train_weight_head.py`](tools/train_weight_head.py#L770-L784)).
`tools/eval_prior_tier_on_wed.py` defaults to `--split test` and reads the
manifest/evaluation data without requiring the lock flag or writing the
evaluation access log ([`tools/eval_prior_tier_on_wed.py`](tools/eval_prior_tier_on_wed.py#L103-L116),
[`tools/eval_prior_tier_on_wed.py`](tools/eval_prior_tier_on_wed.py#L284-L316)).
The documented protocol requires the lock flag and audit logging
([`docs/eval_protocol.md`](docs/eval_protocol.md#L73-L80),
[`docs/eval_protocol.md`](docs/eval_protocol.md#L207-L218)).

**Impact.** A routine training/evaluation command can access the protected
split without the prescribed guard or trace. This is an evaluation-governance
defect. The audit inspected code and documentation only; it did not open the
protected split or rerun its evaluation.

### P1 — General mode assigned unexplained food mass to matched recipe nutrition (fixed)

**Evidence.** General mode adds `unexplained_g` to `total_g` while emitting
matched component masses that sum only to `total_visible_g`
([`engine/general_mode.py`](engine/general_mode.py#L106-L152)). Monte Carlo
nutrition then uses the full portion mass and matched recipe proportions
([`engine/mc.py`](engine/mc.py#L74-L76),
[`engine/mc.py`](engine/mc.py#L113-L118)). The existing regression test
expects 104 g total, 99 g matched components, and nutrition based on the 104 g
total ([`tests/test_general_mode.py`](tests/test_general_mode.py#L108-L125)).

**Impact.** Unexplained mass is represented as if it had the nutrient profile
of the recognized recipe. Total mass and nutrient attribution disagree about
what was identified.

### P1 — A negative base-plane height correction was not penalized by compliance (fixed)

**Evidence.** The portion estimator flips all height signs when median height
is negative and records `base_sign_flip`
([`models/portion_estimator.py`](models/portion_estimator.py#L203-L212)).
Compliance coverage checks do not include that flag
([`engine/compliance.py`](engine/compliance.py#L59-L64)).

**Impact.** A corrected height map can retain full coverage and avoid an
abstention penalty even though its base-plane orientation required a global
sign reversal. This establishes a missing policy connection; it does not
establish how often the condition occurs in production captures.

### P1 — Recipe data lookup depended on the current working directory (fixed)

**Evidence.** `models/recipe_table.py` opens `data/indb_recipes.yaml` as a
relative path ([`models/recipe_table.py`](models/recipe_table.py#L19-L31)),
while `config.py` defines the project root and data directory independently
of the process working directory ([`config.py`](config.py#L1-L14)). A `.venv`
reproduction launched from `/tmp` with the project on `PYTHONPATH` raised
`FileNotFoundError` for that recipe table.

**Impact.** Importing or running affected commands outside the repository
working directory can fail despite a valid project installation.

### P1 — Multipart request data was parsed and spooled before the endpoint byte cap (fixed in current working tree)

**Evidence.** FastAPI receives `UploadFile` form data and checks the 12 MiB
limit only inside the endpoint ([`main.py`](main.py#L195-L214)). The admission
middleware limits concurrent requests, not body bytes
([`main.py`](main.py#L20-L47)). Inspection of the installed Starlette parser
from `.venv` confirmed it consumes multipart input and writes file parts to a
spooled temporary file before the endpoint is called; its part-size check
applies to non-file fields.

**Current status.** `AnalyzeBodySizeMiddleware` now checks `Content-Length` and
also bounds chunked bodies before calling FastAPI's multipart parser. Its cap
allows the 12 MiB file limit plus 64 KiB of multipart overhead; the endpoint
still enforces the smaller file-only limit. A direct ASGI regression verifies
that an oversized chunked body returns 413 without invoking the parser.

**Current status.** A configurable request-body deadline now rejects slow
uploads before multipart parsing; focused ASGI tests cover the timeout and
oversized chunked-body cases. A reachable deployment still needs proxy/server
connection and concurrency limits.

### P1 — Tracked WED-derived artifacts conflict with the documented release policy (open rights/release decision)

**Evidence.** `docs/licenses.md` says WED terms are unresolved, nothing leaves
the machine, and derived artifacts remain release-gated
([`docs/licenses.md`](docs/licenses.md#L79-L89)). Git tracks
`data/wed_manifest.jsonl`, `data/wed/all_food_data.json`,
`data/wed/index_map.json`, `data/weight_head.pt`, and
`data/weight_head_sigma.yaml`; an older ADR says some artifacts are committed
([`docs/adr/0002-learned-weight-fallback.md`](docs/adr/0002-learned-weight-fallback.md#L57-L62)).

**Impact.** Repository state and current rights/release guidance disagree.
This is a provenance and release-governance conflict, not a legal conclusion.

### P2 — `plate_sanity_g` was configured without a runtime consumer (fixed)

**Evidence.** The standard defines `plate_sanity_g`
([`data/standards.yaml`](data/standards.yaml#L67-L70)) and README says a lint
uses the plate sanity check ([`README.md`](README.md#L457-L465)), but source
search found no runtime use of that key.

**Impact.** Operators may believe this configured plausibility check runs when
it does not. The audit confirmed non-use in searched code, not whether a
separate untracked tool implements it.

### P2 — Student names containing percent escapes could break student routes (fixed)

**Evidence.** Student list links encode the name with `encodeURIComponent`
([`frontend/src/pages/Students.tsx`](frontend/src/pages/Students.tsx#L93));
React Router supplies a decoded route parameter, and the detail page calls
`decodeURIComponent` again ([`frontend/src/pages/Students.tsx`](frontend/src/pages/Students.tsx#L295)).
An installed-router reproduction with `50% rice` raised `URIError` on the
second decode.

**Impact.** A valid student name containing a percent sign can make its detail
route fail to render.

### P2 — A malformed browser record could crash dashboard aggregation (fixed)

**Evidence.** The persisted-record validator accepts any object with a string
`id` ([`frontend/src/services/records.ts`](frontend/src/services/records.ts#L174-L202)),
while dashboard tallying assumes `summary.verdict` exists
([`frontend/src/services/records.ts`](frontend/src/services/records.ts#L79-L88),
[`frontend/src/pages/Dashboard.tsx`](frontend/src/pages/Dashboard.tsx#L187)).
The auditor reproduced the crash using a record containing only `{"id":"x"}`.

**Impact.** Stale, manually edited, or partially written local storage can
break the dashboard instead of being rejected or safely ignored.

### P2 — “Clear all” left legacy records and profile data in browser storage (fixed)

**Evidence.** The clear action saves an empty v2 record list
([`frontend/src/context/records.tsx`](frontend/src/context/records.tsx#L62-L67)),
but the legacy v1 key remains and migration does not remove it
([`frontend/src/services/records.ts`](frontend/src/services/records.ts#L45-L47),
[`frontend/src/services/records.ts`](frontend/src/services/records.ts#L207-L219)).
Profile preferences, including name and demographic fields, are stored under
a separate key ([`frontend/src/pages/Settings.tsx`](frontend/src/pages/Settings.tsx#L365-L407),
[`frontend/src/context/prefs.tsx`](frontend/src/context/prefs.tsx#L23-L36)).

**Impact.** The visible clear action does not erase all analysis-related or
profile data from the browser. This is a concrete deletion-control gap in
addition to the broader privacy/retention limitation below.

### P2 — Application startup could fail when browser local storage is unavailable (fixed)

**Evidence.** `main.tsx` reads `window.localStorage` before React mounts and
without catching access errors ([`frontend/src/main.tsx`](frontend/src/main.tsx#L14-L23)).
Browsers can throw on storage access under restricted privacy settings or
storage policy.

**Impact.** The frontend can fail before rendering where the browser denies
local storage access.

### P2 — General mode exposed school compliance analytics (fixed)

**Evidence.** Analytics computes and renders compliance rate and PASS
distribution without checking the selected mode
([`frontend/src/pages/Analytics.tsx`](frontend/src/pages/Analytics.tsx#L59-L99),
[`frontend/src/pages/Analytics.tsx`](frontend/src/pages/Analytics.tsx#L156-L205)).
The navigation exposes Analytics in both modes
([`frontend/src/layout/Sidebar.tsx`](frontend/src/layout/Sidebar.tsx#L10-L47)),
while the general-mode contract has no compliance verdict
([`docs/adr/0003-two-app-modes.md`](docs/adr/0003-two-app-modes.md#L14-L37)).

**Impact.** In general mode the UI can present school compliance metrics for
records whose mode is not persisted and whose general-mode result should not
have a compliance verdict.

### P2 — History memoization did not update when the app mode changed (fixed)

**Evidence.** The history filter reads `general` in its memoized calculation,
but the dependency list omits it ([`frontend/src/pages/History.tsx`](frontend/src/pages/History.tsx#L51-L65)).

**Impact.** Changing modes while the history page remains mounted can leave
the list filtered using the previous mode until another dependency changes.

### P2 — README performance claims omitted the scope of their evidence (updated)

**Evidence.** README presents MoGe approximately 1.1% median error and 46/46
gallery LOO results without the nearby synthetic/rendered and two-class scope
recorded in the diagnostic report ([`README.md`](README.md#L123-L126),
[`docs/diagnostic_report.md`](docs/diagnostic_report.md#L31-L46)).

**Impact.** The summary can be read as broader, independent real-image
validation than the underlying experiment supports. This is claim-scope debt,
not a new measurement.

### P2 — License documentation had conflicting Nutrition5k status (clarified in current working tree)

**Evidence.** `docs/licenses.md` describes Nutrition5k as planned, while the
dataset ledger and readiness report describe completed local/test analyses
([`docs/licenses.md`](docs/licenses.md#L17-L23),
[`docs/ledger/020-model-readiness-source-decisions.md`](docs/ledger/020-model-readiness-source-decisions.md#L45-L53),
[`docs/production-readiness.md`](docs/production-readiness.md#L118-L127)).

**Impact.** A reader cannot determine whether the source was only planned,
locally obtained, or used in experiments.

**Current status.** [`docs/licenses.md`](docs/licenses.md) now records prior
local research/evaluation use, the rejected candidate, and that Nutrition5k
does not serve the application. This documentation change does not change the
dataset's license or the project's rights position.

### P2 — Runtime evaluation reports did not bind results to exact weight-head artifacts (fixed)

**Evidence.** `tools/run_eval.py` records the checkpoint path but not a digest
for the checkpoint or sigma file ([`tools/run_eval.py`](tools/run_eval.py#L343-L351)).
The documented lock excludes model and sigma artifact hashes
([`docs/eval_protocol.md`](docs/eval_protocol.md#L186-L193)).

**Impact.** A report cannot establish which exact mutable-at-path artifacts
produced its metrics, weakening reproduction and lineage.

### P2 — Near-edge-on card geometry is warning-only while area correction grows

**Evidence.** The estimator divides observed footprint by cosine of estimated
tilt ([`models/portion_estimator.py`](models/portion_estimator.py#L214-L222));
the pipeline emits a lint warning for tilt but does not reject the measurement
([`engine/pipeline.py`](engine/pipeline.py#L328-L336)).

**Impact.** If a highly tilted card passes earlier anchor checks, the
correction can become large while remaining scoreable. This is a conditional
failure mode; its frequency in accepted captures was not established.

### P2 — Default file logging could prevent startup on a read-only application filesystem (fixed)

**Evidence.** Importing `main.py` configures logging, creates `<repo>/logs`,
and opens a rotating file there unless `NUTRISENSE_LOG_DIR` is set
([`main.py`](main.py#L78-L102)). No CI job starts the app in a read-only
container or package directory ([`.github/workflows/ci.yml`](.github/workflows/ci.yml#L25-L83)).

**Impact.** A read-only deployment image or source directory can fail during
module import. This is conditional on deployment filesystem permissions.

### P2 — The onboarding modal lacked focus trapping and focus restoration (fixed)

**Evidence.** The onboarding dialog receives initial focus and supports
Escape, but does not trap focus within the modal or restore focus to the
opener ([`frontend/src/ui/OnboardingModal.tsx`](frontend/src/ui/OnboardingModal.tsx#L148-L186)).

**Impact.** Keyboard and assistive-technology users can move focus behind an
active modal and may lose their prior navigation position when it closes.

## Confirmed production limitations and unmet evidence

### L1 — No valid production accuracy result on representative target meals

The WED results are in-domain ROI evidence, not independent mixed Indian meal
evidence. The six-plate ArUco set is EVAL-ONLY and too small for a production
claim. The documentation explicitly says no candidate passes all quality,
generalization, calibration, nutrition, and operations gates
([`docs/technical-project-report.md`](docs/technical-project-report.md#L35-L38)).

Cross-domain results reinforce the gap:

- AI-ServicesBB: numeric output on 67/160 repeated post-meal views and 93
  abstentions; numeric labels did not establish component correspondence
  ([`docs/production-readiness.md`](docs/production-readiness.md#L48-L59)).
- LeFood-Set: production path abstained on all 143 held-out images
  ([`docs/production-readiness.md`](docs/production-readiness.md#L60-L76)).
- VLM Food Benchmark: production path abstained on all 60 test images
  ([`docs/production-readiness.md`](docs/production-readiness.md#L77-L91)).

### L2 — The displayed nominal 90% intervals are known to under-cover

The locked report measured 82.77% coverage, and validation calibration reached
90% only with a 47% width expansion beyond the registered cap
([`docs/production-readiness.md`](docs/production-readiness.md#L10-L15),
[`docs/production-readiness.md`](docs/production-readiness.md#L93-L99)).

The UI labels an uncertainty value and presents nutrient intervals, but no
production-valid calibration supports interpreting them as dependable 90%
coverage for target captures. This is an accuracy and communication limitation.

### L3 — Nutrition accuracy is unvalidated end-to-end

The nutrition system derives kcal/protein from estimated grams, assumed recipe
shares, and a composition table ([`engine/mc.py`](engine/mc.py#L59-L170)). The
project's Nutrition5k candidate was rejected; full-slot evaluation was unusable
and the oracle diagnostic used held-out ingredient labels
([`docs/production-readiness.md`](docs/production-readiness.md#L118-L127)).

No representative independent plate-level nutrition ground truth validates the
numbers shown to users.

The general-mode path also applies recognized recipe proportions to the full
portion mass when some mass is explicitly marked unexplained (see the P1
general-mode finding above). Generic WED-derived nutrition entries are marked
assumed in the source table, while Monte Carlo uncertainty may use the generic
4% table sigma when no wider range is present
([`data/nutrients.yaml`](data/nutrients.yaml#L39-L42),
[`engine/mc.py`](engine/mc.py#L86-L92)). Those intervals do not independently
validate the assumed values.

### L4 — The measured-anchor geometry path has unresolved plate/rim/table contamination

The real-plate report and issue log document non-zero height on plate/rim/table
regions and mask spill; local surface-area integration regressed synthetic
scenes and the card-position study had only two detectable placements
([`docs/known_issues.md`](docs/known_issues.md#L7-L27)). The card-versus-forced-
prior comparison was worse for the card path on the small pilot
([`docs/production-readiness.md`](docs/production-readiness.md#L179-L189)).

This means a detected reference card does not establish that food volume is
being isolated correctly.

### L5 — Meal recognition and component correspondence are not validated

The classifier has WED ROI/gallery evidence, but item labels on target mixed
meals are not linked to weighed components. Repeated same-label assignments are
already observed. The project reports only clear component matches and never
claims a one-to-one match for every predicted item mask
([`docs/production-readiness.md`](docs/production-readiness.md#L185-L189)).

The 2026-11-02 development smoke check provides one direct example: a meal with
12 annotated labels produced five localized estimates, including a repeated
rice label, and a total 56.4% below its annotated mass. This is a failure
diagnostic, not a segmentation score; item-level region ground truth is not
available for precision/recall.

### L6 — Recognition remains limited to the WED class set

School and General modes can process all 41 WED food classes, with generic
assumed nutrient rows for classes without an official menu recipe. The model
does not recognize every Indian food, and the external 23-image meal set
primarily abstained or failed component correspondence. Product copy should
continue to state this fixed recognition scope and the estimate caveat.

### L7 — Deployment validation is incomplete

The repository has no container/orchestrator deployment artifact, no
authentication/authorization layer, no external rate limiting, no dependency
update automation, no software-bill-of-material workflow, and no security scan
in CI. The CI covers lint, a baseline type count, non-GPU tests, TypeScript,
frontend tests, and build ([`.github/workflows/ci.yml`](.github/workflows/ci.yml#L25-L83)).

The project itself records that cold-start distribution, sustained load,
multi-worker behavior, remote network behavior, target-container behavior,
timeouts, and error-rate budgets remain unmeasured
([`docs/production-readiness.md`](docs/production-readiness.md#L156-L167),
[`docs/technical-project-report.md`](docs/technical-project-report.md#L203-L209)).

### L8 — Privacy, retention, and multi-user controls are not production-defined

The frontend stores photos as thumbnails, analyses, and optional student names
in browser `localStorage` ([`frontend/src/main.tsx`](frontend/src/main.tsx#L14-L19),
[`frontend/src/pages/Analyze.tsx`](frontend/src/pages/Analyze.tsx#L86-L97)).
There is no authenticated identity, server persistence policy, retention
expiry, encryption-at-rest design, consent flow, or privacy notice for real
deployment. The Settings page can clear local records and profile preferences,
but there is no user-scoped account or automatic retention workflow. For a
localhost demonstration this is not automatically a security flaw; for school
use it remains an unresolved product and compliance gap.

### L9 — Data/commercial-rights path is unresolved for most useful sources

The technical report states that commercial distribution requires written terms
for WED/ITD and any included artifact
([`docs/technical-project-report.md`](docs/technical-project-report.md#L243-L250)).
MetaFood3D is CC BY-NC and cannot clear commercial serving use
([`docs/production-readiness.md`](docs/production-readiness.md#L41-L46)).

No rights-cleared representative weighed mixed-plate development and independent
test set is available for product promotion.

### L10 — Current operational performance does not establish production SLOs

Successful local scored calls had only two observations (p50 8.263 s, p95
8.338 s), while faster 735–751 ms measurements were abstention paths
([`docs/production-readiness.md`](docs/production-readiness.md#L129-L155)).
The stated limits are provisional local budgets, not deployment guarantees.

### L11 — The static single-image design has unmeasured capture sensitivity

The product depends on a single photo, card detection, monocular depth,
assumed intrinsics, segmentation, classification, and density/recipe priors.
Angle spread across unchanged ArUco plates and card-position sensitivity were
observed, but not resolved with independent target data. A single photo cannot
by itself establish hidden-food mass, component boundaries, food-versus-vessel
height, or occluded ingredients.

### L12 — Test passing does not establish exhaustive behavioral coverage

The repository has regression tests and a baseline type-count gate, but no
coverage threshold or published coverage report, and this audit found no
property/fuzz test, protocol-validation suite, external security test, or
production-like load test. CI excludes GPU/model-backed paths; some checkpoint
tests can skip when local artifacts are absent, and many API contract tests use
stubs rather than a production model. Frontend checks use unit/jsdom and do not
exercise the browser against a live API. The classifier holdout is split by
file ordering rather than grouped by plate/session, and locked-data CI allows
missing image files. Passing tests therefore establish the executed assertions
only. They cannot support a claim that all input, state-transition, accuracy,
or deployment failures have been discovered.

### L13 — WED test evidence is not a fresh, untouched independent holdout

The documented experiment history records prior test-split use and later
reruns ([`docs/known_issues.md`](docs/known_issues.md#L90-L104),
[`docs/production-readiness.md`](docs/production-readiness.md#L93-L110)). The
current direct readers now require explicit flags, but past exposure remains;
reported WED test metrics are historical internal evidence, not a fresh,
one-time independent test. No test-split data was opened for this update.

### L14 — Build and hosted automation were not pinned to immutable actions

The 2026-11-01 baseline workflow referenced third-party actions by version
tags. The current workflow pins checkout, setup-uv, and setup-node to full
commit SHAs; the original mutable-tag defect is corrected. CI still validates
a limited offline and mocked path and does not establish GPU or deployment-
image behavior.

### L15 — Upload resource safety still depends partly on controls outside the application

The application bounds request-body bytes and enforces a configurable upload
deadline before multipart parsing. A production proxy/server still needs
connection, concurrency, and request-time limits; no deployment proxy
configuration is present in the repository. The application-level timeout
fix reduces the risk but does not replace those external controls.

## Risks requiring a deployment decision

These are source-backed concerns, but the severity depends on whether the
service leaves localhost or handles sensitive operational data.

1. **Unauthenticated API.** The API has no auth or authorization. CORS is
   restricted by default to local Vite origins, but CORS is not authentication.
   Exposing it through a proxy would need explicit identity and abuse controls.
2. **No request-level rate limit / reverse-proxy policy.** The two-request
   in-process admission cap limits one worker, but does not replace network
   rate limiting, upload-body limits at the proxy, TLS, or observability.
3. **Runtime downloads.** First-use model downloads need network access and
   mutable upstream artifact availability; production needs prefetching,
   checksums/revisions, and a failure policy.
4. **Browser-local records.** User history can be lost with browser-data
   clearing and is accessible to scripts running on the same origin. This is a
   privacy and durability decision, not a backend database bug.
5. **Documentation claims need release governance.** README/marketing language
   should be reviewed against the evidence limitations above before any public
   deployment claim.
6. **External upload controls.** The application enforces byte and duration
   limits before multipart parsing. A reachable deployment still needs the
   proxy/server to bound connections, concurrency, and overall request time.

## What this audit did not establish

- It cannot prove the absence of additional bugs, security vulnerabilities, or
  model failures.
- It can claim only that every finding from the documented audit method is
  flagged in this file; it cannot truthfully claim that every possible issue in
  the project is known.
- It did not retune, retrain, rerun, or inspect closed locked evaluations.
- It did not run the full GPU test suite successfully under an idle-GPU
  condition; the audit recorded the observed contention instead.
- It did not perform an external penetration test, legal review, privacy
  impact assessment, accessibility audit, or target-hardware load test.
- Ten independent, domain-scoped passes reviewed the repository; each finding
  included here was consolidated and checked against source or cited project
  evidence. The passes do not amount to exhaustive formal verification or
  prove that every possible issue has been found.
- It does not rank root causes beyond the measured/code-backed evidence.

## Release-blocking synthesis

Before production claims are supportable, the project needs all of the
following evidence and controls:

1. A safe, independently validated multi-item measurement path that does not
   add duplicate masks or silently omit detected food.
2. Fresh, permissioned, representative weighed mixed-plate development and
   independent test groups, with component correspondence, tare, camera,
   session, and repeated-view metadata.
3. Independently calibrated uncertainty and validated nutrition outcomes.
4. Resolved dependency advisories, input/resource limits, client/server
   timeouts, safe public error responses, readiness semantics, and deployment
   security controls.
5. A target-environment load, concurrency, GPU-memory, recovery, privacy, and
   data-rights validation record.

Until then, NutriSense remains a research prototype with reproducible internal
checks and explicit evidence boundaries, not a production-grade portion,
nutrition, or compliance system.
