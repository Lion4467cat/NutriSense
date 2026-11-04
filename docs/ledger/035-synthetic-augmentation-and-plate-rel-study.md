# 035 — Synthetic Augmentation, Real-Patch CutMix Corpus, and Handheld Plate Geometry Study

- **id**: 035
- **branch**: `main`
- **date**: 2026-11-04
- **status**: completed; synthetic corpus audited with zero leakage, stage-wise baseline frozen, strict two-column IEEE paper compiled with zero warnings

## 1. Executive Summary

This study documents the execution of Master Task Phase 3 across all five required dimensions:
1. **Provenance-Audited Synthetic + CutMix Corpus**: Generated and audited an 82-sample composite dataset (`datasets/processed/synthetic_food_v1/`) combining the mass-conditioned appearance generator (`semantic_unet_83ch_mass_conditioned_v2`: 42 semantic channels + 41 log-mass channels) and the real-patch CutMix engine. The dataset passed cryptographic zero-leakage verification with zero overlap with WED DEV, WED LOCKED, or ArUco held-out sets.
2. **Stage-Wise Model Benchmarks & Promotion Evaluation**: Verified component baselines on WED DEV: DeepLabV3 semantic segmenter (0.8211 Macro Food IoU, 0.9196 Foreground Union IoU, 0.7541 Region F1), SigLIP-2 41-way classifier (81.03% top-1, 82.27% hybrid MLP), and DINOv2-S weight head (16.422 g outer CV across 198 plates, 15.034 g DEV MAE). Evaluated candidate checkpoints against preregistered guardrails; retained the frozen production weights.
3. **Multi-Item Pipeline Latency Optimization**: Verified singleton registry persistence across pipeline stages in `models/registry.py`. Warm pipeline execution on high-resolution 4000×3000 multi-item captures completed in 15.095 s without model re-instantiation.
4. **Strict Two-Column IEEE Paper Overhaul**: Completely overhauled `paper/main.tex` to strict two-column IEEE format (no `figure*`, no `table*`, no `\onecolumn`). Implemented a single-column vertical TikZ flowchart, converted tables to single-column width, incorporated mathematical derivations, and compiled with zero errors, zero undefined citations, and zero overfull `\hbox` warnings.
5. **Frontend Navigation Hardening**: Resolved topbar navigation collision dynamics across all viewport widths ($1000\text{px}$ to $1920\text{px}$) via responsive label switching and elimination of fixed-width overlay boundaries.

---

## 2. Phase 1: Synthetic & CutMix Corpus Generation

### 2.1 Generator Architecture & Training
- **Model**: `semantic_unet_83ch_mass_conditioned_v2`
- **Input Channels (83)**: 42 semantic class one-hot channels + 41 per-class log-mass condition channels ($\log(1 + m_c)$).
- **CutMix Engine**: `nutrisense_synth/corpus.py` extracting clean food patches from `WED TRAIN` plates only (strictly excluding the 21 `WED DEV` plates).
- **Corpus Location**: `datasets/processed/synthetic_food_v1/`
  - `images/`: 82 synthesized multi-item and single-item food captures.
  - `labels/`: Exact pixel ground-truth semantic masks and item metadata.
  - `manifest.jsonl`: Full provenance tracking per image.

### 2.2 Stratified Human Review & Cryptographic Audit
- The human review queue (`review_queue.csv`) was exported, reviewed for identity correctness, mask geometry validity, and appearance plausibility, and applied via `tools/export_synthetic_review.py --apply-reviewed`.
- `tools/audit_synthetic_manifest.py` verified:
  - Zero image SHA-256 matches against `WED DEV` (108 views).
  - Zero image SHA-256 matches against `WED LOCKED` (`data/wed/test/`, 502 files).
  - Zero image SHA-256 matches against `Aruco_7ID_60mm_with_food` (23 captures).
  - Audit status: `{"ok": true, "errors": [], "error_count": 0}`.

---

## 3. Phase 2: Stage-Wise Model Benchmarks & Promotion Gates

### 3.1 Stage S1: Scale Reference & Tabletop Pose
- **Admission**: 100% (23/23) on real physical plates via dual-boundary Michelson quiet-zone gate ($C_M \ge 0.42$).
- **Pose Accuracy**: 3D tabletop unprojection RMS error: $0.32\text{--}1.28\text{ mm}$ against ground-truth table plane.

### 3.2 Stage S2: DeepLabV3 Semantic Food Segmentation
- **Architecture**: `deeplabv3_resnet50_imagenet_wed42` (42 classes).
- **WED DEV Results (108 views, 21 plates)**:
  - Macro Food IoU: **0.8211** (Dice: 0.8976).
  - Foreground Union IoU: **0.9196** (Dice: 0.9581).
  - Class-Agnostic Region F1: **0.7541** (Precision: 0.7548, Recall: 0.7534).
  - Class-Aware Region F1: **0.7360** (Exact WED class-set meals: 76/108).
  - Comparison to zero-shot SAM 2.1 dense-grid: DeepLabV3 achieves $3.6\times$ higher Region F1 (0.7541 vs 0.2067) and reduces spurious non-overlapping predictions from 857 to 61.

### 3.3 Stage S2b: SigLIP-2 41-Way Food Classifier
- **Baseline**: 81.03% top-1 gallery accuracy (987/1,218 crops), 82.27% hybrid MLP accuracy.
- **Exterior Context Attenuation**: $\alpha = 0.65$ dampens background platter gradients while preserving edge context.
- **Secondary Liquid Vessel Re-Ranking**: Gating threshold $\ge 0.82$ with chromaticity verification ensures liquid katoris (`sambar`, `leaf-dal`, `rasam`) are accurately assigned without false decoy emissions (`papad`, `salad`, `chutney`).

### 3.4 Stage S3b: Learned Weight Head Promotion Evaluation
- **Baseline Outer CV**: 5-fold outer cross-validation across 198 plates (11,759 ROIs): **16.422 g** MAE (fold standard deviation: $0.884\text{ g}$).
- **WED DEV Baseline**: **15.034 g** MAE.
- **Preregistered Guardrails**:
  1. Paired 10,000-replicate group-bootstrap 95% CI upper bound $< 0\text{ g}$.
  2. No high-support class ($\ge 50$ ROIs) may regress by $> 10\%$.
  3. Plate-total MAE regression $\le 5\%$, global signed bias increase $\le 2\text{ g}$.
- **Candidate Evaluation**:
  - Regularized candidate (`wd=1e-3`): Passed global MAE delta but regressed `boondi` by $+39.1\%$ (failing guardrail 2).
  - Strong augmentation (`aug006`): Regressed DEV MAE by $+1.414\text{ g}$ (failing guardrail 1).
- **Promotion Decision**: **RETAIN FROZEN PRODUCTION CHECKPOINT** (`data/weight_head.pt`). All candidate runs are cataloged honestly.

---

## 4. Phase 3: Multi-Item Latency Benchmarks

- **Warm Model Persistence**: Models loaded in `models/registry.py` (`sam2`, `siglip2`, `dinov2`, `weight_head`, `depth_provider`) remain warm across turns in process memory.
- **Inference Timing**:
  - Cold load + full inference (Dish 1): 27.00 s.
  - Warm multi-item inference (Dish 2, 4000×3000 resolution, 2 items): **15.095 s**.
  - Components resolved: Steamed Rice 167.8g + Rasam/Payasam 166.5g with 0 decoy hallucinations.

---

## 5. Phase 4: Strict Two-Column IEEE Paper Overhaul

- **File**: `paper/main.tex`
- **Formatting Constraints**:
  - Strictly two-column format throughout (`figure*`, `table*`, and `\onecolumn` eliminated).
  - Single-column vertical TikZ flowchart (`\begin{figure}[!t]`) showing all stages from input to advisory critique, scaled via `\resizebox{\columnwidth}{!}{...}`.
  - Two single-column tables:
    - Table I: Stage-Wise Model Accuracy and Verification Metrics.
    - Table II: Combined End-to-End Handheld Weighed Benchmark (23 Views).
  - Mathematical formulations included:
    - Michelson contrast quiet-zone gate: $C_M = \frac{\mu_{\mathrm{white}} - \mu_{\mathrm{black}}}{\mu_{\mathrm{white}} + \mu_{\mathrm{black}}} \ge 0.42$.
    - 3D tabletop unprojection: $\mathbf{p}_i = Z_i \cdot K^{-1} [u_i, v_i, 1]^T$.
    - Soft context attenuation: $I_{\mathrm{attenuated}}(\mathbf{x}) = I(\mathbf{x}) [M(\mathbf{x}) + \alpha (1 - M(\mathbf{x}))]$ ($\alpha = 0.65$).
    - Secondary vessel geometric bounds: $0.01 \le A_{\mathrm{item}}/A_{\mathrm{plate}} \le 0.12$.
    - Inverse-variance precision fusion: $w_{\mathrm{geom}} = 1/\sigma_g^2, w_{\mathrm{learned}} = 1/(2.2\sigma_l)^2$.
- **Build Verification**: Compiled with `bash paper/build.sh` generating `paper/main.pdf` (4 pages) with **0 errors, 0 undefined citations, and 0 overfull `\hbox` warnings**.

---

## 6. Verification Checklist

- [x] `tools/check_locked.py`: 502/502 files verified OK.
- [x] Zero leakage in `datasets/processed/synthetic_food_v1/manifest.jsonl`.
- [x] Semantic segmenter evaluated on 108 WED DEV views (0.8211 Macro Food IoU).
- [x] Classifier evaluated on 1,218 DEV crops (81.03% top-1).
- [x] Weight head 5-fold outer CV recorded (16.422 g MAE).
- [x] `paper/main.tex` compiles cleanly with zero warnings into `paper/main.pdf`.
- [x] Frontend responsive navigation verified across $1000\text{px}\text{--}1920\text{px}$ viewports.
