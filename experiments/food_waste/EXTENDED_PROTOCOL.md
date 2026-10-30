# Extended AI-ServicesBB Food Waste diagnostic

Pre-registered 2026-10-30 after the initial four-receipt run. This is an
inference-only coverage check on the remaining groups of the same official
`train` split; it is not a candidate comparison or model-selection claim.

- Source revision: `f008d0c7b41ea4408b66bd1b7bb9ecd58b70349d`.
- Fetch only the author `train` split. Never fetch or inspect official `test`.
- Order the 12 train receipt IDs by
  `SHA256("nutrisense-food-waste-dev-20261030:" + bonid)`.
- The initial run used positions 1–4 (see `PROTOCOL.md`). This run uses only
  positions 5–12 (the remaining eight receipts). All images from each receipt
  remain grouped.
- Target is `sum(Menge_Rückläufer)` food-only returned grams. No target or
  label is passed to the unchanged pipeline.
- Run on CUDA from `.venv`, `day=mon`, `band=1-5`, `serving_style=mixed`;
  no CPU fallback. Save all raw model outputs, per-stage timings and resource
  reasons in `raw_extended.jsonl`.
- Report every receipt separately. Null grams remain abstentions and are not
  converted into zero-error or zero-gram predictions. Do not tune, retrain,
  change thresholds/configs, or promote a model from these results.

This extends development evidence only. The official test split remains
untouched; these 12 train receipts are not independent evidence of serving
generalization.
