# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""High-Resolution Publication-Quality Architectural Diagram Generator for NutriSense Academic Report.

B.M.S. College of Engineering, Department of Machine Learning, Bengaluru.
Generates all 9 system and conceptual diagrams matching current deployed setup:
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
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

OUTPUT_DIR = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report/assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==============================================================================
# Helper Drawing Functions with Dynamic Text Wrapping & Zero Boundary Bleed
# ==============================================================================

def add_header(ax, title, subtitle, y_top=0.965):
    ax.text(0.5, y_top, title, ha="center", va="top", fontsize=13.0, fontweight="bold", color="#0F172A", family="DejaVu Sans")
    ax.text(0.5, y_top - 0.032, subtitle, ha="center", va="top", fontsize=9.2, style="italic", color="#475569", family="DejaVu Sans")


def draw_wrapped_card(ax, xy, width, height, title, items, header_bg="#1E293B", body_bg="#FFFFFF",
                      border_color="#CBD5E1", title_color="#FFFFFF", title_fontsize=9.0, item_fontsize=7.5,
                      radius=0.012, wrap_chars=None):
    x, y = xy
    # Outer box
    rect = patches.FancyBboxPatch((x, y), width, height, boxstyle=f"round,pad={radius}", ec=border_color, fc=body_bg, lw=1.5, zorder=2)
    ax.add_patch(rect)

    # Header height based on title lines
    title_lines = title.split("\n")
    header_h = max(height * 0.15, 0.032 + len(title_lines) * 0.018)
    header_rect = patches.FancyBboxPatch((x, y + height - header_h), width, header_h, boxstyle=f"round,pad={radius}", ec=header_bg, fc=header_bg, lw=1.5, zorder=3)
    ax.add_patch(header_rect)
    sub_rect = patches.Rectangle((x, y + height - header_h), width, header_h * 0.5, fc=header_bg, ec=header_bg, zorder=3)
    ax.add_patch(sub_rect)

    # Header text
    ax.text(x + width / 2, y + height - header_h / 2, title, ha="center", va="center",
            fontsize=title_fontsize, fontweight="bold", color=title_color, zorder=4, family="DejaVu Sans")

    if not items:
        return

    # Measure wrapped lines
    if wrap_chars is None:
        wrap_chars = max(int(width * 115), 20)

    rendered_items = []
    total_lines = 0
    for item in items:
        bullet, txt = item if isinstance(item, tuple) else ("•", item)
        lines = textwrap.wrap(txt, width=wrap_chars)
        if not lines:
            continue
        rendered_items.append((bullet, lines))
        total_lines += len(lines)

    if not rendered_items:
        return

    # Calculate exact available body height and scale line spacing so content never spills out
    avail_body_h = height - header_h - 0.030
    line_spacing = min(0.021, avail_body_h / max(total_lines + len(rendered_items) * 0.25, 1))
    effective_font_size = min(item_fontsize, max(6.2, line_spacing * 380))

    cur_y = y + height - header_h - 0.018
    for bullet, lines in rendered_items:
        b_color = "#2563EB"
        if bullet == "✓":
            b_color = "#16A34A"
        elif bullet == "✗":
            b_color = "#DC2626"
        elif bullet in ("Mode A:", "Mode B:", "DEV:", "LOCK:"):
            b_color = "#D97706"

        indent = 0.036 if (bullet.strip() and len(bullet) <= 2) else (0.015 if not bullet.strip() else 0.065)
        if bullet.strip():
            ax.text(x + 0.012, cur_y, bullet, ha="left", va="top", fontsize=effective_font_size,
                    fontweight="bold", color=b_color, zorder=4, family="DejaVu Sans")

        for line in lines:
            ax.text(x + indent, cur_y, line, ha="left", va="top", fontsize=effective_font_size,
                    color="#1E293B", zorder=4, family="DejaVu Sans")
            cur_y -= line_spacing
        cur_y -= (line_spacing * 0.25)


# ==============================================================================
# Diagram 1: Figure 1.1 Problem Context & Workflow
# ==============================================================================

def generate_figure_1_1():
    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 1.1: NutriSense Problem Context & Optical Assessment Workflow",
               "Real-World Institutional Feeding Constraints → Single-View RGB AI Inference → Auditable Compliance Output", y_top=0.965)

    items_p1 = [
        ("•", "High-throughput lunch distribution (>400 students/hour) in school canteens."),
        ("•", "Varying stainless steel plates, trays and partition thalis."),
        ("•", "Liquid curries, rasam and dal with fluid meniscus surfaces."),
        ("•", "Absence of digital weighing scales and severe manual audit fatigue."),
        ("•", "Hidden macronutrient, calorie, and protein dietary gaps."),
        ("•", "Subjective visual inspections lack auditable verification."),
    ]
    draw_wrapped_card(ax, (0.04, 0.06), 0.28, 0.82, "1. Canteen Realities\n(Operational Context)", items_p1,
                      header_bg="#B91C1C", border_color="#FCA5A5", wrap_chars=32)

    ax.annotate("", xy=(0.35, 0.47), xytext=(0.325, 0.47),
                arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=2.5, mutation_scale=16), zorder=5)

    items_p2 = [
        ("•", "Single top-down RGB capture via accessible smartphone camera."),
        ("•", "Mode A (Fiducial): 60 mm ArUco marker (DICT_4X4_50)."),
        (" ", "└ Michelson contrast CM >= 0.42 quiet-zone verification."),
        (" ", "└ Homography & camera pose: 0.74 mm RMS error."),
        ("•", "Mode B (Card-Free): Zero-marker intake."),
        (" ", "└ Base tabletop annulus RANSAC plane fitting."),
        (" ", "└ ImplicitScaleHead (6-Fold LODO-CV, 77.0% acc)."),
        (" ", "└ 80.1% Volume Bias Cut (-223.5 g → -44.4 g)."),
    ]
    draw_wrapped_card(ax, (0.36, 0.06), 0.28, 0.82, "2. Single-View Capture\n(Dual-Mode Scaling)", items_p2,
                      header_bg="#1D4ED8", border_color="#93C5FD", wrap_chars=32)

    ax.annotate("", xy=(0.67, 0.47), xytext=(0.645, 0.47),
                arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=2.5, mutation_scale=16), zorder=5)

    items_p3 = [
        ("•", "SAM 2.1 Hiera + DeepLabV3 (95.81% foreground Dice)."),
        ("•", "Vessel liquid detector for katoris and partition cups."),
        ("•", "SigLIP-2 ViT-B/16 (82.27% Top-1) + 115 Indian Dish Hub."),
        ("•", "MoGe-2 3D Metric Depth + DINOv2-S Mass Head Fusion."),
        ("•", "ICMR-NIN IFCT 2017 & INDB 1,014 Recipe Knowledge Base."),
        ("•", "Comonotonic 4,000-draw Monte Carlo uncertainty bounds."),
        ("•", "PM POSHAN Verdict: PASS / FAIL / BORDERLINE [p05, p95]."),
    ]
    draw_wrapped_card(ax, (0.68, 0.06), 0.28, 0.82, "3. AI Metrology\n(Compliance Verdict)", items_p3,
                      header_bg="#047857", border_color="#6EE7B7", wrap_chars=32)

    out_path = os.path.join(OUTPUT_DIR, "figure_1_1_problem_context.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 2: Figure 1.2 Approach Comparison
# ==============================================================================

def generate_figure_1_2():
    fig, ax = plt.subplots(figsize=(11.5, 6.2), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 1.2: Architectural Comparison: Conventional 2D vs. NutriSense 3D Metrology",
               "Structural Contrast between Heuristic Pixel Counting and Physics-Grounded 3D Metric Computer Vision", y_top=0.965)

    items_conv = [
        ("✗", "2D Bounding Boxes: YOLO / Faster R-CNN rectangular boxes miss complex mixed food boundaries and partition edges."),
        ("✗", "Arbitrary Pixel Multipliers: Multiplies pixel area by magic constant; completely blind to 3D mound height."),
        ("✗", "Flat Food Assumption: Treats 150g rice mound and 20g flat dosa as identical 2D surface areas."),
        ("✗", "Generic Western Food Tables: Relies on US USDA tables; ignores Indian spices, gravies, and dal dilution."),
        ("✗", "Deterministic Point Estimates: Outputs single number (e.g. '520 kcal') hiding massive unmeasured estimation variance."),
        ("✗", "Opaque Binary Verdict: Black-box pass/fail with zero explainability, no audit trail, and silent classification failure."),
    ]
    draw_wrapped_card(ax, (0.04, 0.06), 0.44, 0.82, "Conventional 2D Food Analysis\n(Heuristic & Fragile)", items_conv,
                      header_bg="#DC2626", body_bg="#FEF2F2", border_color="#FCA5A5", item_fontsize=8.0, wrap_chars=54)

    items_nutri = [
        ("✓", "Promptable Instance Segmentation: SAM 2.1 Hiera-Large + DeepLabV3 (95.81% FG Dice, 82.11% food IoU)."),
        ("✓", "Metric 3D Unprojection: MoGe-2 dense surface reconstruction with RANSAC tabletop support plane."),
        ("✓", "Dual-Mode Scale Anchoring: 60mm ArUco fiducial (0.74 mm RMS) & Card-Free Mode B ImplicitScaleHead."),
        ("✓", "Calibrated Mass Fusion: Inverse-variance fusion (~82% geometric volume × density, ~18% DINOv2-S head)."),
        ("✓", "Indian Domain Grounding: ICMR-NIN IFCT 2017 & INDB 1,014 cooked recipes + 115 regional dish hub."),
        ("✓", "Statutory Metrology: 4,000-draw comonotonic Monte Carlo [p05, p50, p95] + PM POSHAN audit engine."),
    ]
    draw_wrapped_card(ax, (0.52, 0.06), 0.44, 0.82, "NutriSense Metrological Pipeline\n(Physics-Grounded 3D AI)", items_nutri,
                      header_bg="#059669", body_bg="#F0FDF4", border_color="#86EFAC", item_fontsize=8.0, wrap_chars=54)

    out_path = os.path.join(OUTPUT_DIR, "figure_1_2_approach_comparison.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 3: Figure 5.1 System Architecture
# ==============================================================================

def generate_figure_5_1():
    fig, ax = plt.subplots(figsize=(12, 12.0), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 5.1: NutriSense Multi-Stage Metrological System Architecture",
               "Six-Stage Deep Vision & Compliance Pipeline: Client → Gateway → GPU Pipeline → Metrology → Audit Store", y_top=0.978)

    # 1. Client Layer: y=0.825, h=0.125
    items_client = [
        ("•", "React 19 + TypeScript + Vite | Tailwind CSS + Accessible Color Tokens"),
        ("•", "Responsive Topbar Navigation (Home · Analyze · History · Insights · Students · Menu · Settings)"),
        ("•", "Dynamic Multi-Item Canvas Segmentation Mask Overlays & Real-Time Confidence Dials"),
        ("•", "Conversational Meal Coach / Critique Drawer & PM POSHAN Statutory Standards Dashboard"),
    ]
    draw_wrapped_card(ax, (0.05, 0.825), 0.90, 0.125, "Client Presentation Layer (Browser Web Application)", items_client,
                      header_bg="#0284C7", border_color="#7DD3FC", item_fontsize=8.0, wrap_chars=110)

    ax.annotate("", xy=(0.50, 0.805), xytext=(0.50, 0.825), arrowprops=dict(facecolor="#0284C7", edgecolor="#0284C7", arrowstyle="->", lw=2), zorder=5)

    # 2. Gateway Layer: y=0.665, h=0.135
    items_gw = [
        ("•", "FastAPI Service (Port 8000) | Uvicorn + AnyIO Bounded Inference Queue | 12 MiB Upload Limit"),
        ("•", "19-Key Cryptographic JSON Wire Contract (engine/contract.py ↔ frontend/src/types/contract.gen.ts)"),
        ("•", "Input Quality Gates: Digital Zoom Check, Resolution (≥800×800), Day & Class-Band Validation"),
        ("•", "CUDA Out-Of-Memory Guard: Automatic GPU registry cache flush & retry with memory protection"),
    ]
    draw_wrapped_card(ax, (0.05, 0.665), 0.90, 0.135, "API Gateway & Wire Contract Tier (FastAPI + Pydantic v2)", items_gw,
                      header_bg="#1E293B", border_color="#94A3B8", item_fontsize=8.0, wrap_chars=110)

    ax.annotate("", xy=(0.50, 0.645), xytext=(0.50, 0.665), arrowprops=dict(facecolor="#1E293B", edgecolor="#1E293B", arrowstyle="->", lw=2), zorder=5)

    # 3. Middle 3 Stage Cards: S1, S2, S3 (y=0.345, h=0.290)
    items_s1 = [
        ("Mode A:", "60 mm ArUco Marker (DICT_4X4_50)"),
        (" ", "  CM >= 0.42 Michelson quiet-zone"),
        (" ", "  Homography: 0.74 mm RMS error"),
        ("Mode B:", "Card-Free ImplicitScaleHead"),
        (" ", "  Tabletop annulus RANSAC plane"),
        (" ", "  6-Fold LODO-CV: 77.0% scale acc"),
        (" ", "  80.1% volume bias reduction"),
    ]
    draw_wrapped_card(ax, (0.05, 0.345), 0.28, 0.290, "Stage S1: Scale Anchor\n(Dual-Mode Scaling)", items_s1,
                      header_bg="#D97706", border_color="#FCD34D", item_fontsize=7.5, wrap_chars=34)

    items_s2 = [
        ("•", "SAM 2.1 Hiera + DeepLabV3 (95.8% Dice)"),
        ("•", "Vessel Liquid Detector (LIQUID_BOWL)"),
        ("•", "Dynamic Multi-Item Meal Parsing:"),
        (" ", "  Indian Thali (X Items) / Rice + Rasam"),
        ("•", "SigLIP-2 ViT-B/16 (α=0.65, 82.3% Top-1)"),
        ("•", "115 Regional Indian Dish Knowledge Hub"),
        (" ", "  1,206 Bharat & Rajistics Visual Prototypes"),
    ]
    draw_wrapped_card(ax, (0.36, 0.345), 0.28, 0.290, "Stage S2: Segmentation\n(Masking & Classification)", items_s2,
                      header_bg="#7C3AED", border_color="#C4B5FD", item_fontsize=7.5, wrap_chars=34)

    items_s3 = [
        ("•", "MoGe-2 ViT-L Metric Depth Estimation"),
        ("•", "Tabletop Support Plane Regression"),
        ("•", "DINOv2-S Heteroscedastic Mass Head"),
        ("DEV:", "MAE: 15.03 g (81.7% accuracy)"),
        ("LOCK:", "MAE: 14.67 g (80.0% accuracy)"),
        ("•", "Inverse-Variance Precision Mass Fusion:"),
        (" ", "  ~82% Geometry Volume + ~18% Learned"),
    ]
    draw_wrapped_card(ax, (0.67, 0.345), 0.28, 0.290, "Stage S3: 3D Depth & Mass\n(Surface & Mass Fusion)", items_s3,
                      header_bg="#2563EB", border_color="#93C5FD", item_fontsize=7.5, wrap_chars=34)

    # Arrows between S1 -> S2 -> S3
    ax.annotate("", xy=(0.355, 0.49), xytext=(0.335, 0.49), arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=2), zorder=5)
    ax.annotate("", xy=(0.665, 0.49), xytext=(0.645, 0.49), arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=2), zorder=5)

    ax.annotate("", xy=(0.50, 0.325), xytext=(0.50, 0.345), arrowprops=dict(facecolor="#059669", edgecolor="#059669", arrowstyle="->", lw=2), zorder=5)

    # 4. Stage S4 & S5: Nutritional Metrology: y=0.170, h=0.145
    items_compliance = [
        ("•", "Nutritional Database: Grounded ICMR-NIN IFCT 2017 & INDB Master (1,014 Cooked Indian Recipes)"),
        ("•", "Comonotonic Monte Carlo Engine: 4,000 paired draws propagating portion mass and density variances"),
        ("•", "Confidence Calibration: Returns rigorous [p05, p50, p95] bounds for volume (ml), mass (g), kcal, and protein (g)"),
        ("•", "Statutory PM POSHAN Rule Engine: Primary (450 kcal / 12g) & Upper-Primary (700 kcal / 20g) statutory compliance audit"),
    ]
    draw_wrapped_card(ax, (0.05, 0.170), 0.90, 0.145, "Stage S4 & S5: Nutritional Metrology & Comonotonic Compliance Engine", items_compliance,
                      header_bg="#059669", border_color="#86EFAC", item_fontsize=8.0, wrap_chars=110)

    ax.annotate("", xy=(0.50, 0.150), xytext=(0.50, 0.170), arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=2), zorder=5)

    # 5. Storage Tier: y=0.035, h=0.105
    items_storage = [
        ("•", "Audit Trail: Longitudinal JSON/SQLite Storage | Cryptographic Evaluation Lock (502/502 Pinned Sha256 Hashes)"),
        ("•", "Regression Gateways: 385 Automated Tests (381 unit, 4 red-team chaos audit) | Zero-Leakage WED DEV / LOCKED Splits"),
    ]
    draw_wrapped_card(ax, (0.05, 0.035), 0.90, 0.105, "Persistence, Audit Governance & Zero-Leakage Evaluation Tier", items_storage,
                      header_bg="#334155", border_color="#94A3B8", item_fontsize=8.0, wrap_chars=110)

    out_path = os.path.join(OUTPUT_DIR, "system_architecture.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 4: Figure 5.2 Whole-Project Flowchart
# ==============================================================================

def generate_figure_5_2():
    fig, ax = plt.subplots(figsize=(11, 16.5), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 5.2: NutriSense End-to-End Decision Flowchart",
               "Step-by-Step Logic Execution: Capture Validation → Scale Anchoring → Multi-Item Decomposition → Compliance Verdict", y_top=0.985)

    def draw_node(xy, w, h, text, bg="#FFFFFF", ec="#1E293B", text_color="#1E293B", shape="round", bold=False, fontsize=8.0):
        x, y = xy
        if shape == "round":
            box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015", ec=ec, fc=bg, lw=1.5, zorder=2)
        elif shape == "diamond":
            pts = np.array([[x + w/2, y + h], [x + w, y + h/2], [x + w/2, y], [x, y + h/2]])
            box = patches.Polygon(pts, closed=True, ec=ec, fc=bg, lw=1.5, zorder=2)
        else:
            box = patches.Rectangle((x, y), w, h, ec=ec, fc=bg, lw=1.5, zorder=2)
        ax.add_patch(box)

        weight = "bold" if bold else "normal"
        lines = text.split("\n")
        n = len(lines)
        start_y = y + h/2 + (n - 1) * 0.009
        for i, line in enumerate(lines):
            ax.text(x + w/2, start_y - i * 0.018, line, ha="center", va="center",
                    fontsize=fontsize, color=text_color, fontweight=weight, zorder=3, family="DejaVu Sans")

    def draw_arrow(start, end, label=None, label_side="top"):
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=1.8), zorder=4)
        if label:
            mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
            dy = 0.016 if label_side == "top" else -0.016
            ax.text(mx, my + dy, label, ha="center", va="center", fontsize=7.5, fontweight="bold",
                    color="#B91C1C" if "NO" in label or "FAIL" in label else "#15803D",
                    bbox=dict(boxstyle="round,pad=0.2", fc="#FFFFFF", ec="#CBD5E1", lw=0.8, alpha=0.95), zorder=5, family="DejaVu Sans")

    # 1. Start Node: y=0.900
    draw_node((0.33, 0.900), 0.34, 0.045, "START: Meal Capture Upload\nRGB Photo + Context: Day, Class Band 1-5 / 6-8",
              bg="#DBEAFE", ec="#1D4ED8", text_color="#1E3A8A", bold=True, fontsize=8.0)
    draw_arrow((0.50, 0.900), (0.50, 0.860))

    # 2. Input Validation Gates: y=0.815
    draw_node((0.26, 0.815), 0.48, 0.040, "Input Validation Gates (engine/gates.py)\nUpload Size <= 12 MiB | Resolution >= 800x800 | Digital Zoom Gate",
              bg="#F8FAFC", ec="#64748B", fontsize=7.5)
    draw_arrow((0.50, 0.815), (0.50, 0.770))

    # Decision 1: Pass Input Gates?: y=0.710
    draw_node((0.36, 0.710), 0.28, 0.055, "Pass Input\nGates?", bg="#FEF3C7", ec="#D97706", shape="diamond", bold=True, fontsize=8.0)
    draw_arrow((0.64, 0.737), (0.76, 0.737), "NO")
    draw_node((0.76, 0.715), 0.20, 0.045, "ABSTAIN / 422\nReturn Structured Failure", bg="#FEE2E2", ec="#DC2626", text_color="#B91C1C", bold=True, fontsize=7.5)

    draw_arrow((0.50, 0.710), (0.50, 0.665), "YES")

    # 3. Scale Mode Decision: y=0.605
    draw_node((0.36, 0.605), 0.28, 0.055, "ArUco 60mm Marker\nCM >= 0.42 Quiet Zone?", bg="#FEF3C7", ec="#D97706", shape="diamond", bold=True, fontsize=8.0)

    # Branch A: Mode A
    draw_arrow((0.36, 0.632), (0.22, 0.632), "YES (Mode A)")
    draw_node((0.04, 0.610), 0.18, 0.045, "Stage S1a: Physical Fiducial\nHomography & Pose Fit\n(0.74 mm RMS Error)", bg="#DCFCE7", ec="#16A34A", fontsize=7.5)

    # Branch B: Mode B
    draw_arrow((0.64, 0.632), (0.77, 0.632), "NO (Mode B)")
    draw_node((0.77, 0.610), 0.19, 0.045, "Stage S1b: Card-Free\nImplicitScaleHead LODO-CV\n(80.1% Volume Bias Cut)", bg="#E0E7FF", ec="#4338CA", fontsize=7.5)

    # Merge to Segmentation
    draw_arrow((0.13, 0.610), (0.38, 0.555))
    draw_arrow((0.86, 0.610), (0.62, 0.555))

    # 4. Stage S2: Segmentation: y=0.510
    draw_node((0.24, 0.510), 0.52, 0.045, "Stage S2: Promptable SAM 2.1 Hiera + DeepLabV3\nForeground Mask Proposal + Katori Liquid Bowl Promotion",
              bg="#F3E8FF", ec="#7C3AED", bold=True, fontsize=8.0)
    draw_arrow((0.50, 0.510), (0.50, 0.465))

    # Multi-Item Parsing Decision: y=0.410
    draw_node((0.37, 0.410), 0.26, 0.055, "Number of Food\nItems / Vessels?", bg="#FEF3C7", ec="#D97706", shape="diamond", bold=True, fontsize=8.0)
    draw_arrow((0.37, 0.437), (0.22, 0.437), ">= 3 Items")
    draw_node((0.04, 0.415), 0.18, 0.045, "Indian Thali Multi-Item\nDecompose Rice, Rasam,\nDal & Curries", bg="#FEF3C7", ec="#D97706", fontsize=7.5)

    draw_arrow((0.63, 0.437), (0.77, 0.437), "1-2 Items")
    draw_node((0.77, 0.415), 0.19, 0.045, "Dual / Single Item\nRice + Rasam / Biryani\nFocused Crop Extraction", bg="#FEF3C7", ec="#D97706", fontsize=7.5)

    # Merge to Classification
    draw_arrow((0.13, 0.415), (0.38, 0.360))
    draw_arrow((0.86, 0.415), (0.62, 0.360))

    # 5. Dish Classification: y=0.315
    draw_node((0.22, 0.315), 0.56, 0.045, "Stage S2b: SigLIP-2 ViT-B/16 Regional Indian Dish Hub\n1,206 Bharat & Rajistics Visual Prototypes + 115 Text Prompts (82.27% Top-1)",
              bg="#F3E8FF", ec="#7C3AED", fontsize=7.5)
    draw_arrow((0.50, 0.315), (0.50, 0.270))

    # 6. Stage S3: 3D Depth & Mass Estimation: y=0.220
    draw_node((0.18, 0.220), 0.64, 0.050, "Stage S3: MoGe-2 3D Metric Depth Unprojection + Tabletop RANSAC Fit\nInverse-Variance Fusion (~82% Geometry Volume x Density + ~18% DINOv2-S Mass Head)",
              bg="#EFF6FF", ec="#2563EB", bold=True, fontsize=8.0)
    draw_arrow((0.50, 0.220), (0.50, 0.175))

    # 7. Stage S4 & S5: Nutritional Engine & Monte Carlo: y=0.125
    draw_node((0.16, 0.125), 0.68, 0.050, "Stage S4 & S5: ICMR-NIN IFCT 2017 & INDB 1,014 Recipe Lookup\n4,000-Draw Comonotonic Monte Carlo Uncertainty Bounds [p05, p50, p95]",
              bg="#ECFDF5", ec="#059669", bold=True, fontsize=8.0)
    draw_arrow((0.50, 0.125), (0.50, 0.085))

    # 8. Compliance Decision: y=0.055
    draw_node((0.34, 0.055), 0.32, 0.052, "P(E >= Emin) >= 0.90\nAND P(P >= Pmin) >= 0.90\nAND Coverage >= 0.85?",
              bg="#FEF3C7", ec="#D97706", shape="diamond", bold=True, fontsize=7.5)

    # Verdicts
    draw_arrow((0.34, 0.081), (0.19, 0.081), "YES")
    draw_node((0.03, 0.060), 0.16, 0.042, "VERDICT: PASS\nStatutory Target Met", bg="#DCFCE7", ec="#16A34A", text_color="#15803D", bold=True, fontsize=7.5)

    draw_arrow((0.50, 0.055), (0.50, 0.028))
    ax.text(0.50, 0.040, "NO", ha="center", va="center", fontsize=7.5, fontweight="bold",
            color="#B91C1C", bbox=dict(boxstyle="round,pad=0.2", fc="#FFFFFF", ec="#CBD5E1", lw=0.8), zorder=5, family="DejaVu Sans")
    draw_node((0.41, 0.005), 0.18, 0.023, "VERDICT: FAIL\nNutritional Deficit", bg="#FEE2E2", ec="#DC2626", text_color="#B91C1C", bold=True, fontsize=7.2)

    draw_arrow((0.66, 0.081), (0.80, 0.081), "UNCERTAIN")
    draw_node((0.80, 0.060), 0.17, 0.042, "VERDICT: BORDERLINE\nDeficit Warning", bg="#FEF9C3", ec="#CA8A04", text_color="#854D0E", bold=True, fontsize=7.5)

    out_path = os.path.join(OUTPUT_DIR, "whole_project_flowchart.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 5: Figure 5.3a Conceptual Class & Module Diagram
# ==============================================================================

def generate_figure_5_3a():
    fig, ax = plt.subplots(figsize=(13.5, 9.2), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 5.3(a): NutriSense Conceptual Class and Modular Architecture Diagram",
               "Decoupled Service-Oriented Subsystems: Ingestion → Vision Models → Metrology → Compliance → Contract", y_top=0.970)

    # Row 1 (y=0.62, h=0.30)
    c1 = [
        ("+ app: FastAPI"),
        ("+ /analyze(image, day, band): JSON"),
        ("+ /health(): StatusResponse"),
        ("+ /meal-critique(analysis): Critique"),
    ]
    draw_wrapped_card(ax, (0.03, 0.62), 0.22, 0.30, "FastAPI Service\n(main.py)", c1, header_bg="#0284C7", title_fontsize=8.5, item_fontsize=7.2, wrap_chars=25)

    c2 = [
        ("+ run(image, context): Analysis"),
        ("+ validate_gates(): GateResult"),
        ("+ dispatch_scale(): AnchorResult"),
        ("+ fuse_mass(): MassDistribution"),
    ]
    draw_wrapped_card(ax, (0.27, 0.62), 0.22, 0.30, "Pipeline Engine\n(engine/pipeline.py)", c2, header_bg="#1E293B", title_fontsize=8.5, item_fontsize=7.2, wrap_chars=25)

    c3 = [
        ("+ detect_aruco(rgb): AnchorA"),
        ("+ cm_per_pixel: float"),
        ("+ estimate_implicit(rgb): AnchorB"),
        ("+ annulus_plane_fit(): PlaneEq"),
    ]
    draw_wrapped_card(ax, (0.51, 0.62), 0.22, 0.30, "Scale Anchor\n(models/scale_anchor.py)", c3, header_bg="#D97706", title_fontsize=8.5, item_fontsize=7.2, wrap_chars=25)

    c4 = [
        ("+ segment(rgb): List[Mask]"),
        ("+ detect_liquid_bowls(): Bowls"),
        ("+ filter_candidates(): CleanMasks"),
        ("+ decompose_thali(): Items"),
    ]
    draw_wrapped_card(ax, (0.75, 0.62), 0.22, 0.30, "SAM 2.1 Segmenter\n(models/dish_segmenter.py)", c4, header_bg="#7C3AED", title_fontsize=8.5, item_fontsize=7.2, wrap_chars=25)

    # Row 2 (y=0.29, h=0.30)
    c5 = [
        ("+ embed(crop): Tensor[768]"),
        ("+ classify(embedding): TopK"),
        ("+ gallery: 115 Indian Dishes"),
        ("+ prototypes: 1,206 vectors"),
    ]
    draw_wrapped_card(ax, (0.03, 0.29), 0.22, 0.30, "Food Classifier\n(models/food_classifier.py)", c5, header_bg="#7C3AED", title_fontsize=8.5, item_fontsize=7.2, wrap_chars=25)

    c6 = [
        ("+ infer_depth(rgb): MetricDepthMap"),
        ("+ fit_tabletop_plane(): NormalVec"),
        ("+ compute_volume(mask, depth): ml"),
        ("+ unproject_pcd(): PointCloud3D"),
    ]
    draw_wrapped_card(ax, (0.27, 0.29), 0.22, 0.30, "Depth Engine\n(engine/depth.py)", c6, header_bg="#2563EB", title_fontsize=8.5, item_fontsize=7.2, wrap_chars=25)

    c7 = [
        ("+ extract_dinov2_features(): Tensor"),
        ("+ predict_mass(features): (mu, var)"),
        ("+ fuse_mass(geo_mass, mlp_mass): g"),
        ("+ uncertainty_variance: float"),
    ]
    draw_wrapped_card(ax, (0.51, 0.29), 0.22, 0.30, "DINOv2 Weight Head\n(models/weight_head.py)", c7, header_bg="#2563EB", title_fontsize=8.5, item_fontsize=7.2, wrap_chars=25)

    c8 = [
        ("+ lookup_ifct(dish_id): Nutrients"),
        ("+ monte_carlo_draws(4000): Dist"),
        ("+ evaluate_poshan(dist, band): Verdict"),
        ("+ coverage_score(): [0, 1]"),
    ]
    draw_wrapped_card(ax, (0.75, 0.29), 0.22, 0.30, "Nutrition Metrology\n(engine/compliance.py)", c8, header_bg="#059669", title_fontsize=8.5, item_fontsize=7.2, wrap_chars=25)

    # Bottom: Wire Contract Box (y=0.04, h=0.22)
    items_contract = [
        ("•", "19-Key Cryptographic JSON Contract (engine/contract.py ↔ frontend/src/types/contract.gen.ts)"),
        ("•", "Keys: id, createdAt, verdict, dish, grams, kcal, protein_g, coverage, confidence, intervals [p05, p50, p95], items, reasons, failures"),
    ]
    draw_wrapped_card(ax, (0.03, 0.04), 0.94, 0.22, "Auditable Wire Contract Specification (AnalysisContract)", items_contract,
                      header_bg="#334155", title_fontsize=9.5, item_fontsize=8.0, wrap_chars=110)

    out_path = os.path.join(OUTPUT_DIR, "conceptual_module_diagram.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 6: Figure 5.3b Activity Diagram
# ==============================================================================

def generate_figure_5_3b():
    fig, ax = plt.subplots(figsize=(12, 11.5), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 5.3(b): NutriSense Meal Analysis Activity Diagram across System Swimlanes",
               "Sequential Processing Swimlanes: Client → Gateway → GPU Pipeline → Nutritional Metrology → Audit Store", y_top=0.975)

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
        ax.text(x + w/2, 0.89, title, ha="center", va="center", fontsize=8.0, fontweight="bold", color="#FFFFFF", zorder=3, family="DejaVu Sans")

    def act_box(xy, w, h, txt, bg="#FFFFFF", ec="#1E293B", bold=False):
        x, y = xy
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01", ec=ec, fc=bg, lw=1.5, zorder=4)
        ax.add_patch(box)
        weight = "bold" if bold else "normal"
        ax.text(x + w/2, y + h/2, txt, ha="center", va="center", fontsize=7.5, color="#1E293B", fontweight=weight, zorder=5, family="DejaVu Sans")

    def act_arrow(start, end):
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(facecolor="#475569", edgecolor="#475569", arrowstyle="->", lw=1.5), zorder=6)

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

    # Clean return path: from Statutory Rule Engine (0.725, 0.16) down to 0.07, across to 0.305, then up to gateway box
    ax.plot([0.725, 0.725], [0.16, 0.07], color="#475569", lw=1.5, zorder=6)
    ax.plot([0.725, 0.305], [0.07, 0.07], color="#475569", lw=1.5, zorder=6)
    act_arrow((0.305, 0.07), (0.305, 0.10))

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
    fig, ax = plt.subplots(figsize=(11.5, 7.8), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 5.3(c): NutriSense Use Case Diagram across Institutional Stakeholders",
               "Institutional Actors & Application Boundary: Headmaster · Canteen Supervisor · Field Inspector · ML Engineer", y_top=0.965)

    # System boundary box (top=0.86, height=0.81)
    sys_box = patches.FancyBboxPatch((0.24, 0.05), 0.52, 0.81, boxstyle="round,pad=0.02", ec="#1E293B", fc="#F8FAFC", lw=2, zorder=1)
    ax.add_patch(sys_box)
    ax.text(0.50, 0.835, "NutriSense Application System Boundary", ha="center", va="center", fontsize=9.2, fontweight="bold", color="#0F172A", zorder=2, family="DejaVu Sans")

    # Actors Left
    ax.text(0.10, 0.68, "School Headmaster /\nPrincipal", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1E293B", zorder=3, family="DejaVu Sans")
    ax.text(0.10, 0.26, "Canteen Cook /\nKitchen Supervisor", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1E293B", zorder=3, family="DejaVu Sans")

    # Actors Right
    ax.text(0.90, 0.68, "PM POSHAN Field\nInspector / Officer", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1E293B", zorder=3, family="DejaVu Sans")
    ax.text(0.90, 0.26, "ML Research Engineer /\nSystem Administrator", ha="center", va="center", fontsize=8.5, fontweight="bold", color="#1E293B", zorder=3, family="DejaVu Sans")

    # Use Case Ovals in Center (x=0.34 to 0.66, width=0.32)
    use_cases = [
        ((0.34, 0.74), 0.32, 0.050, "UC-1: Upload & Validate Meal Photograph"),
        ((0.34, 0.64), 0.32, 0.050, "UC-2: Estimate 3D Portion Mass (Dual-Mode S1)"),
        ((0.34, 0.54), 0.32, 0.050, "UC-3: Multi-Item Food & Liquid Segmentation"),
        ((0.34, 0.44), 0.32, 0.050, "UC-4: Verify PM POSHAN Compliance Status"),
        ((0.34, 0.34), 0.32, 0.050, "UC-5: Review Comonotonic Monte Carlo Bounds"),
        ((0.34, 0.24), 0.32, 0.050, "UC-6: Query Conversational Dietary Critique"),
        ((0.34, 0.14), 0.32, 0.050, "UC-7: Audit Historical Roster & Daily Logs"),
        ((0.34, 0.06), 0.32, 0.050, "UC-8: Manage Menu & Ingest IFCT/INDB Data"),
    ]

    for (x, y), w, h, label in use_cases:
        oval = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015", ec="#2563EB", fc="#EFF6FF", lw=1.5, zorder=4)
        ax.add_patch(oval)
        ax.text(x + w/2, y + h/2, label, ha="center", va="center", fontsize=7.8, fontweight="bold", color="#1E293B", zorder=5, family="DejaVu Sans")

    # Connect lines: LEFT actors connect to x=0.34
    # Headmaster -> UC1, UC4, UC7
    ax.plot([0.18, 0.34], [0.68, 0.765], color="#64748B", lw=1.3, zorder=2)
    ax.plot([0.18, 0.34], [0.68, 0.465], color="#64748B", lw=1.3, zorder=2)
    ax.plot([0.18, 0.34], [0.68, 0.165], color="#64748B", lw=1.3, zorder=2)

    # Kitchen Supervisor -> UC1, UC2, UC6
    ax.plot([0.18, 0.34], [0.26, 0.755], color="#64748B", lw=1.3, zorder=2)
    ax.plot([0.18, 0.34], [0.26, 0.665], color="#64748B", lw=1.3, zorder=2)
    ax.plot([0.18, 0.34], [0.26, 0.265], color="#64748B", lw=1.3, zorder=2)

    # Connect lines: RIGHT actors connect to x=0.66
    # Field Inspector -> UC4, UC5, UC7
    ax.plot([0.82, 0.66], [0.68, 0.465], color="#64748B", lw=1.3, zorder=2)
    ax.plot([0.82, 0.66], [0.68, 0.365], color="#64748B", lw=1.3, zorder=2)
    ax.plot([0.82, 0.66], [0.68, 0.165], color="#64748B", lw=1.3, zorder=2)

    # ML Admin -> UC2, UC3, UC8
    ax.plot([0.82, 0.66], [0.26, 0.665], color="#64748B", lw=1.3, zorder=2)
    ax.plot([0.82, 0.66], [0.26, 0.565], color="#64748B", lw=1.3, zorder=2)
    ax.plot([0.82, 0.66], [0.26, 0.085], color="#64748B", lw=1.3, zorder=2)

    out_path = os.path.join(OUTPUT_DIR, "nutrisense_use_case_diagram.png")
    fig.savefig(out_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


# ==============================================================================
# Diagram 8: Figure 6.1 Backend & Frontend Implementation Layout
# ==============================================================================

def generate_figure_6_1():
    fig, ax = plt.subplots(figsize=(12, 10.0), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    add_header(ax, "Figure 6.1: NutriSense Repository and Technical Implementation Architecture",
               "Clean Separation between Backend FastAPI Engine, Synchronized Wire Contract, and React 19 Frontend", y_top=0.970)

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
    draw_wrapped_card(ax, (0.04, 0.50), 0.44, 0.43, "Backend Service Tier\n(engine/, models/, server/)", items_be,
                      header_bg="#1E293B", border_color="#CBD5E1", item_fontsize=7.5, wrap_chars=50)

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
    draw_wrapped_card(ax, (0.52, 0.50), 0.44, 0.43, "Frontend Web Client\n(React 19 + TypeScript + Vite)", items_fe,
                      header_bg="#0284C7", border_color="#7DD3FC", item_fontsize=7.5, wrap_chars=50)

    # Box 3: Synchronized Wire Contract
    items_contract = [
        ("•", "Python Source: engine/contract.py — 19-key Pydantic dataclass validating all API payloads"),
        ("•", "TypeScript Target: frontend/src/types/contract.gen.ts — Auto-generated via tools/gen_contract_ts.py"),
        ("•", "Continuous Verification: Synchronized 100% via GitHub Actions CI gate (tools/gen_contract_ts.py --check)"),
    ]
    draw_wrapped_card(ax, (0.04, 0.27), 0.92, 0.20, "Synchronized Cryptographic Wire Contract (19 Keys)", items_contract,
                      header_bg="#059669", border_color="#86EFAC", item_fontsize=8.0, wrap_chars=110)

    # Box 4: Quality Assurance & Guardrails
    items_qa = [
        ("•", "Automated Python Tests: 385 automated tests (381 unit and regression tests, 4 red-team chaos audit tests, zero failures)"),
        ("•", "Frontend Test Suite: 115 Vitest automated unit and contract tests across 22 test files with full TypeScript strictness"),
        ("•", "Cryptographic Evaluation Lock: tools/check_locked.py validates 502/502 pinned sha256 hashes (502 ok, 0 skipped, 0 failed)"),
        ("•", "CI/CD Automation: GitHub Actions workflows enforce ruff linting, pyright typecheck (baseline 144), and Vitest verification"),
    ]
    draw_wrapped_card(ax, (0.04, 0.04), 0.92, 0.20, "Testing, Cryptographic Guardrails & CI/CD Pipeline", items_qa,
                      header_bg="#334155", border_color="#94A3B8", item_fontsize=8.0, wrap_chars=110)

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

    plt.suptitle("Figure 6.2: Probabilistic Nutritional Metrology & Comonotonic Monte Carlo Propagation",
                 fontsize=13.0, fontweight="bold", y=0.98, color="#0F172A", family="DejaVu Sans")
    plt.figtext(0.5, 0.955, "Simulated Comonotonic Sampling (4,000 Draws) Propagating Mass & Density Variance to [p05, p50, p95] Statutory Bounds",
                ha="center", fontsize=9.2, style="italic", color="#475569", family="DejaVu Sans")

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
    ax1.set_title("1. Portion Mass Distribution M ~ LogNormal", fontsize=10.0, fontweight="bold", color="#1E293B", family="DejaVu Sans")
    ax1.set_xlabel("Estimated Mass (grams)", fontsize=8.5, family="DejaVu Sans")
    ax1.set_ylabel("Probability Density", fontsize=8.5, family="DejaVu Sans")
    ax1.legend(loc="upper right", fontsize=7.5)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # 2. Comonotonic Rank-Coupled Draws
    ax2 = fig.add_subplot(2, 2, 2)
    u_draws = np.random.uniform(0.01, 0.99, 4000)
    u_draws_sorted = np.sort(u_draws)
    energy_draws = np.percentile(np.random.lognormal(np.log(297.0), 0.15, 10000), u_draws_sorted * 100)
    protein_draws = np.percentile(np.random.lognormal(np.log(6.4), 0.18, 10000), u_draws_sorted * 100)

    ax2.scatter(energy_draws, protein_draws, s=8, color="#8B5CF6", alpha=0.25, label="Comonotonic Pairs (u_E = u_P)")
    ax2.set_title("2. Comonotonic Rank-Coupled Draws (4,000 Draws)", fontsize=10.0, fontweight="bold", color="#1E293B", family="DejaVu Sans")
    ax2.set_xlabel("Coupled Energy (kcal)", fontsize=8.5, family="DejaVu Sans")
    ax2.set_ylabel("Coupled Protein (grams)", fontsize=8.5, family="DejaVu Sans")
    ax2.grid(True, linestyle=":", alpha=0.6)

    # 3. Energy Distribution vs Statutory Target
    ax3 = fig.add_subplot(2, 2, 3)
    p05_e, p50_e, p95_e = np.percentile(energy_draws, [5, 50, 95])
    ax3.hist(energy_draws, bins=50, density=True, color="#6EE7B7", edgecolor="#059669", alpha=0.7)
    ax3.axvline(p50_e, color="#047857", lw=2, label=f"Median p50: {p50_e:.0f} kcal")
    ax3.axvline(p05_e, color="#D97706", lw=1.5, linestyle="--", label=f"p05: {p05_e:.0f} kcal")
    ax3.axvline(p95_e, color="#D97706", lw=1.5, linestyle="--", label=f"p95: {p95_e:.0f} kcal")
    ax3.axvline(450, color="#DC2626", lw=2, linestyle="-.", label="PM POSHAN Target (450 kcal)")
    ax3.set_title("3. Energy Distribution vs Statutory Target", fontsize=10.0, fontweight="bold", color="#1E293B", family="DejaVu Sans")
    ax3.set_xlabel("Energy (kcal)", fontsize=8.5, family="DejaVu Sans")
    ax3.set_ylabel("Probability Density", fontsize=8.5, family="DejaVu Sans")
    ax3.legend(loc="upper left", fontsize=7.5)
    ax3.grid(True, linestyle=":", alpha=0.6)

    # 4. Statutory Decision Space
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axvspan(0, 450, color="#FEE2E2", alpha=0.5, label="FAIL: Nutritional Deficit")
    ax4.axvspan(450, 600, ymin=0.48, ymax=1.0, color="#DCFCE7", alpha=0.6, label="PASS: P(E>=450)>=0.90 & P(P>=12)>=0.90")
    ax4.axvspan(450, 600, ymin=0.0, ymax=0.48, color="#FEF9C3", alpha=0.6, label="BORDERLINE: Deficit / High Variance")
    ax4.scatter([298], [6.4], color="#0F172A", s=80, marker="X", zorder=5, label="Meal Estimate (298 kcal, 6.4 g)")
    ax4.set_xlim(350, 600)
    ax4.set_ylim(0, 25)
    ax4.set_title("4. Statutory Decision Space & Governance Boundaries", fontsize=10.0, fontweight="bold", color="#1E293B", family="DejaVu Sans")
    ax4.set_xlabel("Energy (kcal)", fontsize=8.5, family="DejaVu Sans")
    ax4.set_ylabel("Protein (grams)", fontsize=8.5, family="DejaVu Sans")
    ax4.legend(loc="lower right", fontsize=7.5)
    ax4.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_path = os.path.join(OUTPUT_DIR, "nutrition_assessment_and_uncertainty.png")
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print("✅ Generated:", out_path)


def main():
    print("🎨 Generating all 9 High-Resolution Publication-Quality Diagrams...")
    generate_figure_1_1()
    generate_figure_1_2()
    generate_figure_5_1()
    generate_figure_5_2()
    generate_figure_5_3a()
    generate_figure_5_3b()
    generate_figure_5_3c()
    generate_figure_6_1()
    generate_figure_6_2()
    print("🎉 All 9 diagrams regenerated cleanly in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
