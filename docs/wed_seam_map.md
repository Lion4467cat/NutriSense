# The WED dataset seam map (swap points)

Decision record: WED is the **backup** dataset — the real dataset has not
arrived yet (grill round-1, Q2). To make the future swap cheap, the seams the
real dataset has to flow through are enumerated here; the code behind each
seam stays as-is until the real shape is known (grill Q15: light investment,
no speculative refactor).

## What actually touches WED today

| Seam point | Where | What the real dataset swap touches |
| --- | --- | --- |
| Split definition + row schema | `data/wed_manifest.jsonl`, built by `tools/build_wed_manifest.py` (train 1146 / val 108 / test 248 views, 267 plates, seed 42; fields: `date_key`, `set`, `split`, `image`, `mask`, `dishes[].{class_id,weight_g}`) | Rebuild the manifest for the new capture set; plate-key + row schema may change shape — the loaders below are the only readers |
| Manifest readers | `load_manifest(split)` in `tools/train_weight_head.py`; `tools/run_eval.py` (same source of split); `tools/stress_suite.py` (frozen perturbation hooks) | Row-shape changes ripple here first — keep the row's essential contract (`image`, `mask`, class ids, grams) as the seam interface |
| Dataset class | `WedPlates` in `tools/train_weight_head.py` (multi-view image + per-dish ROIs, hflip-only baseline augmentation; ledger 001 adds train-only photometric block) | New capture geometry (view layout, masks) lands here; the eval path shares the deployable model class, not the dataset |
| Model inputs | `models/weight_head.py` (deployed frozen DINOv2-S/14 encoder; optional ResNet-50 comparison path; ROI-align → class-conditional regression; `RESIZE`, ROI coords); `models/registry.py` (class id ↔ menu dish mapping) | Class vocabulary changes with the real menu; `models/registry.py` + `data/wed_dishes.yaml` are the mapping seam (use `config.load_wed_index()`, never the raw id map) |
| Training entry | `tools/train_weight_head.py` CLI (`--out data/weight_head.pt`, `--sigma-out data/weight_head_sigma.yaml`) | Unchanged mechanically; the per-class sigma file is a data seam feeding `engine/mc.py` intervals |
| Eval tiers | `tools/run_eval.py` (DEV = the only tuning tier), `tools/compare_runs.py` (paired plate bootstrap), `docs/locked_manifest.txt` (pins eval code + `data/wed/test/`) | A new dataset means a NEW lock + a re-pin (`tools.check_locked --write`, approved) — the lock itself is the swap gate |
| Gallery (open-set classification) | `tools/build_gallery.py --source ../DATASET` → `data/gallery.npz`; `models/food_classifier.py`; abstain knob `gallery_match_threshold` in `data/params_status.yaml` | The real capture set replaces the gallery source; the class-dir → menu-dish alias mapping in `scan_source` is the acceptance seam |
| Physics/vector calibration | `data/params_status.yaml` (coverage caps, thresholds), `data/menu.yaml` + `data/standards.yaml` (dish names and standards — never hardcoded), `data/nutrients.yaml`, `config.py` (`MENU_PATH`, `_CACHE` loaders) | Content refresh via yaml, no code change — this is the seam that made the contract swap cheap in the v5 rebuild |
| Frontend contract | `engine/contract.py` → `tools/gen_contract_ts.py` → `frontend/src/types/contract.gen.ts` | If the real dataset adds fields (e.g. richer provenance), regenerate here; pages + Zod decode pick it up automatically |

## Rules for the swap (written now, cheap to follow)

1. The manifest row contract — image + mask + per-dish class/grams — is the
   load-bearing interface; if the real dataset changes it, adapt in
   `load_manifest`/`WedPlates` only.
2. Class id vocab is owned by `models/registry.py` + `data/wed_dishes.yaml`;
   never hardcode dish names in code (repo rule since S0).
3. New dataset ⇒ new eval lock: run `tools/build_wed_manifest`, then
   `tools.check_locked --write` (approved-only), then a fresh entry-000-style
   baseline in the ledger before any tuning.
4. Everything above the seam (contract, compliance scoring, MC, UI) should
   not know the dataset changed. If the swap requires edits outside the
   table above, that is a seam violation — fix at the seam instead.
