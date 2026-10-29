# 07: Ingredient-compositional method — grams for any Indian dish, no school dataset

**What to build:** Replace the "dish-name-first" constraint with an
**ingredient-first** pipeline (design:
`docs/research/general-indian-dish-method.md`): open-vocab component masks →
metric volume (device depth OR monocular shape × card scale) → per-state
density priors → grams; recipes (INDB) supply composition shares + nutrient
lookup; a frozen-feature ingredient-conditional head (Nutrition5k
per-ingredient supervision) refines geometric grams as a bounded residual so
geometry stays the floor for unseen dishes.

**Blocked by:** nothing (07a–07d independent; 07e last).

**Status:** in-progress (2026-10-29 — 07a done (ledger 007 keep), 07c data
layer done (ledger 010 keep): FAO/INFOODS v2 density table regenerated from
source (23 states: 7 literature / 16 assumed, 22 serving-audit entries) with
`literature` vs `analogue_transfer` honesty split; out-of-scope thali demo
runs end-to-end through the untouched measured tier (717 g synthetic-demo,
mechanism not accuracy). Gates: ruff 0, pyright 212 = baseline, hermetic
suite 223 passed. In flight: 07b Nutrition5k overhead pull (~250/600 dishes,
HF mirror `mmathys/food-nutrients` — original GCS bucket now holds only the
194.8 GB tarball), then 07d + 07e.)

- [x] 07a depth harness: MoGe-2 shape vs measured device depth on frames that
      have both (height-field mm-MAE + grams delta through the untouched
      measured tier), pre-registered ledger gate before running — **done as
      ledger 007 keep**: no device depth exists in WED (manifest is image+mask
      only) and no card is detectable in DEV frames, so the harness became a
      paired mode comparison (fallback K vs MoGe predicted K) + oracle-scale
      bound;      headline finding: unprojection/shape is sound, absolute scale is
      the entire defect — gate met (ΔMAE −165.5 g CI [−195.6, −137.5])
      `docs/ledger/007-moge-intrinsics-geometry.md`
- [ ] 07b ingredient teacher: ingredient-conditional head trained on
      Nutrition5k per-ingredient grams via the ticket-01 feature cache;
      report leave-ingredient-out split + in-domain MAE vs the 29.4 g/13.7%
      paper reference; ledger keep/revert with paired CIs — **ran as ledger
      012 revert (603-image mirror pull, 555 labelled dishes)**: in-domain
      test macro per-ingredient MAE 32.4 g (gate ≤80 met; paper ref 29.4 g
      dish-level RGB+volume), but the pre-registered transfer gate is NOT
      met — mixed greens fails on 3 held dishes (20.1 g vs 2×6.2 g bound)
      and white rice/olive oil have zero held-out test coverage, so the
      checkpoint is renamed `data/ingredient_head_candidate.pt` and does not
      serve (the 07e route stays checkpoint-absent). Follow-up: 1,000-dish
      pull + re-pick LIO ingredients with ≥2 test dishes each, fresh
      pre-registered entry
      `docs/ledger/012-n5k-ingredient-head-07b.md`
- [x] 07c ingredient-state density table (FAO/INFOODS v2, use-with-
      citation, nothing bundled — regenerated from the source XLSX by
      `tools/import_density_table.py`/`data/ingredient_densities.yaml`) +
      `out_of_scope` thali demo through the existing measured tier — **done
      as ledger 010 keep**: honesty split `literature` / `analogue_transfer`,
      22-entry serving audit; learned per-state density residuals deferred to
      the 07b head (07b-coupled)
      `docs/ledger/010-ingredient-density-table-07c.md`
- [x] 07d recipe table: INDB recipes imported + composition-share /
      per-100 g nutrient audit; invisible-component distribution rule —
      **done as ledger 011 keep**: data/indb_recipes.yaml (1,014 recipes,
      50.9% gram-resolved rows, Atwater median |delta| 1.3%),
      models/recipe_table.distribute_invisible (tested seam),
      menu-vs-INDB audit report (sambar assumed value likely −38 kcal low;
      bisibelebath has no INDB recipe). Adoption of INDB menu values is a
      separate ledger pass — audit never silently calibrates
      `docs/ledger/011-indb-recipe-table-07d.md`
- [x] 07e General-mode serving integration + uncertainty routing
      (`composition_inferred`, band widening for unknown states);
      School mode byte-untouched (spec 002 decision 1) — **done as ledger 013
      keep**: off-menu-only ingredient route (checkpoint-gated loader
      `models/ingredient_head.py` + `engine/general_mode.py` recipe match /
      composition MC / uncertainty flags `composition_inferred` /
      `unknown_state_widening`), `path_used: ingredient_head` added to the
      contract vocabulary; all three pre-registered criteria met hermetically
      (ruff 0, pyright 209, pytest 243, vitest 66). The route is a seam until
      the real ledger 012 checkpoint lands — match threshold and sigma
      defaults (0.5 / 0.35 / 0.45) re-read then
      `docs/ledger/013-general-mode-serving-07e.md`
- [ ] Every accuracy experiment carries its own pre-registered ledger entry
      per repo rules; no LOCKED read anywhere in this ticket
