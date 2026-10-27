# Tasks: NutriSense IEEE Paper Audit Corrections

**Input**: Design documents from `specs/001-ieee-conference-paper/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, and `quickstart.md`

**Tests**: No application tests requested; validate the paper by compiling and visually inspecting the generated PDF.

## Phase 1: Setup

**Purpose**: Confirm the current sources that constrain the paper.

- [X] T001 [US1] Reconcile pipeline, thresholds, and evaluation scope against `engine/pipeline.py`, `engine/compliance.py`, `data/standards.yaml`, and `docs/ledger/002-dinov2-encoder.md` before editing the manuscript.

## Phase 2: Manuscript Accuracy (User Story 1, Priority: P1)

**Goal**: Make the methods, evaluation, and diagram match the current runtime and evidence.

**Independent Test**: Compare each diagram branch and each numerical claim in `paper/main.tex` with its cited code, report, or primary source; no unsupported or contradictory claim remains.

- [X] T002 [US1] Correct single-mask/single-dish scope, no-marker fallback behavior, policy thresholds, age-band minima, WED DEV protocol, and limitations in `paper/main.tex`.
- [X] T003 [US1] Replace the compact flowchart in `paper/main.tex` with a legible conference-width diagram showing all principal runtime paths and outputs, following `engine/pipeline.py` and the corrected behavior in `README.md`.
- [X] T004 [P] [US1] Update references to final publication metadata and exact official guideline source/date in `paper/references.bib`.
- [X] T005 [P] [US1] Correct the README fallback branch so `README.md` matches current learned-head behavior in `engine/pipeline.py`.
- [X] T006 [US1] Remove the disputed synthetic SAM IoU point estimate from `paper/main.tex` and scope the test as synthetic component evidence.

## Phase 3: IEEE Draft Readiness (User Stories 2 and 3, Priority: P1/P2)

**Goal**: Keep the paper in IEEE conference format and make draft-only metadata explicit.

**Independent Test**: Compile the manuscript using the vendored IEEE conference class and inspect all PDF pages for readable figures, complete citations, and unmarked placeholder emails.

- [X] T007 [US3] Mark the three `example.com` addresses as placeholders in the author block of `paper/main.tex`, retaining `gokulaswamyss@gmail.com` exactly.
- [X] T008 [US2] Update `paper/README.md` with the revised figure, draft status, and the remaining venue/page-limit check.
- [X] T009 [US2] Compile `paper/main.tex` with its bibliography and inspect the generated `paper/main.pdf` for clipping, legibility, citation rendering, and IEEE two-column layout.

## Phase 4: Polish

**Purpose**: Record completion and preserve review readiness.

- [X] T010 [US2] Update `specs/001-ieee-conference-paper/quickstart.md` with the paper validation outcome and any remaining venue-specific submission requirement.

## Dependencies & Execution Order

- T001 is the evidence gate and precedes manuscript changes.
- T002, T003, and T006 edit `paper/main.tex` and must be completed sequentially.
- T004 and T005 affect separate files and can proceed independently after T001.
- T007 and T008 also edit `paper/main.tex` and `paper/README.md`; complete them before T009.
- T009 precedes T010 because the quickstart records the actual validation result.

## Parallel Opportunities

- After T001, T004 (`paper/references.bib`) and T005 (`README.md`) can be done independently while the manuscript text/figure is edited sequentially.

## Implementation Strategy

Complete all corrections in the existing IEEE draft, then compile and visually inspect it as one reviewable deliverable. The draft remains generic because no target conference or page limit has been selected.

## Phase 5: Readability and Pending Project Dataset (User Stories 1 and 2, Priority: P1)

**Goal**: Address author feedback on figure and author-block readability, and make the uncollected project dataset distinct from the available WED fallback evidence.

**Independent Test**: At IEEE two-column page size, the flowchart and author block have visible whitespace and no cramped/overlapping content; paper text reports only existing WED DEV data-based results, while project-dataset results are clearly marked pending.

- [X] T011 [US1] Update `specs/001-ieee-conference-paper/spec.md` with the readability, author-block, and pending project-dataset requirements and success criteria.
- [X] T012 [US1] Update `specs/001-ieee-conference-paper/plan.md` and this task plan for the new readability and pending-results scope.
- [X] T013 [US1] Redesign `paper/figures/pipeline.svg` with spacious grouped paths and update `paper/figures/pipeline.pdf` from that source.
- [X] T014 [US1] Clarify WED DEV as fallback dataset evidence, add a clearly labeled pending project-dataset results subsection/table, and rebalance the four-author block in `paper/main.tex`.
- [X] T015 [US2] Compile and visually inspect `paper/main.pdf`; update `paper/README.md` and `specs/001-ieee-conference-paper/quickstart.md` with validation and outstanding data-collection/submission steps.

**Dependencies & Execution Order**: T011 and T012 precede implementation. T013 and T014 can be edited independently after T012; T015 follows both.

**Implementation Strategy**: Preserve current WED values as development-only fallback results; do not invent project-dataset metrics. Keep the pending-results area visibly distinct and replace its pending labels only after project data collection and evaluation.

## Phase 6: Flowchart Placement (User Story 1, Priority: P1)

**Goal**: Keep the architecture figure close to its first explanation, before detailed methods.

**Independent Test**: In the compiled PDF, the figure appears in the main body before Results and References, rather than after them.

- [X] T016 [US1] Adjust the wide figure float placement in `paper/main.tex`, compile and inspect `paper/main.pdf`, and record the result in `specs/001-ieee-conference-paper/quickstart.md`.

## Phase 7: Citation and Source Audit (User Story 1, Priority: P1)

**Goal**: Verify every citation against its actual source and ensure the manuscript's statements and bibliography metadata match.

**Independent Test**: Trace each citation key from manuscript to a primary publication or official document, verify its metadata and supported claim, and confirm there are no missing or unused records.

- [X] T017 [US1] Cross-check all in-text citations and bibliography entries against primary sources; correct the MoGe-2 record, exact PM POSHAN PDF, proceedings metadata, and any unsupported wording; document the source-by-source audit.
- [X] T018 [US1] Verify national PM POSHAN grade coverage and nutrition bands; revise the manuscript and source audit to state Bal Vatika through class VIII coverage.
- [X] T019 [US1] Verify Karnataka's official IX–X state Mid-Day Meal extension, update the 9–10 configuration basis, and distinguish the state extension from central PM POSHAN coverage throughout the paper and audit.

**Validation**: Recompile the paper and inspect rendered references and nearby claims. Record the audit outcome in `citation-audit.md` and `quickstart.md`.

## Phase 8: Final Manuscript Audit Corrections (User Stories 1 and 2, Priority: P1)

**Goal**: Preserve supplied author order, document project-specific evidence without a repository self-citation, bound the policy claim to the captured serving, and correct final layout/validation records.

- **Independent Test**: Compile and inspect every PDF page; author order is clear, project metrics state their evaluation protocols without citing the project's own repository, no multi-dish whole-meal compliance claim is made, and validation records match the rendered output.

- [X] T020 [US1] Correct visible author order, document project-metric evaluation protocols, clarify single-serving verdict scope, rebalance the float/reference layout, synchronize the quickstart, and recompile/inspect the paper.

## Phase 9: Reproducible TeX Build and Overleaf Setup (User Story 2, Priority: P1)

**Goal**: Restore a working local TeX compiler, give authors a one-command build, and keep the complete manuscript project ready for Overleaf.

- **Independent Test**: `paper/build.sh` successfully compiles `main.tex`, bibliography, and project figure to `paper/main.pdf`; the Overleaf instructions identify all required files and the main document.

- [X] T021 [US2] Repair the local TeX Live installation, add `paper/build.sh`, document the Overleaf project setup, update the specification and quickstart, and verify a complete build.

## Phase 10: Codebase Consistency Follow-up

**Purpose**: Resolve remaining wording gaps found by checking the manuscript against the current implementation and evidence.

- [X] T022 [US1] Qualify WED as the only current dataset-based **mass-estimation** result and define the pending project dataset as real-meal mass-annotated captures, distinguishing both from the existing 46-image classifier gallery per FR-005, FR-019, and SC-009.
- [X] T023 [US1] Describe the DINOv2-S head as encoding the resized full capture and ROI-pooling a bounding box derived from the segmentation mask; state that the pipeline currently runs MoGe before selecting the mass path, so a depth-stage failure can prevent learned-weight estimation, per FR-004, SC-006, and `engine/pipeline.py`.
- [X] T024 [US1] Distinguish official Bal Vatika/national coverage from the application's three configured bands (1--5, 6--8, and Karnataka 9--10), and state that no separate Bal Vatika band is exposed, per FR-015 and FR-024.
- [X] T025 [US1] Remove the README claim that every no-card prior-tier result is unable to reach PASS/FAIL and make the overview agree with the implemented learned-weight versus size-prior geometry paths, per T005 and `engine/compliance.py`.
- [X] T026 [US2] Rebuild the paper and visually inspect its layout after the codebase consistency corrections, per FR-012.
- [X] T027 [US2] Upload the corrected local source to the existing `nutrisense` Overleaf project and confirm its hosted build, per FR-027.
- [X] T028 [US2] Commit and push the validated manuscript and documentation corrections to `main`, per FR-027.

## Phase 11: Repository Citation Removal and Classifier/Diagram Precision

**Goal**: Remove the project's own repository from the bibliography, accurately explain the current SigLIP 2 classifier behavior and gallery scope, and improve first-row flowchart spacing and connector visibility.

**Independent Test**: No manuscript citation or bibliography entry points to the NutriSense repository; the classifier description matches the runtime (one output label per capture, current 46-image/two-class gallery, text scoring only without a gallery); the rebuilt diagram has clear arrows and contained labels.

- [X] T029 [US1] Remove the NutriSense repository citation, preserve the project metrics as author-generated results with evaluation scope/protocol, and update citation-audit and authoring documentation.
- [X] T030 [US1] Correct SigLIP 2 wording to distinguish one predicted dish label per capture from the number of candidate classes/model capacity, and state that the current gallery has 46 images across two dish classes.
- [X] T031 [US1] Widen the first-row flowchart gaps, strengthen arrowheads/strokes, compile the paper, and inspect the complete rendered diagram for overflow and readability.
- [X] T032 [US2] Upload the reviewed source and updated diagram asset to the existing Overleaf project, confirm its hosted build, then commit and push all changes to `main`.

## Phase 12: Flowchart Text Containment

**Goal**: Keep all flowchart labels inside their node boundaries in the compiled paper and in the Overleaf project.

**Independent Test**: Render the SVG and the compiled IEEE PDF; confirm each node's text stays inside its shape, then verify Overleaf compiles the updated `figures/pipeline.pdf` with zero errors.

- [X] T033 [US1] Wrap the measured-scale geometry detail into centered lines that fit inside its node and inspect all flowchart node text bounds.
- [X] T034 [US2] Regenerate the vector PDF, rebuild and visually inspect the paper, replace the `figures/pipeline.pdf` asset in Overleaf, verify the hosted build, and commit and push the updated diagram to `main`.

## Phase 13: Citation Verification Refresh

**Goal**: Recheck every manuscript citation against current primary sources, use final publication records where available, and bound government-policy claims to the evidence.

**Independent Test**: Every in-text key resolves to one bibliography record, every record is cited, metadata matches its source, the source supports the nearby claim, and the compiled IEEE bibliography has no unresolved citation warnings.

- [X] T035 [US1] Reverify all ten citations and source claims; update MoGe-2 to its final NeurIPS 2025 record, clarify the Karnataka 9--10 threshold as an application mapping, record the WED pagination evidence limits, rebuild the manuscript locally and in Overleaf, and confirm zero hosted compile errors.
