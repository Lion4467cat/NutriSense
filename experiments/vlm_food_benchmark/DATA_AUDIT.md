# VLM Food Benchmark data audit

Source revision: `d715df0c0debe65da805618431e67f6d0fa01c71`.
Manifest SHA-256: `34127e792113311a380b668f6c7215daab9ee7b5a391a55458ad2cc37ed24fbf`.
Images: 200; food-item labels: 870.
Image hash duplicates: 0.
Ground truth is sourced from the repository's `structured_food_labels.csv`; the repository states item weights are scale-measured with empty-plate tare subtracted.

| Participant group | Images | Split |
|---|---:|---|
| participant_1 | 48 | train |
| participant_2 | 28 | train |
| participant_3 | 34 | dev |
| participant_4 | 22 | train |
| participant_5 | 8 | train |
| participant_6 | 60 | test |

| Split | Images |
|---|---:|
| train | 106 |
| dev | 34 |
| test | 60 |

## Split composition

| Split | Images | Mean items/image | Mean total g | Median total g | Total range g |
|---|---:|---:|---:|---:|---:|
| train | 106 | 5.06 | 712.4 | 709.0 | 160.0–1127.0 |
| dev | 34 | 1.06 | 320.2 | 286.5 | 39.0–770.0 |
| test | 60 | 4.97 | 761.9 | 764.0 | 94.0–1154.0 |

Participant groups are disjoint by construction. The test set is participant_6 (60 images) and is reserved for the one-shot comparison in `PROTOCOL.md`. The primary paper describes participant 3's 34-image subset as home-prepared lunches, while the repository README broadly describes the dataset as university-canteen meals; participant-level split composition therefore confounds setting with the dev partition. See https://doi.org/10.3390/nu18213582.
