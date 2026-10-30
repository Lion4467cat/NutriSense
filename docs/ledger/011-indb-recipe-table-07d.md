# 011 — INDB recipe table + invisible-component rule (ticket 07d)

- **id**: 011
- **branch**: `general-mode-calibration`
- **date**: 2026-10-29
- **author**: Buffy (agent)

## Hypothesis

The INDB capstone files (1,014 Indian recipes with per-recipe raw-ingredient
composition + master per-100 g/per-serving nutrient table) can supply the
S5 composition/nutrient layer for *unseen* dishes: recipes are matched by
name, invisible components (oil/ghee/spices/salt/water — not segmentable on
the plate) are distributed over visible carriers proportional to their
raw-gram mass, and the menu's `status: assumed` nutrient values get their
first real recipe-table deltas. Nothing is bundled: the artifact regenerates
from the downloaded source xlsx files.

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| recipes with recipe-backed per-100 g macros | 0 | 1,014 | data layer only |
| menu assumed-value audit | none | deltas vs matched INDB recipes | audit-only report |
| gram-resolved composition coverage | n/a | measured and recorded (51% of rows) | honest unit policy |

## Success criterion (written BEFORE coding)

`data/indb_recipes.yaml` regenerates from sources with provenance meta +
audit summary; unit-resolution policy is explicit (g/kg direct, ml/L at the
recorded water approximation, tsp/cup/pinch/... unresolved with
`g_resolution: null`); the invisible rule is materialized both as data
(`visible` flags + `mass_audit_g`) and as the serving seam
`models/recipe_table.distribute_invisible` (share-preserving, mass-total
inflating); menu-vs-INDB audit is a report, never a gate; tests + ruff 0 +
pyright at the 212 baseline.

## Change

- `tools/import_indb_recipes.py` — parses `recipes.xlsx` (10,271 ingredient
  rows), `INDB.xlsx` (master nutrient rows), `recipes_names.xlsx`; writes
  `data/indb_recipes.yaml` (1,014 recipes). Atwater 4/4/9 sanity per recipe;
  `visible` classification by name patterns (method doc §7) with overrides
  (e.g. ginger ale stays visible).
- `data/indb_recipes.yaml` — generated artifact (~2.6 MB).
- `models/recipe_table.py` — serving seam: `load_recipes`,
  `recipe_nutrients_per_100g`, `distribute_invisible`.
- `tools/audit_menu_vs_indb.py` + `data/reports/menu_indb_audit.yaml` —
  menu generic_ids vs matched INDB recipes (Murphy: `bisibelebath` has no
  INDB recipe — real coverage gap, recorded).
- `tests/test_indb_recipes.py`, `tests/test_recipe_table.py` — schema +
  honesty guards.

Sources: https://github.com/lindsayjaacks/Indian-Nutrient-Databank-INDB-
(recipes.xlsx, INDB.xlsx, recipes_names.xlsx, Units.xlsx — not redistributed;
use-with-citation per docs/licenses.md posture).

## Result

Data tier run: importer on the 2025 INDB release (version pinned by the
GitHub repo commit fbdb62b-era files).

| check | result |
| --- | --- |
| recipes imported | 1,014 (all three sources: ASC/BFP/OSR) |
| ingredient rows gram-resolved | 5,232 / 10,271 (50.9%) |
| resolved raw mass | 396.6 kg |
| invisible rows flagged | 1,146 |
| Atwater median |delta| | 1.3% (internally consistent table) |
| tests | 11 passed (6 + 5) |
| ruff (all 07d files) | 0 |
| pyright gate | 212 = baseline 212 |

Audit deltas that matter (menu `status: assumed` vs INDB matched recipe):

| generic_id | matched INDB recipe | kcal/100 g delta | protein delta |
| --- | --- | --- | --- |
| sambar (assumed 60) | ASC167 Sambar (96.9) | **−38.1%** | −25.4% |
| vegetable_rice (assumed 150) | ASC115 Mixed vegetable pulao (113) | +32.7% | +28.5% |
| rice_boiled (literature 112) | ASC167 Sambar (96.9) | +15.6% | −28.4% (cross-dish match, treat cautiously) |
| curd (literature) | ASC126 Curd rice | −69.3% | — (match is curd-rice, not plain curd; audit-only) |
| bisibelebath (assumed 185) | none in INDB | no INDB recipe exists | coverage gap |

The assumed sambar value (60 kcal/100 g) is likely low vs INDB's 96.9 — a
concrete candidate for the next honesty pass, but adoption needs its own
ledger entry (this ticket's rule: audit, never silent calibration).

## Decision

- **keep** — artifact + serving seam meet the honesty schema; the
  distribution rule is now a testable function rather than a paragraph of
  prose; menu deltas are recorded for the follow-up.

## Follow-ups

- 07e wires `distribute_invisible` + `recipe_nutrients_per_100g` into the
  General-mode serving path (`composition_inferred` flag).
- A candidate ledger trial adopting INDB per-100 g values for `sambar` /
  `vegetable_rice` where matched recipes are plausible (paired DEV evaluate
  through `tools/eval_prior_tier_on_wed.py`, keep/revert).
- tsp/cup composition shares need the Units.xlsx per-item conversions to go
  beyond 50.9% resolution; deferred (per-substance, error-prone mapping).
