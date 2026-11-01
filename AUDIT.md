# NutriSense production-readiness audit

**Date:** 2026-11-01
**Scope:** Read-only audit of the checked-out repository, current application
paths, automated checks, documented experiments, and dependency state. No model,
threshold, configuration, checkpoint, protected evaluation file, or serving code
was changed. The weighed ArUco plates remain EVAL-ONLY.

## Executive conclusion

NutriSense is **not production-ready for reliable automated food-mass,
nutrition, or compliance claims**. This is supported both by confirmed software
defects and by the project's own measured evidence. The most serious issue is
the multi-item path: it can treat overlapping or repeated masks as separate
servings and add their grams. The real weighed-plate pilot measured item-mask
area sums of 2.84–7.71 times the corresponding top-level food-mask area.

This document is an audit inventory, not a recommendation to tune on any
closed evaluation source. Findings are classified as:

- **Confirmed defect:** directly established from current code, a reproducible
  command, or a measured repository artifact.
- **Confirmed limitation / evidence gap:** a necessary production property has
  not been demonstrated, or documentation records it as unmet.
- **Risk:** source-supported concern that requires a deployment decision or
  threat model before it can be called a runtime defect.

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

### P0 — Multi-item masks can be double-counted into the meal total

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

### P0 — The detector silently caps a meal at four items

**Evidence.** `MAX_ITEMS = 4`; candidates beyond the four largest masks are
discarded ([`models/dish_segmenter.py`](models/dish_segmenter.py#L182-L230)).
The returned segmentation count is only the count of resolved items, not the
number of candidates that were detected and then discarded
([`engine/pipeline.py`](engine/pipeline.py#L679-L705)).

**Impact.** A meal with more than four valid vessels can be undercounted with
no dedicated warning, reason, or coverage penalty.

### P0 — Partial multi-item failures still produce an aggregate verdict

**Evidence.** Unrecognized, failed-classification, failed-portion, and
failed-nutrition items are skipped; all remaining items are added into a total
([`engine/pipeline.py`](engine/pipeline.py#L541-L596)). The seam test confirms
the resulting total equals only the measured item while an item was excluded
([`tests/test_multi_item.py`](tests/test_multi_item.py#L172-L197)).

**Impact.** A partial plate can receive PASS, FAIL, or BORDERLINE based on an
incomplete total. The generic assumption says items were excluded, but does not
make the final total safe to interpret as the whole meal.

### P1 — The UI hides the item-level evidence needed to interpret multi-item results

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

### P1 — Saved-result presentation changes with the current app mode

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

### P1 — Aggregate uncertainty assumes independent item draws despite shared upstream errors

**Evidence.** Per-item Monte Carlo runs use different seeds and `aggregate_meal`
sums samples elementwise ([`engine/pipeline.py`](engine/pipeline.py#L581-L637);
[`engine/mc.py`](engine/mc.py#L174-L206)). The same code comments acknowledge
shared-anchor/pose terms while retaining independent sampling
([`engine/mc.py`](engine/mc.py#L174-L182)). In practice, items on one photo
share the same anchor, camera, depth map, segmentation conditions, and often
the same duplicated mask failure.

**Impact.** The combined interval can be too narrow when errors move together.
This is separate from the already measured single-item interval undercoverage.

### P1 — `serving_style` is accepted without validation

**Evidence.** The API accepts an arbitrary optional form string
([`main.py`](main.py#L195-L218)) and the pipeline echoes it into `dish`
([`engine/pipeline.py`](engine/pipeline.py#L395-L397)). A dependency-injected
pipeline run with `serving_style="not-a-valid-style"` returned `PASS` and echoed
that exact invalid value, although the menu exposes only `mixed` and `single`.

**Impact.** API clients can store and display invalid capture metadata. Unlike
day and band, it has no validation contract or rejection path.

### P1 — Raw inference exceptions are sent to API clients

**Evidence.** `stage()` places exception class and message in `Failure.error`
([`engine/contract.py`](engine/contract.py#L283-L320)), and `Analysis.to_wire()`
serializes failures ([`engine/contract.py`](engine/contract.py#L347-L368)).
During this audit, a GPU OOM result exposed GPU capacity, free memory, and
process IDs. The existing redaction removes paths only.

**Impact.** Clients receive unnecessary infrastructure details and unstable
low-level text. This is an information-disclosure and API-contract-quality
defect.

### P1 — The zoom gate treats absent EXIF metadata as compliant

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

### P1 — A small compressed upload can expand without a pixel limit

**Evidence.** The endpoint limits bytes to 12 MiB but passes the temporary file
to `cv2.imread` without a dimension, pixel-count, or decoded-memory limit
([`main.py`](main.py#L55-L58), [`main.py`](main.py#L178-L222)).

**Impact.** If the endpoint is exposed, decompression bombs or very large valid
images can consume host RAM/CPU before inference admission helps.

### P1 — No frontend request timeout or cancellation

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

### P1 — Four high-severity frontend dependency advisories are unresolved

**Evidence.** `npm audit --omit=dev` reported high-severity advisories for
direct `zod@4.6.5` and `vite@6.4.3`, plus transitive `undici@8.11.2` and
`source-map-js@1.2.1`. Audit metadata showed fixes available for all four.

**Impact.** `vite` exposure is chiefly the development server, while `zod`
ships in the client bundle. The full exposure depends on deployment topology,
but a production release should not carry known high-severity advisories
without an explicit risk decision.

### P2 — The application is not type-clean; its gate accepts 205 errors

**Evidence.** `.venv/bin/python -m tools.pyright_gate` passed only because it
matches `pyright.baseline` at 205 errors. The raw report includes 38 diagnostics
in `engine/pipeline.py`, including possible `None` access and wire-contract
type mismatches.

**Impact.** This is not evidence of 205 runtime failures, but it suppresses
new-signal value in a critical inference module and raises regression risk.

### P2 — Model artifacts are loaded from mutable upstream revisions at runtime

**Evidence.** The serving code calls Hugging Face / MoGe `from_pretrained` with
model names but no immutable revision for classifier, segmenter, depth, and
the DINO backbone ([`models/food_classifier.py`](models/food_classifier.py#L110-L115),
[`models/dish_segmenter.py`](models/dish_segmenter.py#L39-L47),
[`engine/depth.py`](engine/depth.py#L70-L82),
[`models/weight_head.py`](models/weight_head.py#L79)).

**Impact.** A cold environment can download changed artifacts, fail because of
network availability, or diverge from measured behavior. This is a
reproducibility, availability, and supply-chain risk.

### P2 — A transient model-load failure remains sticky until process recovery

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

### P2 — The UI can show an analysis as saved when browser persistence failed

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

### P1 — The locked WED test split can be read without the lock protocol

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

### P1 — General mode assigns unexplained food mass to matched recipe nutrition

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

### P1 — A negative base-plane height correction is not penalized by compliance

**Evidence.** The portion estimator flips all height signs when median height
is negative and records `base_sign_flip`
([`models/portion_estimator.py`](models/portion_estimator.py#L203-L212)).
Compliance coverage checks do not include that flag
([`engine/compliance.py`](engine/compliance.py#L59-L64)).

**Impact.** A corrected height map can retain full coverage and avoid an
abstention penalty even though its base-plane orientation required a global
sign reversal. This establishes a missing policy connection; it does not
establish how often the condition occurs in production captures.

### P1 — Recipe data lookup depends on the current working directory

**Evidence.** `models/recipe_table.py` opens `data/indb_recipes.yaml` as a
relative path ([`models/recipe_table.py`](models/recipe_table.py#L19-L31)),
while `config.py` defines the project root and data directory independently
of the process working directory ([`config.py`](config.py#L1-L14)). A `.venv`
reproduction launched from `/tmp` with the project on `PYTHONPATH` raised
`FileNotFoundError` for that recipe table.

**Impact.** Importing or running affected commands outside the repository
working directory can fail despite a valid project installation.

### P1 — Multipart request data is parsed and spooled before the endpoint byte cap

**Evidence.** FastAPI receives `UploadFile` form data and checks the 12 MiB
limit only inside the endpoint ([`main.py`](main.py#L195-L214)). The admission
middleware limits concurrent requests, not body bytes
([`main.py`](main.py#L20-L47)). Inspection of the installed Starlette parser
from `.venv` confirmed it consumes multipart input and writes file parts to a
spooled temporary file before the endpoint is called; its part-size check
applies to non-file fields.

**Impact.** An oversized upload can consume or spill temporary storage before
the endpoint returns 413. Exposure depends on network reachability and
deployment limits; this is separate from the decoded-image pixel limit above.

### P1 — Tracked WED-derived artifacts conflict with the documented release policy

**Evidence.** `docs/licenses.md` says WED terms are unresolved, nothing leaves
the machine, and derived artifacts remain release-gated
([`docs/licenses.md`](docs/licenses.md#L79-L89)). Git tracks
`data/wed_manifest.jsonl`, `data/wed/all_food_data.json`,
`data/wed/index_map.json`, `data/weight_head.pt`, and
`data/weight_head_sigma.yaml`; an older ADR says some artifacts are committed
([`docs/adr/0002-learned-weight-fallback.md`](docs/adr/0002-learned-weight-fallback.md#L57-L62)).

**Impact.** Repository state and current rights/release guidance disagree.
This is a provenance and release-governance conflict, not a legal conclusion.

### P2 — `plate_sanity_g` is configured and documented but has no runtime consumer

**Evidence.** The standard defines `plate_sanity_g`
([`data/standards.yaml`](data/standards.yaml#L67-L70)) and README says a lint
uses the plate sanity check ([`README.md`](README.md#L457-L465)), but source
search found no runtime use of that key.

**Impact.** Operators may believe this configured plausibility check runs when
it does not. The audit confirmed non-use in searched code, not whether a
separate untracked tool implements it.

### P2 — Student names containing percent escapes can break student routes

**Evidence.** Student list links encode the name with `encodeURIComponent`
([`frontend/src/pages/Students.tsx`](frontend/src/pages/Students.tsx#L93));
React Router supplies a decoded route parameter, and the detail page calls
`decodeURIComponent` again ([`frontend/src/pages/Students.tsx`](frontend/src/pages/Students.tsx#L295)).
An installed-router reproduction with `50% rice` raised `URIError` on the
second decode.

**Impact.** A valid student name containing a percent sign can make its detail
route fail to render.

### P2 — A malformed browser record can crash dashboard aggregation

**Evidence.** The persisted-record validator accepts any object with a string
`id` ([`frontend/src/services/records.ts`](frontend/src/services/records.ts#L174-L202)),
while dashboard tallying assumes `summary.verdict` exists
([`frontend/src/services/records.ts`](frontend/src/services/records.ts#L79-L88),
[`frontend/src/pages/Dashboard.tsx`](frontend/src/pages/Dashboard.tsx#L187)).
The auditor reproduced the crash using a record containing only `{"id":"x"}`.

**Impact.** Stale, manually edited, or partially written local storage can
break the dashboard instead of being rejected or safely ignored.

### P2 — “Clear all” leaves legacy records and profile data in browser storage

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

### P2 — Application startup can fail when browser local storage is unavailable

**Evidence.** `main.tsx` reads `window.localStorage` before React mounts and
without catching access errors ([`frontend/src/main.tsx`](frontend/src/main.tsx#L14-L23)).
Browsers can throw on storage access under restricted privacy settings or
storage policy.

**Impact.** The frontend can fail before rendering where the browser denies
local storage access.

### P2 — General mode still exposes school compliance analytics

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

### P2 — History memoization does not update when the app mode changes

**Evidence.** The history filter reads `general` in its memoized calculation,
but the dependency list omits it ([`frontend/src/pages/History.tsx`](frontend/src/pages/History.tsx#L51-L65)).

**Impact.** Changing modes while the history page remains mounted can leave
the list filtered using the previous mode until another dependency changes.

### P2 — README performance claims omit the scope of their evidence

**Evidence.** README presents MoGe approximately 1.1% median error and 46/46
gallery LOO results without the nearby synthetic/rendered and two-class scope
recorded in the diagnostic report ([`README.md`](README.md#L123-L126),
[`docs/diagnostic_report.md`](docs/diagnostic_report.md#L31-L46)).

**Impact.** The summary can be read as broader, independent real-image
validation than the underlying experiment supports. This is claim-scope debt,
not a new measurement.

### P2 — License documentation has conflicting Nutrition5k status

**Evidence.** `docs/licenses.md` describes Nutrition5k as planned, while the
dataset ledger and readiness report describe completed local/test analyses
([`docs/licenses.md`](docs/licenses.md#L17-L23),
[`docs/ledger/020-model-readiness-source-decisions.md`](docs/ledger/020-model-readiness-source-decisions.md#L45-L53),
[`docs/production-readiness.md`](docs/production-readiness.md#L118-L127)).

**Impact.** A reader cannot determine whether the source was only planned,
locally obtained, or used in experiments.

### P2 — Runtime evaluation reports do not bind results to exact weight-head artifacts

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

### P2 — Default file logging can prevent startup on a read-only application filesystem

**Evidence.** Importing `main.py` configures logging, creates `<repo>/logs`,
and opens a rotating file there unless `NUTRISENSE_LOG_DIR` is set
([`main.py`](main.py#L78-L102)). No CI job starts the app in a read-only
container or package directory ([`.github/workflows/ci.yml`](.github/workflows/ci.yml#L25-L83)).

**Impact.** A read-only deployment image or source directory can fail during
module import. This is conditional on deployment filesystem permissions.

### P2 — The onboarding modal lacks focus trapping and focus restoration

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

### L6 — General mode overstates its practical scope relative to evidence

The UI says “Analyze any meal” and “Any recognized Indian dish”
([`frontend/src/pages/Analyze.tsx`](frontend/src/pages/Analyze.tsx#L115-L121)).
The serving catalog is only the configured menu plus WED-derived off-menu
entries, and documented external test sets primarily abstained or failed
transfer. “Any” is therefore a product-copy overstatement, even though the
screen carries estimate caveats.

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
There is no authenticated identity, server persistence policy, deletion or
retention workflow, encryption-at-rest design, consent flow, or privacy notice
for real deployment. For a localhost demonstration this is not automatically a
security flaw; for school use it is an unresolved product and compliance gap.
The browser profile is shared without user scoping, there is no retention
expiry, and the visible clear action leaves legacy and profile keys behind
(see the P2 deletion-control finding above). The onboarding modal also lacks
complete keyboard focus management.

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
[`docs/production-readiness.md`](docs/production-readiness.md#L93-L110)).
Together with the unguarded scripts identified above, this means reported WED
test metrics should be treated as historical internal evidence, not as a new
one-time independent test. No test-split data was opened for this audit.

### L14 — Build and hosted automation are not fully pinned to immutable actions

The CI workflow references third-party actions by version tags rather than
commit digests ([`.github/workflows/ci.yml`](.github/workflows/ci.yml#L25-L83)).
Tags can be moved upstream, so the checked-in workflow does not by itself
provide immutable action provenance. CI also validates a limited offline and
mocked path; it does not establish GPU or deployment-image behavior.

### L15 — Upload resource safety depends on controls outside the application

The endpoint has no application-level request-body timeout, and multipart
parsing precedes the endpoint's byte cap. A slow or oversized request can hold
request capacity or temporary storage unless the hosting proxy/server applies
body-size, connection, and request-time limits. No such production proxy
configuration is present in the repository; this remains a deployment gap.

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
6. **Temporary-storage and slow-upload controls.** Oversized multipart bodies
   are parsed before the endpoint limit, and no application request timeout is
   enforced. The external proxy/server must bound body size, upload duration,
   and temporary storage for a reachable deployment.

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
