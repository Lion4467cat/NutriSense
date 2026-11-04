# Renderer-grounded metric depth and geometry validation

This controlled validation uses analytic renderer ground truth only. It does
not use WED test, LOCKED, or ArUco evaluation captures, and it does not write
training examples.

## Metric depth

The MoGe baseline contains 82 views across 41 renderer meal groups. Raw MoGe
predictions are relative-scale outputs and are not suitable for absolute
geometry:

| Condition | Views | Median predicted / target scale | AbsRel | MAE |
| --- | ---: | ---: | ---: | ---: |
| Card present, before calibration | 41 | 8.39× | 7.324 | 3.667 m |
| Card present, after ID 7 / 60 mm calibration | 41 | 0.992× | 0.0304 | 0.0183 m |
| No card, raw relative depth | 41 | 4.94× | 3.920 | 1.975 m |

The calibrated all-visible card result has δ<1.25 = 0.9997. This demonstrates
the renderer calibration math; it is not a real-camera depth-accuracy claim.
No-card MoGe is explicitly excluded from absolute metric geometry in the
application pipeline.

## Geometry and mass

With renderer ground-truth depth, food mask, marker corners, and base geometry,
the estimator was checked on 123 scenes: 41 WED classes × 3 portion levels.

| Metric | Result |
| --- | ---: |
| Mass MAE | 5.67 g |
| Mass bias | +2.85 g |
| Mean absolute relative mass error | 5.20% |
| 90% interval coverage | 100% |

This is an oracle-input geometry check; it does not include real segmentation
or real marker-corner error. Density and vessel/base assumptions retain their
configured provenance and uncertainty.

## Nine-gram chutney diagnostic

The 9 g renderer chutney case returns 9.44 g with exact metric depth and a
measured marker. A 0.5× depth multiplier returns 4.72 g and a 1.5× multiplier
returns 14.16 g, showing direct sensitivity to metric scale. With the table
base prior, an 8 mm adverse base-height offset makes the estimated food surface
fall behind the base plane and the estimator abstains. The no-card size-prior
case returns 12.42 g only in this renderer diagnostic; production never treats
its size prior or raw MoGe depth as validated absolute food mass.

## Artifacts

- `renderer_metric_depth.json`: per-condition metric-depth results and group
  bootstrap intervals.
- `renderer_geometry.json`: per-class and per-portion geometry/mass results.
- `renderer_geometry_sensitivity.json`: depth-scale, base-plane, shape, and
  density perturbations for the 9 g chutney case.

