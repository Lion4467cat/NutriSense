# Implementation Plan: NutriSense IEEE Conference Paper

**Branch**: `main` | **Updated**: 2026-11-02 | **Spec**: [spec.md](spec.md)

## Summary

Produce a review-ready, evidence-bounded IEEE conference draft describing the integrated NutriSense research prototype. The manuscript covers the current multi-item pipeline and safe estimate-only fallbacks, separates model-component evidence from end-to-end pilot evidence, documents policy scope and limitations, and gives concrete future evaluation work. No new dataset is collected and no closed evaluation set is reopened.

## Technical Context

**Source and output**: LaTeX manuscript, BibTeX references, and figures under `paper/`; planning artifacts under this directory. The build uses the vendored IEEEtran conference class and the project's local TeX Live installation.

**Runtime facts to describe**: A 60 mm ArUco ID 7 marker printed on A4 provides a measured scale path. SAM 2.1 proposes a top-level food mask and up to nine item regions. Overlap pixels are partitioned once using nearest exclusive-region seeds. SigLIP 2 ranks the configured 41 WED classes. Distinct regions can be portioned and aggregated; uncertain structure or labels can fall back to an estimate-only result without school scoring. Hard input/model failures can still return `cannot_verify`. The optional Ollama Cloud meal critique follows analysis and is not part of the compliance decision.

**Evidence policy**: Keep WED DEV, the one-time WED LOCKED report, gallery leave-one-out, synthetic checks, and the pre-change 23-view EVAL-ONLY pilot separate. Preserve the reported scope and limitations for every value. Do not claim real-mask IoU/F1, validated meal-level nutrient accuracy, coach quality, post-fix pilot gains, or 90% accuracy. Do not tune against the locked pilot or consumed WED split.

**Validation**: Build the paper and inspect every rendered page, citations, bibliography balance, table readability, and claim consistency. Focused software regression checks are documented separately in `AUDIT.md`; this manuscript plan does not authorize retesting closed evaluation data.

## Deliverables

- `paper/main.tex`, `paper/references.bib`, and `paper/figures/pipeline.pdf` as editable source assets.
- `paper/main.pdf` as the compiled review draft.
- Updated quickstart, claim-evidence map, citation audit, and requirements reflecting current behavior and evidence.

## Completion Conditions

- The narrative and diagram agree with the current runtime, including multi-item aggregation, estimate-only fallbacks, and hard failures.
- All project results identify their evaluation scope; no metric is presented as independent end-to-end accuracy without supporting evidence.
- Author names and supplied affiliation are correct; unverified email addresses are omitted.
- The bibliography resolves completely and cited sources support the associated statements.
- The compiled PDF has no clipped content and has been rendered and visually checked page by page.
- The paper remains a generic draft pending venue-specific rules and independently annotated evaluation data.
