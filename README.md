# NutriSense 🍱
### Photo → portion → nutrients → PM POSHAN compliance verdict, for Karnataka MDM canteens

[![Python](https://img.shields.io/badge/Python-3.14-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-70%20passed-brightgreen.svg)](#-testing)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-SAM%202.1%20%C2%B7%20SigLIP2%20%C2%B7%20MoGe--2-yellow.svg)](https://huggingface.co)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)

---

## 📌 Overview

NutriSense turns a single **photo of a plated mid-day meal** into a compliance verdict against the **PM POSHAN (MDM) food & nutrition guidelines**. One capture → dish identification → portion in grams → Monte Carlo nutrient intervals → **PASS / BORDERLINE / FAIL** with honest coverage and assumptions.

Everything the pipeline decides is traceable: which scale anchor was used, how large the uncertainty was, which parameters are still `assumed`, and why a verdict landed where it did. No attendance tracking, no chatbot, no database — v5 is deliberately a single, testable photo-analysis pipeline.

**What it does:**

- Measures portion size from one photo using a printed **reference card** (60 mm) or **₹10 coin** (27 mm) as metric scale — or honestly degrades to a documented *prior* tier that can never issue PASS/FAIL
- Identifies the dish from a 46-photo gallery (SigLIP2), abstaining rather than guessing
- Estimates volume from monocular depth (MoGe-2, calibrated against the card to ~1.1% median error)
- Propagates every uncertainty through a Monte Carlo engine (4000 samples) into 90% intervals
- Scores energy & protein probabilities against the class-band minimums, gated by a **coverage** score

---

## 🔁 Analysis Pipeline

The actual photo → verdict flow as built (`engine/pipeline.py`):

```mermaid
flowchart TD
    IMG["Photo capture<br/>(JPEG + EXIF)"] --> LINT

    subgraph LINT["Lint gates"]
        L1{"digital_zoom == 1.0?"}
        L2{"day in menu?"}
        L3{"band in 1-5 / 6-8 / 9-10?"}
        L4["resolution note<br/>(min side < 1280px, non-blocking)"]
        L1 -->|yes| L2
        L2 -->|yes| L3
        L3 -->|ok| L4
    end

    L1 -->|no| FAIL_CV
    L2 -->|no| FAIL_CV
    L3 -->|no| FAIL_CV

    L4 --> ANCHOR["S1 scale anchor<br/>card 60mm / coin 21mm / prior"]
    ANCHOR --> SEG["S2 segment<br/>(SAM2.1)"]

    SEG -->|exception| FAIL_CV
    SEG --> CLS{"classify<br/>(SigLIP2 gallery)"}

    CLS -->|"dish = null"| FAIL_CV2["cannot_verify<br/>dish unrecognized"]
    CLS -->|"status = out_of_scope"| OOS["out_of_scope<br/>(wheat product)"]
    CLS -->|"dish found"| DEPTH["S3 depth<br/>(MoGe-2 monocular)"]

    DEPTH --> TIER{"anchor tier?"}
    TIER -->|measured| CAL["calibrate_depth_scale<br/>(card/coin, meters)<br/>~1.1% error"]
    TIER -->|prior| NOCAL["no calibration<br/>scale = 1.0, source = none"]
    CAL --> PORTION
    NOCAL --> PORTION["S3 portion<br/>grams = area × height × density<br/>ring / table-prior / size-prior"]

    PORTION -->|exception| FAIL_CV3["cannot_verify<br/>portion estimation failed"]
    PORTION --> MC["S4 Monte Carlo<br/>n=4000, seed fixed<br/>sole interval owner"]

    MC --> VER{"S5 compliance"}
    VER -->|"P >= 0.9, C >= 0.85"| PASS["PASS"]
    VER -->|"P <= 0.1, C >= 0.90"| FAILV["FAIL"]
    VER -->|otherwise| BORD["BORDERLINE"]
    VER -->|"wheat / zoom / band"| SC["out_of_scope /<br/>cannot_verify"]

    PASS --> RESULT
    FAILV --> RESULT
    BORD --> RESULT
    SC --> RESULT
    FAIL_CV --> RESULT
    FAIL_CV2 --> RESULT
    FAIL_CV3 --> RESULT
    OOS --> RESULT

    RESULT["Result dict<br/>verdict + lint + anchor + segmentation<br/>+ classification + dish + portion<br/>+ nutrition + coverage + assumptions<br/>+ advisory + model_versions"]

    classDef gate fill:#ffe0e0,stroke:#c00
    classDef ok fill:#e0ffe0,stroke:#0a0
    classDef warn fill:#fff8dc,stroke:#b80
    class FAIL_CV,FAIL_CV2,FAIL_CV3,SC gate
    class PASS ok
    class BORD,OOS warn
```

### Pipeline components

| Stage | What runs | Model / method |
|---|---|---|
| Lint | digital-zoom gate, day/band validation, resolution note | pure rules |
| S1 Scale anchor | 3 tiers: card → coin → prior (prior caps coverage at 0.60) | ArUco card detector, bimetallic coin detector |
| S2 Segment | food mask from the plate photo | SAM 2.1 (`facebook/sam2.1-hiera-large`) |
| S2 Classify | gallery-first dish match with open-set abstain; text fallback | SigLIP2 (`google/siglip2-base-patch16-224`) |
| S3 Depth | metric depth, scale-calibrated against the marker | MoGe-2 (`Ruicheng/moge-2-vitl`) |
| S3 Portion | grams = anchor-scaled area × height above base × density | ring / table-prior / size-prior paths |
| S4 Nutrition | lognormal sampling of every uncertainty source | Monte Carlo, n=4000, fixed seed (sole interval owner) |
| S5 Compliance | P(at/above min) per mandatory nutrient × coverage gates | pure rules from `data/standards.yaml` |

---

## ✨ Features

**Implemented and tested (70 tests green):**

- **Three-tier scale anchor** — reference card (60 mm ArUco), ₹10 coin (27 mm), or size prior; tier is always reported and gates verdict authority
- **Gallery dish classification** — 46 real dish photos, leave-one-out 46/46, abstain threshold 0.82 (synthetic renders correctly abstain)
- **Monocular depth with metric calibration** — raw MoGe scale is ~6× off out-of-domain; card calibration brings it to ~1.1% median error
- **Portion estimation** — plate +6.6% / bowl +5.6% volume vs ground truth on synthetic scenes; prior tier flagged `vessel_shape_uncertain`
- **Monte Carlo nutrient engine** — grams lognormal from per-dish σ, recipe-share noise, nutrient-table σ, temperature-scaled intervals; raw-equivalent diagnostics kept informational only
- **Compliance verdicts** — PASS ≥ P0.90 & coverage ≥ 0.85 / FAIL ≤ P0.10 & coverage ≥ 0.90 / else BORDERLINE; prior tier and wheat products can never PASS or FAIL; salt is advisory only
- **FastAPI service** — `GET /health`, `GET /menu`, `POST /analyze` with full diagnostics in every response
- **React frontend** — capture form, verdict card, pure-CSS nutrient interval bars against band minimums, coverage gates, portion + quality panels (screenshot below)
- **Synthetic scene renderer** — full GT (image, depth, masks, grams, anchor) powering the test suite

![Frontend result view](docs/assets/frontend-result.png)

**Open gates (M1–M8, see `docs/final-report.md`):** physical reference-card run against a kitchen scale, prior-tier depth-scale validation, real-photo abstain/segmentation tuning (real canteen photos currently segment poorly — see Known Limitations), nutrient-table validation, holdout evaluation.

---

## 🗄️ Data & Sources

| Source | What it provides | Where |
|---|---|---|
| PM POSHAN menu + F&N guidelines (user-provided doc) | dishes, days, class bands, kcal/protein minimums | `data/menu.yaml`, `data/standards.yaml` |
| IFCT 2017 (NIN Hyderabad) | boiled-rice / curd nutrient values (literature rows) | `data/nutrients.yaml` |
| Recipe assumptions | sambar, vegetable_rice, bisi_belee_bath rows (marked `assumed`) | `data/nutrients.yaml`, `data/params_status.yaml` |
| Canteen phone photos (46) | classifier gallery | `data/gallery.npz`, `../DATASET/` |
| Synthetic renderer | ground truth for the test suite | `tests/synth/` |
| Reference card (A6, 300 dpi) | metric scale marker | `docs/assets/reference_card_A6_300dpi.png` |

No USDA API, no external database, no network calls at runtime — all policy lives in versioned YAML.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI · Python 3.14 · uv-managed `.venv` |
| Vision | PyTorch 2.13 (CUDA) · SAM 2.1 · SigLIP2 · MoGe-2 via HuggingFace Transformers |
| Geometry | OpenCV 5 · NumPy 2 · custom `geo/` package |
| Uncertainty | NumPy Monte Carlo (seeded) |
| Frontend | React 18 · Vite 6 · pure-CSS charts (no chart runtime needed) |
| Tests | pytest — 70 tests (synthetic GT scenes + HTTP E2E) |

---

## 📁 Project Structure

```
NutriSense/
├── main.py                    # FastAPI: /health /menu /analyze
├── geo/                       # camera pose, planes, quads, back-projection
├── models/
│   ├── scale_anchor.py        # S1: card / coin / prior tiers
│   ├── dish_segmenter.py      # S2: SAM 2.1 food masking
│   ├── food_classifier.py     # S2: SigLIP2 gallery-first + text fallback
│   └── portion_estimator.py   # S3: area × height × density → grams
├── engine/
│   ├── pipeline.py            # S6: analyze() orchestration + gates
│   ├── depth.py               # MoGe-2 wrapper + marker calibration
│   ├── mc.py                  # S4: Monte Carlo (sole interval owner)
│   ├── nutrients.py           # nutrient table access
│   └── compliance.py          # S5: verdict + coverage rules
├── data/                      # single sources of truth (YAML + gallery.npz)
├── tests/                     # 70 tests incl. synth/ renderer with full GT
├── docs/                      # protocol, reports, flowchart, card asset
├── tools/                     # reference-card generator, gallery builder
└── frontend/                  # React 18 + Vite analyzer UI
```

---

## 🚀 Getting Started

### Prerequisites

- **uv** (Python package manager) — https://docs.astral.sh/uv/
- **Python 3.14**, **Node 20+**
- NVIDIA GPU + CUDA recommended (CPU works, slower)

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/Lion4467cat/NutriSense.git
cd NutriSense
```

**2. Create the Python environment (uv)**

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-cv.txt
```

**3. Run the backend (port 8731)**

```bash
.venv/bin/uvicorn main:app --port 8731
```

**4. Run the frontend (separate terminal)**

```bash
cd frontend
npm install
npm run dev
```

**5. Run the tests**

```bash
.venv/bin/pytest -q
```

### Access the App

- **Frontend:** http://localhost:5173
- **Backend API Base:** http://127.0.0.1:8731
- **Interactive Docs:** `http://127.0.0.1:8731/docs`
- **Health Check:** `http://127.0.0.1:8731/health`

The frontend reads the API base from `VITE_API_BASE` (default `http://127.0.0.1:8731`). First run downloads HF model weights (~3 GB) — prefix with `HF_HUB_DISABLE_XET=1` if downloads stall. Full agent notes live in `AGENTS.md`.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Server status |
| GET | `/health` | Health check (`phase`) |
| GET | `/menu` | Dishes, days, class bands, capture fields (single source of truth) |
| POST | `/analyze` | Multipart upload (`file`, `day`, `band`, `serving_style`) → full analysis |

### Example Response — `/analyze`

```json
{
  "verdict": "FAIL",
  "reasons": ["mandatory nutrient below minimum with sufficient coverage", "kcal: P=0.06 <= 0.1 fail zone"],
  "lint": {"digital_zoom": null, "min_side_px": 1100, "resolution_ok": false, "notes": ["min side 1100 < 1280px (marker tier may fall back to prior)"]},
  "anchor": {"method": "card_aruco", "tier": "measured", "cm_per_px": 0.0547, "tilt_deg": 39.0, "depth_scale_factor": 0.1417, "depth_scale_source": "card"},
  "classification": {"dish": "rice_sambar", "confidence": 0.9, "method": "gallery"},
  "dish": {"id": "rice_sambar", "display_name": "Rice & Sambar", "day": "mon", "band": "1-5"},
  "portion": {"grams": 298.5, "volume_ml": 354.8, "base_method": "ring", "scale_tier": "measured", "sigma_grams_rel": 0.37, "flags": []},
  "nutrition": {"kcal": {"mean": 271.0, "interval_90": [141.0, 466.0]}, "protein_g": {"mean": 7.3, "interval_90": [3.8, 12.5]}},
  "coverage": {"score": 1.0, "factors": {"anchor": 1.0, "base": 1.0}, "pass_min": 0.85, "fail_min": 0.9},
  "compliance": {"day": "mon", "band": "1-5", "probs": {"kcal": 0.06, "protein_g": 0.06}, "nutrients": {"kcal": {"min": 450.0, "p_at_or_above_min": 0.06, "interval_90": [141.0, 466.0]}}},
  "assumptions": ["nutrient table row sambar (assumed)"],
  "advisory": {"note": "advisory only — salt is never a verdict nutrient"},
  "model_versions": {"segmenter": "facebook/sam2.1-hiera-large", "classifier": "google/siglip2-base-patch16-224", "depth": "Ruicheng/moge-2-vitl"}
}
```

---

## 📸 Data Capture Procedure (golden set)

Full protocol: [`docs/protocol.md`](docs/protocol.md). Goal: **30 golden plates** — 4 pilot / 13 dev / 13 holdout — for calibration, tuning, and one sealed final evaluation.

### Day-1 setup (do this once, before any capture)

1. **Print the reference card**: `docs/assets/reference_card_A6_300dpi.png` on **A6 paper at 100% scale — turn OFF "fit to page"** (borderless if your printer supports it).
2. **Ruler-check the black square**: it must measure **exactly 100.0 mm (±0.5 mm)**. If off:
   - reprint, **or**
   - measure the actual size and record it in `data/anchor_config.json` → `card.square_mm`, then set `ruler_checked: true` with the date in `ruler_checked_note`.
   - This square is the metric ground truth for every `measured`-tier plate — a 1 mm error here is a 1% scale error in every verdict.
3. **Kitchen scale**: 1 g resolution. Zero it with the **empty vessel on it (tare)** before weighing food. Use the *same* scale and vessels across all splits.

### Per-plate capture — step by step

1. **Table & light**: plain, matte surface; even lighting; no harsh shadows or HDR tricks.
2. **Arrange the plate**: vessel centred, **entire tray/vessel inside the frame** (nothing cropped), food as served (don't restyle it).
3. **Place the card**: reference card flat **beside the vessel on the same surface plane**, fully visible, not overlapping the vessel. Marker must be **≥ 80 px** in the final image (fill roughly ⅛ of the frame width). No card? A ₹10 bimetallic coin (27 mm) beside the vessel is the fallback — if both are present, card wins.
4. **Frame the shot**: slight top-down angle (**tilt < 50°**), whole tray in frame with a little margin, **digital zoom OFF (zoom = 1.0)** — this is a hard gate, the pipeline returns `cannot_verify` on zoomed photos.
5. **Focus on the food** — tap to focus, avoid motion blur, keep original EXIF intact (no messaging-app re-compression; send the original file).
6. **Shoot**, then immediately verify: card/coin sharp? tray fully in frame? no reflections covering the marker?
7. **Weigh** (while the photo is fresh):
   - place empty vessel on scale → record `vessel_g` (tare)
   - serve food in → record total, subtract tare → `total_net_g`
   - **dev/holdout splits: weigh each dish separately** (`per_dish` array) — this is what tunes the composition model.
8. **Record metadata** in the plate's `meta.json` at capture time:

```json
{
  "plate_id": "dev/plate_03",
  "day": "mon", "band": "1-5", "dish": "rice_sambar",
  "serving_style": "mixed",
  "camera": "realme 14T", "captured_at": "2026-10-09T12:40:00",
  "anchor": {"card_present": true, "coin_present": false, "ruler_checked": true},
  "notes": ""
}
```

```json
{
  "vessel_g": 320, "total_net_g": 465,
  "per_dish": [{"name": "rice_sambar", "g": 465}],
  "scale": "kitchen_scale_1g"
}
```

### Folder layout

```
DATASET/golden/
  pilot/plate_01/{photo.jpg, meta.json, weights.json}
  dev/plate_01/...
  holdout/plate_01/...
```

### Splits

| Split | n | Weighing | Purpose |
|---|---|---|---|
| pilot | 4 | tray totals (per plate) | M0b go/no-go: does depth/scale pipeline behave |
| dev | 13 | **per dish** in the tray | tune σ, temperature, composition rules |
| holdout | 13 | **per dish** | M8 — opened **once**; results labeled `indicative` |

- Holdout stays out of any tuning — no peeking at per-plate errors before M8.

### What the pipeline checks for you (capture lint)

| Check | Consequence if violated |
|---|---|
| digital zoom == 1.0 | hard gate → `cannot_verify` |
| min side ≥ 1280 px | note in response; marker tier may fall back |
| card marker ≥ 80 px (or coin) | falls back to prior tier → coverage capped at 0.60, **can never PASS/FAIL** |
| plate weight inside `plate_sanity_g` band (`data/standards.yaml`, ±25%) | flagged only — never auto-rejects |
| day ∈ menu days, dish ∈ `data/menu.yaml` ids | `cannot_verify` |

### Common mistakes that ruin a capture

- 🚫 card at an angle to the vessel or on a different surface (e.g. held in hand) — scale is wrong
- 🚫 card partially covered by the vessel or cropped out of frame — falls to prior tier
- 🚫 digital zoom or heavy crop — protocol violation, `cannot_verify`
- 🚫 shiny reflections washing out the ArUco marker — undetectable, falls to prior
- 🚫 tray cropped (rim outside frame) — area and ring-fit both fail
- 🚫 messaging-app photo transfer (re-compressed, EXIF stripped) — transfer originals

---

## 🎯 Compliance Standards

Policy lives verbatim in `data/standards.yaml` (transcribed from the user's PM POSHAN Food & Nutrition guidelines):

| Class band | Energy (min) | Protein (min) |
|---|---|---|
| 1–5 | 450 kcal | 12 g |
| 6–8 | 700 kcal | 20 g |
| 9–10 | 700 kcal | 20 g *(identical rows in the source doc)* |

- **Verdicts**: PASS needs P ≥ 0.90 *and* coverage ≥ 0.85; FAIL needs P ≤ 0.10 *and* coverage ≥ 0.90; everything else is BORDERLINE
- **Coverage** multiplies ledger factors (anchor tier, base-plane method, capture quality) — a prior-tier anchor caps it at 0.60, so a guessed scale can never FAIL a plate
- **Salt** (2 g primary / 4 g upper) is reported as an advisory only — never a verdict nutrient
- Raw per-child/day gram allocations are surfaced as informational diagnostics, never compared against cooked plate weight

---

## 🌍 SDG Alignment

| SDG | Goal | Target | How NutriSense contributes |
|---|---|---|---|
| SDG 2 | Zero Hunger | **2.2** — end all forms of malnutrition by 2030 | Verifiable per-plate energy & protein adequacy against PM POSHAN minimums — turns *"a meal was served"* into *"the meal met the standard"*, with quantified uncertainty and honest coverage |
| SDG 3 | Good Health and Well-being | **3.4** — reduce premature mortality from non-communicable diseases | Childhood undernutrition tracks into lifelong health risks; per-plate checks make dietary deficits visible early, meal by meal, instead of at annual surveys |
| SDG 4 | Quality Education | **4.1** — ensure free, equitable and quality primary/secondary education | PM POSHAN explicitly aims to lift enrolment, attendance and learning levels; NutriSense protects the meal quality those outcomes depend on |

---

## 👥 Team

| Name | USN | Role |
|---|---|---|
| Aryan Kumar | 1BM23AI037 | System Architecture & Integration |
| Roshanth V | 1BM23AI155 | Food Detection & ML Pipeline |
| S S Gokula Swamy | 1BM23AI158 | Database & Backend |
| Somanath S D | 1BM23AI187 | Agentic AI & Compliance Engine |

**Guide:** Prof. Varsha R, Dept. of Machine Learning, BMSCE

---

## 🏫 Institution

**Department of Machine Learning**
B.M.S. College of Engineering, Bengaluru — 560 019
*(An Autonomous Institute, Affiliated to VTU)*

**Course:** Project Work 2 (24AM7PWPW2)
**Academic Year:** 2026–27

---

## ⚠️ Known Limitations

- **Real-photo segmentation & anchor**: fully validated on synthetic scenes (70 tests green), but real canteen photos currently segment poorly (tiny masks → ~0 g) and the coin detector can false-positive on shiny vessels — the M1/M3 real-world tuning gates. Until those close, treat field results as indicative.
- **Prior tier depth scale** is uncalibrated (`depth_scale_sigma_pct` open at M6).
- **Assumed nutrient rows**: sambar / vegetable_rice / bisi_belee_bath values are literature-plausible assumptions, flagged in every response (`assumptions`).

---

## 📚 References

**Models & methods**

1. Ravi et al. (2024). *SAM 2: Segment Anything in Images and Videos.* arXiv:2408.00714. — image segmentation (S2).
2. Tschannen et al. (2025). *SigLIP 2: Multilingual Vision-Language Encoders with Improved Semantic Understanding, Localization, and Dense Features.* arXiv:2502.14786. Google DeepMind. — dish gallery embeddings (S2).
3. Wang et al. (2025). *MoGe-2: Accurate Monocular Geometry with Metric Scale and Sharp Details.* arXiv:2507.02546 (NeurIPS 2025). Microsoft Research. — metric depth (S3).
4. Garrido-Jurado et al. (2014). *Automatic generation and detection of highly reliable fiducial markers under occlusion.* Pattern Recognition 48(6), 2051–2061. — ArUco reference-card detection (S1 scale anchor).

**Nutrition & policy**

5. National Institute of Nutrition (2017). *Indian Food Composition Tables (IFCT 2017).* NIN, Hyderabad. — literature nutrient rows in `data/nutrients.yaml`.
6. Ministry of Education, Government of India. *PM POSHAN — Food & Nutrition Guidelines.* — band minimums & compliance rules, transcribed into `data/standards.yaml`.
7. Government of Karnataka. *Mid-Day Meal Scheme Guidelines.* Dept. of Public Instruction. — weekly menu in `data/menu.yaml`.
8. SPMCIL. *₹10 bimetallic coin specifications* (27.0 mm diameter). — secondary scale anchor tier.

---

## 📄 License

[MIT](LICENSE) — © 2026 S S Gokula Swamy. Developed for Project Work 2 (2026–27) at B.M.S. College of Engineering. Model/dataset attributions: `docs/licenses.md`.
