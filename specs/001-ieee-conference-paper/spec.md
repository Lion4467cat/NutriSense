# Feature Specification: NutriSense IEEE Conference Paper

**Feature Branch**: `main` (per user request)

**Created**: 2026-10-26

**Status**: Draft

**Input**: User request: prepare a generic IEEE conference paper about NutriSense using IEEE's official conference template; authors are SS Gokula Swamy, Roshanth V, Somanath S.D, and Aryan Kumar, affiliated with BMS College of Engineering. The corresponding address is gokulaswamyss@gmail.com; other author emails are placeholders. Follow-up audit fixes require a detailed diagram based on current runtime behavior, a precise single-mask/single-dish scope statement, complete evaluation and policy details, and reconciled quantitative claims and bibliography metadata.

## User Scenarios & Testing

### User Story 1 - Review the project as a research manuscript (Priority: P1)

The project authors need a concise conference paper that explains NutriSense's motivation, method, evaluation, findings, and limitations in a form suitable for coauthor review.

**Why this priority**: A defensible, readable account of the project is the central deliverable.

**Independent Test**: A reviewer unfamiliar with the repository can read the draft and explain the system's input, outputs, method, evidence, and limitations without relying on undocumented details.

**Acceptance Scenarios**:

1. **Given** the current repository and its reports, **When** an author reviews the manuscript, **Then** the described pipeline and results match the current implementation and cited evidence.
2. **Given** the paper's evaluation section, **When** a reviewer traces each metric, **Then** the model, split, sample count, uncertainty interval, and source report are identifiable.
3. **Given** the system diagram and methods, **When** a reviewer compares them with the current repository, **Then** the diagram includes the major success, abstention, out-of-scope, failure, measured-scale, and no-marker paths without claiming multi-dish processing.
4. **Given** conflicting repository summaries for a component metric, **When** the paper reports evaluation evidence, **Then** it reports only a reconciled, traceable value or omits that quantitative claim.

### User Story 2 - Prepare the manuscript in IEEE conference format (Priority: P1)

The authors need the paper composed with the official IEEE conference template and checked against its formatting guidance.

**Why this priority**: The requested output is an IEEE conference paper, and template compliance affects whether it can be submitted.

**Independent Test**: The manuscript source compiles into a readable two-column conference-format PDF using the official IEEE template, with template instructions removed and no overflowing content.

**Acceptance Scenarios**:

1. **Given** the IEEE conference manuscript source, **When** it is compiled with the official template, **Then** the result has the IEEE conference layout and contains no example guidance text.
2. **Given** figures, tables, equations, and references in the paper, **When** the compiled PDF is reviewed, **Then** they remain legible, numbered, cited, and within page boundaries.

### User Story 3 - Confirm authorship and submission metadata (Priority: P2)

The authors need their names and institutional affiliation included, with the supplied email and clearly marked temporary addresses for the remaining coauthors.

**Why this priority**: The manuscript needs an accurate author block, and placeholder addresses must not be mistaken for verified contact details.

**Independent Test**: The author block contains all four names and BMS College of Engineering; the supplied email is exact and all other email placeholders are visibly flagged for confirmation before submission.

**Acceptance Scenarios**:

1. **Given** the author details supplied by the project owner, **When** the manuscript metadata is checked, **Then** the author names and affiliation match those details.
2. **Given** the temporary email entries, **When** a submission-ready review is performed, **Then** no placeholder email is presented as verified contact information.

### Edge Cases

- The target conference may impose a different page size, page limit, anonymization rule, or bibliography requirement; the venue's current instructions must override the generic IEEE defaults when a venue is selected.
- Historical project reports may describe an earlier model. The manuscript must label those results as historical and must not present old ResNet-50 test results as current DINOv2-S performance.
- The current learned-weight result is a DEV-set result; no current DINOv2-S LOCKED test result is established in the reviewed source material.
- Some project parameters remain assumed or await field validation; these must be reported as limitations rather than established findings.
- The field marker is a 60 mm ArUco printed on A4. The legacy 100 mm square in the synthetic A6 fixture is not a field measurement and must not appear as the project's capture protocol.

## Requirements

### Functional Requirements

- **FR-001**: The manuscript MUST explain the NutriSense problem, intended setting, and expected contribution in terms understandable to a computer-vision and applied-health audience.
- **FR-002**: The manuscript MUST describe the end-to-end workflow from a meal photograph through dish recognition, portion estimation, nutrient uncertainty, and PM POSHAN compliance assessment.
- **FR-003**: The manuscript MUST distinguish measured scale from the 60 mm ArUco marker on A4 from prior-tier estimates used when no marker is detected.
- **FR-004**: The manuscript MUST describe the actual model components and their roles without implying that a model or data collection step was used when it was not.
- **FR-005**: Every quantitative result MUST identify its metric, evaluation split, sample basis, model/checkpoint where relevant, and supporting repository report or primary reference.
- **FR-006**: The manuscript MUST report the current DINOv2-S WED DEV MAE and its confidence interval from the current evaluation ledger, and MUST NOT infer DINOv2-S performance on the LOCKED test split.
- **FR-007**: The manuscript MUST identify limitations, including the distinction between DEV and test results, assumed parameters, coverage effects, and pending real-world validation.
- **FR-008**: The manuscript MUST use the official IEEE conference template in conference mode and remove template guidance text from the paper.
- **FR-009**: The manuscript MUST include the authors SS Gokula Swamy, Roshanth V, Somanath S.D, and Aryan Kumar, with BMS College of Engineering as the supplied affiliation.
- **FR-010**: The author block MUST use `gokulaswamyss@gmail.com` for SS Gokula Swamy and visibly label the other supplied dummy email addresses as placeholders requiring author confirmation.
- **FR-011**: The manuscript MUST cite primary sources for methods, datasets, standards, and prior-work comparisons, and MUST include complete, traceable references.
- **FR-012**: The source and compiled PDF MUST be reviewed for formatting, figure/table readability, citation completeness, and factual consistency before delivery.
- **FR-013**: The pipeline figure MUST be a legible, full-width, detailed representation of current runtime paths, including input/stage-failure abstention, unrecognized-dish abstention, out-of-scope dishes, measured geometry, mapped no-marker learned mass, learned-head unavailability, unmapped-dish size-prior geometry, compliance verdicts, and the serialized response.
- **FR-014**: The paper MUST state that the current image pipeline segments one food mask and classifies one dish per capture; it MUST NOT imply independent multi-region or multi-dish inference.
- **FR-015**: The methods MUST specify mandatory nutrients, student-band minima, probability thresholds, coverage thresholds, cooked-plate energy basis, and the repository's flagged 9–10 band inheritance.
- **FR-016**: The evaluation protocol MUST state that WED DEV mass evaluation uses ground-truth class/ROI inputs and does not exercise upstream segmentation or classification, and MUST scope the data split and bootstrap method.
- **FR-017**: The manuscript MUST omit or clearly qualify quantitative claims whose source evidence conflicts; specifically, no single synthetic segmentation IoU may be presented as settled until the repository evidence is reconciled.
- **FR-018**: Bibliographic records MUST use final publication metadata when available, cite the exact official PM POSHAN guideline and date, and distinguish a paper's page count from proceedings pagination.
- **FR-019**: The manuscript MUST distinguish existing WED development evidence from the project's own dataset, explicitly state that project-dataset collection and evaluation are pending, and reserve a clearly labeled results area for its eventual sample counts, mass errors, uncertainty coverage, and end-to-end measures without inventing values.
- **FR-020**: The full-width runtime figure MUST use a readable visual hierarchy and separated paths with sufficient whitespace; labels and connectors MUST remain legible at the compiled IEEE page size, with no overlapping or confusing branch crossings.
- **FR-021**: The four authors MUST appear in a balanced, individually identified IEEE author layout with sufficient separation between names and contact details; long placeholder addresses MUST not crowd adjacent authors.
- **FR-022**: The pipeline figure MUST appear in the main body before the Results section, near its System Overview discussion, rather than after the references; retain compliant IEEE float placement.

### Key Entities

- **Manuscript**: Title, abstract, sections, figures, tables, equations, references, and final compiled paper.
- **Author**: Name, affiliation, email, and whether the email is verified or a placeholder.
- **Project method**: Image inputs, stages, model roles, measured and prior scale paths, uncertainty, and compliance output.
- **Evaluation result**: Metric, model/checkpoint, data split, sample basis, confidence interval, protocol, and source.
- **Reference**: Primary publication or official guidance cited to support a method, dataset, standard, or formatting decision.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All four authors and their supplied institution appear correctly in the manuscript metadata; only the first supplied email is treated as verified.
- **SC-002**: Every numerical project claim in the paper can be traced to a project report, evaluation output, or cited primary source.
- **SC-003**: The evaluation section distinguishes the current DEV result from historical and LOCKED test results, with zero unsupported DINOv2-S test-set claims.
- **SC-004**: The manuscript compiles with the official IEEE conference template and has no unremoved template guidance, clipped text, or unreadable figures/tables.
- **SC-005**: A coauthor can identify the paper's contribution, method, strongest evidence, and principal limitations from the manuscript without consulting the source code.
- **SC-006**: The diagram's branches agree with `engine/pipeline.py`, and the narrative contains no claim that the current runtime independently processes multiple dish regions.
- **SC-007**: The policy thresholds and WED evaluation boundary are stated with the exact values and input scope used by the repository.
- **SC-008**: All references identify traceable publication or official-document metadata; no conflicting synthetic IoU value is presented as settled evidence.
- **SC-009**: The manuscript reports no project-collected dataset statistics before collection; its reserved project-results area labels each such value as pending and keeps WED DEV values clearly identified as external development evidence.
- **SC-010**: At IEEE two-column page size, the flowchart's branch labels and nodes can be read without overlap or visually cramped convergence.
- **SC-011**: The four author names and their contact lines are visually separated and balanced in the compiled title area, with no email wrapping into adjacent author blocks.
- **SC-012**: The flowchart appears before the Results section and before the references in the compiled paper.

## Assumptions

- The target is a generic IEEE-sponsored conference paper; no specific conference, page limit, or submission portal has been selected.
- The official IEEE conference template is the required baseline. Once a venue is selected, its current instructions may further constrain the manuscript.
- The paper will summarize existing project evidence; it will not report new experiments unless the authors later authorize and conduct them.
- The project-specific capture/annotation dataset has not yet been collected. WED DEV is the only current dataset-based fallback result; a distinct pending-results slot will be retained for the project's own dataset and completed only after collection and evaluation.
- All authors share the affiliation BMS College of Engineering, as supplied.
- Temporary emails for Roshanth V, Somanath S.D, and Aryan Kumar will use clearly marked `example.com` placeholders and must be replaced before submission.
- A working title may be proposed during drafting and confirmed by the authors during review.
- The manuscript source will be editable and the compiled PDF will be delivered for review.
