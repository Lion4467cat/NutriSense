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

The current pipeline figure shows multi-item region detection, overlap
partitioning, estimate-only fallbacks, hard failures, and the optional meal
coach. The manuscript distinguishes the WED DEV and one-time LOCKED mass-head
reports, the contaminated WED classifier crop score, the local gallery
leave-one-out diagnostic, and the pre-change 23-view ArUco pilot. The pilot is
EVAL-ONLY; recent fixes are explicitly unvalidated on it. Conflicting SAM
synthetic IoU summaries are omitted, and the manuscript makes no real-mask
IoU/F1, end-to-end accuracy, or nutrient-error claim. The pilot is not a
sufficient independently annotated real-meal dataset for those metrics.

The source-by-source reference review, citation-key reconciliation, and claim
scope notes are recorded in
[`../specs/001-ieee-conference-paper/citation-audit.md`](../specs/001-ieee-conference-paper/citation-audit.md).

## Compile

Run the setup script once on Linux x86-64 to install a local TeX Live 2026
compiler and paper dependencies, then build from any directory:

```sh
cd paper
./setup_texlive.sh
./build.sh
```

`build.sh` selects the paper-local TeX Live tools, runs `latexmk`, and writes
`main.pdf` beside the source. For Overleaf, create a project and upload
`main.tex`, `references.bib`, `IEEEtran.cls`, `IEEEtran.bst`, and
`figures/pipeline.pdf`, preserving the `figures/` folder. Set `main.tex` as the
main document. Overleaf supplies its own LaTeX installation; `.texlive/`, the
local build scripts, and generated auxiliary files are not needed there.

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
- Treat the school policy category as applying to the detected and aggregated meal regions. The estimate-only fallback has no school-compliance verdict, and the current multi-item regions have not been validated on an independent real-photo set.
- Present project-specific evaluation metrics as author-generated results, state each metric's split, sample basis, and synthetic/gallery/WED scope, and do not cite the NutriSense repository in the bibliography.
- Report the one-time DINOv2-S WED LOCKED result only as descriptive evidence; it is closed to tuning and its 82.77% nominal 90% interval coverage is below target.
- Label synthetic and gallery leave-one-out results by their actual validation
  setting; do not present them as independent real-world test results.
- Keep each external citation attached only to the claim its source supports;
  use the citation audit when adding or changing references.
- Author email addresses have been omitted rather than invented; add verified contact details if required by the selected conference.
- Do not include WED images or other restricted dataset material without
  confirming reuse rights.
