# Class-specific appearance pilot review

## Review state

This is a small renderer redesign pilot, **not approved for training or corpus scale-up**. Please inspect [the gallery](index.html) and record decisions in [human_review.csv](human_review.csv). The gallery keeps visual identity, photorealism, automated task checks, and physical-label checks in separate columns. All human appearance decisions remain `REVIEW_REQUIRED`.

The pilot contains six isolated dishes and one four-item thali, each rendered as an exact card/no-card pair (14 images total). Every generated image is accompanied by its eligible WED TRAIN reference crop and mask overlay. RGB, class mask, component mask, object mask, metric-depth visualization, and surface-height visualization are available from each scene card.

## Why the earlier pilot collapsed to similar mounds

The previous `analytic-heightfield-v2-pilot` assigned each isolated dish a radial function of the form `h(r) = h_max * (1 - (r/R)^n)`. Class selection changed a few values such as radius, fill factor, and coarse “flat/loose/moist” labels, but did not change the underlying radial surface. The composed meal used one radial surface split into angular sectors, which created wedge-like regions.

Appearance then came from one of seven broad material profiles. WED TRAIN statistics supplied median RGB and luminance spread, which only changed the base color and low-amplitude smooth noise. There were no rice grains, vegetable pieces, bread blisters, or class-specific ingredients. Finally, the simple directional-light shader and global blur further softened the few differences that did exist. The dominant causes were shared geometry and absent ingredient-scale detail; material profiles reinforced sameness; lighting and blur were secondary.

## Redesign

`nutrisense_synth/food_models.py` now defines an explicit recipe for every WED class and produces deterministic 1 mm height/albedo grids. The geometry is a height field, not a full volumetric mesh. Ingredient microgeometry remains inside its parent WED semantic region because WED has no ingredient-instance annotation.

| Shape/material family | WED classes |
|---|---|
| Curry with distinct chunks | Bottle-gourd-curry, aloo-curry, beans-curry, channa-brinjal, kofta-curry, mirchi-ka-salan, non-spicy-curry, rajma, sambar |
| Dry-cut pieces | aloo-capsicum, aloo-fry, beetroot-kobari, beetroot-poriyal, dondakaya-fry, kakarakaya-fry |
| Mixed grains and ingredients | bisi-bele-bath, chicken-dum-biryani, veg-dum-briyani, veg-pulao |
| Cooked rice grains | steamed-rice |
| Flat sheet / blistered crisp | phulka, papad |
| Distinct salad/fruit pieces | salad, Watermelon, Papaya, Banana, Muskmelon |
| Lentils, broths, pastes and dairy | boondi (small rounds), cabbage-dry (shreds), chutney, curd, leaf-dal, mango-pickle, masoor-dal, muddha-pappu, non-spicy-dal, pachi-pulusu, payasam, raita, rasam, tomato-pappu |

The final family contains some subclasses such as leafy dal and dairy with inclusions; their exact recipe palettes/details are defined per class in the registry rather than inferred from a generic profile. The recipe colors and ingredient forms are renderer assumptions. Eligible TRAIN pixels guide broad class tone only; source pixels are not copied into generated scenes. The pilot references and source hashes identify only eligible TRAIN groups, with the fixed DEV carve removed before image paths are opened.

## Physical label contract

Each class surface is numerically rescaled so its 1 mm-cell height integral equals `mass_g / density_g_ml` within raster discretization. The stored depth map is camera-Z in metres; the scene bundle stores camera intrinsics/pose, world-space points, object and component IDs, surface heights, class masks, component volume, mass, and density. Marker metadata includes projected and world-space corners, card center, in-plane angle, and normal for the ID 7 / 60 mm target. Renderer checks verify visible-mask alignment, finite positive depth, marker dimensions/geometry, and mass = volume × recorded density.

Density values are not presented as measured class truths. A direct cited reference is used where applicable; otherwise the pilot carries analogue/project-assumption provenance and its configured uncertainty range. The source TRAIN mass selects an observed portion size; it is not used as density or shape supervision. Model-predicted mass is not used.

Automated label checks do not establish that the pixels visually depict the assigned class. The gallery marks visual identity and photorealism pending independently of physical-label validity. Failure of any renderer geometry or pair check blocks the sample. Human review remains the gate.

## Pilot and validation

- Isolated classes: Bottle-gourd-curry, chicken-dum-biryani, papad, phulka, salad, steamed-rice.
- Composite: steamed-rice + Bottle-gourd-curry + papad + salad, with independent component TRAIN ancestry recorded.
- Card: exact deployed synthetic marker convention, DICT_4X4_50 ID 7 with 60 mm side. Card/no-card scenes share all scene settings; the card flag is the only config difference.
- Automated outcome: see [pilot_validation.json](../../../datasets/processed/synthetic_food_appearance_pilot_20261103/pilot_validation.json) and the manifest. The initial run caught and fixed component IDs that extended under occluders; the final run reports 14/14 automated image checks passing.
- Human outcome: pending. No generated sample is approved for supervised classification training or scale-up.

## Known limitations and open review questions

- This remains a procedural illustration renderer. It is not photorealistic and has no learned appearance model; visually realistic capture variation is unresolved.
- Food objects are height fields with procedural surface inclusions, not watertight volumetric meshes or scanned food. Surface microgeometry improves class cues but is not ingredient-instance ground truth.
- The thali is a compact renderer composition. Some class portions can still look too regular or too tall; compare its four regions with the WED references and mark specific artifacts.
- Lighting/background are still stylized and single-source. The pilot focuses first on class morphology and texture, not camera-realistic photography.
- Class-identity correctness must be judged from the WED reference beside the rendered sample. A valid class mask, depth map, or mass value is not visual evidence.
- Check portion plausibility independently from whether mass and volume labels are internally consistent.

## Reproduce

From repository root:

```bash
.venv/bin/python -m tools.generate_synthetic_appearance_pilot
.venv/bin/python -m tools.build_synthetic_appearance_review
```

The first command reads only `data/wed_manifest.jsonl` TRAIN records after removing the fixed DEV groups, uses `data/wed` TRAIN images/masks for references and palette statistics, and writes a separate pilot under `datasets/processed/synthetic_food_appearance_pilot_20261103/`. The second writes the local gallery/review CSV here. It does not access LOCKED, ArUco evaluation, or WED test images; does not generate the complete 41-class corpus; and does not train production models, GANs, or diffusion models.
