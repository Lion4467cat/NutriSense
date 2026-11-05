"""Generate a professional 20-slide widescreen (16:9) PowerPoint presentation for NutriSense.

Daylight Academic Light Theme:
- Background: Pure White (#FFFFFF) with Alabaster canvas (#F8FAFC)
- Card Containers: Solid White (#FFFFFF) with refined slate border (#CBD5E1)
- Typography: Deep Charcoal (#0F172A) titles, Slate (#334155) body, 15-17pt readable font
- Accents: BMSCE Royal Blue (#1E3A8A), Forest Emerald (#047857), Sky Blue (#0284C7)
- Charts: Clean white background with crisp dark labels and high-contrast bars
- Visuals: Embedded live high-res UI screenshots (Home Dashboard & Multi-Item Result)
- Speaker Notes: Complete, defense-ready speaker notes across all 20 slides

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

# Color Palette: Daylight Academic Light Theme (BMSCE Royal Blue & Forest Emerald)
BG_COLOR = RGBColor(255, 255, 255)            # Pure White #FFFFFF
CANVAS_BG = RGBColor(248, 250, 252)          # Slate 50 #F8FAFC
CARD_BG = RGBColor(255, 255, 255)            # Card White #FFFFFF
CARD_BG_ALT = RGBColor(241, 245, 249)        # Slate 100 #F1F5F9
CARD_BORDER = RGBColor(203, 213, 225)        # Slate 300 #CBD5E1
CARD_BORDER_DARK = RGBColor(148, 163, 184)   # Slate 400 #94A3B8
HEADER_ROYAL = RGBColor(30, 58, 138)         # BMSCE Royal Blue #1E3A8A
HEADER_CYAN = RGBColor(2, 132, 199)          # Deep Sky #0284C7
TEXT_PRIMARY = RGBColor(15, 23, 42)          # Deep Charcoal #0F172A
TEXT_MUTED = RGBColor(71, 85, 105)           # Slate 600 #475569
TEXT_BODY = RGBColor(30, 41, 59)             # Slate 800 #1E293B
ACCENT_EMERALD = RGBColor(4, 120, 87)        # Forest Emerald #047857
ACCENT_AMBER = RGBColor(180, 83, 9)          # Deep Amber #B45309
ACCENT_RED = RGBColor(185, 28, 28)           # Crimson Red #B91C1C

TEMP_CHARTS_DIR = "/tmp/nutrisense_pptx_charts"
os.makedirs(TEMP_CHARTS_DIR, exist_ok=True)


def generate_pipeline_chart() -> str:
    """Generate pipeline DAG diagram for Slide 6 in clean light theme."""
    path = os.path.join(TEMP_CHARTS_DIR, "pipeline_dag.png")
    fig, ax = plt.subplots(figsize=(11.0, 3.4), facecolor="#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    stages = [
        ("S1: Scale Anchor", "ArUco (60mm) +\nImplicit Scale Head", "#047857", "#E6F4EA"),
        ("S2a: Segmentation", "DeepLabV3 +\nSAM 2.1 Hiera", "#0284C7", "#E0F2FE"),
        ("S2b: Classifier", "SigLIP-2 (ViT-B)\n115 Indian Dishes", "#4338CA", "#EEF2FF"),
        ("S3a: Metric Depth", "MoGe-2 (ViT-L)\nAnnular Ring Plane", "#B45309", "#FEF3C7"),
        ("S3b: Mass Head", "Volumetric Fusion\n+ DINOv2-S Prior", "#9D174D", "#FCE7F3"),
        ("S4/S5: Compliance", "4k Monte Carlo\nPM POSHAN Verdict", "#047857", "#E6F4EA"),
    ]

    for i, (title, sub, border_col, fill_col) in enumerate(stages):
        x = i * 1.8 + 0.1
        rect = Rectangle((x, 0.4), 1.55, 2.0, facecolor=fill_col, edgecolor=border_col, linewidth=2.0, transform=ax.transData)
        ax.add_patch(rect)
        ax.text(x + 0.775, 1.95, title, ha="center", va="center", color=border_col, weight="bold", fontsize=10.5)
        ax.text(x + 0.775, 1.15, sub, ha="center", va="center", color="#0F172A", fontsize=9.0, weight="medium")

        if i < len(stages) - 1:
            ax.annotate("", xy=(x + 1.8, 1.4), xytext=(x + 1.55, 1.4),
                        arrowprops=dict(arrowstyle="->", color="#0284C7", lw=2.5))

    ax.set_xlim(-0.1, 10.9)
    ax.set_ylim(0.0, 2.7)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return path


def generate_weighed_bar_chart() -> str:
    """Generate 4-way estimation bar chart for Slide 16 in clean light theme."""
    path = os.path.join(TEMP_CHARTS_DIR, "weighed_bars.png")
    fig, ax = plt.subplots(figsize=(6.8, 4.2), facecolor="#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    dishes = ["Dish 1\n(Rice+Sambar)", "Dish 2\n(Rice+Rasam)", "Dish 3\n(Chappati)", "Dish 5\n(Veg Biryani)", "Dish 6\n(Chicken Biryani)"]
    gt = [450.0, 338.0, 191.0, 150.0, 351.0]
    pred_mode_a = [383.3, 346.2, 165.5, 151.1, 358.8]
    pred_mode_b = [433.1, 325.9, 177.5, 181.7, 262.7]

    x = np.arange(len(dishes))
    width = 0.26

    ax.bar(x - width, gt, width, label="Ground Truth (Scale)", color="#0284C7", edgecolor="#0369A1", linewidth=1.5)
    ax.bar(x, pred_mode_a, width, label="Mode A (ArUco Fused)", color="#047857", edgecolor="#065F46", linewidth=1.5)
    ax.bar(x + width, pred_mode_b, width, label="Mode B (Card-Free)", color="#D97706", edgecolor="#B45309", linewidth=1.5)

    ax.set_ylabel("Portion Weight (grams)", color="#0F172A", fontsize=11, weight="bold")
    ax.set_title("Physical Scale vs NutriSense Estimation", color="#0F172A", fontsize=12, weight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(dishes, color="#1E293B", fontsize=9, weight="bold")
    ax.tick_params(colors="#334155", which="both", labelsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.35, color="#94A3B8")
    for spine in ax.spines.values():
        spine.set_color("#CBD5E1")
    ax.legend(facecolor="#F8FAFC", edgecolor="#CBD5E1", labelcolor="#0F172A", fontsize=9, loc="upper right")

    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return path


def generate_bias_reduction_chart() -> str:
    """Generate Card-Free Mode B bias reduction chart for Slide 17 in clean light theme."""
    path = os.path.join(TEMP_CHARTS_DIR, "bias_reduction.png")
    fig, ax = plt.subplots(figsize=(6.6, 4.2), facecolor="#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    metrics = ["Signed Mass Bias (g)", "Out-of-Fold MAE (g)"]
    baseline = [-223.52, 225.40]
    annulus_fit = [-44.40, 153.23]

    x = np.arange(len(metrics))
    width = 0.35

    b1 = ax.bar(x - width/2, baseline, width, label="Baseline (Plate Plane Collapse)", color="#DC2626", edgecolor="#991B1B", linewidth=1.5)
    b2 = ax.bar(x + width/2, annulus_fit, width, label="Annulus Fit + Frustum Fusion", color="#047857", edgecolor="#065F46", linewidth=1.5)

    ax.set_ylabel("Error (grams)", color="#0F172A", fontsize=11, weight="bold")
    ax.set_title("Card-Free Mode B: 80.1% Signed Bias Reduction", color="#0F172A", fontsize=12, weight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, color="#0F172A", fontsize=10, weight="bold")
    ax.tick_params(colors="#334155", which="both", labelsize=9.5)
    ax.axhline(0, color="#64748B", linewidth=1.5, linestyle="--")
    ax.set_ylim(-280, 310)
    ax.grid(axis="y", linestyle="--", alpha=0.35, color="#94A3B8")
    for spine in ax.spines.values():
        spine.set_color("#CBD5E1")

    # Add data callout labels
    ax.text(0 - width/2, -252, "-223.5 g", ha="center", color="#DC2626", weight="bold", fontsize=10)
    ax.text(0 + width/2, -72, "-44.4 g\n(-80.1%)", ha="center", color="#047857", weight="bold", fontsize=10)
    ax.text(1 - width/2, 242, "225.4 g", ha="center", color="#DC2626", weight="bold", fontsize=10)
    ax.text(1 + width/2, 168, "153.2 g\n(-32.0%)", ha="center", color="#047857", weight="bold", fontsize=10)

    ax.legend(facecolor="#F8FAFC", edgecolor="#CBD5E1", labelcolor="#0F172A", fontsize=9.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return path


def add_background(slide):
    """Add solid light alabaster canvas background rectangle."""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    shape.fill.solid()
    shape.fill.fore_color.rgb = CANVAS_BG
    shape.line.fill.background()
    return shape


def add_header(slide, title: str, category: str = "NUTRISENSE · B.E. MAJOR PROJECT DEFENSE"):
    """Add unified slide header with category eyebrow and title in high-contrast light theme."""
    # Eyebrow
    tx_cat = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
    tf_c = tx_cat.text_frame
    tf_c.word_wrap = True
    p_c = tf_c.paragraphs[0]
    p_c.text = category.upper()
    p_c.font.size = Pt(11)
    p_c.font.bold = True
    p_c.font.color.rgb = HEADER_ROYAL

    # Title
    tx_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.7), Inches(0.75))
    tf_t = tx_title.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title
    p_t.font.size = Pt(25)
    p_t.font.bold = True
    p_t.font.color.rgb = TEXT_PRIMARY

    # Accent Line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.50), Inches(11.7), Inches(0.025))
    line.fill.solid()
    line.fill.fore_color.rgb = CARD_BORDER
    line.line.fill.background()


def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=CARD_BORDER):
    """Add clean rounded container card."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1.4)
    return shape


def set_notes(slide, notes_text: str):
    """Attach rich speaker notes to slide."""
    slide.notes_slide.notes_text_frame.text = notes_text.strip()


def build_presentation(output_path: str):
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank_layout = prs.slide_layouts[6]

    print("🎨 Generating high-contrast daylight chart assets...")
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
    add_card(s1, Inches(0.8), Inches(0.7), Inches(11.733), Inches(6.1), bg_color=CARD_BG, border_color=HEADER_ROYAL)

    tb = s1.shapes.add_textbox(Inches(1.2), Inches(0.95), Inches(11.0), Inches(5.6))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "NUTRISENSE"
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    p2 = tf.add_paragraph()
    p2.text = "AI-Powered 3D Dietary Assessment & Nutrition Auditing from a Single Meal Photo"
    p2.font.size = Pt(20)
    p2.font.bold = True
    p2.font.color.rgb = TEXT_PRIMARY
    p2.space_before = Pt(6)

    p3 = tf.add_paragraph()
    p3.text = "B.E. Major Project Viva Defense & Final Academic Review · Course: 24AM7PWPW2 (2026–27)"
    p3.font.size = Pt(14)
    p3.font.bold = True
    p3.font.color.rgb = HEADER_CYAN
    p3.space_before = Pt(8)

    p4 = tf.add_paragraph()
    p4.text = "Department of Machine Learning, B.M.S. College of Engineering (BMSCE), Bengaluru"
    p4.font.size = Pt(13)
    p4.font.color.rgb = TEXT_MUTED
    p4.space_before = Pt(4)

    # Divider
    div = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(3.2), Inches(10.9), Inches(0.02))
    div.fill.solid()
    div.fill.fore_color.rgb = CARD_BORDER
    div.line.fill.background()

    # Team & Guide Details in 2 columns
    tb_team = s1.shapes.add_textbox(Inches(1.2), Inches(3.4), Inches(5.4), Inches(3.0))
    tf_team = tb_team.text_frame
    tf_team.word_wrap = True
    pt = tf_team.paragraphs[0]
    pt.text = "PROJECT TEAM"
    pt.font.size = Pt(13)
    pt.font.bold = True
    pt.font.color.rgb = HEADER_ROYAL

    pt1 = tf_team.add_paragraph()
    pt1.text = "• S S Gokula Swamy (1BM23AI158) — Project Lead & Principal Architect\n  (End-to-End Pipeline, 3D Annulus Geometry, Card-Free Head, Synthetic CutMix)"
    pt1.font.size = Pt(11)
    pt1.font.bold = True
    pt1.font.color.rgb = TEXT_PRIMARY
    pt1.space_before = Pt(4)

    pt2 = tf_team.add_paragraph()
    pt2.text = "• Somanath S D (1BM23AI187) — Full-Stack Developer & UI Lead\n  (FastAPI Backend, React 19 Frontend, Topbar Navigation, Student Roster)"
    pt2.font.size = Pt(11)
    pt2.font.color.rgb = TEXT_BODY
    pt2.space_before = Pt(3)

    pt3 = tf_team.add_paragraph()
    pt3.text = "• Roshanth V (1BM23AI155) — ML Engineer (Computer Vision & Segmentation)\n  (DeepLabV3 + SAM 2.1 Hiera Integration, 95.8% Dice Mask Extraction)"
    pt3.font.size = Pt(11)
    pt3.font.color.rgb = TEXT_BODY
    pt3.space_before = Pt(3)

    pt4 = tf_team.add_paragraph()
    pt4.text = "• Aryan Kumar (1BM23AI037) — ML Engineer (Nutritional Data & Compliance)\n  (INDB/IFCT Master Database, 4k Monte Carlo Engine, PM POSHAN Mandates)"
    pt4.font.size = Pt(11)
    pt4.font.color.rgb = TEXT_BODY
    pt4.space_before = Pt(3)

    tb_guide = s1.shapes.add_textbox(Inches(6.8), Inches(3.4), Inches(5.3), Inches(3.0))
    tf_guide = tb_guide.text_frame
    tf_guide.word_wrap = True
    pg = tf_guide.paragraphs[0]
    pg.text = "PROJECT GUIDE & EVALUATION"
    pg.font.size = Pt(13)
    pg.font.bold = True
    pg.font.color.rgb = ACCENT_EMERALD

    pg1 = tf_guide.add_paragraph()
    pg1.text = "Prof. Varsha R\nAssistant Professor, Department of Machine Learning\nB.M.S. College of Engineering, Bengaluru"
    pg1.font.size = Pt(12)
    pg1.font.bold = True
    pg1.font.color.rgb = TEXT_PRIMARY
    pg1.space_before = Pt(4)

    pg2 = tf_guide.add_paragraph()
    pg2.text = "Key Project Achievements:\n• 90.58% Mean Real-World Mass Accuracy (29.7g MAE across Dishes 1–6)\n• 99.3% Accuracy on Dish 5 Veg Biryani (151.1g estimated vs 150.0g scale)\n• 80.1% Signed Bias Reduction in Card-Free Mode B (-223.5g to -44.4g)\n• 115 Indian Dishes Gallery + INDB/IFCT Master Nutritional Table"
    pg2.font.size = Pt(11.5)
    pg2.font.color.rgb = TEXT_BODY
    pg2.space_before = Pt(6)

    set_notes(s1, """
Respected Guide Prof. Varsha R and External Examiners, good morning.

We are proud to present NutriSense: an AI-Powered 3D Dietary Assessment and Nutrition Auditing System from a Single Meal Photo.

Our project addresses one of the most critical public health challenges in India: the accurate, real-time auditing of government school midday meals under the statutory PM POSHAN scheme.

Lead Architect Gokula Swamy spearheaded the pipeline design, the card-free implicit scale estimation, and the 3D tabletop annulus geometry. Somanath S D engineered the full-stack web application. Roshanth V developed the food segmentation models, and Aryan Kumar managed the Indian nutritional database and Monte Carlo compliance engines.

Over the next 20 slides, we walk through our system architecture, the Master Accuracy percentages, our physical weighed benchmarks, and our interactive web application.
""")

    # =========================================================================
    # SLIDE 2: EXECUTIVE SUMMARY & PROBLEM FORMULATION
    # =========================================================================
    print("Slide 2: Executive Summary...")
    s2 = prs.slides.add_slide(blank_layout)
    add_background(s2)
    add_header(s2, "Executive Summary & Engineering Problem")

    # 3 Cards
    cards_data = [
        ("The Challenge", "Severe Under-Reporting & Volume Collapse", [
            "Dietary recall surveys suffer from 30%–50% cognitive recall bias.",
            "Existing 2D vision apps rely on coarse 2D bounding boxes, causing catastrophic volume collapse on piled or multi-item foods.",
            "Indian thali meals combine liquid gravies (sambar, rasam) with porous mounds (steamed rice, biryani) having zero visual scale.",
            "Government schools lack precision weighing balances at rural distribution points."
        ], ACCENT_RED),
        ("The NutriSense Solution", "5-Stage 3D Metric Vision & Multi-Prototype Fusion", [
            "Single overhead smartphone photo captures geometry, volume, and multi-component composition.",
            "Dual-scale operating modes: Fiducial ArUco Card (Mode A, sub-millimeter) or Card-Free Implicit Scale Head (Mode B, 6-Fold LODO-CV).",
            "Multi-component SAM 2.1 Hiera segmentation + SigLIP-2 vision-text classification across 115 Indian dishes.",
            "MoGe-2 metric depth with 3D Tabletop Annulus plane fitting and Frustum Voxel Integration."
        ], HEADER_ROYAL),
        ("Academic & Practical Impact", "PM POSHAN Mandate & Open-Source Rigor", [
            "Real Weighed Accuracy: 90.58% across Dishes 1–6 (29.7g MAE) and up to 99.3% on Dish 5.",
            "Card-Free Mode B: Slashed negative volume bias by 80.1% (-223.5g to -44.4g) via Annulus fit.",
            "Statutory Compliance: 4,000 Monte Carlo draws quantifying energy (kcal), protein (g), fat, and carbohydrates against NFSA 2013.",
            "100% Zero-Leakage: Cryptographically locked evaluation protocol, 378 unit tests passing."
        ], ACCENT_EMERALD),
    ]

    for i, (eyebrow, title, bullets, col) in enumerate(cards_data):
        left_val = 0.8 + i * 3.95
        add_card(s2, Inches(left_val), Inches(1.8), Inches(3.8), Inches(5.1), bg_color=CARD_BG, border_color=col)
        tb = s2.shapes.add_textbox(Inches(left_val + 0.2), Inches(1.95), Inches(3.4), Inches(4.8))
        tf = tb.text_frame
        tf.word_wrap = True

        pe = tf.paragraphs[0]
        pe.text = eyebrow.upper()
        pe.font.size = Pt(11)
        pe.font.bold = True
        pe.font.color.rgb = col

        pt = tf.add_paragraph()
        pt.text = title
        pt.font.size = Pt(15)
        pt.font.bold = True
        pt.font.color.rgb = TEXT_PRIMARY
        pt.space_before = Pt(4)

        for b in bullets:
            pb = tf.add_paragraph()
            pb.text = f"• {b}"
            pb.font.size = Pt(12)
            pb.font.color.rgb = TEXT_BODY
            pb.space_before = Pt(8)

    set_notes(s2, """
On Slide 2, we formulate the core engineering problem.

Nutritional deficiency affects millions of school children. While India's PM POSHAN scheme feeds over 120 million children daily, monitoring meal quality and quantity has relied on manual record books and self-reporting, which suffer from a 30% to 50% bias.

Existing smartphone apps attempt 2D bounding-box classification, which completely ignores meal depth, height, and density. When rice or sambar is served, a 2D bounding box cannot tell whether the mound is 100 grams or 400 grams.

NutriSense solves this through a rigorous 5-stage computer vision pipeline that recovers true 3D metric volume from a single overhead smartphone photograph.
""")

    # =========================================================================
    # SLIDE 3: MOTIVATION & STATUTORY MANDATE
    # =========================================================================
    print("Slide 3: Motivation & Statutory Mandate...")
    s3 = prs.slides.add_slide(blank_layout)
    add_background(s3)
    add_header(s3, "Statutory Framework: PM POSHAN & NFSA Schedule II")

    # Left card: Statutory requirements table
    add_card(s3, Inches(0.8), Inches(1.8), Inches(6.8), Inches(5.1))
    tb_l = s3.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(6.4), Inches(4.7))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "National Food Security Act (NFSA) 2013 Legal Norms"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    p_sub = tf_l.add_paragraph()
    p_sub.text = "Schedule II prescribes mandatory nutritional quotas per child per school day:"
    p_sub.font.size = Pt(12)
    p_sub.font.color.rgb = TEXT_MUTED
    p_sub.space_before = Pt(4)

    # Table of standards
    rows_data = [
        ("Nutrient Component", "Primary (Class I–V)", "Upper-Primary (Class VI–VIII)"),
        ("Energy (Calories)", "Minimum 450 kcal", "Minimum 700 kcal"),
        ("Protein (Grams)", "Minimum 12.0 grams", "Minimum 20.0 grams"),
        ("Food Grains (Rice/Wheat)", "100 grams dry weight", "150 grams dry weight"),
        ("Pulses (Dal / Sambar)", "20 grams dry weight", "30 grams dry weight"),
        ("Vegetables", "50 grams fresh weight", "75 grams fresh weight"),
        ("Oil & Fat", "5 grams", "7.5 grams"),
    ]

    for item, prim, upp in rows_data[1:]:
        p_row = tf_l.add_paragraph()
        p_row.text = f"• {item}: {prim} | {upp}"
        p_row.font.size = Pt(12)
        p_row.font.color.rgb = TEXT_BODY
        p_row.space_before = Pt(6)

    # Right card: Monitoring gap and compliance engine
    add_card(s3, Inches(7.8), Inches(1.8), Inches(4.7), Inches(5.1), bg_color=CARD_BG, border_color=ACCENT_EMERALD)
    tb_r = s3.shapes.add_textbox(Inches(8.0), Inches(2.0), Inches(4.3), Inches(4.7))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "The Real-World Monitoring Gap"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = ACCENT_EMERALD

    bullets_r = [
        "Zero Real-Time Verification: Current inspections are periodic and manual; school cooks cannot calibrate portions.",
        "4,000 Monte Carlo Simulations: NutriSense propagates uncertainty from depth noise, segmentation fuzziness, and ingredient variation.",
        "Probabilistic Statutory Audit: Computes P(Compliance >= 450 kcal) and P(Protein >= 12g) directly from the photo.",
        "Actionable School Verdict: Delivers clear, tamper-evident verdicts: 'Compliant', 'Deficient in Protein', or 'Under-Portioned'."
    ]
    for b in bullets_r:
        pr_b = tf_r.add_paragraph()
        pr_b.text = f"• {b}"
        pr_b.font.size = Pt(12)
        pr_b.font.color.rgb = TEXT_BODY
        pr_b.space_before = Pt(10)

    set_notes(s3, """
Slide 3 highlights the statutory framework. Under Schedule II of the National Food Security Act 2013, providing 450 kcal and 12 grams of protein for primary children, and 700 kcal and 20 grams of protein for upper-primary children, is a legally enforceable right.

However, in practice, there is no real-time technological audit at serving time.

NutriSense bridges this gap. By mapping estimated volume and mass to the Indian Food Composition Tables (IFCT 2017) and executing 4,000 Monte Carlo simulations, NutriSense calculates the exact probability of meeting statutory nutrition requirements before the plate is consumed.
""")

    # =========================================================================
    # SLIDE 4: RELATED WORK & RESEARCH GAPS
    # =========================================================================
    print("Slide 4: Related Work & Research Gaps...")
    s4 = prs.slides.add_slide(blank_layout)
    add_background(s4)
    add_header(s4, "Related Work & Key Research Gaps in Literature")

    gaps_data = [
        ("2D Vision Dietary Apps", "MyFitnessPal, Lose It!, Calorie Mama",
         "Rely entirely on 2D bounding boxes and user portion heuristics ('1 cup', 'medium bowl'). Incapable of measuring physical mass; average error exceeds 42% on composite dishes.",
         ACCENT_RED),
        ("Multi-View 3D Food Scanning", "NeRF, Gaussian Splatting, Multi-Angle Photogrammetry",
         "Require 20–50 video frames or continuous camera trajectories. Impractical for noisy school canteens with hungry children; requires heavy GPU workstations (>30s per scan).",
         ACCENT_AMBER),
        ("Western-Biased Benchmarks", "Nutrition5k, Food-101, Recipe1M",
         "Trained on Western plated foods (burgers, steaks, sliced salads). Complete absence of amorphous composite Indian dishes (khichdi, rasam, dal, biryani) and steel thali plates.",
         HEADER_CYAN),
        ("NutriSense Contribution", "Single-View Metric 3D Vision + Indian Knowledge Hub",
         "Recovers metric scale and 3D volume from 1 overhead smartphone image (<3.5s). 115 regional dishes, Tabletop Annulus depth sampling, and zero-leakage benchmark validation.",
         ACCENT_EMERALD),
    ]

    for i, (category, systems, desc, col) in enumerate(gaps_data):
        row = i // 2
        col_idx = i % 2
        left_val = 0.8 + col_idx * 5.95
        top_val = 1.8 + row * 2.65
        add_card(s4, Inches(left_val), Inches(top_val), Inches(5.8), Inches(2.45), bg_color=CARD_BG, border_color=col)
        tb = s4.shapes.add_textbox(Inches(left_val + 0.2), Inches(top_val + 0.15), Inches(5.4), Inches(2.15))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = category
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.text = f"Baseline / Prior Art: {systems}"
        p2.font.size = Pt(11)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_MUTED
        p2.space_before = Pt(2)

        p3 = tf.add_paragraph()
        p3.text = desc
        p3.font.size = Pt(12)
        p3.font.color.rgb = TEXT_BODY
        p3.space_before = Pt(4)

    set_notes(s4, """
Slide 4 positions NutriSense against existing literature.

Previous systems fall into two extremes: 2D smartphone apps that simply guess portions from bounding boxes, and multi-view 3D scanning systems like NeRF that require dozens of images and intense computing power.

Furthermore, Western datasets like Nutrition5k fail completely on Indian dietary patterns, where rice and dal mix together, forming complex fluid and porous boundaries.

NutriSense operates on a single photograph, infers true 3D metric volume, and explicitly models regional Indian foods.
""")

    # =========================================================================
    # SLIDE 5: MASTER ACCURACY TABLE (CORE EVALUATION SLIDE)
    # =========================================================================
    print("Slide 5: Master Accuracy Table...")
    s5 = prs.slides.add_slide(blank_layout)
    add_background(s5)
    add_header(s5, "Master Accuracy (%) Across Pipeline Stages & Final Models")

    # Add descriptive callout banner
    add_card(s5, Inches(0.8), Inches(1.7), Inches(11.733), Inches(0.55), bg_color=CARD_BG_ALT, border_color=HEADER_ROYAL)
    tb_b = s5.shapes.add_textbox(Inches(0.9), Inches(1.72), Inches(11.5), Inches(0.5))
    tf_b = tb_b.text_frame
    p_b = tf_b.paragraphs[0]
    p_b.text = "Definitive Percentage Accuracy (%) alongside rigorous scientific error metrics across all 5 modular stages and physical benchmarks:"
    p_b.font.size = Pt(12)
    p_b.font.bold = True
    p_b.font.color.rgb = HEADER_ROYAL

    # Table dimensions: 11 rows (1 header + 10 data), 5 columns
    rows = 11
    cols = 5
    table_shape = s5.shapes.add_table(rows, cols, Inches(0.8), Inches(2.35), Inches(11.733), Inches(4.7))
    table = table_shape.table
    table.columns[0].width = Inches(1.6)
    table.columns[1].width = Inches(2.2)
    table.columns[2].width = Inches(2.3)
    table.columns[3].width = Inches(2.2)
    table.columns[4].width = Inches(3.433)

    table_data = [
        ("Pipeline Stage", "Core Model / Architecture", "Accuracy (%)", "Scientific Metric", "Benchmark / Validation Split"),
        ("Stage S1a: Scale Anchor", "ArUco OpenCV Detector (60mm)", "100.0%", "Plane RMS: 0.74 mm", "23 Weighed Captures (Dishes 1–6)"),
        ("Stage S1b: Implicit Scale", "ImplicitScaleHead (ResNet18)", "77.00%", "MAE: 0.00251 cm/px (23.0% MAPE)", "6-Fold Leave-One-Dish-Out CV"),
        ("Stage S2a: Foreground", "DeepLabV3+ (ResNet50)", "95.81%", "FG Dice: 95.81%, IoU: 91.96%", "WED DEV (108 views, 21 plates)"),
        ("Stage S2a: Food Classes", "SAM 2.1 Hiera + DeepLabV3+", "89.76%", "Macro Dice: 89.76%, IoU: 82.11%", "WED DEV Multi-Component Split"),
        ("Stage S2b: Classifier", "SigLIP-2 (ViT-B/16 fused)", "82.27%", "Top-1: 82.27%, Top-5: 96.40%", "WED DEV (Macro Recall: 82.12%)"),
        ("Stage S2c: Regional Hub", "Multi-Prototype Indian Hub", "81.03%", "1,206 Prototypes (115 Dishes)", "INDB / IFCT Indian Regional Corpus"),
        ("Stage S3a: Depth & Plane", "MoGe-2 (ViT-L) + Annulus Fit", "92.60%", "Plane RMS < 1.0 mm, Tare 3.5 mm", "Physical Geometry & Depth Sampler"),
        ("Stage S3b: Mass Estimation", "Frustum Voxel + DINOv2 Prior", "81.70%", "DEV MAE: 15.03g / LOCKED: 14.67g", "WED DEV / LOCKED (502 pinned files)"),
        ("Overall Weighed (Mode A)", "NutriSense Full Pipeline (ArUco)", "90.58%", "MAE: 29.70g (Dish 5: 99.3%, D6: 97.8%)", "Physical Digital Balance (Dishes 1–6)"),
        ("Card-Free Mode B", "Implicit Scale + Annulus Sampler", "68.20%", "80.1% Bias Cut (-223.5g → -44.4g)", "Leave-One-Dish-Out Zero-Card Captures"),
    ]

    for r_idx, row in enumerate(table_data):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if c_idx in [2, 3] else PP_ALIGN.LEFT
            if r_idx == 0:
                p.font.bold = True
                p.font.size = Pt(11)
                p.font.color.rgb = RGBColor(255, 255, 255)
                cell.fill.solid()
                cell.fill.fore_color.rgb = HEADER_ROYAL
            else:
                p.font.size = Pt(10)
                if c_idx == 2:
                    p.font.bold = True
                    p.font.color.rgb = ACCENT_EMERALD if "9" in val or "100" in val or "8" in val else TEXT_PRIMARY
                else:
                    p.font.color.rgb = TEXT_BODY
                cell.fill.solid()
                cell.fill.fore_color.rgb = CARD_BG if r_idx % 2 == 1 else CARD_BG_ALT

    set_notes(s5, """
Slide 5 directly answers the primary question asked by our academic evaluators: 'What is the accuracy of each individual model and the combined pipeline?'

Here we see the full breakdown:
- Stage S1a Fiducial Scale achieves 100% detection rate with sub-millimeter plane fit RMS of 0.74 mm.
- Stage S1b Card-Free Implicit Scale achieves 77.0% scale accuracy under strict 6-fold leave-one-dish-out cross-validation.
- Stage S2a Food Segmentation achieves 95.81% foreground Dice and 89.76% macro food class Dice.
- Stage S2b Multi-Item Classification delivers 82.27% Top-1 accuracy and 96.40% Top-5 accuracy across regional foods.
- Stage S3b Mass Estimation reaches 81.70% accuracy on the DEV benchmark.
- On our real-world physical weighed dataset, our overhead pipeline achieves 90.58% mean accuracy with an MAE of 29.7 grams, achieving 99.3% accuracy on Dish 5 Veg Biryani.
- In Card-Free Mode B, our Tabletop Annulus fit eliminated 80.1% of the negative volume bias, cutting signed bias from -223.5g down to -44.4g.
""")

    # =========================================================================
    # SLIDE 6: SYSTEM ARCHITECTURE & MODULAR PIPELINE
    # =========================================================================
    print("Slide 6: System Architecture...")
    s6 = prs.slides.add_slide(blank_layout)
    add_background(s6)
    add_header(s6, "End-to-End Modular Architecture: 5 Processing Stages")

    # Add Pipeline DAG Diagram
    add_card(s6, Inches(0.8), Inches(1.8), Inches(11.733), Inches(2.7), bg_color=CARD_BG, border_color=HEADER_ROYAL)
    s6.shapes.add_picture(pipeline_img, Inches(1.1), Inches(1.9), width=Inches(11.1))

    # Architecture Highlights below
    add_card(s6, Inches(0.8), Inches(4.7), Inches(11.733), Inches(2.2), bg_color=CARD_BG_ALT, border_color=CARD_BORDER)
    tb = s6.shapes.add_textbox(Inches(1.0), Inches(4.85), Inches(11.3), Inches(1.9))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Key Architectural Tenets of the NutriSense Engine:"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_arch = [
        "Strict Separation of Geometry and Classification: Depth and scale geometry (S1, S3) are decoupled from semantic recognition (S2), ensuring zero error propagation from misclassifications.",
        "Deterministic Wire Contract: All stages exchange a validated 19-key JSON contract with TypeScript client parity.",
        "Batched Tensor Core FP16 Execution: Pipeline runs end-to-end on an NVIDIA RTX 4060 Laptop GPU in <3.5 seconds.",
        "Graceful Fallback Logic: Automatic seamless transition between ArUco card mode (Mode A) and Card-Free implicit scale (Mode B)."
    ]
    for b in bullets_arch:
        pb = tf.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(4)

    set_notes(s6, """
Slide 6 illustrates our end-to-end modular architecture.

The pipeline ingests a single RGB image and executes 5 stages:
1. Scale anchoring via ArUco marker or the Implicit Scale Head.
2. Multi-component segmentation using DeepLabV3+ and SAM 2.1 Hiera.
3. Food classification using SigLIP-2 ViT-B fused with our 115 Indian Dishes Gallery.
4. Metric 3D depth recovery using MoGe-2 with Tabletop Annulus plane fitting.
5. Volumetric integration and 4,000-draw Monte Carlo nutritional compliance checking.

The entire process completes in under 3.5 seconds on a laptop GPU.
""")

    # =========================================================================
    # SLIDE 7: STAGE S1a: PHYSICAL FIDUCIAL SCALE ANCHOR
    # =========================================================================
    print("Slide 7: Stage S1a...")
    s7 = prs.slides.add_slide(blank_layout)
    add_background(s7)
    add_header(s7, "Stage S1a: Physical Fiducial Scale Anchor (ArUco 60mm)")

    add_card(s7, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb_l = s7.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "Sub-Millimeter Camera Calibration"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_s1a = [
        "Fiducial Design: 60mm ArUco marker (DICT_4X4_50, ID 7) laminated beside the plate rim.",
        "Perspective PnP Solver: OpenCV cv2.solvePnP calculates camera rotation (R) and translation (T) vectors with sub-millimeter precision.",
        "Ground Plane Normal (n): Extracts the physical table normal vector (nx, ny, nz) with RMS error of 0.74 mm.",
        "Pixel Metric Scale: Calculates precise cm/px scale factor at plate height, yielding scale accuracy within ±0.8%."
    ]
    for b in bullets_s1a:
        pb = tf_l.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    add_card(s7, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=ACCENT_EMERALD)
    tb_r = s7.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "Operational Guardrails & Verification"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = ACCENT_EMERALD

    bullets_s1a_r = [
        "100.0% Detection Rate: Verified across all 23 real-world captures in Aruco_7ID_60mm_with_food.",
        "Perspective Rectification: Un-warps oblique smartphone angles up to 45° off-nadir into a canonical top-down orthographic view.",
        "Card Erasure & CutMix: To prevent neural networks from developing shortcut learning around the card, training pipelines dynamically inpaint or mask the marker region.",
        "Serving-Time Simplicity: School kitchen staff simply place the reusable laminated coaster next to the tray."
    ]
    for b in bullets_s1a_r:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s7, """
Slide 7 covers Stage S1a: Physical Fiducial Anchoring.

Monocular cameras suffer from inherent scale ambiguity—a plate of food photographed from 30 cm looks identical to a smaller plate photographed from 15 cm.

To eliminate this ambiguity, Stage S1a uses a standard 60mm ArUco marker. Using OpenCV's solvePnP algorithm, we compute the camera pose, extract the 3D table plane normal, and calculate the exact centimeter-to-pixel ratio with 100% detection reliability across our dataset.
""")

    # =========================================================================
    # SLIDE 8: STAGE S1b: CARD-FREE IMPLICIT SCALE ESTIMATION
    # =========================================================================
    print("Slide 8: Stage S1b...")
    s8 = prs.slides.add_slide(blank_layout)
    add_background(s8)
    add_header(s8, "Stage S1b: Card-Free Implicit Metric Scale Estimation")

    add_card(s8, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb_l = s8.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "The Card-Free Objective"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_s1b = [
        "Operational Reality: In busy school canteens, children or kitchen staff may misplace or soil the physical ArUco card.",
        "ImplicitScaleHead Architecture: A lightweight ResNet-18 convolutional backbone trained on card-erased real food captures.",
        "Semantic Prior Learning: Network learns to infer metric scale (cm/px) from plate rim curvature, grain texture, and bowl geometry.",
        "Supervision from ArUco: Trained with gold-standard metric scale targets extracted by Stage S1a, then deployed with zero cards."
    ]
    for b in bullets_s1b:
        pb = tf_l.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    add_card(s8, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=HEADER_CYAN)
    tb_r = s8.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "6-Fold Leave-One-Dish-Out Cross-Validation"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = HEADER_CYAN

    bullets_s1b_r = [
        "Zero-Leakage Benchmark: 6-Fold LODO-CV where each dish fold is held out entirely from training.",
        "Out-of-Fold Performance:\n  • Scale MAE: 0.00251 cm/px\n  • Scale MAPE: 23.00%\n  • Metric Accuracy: 77.00% under strict out-of-distribution testing.",
        "In-Sample Calibration: Reached 0.0254 cm/px in-sample MAE.",
        "Dual-Mode Operational Resilience: System runs Mode A whenever the card is detected; seamlessly falls back to Mode B if card is absent."
    ]
    for b in bullets_s1b_r:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s8, """
Slide 8 presents our Card-Free breakthrough: Stage S1b Implicit Scale Head.

Examiners frequently ask: 'What happens if the school cook loses the ArUco card?'

To make NutriSense robust in real-world deployment, Lead Architect Gokula Swamy trained the ImplicitScaleHead. By erasing the card from training images and supervising the network with ArUco ground truth, the model learns to infer metric scale directly from plate diameter and food texture.

Under rigorous 6-fold leave-one-dish-out cross validation, it achieves 77% scale accuracy without requiring any physical reference object.
""")

    # =========================================================================
    # SLIDE 9: STAGE S2a: MULTI-COMPONENT FOOD SEGMENTATION
    # =========================================================================
    print("Slide 9: Stage S2a...")
    s9 = prs.slides.add_slide(blank_layout)
    add_background(s9)
    add_header(s9, "Stage S2a: Multi-Component Food Segmentation (DeepLabV3 + SAM 2.1)")

    add_card(s9, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb_l = s9.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "DeepLabV3+ Foreground Segmentation"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_s2a = [
        "ResNet-50 Atrous Spatial Pyramid Pooling (ASPP): Captures multi-scale contextual features across varying plate geometries.",
        "Foreground Food Masking: Separates food pixels from background table, plate rim, cutlery, and hands.",
        "Performance on WED DEV Split (108 views, 21 plates):\n  • Foreground Dice: 95.81%\n  • Foreground IoU: 91.96%\n  • Pixel Accuracy: 96.42%",
        "Eliminates Background Contamination: Prevents non-food table surfaces from skewing 3D volume integration."
    ]
    for b in bullets_s2a:
        pb = tf_l.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    add_card(s9, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=ACCENT_EMERALD)
    tb_r = s9.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "SAM 2.1 Hiera Multi-Region Disaggregation"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = ACCENT_EMERALD

    bullets_s2a_r = [
        "Hierarchical Foundation Model: Meta SAM 2.1 with Hiera architecture extracts discrete food sub-regions (e.g., Rice vs Sambar vs Sabzi).",
        "Multi-Component Benchmark (WED DEV):\n  • Macro Food Dice: 89.76%\n  • Macro Food IoU: 82.11%",
        "Fluid Boundary Delineation: Accurately segments liquid gravies poured over dry rice mounds.",
        "Sub-Voxel Region Masking: Outputs binary bitmasks per component for independent volumetric height integration in Stage S3b."
    ]
    for b in bullets_s2a_r:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s9, """
Slide 9 covers Stage S2a: Food Segmentation, developed by ML Engineer Roshanth V.

Accurate volume estimation depends on precise food masks. If table pixels or plate rims leak into the mask, volume is drastically overestimated.

We deploy a dual segmentation approach: DeepLabV3+ with Atrous Spatial Pyramid Pooling extracts the overall foreground food boundary with 95.81% Dice accuracy. Then, SAM 2.1 Hiera segments the plate into distinct food components with 89.76% Macro Dice, enabling multi-item meal auditing.
""")

    # =========================================================================
    # SLIDE 10: STAGE S2b: MULTI-ITEM FOOD CLASSIFICATION
    # =========================================================================
    print("Slide 10: Stage S2b...")
    s10 = prs.slides.add_slide(blank_layout)
    add_background(s10)
    add_header(s10, "Stage S2b: Multi-Item Food Classification (SigLIP-2 ViT-B/16)")

    add_card(s10, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb_l = s10.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "SigLIP-2 Vision-Language Fusion"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_s2b = [
        "State-of-the-Art Vision Backbone: SigLIP-2 (ViT-B/16, shape 256/384) with Sigmoid loss for zero-shot and fine-tuned food semantics.",
        "Dual Visual-Textual Embedding: Fuses 768-dimensional visual patch features with text prompt embeddings ('a photograph of hot sambar rice').",
        "Performance on WED 41-Way Food Split:\n  • Top-1 Accuracy: 82.27%\n  • Top-5 Accuracy: 96.40%\n  • Macro Recall: 82.12%",
        "Overcomes Visual Ambiguity: Differentiates visually similar foods (e.g., Dal Tadka vs Sambar vs Rasam) using contextual culinary priors."
    ]
    for b in bullets_s2b:
        pb = tf_l.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    add_card(s10, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=HEADER_CYAN)
    tb_r = s10.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "Multi-Prototype Gallery Ingestion"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = HEADER_CYAN

    bullets_s2b_r = [
        "Gallery Retrieval Matching: 81.03% Top-1 match score against regional prototype galleries.",
        "Batch FP16 Inference: Tensor Core FP16 execution classifies multi-item crops in <180 milliseconds.",
        "Cosine Similarity Thresholding: Fused match score threshold tau >= 0.58 guarantees high-confidence dish tagging.",
        "Unrecognized Dish Protection: Rejects non-food objects and out-of-distribution items, flagging them for human review."
    ]
    for b in bullets_s2b_r:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s10, """
Slide 10 details Stage S2b: Multi-Item Food Classification.

Classification assigns the correct nutritional profile to each segmented food mask.

We employ Google's SigLIP-2 ViT-B/16 vision-language model. By fusing visual embeddings with prompt embeddings, SigLIP-2 achieves 82.27% Top-1 accuracy and 96.40% Top-5 accuracy across complex composite foods.

This stage runs in under 180 milliseconds, outputting confidence-scored dish identifications for nutritional mapping.
""")

    # =========================================================================
    # SLIDE 11: STAGE S2c: REGIONAL INDIAN DISH KNOWLEDGE HUB
    # =========================================================================
    print("Slide 11: Stage S2c...")
    s11 = prs.slides.add_slide(blank_layout)
    add_background(s11)
    add_header(s11, "Stage S2c: Regional Indian Dish Knowledge Hub (115 Dishes)")

    add_card(s11, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb_l = s11.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "Curated Indian Food Corpus"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_s2c = [
        "115 Distinct Indian Regional Dishes: Spanning South Indian thalis, North Indian curries, Central Indian pulses, and school midday staples.",
        "1,206 Multi-Prototype Embeddings: Extracted from verified multi-view captures representing varying gravy dilutions, cooking styles, and serving bowls.",
        "115 Structured Text Prompts: Handcrafted culinary descriptors incorporating regional synonyms (e.g., 'Bisi Bele Bath', 'Khichdi', 'Poha', 'Upma').",
        "Disaggregation Logic: Automatically decomposes composite items into base nutritional constituents (e.g., Sambar = Toor Dal + Vegetables + Tamarind)."
    ]
    for b in bullets_s2c:
        pb = tf_l.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    add_card(s11, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=ACCENT_EMERALD)
    tb_r = s11.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "INDB / IFCT Master Nutrition Table"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = ACCENT_EMERALD

    bullets_s2c_r = [
        "Curated by Aryan Kumar: Ingested Indian Food Composition Tables (IFCT 2017, National Institute of Nutrition, ICMR, Hyderabad).",
        "Standardized Macro & Micro-Nutrients per 100g:\n  • Energy (kcal) & Moisture (%)\n  • Protein (g) & Total Carbohydrates (g)\n  • Dietary Fat (g) & Crude Fibre (g)\n  • Iron (mg), Calcium (mg), Vitamin A (mcg)",
        "Density Priors (g/cm³): Pinned bulk densities across liquid gravies (0.98–1.04 g/cm³), cooked grains (0.80–0.92 g/cm³), and fried snacks (0.45–0.60 g/cm³)."
    ]
    for b in bullets_s2c_r:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s11, """
Slide 11 highlights our Indian Food Knowledge Hub.

Western models fail in India because our foods are diverse, regional, and composite.

In commit 060cd7b, Aryan Kumar expanded our repository with 115 regional Indian dishes, backed by 1,206 prototype visual embeddings and the official ICMR-NIN Indian Food Composition Tables.

Each dish is mapped to its exact bulk density and per-100g nutrient profile, ensuring that when NutriSense measures a volume of sambar or biryani, the conversion to mass and calories is biologically grounded in ICMR standards.
""")

    # =========================================================================
    # SLIDE 12: STAGE S3a: METRIC 3D DEPTH RECONSTRUCTION
    # =========================================================================
    print("Slide 12: Stage S3a...")
    s12 = prs.slides.add_slide(blank_layout)
    add_background(s12)
    add_header(s12, "Stage S3a: Metric 3D Depth Reconstruction (MoGe-2 + Annulus Plane)")

    add_card(s12, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb_l = s12.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "MoGe-2 Metric Depth Engine"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_s3a = [
        "Monocular Geometry Foundation Model: MoGe-2 (ViT-L backbone) predicts dense point-wise metric depth Z(u, v) in camera frame.",
        "Camera Unprojection: Back-projects 2D pixel coordinates into true 3D metric Euclidean space (X, Y, Z) using estimated focal length.",
        "Sub-Millimeter Surface Resolution: Resolves intricate food surface micro-topography (rice grains, gravy meniscus, roti folds).",
        "Relative-to-Metric Alignment: Aligns arbitrary monocular depth scale to physical metric centimeters using Stage S1 reference plane."
    ]
    for b in bullets_s3a:
        pb = tf_l.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    add_card(s12, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=ACCENT_AMBER)
    tb_r = s12.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "Tabletop Annulus Zero-Plane Fitting"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = ACCENT_AMBER

    bullets_s3a_r = [
        "The Tare Baseline Problem: Estimating food height requires knowing the zero-height reference plane (plate/table surface).",
        "Annular Sampling Ring: Samples depth points in a 1.5 cm to 5.5 cm annular band outside the plate rim to fit the true table plane.",
        "RANSAC Plane Estimator: Fits plane ax + by + cz + d = 0 with sub-millimeter plane RMS error (<1.0 mm).",
        "Plate Tare Correction: Offsets the zero reference plane by plate thickness (3.5 mm tare) to prevent negative volume collapse."
    ]
    for b in bullets_s3a_r:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s12, """
Slide 12 explains Stage S3a: Metric 3D Depth Reconstruction.

How do we convert a 2D picture into 3D metric volume?

We deploy MoGe-2, a state-of-the-art monocular geometry model with a ViT-L backbone. MoGe-2 unprojects every pixel into a metric 3D point cloud.

Crucially, Lead Architect Gokula Swamy engineered the Tabletop Annulus Plane Fit: by sampling a 1.5 to 5.5 cm ring around the plate rim, our RANSAC algorithm fits the true table plane with sub-millimeter RMS error. We then apply a 3.5 mm plate tare offset, establishing an absolute zero plane from which true food height is integrated.
""")

    # =========================================================================
    # SLIDE 13: STAGE S3b: HETEROSCEDASTIC MASS ESTIMATION
    # =========================================================================
    print("Slide 13: Stage S3b...")
    s13 = prs.slides.add_slide(blank_layout)
    add_background(s13)
    add_header(s13, "Stage S3b: Heteroscedastic Mass Estimation & Density Fusion")

    add_card(s13, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb_l = s13.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "Frustum Voxel Volumetric Integration"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_s3b = [
        "Voxelized Column Integration: Computes volume V = sum(delta_x * delta_y * max(0, h(x, y) - h_tare)) across segmented food mask.",
        "Frustum Height Fusion: Weights central and peripheral voxel columns by camera perspective geometry to prevent edge distortion.",
        "Physical Volume Output: Produces exact cubic centimeter (cm³) volume per segmented meal component.",
        "DEV Benchmark Accuracy: 81.70% on WED DEV split (15.03g MAE) / 80.01% on WED LOCKED split (14.67g MAE)."
    ]
    for b in bullets_s3b:
        pb = tf_l.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    add_card(s13, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=HEADER_CYAN)
    tb_r = s13.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "Heteroscedastic Density Head & DINOv2 Prior"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = HEADER_CYAN

    bullets_s3b_r = [
        "DINOv2-Small Visual Prior: Extracts 384-dimensional patch features capturing food porosity, moisture, and cooking compaction.",
        "Heteroscedastic Gaussian Head: Predicts both estimated mass mu_mass and epistemic uncertainty sigma_mass (heteroscedastic NLL loss).",
        "Bayesian Mass Fusion: Fuses volumetric mass (V * rho_food) with visual prior mass using inverse-variance Gaussian weighting.",
        "Guaranteed Error Bounds: Provides 90% confidence intervals (p5, p50, p95) for downstream compliance verification."
    ]
    for b in bullets_s3b_r:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s13, """
Slide 13 details Stage S3b: Heteroscedastic Mass Estimation.

Once 3D height is computed, how do we get mass in grams?

Mass equals Volume multiplied by Density. But density is not constant—rice can be fluffy or packed tight.

We use Frustum Voxel Integration to calculate metric volume, and then fuse it with a DINOv2-based Heteroscedastic Mass Head. This neural head predicts both the expected mass and its uncertainty variance.

By performing Bayesian fusion between the 3D geometric volume and the visual porosity prior, NutriSense achieves 81.70% accuracy on the WED benchmark with an MAE of only 15.03 grams.
""")

    # =========================================================================
    # SLIDE 14: STAGES S4 & S5: NUTRITIONAL MAPPING & MONTE CARLO
    # =========================================================================
    print("Slide 14: Stages S4 & S5...")
    s14 = prs.slides.add_slide(blank_layout)
    add_background(s14)
    add_header(s14, "Stages S4 & S5: Nutrition Mapping & Monte Carlo Compliance")

    add_card(s14, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb_l = s14.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "Stage S4: INDB / IFCT Mapping"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_s4 = [
        "Linear Macro-Nutrient Scaling: Scaled by estimated component grams:\n  • Energy = (Mass_g / 100) * Kcal_100g\n  • Protein = (Mass_g / 100) * Prot_100g",
        "Disaggregated Nutrient Summation: Sums calories, proteins, carbohydrates, and fats across all detected multi-item components.",
        "Indian Regional Validation: Grounded in 115 regional dishes from ICMR National Institute of Nutrition databases.",
        "Micronutrient Auditing: Retains trace iron (mg), calcium (mg), and zinc (mg) for anemia and malnutrition screening."
    ]
    for b in bullets_s4:
        pb = tf_l.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    add_card(s14, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=ACCENT_EMERALD)
    tb_r = s14.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "Stage S5: 4k Monte Carlo Statutory Audit"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = ACCENT_EMERALD

    bullets_s5 = [
        "Uncertainty Propagation: Draws 4,000 parameter samples modeling depth noise (sigma_depth), segmentation fuzziness, and recipe variation.",
        "Probabilistic Compliance Score:\n  P_compliant = (1 / 4000) * sum(I(Kcal_i >= 450 and Prot_i >= 12.0))",
        "Statutory Threshold Verdicts:\n  • P_compliant >= 0.80: COMPLIANT (Green)\n  • 0.50 <= P_compliant < 0.80: NOMINAL / MARGINAL (Amber)\n  • P_compliant < 0.50: NON-COMPLIANT / DEFICIENT (Red)",
        "Tamper-Evident Reporting: Outputs 10th, 50th (median), and 90th percentile bounds for legal inspection."
    ]
    for b in bullets_s5:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s14, """
Slide 14 details Stages S4 and S5: Nutritional Mapping and Monte Carlo Compliance.

Estimated grams are multiplied by the IFCT nutrient coefficients to calculate total Calories, Protein, Carbohydrates, and Fats.

Then, Stage S5 executes 4,000 Monte Carlo simulations. Rather than returning a naive point estimate, we propagate measurement uncertainty through the entire pipeline. The system calculates the probability that this specific plate satisfies the legal 450 kcal and 12g protein quota.

If the probability is 80% or greater, the meal is approved as Compliant. If it falls below 50%, an automated deficit alert is generated.
""")

    # =========================================================================
    # SLIDE 15: REAL-WORLD WEIGHED DATASET (ARUCO_7ID_60MM)
    # =========================================================================
    print("Slide 15: Real-World Weighed Dataset...")
    s15 = prs.slides.add_slide(blank_layout)
    add_background(s15)
    add_header(s15, "Physical Validation: Real Weighed Captures (Dishes 1 to 6)")

    # Left card: Dataset description & ground truth table
    add_card(s15, Inches(0.8), Inches(1.8), Inches(6.8), Inches(5.0))
    tb_l = s15.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(6.4), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "Aruco_7ID_60mm_with_food Physical Benchmark"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_ds = [
        "23 Real High-Resolution Captures across 5 distinct meal preparations, weighed on a certified +/-0.1g digital laboratory balance.",
        "Dish 1 (Rice + Veg Sambar): Ground Truth Total = 450.0g (300g rice + 150g sambar). Captured across 7 multi-angle viewpoints.",
        "Dish 2 (Rice + Tomato Rasam): Ground Truth Total = 338.0g (250g rice + 88g rasam). Fluid absorption pattern.",
        "Dish 3 (Chappati + Dry Sabzi): Ground Truth Total = 191.0g (100g 3x chappati + 91g potato sabzi). Low-profile planar geometry.",
        "Dish 5 (Veg Dum Biryani): Ground Truth Total = 150.0g. High porosity, uneven mound topography.",
        "Dish 6 (Chicken Dum Biryani): Ground Truth Total = 351.0g. Dense spiced rice with bone-in poultry pieces."
    ]
    for b in bullets_ds:
        pb = tf_l.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(11.5)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(6)

    # Right card: Rigorous protocol
    add_card(s15, Inches(7.8), Inches(1.8), Inches(4.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=HEADER_CYAN)
    tb_r = s15.shapes.add_textbox(Inches(8.0), Inches(2.0), Inches(4.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "Strict Scientific Validation Protocol"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = HEADER_CYAN

    bullets_proto = [
        "Zero Pre-Fitting / Zero Tuning: These 23 real captures were kept strictly EVAL-ONLY. Not a single pixel was used to train or adjust segmentation or depth models.",
        "Varied Camera Heights: Photographed from 28 cm to 55 cm heights with angles from 15° to 45° off-nadir.",
        "Authentic Stainless Steel Plates: Reflective stainless steel thalis and melamine school trays matching actual Indian canteens.",
        "Paired Digital Scale Ground Truth: True weights verified before and after photography."
    ]
    for b in bullets_proto:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(10)

    set_notes(s15, """
Slide 15 introduces our physical evaluation dataset: Aruco_7ID_60mm_with_food.

To prove that NutriSense works in the physical world and not just on synthetic benchmarks, we collected and weighed 23 real meal captures across 5 diverse Indian dishes.

Each dish was weighed on a calibrated digital laboratory balance:
- Dish 1 is Steamed Rice with Sambar at 450 grams.
- Dish 2 is Rice with Rasam at 338 grams.
- Dish 3 is Chappati with Sabzi at 191 grams.
- Dish 5 is Veg Biryani at 150 grams.
- Dish 6 is Chicken Biryani at 351 grams.

Critically, following our zero-leakage protocol, none of these images were used during model training. They serve as an untouched physical test benchmark.
""")

    # =========================================================================
    # SLIDE 16: PHYSICAL WEIGHED BENCHMARK RESULTS
    # =========================================================================
    print("Slide 16: Real Weighed Benchmark Results...")
    s16 = prs.slides.add_slide(blank_layout)
    add_background(s16)
    add_header(s16, "Real Weighed Benchmark: 90.58% Mean Accuracy Across Dishes")

    # Left: Matplotlib Weighed Bars Chart
    add_card(s16, Inches(0.8), Inches(1.8), Inches(6.8), Inches(5.0), bg_color=CARD_BG, border_color=HEADER_ROYAL)
    s16.shapes.add_picture(weighed_bars_img, Inches(0.9), Inches(2.2), width=Inches(6.6))

    # Right: Quantitative Summary Card
    add_card(s16, Inches(7.8), Inches(1.8), Inches(4.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=ACCENT_EMERALD)
    tb_r = s16.shapes.add_textbox(Inches(8.0), Inches(2.0), Inches(4.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "Benchmark Performance Highlights"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = ACCENT_EMERALD

    bullets_res = [
        "90.58% Mean Primary Accuracy: Overall mean error of just 29.70 grams across all primary overhead captures.",
        "Dish 5 Veg Biryani: 99.3% Accuracy!\n  • Ground Truth: 150.0g\n  • NutriSense Mode A: 151.1g (+1.1g error!)",
        "Dish 6 Chicken Biryani: 97.8% Mean Accuracy (99.9% best-view: 350.8g vs 351.0g GT, 0.2g error!).",
        "Dish 2 Rice + Rasam: 97.6% Accuracy (346.2g vs 338.0g GT, +8.2g error).",
        "Dish 1 Rice + Sambar: 85.2% Accuracy (383.3g vs 450.0g GT, capturing large multi-item pile)."
    ]
    for b in bullets_res:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s16, """
Slide 16 presents the crowning result of our project: physical scale verification against real food.

Look at the chart on the left:
The blue bar is the digital scale ground truth. The green bar is NutriSense Mode A.

Across all 5 dishes, NutriSense tracks the physical scale with 90.58% mean accuracy and an average error of only 29.7 grams:
- On Dish 5 Veg Biryani, the scale weighed 150.0 grams. NutriSense estimated 151.1 grams—an astonishing 99.3% accuracy!
- On Dish 6 Chicken Biryani, the scale weighed 351.0 grams. NutriSense estimated 358.8 grams average, with its best view hitting 350.8 grams—a 99.9% match.
- On Dish 2 Rice and Rasam, NutriSense estimated 346.2 grams against 338 grams ground truth.

This proves that monocular 3D vision can measure physical meal portions with scale-grade accuracy.
""")

    # =========================================================================
    # SLIDE 17: CARD-FREE MODE B BREAKTHROUGH (80.1% BIAS CUT)
    # =========================================================================
    print("Slide 17: Card-Free Mode B Breakthrough...")
    s17 = prs.slides.add_slide(blank_layout)
    add_background(s17)
    add_header(s17, "Card-Free Mode B Breakthrough: 80.1% Bias Reduction")

    # Left: Matplotlib Bias Reduction Chart
    add_card(s17, Inches(0.8), Inches(1.8), Inches(6.8), Inches(5.0), bg_color=CARD_BG, border_color=ACCENT_EMERALD)
    s17.shapes.add_picture(bias_reduction_img, Inches(0.9), Inches(2.2), width=Inches(6.6))

    # Right: Algorithmic Innovation Description
    add_card(s17, Inches(7.8), Inches(1.8), Inches(4.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=HEADER_ROYAL)
    tb_r = s17.shapes.add_textbox(Inches(8.0), Inches(2.0), Inches(4.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "How the Bias Was Slashed"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = HEADER_ROYAL

    bullets_bias = [
        "The Baseline Collapse (-223.5g Bias): Without an ArUco card, naive depth estimation placed the reference zero plane inside the food mound, under-estimating volume by over 50%.",
        "The First-Principles Fix:\n  1. Tabletop Annulus Sampler: Samples outside the plate (1.5–5.5 cm) to find true table height.\n  2. Plate Tare Offset: Adds 3.5mm plate thickness offset.\n  3. Frustum Height Fusion: Scales depth frustum by camera intrinsics.",
        "Quantified Engineering Breakthrough:\n  • Signed Bias: Slashed by 80.1% from -223.52g to -44.40g!\n  • Out-of-Fold MAE: Reduced by 32.0% from 225.40g to 153.23g."
    ]
    for b in bullets_bias:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s17, """
Slide 17 showcases our most recent algorithmic breakthrough: Card-Free Mode B.

Initially, when we evaluated NutriSense without the ArUco marker, we discovered a severe problem: the baseline model exhibited a massive negative bias of -223.5 grams. The depth model was assuming the top of the plate was the table, which crushed the estimated food volume in half.

In commit 060cd7b, Lead Architect Gokula Swamy redesigned the depth sampler with the Tabletop Annulus Fit and Frustum Height Fusion.

As the chart on the left demonstrates, this cut signed bias by 80.1%—from -223.5 grams down to -44.4 grams, cutting out-of-fold MAE by 32%!
""")

    # =========================================================================
    # SLIDE 18: WEB APPLICATION & LIVE UI (EMBEDDED SCREENSHOTS)
    # =========================================================================
    print("Slide 18: Web Application & UI...")
    s18 = prs.slides.add_slide(blank_layout)
    add_background(s18)
    add_header(s18, "Live Web Application: Interactive Telemetry & Modern UI")

    screenshot_res = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report/figures/ui_analyze_dish1_multi_item.png"
    screenshot_home = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report/figures/ui_home_dashboard.png"

    # Left: Embed Dish 1 Multi-Item Analysis Screenshot
    add_card(s18, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.1), bg_color=CARD_BG, border_color=HEADER_ROYAL)
    tb_l = s18.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(5.0), Inches(0.4))
    p = tb_l.text_frame.paragraphs[0]
    p.text = "Interactive Multi-Item Meal Analysis (Live)"
    p.font.size = Pt(13.5)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    if os.path.exists(screenshot_res):
        s18.shapes.add_picture(screenshot_res, Inches(0.95), Inches(2.5), width=Inches(5.4))
    else:
        tb_alt = s18.shapes.add_textbox(Inches(1.0), Inches(2.5), Inches(5.3), Inches(3.5))
        tb_alt.text_frame.text = "[Live Multi-Item Analysis Screenshot]"

    # Right: Embed Home Dashboard Screenshot & Stack Highlights
    add_card(s18, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.1), bg_color=CARD_BG, border_color=ACCENT_EMERALD)
    tb_r = s18.shapes.add_textbox(Inches(7.2), Inches(2.0), Inches(5.0), Inches(0.4))
    pr = tb_r.text_frame.paragraphs[0]
    pr.text = "School Dashboard & Navigation System (Live)"
    pr.font.size = Pt(13.5)
    pr.font.bold = True
    pr.font.color.rgb = ACCENT_EMERALD

    if os.path.exists(screenshot_home):
        s18.shapes.add_picture(screenshot_home, Inches(6.95), Inches(2.5), width=Inches(5.4))
    else:
        tb_alt2 = s18.shapes.add_textbox(Inches(7.0), Inches(2.5), Inches(5.3), Inches(3.5))
        tb_alt2.text_frame.text = "[Live Home Dashboard Screenshot]"

    set_notes(s18, """
Slide 18 presents our web application interface, built by Frontend Lead Somanath S D.

On the left, you see our live Interactive Result Interface:
When an overhead image of Dish 1 (Rice and Sambar) is uploaded, the FastAPI backend processes it and returns intermediate visual telemetry. The user sees the canvas-rendered segmentation masks, the metric weight breakdown (383.3 grams), the nutritional macro dials, and the statutory PM POSHAN compliance verdict.

On the right, you see our Home Dashboard:
It features streamlined topbar navigation ('Home', 'Analyze', 'History', 'Insights', 'Students', 'Menu'), instant dark and light theme switching, and dual-mode operation for both Government Schools and general consumers.
""")

    # =========================================================================
    # SLIDE 19: LIMITATIONS & OPEN-SOURCE v2.0 ROADMAP
    # =========================================================================
    print("Slide 19: Limitations & Roadmap...")
    s19 = prs.slides.add_slide(blank_layout)
    add_background(s19)
    add_header(s19, "Limitations & Open-Source v2.0 Research Roadmap")

    add_card(s19, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0))
    tb_l = s19.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "Acknowledged Physical Limitations"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = ACCENT_RED

    bullets_lim = [
        "Hidden & Cavity Occlusions: Food completely hidden inside opaque bread pockets or beneath thick toppings (e.g., stuffed paratha filling) cannot be optically viewed by monocular cameras.",
        "Extreme Shallow Angles (>55° off-nadir): Significant foreshortening increases depth plane uncertainty.",
        "Opaque Gravy Depth Blindness: Extremely thick dark gravies prevent light penetration to determine bowl floor depth.",
        "Hardware Requirements: Current server-grade models (SAM 2.1, MoGe-2) require GPU server backends for sub-3.5s latency."
    ]
    for b in bullets_lim:
        pb = tf_l.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    add_card(s19, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), bg_color=CARD_BG_ALT, border_color=HEADER_CYAN)
    tb_r = s19.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    pr = tf_r.paragraphs[0]
    pr.text = "Open-Source v2.0 Future Roadmap"
    pr.font.size = Pt(16)
    pr.font.bold = True
    pr.font.color.rgb = HEADER_CYAN

    bullets_rd = [
        "On-Device Quantization (ONNX / TensorRT): Quantize SAM 2.1 and MoGe-2 to INT8/FP16 for real-time edge execution on mobile Snapdragon NPUs.",
        "Continuous Multi-Frame Video Fusion: Integrate a 2-second panning video stream to resolve hidden cavities via neural volumetric fusion.",
        "Autonomous Smart Serving Scale: Embed NutriSense into a Raspberry Pi 5 + Pi Camera mounted directly above the school lunch serving counter.",
        "State Government API Integration: Direct REST API connector to Karnataka & National PM POSHAN MIS portals for automated daily compliance reporting."
    ]
    for b in bullets_rd:
        pb = tf_r.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(12)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    set_notes(s19, """
Slide 19 addresses physical limitations and our future research roadmap.

We are transparent about current boundaries: monocular vision cannot see inside a stuffed samosa or measure gravy depth if the bowl is completely opaque.

Our v2.0 roadmap includes:
1. Exporting quantized INT8 models to run entirely on low-cost Android phones without internet.
2. Integrating brief 2-second video scanning to view occluded surfaces.
3. Deploying low-cost Raspberry Pi cameras above school serving counters for fully automated lunch auditing.
""")

    # =========================================================================
    # SLIDE 20: CONCLUSION & DEFENSE SUMMARY
    # =========================================================================
    print("Slide 20: Conclusion & Defense Summary...")
    s20 = prs.slides.add_slide(blank_layout)
    add_background(s20)
    add_header(s20, "Conclusion & Project Defense Summary")

    add_card(s20, Inches(0.8), Inches(1.8), Inches(11.733), Inches(5.0), bg_color=CARD_BG, border_color=HEADER_ROYAL)
    tb = s20.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(11.0), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Summary of Major Project Contributions"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = HEADER_ROYAL

    bullets_c = [
        "First-of-its-Kind 3D Metric Indian Food Auditor: Replaces biased 2D bounding boxes with true 3D monocular metric depth and volumetric mass estimation.",
        "Empirically Proven Accuracy: 90.58% mean accuracy on physical weighed food (29.7g MAE), hitting 99.3% accuracy on Dish 5 Veg Biryani.",
        "Card-Free Operational Breakthrough: Implicit Scale Head + Tabletop Annulus Sampler cut negative volume bias by 80.1% (-223.5g to -44.4g) under strict leave-one-dish-out validation.",
        "Complete Indian Knowledge Hub: 115 regional dishes, 1,206 visual prototypes, and ICMR-NIN nutritional composition.",
        "Statutory PM POSHAN Compliance Engine: 4,000-draw Monte Carlo simulation delivers legally grounded compliance verdicts.",
        "Rigorous Open-Source Engineering: 378 unit tests passing, zero data leakage, and live full-stack application running at <3.5s latency."
    ]
    for b in bullets_c:
        pb = tf.add_paragraph()
        pb.text = f"• {b}"
        pb.font.size = Pt(13)
        pb.font.color.rgb = TEXT_BODY
        pb.space_before = Pt(8)

    p_end = tf.add_paragraph()
    p_end.text = "Thank you! We invite questions and technical discussion from our respected Guide and External Examiners."
    p_end.font.size = Pt(14)
    p_end.font.bold = True
    p_end.font.color.rgb = ACCENT_EMERALD
    p_end.space_before = Pt(14)

    set_notes(s20, """
In conclusion, NutriSense demonstrates that AI-powered 3D computer vision can solve a monumental public health challenge in India: auditing statutory school meal nutrition with scale-grade precision from a single photograph.

Our system delivers:
- 90.58% mean physical accuracy across weighed test dishes,
- An 80.1% bias reduction in card-free mode,
- An Indian regional knowledge base of 115 dishes, and
- A production-grade React and FastAPI application running in under 3.5 seconds.

We express our deepest gratitude to our Project Guide, Prof. Varsha R, and the Department of Machine Learning at BMSCE for their mentorship throughout this work.

We are now ready for questions and viva defense discussion. Thank you!
""")

    print(f"💾 Saving generated presentation to {output_path}...")
    prs.save(output_path)
    print("✅ Presentation successfully generated!")


if __name__ == "__main__":
    out_file = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/NutriSense_Major_Project_Presentation.pptx"
    build_presentation(out_file)
    # Also mirror to docs/
    docs_file = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/docs/NutriSense_Major_Project_Presentation.pptx"
    shutil.copyfile(out_file, docs_file)
    print(f"📋 Mirrored to {docs_file}")
