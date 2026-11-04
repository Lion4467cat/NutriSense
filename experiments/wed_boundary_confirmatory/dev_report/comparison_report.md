# Confirmatory WED boundary-loss comparison

Fixed DEV: 108 views / 21 meal groups. Seeds: 42, 43, 44; 20 epochs per run.
Frozen reference SHA-256: `946a8adc50b131465da421c14caee19f03e4471ed883c8d77bdce119cb0ae963`. LOCKED/ArUco/WED test/synthetic accessed: **No**.

Both loss conditions use paired initialization, per-epoch sample order and augmentation seeds. Per-seed figures and pooled 21-group bootstrap intervals are in the JSON.

## Per-seed metrics

| Seed | Loss | Macro food IoU | Foreground IoU | Boundary F1 | Tiny pixel recall | Tiny component recall | Region F1 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 42 | standard | 0.8221 | 0.9149 | 0.5627 | 0.3472 | 0.0027 | 0.7392 |
| 42 | boundary_aware | 0.8142 | 0.9136 | 0.5552 | 0.4067 | 0.0054 | 0.7468 |
| 43 | standard | 0.8205 | 0.9149 | 0.5624 | 0.3331 | 0.0054 | 0.7388 |
| 43 | boundary_aware | 0.8231 | 0.9137 | 0.5563 | 0.3781 | 0.0081 | 0.7510 |
| 44 | standard | 0.8191 | 0.9140 | 0.5585 | 0.3764 | 0.0054 | 0.7434 |
| 44 | boundary_aware | 0.8229 | 0.9137 | 0.5553 | 0.4013 | 0.0054 | 0.7519 |

## Mean across seeds

| Loss | Macro food IoU | Foreground IoU | Boundary F1 | Tiny pixel recall | Tiny component recall | Region F1 |
|---|---:|---:|---:|---:|---:|---:|
| standard | 0.8205 ± 0.0015 | 0.9146 ± 0.0005 | 0.5612 ± 0.0023 | 0.3522 ± 0.0221 | 0.0045 ± 0.0016 | 0.7405 ± 0.0026 |
| boundary_aware | 0.8201 ± 0.0050 | 0.9137 ± 0.0001 | 0.5556 ± 0.0006 | 0.3953 ± 0.0152 | 0.0063 ± 0.0016 | 0.7499 ± 0.0027 |

## Boundary-aware minus matched standard loss

| Metric | Mean paired difference | 95% group-bootstrap CI | Across-seed SD |
|---|---:|---:|---:|
| macro_food_iou | -0.0005 | [-0.0028, +0.0016] | 0.0064 |
| foreground_iou | -0.0009 | [-0.0014, -0.0004] | 0.0005 |
| region_f1 | +0.0095 | [+0.0038, +0.0154] | 0.0025 |
| boundary_f1_tolerance_3px | -0.0056 | [-0.0084, -0.0025] | 0.0022 |
| tiny_pixel_recall | +0.0431 | [-0.0290, +0.1160] | 0.0174 |
| tiny_region_recall_iou_0_5 | +0.0018 | [+0.0000, +0.0046] | 0.0016 |
| mean_merge_proxy_per_view | +0.0401 | [-0.0120, +0.0957] | 0.0527 |
| mean_fragmentation_proxy_per_view | +0.0031 | [-0.0390, +0.0498] | 0.0588 |

## Boundary-aware minus frozen reference

| Metric | Mean paired difference | 95% group-bootstrap CI | Across-seed SD |
|---|---:|---:|---:|
| macro_food_iou | -0.0010 | [-0.0091, +0.0050] | 0.0050 |
| foreground_iou | -0.0059 | [-0.0070, -0.0048] | 0.0001 |
| region_f1 | +0.0139 | [+0.0046, +0.0243] | 0.0027 |
| boundary_f1_tolerance_3px | -0.0417 | [-0.0510, -0.0322] | 0.0006 |
| tiny_pixel_recall | +0.0550 | [-0.0531, +0.1329] | 0.0152 |
| tiny_region_recall_iou_0_5 | +0.0009 | [-0.0045, +0.0064] | 0.0016 |
| mean_merge_proxy_per_view | +0.0525 | [-0.0126, +0.1231] | 0.0283 |
| mean_fragmentation_proxy_per_view | -0.0864 | [-0.1509, -0.0220] | 0.0475 |

## Per-class IoU

Mean over the three seeds; absent DEV classes are `n/a`.

| ID | Class | Frozen | Standard mean ± SD | Boundary mean ± SD | Boundary − standard |
|---:|---|---:|---:|---:|---:|
| 2 | aloo-capsicum | 0.801 | 0.7950 ± 0.0014 | 0.7969 ± 0.0098 | +0.002 |
| 3 | aloo-curry | 0.835 | 0.8357 ± 0.0035 | 0.8367 ± 0.0077 | +0.001 |
| 4 | aloo-fry | 0.646 | 0.6399 ± 0.0035 | 0.6374 ± 0.0036 | -0.003 |
| 5 | beans-curry | 0.870 | 0.8621 ± 0.0034 | 0.8629 ± 0.0064 | +0.001 |
| 6 | beetroot-kobari | 0.764 | 0.7667 ± 0.0016 | 0.7620 ± 0.0059 | -0.005 |
| 7 | beetroot-poriyal | 0.881 | 0.8769 ± 0.0058 | 0.8756 ± 0.0066 | -0.001 |
| 8 | bisi-bele-bath | 0.896 | 0.9013 ± 0.0016 | 0.9033 ± 0.0022 | +0.002 |
| 9 | boondi | 0.810 | 0.8001 ± 0.0053 | 0.8008 ± 0.0032 | +0.001 |
| 10 | cabbage-dry | 0.893 | 0.8889 ± 0.0032 | 0.8875 ± 0.0016 | -0.001 |
| 11 | channa-brinjal | 0.836 | 0.8617 ± 0.0060 | 0.8685 ± 0.0097 | +0.007 |
| 12 | chicken-dum-biryani | 0.841 | 0.8139 ± 0.0079 | 0.8101 ± 0.0125 | -0.004 |
| 13 | chutney | 0.831 | 0.8155 ± 0.0028 | 0.8121 ± 0.0037 | -0.003 |
| 14 | curd | 0.909 | 0.9011 ± 0.0013 | 0.8995 ± 0.0014 | -0.002 |
| 15 | dondakaya-fry | 0.775 | 0.8033 ± 0.0194 | 0.7933 ± 0.0051 | -0.010 |
| 16 | kakarakaya-fry | 0.762 | 0.7901 ± 0.0305 | 0.7762 ± 0.0106 | -0.014 |
| 17 | kofta-curry | 0.861 | 0.8430 ± 0.0094 | 0.8446 ± 0.0118 | +0.002 |
| 18 | leaf-dal | 0.471 | 0.6472 ± 0.0299 | 0.6315 ± 0.0663 | -0.016 |
| 19 | mango-pickle | 0.796 | 0.7859 ± 0.0013 | 0.7883 ± 0.0014 | +0.002 |
| 21 | mirchi-ka-salan | 0.913 | 0.8880 ± 0.0031 | 0.8839 ± 0.0026 | -0.004 |
| 22 | muddha-pappu | 0.815 | 0.6545 ± 0.0689 | 0.7024 ± 0.0605 | +0.048 |
| 23 | non-spicy-curry | 0.826 | 0.8236 ± 0.0027 | 0.8220 ± 0.0034 | -0.002 |
| 24 | non-spicy-dal | 0.696 | 0.7402 ± 0.0044 | 0.7370 ± 0.0296 | -0.003 |
| 25 | pachi-pulusu | 0.859 | 0.8489 ± 0.0055 | 0.8503 ± 0.0039 | +0.001 |
| 26 | papad | 0.874 | 0.8686 ± 0.0030 | 0.8669 ± 0.0025 | -0.002 |
| 27 | payasam | 0.894 | 0.8923 ± 0.0084 | 0.8928 ± 0.0094 | +0.001 |
| 28 | phulka | 0.934 | 0.9242 ± 0.0009 | 0.9228 ± 0.0015 | -0.001 |
| 29 | raita | 0.912 | 0.9008 ± 0.0064 | 0.9008 ± 0.0048 | -0.000 |
| 30 | rajma | 0.913 | 0.9038 ± 0.0032 | 0.9057 ± 0.0082 | +0.002 |
| 32 | salad | 0.866 | 0.8601 ± 0.0010 | 0.8580 ± 0.0018 | -0.002 |
| 33 | sambar | 0.876 | 0.8981 ± 0.0067 | 0.8938 ± 0.0013 | -0.004 |
| 34 | steamed-rice | 0.886 | 0.8812 ± 0.0026 | 0.8804 ± 0.0008 | -0.001 |
| 35 | tomato-pappu | 0.560 | 0.6347 ± 0.0172 | 0.6289 ± 0.0332 | -0.006 |
| 36 | veg-dum-briyani | 0.837 | 0.8227 ± 0.0061 | 0.8196 ± 0.0075 | -0.003 |
| 37 | veg-pulao | 0.873 | 0.8609 ± 0.0064 | 0.8625 ± 0.0060 | +0.002 |
| 38 | Watermelon | 0.841 | 0.8374 ± 0.0004 | 0.8355 ± 0.0010 | -0.002 |
| 39 | Papaya | 0.877 | 0.8619 ± 0.0085 | 0.8642 ± 0.0041 | +0.002 |
| 40 | Banana | 0.927 | 0.9200 ± 0.0031 | 0.9198 ± 0.0008 | -0.000 |
| 41 | Muskmelon | 0.545 | 0.5304 ± 0.0069 | 0.5281 ± 0.0060 | -0.002 |

## Tiny-component overlap diagnosis

Buckets classify each tiny GT component by its best same-class predicted-component IoU. Partial overlap can raise pixel coverage while remaining below the complete-component IoU≥0.5 threshold.

### standard

| Seed | Tiny GT | No overlap | Partial overlap <0.5 | Match ≥0.5 | Multi-pred overlaps | Mean best pixel coverage |
|---:|---:|---:|---:|---:|---:|---:|
| 42 | 370 | 254 | 115 | 1 | 0 | 0.262 |
| 43 | 370 | 275 | 93 | 2 | 1 | 0.219 |
| 44 | 370 | 262 | 106 | 2 | 0 | 0.252 |

### boundary_aware

| Seed | Tiny GT | No overlap | Partial overlap <0.5 | Match ≥0.5 | Multi-pred overlaps | Mean best pixel coverage |
|---:|---:|---:|---:|---:|---:|---:|
| 42 | 370 | 258 | 110 | 2 | 0 | 0.270 |
| 43 | 370 | 264 | 103 | 3 | 0 | 0.261 |
| 44 | 370 | 253 | 115 | 2 | 2 | 0.268 |

## Promotion

Matched-control gate: **FAIL**.
Frozen-reference gate: **FAIL**.
Recommendation: **retain_frozen_deeplabv3_and_close_boundary_loss_line**.

All regions, merges, and fragments are connected components of semantic WED masks, not serving-level instance labels. If gates fail, retain the frozen checkpoint and close this loss line.
