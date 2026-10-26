# NutriSense IEEE conference paper

This directory is the editable manuscript workspace. `main.tex` is based on
IEEE's `bare_conf.tex` starter using the official IEEEtran conference class; it
is not a completed or submission-ready paper. The planning brief and claim
constraints are in [`../specs/001-ieee-conference-paper/`](../specs/001-ieee-conference-paper/).

## Template and venue

The source selects `IEEEtran` in `conference` mode and uses the matching
`IEEEtran` bibliography style. The IEEEtran package and its original
`bare_conf.tex` starter have been downloaded from CTAN and are included here:
`IEEEtran.cls`, `IEEEtran.bst`, and `template/`. CTAN describes IEEEtran as the
class and bibliography style for officially correct IEEE journal and
conference output. The IEEE-linked ZIP endpoint returned an access challenge
in this environment, so the CTAN distribution is the local source. IEEE's
conference author center points authors to the official templates in Word or
LaTeX:

- <https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/>
- <https://www.ieee.org/conferences/publishing/templates.html>

No specific conference has been selected yet. Before submission, obtain the
current author kit from IEEE's template selector and the chosen event, then
apply any event-specific page limit, page size, anonymization, and PDF checks.
The downloaded template version and any event-specific changes should be
recorded in `IEEE_TEMPLATE_SOURCE.md`.

The paper's pipeline figure uses separated stages and portion-source lanes at
full conference width, including abstention and out-of-scope paths; the IEEE
double-column float appears in the main body before Results and References. The four
authors appear in two balanced columns, each with an individually paired
affiliation and contact line. It documents one selected food mask and one dish
classification per capture. The only current dataset-based result is the WED
DEV mass-head fallback using ground-truth ROI/class inputs; the project-specific
capture dataset has not yet been collected. A pending-results subsection and
table reserve fields for its future sample counts, mass errors, uncertainty
coverage, and end-to-end measures without inventing values.
The repository's synthetic SAM IoU point estimate is unresolved (0.97 versus
0.98 in historical notes), so the paper reports the test's asserted floor and
does not claim either point value.

The source-by-source reference review, citation-key reconciliation, and claim
scope notes are recorded in
[`../specs/001-ieee-conference-paper/citation-audit.md`](../specs/001-ieee-conference-paper/citation-audit.md).

## Compile

Run the setup script once on Linux x86-64 to install a local TeX Live 2026
compiler and paper dependencies, then compile from this directory:

```sh
./setup_texlive.sh
PATH="$PWD/.texlive/2026/bin/x86_64-linux:$PATH" latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The installer follows the TeX Users Group's local installation procedure and
uses the minimal scheme plus the recommended LaTeX and font collections. It
does not need administrator access. TeX Live is installed in `.texlive/` and
is ignored by Git.

The IEEEtran class and BibTeX style are vendored here so the manuscript uses
the tracked template files. TeX Live, its package cache, and generated files
are kept out of Git. The PDF is a generated review artifact and is ignored
unless the authors want to version a review copy.

## Drafting rules

- Treat the title in `main.tex` as provisional.
- Replace each TODO only after checking the supporting source in the repository.
- The 60 mm ArUco ID 7 marker printed on A4 is the field data-collection asset.
- Describe national PM POSHAN as covering Bal Vatika through class VIII. The configured 9--10 band represents Karnataka's separately documented state Mid-Day Meal extension, not national PM POSHAN eligibility; see the source-by-source audit.
- Scope the DINOv2-S value to WED DEV; do not claim DINOv2-S LOCKED/test results.
- Label synthetic and gallery leave-one-out results by their actual validation
  setting; do not present them as independent real-world test results.
- Keep each external citation attached only to the claim its source supports;
  use the citation audit when adding or changing references.
- Placeholder coauthor emails are explicitly marked in the author block and must be replaced
  before submission.
- Do not include WED images or other restricted dataset material without
  confirming reuse rights.
