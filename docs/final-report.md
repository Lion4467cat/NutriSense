# NutriSense v5 — Final Build Report

**Date:** 2026-10-08 (updated 2026-10-10)
**Status:** S0–S6 complete — **88/88 tests green (isolated run)**, server smoke-tested, phase `built`. Frontend rebuilt (React 18 + TypeScript).

Pipeline: photo → dish ID → portion grams → nutrients → MDM compliance verdict.

## Test results

```
88 passed
```

| Test file | Tests | Covers |
|---|---|---|
| `tests/test_geo.py` | 5 | coordinate transforms, back-projection |
| `tests/test_card.py` | 4 | reference-card detection, corner ordering |
| `tests/test_scale_anchor.py` | 6 | 2-tier anchor: card / prior |
| `tests/test_renderer.py` | 7 | synthetic dish renderer, handedness |
| `tests/test_s2.py` | 5 | segmenter + gallery classifier |
| `tests/test_portion.py` | 7 | S3 portion estimator (ring + prior tiers) |
| `tests/test_mc.py` | 7 | S4 Monte Carlo engine, nutrient table |
| `tests/test_compliance.py` | 9 | S5 verdicts, coverage, gate rules |
| `tests/test_api.py` | 7 | S6 pipeline + HTTP endpoints (E2E) |
| `tests/test_pipeline_seams.py` | 12 | 8 pipeline seams (lint, failures, contracts) |
| `tests/test_contract.py` | 11 | single 16-key result contract |
| `tests/test_contract_gen.py` | 3 | generated TS schema + fixture parity |
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
- Monocular metric scale is ~6.2× off out-of-domain → **`calibrate_depth_scale`** uses card marker corners with meters on both sides → **1.1% median error** (from 519% raw).
- Prior tier has no card: depth scale uncalibrated, `depth_scale_sigma_pct` remains an **M6 gate**.

### S4 — Monte Carlo engine (`engine/mc.py`, `engine/nutrients.py`)
- Portion grams sampled lognormal from `sigma_grams_rel`; recipe-share noise renormalized across dishes.
- Nutrient table entries: literature σ widened for generic dishes (`nutrient_table_sigma_pct: 4`); `temperature_scale` widens the central 90% interval only.
- Sample keys: `kcal_samples`, `protein_g_samples` (contract shared with compliance).
- Raw-equivalent kcal diagnostics are informational only — verdict uses cooked plate kcal.
- `data/nutrients.yaml` created; `data/menu.yaml` gains densities + shares (rice 0.6 / sambar 0.4, matching renderer GT).

### S5 — Compliance (`engine/compliance.py`)
- **Verdict:** PASS if P≥0.9, FAIL if P≤0.1, else BORDERLINE.
- **Coverage** `C` = product of ledger factors: `coverage_anchor_prior` 0.60 × `coverage_base_table_prior` 0.85 × `coverage_quality_degraded` 0.90.
- **Gates:** FAIL requires C≥0.90 (table-prior C=0.85 blocks FAIL, still allows PASS); PASS requires C≥0.85; prior tier caps C at 0.60 → never PASS/FAIL.
- Zoom / band violations → `cannot_verify`; wheat products → `out_of_scope` (MDM scope rule).
- Salt: advisory only, never affects verdict.

### S6 — Pipeline + API (`engine/pipeline.py`, `main.py`)
- `analyze(image, day, band, exif, deps)` — `deps` injects segment/classify/depth overrides for tests.
- Endpoints: `GET /health` → `{"status":"ok","phase":"built"}`, `GET /menu`, `POST /analyze` (multipart: file, day, band, serving_style).
- Lint gates for digital zoom, day, band run before ML stages.
- E2E test exercises the real anchor → SAM → MoGe depth → portion → MC chain over HTTP.

## Assumptions pending physical validation (M-gates)

| Item | Value | Gate |
|---|---|---|
| Densities | rice 0.75, sambar 1.03, veg-rice 0.85, BBB 0.90 g/cm³ | M1 |
| Dish shares | rice 0.6 / sambar 0.4 | M1 |
| Generic nutrient entries | sambar 60/2.5, veg-rice 150/3.5, BBB 185/5.0 | M4 |
| `nutrient_table_sigma_pct` | 4 (literature-derived) | M4 |
| Prior-tier geometry | base σ 4.5/6.0 mm, height 8.0 mm, diameter 170 mm, tilt 30° | M2 |
| Depth scale (uncalibrated tier) | `depth_scale_sigma_pct` | M6 |

## Remaining work (per plan)

- **M1** — physical reference-card run against kitchen scale.
- **M2** — prior-tier calibration on real dishes without markers.
- **M3** — real-world abstain-threshold tuning (0.82 vs field photos).
- **M4** — nutrient table validation.
- **M5** — compliance pilot with real MDM day bands.
- **M6** — depth-scale σ validation for the prior tier.
- Frontend: rebuilt (React 18 + TypeScript, hash router, localStorage history/students, 6 themes × 6 palettes) — see README screenshots.

## Environment notes

- uv-managed `.venv/` (CPython 3.14); torch 2.13.0+cu130, transformers 5.16.1, fastapi 0.142.2, numpy 2.5.3.
- HF downloads require `HF_HUB_DISABLE_XET=1` (xet backend stalls).
- Full gotcha list lives in `AGENTS.md`.
