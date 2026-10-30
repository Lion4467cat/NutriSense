# NutriSense Glossary

Domain terms as the code uses them. Terms map to `engine/contract.py` unless noted.

**Verdict**
The single scored outcome of an analysis: `PASS`, `BORDERLINE`, `FAIL`,
`cannot_verify`, or `out_of_scope`. Owned by the compliance stage
(`engine/compliance.py`); carried as a closed vocabulary on the wire.
`ESTIMATED` remains a valid wire value **only for legacy records** — since
the 2026-10-11 graduation, no-card plates are scored like any other plate
and instead lead their reasons with the no-reference-card estimate
disclaimer.

**Reason**
A canonical, human-readable explanation of *why* a verdict came out as it
did — every verdict has at least one, including PASS. Shape:
`{kind, text}`. Reasons are data, not logs: the UI renders them directly.
The `kind` vocabulary (`ReasonKind`) is open on the wire — the UI shows a
default glyph for kinds it does not know.

**Failure**
A hard fault: a stage crashed or a gate rejected the input. Shape:
`{kind, stage, error}`. `failures` appears on the wire only for hard faults;
each failure generates its own reason. Silent degradations (e.g. anchor
falling back to prior tier) are *not* failures — they show up in the stage's
detail block, `assumptions`, or `coverage.factors` instead.

**Stage**
One guarded step of the pipeline: `input`, `anchor`, `segment`, `classify`,
`depth`, `portion`, `nutrition`, `compliance`. Each has a `StagePolicy` —
`fatal` (exception → Failure → `cannot_verify`, never HTTP 500) or
`degrade` (exception → registered fallback, logged, no failure entry).

**Anchor tier**
How scale was measured: `measured` (reference card detected) or
`prior` (size/assumption priors). Prior tier sets coverage by grams source —
`estimated_weight` (0.90, learned head) or `anchor_prior` (0.60, geometry;
still can never issue PASS/FAIL) — and every prior-tier verdict leads its
reasons with the `no_reference_card` estimate disclaimer.

**Learned weight tier**
Prior-tier grams from the WED-trained head (`models/weight_head.pt`,
`data/wed_dishes.yaml` mapping) instead of geometry. Triggered only when
the anchor is `prior` and the checkpoint loads; any failure silently
degrades to the geometry path. Reported as `grams_source: learned_weight`
with `base_method: learned_weight`; per-class σ comes from the carved
validation split (`data/weight_head_sigma.yaml`). Graduated 2026-10-11
(ADR 0002 amendment): scored like a measured plate under the
`estimated_weight` coverage factor (0.90), always with the no-card
estimate disclaimer; local spot-check remains as follow-up evidence.

**Classifier confidence**
`classification.confidence`, returned by the dish classifier. In gallery
mode this is the top-1 softmax over serving-label scores; in text-fallback
mode it is the top sigmoid probability. It is not the gallery similarity
score and is not the pipeline's coverage score.

**Gallery match score**
`classification.match_score`, returned by gallery classification. It is the
best serving-label score, calculated from the top-3 mean cosine similarity.
The classifier compares it with `gallery_match_threshold`; it is not a
probability and does not have to equal classifier confidence. Text-fallback
classification has no gallery match score (`null`).

**Policy**
The whole rule set an analysis was judged by — verdict P-zones (`pass_p`,
`fail_p`), coverage gates (`pass_min`, `fail_min`), the mandatory nutrient
set, every band's minima and directions, coverage factor values, and the
capture lint limit (`lint_min_side_px`) — plus `policy_version`, a 12-hex
digest over all of those sources (a strict test flips each rule and demands
the digest move). Served on every `/analyze` response and on `/menu`;
records store it so old results can tell which rule set produced them.
Records from before the contract carry no policy block and read as
`unknown`; the UI only claims "judged under an earlier policy" when today's
policy is loaded and ready.

**Coverage**
Overall coverage score (product of applicable evidence/degradation factors)
gating PASS/FAIL. This is separate from dish classifier confidence; see
`engine/compliance.py`.

**School mode**
The app mode for PM POSHAN compliance. Dishes come from the school menu
(the single source of dish truth), the capture carries `day` + `band`, and
the analysis ends in a Verdict judged under Policy. Non-menu dishes stay
`out_of_scope` here.

**General mode**
The app mode for any meal. Dishes come from the full WED serving set
(41 classes), the capture carries no `day`/`band`, and there is no PM
POSHAN compliance scoring — the analysis reports grams and nutrients
compared to a Daily goal. The user switches between the two modes.

**Daily goal**
The nutrient amounts one person should eat in a day. Defaults come from
WHO tables by age, gender, and physical activity level; the user may
enter their own goal instead. A meal is shown as a share of the Daily
goal.
