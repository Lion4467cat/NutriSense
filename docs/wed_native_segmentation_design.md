# WED-native food segmentation baseline

Status: annotation audit and design recorded before model implementation or training. No synthetic images, LOCKED images, or ArUco evaluation images are used.

## Annotation audit

The audit reads only WED manifest rows marked `train`, then reproduces the existing seed-42, 10% physical-group DEV carve from those TRAIN groups. It does not deserialize the manifest's separate WED test rows or inspect their files.

| Partition | Views | Physical meal groups |
| --- | ---: | ---: |
| Eligible model TRAIN | 1,038 | 198 |
| Existing DEV carve | 108 | 21 |

Each image view has a corresponding single-channel `uint8` `gtFine_labelIds.png` raster, 1,365 × 1,024 in the audited files. Pixel values use the WED `index_map.json`: `0` is background and `1..41` map directly to the 41 food class names. All 41 food IDs occur in both eligible TRAIN and DEV masks. A view contains 8–14 distinct food class IDs (median 11; mean about 11.3 on DEV). The per-view manifest also provides dish names and measured meal-level net grams; these values are not needed as segmentation targets.

### What the masks supervise

- **Semantic segmentation is directly supported.** Every annotated food pixel has a class ID, so the target is a dense 42-way label map: background plus the 41 WED classes. Multiple foods on the same plate are represented as different class IDs in the same raster.
- **Instance segmentation is not directly supported.** The raster contains class IDs, not per-object/serving IDs, polygons, boxes, or panoptic IDs. Two separate servings of the same class therefore share the same pixel value. Connected components can be derived from a class mask as a reproducible region-evaluation convention, but they are not guaranteed to be annotated physical instances: touching same-class servings merge, while annotation gaps can split one serving.
- The masks are mutually exclusive per pixel. The annotation does not express overlapping food layers or a visible-vs-occluded decomposition.

### Multiple-component audit

Counting 8-connected components separately within each class mask finds more components than class-present views for many classes across the 1,146 rows marked TRAIN (including the existing DEV carve); for example, phulka has 1,138 components across 891 class-present views, and steamed rice has 2,070 across 1,142 views. This confirms that same-class disconnected regions occur, but does not convert them into authoritative instance IDs. Region metrics below call them **semantic connected regions** and explicitly retain this limitation.

## Architecture selected for the first supervised baseline

Use a 42-channel semantic segmentation network: a ResNet-50 encoder initialized from ImageNet weights, a DeepLabV3 atrous-pyramid decoder, and a replacement 1×1 classifier head producing background plus exactly 41 WED logits. Train the encoder and decoder end to end. The model predicts class identity and food-region pixels jointly; it does not create generic object proposals and then guess a class for each proposal.

This matches the supervision because WED supplies dense, mutually exclusive class pixels for every food region. The existing SAM2 prompt path predicts class-agnostic masks, which cannot learn the WED class boundaries from its output alone. A semantic model can be scored directly against the provided raster and its class IDs. Connected components of each predicted class map provide candidate meal regions after inference; they are a derived grouping step, not a claim of instance supervision.

Training will use only the 1,038 eligible TRAIN views. A deterministic, group-held-out subset of those eligible TRAIN physical groups will be used for early stopping and model selection; the 108-view DEV carve will remain untouched until the selected checkpoint and inference thresholds are fixed. Data augmentations must apply identical spatial transforms to image and label map; image-only color/brightness variation is allowed. Class imbalance will be addressed through a documented, capped frequency-based pixel loss weighting plus a foreground overlap term. Input resize, seed, group split, class weights, optimizer, schedule, early stopping rule, checkpoint hash, and package/model revisions must be recorded in the run report.

## Evaluation contract

Evaluate the selected checkpoint on the fixed 108-view DEV carve and compare against the saved 25-point SAM2 candidate on the same views. Neither method may use DEV to fit weights, thresholds, or class mappings.

Report:

1. Per-class pixel precision, recall, IoU, and Dice; macro foreground mIoU and aggregate foreground union IoU/Dice.
2. Semantic connected-region precision/recall/F1 using class-consistent one-to-one maximum-IoU matching at IoU ≥ 0.5. Also report unmatched predictions that overlap a GT region as duplicate fragments, unmatched non-overlapping predictions as spurious regions, and unmatched GT regions as missed semantic components.
3. Complete-meal class-set accuracy and complete semantic-region recovery, defined separately. Exact component recovery is only a proxy because WED does not provide instance IDs.
4. Group-bootstrap 95% confidence intervals over the 21 physical meal groups.
5. Side-by-side image, WED semantic ground truth, model prediction, and SAM2 comparison panels for representative DEV multi-item meals, chosen by a fixed rule covering low, median, and high food-class counts. Visualization colors must be keyed to the WED class IDs.

For a fair SAM2 comparison, retain the prior candidate's class-agnostic proposal metrics (foreground union and semantic-region overlap/recall) on exactly the same DEV views. Do not report SAM2 per-class pixel precision or exact class-set accuracy unless its proposals are assigned classes using the same separately frozen classifier; the saved SAM2 masks themselves are unlabelled. The baseline runner should make this difference explicit instead of implying the methods have equivalent outputs.

This deliverable is a detection/segmentation baseline only. It does not change depth, geometry, portions, or meal-weight code, and it makes no instance-segmentation or mass-estimation claim.

## Initial trained baseline results

Implementation followed the design above. The model is torchvision DeepLabV3 with a ResNet-50 ImageNet V2 backbone and 42 semantic logits. It trained for 20 epochs on 1,038 eligible WED TRAIN views (198 groups), with 10% of those groups held out internally for early stopping. The selected checkpoint is epoch 19, internal validation macro food IoU 0.8358. The fixed 108-view DEV carve remained out of training and checkpoint selection.

On DEV, macro food IoU is **0.8211**, macro food Dice **0.8976**, foreground union IoU **0.9196** (group-bootstrap 95% CI **0.9088–0.9245**), and foreground union Dice **0.9581**. The macro mean covers 38 classes present on DEV; three WED classes have no DEV examples. Per-class precision, recall, IoU, Dice, present-view counts, and IoU intervals are in the report.

Using 8-connected class-specific regions as the declared semantic-region proxy, class-aware region precision / recall / F1 are **0.7367 / 0.7353 / 0.7360**; exact class-set detection is **76/108 meals (70.4%)**. Strict exact semantic-region recovery is 0/108, with 424 unmatched GT regions. Under the common class-agnostic comparison, the WED model gets region F1 **0.7541** (95% CI **0.7368–0.7910**) against SAM2's **0.2077** (95% CI **0.1825–0.2331**); WED regions have 395 misses, while SAM2 has 1,282. Counts of duplicate-overlapping and spurious proposals are broken out in the report. Region recovery remains imperfect and component topology is only derived from semantic labels.

Full reproducibility metadata, per-class and per-view metrics, and group-bootstrap intervals are in [dev_report.json](../experiments/wed_native_segmentation/dev_report.json); the readable tables and visual comparisons are in [dev_report.md](../experiments/wed_native_segmentation/dev_report.md). The selected model is [model_best.pt](../experiments/wed_native_segmentation/model_best.pt), with training history and group/source hashes in [training_report.json](../experiments/wed_native_segmentation/training_report.json). Three representative multi-item DEV views show original, WED ground truth, model prediction, and the SAM2 proposal outlines.

These results establish a substantially better WED-aligned semantic segmentation baseline than generic SAM2 proposals. They do not establish instance segmentation, exact complete-meal region recovery, or any improvement in mass estimation.

## Error analysis and preserved baseline

The checkpoint was copied byte-for-byte to [model_wed_semantic_baseline.pt](../experiments/wed_native_segmentation/model_wed_semantic_baseline.pt). Its SHA-256 is `946a8adc50b131465da421c14caee19f03e4471ed883c8d77bdce119cb0ae963`, matching the evaluated checkpoint. [baseline_manifest.json](../experiments/wed_native_segmentation/baseline_manifest.json) pins the checkpoint, training report, DEV report, error report, and DEV group hash.

Inference-only error analysis on the same DEV carve found 1,602 GT connected components and 1,599 predicted components. At same-class IoU ≥ 0.5, 1,178 regions match. Of the errors, 290 GT components have no same-class predicted overlap, 424 fail the IoU matching threshold overall, 42 GT components overlap multiple predicted components (fragmentation proxy), and 79 predicted components overlap multiple GT components of the same class (merge proxy). There are 85 unmatched predictions that overlap a GT component and 336 unmatched predictions with no same-class GT overlap. Exact class-set detection remains 76/108 meals.

Small annotated regions are disproportionately missed. Of 370 GT components smaller than 0.1% of image area, 269 (72.7%) have no same-class overlap, pixel recall is 34.0%, and only 2 meet IoU ≥ 0.5. By comparison, for regions at least 0.5% of image area, 14/1,104 have no overlap, pixel recall is 93.4%, and region recall at IoU ≥ 0.5 is 96.9%. These tiny components may include annotation islands and should not automatically be interpreted as tiny servings.

Steamed rice has the largest component error counts: 69 no-overlap GT components, 12 fragmented GT components, and 20 predicted components overlapping multiple GT components. Papad has 32 no-overlap GT components and salad has 29. Small-region misses can coexist with strong class pixel IoU because the large annotated regions dominate pixel area. Lowest DEV class IoUs include leaf-dal (0.471), Muskmelon (0.545), tomato-pappu (0.560), aloo-fry (0.646), and non-spicy-dal (0.696); these classes merit inspection in any next training iteration.

The merge and fragmentation counts are strictly **semantic connected-component proxies**. WED has no instance IDs: touching same-class servings can appear as one GT component, separated pixels within one serving can appear as multiple components, and predicted holes can split a mask. Thus the measured counts quantify disagreement with raster topology, not physical serving merges or splits. Likewise, exact class-set accuracy says that each class occurs somewhere in the prediction; it does not ensure every serving of that class was localized.

The full per-class, per-view and size-stratified analysis and error-marked multi-item thali visuals are in [error_analysis.md](../experiments/wed_native_segmentation/error_analysis.md) and [error_analysis.json](../experiments/wed_native_segmentation/error_analysis.json). The analysis used only the fixed DEV images and the preserved checkpoint. No LOCKED, ArUco, or WED test image was accessed; synthetic generation remains paused.
