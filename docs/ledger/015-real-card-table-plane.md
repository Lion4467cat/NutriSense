# 015 — Real-card table-plane portion geometry

- **id**: 015
- **branch**: `spec-002-integration`
- **date**: 2026-10-29
- **author**: agent (CodeBuddy)

## Hypothesis

On real MoGe depth, the ring plane fitted inside the food mask follows the
food surface rather than the vessel base and systematically inflates height.
A table plane fitted outside the mask plus the configured vessel-floor prior
should be more stable on card-bearing phone captures. Synthetic renderer
scenes must retain the validated ring path.

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| real ArUco main-food MAE | 213.2 g on four numeric named-image outputs | substantial reduction | table-plane diagnostic, not a promised result |
| alternate-view validation MAE | recorded by this entry | paired improvement over ring | 13 views withheld from strategy selection |
| synthetic volume error | existing ring baseline | no material regression | measured real-MoGe branch only |
| aspirational product target | — | ≤5 g MAE on independent real captures | not considered proven by this small dataset |

## Success criterion (written BEFORE serving code)

The real-MoGe/measured-tier table-plane candidate must reduce main-food MAE
on the 13 alternate-view validation images versus the ring baseline on the
same successfully scored views, with no increase in pipeline failures and no
synthetic-test regression. The ≤5 g goal is separately reported as met or not
met; it is not hidden by averaging away cannot-verify outcomes. No LOCKED WED
read. This criterion is written after the six named-image diagnostic but
before serving code; the 13 alternate views were not used to select the
candidate.

## Change

Planned: select `table_prior` only for measured-tier MoGe inference in
`engine/pipeline.py`; retain ring-first geometry for synthetic/GT depth and
all prior-tier behavior. Add focused seam tests and a reproducible real-image
comparison report.

## Sources

- `models/portion_estimator.py` — ring and table-plane implementations.
- `docs/ledger/007-moge-intrinsics-geometry.md` — real-image monocular
  scale/shape limitations and the need for a physical anchor.
- `../Aruco_7ID_60mm_with_food/` — six dishes, 19 views, food weights in
  the six named files; alternate views inherit only their dish's measurement.
- MoGe-2 paper: https://arxiv.org/html/2507.02546v1

## Result

All 23 local ArUco images were evaluated: six named development images and 17
alternate validation views. The validation images were not used to select the
candidate. No LOCKED WED data was read.

| image set | numeric outputs | ring MAE | table MAE | ≤5 g | cannot/out-of-scope |
| --- | ---: | ---: | ---: | ---: | --- |
| named development | 4 | 213.2 g | 41.1 g | 0 | 2 cannot |
| alternate validation | 12 | 175.9 g | 100.0 g | 2 | 3 cannot + 2 out-of-scope |
| combined | 16 | 185.2 g | 85.3 g | 2 | 5 cannot + 2 out-of-scope |

On the 12 validation views with numeric outputs under both modes, MAPE fell
from 78.94% to 44.83%, outputs within ±20% rose from 1 to 4, and the number of
pipeline outcomes did not change. Marker detection produced a measured anchor
on 20/23 images. Real-MoGe table portions carry `vessel_shape_uncertain`, so
the previously unsafe measured-geometry PASS/FAIL outcomes become BORDERLINE.

Focused geometry/pipeline tests: 9 passed. Full quality gates are recorded in
the final project verification, not used to alter this result.

The pre-registered improvement criterion is met. **The separate ≤5 g MAE
product goal is not met**: only two individual validation predictions, not the
MAE, fall within 5 g. These repeated views also remain insufficient for an
independent production-accuracy claim.

## Decision

- **keep** — the alternate-view validation MAE decreases without changing the
  number of pipeline outcomes, and synthetic/GT-depth tests retain the ring
  path. The 5 g target remains explicitly unmet.

## Follow-ups

Multi-item segmentation and independent per-ingredient weights remain
necessary for rice+rasam and biryani+egg meals. A ≤5 g claim requires a larger,
independently captured, dish-held-out dataset; these repeated views are not
sufficient for that claim. Recognition still confuses biryani with vegetable
rice, and the learned no-card head measured 98.15 g MAE on the six named real
images, so switching portion heads is not a shortcut to the target.
