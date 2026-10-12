# 000 — Baseline: eval harness, lock, and stress suite (chunk A)

- **id**: 000
- **branch**: `loop-setup` (commits `884b2bd`, `a371253`, `3d25a43`)
- **date**: 2026-10-12
- **author**: agent (loop-setup chunk A)

## Hypothesis

Before any idea is tried, the evaluation must be (a) reproducible, (b)
honest about its own limits, and (c) protected from post-hoc tampering. A
harness that records the deployable path (frozen encoder in `eval()`,
head-only checkpoint), plate-bootstrap CIs, stress deltas, and a hash lock
over the eval code + split + test images gives every later experiment a
number it can be judged by.

## Expected effect

No metric moves — this chunk changes no model code. Expected artefacts: a
DEV number with a CI, a stress profile, a lock that fails when tampered
with, and a locked-tier path that can only be taken deliberately.

## Success criterion (written BEFORE coding)

`tools/run_eval --tier dev` completes on the deployable path and reports
MAE with a 95% CI; `tools/stress_suite` reproduces the STAGE 1B
perturbations bit-for-bit; `tools/check_locked` exits 1 on a changed,
missing, or unpinned in-scope file and 0 on the pristine repo; the locked
tier refuses to run without `--i-know-this-is-locked` and appends exactly
one access-log line per run.

## Change

- `tools/run_eval.py` — DEV / TRAIN / LOCKED tiers on the deployable path
  (`WedPlates` → frozen encoder → ROI head), per-class σ from
  `data/weight_head_sigma.yaml`, plate-level bootstrap 95% CIs, `--stress`
  gated to DEV, `--limit` recorded in the report, locked tier gated and
  access-logged; chunk B adds per-plate aggregates + `wall_s` /
  `peak_vram_mb` to every report.
- `tools/stress_suite.py` — frozen copy of the STAGE 1B perturbations from
  `tools/bn_experiment.py` (brightness/contrast, blur, perspective, JPEG,
  half-resolution), labelled `WED stress test, not real-world`.
- `tools/check_locked.py` + `docs/locked_manifest.txt` — SHA-256 lock over
  the eval code, the split definition, and every `data/wed/test/` image;
  `data/wed/test/` also chmod'd read-only.
- `tests/test_locked_eval.py` — guards for all of the above.
- `docs/eval_protocol.md` — the protocol itself.

## Sources

- `docs/final-report.md` — WED splits (train 1146 / val 108 / test 248
  views), deployable val MAE 20.30 g, paper baseline 14.51 g.
- `tools/bn_experiment.py` — the perturbations frozen into
  `tools/stress_suite.py`.
- `docs/known_issues.md` — BN train/eval mismatch that makes
  in-process numbers non-deployable.

## Result

Baseline numbers every later entry compares against (all from
`loop-setup` @ `3d25a43`, seed 42, deployable path, 2026-10-12):

| tier | views | MAE (g) | 95% CI | coverage_90 | 95% CI | MAPE % | skipped (no σ) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DEV (val carve) | 108 / 21 plates | **20.298** | [17.247, 24.295] | **0.8645** | [0.812, 0.907] | 24.14 | 0 |
| TRAIN (in-sample) | 1146 | 13.382 | [12.609, 14.200] | 0.9298 | — | 17.39 | 335 |

Mean 90% interval width on DEV: 82.06 g. TRAIN MAPE excludes 5 ROIs with
zero GT. LOCKED never run.

DEV stress profile (same plates, paired, label
`WED stress test, not real-world`):

| perturbation | MAE (g) | Δ vs clean |
| --- | --- | --- |
| clean | 20.298 | — |
| brightness_contrast_0.7 | 21.034 | +0.74 |
| gaussian_blur_k9 | 20.929 | +0.63 |
| perspective_30deg | 25.933 | +5.64 |
| jpeg_q30 | 20.470 | +0.17 |
| half_resolution | 20.550 | +0.25 |

Gates at baseline: ruff 0 · pyright 216/216 (`pyright.baseline`) ·
144 pytest (135 non-gpu + 9 gpu) · 43 vitest · CI run `38235913138` green
on `loop-setup`. Chunk B adds 15 tests (`test_locked_eval` +3,
`test_compare_runs` ×12) → **159 pytest (150 non-gpu + 9 gpu)**, gates
re-run green.

Chunk B (same branch) re-scopes the lock to eval code + split + locked
images only — `models/weight_head.py`, `tools/train_weight_head.py`, and
`data/weight_head_sigma.yaml` are deliberately unpinned so a re-pin of the
*evaluation* can never silently cover a change to the *model being
evaluated* — and adds `tools/compare_runs.py` (paired plate bootstrap),
`tools/log_run.py` + gitignored `runs/experiments.jsonl`,
`tools/should_stop.py`, and this ledger.

## Decision

- **keep** — the harness is the precondition for every later decision; the
  DEV/CI/stress numbers above are the reference point for all entries ≥
  001.

## Follow-ups

- First real experiment (entry 001) must baseline-compare against
  `data/reports/run_eval_dev.json` with `tools/compare_runs.py`.
- Consider tightening interval width (82 g mean on a ~20 g MAE) without
  losing coverage — separate entry, DEV only.
