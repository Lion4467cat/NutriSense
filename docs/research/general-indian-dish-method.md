# General method: grams for ANY Indian dish, without the school dataset

- **Date:** 2026-10-29 · **Status:** proposed design, grounded in the 2026-10-29
  research sweep (sources at bottom) + the artifacts already in this repo.
- **Motivation:** the school capture dataset may never arrive (owner decision,
  2026-10-29). Meanwhile the learned head is **class-conditional on the 41 WED
  classes** (`models/weight_head.py`) — it structurally cannot serve an
  unseen dish — and the measured geometry tier (`models/portion_estimator.py`)
  needs device depth + a menu dish entry with densities. Two augmentation
  attempts (ledgers 001, 006) failed to fix plate-level session bias, which
  confirms that more jitter on 219 sessions is not the path. The design below
  makes the method **dish-name-free**: it estimates *ingredients*, and treats
  dish recipes as composition priors — which is exactly the "feed it recipes"
  direction, made concrete.

## 1. The one-line idea

Indian dishes decompose into a small universal **ingredient alphabet** (~40–60
cooked states: rice, dal/gravy, yogurt, flatbread, dry-veg, gravy-veg,
onion-tomato masala, ghee/oil, papad, salad, fruit, …). Nutrition5k measures
grams **per ingredient**; Indian recipe tables (INDB: 1,014 recipes) define
**shares and typical states** of those same ingredients. So:

1. Segment the plate into ingredient-level components (open-vocabulary).
2. Estimate **metric volume** per component (mask area × height above the
   fitted base plane).
3. Convert volume → grams with a **per-state density prior**, corrected by a
   learned ingredient regressor where supervision exists.
4. Sum → dish grams; match the composition against a recipe table to label
   the dish and fetch kcal/protein per 100 g.

The dish name is read LAST. A new Indian dish is a new mixture of known
ingredient states — no per-dish training data needed.

## 2. Why this is the right response to "no school dataset"

| constraint of the current method | consequence | how this design removes it |
|---|---|---|
| head emits one gram per WED class slot | unseen dish = unusable | estimates ingredient states, not dishes |
| head is RGB-only; anchor's cm/px (±0.3%) computed then discarded | scale-blind; whole plates slide (ledger 005: plate-σ 0.700 vs 0.131 iid) | volume path is inherently scale-metered; learned refinement fuses metric geometric features |
| device depth required for the measured tier | most user phone photos can't run it | monocular metric depth (shape from MoGe-2/UniDepthV2 + card scale) covers RGB-only captures |
| school dataset assumed for fine-tuning | blocked | supervision comes from measured non-Indian datasets with per-ingredient grams (Nutrition5k, CC BY 4.0 — already pulled); WED stays as the measured-Indian validation set |
| density per dish only exists for menu dishes | out_of_scope dishes | per-ingredient-state density priors (FAO/INFOODS density table v2, 638 foods, XLSX) + learned residual densities from measurement |

## 3. What the research actually established (honest reading)

- **Volume helps, in-distribution:** Nutrition5k's mass regressor went from
  MAE 40.4 g (18.8%) on RGB alone to **29.4 g (13.7%) when fed a depth-derived
  volume scalar** alongside RGB. Volume is the proven accuracy lever.
- **No paper proves volume×density for UNSEEN foods.** Nobody published a
  leave-food-type-out or leave-cuisine-out gram-MAE comparison of the
  geometric pipeline (closest: 3D-object-scaling at 14–17% error *with* a
  known 3D food model and a scene reference). So our validation protocol
  (§6) is a contribution, not a formality.
- **Monocular metric depth candidates, all open weights:**
  MoGe-2 ViT-L (MIT code, ~326M, **60 ms/image on A100/3090**, resolution
  flexible; predicts *shape separately from a global metric scale* — ideal,
  since our card already fixes true scale) · UniDepthV2 (CC BY-NC — eval/research
  only) · Depth Pro (Apple custom license — read terms before any serving use;
  best edge sharpness) · Metric3D v2 (BSD-2, but its metric recovery is
  focal-critical; our card is not a focal proxy). **Candidate #1: MoGe-2.**
- **Recipe/ingredient knowledge bases that are actually usable:**
  INDB (Indian Nutrient Databank, anuvaad.org.in): 1,014 Indian recipes,
  per-100 g + per-serving, downloadable Excel — recipe-level nutrition;
  underlying IFCT 2017 must be requested from NIN if we need the raw tables.
  IFCT 2017: free-access official PDF (528 key foods) but redistribution terms
  unclear — use, don't bundle. FAO/INFOODS Density Database v2: machine-readable
  densities (e.g. boiled rice 0.73 g/ml) — this is the open density prior'.
- **Recognition:** no trustworthy published zero-shot food numbers exist.
  SigLIP 2 (multilingual) zero-shot over a curated Indian name list
  (English + regional names + transliterations) is the cheap baseline;
  OVFoodSeg-style learned open-vocab ingredient segmentation (+4.9 mIoU on
  novel FoodSeg103 classes) is the upgrade path. Khana (131k images, 80 Indian
  dishes, non-commercial) = eval-only coverage testing.

## 4. The pipeline, mapped onto this repo's seams

```
photo → S1 anchor (exists, models/scale_anchor.py; card ±0.3% or prior)
      → S2 food mask + component masks (new: open-vocab ingredient seg)
      → S3 volume/mask: area_cm² × mean_h_mm above fitted base plane
             depth = device depth (exists | portion_estimator seam)
                     or MoGe-2 shape × card scale (new; no device depth)
             base plane = existing ring/table-prior fitter (geo/plane.py)
      → S4 grams = Σ_c volume_c × ρ(state_c)
             ρ from FAO/INFOODS + learned per-state residual (from Nutrition5k
             ingredient supervision); invisible components (oil, spices,
             salt dissolved in gravy) from recipe shares × gravy grams
      → S5 label: composition vector vs recipe table (INDB) → dish name,
             kcal/protein per 100 g; General-mode goal shares (exists)
      → uncertainty: per-component sigma_rel → existing MC engine (S4 seam);
             unknown-state components widen bands automatically
```

Two-tier accuracy philosophy: the geometric estimate is the **always-on
baseline** (works for every dish, every ingredient alphabet member); the
**learned ingredient-conditional head** (below) refines it *only where it has
supervision*, never blocking an unknown dish.

### 4a. The learned part: ingredient-conditional head (the Nutrition5k transfer)

Replace `head_mlp`'s 41 dish slots with **~50 ingredient-state slots**; the
same frozen-DINOv2 + ROI + MLP family (`tools/train_weight_head.py`,
feature-cache path — a full run drops from 70 min to minutes) trained on
Nutrition5k **per-ingredient grams** (already pulled locally: 4,768 + 238
dishes, ingredient rows). Two fusion options, gated by ledger experiments:

- **(F1) feature-fusion:** geometric channels (area_cm², mean_h_mm,
  cm/px interval, mask/plate fraction) concatenated with pooled ROI features
  before the MLP — finally *uses* the anchor signal the serving path computes.
- **(F2) residual-shrinkage:** head predicts a multiplicative correction to
  the geometric grams instead of the grams themselves —
  `grams = grams_geom × exp(head)`, bounded (exp clamp) so geometry remains
  the safety floor. This is the recommended first experiment: it cannot
  regress below the geometry baseline by construction.

Indian-side knowledge enters as **recipes**, not as training data: the recipe
table supplies composition shares (what fraction of a dal is water+aromatics),
typical densities per state, and the per-100 g nutrient composition (INDB) —
so grams are interpreted without any Indian measurement set.

## 5. Efficiency budget (all frozen models, one pass)

| stage | model | cost |
|---|---|---|
| anchor | existing ArUco detector | ms |
| depth (RGB-only) | MoGe-2 ViT-L @ ~840² | ~60 ms (A100/3090, fp16) |
| segmentation | SAM2-tiny / FoodSeg-based | ≤ 0.2 s target |
| features | DINOv2-S, one pass @ 224² | existing encode() cost |
| head | same tiny MLP (50 slots) | existing |
| total | | **< 1 s per capture on the 4060 box**, CPU-only mode possible with device depth |

Feature caching (ticket 01) applies to every training/eval loop, so iteration
stays in minutes like the ticket-01 promise.

## 6. Validation protocol (pre-registered style, before any code)

1. **Depth-shape harness (no new data):** reuse the existing DEV/capture
   frames that HAVE device depth — run MoGe-2 on the RGB, reconstruct,
   compare height-field above the fitted base plane against measured depth
   (mm-MAE on food pixels + final grams delta through the untouched
   measured tier). Gate: geometry-tier grams from monocular depth within
   a paired CI of the device-depth grams on those frames.
2. **Ingredient teacher:** train (F2) on Nutrition5k ingredient-level grams;
   in-domain teacher MAE reported honestly against the paper's 29.4 g/13.7%
   reference point; **leave-ingredient-out** split to prove
   ingredient transfer instead of memorisation.
3. **Indian validation with what exists:** WED's 21 DEV plates (deployable
   path, paired plate-bootstrap CIs — instruments from ledgers 005/006) as
   the measured-Indian check, vs. the 15.03 g DEV MAE incumbent baseline;
   NO LOCKED read.
4. **Recipe-composition check:** INDB per-100 g nutrient of the predicted
   dish vs a menu-dish standards entry where both exist (audit table, not a
   gate).
Every accuracy experiment runs as its own ledger entry with keep/revert
discipline, per repo rules.

## 7. Risks and designed mitigations

- **Glossy/semi-liquid surfaces trip monocular depth** → the F2 residual
  formulation bounds how far the head can push geometry; card-scale
  planarity and the ring base-fitter stay authoritative.
- **Mixed-gravy segmentation (you can't segment "onion" inside sambar)** →
  recipe shares distribute invisible components proportional to the visible
  carrier mass; uncertainty flag `composition_inferred`.
- **Particulate/flat foods (rice, papad, roti) aren't solid volumes** →
  state-aware volume definitions: papad/roti from count/diameter unit-weights
  (WED portion study: chapati portions tracked by count), rice from
  height × packed-area with bulk density (0.73 g/ml reference), never solid
  density.
- **IFCT/INDB redistribution terms are unclear** → use-with-citation posture
  like WED (`docs/licenses.md`); nothing bundled into the repo.
- **Depth-Pro / UniDepthV2 licenses** are restrictive/custom → MoGe-2 (MIT
  code; verify model-card terms before any commercial serving) is the
  default; the harness (6.1) decides empirically anyway.

## 8. Sequencing (→ ticket 07)

1. `07a` depth-shape harness + MoGe-2 candidate vs device depth on existing frames.
2. `07b` Nutrition5k ingredient-teacher run (F2 residual head, feature cache).
3. `07c` ingredient-state density table (FAO/INFOODS + learned residuals) +
   `out_of_scope`-dish demo path through the existing measured tier.
4. `07d` recipe table (INDB import + audit) wiring composition shares and
   nutrient lookup into S5.
5. `07e` General-mode serving integration + uncertainty routing; school
   records untouched (spec 002 decision 1).
Items 2–4 are independent; 1 gates nothing but is cheapest first evidence.

## Sources (accessed 2026-10-29)

- MoGe-2 paper https://arxiv.org/html/2507.02546v1 · repo
  https://github.com/microsoft/MoGe (timing/attention clarification issue 74;
  weight-license question issue 98)
- UniDepthV2 https://arxiv.org/html/2502.20110v2 ·
  https://github.com/lpiccinelli-eth/UniDepth (CC BY-NC 4.0)
- Depth Pro https://arxiv.org/html/2410.02073v2 ·
  https://github.com/apple-aiml-research/ml-depth-pro (Apple custom license)
- Metric3D v2 https://arxiv.org/html/2404.15506v4 ·
  https://github.com/yvanyin/metric3d (BSD-2, focal-critical)
- Nutrition5k https://arxiv.org/html/2103.03375v2 ·
  https://github.com/google-research-datasets/Nutrition5k (CC BY 4.0; 29.4 g
  mass MAE with volume feature; per-ingredient grams)
- DPF-Nutrition https://pmc.ncbi.nlm.nih.gov/articles/PMC10706621/ (10.6% mass
  MAE, trained fusion, in-distribution)
- 3D-object-scaling portion estimation https://arxiv.org/html/2404.12257v2
- MFP3D https://arxiv.org/html/2411.10492v2
- OVFoodSeg https://arxiv.org/html/2404.01409v1
- SigLIP 2 https://arxiv.org/html/2502.14786
- INDB https://www.anuvaad.org.in/indian-nutrient-databank/ ·
  https://github.com/lindsayjaacks/Indian-Nutrient-Databank-INDB-
- IFCT 2017 official PDF https://www.nin.res.in/ebooks/IFCT2017.pdf ·
  FAO entry https://www.fao.org/food-composition/tables-and-databases/detail/(country--date)-title-9/en
- FAO/INFOODS Density Database v2
  https://www.fao.org/food-composition/tables-and-databases/detail/(global--2012)-fao-infoods-density-database---version-2/en
- Indian Thali project (behind our WED baseline) https://github.com/yasharora102/Indian_Thali_ICVGIP2025
- Khana dataset (non-commercial) https://khana.omkarprabhu.in/ · https://arxiv.org/html/2509.06006v1
- Urban Indian portion-size study
  https://www.foodandnutritionjournal.org/volume8number1/assessment-of-portion-sizes-of-food-items-commonly-consumed-by-urban-indian-adults-a-preliminary-study/
- Fang et al. volume-comparison cautionary data
  https://pmc.ncbi.nlm.nih.gov/articles/PMC6226035/
