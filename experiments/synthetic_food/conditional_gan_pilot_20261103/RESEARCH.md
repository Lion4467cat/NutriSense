# Conditional semantic GAN feasibility: SPADE and pix2pixHD

**Scope:** primary-source review of semantic-layout-to-image methods and the local GAN adapter/trainer. No model weights were downloaded and no training was run. For the support audit, only eligible WED TRAIN masks and paired TRAIN image headers were read; no DEV, LOCKED, ArUco evaluation or WED test assets were accessed.

## Findings

### pix2pixHD

The official [NVIDIA/pix2pixHD repository](https://github.com/NVIDIA/pix2pixHD) implements semantic-label-map-to-image translation with a coarse-to-fine generator, multi-scale discriminators and instance-edge conditioning. Its [paper](https://arxiv.org/abs/1711.11585) reports 2048×1024 synthesis and introduces multi-scale generator/discriminator components and diverse outputs. The repository's [README](https://github.com/NVIDIA/pix2pixHD/blob/master/README.md) documents 1024×512 training and lists an NVIDIA GPU with at least 11 GB memory as its prerequisite; this is the published requirement for that code/configuration, not a measured minimum at 256×256. Its [LICENSE.txt](https://github.com/NVIDIA/pix2pixHD/blob/master/LICENSE.txt) is BSD-style and permits source/binary redistribution subject to its conditions. Its example Cityscapes checkpoint is hosted separately through Google Drive; code licensing does not establish checkpoint or dataset licensing.

**NutriSense fit:** the most practical first comparison for an 8 GB RTX 4060 is a reduced 256×256 pix2pixHD-like configuration, batch size 1 initially, AMP, and the multi-scale/feature-matching losses kept where memory permits. That is a testable starting point, not an established memory guarantee. The semantic layouts are compatible in principle, but WED provides only 1,038 eligible TRAIN views across 198 groups after excluding the fixed DEV carve, so the minority classes have much less independent variation than the large-image street-scene tasks for which pix2pixHD was demonstrated.

### SPADE

SPADE's [CVPR paper](https://arxiv.org/abs/1903.07291) conditions normalization layers at each spatial position on a resized semantic map, specifically to preserve semantic structure through the generator. The official [NVlabs/SPADE README](https://github.com/NVlabs/SPADE/blob/master/README.md) says a newer, more performant reimplementation is in Imaginaire; it also documents custom paired label/image directories, label count and optional instance maps. The same README says reproducing the paper used an NVIDIA DGX-1 with eight V100 GPUs. The official SPADE [license](https://github.com/NVlabs/SPADE/blob/master/LICENSE.md) is CC BY-NC-SA 4.0 and says academic research only; commercial use requires contacting NVIDIA.

The legacy SPADE repository has pretrained model downloads for COCO, ADE20K and Cityscapes, but these are not food models. The README states that GauGAN weights are not released. Checkpoint download availability is therefore not a route to a NutriSense food generator, and separate model/data terms would need review before adopting any checkpoint.

NVlabs points to [Imaginaire](https://github.com/NVlabs/imaginaire) as its faster reimplementation. Its individual model files carry NVIDIA Source Code License-NC notices (for example [pix2pixHD generator source](https://github.com/NVlabs/imaginaire/blob/master/imaginaire/generators/pix2pixHD.py)); do not assume this repository is suitable for commercial/product deployment. Its dependency stack is also a larger integration than adapting our existing PyTorch pipeline.

**NutriSense fit:** SPADE is the better architectural match if pix2pixHD washes out small food regions or class boundaries, but the official legacy implementation's license and published 8×V100 reproduction setup make it a poor first implementation base for a product path. A lightweight 256px custom SPADE-style generator could be evaluated for research, after confirming the project's allowed research use and the omitted constraint at the end of the request.

## Local paired data audit

The local manifest helper reads only `split=train` rows and removes the established 21-group DEV carve before returning eligible training views. A sequential, CPU-only scan of those eligible training masks found 1,038 readable paired image/mask views across 198 source groups, with all 41 semantic IDs represented. Pixel-positive support for the requested classes is:

| WED class | Class ID | Eligible TRAIN views with mask pixels | Source groups |
|---|---:|---:|---:|
| Steamed rice | 34 | 1,034 | 198 |
| Chicken dum biryani | 12 | 84 | 17 |
| Bottle-gourd curry | 1 | 102 | 21 |
| Phulka | 28 | 824 | 158 |
| Salad | 32 | 1,010 | 198 |

The images and masks are paired at the view level, so paired supervision is available. However, the effective independent sample count is bounded by groups, not frames; repeated views from one meal must remain in the same partition and cannot be counted as independent food appearances. The severe support skew for biryani and bottle-gourd curry argues against naive image-uniform training or relying on the GAN discriminator to fix data scarcity. A class/group-balanced sampler and per-class sampling diagnostics are needed. The five-class pilot's candidate classes are also mixed with the remaining WED classes in most full-meal layouts; this is useful context, but it is not a collection of isolated, class-only examples.

## Local implementation audit

The repository already contains `nutrisense_synth/methods/gan_training.py` and `nutrisense_synth/methods/gan.py`. The current trainer is a small pix2pix-style U-Net plus a single PatchGAN discriminator, using BCE adversarial loss plus L1 reconstruction. It reads eligible WED TRAIN pairs, uses group-aware class weights, and writes a provenance sidecar. It does **not** implement SPADE normalization, pix2pixHD's coarse-to-fine/multi-scale design, multi-scale discriminators, feature-matching loss, or perceptual loss. Its current internal training resolution is 384×256. There is also a condition mismatch to fix before reuse: training appends an all-zero depth channel while `GANMethod.generate()` appends per-image normalized metric depth. The model would therefore see a depth condition at inference that it never saw during training. This is a useful baseline implementation seam, not an implementation of either named reference architecture.

## Recommended experiment design

After receiving the complete constraints, compare a matched 256×256 budget using the existing small pix2pix-style baseline and one SPADE-style candidate, with frozen inputs, identical eligible TRAIN groups, fixed seeds, and equal step budgets. Save source masks and raw generated RGB separately. Freeze the deployed segmentation checkpoint for diagnostics; report per-class mask IoU/boundary consistency and class confusion on generated RGB, but do not use those diagnostics as proof of realism. Make human identity review a separate gate. Evaluate the five selected classes on renderer masks; keep geometry/depth/mass/marker files immutable and reject any RGB where the frozen segmenter or human inspection indicates label drift. Do not tune on DEV, LOCKED, ArUco evaluation, or WED test data.

At 256×256, use AMP and batch-size-1 memory profiling on the authorized GPU before committing a longer run. Measure `torch.cuda.max_memory_allocated`, images/sec, losses and fixed visualization grids; no published source confirms the exact memory/throughput of a NutriSense-adapted 41-class model on an RTX 4060 8 GB. Do not download upstream weights for this experiment unless their checkpoint-specific and dataset-derived terms are first verified.

## Source links

- [SPADE CVPR paper / arXiv](https://arxiv.org/abs/1903.07291)
- [Official SPADE code and README](https://github.com/NVlabs/SPADE)
- [Official SPADE license](https://github.com/NVlabs/SPADE/blob/master/LICENSE.md)
- [pix2pixHD CVPR paper / arXiv](https://arxiv.org/abs/1711.11585)
- [Official NVIDIA pix2pixHD code and README](https://github.com/NVIDIA/pix2pixHD)
- [pix2pixHD license](https://github.com/NVIDIA/pix2pixHD/blob/master/LICENSE.txt)
- [NVIDIA Imaginaire library](https://github.com/NVlabs/imaginaire)
