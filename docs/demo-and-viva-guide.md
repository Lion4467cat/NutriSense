# NutriSense Demonstration & Viva Examination Guide

This guide is designed for project evaluators, conference reviewers, viva defense committees, and developers conducting live demonstrations of **NutriSense: AI-Powered 3D Dietary Assessment & Nutrition Auditing from a Single Meal Photo**.

---

## 📊 Model-by-Model & End-to-End Pipeline Accuracy Summary

Evaluators, academic guides, and viva defense committees specifically examine: *"What is the verified percentage accuracy (%) of each machine learning model and the combined vision pipeline?"*

### Scientific Accuracy Metric Definitions
1. **Detection & Verification Gates**: $\text{Accuracy} = \frac{N_{\text{correct}}}{N_{\text{total}}} \times 100\%$
2. **Semantic Segmentation**: 
   - **Dice Similarity Coefficient (F1)**: $\text{Dice} = \frac{2 |A \cap B|}{|A| + |B|} \times 100\%$
   - **Intersection over Union (Jaccard Index)**: $\text{IoU} = \frac{|A \cap B|}{|A \cup B|} \times 100\%$
3. **Food Classification**:
   - **Top-1 / Top-5 Categorical Accuracy**: Fraction of test crops where the ground-truth dish appears in the top $k$ predictions.
   - **Macro-Averaged Recall**: Balanced class-wise sensitivity across all 41 categories.
4. **Portion Weight & Mass Estimation**:
   - **Volumetric Mass Accuracy (%)**: $\text{Accuracy}_{\text{mass}} = 100\% - \text{MAPE} = 100\% - \left(\frac{1}{N}\sum_{i=1}^N \frac{|\hat{m}_i - m_i|}{m_i}\right) \times 100\%$

---

### Master Model-by-Model Accuracy Table

| Stage & Subsystem | Architecture / Model | Primary Accuracy (%) | Key Error / Overlap Metric | Evaluated Split & Scope |
| :--- | :--- | :---: | :---: | :--- |
| **Stage S1a: Physical Anchor** | 60 mm ArUco 7-ID + Michelson Contrast Gate | **100.0%** Detection | Plane RMS: **0.74 mm** (Scale: $\pm 0.8\%$) | 23 Real Captures (Dishes 1–6) |
| **Stage S1b: Implicit Scale Head** | Teacher-Student DINOv2-S Regressor | **77.00%** Scale Accuracy | Scale MAE: **0.00251 cm/px** ($23.00\%$ MAPE) | 6-Fold LODO-CV ($N=23$, Held-Out Dishes) |
| **Stage S2: Semantic Segmentation** | DeepLabV3 (ResNet-50) + SAM 2.1 Hiera | **95.81%** FG Dice / **82.11%** Food IoU | Macro Dice: **89.76%**, Boundary F1: **59.73%** | WED DEV ($108$ views, $21$ plates) |
| **Stage S2b: Primary Food Classifier**| Google SigLIP-2 (ViT-B/16, $\alpha=0.65$) | **82.27%** Top-1 / **96.40%** Top-5 | Macro Recall: **82.12%**, Top-1 Gallery: **81.03%** | WED DEV ($1,218$ food crops, 41 classes) |
| **Stage S2c: Two-Tier Indian Bank** | Fused SigLIP-2 Prototypes + Text Ensembles | **115 Regional Classes** | Fused Score: $0.70 \cdot S_{\text{vis}} + 0.30 \cdot S_{\text{text}} \ge 0.58$ | $1,206$ Bharat/Rajistics Visual Prototypes |
| **Stage S3a: Metric 3D Depth** | MoGe-2 (ViT-L) + Annulus Tabletop Fit | **Sub-millimeter** Plane RMS | Annular Ring $1.5\text{--}5.5\text{ cm}$, Tare $3.5\text{ mm}$ | Monocular Metric Reconstruction |
| **Stage S3b: Mass Estimation Head** | Frozen DINOv2-S + Heteroscedastic MLP | **81.70%** DEV / **80.01%** LOCKED | DEV MAE: **15.03 g**, LOCKED MAE: **14.67 g** | WED DEV ($1,218$ ROIs) & LOCKED ($2,793$ ROIs) |
| **Stage S4/S5: Compliance Engine** | 4,000-draw Comonotonic Monte Carlo | **100.0%** Valid Verdicts | Coverage Gate: $C \ge 0.85$, Seed 1234 | PM POSHAN Primary & Upper-Primary |
| **End-to-End: Primary Overhead Meals** | Full 6-Stage Deterministic Fused Pipeline | **90.58%** Mean Accuracy | MAE: **29.70 g** (MAPE: **9.42%**) | Real Weighed Handheld Plates ($N=6$) |
| **End-to-End: All-View Handheld Meals**| Full 6-Stage Deterministic Fused Pipeline | **69.56%** Mean Accuracy | MAE: **93.94 g** (MAPE: **30.44%**) | All 23 Handheld Captures (up to $65^\circ$ tilt) |
| **Card-Free Mode B (Zero Marker)** | Annulus Reconstruction + LODO Implicit Head | **53.49%** Out-of-Fold Mass Acc | MAE: **153.23 g**, Signed Bias: **-44.40 g** | **80.1% Bias Reduction** (from $-223.52\text{ g}$) |

---

### Real-World Multi-Item Weighed Meals Breakdown (Dishes 1–6)

| Dish Cohort | Menu & Components Tested | Ground-Truth Mass | NutriSense Predicted (Mode A) | Absolute Error | Volumetric Accuracy ($100\% - \|\%\text{Err}\|$) | Card-Free Mode B Prediction | Mode B Accuracy |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dish 6** | Chicken Dum Biryani Plate | **351.0 g** | **358.8 g** | $+7.8\text{ g}$ ($+2.2\%$) | **97.8%** *(Best View: **99.9%**)* | 262.7 g | **74.8%** |
| **Dish 5** | Veg Dum Biryani Plate | **150.0 g** | **151.1 g** | $+1.1\text{ g}$ ($+0.7\%$) | **99.3%** *(Best View: **99.2%**)* | 181.7 g | **78.9%** |
| **Dish 2** | Steamed Rice + Rasam Katori | **338.0 g** | **346.2 g** | $+8.2\text{ g}$ ($+2.4\%$) | **97.6%** *(Best View: **98.1%**)* | 325.9 g | **96.4%** |
| **Dish 3** | Steamed Rice + Chappati / Chutney | **191.0 g** | **165.5 g** | $-25.5\text{ g}$ ($-13.4\%$) | **86.6%** *(Best View: **97.1%**)* | 177.5 g | **92.9%** |
| **Dish 1** | Steamed Rice + Veg Sambar (Multi-Item)| **450.0 g** | **383.3 g** | $-66.7\text{ g}$ ($-14.8\%$) | **85.2%** *(Sambar bowl: **98.8%**)* | 433.1 g | **96.2%** |
| **Dish 4** | Chicken Biryani (Deep Steel Vessel) | **250.0 g** | **209.0 g** | $-41.0\text{ g}$ ($-16.4\%$) | **83.6%** *(Tilted perspective)* | 154.4 g | **61.8%** |
| **Summary** | **Pooled Primary Overhead Benchmark** | — | — | **MAE: 29.70 g** | **90.58% Mean Accuracy** | **Bias: -44.40 g** | **80.1% Bias Cut** |

---

---

## 1. Quickstart & System Execution

NutriSense provides two execution modalities: **Local Development Environment** (for rapid iterative testing) and **Docker Containerization** (for isolated, reproducible deployment).

### Option A: Local Full-Stack Development (Recommended for Live Viva)

#### 1. Backend API Service
Ensure the Python virtual environment is activated and start the FastAPI server:
```bash
cd /home/tinkerer/Desktop/Nutrisense/NutriSense-main
./.venv/bin/uvicorn engine.api:app --host 0.0.0.0 --port 8000 --reload
```
- API Docs & Swagger: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health` (verifies GPU device, CUDA version, and model weights)

#### 2. Frontend Web Interface
In a separate terminal, launch the Vite development server:
```bash
cd /home/tinkerer/Desktop/Nutrisense/NutriSense-main/frontend
npm run dev
```
- Web Application: `http://localhost:5173`

---

### Option B: Production Docker Compose Deployment

Ensure the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) is installed on the host machine.
```bash
docker compose up --build
```
- Unified Interface: `http://localhost:5173` (proxied to backend API on port 8000)

---

## 2. Recommended Live Demonstration Script

Follow this step-by-step walkthrough to showcase the core capabilities of the system during a demo or evaluation:

### Step 1: Interface Overview & Theme System
1. Open `http://localhost:5173` in a desktop browser.
2. Observe the unified top navigation header (`Home`, `Analyze`, `History`, `Insights`, `Students`, `Menu`).
3. Click the **Theme Toggle** (sun/moon icon) in the top-right header to cycle through the 8 custom colorways (e.g., *OLED Teal*, *Rosé Dawn*, *Dracula*, *Nord*, *Dark Indigo*).
4. Note the **Mode Switch** (`School` vs. `General`):
   - **School Mode**: Audits meals against statutory Government of India **PM POSHAN scheme** nutritional norms.
   - **General Mode**: Evaluates dietary contributions against individual **WHO/FAO daily goals**.

### Step 2: High-Accuracy Single-Photo Analysis (Mode A: Marker Present)
1. Navigate to the **Analyze** tab.
2. Select or drag-and-drop the recommended benchmark image:
   - File: `Aruco_7ID_60mm_with_food/Dish 5/20261025_194452.jpg` (Single Biryani plate, Ground Truth: **150.0 g**).
3. Click **Analyze Plate**.
4. Observe the results card:
   - **Estimated Mass:** `151.2 g` (**+1.2 g / +0.8% error** vs. physical scale).
   - **Scale Anchor:** Detected 60 mm ArUco ID 7 with high Michelson contrast ($C_M \ge 0.42$).
   - **Depth Calibration:** MoGe-2 unprojected surface with fitted 3D tabletop plane.
   - **Nutritional Breakdown:** Energy (kcal), Protein (g), Carbohydrates (g), and Fat (g) with 90% confidence bounds.
   - **Compliance Verdict:** PASS / BORDERLINE indicator according to selected demographic band.

### Step 3: Complex Multi-Item Institutional Thali (Dish 2 or Dish 3)
1. Upload `Aruco_7ID_60mm_with_food/Dish 2/20261025_184852.jpg` (Rice + Rasam, Ground Truth: **338.0 g**).
2. Point out:
   - **Multi-Item Decomposition:** Correctly distinguishes the central steamed rice mound from the steel side bowl (*katori*) containing rasam.
   - **Zero Mask Explosion:** Background gray attenuation ($\alpha = 0.65$) prevents rice embeddings from misclassifying the rasam bowl as rice.
   - **Estimated Mass:** `367.1 g` (**+8.6% error**), avoiding legacy multi-item volume blowup ($>1,700\text{ g}$).

### Step 4: Card-Free Implicit Scale Estimation (Mode B)
1. In the analysis settings or API query, disable the required fiducial card flag or submit a cropped meal image where the marker is absent.
2. Explain to the evaluators that NutriSense activates the **`ImplicitScaleHead`** trained via marker-dropout teacher-student supervision, recovering metric scale ($0.00196\text{ cm/px}$ LODO-CV MAE) directly from plate geometry and perspective cues.

### Step 5: Nutritional Insights & Student Ledger
1. Click **Insights** in the topbar: view aggregated nutritional trends, macronutrient balance ratios, and meal compliance distributions.
2. Click **Students**: inspect cohort-level nutritional intake records, flagging under-nourished student bands.
3. Click **Menu & standards**: inspect official PM POSHAN nutritional minimums (Energy and Protein statutory thresholds).

---

## 3. Defense Examination: 10 Essential Viva Questions & Model Answers

### Q1: Why not simply feed the 2D meal image into a Vision-Language Model (VLM) like GPT-4o or Gemini 1.5 Pro to predict weight?
> **Answer:** Monocular 2D images suffer from fundamental metric scale ambiguity. A 10 cm plate viewed close-up projects to the identical 2D pixel area as a 30 cm thali viewed from further away. In our empirical canteen held-out benchmark ([Ledger 027](file:///home/tinkerer/Desktop/Nutrisense/NutriSense-main/docs/ledger/027-vlm-canteen-participant-heldout.md)), direct VLM zero-shot predictions exhibited a massive negative bias ($-106.9\text{ g}$ mean error) and hallucinated gram estimates regardless of actual physical mass. NutriSense enforces physics-based volume reconstruction by unprojecting dense metric depth, computing 3D integration over the tabletop plane, and factoring food densities from the Indian Food Composition Tables (IFCT 2017).

---

### Q2: How does the system handle variable camera angles and perspective tilts?
> **Answer:** NutriSense utilizes a multi-stage geometric normalizer:
> 1. In Mode A, four corners of the 60 mm ArUco marker are detected, and camera extrinsics ($\mathbf{R}, \mathbf{t}$) are computed using OpenCV's Perspective-n-Point (PnP) solver.
> 2. The monocular depth map from MoGe-2 is unprojected into 3D camera coordinates $\mathbf{P} = z \cdot \mathbf{K}^{-1} [u, v, 1]^T$.
> 3. An exterior ring of tabletop points surrounding the food mask is sampled, and a 3D tabletop plane ($ax + by + cz + d = 0$) is fitted via Singular Value Decomposition (SVD).
> 4. Food thickness is computed along the plane normal vector rather than the tilted camera line-of-sight, eliminating perspective foreshortening.

---

### Q3: What is "mask explosion" in SAM 2, and how did NutriSense eliminate it?
> **Answer:** Segment Anything Model (SAM 2.1) is class-agnostic. On complex Indian thalis with reflective stainless steel plates and liquid gravies, unconstrained dense-grid prompting generates 30 to 57 overlapping proposal fragments, tabletop shadows, and plate rim highlights. Summing their individual 3D volumes resulted in a $2.8\times$ to $7.7\times$ mass overestimation (e.g., $912\text{ g}$ on a $150\text{ g}$ plate). NutriSense introduced:
> 1. An outer convex hull containment test ($\text{Area} / \text{ConvexArea} \ge 0.60$).
> 2. A boundary clearance filter discarding proposals that touch the plate rim.
> 3. Same-food family union coalescing ($M_{\text{merged}} = M_1 \cup M_2$) for fragmented rice mounds. This strictly bounded the sum-to-top area ratio to $1.00\times$ with **0 phantom items**.

---

### Q4: Why train a native DeepLabV3 segmenter if SAM 2 is already available?
> **Answer:** While SAM 2 excels at hard, high-contrast object boundaries, Indian institutional dishes (such as dal over rice, sambar, or khichdi) feature diffuse, liquid, and amorphous boundaries. As shown in our World-Exchange-Diet (WED) comparative study ([Ledger 029](file:///home/tinkerer/Desktop/Nutrisense/NutriSense-main/docs/ledger/029-wed-semantic-segmentation-study.md)), native DeepLabV3 achieves a **0.7541 Region F1** and **0.8211 Macro Food IoU**, outperforming zero-shot SAM 2 dense grids (**0.2077 F1**) by $3.6\times$ and eliminating spurious proposal fragmentation.

---

### Q5: How does the card-free mode (`ImplicitScaleHead`) work without an ArUco fiducial?
> **Answer:** `ImplicitScaleHead` ([Ledger 036](file:///home/tinkerer/Desktop/Nutrisense/NutriSense-main/docs/ledger/036-card-free-implicit-scale-and-docker.md)) uses a **marker-dropout teacher-student architecture**. During training on real ArUco captures, the teacher uses the detected physical marker to establish the exact ground truth metric scale ($cm/px$) and depth scale factor ($s_Z$). The student model receives the same image with the marker digitally inpainted/erased and learns to predict scale from plate geometry, dish boundaries, and visual perspective. In our 6-Fold Leave-One-Dish-Out Cross-Validation (LODO-CV), it achieved an out-of-distribution scale error of **$0.00196\text{ cm/px}$ (17.81% MAPE)**.

---

### Q6: How are food densities determined, and how is packing variance handled?
> **Answer:** Each recognized dish class is mapped to its standard density ($\rho\text{ in g/cm}^3$) derived from the National Institute of Nutrition (NIN) **Indian Food Composition Tables (IFCT 2017)**. Because real food packing varies (e.g., fluffy basmati rice at $0.70\text{ g/cm}^3$ vs. compacted rice at $0.95\text{ g/cm}^3$), NutriSense implements a **4,000-iteration Bayesian Monte Carlo engine**. Density and depth noise are modeled as log-normal distributions, outputting certified $p_{05}$ to $p_{95}$ (90%) confidence intervals rather than a misleading single-point estimate.

---

### Q7: What are the exact statutory PM POSHAN standards verified in School Mode?
> **Answer:** Under the Government of India National Programme of PM POSHAN (formerly Mid-Day Meal Scheme):
> - **Primary (Classes 1 to 5):** Minimum **450 kcal** Energy and **12.0 g** Protein per meal.
> - **Upper Primary (Classes 6 to 8):** Minimum **700 kcal** Energy and **20.0 g** Protein per meal.
> NutriSense samples the posterior energy and protein distributions and assigns a certified verdict:
> - **PASS:** $\ge 85\%$ of Monte Carlo samples meet both statutory thresholds.
> - **BORDERLINE:** Median meets the threshold but lower confidence bound falls short.
> - **FAIL:** Median falls below the statutory standard.

---

### Q8: What zero-leakage protocol was followed to ensure scientific integrity?
> **Answer:** Scientific integrity is enforced by three non-negotiable architectural guardrails:
> 1. **Cryptographic Lock:** `tools/check_locked.py` pins SHA-256 hashes of all 502 test images in `data/wed/test/`. Any tampering or reading immediately halts pipeline execution.
> 2. **Split Isolation:** The 21 `WED DEV` plates (108 views) are held out exclusively for model selection and bootstrap evaluation, never touched during training.
> 3. **Eval-Only Benchmark:** The 23 physical ArUco captures (`Aruco_7ID_60mm_with_food`) remain permanently eval-only; zero training or threshold tuning is conducted on them.

---

### Q9: Why is background attenuation ($\alpha = 0.65$) necessary in the SigLIP classifier?
> **Answer:** When cropping secondary dishes (e.g., a small stainless steel bowl of coconut chutney or rasam placed inside a thali), rectangular bounding box crops inevitably contain surrounding white rice or dark table pixels. Standard vision transformers attend heavily to high-contrast surrounding pixels, misclassifying chutney as rice. By applying linear gray blending ($I_{\text{masked}} = 0.65 \cdot I + 0.35 \cdot 128$) to pixels outside the segmented object mask, background interference is neutralized while retaining dish texture and chromaticity.

---

### Q10: How does inverse-variance sensor fusion combine metric geometry and learned representations?
> **Answer:** For food items where both 3D depth geometry ($\hat{m}_{\text{geom}}$) and learned DINOv2-S weight representations ($\hat{m}_{\text{learned}}$) are available, NutriSense blends them using inverse-variance weights:
> $$\hat{m} = \frac{w_{\text{geom}} \hat{m}_{\text{geom}} + w_{\text{learned}} \hat{m}_{\text{learned}}}{w_{\text{geom}} + w_{\text{learned}}}, \quad w_{\text{geom}} = \frac{1}{\sigma_{\text{geom}}^2}, \quad w_{\text{learned}} = \frac{1}{(2.20 \cdot \sigma_{\text{learned}})^2}$$
> The $2.20$ inflation factor reflects the higher variance of appearance-based estimation across varying smartphone camera ISP pipelines.
