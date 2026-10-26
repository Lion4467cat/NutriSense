# NutriSense IEEE conference paper

This directory is the editable manuscript workspace. `main.tex` is a starter
scaffold using IEEE's conference class and author-block structure; it is not a
completed or submission-ready paper. The planning brief and claim constraints
are in [`../specs/001-ieee-conference-paper/`](../specs/001-ieee-conference-paper/).

## Template and venue

The source selects `IEEEtran` in `conference` mode and uses the matching
`IEEEtran` bibliography style. IEEE's conference author center directs authors
to its conference templates in Word or LaTeX:

- <https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/>
- <https://www.ieee.org/conferences/publishing/templates.html>

No specific conference has been selected yet. Before submission, obtain the
current author kit from IEEE's template selector and the chosen event, then
apply any event-specific page limit, page size, anonymization, and PDF checks.
The downloaded template version and any event-specific changes should be
recorded in `IEEE_TEMPLATE_SOURCE.md`.

## Compile

Install a LaTeX distribution that includes `IEEEtran`, BibTeX, and `latexmk`,
then run from this directory:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

The current workspace does not have `pdflatex`, `latexmk`, or `IEEEtran.cls`
installed, so a local PDF has not yet been built. The PDF is a generated review
artifact and should not be committed unless the authors want a versioned review
copy.

## Drafting rules

- Treat the title in `main.tex` as provisional.
- Replace each TODO only after checking the supporting source in the repository.
- The 60 mm ArUco ID 7 marker printed on A4 is the field data-collection asset.
- Scope the DINOv2-S value to WED DEV; do not claim DINOv2-S LOCKED/test results.
- Label synthetic and gallery leave-one-out results by their actual validation
  setting; do not present them as independent real-world test results.
- Placeholder coauthor emails are intentionally marked and must be replaced
  before submission.
- Do not include WED images or other restricted dataset material without
  confirming reuse rights.
