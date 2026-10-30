# AI-ServicesBB Food Waste diagnostic results

Dataset: `AI-ServicesBB/food-waste-dataset`, revision `f008d0c7b41ea4408b66bd1b7bb9ecd58b70349d`; author-stated CC BY 4.0 (cite [author repo](https://github.com/aihpi/pilotproject-food-waste) and [dataset card](https://huggingface.co/datasets/AI-ServicesBB/food-waste-dataset)).
This is a current-pipeline cross-domain `test` run; it is not a model-selection claim.
The author official `test` split was evaluated once and is permanently closed to development.
Ground truth is food-only sum of `Menge_Rückläufer`. Null predictions are abstentions
and are excluded from grams error; they are reported separately, not converted to zero.
All metrics are descriptive over repeated views grouped by receipt.

## Per-receipt score

| Receipt | True food g | Views | Numeric | Abstain | Mean predicted g (numeric only) | Mean signed error g | MAE g | Numeric min–max g | Spread % of true | Direction |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 538369 | 100.0 | 40 | 25 | 15 | 180.1 | 80.1 | 80.9 | 92.4–291.8 | 199.4 | over |
| 538642 | 114.0 | 40 | 14 | 26 | 139.6 | 25.6 | 44.9 | 82.3–307.4 | 197.5 | over |
| 539002 | 88.0 | 40 | 0 | 40 | — | — | — | — | — | no numeric output |
| 539006 | 46.0 | 40 | 28 | 12 | 88.5 | 42.5 | 42.5 | 51.3–166.9 | 251.3 | over |

## Multi-item mask overlap audit

A pair is overlap-flagged when IoU > 0.50. The existing dedupe threshold is 0.70, so 0.50–<0.70 pairs are retained by that threshold. The duplicate-drop calculation below is hypothetical and does not alter any recorded prediction.

| Receipt | Row | Predicted g | Top food area px | Sum item area px | Area ratio | IoUs | Pairs 0.50–<0.70 | Flagged item grams | Flagged % total | Hypothetical total after drop g | Delta g |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 538369 | 1 | 188.9 | 1865707 | 3620209 | 1.940 | 0-1:0.695 | 1 | 188.9 | 100.0 | 94.8 | -94.1 |
| 538369 | 4 | 206.7 | 2303741 | 3067635 | 1.332 | 0-1:0.514 | 1 | 206.7 | 100.0 | 103.5 | -103.2 |
| 538369 | 5 | 181.3 | 2290574 | 3071036 | 1.341 | 0-1:0.449 | 0 | 0.0 | 0.0 | 181.3 | 0.0 |
| 538369 | 6 | 181.9 | 2150475 | 3421966 | 1.591 | 0-1:0.608 | 1 | 181.9 | 100.0 | 91.3 | -90.6 |
| 538369 | 7 | 196.8 | 2295701 | 3469265 | 1.511 | 0-1:0.637 | 1 | 196.8 | 100.0 | 98.4 | -98.4 |
| 538369 | 8 | 192.5 | 2247595 | 3075680 | 1.368 | 0-1:0.526 | 1 | 192.5 | 100.0 | 96.5 | -96.0 |
| 538369 | 10 | 284.7 | 2123515 | 4976793 | 2.344 | 0-1:0.682, 0-2:0.640, 1-2:0.430 | 2 | 284.7 | 100.0 | 95.8 | -188.9 |
| 538369 | 13 | 184.0 | 551197 | 3195257 | 5.797 | 0-1:0.491 | 0 | 184.0 | 100.0 | 184.0 | 0.0 |
| 538369 | 14 | 198.8 | 546622 | 3195510 | 5.846 | 0-1:0.605 | 1 | 198.7 | 99.9 | 99.4 | -99.4 |
| 538369 | 15 | 92.4 | 546845 | 3042720 | 5.564 | 0-1:0.399 | 0 | unknown (known 92.4 g; 1 item grams null) | — | — | — |
| 538369 | 16 | 200.6 | 574743 | 3414600 | 5.941 | 0-1:0.681 | 1 | 200.6 | 100.0 | 100.3 | -100.3 |
| 538369 | 17 | 195.0 | 546274 | 3159567 | 5.784 | 0-1:0.473 | 0 | 194.9 | 99.9 | 194.9 | -0.1 |
| 538369 | 18 | 199.1 | 77855 | 3273595 | 42.047 | 0-1:0.684 | 1 | 199.1 | 100.0 | 99.6 | -99.5 |
| 538369 | 19 | 291.8 | 36966 | 3190423 | 86.307 | 0-1:0.256, 0-2:0.007, 1-2:0.413 | 0 | 291.8 | 100.0 | 291.8 | 0.0 |
| 538369 | 25 | 185.6 | 446648 | 2960880 | 6.629 | 0-1:0.366 | 0 | 185.5 | 99.9 | 185.5 | -0.1 |
| 538369 | 26 | 183.9 | 338100 | 3203226 | 9.474 | 0-1:0.553 | 1 | 183.9 | 100.0 | 92.9 | -91.0 |
| 538369 | 28 | 215.4 | 48419 | 3192918 | 65.943 | 0-1:0.578 | 1 | 215.5 | 100.0 | 107.8 | -107.6 |
| 538369 | 29 | 194.9 | 33492 | 3334956 | 99.575 | 0-1:0.558 | 1 | 194.8 | 99.9 | 97.9 | -97.0 |
| 538369 | 30 | 204.8 | 201769 | 3283188 | 16.272 | 0-1:0.684 | 1 | 204.8 | 100.0 | 102.8 | -102.0 |
| 538369 | 32 | 203.8 | 365563 | 3378804 | 9.243 | 0-1:0.700 | 1 | 203.8 | 100.0 | 102.2 | -101.6 |
| 538642 | 40 | 276.8 | 1180065 | 4845154 | 4.106 | 0-1:0.663, 0-2:0.593, 1-2:0.317 | 2 | 276.7 | 100.0 | 92.5 | -184.3 |
| 538642 | 48 | 182.8 | 837611 | 3030442 | 3.618 | 0-1:0.377 | 0 | 182.8 | 100.0 | 182.8 | 0.0 |
| 538642 | 49 | 115.1 | 1460579 | 4780326 | 3.273 | 0-1:0.592, 0-2:0.606, 1-2:0.298 | 2 | unknown (known 115.1 g; 2 item grams null) | — | 115.1 | 0.0 |
| 538642 | 52 | 180.8 | 802888 | 3079525 | 3.836 | 0-1:0.383 | 0 | 180.8 | 100.0 | 180.8 | 0.0 |
| 538642 | 53 | 307.4 | 645727 | 4782664 | 7.407 | 0-1:0.662, 0-2:0.451, 1-2:0.189 | 1 | 307.4 | 100.0 | 204.7 | -102.7 |
| 538642 | 58 | 96.0 | 2565310 | 6647891 | 2.591 | 0-1:0.689, 0-2:0.540, 0-3:0.596, 1-2:0.633, 1-3:0.501, 2-3:0.245 | 5 | unknown (known 96.0 g; 3 item grams null) | — | 96.0 | 0.0 |
| 538642 | 62 | 102.5 | 376637 | 3629068 | 9.635 | 0-1:0.632 | 1 | unknown (known 102.5 g; 1 item grams null) | — | 102.5 | 0.0 |
| 539006 | 129 | 135.4 | 2021287 | 3441629 | 1.703 | 0-1:0.594 | 1 | 135.4 | 100.0 | 68.9 | -66.5 |
| 539006 | 133 | 166.9 | 2083068 | 2179363 | 1.046 | 0-1:0.048 | 0 | 0.0 | 0.0 | 166.9 | 0.0 |
| 539006 | 135 | 161.7 | 2082234 | 3511130 | 1.686 | 0-1:0.651 | 1 | 161.7 | 100.0 | 81.2 | -80.5 |
- Receipt 538369: 20 audited multi-item views; mean flagged grams 195.2 g across fully known rows; 1 flagged item gram values were null. Hypothetical duplicate-drop mean total is 127.4 g over 19 calculable views (true 100.0 g).
- Receipt 538642: 7 audited multi-item views; mean flagged grams 236.9 g across fully known rows; 6 flagged item gram values were null. Hypothetical duplicate-drop mean total is 139.2 g over 7 calculable views (true 114.0 g).
- Receipt 539006: 3 audited multi-item views; mean flagged grams 99.0 g across fully known rows (64.0% of their mean predicted total); 0 flagged item gram values were null. Hypothetical duplicate-drop mean total is 105.7 g over 3 calculable views (true 46.0 g).

Numeric coverage: 67/160 views; abstentions: 93/160.
Across numeric views only (not plate-independent): mean signed error 53.0 g, MAE 57.3 g.

## Receipt labels and unmatched components

Exact case-insensitive string equality is the only component match used here; no fuzzy pairing.

- Receipt 538369: ground-truth components: Kartoffelpüree 54.0 g; Wirsing 24.0 g; Zwiebel 0.0 g; Helle Sauce 22.0 g; Fleischbällchen gebrüht 0.0 g.
  - Top-level classifier labels per image: {'vegetable_rice': 25, 'ABSTAIN': 15}.
  - Item classifier labels per emitted item: {'vegetable_rice': 46, 'UNLABELED': 1}.
  - Exact matched components: none; unmatched ground-truth components: ['Kartoffelpüree', 'Wirsing', 'Zwiebel', 'Helle Sauce', 'Fleischbällchen gebrüht'].
- Receipt 538642: ground-truth components: Linseneintopf 91.0 g; Schinken Mettwurst 23.0 g.
  - Top-level classifier labels per image: {'vegetable_rice': 14, 'ABSTAIN': 26}.
  - Item classifier labels per emitted item: {'vegetable_rice': 20, 'UNLABELED': 6}.
  - Exact matched components: none; unmatched ground-truth components: ['Linseneintopf', 'Schinken Mettwurst'].
- Receipt 539002: ground-truth components: Kartoffeln 0.0 g; Sauerkraut 48.0 g; Schweinenackenbraten 33.0 g; Braune Sauce 7.0 g.
  - Top-level classifier labels per image: {'ABSTAIN': 40}.
  - Item classifier labels per emitted item: {}.
  - Exact matched components: none; unmatched ground-truth components: ['Kartoffeln', 'Sauerkraut', 'Schweinenackenbraten', 'Braune Sauce'].
- Receipt 539006: ground-truth components: Reibekuchen 46.0 g; Apfelmus 0.0 g.
  - Top-level classifier labels per image: {'vegetable_rice': 28, 'ABSTAIN': 12}.
  - Item classifier labels per emitted item: {'vegetable_rice': 31}.
  - Exact matched components: none; unmatched ground-truth components: ['Reibekuchen', 'Apfelmus'].

## Per-image outputs

`pred−true` and percent error are shown only when the pipeline returned grams.

| Receipt | Row | Verdict | Anchor | Pred g | True g | Signed g | Error % | Dish label | Reason / classifier evidence |
|---:|---:|---|---|---:|---:|---:|---:|---|---|
| 538369 | 0 | FAIL | prior | 108.5 | 100.0 | 8.5 | 8.5 | vegetable_rice | gallery match vegetable_rice=0.828 >= 0.80 |
| 538369 | 1 | FAIL | prior | 188.9 | 100.0 | 88.9 | 88.9 | vegetable_rice | gallery match vegetable_rice=0.827 >= 0.80 |
| 538369 | 2 | FAIL | prior | 102.7 | 100.0 | 2.7 | 2.7 | vegetable_rice | gallery match vegetable_rice=0.817 >= 0.80 |
| 538369 | 3 | FAIL | prior | 102.5 | 100.0 | 2.5 | 2.5 | vegetable_rice | gallery match vegetable_rice=0.820 >= 0.80 |
| 538369 | 4 | FAIL | prior | 206.7 | 100.0 | 106.7 | 106.7 | vegetable_rice | gallery match vegetable_rice=0.825 >= 0.80 |
| 538369 | 5 | FAIL | prior | 181.3 | 100.0 | 81.3 | 81.3 | vegetable_rice | gallery match vegetable_rice=0.820 >= 0.80 |
| 538369 | 6 | FAIL | prior | 181.9 | 100.0 | 81.9 | 81.9 | vegetable_rice | gallery match vegetable_rice=0.826 >= 0.80 |
| 538369 | 7 | FAIL | prior | 196.8 | 100.0 | 96.8 | 96.8 | vegetable_rice | gallery match vegetable_rice=0.821 >= 0.80 |
| 538369 | 8 | FAIL | prior | 192.5 | 100.0 | 92.5 | 92.5 | vegetable_rice | gallery match vegetable_rice=0.804 >= 0.80 |
| 538369 | 9 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.792 < 0.80 |
| 538369 | 10 | FAIL | prior | 284.7 | 100.0 | 184.7 | 184.7 | vegetable_rice | gallery match vegetable_rice=0.809 >= 0.80 |
| 538369 | 11 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.794 < 0.80 |
| 538369 | 12 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.799 < 0.80 |
| 538369 | 13 | FAIL | prior | 184.0 | 100.0 | 84.0 | 84.0 | vegetable_rice | gallery match vegetable_rice=0.803 >= 0.80 |
| 538369 | 14 | FAIL | prior | 198.8 | 100.0 | 98.8 | 98.8 | vegetable_rice | gallery match vegetable_rice=0.815 >= 0.80 |
| 538369 | 15 | FAIL | prior | 92.4 | 100.0 | -7.6 | -7.6 | vegetable_rice | gallery match vegetable_rice=0.805 >= 0.80 |
| 538369 | 16 | FAIL | prior | 200.6 | 100.0 | 100.6 | 100.6 | vegetable_rice | gallery match vegetable_rice=0.815 >= 0.80 |
| 538369 | 17 | FAIL | prior | 195.0 | 100.0 | 95.0 | 95.0 | vegetable_rice | gallery match vegetable_rice=0.803 >= 0.80 |
| 538369 | 18 | FAIL | prior | 199.1 | 100.0 | 99.1 | 99.1 | vegetable_rice | gallery match vegetable_rice=0.818 >= 0.80 |
| 538369 | 19 | FAIL | prior | 291.8 | 100.0 | 191.8 | 191.8 | vegetable_rice | gallery match vegetable_rice=0.803 >= 0.80 |
| 538369 | 20 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.791 < 0.80 |
| 538369 | 21 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.791 < 0.80 |
| 538369 | 22 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.792 < 0.80 |
| 538369 | 23 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.782 < 0.80 |
| 538369 | 24 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.797 < 0.80 |
| 538369 | 25 | FAIL | prior | 185.6 | 100.0 | 85.6 | 85.6 | vegetable_rice | gallery match vegetable_rice=0.802 >= 0.80 |
| 538369 | 26 | FAIL | prior | 183.9 | 100.0 | 83.9 | 83.9 | vegetable_rice | gallery match vegetable_rice=0.804 >= 0.80 |
| 538369 | 27 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.774 < 0.80 |
| 538369 | 28 | FAIL | prior | 215.4 | 100.0 | 115.4 | 115.4 | vegetable_rice | gallery match vegetable_rice=0.808 >= 0.80 |
| 538369 | 29 | FAIL | prior | 194.9 | 100.0 | 94.9 | 94.9 | vegetable_rice | gallery match vegetable_rice=0.809 >= 0.80 |
| 538369 | 30 | FAIL | prior | 204.8 | 100.0 | 104.8 | 104.8 | vegetable_rice | gallery match vegetable_rice=0.813 >= 0.80 |
| 538369 | 31 | FAIL | prior | 108.2 | 100.0 | 8.2 | 8.2 | vegetable_rice | gallery match vegetable_rice=0.800 >= 0.80 |
| 538369 | 32 | FAIL | prior | 203.8 | 100.0 | 103.8 | 103.8 | vegetable_rice | gallery match vegetable_rice=0.805 >= 0.80 |
| 538369 | 33 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.800 < 0.80 |
| 538369 | 34 | FAIL | prior | 97.7 | 100.0 | -2.3 | -2.3 | vegetable_rice | gallery match vegetable_rice=0.801 >= 0.80 |
| 538369 | 35 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.794 < 0.80 |
| 538369 | 36 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match payasam=0.762 < 0.80 |
| 538369 | 37 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.758 < 0.80 |
| 538369 | 38 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match payasam=0.748 < 0.80 |
| 538369 | 39 | cannot_verify | prior | — | 100.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.756 < 0.80 |
| 538642 | 40 | FAIL | prior | 276.8 | 114.0 | 162.8 | 142.8 | vegetable_rice | gallery match vegetable_rice=0.802 >= 0.80 |
| 538642 | 41 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.797 < 0.80 |
| 538642 | 42 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.797 < 0.80 |
| 538642 | 43 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.785 < 0.80 |
| 538642 | 44 | FAIL | prior | 82.3 | 114.0 | -31.7 | -27.8 | vegetable_rice | gallery match vegetable_rice=0.804 >= 0.80 |
| 538642 | 45 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.795 < 0.80 |
| 538642 | 46 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.794 < 0.80 |
| 538642 | 47 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.787 < 0.80 |
| 538642 | 48 | FAIL | prior | 182.8 | 114.0 | 68.8 | 60.4 | vegetable_rice | gallery match vegetable_rice=0.802 >= 0.80 |
| 538642 | 49 | FAIL | prior | 115.1 | 114.0 | 1.1 | 1.0 | vegetable_rice | gallery match vegetable_rice=0.803 >= 0.80 |
| 538642 | 50 | FAIL | prior | 103.4 | 114.0 | -10.6 | -9.3 | vegetable_rice | gallery match vegetable_rice=0.803 >= 0.80 |
| 538642 | 51 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.781 < 0.80 |
| 538642 | 52 | FAIL | prior | 180.8 | 114.0 | 66.8 | 58.6 | vegetable_rice | gallery match vegetable_rice=0.811 >= 0.80 |
| 538642 | 53 | BORDERLINE | prior | 307.4 | 114.0 | 193.4 | 169.6 | vegetable_rice | gallery match vegetable_rice=0.809 >= 0.80 |
| 538642 | 54 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.799 < 0.80 |
| 538642 | 55 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.792 < 0.80 |
| 538642 | 56 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.794 < 0.80 |
| 538642 | 57 | FAIL | prior | 111.4 | 114.0 | -2.6 | -2.3 | vegetable_rice | gallery match vegetable_rice=0.801 >= 0.80 |
| 538642 | 58 | FAIL | prior | 96.0 | 114.0 | -18.0 | -15.8 | vegetable_rice | gallery match vegetable_rice=0.805 >= 0.80 |
| 538642 | 59 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.781 < 0.80 |
| 538642 | 60 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.797 < 0.80 |
| 538642 | 61 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.793 < 0.80 |
| 538642 | 62 | FAIL | prior | 102.5 | 114.0 | -11.5 | -10.1 | vegetable_rice | gallery match vegetable_rice=0.810 >= 0.80 |
| 538642 | 63 | FAIL | prior | 114.0 | 114.0 | 0.0 | 0.0 | vegetable_rice | gallery match vegetable_rice=0.811 >= 0.80 |
| 538642 | 64 | FAIL | prior | 89.7 | 114.0 | -24.3 | -21.3 | vegetable_rice | gallery match vegetable_rice=0.805 >= 0.80 |
| 538642 | 65 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.766 < 0.80 |
| 538642 | 66 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.796 < 0.80 |
| 538642 | 67 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.760 < 0.80 |
| 538642 | 68 | FAIL | prior | 98.5 | 114.0 | -15.5 | -13.6 | vegetable_rice | gallery match vegetable_rice=0.803 >= 0.80 |
| 538642 | 69 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.793 < 0.80 |
| 538642 | 70 | FAIL | prior | 93.2 | 114.0 | -20.8 | -18.2 | vegetable_rice | gallery match vegetable_rice=0.801 >= 0.80 |
| 538642 | 71 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.797 < 0.80 |
| 538642 | 72 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.784 < 0.80 |
| 538642 | 73 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.779 < 0.80 |
| 538642 | 74 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.778 < 0.80 |
| 538642 | 75 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.782 < 0.80 |
| 538642 | 76 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.737 < 0.80 |
| 538642 | 77 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.734 < 0.80 |
| 538642 | 78 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.749 < 0.80 |
| 538642 | 79 | cannot_verify | prior | — | 114.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.733 < 0.80 |
| 539002 | 80 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.765 < 0.80 |
| 539002 | 81 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.782 < 0.80 |
| 539002 | 82 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.734 < 0.80 |
| 539002 | 83 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.780 < 0.80 |
| 539002 | 84 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.773 < 0.80 |
| 539002 | 85 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.782 < 0.80 |
| 539002 | 86 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.744 < 0.80 |
| 539002 | 87 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.776 < 0.80 |
| 539002 | 88 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.755 < 0.80 |
| 539002 | 89 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.759 < 0.80 |
| 539002 | 90 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.717 < 0.80 |
| 539002 | 91 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.768 < 0.80 |
| 539002 | 92 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.697 < 0.80 |
| 539002 | 93 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.737 < 0.80 |
| 539002 | 94 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.716 < 0.80 |
| 539002 | 95 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.717 < 0.80 |
| 539002 | 96 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.767 < 0.80 |
| 539002 | 97 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.762 < 0.80 |
| 539002 | 98 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.737 < 0.80 |
| 539002 | 99 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.767 < 0.80 |
| 539002 | 100 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.711 < 0.80 |
| 539002 | 101 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.722 < 0.80 |
| 539002 | 102 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.688 < 0.80 |
| 539002 | 103 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.687 < 0.80 |
| 539002 | 104 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.749 < 0.80 |
| 539002 | 105 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.723 < 0.80 |
| 539002 | 106 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.722 < 0.80 |
| 539002 | 107 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.746 < 0.80 |
| 539002 | 108 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.722 < 0.80 |
| 539002 | 109 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.762 < 0.80 |
| 539002 | 110 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.697 < 0.80 |
| 539002 | 111 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.661 < 0.80 |
| 539002 | 112 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.769 < 0.80 |
| 539002 | 113 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.749 < 0.80 |
| 539002 | 114 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.746 < 0.80 |
| 539002 | 115 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.762 < 0.80 |
| 539002 | 116 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.756 < 0.80 |
| 539002 | 117 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.753 < 0.80 |
| 539002 | 118 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.751 < 0.80 |
| 539002 | 119 | cannot_verify | prior | — | 88.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.738 < 0.80 |
| 539006 | 120 | FAIL | prior | 79.8 | 46.0 | 33.8 | 73.5 | vegetable_rice | gallery match vegetable_rice=0.817 >= 0.80 |
| 539006 | 121 | FAIL | prior | 71.8 | 46.0 | 25.8 | 56.1 | vegetable_rice | gallery match vegetable_rice=0.807 >= 0.80 |
| 539006 | 122 | FAIL | prior | 77.3 | 46.0 | 31.3 | 68.0 | vegetable_rice | gallery match vegetable_rice=0.807 >= 0.80 |
| 539006 | 123 | FAIL | prior | 74.6 | 46.0 | 28.6 | 62.2 | vegetable_rice | gallery match vegetable_rice=0.831 >= 0.80 |
| 539006 | 124 | FAIL | prior | 51.3 | 46.0 | 5.3 | 11.5 | vegetable_rice | gallery match vegetable_rice=0.823 >= 0.80 |
| 539006 | 125 | FAIL | prior | 54.9 | 46.0 | 8.9 | 19.3 | vegetable_rice | gallery match vegetable_rice=0.835 >= 0.80 |
| 539006 | 126 | FAIL | prior | 52.0 | 46.0 | 6.0 | 13.0 | vegetable_rice | gallery match vegetable_rice=0.815 >= 0.80 |
| 539006 | 127 | FAIL | prior | 57.6 | 46.0 | 11.6 | 25.2 | vegetable_rice | gallery match vegetable_rice=0.828 >= 0.80 |
| 539006 | 128 | FAIL | prior | 86.3 | 46.0 | 40.3 | 87.6 | vegetable_rice | gallery match vegetable_rice=0.832 >= 0.80 |
| 539006 | 129 | FAIL | prior | 135.4 | 46.0 | 89.4 | 194.3 | vegetable_rice | gallery match vegetable_rice=0.801 >= 0.80 |
| 539006 | 130 | FAIL | prior | 85.1 | 46.0 | 39.1 | 85.0 | vegetable_rice | gallery match vegetable_rice=0.817 >= 0.80 |
| 539006 | 131 | FAIL | prior | 73.4 | 46.0 | 27.4 | 59.6 | vegetable_rice | gallery match vegetable_rice=0.820 >= 0.80 |
| 539006 | 132 | FAIL | prior | 92.6 | 46.0 | 46.6 | 101.3 | vegetable_rice | gallery match vegetable_rice=0.828 >= 0.80 |
| 539006 | 133 | FAIL | prior | 166.9 | 46.0 | 120.9 | 262.8 | vegetable_rice | gallery match vegetable_rice=0.829 >= 0.80 |
| 539006 | 134 | FAIL | prior | 80.6 | 46.0 | 34.6 | 75.2 | vegetable_rice | gallery match vegetable_rice=0.804 >= 0.80 |
| 539006 | 135 | FAIL | prior | 161.7 | 46.0 | 115.7 | 251.5 | vegetable_rice | gallery match vegetable_rice=0.817 >= 0.80 |
| 539006 | 136 | FAIL | prior | 97.7 | 46.0 | 51.7 | 112.4 | vegetable_rice | gallery match vegetable_rice=0.837 >= 0.80 |
| 539006 | 137 | FAIL | prior | 81.7 | 46.0 | 35.7 | 77.6 | vegetable_rice | gallery match vegetable_rice=0.816 >= 0.80 |
| 539006 | 138 | FAIL | prior | 92.6 | 46.0 | 46.6 | 101.3 | vegetable_rice | gallery match vegetable_rice=0.813 >= 0.80 |
| 539006 | 139 | FAIL | prior | 83.4 | 46.0 | 37.4 | 81.3 | vegetable_rice | gallery match vegetable_rice=0.813 >= 0.80 |
| 539006 | 140 | FAIL | prior | 96.3 | 46.0 | 50.3 | 109.3 | vegetable_rice | gallery match vegetable_rice=0.836 >= 0.80 |
| 539006 | 141 | FAIL | prior | 79.8 | 46.0 | 33.8 | 73.5 | vegetable_rice | gallery match vegetable_rice=0.824 >= 0.80 |
| 539006 | 142 | FAIL | prior | 86.2 | 46.0 | 40.2 | 87.4 | vegetable_rice | gallery match vegetable_rice=0.813 >= 0.80 |
| 539006 | 143 | FAIL | prior | 75.0 | 46.0 | 29.0 | 63.0 | vegetable_rice | gallery match vegetable_rice=0.812 >= 0.80 |
| 539006 | 144 | FAIL | prior | 95.9 | 46.0 | 49.9 | 108.5 | vegetable_rice | gallery match vegetable_rice=0.805 >= 0.80 |
| 539006 | 145 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.792 < 0.80 |
| 539006 | 146 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.742 < 0.80 |
| 539006 | 147 | FAIL | prior | 77.3 | 46.0 | 31.3 | 68.0 | vegetable_rice | gallery match vegetable_rice=0.810 >= 0.80 |
| 539006 | 148 | FAIL | prior | 97.4 | 46.0 | 51.4 | 111.7 | vegetable_rice | gallery match vegetable_rice=0.810 >= 0.80 |
| 539006 | 149 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.755 < 0.80 |
| 539006 | 150 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.737 < 0.80 |
| 539006 | 151 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.768 < 0.80 |
| 539006 | 152 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.792 < 0.80 |
| 539006 | 153 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.797 < 0.80 |
| 539006 | 154 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.766 < 0.80 |
| 539006 | 155 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.782 < 0.80 |
| 539006 | 156 | FAIL | prior | 113.4 | 46.0 | 67.4 | 146.5 | vegetable_rice | gallery match vegetable_rice=0.815 >= 0.80 |
| 539006 | 157 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.784 < 0.80 |
| 539006 | 158 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.740 < 0.80 |
| 539006 | 159 | cannot_verify | prior | — | 46.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.792 < 0.80 |

## Mask overlap audit

No separate overlay was rendered for phase `test`; visual observations are limited to the initial report.
Across 30 multi-item views, item-area-sum/top-mask ratios span 1.046–99.575; 28 pairs are in the existing dedupe-pass band 0.50–<0.70; 28 images have at least one overlap/area flag.
Height above a base plane cannot be assessed from this mask-only phase; its numeric outputs use the prior learned-weight route.

## Run observations

`PASS`, `BORDERLINE`, and `FAIL` are nutrient-compliance verdicts; they are not mass-accuracy gates.
Verdicts: {'FAIL': 66, 'cannot_verify': 93, 'BORDERLINE': 1}. Median end-to-end time per image: 0.90 s; numeric-output median 4.70 s; abstention median 0.49 s; first image 30.44 s.
The persisted raw JSONL has per-stage timings, full pipeline reasons, portions, item-mask metadata, and item labels. The separate mask-audit JSONL contains replayed mask areas, flags and pairwise IoUs.


## Exact-match and leakage checks

Largest absolute-error output: receipt 538642 row 53, 307.4 g vs 114.0 g (signed +193.4 g; verdict `BORDERLINE`).
Exact rounded total matches: receipt 538642 row 63 (114.0 g; raw head slots {'36': 113.95}).
These are rounded output matches, not evidence of per-component correctness; inspect the item/classification and source receipt before interpreting them.
Leakage check: the runner passes only image pixels, EXIF, day, band, and serving style to `pipeline.analyze`; it attaches ground-truth weights/components to the JSONL after inference. The run records pipeline code SHA-256 `f38aebbf137f391000decafa505e2307aa807511491c5e8de50cf7b03914c000`. No target leakage is evident at this call boundary.

## Interpretation limits

This `test` run covers 4 receipt groups from the author `test` split. No labels were passed to inference. German canteen leftovers are a cross-domain input; a rejection is a coverage result, not a zero-weight error. The official test split is evaluation-only and must not inform development.
