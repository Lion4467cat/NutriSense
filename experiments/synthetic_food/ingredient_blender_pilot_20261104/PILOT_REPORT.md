# Ingredient-level Blender pilot report

**Status: prepared for human review; no visual or physical-label approval is implied.**

## Scope

- Three WED classes: chicken dum biryani, bottle-gourd curry, and salad.
- Three isolated portion conditions per class, plus two TRAIN-observed composed meal types.
- 11 seeded scenes, each rendered with and without the deployed ID 7 / 60 mm marker: 22 RGB images total.
- Blender 5.2.3, Cycles CPU, 448 × 336, 12 samples. The local Blender device query exposed the Intel CPU only; RTX rendering remains unverified.
- Eligible WED TRAIN appearance summaries/crops guided the recipes. No DEV, LOCKED, ArUco evaluation or WED test images were used.

## What the pilot demonstrates

The new renderer has separate seeded ingredient geometry rather than a single class mound: rice kernels and browned pieces; gourd-like chunks, gravy, onion rings and herbs; cucumber slices, tomato, onion and herbs. Geometry Nodes scatter reusable ingredient meshes. Blender scene geometry drives semantic masks, ingredient-region IDs, camera-Z depth, evaluated mesh volume and camera/marker metadata.

All 11 present-card views detect DICT_4X4_50 marker ID 7. Projected-versus-detected marker corner error is 1.42–3.19 px. Automated checks report no geometry/label bundle errors, and each card/no-card pair has identical camera, seed, components, food masks and food depth. At 12 Cycles samples, a few low-amplitude pixels outside the card plus a 2 px halo can vary due to path-tracing/edge sampling; the audit records this tolerance explicitly.

The Blender data are reproducible and physically linked to the rendered mesh, but the mass field is `estimated_mass_g`: mesh volume multiplied by an assumed class-density prior. Its interval reflects configured density uncertainty. It is not measured mass or independent ground truth. Recipe ingredient identities and compositions remain hypotheses because WED does not provide ingredient-level labels.

## Visual comparison and limitations

The comparison sheet aligns eligible WED TRAIN crops, the previous renderer, the complete-food mesh preview and the new card/no-card renders. The procedural pilot improves visible ingredient separation over the previous generic renderer. It has not yet reached photorealistic food appearance:

- Biryani grains are individually visible, but the pile is uniformly distributed and chicken pieces are not reliably salient at review resolution.
- Bottle-gourd curry shows separate chunks and garnish, but the gravy and serving remain simplified and stylized.
- Salad components are identifiable as cucumber-like rounds and tomato pieces, but their regular spacing and smooth surfaces look artificial.
- Composed meals are cleanly separated on the plate, but still look like arranged procedural assets rather than natural meals.

The complete-food mesh preview can look more realistic for some classes, but earlier asset review found identity mismatch; visual polish alone does not establish the WED label. No reusable external meshes were included because the available MetaFood3D assets reviewed were CC BY-NC 4.0 and did not establish exact identity/scale for these recipes.

## Task-specific status

| Dimension | Status | Evidence and limitation |
|---|---|---|
| Class identity / food appearance | **REVIEW_REQUIRED** | Recipe class is assigned by the generator. No classifier or human review has approved identity. |
| Ingredient composition | **REVIEW_REQUIRED** | Ingredients are recipe hypotheses guided by WED TRAIN examples; WED does not label them individually. |
| Semantic and ingredient masks | **Automated PASS; human review pending** | Masks are ray-cast from exact rendered object IDs; visual boundary/food identity still needs review. |
| Metric depth | **Automated PASS; human review pending** | Camera-Z is ray-cast from the same Blender scene and uses metres. |
| Geometry and volume | **Automated PASS; human review pending** | Evaluated Blender meshes provide volume. Physical plausibility depends on recipe geometry and needs review. |
| Mass and density | **ASSUMPTION_ONLY** | Volume × uncertain class density. Not measured grams and not held-out truth. |
| Marker geometry and detection | **Automated PASS; human review pending** | 11/11 card views detect ID 7; projected corner error 1.42–3.19 px. |
| Card/no-card matching | **Automated PASS with low-level render tolerance** | Pair seed, camera, geometry, masks and food depth match. RGB differences are confined to the card footprint except for a small recorded path-trace/edge tolerance. |
| Overall visual approval | **PENDING** | Human review sheet remains unfilled. No image is approved for training. |

## Review artifacts

Generated artifacts are under the ignored processed-data directory so the pilot does not become source-controlled dataset content:

- `datasets/processed/synthetic_food_ingredient_blender_pilot_20261104/gallery.html` — paired RGB, masks and metadata for all 22 views.
- `datasets/processed/synthetic_food_ingredient_blender_pilot_20261104/comparison_contact_sheet.png` — TRAIN references and renderer comparisons for isolated portions.
- `datasets/processed/synthetic_food_ingredient_blender_pilot_20261104/composed_pairs.png` — both composed card/no-card pairs.
- `datasets/processed/synthetic_food_ingredient_blender_pilot_20261104/human_review.csv` — review decisions are pending; do not treat blanks as approval.
- `datasets/processed/synthetic_food_ingredient_blender_pilot_20261104/validation.json` — automated checks and tolerances.

## Decision

This pilot validates an automated ingredient-level Blender workflow and aligned physical labels under explicit assumptions. The remaining visual gap is material: the food still looks procedural and too regularly arranged. Keep this as a research preview only. Do not scale the corpus, train food classifiers on it, or start GAN/diffusion work until the human review accepts class identity/appearance and separately reviews label validity. If review rejects the appearance, next work should focus on less regular ingredient placement, improved food-surface materials and better class-specific reference conditioning, then produce a new small pilot.
