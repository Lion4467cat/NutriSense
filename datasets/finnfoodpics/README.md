# FinnFoodPics local acquisition

The downloaded FinnFoodPics files are organized under `datasets/raw/portion/finnfoodpics/`:

```text
raw/portion/finnfoodpics/
├── archives/             original 2023, 2024, and 2026 zip files
└── versions/
    ├── 2023/             original extracted release
    ├── 2024/             duplicate image release with 2024 license file
    └── 2026/             latest extracted release and 2026 license/workbook
```

The original extracted folders were moved without modifying the source images. The 2024 extracted copy contains the same image files as the 2023 copy, but has a different license document; keep both for provenance. The 2026 release contains updated workbook/license files and small differences in Windows thumbnail metadata. Do not treat the three releases as independent data.

The 2026 workbook and PDF license remain alongside the images. Stale Excel lock files and `Thumbs.db` are operating-system artifacts, not dataset records, and are excluded from any manifest. `datasets/raw/` is ignored by Git; do not commit image files, archives, or the license PDF.

Generate the local, identity-grouped manifest with:

```bash
.venv/bin/python -m tools.build_finnfoodpics_manifest
```

This writes `datasets/processed/finnfoodpics_v2026_manifest.csv` (also Git-ignored). It has 720 rows across 72 snack identities, with all ten calorie levels for an identity assigned together to train/validation/test. Three identities (`carbohydrate_5`, `carbohydrate_32`, `combo_17`; 30 images total) do not have rows in the 2026 workbook, so their manifest records contain only the filename calorie-tier label and no nutrition or nominal-mass target. For the other images, the nominal mass is scaled from the workbook's 120 kcal portion; it is not a per-image scale measurement. Keep these targets in the separate FinnFoodPics task, never in WED measured-grams evaluation.

## Intended use in NutriSense

The dataset has 72 Finnish snack identities, each represented at ten calorie-defined portion levels (40–400 kcal). The workbook provides per-100 g nutrition and a standardized 120 kcal portion, as well as visual and preference metadata. Use it only for a controlled snack/energy-density side experiment or external evaluation. It is not a direct source of weighed mixed-meal labels for the WED gram model. Never infer the portion target from a filename during model input; parse portion level only as a label, and group all images for a snack identity in one split.

The local 2026 license identifies the database as CC BY-NC-SA 4.0, for noncommercial research, with restrictions on broad redistribution/public uploads. Keep the source local and consult that license before publishing derived images or model artifacts. The article's open-access license does not replace the separate image-database license.

Dataset record: [University of Helsinki research portal](https://researchportal.helsinki.fi/en/datasets/finnfoodpics-image-database/). Paper: Kanyamibwa et al. (2025), *FinnFoodPics: A database of Finnish snack foods for investigating modern eating behaviors*, Food Quality and Preference 129, 105512, DOI 10.1016/j.foodqual.2025.105512.
