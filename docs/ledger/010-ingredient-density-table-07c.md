# 010 — Ingredient-state density table + out-of-scope demo (ticket 07c)

- **id**: 010
- **branch**: `general-mode-calibration`
- **date**: 2026-10-29
- **author**: Buffy (agent)

## Hypothesis

An ingredient-state density table derived from the FAO/INFOODS Density
Database v2 (machine-readable XLSX, 638 foods) replaces the per-dish ad-hoc
`density_g_ml` assumptions in `data/menu.yaml` with cite-backed values, so the
measured geometry tier (S4: `volume × ρ`) can serve dishes that were never in
the menu — the first concrete "any Indian dish" path. Nothing is bundled: the
table is regenerated from the downloaded source XLSX by
`tools/import_density_table.py`, with per-state provenance (BiblioID + xlsx
row number).

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| sources per density (out-of-scope dish) | 0 (assumed) | ≥ 13/23 states FAO-cited | literature + analogue_transfer |
| serving audit coverage | none | 22 generic_ids, every one either FAO-matched or explicitly `assumed` | audit-only layer |
| serving behavior | menu dishes only | unchanged for menu dishes | byte-level: densities for menu dishes not touched in this entry |

Honesty rule demanded by the demo run: a value carried from the *nearest
analogue* row (e.g. curd → cultured milk, vegetable fry → fried onions) must
NOT be labeled `literature`. States are split into `rule: literature` vs
`rule: analogue_transfer`; both carry `reference_rows`, only the former
is a direct FAO match. The audit layer carries `fao_density_g_ml` +
`value_status` for both, and `status: assumed` (no FAO row) otherwise.

## Success criterion (written BEFORE coding)

`tools/demo_out_of_scope_density.py` — a thali that is neither a WED class nor
a menu dish — completes through the untouched measured tier
(`models.portion_estimator.estimate_portion`, card-measured anchor) with
per-component densities whose provenance is printed per component from the
generated table; every audit entry's `serving_id` is one the serving path
reads; `tests/test_densities.py` green; ruff 0; pyright at or below the 212
baseline; full hermetic suite passes.

## Change

- `tools/import_density_table.py` — parses the FAO v2 XLSX into
  `data/ingredient_densities.yaml` (23 states: 7 literature, 16 assumed;
  22 serving audit entries). `analogue_transfer` split added after the first
  demo run showed proxies mislabeled as literature.
- `data/ingredient_densities.yaml` — generated artifact (see above).
- `tools/demo_out_of_scope_density.py` — synthetic 640×480 overhead capture
  (flat table + 8 cm food dome, card cm/px anchor), runs the real
  `estimate_portion`; prints each component's density and its source
  (FAO literature row / nearest-analogue FAO row / serving assumed).
- `tests/test_densities.py` — schema + honesty guards (every state has a
  rule; every audit `serving_id` exists in the stack; analogue states can't
  claim `literature`; cache flow of `config.load_densities`).
- `config.py` — `load_densities()` with the repo's standard cache pattern.

Source: FAO/INFOODS Density Database v2 XLSX fetched manually to
`/tmp/density_DB_v2.xlsx` (not redistributed — use-with-citation posture,
per repo `docs/licenses.md`).

## Sources

- https://www.fao.org/fileadmin/templates/food_composition/documents/density_DB_v2_0_final-1__1_.xlsx — the density source
- `docs/research/general-indian-dish-method.md` §4 S4 — the design seam

## Result

No accuracy metric is claimed by this entry: the demo capture is synthetic,
so its 717 g total shows the mechanism, not real error. The run:

```
footprint 343 cm^2, mean height 26.3 mm, volume 902 ml
effective density 0.795 g/ml -> grams 717 g (base_method=ring, tier=measured)
  rice: share 0.55 x 0.730 g/ml [FAO literature row]          -> 394 g
  dal:  share 0.25 x 1.054 g/ml [nearest-analogue FAO row]    -> 179 g
  curd: share 0.10 x 1.010 g/ml [nearest-analogue FAO row]    ->  72 g
  veg_fry share 0.07 x 0.750 g/ml [nearest-analogue FAO row]  ->  50 g
  papad: share 0.03 x 0.400 g/ml [serving assumed]            ->  22 g
flags=[] sigma_grams_rel=0.226
```

Gates (exit codes preserved one-command-per-call):

| check | result |
| --- | --- |
| `pytest tests/test_densities.py` | 7 passed |
| full hermetic suite | 223 passed (74 s) |
| ruff (importer/demo/tests) | 0 |
| pyright gate | 212 = baseline 212 |

Environment regression fixed en route: `openpyxl` (the only parser for the
FAO XLSX) was missing from `.venv` and unpinned; reinstalled and pinned
`openpyxl==3.1.5` in `pyproject.toml`.

## Decision

- **keep** — the artifact meets the honesty schema and the demo proves the
  out-of-scope path end-to-end with no serving behavior change; the measured
  tier now has a cite-backed density floor for any dish whose parts are in
  the ingredient alphabet.

## Follow-ups

- 07d wires INDB composition shares so `share` stops being a hand guess for
  out-of-scope dishes (the demo's shares are illustrative).
- Learned per-state density residuals (Nutrition5k measurement → residual
  correction) remain 07b-coupled work; the table's `learned_residual` slots
  are empty by design.
- Papad-type states have no FAO row (unit-weight foods) — the state-aware
  volume definitions (count/diameter) from §7 of the method doc are the
  designed fix, not a density.
