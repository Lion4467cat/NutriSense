# WHO-derived daily goal values (energy + protein) by age, sex and physical activity level

**Status:** research only — no decisions made here; see §8 "Open questions (one line each)".
**Prepared:** 2026-10-28 (all URLs fetched that day — verification log below). Feeds a future `data/goals_who.yaml`. Independent-sources comparison (§6, sources S11–S19) added the same day.
**Currency check:** performed 2026-10-28 — **no superseding publication; see §0**.

## 0. Currency check (2026-10-28) and latest-wins statement

**Result: no FAO/WHO/UNU publication from 2008–2026 supersedes the energy values (S1, 2004) or the protein values (S2, 2007). Both remain the operative world references.** Evidence, per report:

**Energy (S1, 2004 — still current).** (a) FAO's official undernourishment (PoU/MDER) methodology states it derives requirements "based on the report of a Joint FAO/WHO/UNU Expert Consultation on human energy requirements (…y5686e…) released in 2004" (S5, fetched — quote at lines 56–58 of its text layer). (b) FAO's live PoU pages and the *SOFI 2026* edition (published 2026) still compute MDER from that same consultation framework (S10). (c) An **update is in progress but has published no values**: a FAO/WHO/IAEA consultancy meeting (IAEA Vienna, June 2024) with 15 nutrition/energy-metabolism experts reviewed S1, flagged concerns (global obesity, BMR variation across populations, declining BMR, LMIC data gaps, >90 y, pregnancy/lactation) and "formulated a roadmap … to update estimates of energy requirement"; a series of papers on a "paradigm shift" and further consultations involving dietitians/clinicians were announced, fed by IAEA's DLW database (~12 000 measurements) and a 2022 IAEA CRP on pre-adolescents/adolescents in LMICs (S6, fetched). **Standing instruction: re-run this currency check before any production use of `data/goals_who.yaml`; if FAO/WHO/UNU publishes revised energy values, re-research and replace.**

**Protein (S2, 2007 — still current).** No newer FAO/WHO/UNU protein-requirements consultation exists (2026-10-28 searches). Three footnote-level updates, none changing the g/kg requirement values:
- **FN1 — quality scoring method (adopted, affects gap G8 only):** FAO FNP 92 (2013, report of the Auckland 31 March–2 April 2011 FAO expert consultation; S7, fetched) recommends **DIAAS replace PDCAAS** for protein-quality evaluation. This changes how a diet's effective quality score is computed, not the requirement values.
- **FN2 — requirement debate (not adopted):** IAAO-method studies and 2-phase reanalyses propose higher adult protein requirements (verified per-study values incl. older adults in §6.1, S16–S19; Matsumoto 2023 scoping review + Elango 2023 editorial, *J. Nutrition*; contested by Millward 2024). A 2024–11 US AHRQ systematic review informing the (still-2005) US DRIs concluded evidence 2000–2024 is "inconclusive" (S9). National/scientific-debate level — **not adopted by WHO/FAO/UNU, therefore not substituted here.**
- **FN3 — related food-based guideline (in development):** WHO guideline on *optimal intake of animal-source foods* (GDG scope set Nov 2024; public scope call closed 2025-09-01; S8, fetched). It will not revise requirement values; not yet published.

**National-level updates (documented, not substituted — see §6):** the US energy DRIs **were** revised in 2023 (NASEM, DLW-based equations — S12); US protein DRIs remain the 2005 IOM values (S11; AHRQ 2024-11 review found the 2000–2024 evidence "inconclusive", S9); EFSA's EU DRVs date from 2012 (protein, S13) and 2013 (energy, S14) and adopt the WHO/FAO/UNU 2007 protein method unchanged. None supersedes WHO/FAO/UNU globally; §6 compares them against the WHO values. They stay non-operative for the YAML unless the owner decides otherwise (G12/G13).

**Growth reference:** WHO 2007 Reference (S3) still current for 5–19 y (WHO tools pages live 2026-10-28).

**Latest-wins policy applied:** where a newer WHO/FAO/UNU decision exists (FN1) it is footnoted into the affected gap; where only national or contested science exists (FN2, and the national reference systems S11–S14) it is recorded, compared in §6, but **not** substituted, because this file's authority chain is WHO/FAO/UNU official > national bodies > journal debate.

## Source register

Basis tokens used throughout this file: `S#·year·table/section·direct` (number printed in the source) or `·derived` (computed in this file; derivation shown inline). URL + access date for every code live in this register and the verification log; **all access dates are 2026-10-28**.

| Code | Source | Year | URL(s) | How verified 2026-10-28 |
|---|---|---|---|---|
| S1 | FAO/WHO/UNU. *Human energy requirements. Report of a Joint FAO/WHO/UNU Expert Consultation* (Rome 2001; FAO Food and Nutrition Technical Report Series 1) | 2004 (web ed.) | <https://www.fao.org/3/y5686e/y5686e00.htm>; ch. 4: <https://www.fao.org/3/y5686e/y5686e06.htm>; ch. 5: <https://www.fao.org/3/y5686e/y5686e07.htm> + <https://www.fao.org/3/y5686e/y5686e08.htm> | full text fetched (webfetch) |
| S2 | WHO/FAO/UNU. *Protein and amino acid requirements in human nutrition* (WHO Technical Report Series 935) | 2007 | <https://iris.who.int/handle/10665/43411>; PDF: <https://iris.who.int/server/api/core/bitstreams/b7c5ec43-bc59-4b38-b702-3f0e96a06fa1/content> | full text fetched (curl → pdftotext) |
| S3 | WHO. *WHO 2007 growth reference* — weight-for-age 5–10 y (cross-check of child medians only) | 2007 | <https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators/weight-for-age-5to10-years>; boys/girls z-tables + simplified tables under `cdn.who.int/media/docs/default-source/child-growth/growth-reference-5-19-years/weight-for-age-(5-10-years)/` | page + tables fetched |
| S4 | WHO. *Measuring change in nutritional status* | 1983 | — (not fetched; the weight source S1 itself cites in Tables 4.5/4.6 footnotes) | via S1 only |
| S5 | FAO. *Updating the minimum dietary energy requirements* (PoU methodology metadata) | 2008/2009 | <https://www.fao.org/fileadmin/templates/ess/documents/food_security_statistics/metadata/undernourishment_methodology.pdf> | fetched (curl → pdftotext) |
| S6 | IAEA. "Understanding Human Calorie Needs: IAEA Supports FAO and WHO" | 2024-08-28 | <https://www.iaea.org/newscenter/news/understanding-human-calorie-needs-iaea-supports-fao-and-who> | fetched (webfetch; curl gets 403 bot-block) |
| S7 | FAO. *Dietary protein quality evaluation in human nutrition. Report of an FAO Expert Consultation* (Auckland, 31 March–2 April 2011) = Food and Nutrition Paper 92 | 2013 | <https://www.fao.org/ag/humannutrition/35978-02317b979a686a57aa4593304ffc17f06.pdf> | fetched (curl → pdftotext; DIAAS/PDCAAS chapters confirmed) |
| S8 | WHO. "Call for comment on the scope of the WHO guideline on optimal intake of animal-source foods" | 2025-09-01 | <https://www.who.int/news-room/articles-detail/call-for-comment-on-the-scope-of-the-who-guideline-on-optimal-intake-of-animal-source-foods> | fetched (webfetch) |
| S9 | AHRQ. *Evaluation of Dietary Protein and Amino Acid Requirements: A Systematic Review* (Burstad et al.; PROSPERO CRD42023446618) | 2024-11 | <https://doi.org/10.23970/ahrqepcsrproteinamino> → <https://effectivehealthcare.ahrq.gov/products/dietary-protein-intake/research>; report PDF: <https://effectivehealthcare.ahrq.gov/sites/default/files/related_files/dietary-protein-intake.pdf> | DOI resolution verified; abstract + report tables (incl. its Table 5 on the one child/adolescent study) via search crawl — direct PDF fetch is bot-blocked (0 bytes) |
| S10 | FAO/IFAD/UNICEF/WFP/WHO. *SOFI 2026*, supplementary material to ch. 2 (PoU/MDER framework unchanged) | 2026 | <https://openknowledge.fao.org/server/api/core/bitstreams/fbd7e989-deb5-415b-a5b9-bfa08269b9d7/content> | HTTP 200; content seen via search crawl |
| S11 | IOM (US Standing Committee on the Scientific Evaluation of Dietary Reference Intakes). *Dietary Reference Intakes for Energy, Carbohydrate, Fiber, Fat, Fatty Acids, Cholesterol, Protein, and Amino Acids* | 2005 | NAP catalog: <https://nap.nationalacademies.org/catalog/10490>; full PDF mirror fetched: cambridgefoodscience.org (IOM 2005 DRI book, 5 150 967 B) | mirror PDF fetched (→ pdftotext): EER equations + PA coefficients + reference tables 5-8/5-9, boys' EER table 5-20, girls' 3-y row 5-21, adult example table 5-22, and the protein-RDA text read |
| S12 | NASEM. *Dietary Reference Intakes for Energy* | 2023 (pub. 2023-01-17) | <https://nap.nationalacademies.org/catalog/26818>; ch. 5: <https://nap.nationalacademies.org/read/26818/chapter/7>; doi <https://doi.org/10.17226/26818>; Bookshelf NBK588659 / ch. 5 NBK591021 | ch. 5 fetched (webfetch): Tables 5-3 (PAL percentile cutoffs), 5-15 (children/adolescents equations + energy-cost-of-growth footnotes), 5-16 (adult equations), 5-17/5-18 (pregnancy/lactation) read. NCBI Bookshelf mirror blocked (reCAPTCHA) |
| S13 | EFSA NDA Panel. "Scientific Opinion on Dietary Reference Values for protein" (EFSA Journal 2012;10(2):2557) | 2012 (version replaced 5 Feb 2015) | doi <https://doi.org/10.2903/j.efsa.2012.2557>; official DRV summary tables: <https://www.efsa.europa.eu/sites/default/files/assets/DRV_Summary_tables_jan_17.pdf> | opinion PDF mirror fetched (1 629 907 B → pdftotext): adult AR/PRI incl. ≥60 y, child/adolescent AR Tables 9–10, PRI summary Table 12 (per-year + reference weights), pregnancy/lactation read. Wiley/unimi.it landing pages return HTML stubs — the mirror PDF is the verified copy |
| S14 | EFSA NDA Panel. "Scientific Opinion on Dietary Reference Values for energy" (EFSA Journal 2013;11(1):3005) | 2013 | doi <https://doi.org/10.2903/j.efsa.2013.3005>; AR table verified from the official summary tables (S13 row URL, version 4, September 2017) | summary-tables PDF fetched (343 731 B → pdftotext): Table 1 energy ARs read in full (incl. `1 MJ = 238.83 kcal`, PAL definitions, ≥80 y exclusion, pregnancy/lactation additions). Full opinion's abstract/method via search crawl (Henry 2005 REE × PAL; EU survey heights; BMI 22 weights; WHO growth standards for children) |
| S15 | Pontzer Y, Yamada Y, Sagayama H, et al. "Daily energy expenditure through the human life course", *Science* 373(6557):808–812 | 2021 | doi <https://doi.org/10.1126/science.abe5017>; PMC8370708 (blocked) | abstract + key methods/results via science.org full-text crawl |
| S16 | Elango R, Humayun MA, Ball RO, Pencharz PB. "Protein requirement of healthy school-age children determined by the indicator amino acid oxidation method", *Am J Clin Nutr* (online 2011-11-03) | 2012 | doi <https://doi.org/10.3945/ajcn.111.012815>; PMID 22049165; <https://ajcn.nutrition.org/article/S0002-9165(23)02514-5/fulltext> | abstract in full via search crawl (ajcn.nutrition.org direct fetch = 403); same study's data quoted in S9 (report Table 5) and S19 |
| S17 | Rafii M, Chapman K, Owens J, Elango R, Campbell WW, Ball RO, et al. "Dietary protein requirement of female adults >65 years determined by the indicator amino acid oxidation technique…", *J Nutr* (online 2014-10-16) | 2015 | doi <https://doi.org/10.3945/jn.114.197517> | abstract (methods + results) via jn.nutrition.org crawl |
| S18 | Rafii M, Chapman K, Elango R, Campbell WW, Ball RO, Pencharz PB. "Dietary protein requirement of men >65 years old determined by the indicator amino acid oxidation technique…", *J Nutr* (online 2016-03-10) | 2016 | doi <https://doi.org/10.3945/jn.115.225631> | abstract + results (incl. figure caption values) via jn.nutrition.org crawl |
| S19 | Courtney-Martin G, Ball RO, Pencharz PB, Elango R. "Protein requirements during aging", *Nutrients* 8(8):492 | 2016 | doi <https://doi.org/10.3390/nu808492> | abstract + Table 1 (IAAO values incl. young men, elderly; 2-phase NB reanalysis) via mdpi.com crawl |

## Verification log (2026-10-28)

- S1: all three chapter URLs fetched full-text; Tables 4.2/4.3 (moderate per-year), 4.5/4.6 (light/moderate/heavy per-year), 5.2 (Schofield), 5.3 (PAL classes), 5.4–5.9 (adult requirements) read from the fetched text.
- S2: PDF fetched via IRIS DSpace REST API chain (item uuid `78c03092-bcc2-40f5-90d1-60641ecdf6ea` → bundles → bitstream uuid `b7c5ec43-bc59-4b38-b702-3f0e96a06fa1`); `pdftotext -layout`; Tables 33a/b, 46, 47, 48 and sections 7.10, 9.3.3, 13.6, 14.1–14.7 read.
- S3: indicator page + boys/girls weight-for-age tables fetched; medians extracted for the §7 cross-check.
- S5, S6, S7, S8: fetched as listed in the register. S9, S10, S15, S16, S17, S18, S19: DOI/live-URL verified; content from search crawl (S9's abstract quoted in §0/FN2; S15–S19 content in §6).
- S11: full-book PDF mirror fetched (5 150 967 B; pdftotext): EER equations for men/women 19+ and children (3–8 y and 9–18 y forms) with PA coefficients and energy-deposition add-ons (+20 kcal/d ages 3–8, +25 ages 9–18); reference Tables 5-8/5-9 (Kuczmarski 2000 medians); boys' EER Table 5-20 rows; girls' 3-y row of Table 5-21; adult example Table 5-22; protein RDA text (1–3 y 1.05 g/kg/d = 13 g; 4–8 y 0.95 = 19 g; 9–13 y 0.95 = 34 g; 14–18 y 0.85 = 52 g m / 46 g f; 19–30/31–50/51–70/>70 y all 0.80 g/kg/d = 56 g m / 46 g f). A footnote documents a prepublication correction 0.88 → 0.87 g/kg/d.
- S12: NAP chapter 5 fetched; NASEM 2023 PAL-percentile cutoffs (Table 5-3), children/adolescents equations (Table 5-15, with energy-cost-of-growth footnotes a–c), adult equations (Table 5-16), pregnancy/lactation equations (Tables 5-17/5-18, registered only) read. DLW database composition (8 600 obs; IAEA v3.6.1 = 5 717 after exclusions + SOLNAS 380 + IOM 2 283 + CNRC 220) and the "general population" referent statement read. NCBI Bookshelf blocked (reCAPTCHA). A dataset-composition claim about excluded low-income-country studies was **not** re-verified in the primary text and is therefore **not asserted** in this file.
- S13: mirror PDF fetched (1 629 907 B; pdftotext): adult AR 0.66 / PRI 0.83 g/kg/d (incl. ≥60 y, 133 mg N/kg/d, 47 % efficiency, CV 12 %, "2× PRI regularly consumed" safety note); child/adolescent average-requirement Tables 9–10 (0.69–0.75 g/kg/d per year); PRI summary Table 12 (per-year 0.85–0.92 g/kg/d for ages 5–10; 18–59 y and ≥60 y 0.83; reference weights: adults 74.6/62.1 kg from SCF 1993, children van Buuren 2012 EU medians); pregnancy +1/+9/+28 g/d, lactation +19/+13 g/d. The 2015-02-05 "replaces the earlier version" editorial note is on the PDF.
- S14: official EFSA DRV summary tables (v4, 2017-09) fetched (343 731 B; pdftotext): energy Table 1 read in full — per-year ARs for 1–17 y (1–3 y at PAL 1.6 only; 4–9 y at 1.4/1.6/1.8; 10–17 y at 1.6/1.8/2.0) and adults 18–79 y in 10-year bands at 1.4/1.6/1.8/2.0; no ARs for ≥80 y; footnote `1 MJ = 238.83 kcal`; PAL mapping "1.4 low active (sedentary), 1.6 moderately active, 1.8 active, 2.0 very active" (EFSA NDA Panel 2013); pregnancy +0.29/+1.1/+2.1 MJ, lactation +2.1 MJ. The full opinion (method text) is search-crawl only; the unimi.it full-PDF link was not fetched (landing stubs).
- Computed values in §6: produced by a python3 script (standard library only) from the verified equations/tables; every `derived` entry is reproducible from the equations quoted in §3 (S1), §6 (S11/S12) and the printed tables (S13/S14).
- **Dead URLs worked around:** `whqlibdoc.who.int/trs/WHO_TRS_935_eng.pdf` (gone), `www.who.int/publications/i/item/9241209356` (404), `apps.who.int/iris/...` legacy paths (Angular SPA shell, 755-byte HTML, no content) → the IRIS DSpace API content URL above is the working canonical for S2. Also 404: `fao.org/4/a0075e/a0075e.pdf` (archive-code guess for FNP 92) → the `/ag/humannutrition/35978-…pdf` URL is the working one. Blocked hosts with no workaround: ajcn.nutrition.org (403), jn.nutrition.org (403 on direct fetch; crawl-readable), PMC/PubMed (reCAPTCHA), AHRQ report PDF direct fetch (0 bytes).
- No §3–§5 values are taken from secondary summaries; every number traces to S1 or S2 (or S3 for the cross-check weights). §6's comparison values trace to S11–S19 as marked; nothing there comes from unverified secondary summaries.

## 1. What these numbers are — and are not

S1's energy values and S2's protein values are **average requirements for healthy, well-nourished populations**, not individual prescription doses, and not upper limits. S1 states explicitly: "the energy requirements and dietary energy recommendations in this report are to be applied to population groups and not to individuals" (S1·2004·§5.4.1·direct). Energy requirement = total energy expenditure (TEE, measured by DLW/HRM in 801 boys + 808 girls for children; factorial BMR × PAL for adults) **plus** ~2 kcal per gram of weight gain for growth in children (S1·2004·§4.3–4.4·direct). S2's protein "safe level of intake" is the 97.5th percentile of the requirement distribution (mean 0.66 g/kg/d + 1.96 SD, assuming 12% CV) — deliberately conservative for an individual ("will have a very low (<2.5%) risk of deficiency", S2·2007·§14.1.1·direct), and it assumes proteins of quality score 1.0 (PDCAAS-corrected diets lower it further, S2·2007·§14.7·direct; scoring-method successor = DIAAS, FN1). Neither report sets a safe upper limit for protein in children/adults (S2·2007·§13.6/§14.2·direct). For NutriSense's "Daily goal": the WHO numbers are a *defensible default floor/target for an average healthy person of that age/sex/activity band*, and any personal override (actual weight, real activity) is legitimate and expected.

## 2. The PAL framework (needed to read both tables)

S1·2004·Table 5.3·direct classifies lifestyles by PAL (= 24-h TEE ÷ BMR) into **sedentary/light 1.40–1.69, active/moderate 1.70–1.99, vigorous 2.00–2.40**. Adult requirement tables (S1·2004·Tables 5.4–5.9·direct) tabulate factors **1.45, 1.60, 1.75, 1.90, 2.05, 2.20**; the report's own worked example uses the **mid-point of "moderately active" = 1.85** (S1·2004·§5.4.1·direct), and its lifestyle worked examples give PAL ≈ 1.53 (sedentary), 1.76 (active), 2.25 (vigorous) (S1·2004·§5.1/Table 5.1·direct). For children, S1 does **not** reuse adult PAL anchors: moderate-activity child requirements were derived from measured TEE (child PAL ≈ 1.5–1.9 by age); "light" = −15% and "vigorous" (labelled "heavy" in Tables 4.5/4.6) = +15% of the moderate value, applicable **from age 6 up** (S1·2004·§4.4.2–4.4.3·direct). The anchor set "1.4 / 1.6 / 1.8 / 2.0" quoted in the project brief does not appear in S1 as category anchors — see gap G2. (It **is**, however, EFSA's adult anchor set — S14·2013·direct — see §6.1.)

## 3. Energy table — daily energy requirement (kcal/day)

School-age bands are **project bands aggregated by equal-weight mean of S1's single-year rows** (S1 prints single-year rows only); adults use S1 Tables 5.4–5.9 **directly** at a stated representative mean weight (the report's tables vary weight; the weight is an assumption — gap G4). Bands = inclusive single-year rows: 5–8 = rows 5–6/6–7/7–8/8–9; 9–11 = 9–10/10–11/11–12; 12–14 = 12–13/13–14/14–15; 15–17 = 15–16/16–17/17–18 (S1 row "7–8" = median at 7.5 y).

| Age band | Sex | PAL level | Energy (kcal/day) | Basis |
|---|---|---|---|---|
| 5–8 | boys | light (−15%) | 1 450 | S1·2004·T4.5 rows 6–7/7–8/8–9·derived (mean of 1 350/1 450/1 550; no light value for age 5 — gap G6) |
| 5–8 | boys | moderate | 1 645 | S1·2004·T4.5 rows 5–6/6–7/7–8/8–9·derived (mean of 1 475/1 575/1 700/1 825) |
| 5–8 | boys | vigorous (+15%) | 1 950 | S1·2004·T4.5 rows 6–7/7–8/8–9·derived (mean of 1 800/1 950/2 100; gap G6) |
| 5–8 | girls | light (−15%) | 1 335 | S1·2004·T4.6 rows 6–7/7–8/8–9·derived (mean of 1 225/1 325/1 450; gap G6) |
| 5–8 | girls | moderate | 1 500 | S1·2004·T4.6 rows 5–6/6–7/7–8/8–9·derived (mean of 1 325/1 425/1 550/1 700) |
| 5–8 | girls | vigorous (+15%) | 1 790 | S1·2004·T4.6 rows 6–7/7–8/8–9·derived (mean of 1 650/1 775/1 950; gap G6) |
| 9–11 | boys | light | 1 835 | S1·2004·T4.5 rows 9–10/10–11/11–12·derived (mean of 1 675/1 825/2 000) |
| 9–11 | boys | moderate | 2 160 | S1·2004·T4.5 rows 9–10/10–11/11–12·derived (mean of 1 975/2 150/2 350) |
| 9–11 | boys | vigorous | 2 485 | S1·2004·T4.5 rows 9–10/10–11/11–12·derived (mean of 2 275/2 475/2 700) |
| 9–11 | girls | light | 1 700 | S1·2004·T4.6 rows 9–10/10–11/11–12·derived (mean of 1 575/1 700/1 825) |
| 9–11 | girls | moderate | 2 000 | S1·2004·T4.6 rows 9–10/10–11/11–12·derived (mean of 1 850/2 000/2 150) |
| 9–11 | girls | vigorous | 2 300 | S1·2004·T4.6 rows 9–10/10–11/11–12·derived (mean of 2 125/2 300/2 475) |
| 12–14 | boys | light | 2 360 | S1·2004·T4.5 rows 12–13/13–14/14–15·derived (mean of 2 175/2 350/2 550) |
| 12–14 | boys | moderate | 2 775 | S1·2004·T4.5 rows 12–13/13–14/14–15·derived (mean of 2 550/2 775/3 000) |
| 12–14 | boys | vigorous | 3 185 | S1·2004·T4.5 rows 12–13/13–14/14–15·derived (mean of 2 925/3 175/3 450) |
| 12–14 | girls | light | 2 010 | S1·2004·T4.6 rows 12–13/13–14/14–15·derived (mean of 1 925/2 025/2 075) |
| 12–14 | girls | moderate | 2 365 | S1·2004·T4.6 rows 12–13/13–14/14–15·derived (mean of 2 275/2 375/2 450) |
| 12–14 | girls | vigorous | 2 725 | S1·2004·T4.6 rows 12–13/13–14/14–15·derived (mean of 2 625/2 725/2 825) |
| 15–17 | boys | light | 2 810 | S1·2004·T4.5 rows 15–16/16–17/17–18·derived (mean of 2 700/2 825/2 900) |
| 15–17 | boys | moderate | 3 300 | S1·2004·T4.5 rows 15–16/16–17/17–18·derived (mean of 3 175/3 325/3 400) |
| 15–17 | boys | vigorous | 3 800 | S1·2004·T4.5 rows 15–16/16–17/17–18·derived (mean of 3 650/3 825/3 925) |
| 15–17 | girls | light | 2 125 | S1·2004·T4.6 rows 15–16/16–17/17–18·derived (mean of 2 125/2 125/2 125) |
| 15–17 | girls | moderate | 2 500 | S1·2004·T4.6 rows 15–16/16–17/17–18·derived (mean of 2 500/2 500/2 500) |
| 15–17 | girls | vigorous | 2 875 | S1·2004·T4.6 rows 15–16/16–17/17–18·derived (mean of 2 875/2 875/2 875) |
| 18–29.9 | men | sedentary (1.45 × BMR) | 2 400 | S1·2004·T5.4·direct (mean weight 65 kg; BMR/kg 108 kJ = 26 kcal/kg) |
| 18–29.9 | men | moderate (1.75 × BMR) | 2 900 | S1·2004·T5.4·direct (65 kg) |
| 18–29.9 | men | vigorous (2.05 × BMR) | 3 450 | S1·2004·T5.4·direct (65 kg) |
| 18–29.9 | women | sedentary (1.45 × BMR) | 1 900 | S1·2004·T5.7·direct (55 kg; BMR/kg 99 kJ = 24 kcal/kg) |
| 18–29.9 | women | moderate (1.75 × BMR) | 2 300 | S1·2004·T5.7·direct (55 kg) |
| 18–29.9 | women | vigorous (2.05 × BMR) | 2 650 | S1·2004·T5.7·direct (55 kg) |
| 30–59.9 | men | sedentary | 2 350 | S1·2004·T5.5·direct (65 kg; BMR/kg 104 kJ = 25 kcal/kg) |
| 30–59.9 | men | moderate | 2 850 | S1·2004·T5.5·direct (65 kg) |
| 30–59.9 | men | vigorous | 3 300 | S1·2004·T5.5·direct (65 kg) |
| 30–59.9 | women | sedentary | 1 850 | S1·2004·T5.8·direct (55 kg; BMR/kg 98 kJ = 24 kcal/kg) |
| 30–59.9 | women | moderate | 2 250 | S1·2004·T5.8·direct (55 kg) |
| 30–59.9 | women | vigorous | 2 650 | S1·2004·T5.8·direct (55 kg) |
| ≥60 | men | sedentary | 1 950 | S1·2004·T5.6·direct (65 kg; BMR/kg 87 kJ = 21 kcal/kg) |
| ≥60 | men | moderate | 2 350 | S1·2004·T5.6·direct (65 kg) |
| ≥60 | men | vigorous | 2 750 | S1·2004·T5.6·direct (65 kg) |
| ≥60 | women | sedentary | 1 700 | S1·2004·T5.9·direct (55 kg; BMR/kg 88 kJ = 21 kcal/kg) |
| ≥60 | women | moderate | 2 050 | S1·2004·T5.9·direct (55 kg) |
| ≥60 | women | vigorous | 2 350 | S1·2004·T5.9·direct (55 kg) |

**Adult derivation for any weight/age (S1·2004·§5.4.1 + Table 5.2·direct):** BMR (kcal/day): men 18–30: `15.057 × W + 692.2`; men 30–60: `11.472 × W + 873.1`; men ≥60: `11.711 × W + 587.7`; women 18–30: `14.818 × W + 486.6`; women 30–60: `8.126 × W + 845.6`; women ≥60: `9.082 × W + 658.5`. Then `kcal/day = BMR × PAL`. Check (S1·2004·T5.4·cross-check, derived): men 18–30 @65 kg → BMR = 1 671 kcal; ×1.45 = 2 423 → table prints 2 400; ×1.60 = 2 673 → 2 650; ×1.75 = 2 924 → 2 900; ×1.90 = 3 175 → 3 150; ×2.05 = 3 425 → 3 450; ×2.20 = 3 676 → 3 700 (report rounds to closest 50 kcal/d — Tables 5.4–5.9 footnote). Alternative PAL anchors (1.55/1.85/2.20 mid-points) are also legitimate — gap G2.

**Weight dependence (adults):** BMR/kg falls as weight rises (S1·2004·T5.4–5.9·direct), so e.g. men 18–30 @70 kg, PAL 1.75 → 3 050 kcal (S1·2004·T5.4·direct) vs 2 900 @65 kg. If the YAML stores per-kg values (BMR/kg × PAL) plus the Schofield equations, any user weight is handled exactly.

**Worked example — median-weight child (kept):** a 7.5-year-old boy, WHO 2007 Reference weight-for-age median (M) = **23.9 kg** (S3·2007·boys z-table row 7 y 5 m·direct; the S1 row "7–8" uses 24.0 kg from the older WHO 1983 standards — gap G5). Moderate-activity requirement for boys 7–8 y = **71 kcal/kg/day** (S1·2004·T4.5·direct). Energy goal = 23.9 × 71 ≈ **1 700 kcal/day** — identical to S1's printed value for that row (1 700 kcal/d at 24.0 kg), confirming the per-kg × median-weight method reproduces the report. Protein: 0.92 g/kg/d (S2·2007·Table 47·direct, 7–10 y) × 23.9 kg ≈ **22 g/day**.

## 4. Protein table — safe level of protein intake

S2·2007·Table 47·direct states g/kg/day, median reference weights ("WHO reference values", footnote a) and g/day directly for children; adults come from S2·2007·Table 46·direct (0.83 g/kg/day; the table itself prints 55 kg → 46 g, 65 kg → 54 g, 70 kg → 58 g, 75 kg → 62 g).

| Age group | Sex | g/kg/day | g/day (median weight) | Median weight (kg) | Basis |
|---|---|---|---|---|---|
| 4–6 y | boys | 0.87 | 17.1 | 19.7 | S2·2007·T47·direct |
| 4–6 y | girls | 0.87 | 16.2 | 18.6 | S2·2007·T47·direct |
| 7–10 y | boys | 0.92 | 25.9 | 28.1 | S2·2007·T47·direct |
| 7–10 y | girls | 0.92 | 26.2 | 28.5 | S2·2007·T47·direct |
| 11–14 y | boys | 0.90 | 40.5 | 45.0 | S2·2007·T47·direct |
| 11–14 y | girls | 0.89 | 41.0 | 46.1 | S2·2007·T47·direct |
| 15–18 y | boys | 0.87 | 57.9 | 66.5 | S2·2007·T47·direct |
| 15–18 y | girls | 0.84 | 47.4 | 56.4 | S2·2007·T47·direct |
| >18 y (all adults) | men & women | 0.83 | 0.83 × W (at 55/65/70/75 kg: 46/54/58/62 — printed in T46) | — | g/kg: S2·2007·T46/§14.2·direct; g/day at other weights: derived = 0.83 × weight (see FN2 for the contested higher IAAO proposals — not adopted; verified per-study values in §6.1) |

**Derivation (S2·2007·§9.3.3/Tables 33a-b/§7.10·direct):** average requirement = maintenance (0.66 g/kg/d, the adult meta-analysis value, used for all ages ≥6 months) + growth deposition ÷ 0.58 efficiency of utilization; safe level = average + 1.96 SD using 12% CV (adult value) for maintenance and deposition SD (Table 29) ÷ 0.58. Example (boys 7–10 y, Table 33a): 0.66 + 0.09 = 0.75 average → 0.92 safe. Adult average 0.66 → safe 0.83 g/kg/d (133 mg N/kg/d; S2·2007·§7.10·direct). No sex differentiation in adults ("no justification for any differentiation between males and females", S2·2007·§7.10/§14.2·direct). Values assume protein quality score 1.0 (PDCAAS at publication; DIAAS is the successor method — FN1).

Note the intentional divergence in shape: protein g/kg **rises slightly** at 7–10 y (0.92) vs 4–6 y (0.87) because mid-childhood growth deposition plateaus while the maintenance term dominates; then falls to the adult 0.83 across adolescence.

## 5. Full single-year energy data (S1 Tables 4.5/4.6 verbatim, ages 5–17)

All values below are `S1·2004·T4.5 (boys) / T4.6 (girls)·direct`. Boys' third column is labelled "heavy physical activity" in S1.

### Boys (S1 Table 4.5) — weight kg | light kcal/d (PAL) | moderate kcal/d (PAL) | heavy kcal/d (PAL)

| Age interval | Weight | Light | Moderate | Heavy |
|---|---|---|---|---|
| 5–6 | 19.7 | — | 1 475 (1.55) | — |
| 6–7 | 21.7 | 1 350 (1.30) | 1 575 (1.55) | 1 800 (1.80) |
| 7–8 | 24.0 | 1 450 (1.35) | 1 700 (1.60) | 1 950 (1.85) |
| 8–9 | 26.7 | 1 550 (1.40) | 1 825 (1.65) | 2 100 (1.90) |
| 9–10 | 29.7 | 1 675 (1.40) | 1 975 (1.65) | 2 275 (1.90) |
| 10–11 | 33.3 | 1 825 (1.45) | 2 150 (1.70) | 2 475 (1.95) |
| 11–12 | 37.5 | 2 000 (1.50) | 2 350 (1.75) | 2 700 (2.00) |
| 12–13 | 42.3 | 2 175 (1.55) | 2 550 (1.80) | 2 925 (2.05) |
| 13–14 | 47.8 | 2 350 (1.55) | 2 775 (1.80) | 3 175 (2.05) |
| 14–15 | 53.8 | 2 550 (1.60) | 3 000 (1.85) | 3 450 (2.15) |
| 15–16 | 59.5 | 2 700 (1.60) | 3 175 (1.85) | 3 650 (2.15) |
| 16–17 | 64.4 | 2 825 (1.55) | 3 325 (1.85) | 3 825 (2.15) |
| 17–18 | 67.8 | 2 900 (1.55) | 3 400 (1.85) | 3 925 (2.15) |

Moderate derivation (S1·2004·T4.5 note·direct): `MJ/d = (1.298 + 0.265·W − 0.0011·W²) + 8.6 kJ/g daily weight gain`; light = −15%, heavy = +15%; weight = median at interval mid-point, WHO 1983 standards (S4).

### Girls (S1 Table 4.6) — same structure

| Age interval | Weight | Light | Moderate | Heavy |
|---|---|---|---|---|
| 5–6 | 18.6 | — | 1 325 (1.55) | — |
| 6–7 | 20.6 | 1 225 (1.30) | 1 425 (1.55) | 1 650 (1.80) |
| 7–8 | 23.3 | 1 325 (1.35) | 1 550 (1.60) | 1 775 (1.85) |
| 8–9 | 26.6 | 1 450 (1.40) | 1 700 (1.65) | 1 950 (1.90) |
| 9–10 | 30.5 | 1 575 (1.40) | 1 850 (1.65) | 2 125 (1.90) |
| 10–11 | 34.7 | 1 700 (1.45) | 2 000 (1.70) | 2 300 (1.95) |
| 11–12 | 39.2 | 1 825 (1.50) | 2 150 (1.75) | 2 475 (2.00) |
| 12–13 | 43.8 | 1 925 (1.50) | 2 275 (1.75) | 2 625 (2.00) |
| 13–14 | 48.3 | 2 025 (1.50) | 2 375 (1.75) | 2 725 (2.00) |
| 14–15 | 52.1 | 2 075 (1.50) | 2 450 (1.75) | 2 825 (2.00) |
| 15–16 | 55.0 | 2 125 (1.50) | 2 500 (1.75) | 2 875 (2.00) |
| 16–17 | 56.4 | 2 125 (1.50) | 2 500 (1.75) | 2 875 (2.00) |
| 17–18 | 56.7 | 2 125 (1.45) | 2 500 (1.70) | 2 875 (1.95) |

Moderate derivation (S1·2004·T4.6 note·direct): `MJ/d = (1.102 + 0.273·W − 0.0019·W²) + 8.6 kJ/g daily weight gain`; light = −15%, heavy = +15%.

## 6. WHO vs independent national/regional reference values (added 2026-10-28)

**Purpose and authority chain.** WHO/FAO/UNU reports (S1, S2) remain the operative world references (§0). This section documents how the WHO values compare with the three main independent reference systems — the US DRIs (IOM 2005 for protein, S11; NASEM 2023 for energy, S12) and EFSA's EU DRVs (protein 2012, S13; energy 2013, S14) — plus the DLW literature (S15) and the IAAO protein studies (S16–S19). **Nothing here changes the WHO defaults; the comparison exists so that any later decision (G12/G13) is made with verified numbers.** Computed values are marked `derived` (all reproducible from equations/tables quoted in the register; python re-check 2026-10-28, see verification log).

### 6.1 PAL-anchor map (required before reading any comparison)

The four systems use different activity anchors — "same" lifestyle names sit at different PALs, so **printed values must not be compared without re-anchoring**:

| System | Adult anchors | Child anchors | Basis |
|---|---|---|---|
| WHO (S1) | columns 1.45/1.60/1.75/1.90/2.05/2.20; classes sedentary/light 1.40–1.69, moderate 1.70–1.99, vigorous 2.00–2.40 | child "moderate" per-row PAL 1.55–1.85 (rises with age); light/heavy = ±15% | S1·2004·T5.3, T4.5/4.6, T5.4–5.9·direct |
| EFSA (S14) | PAL 1.4/1.6/1.8/2.0 = low active (sedentary)/moderately active/active/very active | 4–9 y rows at PAL 1.4/1.6/1.8; 10–17 y at 1.6/1.8/2.0 | S14·2013 + official summary table·direct |
| IOM 2005 (S11) | PA coefficients (BEE multipliers) for PAL bands ≥1.0<1.4/≥1.4<1.6/≥1.6<1.9/≥1.9<2.5: men 1.00/1.11/1.25/1.48; women 1.00/1.12/1.27/1.45 | same bands; coefficients boys 1.00/1.13/1.26/1.42, girls 1.00/1.16/1.31/1.56 | S11·2005·§5·direct |
| NASEM 2023 (S12) | age-specific percentile cutoffs — 19–70.99 y: <1.53/1.53–1.68/1.68–1.85/>1.85; 71+y: <1.46/1.46–1.62/1.62–1.79/>1.79 | 3–8.99 y: <1.31/1.31–1.44/1.44–1.59/>1.59; 9–13.99 y: <1.44/1.44–1.59/1.59–1.77/>1.77; 14–18.99 y: <1.56/1.56–1.73/1.73–1.92/>1.92 | S12·2023·T5-3·direct |

**Pairing used below (closest anchors):** WHO moderate (adults PAL 1.75; child rows ≈1.55–1.85) ↔ EFSA PAL 1.8 for ages 12–17 and adults (1.6 for ages 5–8, where WHO's child PAL is lower) ↔ IOM "active" ↔ NASEM "Active". WHO sedentary 1.45 ↔ EFSA 1.4 ↔ IOM "low active"/NASEM "Inactive"; WHO vigorous 2.05 ↔ EFSA 2.0 ↔ IOM "very active"/NASEM "Very active".

### 6.2 Protein (g/kg body weight/day)

| Band | WHO safe (S2) | EFSA PRI (S13) | US RDA (S11) | IAAO EAR / safe (S16–S19) | Divergence vs WHO |
|---|---|---|---|---|---|
| 5–8 y | 0.87 (4–6 y) – 0.92 (7–10 y) | 0.85 (5 y) → 0.92 (8 y), per year | 0.95 (4–8 y) | 1.3 / 1.55 (study ages 6–11; S16) | EFSA −0…−2 %; US +3–9 %; IAAO EAR +41 %, safe +68–78 % |
| 9–11 y | 0.92 | 0.91–0.92 (9–10 y) | 0.95 (9–13 y) | (S16 covers ages 6–11) | EFSA −0–1 %; US +3 % |
| 12–14 y | 0.90 / 0.89 (m/f) | 0.90 (12–13 y) → 0.89/0.88 (14 y m/f) | 0.95 (to 13 y) / 0.85 (14–18 y) | no data — the only child/adolescent requirement study from 2000–2024 is S16 (S9 rates it "insufficient evidence") | EFSA ≈0 %; US +6 % (12–13 y), −5 % (14 y) |
| 15–17 y | 0.87 / 0.84 (m/f) | m 0.88–0.86; f 0.85–0.83 (15→17 y) | 0.85 (14–18 y; **no sex split**) | no data | EFSA −1…+1 %; US −2…+1 % |
| 18–59 y | 0.83 | 0.83 | 0.80 (19–50 y) | 0.93 / 1.2 (young men, S19 T1 = IAAO literature); 2-phase NB reanalysis 0.91 / 1.0 (S19 T1) | EFSA 0 %; US −3.6 %; IAAO +12 %/+45 %; 2-phase NB +10/+20 % |
| ≥60 y | 0.83 (S2 does not split adult age) | 0.83 (≥60 y) | 0.80 (51–70 y and >70 y) | men >65 y: 0.94 / 1.24 (S18, n=6); women >65 y: 0.96 / 1.29 (S17, n=12); review summary 0.9 / 1.2 (S19) | IAAO EAR +13–16 %; safe +45–55 % |

Notes:
1. **EFSA's child values are not an independent test of the method** — EFSA adopted the WHO/FAO/UNU 2007 factorial approach wholesale (S13·2012·§5.1.3·direct). Child agreement is by construction; the genuinely independent child evidence is the US RDA (+3–9 %) and the single IAAO study (+41–78 %).
2. IAAO evidence caveats: small samples (children n=7/56 test days; men >65 y n=6/42; women >65 y n=12/82), short test intakes (1 study day after 2-day adaptation), one research group; contested (Millward 2024; FN2); rated "inconclusive" for 2000–2024 by AHRQ (S9); no national body has adopted IAAO protein values.
3. The US adolescent RDA makes no sex split (0.85 m/f, 14–18 y); WHO/EFSA sex-split reflects sex-specific growth deposition. g/day figures also rest on different referent weights (US: 52 g at ref ~61 kg; WHO median 66.5 kg — S11·2005·Table 1-1·direct vs S2·2007·T47·direct).
4. EFSA g/day columns use its own referents (adults 74.6 kg m / 62.1 kg f, SCF 1993; children van Buuren 2012 EU medians — S13·2012·T12·direct); never mix g/day across systems (gap G4 logic).
5. EFSA's adult PRI 0.83 comes from the same WHO/FAO/UNU 2007 method (maintenance 0.66, efficiency 47 %, CV 12 % — S13·2012·§5.1.2·direct); the only true national divergence at adult level is the US 0.80 (−3.6 %).
6. S19's own reading of young-vs-old: "no difference in requirement on a gender basis or on a per kg body weight basis between younger and older adults" — but both sit ~40 % above current EAR/RDA on the IAAO method.

### 6.3 Energy (kcal/day)

**Adults — moderate-activity column.** WHO at its representative weights (men 65 kg, women 55 kg; band-midpoint ages): 1.45/1.75/2.05 columns `direct` (§3); 1.60/1.90 columns `derived` via the S1 equation (§3 check block). IOM 2005 and NASEM 2023 computed **at the same inputs** (65/55 kg, 1.70/1.60 m, band-midpoint ages) from their verified equations (`derived`). EFSA values are its printed ARs — **heavier referents** (EU survey heights + BMI 22 ≈ ~70 kg men/~58 kg women), so EFSA divergences overstate per-kg differences:

| Group | WHO moderate (1.75) | IOM 2005 "active" (PA 1.25/1.27) | NASEM 2023 "Active" | EFSA 2013 @PAL 1.8 (printed) |
|---|---|---|---|---|
| men 18–29.9 | 2 900 | 2 870 (−0.9 %) | 2 890 (−0.4 %) | 3 010 (+3.8 %) |
| women 18–29.9 | 2 300 | 2 320 (+0.7 %) | 2 270 (−1.4 %) | 2 410 (+4.9 %) |
| men 30–59.9 | 2 850 | 2 670 (−6.2 %) | 2 660 (−6.7 %) | 2 910 (+2.2 %) (30–39 y row) |
| women 30–59.9 | 2 250 | 2 170 (−3.5 %) | 2 120 (−5.8 %) | 2 340 (+4.0 %) (30–39 y row) |
| men ≥60 | 2 350 | 2 430 (+3.6 %) | 2 390 (+1.7 %) | 2 600 (+10.8 %) (60–69 y row) |
| women ≥60 | 2 050 | 2 000 (−2.5 %) | 1 950 (−5.1 %) | 2 100 (+2.5 %) (60–69 y row) |

Other columns behave the same way once re-anchored (computed `derived`): e.g. men 18–29.9 — IOM "low active" 2 600 vs WHO's 1.60 column 2 650 (−1.9 %), NASEM "Inactive" 2 515 vs WHO sedentary 2 400 (+4.8 %, percentile base <1.53 vs WHO 1.45 point anchor), NASEM "Very active" 3 120 vs WHO vigorous 3 450 (−9.6 %). Printed IOM adult reference (S11·2005·T5-22·direct): men 30 y, 1.70 m, BMI 18.5→24.99: sedentary/low/active/very = 2 144→2 993 / 2 339→3 434 kcal. Adult pattern: **at matched anchors all systems agree within roughly ±1–11 %**; WHO's 30–59.9 y column runs ~+3–7 % above IOM/NASEM (their height terms + US-referent data), EFSA's run +2–5 % above WHO (Henry-BMR) except men ≥60 (+10.8 % — Henry elderly BMR + heavier referent).

**Children — band means at each system's moderate-equivalent anchor** (WHO moderate baseline from §3; EFSA at the matched per-age PAL; IOM 2005 "active" coefficients; NASEM 2023 "Active"; all four non-WHO columns computed `derived` from verified equations + IOM reference children S11·T5-8/5-9 and printed EFSA per-year ARs S14·T1):

| Band | Sex | WHO moderate | EFSA @matched PAL | IOM 2005 active | NASEM 2023 Active |
|---|---|---|---|---|---|
| 5–8 | boys | 1 645 | 1 670 @1.6 (+1.3 %) | 1 790 (+9.1 %) | 1 600 (−2.7 %) |
| 5–8 | girls | 1 500 | 1 550 @1.6 (+3.5 %) | 1 690 (+12.4 %) | 1 470 (−2.1 %) |
| 9–11 | boys | 2 160 | 2 210 @1.8 (+2.5 %) | 2 160 (−0.1 %) | 2 090 (−3.1 %) |
| 9–11 | girls | 2 000 | 2 070 @1.8 (+3.5 %) | 1 970 (−1.7 %) | 1 830 (−8.4 %) |
| 12–14 | boys | 2 775 | 2 630 @1.8 (−5.3 %) | 2 630 (−5.4 %) | 2 600 (−6.4 %) |
| 12–14 | girls | 2 365 | 2 350 @1.8 (−0.8 %) | 2 270 (−4.2 %) | 2 220 (−6.3 %) |
| 15–17 | boys | 3 300 | 3 180 @1.8 (−3.7 %) | 3 130 (−5.1 %) | 3 120 (−5.4 %) |
| 15–17 | girls | 2 500 | 2 530 @1.8 (+1.3 %) | 2 450 (−1.9 %) | 2 500 (−0.2 %) |

Reading: at **matched PAL anchors the systems cluster within roughly ±1–12 %**, and the sign of each residual is explained: IOM's child "active" (PAL 1.6–1.9 constant) overshoots WHO's younger-child moderate (per-row PAL 1.55–1.65) by +9–12 %, then converges (−0…−5 %) where WHO's per-row PAL reaches 1.75–1.85; EFSA's and NASEM's age-graded anchors track WHO's rising child PAL better; NASEM's percentile-defined categories (built on observed US-children activity) sit slightly below WHO's fixed anchors for 9–14 y girls (−8 %). No system contradicts WHO's child values by more than ~12 % once anchors are aligned.

### 6.4 DLW evidence check (S15, S12)

- Pontzer et al. 2021 (S15): DLW across 29 countries, n=6,421 (64 % female, 8 days–95 y): fat-free-mass-adjusted TEE rises steeply in infancy (~50 % above adult level at ~1 y), declines to adult levels by ~20.5 y (95 % CI 19.8–21.2), **stays stable 20–60 y**, then declines ~0.7 %/y after ~63 y (CI 60.1–65.9); 90+ ≈ 26 % below middle-aged adults. This supports WHO's ≥60 break and its smooth within-band structure (S1's 18–29.9/30–59.9/≥60 bands).
- NASEM 2023 (S12) built EER equations **directly** on a DLW database (8 600 observations after exclusions: IAEA database v3.6.1 = 5 717 + SOLNAS 380 + IOM 2 283 + CNRC 220) with the referent population changed to the "general population" (i.e. including people with overweight/obesity/chronic disease). Its adult equations agree with WHO's moderate column within −6.7 %…+1.7 % at matched inputs (§6.3, computed) — the DLW evidence broadly corroborates WHO's adult factorial values, with WHO running ~+2–7 % high for the US-referent 30–59.9 y groups.
- WHO's child tables were **already DLW/HRM-based** (801 boys + 808 girls in measured cohorts, S1·2004·§4.3–4.4·direct); the newer/larger DLW datasets do not overturn them at band level (±1–12 % at matched anchors, §6.3). The FAO/WHO/IAEA reevaluation (§0) is the expected official update path — S12 is the strongest preview of its likely direction (direct-DLW equations; general-population referent).

### 6.5 Assessment and recommendation (analysis, clearly marked — this is not WHO text)

**Protein — keep the WHO safe levels (0.83 g/kg/d adults; 0.87–0.92 children) as the default for every band.** (i) EFSA's EU PRI is numerically identical for adults (0.83) and method-identical for children — the WHO values remain the accepted international standard; (ii) the US RDA differs by −3.6 % (adults) to +3–9 % (children) — small, and not actionable without a US persona; (iii) the IAAO uplift (+12–78 % depending on band/metric) is a live scientific question but not adoption-ready: single-group studies (n=6–12), short test intakes, contested in the literature, and rated "inconclusive" by the 2024 AHRQ review that will inform the next US DRI update (S9). If a future FAO/WHO/UNU or NASEM protein update adopts IAAO-informed values (most plausible for ≥60 y), re-research — tracked as G12.

**Energy — keep the WHO values (§3) as the default for every band.** (i) Agreement with EFSA 2013 is within ~±5 % at matched PAL for most groups (men ≥60 +11 % exception — Henry-BMR + heavier EU referent); (ii) NASEM 2023 — the most modern system, DLW-regression-based — corroborates WHO's moderate column within −6.7 %…+1.7 % at matched inputs; (iii) WHO's child values are already measurement-based; (iv) the official successor (FAO/WHO/IAEA reevaluation, §0) is in progress, so switching to a national system now would be churn, not gain. NASEM 2023 is the designated fallback if a US-population variant is ever required (G13); EFSA 2013 serves the same role for an EU persona.

**Method caveats that apply to any future switch:** PAL anchors are not interchangeable across systems (§6.1) — comparing printed values without re-anchoring overstates disagreement by up to ~±10 %; referent persons differ (WHO 65/55 kg; EFSA EU-survey height + BMI 22; IOM BMI 18.5–25 tables; NASEM accepts any weight/height); all four systems assume protein quality 1.0 (FN1 applies to each); none of the compared systems changes §1's population-vs-individual caveat.

## 7. Cross-checks performed

- Equation vs table (adults, S1·2004·derived check): Schofield × PAL reproduces S1 Tables 5.4–5.9 within the report's stated rounding (closest 50 kcal/d) — see §3 check block.
- Child median weights (S1/S4 vs S3, derived check): at 7.5 y boys 24.0 vs 23.9 kg; girls 23.3 vs 23.4 kg; at 9.5 y boys 29.7 vs ≈29.5 (S3 z-rows 9:5 = 29.3, 9:6 = 29.6, 9:7 = 29.8); girls 30.5 vs ≈30.2 (rows 9:5 = 29.7, 9:6 = 30.0, 9:8 = 30.6). Differences ≤ ~0.5 kg (≈ ±1–2 % of the energy goal). S3 has **no weight-for-age beyond 10 y** (WHO stopped WFA at 10 y due to pubertal confounding — S3·2007·indicator page·direct), so 11–17 y medians rest on S1/S4.
- Protein (S2·2007·derived check): summary Table 47 agrees with per-year Tables 33a/33b (e.g. 4–6 y safe 0.87 = ages 4/5/6 = 0.86/0.85/0.89; 7–10 y 0.92 = 0.91/0.92/0.92/0.91).
- Cross-system energy (new, §6.3, derived): NASEM 2023 "Active" and IOM 2005 "active" EERs computed at WHO's reference adults (65/55 kg, 1.70/1.60 m, band-midpoint ages) reproduce WHO's moderate column within **−6.7 %…+1.7 %** (NASEM) and **−6.2 %…+3.6 %** (IOM) across all six adult groups; EFSA 2013 printed ARs at PAL 1.8 sit +2.2 %…+10.8 % above it (heavier referents + Henry BMR).
- Cross-system protein (new, §6.2, direct/derived): EFSA adult PRI = WHO safe level exactly (0.83); US adult RDA −3.6 %; child-level agreement EFSA −2…+1 %, US +3–9 % — see §6.2 table.

## 8. Open questions (one line each; no decision made here — options listed)

- **G1 Band mapping.** S1 prints single-year rows, S2 its own bands (4–6/7–10/11–14/15–18), project bands are 5–8/9–11/12–14/15–17 — options: equal-weight band means (used here), nearest-row lookup, mid-band row, or adopt S2's bands for protein.
- **G2 PAL anchors.** S1 offers ranges (1.40–1.69/1.70–1.99/2.00–2.40), six columns (1.45/1.60/1.75/1.90/2.05/2.20), and mid-points/exemplars (~1.55/1.85/2.20 or Table 5.1's 1.53/1.76/2.25); the brief's "1.4/1.6/1.8/2.0" is not an S1 anchor set (it is EFSA's — §6.1) — options: store ranges + mid-points, or columns 1.45/1.75/2.05.
- **G3 Population vs individual.** S1 §5.4.1: values are for populations (±8–10% within each PAL class) — options: caveat text only, or add a per-user calibration path.
- **G4 Adult weight assumption.** Printed kcal/day need a weight; men 65 kg / women 55 kg used here (rows exist in T5.4–5.9; alternatives 60/70 kg men, 50/60 kg women) — options: store Schofield equations + PAL (exact for any weight), fixed median-weight rows, or user-weight formula. (EFSA's printed ARs use ~70/58 kg EU referents — §6.3; never mix g/day or kcal/day across systems.)
- **G5 Child weight standard.** S1 medians are WHO-1983 (S4); WHO 2007 (S3) matches within ~0.5 kg for 5–10 y but has no WFA >10 y — options: keep S1's self-consistent weights, or recompute per-kg goals against S3 for 5–10 y only (11–17 y stays S1/S4 or derives weight via BMI-for-age × height-for-age).
- **G6 Age 5 levels.** S1 applies ±15% only from age 6, so age 5 has a moderate value only (the 5–8 band rows above exclude age 5, n = 3) — options: extrapolate ±15% at age 5, moderate-only at 5, or start bands at 6.
- **G7 Protein band split.** Project band 5–8 spans S2's 4–6 y (0.87) and 7–10 y (0.92) — options: per-year interpolation (S2·2007·§14.1.3 recommends the §9 tables for precision), weighted band mean (weights undefined), or S2 bands in the YAML for protein.
- **G8 Protein quality correction (see FN1).** All S2 values assume quality score 1.0; for mixed/vegetarian meals the effective requirement is 0.83/score, and FNP 92 (2013) replaces PDCAAS with DIAAS for computing that score — options: apply the correction to the diet side (S2·2007·§14.7's direction), to the goal, or display only.
- **G9 Pregnancy/lactation/elderly.** S2·2007·Table 48·direct: +1/+10/+31 g/d (T1/2/3 pregnancy), +19 g (0–6 mo) / +13 g (after) lactation; S1·2004·§6–7·direct: +375/+1 200/+1 950 kJ/d pregnancy, +2 800/+1 925 kJ/d lactation — out of school-meal scope; record only if the app serves adults broadly. (Comparison anchors if ever needed: EFSA +1/+9/+28 and +19/+13 g/d, S13·T12·direct; NASEM 2023 energy-pregnancy/lactation equations S12·T5-17/5-18·direct.)
- **G10 S2 Table 33b text-layer artifact.** In the fetched PDF text layer, girls 12–13 y safe levels render "1.89/1.88" (inconsistent with neighbours and with Table 47's 0.89) — Table 47 is canonical; re-verify against the printed report only if per-year girls' values are needed.
- **G11 Energy has no safety margin by design.** Unlike protein, S1 adds no percentile margin (surplus storage = obesity risk) — never scale kcal up; if a margin is wanted, move up one PAL class.
- **G12 IAAO-informed protein uplift (new, §6.2).** IAAO/2-phase-NB studies propose adults ~0.91–0.99 EAR / 0.99–1.2 safe and ≥65 y 0.94–0.96 / 1.24–1.29 g/kg/d (S16–S19), i.e. +12–55 % vs WHO — contested, AHRQ-inconclusive, no national adoption — options: keep WHO (current default), expose an optional personal "higher-protein mode" multiplier, or wait for DRI/FAO adoption.
- **G13 Alternative authority sets (new, §6.3–6.5).** NASEM 2023 energy (US, DLW-based, percentile PAL categories) and EFSA 2012/2013 (EU) are documented and agree with WHO mostly within ±1–11 % at matched anchors — options: keep WHO-only (current default), add locale/persona-specific YAML variants, or adopt NASEM 2023 for adult bands if a US persona is ever required.

## 9. Notes for the future YAML (mapping hints, not decisions)

- Energy keys: `age_band × sex × pal_level → kcal_per_day` (values in §3), plus optionally `kcal_per_kg` and the child TEE/growth equations (§5 notes) so non-median weights scale correctly; adults need the Schofield equations (§3) + PAL factor rather than a fixed kcal figure.
- Protein keys: `age_group × sex → g_per_kg_day` (§4), with `g_per_day = g_per_kg × weight (actual or WHO-median)`.
- Rounding used in the sources: children to closest 25 kcal/d (S1·2004·T4.5/4.6 note·direct), adults to closest 50 kcal/d (S1·2004·T5.4–5.9 note·direct), protein to 2 significant figures (S2·2007·§14.1.2·direct).
- If G13 is ever accepted, alternative authority sets must be separate top-level keys (e.g. `energy_us_nasem_2023`, `protein_eu_efsa_2012`) that never overwrite the WHO defaults; PAL levels would need per-set anchor definitions (§6.1), since level names are not interchangeable across systems.
