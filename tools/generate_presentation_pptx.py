"""Generate a professional 20-slide widescreen (16:9) PowerPoint presentation for NutriSense.

B.E. Major Project Viva Defense & Academic Review
Department of Machine Learning, B.M.S. College of Engineering, Bengaluru

Lead Architect: S S Gokula Swamy (1BM23AI158)
Team: Somanath S D (1BM23AI187), Roshanth V (1BM23AI155), Aryan Kumar (1BM23AI037)
Project Guide: Prof. Varsha R, Assistant Professor, Dept. of ML, BMSCE
"""

import os
import shutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# Widescreen 16:9 dimensions
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)

# Color Palette (Dark Academic Slate & Emerald)
BG_COLOR = RGBColor(15, 23, 42)        # Slate 900 #0f172a
CARD_BG = RGBColor(30, 41, 59)         # Slate 800 #1e293b
CARD_BORDER = RGBColor(51, 65, 85)     # Slate 700 #334155
CARD_HEADER_BG = RGBColor(24, 34, 53)  # Slate 850
TEXT_PRIMARY = RGBColor(248, 250, 252) # Slate 50 #f8fafc
TEXT_MUTED = RGBColor(148, 163, 184)   # Slate 400 #94a3b8
TEXT_BODY = RGBColor(226, 232, 240)    # Slate 200 #e2e8f0
ACCENT_EMERALD = RGBColor(16, 185, 129) # Emerald 500 #10b981
ACCENT_CYAN = RGBColor(56, 189, 248)   # Sky 400 #38bdf8
ACCENT_AMBER = RGBColor(245, 158, 11)  # Amber 500 #f59e0b
ACCENT_RED = RGBColor(239, 68, 68)     # Red 500 #ef4444

TEMP_CHARTS_DIR = "/tmp/nutrisense_pptx_charts"
os.makedirs(TEMP_CHARTS_DIR, exist_ok=True)


def generate_pipeline_chart() -> str:
    """Generate pipeline DAG diagram for Slide 6."""
    path = os.path.join(TEMP_CHARTS_DIR, "pipeline_dag.png")
    fig, ax = plt.subplots(figsize=(10.5, 3.2), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")

    stages = [
        ("S1: Scale Anchor", "ArUco (60mm) +\nImplicit Head", "#10b981"),
        ("S2a: Segmentation", "DeepLabV3 +\nSAM 2.1 Hiera", "#38bdf8"),
        ("S2b: Classifier", "SigLIP-2 (ViT-B)\n115 Indian Dishes", "#818cf8"),
        ("S3a: Metric Depth", "MoGe-2 (ViT-L)\nAnnulus Table Plane", "#f59e0b"),
        ("S3b: Mass Head", "Volumetric Fusion\n+ DINOv2-S Prior", "#ec4899"),
        ("S4/S5: Compliance", "4k Monte Carlo\nPM POSHAN Verdict", "#10b981"),
    ]

    for i, (title, sub, col) in enumerate(stages):
        x = i * 1.8 + 0.1
        rect = Rectangle((x, 0.4), 1.5, 1.8, facecolor="#1e293b", edgecolor=col, linewidth=2, transform=ax.transData)
        ax.add_patch(rect)
        ax.text(x + 0.75, 1.8, title, ha="center", va="center", color="#f8fafc", weight="bold", fontsize=10)
        ax.text(x + 0.75, 1.1, sub, ha="center", va="center", color="#94a3b8", fontsize=8.5)

        if i < len(stages) - 1:
            ax.annotate("", xy=(x + 1.8, 1.3), xytext=(x + 1.5, 1.3),
                        arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=2.5))

    ax.set_xlim(-0.2, 10.8)
    ax.set_ylim(0.0, 2.5)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return path


def generate_weighed_bar_chart() -> str:
    """Generate 4-way estimation bar chart for Slide 16."""
    path = os.path.join(TEMP_CHARTS_DIR, "weighed_bars.png")
    fig, ax = plt.subplots(figsize=(6.5, 4.0), facecolor="#1e293b")
    ax.set_facecolor("#1e293b")

    dishes = ["Dish 1\n(Rice+Sambar)", "Dish 2\n(Rice+Rasam)", "Dish 3\n(Chappati)", "Dish 5\n(Veg Biryani)", "Dish 6\n(Chicken Biryani)"]
    gt = [450.0, 338.0, 191.0, 150.0, 351.0]
    pred_mode_a = [383.3, 346.2, 165.5, 151.1, 358.8]
    pred_mode_b = [433.1, 325.9, 177.5, 181.7, 262.7]

    x = np.arange(len(dishes))
    width = 0.26

    ax.bar(x - width, gt, width, label="Ground Truth (Scale)", color="#38bdf8", edgecolor="#0284c7")
    ax.bar(x, pred_mode_a, width, label="Mode A (ArUco Fused)", color="#10b981", edgecolor="#059669")
    ax.bar(x + width, pred_mode_b, width, label="Mode B (Card-Free)", color="#f59e0b", edgecolor="#d97706")

    ax.set_ylabel("Portion Weight (grams)", color="#f8fafc", fontsize=10, weight="bold")
    ax.set_title("Physical Scale vs NutriSense Estimation", color="#f8fafc", fontsize=11, weight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(dishes, color="#94a3b8", fontsize=8.5)
    ax.tick_params(colors="#94a3b8", which="both")
    ax.grid(axis="y", linestyle="--", alpha=0.2, color="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#334155")
    ax.legend(facecolor="#0f172a", edgecolor="#334155", labelcolor="#f8fafc", fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return path


def generate_bias_reduction_chart() -> str:
    """Generate Card-Free Mode B bias reduction chart for Slide 17."""
    path = os.path.join(TEMP_CHARTS_DIR, "bias_reduction.png")
    fig, ax = plt.subplots(figsize=(6.2, 4.0), facecolor="#1e293b")
    ax.set_facecolor("#1e293b")

    metrics = ["Signed Mass Bias (g)", "Out-of-Fold MAE (g)"]
    baseline = [-223.52, 225.40]
    annulus_fit = [-44.40, 153.23]

    x = np.arange(len(metrics))
    width = 0.35

    b1 = ax.bar(x - width/2, baseline, width, label="Baseline (Plate Plane Collapse)", color="#ef4444", edgecolor="#b91c1c")
    b2 = ax.bar(x + width/2, annulus_fit, width, label="Annulus Fit + Frustum Fusion", color="#10b981", edgecolor="#047857")

    ax.set_ylabel("Error (grams)", color="#f8fafc", fontsize=10, weight="bold")
    ax.set_title("Card-Free Mode B: 80.1% Signed Bias Reduction", color="#f8fafc", fontsize=11, weight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, color="#94a3b8", fontsize=9, weight="bold")
    ax.tick_params(colors="#94a3b8", which="both")
    ax.axhline(0, color="#64748b", linewidth=1.2, linestyle="--")
    ax.grid(axis="y", linestyle="--", alpha=0.2, color="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#334155")

    # Add data callout labels
    ax.text(0 - width/2, -245, "-223.5 g", ha="center", color="#ef4444", weight="bold", fontsize=9)
    ax.text(0 + width/2, -65, "-44.4 g\n(80.1% cut)", ha="center", color="#10b981", weight="bold", fontsize=9)
    ax.text(1 - width/2, 235, "225.4 g", ha="center", color="#ef4444", weight="bold", fontsize=9)
    ax.text(1 + width/2, 163, "153.2 g\n(32% cut)", ha="center", color="#10b981", weight="bold", fontsize=9)

    ax.legend(facecolor="#0f172a", edgecolor="#334155", labelcolor="#f8fafc", fontsize=8.5, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return path


def add_background(slide):
    """Add solid dark navy background rectangle."""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    shape.fill.solid()
    shape.fill.fore_color.rgb = BG_COLOR
    shape.line.fill.background()
    return shape


def add_header(slide, title: str, category: str = "NUTRISENSE · B.E. MAJOR PROJECT DEFENSE"):
    """Add unified slide header with category eyebrow and title."""
    # Eyebrow
    tx_cat = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
    tf_c = tx_cat.text_frame
    tf_c.word_wrap = True
    p_c = tf_c.paragraphs[0]
    p_c.text = category.upper()
    p_c.font.size = Pt(10)
    p_c.font.bold = True
    p_c.font.color.rgb = ACCENT_CYAN

    # Title
    tx_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.7), Inches(0.7))
    tf_t = tx_title.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title
    p_t.font.size = Pt(22)
    p_t.font.bold = True
    p_t.font.color.rgb = TEXT_PRIMARY

    # Accent Line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.42), Inches(11.7), Inches(0.02))
    line.fill.solid()
    line.fill.fore_color.rgb = CARD_BORDER
    line.line.fill.background()


def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=CARD_BORDER):
    """Add rounded container card."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1.2)
    return shape


def set_notes(slide, notes_text: str):
    """Attach rich speaker notes to slide."""
    slide.notes_slide.notes_text_frame.text = notes_text.strip()


def build_presentation(output_path: str):
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank_layout = prs.slide_layouts[6]

    print("🎨 Generating standalone chart assets...")
    pipeline_img = generate_pipeline_chart()
    weighed_bars_img = generate_weighed_bar_chart()
    bias_reduction_img = generate_bias_reduction_chart()

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    print("Slide 1: Title Slide...")
    s1 = prs.slides.add_slide(blank_layout)
    add_background(s1)

    # Main Card
    add_card(s1, Inches(1.0), Inches(0.8), Inches(11.333), Inches(5.9), bg_color=CARD_BG, border_color=ACCENT_EMERALD)

    tb = s1.shapes.add_textbox(Inches(1.4), Inches(1.1), Inches(10.5), Inches(5.2))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "NUTRISENSE"
    p.font.size = Pt(38)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD

    p2 = tf.add_paragraph()
    p2.text = "AI-Powered 3D Dietary Assessment & Nutrition Auditing from a Single Meal Photo"
    p2.font.size = Pt(18)
    p2.font.bold = True
    p2.font.color.rgb = TEXT_PRIMARY
    p2.space_before = Pt(6)

    p3 = tf.add_paragraph()
    p3.text = "B.E. Major Project Viva Defense & Final Academic Review · Course: 24AM7PWPW2 (2026–27)"
    p3.font.size = Pt(13)
    p3.font.color.rgb = ACCENT_CYAN
    p3.space_before = Pt(8)

    p4 = tf.add_paragraph()
    p4.text = "━" * 58
    p4.font.size = Pt(12)
    p4.font.color.rgb = CARD_BORDER
    p4.space_before = Pt(10)

    # Team attribution
    p5 = tf.add_paragraph()
    p5.text = "Project Lead & Principal Architect: S S Gokula Swamy (1BM23AI158)"
    p5.font.size = Pt(14)
    p5.font.bold = True
    p5.font.color.rgb = ACCENT_EMERALD
    p5.space_before = Pt(10)

    p6 = tf.add_paragraph()
    p6.text = "Frontend Architecture & UI Lead: Somanath S D (1BM23AI187)\nNutritional Knowledge Base & IFCT Lead: Roshanth V (1BM23AI155)\nExperimental Benchmarking & QA Lead: Aryan Kumar (1BM23AI037)"
    p6.font.size = Pt(12)
    p6.font.color.rgb = TEXT_BODY
    p6.space_before = Pt(4)

    p7 = tf.add_paragraph()
    p7.text = "Project Guide: Prof. Varsha R, Assistant Professor\nDepartment of Machine Learning, B.M.S. College of Engineering, Bengaluru — 560 019"
    p7.font.size = Pt(12)
    p7.font.bold = True
    p7.font.color.rgb = ACCENT_CYAN
    p7.space_before = Pt(12)

    set_notes(s1, """
Good morning respected members of the evaluation committee, external examiners, and our project guide Prof. Varsha R.

Welcome to the B.E. Major Project defense for NutriSense: AI-Powered 3D Dietary Assessment and Nutrition Auditing from a Single Meal Photo.

Our project addresses one of the most critical public health monitoring challenges in India—auditing institutional meal adequacy under the statutory PM POSHAN national mid-day meal scheme.

Today, we will present our end-to-end 6-stage computer vision and physical metrology system. Our Lead Architect, S S Gokula Swamy, engineered the core 3D vision, depth unprojection, and machine learning pipelines; Somanath S D built the full-stack React 19 web application; Roshanth V curated the ICMR-NIN IFCT nutritional database; and Aryan Kumar executed the real-world laboratory scale benchmark.

Let us begin with the institutional problem and public health motivation.
""")

    # =========================================================================
    # SLIDE 2: EXECUTIVE SUMMARY & PROBLEM FORMULATION
    # =========================================================================
    print("Slide 2: Executive Summary...")
    s2 = prs.slides.add_slide(blank_layout)
    add_background(s2)
    add_header(s2, "Executive Summary & Problem Formulation")

    # 3 Cards
    add_card(s2, Inches(0.8), Inches(1.8), Inches(3.6), Inches(5.0))
    tb = s2.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(3.2), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "The Scale of the Problem"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_AMBER
    p2 = tf.add_paragraph()
    p2.text = "• PM POSHAN serves 120M children across 1.14M schools daily in India.\n• High operational friction: manual kitchen weigh-ins are unscalable and disrupt serving lines.\n• Paper records lack tamper-proof photographic verification.\n• Widespread nutritional variance leads to silent micro-nutrient deficits and child stunting."
    p2.font.size = Pt(12)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(12)

    add_card(s2, Inches(4.85), Inches(1.8), Inches(3.6), Inches(5.0))
    tb = s2.shapes.add_textbox(Inches(5.05), Inches(2.0), Inches(3.2), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Why 2D Vision Collapses"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_RED
    p2 = tf.add_paragraph()
    p2.text = "• Scale Ambiguity: A 2D photo has no depth; a plate close to the camera looks identical to a giant serving tray.\n• High-sided Steel Thalis: Plate rims obscure the true tabletop ground plane.\n• Volume Collapse: 2D pixel area heuristics exhibit >60% errors on dense mounds and deep katoris.\n• Raw geometry without learned priors yields catastrophic +500% errors."
    p2.font.size = Pt(12)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(12)

    add_card(s2, Inches(8.9), Inches(1.8), Inches(3.6), Inches(5.0))
    tb = s2.shapes.add_textbox(Inches(9.1), Inches(2.0), Inches(3.2), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "NutriSense Solution"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD
    p2 = tf.add_paragraph()
    p2.text = "• Metric Scale Anchoring: 60mm ArUco card (Mode A) + LODO-CV implicit neural scale head (Mode B).\n• 3D Monocular Reconstruction: MoGe-2 (ViT-L) surface unprojection with tabletop annulus plane fitting.\n• Volumetric Mass Fusion: Heteroscedastic DINOv2-S prior + empirical recipe densities.\n• Comonotonic Monte Carlo: 4,000-draw statutory compliance against PM POSHAN norms."
    p2.font.size = Pt(12)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(12)

    set_notes(s2, """
On Slide 2, we formulate the core engineering problem.

The Government of India's PM POSHAN scheme feeds over 120 million schoolchildren every single school day. However, monitoring meal quality remains a massive challenge. Traditional manual logging on paper registers is subjective, slow, and impossible to audit independently.

Why can't we simply use existing 2D mobile apps? Because 2D photos suffer from fundamental scale ambiguity. A 2D pixel count tells you nothing about physical depth or mass. In Indian school lunchrooms, meals are served on stainless steel thalis with high rims and deep katori bowls. In our experiments, naive 2D area heuristics caused over 500% volumetric error!

NutriSense solves this by combining physical fiducial scale anchoring, deep metric monocular depth, annulus plane fitting, and a comonotonic Monte Carlo compliance engine.
""")

    # =========================================================================
    # SLIDE 3: MOTIVATION & STATUTORY MANDATE
    # =========================================================================
    print("Slide 3: Motivation & Statutory Mandate...")
    s3 = prs.slides.add_slide(blank_layout)
    add_background(s3)
    add_header(s3, "Statutory Mandates & Institutional Requirements")

    add_card(s3, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s3.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.1), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "PM POSHAN Legal Norms (NFSA 2013)"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "Under the National Food Security Act (NFSA 2013), hot cooked meals must satisfy strict per-child statutory minimums:\n\n" \
              "1. Primary Tier (Classes 1–5):\n" \
              "   • Minimum Energy: 450 kcal\n" \
              "   • Minimum Protein: 12.0 g\n" \
              "   • Foodgrains: 100 g, Pulses: 20 g, Vegetables: 50 g\n\n" \
              "2. Upper-Primary Tier (Classes 6–8):\n" \
              "   • Minimum Energy: 700 kcal\n" \
              "   • Minimum Protein: 20.0 g\n" \
              "   • Foodgrains: 150 g, Pulses: 30 g, Vegetables: 75 g\n\n" \
              "Statutory Violation Risk: Meal dilution directly deprives growing children of brain development nutrients."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s3, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s3.shapes.add_textbox(Inches(7.1), Inches(2.0), Inches(5.1), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Operational Canteen Constraints"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD
    p2 = tf.add_paragraph()
    p2.text = "To deploy in real government schools, any AI solution must satisfy severe non-cooperative constraints:\n\n" \
              "• Zero Disruptions: Inspection must complete in under 5 seconds from a single quick smartphone photo.\n" \
              "• Severe Lighting & Glare: Stainless steel thalis cause specular highlights and reflections that deceive edge detectors.\n" \
              "• Handheld Perspective Variations: Photos are captured between 0° (overhead) and 65° (oblique tilt).\n" \
              "• High Density Packing: Mixed meals (rice + sambar + chutney) have overlapping boundaries and varying void fractions.\n" \
              "• Audit Integrity: Must provide cryptographic audit logs (sha256 manifests) preventing manual tampering."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s3, """
Slide 3 highlights the statutory framework. Under Schedule II of the National Food Security Act 2013, providing 450 kcal and 12 grams of protein for primary children, and 700 kcal and 20 grams of protein for upper-primary children, is a legally enforceable right.

Yet in reality, school canteens face severe operational friction. Headmasters cannot weigh individual plates on digital balances while 300 hungry children stand in line.

Any optical system must work from a single handheld capture, handle harsh kitchen lighting, specular reflections off stainless steel thalis, and variable smartphone camera angles up to 65 degrees, without failing or hallucinating.
""")

    # =========================================================================
    # SLIDE 4: RELATED WORK & RESEARCH GAPS
    # =========================================================================
    print("Slide 4: Related Work & Research Gaps...")
    s4 = prs.slides.add_slide(blank_layout)
    add_background(s4)
    add_header(s4, "Related Work & Prior Art Gaps")

    # Table layout comparing approaches
    table_shape = s4.shapes.add_table(5, 5, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.8))
    table = table_shape.table
    table.columns[0].width = Inches(2.3)
    table.columns[1].width = Inches(2.3)
    table.columns[2].width = Inches(2.3)
    table.columns[3].width = Inches(2.4)
    table.columns[4].width = Inches(2.4)

    headers = ["Methodology", "Representative Prior Art", "Key Strength", "Fatal Failure Mode", "NutriSense Superiority"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD_HEADER_BG
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        p.alignment = PP_ALIGN.CENTER

    data = [
        ("2D Segmentation &\nArea Heuristics", "Food101, Nutrition5k\n(Meyers et al., 2015)", "Fast, lightweight\n2D pixel counting", "Scale ambiguity; ignores height;\n>60% error on mounds", "True metric 3D depth unprojection\nvia MoGe-2 (ViT-L)"),
        ("Multi-View 3D &\nRGB-D Stereo", "DepthFood, Im2Calorie\n(Fang et al., 2018)", "Accurate 3D mesh\nreconstruction", "Requires multiple photos or\nexpensive LiDAR/stereo rigs", "Single-photo monocular inference;\nzero multi-photo burden"),
        ("VLM Black-Box\nPrompting", "GPT-4o, Gemini 1.5 Pro\n(Lu et al., 2024)", "Open-vocabulary food\nunderstanding", "Severe volumetric hallucinations;\nno physical scale ground truth", "Grounded physical metrology;\nstrict 19-key wire contract"),
        ("Monocular Depth\nBaselines", "MiDaS, Depth Anything\n(Yang et al., 2024)", "Good relative depth\nsalience", "Relative disparity only;\ncollapses on flat food surfaces", "Annulus tabletop fit + tare offset;\nsub-mm plane regression RMS"),
    ]

    for row_idx, row in enumerate(data, start=1):
        for col_idx, text in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            cell.text = text
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG if row_idx % 2 == 1 else RGBColor(22, 30, 46)
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            p.font.color.rgb = ACCENT_EMERALD if col_idx == 4 else TEXT_BODY
            if col_idx == 4:
                p.font.bold = True

    set_notes(s4, """
Slide 4 positions NutriSense against existing literature.

Traditional 2D methods like Nutrition5k rely on pixel area regression. But a flat 2D area cannot distinguish between 50 grams of flat rice spread across a plate and 300 grams of compacted rice mounded high.

Multi-view stereo and RGB-D cameras require children to take 10 photos around a plate, or require specialized hardware like Intel RealSense or LiDAR, which are completely infeasible for rural schools.

Commercial VLMs like GPT-4o hallucinate portions wildly because they have no physical reference scale. They might guess 200 calories when the true value is 600 calories.

NutriSense provides the missing link: single-photo monocular metric depth with explicit physical scale anchoring and comonotonic uncertainty propagation.
""")

    # =========================================================================
    # SLIDE 5: MASTER MODEL-BY-MODEL ACCURACY TABLE
    # =========================================================================
    print("Slide 5: Master Accuracy Table...")
    s5 = prs.slides.add_slide(blank_layout)
    add_background(s5)
    add_header(s5, "Master Model-by-Model & End-to-End Accuracy Summary")

    table_shape = s5.shapes.add_table(8, 5, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.1))
    table = table_shape.table
    table.columns[0].width = Inches(2.6)
    table.columns[1].width = Inches(2.5)
    table.columns[2].width = Inches(2.0)
    table.columns[3].width = Inches(2.4)
    table.columns[4].width = Inches(2.2)

    headers = ["Stage & Subsystem", "Architecture / Model", "Primary Accuracy (%)", "Key Error / Overlap Metric", "Evaluated Scope"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD_HEADER_BG
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        p.alignment = PP_ALIGN.CENTER

    accuracy_data = [
        ("S1a: Physical Anchor", "60mm ArUco 7-ID + Michelson Gate", "100.0% Detection", "Plane RMS: 0.74 mm (Scale ±0.8%)", "23 Real Captures (Dishes 1–6)"),
        ("S1b: Implicit Scale Head", "Teacher-Student DINOv2-S Regressor", "77.00% Scale Acc", "Scale MAE: 0.00251 cm/px (23.0% MAPE)", "6-Fold LODO-CV (Held-Out Dishes)"),
        ("S2: Semantic Segmentation", "DeepLabV3 + SAM 2.1 Hiera", "95.81% FG Dice", "Food IoU: 82.11%, Macro Dice: 89.76%", "WED DEV (108 views, 21 plates)"),
        ("S2b: Primary Classifier", "Google SigLIP-2 (ViT-B/16, α=0.65)", "82.27% Top-1", "Top-5: 96.40%, Macro Recall: 82.12%", "WED DEV (1,218 crops, 41 classes)"),
        ("S3a: Metric 3D Depth", "MoGe-2 (ViT-L) + Annulus Table Fit", "Sub-mm Plane RMS", "Annular Ring 1.5–5.5cm, Tare 3.5mm", "Monocular Surface Unprojection"),
        ("S3b: Mass Estimation Head", "Frozen DINOv2-S + Heteroscedastic MLP", "81.70% DEV / 80.01% LOCKED", "DEV MAE: 15.03 g, LOCKED MAE: 14.67 g", "WED DEV (1.2k) & LOCKED (2.8k ROIs)"),
        ("End-to-End: Primary Overhead", "Full 6-Stage Deterministic Pipeline", "90.58% Mean Acc", "MAE: 29.70 g (MAPE: 9.42%)", "Real Weighed Handheld Meals (N=6)"),
    ]

    for row_idx, row in enumerate(accuracy_data, start=1):
        for col_idx, text in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            cell.text = text
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG if row_idx % 2 == 1 else RGBColor(22, 30, 46)
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            if col_idx == 2:
                p.font.bold = True
                p.font.color.rgb = ACCENT_EMERALD
            else:
                p.font.color.rgb = TEXT_BODY

    set_notes(s5, """
Slide 5 directly answers the primary question asked by our academic evaluators: 'What is the accuracy of each individual model and the combined pipeline?'

Here is our Master Table:
1. Stage S1a: Physical Fiducial Anchor achieved 100% detection on all 23 real handheld plates with a 0.74 mm median plane fit RMS error.
2. Stage S1b: The Card-Free Implicit Scale Head achieved 77.0% scale accuracy under strict 6-fold leave-one-dish-out cross-validation.
3. Stage S2: Semantic Segmentation achieved a 95.81% Foreground Dice score and 82.11% Food IoU on WED DEV.
4. Stage S2b: SigLIP-2 Food Classifier achieved 82.27% Top-1 categorical accuracy and 96.40% Top-5 accuracy.
5. Stage S3b: Mass estimation achieved 81.70% accuracy on WED DEV and 80.01% on the cryptographically locked WED test split.
6. Combined End-to-End Pipeline: On primary overhead real handheld smartphone meals weighed on lab scales, NutriSense achieved 90.58% mean accuracy, with an MAE of only 29.70 grams!
""")

    # =========================================================================
    # SLIDE 6: SYSTEM ARCHITECTURE & 6-STAGE PIPELINE
    # =========================================================================
    print("Slide 6: System Architecture...")
    s6 = prs.slides.add_slide(blank_layout)
    add_background(s6)
    add_header(s6, "6-Stage Modular System Architecture")

    # Add Diagram Image
    s6.shapes.add_picture(pipeline_img, Inches(0.8), Inches(1.8), Inches(11.7), Inches(3.2))

    # Architecture Bullet Card below
    add_card(s6, Inches(0.8), Inches(5.2), Inches(11.7), Inches(1.8))
    tb = s6.shapes.add_textbox(Inches(1.0), Inches(5.3), Inches(11.3), Inches(1.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Modular Pipeline Design Principles"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "• Strict 19-Key Wire Contract: Type-safe parity between Python backend (engine/contract.py) and TypeScript frontend (contract.gen.ts).\n• Thread-Safe Model Registry: Lazy loading and singleton caching (models/registry.py) preventing CUDA OOM spikes.\n• Dual-Mode Execution: School Mode (statutory PM POSHAN audit) vs General Mode (WHO/FAO individual goals).\n• Deterministic Reproducibility: Cryptographically verified evaluation locks (502/502 files pinned via sha256 in tools/check_locked.py)."
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(4)

    set_notes(s6, """
Slide 6 illustrates our end-to-end modular architecture.

The pipeline executes a directed acyclic graph across 6 distinct stages:
Stage 1 detects the metric anchor.
Stage 2 generates semantic food masks using DeepLabV3 and SAM 2.1, and classifies dishes using SigLIP-2.
Stage 3 unprojects 3D point clouds via MoGe-2 and estimates physical mass.
Stage 4 looks up nutritional density from our ICMR-NIN IFCT knowledge graph.
Stage 5 propagates uncertainty through a 4,000-draw comonotonic Monte Carlo engine to issue the compliance verdict.

Notice our strict architectural guardrails: the backend and frontend are synchronized via a 19-key JSON wire contract, and every single test file is cryptographically locked with sha256 checksums to guarantee zero data leakage.
""")

    # =========================================================================
    # SLIDE 7: STAGE S1a: PHYSICAL FIDUCIAL REFERENCE ANCHOR
    # =========================================================================
    print("Slide 7: Stage S1a...")
    s7 = prs.slides.add_slide(blank_layout)
    add_background(s7)
    add_header(s7, "Stage S1a: Physical Fiducial Anchor & Quiet-Zone Gate")

    add_card(s7, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s7.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Fiducial Design & Admission Protocol"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD
    p2 = tf.add_paragraph()
    p2.text = "• Physical Reference: 60 mm ArUco marker (DICT_4X4_50, ID 7) printed on a standard laminated card or cardholder.\n• Pixel Scale Derivation: Recovers camera extrinsics and local metric scale (cm/px) via Perspective-n-Point (solvePnP).\n• Sub-Millimeter 3D Plane: Unprojects card corners to fit the true reference tabletop plane:\n  Plane RMS: 0.32 mm – 1.28 mm (Median: 0.74 mm).\n• Zero Plate Rim Spill: Card plane fitting guarantees the reference ground is the table, not the food vessel rim."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s7, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s7.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Dual-Boundary Michelson Contrast Gate"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "Problem: Glossy cardboard reflections and steel table glares cause false marker admissions.\n\n" \
              "Mathematical Formulation (Ledger 033):\n" \
              "We enforce a dual quiet-zone photometric gate:\n" \
              "  μ_white = mean intensity of outer margin Q_outer \\ Q_inner\n" \
              "  μ_black = mean intensity of inner marker border B_marker\n" \
              "  C_M = (μ_white - μ_black) / (μ_white + μ_black) ≥ 0.42\n\n" \
              "Verified Outcome:\n" \
              "• 100.0% Detection & Admission (23/23 real captures).\n" \
              "• 0% False Positives under intense steel plate glare.\n" \
              "• Flat 2D Linear Scale Error: ±0.06% to ±1.10% across all angles."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s7, """
Slide 7 covers Stage S1a: Physical Fiducial Anchoring.

To establish ground-truth metric scale, we place a 60 mm ArUco marker beside the plate. Using solvePnP, we derive the exact pixel-to-centimeter conversion factor.

However, in steel canteens, reflections off stainless steel tables often mimic marker squares, leading to false detections. In Ledger 033, we formulated the Dual-Boundary Michelson Contrast Gate. By measuring the Michelson contrast ratio between the outer quiet zone and inner black bits, and enforcing CM >= 0.42, we eliminated all glare false-positives.

Across all 23 real handheld smartphone captures in our test dataset, the admission rate is 100%, and the 3D plane RMS error is just 0.74 mm!
""")

    # =========================================================================
    # SLIDE 8: STAGE S1b: AUXILIARY IMPLICIT SCALE HEAD
    # =========================================================================
    print("Slide 8: Stage S1b...")
    s8 = prs.slides.add_slide(blank_layout)
    add_background(s8)
    add_header(s8, "Stage S1b: Card-Free Implicit Scale Estimation (LODO-CV)")

    add_card(s8, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s8.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Markerless Teacher-Student Distillation"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_AMBER
    p2 = tf.add_paragraph()
    p2.text = "• Objective: Enable Card-Free (Mode B) estimation when students forget or lose the physical ArUco card.\n• Architecture: Teacher-student regression head operating on frozen DINOv2-S and SigLIP-2 multi-scale feature tokens.\n• Marker-Dropout Training: Card pixels are artificially inpainted and masked during training so the network learns natural plate priors (e.g., standard 28 cm thali circumference).\n• Multi-Task Output: Jointly regresses metric scale (cm/px), depth scaling factor (s_Z), and coarse portion mass."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s8, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s8.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "6-Fold Leave-One-Dish-Out (LODO-CV)"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "Rigorous Out-of-Distribution Validation (Ledger 036):\n\n" \
              "To prevent dish memorization, we evaluate using 6-Fold Leave-One-Dish-Out Cross-Validation:\n\n" \
              "• Fold 1 (Dish 1 - Rice+Sambar): Scale MAE: 0.00201 cm/px (19.1% MAPE)\n" \
              "• Fold 2 (Dish 2 - Rice+Rasam): Scale MAE: 0.00122 cm/px (8.59% MAPE)\n" \
              "• Fold 4 (Dish 4 - Biryani Deep): Scale MAE: 0.00020 cm/px (1.94% MAPE)\n" \
              "• Fold 5 (Dish 5 - Biryani Plate): Scale MAE: 0.00282 cm/px (26.6% MAPE)\n\n" \
              "Overall LODO Scale Performance:\n" \
              "• Mean Scale MAE: 0.00251 cm/px (77.0% Accuracy / 23.0% MAPE)\n" \
              "• Proves genuine out-of-fold generalization on unseen meals."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s8, """
Slide 8 presents our Card-Free breakthrough: Stage S1b Implicit Scale Head.

What if a student takes a photo without placing an ArUco card? In commit 53e99bb and Ledger 036, we designed an implicit neural scale head using DINOv2-S embeddings.

To prevent data leakage, we did not evaluate with simple random train-test splits. Instead, we instituted a strict 6-Fold Leave-One-Dish-Out Cross-Validation. When evaluating Dish 1, all 6 photos of Dish 1 were completely withheld from training.

The model achieved an out-of-fold scale MAE of 0.00251 cm/px, representing 77.0% scale accuracy without any reference marker present!
""")

    # =========================================================================
    # SLIDE 9: STAGE S2a: FOOD SEGMENTATION & MASKING
    # =========================================================================
    print("Slide 9: Stage S2a...")
    s9 = prs.slides.add_slide(blank_layout)
    add_background(s9)
    add_header(s9, "Stage S2a: Semantic Food Segmentation & Masking")

    add_card(s9, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s9.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Two-Stage Foundation Segmentation"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "1. DeepLabV3 (ResNet-50 backbone):\n" \
              "   • Generates coarse semantic category priors across 41 food classes.\n" \
              "   • Distinguishes food substances from table, napkin, and plate rims.\n\n" \
              "2. Segment Anything Model 2.1 (SAM 2.1 Hiera-Large):\n" \
              "   • Zero-shot instance boundary refinement.\n" \
              "   • Prompted via dense grid boxes and semantic centroid seeds.\n" \
              "   • Captures fine granular boundaries of loose rice, gravies, and rotis."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s9, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s9.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Quantified Segmentation Benchmark"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD
    p2 = tf.add_paragraph()
    p2.text = "Evaluated on WED DEV (108 views, 21 distinct plates):\n\n" \
              "• Foreground Union Dice: 95.81%\n" \
              "• Foreground IoU (Jaccard Index): 91.96%\n" \
              "• Macro Food Dice (across all 41 classes): 89.76%\n" \
              "• Macro Food IoU: 82.11%\n" \
              "• Boundary F1 Score: 59.73%\n\n" \
              "Decoy Suppression & Mask Integrity:\n" \
              "• Completely eliminated duplicate mask inflation (sum/top area ratio reduced from 7.71× to 1.00×).\n" \
              "• Plate-edge clipping guards prevent masks from bleeding onto the table."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s9, """
Slide 9 covers Stage S2a: Food Segmentation.

We deploy a hybrid architecture combining DeepLabV3 and Meta's SAM 2.1 Hiera. DeepLabV3 provides high-level semantic category priors, while SAM 2.1 refines the boundaries down to single grains of rice.

On the 108-view WED DEV benchmark, this pipeline achieved a 95.81% Foreground Dice score and 82.11% Macro Food IoU.

Crucially, in earlier versions of our pipeline, overlapping masks caused mask explosion where the sum of component areas was 7.7 times larger than the plate! In Ledger 033, we implemented strict spatial non-maximum suppression and decoy suppression, driving the sum-to-top area ratio to exactly 1.00.
""")

    # =========================================================================
    # SLIDE 10: STAGE S2b: MULTI-ITEM FOOD CLASSIFICATION
    # =========================================================================
    print("Slide 10: Stage S2b...")
    s10 = prs.slides.add_slide(blank_layout)
    add_background(s10)
    add_header(s10, "Stage S2b: Multi-Item Food Classification (SigLIP-2)")

    add_card(s10, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s10.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Google SigLIP-2 Vision-Language Backbone"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "• Model: Google SigLIP-2 (ViT-B/16) pre-trained with sigmoid loss for multi-label visual grounding.\n• Hybrid Pooling (α=0.65): Combines global CLS token (35%) with food-region masked average pooling (65%) to focus strictly on food textures.\n• Cosine Nearest-Neighbor Gallery: Matches food crops against verified dish reference embeddings.\n• Sub-Threshold Rejection Floor: Enforces a strict minimum similarity threshold (0.82) preventing false secondary recognition (e.g. steel reflections misclassified as chutney)."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s10, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s10.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Classification Benchmark Performance"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD
    p2 = tf.add_paragraph()
    p2.text = "Evaluated on WED DEV (1,218 food crops, 41 classes):\n\n" \
              "• Top-1 Categorical Accuracy: 82.27%\n" \
              "• Top-5 Categorical Accuracy: 96.40%\n" \
              "• Macro-Averaged Recall: 82.12%\n" \
              "• Gallery Nearest-Neighbor Accuracy: 81.03%\n\n" \
              "Eliminating Phantom Secondary Recognition:\n" \
              "• In previous pipelines, secondary crops were assigned spurious labels like 'pickle' or 'curd' with low scores.\n" \
              "• Our bounded fallback mechanism guarantees that sub-threshold items abstain cleanly instead of corrupting nutritional totals."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s10, """
Slide 10 details Stage S2b: Multi-Item Food Classification.

We use Google SigLIP-2 ViT-B/16. Unlike standard CLIP which uses softmax contrastive loss, SigLIP uses a sigmoid pairwise loss that operates much better on fine-grained dish textures.

We designed a hybrid pooling strategy with alpha=0.65, combining the global image embedding with the masked region embedding. On 1,218 food crops in WED DEV, SigLIP-2 achieved 82.27% Top-1 accuracy and 96.40% Top-5 accuracy.

Furthermore, we resolved the 'phantom secondary recognition' bug: when a reflection appeared on a steel bowl rim, naive classifiers previously labeled it as 'chutney' or 'curd'. By enforcing a hard 0.82 cosine floor, our model correctly abstains.
""")

    # =========================================================================
    # SLIDE 11: STAGE S2c: TWO-TIER INDIAN FOOD KNOWLEDGE HUB
    # =========================================================================
    print("Slide 11: Stage S2c...")
    s11 = prs.slides.add_slide(blank_layout)
    add_background(s11)
    add_header(s11, "Stage S2c: Two-Tier Indian Food Knowledge Hub (115 Dishes)")

    add_card(s11, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s11.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Corpus Expansion & Ingestion"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_AMBER
    p2 = tf.add_paragraph()
    p2.text = "In commit 060cd7b, we scaled NutriSense beyond the baseline 41 WED classes by ingesting major open-source Indian datasets:\n\n" \
              "• Bharat Food Dataset: 961 authentic regional food images.\n" \
              "• Rajistics Indian Food Corpus: 941 curated multi-state meal captures.\n" \
              "• Total Ingested Bank: 1,206 multi-view visual prototypes covering 115 regional Indian dishes.\n" \
              "• Cuisine Breadth: South Indian (Bisi Bele Bath, Rasam, Sambar, Idli, Dosa) and North Indian (Dal Makhani, Rajma, Roti, Paneer)."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s11, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s11.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Two-Tier Hierarchical Routing"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "To guarantee zero regression on core WED benchmarks, we implemented two-tier hierarchical routing:\n\n" \
              "Tier 1 (Core WED 41-Class Gallery):\n" \
              "• Checks standard institutional recipes at match threshold ≥ 0.82.\n" \
              "• Bit-for-bit identical to locked benchmark standards.\n\n" \
              "Tier 2 (Expanded 115-Dish Indian Bank):\n" \
              "• Engaged when Tier 1 abstains.\n" \
              "• Computes visual-text ensemble fusion score:\n" \
              "  Score = 0.70 · S_visual + 0.30 · S_text ≥ 0.58\n" \
              "• Correctly identifies complex regional gravies and composite plates."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s11, """
Slide 11 highlights our Indian Food Knowledge Hub.

Standard academic food datasets like Food101 or Nutrition5k are overwhelmingly Western, featuring burgers, pizzas, and salads. They completely fail on Indian canteen staples like Sambar, Rasam, and Bisi Bele Bath.

In commit 060cd7b, we ingested 961 Bharat food images and 941 Rajistics captures, compiling 1,206 visual prototypes across 115 regional Indian dishes.

To protect our verified WED benchmark, we built a two-tier routing system. Tier 1 executes the primary 41-class gallery. If it abstains, Tier 2 queries the 115-dish Indian bank using visual-text fusion with a 0.58 acceptance threshold.
""")

    # =========================================================================
    # SLIDE 12: STAGE S3a: METRIC 3D DEPTH & RECONSTRUCTION
    # =========================================================================
    print("Slide 12: Stage S3a...")
    s12 = prs.slides.add_slide(blank_layout)
    add_background(s12)
    add_header(s12, "Stage S3a: Metric 3D Depth & Annulus Tabletop Fit")

    add_card(s12, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s12.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "MoGe-2 Metric Monocular Reconstruction"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD
    p2 = tf.add_paragraph()
    p2.text = "• Foundation Model: MoGe-2 (ViT-L) deep metric surface unprojection.\n• Unprojected Point Cloud: Recovers metric (X, Y, Z) coordinates from uncalibrated RGB photos:\n  (X, Y, Z) = Z · K⁻¹ [u, v, 1]ᵀ\n• Depth Consistency: Preserves true spatial curvature across convex rice mounds and concave bowl depressions.\n• Extreme Tilt Robustness: Accurately preserves vertical height even when photos are taken at 45°–65° oblique angles."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s12, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s12.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Tabletop Annulus Fitting & Tare Offset"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "The High-Rim Thali Challenge:\n" \
              "Fitting a plane to points near the plate edge samples the elevated steel rim, skewing the base plane by up to 35 mm!\n\n" \
              "Our Annulus Solution (engine/depth.py):\n" \
              "• We sample points strictly in an annular ring 1.5 cm to 5.5 cm OUTSIDE the detected plate perimeter.\n" \
              "• RANSAC plane regression fits the true tabletop support surface: n · p + d = 0.\n" \
              "• Calibrated Tare Offset: Food height h(u,v) = dist(p, plane) - 3.5 mm tare, accounting for the physical plate bottom thickness."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s12, """
Slide 12 explains Stage S3a: Metric 3D Depth Reconstruction.

To measure volume, we need metric depth. We deploy MoGe-2 ViT-L, which unprojects 2D pixels into a 3D point cloud of real-world metric coordinates.

However, stainless steel plates present a major physical obstacle: their raised rims sit 2 to 4 centimeters above the table. If you sample depth points on the plate rim, the fitted base plane floats in mid-air, cutting food volume by over 50%!

To fix this, we designed the Annulus Tabletop Fit. We sample 3D points in a ring 1.5 to 5.5 centimeters OUTSIDE the plate on the actual table. Then, we apply a 3.5 mm tare offset for the plate bottom thickness, reconstructing true physical height.
""")

    # =========================================================================
    # SLIDE 13: STAGE S3b: HETEROSCEDASTIC MASS ESTIMATION
    # =========================================================================
    print("Slide 13: Stage S3b...")
    s13 = prs.slides.add_slide(blank_layout)
    add_background(s13)
    add_header(s13, "Stage S3b: Heteroscedastic Mass Estimation & Fusion")

    add_card(s13, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s13.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Volumetric & Learned Prior Fusion"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_AMBER
    p2 = tf.add_paragraph()
    p2.text = "NutriSense computes mass through a dual-path fusion framework:\n\n" \
              "1. Geometric Volumetric Path:\n" \
              "   m_geom = ∫∫_M h(u,v) · s_px² · cos(θ) du dv · ρ_eff\n" \
              "   where ρ_eff is the empirical recipe density (e.g. rice 0.75, sambar 1.03 g/cm³).\n\n" \
              "2. Heteroscedastic Learned Prior (WeightHead):\n" \
              "   Frozen DINOv2-S + 3-layer MLP predicting log-normal mass distribution (μ_mass, σ_mass).\n\n" \
              "3. Scale-Modulated Bayesian Fusion:\n" \
              "   Weights geometry when metric anchor confidence is high; falls back gracefully to learned priors when tilt is extreme."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s13, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s13.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Benchmark Accuracy on WED Splits"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD
    p2 = tf.add_paragraph()
    p2.text = "Evaluated on standard Western & Eastern Dishes (WED) benchmark:\n\n" \
              "• WED DEV Carve (108 views, 21 plates, 1,218 ROIs):\n" \
              "  MAE: 15.034 g (81.70% Mass Accuracy)\n" \
              "  RMSE: 22.41 g, Pearson Correlation: r = 0.912\n\n" \
              "• WED LOCKED Holdout (48 plates, 2,793 ROIs):\n" \
              "  MAE: 14.667 g (80.01% Mass Accuracy)\n" \
              "  Evaluated once under zero-leakage cryptographic protocol.\n\n" \
              "• 5-Fold Plate-Grouped Cross-Validation:\n" \
              "  Pooled MAE: 16.421 g over 11,759 held-out food ROIs."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s13, """
Slide 13 details Stage S3b: Heteroscedastic Mass Estimation.

Mass cannot be solved by pure geometry alone, nor by pure deep learning alone. If you rely solely on geometry, occluded liquids fail. If you rely solely on deep learning, the model ignores the actual physical size of the plate.

NutriSense fuses both:
First, a physical volumetric integral integrates height over the segmented area, scaled by physical density priors.
Second, a frozen DINOv2-S heteroscedastic MLP predicts the expected mass distribution.

On the official WED benchmark, our mass estimator achieved 15.03 grams MAE on WED DEV and 14.67 grams MAE on the cryptographically locked WED test set, confirming 81.7% mass accuracy across thousands of diverse food items.
""")

    # =========================================================================
    # SLIDE 14: STAGES S4 & S5: NUTRITION & MONTE CARLO COMPLIANCE
    # =========================================================================
    print("Slide 14: Stages S4 & S5...")
    s14 = prs.slides.add_slide(blank_layout)
    add_background(s14)
    add_header(s14, "Stages S4/S5: ICMR-NIN IFCT & Monte Carlo Compliance")

    add_card(s14, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s14.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "ICMR-NIN IFCT & INDB Knowledge Base"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "• Official Indian Standard: Ingested the Indian Council of Medical Research (ICMR-NIN 2017) Indian Food Composition Tables (IFCT).\n• Comprehensive Curation: 115 regional dishes mapped to verified energy (kcal), protein (g), fat (g), carbohydrates (g), and iron (mg) per 100g.\n• Recipe Composition Modeling: Composite dishes (e.g. Sambar) modeled via cooked grain-pulse ratios (e.g., toor dal + tamarind + drumsticks).\n• Master JSON Knowledge Graph: data/indb_ifct_nutrition_master.json."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s14, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s14.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "4,000-Draw Comonotonic Monte Carlo"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD
    p2 = tf.add_paragraph()
    p2.text = "Why Point Estimates are Dangerous in Law:\n" \
              "Natural food density varies by ±10%, and agricultural nutrient values vary by ±4%. Claiming an exact '452 kcal' is statistically indefensible.\n\n" \
              "Comonotonic Copula Engine (engine/mc.py):\n" \
              "• Generates 4,000 correlated Monte Carlo draws.\n" \
              "• Emits 90% confidence intervals: [p05, p50, p95].\n" \
              "• Statutory Decision Rule:\n" \
              "  - PASS: P(Energy ≥ Mandate) ≥ 0.90\n" \
              "  - BORDERLINE: 0.50 ≤ P < 0.90\n" \
              "  - DEFICIENT (FAIL): P < 0.50"
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s14, """
Slide 14 details Stages S4 and S5: Nutritional Mapping and Monte Carlo Compliance.

We integrated the official ICMR-NIN 2017 Indian Food Composition Tables, curated by teammate Roshanth V.

Crucially, in statutory auditing, point estimates are legally indefensible. Cooked rice packing density fluctuates by 10%, and dal protein content varies with seasonal harvest. If an algorithm claims a meal has exactly 450.1 kcal, that claim cannot stand in court.

Instead, NutriSense runs a 4,000-draw comonotonic Monte Carlo simulation. We compute full 90% confidence intervals. The system issues a 'PASS' only if there is a 90% statistical probability that the meal meets the NFSA statutory threshold.
""")

    # =========================================================================
    # SLIDE 15: REAL-WORLD PHYSICAL WEIGHED CAPTURES
    # =========================================================================
    print("Slide 15: Real-World Weighed Dataset...")
    s15 = prs.slides.add_slide(blank_layout)
    add_background(s15)
    add_header(s15, "Real-World Laboratory-Weighed Dataset (Aruco_7ID)")

    add_card(s15, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s15.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Physical Laboratory Protocol"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_AMBER
    p2 = tf.add_paragraph()
    p2.text = "• Laboratory Digital Scale: Calibrated 0.1 g precision scale used to establish absolute ground-truth weight for every item.\n• 6 Distinct Meal Cohorts:\n  - Dish 1: Steamed Rice + Sambar (450.0 g total, Multi-Item)\n  - Dish 2: Steamed Rice + Rasam (338.0 g total)\n  - Dish 3: Steamed Rice + Chappati / Chutney (191.0 g total)\n  - Dish 4: Chicken Biryani in Deep Vessel (250.0 g total)\n  - Dish 5: Veg Dum Biryani Plate (150.0 g total)\n  - Dish 6: Chicken Dum Biryani Plate (351.0 g total)\n• 23 Handheld Smartphone Photos: Captured under real fluorescent lighting across varied camera angles."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s15, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s15.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Strict EVAL-ONLY Scientific Integrity"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "Zero Data-Leakage Protocol (Ledger 020, 028, 033):\n\n" \
              "• Zero Fine-Tuning: None of the 23 real ArUco images were EVER used to train or fine-tune any segmentation or classification backbone.\n" \
              "• Blind Inference: The pipeline processed raw JPEG images without access to filenames, metadata, or ground-truth masses.\n" \
              "• Multi-Angle Stress Test: Captures range from 0° (top-down) to 65° (oblique), testing perspective projection limits.\n" \
              "• Real Artifacts Present: Steaming hot food, specular reflections from stainless steel thalis, liquid meniscus curvature, and irregular grain compaction."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s15, """
Slide 15 introduces our physical evaluation dataset: Aruco_7ID_60mm_with_food.

To validate NutriSense against real reality, teammate Aryan Kumar prepared 6 authentic meal cohorts, weighing each component on a calibrated digital laboratory balance.

These include multi-item thalis, steamed rice with rasam katoris, chappatis, and chicken biryani in deep steel vessels, totaling 23 handheld smartphone photos.

We stress our commitment to scientific rigor: these 23 images were designated EVAL-ONLY. Not a single pixel was used to fine-tune our models. All results shown next are pure out-of-sample blind inferences.
""")

    # =========================================================================
    # SLIDE 16: REAL WEIGHED BENCHMARK RESULTS (DISHES 1–6)
    # =========================================================================
    print("Slide 16: Real Weighed Benchmark Results...")
    s16 = prs.slides.add_slide(blank_layout)
    add_background(s16)
    add_header(s16, "Real Weighed Benchmark Results (Dishes 1–6)")

    # Left: Table (width 6.2)
    table_shape = s16.shapes.add_table(8, 4, Inches(0.8), Inches(1.8), Inches(6.0), Inches(5.0))
    table = table_shape.table
    table.columns[0].width = Inches(1.4)
    table.columns[1].width = Inches(1.5)
    table.columns[2].width = Inches(1.5)
    table.columns[3].width = Inches(1.6)

    headers = ["Dish Cohort", "Ground Truth", "NutriSense Pred", "Accuracy (%)"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = CARD_HEADER_BG
        p = cell.text_frame.paragraphs[0]
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYAN
        p.alignment = PP_ALIGN.CENTER

    weighed_rows = [
        ("Dish 6 (Chicken Biryani)", "351.0 g", "358.8 g (+2.2%)", "97.8% (Best: 99.9%)"),
        ("Dish 5 (Veg Biryani)", "150.0 g", "151.1 g (+0.7%)", "99.3% (Best: 99.2%)"),
        ("Dish 2 (Rice + Rasam)", "338.0 g", "346.2 g (+2.4%)", "97.6% (Best: 98.1%)"),
        ("Dish 3 (Rice + Chappati)", "191.0 g", "165.5 g (-13.4%)", "86.6% (Best: 97.1%)"),
        ("Dish 1 (Rice + Sambar)", "450.0 g", "383.3 g (-14.8%)", "85.2% (Sambar: 98.8%)"),
        ("Dish 4 (Deep Vessel Biryani)", "250.0 g", "209.0 g (-16.4%)", "83.6% (Oblique tilt)"),
        ("Pooled Primary Overhead", "—", "MAE: 29.70 g", "90.58% Mean Acc"),
    ]

    for row_idx, row in enumerate(weighed_rows, start=1):
        for col_idx, text in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            cell.text = text
            cell.fill.solid()
            cell.fill.fore_color.rgb = CARD_BG if row_idx % 2 == 1 else RGBColor(22, 30, 46)
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(9.5)
            if col_idx == 3:
                p.font.bold = True
                p.font.color.rgb = ACCENT_EMERALD
            else:
                p.font.color.rgb = TEXT_BODY

    # Right: Chart
    s16.shapes.add_picture(weighed_bars_img, Inches(7.0), Inches(1.8), Inches(5.5), Inches(4.9))

    set_notes(s16, """
Slide 16 presents the crowning result of our project: physical scale verification against real food.

Look at the table:
On Dish 5 (Veg Biryani), the physical scale measured 150.0 grams. NutriSense predicted 151.1 grams—an error of just 1.1 grams, or 99.3% accuracy!
On Dish 6 (Chicken Biryani), the ground truth was 351.0 grams. NutriSense predicted 358.8 grams—a 97.8% accuracy, with the top-down capture reaching 99.9% accuracy!
On Dish 2 (Rice + Rasam), ground truth was 338.0 grams, NutriSense predicted 346.2 grams—97.6% accuracy.

Across all primary overhead meals, our pooled MAE is 29.70 grams, giving a mean real-world volumetric accuracy of 90.58%!
""")

    # =========================================================================
    # SLIDE 17: CARD-FREE MODE B BREAKTHROUGH
    # =========================================================================
    print("Slide 17: Card-Free Mode B Breakthrough...")
    s17 = prs.slides.add_slide(blank_layout)
    add_background(s17)
    add_header(s17, "Card-Free Mode B: 80.1% Signed Bias Reduction")

    # Left: Explanation Card
    add_card(s17, Inches(0.8), Inches(1.8), Inches(5.8), Inches(5.0))
    tb = s17.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.4), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Solving the Card-Free Volume Collapse"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_AMBER
    p2 = tf.add_paragraph()
    p2.text = "The Problem (Commit 53e99bb):\n" \
              "When no ArUco card was present, naive depth fitting sampled points on the plate floor, fitting a plane directly through the food. This caused catastrophic volume collapse: a signed bias of -223.52 g!\n\n" \
              "The Engineering Fix (Commit 060cd7b):\n" \
              "1. Base Tabletop Annulus Fit: Samples table surface 1.5–5.5 cm outside the food mask, anchoring the true ground plane.\n" \
              "2. Frustum Height Reconstruction: Uses camera geometry to infer vertical distance from optical center to table.\n" \
              "3. Scale-Modulated Bayesian Fusion: Scales volume using LODO-CV implicit scale head.\n\n" \
              "Verified Quantified Impact:\n" \
              "• Signed Bias slashed by 80.1% (-223.52 g → -44.40 g)!\n" \
              "• Out-of-Fold MAE reduced by 32.0% (225.40 g → 153.23 g)."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    # Right: Chart
    s17.shapes.add_picture(bias_reduction_img, Inches(7.0), Inches(1.8), Inches(5.5), Inches(4.9))

    set_notes(s17, """
Slide 17 showcases our most recent algorithmic breakthrough: Card-Free Mode B.

In our previous release (commit 53e99bb), running without an ArUco card suffered from severe volume collapse. Because there was no marker, the plane fitting routine anchored on the bottom of the plate, effectively slicing off half the food volume, causing a massive -223.5 gram negative bias.

In commit 060cd7b, Lead Architect Gokula Swamy redesigned the depth sampler with the Tabletop Annulus Fit and Frustum Height Fusion.

As the chart on the right demonstrates, this cut signed bias by 80.1%—from -223.5 grams down to -44.4 grams, cutting out-of-fold MAE by 32%!
""")

    # =========================================================================
    # SLIDE 18: WEB APPLICATION & INTERACTIVE UI
    # =========================================================================
    print("Slide 18: Web Application & UI...")
    s18 = prs.slides.add_slide(blank_layout)
    add_background(s18)
    add_header(s18, "Web Application Architecture & Interactive UI")

    add_card(s18, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s18.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Modern Frontend Stack (React 19)"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "• Architecture: React 19 + TypeScript 5.8 + Vite 6 + Tailwind CSS variables.\n• Real-Time Visual Progress: Animated 6-stage telemetry stepper showing scale detection, segmentation masks, depth unprojection, and Monte Carlo status.\n• Interactive Mask Overlay: Canvas-rendered multi-item polygons with hover inspection of individual component grams.\n• Live Nutrition Dials: Real-time SVG dials displaying Energy (kcal), Protein (g), Carbohydrates (g), and Fat (g) with 90% confidence bands.\n• Student Roster Tracking: Localized offline storage of student meal logs."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s18, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s18.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "UI Usability & Design System"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD
    p2 = tf.add_paragraph()
    p2.text = "Engineered by Frontend Lead Somanath S D:\n\n" \
              "• Streamlined Topbar Navigation: Clean 1-word tab navigation ('Home', 'Analyze', 'History', 'Insights', 'Students', 'Menu') with zero text clipping.\n" \
              "• 8 Custom Colorways: Instant theme switching (Dark Slate, OLED Teal, Rosé Dawn, Dracula, Nord, Minimal Light).\n" \
              "• Dual Mode Switcher: One-click toggle between School Canteen Mode (PM POSHAN statutory audit) and General Mode (individual WHO/FAO goals).\n" \
              "• Responsive Mobile Drawer: Optimized for low-cost Android tablets used by school headmasters and kitchen cooks in rural districts."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s18, """
Slide 18 presents our web application interface, built by Somanath S D.

The interface is built with React 19 and TypeScript, communicating with our FastAPI backend. It features an interactive pipeline stepper that visualizes intermediate results: showing the user the detected ArUco card, the multi-item segmentation masks, the 3D depth point cloud, and the final nutrient breakdown.

We also added responsive design with dark and light themes, and an adaptive topbar that guarantees clean navigation across tablet and desktop displays.
""")

    # =========================================================================
    # SLIDE 19: LIMITATIONS & OPEN-SOURCE v2.0 ROADMAP
    # =========================================================================
    print("Slide 19: Limitations & Roadmap...")
    s19 = prs.slides.add_slide(blank_layout)
    add_background(s19)
    add_header(s19, "Physical Limitations & Open-Source v2.0 Roadmap")

    add_card(s19, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s19.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Physical Optical Boundaries"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_AMBER
    p2 = tf.add_paragraph()
    p2.text = "Academic integrity demands acknowledging the fundamental physics of optical dietary assessment:\n\n" \
              "1. Submerged Solids in Opaque Liquids:\n" \
              "   Monocular cameras cannot peer beneath opaque curries to count submerged potato or paneer chunks. Portions are inferred from surface area and recipe density priors.\n\n" \
              "2. Natural Grain Packing Porosity:\n" \
              "   Cooked rice exhibits natural density variance (0.70 g/cm³ for fluffy rice to 0.95 g/cm³ for compacted rice), creating an unavoidable ~10% physical mass variance.\n\n" \
              "3. Extreme Perspective Obliquity (>65°):\n" \
              "   Steep side-views suffer geometric foreshortening."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    add_card(s19, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb = s19.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Open-Source v2.0 Roadmap"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    p2 = tf.add_paragraph()
    p2.text = "1. Massive Wild Canteen Dataset (1,000+ Plates):\n" \
              "   Expand beyond lab captures to multi-state school cafeterias across diverse lighting, tray styles, and regional menus.\n\n" \
              "2. On-Device Edge Quantization (ONNX / TensorRT / TFLite):\n" \
              "   Quantize MoGe-2, DINOv2-S, and SigLIP-2 to INT8/FP16 for 100% offline inference on $100 Android tablets without internet connectivity.\n\n" \
              "3. Multi-Frame Video & Smartphone ToF Sensor Fusion:\n" \
              "   Ingest 3-second 180° video pans and hardware LiDAR/Time-of-Flight depth channels to resolve bowl occlusions.\n\n" \
              "4. Public Hugging Face Benchmark Release:\n" \
              "   Release our 115-dish Indian Food dataset and INDB/IFCT knowledge graph to the AI research community."
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    set_notes(s19, """
Slide 19 addresses physical limitations and our future research roadmap.

We uphold complete scientific transparency: optical cameras have physical limits. No camera can see solid potatoes submerged under opaque sambar; and fluffy cooked rice naturally varies in porosity by about 10%.

To push beyond these boundaries, our Open-Source v2.0 roadmap includes:
First, gathering a 1,000-plate multi-state school dataset;
Second, quantizing our models to INT8 using ONNX Runtime for offline edge execution on cheap Android tablets in rural kitchens;
Third, fusing smartphone Time-of-Flight LiDAR sensors and short 3-second video clips to capture hidden bowl depths.
""")

    # =========================================================================
    # SLIDE 20: CONCLUSION & VIVA DEFENSE SUMMARY
    # =========================================================================
    print("Slide 20: Conclusion & Defense Summary...")
    s20 = prs.slides.add_slide(blank_layout)
    add_background(s20)
    add_header(s20, "Conclusion & Project Defense Summary")

    add_card(s20, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0))
    tb = s20.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(11.1), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Summary of Major Project Deliverables"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = ACCENT_EMERALD

    p2 = tf.add_paragraph()
    p2.text = "✔ End-to-End 3D Optical Vision Pipeline: Fully working 6-stage architecture taking a single raw photo to an ICMR-NIN compliant nutritional audit in <3.5 s (FP16).\n" \
              "✔ Exceptional Real-World Accuracy: 90.58% mean accuracy (29.70 g MAE) on primary real weighed handheld institutional meals; best view reaching 99.9%.\n" \
              "✔ Card-Free Breakthrough: Annulus tabletop plane fitting slashed Mode B signed bias by 80.1% (-223.5 g → -44.4 g) with 77.0% LODO-CV scale accuracy.\n" \
              "✔ 115 Regional Indian Dishes: Ingested Bharat & Rajistics corpora, indexed 1,206 visual prototypes, mapped to official ICMR-NIN IFCT tables.\n" \
              "✔ Production Software Engineering: React 19 web app, Docker containerization, 495+ automated tests, and 502/502 cryptographically locked verification files.\n" \
              "✔ Academic Research Paper: Rigorous two-column IEEE conference paper (paper/main.pdf) with complete mathematical formulations and ablation studies."
    p2.font.size = Pt(11.5)
    p2.font.color.rgb = TEXT_BODY
    p2.space_before = Pt(8)

    p3 = tf.add_paragraph()
    p3.text = "━" * 58
    p3.font.size = Pt(12)
    p3.font.color.rgb = CARD_BORDER
    p3.space_before = Pt(10)

    p4 = tf.add_paragraph()
    p4.text = "Thank you! We invite questions and feedback from the viva evaluation committee."
    p4.font.size = Pt(15)
    p4.font.bold = True
    p4.font.color.rgb = ACCENT_CYAN
    p4.space_before = Pt(8)

    p5 = tf.add_paragraph()
    p5.text = "Project Lead: S S Gokula Swamy | Team: Somanath S D, Roshanth V, Aryan Kumar | Guide: Prof. Varsha R\nDepartment of Machine Learning, B.M.S. College of Engineering, Bengaluru"
    p5.font.size = Pt(11)
    p5.font.color.rgb = TEXT_MUTED
    p5.space_before = Pt(4)

    set_notes(s20, """
In conclusion, NutriSense demonstrates that AI-powered 3D computer vision can be successfully translated from theoretical research into an impactful, practical tool for public health and school meal governance.

We have delivered a complete, production-grade system:
- 90.58% mean portion accuracy on real physical meals;
- An 80.1% bias reduction in Card-Free Mode B;
- Coverage of 115 regional Indian dishes;
- Full statutory compliance against PM POSHAN norms using Monte Carlo uncertainty modeling;
- A modern React 19 web interface and Docker containerization;
- And an IEEE conference paper detailing our methodology.

We would like to express our deepest gratitude to our project guide, Prof. Varsha R, and the Department of Machine Learning at BMS College of Engineering.

We now welcome questions, feedback, and demonstration requests from the evaluation committee. Thank you!
""")

    prs.save(output_path)
    print(f"✅ Successfully generated 20-slide presentation at: {output_path}")


if __name__ == "__main__":
    import sys
    out1 = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/NutriSense_Major_Project_Presentation.pptx"
    out2 = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/docs/NutriSense_Major_Project_Presentation.pptx"

    build_presentation(out1)
    shutil.copyfile(out1, out2)
    print(f"✅ Copied presentation to docs at: {out2}")
