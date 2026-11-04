# Paper Authoring and Validation Quickstart

This guide covers the manuscript workflow using the source and local toolchain in `paper/`.

## Prerequisites

- IEEEtran conference class and BibTeX style from the template files vendored in `paper/`.
- On Linux x86-64, run `paper/setup_texlive.sh` once to install local TeX Live 2026, `pdflatex`, BibTeX, `latexmk`, and the required packages. Other platforms can follow the [TeX Live quick-install guide](https://tug.org/texlive/quickinstall.html).
- Before submission, compare with the selected event's author kit and the current [IEEE conference template guidance](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/).
- Repository evidence listed in [research.md](research.md).
- Verified author contact details if required by the selected conference.

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
4. **Claim audit**: Ensure each author-generated metric states its metric, evaluation protocol, scope, and sample basis. Do not cite the NutriSense repository in the manuscript bibliography. The WED DEV and one-time LOCKED mass-head reports use ground-truth class/region inputs and are not end-to-end performance; the LOCKED report is descriptive only. The WED classifier crop score has DEV/gallery source overlap and must be labeled contaminated. The local gallery leave-one-out score is 78.03% over 997 embeddings and is not an independent test result. Include the pre-change 23-view ArUco pilot as EVAL-ONLY evidence; do not use it to validate recent fixes. Keep synthetic checks, pilot results, gallery results, and WED results distinct. Do not claim real-mask IoU/F1, validated nutrient accuracy, coach quality, or post-fix real-photo gains. The project lacks a fresh independently grouped, tare-corrected dataset with checked item masks, labels, and weights.
5. **Author metadata**: Confirm all four author names and BMS College of Engineering. Contact addresses are omitted rather than fabricated; add verified author emails if the selected event requires them.
6. **Reference audit**: Check each in-text citation has a complete bibliography entry and each cited source supports the associated claim. Verify every source and metadata field against a primary paper or official publication. See [citation-audit.md](citation-audit.md) for the source-by-source findings. National PM POSHAN covers Bal Vatika and classes I--VIII; Karnataka separately documents a state Mid-Day Meal extension to IX--X. NutriSense maps the IX--X band to the central upper-primary 700 kcal / 20 g reference as an application policy choice, not as a separately stated Karnataka grade-specific nutrition norm. The Thali paper's source PDF identifies it as nine pages; see the audit for the pagination caveat.
7. **Venue gate**: Once a target event is selected, compare the manuscript to that event's author kit, page limit, paper size, anonymization rules, and PDF submission checks; use IEEE PDF eXpress if the organizer requires it.

## Expected Outcome

Compilation succeeds, all citations resolve, the PDF contains no overfull or clipped content, the detailed diagram matches the current runtime, and project claims retain their split and validation context. The PDF remains a generic draft until a conference, its page limit, and required author contact details are confirmed.

## Current Validation Record

- `paper/main.tex` compiles with the vendored IEEEtran conference class and bibliography into a five-page US Letter review PDF.
- The final five-page build has been rendered and visually inspected. The flow diagram shows accepted multi-item scoring, estimate-only fallback, hard failure, out-of-scope, and the advisory chat path. The result table and all references remain within the page boundaries; the final reference page has a balanced two-column split.
- The author block lists the four supplied names and shared affiliation without inventing email addresses.
- The manuscript reports the WED DEV/LOCKED mass-head results, contaminated classifier DEV score, gallery leave-one-out score, and pre-change EVAL-ONLY ArUco outcomes with their separate scopes. It does not claim a real-mask F1 or validated nutrient accuracy.
- The citation audit remains in [citation-audit.md](citation-audit.md). National PM POSHAN coverage and the separate Karnataka IX-X extension are described distinctly; the NutriSense repository is not cited in the bibliography.
- The local build produced no unresolved citations or overfull-box warnings. Remaining submission gates: select the target IEEE conference, check its page limit and event-specific author kit, confirm any required verified author contacts, and perform venue-specific PDF validation.
