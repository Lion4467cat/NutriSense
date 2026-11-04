# Research: NutriSense IEEE Conference Paper

Date: 2026-10-26

## IEEE template and publication guidance

**Decision**: Use the current IEEE Author Center conference LaTeX template in conference mode. Record its source and version/date in the manuscript repository, preserve upstream class/style files, and remove all example instructions from the paper. Use generic IEEE conference defaults until a target event is selected; that event's author kit and submission rules override generic choices.

**Rationale**: IEEE's [Conference Author Center](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/) directs authors to IEEE conference templates in Word or LaTeX and links to its template selector. IEEE's [conference paper structure guidance](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/) gives abstract and paper-organization advice. IEEE states that template guidance text must be removed before submission in its [conference publishing information](https://events.ieee.org/planning-basics/ieee-conference-publications/publishing-information-for-ieee-conference-authors/). A specific conference may impose additional page size, length, anonymity, and PDF checks, so no venue-specific rule can be assumed.

**Alternatives considered**: IEEE Word template; a third-party IEEE-like class; a conference-specific kit. LaTeX with IEEE's own class is chosen for a reproducible source, bibliography, equations, and figures. Word remains an acceptable alternative if the authors prefer it. A conference-specific template is deferred until the event is known.

## Paper structure and source discipline

**Decision**: Organize around motivation, prior work, system method, evaluation protocol, results, limitations, and conclusion. Trace every numerical claim to a repository report or primary source. Treat current DEV, TRAIN, historical test, and synthetic/rendered results as distinct evidence categories.

**Rationale**: The project has a detailed experiment ledger and fixed WED split protocol. The DINOv2-S mass head has a DEV carve and one-time LOCKED report; both must retain their split and scope. The 23-view ArUco pilot is EVAL-ONLY and predates the current overlap and estimate-only fallbacks.

**Alternatives considered**: Re-run WED LOCKED or the 23-view ArUco pilot to validate recent fixes. Neither is acceptable: those results are consumed or explicitly EVAL-ONLY. The paper reports their existing results as historical evidence and states that new post-fix validation is pending.

### Repository evidence map

| Claim or result | Evidence to use | Scope/caveat |
|---|---|---|
| Current learned-weight DEV MAE 15.034 g, 95% CI [12.227, 18.889] | `docs/ledger/001-current-state.md` | WED DEV carve: 108 views, 21 plates, 1,218 samples; do not label as test performance |
| Paired DEV change 20.298 → 15.034 g; Δ −5.264 g, 95% CI [−6.232, −4.227] | `docs/ledger/002-dinov2-encoder.md` | Paired evaluation on same DEV plates; not a comparison against a test-set score |
| DEV coverage_90 0.8522 [0.792, 0.899] | `docs/ledger/001-current-state.md`, `docs/eval_protocol.md` | Coverage uses per-class residual sigma; describe its evaluation definition |
| SAM 2.1 segmentation | Runtime configuration and project model notes | No real-mask IoU, Dice, precision, recall, or F1 is established; conflicting synthetic IoU records are omitted |
| SigLIP2 gallery leave-one-out | `data/gallery.npz` and `docs/ledger/003-serve-all-41-classes.md` | 78.03% over 997 embeddings; internal diagnostic, not independent accuracy |
| SigLIP2 41-way WED crop DEV | `data/reports/classifier_41way_dev.json` and `docs/model-metrics.md` | 81.03% top-1, but 41 of 108 DEV images overlap gallery sources; not end-to-end and likely optimistic |
| ArUco real-plate pilot | `AUDIT.md` and `docs/model-metrics.md` | 23 images across six plates; 20 cannot verify, 2 out of scope, 1 borderline, one emitted grams, 0/23 exact labels; EVAL-ONLY and pre-current-fixes |
| Multi-item overlap and estimate-only fixes | `engine/pipeline.py`, focused tests, and `AUDIT.md` | 22 synthetic focused tests pass; no real-photo validation or accuracy improvement is claimed |
| MoGe-2 calibrated depth error about 1.1% | README and project diagnostics | Rendered/synthetic card-calibration result; raw out-of-domain monocular scale is not reliable without calibration |
| Geometry volume error (+6.6% plate, +5.6% bowl) | `docs/final-report.md` | Synthetic ground-truth renderer, not a real-meal field study |
| Project metric provenance | `docs/ledger/001-current-state.md`, `docs/ledger/002-dinov2-encoder.md`, `docs/final-report.md`, `docs/diagnostic_report.md` | Cite these project artifacts for numerical claims, preserving each artifact's validation scope |
| National PM POSHAN and Karnataka IX–X policy bands | `data/standards.yaml`, official PM POSHAN guidelines, Karnataka FPI Research Report No. 4/2021–22, Karnataka Legislative Council Shivamogga and Ballari administrative reports | Distinguish central Bal Vatika–VIII coverage from Karnataka's IX–X state extension; NutriSense maps IX–X to 700 kcal / 20 g as a product policy because a statewide IX–X kcal/protein norm was not established by the reviewed sources. Ballari's report lists a district-specific ingredient allocation but gives no IX–X kcal/protein norm. |

## Primary sources for related work

Use primary papers and official project/government sources in the bibliography. Confirm final bibliographic metadata (author order, venue, pages, DOI) from each source when writing `references.bib`.

| Topic | Primary source | Use in paper |
|---|---|---|
| ArUco markers | Garrido-Jurado et al., *Automatic generation and detection of highly reliable fiducial markers under occlusion*, Pattern Recognition (2014), DOI [10.1016/j.patcog.2014.01.005](https://doi.org/10.1016/j.patcog.2014.01.005) | Marker detection background; NutriSense's field asset is ID 7, 60 mm |
| Promptable segmentation | Ravi et al., *SAM 2: Segment Anything in Images and Videos*, [arXiv:2408.00714](https://arxiv.org/abs/2408.00714) | Segmentation component background |
| Image-text and dense representations | Tschannen et al., *SigLIP 2*, [arXiv:2502.14786](https://arxiv.org/abs/2502.14786) | Gallery-first dish classification background |
| Monocular geometry | Wang et al., *MoGe-2*, [arXiv:2507.02546](https://arxiv.org/abs/2507.02546) and [Microsoft's official repository](https://github.com/microsoft/MoGe) | Depth source and limits |
| Frozen visual features | Oquab et al., *DINOv2*, [arXiv:2304.07193](https://arxiv.org/abs/2304.07193) | Current weight-head encoder; this is the correct identifier (the ledger's former `2304.15003` link was a typo and has been fixed) |
| Indian thali / WED | Arora et al., *What is there in an Indian Thali?*, [paper PDF](https://adityaarun1.github.io/assets/files/icvgip25/thali/Thali_ICVGIP2025_main.pdf) and [project page](https://cvit.iiit.ac.in/research/projects/cvit-projects/indian_thali) | Dataset origin and published comparison; the paper's 14.51 g baseline is not NutriSense's current model result |
| National nutrition policy | Government of India, [PM POSHAN Guidelines (2023)](https://pmposhan.education.gov.in/Files/Guidelines/2023/Guidelines%20on%20PM%20POSHAN%20SCHEME.pdf) and [scheme meal provision information](https://pmposhan.education.gov.in/Meal%20Provision.html) | Central coverage through class VIII and the central primary/upper-primary norms |
| Karnataka state extension | [Fiscal Policy Institute, Government of Karnataka, Research Report No. 4/2021–22](https://fpibengaluru.karnataka.gov.in/storage/pdf-files/Technical%20Reports/FinalReport_PETS_08092022.pdf), [Shivamogga administrative report](https://kla.kar.nic.in/council/house/Paperlaid/149/22.pdf), and [Ballari administrative report](https://kla.kar.nic.in/council/house/Paperlaid/146/71.pdf) | The reports establish a state extension to IX–X. Ballari's district report records that district's ingredient quantities for IX–X, but it does not establish a statewide IX–X kcal/protein minimum. |

## Field scale marker validation

**Decision**: Retain the supplied original as `docs/assets/reference_marker_A4_60mm.pdf`, and use it in field-protocol documentation instead of the A6 reference-card image. Keep the A6 renderer generator only as a clearly labeled synthetic fixture.

**Rationale**: The supplied PDF is one A4 page (`pdfinfo`: 595 × 841 pt). Rendering at 300 dpi and using the repository's configured OpenCV `DICT_4X4_50` detector identifies marker ID 7; all four marker edges render at 708 px, approximately 59.944 mm at 300 dpi. This agrees with `data/anchor_config.json`'s 60.0 mm marker and the production detection path. The copied repository file has the same SHA-256 as the supplied PDF (`aa2c390b15d2ea5f544a2d99cdf3addab35cc865a8dea00b2e34868cd0717780`). The PDF title and creator metadata are consistent with the user's description but do not independently establish the generating website; provenance is attributed to the user.

**Alternatives considered**: Keep the A6 card as the field asset; regenerate a similar marker from repository code; use the 100 mm black square. These are rejected for field instructions because the user confirmed that data collection used the supplied 60 mm A4 marker, and the detector computes scale from the ArUco marker, not the legacy A6 square.

## Data rights and authorship

**Decision**: Cite the WED paper and dataset, but do not include WED photographs or masks in manuscript figures unless their reuse permission is confirmed. Use the supplied author names and affiliation; omit unverified author email addresses.

**Rationale**: `docs/licenses.md` records that WED dataset archive terms are unconfirmed and the raw images are local/git-ignored. Contact details must not be fabricated or presented without author verification.

**Alternatives considered**: Copy WED images into the paper directory or add temporary email addresses. Both risk presenting restricted material or unverified metadata as final. Use author-created diagrams and project-derived aggregate results, and omit email addresses until verified.
