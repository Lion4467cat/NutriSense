# Integrated NutriSense real-data prototype — WED DEV

- Fixed DEV carve: 108 views / 21 physical groups.
- Device: cuda; no GPU available.
- Frozen segmenter checkpoint SHA-256: `946a8adc50b131465da421c14caee19f03e4471ed883c8d77bdce119cb0ae963`.
- LOCKED / ArUco evaluation / WED test accessed: **false / false / false**.
- Ground-truth masks/classes passed to inference: **false**.

## Pipeline routes

The API uses the frozen 41-class WED DeepLabV3, then derives 8-connected class regions. Because WED has no instance IDs and weight labels are per class, disconnected predicted regions of one class are unioned for the learned mass head. The UI receives one bbox and estimate per predicted class; these are class-level estimates, not verified serving instances.

No-card WED-mapped predictions use the existing learned weight head. MoGe is loaded only for a valid measured ID 7 / 60 mm marker; uncalibrated relative depth is never converted to absolute geometry. Renderer-grounded depth/geometry validation is reported separately.

## DEV results

| Metric | Result |
|---|---:|
| Macro food IoU | 0.8219 |
| Foreground IoU | 0.9197 |
| Region precision / recall / F1 | 0.8785 / 0.7360 / 0.8010 |
| Exact semantic class-set meals | 78/108 |
| Individual class-total mass MAE / bias | 16.44 g / -1.52 g |
| Total meal mass MAE / bias | 79.38 g / -17.79 g |
| Numeric total predictions / abstentions | 108 / 0 |
| cannot_verify verdicts / rate | 0 / 0.000 |
| Total-mass abstention rate | 0.000 |
| Complete weighted class-coverage meals | 78/108 |
| Total 90% interval coverage | 0.935 |
| Mean latency / p95 | 0.45 s / 0.45 s |
| Peak process RSS | 3333 MB |

Individual mass is evaluated at WED's class-total granularity, not per connected component. Class false positives and misses contribute zero-vs-label errors. Total meal weight is scored only when the API returns numeric grams; abstentions remain visible in the denominator.

The 90% total-weight interval covered 81.5% of DEV meals, below its nominal target. Intervals are not calibrated well enough to support high-confidence use; report them as uncertainty estimates, not guarantees.

## Per-class segmentation

| Class | IoU | Pixel precision | Pixel recall | GT pixels |
|---|---:|---:|---:|---:|
| Bottle-gourd-curry | 0.0000 | 0.0000 | 0.0000 | 0 |
| aloo-capsicum | 0.8007 | 0.8903 | 0.8883 | 282568 |
| aloo-curry | 0.8347 | 0.9260 | 0.8944 | 262851 |
| aloo-fry | 0.6474 | 0.9101 | 0.6917 | 390659 |
| beans-curry | 0.8695 | 0.9091 | 0.9523 | 1162163 |
| beetroot-kobari | 0.7639 | 0.7827 | 0.9694 | 567872 |
| beetroot-poriyal | 0.8810 | 0.8925 | 0.9856 | 371575 |
| bisi-bele-bath | 0.8959 | 0.9074 | 0.9860 | 271043 |
| boondi | 0.8108 | 0.8465 | 0.9506 | 197656 |
| cabbage-dry | 0.8945 | 0.9361 | 0.9527 | 832799 |
| channa-brinjal | 0.8377 | 0.9267 | 0.8972 | 428634 |
| chicken-dum-biryani | 0.8433 | 0.8838 | 0.9484 | 385657 |
| chutney | 0.8317 | 0.9142 | 0.9020 | 450980 |
| curd | 0.9091 | 0.9371 | 0.9682 | 2695874 |
| dondakaya-fry | 0.7775 | 0.8403 | 0.9124 | 235434 |
| kakarakaya-fry | 0.7642 | 0.9264 | 0.8136 | 208049 |
| kofta-curry | 0.8622 | 0.8944 | 0.9600 | 700684 |
| leaf-dal | 0.4725 | 0.5018 | 0.8903 | 149884 |
| mango-pickle | 0.7962 | 0.8578 | 0.9172 | 238194 |
| masoor-dal | 0.0000 | 0.0000 | 0.0000 | 0 |
| mirchi-ka-salan | 0.9137 | 0.9284 | 0.9830 | 215207 |
| muddha-pappu | 0.8195 | 0.9071 | 0.8946 | 114390 |
| non-spicy-curry | 0.8270 | 0.8676 | 0.9464 | 528147 |
| non-spicy-dal | 0.6976 | 0.8689 | 0.7797 | 1443644 |
| pachi-pulusu | 0.8586 | 0.9301 | 0.9178 | 667741 |
| papad | 0.8747 | 0.9447 | 0.9219 | 2194398 |
| payasam | 0.8937 | 0.9216 | 0.9671 | 253473 |
| phulka | 0.9347 | 0.9665 | 0.9660 | 2592655 |
| raita | 0.9117 | 0.9208 | 0.9892 | 269456 |
| rajma | 0.9135 | 0.9438 | 0.9660 | 459259 |
| rasam | 0.0000 | 0.0000 | 0.0000 | 0 |
| salad | 0.8665 | 0.9188 | 0.9383 | 2023418 |
| sambar | 0.8753 | 0.9090 | 0.9594 | 1147991 |
| steamed-rice | 0.8878 | 0.9419 | 0.9393 | 6633435 |
| tomato-pappu | 0.5613 | 0.7545 | 0.6868 | 489167 |
| veg-dum-briyani | 0.8393 | 0.8719 | 0.9574 | 361499 |
| veg-pulao | 0.8749 | 0.9294 | 0.9372 | 1093037 |
| Watermelon | 0.8409 | 0.8602 | 0.9741 | 921612 |
| Papaya | 0.8777 | 0.9145 | 0.9561 | 503018 |
| Banana | 0.9262 | 0.9537 | 0.9699 | 1106964 |
| Muskmelon | 0.5450 | 0.5542 | 0.9705 | 225860 |

## Representative image-only predictions

![Integrated DEV prediction: visuals/view_001.png](visuals/view_001.png)

![Integrated DEV prediction: visuals/view_055.png](visuals/view_055.png)

![Integrated DEV prediction: visuals/view_108.png](visuals/view_108.png)

## Limits and interpretation

Connected regions are semantic proxies, not instances. Same-class portions may merge and annotation breaks may fragment a class. The learned WED weight head is trained/evaluated in its existing WED setting and may not generalize to canteen captures; its output is an estimate with a broad model uncertainty, not a scale measurement. With no marker the prototype does not claim metric depth or geometry-derived mass. Six manually weighed ArUco groups and all other protected evaluation data remain unused here.

Existing renderer-grounded calibration/geometry results are in `renderer_depth_geometry_report.md`; the frozen segmentation component results are in `../wed_native_segmentation/dev_report.md`.
