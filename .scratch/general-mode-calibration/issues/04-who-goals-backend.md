# 04: General mode backend — WHO goals data + goal-value serving

**What to build:** The backend owns the WHO Daily-goal table and serves goal values over HTTP, so the frontend can compute meal-vs-goal shares. `/analyze` stays mode-agnostic (ADR 0003): no mode flag, no contract change. Values come from the researched WHO defaults with every derivation traceable to the research file.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Goal data file created from `docs/research/who-goals.md` values: energy kcal/day and protein g/day by age band, sex, and activity level; WHO defaults per its §6.5 recommendation; entries marked with status + provenance like all data files
- [ ] The data-shaping choices the research file lists as open (band convention, PAL anchors, weight referents, etc.) are resolved pragmatically for v1 following the research file's recommendations, each recorded in the file's notes as assumed-with-provenance — not silently
- [ ] Goal values served over HTTP alongside existing menu-style data; HTTP-contract seam test covers it
- [ ] `/analyze` request and result contracts unchanged (test guards this)
- [ ] Non-GPU suite hermetic and green; lint + typecheck gates pass
