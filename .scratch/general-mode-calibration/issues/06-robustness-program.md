# 06: Robustness program — cross-validation, augmentation, transfer prep

**What to build:** The documented path to a robust weight head with the data that exists (no second measured-Indian dataset exists — audited): WED cross-validation + augmentation experiments, each with a pre-registered ledger criterion; transfer prep from measured non-Indian teachers (Nutrition5k; FPB eval-only under its non-commercial license); author-contact shortlist pursued (Delhi weighed-photo atlas, FLIC, Sri Lanka set).

**Blocked by:** 03 (calibrated head is the baseline every robustness experiment compares against).

**Status:** done (2026-10-29 — ledgers 005 keep / 006 revert executed with paired CIs; Nutrition5k transfer prep pulled; author-contact shortlist drafted; hermetic suite 216/216, ruff 0, pyright at baseline 212)

- [x] Each experiment gets a pre-registered ledger criterion before coding, per ledger rules; decisions recorded as keep/revert with paired CIs (ledger 005 = keep as measurement, ledger 006 = revert — gates 1 & 3 failed)
- [x] WED cross-validation result recorded (per-fold spread, not just the point estimate) — ledger 005: LOPO fold-refit σ coverage profile, plate jackknife (max |Δ| 1.18 g), per-plate MAE/signed/Gini tables
- [x] Augmentation experiment executed with the stress suite's discipline (labelled as such, DEV tier only) — ledger 006: strong recipe REVERTED (ΔMAE +1.41 g, CI [+0.62, +2.17]; candidate bias profile 0.633 vs 0.700 baseline, far too small)
- [x] Nutrition5k transfer prep: subset pulled into local storage (git-ignored), provenance + license recorded, feasibility note written — no committed images (metadata + 3-dish overhead pilot, ~3 MB, under `data/nutrition5k/` with a `.gitignore` entry; note = `docs/research/nutrition5k-transfer-prep.md`; FPB = Food Portion Benchmark, cc-by-nc-4.0, eval-only — a separate dataset, not part of Nutrition5k)
- [x] Author-contact shortlist drafted with concrete asks (what we'd request, why it helps); no contact details invented (`docs/research/teacher-contact-shortlist.md` — Nutrition5k/Google, ISSAI FPB, Sharma North-Indian weighed series, LeFood-Set CC BY 4.0, Sri Lanka atlas)
- [x] Kill-switch discipline respected: every loop iteration starts with the should_stop check (`tools.should_stop` clear as of 2026-10-29 00:59 UTC during this session; NOTE persisted for future iterations: the historical `/tmp/opencode/aug006_candidate_eval.sh` swap did not include the kill-switch — future swap scripts must call `.venv/bin/python -m tools.should_stop || exit 0` first, per AGENTS.md)
