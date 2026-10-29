# 013 — General-mode ingredient-compositional serving + uncertainty routing (ticket 07e)

- **id**: 013
- **branch**: `general-mode-calibration`
- **date**: 2026-10-29
- **author**: Buffy (agent)

## Hypothesis

An off-menu recognized dish can be served through the ingredient-compositional
route — ingredient head (ledger 012 checkpoint) predicts per-ingredient grams,
the best INDB recipe match (ledger 011 table) supplies composition shares +
per-100 g nutrients, invisible components ride `distribute_invisible` — and the
result rides the existing 18-key wire with `path_used: ingredient_head`
Grams for unmatched/absent-head cases keep the EXACT current off-menu behaviour
(dish-slot head + generic table), and School-mode dishes never take the new
branch.

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| off-menu serving path | dish-slot head + generic table, path_used `learned_head` | ingredient route when checkpoint + recipe match both exist, `composition_inferred` flag set | general mode only |
| composition uncertainty | fixed generic-table sigma | matched: head-rel sigma; weak/unknown-state match: widened by an explicit bump factor | pre-registered defaults below |
| School-mode wire output | unchanged | unchanged (byte-identical) | spec 002 decision 1 |

## Success criterion (written BEFORE coding)

KEEP if all of: (1) with `data/ingredient_head.pt` present and a recipe match,
an off-menu dish returns `path_used = "ingredient_head"`, portion grams > 0,
flags contain `composition_inferred`, and the INDB nutrients reach the wire in
assumed_nutrients; (2) with the checkpoint ABSENT (the case until ledger 012
finishes), off-menu and school responses are byte-identical to the current
pipeline (hermetic suite, unchanged fixtures); (3) a school-menu dish with the
checkpoint present still takes the untouched school path. REVERT otherwise.

## Pre-registered constants (uncertainty routing, no measured calibration yet —
	they are defaults pending a ledger-measured revision)

- Recipe match threshold: best cosine ≥ 0.5 over the recipe's gram-resolved
  component slots against the predicted ingredient vector, else NO match
  (existing off-menu path, unchanged).
- Matched sigma_rel = 0.35 (RGB-only full-frame teacher, ledger 012 gate):
  weaker/unknown-state match widened to 0.45.

## Change

- `models/ingredient_head.py` — checkpoint-gated loader (`data/ingredient_head.pt`,
  head-only, versioned by slots/encoder/seed) + full-frame-ROI predict
  (same preprocessing as the trainer: 224², ImageNet-norm RGB).
- `engine/general_mode.py` — recipe match + composition serving + uncertainty
  routing; `path_used: ingredient_head` added to the closed path vocabulary;
  contract TS regenerated.
- `engine/pipeline.py` — off-menu-only branch right after the SCOPE gate:
  ingredient head loads lazily (absent/failed → existing flow, no degration
  spam), the ingredient route only fires for dishes NOT in menu.yaml.

## Sources

- `docs/research/general-indian-dish-method.md` §4/§7 — design seam
- `docs/ledger/011-indb-recipe-table-07d.md` — recipe table + invisible rule
- `docs/ledger/012-n5k-ingredient-head-07b.md` — ingredient teacher

## Result

(from tests + hermetic suite after implementation)

| check | result |
| --- | --- |
| ingredient route fires (injected head + recipe match) | PASS — `path_used: ingredient_head`, `composition_inferred`, `indb_R001` in assumed_nutrients (tests/test_general_mode.py) |
| checkpoint absent → byte-identical fallback | PASS — full hermetic suite pre-registered off-menu tests unchanged (pytest tests → 243 passed incl. fake-head head present/unmatched injection cases) |
| school dish with head present → school path | PASS — `learned_head` verdict path, route never consulted |
| gates | ruff 0 · pyright 209 (baseline locked, was 212) · pytest 243 · vitest 66 |

## Decision

- **keep** — all three pre-registered criteria met; School-mode bytes untouched
  (pipelined only inside the off-menu branch, gated on the checkpoint being
  present); the recipe-match + sigma defaults are seams pending measured
  re-read once the ledger 012 teacher lands.

## Caveat (recorded honestly)

The route is verified hermetically with a duck-typed head + a mini recipe
fixture; NO real IngredientHead checkpoint exists yet (ledger 012 running),
and the recipe-match threshold/sigma defaults are unmeasured. Serving
numerically through this route before re-reading those numbers is NOT claimed.

## Follow-ups

- Ledger 012 run lands → swap the fake head for the real checkpoint, re-read
  the sigma defaults against the measured MAE.
