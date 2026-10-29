# Spec 007: Weighed multi-item data collection (P4)

- **Status:** protocol defined; collection is field work (not agent work)
- **Date:** 2026-10-29
- **Source:** roadmap P3/P4 — the weight head's binding constraint is
  between-plate systematic bias (per-plate residual std 0.700 vs 0.131
  expected, known_issues 2026-10-29), and multi-item accuracy has no
  per-component ground truth at all (ledgers 015, 016).

## Problem Statement

1. The learned head is limited by **plates, not views**: 21 DEV plates
   produce 5.3× more between-plate variance than iid expects. More views of
   the same plates cannot fix this.
2. Multi-item plates (spec 003/004) have no weighed per-component ground
   truth, so no accuracy gate for the aggregate path can exist.
3. The ≤5 g absolute target is structurally unreachable on large dishes;
   the evaluation target is re-expressed as **relative error per component**
   (provisional ≤10%), with absolute ≤5 g expected only on small sides.

## Protocol extension (docs/data-collection-manual.md §14)

- Multi-item captures: each vessel weighed **separately** (tare per vessel),
  `weights.json` gains a per-component map; plate total is the cross-check
  (|sum − total| ≤ 2 g or the plate is rejected at QA).
- Dish-held-out splits: plates are split by **capture session × dish**, never
  by view, so a dish's plates in DEV and its plates in HOLDOUT come from
  different cooking batches.
- Volume: ~50 plates per common dish, ~300–500 plates total, is the scale at
  which between-plate variance can be modelled rather than absorbed.
- Every capture keeps the existing card protocol (60 mm marker, zoom 1.0,
  EXIF intact) plus the spec-005 angle band (25–60°).

## Success criteria

Protocol documented and consistent with the pipeline's actual config; no code
change, no gates moved. The accuracy claim waits for this data.
