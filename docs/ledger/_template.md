# NNN — <short title>

- **id**: NNN
- **branch**: `iter-…`
- **date**: YYYY-MM-DD
- **author**: <agent or person>

## Hypothesis

What we believe about the system and why this change should move it.

## Expected effect

The named metric(s) this change is expected to move, and the direction:

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| DEV MAE (g) | 20.30 | < … | plate-bootstrap 95% CI |

## Success criterion (written BEFORE coding)

A single falsifiable sentence, e.g. "DEV MAE drops by ≥ 0.5 g with the
paired 95% CI of (cand − base) excluding 0, and DEV 90% coverage stays in
[0.80, 0.95]."

## Change

What was actually changed, in enough detail to reproduce: files, approach,
knobs. Link the commit.

## Sources

- <url or repo-relative path> — what it supports

## Result

Data tier(s) run, both runs' configs (seed, checkpoint), and the paired
difference with its CI from `tools/compare_runs.py`:

| comparison | tier | mae_g base → cand | paired diff [95% CI] | coverage base → cand |
| --- | --- | --- | --- | --- |
| … | dev | 20.30 → … | … | 0.86 → … |

Stress deltas if any (`WED stress test, not real-world`).

## Decision

- **keep** | **revert** — one-sentence reason tied to the success criterion.

## Follow-ups

Anything noticed but deliberately not done.
