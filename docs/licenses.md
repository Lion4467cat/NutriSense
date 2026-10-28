# NutriSense licenses & attribution

Gate **M9**: before any release, confirm the two `unconfirmed` rows below.
Rule while unconfirmed: **cite, never redistribute** (no copying dataset files,
images, or database dumps into this repo or any artifact).
Verified 2026-10-28 (ticket `00-wed-license-provenance`): the WED/ITD "unconfirmed"
state is now stronger than a pending check — **no license text exists anywhere in the
distribution chain** (project page, GitHub repo, archive). See [WED/ITD](#wed--itd-cvit-iiit-h)
below for exactly what was and was not found.

| Asset | License | Source | Status | Use in NutriSense |
|---|---|---|---|---|
| DA3METRIC-LARGE (metric head) | Apache-2.0 | HF model card | confirmed | **not used** (rejected: numpy<2 / py≤3.13 / xformers deps) |
| DA3-LARGE multi-view weights | CC-BY-NC | original paper | confirmed | **not used** (NC) |
| MoGe-2 | MIT | HF model card | confirmed | **used** (metric depth) |
| SAM 2.1 (segmentation) | Apache-2.0 | Meta repo | confirmed | **used** |
| SigLIP2 `google/siglip2-base-patch16-224` | Apache-2.0 | HF model card | confirmed | **used** (gallery classifier) |
| IFCT 2017 nutrient tables | © NIN / Govt. of India, cite | nin.res.in/ebooks/IFCT2017.pdf | confirmed | **cited**; values transcribed into derived tables with attribution |
| Indian Thali (ICVGIP 2025) data+code | code: MIT asserted in README text (badged), **no LICENSE file exists**; paper: CC BY 4.0 (ACM); dataset: **no terms stated anywhere** | project page + paper PDF + authors' GitHub (per-source URLs below) | **dataset terms verified absent** 2026-10-28 — see [WED/ITD](#wed--itd-cvit-iiit-h) | **used**: WeightNet architecture port (`models/weight_head.py`, `tools/train_weight_head.py`); cite the paper |
| ITD / WED (CVIT) | dataset: **none stated** — `WED.tar.gz`/`ITD.tar.gz` ship only images (0 non-image files); page silent on license | cvit.iiit.ac.in | **no terms published** (verified 2026-10-28 — see [WED/ITD](#wed--itd-cvit-iiit-h)) | **used for local training only**: WED images live at `data/wed/{train,test}` but are **git-ignored** (never committed; `data/wed/.gitignore`); committed derived assets are the manifest (weights from the MIT metadata JSON), the slot mapping, the head-only checkpoint, and the σ yaml; cite; no redistribution of images |
| Nutrition5k (Google) | CC BY 4.0 (all data) | GitHub README "License & Contact" | confirmed (2026-10-28) | **planned**: weight-head cross-check + capture-protocol reference; attribution shipped with any use; images still kept out of the repo per house rule |
| FPB (Food Portion Benchmark, ISSAI) — dataset | CC BY-NC 4.0 | HF dataset card metadata | confirmed (2026-10-28) | **eval-only preferred** (NC): portion-geometry teacher; no redistribution; images never committed |
| FPB — code (IS2AI/Multitask-Food-Portion-Estimation) | AGPL-3.0 | GitHub license metadata | confirmed (2026-10-28) | **not vendored** — reference only; any borrowed idea re-implemented, repo stays AGPL-free |
| RASOI (Ashoka Food Computing Lab, NCVPRIPG 2025 challenge) | CC BY-NC-SA 4.0 + mandatory attribution string | official FKG.in library page | confirmed (2026-10-28) | gallery/segmentation prototyping only (NC/SA); **no redistribution**; the required credit line must appear wherever the dataset is referenced |
| Kaggle "Indian Food Images (2026)" | CC BY-NC-SA 4.0 | kaggle.com dataset page | confirmed | gallery prototypes only (if used): attribution + no derivatives redistribution |
| Omnifood-Bench (arXiv 2607.08423) | paper cite | arXiv | confirmed | benchmarks context only |
| PM POSHAN menu + MDM F&N guidelines | user-provided document | — | confirmed | transcribed into data/menu.yaml, data/standards.yaml |
| Golden plate photos (30) | user's own captures | — | confirmed | primary evaluation set |
| Karnataka mid-day menu text | user-provided | — | confirmed | data/menu.yaml |

Open source build deps (torch, transformers, OpenCV, FastAPI, etc.): normal
vendoring rules; `uv pip` installs stay out of the repo.

---

## Dataset license verification (2026-10-28, ticket `00-wed-license-provenance`)

Method: every claim below is from a primary source (the project's own page, the
authors' repository, the distributed archive itself, or the published paper) accessed
**2026-10-28**. Re-fetch at any release checkpoint; access failures are recorded verbatim.

### WED + ITD (CVIT, IIIT-H)

**What was verified:**

- **Paper: CC BY 4.0.** The published paper PDF hosted by CVIT
  (https://cvit.iiit.ac.in/images/ConferencePapers/2025/ICVGIP_Food_Scanner.pdf,
  accessed 2026-10-28) states on page 1: "This work is licensed under a Creative
  Commons Attribution 4.0 International License." with "© 2025 Copyright held by the
  owner/author(s)" and the ACM Reference Format block citing DOI
  10.1145/3774521.3774594. **This covers the paper text only — not the datasets.**
- **Dataset archives: no license, no terms, no readme.** `WED.tar.gz` downloaded from
  https://cvit.iiit.ac.in/images/datasets/food_nutrition/WED.tar.gz (local copy
  `~/Downloads/WED.tar.gz`, listed 2026-10-28): 3,445 entries = 1,394 `.jpg` +
  1,394 `.png` masks + directories, and **zero non-image files** — no LICENSE, README or
  terms document. Same for `ITD.tar.gz` (7,898 `.jpg` + 7,898 `.png`, zero non-image
  files). The archive directory layout (`gtFine/…/setN/`) also matches ADR 0002's
  description of the metadata JSONs living outside it.
- **Project page: silent on licensing.** https://cvit.iiit.ac.in/research/projects/cvit-projects/indian_thali
  (accessed 2026-10-28) contains no occurrence of "license"/"licence", no terms link,
  and no download-agreement text; it repeats the 0 occurrences on the page source.
- **Authors' GitHub: MIT claimed for the project, but no LICENSE file exists.**
  https://github.com/yasharora102/Indian_Thali_ICVGIP2025 (accessed 2026-10-28): the
  README's "License" section says "This project is released under the MIT License" and
  displays an MIT badge — however the badge links to a `LICENSE` blob that does not
  exist (raw URL returns 404), GitHub's license-detection API field is `null`, a
  recursive tree search over the repo finds no license file, and no commit ever touched
  a `LICENSE` path. The MIT claim therefore rests on README prose alone.
  `VERIFICATION_GUIDE.md` exists but is **empty** (0 bytes; raw fetch 2026-10-28).
  The README's only dataset instruction is to download from the project page and
  "please cite our paper" if the code or dataset is useful.
- **ACM DL landing page blocked:** https://dl.acm.org/doi/10.1145/3774521.3774594
  returned **HTTP 403** (automated fetch, 2026-10-28) — the paper's license was verified
  via the CVIT-hosted PDF above instead.

**Verdict.** The *paper* is open (CC BY 4.0); the *code* is MIT per README text; the
*datasets carry no license statement at all* — absent a grant, default law applies
(all rights reserved). The only condition stated anywhere is the README's citation
request. Consequence of "no terms" being stricter than a stated license: **nothing on
WED leaves the machine** — images stay at git-ignored `data/wed/`, nothing redistributes
(only the citation does, per the README), and additionally the trained artifacts
derived from WED images (`data/weight_head.pt`, manifest, mapping, σ yaml) must be
treated as **release-gated**: before any public artifact release, obtain written terms
from CVIT/IIIT-H covering both the dataset and weights trained on it. Gate M9 stays
open for exactly that; author-contact (yasharora102@gmail.com / adityaarun1@gmail.com /
jawahar@iiit.ac.in, all printed in the paper) is the closure path.

**ADR 0002 reconciliation.** ADR 0002 ("Dataset provenance", item 5) reads:
"WED + the two metadata JSONs are downloaded from the authors' project page/repository
(MIT)" and elsewhere "Their code is MIT-licensed … we port the architecture". Verified
result: the **MIT read is correct for the code** (README-asserted; tic of caution: the
LICENSE file the badge points at is missing, so the assertion is unaccompanied), but
**"(MIT)" must not be read past the code** — the dataset download carries no license,
so ADR 0002's parenthetical over-reached onto the data. The recorded practice — images
citation-only and never redistributed — is **our own conservative rule, not a
dataset-stated term**; that distinction is what this entry exists to make. No change in
behaviour follows (we already do the strictest permissible thing under unknown terms);
what changes is that M9's resolution now requires a written statement from CVIT rather
than merely checking the page again.

### Nutrition5k (Google)

- **CC BY 4.0 — verified.** https://github.com/google-research-datasets/Nutrition5k
  (accessed 2026-10-28), section "License & Contact": "We release all Nutrition5k data
  under the Creative Commons V4.0 license" linking to
  https://creativecommons.org/licenses/by/4.0/ — "You are free to share and adapt this
  data for any purpose, even commercially", attribution requested via the CVPR 2021
  citation. Repository was archived read-only on 2026-04-19; the 181.4 GB tarball
  (https://storage.cloud.google.com/nutrition5k_dataset/nutrition5k_dataset.tar.gz)
  remains on the public GCS bucket.

**Verdict.** Training, eval and protocol study all permitted; redistribution would even
be allowed (with attribution + license link) — but house policy keeps its images out of
the repo anyway (cite-only default). ADR/research assumption (CC BY 4.0) **holds**; no
correction.

### FPB (Food Portion Benchmark, ISSAI / Nazarbayev University)

- **Dataset: CC BY-NC 4.0 — verified.** HF dataset card metadata
  (https://huggingface.co/datasets/issai/Food_Portion_Benchmark, raw README
  retrieved 2026-10-28 — front-matter `license: cc-by-nc-4.0`). The card's only other
  term-like text is a citation request to the IEEE Access paper.
- **Paper (secondary metadata only):** IEEE Access 13:152033–152045,
  DOI 10.1109/ACCESS.2025.3603287 — OpenAlex marks the *article* cc-by; IEEE Xplore was
  not fetched. The **operating license for the data** is the card's CC BY-NC 4.0; the
  stricter of the two governs every defensible reading.
- **Code: AGPL-3.0 — verified.** https://github.com/IS2AI/Multitask-Food-Portion-Estimation
  (GitHub license metadata, accessed 2026-10-28). No license section in the README
  itself. AGPL is copyleft → **never vendor their code into NutriSense**.
- **No dataset-download license file was found** beyond the card metadata
  (score-checker / test-labels gating noted on the card).

**Verdict.** Eval-only posture (as recommended in `docs/research/indian-food-datasets.md`)
is the safe choice under NC: no training-side dependency, **no redistribution of images
or labels, images never committed**. This matches — but now **verified** rather than
assumed — the research doc's "CC BY-NC 4.0" claim and its "eval-only preferred given NC"
note. ADR 0002 makes no FPB assumption; nothing to correct there.

### RASOI (NCVPRIPG 2025 challenge, Ashoka University Food Computing Lab)

- **CC BY-NC-SA 4.0 — verified from the official maintainer page.**
  https://fkg-india.github.io/library/datasets/ (accessed 2026-10-28): "This dataset is
  provided under the **CC BY-NC-SA 4.0** license and is intended solely for
  **non-commercial research use**." plus a hard attribution requirement: the credit
  "**Created and maintained by the Food Computing Lab, Ashoka University, India.**"
  must appear "in all publications, presentations, evaluations, communications, and
  anywhere else that the dataset may be referenced".
- **Kaggle listing reachable but content not scrapeable:**
  https://www.kaggle.com/datasets/eda19bdde69843e6a82f85d0a6ee495139a81d5b76f79331eb54dd69e6b0d0a9
  (linked from the FKG.in page; accessed 2026-10-28) rendered only its title
  ("RASOI Challenge Dataset | Kaggle") — the page body is JS/login-gated, so the
  license text on Kaggle itself could not be independently re-verified; the FKG.in
  page (the creators' own site) is used as the primary source instead.

**Verdict.** Gallery/segmentation prototyping (non-commercial) is fine; anything
shipped — even the credit line — must carry the exact attribution string and **the
dataset or its derivatives redistribute nowhere** (NC + SA + mandated credit). This
matches the research doc's claim; now verified from the primary source.

### Standing consequence of stricter-than-assumed terms

- WED: **absent terms are stricter than ADR 0002 assumed** in their vagueness —
  practices unchanged (git-ignored images, cite-only), but M9 closure now = written
  CVIT permission covering dataset **and** the trained head, before any public release
  of NutriSense artifacts.
- FPB / RASOI: NC/SA confirmed → eval-only / prototyping postures stand, both now
  verified rather than assumed.
- Nutrition5k: CC BY 4.0 confirmed → both training and eval permissible; keep the
  house cite-only posture regardless.
