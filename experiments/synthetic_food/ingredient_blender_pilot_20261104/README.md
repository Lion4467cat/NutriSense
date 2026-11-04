# Ingredient-level Blender appearance pilot

The pilot creates three reusable procedural recipes using Blender's Python API:

- Chicken dum biryani: seeded rice-grain instances, three class-conditioned grain materials and irregular browned chicken-like pieces.
- Bottle-gourd curry: an irregular gravy surface, separate cooked gourd pieces, onion rings and herb leaves; the curry is served in a modelled bowl.
- Salad: cucumber cross-sections with seed detail, tomato slices, onion rings and herb leaves.

Geometry Nodes instance the ingredient objects at seeded positions, rotations and scales. Shader Nodes add ingredient-specific colour and roughness variation, procedural surface noise and bump. The scenes use soft window-like lighting, controlled camera/light seed variation and paired card/no-card captures. The card is built from exact 10 mm modules on an 85 mm board, giving a physical 60 mm DICT_4X4_50 ID 7 marker.

## Source and license review

The WED TRAIN-only appearance profiles and stored reference crops guide the three recipes. The current WED annotations do not label ingredient identities or ingredient masks; ingredient composition is therefore a documented recipe hypothesis informed by class names and visual reading of the saved TRAIN crops. No pixel transfer or AI image transformation is used.

The previous local asset audit found MetaFood3D categories such as `Rice`, `Chicken_breast`, `Cucumber`, `Tomato`/`Tomato_slice`, and `Onion`, along with broad cooked-food categories. These source assets are under CC BY-NC 4.0. They are not imported into this pilot because of the noncommercial restriction and unresolved exact identity/scale/mask labels; `Chicken_breast` is not the same as chicken dum biryani, and a tomato/cucumber mesh does not document the WED salad recipe. No external food assets were incorporated. The procedural ingredient meshes in `build_ingredient_pilot.py` are project-authored; Blender-generated files remain subject to the independent source-data, package and reference-image terms.

## Pilot scope and safeguards

- 9 isolated views: three WED TRAIN-supported portion quantiles per class (q20, q50, q80).
- 2 composed meals: biryani + salad and curry + salad, pairings observed in eligible WED TRAIN meal groups.
- Every scene has a card-present/card-absent pair, for 11 scene pairs / 22 RGB images.
- Each image stores class masks, ingredient instance IDs, camera-Z depth in metres, camera intrinsics/extrinsics, 3D recipe geometry/volume, marker pose metadata and density provenance.
- No WED DEV, LOCKED, ArUco evaluation or WED test images are opened by the scripts.
- No production model training, GAN/diffusion, full 41-class generation or corpus scale-up.
- Human appearance and label approval remain pending. The scripts never automatically approve samples.
- The current visual result is still stylized: rice piles are regular, curry surfaces are simplified, and salad slices are too smooth/regular for training approval. See `PILOT_REPORT.md`; this pilot is a workflow feasibility result, not an approved training corpus.

### Physical-label interpretation

The saved 3D component volume is evaluated from the Blender mesh geometry. The mass field is named `estimated_mass_g` and is volume times a class density prior from project configuration. The density values are assumed, not measured on these scenes; the interval is propagated from the configured density uncertainty. The q20/q50/q80 WED TRAIN grams condition portion size, so generated mass estimates are not independent held-out ground truth and must not be used as measured-label validation. They describe the constructed geometry under an explicit density assumption only.

## Output paths

Generated content is local under the ignored path `datasets/processed/synthetic_food_ingredient_blender_pilot_20261104/`.

- `manifest.json`: output index and review state.
- `validation.json`: automated mask, depth, volume/mass-provenance and pair checks.
- `experiments/synthetic_food/ingredient_blender_pilot_20261104/PILOT_REPORT.md`: visual findings, automated checks and the explicit review gate.
- `human_review.csv`: review sheet with human decisions left pending.
- `gallery.html`, `comparison_contact_sheet.png`, `composed_pairs.png`: visual review artifacts.
- `scenes/`: RGB, semantic food masks, ingredient instance IDs, card masks, camera-Z depth maps and scene metadata per image.
- `blend_templates/`: reusable `.blend` scenes for each class and the two composed examples.

## Reproduction

Blender 5.2.3 LTS was found locally. Cycles device enumeration exposed only `Intel Core i7-14700HX` CPU; HIP initialization failed and no RTX device appeared. The pilot was therefore rendered on CPU with 12 Cycles samples at 448×336. GPU support for the RTX 4060 remains unverified; do not switch to it until device enumeration succeeds in a normal Blender session.

```bash
.venv/bin/python experiments/synthetic_food/ingredient_blender_pilot_20261104/prepare_inputs.py
ALSOFT_DRIVERS=null blender --background --threads 8 \
  --python experiments/synthetic_food/ingredient_blender_pilot_20261104/build_ingredient_pilot.py
.venv/bin/python experiments/synthetic_food/ingredient_blender_pilot_20261104/audit_and_build_review.py
```
