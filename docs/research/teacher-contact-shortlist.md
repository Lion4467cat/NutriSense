# Teacher-dataset author-contact shortlist — concrete asks

**Ticket:** `06-robustness-program` (spec 002 decision 11: author-contact
shortlist for measured non-Indian teachers) · **Date:** 2026-10-29.

Ground rule from the ticket: **no contact details invented** — only routes the
sources themselves state. Each entry: what exists, why it helps the weight
head, and the concrete ask.

## 1. Nutrition5k (Google Research) — already accessible; contact only for questions

- **Exists:** 5,006 cafeteria plates; per-ingredient weighed grams + USDA-based
  macros; overhead RGB(-D). Public, stated CC 4.0, directly fetchable (pulled:
  `docs/research/nutrition5k-transfer-prep.md`).
- **Why it helps:** the only large shippable corpus with per-item mass ground
  truth from a non-Indian meal style — the strongest transfer-teacher available
  at zero negotiation cost.
- **Concrete ask:** only if needed — (a) confirm the **exact CC 4.0 flavor**
  (the README names "Creative Commons V4.0" without a deed link); (b) any
  guidance on bulk per-file (overhead `rgb.png`) access etiquette / preferred
  download method to avoid hammering the bucket. Contact route: the GitHub
  repository's stated issue channel on
  https://github.com/google-research-datasets/Nutrition5k.

## 2. Food Portion Benchmark — FPB (ISSAI / Nazarbayev University)

- **Exists:** 14,083 images / 138 classes for food detection + portion-weight
  estimation; dataset card declares **cc-by-nc-4.0**; hidden test labels
  (benchmark posture). https://huggingface.co/datasets/issai/Food_Portion_Benchmark
- **Why it helps:** a community benchmark with a portion-weight evaluation
  protocol — useful as an **eval-only** generalization probe under its
  non-commercial license (per ticket: "FPB eval-only").
- **Concrete ask:** (a) permission for commercial-project evaluation use under
  cc-by-nc-4.0 terms as we currently understand them (eval-only, no artifact
  redistribution); (b) visible-labels sample counts for comparability. Contact
  route: the project page https://issai.nu.edu.kz/fpb/ (contact channel as
  stated on that page; not reproduced here so no details are invented).

## 3. North Indian weighed photo series (Sharma et al.) — the closest India-side lead

- **Exists (published figure of merit, corpus not confirmed open):**
  (a) Sharma & Chadha (2020), *Assessment of Portion Sizes of Food Items
  Commonly Consumed by Urban Indian Adults: A Preliminary Study* — urban Delhi
  subjects, 23 standardized items, digital-scale weighed conversions
  https://www.foodandnutritionjournal.org/volume8number1/assessment-of-portion-sizes-of-food-items-commonly-consumed-by-urban-indian-adults-a-preliminary-study/;
  (b) follow-up Sharma et al. (2023), *Development and evaluation of food
  photograph series software for portion size estimation among urban North
  Indian adults* (publisher record
  https://journals.sagepub.com/doi/10.3233/MNM-230039; corpus reusability
  unpublished).
- **Why it helps:** Indian cuisine plates **with weighed reference portions**
  — exactly the domain our 41-class head lives in; even a small series of
  weighed thali photos gives a domain-matched external validation set for the
  portion head (and Indian ground truth is otherwise only WED).
- **Concrete ask:** access to the photo series (photos + weighed portion
  labels) for research validation under any restriction they propose
  (evaluation-only acceptable); if the 2023 "software" carries the images,
  ask whether research access to that corpus is possible. Contact route: the
  2020 article's stated corresponding author (email printed on that article
  page; do not reproduce here).

## 4. LeFood-Set (2025) — openly licensed measured pre/post grams

- **Exists:** 524 before/after plate image pairs, 34 Indonesian food
  categories, digital-scale weighed before/after; Mendeley Data listing says
  **CC BY 4.0**. https://data.mendeley.com/datasets/cchsk79jkt/1 · paper
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12087991/
- **Why it helps:** direct continuation-of-eating supervision (leftover-aware)
  and an honest external check of grams reasoning on free-plated meals — small,
  cheap, zero-contact needed. A no-contact download.
- **Concrete ask:** none (open); contact the linked corresponding author only
  if the Mendeley license text diverges from CC BY 4.0 at download time.

## 5. Sri Lanka food atlas (Jayawardena & Herath 2017)

- **Exists:** food atlas for Sri Lankan adults, **125 foods** with serial
  weighed portion series (rice 100–800 g; curries in 15 g steps). Article CC
  BY 4.0: https://pmc.ncbi.nlm.nih.gov/articles/PMC7050724/ — but the
  supplementary material is described as "available to authorized users";
  full photographic reuse unclear.
- **Why it helps:** South-Asian-adjacent weighed portion series for a
  culturally close validation set.
- **Concrete ask:** research access to the atlas photo files + portion/gram
  table, with whatever license they require. Contact route: through the
  journal's author-affiliation channel stated in the article (do not invent).

## Priority order and next action

1. No-contact downloads first: LeFood-Set (CC BY 4.0), then batch-scale
   Nutrition5k overhead RGB (see transfer-prep note).
2. FPB eval-only probe behind its license terms.
3. Author contacts in order: Sharma (North-Indian series — highest
   domain value), Sri Lanka atlas, Google Research (license-flavor
   confirmation only).

**Rule respected:** no email addresses or author identities invented in this
document;
every entry points at a route the source itself states.
