# LeFood-Set frozen current-pipeline baseline

This is the single pre-registered evaluation on six category-held-out test foods. No category or weight was sent to inference. This is single-food, cross-domain evidence, not a mixed-meal or production claim.

Ground truth uses source `Weight Before Eaten (g)`, described by Mendeley as food mass. The paper says a plate containing food was weighed but does not document tare handling; this unresolved caveat applies to every gram target below.

Dataset split: `test`; images: 143; test food categories: 6; train split read: False; pipeline SHA-256: `f38aebbf137f391000decafa505e2307aa807511491c5e8de50cf7b03914c000`.

## Test-category results

| Food category | True-mass range g | Images | Numeric totals | Abstentions | Dish label outcome |
|---|---:|---:|---:|---:|---|
| Ayam bumbu bistik | 42.0–85.0 | 22 | 0 | 22 | best gallery match mango-pickle=0.734 < 0.80 (2); best gallery match mango-pickle=0.735 < 0.80 (2); best gallery match mango-pickle=0.758 < 0.80 (2) |
| Bali Tahu | 18.0–67.0 | 22 | 0 | 22 | best gallery match vegetable_rice=0.750 < 0.80 (2); best gallery match vegetable_rice=0.747 < 0.80 (2); best gallery match vegetable_rice=0.748 < 0.80 (2) |
| Bubur | 343.0–343.0 | 1 | 0 | 1 | best gallery match curd=0.766 < 0.80 (1) |
| Ikan Acar Kuning | 25.0–62.0 | 20 | 0 | 20 | best gallery match vegetable_rice=0.781 < 0.80 (1); best gallery match kakarakaya-fry=0.740 < 0.80 (1); best gallery match vegetable_rice=0.750 < 0.80 (1) |
| Opor Ayam | 35.0–52.0 | 2 | 0 | 2 | best gallery match vegetable_rice=0.787 < 0.80 (1); best gallery match vegetable_rice=0.783 < 0.80 (1) |
| Tim | 117.0–227.0 | 76 | 0 | 76 | best gallery match vegetable_rice=0.770 < 0.80 (3); best gallery match steamed-rice=0.766 < 0.80 (3); best gallery match curd=0.757 < 0.80 (3) |

Numeric coverage: 0/143; abstentions: 143/143. Dish label outcomes: {'ABSTAIN': 143}. Verdicts: {'cannot_verify': 143}.
No numeric outputs means signed gram error and MAE are undefined on this split; do not convert abstentions to 0 g or score them as zero error.
Median elapsed time: 0.438 s; first image: 27.009 s.

## Per-image record

| Row | Food | True g | Predicted g | Verdict | Anchor | Gallery rejection evidence |
|---:|---|---:|---:|---|---|---|
| 1 | Bubur | 343.0 | — | cannot_verify | prior | best gallery match curd=0.766 < 0.80 |
| 81 | Tim | 154.0 | — | cannot_verify | prior | best gallery match curd=0.759 < 0.80 |
| 82 | Tim | 174.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.772 < 0.80 |
| 83 | Tim | 178.0 | — | cannot_verify | prior | best gallery match curd=0.784 < 0.80 |
| 84 | Tim | 182.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.770 < 0.80 |
| 85 | Tim | 168.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.770 < 0.80 |
| 86 | Tim | 168.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.756 < 0.80 |
| 87 | Tim | 149.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.769 < 0.80 |
| 88 | Tim | 147.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.761 < 0.80 |
| 89 | Tim | 156.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.750 < 0.80 |
| 90 | Tim | 132.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.753 < 0.80 |
| 91 | Tim | 179.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.769 < 0.80 |
| 92 | Tim | 168.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.759 < 0.80 |
| 93 | Tim | 183.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.766 < 0.80 |
| 94 | Tim | 172.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.749 < 0.80 |
| 95 | Tim | 172.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.767 < 0.80 |
| 96 | Tim | 171.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.773 < 0.80 |
| 97 | Tim | 117.0 | — | cannot_verify | prior | best gallery match curd=0.785 < 0.80 |
| 98 | Tim | 189.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.771 < 0.80 |
| 99 | Tim | 227.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.782 < 0.80 |
| 100 | Tim | 123.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.766 < 0.80 |
| 101 | Tim | 152.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.773 < 0.80 |
| 102 | Tim | 183.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.789 < 0.80 |
| 103 | Tim | 183.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.785 < 0.80 |
| 104 | Tim | 167.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.776 < 0.80 |
| 105 | Tim | 145.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.784 < 0.80 |
| 106 | Tim | 190.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.764 < 0.80 |
| 107 | Tim | 175.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.776 < 0.80 |
| 108 | Tim | 173.0 | — | cannot_verify | prior | best gallery match curd=0.770 < 0.80 |
| 109 | Tim | 124.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.788 < 0.80 |
| 110 | Tim | 152.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.759 < 0.80 |
| 111 | Tim | 156.0 | — | cannot_verify | prior | best gallery match curd=0.777 < 0.80 |
| 112 | Tim | 149.0 | — | cannot_verify | prior | best gallery match curd=0.755 < 0.80 |
| 113 | Tim | 129.0 | — | cannot_verify | prior | best gallery match curd=0.745 < 0.80 |
| 114 | Tim | 163.0 | — | cannot_verify | prior | best gallery match curd=0.759 < 0.80 |
| 115 | Tim | 159.0 | — | cannot_verify | prior | best gallery match curd=0.757 < 0.80 |
| 116 | Tim | 168.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.738 < 0.80 |
| 117 | Tim | 162.0 | — | cannot_verify | prior | best gallery match curd=0.756 < 0.80 |
| 118 | Tim | 155.0 | — | cannot_verify | prior | best gallery match curd=0.754 < 0.80 |
| 119 | Tim | 156.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.743 < 0.80 |
| 120 | Tim | 145.0 | — | cannot_verify | prior | best gallery match curd=0.749 < 0.80 |
| 121 | Tim | 152.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.746 < 0.80 |
| 122 | Tim | 150.0 | — | cannot_verify | prior | best gallery match curd=0.757 < 0.80 |
| 123 | Tim | 146.0 | — | cannot_verify | prior | best gallery match curd=0.755 < 0.80 |
| 124 | Tim | 150.0 | — | cannot_verify | prior | best gallery match curd=0.756 < 0.80 |
| 125 | Tim | 136.0 | — | cannot_verify | prior | best gallery match curd=0.756 < 0.80 |
| 126 | Tim | 188.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.760 < 0.80 |
| 127 | Tim | 140.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.765 < 0.80 |
| 128 | Tim | 155.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.766 < 0.80 |
| 130 | Tim | 170.0 | — | cannot_verify | prior | best gallery match curd=0.741 < 0.80 |
| 131 | Tim | 152.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.746 < 0.80 |
| 132 | Tim | 205.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.767 < 0.80 |
| 133 | Tim | 152.0 | — | cannot_verify | prior | best gallery match curd=0.747 < 0.80 |
| 134 | Tim | 151.0 | — | cannot_verify | prior | best gallery match curd=0.779 < 0.80 |
| 135 | Tim | 157.0 | — | cannot_verify | prior | best gallery match curd=0.757 < 0.80 |
| 136 | Tim | 193.0 | — | cannot_verify | prior | best gallery match curd=0.758 < 0.80 |
| 137 | Tim | 165.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.763 < 0.80 |
| 138 | Tim | 159.0 | — | cannot_verify | prior | best gallery match curd=0.741 < 0.80 |
| 139 | Tim | 152.0 | — | cannot_verify | prior | best gallery match curd=0.758 < 0.80 |
| 140 | Tim | 158.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.760 < 0.80 |
| 142 | Tim | 174.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.762 < 0.80 |
| 143 | Tim | 170.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.772 < 0.80 |
| 144 | Tim | 190.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.779 < 0.80 |
| 145 | Tim | 174.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.784 < 0.80 |
| 146 | Tim | 186.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.781 < 0.80 |
| 147 | Tim | 183.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.770 < 0.80 |
| 148 | Tim | 168.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.778 < 0.80 |
| 149 | Tim | 159.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.766 < 0.80 |
| 150 | Tim | 160.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.775 < 0.80 |
| 151 | Tim | 196.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.770 < 0.80 |
| 152 | Tim | 185.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.762 < 0.80 |
| 153 | Tim | 185.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.770 < 0.80 |
| 154 | Tim | 166.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.765 < 0.80 |
| 155 | Tim | 159.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.763 < 0.80 |
| 156 | Tim | 166.0 | — | cannot_verify | prior | best gallery match curd=0.751 < 0.80 |
| 157 | Tim | 161.0 | — | cannot_verify | prior | best gallery match steamed-rice=0.758 < 0.80 |
| 158 | Tim | 150.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.775 < 0.80 |
| 179 | Opor Ayam | 52.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.787 < 0.80 |
| 180 | Opor Ayam | 35.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.783 < 0.80 |
| 183 | Ikan Acar Kuning | 40.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.781 < 0.80 |
| 184 | Ikan Acar Kuning | 28.0 | — | cannot_verify | prior | best gallery match kakarakaya-fry=0.740 < 0.80 |
| 185 | Ikan Acar Kuning | 30.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.750 < 0.80 |
| 186 | Ikan Acar Kuning | 42.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.795 < 0.80 |
| 187 | Ikan Acar Kuning | 25.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.775 < 0.80 |
| 188 | Ikan Acar Kuning | 41.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.772 < 0.80 |
| 189 | Ikan Acar Kuning | 39.0 | — | cannot_verify | prior | best gallery match kakarakaya-fry=0.761 < 0.80 |
| 190 | Ikan Acar Kuning | 49.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.755 < 0.80 |
| 191 | Ikan Acar Kuning | 41.0 | — | cannot_verify | prior | best gallery match kakarakaya-fry=0.743 < 0.80 |
| 192 | Ikan Acar Kuning | 39.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.716 < 0.80 |
| 193 | Ikan Acar Kuning | 37.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.734 < 0.80 |
| 194 | Ikan Acar Kuning | 32.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.765 < 0.80 |
| 195 | Ikan Acar Kuning | 40.0 | — | cannot_verify | prior | best gallery match kakarakaya-fry=0.746 < 0.80 |
| 196 | Ikan Acar Kuning | 36.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.757 < 0.80 |
| 197 | Ikan Acar Kuning | 37.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.766 < 0.80 |
| 198 | Ikan Acar Kuning | 39.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.738 < 0.80 |
| 199 | Ikan Acar Kuning | 48.0 | — | cannot_verify | prior | best gallery match kakarakaya-fry=0.757 < 0.80 |
| 200 | Ikan Acar Kuning | 39.0 | — | cannot_verify | prior | best gallery match kakarakaya-fry=0.736 < 0.80 |
| 201 | Ikan Acar Kuning | 36.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.739 < 0.80 |
| 202 | Ikan Acar Kuning | 62.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.727 < 0.80 |
| 272 | Ayam bumbu bistik | 54.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.734 < 0.80 |
| 273 | Ayam bumbu bistik | 42.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.770 < 0.80 |
| 274 | Ayam bumbu bistik | 50.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.773 < 0.80 |
| 275 | Ayam bumbu bistik | 54.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.783 < 0.80 |
| 276 | Ayam bumbu bistik | 67.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.762 < 0.80 |
| 277 | Ayam bumbu bistik | 54.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.738 < 0.80 |
| 278 | Ayam bumbu bistik | 61.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.735 < 0.80 |
| 279 | Ayam bumbu bistik | 68.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.734 < 0.80 |
| 280 | Ayam bumbu bistik | 57.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.761 < 0.80 |
| 281 | Ayam bumbu bistik | 52.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.768 < 0.80 |
| 282 | Ayam bumbu bistik | 58.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.774 < 0.80 |
| 283 | Ayam bumbu bistik | 49.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.771 < 0.80 |
| 284 | Ayam bumbu bistik | 43.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.758 < 0.80 |
| 285 | Ayam bumbu bistik | 48.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.758 < 0.80 |
| 286 | Ayam bumbu bistik | 45.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.752 < 0.80 |
| 287 | Ayam bumbu bistik | 44.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.755 < 0.80 |
| 288 | Ayam bumbu bistik | 68.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.751 < 0.80 |
| 289 | Ayam bumbu bistik | 85.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.735 < 0.80 |
| 290 | Ayam bumbu bistik | 64.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.764 < 0.80 |
| 291 | Ayam bumbu bistik | 50.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.766 < 0.80 |
| 292 | Ayam bumbu bistik | 49.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.759 < 0.80 |
| 293 | Ayam bumbu bistik | 55.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.742 < 0.80 |
| 388 | Bali Tahu | 35.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.728 < 0.80 |
| 389 | Bali Tahu | 41.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.716 < 0.80 |
| 391 | Bali Tahu | 35.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.750 < 0.80 |
| 392 | Bali Tahu | 38.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.747 < 0.80 |
| 393 | Bali Tahu | 67.0 | — | cannot_verify | prior | best gallery match mango-pickle=0.751 < 0.80 |
| 394 | Bali Tahu | 51.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.715 < 0.80 |
| 395 | Bali Tahu | 34.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.742 < 0.80 |
| 396 | Bali Tahu | 41.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.748 < 0.80 |
| 397 | Bali Tahu | 25.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.735 < 0.80 |
| 398 | Bali Tahu | 18.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.724 < 0.80 |
| 399 | Bali Tahu | 18.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.732 < 0.80 |
| 400 | Bali Tahu | 30.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.750 < 0.80 |
| 401 | Bali Tahu | 18.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.738 < 0.80 |
| 402 | Bali Tahu | 20.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.754 < 0.80 |
| 403 | Bali Tahu | 35.0 | — | cannot_verify | prior | best gallery match wheat_product=0.737 < 0.80 |
| 404 | Bali Tahu | 35.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.734 < 0.80 |
| 405 | Bali Tahu | 35.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.733 < 0.80 |
| 407 | Bali Tahu | 36.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.712 < 0.80 |
| 408 | Bali Tahu | 36.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.746 < 0.80 |
| 409 | Bali Tahu | 35.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.740 < 0.80 |
| 410 | Bali Tahu | 43.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.748 < 0.80 |
| 411 | Bali Tahu | 36.0 | — | cannot_verify | prior | best gallery match vegetable_rice=0.747 < 0.80 |

## Interpretation

The current pipeline abstained on every test image because its gallery classifier did not reach the configured acceptance score for these unseen Indonesian foods. This is a complete coverage gap on the held-out categories. Since no numeric grams were returned, this run does not establish whether its mass regressor would be accurate on these foods if supplied a dish label.

The held-out categories remain closed to development. Any later candidate may be compared once on this split only after training and epoch selection are frozen using train/dev categories.
