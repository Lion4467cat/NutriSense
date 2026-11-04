# Synthetic corpus phase 1: baseline freeze, renderer audit and pilot plan

Status: baseline references frozen; renderer-only pilot generated and passed
automated checks; stratified human review is pending. This phase does not train
production models or generate GAN/diffusion appearances.

## Frozen real-data baseline

`experiments/synthetic_food/baseline_freeze.json` records SHA-256 digests for
the classifier gallery/model revision, frozen DeepLabV3 checkpoint, weight
head, uncertainty config, integrated pipeline modules, and the reports used as
the reference. Run `uv run --python .venv/bin/python
tools/freeze_synthetic_baseline.py` to recreate it. Generation preflight now
checks each recorded digest and refuses to proceed if any reference changes.

The integrated WED DEV measurements and their limits remain in
`experiments/real_pipeline_baseline/dev_report.md`. The stage record explicitly
does not promote the contaminated SigLIP crop/gallery report as independent
classification accuracy. The integrated class labels come from DeepLabV3;
the separate classifier remains a diagnostic. Renderer depth/geometry metrics
remain renderer-only and do not establish real-camera depth accuracy.

## Renderer audit

| Requirement | Existing support | Gap and pilot treatment |
| --- | --- | --- |
| 41 WED classes | `load_class_registry()` reads IDs/names from the WED index map and verifies 41 classes. | All 41 have eligible non-DEV TRAIN mass examples in the current manifest. Pilot records source group and source annotation hashes. |
| Isolated portions | `build_class_scene()` builds one class scene from grams and density. | All classes share one radial mound, fixed radius/fill profile. Pilot adds explicit morphology presets and samples a central TRAIN-supported portion; no claim that this recovers dish-specific 3D shape. |
| Composed thalis | `build_thali_scene()` places separate component height fields and labels them with `comp_ids`. | Current layout is a regular radial arrangement; pilot includes several multi-class scenes and preserves component IDs. Food overlap/occlusion remains a known renderer limit. |
| Appearance | Seven generic renderer material profiles plus a deterministic class palette. | The palette is not WED-conditioned. Pilot derives robust color/texture statistics from eligible WED TRAIN food pixels only; it does not copy source pixels. This is weak appearance conditioning and requires human review. |
| Portion range | `observed_portion_ranges()` reads WED TRAIN net grams and excludes the seed-42 DEV groups. | One central supported amount per class is only a coverage pilot, not a learned portion distribution. Full generation needs quantile coverage and broader-range tags. |
| Camera/light/viewpoint | Seeded camera pose, illumination direction/intensity, noise and table color. | Current camera family is narrow and vessels are idealized. Pilot varies these seeded parameters and records them; real camera response, lens distortion, shadows and specularity remain absent. |
| ID 7 / 60 mm marker | Renderer places DICT_4X4_50 ID 7 at 60 mm; planted corner/scale/tilt labels are computed from projection. | Outer card artwork is the legacy A6 synthetic fixture, while field capture uses an A4 PDF. Pilot pins marker ID/dimensions and records card layout; paper/artwork fidelity is explicitly not validated. |
| RGB/masks/depth | RGB, food mask, object IDs, component IDs and metric camera-Z depth exist in memory. | Current corpus writer saves RGB, a mask and depth only. Pilot adds a compressed geometry bundle with 3D world points, surface heights, object/component IDs, camera matrices, component volume/mass and marker pose. |
| Physical labels | Mass is integrated from the rendered height field and configured density. | Per-class config numbers are a mix of FAO direct/analogue values and project assumptions. Pilot stores the chosen value, its range, source, status and sampled density. Density stays an explicit assumption unless the exact served food is directly supported. |
| Label QA | Basic shape/finite-depth/mass checks, exact card-pair checks and human review queue exist. | Checks do not yet cross-check class masks/component IDs, geometry volume, marker clipping/scale, or all artifact hashes. Pilot validates these invariants and emits a stratified review sheet. Human review is still pending until a person fills it out. |

### Density evidence and assumptions

The existing source table is `data/ingredient_densities.yaml`. It is derived
from the FAO/INFOODS Density Database v2, which FAO describes as a tool for
converting volume and weight, with values compiled from literature, national
food tables and author measurements ([official FAO database page](https://www.fao.org/infoods/infoods/tables-and-databases/faoinfoods-databases/en/),
[official database PDF](https://www.fao.org/fileadmin/templates/food_composition/documents/density_DB_v2_0_01.pdf)).
Those entries include direct matches, analogues and absent-food assumptions;
they are not interchangeable. Existing `data/wed_dishes.yaml` serving values
are sometimes project assumptions and sometimes differ materially from the
FAO analogue (for example, the salad mapping is explicitly flagged in the
density audit). The pilot will preserve each source/status and uncertainty
range, and will not relabel analogues as class-specific measurements.

## Implementation sequence

1. Freeze reference checkpoints, configuration files and report digests. No
   writer in the pilot may target those paths.
2. Derive a small TRAIN-only appearance profile table from the labeled WED
   TRAIN groups after excluding the seed-42 DEV groups. Persist source hashes
   and per-class support counts; never read DEV images for conditioning.
3. Extend renderer labels to include per-pixel 3D coordinates/surface height,
   geometry volume and component provenance. Preserve camera Z-depth units in
   metres and geometry coordinates in millimetres.
4. Generate one isolated portion for each of the 41 classes and three
   composed multi-item thalis. Render matched card/no-card pairs with a single
   scene seed and compare all scene fields, masks, geometry and RGB diffs.
5. Run automated geometry, mask, depth, mass, marker and lineage checks;
   generate a stratified human-review CSV. Do not call the pilot accepted
   until the human review is completed.
6. Report coverage, ranges, check failures, image examples and limitations.
   Stop before corpus scaling or GAN/diffusion comparison until the pilot is
   reviewed.

## Pilot result

The pilot covers 41/41 classes with 41 isolated portions and three composed
thalis, each rendered with an exactly matched card-present/card-absent pair
(88 images total). Automated geometry/mask/mass checks pass 88/88 scenes and
44/44 pair checks; the audit verified 616 hashed artifacts. Six initial
negative-depth findings in the first thali geometry were traced to densely
packed tiny component domes. The pilot renderer was corrected to use
volume-proportional angular regions across the shared plate surface, after
which every scene passed the positive-depth and geometry gates.

Visual spot checks show the assets remain stylized: isolated foods are smooth
single mounds, and thalis have regular angular boundaries. They do not yet
establish that generated appearance preserves every WED food identity. The 88
row human review queue is pending; until a reviewer completes it and the
task-validity restrictions are applied, the pilot is blocked from training or
scale-up. Detailed results and reproduction commands are in
`experiments/synthetic_food/pilot_report.md`.

## Pilot acceptance gates

- Exact class coverage: all 41 classes; each scene traces to eligible WED
  TRAIN only and carries source image/annotation hashes.
- Card pair: only `anchor.card` changes in config; image diffs stay within the
  projected card footprint; camera, food mask, component IDs, depth, 3D points,
  volume and mass match exactly.
- Renderer labels: masks align to RGB, component IDs map one-to-one to the
  geometry components, finite positive metric depth covers rendered pixels,
  volumes and masses are finite and nonnegative, and mass agrees with the
  stored density × volume convention within numerical integration tolerance.
- Marker: ID 7, DICT_4X4_50, 60 mm, finite in-frame projected corners, and
  planted pose/scale agree with renderer projection.
- Human appearance review: every class represented in the queue; identity,
  appearance and label alignment reviewed. Any rejected example has affected
  tasks disabled in the manifest.

Renderer-controlled agreement only tests internal consistency. It does not
prove food realism, real camera depth accuracy, or that a WED class has a
single true shape/density. Those remain limitations for later real-data
experiments.
