# Implementation Plan: NutriSense IEEE Conference Paper

**Branch**: `main` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-ieee-conference-paper/spec.md`

## Summary

Prepare an evidence-based IEEE conference manuscript describing NutriSense's single-image meal analysis pipeline and its evaluation. Use the official IEEE conference LaTeX template in conference mode, preserve all project-specific evidence and uncertainty labels, and distinguish the current DINOv2-S DEV result from historical ResNet-50 and LOCKED test results. The author block uses the supplied four authors and BMS College of Engineering; three example email addresses remain explicit placeholders.

## Technical Context

**Language/Version**: LaTeX source with BibTeX references; use the version of IEEE's official conference template obtained for the manuscript.

**Primary Dependencies**: Official IEEE conference LaTeX template (`IEEEtran` conference mode and its supplied bibliography style); reproducible figure assets; primary-source references.

**Storage**: Text sources, bibliography, and figures under `paper/`; planning artifacts under `specs/001-ieee-conference-paper/`.

**Testing**: Compile the source and bibliography to PDF; inspect every page for template guidance text, layout overflow, figure/table readability, citation completeness, and factual consistency. Use IEEE PDF eXpress only if the selected conference requires it.

**Target Platform**: Portable LaTeX toolchain and PDF output. Use the official template selector's generic conference template; the selected conference's page size and submission instructions take precedence when known.

**Project Type**: Research manuscript and reproducible submission artifact; this feature does not change the NutriSense runtime application.

**Performance Goals**: Not applicable to manuscript authoring.

**Constraints**: Generic IEEE conference format; no target event or page limit selected. Use current official IEEE template files, do not redistribute restricted dataset imagery, preserve author-provided contact details, and separate DEV, TRAIN, and LOCKED evidence. Do not invent a DINOv2-S test result.

**Scale/Scope**: One conference paper, one editable source, bibliography, figures/tables, and a compiled review PDF. No new experiments are included in this plan.

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
- Scope SAM2.1 IoU 0.98, geometry volume errors, and MoGe's 1.1% depth calibration error to their synthetic/rendered validation. Scope SigLIP2 46/46 to gallery leave-one-out, not independent test performance.
- Use the provided A4 PDF as the field scale marker. It was preserved unchanged; its A4 page and 60 mm ArUco ID 7 geometry match the project detector. The former A6/100 mm graphic remains only as a synthetic fixture generator, not a field-capture asset.

## Phase 1: Design

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
