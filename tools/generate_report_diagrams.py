# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""High-Resolution Publication-Quality Architectural Diagram Generator for NutriSense Academic Report.

Department of Machine Learning, B.M.S. College of Engineering, Bengaluru.
Generates all 9 system and conceptual diagrams matching the current deployed setup:
  1. Figure 1.1: figure_1_1_problem_context.png
  2. Figure 1.2: figure_1_2_approach_comparison.png
  3. Figure 5.1: system_architecture.png
  4. Figure 5.2: whole_project_flowchart.png
  5. Figure 5.3(a): conceptual_module_diagram.png
  6. Figure 5.3(b): meal_analysis_activity_diagram.png
  7. Figure 5.3(c): nutrisense_use_case_diagram.png
  8. Figure 6.1: backend_frontend_implementation_layout.png
  9. Figure 6.2: nutrition_assessment_and_uncertainty.png
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

OUTPUT_DIR = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report/assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==============================================================================
# Helper Drawing Functions
# ==============================================================================

def add_header(ax, title, subtitle, y_top=0.96):
    ax.text(0.5, y_top, title, ha="center", va="top", fontsize=15, fontweight="bold", color="#0F172A", family="sans-serif")
    ax.text(0.5, y_top - 0.038, subtitle, ha="center", va="top", fontsize=10, style="italic", color="#475569", family="sans-serif")

def draw_card(ax, xy, width, height, title, items, header_bg="#1E293B", body_bg="#FFFFFF", border_color="#CBD5E1", title_color="#FFFFFF", title_fontsize=11, item_fontsize=9, radius=0.015):
    x, y = xy
    # Card outer shadow/border box
    rect = patches.FancyBboxPatch((x, y), width, height, boxstyle=f"round,pad={radius}", ec=border_color, fc=body_bg, lw=1.5, zorder=2)
    ax.add_patch(rect)
    
    # Header bar
    header_h = height * 0.18
    header_rect = patches.FancyBboxPatch((x, y + height - header_h), width, header_h, boxstyle=f"round,pad={radius}", ec=header_bg, fc=header_bg, lw=1.5, zorder=3)
    ax.add_patch(header_rect)
    # Patch lower corners of header so it looks flat at the bottom
    sub_rect = patches.Rectangle((x, y + height - header_h), width, header_h * 0.5, fc=header_bg, ec=header_bg, zorder=3)
    ax.add_patch(sub_rect)

    # Title text
    ax.text(x + width / 2, y + height - header_h / 2, title, ha="center", va="center", fontsize=title_fontsize, fontweight="bold", color=title_color, zorder=4, family="sans-serif")

    # Item text lines
    if items:
        n = len(items)
        avail_h = height - header_h - 0.02
        dy = avail_h / max(n, 1)
        start_y = y + height - header_h - 0.025
        for i, item in enumerate(items):
            cur_y = start_y - i * dy
            if isinstance(item, tuple):
                bullet, txt = item
                ax.text(x + 0.012, cur_y, bullet, ha="left", va="top", fontsize=item_fontsize, fontweight="bold", color="#2563EB", zorder=4, family="sans-serif")
                ax.text(x + 0.032, cur_y, txt, ha="left", va="top", fontsize=item_fontsize, color="#1E293B", zorder=4, family="sans-serif")
            else:
                ax.text(x + 0.015, cur_y, item, ha="left", va="top", fontsize=item_fontsize, color="#1E293B", zorder=4, family="sans-serif")


# ==============================================================================
# Diagram 1: Figure 1.1 Problem Context
# ==============================================================================

def generate_figure_1_1():
    fig, ax = plt.subplots(figsize=(10, 5.4), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 1.1: NutriSense Problem Context & Optical Nutrition Assessment Workflow",
               "Real-World Institutional Feeding Constraints → Single-View RGB AI Inference → Auditable Compliance Output", y_top=0.96)

    # Panel 1: Institutional Reality
    items_p1 = [
        ("•", "High-throughput lunch distribution (>400 students/hour)"),
        ("•", "Varying stainless steel plates, trays & partition thalis"),
        ("•", "Liquid curries, rasam & dal with fluid meniscus surfaces"),
        ("•", "Absence of digital scales; severe manual audit fatigue"),
        ("•", "Dietary gaps: hidden macronutrient and protein deficits"),
        ("•", "Subjective visual inspections lack traceable verification"),
    ]
    draw_card(ax, (0.03, 0.08), 0.28, 0.76, "1. Institutional Canteen Reality", items_p1, header_bg="#B91C1C", border_color="#FCA5A5")

    # Arrow 1 -> 2
    ax.annotate("", xy=(0.34, 0.46), xytext=(0.315, 0.46),
                arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=2.5, mutation_scale=18), zorder=5)

    # Panel 2: Single-View RGB Optical Capture & Dual-Mode Scale
    items_p2 = [
        ("•", "Single top-down RGB capture via accessible smartphone"),
        ("•", "Mode A (Fiducial): 60 mm ArUco marker (DICT_4X4_50)"),
        (" ", "  └ Michelson contrast CM >= 0.42 quiet-zone verification"),
        (" ", "  └ Homography & camera pose: 0.74 mm RMS error"),
        ("•", "Mode B (Card-Free Breakthrough): Zero-marker intake"),
        (" ", "  └ Base tabletop annulus RANSAC plane fitting"),
        (" ", "  └ ImplicitScaleHead (6-Fold LODO-CV, 77.0% acc)"),
        (" ", "  └ 80.1% Volume Bias Reduction (-223.5 g → -44.4 g)"),
    ]
    draw_card(ax, (0.355, 0.08), 0.29, 0.76, "2. Single-View Optical Capture & Scale", items_p2, header_bg="#1D4ED8", border_color="#93C5FD")

    # Arrow 2 -> 3
    ax.annotate("", xy=(0.675, 0.46), xytext=(0.65, 0.46),
                arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=2.5, mutation_scale=18), zorder=5)

    # Panel 3: Metrological AI Assessment & Decisions
    items_p3 = [
        ("•", "SAM 2.1 Hiera + DeepLabV3 (95.81% foreground Dice)"),
        ("•", "Liquid bowl / katori detector (LIQUID_BOWL_CLASSES)"),
        ("•", "SigLIP-2 ViT-B/16 (82.27% Top-1) + 115 Indian Dish Hub"),
        ("•", "MoGe-2 3D Metric Depth + DINOv2-S Mass Head Fusion"),
        ("•", "ICMR-NIN IFCT 2017 & INDB 1,014 Recipe Knowledge Base"),
        ("•", "Comonotonic 4,000-draw Monte Carlo uncertainty bounds"),
        ("•", "PM POSHAN Verdict: PASS / FAIL / BORDERLINE [p05, p95]"),
    ]
    draw_card(ax, (0.69, 0.08), 0.28, 0.76, "3. Metrological 3D Assessment & Output", items_p3, header_bg="#047857", border_color="#6EE7B7")

    out_path = os.path.join(OUTPUT_DIR, "figure_1_1_problem_context.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 2: Figure 1.2 Approach Comparison
# ==============================================================================

def generate_figure_1_2():
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 1.2: Architectural Comparison: Conventional 2D Approaches vs. NutriSense 3D Metrological Pipeline",
               "Structural Contrast between Heuristic Pixel Counting and Physics-Grounded 3D Metric Computer Vision", y_top=0.96)

    # Left: Conventional 2D Approaches
    items_conv = [
        ("✗", "2D Bounding Boxes: YOLO / Faster R-CNN rectangular approximations; fails on free-form piles"),
        ("✗", "Arbitrary Pixel Multipliers: Multiplies pixel area by magic constant; completely blind to 3D depth"),
        ("✗", "Flat Food Assumption: Treats 150g rice mound and 20g flat dosa as identical 2D surface areas"),
        ("✗", "Generic Western Food Tables: Relies on US USDA tables; ignores Indian spices, water and dal dilution"),
        ("✗", "Deterministic Point Estimates: Outputs single number (e.g. '520 kcal') hiding massive unmeasured error"),
        ("✗", "Opaque Binary Verdict: Black-box pass/fail with zero explainability, no audit trail, and silent failures"),
    ]
    draw_card(ax, (0.04, 0.08), 0.43, 0.76, "Conventional 2D Food Analysis (Heuristic & Fragile)", items_conv,
              header_bg="#DC2626", body_bg="#FEF2F2", border_color="#FCA5A5", item_fontsize=8.5)

    # Right: NutriSense 3D Metrological Pipeline
    items_nutri = [
        ("✓", "Promptable Instance Segmentation: SAM 2.1 Hiera-Large + DeepLabV3 (95.81% FG Dice, 82.11% food IoU)"),
        ("✓", "Metric 3D Unprojection: MoGe-2 dense surface reconstruction with RANSAC tabletop support plane"),
        ("✓", "Dual-Mode Scale Anchoring: 60mm ArUco fiducial (0.74 mm RMS) & Card-Free Mode B ImplicitScaleHead"),
        ("✓", "Calibrated Mass Fusion: Inverse-variance fusion (~82% geometric volume × density, ~18% DINOv2-S head)"),
        ("✓", "Indian Domain Grounding: ICMR-NIN IFCT 2017 & INDB 1,014 cooked recipes + 115 regional dish hub"),
        ("✓", "Statutory Metrology: 4,000-draw comonotonic Monte Carlo [p05, p50, p95] + PM POSHAN audit engine"),
    ]
    draw_card(ax, (0.53, 0.08), 0.43, 0.76, "NutriSense Metrological Pipeline (Physics-Grounded 3D AI)", items_nutri,
              header_bg="#059669", body_bg="#F0FDF4", border_color="#86EFAC", item_fontsize=8.5)

    out_path = os.path.join(OUTPUT_DIR, "figure_1_2_approach_comparison.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 3: Figure 5.1 System Architecture
# ==============================================================================

def generate_figure_5_1():
    fig, ax = plt.subplots(figsize=(12, 10.5), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 5.1: NutriSense Multi-Stage Metrological System Architecture",
               "Six-Stage Deep Vision & Compliance Pipeline: Client → Gateway → GPU Pipeline → Metrology → Audit Store", y_top=0.97)

    # 1. Client Layer
    items_client = [
        ("•", "React 19 + TypeScript + Vite | Tailwind CSS + Accessible Color Tokens"),
        ("•", "Responsive Topbar Navigation (Home · Analyze · History · Insights · Students · Menu · Settings)"),
        ("•", "Dynamic Multi-Item Canvas Segmentation Mask Overlays & Real-Time Confidence Dials"),
        ("•", "Conversational Meal Coach / Critique Drawer & PM POSHAN Statutory Standards Dashboard"),
    ]
    draw_card(ax, (0.05, 0.81), 0.90, 0.12, "Client Presentation Layer (Browser Web Application)", items_client, header_bg="#0284C7", border_color="#7DD3FC", item_fontsize=8.5)

    # Arrow Down
    ax.annotate("", xy=(0.50, 0.795), xytext=(0.50, 0.81), arrowprops=dict(facecolor="#0284C7", edgecolor="#0284C7", arrowstyle="->", lw=2), zorder=5)

    # 2. Gateway Layer
    items_gw = [
        ("•", "FastAPI Service (Port 8000) | Uvicorn + AnyIO Bounded Inference Queue | 12 MiB Upload Limit"),
        ("•", "19-Key Cryptographic JSON Wire Contract (engine/contract.py ↔ frontend/src/types/contract.gen.ts)"),
        ("•", "Input Quality Gates: Digital Zoom Check, Resolution (≥800×800), Day & Class-Band Validation"),
        ("•", "CUDA Out-Of-Memory Guard: Automatic GPU registry cache flush & retry with memory protection"),
    ]
    draw_card(ax, (0.05, 0.66), 0.90, 0.12, "API Gateway & Wire Contract Tier (FastAPI + Pydantic v2)", items_gw, header_bg="#1E293B", border_color="#94A3B8", item_fontsize=8.5)

    # Arrow Down
    ax.annotate("", xy=(0.50, 0.645), xytext=(0.50, 0.66), arrowprops=dict(facecolor="#1E293B", edgecolor="#1E293B", arrowstyle="->", lw=2), zorder=5)

    # 3. Deep Learning Core Stages (3 columns)
    # Stage S1: Scale
    items_s1 = [
        ("Mode A:", "60 mm ArUco Marker (DICT_4X4_50)"),
        (" ", "  CM >= 0.42 Michelson quiet-zone"),
        (" ", "  Homography: 0.74 mm RMS error"),
        ("Mode B:", "Card-Free ImplicitScaleHead"),
        (" ", "  Tabletop annulus RANSAC plane"),
        (" ", "  6-Fold LODO-CV: 77.0% scale acc"),
        (" ", "  80.1% volume bias reduction"),
    ]
    draw_card(ax, (0.05, 0.35), 0.28, 0.28, "Stage S1: Dual-Mode Scale Anchor", items_s1, header_bg="#D97706", border_color="#FCD34D", item_fontsize=8.0)

    # Stage S2: Segmentation & Classification
    items_s2 = [
        ("•", "SAM 2.1 Hiera + DeepLabV3 (95.8% Dice)"),
        ("•", "Vessel Liquid Detector (LIQUID_BOWL)"),
        ("•", "Dynamic Multi-Item Meal Parsing:"),
        (" ", "  Indian Thali (X Items) / Rice + Rasam"),
        ("•", "SigLIP-2 ViT-B/16 (α=0.65, 82.3% Top-1)"),
        ("•", "115 Regional Indian Dish Knowledge Hub"),
        (" ", "  1,206 Bharat & Rajistics Visual Prototypes"),
    ]
    draw_card(ax, (0.36, 0.35), 0.28, 0.28, "Stage S2: Segmentation & Classification", items_s2, header_bg="#7C3AED", border_color="#C4B5FD", item_fontsize=8.0)

    # Stage S3: Depth & Mass Fusion
    items_s3 = [
        ("•", "MoGe-2 ViT-L Metric Depth Estimation"),
        ("•", "Tabletop Support Plane Regression"),
        ("•", "DINOv2-S Heteroscedastic Mass Head"),
        (" ", "  DEV MAE: 15.03 g (81.7% accuracy)"),
        (" ", "  LOCKED MAE: 14.67 g (80.0% accuracy)"),
        ("•", "Inverse-Variance Precision Mass Fusion:"),
        (" ", "  ~82% Geometry Volume + ~18% Learned"),
    ]
    draw_card(ax, (0.67, 0.35), 0.28, 0.28, "Stage S3: 3D Depth & Mass Estimation", items_s3, header_bg="#2563EB", border_color="#93C5FD", item_fontsize=8.0)

    # Horizontal connector between S1, S2, S3
    ax.annotate("", xy=(0.35, 0.49), xytext=(0.33, 0.49), arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=2), zorder=5)
    ax.annotate("", xy=(0.66, 0.49), xytext=(0.64, 0.49), arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=2), zorder=5)

    # Arrow Down to Compliance
    ax.annotate("", xy=(0.50, 0.33), xytext=(0.50, 0.35), arrowprops=dict(facecolor="#059669", edgecolor="#059669", arrowstyle="->", lw=2), zorder=5)

    # 4. Stage S4 & S5: Nutritional Metrology & Compliance
    items_compliance = [
        ("•", "Nutritional Database: Grounded ICMR-NIN IFCT 2017 & INDB Master (1,014 Cooked Indian Recipes)"),
        ("•", "Comonotonic Monte Carlo Engine: 4,000 paired draws propagating portion mass and density variances"),
        ("•", "Confidence Calibration: Returns rigorous [p05, p50, p95] bounds for volume (ml), mass (g), kcal, and protein (g)"),
        ("•", "Statutory PM POSHAN Rule Engine: Primary (450 kcal / 12g) & Upper-Primary (700 kcal / 20g) statutory compliance audit"),
    ]
    draw_card(ax, (0.05, 0.18), 0.90, 0.14, "Stage S4 & S5: Nutritional Metrology & Comonotonic Compliance Engine", items_compliance, header_bg="#059669", border_color="#86EFAC", item_fontsize=8.5)

    # Arrow Down to Storage
    ax.annotate("", xy=(0.50, 0.165), xytext=(0.50, 0.18), arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=2), zorder=5)

    # 5. Storage & Governance Tier
    items_storage = [
        ("•", "Audit Trail: Longitudinal JSON/SQLite Storage | Cryptographic Evaluation Lock (502/502 Pinned Sha256 Hashes)"),
        ("•", "Regression Gateways: 385 Automated Tests (381 unit, 4 red-team chaos audit) | Zero-Leakage WED DEV / LOCKED Splits"),
    ]
    draw_card(ax, (0.05, 0.05), 0.90, 0.10, "Persistence, Audit Governance & Zero-Leakage Evaluation Tier", items_storage, header_bg="#334155", border_color="#94A3B8", item_fontsize=8.5)

    out_path = os.path.join(OUTPUT_DIR, "system_architecture.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 4: Figure 5.2 Whole-Project Flowchart
# ==============================================================================

def generate_figure_5_2():
    fig, ax = plt.subplots(figsize=(11, 14), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 5.2: NutriSense End-to-End Decision Flowchart",
               "Step-by-Step Logic Execution: Capture Validation → Scale Anchoring → Multi-Item Decomposition → Compliance Verdict", y_top=0.98)

    # Helper for flowchart boxes
    def draw_node(xy, width, height, text, bg="#FFFFFF", ec="#1E293B", text_color="#1E293B", shape="rect", fontsize=8.5, bold=False):
        x, y = xy
        if shape == "round":
            box = patches.FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.015", ec=ec, fc=bg, lw=1.5, zorder=3)
        elif shape == "diamond":
            box = patches.Polygon([[x + width/2, y], [x + width, y + height/2], [x + width/2, y + height], [x, y + height/2]],
                                  ec=ec, fc=bg, lw=1.5, zorder=3)
        else:
            box = patches.Rectangle((x, y), width, height, ec=ec, fc=bg, lw=1.5, zorder=3)
        ax.add_patch(box)
        weight = "bold" if bold else "normal"
        ax.text(x + width/2, y + height/2, text, ha="center", va="center", fontsize=fontsize, color=text_color, fontweight=weight, zorder=4, family="sans-serif")

    def draw_arrow(start, end, label=""):
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=1.8), zorder=5)
        if label:
            mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            ax.text(mid[0] + 0.012, mid[1], label, fontsize=8, fontweight="bold", color="#B91C1C", zorder=6, family="sans-serif")

    # Flowchart Nodes (Top to Bottom)
    # 1. Start Node
    draw_node((0.36, 0.92), 0.28, 0.035, "START: Meal Capture Upload\n(RGB Photo + Context: Day, Class Band 1-5/6-8)", bg="#DBEAFE", ec="#2563EB", shape="round", bold=True)
    draw_arrow((0.50, 0.92), (0.50, 0.885))

    # 2. Input Gates
    draw_node((0.28, 0.84), 0.44, 0.045, "Input Validation Gates (engine/gates.py)\nUpload Size <= 12 MiB | Res >= 800x800 | Digital Zoom Check", bg="#F1F5F9", ec="#475569")
    draw_arrow((0.50, 0.84), (0.50, 0.805))

    # Gate Decision
    draw_node((0.38, 0.745), 0.24, 0.055, "Pass Input\nGates?", bg="#FEF3C7", ec="#D97706", shape="diamond", bold=True)
    draw_arrow((0.50, 0.745), (0.50, 0.69), "YES")
    # Gate Fail branch
    draw_arrow((0.62, 0.772), (0.76, 0.772), "NO")
    draw_node((0.76, 0.75), 0.20, 0.045, "ABSTAIN / 422\nReturn Structured Failure", bg="#FEE2E2", ec="#DC2626", text_color="#991B1B", shape="round")

    # 3. ArUco Marker Check
    draw_node((0.37, 0.635), 0.26, 0.055, "ArUco 60mm Marker\nCM >= 0.42 Quiet Zone?", bg="#FEF3C7", ec="#D97706", shape="diamond", bold=True)
    # Branch A: Mode A
    draw_arrow((0.37, 0.662), (0.24, 0.662), "YES (Mode A)")
    draw_node((0.06, 0.64), 0.18, 0.045, "Stage S1a: Physical Fiducial\nHomography & Pose Fit\n(0.74 mm RMS Error)", bg="#DCFCE7", ec="#16A34A")
    # Branch B: Mode B
    draw_arrow((0.63, 0.662), (0.76, 0.662), "NO (Mode B)")
    draw_node((0.76, 0.64), 0.18, 0.045, "Stage S1b: Card-Free\nImplicitScaleHead LODO-CV\n(80.1% Volume Bias Cut)", bg="#E0E7FF", ec="#4338CA")

    # Merge to Segmentation
    draw_arrow((0.15, 0.64), (0.42, 0.58))
    draw_arrow((0.85, 0.64), (0.58, 0.58))

    # 4. Stage S2: Segmentation & Vessel Detection
    draw_node((0.26, 0.535), 0.48, 0.045, "Stage S2: Promptable SAM 2.1 Hiera + DeepLabV3\nForeground Mask Proposal + Katori Liquid Bowl Promotion", bg="#F3E8FF", ec="#7C3AED", bold=True)
    draw_arrow((0.50, 0.535), (0.50, 0.495))

    # Multi-Item Parsing Decision
    draw_node((0.38, 0.435), 0.24, 0.055, "Number of Food\nItems / Vessels?", bg="#FEF3C7", ec="#D97706", shape="diamond", bold=True)
    draw_arrow((0.38, 0.462), (0.22, 0.462), ">= 3 Items")
    draw_node((0.05, 0.44), 0.17, 0.045, "Indian Thali Multi-Item\nDecompose Rice, Rasam,\nDal & Curries", bg="#FEF3C7", ec="#D97706")
    draw_arrow((0.62, 0.462), (0.77, 0.462), "1-2 Items")
    draw_node((0.77, 0.44), 0.17, 0.045, "Dual / Single Item\nRice + Rasam / Biryani\nFocused Crop Extraction", bg="#FEF3C7", ec="#D97706")

    # Merge to Classification
    draw_arrow((0.135, 0.44), (0.42, 0.38))
    draw_arrow((0.855, 0.44), (0.58, 0.38))

    # 5. Dish Classification
    draw_node((0.26, 0.335), 0.48, 0.045, "Stage S2b: SigLIP-2 ViT-B/16 Regional Indian Dish Hub\n1,206 Bharat & Rajistics Visual Prototypes + 115 Text Prompts (82.27% Top-1)", bg="#F3E8FF", ec="#7C3AED")
    draw_arrow((0.50, 0.335), (0.50, 0.295))

    # 6. Stage S3: 3D Depth & Mass Estimation
    draw_node((0.22, 0.245), 0.56, 0.050, "Stage S3: MoGe-2 3D Metric Depth Unprojection + Tabletop RANSAC Fit\nInverse-Variance Fusion (~82% Geometry Volume x Density + ~18% DINOv2-S Mass Head)", bg="#EFF6FF", ec="#2563EB", bold=True)
    draw_arrow((0.50, 0.245), (0.50, 0.205))

    # 7. Stage S4 & S5: Nutritional Engine & Monte Carlo
    draw_node((0.20, 0.155), 0.60, 0.050, "Stage S4 & S5: ICMR-NIN IFCT 2017 & INDB 1,014 Recipe Lookup\n4,000-Draw Comonotonic Monte Carlo Uncertainty Bounds [p05, p50, p95]", bg="#ECFDF5", ec="#059669", bold=True)
    draw_arrow((0.50, 0.155), (0.50, 0.115))

    # Compliance Decision
    draw_node((0.36, 0.06), 0.28, 0.055, "P(E >= Emin) >= 0.90\nAND P(P >= Pmin) >= 0.90\nAND Coverage >= 0.85?", bg="#FEF3C7", ec="#D97706", shape="diamond", bold=True)
    
    # Verdicts
    draw_arrow((0.36, 0.087), (0.18, 0.087), "YES")
    draw_node((0.04, 0.065), 0.14, 0.045, "VERDICT: PASS\nStatutory Target Met", bg="#DCFCE7", ec="#16A34A", text_color="#15803D", shape="round", bold=True)

    draw_arrow((0.50, 0.06), (0.50, 0.035), "NO")
    draw_node((0.41, 0.005), 0.18, 0.030, "VERDICT: FAIL\nNutritional Deficit", bg="#FEE2E2", ec="#DC2626", text_color="#B91C1C", shape="round", bold=True)

    draw_arrow((0.64, 0.087), (0.80, 0.087), "BORDERLINE")
    draw_node((0.80, 0.065), 0.16, 0.045, "VERDICT: BORDERLINE\nUncertainty / Deficit Warning", bg="#FEF9C3", ec="#CA8A04", text_color="#854D0E", shape="round", bold=True)

    out_path = os.path.join(OUTPUT_DIR, "whole_project_flowchart.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 5: Figure 5.3a Conceptual Class & Module Diagram
# ==============================================================================

def generate_figure_5_3a():
    fig, ax = plt.subplots(figsize=(13, 8.2), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 5.3(a): NutriSense Conceptual Class and Modular Architecture Diagram",
               "Decoupled Service-Oriented Subsystems: Ingestion → Vision Models → Metrology → Compliance → Contract", y_top=0.97)

    # 8 UML Class Cards
    # 1. FastAPI Application
    c1 = [
        ("+ app: FastAPI"),
        ("+ /analyze(image, day, band): JSON"),
        ("+ /health(): StatusResponse"),
        ("+ /meal-critique(analysis): Critique"),
    ]
    draw_card(ax, (0.04, 0.65), 0.20, 0.26, "FastAPI Service (main.py)", c1, header_bg="#0284C7", item_fontsize=7.5)

    # 2. Pipeline Orchestrator
    c2 = [
        ("+ run(image, context): Analysis"),
        ("+ validate_gates(): GateResult"),
        ("+ dispatch_scale(): AnchorResult"),
        ("+ fuse_mass(): MassDistribution"),
    ]
    draw_card(ax, (0.28, 0.65), 0.20, 0.26, "Pipeline (engine.pipeline)", c2, header_bg="#1E293B", item_fontsize=7.5)

    # 3. Scale Anchor
    c3 = [
        ("+ detect_aruco(rgb): AnchorA"),
        ("+ cm_per_pixel: float"),
        ("+ estimate_implicit(rgb): AnchorB"),
        ("+ annulus_plane_fit(): PlaneEq"),
    ]
    draw_card(ax, (0.52, 0.65), 0.20, 0.26, "Scale Anchor (models.scale)", c3, header_bg="#D97706", item_fontsize=7.5)

    # 4. SAM 2.1 Segmenter
    c4 = [
        ("+ segment(rgb): List[Mask]"),
        ("+ detect_liquid_bowls(): Bowls"),
        ("+ filter_candidates(): CleanMasks"),
        ("+ decompose_thali(): Items"),
    ]
    draw_card(ax, (0.76, 0.65), 0.20, 0.26, "Segmenter (models.segmenter)", c4, header_bg="#7C3AED", item_fontsize=7.5)

    # Row 2
    # 5. Food Classifier
    c5 = [
        ("+ embed(crop): Tensor[768]"),
        ("+ classify(embedding): TopK"),
        ("+ gallery: 115 Indian Dishes"),
        ("+ prototypes: 1,206 vectors"),
    ]
    draw_card(ax, (0.04, 0.32), 0.20, 0.26, "Classifier (models.classifier)", c5, header_bg="#7C3AED", item_fontsize=7.5)

    # 6. Depth & Geometry Engine
    c6 = [
        ("+ infer_depth(rgb): MetricDepthMap"),
        ("+ fit_tabletop_plane(): NormalVec"),
        ("+ compute_volume(mask, depth): ml"),
        ("+ unproject_pcd(): PointCloud3D"),
    ]
    draw_card(ax, (0.28, 0.32), 0.20, 0.26, "Depth Engine (engine.depth)", c6, header_bg="#2563EB", item_fontsize=7.5)

    # 7. Mass Estimation Head
    c7 = [
        ("+ extract_dinov2_features(): Tensor"),
        ("+ predict_mass(features): (mu, var)"),
        ("+ fuse_mass(geo_mass, mlp_mass): g"),
        ("+ uncertainty_variance: float"),
    ]
    draw_card(ax, (0.52, 0.32), 0.20, 0.26, "Weight Head (models.weight)", c7, header_bg="#2563EB", item_fontsize=7.5)

    # 8. Nutrition & Compliance Engine
    c8 = [
        ("+ lookup_ifct(dish_id): Nutrients"),
        ("+ monte_carlo_draws(4000): Dist"),
        ("+ evaluate_poshan(dist, band): Verdict"),
        ("+ coverage_score(): [0, 1]"),
    ]
    draw_card(ax, (0.76, 0.32), 0.20, 0.26, "Metrology (engine.compliance)", c8, header_bg="#059669", item_fontsize=7.5)

    # Bottom: Wire Contract Box
    items_contract = [
        ("•", "19-Key Cryptographic JSON Contract (engine/contract.py ↔ frontend/src/types/contract.gen.ts)"),
        ("•", "Keys: id, createdAt, verdict, dish, grams, kcal, protein_g, coverage, confidence, intervals [p05, p50, p95], items, reasons, failures"),
    ]
    draw_card(ax, (0.04, 0.06), 0.92, 0.20, "Auditable Wire Contract Specification (AnalysisContract)", items_contract, header_bg="#334155", item_fontsize=8.5)

    out_path = os.path.join(OUTPUT_DIR, "conceptual_module_diagram.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 6: Figure 5.3b Activity Diagram
# ==============================================================================

def generate_figure_5_3b():
    fig, ax = plt.subplots(figsize=(12, 11), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 5.3(b): NutriSense Meal Analysis Activity Diagram across System Swimlanes",
               "Sequential Processing Swimlanes: Client → Gateway → GPU Pipeline → Nutritional Metrology → Audit Store", y_top=0.97)

    # 5 Swimlanes
    lanes = [
        ("Browser Client\n(React 19 + Vite)", 0.03, 0.17, "#E0F2FE", "#0284C7"),
        ("FastAPI Gateway\n(Port 8000)", 0.22, 0.17, "#F1F5F9", "#475569"),
        ("PyTorch GPU Worker\n(RTX 4060 CUDA FP16)", 0.41, 0.21, "#EDE9FE", "#7C3AED"),
        ("Nutritional Metrology\n(IFCT / INDB Engine)", 0.64, 0.17, "#DCFCE7", "#059669"),
        ("Institutional Audit\n(SQLite / JSON Log)", 0.83, 0.14, "#FEF3C7", "#D97706"),
    ]

    for title, x, w, bg, ec in lanes:
        rect = patches.Rectangle((x, 0.05), w, 0.87, fc=bg, ec=ec, lw=1.2, linestyle="--", alpha=0.6, zorder=1)
        ax.add_patch(rect)
        hdr = patches.Rectangle((x, 0.86), w, 0.06, fc=ec, ec=ec, zorder=2)
        ax.add_patch(hdr)
        ax.text(x + w/2, 0.89, title, ha="center", va="center", fontsize=8.5, fontweight="bold", color="#FFFFFF", zorder=3, family="sans-serif")

    def act_box(xy, w, h, txt, bg="#FFFFFF", ec="#1E293B", bold=False):
        x, y = xy
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01", ec=ec, fc=bg, lw=1.5, zorder=4)
        ax.add_patch(box)
        weight = "bold" if bold else "normal"
        ax.text(x + w/2, y + h/2, txt, ha="center", va="center", fontsize=7.5, color="#1E293B", fontweight=weight, zorder=5, family="sans-serif")

    def act_arrow(start, end):
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=1.5), zorder=6)

    # Activity steps
    # 1. Capture in Client
    act_box((0.04, 0.78), 0.15, 0.045, "Select Image + Context\n(Day, Class Band 1-5)")
    act_arrow((0.19, 0.80), (0.23, 0.80))

    # 2. Gateway Gates
    act_box((0.23, 0.77), 0.15, 0.055, "Validate Input Gates\nDigital Zoom & Res Check")
    act_arrow((0.305, 0.77), (0.305, 0.71))

    # 3. Gateway Rate limit & enqueue
    act_box((0.23, 0.66), 0.15, 0.045, "Enqueue Task in Worker\nBounded Queue (AnyIO)")
    act_arrow((0.38, 0.68), (0.42, 0.68))

    # 4. GPU Scale Anchor
    act_box((0.42, 0.655), 0.19, 0.050, "Stage S1: Scale Anchor\nArUco or ImplicitScaleHead", bg="#FEF9C3", ec="#CA8A04")
    act_arrow((0.515, 0.655), (0.515, 0.595))

    # 5. GPU Segmentation & Classification
    act_box((0.42, 0.54), 0.19, 0.050, "Stage S2: SAM 2.1 Hiera\n+ SigLIP-2 115 Indian Dishes", bg="#EDE9FE", ec="#7C3AED")
    act_arrow((0.515, 0.54), (0.515, 0.48))

    # 6. GPU MoGe-2 3D Depth & Mass Head
    act_box((0.42, 0.425), 0.19, 0.050, "Stage S3: MoGe-2 Unprojection\n+ DINOv2 Mass Head Fusion", bg="#EFF6FF", ec="#2563EB")
    act_arrow((0.61, 0.45), (0.65, 0.45))

    # 7. Nutritional Engine Lookup
    act_box((0.65, 0.42), 0.15, 0.055, "Stage S4: Grounded Lookup\nICMR-NIN IFCT & INDB", bg="#DCFCE7", ec="#16A34A")
    act_arrow((0.725, 0.42), (0.725, 0.35))

    # 8. Monte Carlo Simulation
    act_box((0.65, 0.29), 0.15, 0.055, "Stage S5: Comonotonic MC\n4,000 Draws [p05, p95]", bg="#DCFCE7", ec="#16A34A")
    act_arrow((0.725, 0.29), (0.725, 0.22))

    # 9. PM POSHAN Compliance Verdict
    act_box((0.65, 0.16), 0.15, 0.055, "Statutory Rule Engine\nPASS / FAIL / BORDERLINE", bg="#DCFCE7", ec="#16A34A", bold=True)

    # Persist in Audit Store
    act_arrow((0.80, 0.187), (0.84, 0.187))
    act_box((0.84, 0.16), 0.12, 0.055, "Save Audit Record\n(Immutable Log)", bg="#FEF3C7", ec="#D97706")

    # Return to Gateway -> Client
    act_arrow((0.725, 0.16), (0.305, 0.13))
    act_box((0.23, 0.10), 0.15, 0.045, "Serialize 19-Key JSON\n(AnalysisContract)")
    act_arrow((0.23, 0.12), (0.19, 0.12))
    act_box((0.04, 0.095), 0.15, 0.055, "Render Mask Overlays,\nNutrition Dials & Coach", bg="#DBEAFE", ec="#2563EB", bold=True)

    out_path = os.path.join(OUTPUT_DIR, "meal_analysis_activity_diagram.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 7: Figure 5.3c Use Case Diagram
# ==============================================================================

def generate_figure_5_3c():
    fig, ax = plt.subplots(figsize=(11, 7.2), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 5.3(c): NutriSense Use Case Diagram across Institutional Stakeholders",
               "Separation of Concerns: School Headmaster · Kitchen Supervisor · Field Auditor · System Administrator", y_top=0.96)

    # Draw System Boundary Box
    sys_box = patches.FancyBboxPatch((0.24, 0.06), 0.52, 0.84, boxstyle="round,pad=0.02", ec="#1E293B", fc="#F8FAFC", lw=2, zorder=1)
    ax.add_patch(sys_box)
    ax.text(0.50, 0.88, "NutriSense Application System Boundary", ha="center", va="center", fontsize=10, fontweight="bold", color="#0F172A", zorder=2, family="sans-serif")

    # Actors Left
    ax.text(0.10, 0.72, "School Headmaster /\nPrincipal", ha="center", va="center", fontsize=9, fontweight="bold", color="#1E293B", zorder=3)
    ax.text(0.10, 0.28, "Canteen Cook /\nKitchen Supervisor", ha="center", va="center", fontsize=9, fontweight="bold", color="#1E293B", zorder=3)

    # Actors Right
    ax.text(0.90, 0.72, "PM POSHAN Field\nInspector / Officer", ha="center", va="center", fontsize=9, fontweight="bold", color="#1E293B", zorder=3)
    ax.text(0.90, 0.28, "ML Research Engineer /\nSystem Administrator", ha="center", va="center", fontsize=9, fontweight="bold", color="#1E293B", zorder=3)

    # Use Case Ovals in Center
    use_cases = [
        ((0.36, 0.76), 0.28, 0.055, "UC-1: Upload & Validate Meal Photograph"),
        ((0.36, 0.66), 0.28, 0.055, "UC-2: Estimate 3D Portion Mass (Dual-Mode S1)"),
        ((0.36, 0.56), 0.28, 0.055, "UC-3: Multi-Item Food & Liquid Segmentation"),
        ((0.36, 0.46), 0.28, 0.055, "UC-4: Verify PM POSHAN Compliance Status"),
        ((0.36, 0.36), 0.28, 0.055, "UC-5: Review Comonotonic Monte Carlo Bounds"),
        ((0.36, 0.26), 0.28, 0.055, "UC-6: Query Conversational Dietary Critique"),
        ((0.36, 0.16), 0.28, 0.055, "UC-7: Audit Historical Roster & Daily Logs"),
        ((0.36, 0.07), 0.28, 0.055, "UC-8: Manage Menu & Ingest IFCT/INDB Data"),
    ]

    for (x, y), w, h, label in use_cases:
        oval = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015", ec="#2563EB", fc="#EFF6FF", lw=1.5, zorder=4)
        ax.add_patch(oval)
        ax.text(x + w/2, y + h/2, label, ha="center", va="center", fontsize=8, fontweight="bold", color="#1E293B", zorder=5, family="sans-serif")

    # Connect lines from actors to use cases
    # Headmaster -> UC1, UC4, UC7
    ax.plot([0.18, 0.36], [0.72, 0.78], color="#64748B", lw=1.2, zorder=2)
    ax.plot([0.18, 0.36], [0.72, 0.48], color="#64748B", lw=1.2, zorder=2)
    ax.plot([0.18, 0.36], [0.72, 0.18], color="#64748B", lw=1.2, zorder=2)

    # Kitchen Supervisor -> UC1, UC2, UC6
    ax.plot([0.18, 0.36], [0.28, 0.76], color="#64748B", lw=1.2, zorder=2)
    ax.plot([0.18, 0.36], [0.28, 0.68], color="#64748B", lw=1.2, zorder=2)
    ax.plot([0.18, 0.36], [0.28, 0.28], color="#64748B", lw=1.2, zorder=2)

    # Field Inspector -> UC4, UC5, UC7
    ax.plot([0.82, 0.64], [0.72, 0.48], color="#64748B", lw=1.2, zorder=2)
    ax.plot([0.82, 0.64], [0.72, 0.38], color="#64748B", lw=1.2, zorder=2)
    ax.plot([0.82, 0.64], [0.72, 0.18], color="#64748B", lw=1.2, zorder=2)

    # ML Admin -> UC2, UC3, UC8
    ax.plot([0.82, 0.64], [0.28, 0.68], color="#64748B", lw=1.2, zorder=2)
    ax.plot([0.82, 0.64], [0.28, 0.58], color="#64748B", lw=1.2, zorder=2)
    ax.plot([0.82, 0.64], [0.28, 0.09], color="#64748B", lw=1.2, zorder=2)

    out_path = os.path.join(OUTPUT_DIR, "nutrisense_use_case_diagram.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 8: Figure 6.1 Backend & Frontend Implementation Layout
# ==============================================================================

def generate_figure_6_1():
    fig, ax = plt.subplots(figsize=(12, 8.5), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 6.1: NutriSense Repository and Technical Implementation Architecture",
               "Clean Separation between Backend FastAPI Engine, Synchronized Wire Contract, and React 19 Frontend", y_top=0.97)

    # Box 1: Backend Modules (engine/, models/, server/)
    items_be = [
        ("•", "main.py: FastAPI entrypoint, CORS, rate limits, /analyze, /health, /meal-critique, /meal-chat"),
        ("•", "engine/pipeline.py: Master 6-stage sequential deep-learning inference orchestrator"),
        ("•", "engine/depth.py: MoGe-2 ViT-L dense metric depth unprojection & tabletop RANSAC plane fit"),
        ("•", "models/scale_anchor.py & implicit_scale.py: Dual-mode fiducial ArUco (60mm) & Card-Free Mode B"),
        ("•", "models/dish_segmenter.py: SAM 2.1 Hiera + DeepLabV3 promptable multi-item instance segmentation"),
        ("•", "models/food_classifier.py: SigLIP-2 ViT-B/16 (α=0.65) + 115 regional Indian dish prototype gallery"),
        ("•", "models/weight_head.py: DINOv2-S heteroscedastic mass head + inverse-variance precision fusion"),
        ("•", "engine/mc.py & compliance.py: 4,000-draw comonotonic Monte Carlo engine & statutory PM POSHAN rules"),
    ]
    draw_card(ax, (0.04, 0.50), 0.44, 0.41, "Backend Service (engine/, models/, server/)", items_be, header_bg="#1E293B", border_color="#CBD5E1", item_fontsize=8.0)

    # Box 2: Frontend Modules (frontend/src/)
    items_fe = [
        ("•", "App.tsx & Topbar.tsx: Unified responsive navigation (Home · Analyze · History · Insights · Menu)"),
        ("•", "pages/Dashboard.tsx: Live canteen operational view, daily meal tallies & quick upload intake"),
        ("•", "pages/Analyze.tsx & pages/Result.tsx: Multi-item canvas mask overlays, dials & confidence gauges"),
        ("•", "pages/Menu.tsx: Statutory PM POSHAN Mid-Day Meal targets & ICMR-NIN IFCT 2017 nutritional benchmarks"),
        ("•", "pages/Analytics.tsx & History.tsx: Longitudinal compliance trends, student rosters & CSV audit export"),
        ("•", "components/MealCoach.tsx: Interactive AI dietary critique modal & student nutritional coaching"),
        ("•", "contexts/RecordsContext.tsx: Resilient localStorage v2 state persistence with seamless offline sync"),
    ]
    draw_card(ax, (0.52, 0.50), 0.44, 0.41, "Frontend Web Client (React 19 + TypeScript + Vite)", items_fe, header_bg="#0284C7", border_color="#7DD3FC", item_fontsize=8.0)

    # Box 3: Synchronized Wire Contract
    items_contract = [
        ("•", "Python Source: engine/contract.py — 19-key Pydantic dataclass validating all API payloads"),
        ("•", "TypeScript Target: frontend/src/types/contract.gen.ts — Auto-generated via tools/gen_contract_ts.py"),
        ("•", "Continuous Verification: Synchronized 100% via GitHub Actions CI gate (tools/gen_contract_ts.py --check)"),
    ]
    draw_card(ax, (0.04, 0.27), 0.92, 0.20, "Synchronized Cryptographic Wire Contract (19 Keys)", items_contract, header_bg="#059669", border_color="#86EFAC", item_fontsize=8.5)

    # Box 4: Quality Assurance & Cryptographic Verification
    items_qa = [
        ("•", "Automated Python Tests: 385 automated tests (381 unit and regression tests, 4 red-team chaos audit tests, zero failures)"),
        ("•", "Frontend Test Suite: 115 Vitest automated unit and contract tests across 22 test files with full TypeScript strictness"),
        ("•", "Cryptographic Evaluation Lock: tools/check_locked.py validates 502/502 pinned sha256 hashes (502 ok, 0 skipped, 0 failed)"),
        ("•", "CI/CD Automation: GitHub Actions workflows enforce ruff linting, pyright typecheck (baseline 144), and Vitest verification"),
    ]
    draw_card(ax, (0.04, 0.05), 0.92, 0.19, "Testing, Cryptographic Guardrails & CI/CD Pipeline", items_qa, header_bg="#334155", border_color="#94A3B8", item_fontsize=8.5)

    out_path = os.path.join(OUTPUT_DIR, "backend_frontend_implementation_layout.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 9: Figure 6.2 Nutrition Assessment and Uncertainty Reporting
# ==============================================================================

def generate_figure_6_2():
    fig = plt.figure(figsize=(12, 10.5), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")

    # Title & Subtitle
    plt.suptitle("Figure 6.2: Probabilistic Nutritional Metrology & Comonotonic Monte Carlo Propagation",
                 fontsize=14, fontweight="bold", y=0.98, color="#0F172A", family="sans-serif")
    plt.figtext(0.5, 0.955, "Simulated Comonotonic Sampling (4,000 Draws) Propagating Mass & Density Variance to [p05, p50, p95] Statutory Bounds",
                ha="center", fontsize=9.5, style="italic", color="#475569", family="sans-serif")

    # 4 Subplots (2x2 grid)
    # 1. Mass Distribution (LogNormal)
    ax1 = fig.add_subplot(2, 2, 1)
    np.random.seed(42)
    mu_mass, sigma_mass = np.log(265.5), 0.12
    mass_samples = np.random.lognormal(mu_mass, sigma_mass, 4000)
    p05_m, p50_m, p95_m = np.percentile(mass_samples, [5, 50, 95])

    ax1.hist(mass_samples, bins=50, density=True, color="#93C5FD", edgecolor="#1D4ED8", alpha=0.7)
    ax1.axvline(p50_m, color="#1D4ED8", lw=2, label=f"Median p50: {p50_m:.1f} g")
    ax1.axvline(p05_m, color="#D97706", lw=1.5, linestyle="--", label=f"p05: {p05_m:.1f} g")
    ax1.axvline(p95_m, color="#D97706", lw=1.5, linestyle="--", label=f"p95: {p95_m:.1f} g")
    ax1.set_title("1. Portion Mass Distribution M ~ LogNormal", fontsize=11, fontweight="bold", color="#1E293B")
    ax1.set_xlabel("Estimated Mass (grams)", fontsize=9)
    ax1.set_ylabel("Probability Density", fontsize=9)
    ax1.legend(loc="upper right", fontsize=8)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # 2. Comonotonic Scatter (Energy vs Protein)
    ax2 = fig.add_subplot(2, 2, 2)
    # Grounded IFCT values for cooked rice: 112 kcal / 100g, 2.4g protein / 100g
    kcal_per_g = np.random.normal(1.12, 0.05, 4000)
    prot_per_g = np.random.normal(0.024, 0.002, 4000)
    # Comonotonic coupling
    sorted_idx = np.argsort(mass_samples)
    coupled_mass = mass_samples[sorted_idx]
    coupled_kcal = coupled_mass * np.sort(kcal_per_g)
    coupled_prot = coupled_mass * np.sort(prot_per_g)

    ax2.scatter(coupled_kcal, coupled_prot, c="#8B5CF6", alpha=0.25, s=8)
    ax2.set_title("2. Comonotonic Rank-Coupled Draws (4,000 Draws)", fontsize=11, fontweight="bold", color="#1E293B")
    ax2.set_xlabel("Coupled Energy (kcal)", fontsize=9)
    ax2.set_ylabel("Coupled Protein (grams)", fontsize=9)
    ax2.grid(True, linestyle=":", alpha=0.6)

    # 3. Energy Distribution vs PM POSHAN Target
    ax3 = fig.add_subplot(2, 2, 3)
    p05_e, p50_e, p95_e = np.percentile(coupled_kcal, [5, 50, 95])
    ax3.hist(coupled_kcal, bins=50, density=True, color="#86EFAC", edgecolor="#059669", alpha=0.7)
    ax3.axvline(p50_e, color="#059669", lw=2, label=f"Median p50: {p50_e:.0f} kcal")
    ax3.axvline(p05_e, color="#D97706", lw=1.5, linestyle="--", label=f"p05: {p05_e:.0f} kcal")
    ax3.axvline(p95_e, color="#D97706", lw=1.5, linestyle="--", label=f"p95: {p95_e:.0f} kcal")
    ax3.axvline(450.0, color="#DC2626", lw=2, linestyle="-.", label="PM POSHAN Target (450 kcal)")
    ax3.set_title("3. Energy Distribution vs Statutory Target", fontsize=11, fontweight="bold", color="#1E293B")
    ax3.set_xlabel("Energy (kcal)", fontsize=9)
    ax3.set_ylabel("Probability Density", fontsize=9)
    ax3.legend(loc="upper left", fontsize=8)
    ax3.grid(True, linestyle=":", alpha=0.6)

    # 4. Joint Compliance Decision Matrix
    ax4 = fig.add_subplot(2, 2, 4)
    # Decision boundaries
    ax4.fill_between([450, 600], [12, 12], [25, 25], color="#DCFCE7", alpha=0.8, label="PASS: P(E>=450)>=0.90 & P(P>=12)>=0.90")
    ax4.fill_between([350, 450], [0, 0], [25, 25], color="#FEE2E2", alpha=0.6, label="FAIL: Nutritional Deficit")
    ax4.fill_between([450, 600], [0, 0], [12, 12], color="#FEF3C7", alpha=0.6, label="BORDERLINE: Deficit / High Variance")
    # Plot contour or scatter of meal
    ax4.scatter(p50_e, np.median(coupled_prot), color="#0F172A", s=80, marker="X", zorder=5, label=f"Meal Estimate ({p50_e:.0f} kcal, {np.median(coupled_prot):.1f} g)")
    ax4.set_xlim(350, 600)
    ax4.set_ylim(0, 25)
    ax4.set_title("4. Statutory Decision Space & Governance Boundaries", fontsize=11, fontweight="bold", color="#1E293B")
    ax4.set_xlabel("Energy (kcal)", fontsize=9)
    ax4.set_ylabel("Protein (grams)", fontsize=9)
    ax4.legend(loc="lower right", fontsize=7.5)
    ax4.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout(rect=[0.02, 0.03, 0.98, 0.94])
    out_path = os.path.join(OUTPUT_DIR, "nutrition_assessment_and_uncertainty.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Main Generator
# ==============================================================================

def main():
    print("🎨 Generating all 9 high-resolution publication diagrams in", OUTPUT_DIR)
    generate_figure_1_1()
    generate_figure_1_2()
    generate_figure_5_1()
    generate_figure_5_2()
    generate_figure_5_3a()
    generate_figure_5_3b()
    generate_figure_5_3c()
    generate_figure_6_1()
    generate_figure_6_2()
    print("🎉 All 9 architectural diagrams successfully generated!")


if __name__ == "__main__":
    main()
