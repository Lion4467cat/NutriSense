# Conditional GAN five-class pilot — final status

## Training data support

The manifest reader filtered `split=train` entries only and removed the fixed seed-42 DEV groups. A sequential mask scan opened 1,038 eligible TRAIN image-mask pairs from 198 groups; all 41 WED class IDs were present. No DEV, LOCKED, ArUco-evaluation or WED-test images or masks were accessed.

| Class | ID | Mask-positive eligible TRAIN views | Source groups | Foreground pixels |
|---|---:|---:|---:|---:|
| Steamed rice | 34 | 1,034 | 198 | 60,072,927 |
| Chicken dum biryani | 12 | 84 | 17 | 2,410,240 |
| Bottle-gourd curry | 1 | 102 | 21 | 1,383,326 |
| Phulka | 28 | 824 | 158 | 31,927,266 |
| Salad | 32 | 1,010 | 198 | 18,482,834 |

Across all classes, mask-positive view counts range from 62 to 1,034 (16.7×), and foreground pixels range from 1,132,580 to 60,072,927 (53.0×). The frames represent 198 physical meal groups, not 1,038 independent compositions. Biryani and bottle-gourd curry have the weakest support. Group/class sampling cannot create missing appearance variation.

## Architecture and training

The official SPADE implementation is CC BY-NC-SA 4.0 and research-only; official pix2pixHD code is BSD-style, while its documented 1024 × 512 setup lists 11 GB GPU memory. Neither upstream model is trained for WED food; no pretrained weights or external code were downloaded. SPADE's sample COCO/ADE/Cityscapes weights are not relevant food models, and GauGAN weights are unavailable. See `RESEARCH.md` for official-source links and details.

The existing local GAN is a pix2pix-style U-Net with one PatchGAN, not SPADE or pix2pixHD. It also trains with a zero depth channel but supplies normalized depth at inference. The pilot therefore uses a separate project-authored SPADE-style 42-channel semantic generator with two conditional PatchGAN scales, feature matching and paired reconstruction. Its resolution is 256 × 256; no depth signal is used. Parameter counts are 11.95M for the generator and 5.61M for the discriminators.

The authorized RTX 4060 8 GB run completed 20 epochs / 20,760 steps in 883.8 seconds (14 min 44 s): batch 1, AMP, 23.5 images/s average, 553.6 MB peak allocated training VRAM. Generator loss moved 33.42 → 27.21, discriminator loss 2.27 → 2.29, feature-matching loss 2.15 → 1.81, and paired L1 0.201 → 0.134. Loss stability does not demonstrate semantic correctness or realism.

## Five-class results

The frozen DeepLabV3 was applied identically to original Blender RGB and GAN RGB. IoU and 2 px boundary F1 are measured against the unchanged Blender semantic mask. Original Blender RGB already scores poorly for most classes, so these are domain diagnostics rather than real-world accuracy claims.

| Class | Blender IoU | GAN IoU | GAN boundary F1 | GAN area ratio | Segmenter top class | Screen |
|---|---:|---:|---:|---:|---|---|
| Bottle-gourd curry | 0.000 | 0.000 | 0.000 | 0.000 | curd (14) | **Reject** |
| Chicken dum biryani | 0.000 | 0.000 | 0.000 | 0.000 | rasam (31) | **Reject** |
| Phulka | 0.146 | 0.757 | 0.821 | 0.757 | phulka (28) | Human review required |
| Salad | 0.000 | 0.179 | 0.374 | 0.179 | non-spicy-curry (25) | **Reject** |
| Steamed rice | 0.000 | 0.010 | 0.000 | 0.010 | phulka (28) | **Reject** |

The research screen requires target-class IoU ≥ 0.50, boundary F1 ≥ 0.60, target as top predicted food class and predicted/target area ratio in [0.70, 1.30]. Passing only means human review is required; it never auto-approves an image. Four samples are rejected for training. Phulka passes the screen but remains unapproved.

Visual inspection shows conspicuous noisy or wrong-colour food textures in the rejected classes. Phulka is most recognizable but remains stylized. The comparison renders, target masks and frozen-segmenter diagnostic are in `five_class_comparison.png`; complete values are in the ignored `five_class_metrics.json`. Human quality and class-identity decisions remain pending.

![Eligible WED TRAIN references, Blender RGB, GAN RGB, renderer masks and frozen segmenter output](/home/tinkerer/Desktop/Nutrisense/NutriSense-main/datasets/processed/conditional_gan_pilot_20261103/five_class_comparison.png)

## Ground-truth preservation

For all five images, every pixel outside the Blender food mask is byte-identical to Blender RGB. This preserves background and the ID 7 / 60 mm marker appearance. The GAN writes RGB only; semantic masks, metric-depth maps, volume/mass metadata, density assumptions, camera parameters and marker pose were not modified. The generated food interiors nevertheless fail class consistency for four classes, showing why unchanged masks alone do not establish label validity.

The WED TRAIN references shown are eligible training examples also used to fit the GAN. They are not held-out evidence. WED's dataset terms are unpublished; images and WED-derived weights remain local and must not be redistributed.

## Decision

The RTX 4060 can train and run this compact configuration, but this run does not establish that conditional GAN appearance generation can produce trustworthy food images from the current Blender masks. **Do not scale the corpus or train production models on these samples.** First investigate the failed classes, especially why rice and curry layouts do not produce their target classes. A longer run is only justified if in-domain WED TRAIN mask reconstructions show learned class-specific appearance. Any follow-up must keep the same TRAIN-only boundary, immutable physical labels, frozen-segmenter diagnostics and human review gate.

## Reproducibility and constraints

- Experiment scripts: `prepare_pilot_inputs.py`, `spade_pilot.py`, `render_pilot.py`.
- Research/license review: `RESEARCH.md`.
- Reproduction commands and protections: `README.md`.
- All generated images, WED-derived references, model weights and logs are under ignored `datasets/processed/conditional_gan_pilot_20261103/`.
- Production classifier, segmenter and weight checkpoints were not modified. No full corpus, production-model training or protected evaluation was performed.
- Focused Ruff, Python compilation, model CPU forward and one CPU gradient-update smoke checks passed. Full test suite was not run.
