# Feature Specification: NutriSense IEEE Conference Paper

**Feature Branch**: `main` (per user request)

**Created**: 2026-10-26

**Status**: Draft

**Input**: User request: update the IEEE conference paper after project integration, using the current runtime behavior, evaluation evidence, limitations, strengths, and future work. Authors are SS Gokula Swamy, Roshanth V, Somanath S.D, and Aryan Kumar, affiliated with BMS College of Engineering. Contact addresses are not supplied for all authors and must not be invented.

## User Scenarios & Testing

### User Story 1 - Review the project as a research manuscript (Priority: P1)

The project authors need a concise conference paper that explains NutriSense's motivation, method, evaluation, findings, and limitations in a form suitable for coauthor review.

**Why this priority**: A defensible, readable account of the project is the central deliverable.

**Independent Test**: A reviewer unfamiliar with the repository can read the draft and explain the system's input, outputs, method, evidence, and limitations without relying on undocumented details.

**Acceptance Scenarios**:

1. **Given** the current repository and its reports, **When** an author reviews the manuscript, **Then** the described pipeline and results match the current implementation and cited evidence.
2. **Given** the paper's evaluation section, **When** a reviewer traces each metric, **Then** the model, split, sample count, uncertainty interval, and source report are identifiable.
3. **Given** the system diagram and methods, **When** a reviewer compares them with the current repository, **Then** the diagram includes multi-item detection, overlap partitioning, qualified estimate-only fallbacks, measured-scale and no-marker paths, policy outcomes, and hard failure paths without implying validated real-photo accuracy.
4. **Given** conflicting repository summaries for a component metric, **When** the paper reports evaluation evidence, **Then** it reports only a reconciled, traceable value or omits that quantitative claim.

### User Story 2 - Prepare the manuscript in IEEE conference format (Priority: P1)

The authors need the paper composed with the official IEEE conference template and checked against its formatting guidance.

**Why this priority**: The requested output is an IEEE conference paper, and template compliance affects whether it can be submitted.

**Independent Test**: The manuscript source compiles into a readable two-column conference-format PDF using the official IEEE template, with template instructions removed and no overflowing content.

**Acceptance Scenarios**:

1. **Given** the IEEE conference manuscript source, **When** it is compiled with the official template, **Then** the result has the IEEE conference layout and contains no example guidance text.
2. **Given** figures, tables, equations, and references in the paper, **When** the compiled PDF is reviewed, **Then** they remain legible, numbered, cited, and within page boundaries.

### User Story 3 - Preserve accurate authorship metadata (Priority: P2)

The authors need their names and supplied institutional affiliation included without inventing or publishing unverified contact addresses.

**Why this priority**: The author block must identify contributors accurately while keeping submission metadata verifiable.

**Independent Test**: The author block contains all four supplied names and BMS College of Engineering, and contains no fabricated email addresses.

**Acceptance Scenarios**:

1. **Given** the author details supplied by the project owner, **When** the manuscript metadata is checked, **Then** the names and affiliation match those details.
2. **Given** that only one author address was supplied, **When** the draft is compiled, **Then** it omits all email addresses until the authors verify the required submission contacts.

### Edge Cases

- The target conference may impose a different page size, page limit, anonymization rule, or bibliography requirement; the venue's current instructions must override the generic IEEE defaults when a venue is selected.
- Historical project reports may describe an earlier model. The manuscript must label those results as historical and must not present old ResNet-50 test results as current DINOv2-S performance.
- The WED mass-head reports include a DEV carve and a one-time LOCKED report; the locked result is descriptive evidence only and is not an independent end-to-end product result.
- Some project parameters remain assumed or await field validation; these must be reported as limitations rather than established findings.
- The field marker is a 60 mm ArUco printed on A4. The legacy 100 mm square in the synthetic A6 fixture is not a field measurement and must not appear as the project's capture protocol.

## Requirements

### Functional Requirements

- **FR-001**: The manuscript MUST explain the NutriSense problem, intended setting, and expected contribution in terms understandable to a computer-vision and applied-health audience.
- **FR-002**: The manuscript MUST describe the end-to-end workflow from a meal photograph through dish recognition, portion estimation, nutrient uncertainty, and PM POSHAN compliance assessment.
- **FR-003**: The manuscript MUST distinguish measured scale from the 60 mm ArUco marker on A4 from prior-tier estimates used when no marker is detected.
- **FR-004**: The manuscript MUST describe the actual model components and their roles without implying that a model or data collection step was used when it was not.
- **FR-005**: Every quantitative result MUST identify its metric, evaluation split, sample basis, model/checkpoint where relevant, and enough evaluation-protocol detail to distinguish author-generated results from published evidence.
- **FR-006**: The manuscript MUST report the current DINOv2-S WED DEV MAE and its confidence interval from the current evaluation ledger. If it includes the one-time LOCKED report, it MUST label it descriptive, disclose its coverage, and state that it was not used for retuning or calibration.
- **FR-007**: The manuscript MUST identify limitations, including the distinction between DEV and test results, assumed parameters, coverage effects, and pending real-world validation.
- **FR-008**: The manuscript MUST use the official IEEE conference template in conference mode and remove template guidance text from the paper.
- **FR-009**: The manuscript MUST include the authors SS Gokula Swamy, Roshanth V, Somanath S.D, and Aryan Kumar, with BMS College of Engineering as the supplied affiliation.
- **FR-010**: The author block MUST omit unverified email addresses and MUST NOT invent contact details.
- **FR-011**: The manuscript MUST cite primary sources for methods, datasets, standards, and prior-work comparisons, and MUST include complete, traceable references.
- **FR-012**: The source and compiled PDF MUST be reviewed for formatting, figure/table readability, citation completeness, and factual consistency before delivery.
- **FR-013**: The pipeline figure MUST be a legible, full-width, detailed representation of current runtime paths, including input/stage-failure abstention, unrecognized-dish abstention, out-of-scope dishes, measured geometry, mapped no-marker learned mass, learned-head unavailability, unmapped-dish size-prior geometry, compliance verdicts, and the serialized response.
- **FR-014**: The paper MUST describe the current multi-item path: a top-level food mask, up to nine region proposals, overlap partitioning, per-region estimates, and meal-level aggregation. It MUST distinguish this implementation from validated real-photo multi-item accuracy.
- **FR-015**: The methods MUST specify mandatory nutrients, student-band minima, probability thresholds, coverage thresholds, cooked-plate energy basis, and the Karnataka state basis for the configured 9–10 band.
- **FR-016**: The evaluation protocol MUST state that WED DEV mass evaluation uses ground-truth class/ROI inputs and does not exercise upstream segmentation or classification, and MUST scope the data split and bootstrap method.
- **FR-017**: The manuscript MUST omit or clearly qualify quantitative claims whose source evidence conflicts; specifically, no single synthetic segmentation IoU may be presented as settled until the repository evidence is reconciled.
- **FR-018**: Bibliographic records MUST use final publication metadata when available, cite the exact official PM POSHAN guideline and date, and distinguish a paper's page count from proceedings pagination.
- **FR-019**: The manuscript MUST distinguish existing WED evidence from the 23-view real-plate pilot and state that no fresh, independently annotated evaluation set is available for validating the current integration. It MUST NOT reserve placeholder results or invent values.
- **FR-020**: The full-width runtime figure MUST use a readable visual hierarchy and separated paths with sufficient whitespace; labels and connectors MUST remain legible at the compiled IEEE page size, every node label MUST fit within its containing shape, and branch crossings MUST not obscure text.
- **FR-021**: The four authors MUST appear in a balanced IEEE author layout; unverified contact addresses MUST be omitted.
- **FR-022**: The pipeline figure MUST appear in the main body before the Results section, near its System Overview discussion, rather than after the references; retain compliant IEEE float placement.
- **FR-023**: Every in-text citation MUST resolve to one bibliography entry, and every bibliography entry MUST be cited. Each record MUST identify the source actually used (including model version and final publication metadata where available), and the nearby claim MUST be supported by that source; claims must be narrowed when a source does not justify them.
- **FR-024**: The manuscript MUST distinguish national PM POSHAN coverage (Bal Vatika and classes I–VIII) and its primary and upper-primary norms from Karnataka's state Mid-Day Meal extension to classes IX–X. The configured 9–10 band MUST be identified as representing the Karnataka extension, with its upper-primary nutrition basis supported by official Karnataka sources; it MUST NOT be described as centrally defined PM POSHAN eligibility.
- **FR-025**: Every quantitative project result in the manuscript MUST be presented as an author-generated result with its value, evaluation setting, sample basis, and protocol stated; the project's own repository MUST NOT be included as a bibliography reference.
- **FR-026**: The manuscript MUST state that policy scoring uses detected and aggregated regions only when the structure and labels are sufficiently supported; estimate-only fallbacks have no compliance verdict, and current multi-item accuracy is not independently validated.
- **FR-027**: The paper project MUST provide a one-command local build using its configured TeX Live installation and document how to compile the complete project in Overleaf using the vendored assets.

### Key Entities

- **Manuscript**: Title, abstract, sections, figures, tables, equations, references, and final compiled paper.
- **Author**: Name, supplied affiliation, and verified contact details if available.
- **Project method**: Image inputs, stages, model roles, measured and prior scale paths, uncertainty, and compliance output.
- **Evaluation result**: Metric, model/checkpoint, data split, sample basis, confidence interval, protocol, and source.
- **Reference**: Primary publication or official guidance cited to support a method, dataset, standard, or formatting decision.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All four supplied author names and their shared institution appear correctly; no unverified contact address is fabricated.
- **SC-002**: Every numerical project claim in the paper can be traced to a project report, evaluation output, or cited primary source.
- **SC-003**: The evaluation section distinguishes DEV, the one-time LOCKED report, gallery diagnostics, the historical ArUco pilot, and synthetic checks, with no claim that any one component result validates the full pipeline.
- **SC-004**: The manuscript compiles with the official IEEE conference template and has no unremoved template guidance, clipped text, or unreadable figures/tables.
- **SC-005**: A coauthor can identify the paper's contribution, method, strongest evidence, and principal limitations from the manuscript without consulting the source code.
- **SC-006**: The diagram's branches agree with `engine/pipeline.py`, including multi-item region handling and estimate-only fallbacks, and the narrative states that post-fix real-photo quality has not been measured.
- **SC-007**: The policy thresholds and WED evaluation boundary are stated with the exact values and input scope used by the repository.
- **SC-008**: All references identify traceable publication or official-document metadata; no conflicting synthetic IoU value is presented as settled evidence.
- **SC-009**: The manuscript reports the 23-view, six-plate ArUco pilot with its pre-change outcome and EVAL-ONLY boundary, while clearly stating that no fresh independently annotated dataset validates the current integration.
- **SC-010**: At IEEE two-column page size, every flowchart label remains within its node boundary and branch labels/connectors can be read without overlap or visually cramped convergence.
- **SC-011**: The four supplied author names and their shared affiliation appear clearly in the compiled title area, without fabricated contact details.
- **SC-012**: The flowchart appears before the Results section and before the references in the compiled paper.
- **SC-013**: A documented source-by-source audit confirms that every in-text citation has a matching, accurate bibliography record, every bibliography entry is used, and each cited source supports its associated manuscript claim.
- **SC-014**: The policy discussion identifies Bal Vatika and classes I–VIII as national PM POSHAN coverage and accurately explains the separately documented Karnataka IX–X state extension and the 700 kcal / 20 g threshold used by the project band.
- **SC-015**: Every project-specific numerical metric in the manuscript has an explicit scope label (for example, synthetic, gallery leave-one-out, or WED DEV) and enough protocol detail to identify the evaluation; the project's own repository is absent from the bibliography.
- **SC-016**: The manuscript states that the policy result applies to detected and aggregated regions; estimate-only fallbacks have no compliance verdict, and current multi-item accuracy is not independently validated.
- **SC-017**: From the `paper/` directory, `./build.sh` compiles `main.tex`, its bibliography, and the pipeline figure into `main.pdf`; the documented Overleaf workflow includes all required project files and selects `main.tex`.

## Assumptions

- The target is a generic IEEE-sponsored conference paper; no specific conference, page limit, or submission portal has been selected.
- The official IEEE conference template is the required baseline. Once a venue is selected, its current instructions may further constrain the manuscript.
- The paper will summarize existing project evidence; it will not report new experiments unless the authors later authorize and conduct them.
- A 23-view, six-plate ArUco pilot exists but is EVAL-ONLY and lacks independently checked masks and enough tare-corrected weights for a valid broad end-to-end metric. A fresh development/holdout dataset is still required to assess the current integration. WED DEV and the one-time WED LOCKED mass-head report have distinct scopes; the 997-embedding gallery has separate, non-independent leave-one-out evidence.
- All authors share the affiliation BMS College of Engineering, as supplied.
- Author email addresses are omitted until verified and may be added if required by the selected venue.
- A working title may be proposed during drafting and confirmed by the authors during review.
- The manuscript source will be editable and the compiled PDF will be delivered for review.
