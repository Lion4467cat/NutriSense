# Spec 002: Two app modes, 41-class serving, interval calibration

- **Status:** ready-for-agent
- **Date:** 2026-10-28
- **Source:** grilling session 2026-10-28 (decision tree below); ADR 0003; research files `docs/research/who-goals.md` and `docs/research/indian-food-datasets.md`
- **Companion plan/tasks:** to be written in this directory per repo spec-kit convention

## Problem Statement

From the user's perspective:

1. The app recognizes only the three school-menu dishes. Any other meal is
   rejected as `out_of_scope`, so the app cannot be used for home food.
2. The printed weight ranges promise "90% of the time the true weight is
   inside", but only ~85% of samples fall inside. Users cannot tell how
   much to trust a range.
3. There is no way to relate a meal to a person's daily needs — the app
   judges school compliance only, with school bands and standards.
4. Weight-head training takes ~70 minutes per run, which slows every
   experiment that touches the model.

## Solution

Two user-switchable modes (ADR 0003):

- **School mode** — exactly today's behaviour: menu dishes, `day` + `band`,
  a Verdict under Policy, PM POSHAN compliance scoring.
- **General mode** — all 41 WED dish classes are recognizable; the result
  shows grams, nutrients, and each nutrient's share of a **Daily goal**.
  Daily goal defaults come from WHO tables by age, gender, and physical
  activity level; the user may enter their own goal. There is no Verdict
  and no compliance scoring in this mode.

Supporting work: recalibrate the learned-head weight intervals to honest
90% coverage (conformal, leave-one-plate-out), cache frozen encoder
features to make head training fast, and follow a documented robustness
plan (WED cross-validation + transfer from measured non-Indian datasets +
school-capture fine-tuning later).

## User Stories

1. As a school nutrition officer, I want School mode to behave exactly as
   today, so that existing compliance workflows and records stay valid.
2. As a general user, I want to switch between School and General modes,
   so that one app serves both my institutional and personal needs.
3. As a general user, I want any of the 41 known Indian dishes to be
   recognized from a photo, so that I can analyze home-cooked meals.
4. As a general user, I want the grams and nutrients of a recognized
   off-menu dish (e.g. rajma), so that I get useful numbers even without
   school standards.
5. As a general user, I want my meal shown as a share of my Daily goal
   ("620 kcal — 30% of your day"), so that I can understand the meal in
   context of my day rather than as a pass/fail.
6. As a general user, I want Daily goal defaults derived from WHO tables
   for my age, gender, and physical activity level, so that defaults are
   credible without any input from me.
7. As a general user, I want to enter my own Daily goal, so that the
   tracking matches my personal targets.
8. As a general user, I want my profile (age, gender, activity) stored
   once in Settings, so that I do not re-enter it on every capture.
9. As a general user, I want goal edits to apply immediately to my
   history views, so that I do not need to re-capture or re-analyze.
10. As any user, I want the printed 90% weight range to actually contain
    the true weight ~90% of the time, so that I can trust the interval.
11. As any user, I want the interval width to stay reasonable, so that a
    technically-correct-but-useless range (e.g. 100–400 g) is never shown.
12. As any user, I want the point estimate unchanged by calibration, so
    that the grams number I see does not move when intervals are fixed.
13. As a developer, I want the calibration decision recorded as a ledger
    entry with a pre-registered gate, so that the success criterion cannot
    drift after results are known.
14. As a developer, I want the LOCKED test split to remain unread, so
    that test-split integrity is preserved.
15. As a developer, I want the classifier gallery for all 41 classes to
    come from WED train images (with RASOI as a real-capture complement),
    so that serving expansion needs no new field collection.
16. As a developer, I want a leave-one-plate-out evaluation of the
    calibration, so that no plate is ever graded by a calibration that
    saw it.
17. As a developer, I want encoder features cached once per dataset
    during head training, so that experiments run in minutes.
18. As a maintainer, I want the stale weight-head report artifact
    regenerated on the next training run, so that documented staleness
    is finally cleared.
19. As a maintainer, I want WED's license terms confirmed and recorded,
    so that everything built on WED stands on verified provenance.
20. As a maintainer, I want the robustness plan (cross-validation,
    augmentation, transfer) written down as tickets, so that "make it
    robust with available data" is an executable plan, not a wish.
21. As a researcher, I want the WHO goal values traceable to primary
    sources with access dates, so that the numbers in the app are
    auditable.
22. As a parent checking a home meal, I want the no-card estimate
    disclaimer to lead the reasons in General mode too, so that I always
    know when grams are estimated.
23. As a frontend user, I want goal shares computed from results I
    already have, so that changing my goal does not require re-analysis.
24. As a school user, I want General mode to not touch Policy or
    compliance thresholds, so that school records keep their meaning.

## Implementation Decisions

Decided in the grilling session (2026-10-28); details in ADR 0003 and
the research files.

1. **Two modes, one contract.** `/analyze` stays mode-agnostic: same
   request shape, same result contract. Mode selects presentation and
   which dishes are scored; it does not mint a second Policy.
2. **No Verdict in General mode.** The result carries grams, nutrients,
   and share-of-Daily-goal values. The Verdict vocabulary stays a
   School-mode compliance concept. The no-card estimate disclaimer
   (Reason kind `no_reference_card`) still leads reasons on prior-tier
   plates in both modes.
3. **41-class serving.** The WED↔serving mapping expands so every WED
   class resolves to a serving entry; unmapped-class behaviour
   (out_of_scope) disappears. Composite merge rules for multi-slot dishes
   keep the existing validated behaviour.
4. **Gallery from WED train + RASOI.** Gallery images for all classes come
   from WED train images; RASOI (NCVPRIPG 2025, CC BY-NC-SA, real captured
   thalis, boxes+labels, no mass) may complement for gallery/segmentation
   prototyping after a license fit check. The abstain threshold is
   re-derived for the 41-class gallery via its LOO evaluation — not
   carried over from the 2-class gallery.
5. **Goals live in backend data; math lives in the frontend.** WHO goal
   values become a backend data file (single data owner, entries marked
   with status like all data files); goal values are served over HTTP;
   the frontend computes meal-vs-goal shares from the results it already
   stores. User-entered goals and the profile (age/gender/activity) are
   frontend prefs.
6. **WHO values: defaults per the research recommendation.** WHO 2004
   energy / TRS 935 protein values, chosen over independent alternatives
   (EFSA identical, US DRI within ±9%, IAAO contested) — see
   `docs/research/who-goals.md` §6.5. The file's standing re-check
   instruction (FAO/WHO/IAEA reevaluation in progress, no values yet)
   carries into the data file's notes.
7. **Interval calibration: learned-head grams only.** Scope is the
   Learned weight tier intervals (all 41 classes once serving expands).
   Measured-tier geometry intervals and kcal/protein table intervals are
   untouched in this spec.
8. **Staged correction shape.** Stage C first: tune the existing global
   interval-widening parameter on out-of-fold DEV coverage. If the gate
   passes with acceptable per-dish spread, keep. Otherwise Stage B:
   per-dish multipliers. The conformal machinery (normalized residuals,
   leave-one-plate-out over the 21 DEV plates) produces the honest
   out-of-fold coverage either way; the head itself is never retrained
   per fold.
9. **Calibration gate (pre-registered before coding).** Fresh DEV run:
   out-of-fold coverage_90 ≥ 0.90; MAE statistically unchanged (paired
   CI via the existing run-comparison tool); mean interval width growth
   ≤ +25% (else the ticket fails and we investigate); no LOCKED read.
   Recorded in `docs/ledger/` per its rules before any code.
10. **Encoder feature cache.** The frozen encoder's features are computed
    once per dataset and reused across epochs/folds; head training drops
    from ~70 min to minutes. Golden guard: cached-path and live-path
    training produce identical weights.
11. **Robustness plan (T-E, after calibration).** WED cross-validation +
    augmentation; transfer from Nutrition5k (CC BY 4.0, ±1 g scale truth)
    and FPB (lab grams, CC BY-NC 4.0 — **eval-only**, never in the
    training mix); author-contact shortlist (Delhi weighed-photo atlas,
    FLIC, Sri Lanka set) pursued at zero cost. No second measured-Indian
    dataset exists (audited sweep, 2026-10-28) — the plan is the answer
    to that empty result.
12. **WED license confirmation precedes dataset-coupled work** (single
    most critical provenance gate; cite, never redistribute).

## Testing Decisions

- Test external behaviour only, at the highest existing seam. Zero new
  backend seams are introduced by this spec:
  - T-A rides the classify Stage's abstain branch, the deps-injection
    seam in the pipeline entry, and the gallery build tool's LOO
    evaluation; a data-level test asserts every WED class resolves in the
    serving mapping.
  - T-B asserts cached-path vs live-path training equality (golden-style,
    prior art: the weight-head load guards).
  - T-C rides the existing M6 interval-widening hook and the existing
    weight-head injection seam; interval width behaviour is asserted
    through the MC summary contract.
  - T-D rides the existing HTTP-contract seam (goal values served like
    menu data) and the frontend records selectors, tested in vitest like
    the existing tally/attention selectors.
- Acceptance gates for eval-affecting changes run through the eval
  harness (DEV tier only; paired CIs; ledger entries pre-registered).
- Hermetic CI (no GPU, no downloads) keeps covering the unit seams;
  GPU-marked tests cover golden model guards.

## Out of Scope

- Any read of the LOCKED test split.
- Changing compliance scoring, Policy thresholds, or the Verdict
  vocabulary.
- New dataset acquisition (none exists — audited); procurement of
  commercial datasets (foodron.ai) is recorded as an option, not planned.
- Fine-tuning on school captures (waits for the collected dataset; the
  robustness tickets prepare for it).
- Whole-meal multi-dish compliance claims (paper-scoped limitation).
- Mobile applications, accounts, server-side user profiles.
- Settling the 13 WHO data-shaping choices (G1–G13 in
  `docs/research/who-goals.md`) — they are decided during T-D
  implementation, not in this spec.

## Further Notes

- The grilling session's full decision tree: two modes (confirmed),
  staged calibration C→B (confirmed), leave-one-plate-out (confirmed),
  gate + width cap (confirmed), gallery from WED train (confirmed),
  two-ticket ordering expansion→cache→calibration (confirmed, extended
  with T-D/T-E).
- Glossary terms added during the session: School mode, General mode,
  Daily goal.
- Silver lining recorded for the owner: the pending school-capture
  dataset will be the only measured-Indian school-meal dataset in
  existence — collection is human work and remains the project's key
  differentiator.
