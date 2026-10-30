# 03: Conformal calibration of learned-head weight intervals

**What to build:** The 90% weight intervals printed for learned-head grams actually contain the true weight ~90% of the time, honestly measured. Calibration runs leave-one-plate-out over the 21 DEV plates (108 views / 1,218 ROI samples): each fold refits the σ + calibration layer on 20 plates and checks the held-out one — the head is never retrained per fold. Correction shape is staged: tune the existing global interval-widening parameter first; per-dish multipliers only if the gate fails. Gate is pre-registered in the ledger before coding.

**Blocked by:** 01 (cheap folds), 02 (calibrate the expanded serving set, so calibration is done once).

**Status:** gate FAILED as pre-registered — investigation complete, nothing shipped (2026-10-28; ledger 004; follow-up = point-estimate robustness, see known_issues.md + ticket 06)

- [x] Ledger entry pre-registered: out-of-fold DEV coverage_90 ≥ 0.90; MAE statistically unchanged (paired CI via the run-comparison tool); mean interval width growth ≤ +25% else the ticket fails and we investigate; no LOCKED read
- [x] Leave-one-plate-out machinery implemented; per-fold refit touches only the σ/calibration layer (cached encoder features make folds fast)
- [x] Stage C executed and measured; if gate passes, keep; else Stage B (per-dish multipliers) executed and measured — decision recorded in the ledger (decision: DO NOT SHIP — Stage C width +47%, Stage B caps out at 0.8736; root cause is plate-level bias, not width)
- [ ] Calibration result recorded as a data artifact with provenance; interval widening rides the existing seam (no new backend seam) — **not achieved: no artifact landed; the honest interval defect stays open**
- [x] Full non-GPU suite + gpu-marked golden guards stay green
