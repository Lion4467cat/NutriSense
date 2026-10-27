# Research: NutriSense IEEE Conference Paper

Date: 2026-10-26

## IEEE template and publication guidance

**Decision**: Use the current IEEE Author Center conference LaTeX template in conference mode. Record its source and version/date in the manuscript repository, preserve upstream class/style files, and remove all example instructions from the paper. Use generic IEEE conference defaults until a target event is selected; that event's author kit and submission rules override generic choices.

**Rationale**: IEEE's [Conference Author Center](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/) directs authors to IEEE conference templates in Word or LaTeX and links to its template selector. IEEE's [conference paper structure guidance](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/) gives abstract and paper-organization advice. IEEE states that template guidance text must be removed before submission in its [conference publishing information](https://events.ieee.org/planning-basics/ieee-conference-publications/publishing-information-for-ieee-conference-authors/). A specific conference may impose additional page size, length, anonymity, and PDF checks, so no venue-specific rule can be assumed.

**Alternatives considered**: IEEE Word template; a third-party IEEE-like class; a conference-specific kit. LaTeX with IEEE's own class is chosen for a reproducible source, bibliography, equations, and figures. Word remains an acceptable alternative if the authors prefer it. A conference-specific template is deferred until the event is known.

## Paper structure and source discipline

**Decision**: Organize around motivation, prior work, system method, evaluation protocol, results, limitations, and conclusion. Trace every numerical claim to a repository report or primary source. Treat current DEV, TRAIN, historical test, and synthetic/rendered results as distinct evidence categories.

**Rationale**: The project has a detailed experiment ledger and fixed WED split protocol. The current DINOv2-S result is a DEV carve and its comparison is paired on DEV plates. The final report's ResNet-50 test score is historical and was read once; it cannot support a claim about the DINOv2-S checkpoint.

**Alternatives considered**: Re-run the LOCKED split for the paper, or use the older test score as if it described the current model. Neither is acceptable for this planning pass: the repo's policy protects the locked set, no DINOv2-S locked result is documented, and the paper can be planned using the current DEV evidence with an explicit limitation.

### Repository evidence map

| Claim or result | Evidence to use | Scope/caveat |
|---|---|---|
| Current learned-weight DEV MAE 15.034 g, 95% CI [12.227, 18.889] | `docs/ledger/001-current-state.md` | WED DEV carve: 108 views, 21 plates, 1,218 samples; do not label as test performance |
| Paired DEV change 20.298 → 15.034 g; Δ −5.264 g, 95% CI [−6.232, −4.227] | `docs/ledger/002-dinov2-encoder.md` | Paired evaluation on same DEV plates; not a comparison against a test-set score |
| DEV coverage_90 0.8522 [0.792, 0.899] | `docs/ledger/001-current-state.md`, `docs/eval_protocol.md` | Coverage uses per-class residual sigma; describe its evaluation definition |
| SAM2.1 IoU 0.98 | README and project model notes | Synthetic validation only |
| SigLIP2 gallery 46/46 | `data/gallery.npz` and evaluation records | Leave-one-out over the current 46-image gallery (two dish classes), not independent test accuracy; runtime returns one predicted dish label per capture |
| MoGe-2 calibrated depth error about 1.1% | README and project diagnostics | Rendered/synthetic card-calibration result; raw out-of-domain monocular scale is not reliable without calibration |
| Geometry volume error (+6.6% plate, +5.6% bowl) | `docs/final-report.md` | Synthetic ground-truth renderer, not a real-meal field study |
| Project metric provenance | `docs/ledger/001-current-state.md`, `docs/ledger/002-dinov2-encoder.md`, `docs/final-report.md`, `docs/diagnostic_report.md` | Cite these project artifacts for numerical claims, preserving each artifact's validation scope |
| National PM POSHAN and Karnataka IX–X policy bands | `data/standards.yaml`, official PM POSHAN guidelines, Karnataka FPI Research Report No. 4/2021–22, and Karnataka Legislative Council administrative report | Distinguish central Bal Vatika–VIII coverage from Karnataka's IX–X state extension; explain that the project maps the state extension to the same upper-primary 700 kcal / 20 g threshold |

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
| Karnataka state extension | [Fiscal Policy Institute, Government of Karnataka, Research Report No. 4/2021–22](https://fpibengaluru.karnataka.gov.in/storage/pdf-files/Technical%20Reports/FinalReport_PETS_08092022.pdf) and [Karnataka Legislative Council administrative report](https://kla.kar.nic.in/council/house/Paperlaid/149/22.pdf) | State-funded IX–X extension; the administrative report records the extension order and upper-primary-equivalent nutrition content |

## Field scale marker validation

**Decision**: Retain the supplied original as `docs/assets/reference_marker_A4_60mm.pdf`, and use it in field-protocol documentation instead of the A6 reference-card image. Keep the A6 renderer generator only as a clearly labeled synthetic fixture.

**Rationale**: The supplied PDF is one A4 page (`pdfinfo`: 595 × 841 pt). Rendering at 300 dpi and using the repository's configured OpenCV `DICT_4X4_50` detector identifies marker ID 7; all four marker edges render at 708 px, approximately 59.944 mm at 300 dpi. This agrees with `data/anchor_config.json`'s 60.0 mm marker and the production detection path. The copied repository file has the same SHA-256 as the supplied PDF (`aa2c390b15d2ea5f544a2d99cdf3addab35cc865a8dea00b2e34868cd0717780`). The PDF title and creator metadata are consistent with the user's description but do not independently establish the generating website; provenance is attributed to the user.

**Alternatives considered**: Keep the A6 card as the field asset; regenerate a similar marker from repository code; use the 100 mm black square. These are rejected for field instructions because the user confirmed that data collection used the supplied 60 mm A4 marker, and the detector computes scale from the ArUco marker, not the legacy A6 square.

## Data rights and authorship

**Decision**: Cite the WED paper and dataset, but do not include WED photographs or masks in manuscript figures unless their reuse permission is confirmed. Use author metadata exactly as supplied and mark three emails as unverified placeholders.

**Rationale**: `docs/licenses.md` records that WED dataset archive terms are unconfirmed and the raw images are local/git-ignored. The user supplied four names, one known address, and requested dummy emails for the others.

**Alternatives considered**: Copy WED images into the paper directory, or use example.com email addresses without a marker. Both risk presenting restricted material or temporary contact details as final. Use author-created diagrams and project-derived aggregate results; visibly label the three addresses as placeholders pending confirmation.
