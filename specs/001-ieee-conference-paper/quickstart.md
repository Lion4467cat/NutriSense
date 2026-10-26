# Paper Authoring and Validation Quickstart

This guide covers the manuscript workflow using the source and local toolchain in `paper/`.

## Prerequisites

- IEEEtran conference class and BibTeX style from the template files vendored in `paper/`.
- On Linux x86-64, run `paper/setup_texlive.sh` once to install local TeX Live 2026, `pdflatex`, BibTeX, `latexmk`, and the required packages. Other platforms can follow the [TeX Live quick-install guide](https://tug.org/texlive/quickinstall.html).
- Before submission, compare with the selected event's author kit and the current [IEEE conference template guidance](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/).
- Repository evidence listed in [research.md](research.md).
- Confirmation of placeholder email addresses before any submission-ready export.

## Build

From the manuscript directory:

```bash
PATH="$PWD/.texlive/2026/bin/x86_64-linux:$PATH" latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

If `latexmk` is unavailable, run the standard `pdflatex`, `bibtex`, `pdflatex`, `pdflatex` sequence for the manuscript's main file. Keep the output PDF alongside or in the configured output directory.

## Validation Scenarios

1. **Template and layout**: Confirm the source uses IEEE conference mode, the official bibliography style, and the page size selected by the official template or the chosen conference. Confirm no template instructions or sample content remain.
2. **Abstract and index terms**: Confirm the abstract is one self-contained paragraph of no more than 250 words, contains no citations or equations, and is followed by 3–5 index terms. Follow stricter venue guidance if applicable.
3. **Figures and tables**: Open every PDF page at normal size; check that the diagram's branches remain separated, labels do not collide, and captions, equations, tables, author details, and references are readable and not clipped.
4. **Claim audit**: Trace every metric to a ledger, evaluation protocol, primary paper, or official standard. Ensure WED DEV is labeled external fallback mass-head evidence using ground-truth ROI/class inputs, not end-to-end pipeline performance. The project-specific capture dataset remains uncollected; leave its reserved table marked pending until data collection and evaluation are complete. No current DINOv2-S LOCKED/test result is claimed. Keep synthetic validation and gallery leave-one-out results labeled as such, and do not claim a settled SAM IoU point estimate until its 0.97/0.98 conflict is resolved.
5. **Author metadata**: Confirm all four author names and BMS College of Engineering. Verify the first author's supplied email and replace the other three `example.com` placeholders.
6. **Reference audit**: Check each in-text citation has a complete bibliography entry and each cited source supports the associated claim. Cite SAM 2 at ICLR 2025 and DINOv2 at TMLR 2024; cite the official PM POSHAN guideline and identify its 21 December 2022 date. Record the Thali work as a 9-page publication rather than proceedings pages 1--9.
7. **Venue gate**: Once a target event is selected, compare the manuscript to that event's author kit, page limit, paper size, anonymization rules, and PDF submission checks; use IEEE PDF eXpress if the organizer requires it.

## Expected Outcome

Compilation succeeds, all citations resolve, the PDF contains no overfull or clipped content, the detailed diagram matches the current runtime, project claims retain their split and validation context, and all placeholder author emails are explicitly identified for confirmation. The PDF remains a generic draft until a conference and its page limit are selected.

## Current Validation Record

- `paper/main.tex` compiles with the vendored IEEEtran conference class and bibliography into a four-page, US Letter review PDF.
- The full-width runtime diagram was visually inspected at normal page scale; the measured, no-marker mapped/head-available, no-marker unmapped, abstention, out-of-scope, verdict, and serialized-response paths are visible.
- The IEEE double-column float now appears on page 3 of 4, before Results and References; it no longer sits at the end of the PDF.
- The four authors are displayed in two balanced columns with individually paired names and contact details; the project-specific dataset-results table remains explicitly pending collection/evaluation.
- Citations resolve. The Thali entry identifies a nine-page paper and DOI; the PM POSHAN entry points to the official Ministry guideline listing and records the document date.
- The current WED DEV result is identified as external fallback, mass-head-only evaluation on ground-truth ROI/class inputs. No project-dataset, DINOv2-S LOCKED/test, or end-to-end result is claimed.
- The 0.97/0.98 synthetic SAM IoU conflict remains documented in the repository; the manuscript omits a settled point estimate.
- Remaining submission gate: select the target IEEE conference, check its page limit and event-specific author kit, and replace the three visibly marked placeholder email addresses.
