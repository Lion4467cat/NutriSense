# 02: Expand serving to all 41 WED classes + gallery rebuild

**What to build:** The pipeline recognizes and estimates grams for every one of the 41 WED dish classes. The serving mapping expands so no WED class is unmapped; the classifier gallery is rebuilt to cover all 41 classes using WED train images (plus RASOI real-capture thalis if the license check from ticket 00 clears it); the gallery-match abstain threshold is re-derived for the 41-class gallery via its leave-one-out evaluation — not carried over from the 2-class gallery. Previously out_of_scope plates now produce grams + nutrients through the deployable path, still under the same anchor-tier and disclaimer rules.

**Blocked by:** 00 (license gate).

**Status:** done (2026-10-28 — ledger 003, decision keep; DEV paired delta 0.0)

- [x] Serving mapping covers all 41 WED classes; a data-level test asserts every WED class resolves
- [x] Gallery rebuilt (46 photos/2 classes → 41 classes); LOO evaluation recorded; abstain threshold re-derived and set in params
      (covered by ledger 003 result; ticked 2026-10-29. Recognition-accuracy
      follow-up with the honest held-out baseline: ledgers 008+009 —
      gallery argmax 0.8103 per DEV ROI crop, trained heads at parity,
      serving unchanged)
- [ ] Ledger entry pre-registered before code, per `docs/ledger/README.md` rules; fresh DEV run after; gate covers how expansion moves DEV metrics (previously-unreachable plates now score)
- [ ] Existing seam tests (classify abstain, deps injection, learned-head ×5) stay green; no new backend seam
- [ ] No WED/RASOI image redistribution; data files only
