# Research: Model Accuracy and Production Readiness

## Current system evidence

- The deployed mass head is a frozen DINOv2-S/14 encoder with ROI-aligned, class-conditional gram regression. Its recorded WED DEV MAE is **15.034 g** over 108 views / 21 plates; the plate-bootstrap 95% interval is [12.227, 18.889] g. This is DEV evidence only, not a locked-test or broad-generalization claim. Source: `AGENTS.md`, `docs/ledger/001-current-state.md`, `docs/ledger/002-dinov2-encoder.md`.
- WED has 267 plates and 16,211 ROIs with official internal TRAIN/DEV/LOCKED discipline; views from one plate are correlated. Evaluate at plate level and preserve LOCKED access rules.
- Prior Nutrition5k ingredient-head experiment was not promoted; see `docs/ledger/012-n5k-ingredient-head-07b.md`. Existing experimental checkpoints do not replace the deployable baseline.
- Current serving path is FastAPI (`main.py`) with `/health`, `/menu`, `/goals`, and `/analyze`; upload size is bounded, one GPU inference is serialized per process, and CORS origins are configurable. The feature should preserve the response contract while adding measured reliability.
- Existing local assets include WED (`data/wed`), a Nutrition5k subset (`data/nutrition5k`), ECUSTFD (`datasets/raw/portion/ecustfd`), project ArUco captures (`../Aruco_7ID_60mm_with_food`), and FinnFoodPics organized at `datasets/raw/portion/finnfoodpics`. `../DATASET` is a gallery/diagnostic collection, not weighed supervision. ITD is an incomplete archive and recognition-only; it is not a grams training source.

## Dataset supervision fit

| Source | Defensible role now | Group/split unit | Limits |
|---|---|---|---|
| WED | Main Indian plated-food grams training and DEV comparison; locked final report | Plate and capture session | Preserve existing manifests and lock; current DEV has only 21 plates |
| Nutrition5k | Source-aware transfer/auxiliary experiment; RGB-D and nutrition/ingredient tasks where available | Dish ID; retain official split | Cafeteria domain differs from Indian meals; labels and views must be mapped explicitly |
| ECUSTFD | Box/coin detection audit only from current local mirror | Physical portion ID, keeping top/side pair together | Local mirror has 2,978 images/160 portions but lacks `portions.csv`; measured mass/volume targets are unavailable. Coin-based capture is not ArUco; upstream terms also need confirmation. |
| FinnFoodPics | Controlled snack energy-density/portion-order analysis or narrow external snack experiment | Snack identity across all ten calorie levels | 72 Finnish snacks, staged energy tiers, workbook nutrition/120-kcal portion; not mixed-meal weighed grams ground truth |
| Local ArUco captures | Exploratory marker/label QA; score only image-weight pairs already verifiable | Existing dish/session and physical plate/item | Only 23 clustered images, some timestamp-only; too small for reliable independent generalization claims |
| Gallery `../DATASET` | Recognition/gallery QA only | Original image/session | No measured grams established |
| ITD partial archive | Exclude until complete, provenance/terms and annotations are checked; segmentation only | Dish/session | Not a mass label set; current local archive is partial |

The released FinnFoodPics database has 72 food images/snacks photographed at ten calorie portion levels (40–400 kcal), with per-100 g nutrition and a 120-kcal portion size plus visual/participant metadata. The data are behavioral-research stimuli, not an arbitrary-scale meal dataset. Use the local 2026 release and its separate CC BY-NC-SA 4.0 license; do not place source images/archives in Git or a public artifact. The 2023, 2024 and 2026 copies are versions of the same dataset, not three independent datasets.

## Research conclusions

1. **Make the error reduction trustworthy first.** Freeze baseline predictions, data/config hashes and group manifests. Compare candidate predictions paired on the exact same DEV examples; bootstrap whole plates/sessions. Report MAE plus median absolute error, RMSE, mean signed bias, relative error, and plate/meal totals. A smaller ROI MAE is insufficient if it worsens a meal total or a major food/portion group.
2. **Work within the available sample size.** Do not block this plan on new weighed plates or annotation. Audit the current ArUco folder (23 images, with only some filenames encoding weights) and use only labels whose image correspondence and tare meaning can be verified. Treat that tiny set as exploratory QA, not a generalization benchmark. Use existing WED DEV as the tuning source and ECUSTFD/Nutrition5k/FinnFoodPics only for their compatible, separately reported tasks.
3. **Use marker/depth geometry as an ablation, not a promised fix.** A marker gives scale at its plane; it does not provide food height, volume, or density by itself. Compare image-only against marker scale, aligned depth/volume where valid, and compatible learned features. Record angle, distance, intrinsics, marker visibility, and food-vessel geometry.
4. **Do not pool every label into one grams loss.** Preserve source and target meaning. Use only labels that exist (with task-specific or masked losses), and begin with WED-only, then WED+Nutrition5k, WED+ECUSTFD and FinnFoodPics auxiliary experiments. Promote only if WED DEV improves and pre-registered subgroup guardrails pass; keep external domain metrics separate.
5. **Separate recognition/coverage from mass estimation.** Report missed/hallucinated items and component matching, per-item mass, plate total, and end-to-end calories/macros. An apparently strong MAE among matched items can conceal unreported missing foods.
6. **Calibrate uncertainty on disjoint data.** Evaluate interval coverage and width on an independent calibration/evaluation partition, then define confirmation, retry, or abstention behavior for low-confidence, unsupported, or poor-quality captures. Do not claim uncertainty validity under arbitrary domain shift.
7. **Set operational limits from a measured deployment target.** Benchmark full API p50/p95 latency, peak memory/VRAM, throughput/concurrency, upload validation, timeouts, and failures on the intended hardware. The repository has an upload limit and per-process inference limiter already; record these existing controls and their measured behavior.
8. **Version and license the full experiment.** Data adapter version, source/release/license, split/group manifest, preprocessing, checkpoint, config, environment, predictions, confidence intervals, runtime and decision belong together. Do not ship noncommercial FinnFoodPics material in a public package.

## Primary sources

- University of Helsinki FinnFoodPics record, contents and study purpose: <https://researchportal.helsinki.fi/en/datasets/finnfoodpics-image-database/>
- Kanyamibwa et al., FinnFoodPics article (2025): <https://www.sciencedirect.com/science/article/pii/S0950329325000874>
- Nutrition5k official dataset README, data fields, official splits and license: <https://github.com/google-research-datasets/Nutrition5k/blob/main/README.md>
- Thames et al., Nutrition5k CVPR 2021 paper (RGB, depth, mass and nutrition experiments): <https://openaccess.thecvf.com/content/CVPR2021/papers/Thames_Nutrition5k_Towards_Automatic_Nutritional_Understanding_of_Generic_Food_CVPR_2021_paper.pdf>
- ECUSTFD author repository (paired top/side capture, coin scale, annotations, known missing-coin records): <https://github.com/Liang-yc/ECUSTFD-resized->
- ECUSTFD paper: <https://arxiv.org/abs/1705.07632>
- Food Portion Estimation via 3D Object Scaling, CVPR Workshops 2024: <https://openaccess.thecvf.com/content/CVPR2024W/MTF/html/Vinod_Food_Portion_Estimation_via_3D_Object_Scaling_CVPRW_2024_paper.html>
- Angelopoulos et al., Conformal Risk Control, ICLR 2024: <https://proceedings.iclr.cc/paper_files/paper/2024/hash/f3549ef9b5ff520a7e41ff3cc306ab2b-Abstract-Conference.html>

The current `../Aruco_7ID_60mm_with_food/` directory contains 23 images in six dish folders. Six filenames contain weight-like values, while the other views have timestamp filenames. The audit marks zero examples mass-evaluation eligible because filenames alone do not establish whether a vessel value is tare, loaded mass, or a per-image food target. This is useful for marker-pipeline QA, but it is too small and clustered to serve as a representative production test set.

Research-agent findings used here were checked against the cited papers/repos and local records. No claims of transfer performance are inferred from those sources.
