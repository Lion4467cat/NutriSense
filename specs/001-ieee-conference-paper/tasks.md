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
