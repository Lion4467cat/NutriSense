# 05: General mode frontend — mode switch, profile, goal shares

**What to build:** A user can switch to General mode, set their profile (age, gender, physical activity) once in Settings, and see any analyzed meal as grams + nutrients + share of their Daily goal — with WHO defaults or their own entered goals. School mode is unchanged. Goal edits apply immediately to history views without re-analysis.

**Blocked by:** 02 (41-class serving makes off-menu dishes real), 04 (goal values must exist to show).

**Status:** done (2026-10-28 — tsc clean, vitest 66/66, build ok)

- [x] Mode switch (School ↔ General) in the UI; mode is a frontend concern, persisted in prefs
- [x] Settings profile: age band, sex, activity level, one-time entry, stored in existing prefs; defaults chosen sensibly (verified in code 2026-10-29: `frontend/src/pages/Settings.tsx` profile selects → `prefs.profile` via `defaultProfile` served fallback)
- [x] Goal display: served goal values used as defaults; user-entered override editable (`goalOverride` draft form, Reset-to-WHO); shares computed client-side from stored results via `resolveGoal` (services/goals.ts) — no re-analysis
- [x] General mode result views: grams + nutrients + per-nutrient share of Daily goal; NO verdict badge (`GeneralResult.tsx`); no-card estimate disclaimer still leads when applicable
- [x] Frontend gates green: tsc, vitest (66/66), build — recorded 2026-10-28; no frontend file changed since (all session edits backend-only), so the gates stand
- [x] School mode views and records behaviour unchanged (existing tests untouched and green — `Result.test.tsx`, `History.test.tsx` passed in the 66/66 run)
