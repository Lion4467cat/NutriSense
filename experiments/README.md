# Research and evaluation records

Each subdirectory keeps one source or diagnostic effort together: its protocol,
scripts, result summaries, and compact prediction logs. Research checkpoints and
results are not serving artifacts unless a separate promotion record says so.
Raw source datasets stay under the git-ignored `datasets/raw/` or `data/`
directories; do not copy those images into this tree.

| Directory | Purpose | Current status |
|---|---|---|
| [`oracle_ablation/`](oracle_ablation/) | Synthetic diagnostics and the weighed ArUco plate evaluation. | ArUco plates are EVAL-ONLY; results are descriptive and do not authorize tuning. |
| [`food_waste/`](food_waste/) | AI-ServicesBB Food Waste cross-domain pipeline and mask diagnostics. | Official test split is closed; diagnostic only. |
| [`lefoodset/`](lefoodset/) | LeFood-Set audit, frozen pipeline run, and candidate comparison. | Held-out categories are closed; candidate is not in serving. |
| [`metafood3d/`](metafood3d/) | Grouped single-object marker/depth transfer benchmark. | Candidate regressed against baseline; CC BY-NC limits product use. |
| [`vlm_food_benchmark/`](vlm_food_benchmark/) | GTMensa participant-held-out mixed-meal transfer benchmark. | Test participant is closed; candidate is research-only and biased. |

Read each `PROTOCOL.md` and `RESULTS*.md` before interpreting a result. The
current synthesis and the evidence each result can support are in
[`../docs/production-readiness.md`](../docs/production-readiness.md) and
[`../docs/technical-project-report.md`](../docs/technical-project-report.md).
