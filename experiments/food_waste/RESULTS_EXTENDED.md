# AI-ServicesBB Food Waste diagnostic results

Dataset: `AI-ServicesBB/food-waste-dataset`, revision `f008d0c7b41ea4408b66bd1b7bb9ecd58b70349d`; author-stated CC BY 4.0 (cite [author repo](https://github.com/aihpi/pilotproject-food-waste) and [dataset card](https://huggingface.co/datasets/AI-ServicesBB/food-waste-dataset)).
This is a current-pipeline cross-domain DEV diagnostic, not a model-selection claim.
Only the author `train` split was queried; the official `test` split was not fetched.
Ground truth is food-only sum of `Menge_Rückläufer`. Null predictions are abstentions
and are excluded from grams error; they are reported separately, not converted to zero.
All metrics are descriptive over repeated views grouped by receipt.

## Per-receipt score

| Receipt | True food g | Views | Numeric | Abstain | Mean predicted g (numeric only) | Mean signed error g | MAE g | Numeric min–max g | Spread % of true | Direction |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 480654 | 160.0 | 18 | 8 | 10 | 129.6 | -30.4 | 49.7 | 101.7–203.6 | 63.7 | under |
| 480657 | 136.0 | 23 | 0 | 23 | — | — | — | — | — | no numeric output |
| 480658 | 94.0 | 18 | 0 | 18 | — | — | — | — | — | no numeric output |
| 497808 | 80.0 | 23 | 7 | 16 | 143.7 | 63.7 | 63.7 | 122.3–257.5 | 169.0 | over |
| 497810 | 48.0 | 17 | 2 | 15 | 176.9 | 128.9 | 128.9 | 124.8–229.0 | 217.1 | over |
| 497812 | 44.0 | 14 | 10 | 4 | 163.4 | 119.4 | 119.4 | 92.8–311.3 | 496.6 | over |
| 497814 | 34.0 | 12 | 4 | 8 | 128.2 | 94.2 | 94.2 | 121.1–135.0 | 40.9 | over |
| 497821 | 218.0 | 18 | 11 | 7 | 277.5 | 59.5 | 88.0 | 91.1–679.6 | 270.0 | over |

## Multi-item mask overlap audit

A pair is overlap-flagged when IoU > 0.50. The existing dedupe threshold is 0.70, so 0.50–<0.70 pairs are retained by that threshold. The duplicate-drop calculation below is hypothetical and does not alter any recorded prediction.

| Receipt | Row | Predicted g | Top food area px | Sum item area px | Area ratio | IoUs | Pairs 0.50–<0.70 | Flagged item grams | Flagged % total | Hypothetical total after drop g | Delta g |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 480654 | 96 | 193.7 | 20979 | 1488231 | 70.939 | 0-1:0.642 | 1 | 193.7 | 100.0 | 96.9 | -96.8 |
| 480654 | 99 | 203.6 | 303264 | 1655503 | 5.459 | 0-1:0.636 | 1 | 203.6 | 100.0 | 102.6 | -101.0 |
| 480654 | 110 | 110.8 | 1000278 | 1529651 | 1.529 | 0-1:0.638 | 1 | unknown (known 110.8 g; 1 item grams null) | — | 110.8 | 0.0 |
| 497808 | 21 | 257.5 | 18133 | 1552789 | 85.633 | 0-1:0.657 | 1 | 257.6 | 100.0 | 129.3 | -128.2 |
| 497810 | 27 | 229.0 | 13516 | 1463139 | 108.252 | 0-1:0.667 | 1 | 229.0 | 100.0 | 114.6 | -114.4 |
| 497812 | 40 | 237.8 | 1004977 | 1656015 | 1.648 | 0-1:0.662 | 1 | 237.8 | 100.0 | 119.1 | -118.7 |
| 497812 | 42 | 311.3 | 1008786 | 2015914 | 1.998 | 0-1:0.681, 0-2:0.694, 1-2:0.425 | 2 | 311.4 | 100.0 | 103.8 | -207.5 |
| 497812 | 46 | 217.1 | 983172 | 1428721 | 1.453 | 0-1:0.678 | 1 | 217.0 | 100.0 | 108.5 | -108.6 |
| 497812 | 47 | 211.7 | 981534 | 1431627 | 1.459 | 0-1:0.686 | 1 | 211.6 | 100.0 | 106.0 | -105.7 |
| 497821 | 78 | 229.6 | 1021900 | 1527650 | 1.495 | 0-1:0.629 | 1 | unknown (known 229.6 g; 1 item grams null) | — | 229.6 | 0.0 |
| 497821 | 90 | 188.5 | 691509 | 2284765 | 3.304 | 0-1:0.659, 0-2:0.662, 1-2:0.506 | 3 | unknown (known 188.5 g; 1 item grams null) | — | 95.8 | -92.7 |
| 497821 | 92 | 679.6 | 478179 | 1492861 | 3.122 | 0-1:0.628 | 1 | 679.6 | 100.0 | 340.3 | -339.3 |
- Receipt 480654: 3 audited multi-item views; mean flagged grams 198.6 g across fully known rows; 1 flagged item gram values were null. Hypothetical duplicate-drop mean total is 103.4 g over 3 calculable views (true 160.0 g).
- Receipt 497808: 1 audited multi-item views; mean flagged grams 257.6 g across fully known rows (100.0% of their mean predicted total); 0 flagged item gram values were null. Hypothetical duplicate-drop mean total is 129.3 g over 1 calculable views (true 80.0 g).
- Receipt 497810: 1 audited multi-item views; mean flagged grams 229.0 g across fully known rows (100.0% of their mean predicted total); 0 flagged item gram values were null. Hypothetical duplicate-drop mean total is 114.6 g over 1 calculable views (true 48.0 g).
- Receipt 497812: 4 audited multi-item views; mean flagged grams 244.4 g across fully known rows (100.0% of their mean predicted total); 0 flagged item gram values were null. Hypothetical duplicate-drop mean total is 109.3 g over 4 calculable views (true 44.0 g).
- Receipt 497821: 3 audited multi-item views; mean flagged grams 679.6 g across fully known rows; 2 flagged item gram values were null. Hypothetical duplicate-drop mean total is 221.9 g over 3 calculable views (true 218.0 g).

Numeric coverage: 42/143 views; abstentions: 101/143.
Across numeric views only (not plate-independent): mean signed error 64.0 g, MAE 86.7 g.

## Receipt labels and unmatched components

Exact case-insensitive string equality is the only component match used here; no fuzzy pairing.

- Receipt 480654: ground-truth components: Kartoffelpüree 58.0 g; Erbsen 12.0 g; Möhre 14.0 g; Bratenjus 26.0 g; Hähnchen 50.0 g.
  - Top-level classifier labels per image: {'vegetable_rice': 8, 'ABSTAIN': 10}.
  - Item classifier labels per emitted item: {'vegetable_rice': 10, 'UNLABELED': 1}.
  - Exact matched components: none; unmatched ground-truth components: ['Kartoffelpüree', 'Erbsen', 'Möhre', 'Bratenjus', 'Hähnchen'].
- Receipt 480657: ground-truth components: Kartoffeln 42.0 g; Sauerkraut 42.0 g; Braune Sauce 26.0 g; Rostbratwurst 26.0 g.
  - Top-level classifier labels per image: {'ABSTAIN': 23}.
  - Item classifier labels per emitted item: {}.
  - Exact matched components: none; unmatched ground-truth components: ['Kartoffeln', 'Sauerkraut', 'Braune Sauce', 'Rostbratwurst'].
- Receipt 480658: ground-truth components: Kartoffelpüree 32.0 g; Rotkohl 36.0 g; Braune Sauce 12.0 g; Rostbratwurst 14.0 g.
  - Top-level classifier labels per image: {'ABSTAIN': 18}.
  - Item classifier labels per emitted item: {}.
  - Exact matched components: none; unmatched ground-truth components: ['Kartoffelpüree', 'Rotkohl', 'Braune Sauce', 'Rostbratwurst'].
- Receipt 497808: ground-truth components: Kartoffelpüree 0.0 g; Grüne Bohnen 26.0 g; Bratenjus 14.0 g; Hähnchen 40.0 g.
  - Top-level classifier labels per image: {'ABSTAIN': 16, 'vegetable_rice': 7}.
  - Item classifier labels per emitted item: {'vegetable_rice': 8}.
  - Exact matched components: none; unmatched ground-truth components: ['Kartoffelpüree', 'Grüne Bohnen', 'Bratenjus', 'Hähnchen'].
- Receipt 497810: ground-truth components: Eierspätzle 0.0 g; Zucchini 34.0 g; Helle Sauce 14.0 g; Seelachs 0.0 g; Paprika 0.0 g.
  - Top-level classifier labels per image: {'ABSTAIN': 15, 'vegetable_rice': 2}.
  - Item classifier labels per emitted item: {'vegetable_rice': 3}.
  - Exact matched components: none; unmatched ground-truth components: ['Eierspätzle', 'Zucchini', 'Helle Sauce', 'Seelachs', 'Paprika'].
- Receipt 497812: ground-truth components: Semmelknödel 32.0 g; Rotkohl 0.0 g; Rinderbraten 0.0 g; Malzbier-Senf-Sauce 12.0 g.
  - Top-level classifier labels per image: {'vegetable_rice': 10, 'ABSTAIN': 4}.
  - Item classifier labels per emitted item: {'vegetable_rice': 15}.
  - Exact matched components: none; unmatched ground-truth components: ['Semmelknödel', 'Rotkohl', 'Rinderbraten', 'Malzbier-Senf-Sauce'].
- Receipt 497814: ground-truth components: Reis 0.0 g; Pflanzencreme 0.0 g; Möhre 14.0 g; Erbsen 12.0 g; Helle Sauce 8.0 g; Hähnchenstreifen 0.0 g.
  - Top-level classifier labels per image: {'ABSTAIN': 8, 'vegetable_rice': 4}.
  - Item classifier labels per emitted item: {'vegetable_rice': 4}.
  - Exact matched components: none; unmatched ground-truth components: ['Reis', 'Pflanzencreme', 'Möhre', 'Erbsen', 'Helle Sauce', 'Hähnchenstreifen'].
- Receipt 497821: ground-truth components: Kartoffelwürfel 33.0 g; Möhre 24.0 g; Pilze 28.0 g; Linsen 33.0 g; Tomaten-Curry-Sauce 48.0 g; Hähnchenstreifen 52.0 g.
  - Top-level classifier labels per image: {'rice_sambar': 9, 'ABSTAIN': 7, 'vegetable_rice': 2}.
  - Item classifier labels per emitted item: {'rice_sambar': 10, 'UNLABELED': 2, 'vegetable_rice': 3}.
  - Exact matched components: none; unmatched ground-truth components: ['Kartoffelwürfel', 'Möhre', 'Pilze', 'Linsen', 'Tomaten-Curry-Sauce', 'Hähnchenstreifen'].

## Per-image outputs

`pred−true` and percent error are shown only when the pipeline returned grams.

| Receipt | Row | Verdict | Anchor | Pred g | True g | Signed g | Error % | Dish label | Reason / classifier evidence |
|---:|---:|---|---|---:|---:|---:|---:|---|---|
| 480654 | 96 | FAIL | prior | 193.7 | 160.0 | 33.7 | 21.1 | vegetable_rice | gallery match vegetable_rice=0.824 >= 0.80 |
| 480654 | 97 | cannot_verify | prior | — | 160.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.715 < 0.80 |
| 480654 | 98 | cannot_verify | prior | — | 160.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.741 < 0.80 |
| 480654 | 99 | FAIL | prior | 203.6 | 160.0 | 43.6 | 27.2 | vegetable_rice | gallery match vegetable_rice=0.840 >= 0.80 |
| 480654 | 100 | FAIL | prior | 101.7 | 160.0 | -58.3 | -36.4 | vegetable_rice | gallery match vegetable_rice=0.807 >= 0.80 |
| 480654 | 101 | FAIL | prior | 112.2 | 160.0 | -47.8 | -29.9 | vegetable_rice | gallery match vegetable_rice=0.821 >= 0.80 |
| 480654 | 102 | FAIL | prior | 107.3 | 160.0 | -52.7 | -32.9 | vegetable_rice | gallery match vegetable_rice=0.808 >= 0.80 |
| 480654 | 103 | cannot_verify | prior | — | 160.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.749 < 0.80 |
| 480654 | 104 | cannot_verify | prior | — | 160.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.786 < 0.80 |
| 480654 | 105 | cannot_verify | prior | — | 160.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.796 < 0.80 |
| 480654 | 106 | cannot_verify | prior | — | 160.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.765 < 0.80 |
| 480654 | 107 | FAIL | prior | 101.8 | 160.0 | -58.2 | -36.4 | vegetable_rice | gallery match vegetable_rice=0.801 >= 0.80 |
| 480654 | 108 | cannot_verify | prior | — | 160.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.775 < 0.80 |
| 480654 | 109 | cannot_verify | prior | — | 160.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.771 < 0.80 |
| 480654 | 110 | FAIL | prior | 110.8 | 160.0 | -49.2 | -30.8 | vegetable_rice | gallery match vegetable_rice=0.806 >= 0.80 |
| 480654 | 111 | cannot_verify | prior | — | 160.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.761 < 0.80 |
| 480654 | 112 | cannot_verify | prior | — | 160.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.767 < 0.80 |
| 480654 | 113 | FAIL | prior | 105.7 | 160.0 | -54.3 | -33.9 | vegetable_rice | gallery match vegetable_rice=0.829 >= 0.80 |
| 480657 | 132 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.761 < 0.80 |
| 480657 | 133 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.793 < 0.80 |
| 480657 | 134 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.751 < 0.80 |
| 480657 | 135 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.780 < 0.80 |
| 480657 | 136 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match payasam=0.767 < 0.80 |
| 480657 | 137 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.741 < 0.80 |
| 480657 | 138 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.758 < 0.80 |
| 480657 | 139 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.769 < 0.80 |
| 480657 | 140 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.730 < 0.80 |
| 480657 | 141 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match payasam=0.752 < 0.80 |
| 480657 | 142 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match payasam=0.758 < 0.80 |
| 480657 | 143 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match payasam=0.736 < 0.80 |
| 480657 | 144 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.765 < 0.80 |
| 480657 | 145 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.796 < 0.80 |
| 480657 | 146 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match payasam=0.774 < 0.80 |
| 480657 | 147 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.755 < 0.80 |
| 480657 | 148 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.737 < 0.80 |
| 480657 | 149 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.726 < 0.80 |
| 480657 | 150 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.774 < 0.80 |
| 480657 | 151 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.755 < 0.80 |
| 480657 | 152 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.784 < 0.80 |
| 480657 | 153 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.783 < 0.80 |
| 480657 | 154 | cannot_verify | prior | — | 136.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.763 < 0.80 |
| 480658 | 155 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.779 < 0.80 |
| 480658 | 156 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match beetroot-poriyal=0.769 < 0.80 |
| 480658 | 157 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.769 < 0.80 |
| 480658 | 158 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.735 < 0.80 |
| 480658 | 159 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match beetroot-poriyal=0.776 < 0.80 |
| 480658 | 160 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.767 < 0.80 |
| 480658 | 161 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.741 < 0.80 |
| 480658 | 162 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.745 < 0.80 |
| 480658 | 163 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.770 < 0.80 |
| 480658 | 164 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.771 < 0.80 |
| 480658 | 165 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.764 < 0.80 |
| 480658 | 166 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.762 < 0.80 |
| 480658 | 167 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.733 < 0.80 |
| 480658 | 168 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.751 < 0.80 |
| 480658 | 169 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.778 < 0.80 |
| 480658 | 170 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.751 < 0.80 |
| 480658 | 171 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.765 < 0.80 |
| 480658 | 172 | cannot_verify | prior | — | 94.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.778 < 0.80 |
| 497808 | 0 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.791 < 0.80 |
| 497808 | 1 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.765 < 0.80 |
| 497808 | 2 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.785 < 0.80 |
| 497808 | 3 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.768 < 0.80 |
| 497808 | 4 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.782 < 0.80 |
| 497808 | 5 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.783 < 0.80 |
| 497808 | 6 | FAIL | prior | 122.3 | 80.0 | 42.3 | 52.9 | vegetable_rice | gallery match vegetable_rice=0.815 >= 0.80 |
| 497808 | 7 | FAIL | prior | 128.4 | 80.0 | 48.4 | 60.5 | vegetable_rice | gallery match vegetable_rice=0.801 >= 0.80 |
| 497808 | 8 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.764 < 0.80 |
| 497808 | 9 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.794 < 0.80 |
| 497808 | 10 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.773 < 0.80 |
| 497808 | 11 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.760 < 0.80 |
| 497808 | 12 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.772 < 0.80 |
| 497808 | 13 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.762 < 0.80 |
| 497808 | 14 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.751 < 0.80 |
| 497808 | 15 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.773 < 0.80 |
| 497808 | 16 | FAIL | prior | 125.9 | 80.0 | 45.9 | 57.4 | vegetable_rice | gallery match vegetable_rice=0.807 >= 0.80 |
| 497808 | 17 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.793 < 0.80 |
| 497808 | 18 | cannot_verify | prior | — | 80.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.786 < 0.80 |
| 497808 | 19 | FAIL | prior | 122.9 | 80.0 | 42.9 | 53.6 | vegetable_rice | gallery match vegetable_rice=0.811 >= 0.80 |
| 497808 | 20 | FAIL | prior | 124.3 | 80.0 | 44.3 | 55.4 | vegetable_rice | gallery match vegetable_rice=0.807 >= 0.80 |
| 497808 | 21 | FAIL | prior | 257.5 | 80.0 | 177.5 | 221.9 | vegetable_rice | gallery match vegetable_rice=0.815 >= 0.80 |
| 497808 | 22 | FAIL | prior | 124.3 | 80.0 | 44.3 | 55.4 | vegetable_rice | gallery match vegetable_rice=0.801 >= 0.80 |
| 497810 | 23 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.782 < 0.80 |
| 497810 | 24 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.794 < 0.80 |
| 497810 | 25 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.787 < 0.80 |
| 497810 | 26 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.794 < 0.80 |
| 497810 | 27 | FAIL | prior | 229.0 | 48.0 | 181.0 | 377.1 | vegetable_rice | gallery match vegetable_rice=0.803 >= 0.80 |
| 497810 | 28 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.792 < 0.80 |
| 497810 | 29 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.787 < 0.80 |
| 497810 | 30 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.776 < 0.80 |
| 497810 | 31 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.795 < 0.80 |
| 497810 | 32 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.787 < 0.80 |
| 497810 | 33 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.783 < 0.80 |
| 497810 | 34 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.787 < 0.80 |
| 497810 | 35 | FAIL | prior | 124.8 | 48.0 | 76.8 | 160.0 | vegetable_rice | gallery match vegetable_rice=0.805 >= 0.80 |
| 497810 | 36 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.755 < 0.80 |
| 497810 | 37 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.799 < 0.80 |
| 497810 | 38 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.794 < 0.80 |
| 497810 | 39 | cannot_verify | prior | — | 48.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.790 < 0.80 |
| 497812 | 40 | FAIL | prior | 237.8 | 44.0 | 193.8 | 440.5 | vegetable_rice | gallery match vegetable_rice=0.806 >= 0.80 |
| 497812 | 41 | cannot_verify | prior | — | 44.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.798 < 0.80 |
| 497812 | 42 | BORDERLINE | prior | 311.3 | 44.0 | 267.3 | 607.5 | vegetable_rice | gallery match vegetable_rice=0.817 >= 0.80 |
| 497812 | 43 | FAIL | prior | 92.8 | 44.0 | 48.8 | 110.9 | vegetable_rice | gallery match vegetable_rice=0.819 >= 0.80 |
| 497812 | 44 | FAIL | prior | 97.4 | 44.0 | 53.4 | 121.4 | vegetable_rice | gallery match vegetable_rice=0.809 >= 0.80 |
| 497812 | 45 | FAIL | prior | 95.7 | 44.0 | 51.7 | 117.5 | vegetable_rice | gallery match vegetable_rice=0.813 >= 0.80 |
| 497812 | 46 | FAIL | prior | 217.1 | 44.0 | 173.1 | 393.4 | vegetable_rice | gallery match vegetable_rice=0.817 >= 0.80 |
| 497812 | 47 | FAIL | prior | 211.7 | 44.0 | 167.7 | 381.1 | vegetable_rice | gallery match vegetable_rice=0.806 >= 0.80 |
| 497812 | 48 | cannot_verify | prior | — | 44.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.798 < 0.80 |
| 497812 | 49 | FAIL | prior | 175.8 | 44.0 | 131.8 | 299.5 | vegetable_rice | gallery match vegetable_rice=0.821 >= 0.80 |
| 497812 | 50 | FAIL | prior | 95.7 | 44.0 | 51.7 | 117.5 | vegetable_rice | gallery match vegetable_rice=0.804 >= 0.80 |
| 497812 | 51 | FAIL | prior | 99.0 | 44.0 | 55.0 | 125.0 | vegetable_rice | gallery match vegetable_rice=0.807 >= 0.80 |
| 497812 | 52 | cannot_verify | prior | — | 44.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.795 < 0.80 |
| 497812 | 53 | cannot_verify | prior | — | 44.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.795 < 0.80 |
| 497814 | 54 | cannot_verify | prior | — | 34.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.783 < 0.80 |
| 497814 | 55 | FAIL | prior | 121.1 | 34.0 | 87.1 | 256.2 | vegetable_rice | gallery match vegetable_rice=0.809 >= 0.80 |
| 497814 | 56 | FAIL | prior | 135.0 | 34.0 | 101.0 | 297.1 | vegetable_rice | gallery match vegetable_rice=0.801 >= 0.80 |
| 497814 | 57 | cannot_verify | prior | — | 34.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.763 < 0.80 |
| 497814 | 58 | cannot_verify | prior | — | 34.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.790 < 0.80 |
| 497814 | 59 | cannot_verify | prior | — | 34.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.795 < 0.80 |
| 497814 | 60 | FAIL | prior | 125.8 | 34.0 | 91.8 | 270.0 | vegetable_rice | gallery match vegetable_rice=0.809 >= 0.80 |
| 497814 | 61 | FAIL | prior | 131.0 | 34.0 | 97.0 | 285.3 | vegetable_rice | gallery match vegetable_rice=0.810 >= 0.80 |
| 497814 | 62 | cannot_verify | prior | — | 34.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.774 < 0.80 |
| 497814 | 63 | cannot_verify | prior | — | 34.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.779 < 0.80 |
| 497814 | 64 | cannot_verify | prior | — | 34.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.783 < 0.80 |
| 497814 | 65 | cannot_verify | prior | — | 34.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.777 < 0.80 |
| 497821 | 78 | FAIL | prior | 229.6 | 218.0 | 11.6 | 5.3 | rice_sambar | gallery match rice_sambar=0.819 >= 0.80 |
| 497821 | 79 | cannot_verify | prior | — | 218.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.766 < 0.80 |
| 497821 | 80 | cannot_verify | prior | — | 218.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.785 < 0.80 |
| 497821 | 81 | cannot_verify | prior | — | 218.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.776 < 0.80 |
| 497821 | 82 | cannot_verify | prior | — | 218.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.796 < 0.80 |
| 497821 | 83 | FAIL | prior | 269.2 | 218.0 | 51.2 | 23.5 | rice_sambar | gallery match rice_sambar=0.806 >= 0.80 |
| 497821 | 84 | cannot_verify | prior | — | 218.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.790 < 0.80 |
| 497821 | 85 | FAIL | prior | 289.0 | 218.0 | 71.0 | 32.6 | rice_sambar | gallery match rice_sambar=0.808 >= 0.80 |
| 497821 | 86 | FAIL | prior | 260.7 | 218.0 | 42.7 | 19.6 | rice_sambar | gallery match rice_sambar=0.812 >= 0.80 |
| 497821 | 87 | FAIL | prior | 91.1 | 218.0 | -126.9 | -58.2 | vegetable_rice | gallery match vegetable_rice=0.808 >= 0.80 |
| 497821 | 88 | cannot_verify | prior | — | 218.0 | — | — | ABSTAIN | best gallery match rice_sambar=0.781 < 0.80 |
| 497821 | 89 | FAIL | prior | 298.8 | 218.0 | 80.8 | 37.1 | rice_sambar | gallery match rice_sambar=0.825 >= 0.80 |
| 497821 | 90 | FAIL | prior | 188.5 | 218.0 | -29.5 | -13.5 | vegetable_rice | gallery match vegetable_rice=0.827 >= 0.80 |
| 497821 | 91 | FAIL | prior | 226.6 | 218.0 | 8.6 | 3.9 | rice_sambar | gallery match rice_sambar=0.814 >= 0.80 |
| 497821 | 92 | PASS | prior | 679.6 | 218.0 | 461.6 | 211.7 | rice_sambar | gallery match rice_sambar=0.830 >= 0.80 |
| 497821 | 93 | FAIL | prior | 280.1 | 218.0 | 62.1 | 28.5 | rice_sambar | gallery match rice_sambar=0.818 >= 0.80 |
| 497821 | 94 | cannot_verify | prior | — | 218.0 | — | — | ABSTAIN | best gallery match vegetable_rice=0.795 < 0.80 |
| 497821 | 95 | FAIL | prior | 239.7 | 218.0 | 21.7 | 10.0 | rice_sambar | gallery match rice_sambar=0.807 >= 0.80 |

## Mask overlap audit

No separate overlay was rendered for phase `extended`; visual observations are limited to the initial report.
Across 12 multi-item views, item-area-sum/top-mask ratios span 1.453–108.252; 15 pairs are in the existing dedupe-pass band 0.50–<0.70; 12 images have at least one overlap/area flag.
Height above a base plane cannot be assessed from this mask-only phase; its numeric outputs use the prior learned-weight route.

## Run observations

`PASS`, `BORDERLINE`, and `FAIL` are nutrient-compliance verdicts; they are not mass-accuracy gates.
Verdicts: {'FAIL': 40, 'cannot_verify': 101, 'BORDERLINE': 1, 'PASS': 1}. Median end-to-end time per image: 0.46 s; median over all views includes model warm-up and cached steady-state: 0.46 s.
The persisted raw JSONL has per-stage timings, full pipeline reasons, portions, item-mask metadata, and item labels. The separate mask-audit JSONL contains replayed mask areas, flags and pairwise IoUs.

Largest absolute-error view is receipt 497821 row 92: predicted 679.6 g vs 218.0 g (signed +461.6 g), yet verdict `PASS`. Its reason is `No reference card — this photo has no measured scale, so its weight is an estimate (learned model (WED-trained, unvalidated on MDM plates)); the verdict is computed from estimated grams; all mandatory nutrients in pass zone with sufficient coverage`.
Leakage check: the runner calls `pipeline.analyze` with the image, day, band, EXIF and serving style; food-weight labels are attached to the JSONL only after that call returns. This `PASS` is the configured nutrient-zone verdict, not validation of gram accuracy; no target leakage is evident in this path.

## Interpretation limits

This `extended` phase covers 8 receipt groups from the author train split. The system was not tuned against these results. German canteen leftovers are a cross-domain input; a rejection is a coverage result, not a zero-weight error. The four-receipt official test split remains untouched.
