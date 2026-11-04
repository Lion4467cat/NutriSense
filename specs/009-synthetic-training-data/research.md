# Research: Label-Preserving Synthetic Food Data

**Date**: 2026-11-02

## Decisions

### Renderer/domain randomization is the control and label authority

The existing scene renderer directly produces RGB, metric depth, object/component masks, marker ground truth, and mass integrated from its explicit shape and density parameters. Extend this route first as the reproducible control. Randomizing materials, lighting, camera, vessel, and background changes appearance while retaining scene-owned annotations. This follows the simulation-to-real rationale in Tobin et al. (2017), but the paper’s robotics results do not establish NutriSense food-domain accuracy. [Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World](https://arxiv.org/abs/1703.06907)

### GAN candidate: mask-conditioned semantic generation

Use WED TRAIN’s paired image and pixel-label maps to train a conditional GAN that produces image appearance from a renderer scene’s semantic layout. SPADE is a relevant layout-conditioned architecture: [Park et al., Semantic Image Synthesis with Spatially-Adaptive Normalization](https://arxiv.org/abs/1903.07291). The paired pix2pix approach is useful only where aligned condition/output examples exist; its paper shows adversarial training can hallucinate detail and does not guarantee geometry: [Isola et al., Image-to-Image Translation with Conditional Adversarial Networks](https://arxiv.org/abs/1611.07004). WED photos are not paired with the renderer’s exact scenes, so the GAN must be trained from WED’s own masks and then conditioned on compatible renderer layouts. A general unpaired CycleGAN-style route is lower priority because its paper describes texture/color translation as more reliable than geometric changes: [Zhu et al., Unpaired Image-to-Image Translation using Cycle-Consistent Adversarial Networks](https://arxiv.org/abs/1703.10593).

### Diffusion candidate: semantic/depth-conditioned appearance translation

Test a diffusion translator conditioned on renderer segmentation/depth/edge maps. ControlNet makes spatial controls practical, but the control signal is guidance rather than exact ground truth: [Zhang et al., Adding Conditional Control to Text-to-Image Diffusion Models](https://arxiv.org/abs/2302.05543). ControlNet++ addresses control misalignment with pixel-level consistency feedback, reinforcing the need to measure and reject drift: [Siah et al., ControlNet++](https://arxiv.org/abs/2404.07987). Label-guided image translation explicitly applies pixel labels during diffusion translation: [Peng et al., Diffusion-based Image Translation with Label Guidance](https://openaccess.thecvf.com/content/ICCV2023/html/Peng_Diffusion-based_Image_Translation_with_Label_Guidance_for_Domain_Adaptive_Semantic_Segmentation_ICCV_2023_paper.html). Plug-and-Play Diffusion Features are a training-free comparison for appearance/layout transfer, not a source of exact pixel geometry: [Tumanyan et al., CVPR 2023](https://openaccess.thecvf.com/content/CVPR2023/html/Tumanyan_Plug-and-Play_Diffusion_Features_for_Text-Driven_Image-to-Image_Translation_CVPR_2023_paper.html).

### Renderer labels remain authoritative

GAN and diffusion outputs can look realistic while changing class identity, boundaries, depth, card corners, or mass-relevant geometry. Translate only within the food region where practical, preserve renderer geometry and labels, restore the exact marker from the renderer, and retain labels task-by-task only after automated checks. The sample’s physical mass remains volume × documented density; a model’s image-conditioned weight prediction is a separate experimental prediction. Human review is an additional QA gate, not a replacement for measurement or automated checks.

### Keep checkpoint provenance separate from dataset provenance

No external raw image dataset is needed for the core plan. A pretrained diffusion checkpoint may nevertheless encode external training data. It must not silently enter the core comparison: record the checkpoint ID/revision/hash, license, training-data disclosure, permitted downstream use, and possible WED overlap, and evaluate it as a separately labeled research track until reviewed. This is consistent with ControlNet’s use of pretrained diffusion weights, but avoids treating a model card as proof of dataset provenance. [Diffusers ControlNet documentation](https://huggingface.co/docs/diffusers/api/pipelines/controlnet)

### Fair comparison and selection

Keep generation method, class/portion distribution, resolution, sample count, card condition, and downstream optimization budget in the run manifest. Compare 0%, 25%, 50%, 75%, and 100% synthetic fractions at a fixed total training budget. Report discriminator/realism, sample diversity, and review outcomes as diagnostics. Use only real WED DEV task metrics for iterative model selection, with grouped uncertainty and per-stage/end-to-end guardrails.

## Alternatives Considered

| Approach | Decision | Rationale |
|---|---|---|
| Procedural renderer only | Retain as control, not sole candidate | It provides exact labels and reproducibility but current material profiles do not cover 41 classes or realistic appearance variation. |
| Unconditional GAN sampling | Exclude from label-supervised corpus | The output is not tied to a known scene, mask, depth map, marker pose, or physical mass. |
| Pix2pix using WED as paired data | Do not assume pairing | WED images/masks are paired, but WED photos are not paired to matching renderer scenes. Use semantic layout conditioning rather than claiming nonexistent scene pairs. |
| Unpaired CycleGAN | Optional appearance-only comparator | It may alter silhouettes and geometry; it cannot author depth or mass labels. |
| Pretrained diffusion in the core fair matrix | Defer pending provenance review | Different external training data creates a material confound and checkpoint-license obligation. A separate tracked research comparison can revisit it. |
| Discriminator score as promotion gate | Reject | Realism does not verify labels or downstream accuracy. |

## Compute Note

The official Diffusers ControlNet training guide reports about 38 GB VRAM for its example configuration and describes memory-reduction options for smaller GPUs. This is a reference for that example, not a requirement for a compact, from-scratch or parameter-efficient candidate. The project must pilot the intended resolution and record throughput/peak VRAM before fixing the final corpus budget. [ControlNet training guide](https://huggingface.co/docs/diffusers/v0.25.0/training/controlnet)
