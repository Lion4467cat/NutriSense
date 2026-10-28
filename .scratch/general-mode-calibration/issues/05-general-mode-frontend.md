# 05: General mode frontend — mode switch, profile, goal shares

**What to build:** A user can switch to General mode, set their profile (age, gender, physical activity) once in Settings, and see any analyzed meal as grams + nutrients + share of their Daily goal — with WHO defaults or their own entered goals. School mode is unchanged. Goal edits apply immediately to history views without re-analysis.

**Blocked by:** 02 (41-class serving makes off-menu dishes real), 04 (goal values must exist to show).

**Status:** ready-for-agent

- [ ] Mode switch (School ↔ General) in the UI; mode is a frontend concern, persisted in prefs
- [ ] Settings profile: age band, sex, activity level, one-time entry, stored in existing prefs; defaults chosen sensibly
- [ ] Goal display: served goal values used as defaults; user-entered override editable; shares computed client-side from stored results (no re-analysis)
- [ ] General mode result views: grams + nutrients + per-nutrient share of Daily goal; NO verdict badge; no-card estimate disclaimer still leads when applicable
- [ ] Frontend gates green: tsc, vitest (new selectors tested like existing tally/attention), build
- [ ] School mode views and records behaviour unchanged (existing tests untouched and green)
