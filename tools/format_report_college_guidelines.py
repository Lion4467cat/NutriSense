# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Format NutriSense Academic Report according to B.M.S. College of Engineering Guidelines.

Follows 'General_Guideines_for Project Work 2 Report (1).docx':
- Times New Roman font throughout.
- Chapter Titles in 14 pt, ALL CAPS.
- Section Titles (2.1, 2.2, …) in 14 pt, Bold.
- Subsection Titles (2.1.1, 2.1.2, …) in 12 pt, Bold.
- Body Text in 12 pt, Normal, 1.5 line spacing, Justified.
- Figure captions: 'Figure X.Y: Title' centered below figure.
- Table captions: 'Table X.Y: Title' centered above table.
- Images of high resolution, clear, readable, zero dark backgrounds, exact native aspect ratios.
- Strips intrusive '(IEEE STD ...)' tags while preserving high technical/academic rigor.
"""

import os
import re
import io
import shutil
import zipfile
import subprocess
from PIL import Image
from xml.etree import ElementTree as ET
import docx
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

REPORT_DIR = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report"
DOCX_PATH = os.path.join(REPORT_DIR, "NutriSense_Roman_Report.docx")
ASSETS_DIR = os.path.join(REPORT_DIR, "assets")
FIGURES_DIR = os.path.join(REPORT_DIR, "figures")


def set_run_font(run, size_pt=12, bold=False, italic=False, color=RGBColor(0, 0, 0)):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color


def clean_ieee_tags(text: str) -> str:
    """Strip intrusive IEEE STD tags while keeping titles clean and formal."""
    # Strip IEEE Std / ISO tags in parentheses
    text = re.sub(r"\s*\((?:IEEE|ISO)[^)]*\)", "", text, flags=re.IGNORECASE)
    # Strip trailing or standalone Roman numerals after colon e.g. "CHAPTER 1: I. " -> "CHAPTER 1: "
    text = re.sub(r"CHAPTER (\d+):\s+[IVXLCDM]+\.\s+", r"CHAPTER \1: ", text)
    # Strip standalone Roman numerals e.g. "I. INTRODUCTION & PROBLEM CONTEXT" -> "INTRODUCTION & PROBLEM CONTEXT"
    text = re.sub(r"^[IVXLCDM]+\.\s+", "", text)
    # Strip TABLE X.Y (IEEE ...) -> TABLE X.Y
    text = re.sub(r"\s*\(IEEE STD \d+\)", "", text, flags=re.IGNORECASE)
    return text.strip()


def format_docx():
    print("📖 Loading DOCX:", DOCX_PATH)
    doc = docx.Document(DOCX_PATH)

    # 1. Update Table of Contents (Paragraphs 50 to 130)
    toc_map = {
        "CHAPTER 1": ("CHAPTER 1: INTRODUCTION", 1),
        "CHAPTER 2": ("CHAPTER 2: PROBLEM STATEMENT & OBJECTIVES", 6),
        "CHAPTER 3": ("CHAPTER 3: LITERATURE SURVEY", 8),
        "CHAPTER 4": ("CHAPTER 4: SYSTEM REQUIREMENTS SPECIFICATION", 13),
        "CHAPTER 5": ("CHAPTER 5: SYSTEM DESIGN", 17),
        "CHAPTER 6": ("CHAPTER 6: SYSTEM IMPLEMENTATION", 26),
        "CHAPTER 7": ("CHAPTER 7: TESTING AND RESULTS", 32),
        "CHAPTER 8": ("CHAPTER 8: PROJECT MANAGEMENT AND CONCLUSION", 37),
    }

    for p in doc.paragraphs[50:130]:
        t = p.text.strip()
        for prefix, (title, page) in toc_map.items():
            if t.startswith(prefix):
                p.text = f"{title}\t{page}"
                p.paragraph_format.line_spacing = 1.15
                for r in p.runs:
                    set_run_font(r, size_pt=12, bold=True)
                break
            elif "Functional Requirements" in t and ("IEEE" in t or "\t" in t):
                p.text = "4.1 Functional Requirements\t13"
                for r in p.runs:
                    set_run_font(r, size_pt=12)
                break
            elif "Non-functional Requirements" in t and ("IEEE" in t or "\t" in t):
                p.text = "4.2 Non-Functional Requirements\t13"
                for r in p.runs:
                    set_run_font(r, size_pt=12)
                break

    # 2. Update Table 2 (List of Figures)
    if len(doc.tables) > 2:
        t_figs = doc.tables[2]
        fig_rows = [
            ("Figure 1.1", "NutriSense problem context and optical nutrition assessment workflow", "2"),
            ("Figure 1.2", "Architectural comparison: conventional 2D heuristic approaches vs. NutriSense 3D metrological pipeline", "4"),
            ("Figure 5.1", "NutriSense multi-stage metrological system architecture", "17"),
            ("Figure 5.2", "Whole-project decision flowchart from meal capture to compliance verdict", "19"),
            ("Figure 5.3(a)", "Conceptual class and modular architecture diagram", "23"),
            ("Figure 5.3(b)", "Activity diagram for meal analysis across system swimlanes", "24"),
            ("Figure 5.3(c)", "Use case diagram with institutional stakeholder roles", "24"),
            ("Figure 6.1", "Backend and frontend implementation layout and wire contract architecture", "26"),
            ("Figure 6.2", "Probabilistic nutritional metrology and comonotonic Monte Carlo uncertainty propagation", "29"),
            ("Figure A.1", "NutriSense unified desktop dashboard (Clean light-theme UI with responsive topbar navigation)", "43"),
            ("Figure A.2", "Single-dish meal verification: Dish 5 (Vegetable Dum Biryani, 151.1 g estimate vs 150.0 g scale GT, 99.3% accuracy)", "44"),
            ("Figure A.3", "Multi-item Indian Thali meal decomposition: Dish 1 (Steamed rice, sambar, roti, and vegetable curry evaluated)", "45"),
            ("Figure A.4", "Dual-item meal recognition: Dish 2 (Steamed Rice 265.3 g + Tomato Rasam 213.4 g multi-region analysis)", "46"),
            ("Figure A.5", "Statutory PM POSHAN Mid-Day Meal standards & ICMR-NIN IFCT 2017 nutritional targets interface", "47"),
            ("Figure A.6", "Institutional audit logs, daily compliance analytics, and longitudinal nutrient tracking", "48"),
            ("Figure A.7", "Context-aware meal critique and conversational dietary guidance", "49"),
            ("Figure A.8", "System settings, backend connection verification, and accessibility preferences", "50"),
        ]
        for idx, (col0, col1, col2) in enumerate(fig_rows):
            if idx + 1 < len(t_figs.rows):
                row = t_figs.rows[idx + 1]
            else:
                row = t_figs.add_row()
            row.cells[0].text = col0
            row.cells[1].text = col1
            row.cells[2].text = col2
            for cell in row.cells:
                for cp in cell.paragraphs:
                    cp.paragraph_format.space_before = Pt(2)
                    cp.paragraph_format.space_after = Pt(2)
                    for r in cp.runs:
                        set_run_font(r, size_pt=10)

    # 3. Update Table 3 (List of Tables)
    if len(doc.tables) > 3:
        t_tabs = doc.tables[3]
        tab_rows = [
            ("Table 1.1", "Project scope and operational boundaries", "3"),
            ("Table 4.1", "Formal functional requirements specification (FR-01 to FR-14)", "13"),
            ("Table 4.2", "Non-functional requirements specification", "16"),
            ("Table 7.1", "Master model-by-model and end-to-end pipeline accuracy summary", "32"),
        ]
        for idx, (col0, col1, col2) in enumerate(tab_rows):
            if idx + 1 < len(t_tabs.rows):
                row = t_tabs.rows[idx + 1]
            else:
                row = t_tabs.add_row()
            row.cells[0].text = col0
            row.cells[1].text = col1
            row.cells[2].text = col2
            for cell in row.cells:
                for cp in cell.paragraphs:
                    cp.paragraph_format.space_before = Pt(2)
                    cp.paragraph_format.space_after = Pt(2)
                    for r in cp.runs:
                        set_run_font(r, size_pt=10)

    # 4. Standardize Body Paragraphs
    chapter_titles = {
        "CHAPTER 1": "CHAPTER 1\nINTRODUCTION",
        "CHAPTER 2": "CHAPTER 2\nPROBLEM STATEMENT & OBJECTIVES",
        "CHAPTER 3": "CHAPTER 3\nLITERATURE SURVEY",
        "CHAPTER 4": "CHAPTER 4\nSYSTEM REQUIREMENTS SPECIFICATION",
        "CHAPTER 5": "CHAPTER 5\nSYSTEM DESIGN",
        "CHAPTER 6": "CHAPTER 6\nSYSTEM IMPLEMENTATION",
        "CHAPTER 7": "CHAPTER 7\nTESTING AND RESULTS",
        "CHAPTER 8": "CHAPTER 8\nPROJECT MANAGEMENT AND CONCLUSION",
    }

    fig_pattern = re.compile(r"^(?:Fig\.|Figure)\s*([A-Za-z0-9]+\.[\d\w()]+)\.?\s*(.*)", re.IGNORECASE)
    table_pattern = re.compile(r"^TABLE\s*([A-Za-z0-9]+\.\d+)\.?\s*(.*)", re.IGNORECASE)

    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue

        # Check for Chapter Title
        matched_ch = False
        for prefix, full_title in chapter_titles.items():
            if txt.startswith(prefix) and ("INTRODUCTION" in txt or "PROBLEM" in txt or "LITERATURE" in txt or "REQUIREMENT" in txt or "DESIGN" in txt or "IMPLEMENTATION" in txt or "TESTING" in txt or "PROJECT" in txt or "IEEE" in txt or "VII" in txt or "VI." in txt or "V." in txt or "IV." in txt or "III." in txt or "II." in txt or "I." in txt):
                p.text = full_title
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(18)
                p.paragraph_format.space_after = Pt(12)
                for r in p.runs:
                    set_run_font(r, size_pt=14, bold=True)
                matched_ch = True
                break
        if matched_ch:
            continue

        # Check for Section Title (e.g. 1.1, 2.1, 3.1, etc.)
        if re.match(r"^\d+\.\d+\s+[A-Z]", txt):
            cleaned = clean_ieee_tags(txt)
            p.text = cleaned
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(6)
            for r in p.runs:
                set_run_font(r, size_pt=14, bold=True)
            continue

        # Check for Subsection Title (e.g. 2.1.1, 4.1.1, etc.)
        if re.match(r"^\d+\.\d+\.\d+\s+[A-Z]", txt):
            cleaned = clean_ieee_tags(txt)
            p.text = cleaned
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(4)
            for r in p.runs:
                set_run_font(r, size_pt=12, bold=True)
            continue

        # Check for Figure Caption
        m_fig = fig_pattern.match(txt)
        if m_fig:
            fig_num = m_fig.group(1)
            fig_desc = clean_ieee_tags(m_fig.group(2).strip(" .:-"))
            p.text = f"Figure {fig_num}: {fig_desc}"
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(10)
            for r in p.runs:
                set_run_font(r, size_pt=10, italic=True)
            continue

        # Check for Table Caption
        m_tab = table_pattern.match(txt)
        if m_tab:
            tab_num = m_tab.group(1)
            tab_desc = clean_ieee_tags(m_tab.group(2).strip(" .:-"))
            p.text = f"Table {tab_num}: {tab_desc}"
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            for r in p.runs:
                set_run_font(r, size_pt=10, bold=True)
            continue

        # Normal Body Text
        # Only adjust runs if not a title or table cell
        if "IEEE" in txt:
            # Clean paragraph body text of awkward IEEE Std phrasing in headers
            if "In compliance with IEEE Std 830-1998" in txt:
                p.text = txt.replace(
                    "In compliance with IEEE Std 830-1998 (Recommended Practice for Software Requirements Specifications) and ISO/IEC/IEEE 29148:2018, every functional requirement in NutriSense",
                    "Every functional requirement in NutriSense"
                )
            elif "FORMAL FUNCTIONAL REQUIREMENTS SPECIFICATION (IEEE" in txt:
                p.text = "Table 4.1: Formal Functional Requirements Specification"

        # Apply Times New Roman 12pt, 1.5 line spacing, Justified alignment to regular paragraphs
        if len(txt) > 60 and not txt.startswith("Figure") and not txt.startswith("Table") and not txt.startswith("["):
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.line_spacing = 1.5
            p.paragraph_format.space_after = Pt(6)
            for r in p.runs:
                set_run_font(r, size_pt=12)

    doc.save(DOCX_PATH)
    print("✅ Saved formatted DOCX:", DOCX_PATH)


def update_images_and_fix_aspect_ratios():
    print("🖼️ Updating images and recalculating exact XML aspect ratios...")
    image_replacements = {
        # Diagrams
        "image35.png": os.path.join(ASSETS_DIR, "figure_1_1_problem_context.png"),
        "image36.png": os.path.join(ASSETS_DIR, "figure_1_2_approach_comparison.png"),
        "merged_1.png": os.path.join(ASSETS_DIR, "system_architecture.png"),
        "merged_13.png": os.path.join(ASSETS_DIR, "whole_project_flowchart.png"),
        "merged_2.png": os.path.join(ASSETS_DIR, "conceptual_module_diagram.png"),
        "merged_3.png": os.path.join(ASSETS_DIR, "meal_analysis_activity_diagram.png"),
        "merged_4.png": os.path.join(ASSETS_DIR, "nutrisense_use_case_diagram.png"),
        "merged_5.png": os.path.join(ASSETS_DIR, "backend_frontend_implementation_layout.png"),
        "merged_6.png": os.path.join(ASSETS_DIR, "nutrition_assessment_and_uncertainty.png"),
        # UI Screenshots (Appendix A)
        "image37.png": os.path.join(FIGURES_DIR, "ui_home_dashboard.png"),
        "image38.png": os.path.join(FIGURES_DIR, "ui_analyze_dish5_biryani.png"),
        "image39.png": os.path.join(FIGURES_DIR, "ui_analyze_dish1_multi_item.png"),
        "image40.png": os.path.join(FIGURES_DIR, "ui_analyze_dish2_rice_rasam.png"),
        "image41.png": os.path.join(FIGURES_DIR, "ui_menu_standards.png"),
        "image42.png": os.path.join(FIGURES_DIR, "ui_insights_history.png"),
        "image43.png": os.path.join(FIGURES_DIR, "current_ui_critique.png"),
        "image44.png": os.path.join(FIGURES_DIR, "current_ui_settings.png"),
    }

    # Extract all files from docx
    tmp_dir = "/tmp/docx_unpack"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)

    with zipfile.ZipFile(DOCX_PATH, "r") as z:
        z.extractall(tmp_dir)

    # Replace media files with fresh images
    for target_name, src_path in image_replacements.items():
        dest = os.path.join(tmp_dir, "word", "media", target_name)
        if os.path.exists(src_path):
            shutil.copyfile(src_path, dest)
            print(f"  Replaced {target_name} <- {os.path.basename(src_path)}")

    # Parse relationships to map r:id -> media file
    rels_path = os.path.join(tmp_dir, "word", "_rels", "document.xml.rels")
    rels_tree = ET.parse(rels_path)
    rels_root = rels_tree.getroot()
    r_to_media = {}
    for r in rels_root:
        r_id = r.attrib.get("Id")
        target = r.attrib.get("Target", "")
        if "media/" in target:
            r_to_media[r_id] = os.path.basename(target)

    # Parse word/document.xml to recalculate drawing extents
    doc_xml_path = os.path.join(tmp_dir, "word", "document.xml")
    doc_tree = ET.parse(doc_xml_path)
    doc_root = doc_tree.getroot()

    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    }

    MAX_W_EMU = 5029200  # 5.5 inches
    MAX_H_EMU = 5029200  # 5.5 inches (prevent spilling onto next page)

    drawings_fixed = 0
    for drawing in doc_root.findall(".//w:drawing", ns):
        blip = drawing.find(".//a:blip", ns)
        if blip is None:
            continue
        embed_id = blip.attrib.get(f"{{{ns['r']}}}embed")
        media_name = r_to_media.get(embed_id)
        if not media_name:
            continue

        media_file = os.path.join(tmp_dir, "word", "media", media_name)
        if not os.path.exists(media_file):
            continue

        # Open image to get true pixel dimensions
        with Image.open(media_file) as img:
            w_px, h_px = img.size

        # Compute proportional cx, cy
        aspect = h_px / w_px
        cx = MAX_W_EMU
        cy = round(cx * aspect)

        # If too tall for page, clamp height and scale width
        if cy > MAX_H_EMU:
            cy = MAX_H_EMU
            cx = round(cy / aspect)

        # Update wp:extent
        extent = drawing.find(".//wp:extent", ns)
        if extent is not None:
            extent.attrib["cx"] = str(cx)
            extent.attrib["cy"] = str(cy)

        # Update a:xfrm/a:ext
        a_ext = drawing.find(".//a:xfrm/a:ext", ns)
        if a_ext is not None:
            a_ext.attrib["cx"] = str(cx)
            a_ext.attrib["cy"] = str(cy)

        drawings_fixed += 1
        print(f"  Fixed drawing: {media_name} ({w_px}x{h_px}) -> cx={cx}, cy={cy}")

    doc_tree.write(doc_xml_path, xml_declaration=True, encoding="utf-8")
    print(f"✅ Updated {drawings_fixed} drawing dimensions in document.xml")

    # Repack into DOCX
    with zipfile.ZipFile(DOCX_PATH, "w", zipfile.ZIP_DEFLATED) as z_out:
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, tmp_dir)
                z_out.write(full_path, rel_path)

    print("✅ Repacked final DOCX:", DOCX_PATH)


def compile_pdfs():
    print("📄 Compiling PDFs via LibreOffice headless...")
    cmd = [
        "soffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", REPORT_DIR,
        DOCX_PATH,
    ]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if res.returncode != 0:
        print("LibreOffice error:", res.stderr)
        raise RuntimeError("PDF compilation failed")

    out_pdf = os.path.join(REPORT_DIR, "NutriSense_Roman_Report.pdf")
    fixed_pdf = os.path.join(REPORT_DIR, "NutriSense_Roman_Report_Fixed.pdf")
    updated_pdf = os.path.join(REPORT_DIR, "NutriSense_Roman_Report_Updated.pdf")

    shutil.copyfile(out_pdf, fixed_pdf)
    shutil.copyfile(out_pdf, updated_pdf)
    print("✅ Generated PDFs:")
    print("  ->", out_pdf, f"({os.path.getsize(out_pdf)} bytes)")
    print("  ->", fixed_pdf)
    print("  ->", updated_pdf)


if __name__ == "__main__":
    format_docx()
    update_images_and_fix_aspect_ratios()
    compile_pdfs()
    print("🎉 All operations completed successfully!")
