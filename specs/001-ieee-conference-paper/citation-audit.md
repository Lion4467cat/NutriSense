# Citation and Source Audit

**Audited**: 2026-10-27  
**Scope**: Every citation key in `paper/main.tex` and every record in `paper/references.bib`. Source metadata and cited claims were checked against the publisher, official project, preprint, or government source.

| Key | Source checked | What the source supports | Manuscript use and audit outcome |
|---|---|---|---|
| `garrido2014aruco` | Elsevier, *Pattern Recognition* 47(6), 2280–2292 (2014), DOI 10.1016/j.patcog.2014.01.005 | Configurable binary fiducial dictionaries, detection/error correction, and a separate occlusion method combining multiple markers with color segmentation. | The manuscript now distinguishes the paper's multi-marker occlusion approach from NutriSense's single ID 7 marker. The project-specific 60 mm side and A4 print are supported by project files, not by this paper. Metadata verified. |
| `ravi2025sam2` | Official ICLR 2025 proceedings entry, *SAM 2: Segment Anything in Images and Videos* | SAM 2 is a promptable visual segmentation foundation model for images and videos. | Used for the model-family description only. Exact author list, title, venue, year, and proceedings URL verified. |
| `meta2024sam2repo` | Official Meta FAIR GitHub repository, `facebookresearch/sam2` | Meta's official SAM 2 code and checkpoints; the repository announcement identifies SAM 2.1 as the improved checkpoint suite. | Added so the cited implementation version matches the SAM 2.1 checkpoint named in the manuscript. Repository name, organization, and URL verified. |
| `tschannen2025siglip2` | arXiv:2502.14786, *SigLIP 2: Multilingual Vision-Language Encoders with Improved Semantic Understanding, Localization, and Dense Features* | The model family and reported improvements in vision-language representation, localization, and dense prediction. | Listed as an arXiv preprint because no final proceedings/journal publication was identified in this audit. Metadata, author list, DOI, and arXiv URL verified. The project-specific gallery behavior is documented by the repository, not this paper. |
| `wang2025moge2` | arXiv:2507.02546, *MoGe-2: Accurate Monocular Geometry with Metric Scale and Sharp Details* | MoGe-2 estimates a metric-scale point map from a single image. | Corrected the prior bibliography error: the paper had cited MoGe (2024) even though the method section names MoGe-2. Updated authors, title, year, identifier, and URL. Marker calibration is a NutriSense runtime detail supported by project code/configuration. |
| `oquab2024dinov2` | TMLR 2024 publication page (OpenReview forum `a68SUt6zFt`); cross-checked against arXiv:2304.07193 | DINOv2's self-supervised visual representation learning and transfer-oriented features. | Final TMLR venue/year retained; changed the bibliography URL from a secondary index to the official OpenReview publication page. Manuscript claim is scoped to the learned representation, not a project performance claim. |
| `arun2025thali` | ACM proceedings DOI 10.1145/3774521.3774594; authors' paper PDF | The Thali paper's WED dataset and gram-level food-region mass annotations; its ACM citation states nine pages. | Corrected title capitalization and proceedings name and replaced the ambiguous `9 pages` note with published pagination 1–9. Authors, year, publisher, DOI, and page span verified. |
| `pmposhan2022guidelines` | Official Ministry of Education PM POSHAN guideline PDF, section 1.7, nutrition and food norms table | Primary norms of 450 kcal / 12 g protein and upper-primary norms of 700 kcal / 20 g protein per child per day. | Replaced the generic guideline index page with the exact official PDF URL. The paper's mapping of 1–5 and 6–8 to primary/upper-primary bands is explicit; the 9–10 extension remains labeled as the project's inference, not a guideline row. Date retained as 21 December 2022. |

## Citation-key reconciliation

All eight bibliography keys are cited in `paper/main.tex`; every in-text citation resolves to exactly one bibliography record. No unused records or missing keys remain. The only bibliography entry not for a research paper is the official Meta software/checkpoint repository, included to identify the actual SAM 2.1 implementation used.

## Claim limitations retained

- ArUco's cited occlusion result is a multi-marker/color-mask technique; it is not attributed to NutriSense's single-marker setup.
- The MoGe-2 paper supports the model's metric point-map capability; NutriSense marker calibration and its fallback behavior remain project-specific method descriptions.
- SigLIP 2 claims do not imply independent NutriSense recognition accuracy.
- The WED citation supports the dataset and annotations, not NutriSense's own uncollected field dataset or any project-specific dataset result.
- PM POSHAN explicitly defines primary and upper-primary norms; the 9–10 values are described as an implementation inference.
