# NutriSense licenses & attribution

Gate **M9**: before any release, confirm the two `unconfirmed` rows below.
Rule while unconfirmed: **cite, never redistribute** (no copying dataset files,
images, or database dumps into this repo or any artifact).

| Asset | License | Source | Status | Use in NutriSense |
|---|---|---|---|---|
| DA3METRIC-LARGE (metric head) | Apache-2.0 | HF model card | confirmed | **not used** (rejected: numpy<2 / py≤3.13 / xformers deps) |
| DA3-LARGE multi-view weights | CC-BY-NC | original paper | confirmed | **not used** (NC) |
| MoGe-2 | MIT | HF model card | confirmed | **used** (metric depth) |
| SAM 2.1 (segmentation) | Apache-2.0 | Meta repo | confirmed | **used** |
| SigLIP2 `google/siglip2-base-patch16-224` | Apache-2.0 | HF model card | confirmed | **used** (gallery classifier) |
| IFCT 2017 nutrient tables | © NIN / Govt. of India, cite | nin.res.in/ebooks/IFCT2017.pdf | confirmed | **cited**; values transcribed into derived tables with attribution |
| Indian Thali (ICVGIP 2025) data+code | code MIT; dataset terms on site | cvit.iiit.ac.in project page | **dataset terms unconfirmed** | cite; used only as local evaluation reference if permitted |
| ITD / WED (CVIT) | code MIT; `ITD.tar.gz`/`WED.tar.gz` terms unconfirmed | cvit.iiit.ac.in | **unconfirmed** | cite; no redistribution; local eval only |
| Kaggle "Indian Food Images (2026)" | CC BY-NC-SA 4.0 | kaggle.com dataset page | confirmed | gallery prototypes only (if used): attribution + no derivatives redistribution |
| Omnifood-Bench (arXiv 2607.08423) | paper cite | arXiv | confirmed | benchmarks context only |
| PM POSHAN menu + MDM F&N guidelines | user-provided document | — | confirmed | transcribed into data/menu.yaml, data/standards.yaml |
| Golden plate photos (30) | user's own captures | — | confirmed | primary evaluation set |
| Karnataka mid-day menu text | user-provided | — | confirmed | data/menu.yaml |

Open source build deps (torch, transformers, OpenCV, FastAPI, etc.): normal
vendoring rules; `uv pip` installs stay out of the repo.
