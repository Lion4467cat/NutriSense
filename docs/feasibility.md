# NutriSense feasibility — provisional error budget (S0, pre-data)

All rows are `assumed` or `literature` until golden data replaces them (M0b/M6).
Status vocabulary matches `data/params_status.yaml`. Planning figures below
use corrected maths validated with the user (shared terms do not cancel).

## Per-plate energy error budget (90% interval, planning values)

| Component                          | Relative σ (planned) | Status    | Note |
|------------------------------------|----------------------|-----------|------|
| Anchor scale (card tier)           | ~0.2–1%              | assumed   | corner jitter on ≥80 px marker; synthetic verified |
| Anchor scale (prior tier)          | large                | assumed   | no anchor → S3 size priors dominate |
| Mask area (segmentation)           | ~5%                  | assumed   | calibrate on ITD + golden |
| Base plane / depth (ring path)     | ~±26% per-dish grams | assumed   | dominant term, depth ring + κ |
| Base plane (table prior path)      | ~±33% per-dish grams | assumed   | vessel-height prior [0,50 mm] |
| Pose/tilt residue                  | ~1.5%                | assumed   | quad fit residual |
| Component share / recipe           | ~10%                 | assumed   | wider for generic dishes (veg rice) |
| Nutrient table (IFCT)              | ~3–5%                | literature| per-component kcal/protein |
| **Plate kcal (planning)**          | **~±35%**            | assumed   | worst-case ~±41% (prior path) |
| **Plate kcal at σ≈21%**            | zones below          | assumed   | corrected sensitivity |

## Verdict zones at σ ≈ 21% of plate kcal (against 450 kcal lower bound)

| True plate kcal | Reads as |
|-----------------|----------|
| < ~310          | FAIL     |
| ~310 – ~590     | BORDERLINE (norm-cooked 505 kcal lands here — honest) |
| > ~590          | PASS     |

Discrimination target (M7, planted plates): ≥90% correct PASS and ≥90% correct
FAIL at ≥1.5σ separation (≈300 vs ≈700 kcal); false-FAIL ≤5%.
Answer-rate target: ≤50% BORDERLINE + `cannot_verify` — escape hatch if missed:
report margin math in every report; tighter depth/weights are the main lever.

## Sensitivity (what to improve first)

1. **Depth/base-plane** — dominates per-dish grams; depth-ring path beats
   table-prior path (±26% vs ±33%). Get base evidence: low-slope capture angle.
2. **Anchor tier** — card beats prior by a wide margin; keep card in-frame.
3. **Recipe composition** — generic dishes (vegetable_rice) widen σ; official
   recipes (rice_sambar, bisibelebath) are tighter.
4. Shared terms (anchor, pose, plane height, nutrient table) never cancel
   between components — do not net them in planning.

## Service-level objectives (provisional, locked at M6)

| Metric | Target | Status |
|--------|--------|--------|
| Interval coverage (nominal 90%) | 85–95% on dev plates | planning |
| Correct discrimination (planted) | ≥90/90 | planning |
| False FAIL rate | ≤5% | planning |
| Answer rate (PASS/FAIL, not borderline) | ≤50% borderline+c.v. | target, escape hatch above |
| Pose latency | ≤3 s on laptop GPU / ≤10 s CPU | planning |
| Detection recall (menu items) | ≥80% | planning |

## Known open risks

- **Bowl/serving-vessel ambiguity**: vessel-independent design means deep bowls
  can read as low piles; flagged `vessel_shape_uncertain` when depth evidence
  conflicts with prior. Mitigation: capture angle guidance + wider σ path.
- **Mixed sambar plates** (`serving_style: varies`): composition rule fires
  only on high-confidence plain rice + zero sambar evidence; otherwise
  `composition_uncertain` widens σ rather than guessing.
- **Bisibelebath dev plates**: if <2 collected, validation of that dish is
  `synthetic-only` (M7 label), not golden-verified.
- **INDB/ITD/WED terms unconfirmed**: see docs/licenses.md M9 gate.
