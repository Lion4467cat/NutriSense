# Controlled WED segmentation improvement study

DEV: 108 views / 21 physical meal groups. Frozen baseline SHA-256: `946a8adc50b131465da421c14caee19f03e4471ed883c8d77bdce119cb0ae963`.
LOCKED / ArUco / WED test accessed: **No**. Synthetic data used: **No**.

All candidate checkpoints were trained and selected on eligible WED TRAIN groups before this single frozen DEV evaluation. Region and merge/fragmentation figures refer to connected components of semantic rasters; they are not serving-level instance metrics.

Training budget was 10 epochs × 928 sampled TRAIN views per epoch (464 effective optimizer updates per epoch at batch 2), with the same 110-view internal group holdout for checkpoint selection. The selected Stage A recipe by internal-validation macro food IoU was boundary-aware loss.

## Candidate comparison

| Candidate | Macro food IoU | Foreground IoU | Region P / R / F1 | Tiny pixel / region recall | Merge / fragmentation per view | Boundary F1 (3 px) | latency ms | inference / training VRAM MB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| frozen_deeplabv3_reference | 0.8211 | 0.9196 | 0.737 / 0.735 / 0.736 | 0.340 / 0.005 | 0.73 / 0.39 | 0.597 | 118.0 | 736.7 / n/a |
| dlv3_control | 0.8006 | 0.9046 | 0.746 / 0.732 / 0.739 | 0.321 / 0.005 | 0.71 / 0.34 | 0.492 | 118.5 | 736.7 / 5425.3 |
| dlv3_highres | 0.7015 | 0.8859 | 0.550 / 0.677 / 0.607 | 0.201 / 0.000 | 0.56 / 0.73 | 0.444 | 158.0 | 815.9 / 3793.0 |
| dlv3_class_balanced | 0.7969 | 0.9030 | 0.719 / 0.730 / 0.725 | 0.387 / 0.005 | 0.81 / 0.30 | 0.471 | 118.2 | 736.7 / 5427.3 |
| dlv3_food_augmentation | 0.8025 | 0.9051 | 0.741 / 0.734 / 0.737 | 0.405 / 0.005 | 0.73 / 0.26 | 0.484 | 118.3 | 736.7 / 5429.1 |
| dlv3_boundary_loss | 0.8047 | 0.9034 | 0.757 / 0.733 / 0.745 | 0.416 / 0.005 | 0.80 / 0.27 | 0.487 | 118.9 | 736.7 / 5685.3 |
| architecture_deeplabv3plus | 0.7952 | 0.9072 | 0.622 / 0.727 / 0.670 | 0.308 / 0.003 | 0.60 / 0.29 | 0.526 | 38.8 | 739.1 / 4013.3 |
| architecture_segformer_b0 | 0.7942 | 0.9025 | 0.494 / 0.726 / 0.588 | 0.236 / 0.003 | 0.50 / 0.78 | 0.492 | 38.9 | 699.0 / 3070.1 |

## Per-class IoU

| ID | Class | Frozen reference | Best macro candidate | Δ |
|---:|---|---:|---:|---:|
| 1 | Bottle-gourd-curry | n/a | n/a | n/a |
| 2 | aloo-capsicum | 0.801 | 0.779 | -0.022 |
| 3 | aloo-curry | 0.835 | 0.818 | -0.016 |
| 4 | aloo-fry | 0.646 | 0.620 | -0.026 |
| 5 | beans-curry | 0.870 | 0.839 | -0.031 |
| 6 | beetroot-kobari | 0.764 | 0.731 | -0.033 |
| 7 | beetroot-poriyal | 0.881 | 0.840 | -0.041 |
| 8 | bisi-bele-bath | 0.896 | 0.893 | -0.004 |
| 9 | boondi | 0.810 | 0.768 | -0.042 |
| 10 | cabbage-dry | 0.893 | 0.867 | -0.026 |
| 11 | channa-brinjal | 0.836 | 0.827 | -0.009 |
| 12 | chicken-dum-biryani | 0.841 | 0.778 | -0.063 |
| 13 | chutney | 0.831 | 0.794 | -0.037 |
| 14 | curd | 0.909 | 0.896 | -0.013 |
| 15 | dondakaya-fry | 0.775 | 0.813 | +0.039 |
| 16 | kakarakaya-fry | 0.762 | 0.792 | +0.030 |
| 17 | kofta-curry | 0.861 | 0.840 | -0.021 |
| 18 | leaf-dal | 0.471 | 0.603 | +0.131 |
| 19 | mango-pickle | 0.796 | 0.773 | -0.023 |
| 20 | masoor-dal | n/a | n/a | n/a |
| 21 | mirchi-ka-salan | 0.913 | 0.866 | -0.047 |
| 22 | muddha-pappu | 0.815 | 0.709 | -0.106 |
| 23 | non-spicy-curry | 0.826 | 0.794 | -0.031 |
| 24 | non-spicy-dal | 0.696 | 0.721 | +0.025 |
| 25 | pachi-pulusu | 0.859 | 0.836 | -0.023 |
| 26 | papad | 0.874 | 0.850 | -0.024 |
| 27 | payasam | 0.894 | 0.886 | -0.008 |
| 28 | phulka | 0.934 | 0.911 | -0.023 |
| 29 | raita | 0.912 | 0.876 | -0.035 |
| 30 | rajma | 0.913 | 0.891 | -0.022 |
| 31 | rasam | n/a | n/a | n/a |
| 32 | salad | 0.866 | 0.846 | -0.021 |
| 33 | sambar | 0.876 | 0.892 | +0.016 |
| 34 | steamed-rice | 0.886 | 0.873 | -0.013 |
| 35 | tomato-pappu | 0.560 | 0.636 | +0.075 |
| 36 | veg-dum-briyani | 0.837 | 0.775 | -0.062 |
| 37 | veg-pulao | 0.873 | 0.859 | -0.014 |
| 38 | Watermelon | 0.841 | 0.827 | -0.014 |
| 39 | Papaya | 0.877 | 0.857 | -0.020 |
| 40 | Banana | 0.927 | 0.900 | -0.027 |
| 41 | Muskmelon | 0.545 | 0.504 | -0.041 |

Best macro-IoU candidate for class table: `dlv3_boundary_loss`. Classes with no DEV ground-truth pixels show `n/a` and are excluded from macro food IoU.

## Candidate changes versus frozen baseline

| Candidate | Δ macro IoU [95% group CI] | Δ foreground IoU [95% CI] | Δ region F1 [95% CI] | Δ tiny pixel recall [95% CI] | Δ tiny region recall [95% CI] | Gate |
|---|---:|---:|---:|---:|---:|---|
| dlv3_control | -0.020 [-0.028, -0.011] | -0.015 [-0.017, -0.013] | +0.003 [-0.012, +0.018] | -0.019 [-0.116, +0.083] | +0.000 [+0.000, +0.000] | no |
| dlv3_highres | -0.120 [-0.136, -0.072] | -0.034 [-0.041, -0.028] | -0.129 [-0.160, -0.097] | -0.140 [-0.255, -0.030] | -0.005 [-0.014, +0.000] | no |
| dlv3_class_balanced | -0.024 [-0.034, -0.013] | -0.017 [-0.018, -0.015] | -0.011 [-0.036, +0.013] | +0.047 [-0.057, +0.111] | +0.000 [+0.000, +0.000] | no |
| dlv3_food_augmentation | -0.019 [-0.025, -0.012] | -0.014 [-0.016, -0.013] | +0.001 [-0.014, +0.017] | +0.065 [-0.034, +0.125] | +0.000 [+0.000, +0.000] | no |
| dlv3_boundary_loss | -0.016 [-0.024, -0.007] | -0.016 [-0.018, -0.014] | +0.009 [-0.003, +0.020] | +0.076 [+0.015, +0.126] | +0.000 [+0.000, +0.000] | no |
| architecture_deeplabv3plus | -0.026 [-0.036, -0.013] | -0.012 [-0.015, -0.010] | -0.066 [-0.086, -0.046] | -0.032 [-0.224, +0.092] | -0.003 [-0.009, +0.000] | no |
| architecture_segformer_b0 | -0.027 [-0.035, -0.018] | -0.017 [-0.020, -0.015] | -0.148 [-0.182, -0.111] | -0.104 [-0.309, +0.022] | -0.003 [-0.009, +0.000] | no |

## Priority classes across candidates

| Class | Frozen | 10-epoch control | High resolution* | Class-balanced | Food augmentation | Boundary loss | DeepLabV3+ | SegFormer-B0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| leaf-dal | 0.471 | 0.625 | 0.386 | 0.618 | 0.565 | 0.603 | 0.516 | 0.318 |
| papad | 0.874 | 0.850 | 0.812 | 0.850 | 0.854 | 0.850 | 0.847 | 0.831 |
| salad | 0.866 | 0.847 | 0.833 | 0.844 | 0.848 | 0.846 | 0.849 | 0.816 |
| steamed-rice | 0.886 | 0.877 | 0.830 | 0.859 | 0.876 | 0.873 | 0.866 | 0.846 |
| tomato-pappu | 0.560 | 0.624 | 0.541 | 0.620 | 0.567 | 0.636 | 0.590 | 0.613 |
| Muskmelon | 0.545 | 0.498 | 0.504 | 0.491 | 0.507 | 0.504 | 0.524 | 0.540 |

*High-resolution run also held ASPP global-pooling BatchNorm in evaluation mode; see execution note below.

## Small-region metrics by size

Candidate values below are for the highest macro-IoU candidate; full candidate values are in the JSON report.

| GT size bin | GT regions | Pixel recall | IoU≥0.5 region recall | No-overlap miss rate |
|---|---:|---:|---:|---:|
| tiny_lt_0.10pct | 370 | 0.41618672324946954 | 0.005405405405405406 | 0.7135135135135136 |
| small_0.10_to_0.25pct | 37 | 0.6133256661748112 | 0.5405405405405406 | 0.16216216216216217 |
| medium_0.25_to_0.50pct | 91 | 0.8198848976343716 | 0.8791208791208791 | 0.04395604395604396 |
| large_ge_0.50pct | 1104 | 0.930580629852521 | 0.9710144927536232 | 0.010869565217391304 |

## Execution note

- An initial launch completed the matched DeepLabV3 control, then exited at the high-resolution run because the ASPP global-pooling BatchNorm received a singleton batch.
- The high-resolution run completed on retry with physical batch size 1, gradient accumulation 2, and ASPP global-pooling BatchNorm held in evaluation mode; it therefore has this documented training-side adjustment in addition to resolution and is not a perfectly isolated resolution-only ablation.
- No GPU out-of-memory event occurred; all seven final candidates completed 10 epochs and were frozen before DEV inference.

The high-resolution result has an ASPP pooled-BatchNorm adjustment, so interpret it as a practical high-resolution candidate rather than a perfectly isolated resolution-only ablation.

## Recommendation

**No promotion** — No candidate passes every predeclared criterion; keep the frozen reference.

Visual comparisons are in the `visuals/` directory. The JSON report contains all class IoUs, checkpoint and candidate hashes, uncertainty intervals, per-view component counts, runtime and peak memory.
