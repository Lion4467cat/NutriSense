# NutriSense Glossary

Domain terms as the code uses them. Terms map to `engine/contract.py` unless noted.

**Verdict**
The single scored outcome of an analysis: `PASS`, `BORDERLINE`, `FAIL`,
`cannot_verify`, or `out_of_scope`. Owned by the compliance stage
(`engine/compliance.py`); carried as a closed vocabulary on the wire.

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
How scale was measured: `measured` (reference card or coin detected) or
`prior` (size/assumption priors). Prior tier caps coverage at
`anchor_prior_cap`, so it can never issue PASS/FAIL.

**Policy**
The thresholds an analysis was judged by — verdict P-zones (`pass_p`,
`fail_p`), coverage gates (`pass_min`, `fail_min`), coverage factor values,
and the capture lint limit (`lint_min_side_px`) — plus `policy_version`, a
12-hex digest over the yaml source values. Served on every `/analyze`
response and on `/menu`; records store it so old results can tell which rule
set produced them. Records from before the contract carry
`policy_version: "unknown"`.

**Coverage**
Multiplicative confidence score (product of degradation factors) gating
PASS/FAIL. Not a verdict nutrient — see `engine/compliance.py`.
