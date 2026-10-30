# Oracle ablation: Step 2 diagnostic and Step 3 design

**Status:** Step 2 run is complete. Step 3 below is design only. No oracle modes or ablations were run. Stop here for review.

## Scope and frozen conditions

- Project interpreter was activated through `uv run --active --python .venv/bin/python -- ...`.
- Requested cohort: one deterministic view per WED DEV plate (21 plates) plus the six existing phone photos in `data/reports/real_photo_e2e.json` (27 images total).
- Request values: `day="mon"`, `band="1-5"`, `serving_style="mixed"` for every image.
- View selection: lexicographically first image path in each DEV plate group. DEV rows come from the existing fixed DEV carve; the WED test partition was not read by the runner.
- The phone set has no reference card; the WED views have no reference card. Thus this run has no card-present path. It cannot compare card and no-card behavior.
- No label was passed into `pipeline.analyze`. The runner only recorded existing pipeline outputs and telemetry. It used the existing checkpoint and evaluation data. No model/config/eval/label/split files were modified by this diagnostic. The only new task artifacts are in this directory.
- CUDA was required. The runner raises if CUDA is unavailable and does not fall back to CPU. Model stages were loaded sequentially; no OOM occurred.

## GPU check

Command:

```bash
UV_CACHE_DIR=/tmp/nutrisense-uv-cache uv run --active --python .venv/bin/python -- python -u -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); x=torch.randn(1000,1000,device='cuda'); print((x@x).sum().item())"
```

Raw output:

```text
2.13.0+cu130 13.0 True
NVIDIA GeForce RTX 4060 Laptop GPU
-18900.708984375
```

This confirms CUDA is available in the elevated project execution. The GPU operation completed. During the pipeline run, maximum observed stage peaks were:

| Stage | Peak allocated MiB | Peak reserved MiB |
|---|---:|---:|
| Classifier | 1598.04 | 1684.00 |
| Depth | 2477.04 | 2940.00 |
| Food segmentation | 1356.98 | 1746.00 |
| Item segmentation | 1441.05 | 1834.00 |

These are stage peaks recorded by PyTorch's CUDA memory counters; they are not whole-process VRAM maxima. The classifier/segmentation/depth models were unloaded between stages and images. No OOM was recorded.

## Step 2: gate and full-pipeline results

### Per-path outcome and reason counts

| Path | N | Input-gate rejection | Stage failure | Classifier abstention | `cannot_verify` by-design off-menu | PASS | BORDERLINE | FAIL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| WED DEV, no card | 21 | 0 | 0 | 0 | 21 | 0 | 0 | 0 |
| Phone, no card | 6 | 0 | 0 | 0 | 0 | 0 | 1 | 5 |
| Card-present | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

All 27 requests passed the input gate with the valid day/band pair `mon` / `1-5`. There were no technical stage failures and no classifier abstentions. WED emitted `cannot_verify` on all 21 views because the recognized dish was outside the configured menu: all 21 are by-design off-menu cases, so **100% of this run's `cannot_verify` cases are by-design and 0% are genuine failures**. Phone photos returned scored `FAIL`/`BORDERLINE`, not `cannot_verify`; their by-design/genuine `cannot_verify` fraction is therefore not applicable.

Exact reason-code totals over 27 outputs:

```text
{"below_min": 25, "no_reference_card": 27, "off_menu_dish": 21}
```

`no_reference_card` is a scale disclaimer, not a request-gate rejection. The 25 `below_min` reason instances are compliance reasons on the phone photos, including the generic mandatory-nutrient reason and nutrient-specific pass/fail-zone details. Input-gate rejections, stage-failure reason codes, and classifier-abstention codes were all zero.

### WED DEV predictions, grouped by predicted dish

There were 12 predicted `steamed-rice` outputs (140.9–337.6 g), 5 `veg-dum-briyani` outputs (88.7–150.3 g), and 4 `chicken-dum-biryani` outputs (97.0–138.9 g). Every prediction still yielded `cannot_verify` because these names are not on the request menu. The `GT plate contains predicted name` column is only a plate-level presence check against that plate's WED dish labels; it is **not** a class-accuracy score or mask/instance match.

| WED DEV plate | Predicted dish | Predicted g | Mask/image area | Name present in plate GT | End-to-end seconds | Reason codes |
|---|---|---:|---:|---|---:|---|
| 20250512_set14 | steamed-rice | 140.9 | 0.0396 | yes | 13.514 | off_menu_dish, no_reference_card |
| 20250512_set22 | steamed-rice | 189.3 | 0.0133 | yes | 9.328 | off_menu_dish, no_reference_card |
| 20250515_set11 | chicken-dum-biryani | 116.0 | 0.0310 | no | 10.066 | off_menu_dish, no_reference_card |
| 20250515_set20 | steamed-rice | 167.1 | 0.0597 | yes | 7.816 | off_menu_dish, no_reference_card |
| 20250516_set10 | steamed-rice | 312.4 | 0.0362 | yes | 6.807 | off_menu_dish, no_reference_card |
| 20250516_set19 | veg-dum-briyani | 128.2 | 0.0712 | no | 7.152 | off_menu_dish, no_reference_card |
| 20250516_set21 | veg-dum-briyani | 150.3 | 0.0762 | no | 8.021 | off_menu_dish, no_reference_card |
| 20250517_set14 | steamed-rice | 254.1 | 0.1089 | yes | 6.325 | off_menu_dish, no_reference_card |
| 20250517_set16 | steamed-rice | 266.1 | 0.0737 | yes | 7.636 | off_menu_dish, no_reference_card |
| 20250517_set3 | steamed-rice | 193.1 | 0.0936 | yes | 7.001 | off_menu_dish, no_reference_card |
| 20250517_set30 | veg-dum-briyani | 104.0 | 0.0286 | no | 6.705 | off_menu_dish, no_reference_card |
| 20250517_set7 | steamed-rice | 337.6 | 0.0342 | yes | 7.469 | off_menu_dish, no_reference_card |
| 20250519_set10 | chicken-dum-biryani | 138.9 | 0.0385 | no | 6.516 | off_menu_dish, no_reference_card |
| 20250519_set6 | chicken-dum-biryani | 97.0 | 0.0569 | no | 7.282 | off_menu_dish, no_reference_card |
| 20250521_set12 | veg-dum-briyani | 113.8 | 0.0244 | yes | 6.485 | off_menu_dish, no_reference_card |
| 20250521_set15 | veg-dum-briyani | 88.7 | 0.0359 | yes | 7.057 | off_menu_dish, no_reference_card |
| 20250521_set21 | chicken-dum-biryani | 117.5 | 0.0177 | yes | 6.726 | off_menu_dish, no_reference_card |
| 20250523_set1 | steamed-rice | 258.0 | 0.0667 | yes | 6.422 | off_menu_dish, no_reference_card |
| 20250523_set9 | steamed-rice | 244.2 | 0.0235 | yes | 6.913 | off_menu_dish, no_reference_card |
| 20250524_set12 | steamed-rice | 217.6 | 0.0162 | yes | 6.339 | off_menu_dish, no_reference_card |
| 20250524_set15 | steamed-rice | 193.3 | 0.0135 | yes | 6.368 | off_menu_dish, no_reference_card |

Per-image WED ground-truth dish names and weights are retained in the raw JSONL so the selected plate compositions can be inspected without reducing them to the presence check above. The predictions are single selected food regions from multi-dish plates, while WED labels multiple food regions per plate; do not interpret these grams as a matched per-dish MAE result.

### Six phone photos that returned FAIL/BORDERLINE

The configured band minima are **450 kcal** and **12 g protein**. Compliance uses Monte Carlo probability (P) of meeting each minimum: PASS zone needs (P\geq0.90); fail-zone condition is (P\leq0.10). “Below-min” therefore describes the compliance rule, not a measured nutrition truth. The phone photos have no food-mass labels, so this run cannot establish whether a gram estimate is low or correct.

| Image | Identified dish(es) | Predicted g by item (sum) | Image/mask area fraction | Anchor | kcal: mean; P(≥450) | Protein: mean; P(≥12) | Verdict | Seconds |
|---|---|---:|---:|---|---|---|---|---:|
| IMG20260824131408.jpg | rice_sambar | 287.8 | 0.3528 | prior | 261.87; 0.0055 | 7.00 g; 0.0055 | FAIL | 12.003 |
| IMG20260824131418.jpg | steamed-rice ×3 | 139.9 + 145.0 + 133.1 = 418.1 | item masks 0.3610, 0.3343, 0.1493; top-level 0.1168 | prior | 469.27; 0.5988 | 10.06 g; 0.0732 | FAIL | 16.073 |
| IMG20260824131456.jpg | steamed-rice ×3 | 177.7 + 177.1 + 180.0 = 534.7 | item masks 0.3296, 0.2927, 0.2404; top-level 0.2091 | prior | 600.18; 0.9892 | 12.86 g; 0.6823 | BORDERLINE | 16.269 |
| IMG20260824131457.jpg | sambar ×2 | 101.0 + 101.0 = 202.0 | item masks 0.3599, 0.1989; top-level 0.1852 | prior | 121.41; 0.0000 | 5.06 g; 0.0000 | FAIL | 14.906 |
| IMG20260825130507.jpg | vegetable_rice | 90.6 | 0.3648 | prior | 135.79; 0.0000 | 3.16 g; 0.0000 | FAIL | 11.537 |
| IMG20260825130516.jpg | vegetable_rice | 57.6 | 0.3259 | prior | 86.26; 0.0000 | 2.01 g; 0.0000 | FAIL | 11.793 |

All six lack a card, so all use the prior anchor. Their probabilities under both mandatory minima are below the pass-zone threshold except kcal for `IMG20260824131456.jpg`; that image remains BORDERLINE because its protein probability is 0.6823. The estimates for the two vegetable-rice photos are low in absolute grams despite large predicted image-area fractions. That is a diagnostic signal, not proof of underestimation: there are no mass labels for these phone images. The two three-item rice results and the two-item sambar result have strongly overlapping or identical item bounding boxes in the saved predictions; that is consistent with possible duplicate region proposals and could inflate total mass. With no annotated phone masks or food masses, this is a hypothesis only. The app's FAIL verdict means the computed meal nutrients miss configured minima with the rule's coverage; it is not a verified ground-truth classification of the photographed portion.

### Reason/time summary and raw per-image output

Exact runner command:

```bash
HF_HUB_OFFLINE=1 UV_CACHE_DIR=/tmp/nutrisense-uv-cache uv run --active --python .venv/bin/python -- python -u experiments/oracle_ablation/run_step2_diagnostic.py
```

The run started with the following recorded setup and ended with these exact outcome totals:

```text
{"band": "1-5", "cuda": "13.0", "day": "mon", "device": "NVIDIA GeForce RTX 4060 Laptop GPU", "event": "run_started", "n_images": 27, "phone_images": 6, "torch": "2.13.0+cu130", "view_selection": "lexicographically first image path per plate", "wed_dev_plates": 21}
{"counts": {"BORDERLINE": 1, "FAIL": 5, "cannot_verify_by_design_off_menu": 21}, "event": "run_complete", "raw_jsonl": "experiments/oracle_ablation/step2_raw.jsonl"}
```

The full raw output is [step2_raw.jsonl](step2_raw.jsonl), with one JSON record per image: source and plate, WED labels, predicted dish/grams/masks, exact reason codes and text, all stage timing values, per-image wall time, path, anchor, and stage VRAM peaks. The WED table and phone table above are a compact rendering of those actual records; they retain the requested per-image elapsed seconds and reasons.

## ArUco prior fallbacks

Command used (same active project venv):

```bash
UV_CACHE_DIR=/tmp/nutrisense-uv-cache uv run --active --python .venv/bin/python -- python - <<'PY'
from pathlib import Path
import cv2
from config import load_anchor_config
from geo import mean_side_px
from models.scale_anchor import _aruco_detect, _quiet_zone_ok, estimate_anchor
root = Path('../Aruco_7ID_60mm_with_food'); cfg = load_anchor_config()
rel = ['Dish 1/20261025_191009.jpg', 'Dish 1/this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg', 'Dish 2/20261027_085746.jpg']
print('marker_id', cfg['card']['marker_id'], 'dictionary', cfg['card']['dictionary'], 'min_marker_side_px', cfg['tier']['min_marker_side_px'])
for s in rel:
    p = root/s; im = cv2.imread(str(p)); gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    marks = _aruco_detect(gray, cfg['card']['marker_id'], cfg['card']['dictionary'])
    a = estimate_anchor(im, config=cfg)
    print(s, 'raw_id_detections', len(marks), 'side_px', [round(mean_side_px(m), 2) for m in marks], 'quiet_zone', [bool(_quiet_zone_ok(m, gray)) for m in marks], 'anchor', a['label'], 'reason', a['reason'])
PY
```

Raw output:

```text
marker_id 7 dictionary DICT_4X4_50 min_marker_side_px 80
Dish 1/20261025_191009.jpg raw_id_detections 0 side_px [] quiet_zone [] anchor prior reason no reference card in frame — scale from size priors
Dish 1/this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg raw_id_detections 1 side_px [592.34] quiet_zone [False] anchor prior reason no reference card in frame — scale from size priors
Dish 2/20261027_085746.jpg raw_id_detections 1 side_px [431.52] quiet_zone [False] anchor prior reason no reference card in frame — scale from size priors
```

1. `Dish 1/20261025_191009.jpg`: no ID 7 marker was detected. Visual review showed no reference card visible in-frame, so absence/out-of-frame is the supported explanation; no blur/angle/occlusion rejection was emitted.
2. The weight-named `Dish 1` image: the ID 7 quad was detected at 592.34 px, well above the 80 px minimum, but failed the quiet-zone check. The marker/card appears clipped at the right image edge. The detector does not preserve a more specific edge-clipping reason; its final returned reason is generic “no reference card”.
3. `Dish 2/20261027_085746.jpg`: ID 7 quad detected at 431.52 px, above the minimum, but failed quiet-zone validation. The detector's available rejection evidence is exactly `quiet_zone=False`; it does not report blur, angle, or occlusion as the cause. Any more specific cause would be speculation.

## Step 3: oracle plan only

No ablation has been implemented or run. WED provides per-food pixel masks, dish labels, and gram labels on its annotated plates. Honest candidate interventions for a later approved study:

| Oracle/intervention | Buildable now? | Honest scope and limitation |
|---|---|---|
| GT mask → learned weight head | Yes, for WED annotated regions | Substitute the WED food-region mask for the predicted mask on a matched WED item, preserve model class prediction, and feed the result through the existing learned head. Matching must be defined per annotated region; unmatched predictions/regions must be reported rather than silently paired. |
| GT class → learned weight head | Yes, for WED annotated regions | Substitute the WED dish class for the predicted class on a deterministically matched WED food region. Keep predicted mask and other inputs. Report unmatched regions separately. |
| GT mask + GT class → learned weight head | Yes, for WED annotated regions | Joint ceiling for the two interventions above. WED gram labels remain the target used to score error; do not feed them into the pipeline as an oracle. |
| Per-dish gram oracle | No; invalid design | WED grams are outcome labels/targets. Replacing a prediction with the target would trivially erase error and would not test a pipeline stage. |
| Gate bypass on refused WED images | Not a meaningful failure oracle in this run | All WED refusals were configured off-menu behavior. There is no label for “this photo should be verifiable” under the configured menu. Bypassing this policy would confound a deliberate scope decision with a model failure. |
| Card/scale oracle on WED | Blocked | WED has no reference-card geometry/scale annotation for these views. |
| Geometry/volume/depth GT oracle | Blocked | No per-image depth or volume truth is available for the WED/phone cohort. Do not substitute grams as geometry truth. |
| Phone-image GT mask/class/weight oracles | Blocked | The six phone photos have no verified per-item masks, dish labels, or food-only mass labels. Existing predictions and filename notes are not ground truth. |

For geometry-path supervision, the minimal new annotation is **30–50 captures with the reference card in frame, dish ID, and food-only mass measured on a kitchen scale with vessel tare weighed separately**. Masks may be SAM-generated and manually checked. Do not collect per-image depth or volume labels. This is an annotation plan only; no data collection is part of this run.

The actual pipeline and threshold/model configuration were not changed. The later ablation should keep the held-out split fixed and use bootstrap intervals and the preregistered 3% relative minimum effect from the study protocol, but no ranking or MAE claim is made here.

## Protected-file diff against checkpoint H

Command:

```bash
git diff 4f313fd -- tools/run_eval.py tools/stress_suite.py tools/compare_runs.py tools/check_locked.py tools/build_wed_manifest.py data/wed_manifest.jsonl docs/locked_manifest.txt
```

Raw output (non-empty):

```diff
diff --git a/docs/locked_manifest.txt b/docs/locked_manifest.txt
index 9e2452b..506c7f2 100644
--- a/docs/locked_manifest.txt
+++ b/docs/locked_manifest.txt
@@ -8,7 +8,7 @@
 # Verify: .venv/bin/python -m tools.check_locked
 # Regenerate ONLY deliberately, with approval:
 #   .venv/bin/python -m tools.check_locked --write
-# written: 2026-10-12T13:43:47Z  files: 502
+# written: 2026-10-15T03:44:10Z  files: 502
 1e3f2666744332d4c16af5ba5bc66d0a27bba729c334e1beb824ca8232d1b53b  data/wed/test/12-may/gtFine/default/set25/20250512_163527_gtFine_labelIds.png
 e386302dd1d6fde9e50b214e6b26a106d30903481989baf6532505033bf7e3d4  data/wed/test/12-may/gtFine/default/set25/20250512_163533_gtFine_labelIds.png
 306089dcda4a7db75a553598d2302e24847d20652eb6ad0ea96ab95e28da914c  data/wed/test/12-may/gtFine/default/set25/20250512_163536_gtFine_labelIds.png
@@ -508,6 +508,6 @@ d2bdc751a0e62b9bd587e6451cac467a09d4422e8fd4d4a3463fef924d26364e  data/wed/test/
 f5bad6b32963c7ee2ed0ad3cddd7ca02d2d912c90b36c9b3cde7e82fb989214d  data/wed_manifest.jsonl
 cf95d224781f7cc0fcaafc875ab1738ee09e58b59b8e21c24fb333fbb3815479  tools/build_wed_manifest.py
 18f5a40e1105c77547e1e9fb4d54de44275d5e67526b98a3b9ee5da897185531  tools/check_locked.py
-c686da9c9003b736162729c557c73815a4cf721617dc0f85c39aeec63b6c48d8  tools/compare_runs.py
+0ec0dcaf2f1de30f02e82e826fa83e5de59144774215703dd0e6314255caa31c  tools/compare_runs.py
 bfab09a8212f8e45ed4eb351f2474af5a928f6a98ffef163ec2d361d515d721a  tools/run_eval.py
 011ec1ecf77b1ab4c8cc5629dc10f91738de7216fd9aa0fe91b8bd553bef6e44  tools/stress_suite.py
diff --git a/tools/compare_runs.py b/tools/compare_runs.py
index 0498a18..4b5fc39 100644
--- a/tools/compare_runs.py
+++ b/tools/compare_runs.py
@@ -9,8 +9,13 @@ is WED". Seed is fixed, so a re-comparison is reproducible.
 
 Reports:
   * MAE (g)       — paired difference + 95% CI
-  * coverage_90   — paired difference + 95% CI
-  * every stress perturbation present in BOTH reports (same two statistics)
+  * coverage_90   — paired difference + 95% CI    * every stress perturbation present in BOTH reports (same two statistics)
+
+Pairwise stress (same report, when --stress-x is set):
+  * --stress-x KEY --stress-y KEY  paired CI on two stress perturbations
+    within ONE report (both flags; identical K is refused).
+  * --stress-x KEY  auto-picks the first other perturbation in the report.
+  * Without --stress-x  the usual cross-report paired comparison.
 
 Refuses (exit 2) to compare:
   * runs from different tiers (dev / train / locked)
@@ -21,6 +26,8 @@ Refuses (exit 2) to compare:
 Run:
   .venv/bin/python -m tools.compare_runs baseline.json candidate.json \
       [--seed 42] [--out data/reports/compare.json]
+  .venv/bin/python -m tools.compare_runs single_stress.json \
+      single_stress.json --stress-x KEY [ --stress-y OTHER_KEY ]
 """
 from __future__ import annotations
 
@@ -127,6 +134,79 @@ def _stress_pair(base: dict, cand: dict, *, seed: int, reps: int) -> dict:
             "missing_in_candidate": sorted(set(b_st) - set(c_st))}
 
 
+def _stress_pairwise_single_report(report: dict, *, key_x: str, key_y: str | None,
+                                   seed: int, reps: int) -> dict:
+    st = report.get("stress") or {}
+    if key_x not in st:
+        raise CompareRefused(f"stress perturbation {key_x!r} not in report")
+    if key_y is None:
+        missing = [k for k in sorted(st) if k != key_x]
+        if not missing:
+            raise CompareRefused(
+                "single stress perturbation in report — cannot form a pairwise pair")
+        key_y = missing[0]
+    if key_y not in st:
+        raise CompareRefused(
+            f"stress perturbation {key_y!r} not in report (need {key_x!r} and {key_y!r})")
+    if key_x == key_y:
+        raise CompareRefused(
+            f"stress perturbations {key_x!r} and {key_y!r} are the same; "
+            f"use two distinct perturbations for a pairwise comparison")
+    a_pc = _plates(st[key_x], f"stress {key_x}")
+    b_pc = _plates(st[key_y], f"stress {key_y}")
+    if sorted(a_pc) != sorted(b_pc):
+        raise CompareRefused(f"stress {key_x} vs {key_y}: plate sets differ")
+    block = paired_bootstrap(a_pc, b_pc, seed=seed, reps=reps)
+    block["y"] = key_y
+    return {
+        "paired_single": {key_x: block},
+        "missing_in_baseline": [],
+        "missing_in_candidate": [],
+    }
+
+
+def _build_result_for_single_report_stress(report: dict, *, seed: int,
+                                                 reps: int, stress_x: str,
+                                                 stress_y: str | None) -> dict:
+    tier = report.get("tier")
+    pc = _plates(report, "baseline")
+    pc2 = _plates(report, "candidate")
+    if sorted(pc) != sorted(pc2):
+        raise CompareRefused("baseline and candidate plate sets differ within the same report")
+    out = {
+        "tier": tier,
+        "seed": seed,
+        "baseline": {
+            "mae_g": round(
+                sum(v["sum_abs_err"] for v in pc.values()) /
+                sum(v["n"] for v in pc.values()), 3),
+            "coverage_90": (
+                round(
+                    sum(v["n_covered"] for v in pc.values()) /
+                    sum(v["n_sigma"] for v in pc.values()), 4)
+                if sum(v["n_sigma"] for v in pc.values())
+                else None),
+        },
+        "candidate": {
+            "mae_g": None,
+            "coverage_90": None,
+        },
+    }
+    out["baseline"]["coverage_90"] = (
+        round(
+            sum(v["n_covered"] for v in pc.values()) /
+            sum(v["n_sigma"] for v in pc.values()), 4)
+        if sum(v["n_sigma"] for v in pc.values())
+        else None)
+    pb = paired_bootstrap(pc, pc2, seed=seed, reps=reps)
+    out.update(pb)
+    out["stress"] = _stress_pairwise_single_report(
+        report, key_x=stress_x, key_y=stress_y, seed=seed, reps=reps)
+    out["n_plates"] = len(pc)
+    out["n_samples"] = sum(v["n"] for v in pc.values())
+    return out
+
+
 def compare(baseline: dict, candidate: dict, *, seed: int = DEFAULT_SEED,
             reps: int = BOOTSTRAP_REPS) -> dict:
     tier_b, tier_c = baseline.get("tier"), candidate.get("tier")
@@ -162,14 +242,22 @@ def _print_result(res: dict) -> None:
     print(f"tier={t} coverage_90: baseline {c['baseline']} -> candidate "
           f"{c['candidate']}  diff {c['diff']}  paired_ci95 {c['diff_ci95']}",
           flush=True)
-    for name, block in res["stress"]["paired"].items():
-        sm = block["mae_g"]
-        print(f"tier={t} stress={name} mae_g: baseline {sm['baseline']} -> "
-              f"candidate {sm['candidate']}  diff {sm['diff']}  "
-              f"paired_ci95 {sm['diff_ci95']}", flush=True)
+    st = res["stress"]
+    if "paired" in st:
+        for name, block in st["paired"].items():
+            sm = block["mae_g"]
+            print(f"tier={t} stress={name} mae_g: baseline {sm['baseline']} -> "
+                  f"candidate {sm['candidate']}  diff {sm['diff']}  "
+                  f"paired_ci95 {sm['diff_ci95']}", flush=True)
+    if "paired_single" in st:
+        for name, block in st["paired_single"].items():
+            sm = block["mae_g"]
+            print(f"tier={t} stress-pair={name}(x) <-> {block.get('y', '???')}: "
+                  f"baseline {sm['baseline']} -> candidate {sm['candidate']}  "
+                  f"diff {sm['diff']}  paired_ci95 {sm['diff_ci95']}", flush=True)
     for key in ("missing_in_baseline", "missing_in_candidate"):
-        if res["stress"][key]:
-            print(f"tier={t} stress {key}: {res['stress'][key]}", flush=True)
+        if st.get(key):
+            print(f"tier={t} stress {key}: {st[key]}", flush=True)
 
 
 def main(argv: list[str] | None = None) -> int:
@@ -177,6 +265,10 @@ def main(argv: list[str] | None = None) -> int:
         description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
     ap.add_argument("baseline", type=Path, help="run_eval JSON (baseline)")
     ap.add_argument("candidate", type=Path, help="run_eval JSON (candidate)")
+    ap.add_argument("--stress-x", type=str, default=None,
+                    help="pairwise stress perturbation key (single-report mode when set)")
+    ap.add_argument("--stress-y", type=str, default=None,
+                    help="pairwise stress perturbation key (with --stress-x; if omitted, auto-picks another in the same report)")
     ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
     ap.add_argument("--reps", type=int, default=BOOTSTRAP_REPS)
     ap.add_argument("--out", type=Path, default=None,
@@ -185,7 +277,16 @@ def main(argv: list[str] | None = None) -> int:
     try:
         baseline = json.loads(args.baseline.read_text())
         candidate = json.loads(args.candidate.read_text())
-        res = compare(baseline, candidate, seed=args.seed, reps=args.reps)
+        if args.stress_x is not None:
+            if not args.baseline.samefile(args.candidate):
+                raise CompareRefused(
+                    "--stress-x/--stress-y pairwise mode requires a single report "
+                    "(baseline and candidate must be the same file)")
+            res = _build_result_for_single_report_stress(
+                baseline, seed=args.seed, reps=args.reps,
+                stress_x=args.stress_x, stress_y=args.stress_y)
+        else:
+            res = compare(baseline, candidate, seed=args.seed, reps=args.reps)
     except CompareRefused as exc:
         print(f"refused: {exc}", file=sys.stderr)
         return 2
```

This diff is against H and predates this diagnostic; it shows pre-existing edits in the manifest timestamp and `tools/compare_runs.py`. This run did not modify those protected files. The other protected files listed in the command have no diff against H.

## What this diagnostic does not establish

- It does not measure grams MAE/MAPE or compare pipeline stages. No ablations or bootstrap intervals were run.
- It does not establish phone-photo gram/nutrition accuracy because the phone set has no verified food-mass/nutrient labels.
- It does not establish card-present gate/refusal behavior because the requested cohort contained no card-present images.
- It does not show whether an off-menu WED dish would be verifiable under a broader menu; the configured off-menu refusal is by-design.
- It does not rank stages as sources of final error. That requires a later, approved, label-matched oracle study.

## ArUco weighed-plate evaluation — halted at CUDA preflight (2026-10-30)

The six confirmed food-only plate totals were received, but the required GPU run could not start. PyTorch reports CUDA unavailable and `nvidia-smi` cannot communicate with an NVIDIA driver. Per the run instruction, execution stopped here: no pipeline image was scored, no CPU fallback was attempted, and Steps 3–6 were not run. This addendum records the failed preflight only; it is not a score report. No tuning, retraining, threshold/config/model/checkpoint changes, or protected-file edits were made.

### Commands and raw outputs

CUDA preflight:

```text
$ nvidia-smi
NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver. Make sure that the latest NVIDIA driver is installed and running.

$ .venv/bin/python -c 'import torch; print("torch", torch.__version__); print("cuda_available", torch.cuda.is_available()); print("cuda_version", torch.version.cuda)'
torch 2.13.0+cu130
cuda_available False
cuda_version 13.0
```

Protected evaluation lock:

```text
$ .venv/bin/python -m tools.check_locked
check_locked: 502 ok, 0 skipped, 0 failed (502 pinned)
```

Protected-file diff command and result against `4f313fdc6b15e60a3e73e1b49a0a5d5471e12aab`:

```text
$ git diff --no-ext-diff --stat 4f313fd -- tools/compare_runs.py docs/locked_manifest.txt
 docs/locked_manifest.txt |   4 +-
 tools/compare_runs.py    | 121 +++++++++++++++++++++++++++++++++++++++++++----
 2 files changed, 113 insertions(+), 12 deletions(-)

$ git status --short -- tools/compare_runs.py docs/locked_manifest.txt
 M docs/locked_manifest.txt
 M tools/compare_runs.py
```

The protected diff contains the already-known pre-existing edits in those two paths: the manifest timestamp and `tools/compare_runs.py` change. There is no new protected-file diff from this diagnostic. `tools.check_locked` still reports all 502 pins valid. No other evaluation output exists because CUDA was unavailable.

Machine-readable preflight output: `aruco_preflight.jsonl`. The existing `step2_raw.jsonl` is from the earlier diagnostic and is not the result of this ArUco task.

### Evaluation limits

No per-image totals, classification results, angle spreads, card-versus-forced-prior comparisons, or duplicate-mask measurements were obtained. This halted run does not establish accuracy for these plates. Even a completed run on this cohort would not establish performance beyond n=6 plates, one dish each, one kitchen scale, and one phone.

### Authorized GPU retry (2026-10-30)

The user authorized retrying when CUDA is available. The retry was run from the project `.venv` and still failed; execution remains halted.

```text
$ .venv/bin/python -c 'import subprocess, torch; print("torch", torch.__version__); print("cuda_available", torch.cuda.is_available()); print("cuda_version", torch.version.cuda); p=subprocess.run(["nvidia-smi"], text=True, capture_output=True); print("nvidia_smi_exit", p.returncode); print(p.stdout or p.stderr)'
torch 2.13.0+cu130
cuda_available False
cuda_version 13.0
nvidia_smi_exit 9
NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver. Make sure that the latest NVIDIA driver is installed and running.
```

## Completed ArUco weighed-plate evaluation (2026-10-30)

The user verified the GPU from Fish by invoking the project interpreter directly (`./.venv/bin/python`; Fish had rejected the Bash `activate` script). The escalated evaluation runtime then also reported CUDA available and ran on the NVIDIA GeForce RTX 4060 Laptop GPU. All project Python commands used `.venv/bin/python`. The earlier preflight halt was superseded by this successful retry.

### Run command and machine output

```text
$ .venv/bin/python -c 'import torch; print("torch", torch.__version__); print("cuda_available", torch.cuda.is_available()); print("device", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO CUDA DEVICE")'
torch 2.13.0+cu130
cuda_available True
device NVIDIA GeForce RTX 4060 Laptop GPU

$ .venv/bin/python experiments/oracle_ablation/run_aruco_eval.py --paired-card-vs-prior
{"band": "1-5", "cuda": "13.0", "cuda_device": "NVIDIA GeForce RTX 4060 Laptop GPU", "day": "mon", "event": "run_started", "force_prior_default": false, "image_count": 23, "n_mc": 4000, "paired_card_vs_prior": true, "seed": 1234, "serving_style": "mixed", "torch": "2.13.0+cu130"}
{"event": "default_flag_off_replay_check", "identical_pipeline_result": true, "image": "/home/tinkerer/Desktop/Nutrisense/Aruco_7ID_60mm_with_food/Dish 1/20261025_184112.jpg", "original_result_sha256": "041a9c186e17fa8fc5c9d9aa2b74c89a2c66ef31083dd77677d8b064c22b5df6", "replay_result_sha256": "041a9c186e17fa8fc5c9d9aa2b74c89a2c66ef31083dd77677d8b064c22b5df6"}
{"event": "run_complete", "measured_anchor_images": 20, "prior_anchor_images": 3, "raw_jsonl": "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/experiments/oracle_ablation/aruco_raw.jsonl", "records": 43}

$ .venv/bin/python -c 'import json; from collections import Counter; from pathlib import Path; rows=[json.loads(x) for x in Path("experiments/oracle_ablation/aruco_raw.jsonl").read_text().splitlines()]; print("raw_jsonl_records",len(rows)); print("event_counts",dict(Counter(x.get("event") for x in rows))); print("modes",dict(Counter(x.get("mode") for x in rows if x.get("mode")))); print("exceptions",[r for r in rows if r.get("error")])'
raw_jsonl_records 46
event_counts {'run_started': 1, 'image_result': 44, 'default_flag_off_replay_check': 1}
modes {'default': 23, 'forced_prior_paired': 20, 'default_replay_flag_off': 1}
exceptions []
```

The first invocation stopped before inference with `ModuleNotFoundError: No module named 'engine'`; I corrected the new experiment runner’s repository import path and reran it. No pipeline code was changed. The runner checked CUDA before starting and before each model call and refused CPU fallback. It sequentially unloaded models between GPU stages.

The run produced 23 default-path image records, 20 paired forced-prior records for the measured-anchor images, and one default-mode replay. The unpaired images are the three images whose normal anchor was already prior tier. “Cannot verify” and “out of scope” results remain in the score tables; grams are null where the pipeline emitted no portion.

### Scoring and diagnostic rules

- Plate totals use the user-confirmed food-only totals: Dish 1 450 g; Dish 2 338 g; Dish 3 191 g; Dish 4 250 g; Dish 5 150 g; Dish 6 351 g.
- Signed error is predicted minus true; percentage error divides that signed error by the confirmed total. No averages or confidence intervals are used.
- Dishes 1–3 are classified correct only if exact normalized aliases cover all weighed component names. Dishes 4–6 follow the confirmed rubric: any predicted label containing “biryani” is correct. The displayed result includes plate-level and item-level predicted labels.
- Component grams are scored only for exact normalized component aliases. Thus `steamed-rice` can match rice; generic `sambar` does not match `keerai sambar`; `rice_sambar` does not match rice or tomato rasam; `vegetable_rice` does not match dum biryani. Unmatched predictions and ground-truth components are listed explicitly.
- For mask flags, an item is flagged if its pairwise IoU exceeds 0.5 or its area exceeds the top-level food-mask area. “Pixels outside top mask” is also shown. The hypothetical duplicate drop removes the lower-grams item in each >0.5-IoU pair (ties drop the later index); it does not alter reported pipeline totals. Items flagged only for exceeding the top-mask area are reported but are not automatically dropped in that hypothetical.
- Ground-truth values are defined in the new runner and used only after `pipeline.analyze()` returns. The analyze call receives the image, requested day/band/serving style, EXIF, and dependencies; no ground-truth grams or component labels are passed into the pipeline. This was checked in the runner source (`GROUND_TRUTH` and `pipeline.analyze` references).

### Findings and surprising outputs

The output contains large overestimates, large angle-to-angle changes, null totals, and repeated item labels. These were retained as observed. Dish 4–6 had no predicted biryani label; the gram-bearing images in those plates were labeled `vegetable_rice`, and the unrecognized images emitted no grams. The compliance verdict alone therefore does not indicate correct dish classification.

Several multi-item records show item-mask area sums much larger than the top-level food-mask area, and some item pairs exceed the 0.5 IoU flag. The raw results also show repeated `steamed-rice`/`vegetable_rice` items. I checked the runner call path for ground-truth leakage; none is passed to analysis. These are observations from this cohort, not a ranked causal diagnosis. No bug was fixed, and hypothetical mask dropping was not applied.

I also checked exact SHA-256 overlap against the local WED images and gallery source folder:

```text
$ .venv/bin/python experiments/oracle_ablation/check_aruco_hash_overlap.py
{"eval_images": 23, "event": "hash_overlap_check", "matches": [], "source_images_scanned": 2788, "source_root": "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/data/wed"}
{"eval_images": 23, "event": "hash_overlap_check", "matches": [], "source_images_scanned": 46, "source_root": "/home/tinkerer/Desktop/Nutrisense/DATASET"}
```

No exact image-hash match was found in those two local source sets. This check does not establish absence of near-duplicate or other external training leakage.

The flag-off replay of Dish 1 `20261025_184112.jpg` returned the same pipeline result, with matching SHA-256 `041a9c186e17fa8fc5c9d9aa2b74c89a2c66ef31083dd77677d8b064c22b5df6`. `--force-prior` is an opt-in CLI flag with default `false`; `--paired-card-vs-prior` opts into the paired analysis. The pipeline’s default code path was not changed.

### Lock and protected-file checks

```text
$ .venv/bin/python -m tools.check_locked
check_locked: 502 ok, 0 skipped, 0 failed (502 pinned)

$ git diff --no-ext-diff --stat 4f313fd -- tools/compare_runs.py docs/locked_manifest.txt
 docs/locked_manifest.txt |   4 +-
 tools/compare_runs.py    | 121 +++++++++++++++++++++++++++++++++++++++++++----
 2 files changed, 113 insertions(+), 12 deletions(-)

$ git status --short -- tools/compare_runs.py docs/locked_manifest.txt
(no output)
```

The diff against `4f313fd` is the already-known manifest timestamp/checksum and `tools/compare_runs.py` change; the current worktree has no uncommitted changes to either protected path. No protected file was edited by this evaluation. The full diff is saved in `protected_diff_from_4f313fd.txt`.

### Reproducible outputs

- Runner: `run_aruco_eval.py`; default behavior does not force prior. The paired run command above opts into forced-prior comparisons.
- Scorer/report tables: `summarize_aruco_eval.py`.
- Full raw per-image results and replay record: `aruco_raw.jsonl` (46 JSONL records).
- Scorer stdout captured verbatim: `aruco_score_output.md`.
- Protected-file diff: `protected_diff_from_4f313fd.txt`.

The full table output from `.venv/bin/python experiments/oracle_ablation/summarize_aruco_eval.py | tee experiments/oracle_ablation/aruco_score_output.md` follows.
## Per-image primary plate scores
| Plate | Image | Anchor | Predicted labels | Pred g | True g | Signed g | % err | Direction | Class correct | Verdict | Reason codes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dish 1 | 20261025_184112.jpg | measured | rice_sambar; steamed-rice | 496.8 | 450.0 | +46.8 | 10.4 | over | False | BORDERLINE | below_min, below_min |
| Dish 1 | 20261025_184421.jpg | measured | rice_sambar; steamed-rice | 1610.5 | 450.0 | +1160.5 | 257.9 | over | False | PASS | in_zone |
| Dish 1 | 20261025_191003.jpg | measured | vegetable_rice | 1068.6 | 450.0 | +618.6 | 137.5 | over | False | PASS | in_zone |
| Dish 1 | 20261025_191009.jpg | prior | vegetable_rice | 254.2 | 450.0 | -195.8 | -43.5 | under | False | FAIL | no_reference_card, below_min, below_min, below_min, below_min, below_min |
| Dish 1 | 20261025_191019.jpg | measured | vegetable_rice | 1753.4 | 450.0 | +1303.4 | 289.6 | over | False | PASS | in_zone |
| Dish 1 | this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg | prior | none | null | 450.0 | null | null | null | False | cannot_verify | unrecognized |
| Dish 2 | 20261027_085735.jpg | measured | rice_sambar; steamed-rice | 628.3 | 338.0 | +290.3 | 85.9 | over | False | BORDERLINE | below_min, below_min |
| Dish 2 | 20261027_085741.jpg | measured | rice_sambar; steamed-rice | 1773.3 | 338.0 | +1435.3 | 424.6 | over | False | PASS | in_zone |
| Dish 2 | 20261027_085746.jpg | prior | rice_sambar; steamed-rice | 812.0 | 338.0 | +474.0 | 140.2 | over | False | PASS | no_reference_card, in_zone |
| Dish 2 | Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg | measured | rice_sambar; steamed-rice | 887.1 | 338.0 | +549.1 | 162.5 | over | False | PASS | in_zone |
| Dish 3 | 127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg | measured | none | null | 191.0 | null | null | null | False | cannot_verify | unrecognized |
| Dish 3 | 20261029_125158.jpg | measured | wheat_product | null | 191.0 | null | null | null | False | out_of_scope | out_of_scope, classify |
| Dish 3 | 20261029_125203.jpg | measured | wheat_product | null | 191.0 | null | null | null | False | out_of_scope | out_of_scope, classify |
| Dish 4 | 127g plate 206g biryani rice 44 g egg.jpg | measured | vegetable_rice | 1751.8 | 250.0 | +1501.8 | 600.7 | over | False | PASS | in_zone |
| Dish 4 | 20261029_141529.jpg | measured | none | null | 250.0 | null | null | null | False | cannot_verify | unrecognized |
| Dish 4 | 20261029_141536.jpg | measured | vegetable_rice | 37.1 | 250.0 | -212.9 | -85.2 | under | False | BORDERLINE | below_min, below_min, below_min, below_min, coverage_gate |
| Dish 5 | 127g plate 150 g biryani rice.jpg | measured | vegetable_rice | 912.7 | 150.0 | +762.7 | 508.5 | over | False | PASS | in_zone |
| Dish 5 | 20261029_141201.jpg | measured | vegetable_rice | 1277.1 | 150.0 | +1127.1 | 751.4 | over | False | BORDERLINE | coverage_gate |
| Dish 5 | 20261029_141208.jpg | measured | none | null | 150.0 | null | null | null | False | cannot_verify | unrecognized |
| Dish 6 | 127 g plate 257g biryani rice 94g egg_.jpg | measured | vegetable_rice | 1566.0 | 351.0 | +1215.0 | 346.2 | over | False | PASS | in_zone |
| Dish 6 | 20261029_141720.jpg | measured | none | null | 351.0 | null | null | null | False | cannot_verify | unrecognized |
| Dish 6 | 20261029_141725.jpg | measured | vegetable_rice | 1119.4 | 351.0 | +768.4 | 218.9 | over | False | PASS | in_zone |
| Dish 6 | 20261029_141729.jpg | measured | vegetable_rice | 634.4 | 351.0 | +283.4 | 80.7 | over | False | PASS | in_zone |

## Anchor evidence and per-image item outputs
| Plate | Image | Anchor | Detector rejection evidence (prior only) | Items: label/grams/mask px/reason | Top mask px | Elapsed s | Stage timings s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dish 1 | 20261025_184112.jpg | measured | — | [{"i":0,"dish":"steamed-rice","grams":167.1,"mask_area_px":2724538,"reason":null},{"i":1,"dish":"steamed-rice","grams":153.3,"mask_area_px":2402128,"reason":null},{"i":2,"dish":"steamed-rice","grams":113.0,"mask_area_px":1608021,"reason":null},{"i":3,"dish":"steamed-rice","grams":63.3,"mask_area_px":1300319,"reason":null}] | 1379967 | 92.19 | {"anchor":0.10308862199599389,"classify":9.656655390004744,"compliance":0.00010412700066808611,"depth":6.597735175004345,"input":0.005595348004135303,"nutrition":0.012025519987219013,"segment":9.832182261001435} |
| Dish 1 | 20261025_184421.jpg | measured | — | [{"i":0,"dish":"steamed-rice","grams":742.2,"mask_area_px":4218220,"reason":null},{"i":1,"dish":"steamed-rice","grams":202.1,"mask_area_px":2232231,"reason":null},{"i":2,"dish":"steamed-rice","grams":506.6,"mask_area_px":1975106,"reason":null},{"i":3,"dish":"steamed-rice","grams":159.6,"mask_area_px":1490996,"reason":null}] | 1286348 | 87.20 | {"anchor":0.10401972298859619,"classify":10.125221305002924,"compliance":9.181100176647305e-05,"depth":6.757055195004796,"input":2.9071990866214037e-05,"nutrition":0.004930615992634557,"segment":7.082319791006739} |
| Dish 1 | 20261025_191003.jpg | measured | — | [{"i":0,"dish":"vegetable_rice","grams":475.2,"mask_area_px":3499043,"reason":null},{"i":1,"dish":"vegetable_rice","grams":365.8,"mask_area_px":3300762,"reason":null},{"i":2,"dish":"vegetable_rice","grams":227.6,"mask_area_px":2184022,"reason":null}] | 2089855 | 71.59 | {"anchor":0.09300982698914595,"classify":10.416873289999785,"compliance":7.77609966462478e-05,"depth":4.6946910960105015,"input":9.949013474397361e-06,"nutrition":0.0035203209990868345,"segment":7.1235428219952155} |
| Dish 1 | 20261025_191009.jpg | prior | no reference card in frame — scale from size priors | [{"i":0,"dish":"vegetable_rice","grams":86.7,"mask_area_px":4346223,"reason":null},{"i":1,"dish":"vegetable_rice","grams":86.9,"mask_area_px":2720417,"reason":null},{"i":2,"dish":"vegetable_rice","grams":80.6,"mask_area_px":2400658,"reason":null},{"i":3,"dish":null,"grams":null,"mask_area_px":2232006,"reason":"stage_failed"}] | 1816305 | 70.56 | {"anchor":0.11301824200199917,"classify":11.534076456999173,"compliance":0.00014375700266100466,"depth":4.729626643995289,"input":2.4262000806629658e-05,"nutrition":0.0143859310192056,"segment":6.775729059998412} |
| Dish 1 | 20261025_191019.jpg | measured | — | [{"i":0,"dish":"vegetable_rice","grams":852.9,"mask_area_px":3646769,"reason":null},{"i":1,"dish":"vegetable_rice","grams":368.5,"mask_area_px":2605024,"reason":null},{"i":2,"dish":"vegetable_rice","grams":532.1,"mask_area_px":2444502,"reason":null}] | 2099149 | 61.84 | {"anchor":0.12487870598852169,"classify":9.676108610001393,"compliance":7.142200774978846e-05,"depth":4.741035524013569,"input":9.357012459076941e-06,"nutrition":0.0033615619904594496,"segment":6.833756716005155} |
| Dish 1 | this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg | prior | no reference card in frame — scale from size priors | [] | 2064019 | 12.58 | {"anchor":0.06023841100977734,"classify":7.761602875005337,"input":1.4815013855695724e-05,"segment":4.638461795009789} |
| Dish 2 | 20261027_085735.jpg | measured | — | [{"i":0,"dish":"steamed-rice","grams":378.1,"mask_area_px":4067860,"reason":null},{"i":1,"dish":"steamed-rice","grams":129.2,"mask_area_px":1448331,"reason":null},{"i":2,"dish":"steamed-rice","grams":89.5,"mask_area_px":948036,"reason":null},{"i":3,"dish":"rice_sambar","grams":31.6,"mask_area_px":645945,"reason":null}] | 1801252 | 74.03 | {"anchor":0.06694914400577545,"classify":7.51106514899584,"compliance":8.233300468418747e-05,"depth":4.38267732001259,"input":1.014799636323005e-05,"nutrition":0.005098328008898534,"segment":4.966088601999218} |
| Dish 2 | 20261027_085741.jpg | measured | — | [{"i":0,"dish":"rice_sambar","grams":809.0,"mask_area_px":3927705,"reason":null},{"i":1,"dish":"steamed-rice","grams":271.7,"mask_area_px":3323511,"reason":null},{"i":2,"dish":"steamed-rice","grams":454.1,"mask_area_px":2515667,"reason":null},{"i":3,"dish":"steamed-rice","grams":238.6,"mask_area_px":960638,"reason":null}] | 2689984 | 85.32 | {"anchor":0.06811930199910421,"classify":11.305858184001409,"compliance":7.286100299097598e-05,"depth":4.38916562499071,"input":9.71299596130848e-06,"nutrition":0.005129034994752146,"segment":7.299870284012286} |
| Dish 2 | 20261027_085746.jpg | prior | no reference card in frame — scale from size priors | [{"i":0,"dish":"rice_sambar","grams":330.5,"mask_area_px":4226287,"reason":null},{"i":1,"dish":"steamed-rice","grams":163.6,"mask_area_px":1625605,"reason":null},{"i":2,"dish":"steamed-rice","grams":159.6,"mask_area_px":1606238,"reason":null},{"i":3,"dish":"steamed-rice","grams":158.2,"mask_area_px":1022036,"reason":null}] | 1921043 | 77.15 | {"anchor":0.05236607699771412,"classify":11.132386218989268,"compliance":7.983800605870783e-05,"depth":4.348314108996419,"input":1.1787007679231465e-05,"nutrition":0.005251533002592623,"segment":6.999805893006851} |
| Dish 2 | Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg | measured | — | [{"i":0,"dish":"steamed-rice","grams":690.3,"mask_area_px":3342706,"reason":null},{"i":1,"dish":"rice_sambar","grams":196.8,"mask_area_px":2115348,"reason":null},{"i":2,"dish":null,"grams":null,"mask_area_px":2102001,"reason":"unrecognized"},{"i":3,"dish":null,"grams":null,"mask_area_px":2093472,"reason":"unrecognized"}] | 2238762 | 72.71 | {"anchor":0.07257917600509245,"classify":7.920011782000074,"compliance":8.290499681606889e-05,"depth":4.5745467559900135,"input":9.637995390221477e-06,"nutrition":0.002877592996810563,"segment":6.3875513349921675} |
| Dish 3 | 127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg | measured | — | [] | 1197398 | 18.43 | {"anchor":0.06842740801221225,"classify":11.163636110009975,"input":1.1580006685107946e-05,"segment":7.078766294012894} |
| Dish 3 | 20261029_125158.jpg | measured | — | [] | 2756814 | 17.85 | {"anchor":0.0833651119901333,"classify":11.054211994996876,"input":9.744995622895658e-06,"segment":6.602398594011902} |
| Dish 3 | 20261029_125203.jpg | measured | — | [] | 1486967 | 18.12 | {"anchor":0.06534586500492878,"classify":11.074702343990793,"input":9.291994501836598e-06,"segment":6.862425393002923} |
| Dish 4 | 127g plate 206g biryani rice 44 g egg.jpg | measured | — | [{"i":0,"dish":"vegetable_rice","grams":648.4,"mask_area_px":3380699,"reason":null},{"i":1,"dish":"vegetable_rice","grams":683.7,"mask_area_px":3236007,"reason":null},{"i":2,"dish":"vegetable_rice","grams":419.8,"mask_area_px":2184598,"reason":null}] | 2863780 | 78.05 | {"anchor":0.1459450230031507,"classify":12.71680895400641,"compliance":7.979400106705725e-05,"depth":4.970642954009236,"input":9.388997568748891e-06,"nutrition":0.013033876020926982,"segment":6.949135802002274} |
| Dish 4 | 20261029_141529.jpg | measured | — | [] | 2109544 | 18.73 | {"anchor":0.07004914700519294,"classify":11.356600344995968,"input":9.705981938168406e-06,"segment":7.1873183860006975} |
| Dish 4 | 20261029_141536.jpg | measured | — | [{"i":0,"dish":"vegetable_rice","grams":37.1,"mask_area_px":3008664,"reason":null},{"i":1,"dish":null,"grams":null,"mask_area_px":2618164,"reason":"unrecognized"},{"i":2,"dish":null,"grams":null,"mask_area_px":466210,"reason":"unrecognized"}] | 1910322 | 68.77 | {"anchor":0.08335504900605883,"classify":11.344288401000085,"compliance":9.980399045161903e-05,"depth":4.608114071001182,"input":1.0969015420414507e-05,"nutrition":0.0011168320052092895,"segment":7.5184228389989585} |
| Dish 5 | 127g plate 150 g biryani rice.jpg | measured | — | [{"i":0,"dish":"vegetable_rice","grams":533.2,"mask_area_px":4593227,"reason":null},{"i":1,"dish":"vegetable_rice","grams":227.6,"mask_area_px":2685175,"reason":null},{"i":2,"dish":"vegetable_rice","grams":151.9,"mask_area_px":2205702,"reason":null}] | 1724261 | 72.45 | {"anchor":0.07607954301056452,"classify":11.381793975000619,"compliance":8.27189942356199e-05,"depth":4.555471041996498,"input":9.486990165896714e-06,"nutrition":0.0035672509839059785,"segment":7.767696262992104} |
| Dish 5 | 20261029_141201.jpg | measured | — | [{"i":0,"dish":"vegetable_rice","grams":626.4,"mask_area_px":3965049,"reason":null},{"i":1,"dish":"vegetable_rice","grams":322.9,"mask_area_px":3625213,"reason":null},{"i":2,"dish":"vegetable_rice","grams":245.0,"mask_area_px":2754232,"reason":null},{"i":3,"dish":"vegetable_rice","grams":82.8,"mask_area_px":1921954,"reason":null}] | 2266667 | 86.92 | {"anchor":0.058875828006421216,"classify":13.56572892901022,"compliance":8.276200969703496e-05,"depth":4.5785532540030545,"input":9.0529938461259e-06,"nutrition":0.004515066015301272,"segment":6.94694605100085} |
| Dish 5 | 20261029_141208.jpg | measured | — | [] | 1592781 | 18.42 | {"anchor":0.06588466199173126,"classify":12.161935431999154,"input":9.916999260894954e-06,"segment":6.074917374004144} |
| Dish 6 | 127 g plate 257g biryani rice 94g egg_.jpg | measured | — | [{"i":0,"dish":"vegetable_rice","grams":253.6,"mask_area_px":2861409,"reason":null},{"i":1,"dish":"vegetable_rice","grams":612.7,"mask_area_px":2834771,"reason":null},{"i":2,"dish":"vegetable_rice","grams":251.5,"mask_area_px":2508434,"reason":null},{"i":3,"dish":"vegetable_rice","grams":448.3,"mask_area_px":2231172,"reason":null}] | 2289673 | 86.39 | {"anchor":0.08188172600057442,"classify":10.890571676995023,"compliance":7.46589939808473e-05,"depth":5.184104433006723,"input":1.0236006346531212e-05,"nutrition":0.004811059014173225,"segment":7.17264103499474} |
| Dish 6 | 20261029_141720.jpg | measured | — | [] | 659116 | 18.08 | {"anchor":0.09763786899566185,"classify":10.708223609006382,"input":9.594994480721653e-06,"segment":7.163723647987354} |
| Dish 6 | 20261029_141725.jpg | measured | — | [{"i":0,"dish":"vegetable_rice","grams":491.0,"mask_area_px":2794936,"reason":null},{"i":1,"dish":"vegetable_rice","grams":410.3,"mask_area_px":2384894,"reason":null},{"i":2,"dish":"vegetable_rice","grams":218.0,"mask_area_px":2075288,"reason":null}] | 2552359 | 62.56 | {"anchor":0.08406314499734435,"classify":11.361051106010564,"compliance":7.880099292378873e-05,"depth":4.54440639699169,"input":8.9230015873909e-06,"nutrition":0.003567306004697457,"segment":6.517744600001606} |
| Dish 6 | 20261029_141729.jpg | measured | — | [{"i":0,"dish":"vegetable_rice","grams":310.4,"mask_area_px":6290118,"reason":null},{"i":1,"dish":"vegetable_rice","grams":272.1,"mask_area_px":2169799,"reason":null},{"i":2,"dish":"vegetable_rice","grams":51.9,"mask_area_px":827381,"reason":null}] | 2281769 | 72.50 | {"anchor":0.08483582499320619,"classify":10.388756062005996,"compliance":7.138799992389977e-05,"depth":4.713582766999025,"input":9.473005775362253e-06,"nutrition":0.003280447985162027,"segment":6.993255410998245} |

## Per-component scores and unmatched labels
| Plate | Image | Component/status | Pred g | True g | Signed g | % err | Matched items / unmatched detail |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dish 1 | 20261025_184112.jpg | rice | 496.7 | 250 | +246.7 | 98.7 | [{"dish_label": "steamed-rice", "grams": 167.1, "item_index": 0}, {"dish_label": "steamed-rice", "grams": 153.3, "item_index": 1}, {"dish_label": "steamed-rice", "grams": 113.0, "item_index": 2}, {"dish_label": "steamed-rice", "grams": 63.3, "item_index": 3}] |
| Dish 1 | 20261025_184112.jpg | keerai sambar | null | 200 | null | null | [] |
| Dish 1 | 20261025_184112.jpg | UNMATCHED ITEMS | — | — | — | — | [] |
| Dish 1 | 20261025_184112.jpg | UNMATCHED COMPONENTS | — | — | — | — | keerai sambar |
| Dish 1 | 20261025_184421.jpg | rice | 1610.5 | 250 | +1360.5 | 544.2 | [{"dish_label": "steamed-rice", "grams": 742.2, "item_index": 0}, {"dish_label": "steamed-rice", "grams": 202.1, "item_index": 1}, {"dish_label": "steamed-rice", "grams": 506.6, "item_index": 2}, {"dish_label": "steamed-rice", "grams": 159.6, "item_index": 3}] |
| Dish 1 | 20261025_184421.jpg | keerai sambar | null | 200 | null | null | [] |
| Dish 1 | 20261025_184421.jpg | UNMATCHED ITEMS | — | — | — | — | [] |
| Dish 1 | 20261025_184421.jpg | UNMATCHED COMPONENTS | — | — | — | — | keerai sambar |
| Dish 1 | 20261025_191003.jpg | rice | null | 250 | null | null | [] |
| Dish 1 | 20261025_191003.jpg | keerai sambar | null | 200 | null | null | [] |
| Dish 1 | 20261025_191003.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "vegetable_rice", "grams": 475.2, "item_index": 0, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 365.8, "item_index": 1, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 227.6, "item_index": 2, "reason": "no exact component alias match"}] |
| Dish 1 | 20261025_191003.jpg | UNMATCHED COMPONENTS | — | — | — | — | rice, keerai sambar |
| Dish 1 | 20261025_191009.jpg | rice | null | 250 | null | null | [] |
| Dish 1 | 20261025_191009.jpg | keerai sambar | null | 200 | null | null | [] |
| Dish 1 | 20261025_191009.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "vegetable_rice", "grams": 86.7, "item_index": 0, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 86.9, "item_index": 1, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 80.6, "item_index": 2, "reason": "no exact component alias match"}, {"dish_label": null, "grams": null, "item_index": 3, "reason": "no dish label"}] |
| Dish 1 | 20261025_191009.jpg | UNMATCHED COMPONENTS | — | — | — | — | rice, keerai sambar |
| Dish 1 | 20261025_191019.jpg | rice | null | 250 | null | null | [] |
| Dish 1 | 20261025_191019.jpg | keerai sambar | null | 200 | null | null | [] |
| Dish 1 | 20261025_191019.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "vegetable_rice", "grams": 852.9, "item_index": 0, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 368.5, "item_index": 1, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 532.1, "item_index": 2, "reason": "no exact component alias match"}] |
| Dish 1 | 20261025_191019.jpg | UNMATCHED COMPONENTS | — | — | — | — | rice, keerai sambar |
| Dish 1 | this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg | rice | null | 250 | null | null | [] |
| Dish 1 | this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg | keerai sambar | null | 200 | null | null | [] |
| Dish 1 | this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg | UNMATCHED ITEMS | — | — | — | — | [] |
| Dish 1 | this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg | UNMATCHED COMPONENTS | — | — | — | — | rice, keerai sambar |
| Dish 2 | 20261027_085735.jpg | rice | 596.8 | 211 | +385.8 | 182.8 | [{"dish_label": "steamed-rice", "grams": 378.1, "item_index": 0}, {"dish_label": "steamed-rice", "grams": 129.2, "item_index": 1}, {"dish_label": "steamed-rice", "grams": 89.5, "item_index": 2}] |
| Dish 2 | 20261027_085735.jpg | tomato rasam | null | 127 | null | null | [] |
| Dish 2 | 20261027_085735.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "rice_sambar", "grams": 31.6, "item_index": 3, "reason": "no exact component alias match"}] |
| Dish 2 | 20261027_085735.jpg | UNMATCHED COMPONENTS | — | — | — | — | tomato rasam |
| Dish 2 | 20261027_085741.jpg | rice | 964.4 | 211 | +753.4 | 357.1 | [{"dish_label": "steamed-rice", "grams": 271.7, "item_index": 1}, {"dish_label": "steamed-rice", "grams": 454.1, "item_index": 2}, {"dish_label": "steamed-rice", "grams": 238.6, "item_index": 3}] |
| Dish 2 | 20261027_085741.jpg | tomato rasam | null | 127 | null | null | [] |
| Dish 2 | 20261027_085741.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "rice_sambar", "grams": 809.0, "item_index": 0, "reason": "no exact component alias match"}] |
| Dish 2 | 20261027_085741.jpg | UNMATCHED COMPONENTS | — | — | — | — | tomato rasam |
| Dish 2 | 20261027_085746.jpg | rice | 481.4 | 211 | +270.4 | 128.2 | [{"dish_label": "steamed-rice", "grams": 163.6, "item_index": 1}, {"dish_label": "steamed-rice", "grams": 159.6, "item_index": 2}, {"dish_label": "steamed-rice", "grams": 158.2, "item_index": 3}] |
| Dish 2 | 20261027_085746.jpg | tomato rasam | null | 127 | null | null | [] |
| Dish 2 | 20261027_085746.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "rice_sambar", "grams": 330.5, "item_index": 0, "reason": "no exact component alias match"}] |
| Dish 2 | 20261027_085746.jpg | UNMATCHED COMPONENTS | — | — | — | — | tomato rasam |
| Dish 2 | Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg | rice | 690.3 | 211 | +479.3 | 227.2 | [{"dish_label": "steamed-rice", "grams": 690.3, "item_index": 0}] |
| Dish 2 | Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg | tomato rasam | null | 127 | null | null | [] |
| Dish 2 | Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "rice_sambar", "grams": 196.8, "item_index": 1, "reason": "no exact component alias match"}, {"dish_label": null, "grams": null, "item_index": 2, "reason": "no dish label"}, {"dish_label": null, "grams": null, "item_index": 3, "reason": "no dish label"}] |
| Dish 2 | Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg | UNMATCHED COMPONENTS | — | — | — | — | tomato rasam |
| Dish 3 | 127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg | coconut chutney | null | 70 | null | null | [] |
| Dish 3 | 127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg | chapati (2 total) | null | 121 | null | null | [] |
| Dish 3 | 127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg | UNMATCHED ITEMS | — | — | — | — | [] |
| Dish 3 | 127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg | UNMATCHED COMPONENTS | — | — | — | — | coconut chutney, chapati (2 total) |
| Dish 3 | 20261029_125158.jpg | coconut chutney | null | 70 | null | null | [] |
| Dish 3 | 20261029_125158.jpg | chapati (2 total) | null | 121 | null | null | [] |
| Dish 3 | 20261029_125158.jpg | UNMATCHED ITEMS | — | — | — | — | [] |
| Dish 3 | 20261029_125158.jpg | UNMATCHED COMPONENTS | — | — | — | — | coconut chutney, chapati (2 total) |
| Dish 3 | 20261029_125203.jpg | coconut chutney | null | 70 | null | null | [] |
| Dish 3 | 20261029_125203.jpg | chapati (2 total) | null | 121 | null | null | [] |
| Dish 3 | 20261029_125203.jpg | UNMATCHED ITEMS | — | — | — | — | [] |
| Dish 3 | 20261029_125203.jpg | UNMATCHED COMPONENTS | — | — | — | — | coconut chutney, chapati (2 total) |
| Dish 4 | 127g plate 206g biryani rice 44 g egg.jpg | dum biryani | null | 206 | null | null | [] |
| Dish 4 | 127g plate 206g biryani rice 44 g egg.jpg | egg (1) | null | 44 | null | null | [] |
| Dish 4 | 127g plate 206g biryani rice 44 g egg.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "vegetable_rice", "grams": 648.4, "item_index": 0, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 683.7, "item_index": 1, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 419.8, "item_index": 2, "reason": "no exact component alias match"}] |
| Dish 4 | 127g plate 206g biryani rice 44 g egg.jpg | UNMATCHED COMPONENTS | — | — | — | — | dum biryani, egg (1) |
| Dish 4 | 20261029_141529.jpg | dum biryani | null | 206 | null | null | [] |
| Dish 4 | 20261029_141529.jpg | egg (1) | null | 44 | null | null | [] |
| Dish 4 | 20261029_141529.jpg | UNMATCHED ITEMS | — | — | — | — | [] |
| Dish 4 | 20261029_141529.jpg | UNMATCHED COMPONENTS | — | — | — | — | dum biryani, egg (1) |
| Dish 4 | 20261029_141536.jpg | dum biryani | null | 206 | null | null | [] |
| Dish 4 | 20261029_141536.jpg | egg (1) | null | 44 | null | null | [] |
| Dish 4 | 20261029_141536.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "vegetable_rice", "grams": 37.1, "item_index": 0, "reason": "no exact component alias match"}, {"dish_label": null, "grams": null, "item_index": 1, "reason": "no dish label"}, {"dish_label": null, "grams": null, "item_index": 2, "reason": "no dish label"}] |
| Dish 4 | 20261029_141536.jpg | UNMATCHED COMPONENTS | — | — | — | — | dum biryani, egg (1) |
| Dish 5 | 127g plate 150 g biryani rice.jpg | dum biryani | null | 150 | null | null | [] |
| Dish 5 | 127g plate 150 g biryani rice.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "vegetable_rice", "grams": 533.2, "item_index": 0, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 227.6, "item_index": 1, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 151.9, "item_index": 2, "reason": "no exact component alias match"}] |
| Dish 5 | 127g plate 150 g biryani rice.jpg | UNMATCHED COMPONENTS | — | — | — | — | dum biryani |
| Dish 5 | 20261029_141201.jpg | dum biryani | null | 150 | null | null | [] |
| Dish 5 | 20261029_141201.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "vegetable_rice", "grams": 626.4, "item_index": 0, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 322.9, "item_index": 1, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 245.0, "item_index": 2, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 82.8, "item_index": 3, "reason": "no exact component alias match"}] |
| Dish 5 | 20261029_141201.jpg | UNMATCHED COMPONENTS | — | — | — | — | dum biryani |
| Dish 5 | 20261029_141208.jpg | dum biryani | null | 150 | null | null | [] |
| Dish 5 | 20261029_141208.jpg | UNMATCHED ITEMS | — | — | — | — | [] |
| Dish 5 | 20261029_141208.jpg | UNMATCHED COMPONENTS | — | — | — | — | dum biryani |
| Dish 6 | 127 g plate 257g biryani rice 94g egg_.jpg | dum biryani | null | 257 | null | null | [] |
| Dish 6 | 127 g plate 257g biryani rice 94g egg_.jpg | egg (2 total) | null | 94 | null | null | [] |
| Dish 6 | 127 g plate 257g biryani rice 94g egg_.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "vegetable_rice", "grams": 253.6, "item_index": 0, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 612.7, "item_index": 1, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 251.5, "item_index": 2, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 448.3, "item_index": 3, "reason": "no exact component alias match"}] |
| Dish 6 | 127 g plate 257g biryani rice 94g egg_.jpg | UNMATCHED COMPONENTS | — | — | — | — | dum biryani, egg (2 total) |
| Dish 6 | 20261029_141720.jpg | dum biryani | null | 257 | null | null | [] |
| Dish 6 | 20261029_141720.jpg | egg (2 total) | null | 94 | null | null | [] |
| Dish 6 | 20261029_141720.jpg | UNMATCHED ITEMS | — | — | — | — | [] |
| Dish 6 | 20261029_141720.jpg | UNMATCHED COMPONENTS | — | — | — | — | dum biryani, egg (2 total) |
| Dish 6 | 20261029_141725.jpg | dum biryani | null | 257 | null | null | [] |
| Dish 6 | 20261029_141725.jpg | egg (2 total) | null | 94 | null | null | [] |
| Dish 6 | 20261029_141725.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "vegetable_rice", "grams": 491.0, "item_index": 0, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 410.3, "item_index": 1, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 218.0, "item_index": 2, "reason": "no exact component alias match"}] |
| Dish 6 | 20261029_141725.jpg | UNMATCHED COMPONENTS | — | — | — | — | dum biryani, egg (2 total) |
| Dish 6 | 20261029_141729.jpg | dum biryani | null | 257 | null | null | [] |
| Dish 6 | 20261029_141729.jpg | egg (2 total) | null | 94 | null | null | [] |
| Dish 6 | 20261029_141729.jpg | UNMATCHED ITEMS | — | — | — | — | [{"dish_label": "vegetable_rice", "grams": 310.4, "item_index": 0, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 272.1, "item_index": 1, "reason": "no exact component alias match"}, {"dish_label": "vegetable_rice", "grams": 51.9, "item_index": 2, "reason": "no exact component alias match"}] |
| Dish 6 | 20261029_141729.jpg | UNMATCHED COMPONENTS | — | — | — | — | dum biryani, egg (2 total) |

## Plate direction and angle spread (default detected anchors only)
| Plate | True g | Direction across available predictions | Measured-anchor spread | Prior-anchor spread |
| --- | --- | --- | --- | --- |
| Dish 1 | 450 | mixed | 496.8–1753.4 g; range 1256.6 g (279.2% true) | 254.2–254.2 g; range 0.0 g (0.0% true) |
| Dish 2 | 338 | over | 628.3–1773.3 g; range 1145.0 g (338.8% true) | 812.0–812.0 g; range 0.0 g (0.0% true) |
| Dish 3 | 191 | no grams | n/a | n/a |
| Dish 4 | 250 | mixed | 37.1–1751.8 g; range 1714.7 g (685.9% true) | n/a |
| Dish 5 | 150 | over | 912.7–1277.1 g; range 364.4 g (242.9% true) | n/a |
| Dish 6 | 351 | over | 634.4–1566.0 g; range 931.6 g (265.4% true) | n/a |

## Paired card versus forced-prior errors (same measured-anchor images)
| Plate | Image | Card pred g | Card signed g | Forced-prior pred g | Forced-prior signed g | Prior minus card g |
| --- | --- | --- | --- | --- | --- | --- |
| Dish 1 | 20261025_184112.jpg | 496.8 | +46.8 | 819.4 | +369.4 | +322.6 |
| Dish 1 | 20261025_184421.jpg | 1610.5 | +1160.5 | 704.8 | +254.8 | -905.7 |
| Dish 1 | 20261025_191003.jpg | 1068.6 | +618.6 | 219.4 | -230.6 | -849.2 |
| Dish 1 | 20261025_191019.jpg | 1753.4 | +1303.4 | 196.1 | -253.9 | -1557.3 |
| Dish 2 | 20261027_085735.jpg | 628.3 | +290.3 | 813.1 | +475.1 | +184.8 |
| Dish 2 | 20261027_085741.jpg | 1773.3 | +1435.3 | 903.2 | +565.2 | -870.1 |
| Dish 2 | Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg | 887.1 | +549.1 | 490.8 | +152.8 | -396.3 |
| Dish 3 | 127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg | null | null | null | null | null |
| Dish 3 | 20261029_125158.jpg | null | null | null | null | null |
| Dish 3 | 20261029_125203.jpg | null | null | null | null | null |
| Dish 4 | 127g plate 206g biryani rice 44 g egg.jpg | 1751.8 | +1501.8 | 214.6 | -35.4 | -1537.2 |
| Dish 4 | 20261029_141529.jpg | null | null | null | null | null |
| Dish 4 | 20261029_141536.jpg | 37.1 | -212.9 | 85.3 | -164.7 | +48.2 |
| Dish 5 | 127g plate 150 g biryani rice.jpg | 912.7 | +762.7 | 227.1 | +77.1 | -685.6 |
| Dish 5 | 20261029_141201.jpg | 1277.1 | +1127.1 | 264.6 | +114.6 | -1012.5 |
| Dish 5 | 20261029_141208.jpg | null | null | null | null | null |
| Dish 6 | 127 g plate 257g biryani rice 94g egg_.jpg | 1566.0 | +1215.0 | 353.7 | +2.7 | -1212.3 |
| Dish 6 | 20261029_141720.jpg | null | null | null | null | null |
| Dish 6 | 20261029_141725.jpg | 1119.4 | +768.4 | 276.1 | -74.9 | -843.3 |
| Dish 6 | 20261029_141729.jpg | 634.4 | +283.4 | 277.0 | -74.0 | -357.4 |
Flag-off replay check: {"event": "default_flag_off_replay_check", "identical_pipeline_result": true, "image": "/home/tinkerer/Desktop/Nutrisense/Aruco_7ID_60mm_with_food/Dish 1/20261025_184112.jpg", "original_result_sha256": "041a9c186e17fa8fc5c9d9aa2b74c89a2c66ef31083dd77677d8b064c22b5df6", "replay_result_sha256": "041a9c186e17fa8fc5c9d9aa2b74c89a2c66ef31083dd77677d8b064c22b5df6"}
Replay result: {"anchor_tier": "measured", "grams": 496.8, "image": "20261025_184112.jpg"}

## Duplicate-mask and area checks (all default images with >1 output item)
| Plate | Image | Items | Top area px | Sum item px | Sum/top | Max IoU | All pairwise IoU | Item mask areas/outside | Flagged idx | Flagged grams (% total) | Pred total | If overlap duplicate dropped | Delta g |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dish 1 | 20261025_184112.jpg | 4 | 1379967 | 8035006 | 5.823 | 0.523 | [{"i":0,"j":1,"iou":0.001402},{"i":0,"j":2,"iou":0.523145},{"i":0,"j":3,"iou":0.052152},{"i":1,"j":2,"iou":0.019302},{"i":1,"j":3,"iou":0.263235},{"i":2,"j":3,"iou":0.082049}] | [{"area_frac":0.22704483333333333,"area_px":2724538,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":2717788},{"area_frac":0.20017733333333335,"area_px":2402128,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":1648355},{"area_frac":0.13400175,"area_px":1608021,"exceeds_top_food_area":true,"item_index":2,"pixels_outside_top_food_mask":1605952},{"area_frac":0.10835991666666667,"area_px":1300319,"exceeds_top_food_area":false,"item_index":3,"pixels_outside_top_food_mask":268676}] | 0,1,2 | 433.4 known g (87.2% total; missing item grams=0) | 496.8 | 383.7 | -113.1 |
| Dish 1 | 20261025_184421.jpg | 4 | 1286348 | 9916553 | 7.709 | 0.613 | [{"i":0,"j":1,"iou":0.000518},{"i":0,"j":2,"iou":0.424344},{"i":0,"j":3,"iou":0.000425},{"i":1,"j":2,"iou":0.019602},{"i":1,"j":3,"iou":0.613077},{"i":2,"j":3,"iou":0.012003}] | [{"area_frac":0.3515183333333333,"area_px":4218220,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":4218220},{"area_frac":0.18601925,"area_px":2232231,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":991997},{"area_frac":0.16459216666666668,"area_px":1975106,"exceeds_top_food_area":true,"item_index":2,"pixels_outside_top_food_mask":1975106},{"area_frac":0.12424966666666666,"area_px":1490996,"exceeds_top_food_area":true,"item_index":3,"pixels_outside_top_food_mask":237104}] | 0,1,2,3 | 1610.5 known g (100.0% total; missing item grams=0) | 1610.5 | 1450.9 | -159.6 |
| Dish 1 | 20261025_191003.jpg | 3 | 2089855 | 8983827 | 4.299 | 0.557 | [{"i":0,"j":1,"iou":0.009491},{"i":0,"j":2,"iou":0.55706},{"i":1,"j":2,"iou":0.01201}] | [{"area_frac":0.29158691666666664,"area_px":3499043,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":1413831},{"area_frac":0.2750635,"area_px":3300762,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":3300762},{"area_frac":0.18200183333333333,"area_px":2184022,"exceeds_top_food_area":true,"item_index":2,"pixels_outside_top_food_mask":1499169}] | 0,1,2 | 1068.6 known g (100.0% total; missing item grams=0) | 1068.6 | 841.0 | -227.6 |
| Dish 1 | 20261025_191009.jpg | 4 | 1816305 | 11699304 | 6.441 | 0.636 | [{"i":0,"j":1,"iou":0.437344},{"i":0,"j":2,"iou":0.001324},{"i":0,"j":3,"iou":0.011782},{"i":1,"j":2,"iou":0.071783},{"i":1,"j":3,"iou":0.115833},{"i":2,"j":3,"iou":0.635548}] | [{"area_frac":0.36218525,"area_px":4346223,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":4346223},{"area_frac":0.22670141666666666,"area_px":2720417,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":2720373},{"area_frac":0.20005483333333332,"area_px":2400658,"exceeds_top_food_area":true,"item_index":2,"pixels_outside_top_food_mask":590194},{"area_frac":0.1860005,"area_px":2232006,"exceeds_top_food_area":true,"item_index":3,"pixels_outside_top_food_mask":852667}] | 0,1,2,3 | 254.2 known g (100.0% total; missing item grams=1) | 254.2 | null | null |
| Dish 1 | 20261025_191019.jpg | 3 | 2099149 | 8696295 | 4.143 | 0.648 | [{"i":0,"j":1,"iou":0.280883},{"i":0,"j":2,"iou":0.648098},{"i":1,"j":2,"iou":0.385333}] | [{"area_frac":0.30389741666666664,"area_px":3646769,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":1549275},{"area_frac":0.21708533333333332,"area_px":2605024,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":2549531},{"area_frac":0.2037085,"area_px":2444502,"exceeds_top_food_area":true,"item_index":2,"pixels_outside_top_food_mask":1548245}] | 0,1,2 | 1753.5 known g (100.0% total; missing item grams=0) | 1753.4 | 1221.4 | -532.0 |
| Dish 2 | 20261027_085735.jpg | 4 | 1801252 | 7110172 | 3.947 | 0.057 | [{"i":0,"j":1,"iou":0.006423},{"i":0,"j":2,"iou":3.8e-05},{"i":0,"j":3,"iou":0.056958},{"i":1,"j":2,"iou":0.027536},{"i":1,"j":3,"iou":0.011096},{"i":2,"j":3,"iou":0.0}] | [{"area_frac":0.33898833333333334,"area_px":4067860,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":4067624},{"area_frac":0.12069425,"area_px":1448331,"exceeds_top_food_area":false,"item_index":1,"pixels_outside_top_food_mask":42247},{"area_frac":0.079003,"area_px":948036,"exceeds_top_food_area":false,"item_index":2,"pixels_outside_top_food_mask":880145},{"area_frac":0.05382875,"area_px":645945,"exceeds_top_food_area":false,"item_index":3,"pixels_outside_top_food_mask":645945}] | 0 | 378.1 known g (60.2% total; missing item grams=0) | 628.3 | 628.4 | +0.1 |
| Dish 2 | 20261027_085741.jpg | 4 | 2689984 | 10727521 | 3.988 | 0.479 | [{"i":0,"j":1,"iou":0.001419},{"i":0,"j":2,"iou":0.005424},{"i":0,"j":3,"iou":0.003435},{"i":1,"j":2,"iou":0.478965},{"i":1,"j":3,"iou":0.156025},{"i":2,"j":3,"iou":0.027028}] | [{"area_frac":0.32730875,"area_px":3927705,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":3913217},{"area_frac":0.27695925,"area_px":3323511,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":1422939},{"area_frac":0.20963891666666667,"area_px":2515667,"exceeds_top_food_area":false,"item_index":2,"pixels_outside_top_food_mask":41168},{"area_frac":0.08005316666666666,"area_px":960638,"exceeds_top_food_area":false,"item_index":3,"pixels_outside_top_food_mask":869964}] | 0,1 | 1080.7 known g (60.9% total; missing item grams=0) | 1773.3 | 1773.4 | +0.1 |
| Dish 2 | 20261027_085746.jpg | 4 | 1921043 | 8480166 | 4.414 | 0.635 | [{"i":0,"j":1,"iou":0.000787},{"i":0,"j":2,"iou":6.6e-05},{"i":0,"j":3,"iou":3.7e-05},{"i":1,"j":2,"iou":0.269747},{"i":1,"j":3,"iou":0.062666},{"i":2,"j":3,"iou":0.635343}] | [{"area_frac":0.3521905833333333,"area_px":4226287,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":4224366},{"area_frac":0.13546708333333332,"area_px":1625605,"exceeds_top_food_area":false,"item_index":1,"pixels_outside_top_food_mask":11678},{"area_frac":0.13385316666666666,"area_px":1606238,"exceeds_top_food_area":false,"item_index":2,"pixels_outside_top_food_mask":912281},{"area_frac":0.08516966666666667,"area_px":1022036,"exceeds_top_food_area":false,"item_index":3,"pixels_outside_top_food_mask":863082}] | 0,2,3 | 648.3 known g (79.8% total; missing item grams=0) | 812.0 | 653.7 | -158.3 |
| Dish 2 | Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg | 4 | 2238762 | 9653527 | 4.312 | 0.577 | [{"i":0,"j":1,"iou":0.001762},{"i":0,"j":2,"iou":0.013059},{"i":0,"j":3,"iou":0.001016},{"i":1,"j":2,"iou":0.577158},{"i":1,"j":3,"iou":0.430059},{"i":2,"j":3,"iou":0.287295}] | [{"area_frac":0.2785588333333333,"area_px":3342706,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":3332939},{"area_frac":0.176279,"area_px":2115348,"exceeds_top_food_area":false,"item_index":1,"pixels_outside_top_food_mask":566908},{"area_frac":0.17516675,"area_px":2102001,"exceeds_top_food_area":false,"item_index":2,"pixels_outside_top_food_mask":78222},{"area_frac":0.174456,"area_px":2093472,"exceeds_top_food_area":false,"item_index":3,"pixels_outside_top_food_mask":1160023}] | 0,1,2 | 887.1 known g (100.0% total; missing item grams=1) | 887.1 | null | null |
| Dish 4 | 127g plate 206g biryani rice 44 g egg.jpg | 3 | 2863780 | 8801304 | 3.073 | 0.657 | [{"i":0,"j":1,"iou":0.415397},{"i":0,"j":2,"iou":0.199675},{"i":1,"j":2,"iou":0.65682}] | [{"area_frac":0.28172491666666666,"area_px":3380699,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":568865},{"area_frac":0.26966725,"area_px":3236007,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":1787441},{"area_frac":0.18204983333333333,"area_px":2184598,"exceeds_top_food_area":false,"item_index":2,"pixels_outside_top_food_mask":1742388}] | 0,1,2 | 1751.9 known g (100.0% total; missing item grams=0) | 1751.8 | 1332.1 | -419.7 |
| Dish 4 | 20261029_141536.jpg | 3 | 1910322 | 6093038 | 3.190 | 0.545 | [{"i":0,"j":1,"iou":0.54525},{"i":0,"j":2,"iou":0.011592},{"i":1,"j":2,"iou":0.025917}] | [{"area_frac":0.250722,"area_px":3008664,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":1103192},{"area_frac":0.21818033333333334,"area_px":2618164,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":1565886},{"area_frac":0.038850833333333334,"area_px":466210,"exceeds_top_food_area":false,"item_index":2,"pixels_outside_top_food_mask":466102}] | 0,1 | 37.1 known g (100.0% total; missing item grams=1) | 37.1 | null | null |
| Dish 5 | 127g plate 150 g biryani rice.jpg | 3 | 1724261 | 9484104 | 5.500 | 0.378 | [{"i":0,"j":1,"iou":0.003124},{"i":0,"j":2,"iou":0.005318},{"i":1,"j":2,"iou":0.377506}] | [{"area_frac":0.3827689166666667,"area_px":4593227,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":4593223},{"area_frac":0.22376458333333332,"area_px":2685175,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":967892},{"area_frac":0.1838085,"area_px":2205702,"exceeds_top_food_area":true,"item_index":2,"pixels_outside_top_food_mask":1777699}] | 0,1,2 | 912.7 known g (100.0% total; missing item grams=0) | 912.7 | 912.7 | +0.0 |
| Dish 5 | 20261029_141201.jpg | 4 | 2266667 | 12266448 | 5.412 | 0.695 | [{"i":0,"j":1,"iou":0.037151},{"i":0,"j":2,"iou":0.074071},{"i":0,"j":3,"iou":0.083546},{"i":1,"j":2,"iou":0.513953},{"i":1,"j":3,"iou":0.351093},{"i":2,"j":3,"iou":0.695217}] | [{"area_frac":0.33042075,"area_px":3965049,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":3960676},{"area_frac":0.30210108333333335,"area_px":3625213,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":1391014},{"area_frac":0.22951933333333333,"area_px":2754232,"exceeds_top_food_area":true,"item_index":2,"pixels_outside_top_food_mask":1934465},{"area_frac":0.16016283333333334,"area_px":1921954,"exceeds_top_food_area":false,"item_index":3,"pixels_outside_top_food_mask":1786120}] | 0,1,2,3 | 1277.1 known g (100.0% total; missing item grams=0) | 1277.1 | 949.3 | -327.8 |
| Dish 6 | 127 g plate 257g biryani rice 94g egg_.jpg | 4 | 2289673 | 10435786 | 4.558 | 0.618 | [{"i":0,"j":1,"iou":0.004062},{"i":0,"j":2,"iou":0.617898},{"i":0,"j":3,"iou":0.007639},{"i":1,"j":2,"iou":0.029393},{"i":1,"j":3,"iou":0.574005},{"i":2,"j":3,"iou":0.053459}] | [{"area_frac":0.23845075,"area_px":2861409,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":2861409},{"area_frac":0.23623091666666668,"area_px":2834771,"exceeds_top_food_area":true,"item_index":1,"pixels_outside_top_food_mask":621309},{"area_frac":0.20903616666666666,"area_px":2508434,"exceeds_top_food_area":true,"item_index":2,"pixels_outside_top_food_mask":2508434},{"area_frac":0.185931,"area_px":2231172,"exceeds_top_food_area":false,"item_index":3,"pixels_outside_top_food_mask":858128}] | 0,1,2,3 | 1566.1 known g (100.0% total; missing item grams=0) | 1566.0 | 866.3 | -699.7 |
| Dish 6 | 20261029_141725.jpg | 3 | 2552359 | 7255118 | 2.843 | 0.440 | [{"i":0,"j":1,"iou":0.44034},{"i":0,"j":2,"iou":0.293866},{"i":1,"j":2,"iou":0.390818}] | [{"area_frac":0.23291133333333333,"area_px":2794936,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":272033},{"area_frac":0.19874116666666666,"area_px":2384894,"exceeds_top_food_area":false,"item_index":1,"pixels_outside_top_food_mask":889633},{"area_frac":0.17294066666666666,"area_px":2075288,"exceeds_top_food_area":false,"item_index":2,"pixels_outside_top_food_mask":1018550}] | 0 | 491.0 known g (43.9% total; missing item grams=0) | 1119.4 | 1119.3 | -0.1 |
| Dish 6 | 20261029_141729.jpg | 3 | 2281769 | 9287298 | 4.070 | 0.037 | [{"i":0,"j":1,"iou":0.0},{"i":0,"j":2,"iou":0.004823},{"i":1,"j":2,"iou":0.036879}] | [{"area_frac":0.5241765,"area_px":6290118,"exceeds_top_food_area":true,"item_index":0,"pixels_outside_top_food_mask":6289991},{"area_frac":0.18081658333333334,"area_px":2169799,"exceeds_top_food_area":false,"item_index":1,"pixels_outside_top_food_mask":102362},{"area_frac":0.06894841666666666,"area_px":827381,"exceeds_top_food_area":false,"item_index":2,"pixels_outside_top_food_mask":731741}] | 0 | 310.4 known g (48.9% total; missing item grams=0) | 634.4 | 634.4 | +0.0 |

## Per-plate direction counts
| Plate | Image direction counts |
| --- | --- |
| Dish 1 | over 4; under 1; exact 0; null 1 |
| Dish 2 | over 4; under 0; exact 0; null 0 |
| Dish 3 | over 0; under 0; exact 0; null 3 |
| Dish 4 | over 1; under 1; exact 0; null 1 |
| Dish 5 | over 2; under 0; exact 0; null 1 |
| Dish 6 | over 3; under 0; exact 0; null 1 |

Records: default=23 forced_prior_paired=20 flag_off_replay=1

## What this evaluation does not establish

This does not establish performance beyond n=6 plates, one dish each, one kitchen scale, and one phone.

## Mask, classifier-crop, and geometry diagnosis (supplement)

### Run conditions and repeatability

The read-only mask-capture rerun used the same requested settings (`day=mon`, `band=1-5`, `serving_style=mixed`) on the GPU, sequential model loading, and no CPU fallback. The command was:

```text
./.venv/bin/python experiments/oracle_ablation/run_aruco_eval.py --save-masks --out experiments/oracle_ablation/aruco_mask_capture.jsonl
```

Captured stdout begins with `{"event":"run_started","image_count":23,"cuda_device":"NVIDIA GeForce RTX 4060 Laptop GPU","save_masks":true,"force_prior_default":false,...}` and ends with 23 completed image records: 20 measured anchors, 3 prior anchors. Full command output is in [aruco_mask_capture.stdout.log](aruco_mask_capture.stdout.log); raw image-result, timing, reason, anchor, and telemetry records are in [aruco_mask_capture.jsonl](aruco_mask_capture.jsonl).

Compared to the earlier default results, 22/23 pipeline result objects are identical. The sole difference is Dish 1 `20261025_191009.jpg`: earlier output had total 254.2 g and a skipped item due to `[Errno 104] Connection reset by peer`; capture rerun returned 340.1 g with that classification stage succeeding. This records a transient service result, so the original scoring table is retained as the initial run and the separate capture result is not substituted silently. Exact comparison stdout is [compare_mask_capture.stdout.txt](compare_mask_capture.stdout.txt).

The opt-in flag is `--save-masks`, with `store_true` and default off. A separate flag-off replay of `Dish 1/20261025_184112.jpg` produced the same pipeline result SHA-256 as the initial run: `041a9c186e17fa8fc5c9d9aa2b74c89a2c66ef31083dd77677d8b064c22b5df6`. The compare output says `earlier_equals_flag_off=True` and `mask_capture_equals_earlier=True` for that image. The opt-in capture hooks were added only in `experiments/oracle_ablation/run_aruco_eval.py`; no pipeline file changed for this diagnosis.

### A. Sub-threshold dedup pairs

Across the 23 captured image records, 13 item pairs had IoU in `[0.50, 0.70)`, the band below the detector's 0.70 dedup cutoff. Per-image counts and every pair/IoU are included in the generated tables below; images without rows in the pair table have zero pairs in this band. The measured values are computed from saved, effective item masks. Complete per-image pair values (including pairs outside this band) are in [mask_diagnosis_measurements.stdout.txt](mask_diagnosis_measurements.stdout.txt).

### B. Measured-anchor geometry telemetry

The exact estimator-call capture contains per-item footprint area, mean and maximum height, base-plane method and coefficients, density, and resulting grams for the measured-anchor geometry calls. The detailed item table below reports these values; geometry is `n/a` when the pipeline used learned weight rather than geometry or the item did not yield a geometry estimate. In this cohort the measured geometry rows use `table_prior` as their base-plane method. The base-plane plane coefficient `c` is shown as telemetry, not as a physical plate height; it is camera-coordinate plane data. Per-item measurements were captured by wrapping the estimator call in experiment code and restoring the call afterward; pipeline files were not edited.

The table contains all 57 emitted item rows, with 45 geometry telemetry rows. The `fraction in top mask` and classifier-crop fraction are mask-based comparisons, not ground-truth pixel labels. No reliable plate-rim circle/ellipse measurement was available: the full-frame Hough-circle trial yielded multiple candidates per image (food, bowls, and other circles), and visual contours did not isolate a repeatable plate rim. Thus plate area, plate diameter, and item/plate area ratios are n/a; those values were not inferred.

### C. Height-map overlays and plate/rim height

Saved color overlays for the first measured-anchor image in Dishes 1, 4, and 6 show the estimated height map, top-level mask, and item outlines:

- [Dish 1 height overlay](height_maps/Dish%201/20261025_184112.png)
- [Dish 4 height overlay](height_maps/Dish%204/127g%20plate%20206g%20biryani%20rice%2044%20g%20egg.png)
- [Dish 6 height overlay](height_maps/Dish%206/127%20g%20plate%20257g%20biryani%20rice%2094g%20egg_.png)

Visual observation: all three show non-zero height colors on visible steel plate/rim pixels, and also on tabletop/context regions within the item masks. This is not an isolated rim mask; outside-top-mask pixels include plate/rim and table. Numeric outside-top pixel counts and positive-height mean, 95th percentile, and maximum for every selected item are in the height evidence table below. The selected D1 map's four item masks have mean/max heights (mm) 7.645/149.067, 7.956/53.542, 8.755/62.826, 6.071/59.274; D4's three are 12.844/48.073, 14.148/47.373, 12.869/41.696; D6's four are 8.130/12.940, 19.827/60.015, 9.198/17.672, 18.430/60.877. The positive outside-top pixels and visible heat overlay support that plate/rim pixels can contribute estimated volume; because tabletop/context is also included and no rim-only region was annotated, these numbers do not quantify plate thickness alone.

### D. Classifier top-2 and visual crop review

Every item row below includes the classifier's top two labels/scores and confidence. [Classifier crop contact sheets](classifier_crops/) show the exact padded crop supplied to classification for each of the 57 emitted items, indexed by plate, filename, and item. Visual review: Dish 1 and Dish 2 crops commonly contain the food together with substantial plate/table/vessel context; the biryani crops in Dishes 4–6 usually show biryani and/or egg prominently, with plate/table context often also visible. Dish 3 emitted no item crops because the pipeline returned no items on those images. The table's numeric crop/top-mask fraction is an area proxy and must not be read as a visual ground-truth food fraction.

The emitted labels on gram-bearing Dishes 4–6 were `vegetable_rice`, while their top-2 lists generally include a biryani label as second place. Under the fixed user rubric, only the predicted item's selected dish label is the scored classification; a second-place biryani candidate does not make the selected label correct. The per-item table preserves both candidates and confidence. Visual crop review alone cannot establish that a classifier selected a dish label because of a non-food region; those regions co-occur with food in many crops.

### E. Evidence assessment (hypotheses only)

| Hypothesis | Assessment | Evidence in this capture |
|---|---|---|
| (a) Oversized item masks | **Supports** | Item-mask area sums reach 7.709× the top-level mask; 16 image records exceed 1×. Overlays show many item outlines extending over plate/rim, tabletop, and card; 30/57 item masks have at most 0.40 of their pixels inside the top-level food mask. These comparisons do not define ground-truth food masks. |
| (b) Plate/table counted as height above the base plane | **Supports** | D1/D4/D6 height overlays show positive height on visible plate/rim and tabletop pixels inside item masks; outside-top numeric summaries are below. No isolated plate-only mask exists, so plate thickness cannot be separated from table/context error. |
| (c) Classifier labeling non-food crops as dishes | **Supports weakly** | All 57 exact classifier crops were rendered for visual review; many contain sizeable plate/table/vessel/card context alongside food, and 56/57 have at most 0.40 of crop pixels in the top-level mask. However, that mask is not a ground-truth food annotation and often omits secondary food such as bowls/eggs; the crops frequently include visible food. This does not establish which pixels drove any class output. |

No causal ranking follows from these observations. They are hypotheses limited to these photos and pipeline outputs.

### Reproduction commands and raw summary output

```text
$ ./.venv/bin/python experiments/oracle_ablation/summarize_mask_diagnosis.py > experiments/oracle_ablation/mask_diagnosis_measurements.stdout.txt
$ ./.venv/bin/python experiments/oracle_ablation/build_mask_diagnosis_report.py
report_tables=/home/tinkerer/Desktop/Nutrisense/NutriSense-main/experiments/oracle_ablation/MASK_DIAGNOSIS_TABLES.md
image_rows=23 item_rows=57 band_pairs=13 marker_rows=20 height_rows=11
mask_fraction_bands={'mostly inside': 18, 'mixed': 9, 'mostly outside': 30}
crop_fraction_bands={'food dominant': 0, 'mixed': 1, 'context dominant': 56}
item_sum_to_top_ratio_min=0.0 max=7.709074838224182 images_over_1=16
$ ./.venv/bin/python experiments/oracle_ablation/render_classifier_crops.py
... total_classifier_crops=57
$ ./.venv/bin/python -m tools.check_locked
check_locked: 502 ok, 0 skipped, 0 failed (502 pinned)
$ git diff --no-ext-diff 4f313fd -- tools/compare_runs.py docs/locked_manifest.txt
[known diff only: docs/locked_manifest.txt timestamp and tools/compare_runs.py; full output saved in protected_diff_from_4f313fd_mask_diagnosis.txt]
$ git status --short -- tools/compare_runs.py docs/locked_manifest.txt
(no output)
```

The detailed generated tables below were produced by `.venv/bin/python experiments/oracle_ablation/build_mask_diagnosis_report.py` and are also kept separately in [MASK_DIAGNOSIS_TABLES.md](MASK_DIAGNOSIS_TABLES.md). Attempted rim candidates and their raw output are in [plate_area_trial.stdout.txt](plate_area_trial.stdout.txt). Experiment scripts, masks, full-frame overlays, contact sheets, and raw JSONL are all under this directory. Project source outside `experiments/oracle_ablation/` was not edited for this diagnosis; existing unrelated worktree changes remain as they were.

# ArUco mask diagnosis tables

All measurements below are computed from `aruco_mask_capture.jsonl`, the saved NPZ masks/depth maps, and the source image/config. `inside` means fraction of item-mask pixels inside the top-level SAM2 mask; it is a computational comparison, not a ground-truth food label. Classifier crop fraction is the fraction of the 10%-padded item bbox crop inside the top-level mask.

## Per image

| Plate | Image | Anchor | Distinct visible food portions | Pipeline item rows | Pairs IoU 0.50–<0.70 | Item-mask sum / top-mask area | Predicted total (g) |
|---|---|---:|---:|---:|---:|---:|---:|
| Dish 1 | `20261025_184112.jpg` | measured | 2 | 4 | 1 | 5.822607352204799 | 496.8 |
| Dish 1 | `20261025_184421.jpg` | measured | 2 | 4 | 1 | 7.709074838224182 | 1610.5 |
| Dish 1 | `20261025_191003.jpg` | measured | 2 | 3 | 1 | 4.298780058903608 | 1068.6 |
| Dish 1 | `20261025_191009.jpg` | prior | 2 | 4 | 1 | 6.4412661970318865 | 340.1 |
| Dish 1 | `20261025_191019.jpg` | measured | 2 | 3 | 1 | 4.14277166604181 | 1753.4 |
| Dish 1 | `this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg` | prior | 2 | 0 | 0 | 0.0 | n/a |
| Dish 2 | `20261027_085735.jpg` | measured | 2 | 4 | 0 | 3.947349954365075 | 628.3 |
| Dish 2 | `20261027_085741.jpg` | measured | 2 | 4 | 0 | 3.987949742452 | 1773.3 |
| Dish 2 | `20261027_085746.jpg` | prior | 2 | 4 | 1 | 4.41435511854758 | 812.0 |
| Dish 2 | `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` | measured | 2 | 4 | 1 | 4.311993414217322 | 887.1 |
| Dish 3 | `127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg` | measured | 2 | 0 | 0 | 0.0 | n/a |
| Dish 3 | `20261029_125158.jpg` | measured | 2 | 0 | 0 | 0.0 | n/a |
| Dish 3 | `20261029_125203.jpg` | measured | 2 | 0 | 0 | 0.0 | n/a |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | measured | 2 | 3 | 1 | 3.073317084412909 | 1751.8 |
| Dish 4 | `20261029_141529.jpg` | measured | 2 | 0 | 0 | 0.0 | n/a |
| Dish 4 | `20261029_141536.jpg` | measured | 2 | 3 | 1 | 3.1895345392033385 | 37.1 |
| Dish 5 | `127g plate 150 g biryani rice.jpg` | measured | 1 | 3 | 0 | 5.500387702325808 | 912.7 |
| Dish 5 | `20261029_141201.jpg` | measured | 1 | 4 | 2 | 5.411667439460671 | 1277.1 |
| Dish 5 | `20261029_141208.jpg` | measured | 1 | 0 | 0 | 0.0 | n/a |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | measured | 3 | 4 | 2 | 4.557762615010964 | 1566.0 |
| Dish 6 | `20261029_141720.jpg` | measured | 3 | 0 | 0 | 0.0 | n/a |
| Dish 6 | `20261029_141725.jpg` | measured | 3 | 3 | 0 | 2.8425147089418066 | 1119.4 |
| Dish 6 | `20261029_141729.jpg` | measured | 3 | 3 | 0 | 4.070218326219701 | 634.4 |

The visible portion count follows the unchanged plate contents seen across each folder: Dish 3 counts the two chapatis as one weighed serving plus chutney; Dish 6 counts biryani and two eggs separately.

## Per item: mask, crop classifier, and measured geometry

`Area/plate area` and `larger than plate` are n/a: the attempted full frame rim detector did not reliably identify the plate among bowl/food circles. The visual notes refer to the per-image full-frame overlay and item index/color in its footer.

| Plate / image / item | Label, grams | Mask px | Fraction in top mask | Area / plate area | Classifier crop fraction in top mask | Top two labels (scores); confidence | Mean / max height mm | Footprint cm² | Base method; plane c (m) | Density g/ml | Visual read |
|---|---|---:|---:|---:|---:|---|---:|---:|---|---:|---|
| Dish 1 / `20261025_184112.jpg` / 0 | steamed-rice, 167.1 | 2724538 | 0.0024774842560463463 | n/a | 0.12269645238730328 | rice_sambar=0.8390; steamed-rice=0.8293; 0.14647715763790273 | 7.6451324123495965 / 149.06695182432517 | 291.47346751354286 | table_prior; 0.3511984139266992 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_184112.jpg` / 1 | steamed-rice, 153.3 | 2402128 | 0.31379385278386496 | n/a | 0.14700830936401407 | rice_sambar=0.8350; steamed-rice=0.8258; 0.1553816380401527 | 7.9557481299314725 / 53.54245169839476 | 256.9817626222764 | table_prior; 0.3452510284266193 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_184112.jpg` / 2 | steamed-rice, 113.0 | 1608021 | 0.0012866747387005517 | n/a | 0.1312005134055904 | rice_sambar=0.8419; steamed-rice=0.8337; 0.15183450869448323 | 8.75545693311388 / 62.82600040938609 | 172.02749849867928 | table_prior; 0.3539356075580673 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_184112.jpg` / 3 | steamed-rice, 63.3 | 1300319 | 0.793376855986877 | n/a | 0.1341466899970837 | rice_sambar=0.8383; steamed-rice=0.8316; 0.14633556319741278 | 6.070836871799828 / 59.273918530996866 | 139.10926836173417 | table_prior; 0.3491430484744409 | 0.75 | food-centered in overlay; plate/rim may also enter |
| Dish 1 / `20261025_184421.jpg` / 0 | steamed-rice, 742.2 | 4218220 | 0.0 | n/a | 0.10719566666666666 | rice_sambar=0.8424; steamed-rice=0.8171; 0.17107456876653493 | 13.409385942234355 / 71.59343190323705 | 737.9929775745371 | table_prior; 0.35861063862141196 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_184421.jpg` / 1 | steamed-rice, 202.1 | 2232231 | 0.5556028923529868 | n/a | 0.21551773678463826 | rice_sambar=0.8224; steamed-rice=0.8166; 0.15148663535154328 | 6.9001797353790435 / 29.253851814622532 | 390.53695689750333 | table_prior; 0.34564687256264515 | 0.75 | mixed food/context in overlay |
| Dish 1 / `20261025_184421.jpg` / 2 | steamed-rice, 506.6 | 1975106 | 0.0 | n/a | 0.1121189303609924 | rice_sambar=0.8266; steamed-rice=0.8091; 0.15176874883171437 | 19.546133476857417 / 69.28939664939753 | 345.5520001245392 | table_prior; 0.3550195567091704 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_184421.jpg` / 3 | steamed-rice, 159.6 | 1490996 | 0.8409760991981199 | n/a | 0.2919669526533206 | steamed-rice=0.8591; rice_sambar=0.8475; 0.1818212073033092 | 8.156991843825285 / 28.44910442047939 | 260.8551895329605 | table_prior; 0.34257484822873546 | 0.75 | food-centered in overlay; plate/rim may also enter |
| Dish 1 / `20261025_191003.jpg` / 0 | vegetable_rice, 475.2 | 3499043 | 0.5959378035651463 | n/a | 0.3343494100963249 | vegetable_rice=0.8759; rice_sambar=0.8461; 0.1759282181129963 | 14.075459338237682 / 40.19339671900129 | 397.21292365053114 | table_prior; 0.2796839880274711 | 0.85 | mixed food/context in overlay |
| Dish 1 / `20261025_191003.jpg` / 1 | vegetable_rice, 365.8 | 3300762 | 0.0 | n/a | 0.1780266632592214 | vegetable_rice=0.8247; rice_sambar=0.7904; 0.1532625389178982 | 11.484152600497794 / 18.6821475191792 | 374.7039759998875 | table_prior; 0.2760301576279159 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_191003.jpg` / 2 | vegetable_rice, 227.6 | 2184022 | 0.3135742222376881 | n/a | 0.3342121002769835 | vegetable_rice=0.8753; rice_sambar=0.8454; 0.17306998408633115 | 10.80002356398124 / 40.75945676119727 | 247.9311525857443 | table_prior; 0.2798096743635361 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_191009.jpg` / 0 | vegetable_rice, 86.7 | 4346223 | 0.0 | n/a | 0.15162409216128225 | vegetable_rice=0.8449; rice_sambar=0.7934; 0.20957251902917184 | n/a / n/a | n/a | n/a; None | n/a | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_191009.jpg` / 1 | vegetable_rice, 86.9 | 2720417 | 1.6173990972707494e-05 | n/a | 0.1552397435897436 | vegetable_rice=0.8516; rice_sambar=0.7811; 0.2250139388045313 | n/a / n/a | n/a | n/a; None | n/a | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_191009.jpg` / 2 | vegetable_rice, 80.6 | 2400658 | 0.754153236321042 | n/a | 0.2684379710916024 | vegetable_rice=0.8625; rice_sambar=0.8191; 0.18130228061324502 | n/a / n/a | n/a | n/a; None | n/a | food-centered in overlay; plate/rim may also enter |
| Dish 1 / `20261025_191009.jpg` / 3 | vegetable_rice, 85.9 | 2232006 | 0.6179817616977732 | n/a | 0.17094300648043784 | vegetable_rice=0.8480; rice_sambar=0.8051; 0.17722135827153873 | n/a / n/a | n/a | n/a; None | n/a | food-centered in overlay; plate/rim may also enter |
| Dish 1 / `20261025_191019.jpg` / 0 | vegetable_rice, 852.9 | 3646769 | 0.5751650296467914 | n/a | 0.3049083270087624 | vegetable_rice=0.8694; rice_sambar=0.8437; 0.19410696860810808 | 13.194977361419083 / 34.788445579824966 | 760.4077125076848 | table_prior; 0.2718686204135693 | 0.85 | mixed food/context in overlay |
| Dish 1 / `20261025_191019.jpg` / 1 | vegetable_rice, 368.5 | 2605024 | 0.021302298942351396 | n/a | 0.19515505032671973 | vegetable_rice=0.8544; rice_sambar=0.8337; 0.1739253672925542 | 7.980156734622406 / 26.77796189665998 | 543.1877754987003 | table_prior; 0.2643344708561574 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 1 / `20261025_191019.jpg` / 2 | vegetable_rice, 532.1 | 2444502 | 0.36664195815753065 | n/a | 0.3049083270087624 | vegetable_rice=0.8694; rice_sambar=0.8437; 0.19410696860810808 | 12.281438185072691 / 34.808160236337734 | 509.71645696244013 | table_prior; 0.27188725406157427 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085735.jpg` / 0 | steamed-rice, 378.1 | 4067860 | 5.801576258769967e-05 | n/a | 0.15010433333333334 | rice_sambar=0.8315; steamed-rice=0.8042; 0.15407825078273651 | 7.637323178484733 / 59.89385237133804 | 660.0421561623001 | table_prior; 0.37062682010334796 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085735.jpg` / 1 | steamed-rice, 129.2 | 1448331 | 0.9708305629030933 | n/a | 0.18201622112614588 | rice_sambar=0.8466; steamed-rice=0.8181; 0.16507772142255173 | 7.329348196799236 / 43.30837723116667 | 235.00305223795806 | table_prior; 0.3595317519002965 | 0.75 | food-centered in overlay; plate/rim may also enter |
| Dish 2 / `20261027_085735.jpg` / 2 | steamed-rice, 89.5 | 948036 | 0.07161225945006308 | n/a | 0.24892437018042973 | rice_sambar=0.8371; steamed-rice=0.8279; 0.1445782338815058 | 7.759074895535528 / 29.738365514000037 | 153.82626874068487 | table_prior; 0.3570641279712902 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085735.jpg` / 3 | rice_sambar, 31.6 | 645945 | 0.0 | n/a | 0.13490633323532583 | rice_sambar=0.8260; steamed-rice=0.7972; 0.14098867772839696 | 3.577485660231977 / 15.300502787788059 | 104.80963714637596 | table_prior; 0.35913068899927675 | 0.8415032679738563 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085741.jpg` / 0 | rice_sambar, 809.0 | 3927705 | 0.0036886680644294826 | n/a | 0.22416533333333333 | rice_sambar=0.8033; steamed-rice=0.7872; 0.1543872853219806 | 10.217327907558598 / 38.41983928164382 | 940.8754616795369 | table_prior; 0.3260893272429814 | 0.8415032679738563 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085741.jpg` / 1 | steamed-rice, 271.7 | 3323511 | 0.5718566901087434 | n/a | 0.25551492833476036 | rice_sambar=0.8240; steamed-rice=0.8071; 0.14418387703638852 | 4.550353746798947 / 19.66174321407002 | 796.1417536505463 | table_prior; 0.32584043828812226 | 0.75 | mixed food/context in overlay |
| Dish 2 / `20261027_085741.jpg` / 2 | steamed-rice, 454.1 | 2515667 | 0.9836353539637798 | n/a | 0.28017149930659746 | rice_sambar=0.8329; steamed-rice=0.8163; 0.14940877887780854 | 10.04607210085056 / 26.722432236065124 | 602.6240132741576 | table_prior; 0.31605195983737083 | 0.75 | food-centered in overlay; plate/rim may also enter |
| Dish 2 / `20261027_085741.jpg` / 3 | steamed-rice, 238.6 | 960638 | 0.0943893537419923 | n/a | 0.2452341585640555 | rice_sambar=0.8264; steamed-rice=0.8136; 0.1426993732679966 | 13.825113385920142 / 61.905083291113 | 230.11929912172803 | table_prior; 0.3242540506250563 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085746.jpg` / 0 | rice_sambar, 330.5 | 4226287 | 0.00045453609752484867 | n/a | 0.16008691666666666 | rice_sambar=0.8243; vegetable_rice=0.8034; 0.1689111716935056 | n/a / n/a | n/a | n/a; None | n/a | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `20261027_085746.jpg` / 1 | steamed-rice, 163.6 | 1625605 | 0.9928162130406833 | n/a | 0.3224065524434295 | rice_sambar=0.8161; steamed-rice=0.8133; 0.12217470596190286 | n/a / n/a | n/a | n/a; None | n/a | food-centered in overlay; plate/rim may also enter |
| Dish 2 / `20261027_085746.jpg` / 2 | steamed-rice, 159.6 | 1606238 | 0.43203871406354477 | n/a | 0.28684354170162996 | rice_sambar=0.8260; steamed-rice=0.8176; 0.14601217819236323 | n/a / n/a | n/a | n/a; None | n/a | mixed food/context in overlay |
| Dish 2 / `20261027_085746.jpg` / 3 | steamed-rice, 158.2 | 1022036 | 0.15552681118864697 | n/a | 0.28384056877127417 | rice_sambar=0.8238; steamed-rice=0.8138; 0.13753200622848002 | n/a / n/a | n/a | n/a; None | n/a | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` / 0 | steamed-rice, 690.3 | 3342706 | 0.0029218842458774417 | n/a | 0.18750100502512562 | rice_sambar=0.8214; steamed-rice=0.8022; 0.13706561199826656 | 14.551148275494153 / 70.08337633555142 | 632.5038877854489 | table_prior; 0.3619949970541296 | 0.75 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 2 / `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` / 1 | rice_sambar, 196.8 | 2115348 | 0.7320024884794369 | n/a | 0.24718576853576935 | rice_sambar=0.8019; steamed-rice=0.7974; 0.11099549152356246 | 5.84336804755615 / 19.114110599453944 | 400.2642870833311 | table_prior; 0.3525328997510021 | 0.8415032679738563 | food-centered in overlay; plate/rim may also enter |
| Dish 2 / `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` / 2 | unrecognized, n/a | 2102001 | 0.9627868873516235 | n/a | 0.20559913585918074 | vegetable_rice=0.7761; rice_sambar=0.7727; 0.11848548308726428 | n/a / n/a | n/a | n/a; None | n/a | food-centered in overlay; plate/rim may also enter |
| Dish 2 / `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` / 3 | unrecognized, n/a | 2093472 | 0.4458855910181746 | n/a | 0.24780194899961602 | rice_sambar=0.7899; vegetable_rice=0.7847; 0.11339880201256636 | n/a / n/a | n/a | n/a; None | n/a | mixed food/context in overlay |
| Dish 4 / `127g plate 206g biryani rice 44 g egg.jpg` / 0 | vegetable_rice, 648.4 | 3380699 | 0.8317315442753112 | n/a | 0.30738348047514147 | vegetable_rice=0.8219; chicken-dum-biryani=0.7829; 0.16608355015576903 | 12.844039390552028 / 48.07339254502578 | 593.8906414613508 | table_prior; 0.2599962415531131 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 4 / `127g plate 206g biryani rice 44 g egg.jpg` / 1 | vegetable_rice, 683.7 | 3236007 | 0.44763994639072163 | n/a | 0.328053826954808 | vegetable_rice=0.8099; chicken-dum-biryani=0.7540; 0.16193553626025808 | 14.14837460060973 / 47.372911719608375 | 568.4724588031709 | table_prior; 0.2629711996704222 | 0.85 | mixed food/context in overlay |
| Dish 4 / `127g plate 206g biryani rice 44 g egg.jpg` / 2 | vegetable_rice, 419.8 | 2184598 | 0.20242168124295637 | n/a | 0.33604600241164384 | vegetable_rice=0.8106; chicken-dum-biryani=0.7632; 0.15615181615745577 | 12.868965206415636 / 41.69550362090092 | 383.7704295931652 | table_prior; 0.2630345744349459 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 4 / `20261029_141536.jpg` / 0 | vegetable_rice, 37.1 | 3008664 | 0.633328281257063 | n/a | 0.18782220580939396 | vegetable_rice=0.7963; chicken-dum-biryani=0.7624; 0.12889758937903822 | n/a / n/a | n/a | n/a; None | n/a | food-centered in overlay; plate/rim may also enter |
| Dish 4 / `20261029_141536.jpg` / 1 | unrecognized, n/a | 2618164 | 0.40191447136237457 | n/a | 0.23800409273119727 | vegetable_rice=0.7929; chicken-dum-biryani=0.7538; 0.1295828983391721 | n/a / n/a | n/a | n/a; None | n/a | mixed food/context in overlay |
| Dish 4 / `20261029_141536.jpg` / 2 | unrecognized, n/a | 466210 | 0.0002316552626498788 | n/a | 0.23535903883250053 | vegetable_rice=0.8147; chicken-dum-biryani=0.7790; 0.16351330823154459 | 6.439338081441422 / 17.026468163201958 | 67.77351233399082 | table_prior; 0.2825662066411763 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 5 / `127g plate 150 g biryani rice.jpg` / 0 | vegetable_rice, 533.2 | 4593227 | 8.708474455976158e-07 | n/a | 0.14368841666666668 | vegetable_rice=0.8084; chicken-dum-biryani=0.7529; 0.14712722539646247 | 11.744465528603083 / 24.01495571462801 | 534.0902720538143 | table_prior; 0.28552830945129115 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 5 / `127g plate 150 g biryani rice.jpg` / 1 | vegetable_rice, 227.6 | 2685175 | 0.639542301712179 | n/a | 0.2766567530291254 | vegetable_rice=0.8392; chicken-dum-biryani=0.7787; 0.1789623774960047 | 8.57726569966589 / 34.10703041348684 | 312.2262074707173 | table_prior; 0.29079805546625914 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 5 / `127g plate 150 g biryani rice.jpg` / 2 | vegetable_rice, 151.9 | 2205702 | 0.19404389169525166 | n/a | 0.27457084893882644 | vegetable_rice=0.8322; chicken-dum-biryani=0.7724; 0.1677293799997441 | 6.966492278327515 / 35.489118871221166 | 256.47414796822414 | table_prior; 0.2913850775331804 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 5 / `20261029_141201.jpg` / 0 | vegetable_rice, 626.4 | 3965049 | 0.0011028867486883517 | n/a | 0.19012472739473243 | vegetable_rice=0.8202; chicken-dum-biryani=0.7588; 0.19296291807470037 | 10.245637795889317 / 19.748524036348897 | 719.2984598009036 | table_prior; 0.2575498915137474 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 5 / `20261029_141201.jpg` / 1 | vegetable_rice, 322.9 | 3625213 | 0.616294546003228 | n/a | 0.2681393905066367 | vegetable_rice=0.8220; chicken-dum-biryani=0.7825; 0.16004865254215825 | 5.775729874734784 / 23.32865154647921 | 657.6489035444991 | table_prior; 0.2612834064758525 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 5 / `20261029_141201.jpg` / 2 | vegetable_rice, 245.0 | 2754232 | 0.29763905146697883 | n/a | 0.27914295080820495 | vegetable_rice=0.8219; chicken-dum-biryani=0.7605; 0.18485881984891112 | 5.768884927167714 / 22.986580351208268 | 499.6444774161334 | table_prior; 0.261194998434096 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 5 / `20261029_141201.jpg` / 3 | vegetable_rice, 82.8 | 1921954 | 0.07067494851593743 | n/a | 0.30315055408334374 | vegetable_rice=0.8326; chicken-dum-biryani=0.7662; 0.18984063791631056 | 2.793297005594878 / 14.53352397401456 | 348.661151982784 | table_prior; 0.2579266237378081 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 6 / `127 g plate 257g biryani rice 94g egg_.jpg` / 0 | vegetable_rice, 253.6 | 2861409 | 0.0 | n/a | 0.19336821214424457 | vegetable_rice=0.8022; chicken-dum-biryani=0.7857; 0.14129281850637004 | 8.130173758274546 / 12.940300295306526 | 366.9619730288884 | table_prior; 0.2856647783289131 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 6 / `127 g plate 257g biryani rice 94g egg_.jpg` / 1 | vegetable_rice, 612.7 | 2834771 | 0.7808256822156004 | n/a | 0.2916888649389595 | vegetable_rice=0.8116; chicken-dum-biryani=0.7909; 0.16630474414656288 | 19.826746457623123 / 60.01503970010792 | 363.54577735831367 | table_prior; 0.2853942274344451 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 6 / `127 g plate 257g biryani rice 94g egg_.jpg` / 2 | vegetable_rice, 251.5 | 2508434 | 0.0 | n/a | 0.195698547008547 | vegetable_rice=0.8091; chicken-dum-biryani=0.7860; 0.14072517443266724 | 9.198240683794983 / 17.67228525870401 | 321.6946231219468 | table_prior; 0.2827734643523187 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 6 / `127 g plate 257g biryani rice 94g egg_.jpg` / 3 | vegetable_rice, 448.3 | 2231172 | 0.6153913727852447 | n/a | 0.317540884026938 | vegetable_rice=0.8097; chicken-dum-biryani=0.7964; 0.156326440276211 | 18.430102186592556 / 60.877193166324346 | 286.13710213632896 | table_prior; 0.2862055014116391 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 6 / `20261029_141725.jpg` / 0 | vegetable_rice, 491.0 | 2794936 | 0.902669327669757 | n/a | 0.31719940883937253 | vegetable_rice=0.8190; chicken-dum-biryani=0.7911; 0.16319427432855346 | 11.5574032076188 / 48.037914922513515 | 499.8472075992431 | table_prior; 0.287116957098433 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 6 / `20261029_141725.jpg` / 1 | vegetable_rice, 410.3 | 2384894 | 0.6269716809216678 | n/a | 0.28203176632137 | vegetable_rice=0.8257; chicken-dum-biryani=0.7932; 0.17246587430276467 | 11.318007786557311 / 45.369203283583346 | 426.51517112384295 | table_prior; 0.2882436968477978 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 6 / `20261029_141725.jpg` / 2 | vegetable_rice, 218.0 | 2075288 | 0.509200650704866 | n/a | 0.22899785272933418 | vegetable_rice=0.8248; chicken-dum-biryani=0.8020; 0.15500327680572865 | 6.911711887009436 / 30.080983736089717 | 371.1451395538996 | table_prior; 0.2879546473888522 | 0.85 | mixed food/context in overlay |
| Dish 6 / `20261029_141729.jpg` / 0 | vegetable_rice, 310.4 | 6290118 | 2.0190400243683822e-05 | n/a | 0.19014741666666668 | vegetable_rice=0.8229; chicken-dum-biryani=0.7955; 0.17424351945543134 | 6.421890623271299 / 46.867803585484445 | 568.7063432926878 | table_prior; 0.28333073092705424 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |
| Dish 6 / `20261029_141729.jpg` / 1 | vegetable_rice, 272.1 | 2169799 | 0.9528242016887278 | n/a | 0.40407662861846344 | vegetable_rice=0.8304; chicken-dum-biryani=0.8235; 0.15196327960778314 | 16.32010377824769 / 46.838560447720475 | 196.1773141569253 | table_prior; 0.27918630947229417 | 0.85 | food-centered in overlay; plate/rim may also enter |
| Dish 6 / `20261029_141729.jpg` / 2 | vegetable_rice, 51.9 | 827381 | 0.11559366241187555 | n/a | 0.23351844767582638 | vegetable_rice=0.8185; chicken-dum-biryani=0.7784; 0.1753862806243487 | 8.155874274873568 / 33.50264662328611 | 74.80572272568611 | table_prior; 0.2789920511790513 | 0.85 | mostly outside main-food mask; overlay shows plate/table/context; inspect secondary food |

Computed mask/top fraction bands (0.60 and 0.40 cut points): mostly inside 18, mixed 9, mostly outside 30 (n=57).
Classifier crop/top-mask fraction bands: food-dominant 0, mixed 1, context-dominant 56 (n=57).
The crop categories are a mask-area proxy checked against the actual photos; they are not a pixel-level annotation of every food object.

## Pairwise IoU in the dedup threshold band

The detector removes pre-upsample mask pairs at IoU >= 0.70. The rows below are returned item masks whose measured IoU is 0.50 to <0.70.

| Plate | Image | Pair | IoU |
|---|---|---:|---:|
| Dish 1 | `20261025_184112.jpg` | 0-2 | 0.52314463 |
| Dish 1 | `20261025_184421.jpg` | 1-3 | 0.61307704 |
| Dish 1 | `20261025_191003.jpg` | 0-2 | 0.55705999 |
| Dish 1 | `20261025_191009.jpg` | 2-3 | 0.63554816 |
| Dish 1 | `20261025_191019.jpg` | 0-2 | 0.64809791 |
| Dish 2 | `20261027_085746.jpg` | 2-3 | 0.63534287 |
| Dish 2 | `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` | 1-2 | 0.57715804 |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | 1-2 | 0.65682008 |
| Dish 4 | `20261029_141536.jpg` | 0-1 | 0.54524985 |
| Dish 5 | `20261029_141201.jpg` | 1-2 | 0.51395260 |
| Dish 5 | `20261029_141201.jpg` | 2-3 | 0.69521679 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 0-2 | 0.61789773 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 1-3 | 0.57400452 |

## Marker scale and tilt proxy

Marker physical side from `data/anchor_config.json`: 60.0 mm. Marker side px is the mean of the four quad edges. Aspect proxy is shortest/longest edge. Plate diameter itself is n/a because the rim fit was not reliable.

| Plate | Image | Marker side px | Edge aspect proxy | cm/px | Plate diameter cm |
|---|---|---:|---:|---:|---:|
| Dish 1 | `20261025_184112.jpg` | 582.6596 | 0.890936 | 0.01029760803429167 | n/a |
| Dish 1 | `20261025_184421.jpg` | 453.8517 | 0.948608 | 0.013220177539972774 | n/a |
| Dish 1 | `20261025_191003.jpg` | 563.1722 | 0.957386 | 0.010653934194586545 | n/a |
| Dish 1 | `20261025_191019.jpg` | 417.2194 | 0.634594 | 0.014380923605713756 | n/a |
| Dish 2 | `20261027_085735.jpg` | 471.2641 | 0.921116 | 0.012731713457932649 | n/a |
| Dish 2 | `20261027_085741.jpg` | 389.5276 | 0.712695 | 0.01540327161001325 | n/a |
| Dish 2 | `Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg` | 437.5835 | 0.764926 | 0.01371166843391253 | n/a |
| Dish 3 | `127 g plate 47 g bowl- 70g cocunt chutney _121 g of chappati.jpg` | 632.5180 | 0.915769 | 0.009485896083877003 | n/a |
| Dish 3 | `20261029_125158.jpg` | 504.6281 | 0.952501 | 0.011889943265216647 | n/a |
| Dish 3 | `20261029_125203.jpg` | 469.0721 | 0.800989 | 0.012791209374069964 | n/a |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | 453.8617 | 0.619345 | 0.01321988715191063 | n/a |
| Dish 4 | `20261029_141529.jpg` | 604.6991 | 0.915639 | 0.009922291051206808 | n/a |
| Dish 4 | `20261029_141536.jpg` | 497.6427 | 0.930082 | 0.012056842234883526 | n/a |
| Dish 5 | `127g plate 150 g biryani rice.jpg` | 556.9036 | 0.903131 | 0.010773856807570087 | n/a |
| Dish 5 | `20261029_141201.jpg` | 446.5773 | 0.696594 | 0.013435524106713797 | n/a |
| Dish 5 | `20261029_141208.jpg` | 624.9332 | 0.927017 | 0.009601025545323195 | n/a |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 529.8243 | 0.957361 | 0.01132450915566769 | n/a |
| Dish 6 | `20261029_141720.jpg` | 585.4288 | 0.918054 | 0.010248897178594885 | n/a |
| Dish 6 | `20261029_141725.jpg` | 449.3350 | 0.719198 | 0.01335306530063436 | n/a |
| Dish 6 | `20261029_141729.jpg` | 631.3912 | 0.926959 | 0.009502824236688133 | n/a |
| Dish 1 | `20261025_191009.jpg` | n/a | n/a | n/a | n/a |
| Dish 1 | `this plate weight is 127g and rice is 250g _bowl weight is 109g and sambar is 200g.jpg` | n/a | n/a | n/a | n/a |
| Dish 2 | `20261027_085746.jpg` | n/a | n/a | n/a | n/a |

## Height map evidence for rim/table overlap

Height maps are per measured item mask over its fitted base plane. `outside top pixels` includes the visibly overlaid plate/rim and table/context, so it is not an isolated plate-rim segmentation.

| Plate | Image | Item | Mean h mm | Max h mm | Outside-top pixels | Positive outside-top pixels | Mean positive mm | P95 mm | Max positive mm |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dish 1 | `20261025_184112.jpg` | 0 | 7.6451324123495965 | 149.06695182432517 | 2717788 | 1622710 | 12.81645393371582 | 27.538602828979492 | 149.06695556640625 |
| Dish 1 | `20261025_184112.jpg` | 1 | 7.9557481299314725 | 53.54245169839476 | 1648355 | 1221529 | 13.137126922607422 | 26.173824310302734 | 53.542449951171875 |
| Dish 1 | `20261025_184112.jpg` | 2 | 8.75545693311388 | 62.82600040938609 | 1605952 | 967634 | 14.537507057189941 | 30.817989349365234 | 62.82600021362305 |
| Dish 1 | `20261025_184112.jpg` | 3 | 6.070836871799828 | 59.273918530996866 | 268676 | 160008 | 10.252148628234863 | 21.505184173583984 | 59.27391815185547 |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | 0 | 12.844039390552028 | 48.07339254502578 | 568865 | 454959 | 14.235849380493164 | 35.86829376220703 | 48.07339096069336 |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | 1 | 14.14837460060973 | 47.372911719608375 | 1787441 | 1712386 | 12.500983238220215 | 27.838794708251953 | 47.3729133605957 |
| Dish 4 | `127g plate 206g biryani rice 44 g egg.jpg` | 2 | 12.868965206415636 | 41.69550362090092 | 1742388 | 1664022 | 12.746252059936523 | 27.959693908691406 | 41.69550323486328 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 0 | 8.130173758274546 | 12.940300295306526 | 2861409 | 2821777 | 8.244361877441406 | 11.366503715515137 | 12.940299987792969 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 1 | 19.826746457623123 | 60.01503970010792 | 621309 | 507405 | 24.7124080657959 | 56.15591812133789 | 60.01504135131836 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 2 | 9.198240683794983 | 17.67228525870401 | 2508434 | 2283309 | 10.10515022277832 | 13.233243942260742 | 17.672285079956055 |
| Dish 6 | `127 g plate 257g biryani rice 94g egg_.jpg` | 3 | 18.430102186592556 | 60.877193166324346 | 858128 | 653157 | 16.927703857421875 | 30.924253463745117 | 60.877193450927734 |

## Visual observations by plate folder

These are observations from the saved full-frame overlays/contact sheets. The mask index is the matching footer color/index.

| Plate | Visual observation |
|---|---|
| Dish 1 | Rice mound and separate sambar bowl are both visible. Item outlines extend across the steel plate/rim, wood tabletop, and marker/card in multiple angles; several are much broader than the rice pile. |
| Dish 2 | Rice plate and rasam bowl are both visible. Some item outlines follow those vessels, while other outlines include large tabletop and plate-rim regions; the primary top mask does not represent both foods as one region. |
| Dish 3 | Chapati(s) on the plate and the separate chutney bowl are visible. The pipeline produced zero item rows after unrecognized/out-of-scope classification on these three views; top-level overlays remain available. |
| Dish 4 | Biryani and egg are visible. Item outlines include food, plate/rim, and in some views table/card context; all resolved items in this capture were labeled vegetable_rice. |
| Dish 5 | One biryani pile is visible. Several returned masks extend across the plate/rim and wood table; some also include the marker/card context. |
| Dish 6 | Biryani and eggs are visible. Item outlines include the food and eggs, but also broad plate/rim/table/card areas in several views; the top mask mostly traces the biryani mound and excludes some peripheral food. |

## Per-image contact sheets

| Plate | Contact sheet |
|---|---|
| Dish 1 | [overlays/Dish_1_contact_sheet.png] |
| Dish 2 | [overlays/Dish_2_contact_sheet.png] |
| Dish 3 | [overlays/Dish_3_contact_sheet.png] |
| Dish 4 | [overlays/Dish_4_contact_sheet.png] |
| Dish 5 | [overlays/Dish_5_contact_sheet.png] |
| Dish 6 | [overlays/Dish_6_contact_sheet.png] |

## Scope limit

This does not establish performance beyond n=6 plates, one dish each, one kitchen scale, and one phone.
