# Renderer-only synthetic pilot — 2026-11-03

## Decision

The automated geometry and pair checks pass, but **the pilot is not approved
for training or corpus scale-up**. Human appearance/label review is pending.
Visual spot checks show recognizable renderer structure but still highly
stylized food: isolated portions look like smooth single mounds, and composed
thalis use angular sectors with unnaturally clean boundaries. The pilot is
useful for validating labels and pairing, not as evidence of photorealism or
training utility.

## Frozen real-data reference

`baseline_freeze.json` pins 21 files covering the classifier gallery/model
revision, frozen DeepLabV3 checkpoint, frozen weight-head checkpoint, weight
uncertainty configuration, integrated pipeline modules, and the DEV/renderer
reports. Generation and audit commands verify every listed SHA-256 before
running. The frozen segmentation checkpoint digest is
`946a8adc50b131465da421c14caee19f03e4471ed883c8d77bdce119cb0ae963`.

The reference remains the completed integrated WED DEV report. Its primary
limits are retained: the independent SigLIP crop/gallery diagnostic has DEV
source overlap; renderer depth/geometry scores are not real-camera evidence;
weight intervals cover 81.5% at a nominal 90% level. The classifier gallery,
DeepLabV3 checkpoint, weight head, and pipeline configuration were not changed
by pilot generation.

## Renderer changes in this pilot

- Added TRAIN-only class appearance profiles from eligible WED TRAIN image
  pixels inside WED semantic masks: median RGB, between-group RGB quantiles,
  luminance IQR and source hashes. At most eight distinct eligible physical
  groups contribute per class. Source pixels are not copied into the outputs.
- Added coarse shape archetypes: flat sheet/disc, loose pile, cut-piece/loose
  cluster, and moist/compact mound. Portion size, footprint and fill factor
  vary deterministically by seed. Each remains an analytic radial height
  field; these are documented assumptions, not recovered 3D food shapes.
- Reworked thali geometry from small overlapping circles to volume-proportional
  angular regions on a shared plate mound. This eliminated above-camera food
  surfaces and invalid negative depth. Sector boundaries are artificial and
  should not be treated as realistic serving geometry.
- Saved image-aligned class/object/component masks, camera-Z depth in metres,
  surface height and world XYZ in millimetres, camera intrinsics/extrinsics,
  per-component volume/mass/density, and marker pose/dimensions.
- Strengthened renderer checks for positive depth, mask/object/component
  consistency, all component regions present, mass = volume × density, marker
  bounds, and card-pair invariants.

Density labels retain the configured class prior, source/status, evidence
rows, assumption range and a deterministic sampled density. The FAO/INFOODS
database provides direct values for some food states, analogues for others,
and no match for several classes. The current project interval is **not** a
published confidence interval: it uses configured uncertainty (generally
±20%, with the project fallback wider). Steamed rice uses the two cited boiled
rice values, 0.73–0.75 g/ml. Analogue and unmatched foods remain explicitly
assumed. See `data/ingredient_densities.yaml` and the [official FAO/INFOODS
density database](https://www.fao.org/infoods/infoods/tables-and-databases/faoinfoods-databases/en/).

## Pilot contents and automated results

| Measure | Result |
| --- | ---: |
| Eligible WED TRAIN groups | 198 |
| Food classes covered | 41 / 41 |
| Isolated class scenes | 41 |
| Composed thali scenes | 3 |
| Card/no-card scene pairs | 44 |
| Rendered images | 88 (44 card, 44 no-card) |
| Stored, hashed artifact files | 616 |
| Automated scene checks | 88 / 88 pass |
| Card-pair invariant checks | 44 / 44 pass |
| Stratified human review items | 88, pending |
| Production training / GAN / diffusion | None |

The class portion for each isolated pilot example is the middle ordered
WED-TRAIN portion record for that class, selected from distinct physical
groups. The summary records the observed TRAIN range and group support. It is
one central example per class, not a representative sample of the complete
portion distribution. The three thalis use eligible TRAIN meal groups with
11–12 labeled food classes (net food mass only; no plate/bowl tare).

Each card pair shares seed, food appearance, camera, lighting, masks, geometry,
volume, density and mass. Validation confirms only `anchor.card` changes in
configuration, RGB differences stay inside the projected card area, and depth
and 3D points match outside the card footprint. Each marker is rendered as
DICT_4X4_50 ID 7 with 60 mm side and projected pose labels. The renderer still
uses the legacy A6 synthetic card layout; its paper artwork/placement is not
validated against the field A4 PDF.

## Review artifacts

- Pilot manifest and all derived image/label bundles:
  `datasets/processed/synthetic_food_pilot_20261103/` (local-only, git-ignored).
- Contact sheet:
  `datasets/processed/synthetic_food_pilot_20261103/contact_sheet.png`.
- Per-class source/proportion/density summary:
  `datasets/processed/synthetic_food_pilot_20261103/pilot_summary.json`.
- Automated integrity and pair report:
  `datasets/processed/synthetic_food_pilot_20261103/pilot_validation.json`.
- Stratified review queue:
  `datasets/processed/synthetic_food_pilot_20261103/human_review.csv`.

The review sheet has one entry per image and asks a reviewer to mark identity,
mask/geometry alignment, marker correctness where present, appearance
plausibility, task restrictions and notes. A rejected appearance must disable
classification for that sample; a geometry/mask issue must disable
segmentation, depth and mass as appropriate. A successful automated report
alone does not accept the visual labels.

## Limitations and next gate

1. The images are procedural renders with low-frequency noise, not realistic
   food photographs. WED conditioning currently transfers color/texture
   statistics, not ingredient-level appearance or image texture.
2. Radial mounds and sector thalis remain coarse priors; flatbreads, fruit
   chunks, granular rice, liquids and mixed dishes need different physical
   surfaces and occlusion behavior.
3. Density evidence does not cover every exact WED dish. Most classes use an
   analogue or explicit project assumption with broad assumed uncertainty.
4. The renderer models an ideal pinhole camera and simplified vessel/card,
   material, lighting and noise. There are no measured real depth/shape labels
   for these scenes beyond their own analytic construction.
5. A human must inspect the 88 stratified entries, complete
   `human_review.csv`, and apply task-validity restrictions. The pilot must
   pass that review before any dataset scaling. GAN/diffusion research and
   production-model training remain out of scope until that gate is reviewed.

## Reproduction

```bash
.venv/bin/python tools/freeze_synthetic_baseline.py
.venv/bin/python tools/generate_synthetic_pilot.py \
  --output datasets/processed/synthetic_food_pilot_20261103 \
  --seed 20261103 --width 640 --height 480
.venv/bin/python tools/audit_synthetic_pilot.py
.venv/bin/pytest -q tests/test_synth_scene.py tests/test_synth_quality.py \
  tests/test_synth_thali.py tests/test_synth_corpus.py tests/test_synth_manifest.py
```

The three dataset commands never access LOCKED, ArUco evaluation or WED test
images. The pilot loader reads only TRAIN manifest rows and then excludes the
fixed seed-42 DEV physical groups before opening any WED image or mask.
