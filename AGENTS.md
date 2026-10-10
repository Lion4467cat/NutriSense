# NutriSense — agent instructions

## Package management: uv only
- Always use `uv`, never `pip`.
- Env: `.venv/` (uv-managed, CPython 3.14) at repo root.
- Create: `uv venv --python 3.14 .venv`
- Install: `uv pip install --python .venv/bin/python <pkg>`
- Run API: `.venv/bin/uvicorn main:app`
- System python is PEP 668 locked; `pip install` will fail — do not use `--break-system-packages`.

## Project state
- Baseline cleanup done (old pipeline removed).
- **S0 + S1 done**: geo package, configs (`data/*.yaml`), reference card tool, 2-tier scale anchor (card → prior; no coin), synthetic tests.
- **S0 renderer done**: `tests/synth/` full scene render (image/depth/obj_ids/comp_ids/grams GT/anchor GT). Card placement is face-up with texture-down → −Y (aruco chirality; do not flip `_world_from_local` back).
- **S2 done**: `models/dish_segmenter.py` (SAM2.1, centre-point + solidity/nesting selection — IoU 0.98 on synthetic), `models/food_classifier.py` (SigLIP2 gallery-first, text fallback), `tools/build_gallery.py` → `data/gallery.npz` (46 photos, LOO 46/46; text-only was 0.60 so text is fallback only). Open-set abstain via `gallery_match_threshold` in `params_status.yaml` (synthetic renders abstain at ~0.67 < 0.82).
- **S3 done**: `models/portion_estimator.py` — grams = anchor-scaled footprint area × mean depth height above base plane. Ring path (band 1.5% inside mask, **select LARGEST plane residuals** — camera-z decreases with height, low-residual picks the top) → ±7% volume vs GT. Table-prior path flagged `vessel_shape_uncertain`. Prior anchor tier: size prior on ellipse minor axis **de-foreshortened by assumed tilt**. Area uses `cm_px² · ((1+cos tilt)/2)² / cos tilt` (mean-side cm/px under-foreshortens — plain `/cos` overcounts 27% at 39°). Returns `sigma_rel` dict only — intervals belong to S4.
- **S3 depth**: `engine/depth.py` — MoGe-2 (`microsoft/MoGe` installed `--no-deps` + `utils3d_moge` git pin + scipy/click/tqdm/trimesh/matplotlib; DA3 was rejected: needs numpy<2, py≤3.13, xformers/open3d). `MonocularDepth` (RGB float input, `apply_mask=False`, pass `fov_x` when known). **MoGe scale is wildly off out-of-domain (~6× on renders) — ALWAYS calibrate with `calibrate_depth_scale(depth, anchor, K)`** (card 60mm edges; units must be **meters** on both sides); card calibration gets depth to ~1.1% median error. Prior tier: no calibration — depth_scale_sigma stays unvalidated (M6 gate).
- **S4 done**: `engine/mc.py` (sole interval owner: lognormal grams from `sigma_grams_rel`, recipe-share noise, table sigma from `nutrient_table_sigma_pct`, temperature_scale widens central interval, raw-equivalent diagnostics informational only) + `engine/nutrients.py` (`data/nutrients.yaml`: rice_boiled literature, others assumed).
- **S5 done**: `engine/compliance.py` — P per mandatory nutrient, coverage = product of `coverage_*` params (prior anchor 0.60 caps out PASS/FAIL), PASS ≥0.9 & C≥0.85 / FAIL ≤0.1 & C≥0.90 / else BORDERLINE, salt advisory only. Hard gates (zoom/day/band → input, out-of-scope dish → classify) live in `engine/gates.py`, consulted once by `analyze()` before assess() scores.
- **S6 done**: `engine/pipeline.py` (`analyze(image, day, band, exif, deps)` — deps override segment/classify/depth for tests) + `main.py` `/health` `/menu` `/analyze` (multipart file+day+band). All S6 gates tested.
- **Frontend rebuilt for v5 (React 18 + TypeScript)**: `frontend/src/` — hash router (`src/App.tsx`), pages in `src/pages/` (Dashboard, Analyze, Result, History, Students, Menu, Analytics, Settings), result views in `src/result/`, design tokens + 6 themes × 6 accent palettes in `src/styles/tokens.css` (`data-theme` / `data-accent` on `<html>`). API client `src/services/api.ts` (`VITE_API_BASE`, default `http://127.0.0.1:8731`); localStorage: `nutrisense.records.v2` (≤200, migrated once from read-only `nutrisense.records.v1`) + `nutrisense.prefs.v1` (`{theme, accent, userName, defaultDay, defaultBand}`). Charts are pure CSS (no chart runtime). View types are z.infer aliases of the generated Zod schemas (`types/api.ts` is aliases only; `/analyze` `/menu` `/health` are decoded at the client — menuSchema/healthSchema live in contract.gen.ts with a Python-side menu fixture). Records selectors `tally()`/`attention()`/`byNewest()` live in `services/records.ts`; `RecordsState.records` is newest-first by invariant. Verify with `npx tsc --noEmit && npm run build` from `frontend/`. Playwright-core is deliberately NOT in package.json — any `npm i`/`npm uninstall` prunes it; restore with `npm i --no-save playwright-core` and keep ESM screenshot scripts outside the repo (import `/home/tinkerer/Desktop/Nutrisense/NutriSense-main/frontend/node_modules/playwright-core/index.mjs` by absolute path). `node_modules` was Windows-installed — linux needs `npm i @rollup/rollup-linux-x64-gnu --no-save` (re-check after any npm operation) + `chmod +x node_modules/.bin/*`.
- **Full suite: 104 pytest + 43 vitest green** — includes `tests/test_pipeline_seams.py` (8 confirmed pipeline seams: lint note, segment/portion failure branches, classify-unrecognized, depth-scale wiring measured/prior, result contract incl. `compliance` pass-through, HTTP contract) + `tests/test_log_config.py` (pytest never writes the real `logs/nutrisense.log`).
- TDD test report + validated mermaid pipeline flowchart: `docs/pipeline-test-report.md`.
- Build order complete: S0→S6.
- Dish names/standards live only in `data/menu.yaml` + `data/standards.yaml`; never hardcode dish names in code.
- Unmeasured parameters must be marked `assumed` in `data/params_status.yaml`.

## Common commands
- Tests: `.venv/bin/pytest -q` (pytest.ini sets pythonpath; S2/S6 tests need the GPU + cached HF weights)
- API: `.venv/bin/uvicorn main:app --port 8731`
- Reference card: `.venv/bin/python -m tools.make_reference_card`
- Gallery: `.venv/bin/python -m tools.build_gallery --source ../DATASET --out data/gallery.npz`
- HF downloads: prefix with `HF_HUB_DISABLE_XET=1` — the xet backend stalls indefinitely in this environment.
- CV stack installed (torch 2.13 cu130 + transformers 5.16.1 + sentencepiece + moge + httpx): `requirements-cv.txt`.
- OpenCV 5 gotchas: `generateImageMarker` (not generateMarker); `getPerspectiveTransform` needs float32; numpy≥2 has no 2-D `np.cross`.
- Transformers 5 gotchas: load SigLIP2 with `AutoModel` (its config is `model_type: siglip`; `Siglip2Model.from_pretrained` fails shape checks); SigLIP logits = `cos·exp(logit_scale)+logit_bias` (model params); SAM2 points need 4-dim `[image, object, point, xy]` nesting, boxes 3-dim; SAM2 masks come back at 256×256 — resize logits to full res.
- Depth gotchas: install MoGe with `--no-deps` (its pyproject drags gradio/flex-gemm); calibration compares must be meters; `unit_interval`/`interval_90` MC summary key; mc sample key is `protein_g_samples` (matches standards nutrient key).
