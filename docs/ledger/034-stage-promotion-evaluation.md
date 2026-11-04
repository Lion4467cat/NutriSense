# 034 — Stage-Wise Synthetic & Augmentation Promotion Evaluation

- **id**: 034
- **branch**: `009-synthetic-training-data`
- **date**: 2026-11-04
- **status**: completed; baseline frozen, candidate weight promotion rejected per protocol guardrails

## Objective

Evaluate synthetic appearance, domain-randomized ISP lighting, and augmented training candidates across all five pipeline stages according to the preregistered protocol (`docs/ledger/028-synthetic-food-data.md`, `specs/009-synthetic-training-data/spec.md`, and `docs/ledger/032-reject-stylized-renderer-pilot.md`).

Enforce the strict stage promotion order:
$$\text{Classification} \longrightarrow \text{Segmentation} \longrightarrow \text{Depth / Geometry} \longrightarrow \text{Weight Estimation} \longrightarrow \text{End-to-End Pipeline}$$

## Stage Evaluation & Promotion Gates

### 1. Stage 1 — Classification (SigLIP-2 + Gallery + Chromaticity Gates)
- **Baseline**: 81.03% top-1 accuracy / 82.12% macro recall on WED DEV (1,218 annotated crops / 21 plate groups).
- **Decoy Rejection Guardrail**: Zero false `papad`, `salad`, `chutney`, or `curd` secondary item hallucinations on real physical plates (`Dish 1` through `Dish 6`).
- **Result**:
  - Secondary vessel chromaticity gating and sub-threshold re-ranking floor ($\ge 0.82$ for secondary liquid bowls) cleanly resolved the sambar katori on `Dish 1` and `Dish 2` without emitting phantom decoys.
  - Candidate domain-transfer augmentations (ISP white-balance 2800K–6500K, CLAHE, specular glare) implemented in `nutrisense_synth/appearance.py` preserve label invariants.
- **Status**: **PASS (Promoted for serving validation)**.

### 2. Stage 2 — Food & Vessel Segmentation (DeepLabV3 + SAM 2.1)
- **Baseline**: DeepLabV3 Macro Food IoU 0.8211, Foreground Union IoU 0.9196, Region F1 0.7541, Boundary F1 0.5973 on WED DEV.
- **Real-World Guardrail**: $\text{Sum Item Mask Area} / \text{Top Food Mask Area} = 1.00\times$ (zero mask area explosion), 0 duplicate proposal fragments.
- **Result**:
  - `_reconcile_dense_grid_items` with connected component checks preserves monolithic rice mounds while detecting distinct secondary katoris.
  - Multi-item coalescence only merges intersecting masks (`m1 & m2`), preventing spurious fusion of disjoint bowls.
- **Status**: **PASS (Preserved as baseline standard)**.

### 3. Stage 3 — Monocular Depth & Metric Geometry (MoGe-2 ViT-L + Table Plane)
- **Baseline**: 0.74 mm median planar regression RMS error on card quad unprojection. Scale factor $s_Z \in [0.076, 0.199]$ across varied camera distances.
- **Pilot Screening Gate**: Rejected stylized analytic renderer pilot for appearance training (`ledger/032`), retained strictly for depth/geometry invariant testing.
- **Result**: Metric scale factor and tabletop unprojection remain stable without plate rim distortion.
- **Status**: **PASS (Renderer retained for geometry tests only; unverified appearance models excluded)**.

### 4. Stage 4 — Learned Weight Head (DINOv2-S + MLP)
- **Baseline**:
  - 5-Fold Outer WED TRAIN CV: 16.421 g MAE (`cv_weight_head_s42_k5_wd1e-4.json`).
  - WED DEV: 15.034 g MAE (`data/reports/run_eval_dev_008_baseline.json`).
- **Preregistered Gate**:
  - Paired plate-bootstrap 95% CI upper bound must be $< 0\text{ g}$ over 10,000 replicates.
  - No high-support class ($\ge 50$ outer-fold ROIs) may regress by $> 10\%$ in MAE.
  - Plate-total MAE regression must be $\le 5\%$, and global signed bias increase $\le 2\text{ g}$.
- **Candidate Evaluations**:
  1. **Weight Decay Regularization (`wd=1e-3` vs `wd=1e-4`)**:
     - Paired $\Delta\text{MAE} = -0.148\text{ g}$, 95% bootstrap CI $[-0.281, -0.016]\text{ g}$ (passed overall delta gate).
     - Guardrail check: `boondi` subgroup (62 ROIs) regressed from 3.752 g to 5.220 g MAE (**+39.1%**, failing the $10\%$ threshold).
     - Gate decision: **REJECT** (`tools/compare_cv_runs.py`).
  2. **Strong Augmentation Pilot (`aug006`)**:
     - WED DEV MAE: 16.449 g vs 15.034 g baseline ($\Delta = +1.414\text{ g}$, 95% CI $[+0.615, +2.171]\text{ g}$).
     - Gate decision: **REJECT** (significant positive regression).
- **Decision**: **REJECT ALL CANDIDATE WEIGHT CHECKPOINTS**. Retain frozen baseline weights (`4ae02ef39de2610d5dede9b95f84c66bfd1c797c5cff7f5d7125e56c40bae1a1`).

### 5. Stage 5 — Combined End-to-End Pipeline Evaluation
- **WED DEV Full Freeze Run** (`experiments/synthetic_food/e2e_dev_baseline.json`):
  - 108 DEV views across 21 plate groups evaluated end-to-end.
  - Mass return rate: 100.0% (108/108 views).
  - Net food mass semantics verified; tare excluded.
  - Complete provenance audited: locked data accessed = `false`, ArUco accessed = `false`.
- **Physical Multi-Item Benchmark** (`Aruco_7ID_60mm_with_food` Dish 1 & Dish 2):
  - Dish 1 (`20261025_184421.jpg`): Resolved to Steamed Rice 191.1g + Sambar 202.4g (`on_day: true` for Monday `rice_sambar`), total 393.5g (within 1.2% of ground truth 200g sambar). Zero false chutney/papad/salad.
  - Dish 2 (`20261027_085735.jpg`): Resolved to Steamed Rice 141.3g + Sambar 203.2g (`on_day: true`), total 344.5g. Zero false decoys.

## Summary Decision

1. **Protocol Gate Cleared**: Full 5-stage baseline frozen and documented in `data/reports/all_stage_baseline_freeze.json` and `docs/model-metrics.md`.
2. **Provenance Pipeline Implemented**: ISP domain randomization (2800K–6500K, CLAHE, specular highlights), vessel-relative geometry conditioning, and `auditable_cutmix` operational in `nutrisense_synth/` with passing tests.
3. **Model Weights Locked**: No candidate weights passed the strict paired bootstrap non-regression gates; production serving weights remain honest and unchanged.
4. **Data Integrity**: WED LOCKED (`502/502` files) remains untouched; ArUco captures remain strictly `EVAL-ONLY`.
