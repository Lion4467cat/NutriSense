# 04: General mode backend — WHO goals data + goal-value serving

**What to build:** The backend owns the WHO Daily-goal table and serves goal values over HTTP, so the frontend can compute meal-vs-goal shares. `/analyze` stays mode-agnostic (ADR 0003): no mode flag, no contract change. Values come from the researched WHO defaults with every derivation traceable to the research file.

**Blocked by:** None (can start immediately).

**Status:** done (2026-10-28 — GET /goals; G1–G13 recorded as assumed-with-provenance)

- [x] Goal data file created from `docs/research/who-goals.md` values: energy kcal/day and protein g/day by age band, sex, and activity level; WHO defaults per its §6.5 recommendation; entries marked with status + provenance like all data files
- [x] The data-shaping choices G1–G13 resolved pragmatically for v1 following the research file's recommendations, each recorded in the data file's header notes as assumed-with-provenance — not silently (verified 2026-10-29: `[G#]` blocks in `data/goals_who.yaml`; a test enforces the bookkeeping — `test_shaping_choices_recorded_not_silent`, `test_caveats_carry_population_and_margin_notes`)
- [x] Goal values served over HTTP alongside existing menu-style data (`GET /goals` in main.py); HTTP-contract seam test covers it (`test_goals_endpoint_shape`, `test_goals_endpoint_covers_every_profile` in `tests/test_goals.py`)
- [x] `/analyze` request and result contracts unchanged (test guards this — `test_analyze_result_contract_unchanged` / `test_analyze_request_contract_unchanged` verify exact envelope equality and 422 shape)
- [x] Non-GPU suite hermetic and green; lint + typecheck gates pass (re-verified 2026-10-29 with the 41-way session: 206 passed exit 0, ruff 0, pyright at baseline)
