# Dataset workspace

This directory is the home for externally acquired datasets and their provenance. Raw image archives and derived datasets are local-only and ignored by Git. Keep license files and source README files beside each downloaded dataset; do not upload source images or archives to this repository.

## NutriSense data already in the project

The current pipeline and evaluation tools still use these established paths:

| Dataset | Current path | Role |
|---|---|---|
| WED | `data/wed/` | Indian plated-food images with measured grams; current mass model and locked evaluation |
| Nutrition5k | `data/nutrition5k/` | Ingredient weights and nutrition; transfer/teacher experiments |
| ECUSTFD | `datasets/raw/portion/ecustfd/` | 2,978 views grouped into 160 physical portions with box annotations; local mirror is missing `portions.csv`, so it has no verified mass/volume targets and is not grams-training eligible |
| MetaFood3D | `datasets/raw/marker/metafood3d/` | 3D meshes, RGBD videos, flipped-food videos, point clouds, and a nutrition workbook with object weights; CC BY-NC 4.0 |
| FinnFoodPics | `datasets/raw/portion/finnfoodpics/` | Controlled 72-snack portion series, energy-density labels, and nutrition workbook; auxiliary snack experiment only (see `datasets/finnfoodpics/README.md`) |
| AI-ServicesBB Food Waste Dataset | `datasets/raw/portion/ai-servicesbb-food-waste/{train,test}/` | CC BY 4.0; 215 train images / 12 receipts and 160 official-test images / 4 receipts. The author test split was evaluated once and is now closed to development (see `experiments/food_waste/`) |
| LeFood-Set V1 | `datasets/raw/portion/lefood-set/` | CC BY 4.0; 524 complete before/after pairs across 34 Indonesian food categories. The frozen current pipeline abstained on all 143 category-held-out test images. One preregistered research-only scalar candidate was tested once (69.050 g MAE, −60.061 g signed bias) and the test categories are now closed. Tare handling is undocumented in the paper. See `experiments/lefoodset/`. |
| VLM Food Benchmark | `datasets/raw/portion/vlm-food-benchmark/` | CC BY 4.0 data, MIT code; selectively downloaded 200 canteen meal images and 870 manually verified item weights with empty-plate tare subtracted. Participant-held-out experiment: 106 train / 34 dev / 60 test. Current pipeline abstained on all test images; research DINOv2-S candidate MAE 148.0 g vs 172.0 g median baseline, bias −106.9 g. Test is one participant/device cluster; details at `experiments/vlm_food_benchmark/`. |

The local VLM Food Benchmark checkout is sparse and pinned to commit
`d715df0c0debe65da805618431e67f6d0fa01c71`; it contains the images, labels,
participant map, citation, and data license, but not the source model outputs
or code. The source data license is CC BY 4.0 and its code license is MIT.
Audit and reproduce the frozen comparison with the commands in
`experiments/vlm_food_benchmark/PROTOCOL.md`.

Two useful user-collected image sets currently sit one directory above this repository and are intentionally left in place because existing tools and reports refer to those paths:

| Local collection | Current path | Role |
|---|---|---|
| Gallery/canteen images | `../DATASET/` | 46 gallery photos and diagnostic real-plate images; `tools/build_gallery.py` uses this path |
| ArUco food captures | `../Aruco_7ID_60mm_with_food/` | 23 existing card-in-frame images in six dish folders; some filenames encode weights. Audit existing labels only; use for exploratory checks if verifiable—no new capture is assumed. |

`datasets/metafood3d/README.md` records the local MetaFood3D inventory and its use limits; `experiments/metafood3d/RESULTS.md` records a failed research-only single-object benchmark. `CARD_REPORT/` contains geometry diagnostics/reports, not source training images. Keep reports separate from raw images.

WED and Nutrition5k are not moved because training scripts, manifests and the protected WED test split refer to their current paths. `data/cache/` is a derived feature cache, not source data. The local Nutrition5k ingredient table uses a deterministic dish-ID hash split, not the upstream official split. Do not combine datasets by concatenating raw labels: their target units, food granularity, capture conditions and licensing differ. Build source-aware adapters and train only compatible task heads; evaluate WED with its existing locked split.

## Acquisition folders

```text
datasets/
  README.md                 this guide
  registry.csv              source, task, license/access and local status
  download_public.sh        repeatable public Hugging Face acquisitions
  raw/
    marker/                 marker/card/depth capture sources
    portion/                measured mass/volume/nutrition sources
    recognition/            food labels and masks without measured mass
  processed/                generated manifests/adapters; do not edit raw files
```

The download script uses the repository's `.venv` by default (override with `PYTHON=/path/to/python`). It requires the `huggingface_hub` package already installed. Run it from the repository root:

```bash
bash datasets/download_public.sh
```

By default this retrieves ECUSTFD (~144 MB locally). To fetch the Food Portion Benchmark (FPB), run `DOWNLOAD_FPB=1 bash datasets/download_public.sh`; its Hugging Face snapshot has 28,155 individual files and the current host connection estimates several hours. FPB is CC BY-NC 4.0. ECUSTFD's Hugging Face mirror says CC BY 4.0, but the upstream project does not state a license, so retain it for research evaluation only until provenance and reuse terms are confirmed. The script does not download gated or account-based archives implicitly.

The Indian Thali Dataset archive is from its [CVIT project link](https://cvit.iiit.ac.in/images/datasets/food_nutrition/ITD.tar.gz). Its ~821 MB transfer is paused at 140 MB in `datasets/raw/recognition/itd/`. It supports Indian food segmentation/layout work; the public page does not make reuse terms clear, so do not redistribute or train on it until those terms are checked. Keep the partial archive out of experiments and do not resume acquisition before the project review.

## How to decide whether data can train each part

- **Mass/portion head:** use records with actual scale-measured grams and a known correspondence between image, item/plate, and measurement. Keep per-item grams, total meal grams, and volume as distinct targets.
- **Nutrition head/table:** use documented ingredient weights paired with nutrient source and recipe/food identity. Calories calculated from estimated serving labels are not ground-truth mass.
- **Marker/depth geometry:** retain marker corners/ID, known physical size, camera intrinsics/pose, depth units, and the original image. A checkerboard or coin can help scale, but is not ArUco detector training.
- **Recognition/segmentation:** label-only images can expand the gallery or mask/detection evaluation; they cannot supervise grams or calories.
- Keep dataset identity and original split in every manifest row. Never split images from the same plate, session, or participant across train and evaluation. Do not alter the WED locked test set.
- Rebuild local adapters with `.venv/bin/python -m tools.build_nutrition5k_manifest`, `.venv/bin/python -m tools.build_ecustfd_manifest`, and `.venv/bin/python -m tools.build_finnfoodpics_manifest`. Audit outputs with `tools.audit_dataset_manifest`; `--hash-images` checks exact duplicates across local non-locked splits.

For the research rationale and access links, see [fiducial-food-data-and-calorie-apps](../docs/research/fiducial-food-data-and-calorie-apps.md) and [indian-food-datasets](../docs/research/indian-food-datasets.md).
