# Paper Authoring and Validation Quickstart

This guide covers the manuscript workflow using the source and local toolchain in `paper/`.

## Prerequisites

- IEEEtran conference class and BibTeX style from the template files vendored in `paper/`.
- On Linux x86-64, run `paper/setup_texlive.sh` once to install local TeX Live 2026, `pdflatex`, BibTeX, `latexmk`, and the required packages. Other platforms can follow the [TeX Live quick-install guide](https://tug.org/texlive/quickinstall.html).
- Before submission, compare with the selected event's author kit and the current [IEEE conference template guidance](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/).
- Repository evidence listed in [research.md](research.md).
- Confirmation of placeholder email addresses before any submission-ready export.

## Build

From the repository root, install TeX Live once on Linux x86-64 and build the paper:

```bash
cd paper
./setup_texlive.sh
./build.sh
```

`build.sh` uses the TeX Live installation under `paper/.texlive/` and writes `main.pdf`. For Overleaf, upload `main.tex`, `references.bib`, `IEEEtran.cls`, `IEEEtran.bst`, and `figures/pipeline.pdf`, preserving the `figures/` folder; select `main.tex` and the default pdfLaTeX compiler. Overleaf does not need the local setup or build scripts.

## Validation Scenarios

1. **Template and layout**: Confirm the source uses IEEE conference mode, the official bibliography style, and the page size selected by the official template or the chosen conference. Confirm no template instructions or sample content remain.
2. **Abstract and index terms**: Confirm the abstract is one self-contained paragraph of no more than 250 words, contains no citations or equations, and is followed by 3–5 index terms. Follow stricter venue guidance if applicable.
3. **Figures and tables**: Open every PDF page at normal size; check that the diagram's branches remain separated, labels do not collide, and captions, equations, tables, author details, and references are readable and not clipped.
4. **Claim audit**: Ensure each author-generated metric states its metric, evaluation protocol, scope, and sample basis. Do not cite the NutriSense repository in the manuscript bibliography. Ensure WED DEV is labeled external fallback mass-head evidence using ground-truth ROI/class inputs, not end-to-end pipeline performance. The project-specific real-meal capture dataset with portion-mass annotations remains uncollected; leave its reserved table marked pending until data collection and evaluation are complete. The 46-image classifier gallery is separate leave-one-out evidence, not that mass-estimation dataset. It currently contains two dish classes; SigLIP 2 scores available menu classes but the runtime returns one dish label per capture. No current DINOv2-S LOCKED/test result is claimed. Keep synthetic validation and gallery leave-one-out results labeled as such, and do not claim a settled SAM IoU point estimate until its 0.97/0.98 conflict is resolved.
5. **Author metadata**: Confirm all four author names and BMS College of Engineering. Verify the first author's supplied email and replace the other three `example.com` placeholders.
6. **Reference audit**: Check each in-text citation has a complete bibliography entry and each cited source supports the associated claim. Verify every source and metadata field against a primary paper or official publication. See [citation-audit.md](citation-audit.md) for the source-by-source findings. National PM POSHAN covers Bal Vatika and classes I--VIII; Karnataka separately documents a state Mid-Day Meal extension to IX--X, which is the basis for the project's third band. The Thali proceedings article is paginated 1--9 (nine pages).
7. **Venue gate**: Once a target event is selected, compare the manuscript to that event's author kit, page limit, paper size, anonymization rules, and PDF submission checks; use IEEE PDF eXpress if the organizer requires it.

## Expected Outcome

Compilation succeeds, all citations resolve, the PDF contains no overfull or clipped content, the detailed diagram matches the current runtime, project claims retain their split and validation context, and all placeholder author emails are explicitly identified for confirmation. The PDF remains a generic draft until a conference and its page limit are selected.

## Current Validation Record

- `paper/main.tex` compiles with the vendored IEEEtran conference class and bibliography into a five-page, US Letter review PDF.
- The full-width runtime diagram was visually inspected at normal page scale; the measured, no-marker mapped/head-available, no-marker unmapped, abstention, out-of-scope, verdict, and serialized-response paths are visible. The first-row connectors have wider gaps and heavier, clearly visible arrowheads; labels remain within their boxes.
- The near-full-width diagram appears on page 3, before Results; Results begins on page 4. The diagram is legible at normal page scale, and the last-page references are balanced across both columns.
- The four authors are displayed in two balanced columns in the supplied visible order, with individually paired names and contact details; the project-specific dataset-results table remains explicitly pending collection/evaluation.
- Citations resolve. All ten bibliography entries are cited, all in-text citations resolve, and the MoGe-2 entry matches the version named in the manuscript. The Thali entry uses proceedings pages 1--9 and DOI; PM POSHAN links directly to the official guideline PDF, records its issue date, and identifies national coverage through class VIII. Two Karnataka government sources support the separate IX--X state extension. The NutriSense repository is not cited; project metrics are identified as author-generated with their scopes and protocols. A clean build has no overfull-box or undefined-citation warnings; the full-height flowchart float produces expected underfull vertical-box warnings. The updated source and figure compiled in the existing Overleaf project as a five-page PDF. Full findings are in [citation-audit.md](citation-audit.md).
- The current WED DEV result is identified as external fallback, mass-head-only evaluation on ground-truth ROI/class inputs. No project-dataset, DINOv2-S LOCKED/test, or end-to-end result is claimed.
- The paper explicitly limits its policy category to the selected captured serving; it does not claim that one dish capture establishes compliance for a multi-dish meal.
- The 0.97/0.98 synthetic SAM IoU conflict remains documented in the repository; the manuscript omits a settled point estimate.
- Remaining submission gate: select the target IEEE conference, check its page limit and event-specific author kit, and replace the three visibly marked placeholder email addresses.
