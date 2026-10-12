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

## Chunk C1 — card-path baseline (2026-10-12, `loop-baseline`)

- **branch**: `loop-baseline` (from main @ `4f313fd`, the merged loop-setup)
- **scope**: measurement only — no model, threshold or existing test changed.

### Success criterion (prescribed by chunk C1, written before coding)

`tools/card_stress.py` runs the 9 × 31 level matrix (30 scenes/level,
seed 42) and reports per-level detection / false-accept / cm/px / tilt
stats, first level below 95% detection per group, the three weakest
conditions, and the card-path portion error distribution split by tilt
level with bootstrap CIs; a read-only pass over `../DATASET` counts
detectable cards; the tool joins the lock with exactly one new manifest
entry; gates stay green (ruff 0, pyright ≤ 216, full pytest).

### Change

- `tools/card_stress.py` — new stress suite (pinned in
  `docs/locked_manifest.txt` via the approved `check_locked --write`,
  502 → 503 files; the only other manifest changes are `check_locked.py`'s
  own self-hash and the header count).
- `docs/eval_protocol.md` — "Card path (synthetic baseline)" section +
  `tools/card_stress.py` added to the pinned eval-code list.
- `tests/test_card_stress.py` — seed determinism + false-accept guard.

### Result (data/reports/card_stress_baseline.json, 2026-10-12, 4f313fd)

Detection first below 95%: `card_distance_px` 78 → 0.00
(`min_marker_side_px` = 80), `dim_light` mild → 0.00 (quiet zone
205×0.65 = 133 < the detector's fixed 170 brightness gate),
`glare` mild → 0.867, `marker_occlusion_pct` 10 → 0.10. Card tilt
0–60°, blur σ ≤ 5, JPEG q30, resolution ≥ 0.125, plate/food state: all
1.00 at their worst level. False accepts: only occlusion 10%,
0.067 [0, 0.167] (2/30); zero everywhere else. Median cm/px error
≤ 1.3% where detected. Tilt-estimation median error ≤ 0.51° for
15–60°; 5.05° at 0° with 1/30 non-finite pose (counted as
`n_tilt_nan`, never imputed).

Portion error by card tilt (volume = the ±7% claim metric; n = 30 per
level, 2000-rep scene bootstrap):

| tilt | volume median abs [95% CI] | p90 | worst | volume signed | grams signed |
| --- | --- | --- | --- | --- | --- |
| 0° | 0.015 [0.013, 0.015] | 0.018 | 0.021 | −0.015 | −0.127 |
| 15° | 0.064 [0.040, 0.077] | 0.106 | 0.137 | +0.064 | −0.057 |
| 30° | 0.136 [0.108, 0.175] | 0.233 | 0.305 | +0.136 | +0.006 |
| 45° | 0.204 [0.146, 0.261] | 0.339 | 0.464 | +0.204 | +0.066 |
| 60° | 0.227 [0.120, 0.305] | 0.410 | 0.638 | +0.227 | +0.087 |

Grams add a ≈ −11.5% dish-density convention bias on top of the volume
error (render density 0.95 vs `rho_eff` 0.8415), which is why the grams
signed median is *smallest* at mid tilt — the two errors cancel.

Framing note (found during this chunk, recorded so it is never
"fixed" by accident): scenes aim the camera at the card with azimuth
255–275° so plate and card share depth/incidence. Card-centred azimuth
(±40°) makes the plate 15–20° more oblique than the card and produces
−45%…−61% volume error — a scale-transfer artefact of the framing, not
a property the pipeline claims to correct.

`../DATASET`: 46/46 photos contain no reference card (visually
confirmed; all return `prior`, reason "no reference card in frame") —
0 detectable, no cm/px or tilt distribution, no outliers to report.

### Decision (chunk C1)

- **keep** — baseline recorded; the ±7% claim holds through 15° tilt and
  degrades monotonically to a 22.7% median at 60°; all later card-path
  experiments compare against `data/reports/card_stress_baseline.json`.
