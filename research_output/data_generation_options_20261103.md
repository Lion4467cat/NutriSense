# Data-generation options for NutriSense

**Date:** 2026-11-03  
**Scope:** research only; no application, model, test, manifest, protected evaluation, or dataset files were changed.

## Executive conclusion

The highest-value data is not more visually elaborate synthetic food. It is:

1. label-preserving augmentation of existing real WED images and masks;
2. a small, deliberately designed, rights-cleared real capture set with measured net grams, plate groups, and (where possible) card/depth data;
3. unlabeled real-food representation/domain adaptation, with no invented gram targets; and
4. carefully audited real cut-paste/compositing for clutter, occlusion, and rare class combinations.

The current 88-image procedural pilot should not be promoted to production training: its masks/depth/component IDs are internally exact, but its shapes, appearance, shadows, vessels, and density assumptions are not measured real-food truth. Synthetic data can be useful for geometry, scale, controlled ablations, and coverage, but promotion must be decided on untouched real meal groups.

## Project facts that control the answer

The repository's integrated-pipeline documentation states that WED has 41 food classes, per-pixel semantic masks, and one measured net-food mass per class in a physical meal. It has no serving-instance IDs. Same-class connected components are therefore proposals, not serving labels; the learned weight head is evaluated at class-total granularity. Plate/bowl tare is not part of the WED target. The no-card route uses the DINOv2 weight head; the marker route uses ArUco-calibrated MoGe geometry; SigLIP is a meal/class diagnostic.

This means a valid transformed WED example must preserve:

- the semantic mask under the same image transform;
- the class-total target exactly if pixels are only moved/photometrically changed;
- source physical-group identity and split isolation;
- the distinction between measured class totals and any assumed per-instance or density labels.

It must **not** silently turn a connected island into an instance weight. If two same-class portions are pasted or split, the only defensible target is their summed class total unless new instance measurements exist.

## 1. Label-preserving augmentation on real WED

### Photometric transformations: first implementation

Apply synchronized, bounded transformations to RGB only: exposure/brightness, contrast, saturation, hue within a camera-plausible range, white balance, gamma, blur, JPEG/noise, sensor shadow/vignette, and small color-temperature changes. Keep masks unchanged and keep class-total grams unchanged. These target phone/device/lighting robustness and can improve classification, semantic segmentation, and the visual feature input to the weight head. They cannot create new mass evidence and should not be advertised as improving geometry or depth.

Use the real image distribution to set ranges. Extreme hue or texture changes can destroy food identity; blur can erase small classes; JPEG/noise can create mask-edge artifacts. Validate per-class IoU and weight MAE, not only training loss.

### Geometric transformations

Use horizontal/vertical flips only when the capture convention permits them; small rotations, translations, scale/crop, perspective, and mild lens distortion are more defensible for overhead plates. Transform RGB and semantic mask with identical parameters and nearest-neighbor mask interpolation. Grams remain unchanged because this is the same measured plate, not a rescaled physical serving.

Do not use arbitrary anisotropic scaling for a metric-depth or ArUco example. It changes physical geometry and marker dimensions unless the example is explicitly marked as RGB-only training data. Do not mix views from one physical plate across train and validation groups.

### Copy-paste, mosaic, and mixup

**Semantic copy-paste:** paste an annotated real class region into a real background, update the semantic mask, and retain a provenance record. For WED, the safest target is to use it for segmentation/classification only, or to carry the pasted donor's class-total grams as a *weak composite target* with a flag. It is not a measured total for the resulting meal because cut pixels can crop food, hide food, or duplicate the same measured serving.

**CutMix/mixup:** the canonical CutMix paper cuts and pastes image patches and mixes labels proportionally to patch area; mixup uses convex image/label combinations. These are credible regularizers for classification and representation learning, but area-proportional grams are not physically valid for food portions: mass is not proportional to visible pixel area, and a WED class-total can include hidden or merged food. Use them for classifier/encoder experiments, not as gram-supervision examples unless the loss is explicitly weak and the result is never treated as measured mass.

**Mosaic:** four-image tiling can increase scale/context variation and clutter for segmentation/classification. It creates artificial plate boundaries, inconsistent illumination and camera geometry. It is unsuitable for ArUco/MoGe/metric training and should be tested only as a low-probability RGB/mask augmentation for the semantic model.

The source evidence is task-specific: Copy-Paste reports gains for instance segmentation with randomly pasted objects; CutMix reports classifier/localization robustness; YOLOv4 reports Mosaic in an object-detection recipe. None establishes class-total gram correctness for WED.

## 2. Real-food cut-paste and compositing

There are three credible levels:

1. **Alpha composite with measured real masks.** Extract a food region from a real WED image, feather only the boundary, paste onto a real plate/background, and update the semantic mask. Keep donor class, source group, pixel provenance, crop fraction, occlusion ordering, and target policy. Use for segmentation/classification coverage.
2. **Geometry-aware composite.** Estimate a plate plane and place the donor in image coordinates with scale/pose constraints. Add a contact shadow and locally harmonize color/blur. This is better for occlusion and visual context but does not make the mass physically measured.
3. **Learned appearance refinement.** Use a mask/depth-conditioned translator to harmonize the composite, while retaining the original mask as the contract and rejecting samples where a frozen segmenter changes class pixels or adds/removes food.

Shadows should be generated as a separate layer tied to the pasted footprint and light direction; do not paint shadows into the food mask. Occlusion must be represented by an explicit front-to-back ordering. A pasted food fully hidden behind another food should be absent from the visible semantic mask but remain in a separate `hidden_components` ledger only if its mass is known. With WED, it is generally not known at instance level, so do not claim hidden-instance gram truth.

The main failure modes are halos, impossible contact shadows, repeated texture, pasted portions at the wrong scale, donor-background leakage, and target leakage from reusing one physical group's pixels across splits. Human review plus frozen-segmenter consistency is cheap insurance.

## 3. Conditional translation and diffusion

### What is suitable

Mask- or depth-conditioned generation is the only plausible generative route here. ControlNet demonstrates adding spatial controls such as segmentation and depth to a pretrained diffusion model. SDEdit demonstrates guided editing/compositing with a controllable realism/faithfulness tradeoff. Simulated+Unsupervised learning explicitly targets making simulator output more realistic while preserving simulator annotations through self-regularization and local adversarial losses.

For NutriSense, condition on a real plate/background plus a semantic mask, optional depth/plane, camera metadata, and class text. Prefer image-to-image refinement of a real composite over unconstrained text-to-image generation. Keep the original mask, depth, camera, and grams as the authoritative labels; generated RGB is an appearance hypothesis.

### Paired-data requirement and label risk

Unpaired image translation can learn a domain appearance mapping, but it does not guarantee spatial label preservation or mass preservation. Paired real RGB/mask/depth examples are needed to measure fidelity; paired before/after images are not required for every diffusion architecture, but a small paired validation set is required to detect label drift. A generated image can hallucinate garnish, remove thin structures, change occlusion, or alter apparent portion size while leaving the conditioning mask unchanged.

Therefore use generated images first for classifier/encoder and possibly segmentation robustness, with a frozen-segmenter agreement gate. Do not use them as gram targets, depth ground truth, or evidence that the renderer's density/shape assumptions are true. Do not train a conditional generator until the real augmentation and measured-capture baselines have been beaten.

## 4. Synthetic-to-real and domain adaptation

Domain randomization has credible robotics evidence: Tobin et al. transferred a detector trained on randomized non-realistic textures to real robotic scenes and reported robustness to distractors and partial occlusion. Shrivastava et al. used unlabeled real images to refine simulated images while preserving annotations. These are evidence that randomization or appearance adaptation can work when the task-relevant support is covered, not evidence that any synthetic food renderer will transfer.

For this project, randomize nuisance variables that can be specified honestly: camera exposure/white balance, blur/noise, background/tableware, viewpoint, partial occlusion, shadow direction, plate geometry, card placement, and limited food morphology. Keep a real-data anchor in every training mixture. The current renderer's regular mounds and assumption-tagged densities are weak priors for food shape and mass; randomizing them more widely may improve robustness but can also create a larger, still-wrong distribution.

Domain adaptation options, ordered by risk:

- self-supervised pretraining or feature alignment on unlabeled real food photos;
- supervised fine-tuning on a small measured real set, optionally initialized with synthetic geometry;
- mask-conditioned appearance refinement with strict label-consistency checks;
- adversarial feature/image adaptation, only after monitoring negative transfer by class and device.

Failure modes include simulator bias, class-prior shift, style overfitting, pseudo-label confirmation bias, and adaptation that improves WED but harms real phone meals. Report source-only, real-only, mixed, and adapted controls.

## 5. Additional portion data and constraints

### Existing measured option: Nutrition5k

The official Nutrition5k repository describes about 5,006 plates, four rotating side-angle videos, overhead RGB-D when available, ingredient lists, per-ingredient mass, total dish mass, and official dish-level train/test splits. Raw depth is 16-bit with stated units and a 0.4 m maximum. It is released under CC BY 4.0. It is valuable for representation, RGB-D geometry, and portion regression, but it is cafeteria data from a few California sites, not WED's cuisine/class/device distribution. Its ingredient vocabulary does not automatically map to the 41 WED classes. Tare and the exact net-food weighing protocol must be verified before using its masses as WED-compatible targets.

### Classification-only option: Food-101

The official ETH page describes 101,000 images across 101 categories, with 750 training and 250 manually reviewed test images per class; training images intentionally retain noise. It is useful for food appearance pretraining or SigLIP/DINO adaptation, not semantic masks, portion grams, depth, tare, or WED class-total supervision. License and redistribution terms must be checked before incorporation into a product artifact.

### Best project-specific collection

Collect new data under a written protocol: the same or deliberately varied phone/device set; WED-compatible 41-class mapping; plate/bowl tare; net food mass after serving; class totals; optional ingredient and recipe metadata; physical group ID; overhead and oblique views; card dimensions/pose; depth if available; and an explicit record of hidden/removed food. Add instance IDs only if each serving is separately weighed or portioned by a known allocation. Otherwise retain semantic masks and class-total labels.

The new set must have held-out physical plates, cuisines, devices, lighting, and portion ranges. A second scale or repeated weighing is useful for measurement error. Keep source licenses, consent, deletion policy, and model-use rights with every record.

## 6. Unlabeled real food photos

Use unlabeled real photos for DINOv2/SigLIP-compatible representation learning, BYOL/SimCLR-style multi-view invariance, test-time photometric robustness analysis, and domain-adaptive feature alignment. DINO reports useful semantic information in self-supervised ViT features; BYOL and SimCLR show that agreement between augmented views can learn transferable representations without labels.

Recommended augmentations preserve food identity and approximate viewpoint/lighting changes. Do not use strong crops that remove the only evidence for a small class when training a class-total predictor. Pseudo-label masks from DeepLabV3 or a stronger teacher can be used as confidence-weighted segmentation regularization, but pseudo-labels must be marked assumed, filtered by agreement/uncertainty, and never converted into gram ground truth. Unlabeled data can improve classification, representation, and perhaps segmentation robustness; it cannot identify absolute grams or calibrate MoGe scale without measured anchors.

## 7. Ranked recommendation for NutriSense

### Rank 1: real-image augmentation and an evaluation harness

Implement synchronized photometric/geometric augmentation first, then a small semantic copy-paste ablation. Keep real WED class totals unchanged only for same-plate transforms. For composites, use `target_kind=measured_class_total`, `weak_composite`, or `none`; never silently use `instance_weight`.

Expected benefit: classification high, segmentation medium/high, class-total weight low/indirect, geometry/depth none, end-to-end coverage medium. Labels are measured only for unchanged examples; composite labels are partly assumed.

### Rank 2: collect a small measured real capture expansion

Prioritize underrepresented classes, mixed meals, small portions, occlusion, bowls, non-overhead views, additional devices, and cuisine variation. Match the current physical-group split discipline. This is the first intervention likely to improve absolute grams and end-to-end meal coverage because it supplies the missing relationship between real appearance and measured mass.

Expected benefit: classification medium, segmentation high, class-total weight high, geometry/depth high when card/depth are recorded, end-to-end high. Labels are measured at class-total level; instance weights require a new protocol.

### Rank 3: unlabeled-real representation adaptation

Continue to use DINOv2/SigLIP-compatible encoders and compare frozen versus adapted features. Keep the weight head's class-total objective and calibrate residuals on measured DEV groups.

Expected benefit: classification medium/high, segmentation medium, class-total weight medium, geometry/depth low unless depth data is included, end-to-end medium. Labels are unlabeled or assumed except for the held-out measured evaluation.

### Rank 4: audited real cut-paste and conditional appearance refinement

Use this to target occlusion and rare combinations after Rank 1. A diffusion/refinement experiment must preserve masks/depth/metadata, measure frozen-segmenter agreement, and be sampled into the real validation mixture rather than replacing real data.

Expected benefit: classification medium, segmentation medium if agreement holds, class-total weight uncertain/low, geometry/depth none unless conditioning is independently validated, end-to-end uncertain. RGB appearance is generated; all physical labels remain assumed unless inherited unchanged from a measured source.

### Rank 5: renderer/domain-randomization expansion

Keep the renderer for analytic geometry, marker/card tests, controlled occlusion, and ablations. Expand only with explicit source/assumption tags and real-data promotion gates. The 88-image pilot's visual rejection is a reason to improve coverage and provenance, not to chase photorealism as the objective.

Expected benefit: classification low/uncertain, segmentation medium for geometry/occlusion edge cases, class-total weight low unless real mass pairs are mixed, geometry/depth high only for renderer-internal correctness, end-to-end unproven.

### Do not do first

Do not train on the current procedural pilot as if its density, shape, instance, or appearance labels were measured. Do not use pixel-area scaling as WED gram truth. Do not split views of one plate across train and validation. Do not use Nutrition5k or Food-101 without license and label/domain mapping review. Do not promote synthetic-only improvements or renderer-only MoGe/geometry scores as real-meal readiness.

## Data contracts required before scaling

Every example should carry: `source_kind` (`wed_measured`, `new_measured`, `unlabeled_real`, `composite`, `renderer`); `physical_group_id`; split; image/mask/depth/card hashes; class map; `mass_by_class_g`; `mass_semantics` (`net_food_class_total`, `ingredient_total`, `unknown`); tare policy; mask semantics; optional instance IDs; provenance for every pasted region; camera/device metadata; and `label_status` (`measured`, `weak`, `assumed`).

For renderer output also require density source/status, analytic geometry, component IDs, marker pose, camera intrinsics, and a statement that these are renderer labels. A composite must record whether its target is used for classification only, segmentation only, or weak regression.

## Promotion gates and experiment matrix

All candidate changes should be compared on the same frozen real DEV physical groups, with LOCKED remaining untouched. Report pixel mIoU/class IoU, class-set coverage, class-total MAE and bias, meal-total MAE, 90% interval coverage/width, abstentions, device/cuisine/portion slices, and latency. Bootstrap by physical plate, not image view.

| Experiment | Added data | Train target | Primary gate | Secondary gate |
| --- | --- | --- | --- | --- |
| A | Real photometric/geometric views | measured mask + same class totals | no regression in class-total MAE; improved robustness slices | mIoU, calibration |
| B | Real semantic copy-paste | mask; classification-only or weak composite grams | mIoU/class-set coverage on real meals | class-total MAE must not worsen |
| C | New weighed real plates | measured class totals, masks, optional card/depth | grouped real class-total and meal MAE | device/cuisine generalization |
| D | Unlabeled real photos | representation consistency/pseudo-mask confidence only | real DEV classification/segmentation improvement | no pseudo-label-induced class collapse |
| E | Mask/depth-conditioned refinement | authoritative real masks/depth; generated RGB | frozen-segmenter agreement plus real-meal gain | artifact/hallucination review |
| F | Renderer/domain randomization | renderer labels tagged assumed | only promote if mixed training improves real DEV | renderer geometry remains separate |

Promotion requires a preregistered primary metric, a fixed physical-group split, per-class and worst-slice checks, a human review sample for composites/generation, and no degradation beyond an agreed tolerance on the existing real baseline. Synthetic results may justify the next experiment; they cannot establish production readiness alone.

## Sources and concise evidence

1. **CutMix: Regularization Strategy to Train Strong Classifiers with Localizable Features** - https://arxiv.org/abs/1905.04899. Cut-and-paste patches with area-proportional mixed labels; reports classifier/localization and corruption robustness, not food mass validity.
2. **mixup: Beyond Empirical Risk Minimization** - https://arxiv.org/abs/1710.09412. Convex combinations of images and labels improve generalization and reduce memorization; labels are not physical portion measurements.
3. **Simple Copy-Paste is a Strong Data Augmentation Method for Instance Segmentation** - https://arxiv.org/abs/2012.07177. Randomly pasted objects improve COCO/LVIS instance segmentation and combine with pseudo-labeling; it assumes object/instance masks, which WED lacks.
4. **YOLOv4: Optimal Speed and Accuracy of Object Detection** - https://arxiv.org/abs/2004.10934. Reports Mosaic among an object-detection recipe; it does not validate metric geometry or mass labels.
5. **Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World** - https://arxiv.org/abs/1703.06907. Randomized non-realistic textures transferred a detector to real robotic scenes with distractors/partial occlusion; transfer is task and coverage dependent.
6. **Learning from Simulated and Unsupervised Images through Adversarial Training** - https://arxiv.org/abs/1612.07828. Uses unlabeled real images to refine simulated outputs while preserving simulator annotations; relevant precedent for annotation-preserving appearance adaptation.
7. **SDEdit: Guided Image Synthesis and Editing with Stochastic Differential Equations** - https://arxiv.org/abs/2108.01073. Guided diffusion editing supports compositing and exposes a realism/faithfulness tradeoff; it does not guarantee food mask or gram preservation.
8. **Adding Conditional Control to Text-to-Image Diffusion Models** - https://arxiv.org/abs/2302.05543. ControlNet adds segmentation/depth/edge spatial controls to pretrained diffusion backbones and reports robustness with relatively small training sets; generated pixels still need task-specific label checks.
9. **Bootstrap Your Own Latent: A New Approach to Self-Supervised Learning** - https://arxiv.org/abs/2006.07733. Learns representations by predicting the target representation of another augmented view without negative pairs; no gram supervision.
10. **A Simple Framework for Contrastive Learning of Visual Representations** - https://arxiv.org/abs/2002.05709. Shows augmentation composition is critical and learns transferable features with unlabeled images; augmentation must respect food identity here.
11. **Emerging Properties in Self-Supervised Vision Transformers** - https://arxiv.org/abs/2104.14294. DINO self-distillation produces transferable ViT features and reports emergent semantic segmentation information; it does not create physical labels.
12. **Food-101 - Mining Discriminative Components with Random Forests** - https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/. Official dataset page: 101 categories and 101,000 images, with deliberately noisy training images and reviewed test images; classification-only and domain-mismatched for WED grams/masks.
13. **Nutrition5k: Towards Automatic Nutritional Understanding of Generic Food** - https://github.com/google-research-datasets/Nutrition5k and https://arxiv.org/abs/2103.03375. Official repository documents about 5,006 plates, RGB-D, multiple views, ingredient masses, total mass, splits, California cafeteria bias, and CC BY 4.0 licensing.
14. **FAO/INFOODS Density Database v2** - https://www.fao.org/infoods/infoods/tables-and-databases/faoinfoods-databases/en/ and https://www.fao.org/fileadmin/templates/food_composition/documents/density_DB_v2_0_01.pdf. Official density resource for volume-to-weight conversion; it is reference/analogue evidence, not proof of the exact served WED class density.

These sources support method feasibility and failure modes. They do not substitute for a new NutriSense real-meal evaluation, and none changes the WED fact that gram labels are class totals rather than instance weights.