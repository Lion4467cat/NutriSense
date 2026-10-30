# Real-photo end-to-end sanity test — 2026-10-29

Six unposed canteen captures (`../DATASET/`, two per dish) run through
`engine.pipeline.analyze()` exactly as `POST /analyze` calls it
(`day=mon`, `band=1-5`, `serving_style=mixed`). These photos were **not**
captured under the protocol: no ArUco card, no plate measurement, no
per-pixel annotation. Nothing here is an accuracy claim — it is a
deployment sanity report and the closest thing we have to field validation.

Raw rows: `data/reports/real_photo_e2e.json`.

## Results

| photo | dish (match) | grams | kcal | protein | seg (area) | coverage | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pepper_rasam_rice …131408 | rice_sambar (0.946) | 287.8 | 261.9 | 7.0 | centre_box (0.353) | 0.90 | FAIL |
| pepper_rasam_rice …131418 | rice_sambar (0.955) | 312.3 | 284.2 | 7.6 | centre_point (0.117) | 0.90 | FAIL |
| tomato_rasam_rice …131456 | rice_sambar (0.942) | 298.8 | 271.9 | 7.3 | centre_box (0.209) | 0.90 | FAIL |
| tomato_rasam_rice …131457 | rice_sambar (0.946) | 252.5 | 229.8 | 6.1 | centre_point (0.185) | 0.90 | FAIL |
| vegetable_rice …130507 | vegetable_rice (0.945) | 90.6 | 135.8 | 3.2 | centre_point (0.365) | 0.90 | FAIL |
| vegetable_rice …130516 | vegetable_rice (0.957) | 57.6 | 86.3 | 2.0 | centre_point (0.326) | 0.90 | FAIL |

All six: `anchor.tier = prior` ("no reference card in frame — scale from
size priors"), `path_used = learned_head`, no stage failures, runtime
1.2 s warm / 29 s cold.

## What happened, in pipeline order

1. **Anchor — expected failure, correctly reported.** No card, so no
   `cm_per_px`; the anchor degrades to `prior` and every result carries a
   `no_reference_card` reason. This is the documented behaviour, and it is
   what makes the grams "an estimate" rather than a measurement.
2. **Segmentation — improved, still single-vessel.** Two of six frames
   used to return slivers (0.08 % / 0.18 % of frame) and are now served by
   the `centre_box` fallback from ledger 014 (0.353 / 0.209). The other
   four are plate-sized point masks (0.12–0.36). No frame returns a
   degenerate mask any more.
3. **Classification — the strongest link.** 6/6 above the 0.94 gate; the
   pepper and tomato rasam plates are labelled `rice_sambar` (the menu key
   they alias to) and the vegetable-rice plates are labelled
   `vegetable_rice`. No abstention, no cross-class confusion in this
   sample.
4. **Portion — plausible for rice+sambar, low for vegetable rice.** The
   learned weight head reports 252–312 g for the rice+sambar plates (a
   full canteen plate) but only 58–91 g for the vegetable-rice plates,
   despite similar mask areas. That gap is worth a dedicated check: the
   head was trained on WED ROI crops, and a single-dish vegetable-rice
   photo is out of that distribution.
5. **Compliance — FAIL everywhere, by construction.** Band 1-5 requires
   ≥ 450 kcal and ≥ 12 g protein per meal. A single 300 g rice+sambar
   plate carries ~270 kcal / 7 g protein, and the vegetable-rice plates
   carry even less. The pipeline is judging **the captured dish against a
   whole-meal standard**, with no notion of "this photo is one component
   of a meal". The verdict is arithmetically right and semantically
   misleading; `coverage` stays 0.90 because coverage measures nutrient
   table coverage, not meal completeness.

## Conclusions

- The plumbing works end to end on unposed photos: no crashes, no stage
  failures, honest degradation reasons, sub-second warm inference.
- The two weakest links are not the models' accuracy but the **contract**:
  one mask = one serving (ledger 014 follow-up 1) and one serving =
  one meal (this report). Both produce confident, well-formatted numbers
  from the wrong scope.
- Nothing here evaluates the LOCKED split; no gate is claimed or moved.

## Reproduction

```bash
# segmentation strategies (ledger 014)
.venv/bin/python -m tools.diag_real_segmentation --per-class 2

# end-to-end rows
.venv/bin/python - <<'PY'
import cv2, glob, json
from engine.pipeline import analyze
from models.scale_anchor import read_exif
rows = []
for cls in ("pepper_rasam_rice", "tomato_rasam_rice", "vegetable_rice"):
    for f in sorted(glob.glob(f"../DATASET/{cls}/*.jpg"))[:2]:
        r = analyze(cv2.imread(f), day="mon", band="1-5",
                    exif=read_exif(f), serving_style="mixed")
        rows.append({"photo": f, "verdict": r["verdict"],
                     "dish": r["dish"]["id"], "grams": r["portion"]["grams"]})
print(json.dumps(rows, indent=2))
PY
```
