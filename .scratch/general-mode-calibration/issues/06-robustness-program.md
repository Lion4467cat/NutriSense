# 06: Robustness program — cross-validation, augmentation, transfer prep

**What to build:** The documented path to a robust weight head with the data that exists (no second measured-Indian dataset exists — audited): WED cross-validation + augmentation experiments, each with a pre-registered ledger criterion; transfer prep from measured non-Indian teachers (Nutrition5k; FPB eval-only under its non-commercial license); author-contact shortlist pursued (Delhi weighed-photo atlas, FLIC, Sri Lanka set).

**Blocked by:** 03 (calibrated head is the baseline every robustness experiment compares against).

**Status:** ready-for-agent

- [ ] Each experiment gets a pre-registered ledger criterion before coding, per ledger rules; decisions recorded as keep/revert with paired CIs
- [ ] WED cross-validation result recorded (per-fold spread, not just the point estimate)
- [ ] Augmentation experiment executed with the stress suite's discipline (labelled as such, DEV tier only)
- [ ] Nutrition5k transfer prep: subset pulled into local storage (git-ignored), provenance + license recorded, feasibility note written — no committed images
- [ ] Author-contact shortlist drafted with concrete asks (what we'd request, why it helps); no contact details invented
- [ ] Kill-switch discipline respected: every loop iteration starts with the should_stop check
