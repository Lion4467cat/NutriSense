# ADR 0003: Two app modes — School compliance and General goal-tracking

- **Status:** Accepted
- **Date:** 2026-10-28

## Context

The pipeline is built around the school menu: dishes come from the menu
(single source of dish truth), captures carry `day` + `band`, and the
analysis ends in a **Verdict** (PASS/BORDERLINE/FAIL/`cannot_verify`/
`out_of_scope`) judged under **Policy**. The user wants the app to serve
any meal, not only the school menu: the WED-trained head already covers
41 dish classes, but 38 of them have no menu entry, no standards, and no
compliance basis — a Verdict for them would be meaningless (PASS/FAIL
needs standards that do not exist for an off-menu dish).

## Decision

Two user-switchable modes of the app (decided 2026-10-28, grilling session):

1. **School mode** — unchanged behaviour: menu dishes only, `day` + `band`
   capture fields, Verdict under Policy, PM POSHAN compliance scoring.
   Non-menu dishes stay `out_of_scope` here.
2. **General mode** — all 41 WED classes are recognizable and get grams +
   nutrients, but there is **no compliance Verdict**: the result shows
   each nutrient's **share of a Daily goal**. Daily goal defaults come
   from WHO tables by age, gender, and physical activity level
   (`docs/research/who-goals.md`); the user may enter their own goal.
   The profile (age/gender/activity) is a one-time Settings entry, not a
   per-capture field.

## Why not reuse the Verdict machinery in General mode

A single meal is never PASS/FAIL against a *daily* target — stamping a
Verdict there would bend the word. Shares-of-goal answer the real
question ("how much of my day is this meal?"). The Verdict vocabulary
stays single-meaning: a compliance concept owned by School mode.

## Consequences

- Policy stays School-mode machinery; General mode does not mint a second
  Policy with new P-zones.
- WHO goal tables live in `data/` (backend serves goal values); the
  frontend computes meal-vs-goal shares from results it already holds, so
  `/analyze` stays mode-agnostic and goal edits need no re-capture.
- Serving expansion to 41 classes (gallery from WED train images) is a
  prerequisite; see the ticket plan (T-A…T-D, `docs/research/
  indian-food-datasets.md` for dataset options beyond WED).
