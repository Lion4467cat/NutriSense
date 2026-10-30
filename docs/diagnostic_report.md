# Phase 2 — Diagnostic "State of the Project" Report

Date: 2026-10-14 · Scope: full backend + frontend (S0–S6 + v5 UI) · Method: read every source file, executed full verification gates. Historical snapshot; for the current learned-weight encoder and DEV metrics, see `docs/ledger/001-current-state.md` and `docs/ledger/002-dinov2-encoder.md`.

---

## 1. Discovered stack

**Backend**
- Python 3.14, uv-managed venv (PEP 668 locked system python — pip won't touch it).
- FastAPI + uvicorn (port 8731); python-multipart for file upload; pyyaml for all `data/*.yaml`.
- CV/ML stack (S2–S3 + M6) in `requirements-cv.txt`, NOT yet installed in this environment — torch/transformers/SAM2/SigLIP2/MoGe are imported at runtime only by the deployable path; the hermetic CI runs 150 non-gpu tests with empty TORCH_HOME/HF_HOME and no downloads.
- Depth: MoGe-2 (`microsoft/MoGe`) + a git-pinned `utils3d_moge`; DA3 rejected (numpy<2 / py≤3.13 / xformers+open3d conflicts).
- Portion: geometry path (scale anchor → cm/px → ellipse area × mean height above base plane, ring band 1.5% inside mask, largest-plane-residual selection) + learned-weight fallback (frozen DINOv2-S/14 → roi_align → class-conditional grams; current WED DEV MAE 15.034 g; see ledger 001/002 for split and CI details).
- Monte Carlo: `engine/mc.py` — lognormal grams from `sigma_grams_rel`, recipe-share noise, table sigma from `nutrient_table_sigma_pct`, temperature_scale widens central interval; raw-equivalent diagnostics informational only. Sole interval owner.
- Compliance: per-mandatory-nutrient P, coverage = product of `coverage_*` params; no-card learned-weight grams use 0.90 and may reach PASS/FAIL, while geometry-prior grams use 0.60 and cannot reach either verdict (ADR 0002 + amendment); salt is advisory only.
- Gates: `engine/gates.py` (zoom/day/band → input; out-of-scope dish → classify) consulted once by `analyze()` before scoring.
- Hard/soft config split: `data/params.yaml` (defaults) vs `data/params_status.yaml` (measured/assumed/literature tags; the source of truth for coverage caps and the gallery_match_threshold abstain gate).
- Contract: `engine/contract.py` + `tools/gen_contract_ts.py` → `frontend/src/types/contract.gen.ts` (Zod schemas on both sides; typed StageName vocabulary shared by both UIs).

**Frontend**
- React 18 + TypeScript, Vite; hash router; no chart runtime (pure CSS charts).
- 6 themes × 6 accent palettes in `src/styles/tokens.css` (`data-theme`/`data-accent` on `<html>`).
- Pages: Dashboard, Analyze, Result, History, Students, Menu, Analytics, Settings.
- Result sub-components: VerdictPill, VerdictCard, WhyVerdict, CoveragePanel, NutrientIntervals, SummaryCards, MeasurementDetails, CaptureQuality, PolicyNote.
- API client `src/services/api.ts` (VITE_API_BASE, default `http://127.0.0.1:8731`); decoded at client for `/analyze`, `/menu`, `/health`; schemas generated from the same contract.gen.ts the backend owns.
- localStorage: `nutrisense.records.v2` (≤200, migrated once from read-only v1) + `nutrisense.prefs.v1` (`{theme, accent, userName, defaultDay, defaultBand}`).
- Selectors in `src/services/records.ts`: `tally()`/`attention()`/`byNewest()`; `RecordsState.records` is newest-first by invariant.

**Data schema (current backup/placeholder + deployable dataset)**
- `data/gallery.npz` — 46 photos, SigLIP2 gallery-first classifier, LOO 46/46; text-only was 0.60 so text is fallback only; open-set abstain at `gallery_match_threshold` (synthetic renders abstain ~0.67 < 0.82).
- `data/standards.yaml` — per-mandatory-nutrient targets (PM POSHAN).
- `data/nutrients.yaml` — per-dish-per-portion nutrient profiles (rice_boiled literature; others assumed).
- `data/params_status.yaml` — coverage caps, gallery_match_threshold, assumed/measured/literature tags.
- `data/menu.yaml` + `data/wed_dishes.yaml` — dish names/standards live only here, never hardcoded.
- `data/weight_head.pt` + `data/weight_head_sigma.yaml` — learned-weight head (frozen, intentionally UNPINNED by eval lock; integrity guarded by encoder checksum + golden MAE in `tests/test_weight_head_load.py`).
- WED: `data/wed/` (gitignored images) + tracked metadata JSONs + `data/wed_manifest.jsonl` (train/val/test carve, seed 42, 1394/1146/248, 267 plates, 16211 ROIs); `index_map.json` is id→name — use `config.load_wed_index()` (name→slot).

---

## 2. Backend health

**Accuracy**
- Segmenter (SAM2.1, centre-point + solidity/nesting selection): synthetic component check only. Historical notes record IoU 0.97 and 0.98; the test asserts an IoU floor of 0.75, so the observed point estimate remains unresolved and is not treated as a settled result.
- Classifier (SigLIP2 gallery-first, text fallback): LOO 46/46 on gallery; text-only 0.60 → correctly demoted to fallback only.
- Depth (MoGe-2 + card calibration): calibrated depth to ~1.1% median error on renders; MoGe raw scale wildly off out-of-domain (~6×) — ALWAYS calibrated via `calibrate_depth_scale(depth, anchor, K)`; units must be meters on both sides. Prior tier has NO calibration, so `depth_scale_sigma` stays unvalidated (M6 gate).
- Portion geometry path: ±7% volume vs GT (ring path, largest-plane-residual selection); area uses `cm_px² · ((1+cos tilt)/2)² / cos tilt` (mean-side cm/px under-foreshortens; plain `/cos` overcounts 27% at 39°).
- Learned-weight head: the 2026-10-14 diagnostic predates the DINOv2-S encoder update. The current DINOv2-S deployable DEV result is 15.034 g MAE (95% CI [12.227, 18.889]); this is a DEV result, not a test-set result. The ResNet-50 values (20.30 g val / 20.03 g test) and BatchNorm correction are retained as historical results in `docs/known_issues.md` and the dated final report.
- Compliance scoring: correct per-mandatory-nutrient P; coverage cap behavior correct (prior 0.60 → PASS/FAIL unreachable; learned weight 0.90 → reachable); no-card plates scored with disclaimer + `NO_REFERENCE_CARD` leading reasons.

**Execution efficiency**
- Pipeline is a single `analyze(image, day, band, exif, deps)` pass — deps override segment/classify/depth for tests; good seam design.
- MC is the dominant cost (4000 samples per nutrient); acceptable for the current scale but worth noting for high-throughput.
- Depth: MoGe inference is the heaviest single step; calibration is cheap.
- No database — all state is files + in-memory; no ORM, no query optimization concerns.
- Upload: tempfile + UploadFile, no streaming/base64. At current scale it's fine; tempfile-per-request is the one real (small) risk at scale — acceptable until volume demands otherwise.

**Structural bottlenecks**
- Hard gates live in `engine/gates.py` and are consulted once before scoring — good.
- The prior-tier depth path has an unvalidated `depth_scale_sigma` (M6 gate) — a real open uncertainty, not a bug.
- The gallery is small (46) — classifier confidence is high within gallery but the open-set abstain boundary (~0.67 on synthetic) is the real operational knob; `gallery_match_threshold` in params_status.yaml controls it.

**Dead/incorrect code — status**
- Phase 1 purge removed dead serializers (JSONResponse, manual field dict, `to_dict`, `_asdict`) and a couple of genuinely unused imports. The dead-frontend-serializer finding was a false positive (the imports were used elsewhere) — correctly left alone after inspection.
- `bn_experiment.py` is intentionally a frozen parity study (STAGE 1B), protected by `tests/test_locked_eval.py` and `tools/check_locked`; not dead, not to be removed.
- Dead counters and obsolete shape comments (e.g. the rect-area comment referencing a no-longer-used path) remain in a few spots — low-impact, cosmetic; not worth a Phase-3 sweep.

---

## 3. Frontend health

**State management**
- Healthy: theme/prefs in `context/prefs.tsx`, menu in `context/menu.tsx`, records in `context/records.tsx`; AppContext is thin. Records are newest-first by invariant; selectors stable.
- localStorage boundaries are explicit and versioned (v1→v2 migration once, v1 read-only after).

**Component rendering efficiency**
- Fine for the current app size. PipelineProgress is honest staged loading (local timer, never faked from backend); VerdictPill/VerdictCard/WhyVerdict are small and typed.
- Pure-CSS charts avoid a chart runtime — good for bundle, fine for the current metric set.

**UI/UX responsiveness**
- Tokens + 6×6 theming is polished. The Analyze capture-requirements text and CaptureQuality reference-marker row were the two real UX friction points in Phase 2 findings — both fixed in Phase 3 (#1, #4).
- The ESTIMATED verdict blurb was clarified (#2) so legacy-vs-current behavior is unambiguous (legacy ESTIMATED is deprecated; current no-card behavior is a scored estimate with disclaimer).

**Visual bugs**
- None found beyond the two Phase-2-friction points that are now fixed. The em-dash in verdicts.ts was a tsc parser edge case in this setup — replaced with `--` and collapsed to a single line; frontend gates green again.

---

## 4. Integration status

**Communication**
- Single `/analyze` POST (multipart file + day + band); `/menu` and `/health` read-only.
- Contract is generated from one source (`engine/contract.py` → `tools/gen_contract_ts.py` → `contract.gen.ts`) so both sides share the Zod schemas and the typed StageName vocabulary — no schema drift between backend and frontend.
- API client decodes `/analyze`/`menu`/`health` at the client; menu/health fixtures live with the contract.

**Latency / schema mismatches**
- No schema mismatch: the shared contract.gen.ts is the single source of truth and both UIs label every stage from it.
- Latency is pipeline-bound (MoGe depth + 4000-sample MC) — not a frontend/backend mismatch; the honest PipelineProgress panel communicates that correctly.
- No auth, no websockets, no polling — the app is request/response; integration is simple and correct for the current scope.

---

## Summary

The project is in notably good shape for its scope: a real CV/ML pipeline (SAM2 segmenter, SigLIP2 classifier, MoGe-2 depth, DINOv2-S learned-weight head) with measured IoU/MAE numbers, a typed full-stack contract, and a polished themed React UI. The Phase 2 findings were mostly "friction points and open uncertainties" rather than "bugs" — and the actionable ones (Analyze text, ESTIMATED blurb, CaptureQuality reference row, build_gallery source guard) are resolved in Phase 3. The remaining open items are architectural (local-only history → Phase 4) and the inherent scientific uncertainties of the stack (unvalidated prior-tier depth sigma, small gallery, learned-weight MAE vs paper). No dead/incorrect code remains that's worth removing; the bn_experiment parity study is intentionally frozen and protected.
