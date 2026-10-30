# VLM Food Benchmark frozen comparison

60 meals from participant_6 were the only test group. Candidate and serving-pipeline outputs are from the same images; ground truth was not supplied to inference.

## Plate-total results

| Method | Numeric coverage | MAE g | Signed bias g |
|---|---:|---:|---:|
| DINOv2-S research candidate | 60/60 | 148.0 | -106.9 |
| Train+dev median (632.5 g) | 60/60 | 172.0 | -129.4 |
| Current serving pipeline | 0/60 | — | — |

Candidate predictions ranged from 251.7 to 843.0 g; ground-truth totals ranged from 94.0 to 1154.0 g.

The serving pipeline returned no numeric totals, so its plate-total MAE and signed bias are undefined on this test group. Abstentions are not counted as zero error.

## Pipeline coverage and timing

Verdicts: `{'cannot_verify': 60}`. Dish labels: `{'None': 60}`.
Anchors: `{'prior': 60}`. Gallery best-match scores ranged from 0.599 to 0.765; 60/60 were below the existing 0.80 acceptance score.
Median latency: 0.439 s; p95 latency: 0.467 s; first request: 18.570 s; max: 18.570 s.
Per-image reasons are preserved in `raw_pipeline_test.jsonl`.

## Split-composition caveat

| Split | Images | Mean items/image | Mean total g | Median total g |
|---|---:|---:|---:|---:|
| train | 106 | 5.06 | 712.4 | 709.0 |
| dev | 34 | 1.06 | 320.2 | 286.5 |
| test | 60 | 4.97 | 761.9 | 764.0 |

The primary paper describes participant 3's 34-image development subset as home-prepared lunches; the source README broadly describes university-canteen meals. Development is therefore lower-mass and mostly single-item, unlike the train/test groups. This split-composition mismatch may have influenced epoch selection and candidate bias; it is a hypothesis, not a demonstrated cause. No test result was used to retune.

## Per-image plate totals

| Image | Items | True g | Candidate g | Candidate signed error g | Pipeline g | Verdict |
|---|---:|---:|---:|---:|---:|---|
| 029.jpg | 6 | 1098.0 | 697.0 | -401.0 | — | cannot_verify |
| 030.jpg | 2 | 391.0 | 356.9 | -34.1 | — | cannot_verify |
| 031.jpg | 6 | 1069.0 | 809.2 | -259.8 | — | cannot_verify |
| 032.jpg | 1 | 452.0 | 251.7 | -200.3 | — | cannot_verify |
| 033.jpg | 6 | 1039.0 | 679.4 | -359.6 | — | cannot_verify |
| 034.jpg | 6 | 701.0 | 689.7 | -11.3 | — | cannot_verify |
| 035.jpg | 5 | 711.0 | 648.1 | -62.9 | — | cannot_verify |
| 036.jpg | 5 | 656.0 | 690.9 | +34.9 | — | cannot_verify |
| 037.jpg | 7 | 1114.0 | 606.5 | -507.5 | — | cannot_verify |
| 038.jpg | 6 | 1154.0 | 723.8 | -430.2 | — | cannot_verify |
| 039.jpg | 5 | 650.0 | 615.3 | -34.7 | — | cannot_verify |
| 040.jpg | 5 | 720.0 | 563.5 | -156.5 | — | cannot_verify |
| 041.jpg | 6 | 1038.0 | 723.2 | -314.8 | — | cannot_verify |
| 042.jpg | 5 | 641.0 | 593.6 | -47.4 | — | cannot_verify |
| 057.jpg | 5 | 705.0 | 568.2 | -136.8 | — | cannot_verify |
| 058.jpg | 6 | 974.0 | 810.3 | -163.7 | — | cannot_verify |
| 059.jpg | 5 | 529.0 | 570.9 | +41.9 | — | cannot_verify |
| 076.jpg | 5 | 602.0 | 703.0 | +101.0 | — | cannot_verify |
| 077.jpg | 5 | 542.0 | 674.0 | +132.0 | — | cannot_verify |
| 078.jpg | 5 | 639.0 | 818.3 | +179.3 | — | cannot_verify |
| 079.jpg | 5 | 804.0 | 727.3 | -76.7 | — | cannot_verify |
| 085.jpg | 5 | 623.0 | 585.6 | -37.4 | — | cannot_verify |
| 086.jpg | 5 | 585.0 | 685.5 | +100.5 | — | cannot_verify |
| 087.jpg | 5 | 703.0 | 707.6 | +4.6 | — | cannot_verify |
| 088.jpg | 5 | 600.0 | 751.1 | +151.1 | — | cannot_verify |
| 089.jpg | 5 | 674.0 | 802.1 | +128.1 | — | cannot_verify |
| 090.jpg | 5 | 742.0 | 672.5 | -69.5 | — | cannot_verify |
| 109.jpg | 5 | 667.0 | 694.2 | +27.2 | — | cannot_verify |
| 110.jpg | 5 | 843.0 | 731.2 | -111.8 | — | cannot_verify |
| 111.jpg | 5 | 734.0 | 583.0 | -151.0 | — | cannot_verify |
| 112.jpg | 5 | 726.0 | 673.8 | -52.2 | — | cannot_verify |
| 113.jpg | 5 | 885.0 | 570.1 | -314.9 | — | cannot_verify |
| 144.jpg | 5 | 855.0 | 650.8 | -204.2 | — | cannot_verify |
| 145.jpg | 5 | 911.0 | 664.5 | -246.5 | — | cannot_verify |
| 146.jpg | 5 | 811.0 | 690.6 | -120.4 | — | cannot_verify |
| 147.jpg | 5 | 856.0 | 710.1 | -145.9 | — | cannot_verify |
| 148.jpg | 5 | 889.0 | 662.8 | -226.2 | — | cannot_verify |
| 149.jpg | 5 | 771.0 | 585.0 | -186.0 | — | cannot_verify |
| 150.jpg | 5 | 813.0 | 604.4 | -208.6 | — | cannot_verify |
| 151.jpg | 5 | 744.0 | 671.3 | -72.7 | — | cannot_verify |
| 152.jpg | 5 | 738.0 | 661.6 | -76.4 | — | cannot_verify |
| 153.jpg | 5 | 629.0 | 518.7 | -110.3 | — | cannot_verify |
| 154.jpg | 5 | 776.0 | 638.9 | -137.1 | — | cannot_verify |
| 155.jpg | 5 | 912.0 | 716.0 | -196.0 | — | cannot_verify |
| 156.jpg | 5 | 915.0 | 610.4 | -304.6 | — | cannot_verify |
| 157.jpg | 5 | 757.0 | 689.0 | -68.0 | — | cannot_verify |
| 158.jpg | 5 | 821.0 | 843.0 | +22.0 | — | cannot_verify |
| 159.jpg | 5 | 799.0 | 609.0 | -190.0 | — | cannot_verify |
| 160.jpg | 5 | 822.0 | 613.5 | -208.5 | — | cannot_verify |
| 161.jpg | 5 | 724.0 | 607.1 | -116.9 | — | cannot_verify |
| 162.jpg | 5 | 839.0 | 779.9 | -59.1 | — | cannot_verify |
| 176.jpg | 5 | 868.0 | 800.9 | -67.1 | — | cannot_verify |
| 177.jpg | 5 | 826.0 | 499.6 | -326.4 | — | cannot_verify |
| 178.jpg | 5 | 654.0 | 623.6 | -30.4 | — | cannot_verify |
| 179.jpg | 5 | 774.0 | 697.2 | -76.8 | — | cannot_verify |
| 180.jpg | 5 | 712.0 | 653.8 | -58.2 | — | cannot_verify |
| 181.jpg | 5 | 779.0 | 710.0 | -69.0 | — | cannot_verify |
| 182.jpg | 5 | 825.0 | 655.6 | -169.4 | — | cannot_verify |
| 183.jpg | 5 | 790.0 | 751.9 | -38.1 | — | cannot_verify |
| 200.jpg | 1 | 94.0 | 405.7 | +311.7 | — | cannot_verify |

## Interpretation

On this one participant-held-out group, the research candidate's MAE was 148.0 g versus 172.0 g for the train+dev median (-24.0 g), with -106.9 g signed bias. This is a modest single-cluster result with substantial underprediction. The current serving path had zero numeric coverage. The candidate is not integrated and does not establish Indian mixed-meal accuracy or production readiness.
