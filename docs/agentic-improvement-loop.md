# Agentic improvement loop status

**Status date:** 2026-10-30  
**Working branch:** `codex/synthetic-mask-spill-loop`

This loop is currently diagnostic. It has not changed serving code, model
weights, thresholds, configuration, or checkpoints. The ArUco weighed plates
remain EVAL-ONLY permanently; WED LOCKED is never a tuning signal, and the
existing WED DEV/CV evidence is already spent for selection.

## Completed diagnostics

| Ledger | Question | Result | Decision |
|---|---|---|---|
| [022](ledger/022-synthetic-mask-spill.md) | Does 25% vessel-pixel spill alone reproduce the large synthetic total errors? | The registered criterion failed: clean exact-mask totals were within 5% in 3/6 scenes; spill raised absolute error by at least 10 points in 0/6. | No estimator change. Oversized-mask spill alone did not explain the synthetic error pattern. |
| [023](ledger/023-synthetic-surface-area-integration.md) | Does integrating exact local surface area improve exact-mask synthetic estimates? | Failed: ≥5-point absolute-error improvement in 0/6, with a maximum regression of 21.11 points. | Candidate rejected; no estimator change. |
| [024](ledger/024-synthetic-card-position-scale.md) | Does moving a card around unchanged food change the global-scale estimate, and does card-plane homography reduce that spread? | The fixed three-position criterion was not fully assessable because one position per scene was unavailable. For the two measured positions per scene, global-scale spread was 54.45–79.26% and homography-area spread was 0.17–1.84%; exact values are in the raw JSONL. | Strong synthetic mechanism lead only; no serving change. Next validate the effect with a new preregistered, fully detectable placement protocol. |

The first 024 harness output accidentally used the detected scale for its
baseline, contrary to the preregistered planted-scale baseline. That exploratory
output is superseded. The committed run uses the planted renderer scale for
the baseline and the existing image detector's homography for the candidate;
the final stdout and JSONL are the source of its reported measurements.

## Direction forward

1. Keep all work under `experiments/oracle_ablation/` until a mechanism is
   isolated. Do not tune against ArUco plates, WED LOCKED, or already-spent
   development evidence.
2. Complete one preregistered synthetic card-position run with positions where
   every intended card is visible and passes the existing detector unchanged.
   Report detector misses rather than relaxing any gate.
3. If the spatial-scale mechanism reproduces, audit homography coordinates,
   plane-height assumptions, and error against renderer ground truth before
   proposing an opt-in implementation. Synthetic success alone is not a
   promotion gate.
4. Validate any opt-in candidate on newly collected, independent weighed
   captures with a preregistered protocol. Keep the default path byte-for-byte
   unchanged until that evidence justifies a decision.

The current evidence is synthetic mechanism analysis, not real-world accuracy
validation. It does not establish reliable performance across foods, plates,
phones, users, or capture conditions.
