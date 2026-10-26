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

**Goal**: Preserve supplied author order, cite project-specific evidence, bound the policy claim to the captured serving, and correct final layout/validation records.

- **Independent Test**: Compile and inspect every PDF page; author order is clear, project metrics cite their supporting repository artifacts, no multi-dish whole-meal compliance claim is made, and validation records match the rendered output.

- [X] T020 [US1] Correct visible author order, cite repository evidence for project-specific metrics, clarify single-serving verdict scope, rebalance the float/reference layout, synchronize the quickstart, and recompile/inspect the paper.
