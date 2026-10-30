# Experiment ledger

One entry per substantive change to the weight-estimation stack, newest last.
The ledger is the decision record: code and reports say *what the numbers
were*; an entry says *what we thought would happen, what happened, and why
we kept or reverted it*. If a change has no entry, it does not exist.

## Rules

1. **Write the entry before the code.** The success criterion is fixed in
   writing *before* the change is made; after the run it may only be marked
   met/not-met, never edited to fit the outcome.
2. **Every number is paired and labelled.** Report a difference between two
   runs with its paired plate-bootstrap 95% CI from
   `tools/compare_runs.py`, and name the data tier it came from
   (`dev` / `train` / `locked`). A bare "MAE improved" is not a result.
3. **DEV only for tuning.** `train` is in-sample context, `locked` is a
   report and is read at most once per released claim. A decision made on a
   non-DEV number is invalid.
4. **One keep-or-revert per entry.** The decision field is `keep` or
   `revert`, followed by a one-sentence reason. "Keep pending more work" is
   a revert with extra steps.
5. **Sources carry URLs.** Any external claim (paper, dataset card, library
   behaviour) is cited with a link or a repo-relative file path; a number
   nobody can trace does not enter the ledger.
6. **Bookkeeping is local, evidence is committed.** `runs/experiments.jsonl`
   (appended by `tools/log_run.py`) and the report JSONs under
   `data/reports/` are scratch; the entry here is the durable record and
   must be self-contained enough to re-derive the decision.

## Entry lifecycle

```
branch iter-X  →  write entry (criterion pre-committed)
            →  code + run_eval DEV / DEV stress (+ train if in scope)
            →  compare_runs baseline vs candidate (paired CI)
            →  log_run + fill result/decision
            →  keep: merge + close the entry · revert: `git revert` + reason
```

Each iteration **must** run the kill switch first:

```bash
.venv/bin/python -m tools.should_stop || exit 0
```

## Files

| File | What it is |
| --- | --- |
| `_template.md` | The blank entry — copy it, do not re-invent the fields |
| `000-baseline.md` | Chunk-A baseline: the numbers every later entry compares against |

## Recent synthetic diagnostics

| Entry | Question | Decision |
|---|---|---|
| [022 — mask spill](022-synthetic-mask-spill.md) | Does 25% vessel-pixel spill reproduce the synthetic total errors? | Criterion failed; no serving change. |
| [023 — surface-area integration](023-synthetic-surface-area-integration.md) | Does local pixel-area integration improve exact-mask synthetic estimates? | Candidate rejected; no serving change. |
| [024 — card position](024-synthetic-card-position-scale.md) | Does card position change measured scale, and does homography reduce spread? | Two-position evidence is promising, but the three-position criterion was not assessable; no serving change. |
| [025 — card-position replication](025-synthetic-card-position-replication.md) | Does the effect replicate across three fixed placements with all 18 markers detectable? | Preregistered; outcome pending. |

These are synthetic mechanism diagnostics only. The weighed ArUco plates are
permanently EVAL-ONLY and are not eligible for tuning or candidate selection.
