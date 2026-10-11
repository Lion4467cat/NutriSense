# NutriSense v5 — Final Build Report

**Date:** 2026-10-08 (updated 2026-10-11)
**Status:** S0–S6 complete — **110/110 pytest + 43/43 vitest green**, server smoke-tested, phase `built`. Frontend rebuilt (React 18 + TypeScript); post-build hardening (11 bugs + 6 candidates) landed 2026-10-10; learned weight fallback + no-card scored-with-disclaimer graduation landed 2026-10-11 (ADR 0002 + amendment).

Pipeline: photo → dish ID → portion grams → nutrients → MDM compliance verdict.

## Test results

```
110 passed
```

| Test file | Tests | Covers |
|---|---|---|
| `tests/test_geo.py` | 5 | coordinate transforms, back-projection |
| `tests/test_card.py` | 4 | reference-card detection, corner ordering |
| `tests/test_scale_anchor.py` | 7 | 2-tier anchor: card / prior (+ Exif IFD tag reading) |
| `tests/test_renderer.py` | 7 | synthetic dish renderer, handedness |
| `tests/test_s2.py` | 5 | segmenter + gallery classifier |
| `tests/test_portion.py` | 7 | S3 portion estimator (ring + prior tiers) |
| `tests/test_mc.py` | 7 | S4 Monte Carlo engine, nutrient table |
| `tests/test_compliance.py` | 10 | S5 verdicts, coverage, gate rules (+ depth factor, no-card disclaimer) |
| `tests/test_api.py` | 7 | S6 pipeline + HTTP endpoints (E2E) |
| `tests/test_config.py` | 4 | yaml loaders, ledger keys, frozen policy digest |
| `tests/test_gates.py` | 5 | zoom/day/band/scope gates |
| `tests/test_log_config.py` | 1 | pytest never writes the real app log |
| `tests/test_pipeline_seams.py` | 19 | 15 pipeline seams (lint, failures, fov_x, coverage, contracts, learned-weight head ×4) |
| `tests/test_contract.py` | 12 | 16-key result contract + whole-rule-set digest test |
| `tests/test_contract_gen.py` | 4 | generated TS schema + 3 fixture parity (analyze ×2, menu) |
| `tests/test_stage_guards.py` | 5 | per-stage failure guards (HTTP) |

## Phase delivery

### S0 — Foundation
Configs locked (`docs/protocol.md`), conversion tables (`data/conversions.yaml`), geo package, ledger (`data/params_status.yaml`). All assumed values flagged `assumed` pending physical validation.

### S1 — Scale anchor (2 tiers)
- **Tier `measured`**: 60 mm reference card detected in image → metric scale.
- **Tier `prior`**: no marker → vessel-table prior (never PASS/FAIL, coverage capped 0.60).
- Card result exposes `marker_corners_px` in extras — reused by depth calibration.
- Asset: `docs/assets/reference_card_A6_300dpi.png`.

### S2 — Segmentation + classification
- **Segmenter**: SAM2.1-hiera-large, IoU 0.98 on synthetic validation.
- **Classifier**: SigLIP2 gallery-first (46 real dish embeddings in `data/gallery.npz`), leave-one-out **46/46**; text fallback score 0.60.
- `gallery_match_threshold: 0.82` — synthetic renders score ~0.67 and correctly abstain; only real gallery photos or confident text matches proceed.

### S3 — Portion estimator (`models/portion_estimator.py`)
**Method:** `grams = anchor-scaled footprint area × mean depth height above base plane × ρ_eff`

- **Ring path (measured tier):** fit base-plane ring at 1.5% inside mask edge selecting the **largest** plane residuals (camera-z *decreases* with food height); area = `cm_px² · ((1+cos tilt)/2)² / cos tilt`.
- **Table-prior path:** dilate-based outside band, top depth quantile, lift by `base_prior_height_mm`; returns `vessel_shape_uncertain`.
- **Size prior:** de-fore shortened ellipse minor axis over assumed tilt range, scaled by `size_prior_food_diameter_mm`.

**Accuracy vs ground truth (synthetic):**

| Config | Volume error |
|---|---|
| Plate, card anchor | **+6.6%** |
| Bowl, card anchor | **+5.6%** |
| Prior tier | −17.8% (σ_rel 32%) |
| Table-prior | −21.5% (flagged uncertain) |

**3 geometry bugs found and fixed empirically:** inverted erosion band (was sampling *inside* the mask), residual-selection sign (was keeping the top surface, not the base), missing de-foreshortening factor (plain `/cos` overcounted area by 27% at 39° tilt).

### Depth — `engine/depth.py`
- **MoGe-2** (`Ruicheng/moge-2-vitl`, MIT) chosen; DA3 rejected (requires numpy<2, python≤3.13, xformers/open3d/pycolmap).
- Installed `--no-deps` + pinned `utils3d_moge` @62f09d5 (xet/HF cache gotchas noted in AGENTS.md).
- Monocular metric scale is ~6.2× off out-of-domain → **`calibrate_depth_scale`** uses card marker corners with meters on both sides → **1.1% median error** (from 519% raw). It returns `(depth, factor, source)` with source `card` or `none` — declined calibration is reported, never faked.
- The pipeline computes the horizontal field of view from the intrinsic matrix and passes it to the depth model (`fov_x`, degrees; MoGe expects degrees) — seam-tested.
- Prior tier has no card: depth scale uncalibrated, `depth_scale_sigma_pct` remains an **M6 gate**; a measured-but-uncalibrated scale multiplies coverage by `coverage_depth_uncalibrated` (0.80) so it cannot issue PASS.

### S4 — Monte Carlo engine (`engine/mc.py`, `engine/nutrients.py`)
- Portion grams sampled lognormal from `sigma_grams_rel`; recipe-share noise renormalized across dishes.
- Nutrient table entries: literature σ widened for generic dishes (`nutrient_table_sigma_pct: 4`); `temperature_scale` widens the central 90% interval only.
- Sample keys: `kcal_samples`, `protein_g_samples` (contract shared with compliance).
- Raw-equivalent kcal diagnostics are informational only — verdict uses cooked plate kcal.
- `data/nutrients.yaml` created; `data/menu.yaml` gains densities + shares (rice 0.6 / sambar 0.4, matching renderer GT).

### S5 — Compliance (`engine/compliance.py`)
- **Verdict:** PASS if P≥0.9, FAIL if P≤0.1, else BORDERLINE — same zones for every tier; no-card plates add `no_reference_card` as reasons[0] ("weight is an estimate") and pay for it in coverage (learned ×0.90, geometry ×0.60 — ADR 0002 amendment).
- **Coverage** `C` = product of ledger factors: `coverage_anchor_prior` 0.60 (geometry) / `coverage_estimated_weight` 0.90 (learned) × `coverage_base_table_prior` 0.85 × `coverage_quality_degraded` 0.90 × `coverage_depth_uncalibrated` 0.80 (when a measured anchor declined depth calibration). `base_method: learned_weight` skips the table-prior factor (the head's grams already carry model error, measured as per-class σ).
- **Gates:** FAIL requires C≥0.90 (table-prior C=0.85 blocks FAIL, still allows PASS); PASS requires C≥0.85; geometry-prior C=0.60 → never PASS/FAIL; learned-prior C=0.90 → both reachable.
- Zoom / band violations → `cannot_verify`; wheat products → `out_of_scope` (MDM scope rule).
- Salt: advisory only, never affects verdict.

### S6 — Pipeline + API (`engine/pipeline.py`, `main.py`)
- `analyze(image, day, band, exif, deps)` — `deps` injects segment/classify/depth overrides for tests.
- Endpoints: `GET /health` → `{"status":"ok","phase":"built"}`, `GET /menu`, `POST /analyze` (multipart: file, day, band, serving_style).
- Lint gates for digital zoom, day, band run before ML stages.
- E2E test exercises the real anchor → SAM → MoGe depth → portion → MC chain over HTTP.

## Post-build hardening (2026-10-10)

Architecture review → 11 outright bugs fixed + 6 deepening candidates, one
commit each (`7a9d8ea` … `79b1ea5`):

| Fix | Plain words |
|---|---|
| Exif IFD + swapped tags (bug 8) | focal/distance zoom tags were read from the wrong IFD and their constants were swapped — now read correctly; zoom reports honestly |
| Protein fallback (bug 4) | protein never double-counts via an energy-derived substitute |
| Box-path area guard (bug 10) | absurd segmentation boxes are rejected before they OOM |
| Vacuous ordering test (bug 9) | the test now asserts a real descending order |
| `AssessResult` (bug 2 / C6) | failures can no longer be dropped between `assess()` and the wire |
| Depth stage honesty (bugs 5–7 / C3) | `fov_x` reaches the depth model; calibration status feeds coverage; no fabricated `×1.0` in the UI |
| Whole-rule-set digest (bug 1 / C1) | `policy_version` hashes every rule assess() reads; a strict mutation test enforces it |
| Tri-state menu policy (bug 3 / C2) | the "earlier policy" note only speaks when today's policy is actually loaded |
| Generated-only view types (C4) | `types/api.ts` is aliases of the generated Zod; `/menu` and `/health` are decoded |
| Records selectors (C5) | one `tally()`/`attention()`/`byNewest()`; newest-first stated as the `RecordsState` invariant |

## Learned weight fallback (2026-10-11, ADR 0002 + amendment)

Prior tier (no reference card) used to mean geometry × uncalibrated depth.
Measured on the full WED test split, that path is systematically biased —
it now runs through a trained regression head instead, and no-card plates
are scored like any other with a mandatory leading disclaimer that their
weight is an estimate (user decision, graduated same day):

| Evidence | Number |
|---|---|
| Prior-tier geometry baseline, WED test, per-ROI | **MAE 1,464.5 g** (median AE 917 g, bias +1,454 g; 71 empty-mask failures) — `data/reports/prior_tier_wed.json` |
| WED-trained head, test split (248 views / 16,211 train ROIs → best val 19.73 g) | **test MAE 19.32 g** (~76× better than the prior baseline; paper's frozen-ResNet50 baseline: 14.51 g) — `data/reports/weight_head_train.json` |
| `rice_sambar` composite (steamed-rice + sambar on merged mask) | merged-union MAE **44.3 g** ≤ per-ROI-sum 45.9 g → `merge_validated: true` — same report |
| Head vs geometry on-card | head never runs when the anchor is `measured` (seam test) |

Architecture (port of the ICVGIP 2025 "Indian Thali" baseline, trained
ourselves — their checkpoint is unpublished): frozen ImageNet ResNet-50 →
roi_align 7×7 over dish masks → class-conditional gram regression (41 WED
classes). `data/wed/{train,test}` (git-ignored images), slot mapping in
`data/wed_dishes.yaml`, head-only checkpoint `data/weight_head.pt` (~4 MB),
per-class σ `data/weight_head_sigma.yaml` feeds the same MC engine.
Any failure (missing checkpoint, unmapped dish, bad mask) silently falls
back to the geometry path — measured captures are untouched.

Wire: `ReasonKind.NO_REFERENCE_CARD` leads `reasons` on every no-card
plate (*"…this photo has no measured scale, so its weight is an estimate;
the verdict is computed from estimated grams"*), `portion.grams_source` ∈
{`geometry`, `learned_weight`}, nullable `mean_h_mm`/`area_cm2` (no depth
aux on the learned path), optional `head_slots`, new policy factor
`estimated_weight` = 0.90 (PASS and FAIL reachable) while geometry grams
keep the 0.60 cap. `Verdict` still carries `ESTIMATED` as a legacy value
for old records — nothing emits it. Frontend: prior-tier warning banner,
`no_reference_card` reason, Menu/Coverage copy, History filter retained.
Digest **moved**: `8e75c97be3e0` → **`7d3431caec4b`** (graduation commit;
ADR 0002 amendment records the decision).

## Assumptions pending physical validation (M-gates)

| Item | Value | Gate |
|---|---|---|
| Densities | rice 0.75, sambar 1.03, veg-rice 0.85, BBB 0.90 g/cm³ | M1 |
| Dish shares | rice 0.6 / sambar 0.4 | M1 |
| Generic nutrient entries | sambar 60/2.5, veg-rice 150/3.5, BBB 185/5.0 | M4 |
| `nutrient_table_sigma_pct` | 4 (literature-derived) | M4 |
| Prior-tier geometry | base σ 4.5/6.0 mm, height 8.0 mm, diameter 170 mm, tilt 30° | M2 |
| Depth scale (uncalibrated tier) | `depth_scale_sigma_pct` | M6 |
| Learned weight per-class σ | `data/weight_head_sigma.yaml` (carved WED val split; fallback rel σ 0.30) | graduated 2026-10-11; 10-plate spot-check (M1) tunes `coverage_estimated_weight` |

## Remaining work (per plan)

- **M1** — physical reference-card run against kitchen scale.
- **M2** — prior-tier calibration on real dishes without markers.
- **M3** — real-world abstain-threshold tuning (0.82 vs field photos).
- **M4** — nutrient table validation.
- **M5** — compliance pilot with real MDM day bands.
- **M6** — depth-scale σ validation for the prior tier.
- **P5** — *(graduated early 2026-10-11 with disclaimer — see ADR 0002 amendment)* follow-up: run the ~10-plate local spot-check and tune `coverage_estimated_weight` (0.90 today) to the measured local error.
- Frontend: rebuilt (React 18 + TypeScript, hash router, localStorage history/students, 6 themes × 6 palettes) — see README screenshots.

## Environment notes

- uv-managed `.venv/` (CPython 3.14); torch 2.13.0+cu130, transformers 5.16.1, fastapi 0.142.2, numpy 2.5.3.
- HF downloads require `HF_HUB_DISABLE_XET=1` (xet backend stalls).
- Full gotcha list lives in `AGENTS.md`.
