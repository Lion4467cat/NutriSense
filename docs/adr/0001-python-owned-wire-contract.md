# ADR 0001: Python owns the wire contract, generated into TypeScript

- **Status:** Accepted
- **Date:** 2026-10-10

## Context

`POST /analyze` results were shaped in prose: the 14-key set lived in a test
assertion, reasons were bare strings, the unreadable-image path returned a
2-key stub, unguarded stages raised past FastAPI as 500s, and the frontend's
hand-written `types/api.ts` had drifted from the wire (it typed
`nutrition.wider_ranges` as `string[]` while the backend sends a boolean).
Thresholds (`0.9 / 0.1 / 0.85 / 0.90`, the 0.60 prior cap) were hardcoded in
three UI places, so a yaml change would silently desynchronize what the UI
claims the rules are from what the backend enforces.

## Decision

1. **One contract module** — `engine/contract.py` defines the envelope
   (16 keys), the closed Python vocabularies (`Verdict`, `ReasonKind`,
   `FailureKind`, `Stage`), the `Policy` block with its digest, the stage
   guard, and redaction. Every `/analyze` exit builds an `Analysis` and
   serializes through `to_wire()`; there is no second shape.
2. **Generated Zod, not hand-written types** — `tools/gen_contract_ts.py`
   renders `frontend/src/types/contract.gen.ts` from the same vocabularies.
   `tests/test_contract_gen.py` regenerates and diffs (stale file = red);
   the frontend decodes every response with `analysisSchema` and turns a
   Zod failure into `ApiError(500, "The backend returned an unexpected
   response.")`.
3. **Parity proven by fixtures, not trust** — two committed fixtures (happy
   path + unreadable capture) are produced by pytest and validated by vitest
   (`contract.parity.test.ts`). Cross-language drift fails one of the two
   test suites.
4. **Open kinds, closed verdicts** — the wire tolerates unknown
   `reasons[].kind` / `failures[].kind` values (UI shows a default glyph) so
   the backend can add a kind without a frontend release, while `verdict`
   and `failure.stage` are closed enums because exhaustiveness there is
   safety, not friction.
5. **Policy rides the wire** — the UI renders thresholds from
   `result.policy` (fallback constants only for pre-contract records), so
   `data/standards.yaml` stays the single source of truth.
6. **Stages guard, failures explain** — `stage(name, fn)` converts
   exceptions into Failure+reason pairs; `failures[]` is hard-faults only.

## Alternatives considered

- **Hand-maintained TS types mirrored by review** — status quo; already
  drifted once (`wider_ranges`), and nothing fails when it drifts again.
- **OpenAPI/FastAPI codegen** — generates request/response plumbing but not
  the reason/failure vocabularies, nullable-block semantics, or policy
  digest; would still need a second mechanism for fixtures.
- **TypeScript as the source of truth** — the wire is emitted by Python
  before any browser is involved; owning it in TS would invert the runtime
  dependency and leave the Python tests asserting against generated text.
- **Runtime-only structural typing (no schema)** — accepts anything,
  including a backend that silently drops `policy`; the whole point is to
  fail loudly on contract violations.

## Consequences

- Changing a vocabulary or envelope field requires
  `python -m tools.gen_contract_ts --write` (enforced by pytest).
- `frontend/` gains `zod` + `vitest`; `npm test` is part of the gate.
- Old localStorage records keep string reasons; the client normalises them
  (`utils/reasons.ts`) until the Stage 2 records migration.
- Follow-ups owned elsewhere: records v1→v2 with reason normalization and
  eviction fix (Stage 2), providers/stage-label wiring (Stage 3), the
  duplicated gate blocks stay duplicated by decision (candidate #1 of the
  2026-10-10 architecture review).
