# 03: Conformal calibration of learned-head weight intervals

**What to build:** The 90% weight intervals printed for learned-head grams actually contain the true weight ~90% of the time, honestly measured. Calibration runs leave-one-plate-out over the 21 DEV plates (108 views / 1,218 ROI samples): each fold refits the σ + calibration layer on 20 plates and checks the held-out one — the head is never retrained per fold. Correction shape is staged: tune the existing global interval-widening parameter first; per-dish multipliers only if the gate fails. Gate is pre-registered in the ledger before coding.

**Blocked by:** 01 (cheap folds), 02 (calibrate the expanded serving set, so calibration is done once).

**Status:** ready-for-agent

- [ ] Ledger entry pre-registered: out-of-fold DEV coverage_90 ≥ 0.90; MAE statistically unchanged (paired CI via the run-comparison tool); mean interval width growth ≤ +25% else the ticket fails and we investigate; no LOCKED read
- [ ] Leave-one-plate-out machinery implemented; per-fold refit touches only the σ/calibration layer (cached encoder features make folds fast)
- [ ] Stage C executed and measured; if gate passes, keep; else Stage B (per-dish multipliers) executed and measured — decision recorded in the ledger
- [ ] Calibration result recorded as a data artifact with provenance; interval widening rides the existing seam (no new backend seam)
- [ ] Full non-GPU suite + gpu-marked golden guards stay green
