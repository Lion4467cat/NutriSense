# 027 — VLM Food Benchmark participant-held-out transfer check

- **id**: 027
- **branch**: `codex/iter-synthetic-card-homography-check`
- **date**: 2026-10-30
- **status**: completed; research candidate modestly improved median baseline, not promoted

## Question

Can the unchanged NutriSense pipeline return dish/gram results on a fresh
real-world multi-item meal dataset, and does one frozen image-to-total-mass
candidate improve over a train+development median when split by photographer
group?

## Source and license

- GTMensa 2025 is distributed in the
  [VLM Food Benchmark repository](https://github.com/Metabolic-Intelligence-Lab/vlm-food-benchmark),
  accompanying Marchetti et al., *Nutrients* 2026, 18(21), 3582,
  DOI `10.3390/nu18213582`.
- Dataset files are CC BY 4.0; code is MIT. The local sparse checkout pins
  `d715df0c0debe65da805618431e67f6d0fa01c71` and contains only resized images,
  labels, participant map, citation, and licenses.
- The source reports 200 images / 870 food items and individually scale-weighed
  portions with empty-plate tare subtracted.

## Frozen protocol

- Split by the six participant/device groups before inference: participants
  1, 2, 4, and 5 for train (106 images); participant 3 for dev (34); participant
  6 for test (60). Image SHA-256 audit found no exact duplicate images.
- Candidate: frozen DINOv2-S encoder and the existing ROI weight-head
  architecture with a scalar whole-image output. Regress `sqrt(total_food_g)`;
  train with seed 42, AdamW `lr=1e-3`, SmoothL1, batch 16, and 80 epochs.
  Select epoch on the participant-3 dev group, then reinitialize and refit on
  train+dev for the selected epoch count. No candidate or threshold selection
  uses participant 6.
- Compare against the median whole-meal grams from train+dev.
- Run the unchanged `engine.pipeline.analyze` separately on the same test
  images with `day=mon`, `band=1-5`, `serving_style=mixed`. Attach ground truth
  only after the call. Require CUDA; no CPU fallback. No production code or
  checkpoint is changed.

## Result

- The DINOv2-S research candidate had **148.018 g MAE** and **−106.880 g
  signed bias** on the 60-image test group. The train+dev median baseline had
  **172.017 g MAE** and **−129.433 g signed bias**. The candidate reduced MAE
  by **23.999 g (13.95%)**, but predictions still materially underpredicted.
- Candidate prediction range: **251.728–842.979 g**; true meal totals ranged
  **94–1,154 g**.
- Split composition differed substantially: train averaged **5.06 items/image**
  and **712.4 g/meal**; dev averaged **1.06 items/image** and **320.2 g/meal**;
  test averaged **4.97 items/image** and **761.9 g/meal**. The paper describes
  participant 3's development images as home-prepared lunches, while the
  repository README broadly describes the dataset as university-canteen meals.
  This setting/portion mismatch may have influenced epoch selection and the
  observed candidate bias; that is a hypothesis, not a demonstrated cause.
- The unchanged serving pipeline returned `cannot_verify` on **60/60** test
  images and produced no numeric grams. All 60 anchors were `prior`, all dish
  labels abstained, and gallery best-match scores ranged **0.599–0.765**, below
  the configured 0.80 acceptance.
- Pipeline per-image timing: first call **18.571 s**, median **0.439 s**, p95
  **0.467 s** in this one run. It is not an HTTP deployment benchmark.
- This test has one participant/device cluster, so no confidence interval is
  claimed. The result establishes neither Indian-meal performance nor
  production readiness.

## Reproduction and artifacts

```bash
./.venv/bin/python experiments/vlm_food_benchmark/audit_dataset.py
./.venv/bin/python experiments/vlm_food_benchmark/train_candidate.py
./.venv/bin/python experiments/vlm_food_benchmark/evaluate_candidate.py
./.venv/bin/python experiments/vlm_food_benchmark/run_pipeline_test.py
./.venv/bin/python experiments/vlm_food_benchmark/summarize_results.py
```

Audit, manifest, protocols, scripts, candidate checkpoint, training report,
raw JSONL, and the per-image combined result are in
`experiments/vlm_food_benchmark/`. The participant-6 test group is now closed
to further model, threshold, or candidate selection.

## Decision

**Keep as research evidence only.** The fresh measured multi-item source gives
the first candidate-level held-out MAE reduction in this branch of the loop,
but the serving path has zero coverage and the research head has large
negative bias. Do not integrate or promote it. Any further candidate work must
use train/dev groups and a different, fresh holdout for final evaluation.
