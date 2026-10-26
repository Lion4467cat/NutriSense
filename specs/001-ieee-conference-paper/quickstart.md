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
3. **Figures and tables**: Open every PDF page at normal size; check that figures, captions, equations, table text, author details, and references are readable and not clipped.
4. **Claim audit**: Trace every metric to a ledger, evaluation protocol, primary paper, or official standard. Ensure the current DINOv2-S number is a WED DEV result and no current DINOv2-S LOCKED/test result is claimed. Keep synthetic validation and gallery leave-one-out results labeled as such.
5. **Author metadata**: Confirm all four author names and BMS College of Engineering. Verify the first author's supplied email and replace the other three `example.com` placeholders.
6. **Reference audit**: Check each in-text citation has a complete bibliography entry and each cited source supports the associated claim. Confirm the DINOv2 paper identifier is arXiv:2304.07193.
7. **Venue gate**: Once a target event is selected, compare the manuscript to that event's author kit, page limit, paper size, anonymization rules, and PDF submission checks; use IEEE PDF eXpress if the organizer requires it.

## Expected Outcome

Compilation succeeds, all citations resolve, the PDF contains no overfull or clipped content, project claims retain their split and validation context, and all placeholder author emails are explicitly identified for confirmation.
