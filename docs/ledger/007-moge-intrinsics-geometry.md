# 007 — MoGe intrinsics for the geometry tier on real captures (DEV)

- **id**: 007
- **branch**: `spec-002-integration` (ticket `07-ingredient-compositional-method`, item 07a)
- **date**: 2026-10-29
- **author**: agent (Buffy / Codebuff)

## Hypothesis

The prior-tier geometry path on real captures is catastrophically biased: the
2026-10 historical run (`data/reports/prior_tier_wed.json`, WED TEST split)
shows per-ROI MAE **1,464 g with mean bias +1,454 g** (~10× over-prediction —
corroborated by the AGENTS.md note that uncalibrated MoGe scale is ~6× off
out-of-domain). Before any transfer method can rely on the depth→volume path,
the unprojection geometry must be sound. Diagnostic observed (this session, 4
DEV frames): MoGe-2 returns **predicted normalized intrinsics** whose pixel
focal differs from the current EXIF-fallback `camera_matrix` by up to
**1.40×** on portrait frames (`engine/depth.py` even computes and returns
intrinsics, which the caller — `tools/eval_prior_tier_on_wed.py` — ignores).
Hypothesis: unprojecting with MoGe's own predicted K (fx_px = fx_norm × W)
substantially improves the geometry-tier gram estimates on real captures,
because MoGe's metric depth is self-consistent with its predicted focal.

## Expected effect

| metric | baseline (fallback K, DEV, this entry's own run) | expected after (MoGe K) | note |
| --- | --- | --- | --- |
| geometry per-ROI MAE (g) | recorded by mode A run | paired-BETTER with CI excluding 0 | DEV 108 views / 21 plates |
| geometry per-ROI bias (g) | recorded | magnitude shrinks | the ~10× scale catastrophe should partly collapse |
| per-class worst MAE | recorded | reported per mode | diagnostic, not gated |
| failures | recorded | not worse | |

Diagnostics (recorded, not gated): a global depth-scale factor k* fitted on
DEV (ORACLE-SCALE label — fitted in-sample on the DEV labels purely to bound
where the residual error goes; never proposed for serving) with the MAE it
reaches: if k* collapses the remaining MAE, absolute scale is the dominant
defect (serving fix = any physical scale anchor); if it plateaus, shape or
density limits dominate (transfer-problem evidence for ticket 07b/07c).

## Success criterion (written BEFORE coding)

Single-variable comparison on DEV (108 views / 21 plates, identical masks,
densities from the tool's existing table, cached depths): mode B (unproject
with MoGe predicted pixel intrinsics) vs mode A (fallback camera matrix) —
per-ROI MAE paired plate-bootstrap 95% CI (seed 42, resample plates, n ≥
2000) excludes 0 in the improving direction, and mode B failures ≤ mode A
failures. No artifact used by the deployable learned path is touched
(`data/weight_head.pt`, sigma, eval-locked code untouched); this entry does
not propose a serving change by itself — it decides whether the depth-path
geometry is sound enough to build the method on.

## Result

All numbers from `data/reports/` (DEV, 108 views / 21 plates, 1,218 ROI rows
per mode, identical cached MoGe depth for both modes — only K differed):

| mode | per-ROI MAE (g) | bias (g) | failures |
| --- | --- | --- | --- |
| A — fallback camera K | 1,675.1 | +1,666.5 | 33 |
| B — MoGe predicted K | 1,524.3 | +1,513.8 | 33 |

Paired plate-bootstrap (common 1,092 ROI rows, seed 42, n=2000;
`data/reports/prior_tier_wed_dev_compare.json`): ΔMAE (B−A) + per common rows
MAE 1,411.7 → 1,245.9, **Δ = −165.5 g, 95% CI [−195.6, −137.5]** — excludes 0
in the improving direction. Failures equal (33 = 33). **Pre-registered gate 1
met: keep-eligible.**

**Oracle-scale diagnostic (`prior_tier_wed_dev_oracle_sweep_fine.json`, first
40 DEV views, 446 ROIs, mode B):** a single global depth-scale factor k*
drives the geometry MAE from 1,524 g to **65.5 g at k* ≈ 0.030** (median
43.5 g; U-shaped in k — 70.4 g at k=0.05, 1,464 g at k=0.94). At k = 1 the
path over-predicts ~34×; ~96% of the per-ROI error mass is one global
scalar. Labelled ORACLE-SCALE (fitted in-sample for bounding; never a
serving mechanism — serving has no oracle).

**Interpretation:** the MoGe-2 *shape/unprojection* path is sound (its own K
is the measured-best K and measurably better than the fallback in paired
CI) — the defect is the **absolute metric zero-point of monocular depth",
which no intrinsics change can fix. Without a physical scale reference in
frame, the pure-geometry prior tier cannot serve absolute grams. Card
calibration already exists for card frames (engine/depth.py, ~1.1% median
err on renders); WED frames have no card. Closingthe scale gap at serving decisively (learned scale/density residual, or any physical anchor) is the
transfer-method work of tickets 07b/07c.

**Gates after the change:** ruff 0; pyright 212 = baseline; hermetic suite
206 passed (exit 0); no LOCKED read (DEV only); no protected file touched
(evaluation tool is outside the eval-lock pin list).

## Decision


**keep** — the pre-registered criterion is met exactly: mode B's paired
plate-bootstrap 95% CI excludes 0 in the improving direction and failures
did not increase. The `--intrinsics moge` capability stays in the tool;
the tool's default remains `fallback` (bitwise-preserved legacy behaviour;
this entry proposes no serving change). The substantive finding this entry
records for the method design: **scale, not shape, is the dominant defect**
of RGB-only geometry on real captures, which redirects the ingredient-
compositional method to anchor-or-learn-the-scale (07b/07c) rather than
tune unprojection.

## Follow-ups

- Zero-bias crossing sits near k ≈ 0.06–0.10 while the MAE optimum is
  k ≈ 0.03 with −49 g residual bias — sign of a second, smaller area/
  density-side bias the k scalar cannot absorb; revisit after 07c's
  density table lands.
- The oracle bound (MAE 65.5 g median 43.5 g at k*) is the DIY target any
  learned scale/density residual (07b) must beat to justify itself.
- WED rig photos use a fixed multi-view capture (leftImg8bit naming);
  a rig-geometry calibration (known mount, known standoff) would be a
  physical scale source *without* a card — worth one conversation with
  whoever owns the capture rig.

## Sources

- `engine/depth.py` — MoGe-2 provider returns `intrinsics`; card calibration
  path only fires on card frames (none here: all DEV frames prior tier,
  verified this session).
- `data/reports/prior_tier_wed.json` — historical TEST-run catastrophe
  (MAE 1,464 g / bias +1,454 g) motivating this entry.
- AGENTS.md S3-depth notes — uncalibrated MoGe scale ~6× off on renders;
  card calibration to ~1.1% median error where a card exists; WED frames
  have no card (verified: `estimate_anchor` → prior on 5 sampled DEV frames).
- MoGe-2 paper https://arxiv.org/html/2507.02546v1 (predicted intrinsics;
  metric depth self-consistency).
- Ticket `07-ingredient-compositional-method` item 07a (design:
  `docs/research/general-indian-dish-method.md` §6.1).
