# 003 — Serve all 41 WED classes: serving expansion, recognizer gallery, off-menu pipeline path

- **id**: 003
- **branch**: `spec-002-integration` (ticket `02-serve-all-41-classes`, spec 002 decisions 3+4)
- **date**: 2026-10-28
- **author**: agent (implementer subagent, spec-002-integration)

## Hypothesis

The pipeline can recognise and estimate grams for all 41 WED dish classes
without touching the weight head, sigma file, eval code, or the LOCKED
split. The serving mapping (`data/wed_dishes.yaml`) gains entries so every
non-background WED class resolves; the recognizer gallery rebuilds from WED
train ROI crops over all 41 classes (RASOI cleared as a gallery-capable
complement by ticket 00 but not used in this run — WED train is
sufficient); the abstain threshold is re-derived from the new gallery's
leave-one-out evaluation instead of the 2-class 0.82 assumption. Feeding
recognition for previously unreachable (formerly `out_of_scope`) dishes
through the unchanged deployable portion path (learned head where the dish
has WED slots, geometry otherwise) should leave DEV head metrics untouched
— the head, its checkpoint and `data/weight_head_sigma.yaml` are not
modified in this entry.

**Interpretation recorded (ADR 0003 + spec decision 2, mode-agnostic
`/analyze`):** a recognized-but-not-on-menu dish is NOT `out_of_scope` —
the dish IS recognized. It gets grams + nutrients like any other plate,
with Verdict `cannot_verify` and the new Reason kind `off_menu_dish`
leading its reasons. `out_of_scope` remains ONLY for unrecognized/abstained
captures and for menu dishes explicitly scoped out (`wheat_product`).
The no-card estimate disclaimer (`no_reference_card`, prior tier) still
appears on off-menu prior-tier plates per spec story 22, after the leading
`off_menu_dish` reason. Menu dishes keep their exact current verdict path.
School-mode UI treatment of these results is ticket 05's job.

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| DEV MAE (g) | 15.034 | unchanged — paired 95% CI vs the 2026-10-14 keep run covers 0 | head/checkpoint untouched; expansion serves it more classes |
| DEV coverage_90 | 0.8522 | unchanged — paired 95% CI covers 0 | sigma file untouched (calibration is ticket 03) |
| gallery LOO accuracy | 1.000 (46 golds, 2 classes) | recorded for the 41-class gallery | WED train ROI crops (+46 golds retained for menu-dish path) |
| abstain threshold | 0.82 (assumed, 2-class gallery) | re-derived for the 41-class gallery, set in `params_status.yaml` with status+provenance | never inherited |
| resolvable WED classes | 3 menu dishes (4 slots) | 41/41 | data-level test |

## Success criterion (written BEFORE coding)

All of the following, checked in order:

1. **Serving coverage (data):** a data-level test asserts every one of the
   41 non-background WED classes in `data/wed/index_map.json` resolves —
   either into an existing menu-dish `wed_slots` byte-for-byte entry, or an
   `off_menu` serving entry with `wed_slots` resolvable in the index and
   components whose `generic_id` exists in `data/nutrients.yaml`; the four
   existing menu-dish entries and the `generics` block keep their current
   byte content.
2. **Off-menu pipeline behaviour (seams):** with a recognized off-menu
   serving key, the deployable path produces grams + nutrients,
   `verdict = cannot_verify`, `reasons[0].kind = "off_menu_dish"`, empty
   `failures`, populated `path_used`, and `compliance = null` (no school
   compliance for off-menu dishes). The existing invariants still hold:
   classify-unrecognized ⇒ `cannot_verify` with the `unrecognized` reason
   and no portion; menu-dish scope rejection (wheat_product) still yields
   `verdict = out_of_scope`; menu dishes still run through the existing
   seam tests unchanged (learned-head ×5, deps injection, depth wiring).
3. **Gallery + threshold:** `data/gallery.npz` rebuilt in the same artifact
   format (emb/labels/sources/model) covering entries for all 41 WED
   classes (WED train only; RASOI cleared for gallery use by ticket 00 but
   NOT used this run — recorded in the entry); its LOO evaluation (gallery
   method, same top-3 match metric) is recorded here with accuracy and the
   min correct-class score; the abstain threshold is re-derived from that
   LOO (a value at/below the min correct-class LOO score, above the
   synthetic-render negative) and set in `params_status.yaml` marked
   `status: calibrated` with provenance.
4. **DEV head metrics do not move:** one fresh `tools/run_eval --tier dev`
   run completes on the untouched checkpoint; paired plate-bootstrap CI
   (`tools/compare_runs.py`, DEV tier) of ΔMAE and Δcoverage_90 vs the
   last kept DEV run (`data/reports/run_eval_dev_aug002.json`, 15.034 g /
   0.8522) covers 0. No LOCKED read.
5. **Suite + gates:** hermetic non-GPU suite green, ruff 0 findings,
   pyright baseline unchanged.

Decision is `keep` only if 1–5 all hold; any failed element ⇒ `revert` the
corresponding change (the failure names which element).

## Change

- `data/wed_dishes.yaml` — added `serving:` (all 41 class names → target:
  3 menu-equivalent classes route to their menu dish, 38 to same-key
  `off_menu` entries) and `off_menu:` (38 entries: display name, own
  `wed_slots` slot, one component each with `type`/`generic_id`/`share`/
  `density_g_ml`, `nutrition_source: generic`). Existing `dishes:` and
  `generics:` blocks byte-for-byte unchanged.
- `data/nutrients.yaml` — 16 new `assumed` rows for the generic table
  (dals, veg curries/fries, rasam/soup, chutney, pickle, raita, papad,
  boondi, chicken biryani, salad, 4 fruits); steamed-rice/sambar/veg-briyani
  reuse existing rows. Off-menu dishes keep `nutrition_source: generic`
  (the generic per-100 g table, never the official school menu).
- `data/conversions.yaml` + `engine/mc.py` — one new `as_is` yield (1.0,
  assumed, diagnostic-only) and type→yield entries so served-as-is items
  (fruits, curd, chutney, pickle, papad, boondi, payasam, soups) keep an
  honest raw-equivalent diagnostic; existing types unchanged.
- `engine/contract.py` — `ReasonKind.OFF_MENU = "off_menu_dish"`;
  `frontend/src/types/contract.gen.ts` regenerated (kinds stay open).
- `engine/pipeline.py` — classify step: unknown-to-menu dish keys resolve
  through the `serving:` map (menu dish → current path incl. SCOPE gate;
  off-menu entry → dish block from the entry); off-menu plates run
  portion + nutrition and end `cannot_verify` with `off_menu_dish` leading
  reasons (plus `no_reference_card` disclaimer on prior tier),
  `compliance` null. `_wed_slots_for_dish` now also reads `off_menu`.
- `models/food_classifier.py` — serving-key recognition: scores are
  computed per gallery label (top-3 mean, unchanged metric) and aggregated
  to serving targets (menu keys and the `serving:` map); text fallback and
  `build_gallery` validation accept the serving label set (WED class names
  + menu keys).
- `tools/build_gallery.py` — `--wed` mode embeds ROI crops from
  `data/wed_manifest.jsonl` train rows + labelIds masks (embeddings +
  relative source paths only — no WED image data lands in the repo),
  per-class cap, deterministic sampling; `--loo` runs the gallery-method
  leave-one-out evaluation printing accuracy, min correct-class match
  score and the synthetic-render negative score.
- `data/gallery.npz` — rebuilt (46 golds retained + WED-train crop
  entries for the 41 classes + `bisibelebath` crops).
- `data/params_status.yaml` — `gallery_match_threshold` re-derived from
  the LOO (`status: calibrated`, provenance note).
- Tests: `tests/test_wed_serving.py` (data-level coverage), seam tests in
  `tests/test_pipeline_seams.py` (off-menu recognized; unrecognized and
  scope-rejection invariants), `tests/test_s2.py` updated to the 41-class
  gallery reality (GPU-marked), unstitched behaviour untouched.

## Sources

- `specs/002-general-mode-and-calibration/spec.md` — decisions 3, 4 + stories 3, 4, 15, 22.
- `docs/adr/0003-two-app-modes.md` — two modes; no compliance Verdict for off-menu dishes.
- `docs/licenses.md` (ticket 00, verified 2026-10-28) — WED: no published terms → local-only, cite-only, images never committed (gallery stores embeddings, not images); RASOI: CC BY-NC-SA 4.0 + mandated credit line "**Created and maintained by the Food Computing Lab, Ashoka University, India.**" — cleared for gallery/segmentation prototyping only; recorded but not used here.
- `docs/research/indian-food-datasets.md` — WED class taxonomy; RASOI terms.
- `docs/ledger/002-dinov2-encoder.md` — the kept DEV run this entry pairs against.
- WED paper: Arora et al., "What is there in an Indian Thali?", ICVGIP 2025, DOI 10.1145/3774521.3774594.

## Result

All five success criteria hold (checked 2026-10-28).

| comparison | tier | mae_g base → cand | paired diff [95% CI] | coverage base → cand |
| --- | --- | --- | --- | --- |
| run_eval_dev_aug002 → spec-002 dev (mapping expansion, same checkpoint) | dev | 15.034 → 15.034 | 0.0 [0.0, 0.0] | 0.8522 → 0.8522 |

The candidate run (`data/reports/run_eval_dev_spec002_expansion.json`,
`seed=42`, 108 views / 21 plates, 1218 samples, `skipped_no_sigma=0`,
wall 5.04 s, peak VRAM 121 MB) is bitwise-identical to the keep run on
every DEV metric, re-verified after the final code edits — the head path
is provably untouched. Reported to `runs/experiments.jsonl`; paired
comparison in `data/reports/compare_002_vs_expansion.json`. The stress
set is intentionally not part of the candidate run (idle-time budgeting;
stress parity is a lock-harness property).
No DARK or LOCKED read in this entry.

Gallery (criterion 3, recorded numbers):

- Artifact `data/gallery.npz`: **997 = 46 gold photos kept + 951 WED
  train ROI crops** over **44 distinct labels** — all 41 WED class names
  (cap 24/class, e.g. phulka 24, boondi 19, chutney 19, muskmelon 23,
  bisi-bele-bath 24) + menu keys `rice_sambar` (25) / `vegetable_rice`
  (21). Same artifact format; model column `google/siglip2-base-patch16-224`;
  embeddings only (no WED images enter the repo).
- Leave-one-out over all entries (gallery method, top-3-match metric,
  per-label top-3 mean → serving targets, max across labels): **accuracy
  0.7803 of 997; min correct-class match 0.8291, mean 0.9254; min wrong
  match 0.8284**. The LOO misses concentrate in visually-similar
  curry/dal/fruit crop classes (e.g. Banana→curd, Bottle-gourd-curry→
  non-spicy-curry, Muskmelon→muddha-pappu) — the recognition task updates
  only open-set ABSTENTION, not the serving-target argmax, so no correct
  LOO entry acts as a threshold floor; recorded as stated, no knee.
- Synthetic-render negative (renderer scene through `classify_dish`):
  match **0.7158** → abstain (below any plausible threshold).
- **Threshold set to 0.80** in `data/params_status.yaml`
  (`status: calibrated`, provenance notes the 997-entry LOO, min correct
  0.8291, negative 0.7158, date). Sanity: golden held-out menu-dish photos
  still recognized at 0.928–0.963; synthetic at 0.80−0.084. The 2-class
  LOO floor documented for 0.82 (0.857) is superseded.

Verdict mapping (criterion 2, seam coverage): off-menu recognized dish →
grams + assumed-table nutrients on the wire, `verdict = cannot_verify`,
`reasons[0].kind = "off_menu_dish"` (+ `no_reference_card` on prior tier),
`failures` empty, `compliance` null, `path_used = "learned_head"`
(rajma, head slots 220.0 g). Invariants held: unrecognized →
`cannot_verify`/`unrecognized`; phulka → `out_of_scope` via SCOPE; menu
seams ×5 unchanged. Gates and hermetic suite green.

## Decision

**keep** — criteria 1–5 all hold: 41/41 serving coverage with menu/
generic blocks byte-identical; off-menu semantics + preserved invariants
(seam 13); 41-class gallery with LOO + calibrated threshold 0.80 between
the synthetic negative (0.7158) and the correct-class LOO floor (0.8291);
DEV paired CI [0.0, 0.0] on both metrics against the ledger-002 keep run;
hermetic suite 180 passed / 10 GPU deselected (190 with `-m gpu`),
ruff 0 findings, pyright 212 = baseline 212. Deviation from the expected
table: LOO accuracy is 0.7803 (no 1.0) at crop granularity — accepted:
its role is threshold derivation, not closed-set serving accuracy, and
the deployment-level sanity (menu dish re-captures 0.93+ ; synthetic
abstains) holds. Threshold is a recognition-scope calibration only; grams
paths, checkpoint, sigma file and the LOCKED split are untouched.

## Follow-ups

- RASOI as a real-capture gallery complement for classes WED shows only in
  the kiosk setting — cleared (ticket 00), deliberately not drawn on here;
  revisit if field captures misclassify.
- Off-menu verdicts are school-mode-invisible today; ticket 05 owns the UI.
- Interval calibration (ticket 03) — untouched per this entry's scope.
