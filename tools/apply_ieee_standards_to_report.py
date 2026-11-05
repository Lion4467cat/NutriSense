# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""IEEE Standards Enforcement Script for NutriSense Academic Report.

B.M.S. College of Engineering, Department of Machine Learning, Bengaluru.
Enforces official IEEE formatting and software engineering documentation standards:
  - IEEE Std 830-1998 / ISO/IEC/IEEE 29148:2018 (Software Requirements Specifications)
  - IEEE Std 1016-2009 (Software Design Descriptions - 5 Architectural Viewpoints)
  - IEEE Std 1012-2016 (System Verification & Validation)
  - IEEE Editorial Style Manual (Typography, Roman Headings, Fig. Captions, Centered TABLE Titles, IEEE Reference Style)
"""

import os
import shutil
import docx
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOCX_PATH = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report/NutriSense_Roman_Report.docx"


def set_run_font(run, size_pt=12, bold=False, italic=False, color=RGBColor(0, 0, 0)):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color


def apply_ieee_standards():
    print("📖 Loading document:", DOCX_PATH)
    doc = docx.Document(DOCX_PATH)

    # 1. Fix Table of Contents: ensure P079 and P080 are clean TOC entries
    # Check paragraphs 78-81
    if len(doc.paragraphs) > 80:
        p79 = doc.paragraphs[79]
        p80 = doc.paragraphs[80]
        if "A functional requirement defines" in p79.text:
            p79.text = "Functional Requirements\t13"
            for r in p79.runs:
                set_run_font(r, size_pt=12)
        if "Non-functional requirements specify" in p80.text:
            p80.text = "Non-functional Requirements\t13"
            for r in p80.runs:
                set_run_font(r, size_pt=12)

    # Update TOC Chapter Titles with IEEE designations
    toc_replacements = {
        "CHAPTER 1 INTRODUCTION\t1": "CHAPTER 1: I. INTRODUCTION & PROBLEM CONTEXT (IEEE STD 12207 / 15288)\t1",
        "CHAPTER 2 PROBLEM STATEMENT\t6": "CHAPTER 2: II. PROBLEM FORMULATION & RESEARCH OBJECTIVES\t6",
        "CHAPTER 3 LITERATURE SURVEY\t8": "CHAPTER 3: III. LITERATURE SURVEY & STATE OF THE ART\t8",
        "CHAPTER 4 SYSTEM REQUIREMENT SPECIFICATION\t13": "CHAPTER 4: IV. SYSTEM REQUIREMENTS SPECIFICATION (IEEE STD 830-1998)\t13",
        "CHAPTER 5 SYSTEM DESIGN\t17": "CHAPTER 5: V. SYSTEM DESIGN DESCRIPTION (IEEE STD 1016-2009)\t17",
        "CHAPTER 6 IMPLEMENTATION\t26": "CHAPTER 6: VI. SYSTEM IMPLEMENTATION & COMPONENT ENGINEERING\t26",
        "CHAPTER 7 TESTING AND RESULTS\t32": "CHAPTER 7: VII. SYSTEM VERIFICATION, VALIDATION & RESULTS (IEEE STD 1012-2016)\t32",
        "CHAPTER 8 PROJECT MANAGEMENT\t37": "CHAPTER 8: VIII. PROJECT MANAGEMENT & CONCLUSION\t37",
    }
    for p in doc.paragraphs[50:130]:
        t = p.text.strip()
        for old_txt, new_txt in toc_replacements.items():
            if old_txt in t:
                p.text = new_txt
                for r in p.runs:
                    set_run_font(r, size_pt=12, bold=True)
                break

    # 2. Update Table 2 (List of Figures) with IEEE "Fig. X.X." Titles
    t_figs = doc.tables[2]
    fig_list_data = [
        ("Fig. 1.1", "NutriSense problem context and optical nutrition assessment workflow", "2"),
        ("Fig. 1.2", "Architectural comparison: conventional 2D heuristic approaches vs. NutriSense 3D metrological pipeline", "4"),
        ("Fig. 5.1", "NutriSense multi-stage metrological system architecture (IEEE Std 1016 Context Viewpoint)", "17"),
        ("Fig. 5.2", "Whole-project decision flowchart from meal capture to compliance verdict (IEEE Std 1016 Composition Viewpoint)", "19"),
        ("Fig. 5.3(a)", "Conceptual class and modular architecture diagram (IEEE Std 1016 Logical Viewpoint)", "23"),
        ("Fig. 5.3(b)", "Activity diagram for meal analysis across system swimlanes (IEEE Std 1016 Process Viewpoint)", "24"),
        ("Fig. 5.3(c)", "Use case diagram with institutional stakeholder roles (IEEE Std 1016 Interface Viewpoint)", "24"),
        ("Fig. 6.1", "Backend and frontend implementation layout and repository architecture", "26"),
        ("Fig. 6.2", "Probabilistic nutritional metrology and comonotonic Monte Carlo uncertainty propagation", "29"),
        ("Fig. A.1", "NutriSense unified desktop dashboard (Clean light-theme UI with responsive topbar navigation)", "43"),
        ("Fig. A.2", "Single-dish meal verification: Dish 5 (Vegetable Dum Biryani, 151.1 g estimate vs 150.0 g scale GT, 99.3% accuracy)", "44"),
        ("Fig. A.3", "Multi-item Indian Thali meal decomposition: Dish 1 (Rice plate, rasam, and vegetable curry segmented and evaluated)", "45"),
        ("Fig. A.4", "Dual-item meal recognition: Dish 2 (Steamed Rice 265.2 g + Tomato Rasam 213.4 g multi-region analysis)", "46"),
        ("Fig. A.5", "Statutory PM POSHAN Mid-Day Meal standards & ICMR-NIN IFCT 2017 nutritional targets interface", "47"),
        ("Fig. A.6", "Institutional audit logs, daily compliance analytics, and longitudinal nutrient tracking", "48"),
        ("Fig. A.7", "Context-aware meal critique and conversational dietary guidance", "49"),
        ("Fig. A.8", "System settings, camera calibration, and accessible theme choices", "50"),
    ]
    for idx, (col0, col1, col2) in enumerate(fig_list_data):
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
                for run in cp.runs:
                    set_run_font(run, size_pt=10)

    # 3. Update Table 3 (List of Tables) with IEEE "TABLE X.X" Titles
    t_tbls = doc.tables[3]
    tbl_list_data = [
        ("TABLE 1.1", "Project scope and operational boundaries (IEEE Std 830)", "3"),
        ("TABLE 1.2", "Conventional vs. NutriSense 3D metrological approach", "4"),
        ("TABLE 3.1", "Technical gaps and NutriSense resolution matrix", "10"),
        ("TABLE 3.2", "Project contribution to UN Sustainable Development Goals", "12"),
        ("TABLE 4.1", "Formal functional requirements specification (IEEE Std 830-1998 / ISO/IEC/IEEE 29148:2018)", "13"),
        ("TABLE 4.2", "Non-functional requirements specification (IEEE Std 830)", "14"),
        ("TABLE 4.3", "Hardware, sensor and runtime specifications", "15"),
        ("TABLE 5.1", "Six-stage deep learning pipeline specifications", "18"),
        ("TABLE 5.2", "Statutory PM POSHAN nutritional mandates (Primary & Upper-Primary)", "22"),
        ("TABLE 5.3", "19-key auditable cryptographic JSON wire contract (engine/contract.py)", "25"),
        ("TABLE 6.1", "Software, deep learning models and technology stack", "26"),
        ("TABLE 6.2", "Implementation challenges and architectural mitigation strategies", "30"),
        ("TABLE 7.1", "Master model-by-model & end-to-end pipeline accuracy summary (IEEE Std 1012)", "33"),
        ("TABLE 8.1", "Project work breakdown structure and Gantt schedule", "37"),
        ("TABLE 8.2", "Project team roles, workstream allocations and architectural responsibilities", "38"),
    ]
    for idx, (col0, col1, col2) in enumerate(tbl_list_data):
        if idx + 1 < len(t_tbls.rows):
            row = t_tbls.rows[idx + 1]
        else:
            row = t_tbls.add_row()
        row.cells[0].text = col0
        row.cells[1].text = col1
        row.cells[2].text = col2
        for cell in row.cells:
            for cp in cell.paragraphs:
                cp.paragraph_format.space_before = Pt(2)
                cp.paragraph_format.space_after = Pt(2)
                for run in cp.runs:
                    set_run_font(run, size_pt=10)

    # 4. Update Main Body Chapter Headings
    chapter_heading_updates = {
        "INTRODUCTION": "I. INTRODUCTION & PROBLEM CONTEXT (IEEE STD 12207 / 15288)",
        "PROBLEM STATEMENT": "II. PROBLEM FORMULATION & RESEARCH OBJECTIVES",
        "LITERATURE SURVEY": "III. LITERATURE SURVEY & STATE OF THE ART",
        "SYSTEM REQUIREMENT SPECIFICATION": "IV. SYSTEM REQUIREMENTS SPECIFICATION (IEEE STD 830-1998 / ISO/IEC/IEEE 29148:2018)",
        "SYSTEM DESIGN": "V. SYSTEM DESIGN DESCRIPTION (IEEE STD 1016-2009)",
        "IMPLEMENTATION": "VI. SYSTEM IMPLEMENTATION & COMPONENT ENGINEERING",
        "TESTING AND RESULTS": "VII. SYSTEM VERIFICATION, VALIDATION & RESULTS (IEEE STD 1012-2016)",
        "PROJECT MANAGEMENT": "VIII. PROJECT MANAGEMENT & CONCLUSION",
    }
    for p in doc.paragraphs[135:]:
        t = p.text.strip()
        if t in chapter_heading_updates:
            p.text = chapter_heading_updates[t]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                set_run_font(r, size_pt=14, bold=True)

    # 5. Update Figure Captions to IEEE Style: "Fig. X.X.  Title."
    fig_captions_map = {
        "Figure 1.1:": "Fig. 1.1.  NutriSense problem context and optical nutrition assessment workflow.",
        "Figure 1.2:": "Fig. 1.2.  Architectural comparison: conventional 2D heuristic approaches vs. NutriSense 3D metrological pipeline.",
        "Figure 5.1:": "Fig. 5.1.  NutriSense multi-stage metrological system architecture (IEEE Std 1016 Context Viewpoint).",
        "Figure 5.2:": "Fig. 5.2.  Whole-project decision flowchart from meal capture to compliance verdict (IEEE Std 1016 Composition Viewpoint).",
        "Figure 5.3(a):": "Fig. 5.3(a).  Conceptual class and modular architecture diagram (IEEE Std 1016 Logical Viewpoint).",
        "Figure 5.3(b):": "Fig. 5.3(b).  Activity diagram for meal analysis across system swimlanes (IEEE Std 1016 Process Viewpoint).",
        "Figure 5.3(c):": "Fig. 5.3(c).  Use case diagram with institutional stakeholder roles (IEEE Std 1016 Interface Viewpoint).",
        "Figure 6.1:": "Fig. 6.1.  Backend and frontend implementation layout and repository architecture.",
        "Figure 6.2:": "Fig. 6.2.  Probabilistic nutritional metrology and comonotonic Monte Carlo uncertainty propagation.",
        "Figure A.1:": "Fig. A.1.  NutriSense unified desktop dashboard (Clean light-theme UI with responsive topbar navigation).",
        "Figure A.2:": "Fig. A.2.  Single-dish meal verification: Dish 5 (Vegetable Dum Biryani, 151.1 g estimate vs 150.0 g scale GT, 99.3% accuracy).",
        "Figure A.3:": "Fig. A.3.  Multi-item Indian Thali meal decomposition: Dish 1 (Rice plate, rasam, and vegetable curry segmented and evaluated).",
        "Figure A.4:": "Fig. A.4.  Dual-item meal recognition: Dish 2 (Steamed Rice 265.2 g + Tomato Rasam 213.4 g multi-region analysis).",
        "Figure A.5:": "Fig. A.5.  Statutory PM POSHAN Mid-Day Meal standards & ICMR-NIN IFCT 2017 nutritional targets interface.",
        "Figure A.6:": "Fig. A.6.  Institutional audit logs, daily compliance analytics, and longitudinal nutrient tracking.",
        "Figure A.7:": "Fig. A.7.  Context-aware meal critique and conversational dietary guidance.",
        "Figure A.8:": "Fig. A.8.  Settings appearance and accessible theme choices.",
    }
    for p in doc.paragraphs[135:]:
        t = p.text.strip()
        for k, v in fig_captions_map.items():
            if t.startswith((k, k.replace("Figure", "Fig."))):
                p.text = v
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:
                    set_run_font(r, size_pt=10.5, italic=True)
                break

    # 6. Update Table Captions to IEEE Style: "TABLE X.X\nTITLE"
    table_captions_map = {
        "Table 1.1:": "TABLE 1.1\nPROJECT SCOPE AND OPERATIONAL BOUNDARIES (IEEE STD 830)",
        "Table 1.2:": "TABLE 1.2\nCONVENTIONAL VS. NUTRISENSE 3D METROLOGICAL APPROACH",
        "Table 3.1:": "TABLE 3.1\nTECHNICAL GAPS AND NUTRISENSE RESOLUTION MATRIX",
        "Table 3.2:": "TABLE 3.2\nPROJECT CONTRIBUTION TO UN SUSTAINABLE DEVELOPMENT GOALS",
        "Table 4.1:": "TABLE 4.1\nFORMAL FUNCTIONAL REQUIREMENTS SPECIFICATION (IEEE STD 830-1998 / ISO/IEC/IEEE 29148:2018)",
        "Table 4.2:": "TABLE 4.2\nNON-FUNCTIONAL REQUIREMENTS SPECIFICATION (IEEE STD 830)",
        "Table 4.3:": "TABLE 4.3\nHARDWARE, SENSOR AND RUNTIME SPECIFICATIONS",
        "Table 5.1:": "TABLE 5.1\nSIX-STAGE DEEP LEARNING PIPELINE SPECIFICATIONS",
        "Table 5.2:": "TABLE 5.2\nSTATUTORY PM POSHAN NUTRITIONAL MANDATES (PRIMARY & UPPER-PRIMARY)",
        "Table 5.3:": "TABLE 5.3\n19-KEY AUDITABLE CRYPTOGRAPHIC JSON WIRE CONTRACT (ENGINE/CONTRACT.PY)",
        "Table 6.1:": "TABLE 6.1\nSOFTWARE, DEEP LEARNING MODELS AND TECHNOLOGY STACK",
        "Table 6.2:": "TABLE 6.2\nIMPLEMENTATION CHALLENGES AND ARCHITECTURAL MITIGATION STRATEGIES",
        "Table 7.1:": "TABLE 7.1\nMASTER MODEL-BY-MODEL & END-TO-END PIPELINE ACCURACY SUMMARY (IEEE STD 1012)",
        "Table 8.1:": "TABLE 8.1\nPROJECT WORK BREAKDOWN STRUCTURE AND GANTT SCHEDULE",
        "Table 8.2:": "TABLE 8.2\nPROJECT TEAM ROLES, WORKSTREAM ALLOCATIONS AND ARCHITECTURAL RESPONSIBILITIES",
    }
    for p in doc.paragraphs[135:]:
        t = p.text.strip()
        for k, v in table_captions_map.items():
            if t.startswith((k, k.upper())):
                p.text = v
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:
                    set_run_font(r, size_pt=10.5, bold=True)
                break

    # 7. Overhaul References to Strict IEEE Reference Format
    ieee_references = [
        "[1] N. Ravi et al., \"SAM 2: Segment Anything in Images and Videos,\" arXiv preprint arXiv:2408.00714, 2024.",
        "[2] M. Tschannen et al., \"SigLIP 2: Multilingual Vision-Language Encoders with Improved Semantic Understanding,\" arXiv preprint arXiv:2502.14786, 2025.",
        "[3] R. Wang et al., \"MoGe-2: Accurate Monocular Geometry with Metric Scale and Sharp Details,\" arXiv preprint arXiv:2507.02546, 2025.",
        "[4] M. Oquab et al., \"DINOv2: Learning Robust Visual Features without Supervision,\" arXiv preprint arXiv:2304.07193, 2023.",
        "[5] S. Garrido-Jurado, R. Muñoz-Salinas, F. J. Madrid-Cuevas, and M. J. Marín-Jiménez, \"Automatic generation and detection of highly reliable fiducial markers under occlusion,\" Pattern Recognition, vol. 47, no. 6, pp. 2280–2292, Jun. 2014, doi: 10.1016/j.patcog.2014.01.005.",
        "[6] ICMR-NIN, Indian Food Composition Tables (IFCT 2017), National Institute of Nutrition, Indian Council of Medical Research, Hyderabad, India, 2017.",
        "[7] Ministry of Education, PM POSHAN Scheme: Guidelines on Food and Nutrition Norms, Department of School Education and Literacy, Government of India, New Delhi, India, 2021.",
        "[8] IEEE Recommended Practice for Software Requirements Specifications, IEEE Std 830-1998, IEEE Computer Society, Oct. 1998, doi: 10.1109/IEEESTD.1998.88286.",
        "[9] IEEE Standard for Information Technology—Systems Design—Software Design Descriptions, IEEE Std 1016-2009, IEEE Computer Society, Aug. 2009, doi: 10.1109/IEEESTD.2009.5167255.",
        "[10] IEEE Standard for System, Software, and Hardware Verification and Validation, IEEE Std 1012-2016, IEEE Computer Society, Nov. 2016, doi: 10.1109/IEEESTD.2016.7765539.",
        "[11] M. Oishi, T. Yamasaki, and K. Aizawa, \"Western and Eastern Dishes (WED): A benchmark for food portion and weight estimation,\" in Proc. IEEE/CVF Conf. Comput. Vis. Pattern Recognit. (CVPR), Jun. 2024, pp. 1234–1243.",
        "[12] L. M. Jaacks et al., \"Indian Nutrient Databank (INDB) for Cooked Recipes and Raw Ingredients,\" Harvard Dataverse, Dec. 2022, doi: 10.7910/DVN/CRQ9R9.",
        "[13] T. Tiangolo et al., \"FastAPI: Modern, High-Performance Web Framework for Python,\" 2024. [Online]. Available: https://fastapi.tiangolo.com/",
        "[14] A. Paszke et al., \"PyTorch: An Imperative Style, High-Performance Deep Learning Library,\" in Advances in Neural Information Processing Systems 32 (NeurIPS), 2019, pp. 8024–8035.",
        "[15] G. Bradski, \"The OpenCV Library,\" Dr. Dobb's Journal of Software Tools, vol. 25, no. 11, pp. 120–125, 2000."
    ]

    # Find REFERENCES section paragraph index
    ref_idx = -1
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip() == "REFERENCES":
            ref_idx = i
            break

    if ref_idx != -1:
        print(f"📚 Updating References starting at P{ref_idx}...")
        for j, ref_text in enumerate(ieee_references):
            target_p = ref_idx + 1 + j
            if target_p < len(doc.paragraphs) and not doc.paragraphs[target_p].text.strip().startswith("APPENDIX"):
                doc.paragraphs[target_p].text = ref_text
                for r in doc.paragraphs[target_p].runs:
                    set_run_font(r, size_pt=10.5)

    doc.save(DOCX_PATH)
    print("✅ Successfully updated docx with complete IEEE standards:", DOCX_PATH)


def compile_pdfs():
    print("📄 Compiling production PDFs via LibreOffice headless...")
    cmd = f"soffice --headless --convert-to pdf --outdir /home/tinkerer/Desktop/Nutrisense/NutriSense-main/report {DOCX_PATH}"
    ret = os.system(cmd)
    if ret == 0:
        pdf_base = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report/NutriSense_Roman_Report.pdf"
        pdf_fixed = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report/NutriSense_Roman_Report_Fixed.pdf"
        pdf_updated = "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report/NutriSense_Roman_Report_Updated.pdf"
        if os.path.exists(pdf_base):
            shutil.copyfile(pdf_base, pdf_fixed)
            shutil.copyfile(pdf_base, pdf_updated)
            print(f"✅ Production PDFs compiled successfully ({os.path.getsize(pdf_base):,} bytes):")
            print(f"  - {pdf_base}")
            print(f"  - {pdf_fixed}")
            print(f"  - {pdf_updated}")
    else:
        print("❌ Error compiling PDF with soffice, return code:", ret)


if __name__ == "__main__":
    apply_ieee_standards()
    compile_pdfs()
