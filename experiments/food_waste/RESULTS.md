# AI-ServicesBB Food Waste diagnostic results

Dataset: `AI-ServicesBB/food-waste-dataset`, revision `f008d0c7b41ea4408b66bd1b7bb9ecd58b70349d`; author-stated CC BY 4.0 (cite [author repo](https://github.com/aihpi/pilotproject-food-waste) and [dataset card](https://huggingface.co/datasets/AI-ServicesBB/food-waste-dataset)).
This is a current-pipeline cross-domain DEV diagnostic, not a model-selection claim.
Only the author `train` split was queried; the official `test` split was not fetched.
Ground truth is food-only sum of `Menge_Rückläufer`. Null predictions are abstentions
and are excluded from grams error; they are reported separately, not converted to zero.
All metrics are descriptive over repeated views grouped by receipt.
The remaining eight train receipts and 143 views are in [the extended report](RESULTS_EXTENDED.md).

## Per-receipt score

| Receipt | True food g | Views | Numeric | Abstain | Mean predicted g (numeric only) | Mean signed error g | MAE g | Numeric min–max g | Spread % of true | Direction |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 480656 | 184.0 | 18 | 0 | 18 | — | — | — | — | — | no numeric output |
| 480659 | 138.0 | 19 | 0 | 19 | — | — | — | — | — | no numeric output |
| 480660 | 140.0 | 23 | 21 | 2 | 177.3 | 37.3 | 56.2 | 90.9–280.3 | 135.3 | over |
| 497816 | 26.0 | 12 | 8 | 4 | 117.0 | 91.0 | 91.0 | 109.0–130.1 | 81.2 | over |

## Multi-item mask overlap audit

A pair is overlap-flagged when IoU > 0.50. The existing dedupe threshold is 0.70, so 0.50–<0.70 pairs are retained by that threshold. The duplicate-drop calculation below is hypothetical and does not alter any recorded prediction.

| Receipt | Row | Predicted g | Top food area px | Sum item area px | Area ratio | IoUs | Pairs 0.50–<0.70 | Flagged item grams | Flagged % total | Hypothetical total after drop g | Delta g |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 480660 | 192 | 178.2 | 11936 | 1633080 | 136.820 | 0-1:0.610 | 1 | 178.2 | 100.0 | 90.0 | -88.2 |
| 480660 | 193 | 178.4 | 34729 | 1667902 | 48.026 | 0-1:0.635 | 1 | 178.4 | 100.0 | 89.8 | -88.6 |
| 480660 | 196 | 185.6 | 842951 | 1645184 | 1.952 | 0-1:0.585 | 1 | 185.6 | 100.0 | 93.8 | -91.8 |
| 480660 | 198 | 247.3 | 36771 | 2284773 | 62.135 | 0-1:0.695, 0-2:0.514, 1-2:0.664 | 3 | 247.4 | 100.0 | 83.6 | -163.7 |
| 480660 | 199 | 165.6 | 110796 | 1670081 | 15.073 | 0-1:0.664 | 1 | 165.6 | 100.0 | 83.2 | -82.4 |
| 480660 | 200 | 252.0 | 39817 | 2326621 | 58.433 | 0-1:0.672, 0-2:0.680, 1-2:0.650 | 3 | 251.9 | 100.0 | 84.9 | -167.1 |
| 480660 | 201 | 189.4 | 184869 | 1640805 | 8.876 | 0-1:0.697 | 1 | 189.4 | 100.0 | 95.0 | -94.4 |
| 480660 | 202 | 280.3 | 591190 | 2307213 | 3.903 | 0-1:0.675, 0-2:0.619, 1-2:0.468 | 2 | 280.2 | 100.0 | 94.1 | -186.2 |
| 480660 | 203 | 169.1 | 45182 | 1376514 | 30.466 | 0-1:0.678 | 1 | 169.1 | 100.0 | 85.1 | -84.0 |
| 480660 | 204 | 187.5 | 222248 | 1464736 | 6.591 | 0-1:0.451 | 0 | 187.5 | 100.0 | 187.5 | 0.0 |
| 480660 | 205 | 196.8 | 815968 | 1701613 | 2.085 | 0-1:0.672 | 1 | 196.8 | 100.0 | 99.3 | -97.5 |
| 480660 | 206 | 191.3 | 50115 | 1348639 | 26.911 | 0-1:0.456 | 0 | 191.2 | 99.9 | 191.2 | -0.1 |
| 480660 | 207 | 180.2 | 832839 | 1710396 | 2.054 | 0-1:0.663 | 1 | 180.2 | 100.0 | 90.8 | -89.4 |
| 480660 | 209 | 191.8 | 853211 | 1721768 | 2.018 | 0-1:0.680 | 1 | 191.8 | 100.0 | 96.3 | -95.5 |
| 480660 | 210 | 263.8 | 870012 | 2426293 | 2.789 | 0-1:0.690, 0-2:0.666, 1-2:0.468 | 2 | 263.8 | 100.0 | 89.0 | -174.8 |
| 480660 | 211 | 164.3 | 44300 | 1522498 | 34.368 | 0-1:0.574 | 1 | 164.3 | 100.0 | 83.4 | -80.9 |
- Receipt 480660: 16 audited multi-item views; mean flagged grams 201.3 g across fully known rows (100.0% of their mean predicted total); 0 flagged item gram values were null. Hypothetical duplicate-drop mean total is 102.3 g over 16 calculable views (true 140.0 g).

Numeric coverage: 29/72 views; abstentions: 43/72.
Across numeric views only (not plate-independent): mean signed error 52.1 g, MAE 65.8 g.

## Receipt labels and unmatched components

Exact case-insensitive string equality is the only component match used here; no fuzzy pairing.

- Receipt 480656: ground-truth components: Kartoffeln 62.0 g; Erbsen 24.0 g; Möhre 38.0 g; Braune Sauce 18.0 g; Hähnchen 42.0 g.
  - Top-level classifier labels per image: {'ABSTAIN': 18}.
  - Item classifier labels per emitted item: {}.
  - Exact matched components: none; unmatched ground-truth components: ['Kartoffeln', 'Erbsen', 'Möhre', 'Braune Sauce', 'Hähnchen'].
- Receipt 480659: ground-truth components: Kartoffeln 30.0 g; Erbsen 12.0 g; Möhre 16.0 g; Schnitzel 48.0 g; Pilze 14.0 g; Sahne 2.0 g; Braune Sauce 16.0 g.
  - Top-level classifier labels per image: {'ABSTAIN': 19}.
  - Item classifier labels per emitted item: {}.
  - Exact matched components: none; unmatched ground-truth components: ['Kartoffeln', 'Erbsen', 'Möhre', 'Schnitzel', 'Pilze', 'Sahne', 'Braune Sauce'].
- Receipt 480660: ground-truth components: Reis 26.0 g; Blumenkohl 34.0 g; Paniertes Fischfilet 54.0 g; Helle Sauce 26.0 g.
  - Top-level classifier labels per image: {'vegetable_rice': 21, 'ABSTAIN': 2}.
  - Item classifier labels per emitted item: {'vegetable_rice': 41}.
  - Exact matched components: none; unmatched ground-truth components: ['Reis', 'Blumenkohl', 'Paniertes Fischfilet', 'Helle Sauce'].
- Receipt 497816: ground-truth components: Reis 0.0 g; Dressing Portion 0.0 g; Eisbergsalat 0.0 g; Krautsalat 0.0 g; Paprika 0.0 g; Sahne 0.0 g; Braune Sauce 0.0 g; Hähnchen 26.0 g.
  - Top-level classifier labels per image: {'ABSTAIN': 4, 'vegetable_rice': 8}.
  - Item classifier labels per emitted item: {'vegetable_rice': 8}.
  - Exact matched components: none; unmatched ground-truth components: ['Reis', 'Dressing Portion', 'Eisbergsalat', 'Krautsalat', 'Paprika', 'Sahne', 'Braune Sauce', 'Hähnchen'].

## Per-image outputs

`pred−true` and percent error are shown only when the pipeline returned grams.

| Receipt | Row | Verdict | Anchor | Pred g | True g | Signed g | Error % | Dish label | Reason / classifier evidence |
|---:|---:|---|---|---:|---:|---:|---:|---|---|
| 480656 | 114 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.731 < 0.80 |
| 480656 | 115 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.714 < 0.80 |
| 480656 | 116 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.762 < 0.80 |
| 480656 | 117 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.719 < 0.80 |
| 480656 | 118 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.756 < 0.80 |
| 480656 | 119 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.759 < 0.80 |
| 480656 | 120 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.739 < 0.80 |
| 480656 | 121 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.731 < 0.80 |
| 480656 | 122 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.735 < 0.80 |
| 480656 | 123 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.756 < 0.80 |
| 480656 | 124 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.743 < 0.80 |
| 480656 | 125 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.737 < 0.80 |
| 480656 | 126 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.721 < 0.80 |
| 480656 | 127 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match aloo-fry=0.722 < 0.80 |
| 480656 | 128 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.729 < 0.80 |
| 480656 | 129 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.745 < 0.80 |
| 480656 | 130 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.741 < 0.80 |
| 480656 | 131 | cannot_verify | prior | — | 184.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.721 < 0.80 |
| 480659 | 173 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.764 < 0.80 |
| 480659 | 174 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.783 < 0.80 |
| 480659 | 175 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.756 < 0.80 |
| 480659 | 176 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match kakarakaya-fry=0.721 < 0.80 |
| 480659 | 177 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match kakarakaya-fry=0.749 < 0.80 |
| 480659 | 178 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.750 < 0.80 |
| 480659 | 179 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.727 < 0.80 |
| 480659 | 180 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.741 < 0.80 |
| 480659 | 181 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.754 < 0.80 |
| 480659 | 182 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.756 < 0.80 |
| 480659 | 183 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match aloo-fry=0.735 < 0.80 |
| 480659 | 184 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match kakarakaya-fry=0.730 < 0.80 |
| 480659 | 185 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match kakarakaya-fry=0.720 < 0.80 |
| 480659 | 186 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match kakarakaya-fry=0.723 < 0.80 |
| 480659 | 187 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.744 < 0.80 |
| 480659 | 188 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match kakarakaya-fry=0.734 < 0.80 |
| 480659 | 189 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.738 < 0.80 |
| 480659 | 190 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.759 < 0.80 |
| 480659 | 191 | cannot_verify | prior | — | 138.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.764 < 0.80 |
| 480660 | 192 | FAIL | prior | 178.2 | 140.0 | 38.2 | 27.3 | vegetable_rice | gallery match vegetable_rice=0.819 >= 0.80 |
| 480660 | 193 | FAIL | prior | 178.4 | 140.0 | 38.4 | 27.4 | vegetable_rice | gallery match vegetable_rice=0.816 >= 0.80 |
| 480660 | 194 | FAIL | prior | 93.1 | 140.0 | -46.9 | -33.5 | vegetable_rice | gallery match vegetable_rice=0.814 >= 0.80 |
| 480660 | 195 | cannot_verify | prior | — | 140.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.775 < 0.80 |
| 480660 | 196 | FAIL | prior | 185.6 | 140.0 | 45.6 | 32.6 | vegetable_rice | gallery match vegetable_rice=0.827 >= 0.80 |
| 480660 | 197 | cannot_verify | prior | — | 140.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.796 < 0.80 |
| 480660 | 198 | FAIL | prior | 247.3 | 140.0 | 107.3 | 76.6 | vegetable_rice | gallery match vegetable_rice=0.816 >= 0.80 |
| 480660 | 199 | FAIL | prior | 165.6 | 140.0 | 25.6 | 18.3 | vegetable_rice | gallery match vegetable_rice=0.828 >= 0.80 |
| 480660 | 200 | FAIL | prior | 252.0 | 140.0 | 112.0 | 80.0 | vegetable_rice | gallery match vegetable_rice=0.809 >= 0.80 |
| 480660 | 201 | FAIL | prior | 189.4 | 140.0 | 49.4 | 35.3 | vegetable_rice | gallery match vegetable_rice=0.820 >= 0.80 |
| 480660 | 202 | FAIL | prior | 280.3 | 140.0 | 140.3 | 100.2 | vegetable_rice | gallery match vegetable_rice=0.828 >= 0.80 |
| 480660 | 203 | FAIL | prior | 169.1 | 140.0 | 29.1 | 20.8 | vegetable_rice | gallery match vegetable_rice=0.835 >= 0.80 |
| 480660 | 204 | FAIL | prior | 187.5 | 140.0 | 47.5 | 33.9 | vegetable_rice | gallery match vegetable_rice=0.827 >= 0.80 |
| 480660 | 205 | FAIL | prior | 196.8 | 140.0 | 56.8 | 40.6 | vegetable_rice | gallery match vegetable_rice=0.828 >= 0.80 |
| 480660 | 206 | FAIL | prior | 191.3 | 140.0 | 51.3 | 36.6 | vegetable_rice | gallery match vegetable_rice=0.820 >= 0.80 |
| 480660 | 207 | FAIL | prior | 180.2 | 140.0 | 40.2 | 28.7 | vegetable_rice | gallery match vegetable_rice=0.817 >= 0.80 |
| 480660 | 208 | FAIL | prior | 122.6 | 140.0 | -17.4 | -12.4 | vegetable_rice | gallery match vegetable_rice=0.822 >= 0.80 |
| 480660 | 209 | FAIL | prior | 191.8 | 140.0 | 51.8 | 37.0 | vegetable_rice | gallery match vegetable_rice=0.818 >= 0.80 |
| 480660 | 210 | FAIL | prior | 263.8 | 140.0 | 123.8 | 88.4 | vegetable_rice | gallery match vegetable_rice=0.827 >= 0.80 |
| 480660 | 211 | FAIL | prior | 164.3 | 140.0 | 24.3 | 17.4 | vegetable_rice | gallery match vegetable_rice=0.821 >= 0.80 |
| 480660 | 212 | FAIL | prior | 99.8 | 140.0 | -40.2 | -28.7 | vegetable_rice | gallery match vegetable_rice=0.823 >= 0.80 |
| 480660 | 213 | FAIL | prior | 90.9 | 140.0 | -49.1 | -35.1 | vegetable_rice | gallery match vegetable_rice=0.819 >= 0.80 |
| 480660 | 214 | FAIL | prior | 95.3 | 140.0 | -44.7 | -31.9 | vegetable_rice | gallery match vegetable_rice=0.830 >= 0.80 |
| 497816 | 66 | cannot_verify | prior | — | 26.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.777 < 0.80 |
| 497816 | 67 | FAIL | prior | 114.5 | 26.0 | 88.5 | 340.4 | vegetable_rice | gallery match vegetable_rice=0.814 >= 0.80 |
| 497816 | 68 | FAIL | prior | 112.0 | 26.0 | 86.0 | 330.8 | vegetable_rice | gallery match vegetable_rice=0.830 >= 0.80 |
| 497816 | 69 | FAIL | prior | 109.0 | 26.0 | 83.0 | 319.2 | vegetable_rice | gallery match vegetable_rice=0.805 >= 0.80 |
| 497816 | 70 | FAIL | prior | 110.4 | 26.0 | 84.4 | 324.6 | vegetable_rice | gallery match vegetable_rice=0.827 >= 0.80 |
| 497816 | 71 | FAIL | prior | 124.8 | 26.0 | 98.8 | 380.0 | vegetable_rice | gallery match vegetable_rice=0.811 >= 0.80 |
| 497816 | 72 | FAIL | prior | 130.1 | 26.0 | 104.1 | 400.4 | vegetable_rice | gallery match vegetable_rice=0.815 >= 0.80 |
| 497816 | 73 | cannot_verify | prior | — | 26.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.790 < 0.80 |
| 497816 | 74 | FAIL | prior | 116.5 | 26.0 | 90.5 | 348.1 | vegetable_rice | gallery match vegetable_rice=0.815 >= 0.80 |
| 497816 | 75 | FAIL | prior | 118.8 | 26.0 | 92.8 | 356.9 | vegetable_rice | gallery match vegetable_rice=0.816 >= 0.80 |
| 497816 | 76 | cannot_verify | prior | — | 26.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.797 < 0.80 |
| 497816 | 77 | cannot_verify | prior | — | 26.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.758 < 0.80 |

## Mask overlap audit

![SAM masks on a representative Food Waste DEV image](overlays/receipt-480660-row-0192.png)
Visual observation for receipt 480660, source row 192: the colored item masks cover most of the plate and overlap, while the cyan top-level mask is small. Numbers: top mask 11936 px; summed item masks 1633080 px; area ratio 136.820; pair IoU 0.610. Across 16 multi-item views, item-area-sum/top-mask ratios span 1.952–136.820; 20 pairs fall in the existing dedupe-pass band 0.50–<0.70.

Hypothesis evidence ratings:
- **(a) Oversized item masks — supports strongly.** In this overlay, the item masks visibly cover plate regions; 16 multi-item views have item-area-sum/top-mask ratios above 1.
- **(b) Plate/table counted as height above the base plane — cannot decide.** Accepted outputs use the prior learned-weight path (`area_cm2` and `mean_h_mm` are null); no height map was produced.
- **(c) Classifier labels non-food crops as dishes — supports for this image.** The item labels are ['vegetable_rice', 'vegetable_rice'], while recorded components are Reis, Blumenkohl, Paniertes Fischfilet, Helle Sauce; the overlay shows each item mask includes extensive plate area.

## Run observations

Verdicts: {'cannot_verify': 43, 'FAIL': 29}. Median end-to-end time per image: 0.85 s; median over all views includes model warm-up and cached steady-state: 0.85 s.
The persisted raw JSONL has per-stage timings, full pipeline reasons, portions, item-mask metadata, and item labels. The separate mask-audit JSONL contains replayed mask areas, flags and pairwise IoUs.

## Interpretation limits

This `initial` phase covers 4 receipt groups from the author train split. The system was not tuned against these results. German canteen leftovers are a cross-domain input; a rejection is a coverage result, not a zero-weight error. The four-receipt official test split remains untouched.
