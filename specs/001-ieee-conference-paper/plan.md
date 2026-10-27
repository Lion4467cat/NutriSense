# Implementation Plan: NutriSense IEEE Conference Paper

**Branch**: `main` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-ieee-conference-paper/spec.md`; follow-up readability and pending-dataset-results revision.

## Summary

Revise the evidence-based IEEE conference manuscript to resolve audit findings and author feedback. Keep the official IEEE conference template, show the runtime in a spacious two-column-wide figure with separated branches, use a neat and balanced four-author block, clearly separate current WED development evidence from the project's uncollected dataset, reserve a labeled pending-results area, correct the no-marker head-failure path, state policy/evaluation boundaries explicitly, remove unsettled segmentation IoU, and use traceable final bibliography metadata. Preserve the supplied author details and clearly marked dummy coauthor emails.

## Technical Context

**Language/Version**: LaTeX source with BibTeX references; IEEEtran 1.8b conference mode, with the upstream `bare_conf.tex` retained as the source starter. Check the selected event's current author kit before submission.

**Primary Dependencies**: IEEEtran conference class and supplied BibTeX style; local TeX Live 2026 (`pdflatex`, BibTeX, and `latexmk`) driven through `paper/build.sh`; reproducible figure assets; primary-source references. Overleaf uses the same vendored project files with its hosted compiler.

**Storage**: Text sources, bibliography, and figures under `paper/`; planning artifacts under `specs/001-ieee-conference-paper/`.

**Validation**: Compile the source and bibliography to PDF; inspect every page for template guidance text, layout overflow, figure/table readability, author-block spacing, citation completeness, and factual consistency. Confirm project-specific dataset results remain marked pending while WED DEV remains clearly identified as the existing fallback evidence. Do not run application test suites for this manuscript-only change. Use IEEE PDF eXpress only if the selected conference requires it.

**Target Platform**: Portable LaTeX toolchain and PDF output. Use the official template selector's generic conference template; the selected conference's page size and submission instructions take precedence when known.

**Project Type**: Research manuscript and reproducible submission artifact; this feature does not change the NutriSense runtime application.

**Performance Goals**: Not applicable to manuscript authoring.

**Constraints**: Generic IEEE conference format; no target event or page limit selected. Use current official IEEE template files, do not redistribute restricted dataset imagery, preserve author-provided contact details, and separate DEV, TRAIN, and LOCKED evidence. Do not invent a DINOv2-S test result. The runtime returns one mask and one dish classification per capture; WED evaluation uses ground-truth ROI/class inputs. A conflicting SAM synthetic IoU must be omitted until reconciled.

**Scale/Scope**: One conference paper, one editable source, bibliography, figures/tables, and a compiled review PDF. No new experiments are included in this plan.

**Citation policy for project results**: Report in-house metrics as author-generated results with their evaluation protocol, split, sample basis, and scope stated in the manuscript. Do not include the NutriSense repository itself as a bibliography reference.

## Constitution Check

**Pre-design gate**

- **Evidence Before Claims**: Pass. Manuscript claims must cite project reports or primary sources; assumed parameters remain marked as assumptions.
- **Reproducible Evaluation**: Pass. The current DINOv2-S numbers are DEV-only. LOCKED results are not claimed or repurposed.
- **Honest Uncertainty**: Pass. The paper will distinguish marker-based measured scale, prior scale, and learned-weight estimates, and state pending real-world validation.
- **Preserve Public Contracts**: Pass. The paper work does not alter runtime API or policy contracts. The adjacent marker-size correction only removes a duplicate calibration constant and clarifies capture documentation.
- **Verify Proportionately**: Pass. The marker PDF is verified against the existing detector configuration and rendered physical size. Manuscript validation is defined in quickstart; no evaluation lock is regenerated.
- **Data rights**: Pass with a constraint. Cite the WED source, but do not include or redistribute locally held WED images unless reuse rights are confirmed.

**Post-design gate**: Pass. The design keeps manuscript sources separate from application code, cites primary research and official IEEE guidance, specifies a citation-to-claim audit, and leaves venue-specific rules as a final check when an event is selected.

## Phase 0: Research Summary

See [research.md](research.md) for the source-by-source decisions and caveats. Key decisions:

- Select IEEE's official conference LaTeX template in conference mode. IEEE provides Word and LaTeX templates; the target conference's current instructions take precedence over generic defaults.
- Structure the paper around the pipeline and its evidence: card-based metric scale, fallback paths, dish localization/classification, learned weight estimation, nutrient uncertainty, and PM POSHAN policy scoring.
- Treat the current result as WED DEV performance: 15.034 g MAE on 108 views / 21 plates / 1,218 ROIs with a plate-bootstrap 95% interval of [12.227, 18.889]. The paired DEV difference against the ResNet-50 baseline is −5.264 g [−6.232, −4.227]. Do not claim a DINOv2-S LOCKED/test result.
- Scope SAM2.1 IoU 0.98, geometry volume errors, and MoGe's 1.1% depth calibration error to their synthetic/rendered validation. Scope SigLIP2 46/46 to gallery leave-one-out, not independent test performance. The current gallery contains 46 images from two dish classes; the runtime returns one predicted label or abstention per capture and uses text-prompt scores only when no gallery is available.
- Use the provided A4 PDF as the field scale marker. It was preserved unchanged; its A4 page and 60 mm ArUco ID 7 geometry match the project detector. The former A6/100 mm graphic remains only as a synthetic fixture generator, not a field-capture asset.

## Phase 1: Design

### Audit Corrections

- Build the conference-width pipeline diagram from current runtime behavior, not the stale README fallback: mapped no-marker dish plus missing/failing learned head returns `cannot_verify`; only an unmapped no-marker dish uses size-prior geometry.
- Explicitly represent the current one-mask/one-dish-per-image scope, unrecognized and out-of-scope outcomes, stage errors, measured/no-marker mass paths, compliance thresholds, disclaimer, and serialized response.
- Recompose the diagram into clearly separated rows/lanes with generous whitespace and shorter labels; ensure the full-width PDF remains legible at page scale and avoid overlapping connectors.
- Retain an explicitly labeled, pending project-dataset-results slot with fields for sample counts, mass error/intervals, uncertainty coverage, and end-to-end evaluation; do not populate it until this dataset is collected and evaluated. State that WED DEV is the only current dataset-based mass-estimation result, and distinguish the existing 46-image classifier gallery leave-one-out check from the pending real-meal mass-annotated capture dataset.
- Rebalance and uncramp the IEEE author block while preserving all supplied names, affiliation, and email placeholder labels.
- Place each of the four authors in a separate, evenly spaced conference author block with a consistent affiliation line; keep contact text small enough to fit without colliding or wrapping into another author's block.
- Place the wide pipeline float in the main body before Results and References, close to the System Overview discussion, while keeping IEEE conference float behavior.
- State exact national PM POSHAN minima and probability/coverage gates, and distinguish these from the Karnataka state extension that supports the project's 9–10 band.
- State that WED DEV mass evaluation uses ground-truth ROI/class labels, the plate-grouped 10% carve, fixed seed 42, and 2,000 plate-bootstrap replicates; it is not upstream or end-to-end evaluation.
- Remove the disputed synthetic IoU point estimate from the paper; the module note says 0.97 while summary reports say 0.98.
- Cite SAM 2's ICLR 2025 paper and the official Meta SAM 2.1 repository, DINOv2's TMLR 2024 publication, and the official PM POSHAN guideline dated 21 December 2022. Record the Thali article's actual proceedings pages 1--9. See [citation-audit.md](citation-audit.md) for the completed source-by-source audit.
- Audit all in-text citation keys against `references.bib`; verify titles, authors, versions, venues/years, identifiers, and claim support using the primary paper or official guideline. Use the MoGe-2 record because that is the model named by the implementation, and record all outcomes in `citation-audit.md`.
- Keep project evaluation records out of the bibliography; state project metrics as author-generated and provide enough protocol detail to understand each result.

### Manuscript Structure

1. Title, author affiliations, abstract, and index terms.
2. Introduction and problem framing for image-based meal assessment in a school meal setting.
3. Related work: visual food/portion estimation, Indian thali datasets, and relevant foundation models.
4. NutriSense method: scale anchor and 60 mm marker, segmentation/classification, portion pathways, nutrient uncertainty, and compliance decisions.
5. Experimental protocol: WED split handling, DEV-only tuning, metrics, and separate synthetic validation.
6. Results: current DEV evaluation, paired DINOv2-S comparison, and explicitly scoped stage-level results.
7. Limitations and discussion: dataset/domain limits, no DINOv2-S test result, unvalidated assumptions, coverage behavior, and pending field validation.
8. Conclusion and references.

### Planned Artifact Layout

```text
paper/
├── main.tex                 # IEEE conference manuscript
├── references.bib           # IEEE-formatted bibliography records
├── figures/                 # Author-created diagrams/charts only
├── IEEE_TEMPLATE_SOURCE.md  # Source URL, version/date, and local modifications
└── README.md                # Reproduction and compilation instructions

specs/001-ieee-conference-paper/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
└── quickstart.md
```

### Interface Contracts

No API or external software contract is introduced by this feature; the deliverable is a paper source and PDF. A `/contracts/` directory is not needed.

### Complexity Tracking

No constitution violations or unnecessary system complexity are introduced.
