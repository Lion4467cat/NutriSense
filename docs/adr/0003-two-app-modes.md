# ADR 0003: School standards and General goal tracking

- **Status:** Accepted; updated 2026-11-02
- **Original date:** 2026-10-28

## Context

The WED classifier recognizes 41 food classes, but the official school menu
contains only a few matching recipes. The remaining classes have generic
nutrient mappings, and some rows are assumptions rather than verified recipe
data. The project now needs both a School-mode check against its existing
per-meal standards and a General-mode comparison with personal daily goals.

## Decision

1. **School mode** — automatically detect one or several food regions, resolve
   recognized WED classes, estimate portions and nutrients, aggregate the meal,
   and score its estimated energy and protein against the existing standard for
   the selected class band. The selected day remains menu context; it does not
   change the energy/protein threshold. This applies to all 41 WED food classes,
   including classes outside the published school menu. Generic nutrient rows
   remain marked as assumed. A result for an outside-menu food is a nutrient
   standards estimate; it does not claim that the food was served or appears on
   that day's official menu. Phulka (`wheat_product`) is included with an
   assumed cooked-roti nutrient row.
2. **General mode** — use the same portion and nutrient estimates for any
   recognized WED class, but do not produce a school standards verdict. Show
   each nutrient's share of the user's Daily goal. Daily goal defaults come
   from WHO tables by age band, sex, and activity level
   (`docs/research/who-goals.md`); the user may enter a personal goal.

Both modes use the same automatic meal-region detector. If regions cannot be
separated or a detected item cannot be resolved safely, the pipeline abstains
from the whole-meal total. It does not ask the user to declare `single` or
`mixed`.

## Why the two modes have different verdicts

School mode checks the configured school-meal energy/protein benchmark for the
selected class band. General mode tracks progress toward a daily target, so it
must not label one meal PASS or FAIL against a full day's goal. School-mode results that
use generic food rows still show their assumptions; a standards result is
therefore an estimate, not a claim that the recipe is known exactly.

## Consequences

- The API accepts a `mode` field. Older clients that omit it default to
  `school`; the current frontend sends the user's selected mode explicitly.
- School standards are evaluated from the aggregate nutrient estimate for all
  recognized classes. Official menu availability remains a separate item of
  context and does not block that check.
- The WED serving map covers all 41 classes. Wheat-product data uses an
  assumed cooked-roti nutrient profile because the existing mapping had been
  marked out of scope.
- General mode has no compliance verdict and continues to use personal goal
  shares plus the meal critique.
- Food recognition, item separation, portion accuracy, and generic nutrient
  quality still need evaluation on fresh, manually measured development data.
  The 23-image ArUco set remains evaluation-only and was not used to tune this
  change.

The historical decision to withhold school verdicts for all off-menu foods is
recorded in [ledger 003](../ledger/003-serve-all-41-classes.md); this ADR
supersedes that behavior for School mode while preserving the General-mode
no-verdict rule.
