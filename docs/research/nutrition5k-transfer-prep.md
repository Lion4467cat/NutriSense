# Nutrition5k transfer prep — provenance, license, and feasibility

**Ticket:** `06-robustness-program` (spec 002 decision 11: transfer prep from
measured non-Indian "teacher" datasets) · **Date:** 2026-10-29 · **Status:** prep
complete; no training run performed.

## Provenance

- **Dataset:** Nutrition5k (UCSF cafés, 5,006 plates; ~3,500 with overhead
  RGB-D). Paper: "Nutrition5k: A Direction-Aware Multi-Modal Nutrition
  Database" (CVPR 2021), arXiv 2103.03375. Released by Google Research.
- **Canonical access (authoritative):** `gs://nutrition5k_dataset/`
  (bucket browser: https://console.cloud.google.com/storage/browser/nutrition5k_dataset;
  README + instructions: https://github.com/google-research-datasets/Nutrition5k).
  `gsutil` is documented by the README, but the bucket is **publicly listable
  and fetchable via the anonymous GCS JSON API**, which is what we used — no
  gcloud auth required.
- **Pulled into local storage (git-ignored under `data/nutrition5k/`):**
  - `metadata/dish_metadata_cafe1.csv` (4,768 dish rows; 2.2 MB)
  - `metadata/dish_metadata_cafe2.csv` (238 dish rows)
  - `metadata/ingredients_metadata.csv` (555 ingredients)
  - `README` (bucket copy, 73 bytes)
  - Pilot overhead imagery: `imagery/realsense_overhead/{dish_1561662216,
    dish_1556572657, dish_1556573514}/rgb.png` (640×480 RGB PNG, ~0.4 MB each;
    total local footprint ~3 MB). Depth PNGs deliberately not pulled for the
    pilot; the teacher-transfer plan needs only the overhead RGB.
  - Ground truth verified from the CSVs: per-dish total mass + calories +
    macros, **plus per-ingredient grams** (e.g. `dish_1561662216`: 300.79 g
    total, 193 kcal, ingredient rows `soy sauce 3.40 g`, `garlic 2.12 g`, …).
  - Nothing is committed to git; `.gitignore` entry `data/nutrition5k/` added.

## License

- The official dataset README states: **"We release all Nutrition5k data
  under the Creative Commons V4.0 license"** and the summary phrases it as
  usable for any purpose including commercial. The README **does not pin the
  exact CC 4.0 flavor** (BY/CC0) or link a deed — treat it as the GitHub
  wording and cite the paper.
- **FPB correction (recorded):** the non-commercial, eval-only item in the
  ticket is **FPB = Food Portion Benchmark** (ISSAI/NU, 14,083 images / 138
  classes, `cc-by-nc-4.0` on the Hugging Face card,
  https://huggingface.co/datasets/issai/Food_Portion_Benchmark) — it is a
  separate dataset, NOT part of Nutrition5k. FPB stays eval-only here under
  its non-commercial license if ever used.
- Redistribution posture: **no Nutrition5k images will be committed**; the
  local subset stays git-ignored, consistent with the citation-only posture
  used for WED (`docs/licenses.md`).

## Feasibility note (teacher transfer, RASOI scale head → Nutrition5k scale)

- **What a "teacher" transfer means concretely:** a DINOv2-feature regressor
  of the same family as `tools/train_weight_head.py` (frozen DINOv2 encoder +
  the plain `head_mlp`, recipe `baseline rgb/no-attn/geom-none`) trained on
  Nutrition5k overhead dishes with
  **total-dish-mass grams** as the target (ingredient-level grams are also
  available and match the portion-head's per-item output shape). Nutrition5k's
  paper itself trained exactly this shape (InceptionV2 regressor, JFT-300M
  pretrain) — the target task is proven learnable on this data.
- **Domain gap (why teacher-only):** Nutrition5k is rectangular silverware +
  US café plates on a captured turntable, no ArUco card, fixed-ish camera
  geometry. Our head assumes card-metered scale. The transfer is therefore
  **feature-level pretraining then prompt/domain re-fitting on the Indian
  data**, not direct inference. Sizing experiment needed first: train the
  simplest regressor (per-dish mass, fc head on frozen DINOv2 features — the
  ticket-01 feature-cache path applies directly) on a few hundred dishes and
  check the loss curve before committing to the full-scale pull.
- **Cost of scale-up:** no per-component sizes are published; the full tarball
  is 181.4 GB (194.8 GB exact, md5 verified in the bucket listing, not
  downloaded). Median overhead `rgb.png` ≈ 0.4 MB → a 1,000-dish overhead-RGB
  subset ≈ 0.4–1 GB (`dish_metadata` first, filter to dishes present under
  `imagery/realsense_overhead/`, then fetch just `rgb.png` per dish). The
  anonymous-API pattern used here scales to that volume with a listed-prefix
  walk; rate limits unknown — pilot first.
- **Blocking/unknown items:** the documented `gsutil` tooling requires the
  gcloud SDK only for convenience, not for access; TFDS catalog has no
  Nutrition5k entry; side-angle payloads are large (~36 MB/dish average across
  the whole release) and are not needed for this plan.

## Source URLs

- Dataset repo (license statement + gsutil instructions):
  https://github.com/google-research-datasets/Nutrition5k
- Paper (sampling, ingredient weighing, USDA mapping):
  https://arxiv.org/html/2103.03375v2
- Bucket browser: https://console.cloud.google.com/storage/browser/nutrition5k_dataset
- FPB dataset card (cc-by-nc-4.0 — separate dataset):
  https://huggingface.co/datasets/issai/Food_Portion_Benchmark/blob/main/README.md
- Public-pretraining comparison on Nutrition5k:
  https://arxiv.org/html/2508.03996v2
