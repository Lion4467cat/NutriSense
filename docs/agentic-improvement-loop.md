# Agentic improvement loop status

**Status date:** 2026-10-30  
This loop is currently diagnostic. It has not changed serving code, production
weights, thresholds, or configuration. A separate research-only checkpoint
was trained for ledger 027 and is not loaded by the app. The ArUco weighed plates
remain EVAL-ONLY permanently; WED LOCKED is never a tuning signal, and the
existing WED DEV/CV evidence is already spent for selection.

## Completed diagnostics

| Ledger | Question | Result | Decision |
|---|---|---|---|
| [022](ledger/022-synthetic-mask-spill.md) | Does 25% vessel-pixel spill alone reproduce the large synthetic total errors? | The registered criterion failed: clean exact-mask totals were within 5% in 3/6 scenes; spill raised absolute error by at least 10 points in 0/6. | No estimator change. Oversized-mask spill alone did not explain the synthetic error pattern. |
| [023](ledger/023-synthetic-surface-area-integration.md) | Does integrating exact local surface area improve exact-mask synthetic estimates? | Failed: ≥5-point absolute-error improvement in 0/6, with a maximum regression of 21.11 points. | Candidate rejected; no estimator change. |
| [024](ledger/024-synthetic-card-position-scale.md) | Does moving a card around unchanged food change the global-scale estimate, and does card-plane homography reduce that spread? | The fixed three-position criterion was not fully assessable because one position per scene was unavailable. For the two measured positions per scene, global-scale spread was 54.45–79.26% and homography-area spread was 0.17–1.84%; exact values are in the raw JSONL. | Strong synthetic mechanism lead only; no serving change. Next validate the effect with a new preregistered, fully detectable placement protocol. |
| [025](ledger/025-synthetic-card-position-replication.md) | Does card-position scale sensitivity reproduce with all placements detected? | All 18 anchors measured; planted-global spread 65.96–70.74% in 6/6 scenes; homography-area spread 1.38–3.27%, ≤2% in 4/6. Signed homography-area errors were −4.60% to −0.71%. | Synthetic mechanism criterion met; no serving change. Same six base scenes and exact masks; intrinsics matched renderer. |
| [026](ledger/026-card-food-plane-height-audit.md) | Does food-base-plane projection reduce residual footprint-area error? | No: mean absolute area error was 8.68% at food-base height versus 1.33% for detected card homographies. The renderer source defines mask support from table-plane ray intersections; table-plane projection gave −0.90% to −0.57% signed error. | Preregistered criterion not met; synthetic renderer convention limits interpretation. No code change. |
| [027](ledger/027-vlm-canteen-participant-heldout.md) | Does a fresh, multi-item weighed meal set expose current-path coverage and support a transfer candidate? | On 60 meals from a participant-held-out group, the frozen serving path abstained 60/60. A DINOv2-S scalar candidate scored 148.018 g MAE vs 172.017 g train+dev median, with −106.880 g bias. | First held-out external candidate gain in this loop, but no serving change: one participant/device cluster and substantial underprediction. Test group is closed. |

The first 024 harness output accidentally used the detected scale for its
baseline, contrary to the preregistered planted-scale baseline. That exploratory
output is superseded. The committed run uses the planted renderer scale for
the baseline and the existing image detector's homography for the candidate;
the final stdout and JSONL are the source of its reported measurements.

## Direction forward

1. Keep each research study isolated under its own `experiments/` subdirectory
   with a frozen protocol, raw outputs, and audit trail. Do not tune against
   ArUco plates, WED LOCKED, or already-spent development evidence.
2. The fixed-placement replication (025) met its synthetic mechanism
   criterion. It used the same six base scenes, exact food masks, and
   renderer-matched fallback intrinsics; it does not validate real photos.
3. The plane audit (026) did not support the registered food-base-plane
   explanation. Source inspection found a renderer support-coordinate
   limitation; the renderer and serving code were left unchanged.
4. Do not promote the homography result from synthetic numbers. Ledger 027 is
   the first new measured multi-item transfer comparison: its external scalar
   candidate modestly beat a median baseline, but the current serving path had
   zero numeric coverage and the candidate retained large negative bias. Its
   one-participant test is closed. Further research may use only remaining
   train/dev groups and needs a different fresh holdout before promotion. The
   ArUco plates remain EVAL-ONLY permanently.

The loop now contains both synthetic mechanism analysis and one real-world
cross-domain measured-meal test. Neither establishes reliable Indian meal
performance across foods, plates, phones, users, or capture conditions.

## Current verification boundary

The 2026-10-30 verification run collected 281 backend tests (271 non-GPU and
10 GPU-marked) but did not complete the backend suite in the restricted
execution environment. The frontend suite passed 70 tests and its production
build succeeded. Ruff and the Pyright baseline gate reported findings; the
details are recorded in `docs/production-readiness.md`. These status checks do
not alter the diagnostic decisions above.
