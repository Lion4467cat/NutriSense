# Research: measured Indian-food datasets for NutriSense (strict bar)

**Owner requirement (narrowed 2026-10-28).** A dataset qualifies ONLY if it satisfies BOTH:

- **(A)** Indian or South-Asian cuisine focus (or substantial Indian dish coverage), AND
- **(B)** quantitative **mass/portion annotation in grams captured on real plated food** — kitchen-scale truth, not estimated from nutrition labels or LLM guesses.

Purpose: train/fine-tune the learned per-portion mass head (RGB photos of plated food) and build the classifier gallery. Label-only web collections are out of scope as primary candidates (short rejected table below). Non-Indian measured sets are documented in a secondary table (Nutrition5k's per-ingredient weighing protocol is the gold standard to imitate) but do not fulfill the purpose.

**Method.** Deep pass performed 2026-10-28: WED citation graph traced (Semantic Scholar API + search; every citing paper followed), FPB citation graph traced (OpenAlex), Indian institutional repositories (Mendeley Data, IEEE DataPort, Zenodo, Shodhganga), dietetics literature (weighed-portion photo atlases), theses, and targeted queries ("thali weight", "Indian food portion size dataset", "Indian plate weight estimation", 2019–2026). A second **exhaustive sweep (same day) covered 10 further venue categories** — see §4 "Exhaustive sweep" for the audited list. All URLs accessed 2026-10-28. Repo context: `docs/licenses.md`, `docs/wed_seam_map.md`.

---

## 1. Qualifying: measured Indian / South-Asian

### WED + ITD (CVIT, IIIT Hyderabad) — the only qualifying public dataset found
- **What.** WED (Weight Estimation Dataset): 267 plates, 1,394 multi-view images, 41 dishes, **gram-level weights of individual dish regions recorded on a precision digital scale (±1 g)** in a real kiosk/dining environment. Companion ITD: 796 plates, 7,900 images, 50 dishes, pixel masks (masks only — no mass; see rejected table). Paper: Arora, Arun, Jawahar, "What is there in an Indian Thali?", ICVGIP 2025; ACM DL DOI 10.1145/3774521.3774594 (**paper open access, CC BY 4.0**).
- **Source.** Project page: https://cvit.iiit.ac.in/research/projects/cvit-projects/indian_thali; direct: `https://cvit.iiit.ac.in/images/datasets/food_nutrition/WED.tar.gz` (accessed 2026-10-28). Paper PDF: https://cvit.iiit.ac.in/images/ConferencePapers/2025/ICVGIP_Food_Scanner.pdf.
- **License.** Code MIT; **dataset terms still not stated on the page** — remains the M9 gate in `docs/licenses.md` (cite, never redistribute; images git-ignored under `data/wed/`).
- **Fit.** (a) anchor + (b) Indian anchor. Everything else in this document fails one bar.
- **WED-adjacent CVIT releases (watch items, not qualifying):** "How Does India Cook Biryani?" (ICVGIP 2025, Rishi, Goel, Arun, Jawahar; arXiv 2601.06198) — 12 regional biryani styles, cooking **videos** with temporal segmentation; "the dataset, prompts, and annotations will be released" (future tense; no mass; not plated meals). https://arxiv.org/html/2601.06198v1 and https://cvit.iiit.ac.in/research/publications (accessed 2026-10-28).

**No other dataset passed both bars.** Section 5 quantifies the near-misses.

## 2. Measured (grams on real food) but NOT Indian — documented, secondary

### Nutrition5k (Google) — protocol gold standard to imitate
- 5,006 real cafeteria plates; per-ingredient mass captured by a digital scale under the plate (±1 g, incremental scanning); overhead RGB-D + 4 side videos; CC BY 4.0; public GCS bucket. Source: https://github.com/google-research-datasets/Nutrition5k; paper arXiv 2103.03375 (CVPR 2021) — "A digital scale under the plate captures the incremental weight within +/- 1 gram" (accessed 2026-10-28). American cuisine; repo archived 2026-04-19 but bucket public. **Use as: weight-head cross-check + capture/annotation-protocol reference for the school-capture campaign.**

### FPB — Food Portion Benchmark (ISSAI, Nazarbayev University)
- 14,083 images / 138 classes, lab-captured (Intel RealSense D455 + phones), top-down + 4 side angles, **boxes + laboratory-measured weights in grams** (YOLO 6th column), small/medium/large portion buckets; splits 9,521/2,365/2,197; public leaderboard. Source: https://huggingface.co/datasets/issai/Food_Portion_Benchmark; paper: IEEE Access 13:152033–152045, DOI 10.1109/ACCESS.2025.3603287 (CC BY); code https://github.com/IS2AI/Multitask-Food-Portion-Estimation (accessed 2026-10-28). **License discrepancy to note:** HF dataset card says **CC BY-NC 4.0**; OpenAlex marks the article cc-by (paper vs dataset distinction). Correction from previous draft: the underlying detector is YOLOv12 (arXiv 2502.12524 is the YOLOv12 paper, **not** the FPB paper). Central Asian (Kazakh) cuisine. **Use as: portion-geometry teacher; eval-only preferred given NC.**

### LeFood-Set (Brawijaya + Okayama)
- 524 before/after pairs, Indonesian dishes, grams from digital scales; CC BY 4.0; DOI 10.17632/cchsk79jkt.1 https://data.mendeley.com/datasets/cchsk79jkt/1 (accessed 2026-10-28). **Use as: leftover-logic smoke test.**

### FLIC (Milano-Bicocca + Parma) — measured, public release
- 401 full + 401 leftover canteen trays, pixel masks + physically measured mass (avg 121.56 g/item full trays); Applied Sciences 16(11):5465, DOI 10.3390/app16115465, open access (https://www.mdpi.com/2076-3417/16/11/5465). The paper links the [dataset folder](https://drive.google.com/drive/folders/1IGCjr7y-_zsZfHTsL4CyxdkspTp8Uhnt) (reviewed 2026-10-30). Confirm dataset terms before reuse.

### ECUSTFD
- 2,978 images, 19 whole-food types, per-object weight_g + volume with 25 mm coin calibration; https://github.com/Liang-yc/ECUSTFD-resized- (accessed 2026-10-28). Single items, not plated; license unstated.

### Sri Lanka 2,380-image weighed set (Wimalasiri & Sahoo, arXiv 2405.16478, May 2024)
- 2,380 images, **14 food types** (cherry tomato, oatmeal, steamed rice, stir-fried spinach, sweet corn, grape, guava, orange, papaya, pineapple, red apple, steamed bun with meat, sweet potato, toast bread), boxes + weights; portions largely fixed per class (e.g., 100 g / 150 g rows in Table V). **Not Indian** (Sri Lankan/Taiwanese; generic whole foods); **no public release stated in the paper** (accessed 2026-10-28). Nearest-miss by geography, but fails A (cuisine, plated meals) and is unavailable.

### Mediterranean weighed sets (Konstantakopoulos et al., Univ. of Ioannina)
- EMBC 2023: 5,177 images / 50 Greek foods, reference card in frame, grams (22.6 g mean error model); Sci Rep 13:21040 (2023, DOI 10.1038/s41598-023-47885-0): 23,052 images / 226 dishes / 24,996 weighed records. Sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC10686975, https://pubmed.ncbi.nlm.nih.gov/38082778 (accessed 2026-10-28). **Public download of the weighed images not located** (the related MedGRFood classification set exists but without mass). Not Indian; not confirmed available.

### MM-Food-100K (Humanbased-AI, HF) — pseudo-weights, fails B explicitly
- 100k rows: image_url, dish_name, ingredients, `portion_size` strings like "chicken:300g", nutritional_profile, cooking_method; arXiv 2508.10429; license **OpenRAIL**; https://huggingface.co/datasets/Humanbased-AI/MM-Food-100K (accessed 2026-10-28). Sampled rows are generic Asian/Western dishes (no visible Indian coverage); **portion grams are annotator/LLM estimates, not scale measurements** — fails B by the owner's definition. Documented to prevent future confusion.

### FoodWeight1.4M (ICME 2025)
- 1.4M images / 1,550 categories, "weights precisely measured", supermarket scenarios; DOI 10.1109/ICME59968.2025.11209123. **No public release found** (accessed 2026-10-28); packaged-goods domain.

## 3. Rejected: label-only (no mass) — short table

| Dataset | Indian? | Contents | Source (accessed 2026-10-28) | Why out |
|---|---|---|---|---|
| Khana (Ashoka) | Yes | 131K+ imgs, 80 classes, taxonomy; Swiggy/Zomato-scraped; non-commercial; 6.4 GB Drive | https://khana.omkar.xyz; arXiv 2509.06006 | Labels only; keep as (b)-fallback if gallery needs expansion |
| ITD (CVIT) | Yes | 796 plates, 7,900 imgs, 50 dishes, masks; same lab as WED | `https://cvit.iiit.ac.in/images/datasets/food_nutrition/ITD.tar.gz` | Masks, no mass; still useful as segmentation teacher under WED rules |
| IndianFood10/20 (IIIT-D Bagler lab) | Yes | 11,547 / 17,817 imgs, 10/20 classes, YOLO boxes incl. thali platters; Instagram-scraped; IEEE DataPort DOI 10.21227/a7h5-2d06 | arXiv 2205.04841 | Labels only; license unclear |
| Kaggle Indian Food Images + mirrors | Yes | ~80 classes / ~4k imgs; CC BY-NC-SA (already tracked); Apache-2.0 / CC0 re-uploads exist | kaggle.com/datasets/tastypev/indian-food-images-dataset | Labels only; gallery prototypes only (per `docs/licenses.md`) |
| Food Wise AI (IEEE DataPort, Sep 2026) | Yes | 21 Indian classes, classification | https://ieee-dataport.org/documents/food-wise-ai-multi-class-food-image-dataset-food-recognition-and-intelligent | Labels only |
| **RASOI** (NCVPRIPG 2025 challenge, FKG.in) | Yes | Composite thalis with **bounding boxes + labels** + standalone recipes; CC BY-NC-SA 4.0; Kaggle-hosted | https://fkg-india.github.io/library/datasets (accessed 2026-10-28) | Boxes/labels only, no mass — **strongest new thali-layout lead from the sweep**; gallery/segmentation candidate |
| FoodLens (Google Research) | Yes | 30K restaurant-menu images, 140+ dishes, multi-label + fine-grained hierarchy; Springer DOI 10.1007/978-3-032-01169-5_16 (2025) | https://research.google/pubs/foodlens-fine-grained-and-multi-label-classification-ofindian-food-images (accessed 2026-10-28) | Labels only; **no public release found** (likely internal Google data) |
| IndianFoodNet30 (Agarwal et al., 2023a) | Yes | 11,487 single-item images, 30 classes; described as "publicly available" by Garisa et al. 2026 (DOI 10.3389/fcomp.2026.1753764) | Frontiers paper §3.1 (accessed 2026-10-28) | Labels only; single items (no plates, no mass) |
| Datacluster Labs Indian-Food-Image-Dataset (SNTL84 GitHub re-upload) | Yes | ~3,500 real-world mobile-captured images, classification + detection annotations | https://github.com/SNTL84/Indian-Food-Image-Dataset; https://github.com/datacluster-labs/Indian-Food-Image-Dataset (accessed 2026-10-28) | Labels only; commercial crowd-sourced provenance (Datacluster) |
| The-massive-Indian-Food-Dataset + HF mirrors (bharat-raghunathan, MiteshRege, N16069, muhammadbilal5110, rajistics) | Yes | Multi-class scraped images; one CC0 source, mirrors CC0/unknown | https://www.kaggle.com/datasets/anshulmehtakaggl/themassiveindianfooddataset; https://huggingface.co/datasets/bharat-raghunathan/indian-foods-dataset (accessed 2026-10-28) | Labels only; scrape provenance |
| Food Recognition 2022 (AICrowd/Swiss) | No | 43,962 imgs, 498 classes, Swiss Food ontology, masks; includes weight/volume **estimates** | https://datasetninja.com/food-recognition (accessed 2026-10-28) | Weights are estimated, not measured (fails B); not Indian |
| Food-101 / UEC-100/256 / UNIMIB2016 / FoodSeg103 / FoodNExTDB / Taiwanese-Food-101 | No | Standard label/box/mask benchmarks (details in prior draft) | see prior draft section B6 | Not Indian, no mass |
| IFCT 2017 (Zenodo npm `ifct2017` + `pictures`), Kaggle "Indian Food Nutritional Values" (250+ dishes, per-100g), Mendeley "Indian Packaged Foods" (852 products), IndicRecipeNutri (219,386 recipes) | Yes | Nutrient tables / composition / recipes + tiny representative thumbnails | https://zenodo.org/records/7088653; kaggle.com/datasets/batthulavinay/indian-food-nutrition; https://data.mendeley.com/datasets/rhswn9z9xr/1; zenodo.org/records/22729969 | No portion images; per-100g label data (feeds nutrient lookup, not mass head) |

## 4. Dead ends / near-misses (quantified)

**Citation-trail work (as instructed):**
- **WED citing papers (Semantic Scholar API, 2026-10-28): exactly one** — "YOLO-MCD: An Efficient Detection Method for Multi-Dish Recognition", J. Food Science 2026, DOI 10.1111/1750-3841.71484 — Chinese-dish **detection only** (self-built Chinese multi-dish set, no mass, not Indian). No other Indian mass dataset surfaced via this lead.
- **FPB citing papers (OpenAlex, 2026-10-28): 8** — reviews, human-vs-AI portion comparison (J. Nutrition 2026), and Central-Asian detection follow-ups; none introduces an Indian or new South-Asian measured dataset.
- Google Scholar citation search: no additional citing works surfaced in web search; the WED paper's ACM listing (Jul 2026) is too recent for a deep citation tree.

**Dietetics near-misses (weighed Indian/South-Asian photos exist in papers, but no public CV dataset):**
- **Sharma & Chadha 2020** (Current Research in Nutrition and Food Science 8(1), DOI 10.12944/CRNFSJ.8.1.17): portion sizes of common foods for 60 urban Delhi adults, **weighed on SECA Culina 852 (1 g precision)**, grams derived for North Indian foods; follow-up software paper: Sharma & Chadha 2023, Minerva Nutrition 16(4):293–312, DOI 10.3233/MNM-230039 (paywalled). **What it lacks:** photo series not released as a dataset; what it would take: contact authors (Delhi) for the photograph series + weight tables.
- **Nepal photographic food atlas** (Public Health Nutrition, 2016; PMC10271048, PubMed 26996822): 40 locally prepared foods, life-size photos, weighed portions (rice series 50–1000 g; rice/dal/vegetable-curry validation vs weighed intakes). **South Asian + kitchen-scale truth, but:** atlas images published only as paper figures; no downloadable dataset; what it would take: author contact (unlikely; 2016 paper).
- China (799 pics/303 foods), Singapore (298 entries, 1 g precision, Frontiers in Nutrition 2026, DOI 10.3389/fnut.2026.1930409), Japan (209 items) photographic atlases — same pattern: weighed, paper-only, not Indian.
- **Shodhganga / Indian theses:** searches for thali/portion/weight-estimation image datasets returned nothing usable (portal searches surfaced no dataset-bearing thesis, accessed 2026-10-28).

**Other dead ends (unchanged from prior draft):** "NSFStats" (no such dataset found), "NFood-101" (not found), FoodWeight1.4M (no release), Amrita Vishwa Vidyapeetham (Indian-food CV papers, e.g. 17-class YOLOv11m set, but no public dataset: https://www.amrita.edu/publication/yolo-v11m-powered-food-detection-and-nutritional-analysis-for-indian-cuisine), IndianFoodNet (~5,500 imgs / 30 classes, described in arXiv 2509.16286; no release; **distinct from IndianFoodNet30**, which Garisa et al. 2026 call publicly available — see rejected table), FLIC download (no link), IIIT-H "Indian food map" (blog-stage, The Hindu 2026-06-05, no dataset release).

### Exhaustive sweep (2026-10-28) — audited venue list (10 categories, all exhausted)

Per-owner instruction, an internet-wide pass across categories not covered by the deep pass. **Outcome: no dataset cleared both bars; the bar-A×B intersection remains WED-only.** New near-misses were added to the rejected table (RASOI, FoodLens, IndianFoodNet30, Datacluster/SNTL84, massive-Indian mirrors, Food Recognition 2022).

1. **Hugging Face Hub (API search):** `thali` → only irrelevant hits (Arabidopsis thaliana DNA sets, "Thalia-Functions-13k"); `indian food` → only known label-only mirrors (rajistics, N16069, MiteshRege, muhammadbilal5110 — all re-uploads of the same 6,269-row Kaggle set); `food weight` → **zero results**. Nothing new.
2. **Roboflow Universe:** IndianFood-7 (817 imgs, 7 classes, boxes, search-engine crawled, CC BY 4.0, by Ahuja scholar) and food-app/indian-food-dca77 (3,976 imgs, classification) — label-only. No Indian mass set.
3. **datasetninja / Supervisely:** food category (421 datasets total indexed) → FoodSeg103 (Apache-2.0), Food Recognition 2022 (CC0, estimated weights) — no Indian mass set (see rejected table).
4. **Government/institutional (data.gov.in, ICMR-NIN, ICAR-CFTRI, FSSAI):** only composition tables, lab manuals, tender notices — no image datasets. Dead end.
5. **GitHub (code + repo search):** recipe-text CSVs (Archana's Kitchen, 6,871 entries — text only); SNTL84/Datacluster re-upload (label-only); **foodron.ai** — commercial service advertising 30,000+ pre-annotated Indian food images (600+ dishes, real home-thali photos) — **paid annotation service, contact-gated, not a public dataset**; recorded as a commercial lead only.
6. **Kaggle (harder terms):** The-massive-Indian-Food-Dataset (CC0, scraped), ashishpadala (2,000 imgs / ~16–20 classes, Google Images), iamsouravbanerjee (4,000 / 80), batthulavinay nutrition CSV (INDB-derived, per-100 g), shellel.com (1,054 dishes) and indiancalorie.com (10,000+ dishes; katori=150 g, roti=40 g conventions) — portion-**convention** references with no images, useful only as priors. Nothing measured.
7. **Multilingual (Hindi):** "थाली भोजन डेटासेट / भारतीय खाना छवि" → only known mirrors + recipe CSVs. Nothing new.
8. **WED author pages:** yasharora102.github.io → empty template page (no projects listed). adityaarun1.github.io → full publication list checked (accessed 2026-10-28): **no food/mass follow-up after ICVGIP 2025**; author now at Adobe MDSR (diffusion/visual reasoning). Biryani-paper code released at github.com/farzanashaju/how-does-india-cook-biryani — cooking videos, no mass.
9. **Benchmarks, surveys, workshops:** "FoodRecognitionBench" queries → nothing with Indian mass annotations (the AICrowd Food Recognition 2022 line is the main "benchmark" and fails B). CVPR 2025 MTF workshop → Khlaisamniang et al. two-step MLLM paper (Nutrition320 = Nutrition5k subset + Gindee121 app images; no new dataset). Frontiers in Computer Science, 10 Mar 2026, DOI 10.3389/fcomp.2026.1753764 (Garisa, Kumar, Singh, SRM University-AP; SAM + SE-DenseNet121 for thali recognition) → uses IndianFoodNet30 + 50 unannotated thali photos; **data availability: "inquiries directed to the corresponding author" — no release**. DietAI24 (Communications Medicine, DOI 10.43856/s43856-025-01159-0) → FNDDS portion standards, US-centric, no dataset release.
10. **Social/academic request channels (Reddit, Hacker News, Stack Exchange):** only nutrition-CSV chatter; no measured-dataset requests, leaks, or releases.

## 5. Recommendation — honest top line

**WED is the only public dataset that clears BOTH bars (Indian + kitchen-scale grams on real plated food).** After a genuinely deep pass — every WED citation followed, FPB citations checked, Mendeley/IEEE-DataPort/Zenodo/Shodhganga swept, dietetics literature mined — no second qualifying dataset exists as of 2026-10-28.

Nearest misses, quantified:
| Candidate | Has | Lacks | Cost to fix |
|---|---|---|---|
| Sharma & Chadha (Delhi) | Weighed North-Indian portions (1 g scale), photo series exists | Photos+weights not public | Email authors; low effort, unclear outcome |
| Nepal food atlas | South Asian, weighed, life-size photos | Not public, 2016, single-portion series | Author contact; likely stale |
| Sri Lanka 2,380-img set | Boxes + grams, Asian | Not Indian cuisine, whole foods, no release | Author contact |
| FLIC | Measured trays + masks | No Indian dishes | Public dataset folder; confirm terms |
| MedGRFood-weighed | 23k weighed images w/ reference object | Greek cuisine, release unverified | Author contact |
| RASOI (NCVPRIPG 2025) | Real composite Indian thalis + boxes, CC BY-NC-SA 4.0, on Kaggle | Boxes only, no mass | None needed for gallery/segmentation work — usable under NC for research |
| MM-Food-100K | 100k images + portion strings | Grams are estimated (fails B), OpenRAIL, no Indian focus | None — unusable for (a) by definition |

**Therefore:** robustness for the mass head must come from protocol work, not a second dataset:
1. **Cross-validation and augmentation on WED** (multi-view splits already defined in `tools/train_weight_head.py` seams; stress suite in `tools/stress_suite.py`).
2. **Transfer via protocol-identical but non-Indian teachers** — Nutrition5k (per-ingredient ±1 g scale truth) and FPB (lab grams, portion buckets) as auxiliary fine-tuning sources, keeping Indian eval (WED test 248 views) uncontaminated; treat FPB as eval-only if licensing conservatism is preferred (HF card CC BY-NC 4.0).
3. **School-capture fine-tuning remains the primary domain adaptation path** (as already planned).
4. Optionally: author-contact campaign (Sharma & Chadha Delhi; Sri Lanka set) — cheap, but each is a long-shot. FLIC is now publicly linked by its paper; see the row above.

**Classifier gallery:** nothing in this pass changes the gallery plan — Khana / Kaggle prototypes (label-only, licenses tracked) remain the (b) sources; they simply no longer count toward the mass-head bar.

## 6. Gaps / decisions needed
- **WED/ITD dataset license terms** — still unconfirmed (M9 gate). Now more critical: WED is the sole qualifier, so its terms govern everything.
- **Approve "protocol transfer" plan**: fine-tune/cross-train on Nutrition5k + FPB, evaluate on WED test; accept that dish-label transfer is weak (US/Kazakh cuisine) while scale/portion geometry transfers.
- **Author-contact shortlist** (Delhi photo series; FLIC; Sri Lanka 2,380): pursue or drop?
- **Gallery add-on decision**: RASOI (CC BY-NC-SA 4.0, real composite thalis + boxes) is the strongest new (b)-side candidate found in the sweep — adopt for segmentation/layout prototyping or keep current Kaggle-prototype posture?
- **FPB train-vs-eval posture** under CC BY-NC 4.0.
- Watch items: CVIT biryani-video release, FoodWeight1.4M release, FoodLens (Google) release — re-check quarterly.
