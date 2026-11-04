# Confirmatory boundary-loss study protocol

Status: fixed before this focused study's runner and checkpoints. The frozen 20-epoch DeepLabV3 reference remains unchanged.

## Question

Does adding the boundary-weighted CE term to the existing weighted-CE + foreground soft-Dice objective improve WED semantic segmentation when all other training conditions are matched?

## Data and separation

- Use only eligible WED TRAIN groups for gradient updates and internal checkpoint selection.
- Keep the same fixed internal 928-view train / 110-view validation split and group hashes as the prior WED study.
- Keep the existing 108-view / 21-group DEV carve for final evaluation only; do not tune thresholds, loss weights, or recipes on DEV.
- Do not access WED LOCKED/test images or ArUco evaluation images. No synthetic data and no geometry/weight work.

## Paired training conditions

Run three paired seeds (42, 43, 44) when the approved GPU runtime is available. For each seed, create one DeepLabV3 initialization with an ImageNet-1K V2 ResNet-50 backbone and a seed-specific 42-class head, save it, then load that exact state into both loss conditions. Within each pair, use identical WED examples in the same order, identical horizontal-flip and mild brightness/contrast augmentation draws, identical class weights, batch size 2, optimizer, learning-rate schedule, number of updates, and checkpoint rule. Seed changes affect only the initialized head and training randomness; the physical-group split stays fixed.

Both conditions use 768×1024 inputs, 928 training views per epoch, 110 internal validation views, batch size 2, AdamW (backbone LR 2e-5, head LR 2e-4, weight decay 1e-4), cosine decay over 20 epochs, and 20 complete epochs. The control uses 0.7 weighted CE + 0.3 foreground soft Dice. The treatment changes only CE pixel weighting by the pre-existing 3× boundary multiplier, retaining 0.7 CE + 0.3 Dice. Select each run's checkpoint by best internal-validation macro food IoU, with no early stopping. Record paired initialization hashes, per-epoch example-order hashes, update counts, training time, peak VRAM, and checkpoint hashes.

The frozen original checkpoint is evaluated as a separate reference anchor. “Original DeepLabV3” in the matched experiment means a freshly initialized standard-loss control; the protected frozen checkpoint is never retrained or overwritten.

## Evaluation and explanation

After all six candidate checkpoints are frozen, evaluate them and the frozen reference on the same 108 DEV views. Report per-seed metrics and variability, pooled paired differences with 95% physical-meal-group bootstrap intervals, and the same metric definitions as the prior report: macro food IoU, foreground union IoU, class-wise boundary F1 at 3-pixel tolerance, all 41 per-class IoUs, tiny-bin pixel recall and IoU≥0.5 component recall, and class-aware region precision/recall/F1.

For the tiny-region explanation, additionally count same-class GT tiny components with no predicted overlap, overlap but best component IoU below 0.5, IoU≥0.5 match, partial-pixel coverage, and overlap with multiple predicted components. This distinguishes pixel coverage from complete component recovery. Connected components remain semantic raster proxies; WED has no instance IDs.

## Promotion criterion

First assess the loss effect against the paired 20-epoch standard-loss control: require mean macro food IoU gain ≥0.01 and a paired physical-group bootstrap 95% CI above zero, plus ≥5 percentage-point gain in tiny pixel recall or tiny IoU≥0.5 component recall with its CI above zero. Require the lower CI bound for foreground IoU and region F1 to be above −0.01, no priority-class IoU regression worse than −0.05, the upper CI bound on merge and fragmentation increases ≤+0.25 per meal, and boundary F1 no worse than −0.01.

Any product promotion must also satisfy the same gains and guardrails against the frozen original reference. If either comparison fails, keep the frozen checkpoint and close boundary-aware loss as the current research line. The 95% bootstrap intervals describe variability across DEV meal groups; the three paired seeds separately describe training-seed variability.

## Execution addendum before accepted paired runs

The first long process did not complete the pair. To avoid losing progress to long-session termination, each accepted 20-epoch model run is executed as two 10-epoch chunks. At every epoch, the training seed, sampler, worker/augmentation generator, and model RNG are derived deterministically from the same `(training seed, epoch)` pair. Model, optimizer, scheduler, and gradient-scaler states are checkpointed at epoch 10 and restored for epochs 11–20. The paired loss conditions therefore receive identical per-epoch samples and augmentation draws across the chunk boundary. A standalone 20-epoch standard-loss run made before this change is preserved but excluded from the confirmatory comparison because its persistent-worker augmentation stream cannot be paired to the resumed treatment run.
