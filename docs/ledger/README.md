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
| [025 — card-position replication](025-synthetic-card-position-replication.md) | Does the effect replicate across three fixed placements with all 18 markers detectable? | Criterion met: global-scale sensitivity in 6/6 scenes; homography spread ≤2% in 4/6; no serving change. |
| [026 — card/food plane-height audit](026-card-food-plane-height-audit.md) | Does projecting the food contour through card height bias its footprint area? | Criterion not met; source audit found the renderer defines mask support from table-plane ray intersections. No code change. |
| [027 — VLM canteen heldout](027-vlm-canteen-participant-heldout.md) | How does direct vision-language transfer perform on held-out university canteen meals? | Large negative bias (-106.9g); retained as research benchmark with serving guarded behind 0.80 gallery threshold. |
| [028 — synthetic food data](028-synthetic-food-data.md) | Strategy for physical volume and depth simulation for Indian institutional meals. | Outlined physical rendering criteria; rejected analytic naive surfaces. |
| [029 — WED semantic segmentation study](029-wed-semantic-segmentation-study.md) | Evaluation of native 42-class DeepLabV3 segmentation on institutional thalis. | Achieved 0.8211 macro food IoU, 0.9196 foreground IoU, and 0.7541 region F1. |
| [030 — WED boundary-loss confirmatory](030-wed-boundary-loss-confirmatory.md) | Confirmatory 3-seed evaluation of boundary-aware loss on institutional food boundaries. | Boundary F1 0.5973; tiny-component recall increased to 0.3953. |
| [031 — mass-conditioned GAN](031-mass-conditioned-gan.md) | Feasibility of conditioning generative appearance models on class-level gram targets. | Architecture verified; flagged domain shift risks for raw generation. |
| [032 — reject stylized renderer pilot](032-reject-stylized-renderer-pilot.md) | Can an 88-image stylized procedural renderer pilot be used for appearance training? | Rejected for appearance training; retained strictly for geometry and invariance tests. |
| [033 — ArUco card plane & vessel fusion](033-aruco-card-plane-and-vessel-fusion.md) | Fix multi-item mask explosion, quiet-zone dropouts, and rim-plane truncation on real captures. | Approved and deployed: 23/23 admission (100%), 0 tabletop items, 29.7g primary MAE (9.42% MAPE). |
| [034 — stage promotion evaluation](034-stage-promotion-evaluation.md) | Stage-wise synthetic and augmentation promotion evaluation across all pipeline stages. | Baseline frozen; candidate weight head promotion rejected per protocol guardrails. |
| [035 — synthetic augmentation & plate study](035-synthetic-augmentation-and-plate-rel-study.md) | Provenance-audited synthetic & CutMix corpus generation, stage-wise audits, and strict two-column IEEE paper overhaul. | Corpus audited (zero leakage); paper compiled with 0 errors/warnings; production weights preserved. |
| [036 — card-free implicit scale & docker](036-card-free-implicit-scale-and-docker.md) | Card-free metric scale estimation via marker-dropout teacher-student training and production containerization. | Achieved 0.00196 cm/px (17.81% MAPE) 6-fold LODO-CV; docker compose runtime verified. |

These are synthetic mechanism diagnostics only. The weighed ArUco plates are
permanently EVAL-ONLY and are not eligible for tuning or candidate selection.
