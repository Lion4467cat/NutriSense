# 030 — confirmatory WED boundary-loss comparison

- **id**: 030
- **branch**: `codex/iter-synthetic-card-homography-check`
- **date**: 2026-11-03
- **author**: Codex

## Hypothesis

The prior boundary-aware DeepLabV3 raised tiny-region pixel recall but did not raise the rate of complete tiny semantic-component matches. A longer, paired 20-epoch comparison may show whether this effect survives equal initialization, data order, augmentation, optimizer, and checkpoint selection.

## Expected effect

Relative to a matched standard-loss DeepLabV3 control, boundary-weighted CE should improve macro food IoU and tiny-region recovery without meaningful loss in foreground IoU, region F1, priority classes, boundary quality, or topology proxies.

## Success criterion (written BEFORE coding)

As fixed in [the confirmatory protocol](../../experiments/wed_boundary_confirmatory/protocol.md): across three paired seeds, require ≥+0.01 macro food IoU with a paired DEV meal-group bootstrap 95% CI above zero and ≥+5 percentage points in tiny pixel recall or IoU≥0.5 tiny-component recall with its CI above zero; maintain the predeclared foreground, region-F1, priority-class, merge/fragmentation, and boundary guardrails against both the matched control and frozen reference.

## Change

Completed three paired seeds (42, 43, 44), with 20 epochs per loss condition and matched initialization, train/validation groups, batch order, augmentation, optimizer schedule, and checkpoint selection. The six candidate checkpoints and frozen reference were evaluated on the fixed DEV carve. The corrected CPU/GPU-compatible evaluator records unavailable inference VRAM as `null` instead of failing aggregation on CPU.

## Sources

- [Confirmatory protocol](../../experiments/wed_boundary_confirmatory/protocol.md) — paired setup, metrics, and decision rule.
- [Prior controlled study](../../experiments/wed_segmentation_study/dev_comparison/comparison_report.md) — initial finding motivating confirmation.
- [WED annotation audit](../wed_native_segmentation_design.md) — semantic labels and absence of serving instance IDs.

## Result

Full metrics and per-class results: [fixed-DEV comparison report](../../experiments/wed_boundary_confirmatory/dev_report/comparison_report.md) and [JSON](../../experiments/wed_boundary_confirmatory/dev_report/comparison_report.json). The report covers 108 views / 21 meal groups and confirms LOCKED, ArUco, and WED test data were not accessed.

- Boundary-aware vs matched standard: macro food IoU −0.0005 (95% group-bootstrap CI −0.0028 to +0.0016); tiny pixel recall +4.31 percentage points (CI −2.90 to +11.60 pp); tiny component recall +0.18 pp (CI 0.00 to +0.46 pp). The required macro and tiny-recall gains were not established.
- Region F1 increased +0.0095 (CI +0.0038 to +0.0154), while foreground IoU decreased −0.0009 (CI −0.0014 to −0.0004). Boundary F1 decreased −0.0056 vs the matched control, but −0.0417 vs the frozen reference and failed that guardrail.
- Across each seed's 370 tiny GT components, standard-loss complete matches were 1, 2, and 2; boundary-aware matches were 2, 3, and 2. Most tiny components had no same-class predicted overlap, so the modest pixel-coverage gain rarely produced a complete component match.

## Decision

- **Retain the frozen DeepLabV3 reference; close the boundary-aware-loss line.** Neither promotion gate passed. Do not promote the boundary-aware checkpoints.

## Follow-ups

Based on the WED error audit and this confirmation, prioritize a controlled small-region recall study aimed at the 68%–74% no-overlap tiny-component misses, using scale-aware crops or sampling from eligible TRAIN groups. Measure IoU≥0.5 component recall separately from pixel recall, preserve the fixed DEV carve for evaluation, and continue describing connected components only as semantic-region proxies because WED has no serving IDs.
