# NutriSense Demonstration & Viva Examination Guide

This guide is designed for project evaluators, conference reviewers, viva defense committees, and developers conducting live demonstrations of **NutriSense: AI-Powered 3D Dietary Assessment & Nutrition Auditing from a Single Meal Photo**.

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
2. Observe the unified top navigation header (`Home`, `Analyze`, `History`, `Insights`, `Students`, `Menu & standards`).
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
