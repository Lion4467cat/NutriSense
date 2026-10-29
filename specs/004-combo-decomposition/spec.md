# Spec 004: Per-item recognition — combo decomposition (P1)

- **Status:** ready-for-agent
- **Date:** 2026-10-29
- **Source:** ledger 016 follow-up 1 (multi-item over-count: every vessel crop
  classifies as the combo dish), ledger 009 (per-crop RGB evidence limit).

## Problem Statement

On the multi-item path (spec 003), each vessel crop is classified against the
FULL gallery. A rice+rasam plate's full-frame classification is the combo dish
(`rice_sambar`), and every vessel crop then re-matches the same combo — so
each vessel is portioned with the full mixed-dish recipe and the aggregate
double/triple-counts (772–880 g on one plate, ledger 016).

## Solution

**Combo decomposition**: when the plate-level dish maps to ≥ 2 WED component
classes (a combo), per-item crop classification is restricted to the combo's
component serving targets (argmax over the already-computed gallery score
vector, same top-3-mean cosine metric — no extra model call). The item then
portions under its own component dish entry (off-menu entries like
`steamed-rice`, `sambar` carry their own components/densities), so the
aggregate sums distinct components instead of repeated combos.

- The same `gallery_match_threshold` applies to the restricted match
  (pre-registered default). Below threshold → the item keeps its
  unrestricted classification (robust fallback, today's behaviour).
- Single-component dishes (one WED slot) are unaffected.
- No new model, no new dependency, no LOCKED read.

## Success criteria (written BEFORE code)

1. Hermetic suite green, ruff clean, pyright ≤ baseline 209.
2. New seam tests: two-vessel combo frame decomposes into distinct component
   dishes with namespaced aggregate components; below-threshold component
   scores fall back to the unrestricted classification.
3. Real-photo diagnostic re-run (same six frames, no GT): rice+rasam multi
   frames show per-item component dishes instead of N× the combo; grams
   recorded and compared against the ledger-016 over-count honestly.
