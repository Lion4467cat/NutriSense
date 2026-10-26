# NutriSense Constitution

## Core Principles

### I. Evidence Before Claims
Scientific and product claims must be traceable to source code, evaluation reports, published sources, or clearly marked assumptions. Do not describe assumed parameters as measured values.

### II. Reproducible Evaluation
Keep DEV, TRAIN, and LOCKED evaluation roles distinct. Do not tune on LOCKED data or imply that a result from one encoder, split, or evaluation protocol applies to another.

### III. Honest Uncertainty
Report the system's limitations, coverage, and failure behavior. Keep measured scale, prior scale, and learned-weight estimates distinct in documentation and user-facing claims.

### IV. Preserve Public Contracts
Changes to API schemas, policy digests, generated frontend types, and protected evaluation artifacts require focused updates and the repository's prescribed validation. Avoid broad reformatting or unrelated cleanup.

### V. Verify Proportionately
Use the documented project gates for behavioral changes. Do not regenerate evaluation locks or make claims of test success without running the corresponding checks.

## Project Constraints

- Use `uv` for Python package management; do not install packages with `pip`.
- Do not add private data, credentials, model caches, or ignored datasets to commits.
- Treat `docs/ledger/` and the evaluation protocol as the source of truth for model metrics, split definitions, and evaluation decisions.
- The field scale marker is the 60 mm ArUco marker on A4 in `docs/assets/reference_marker_A4_60mm.pdf`. The legacy A6 image generator exists only for synthetic renderer tests.
- The IEEE paper must follow the official IEEE conference template and distinguish current DEV results from historical ResNet-50/test-set results.

## Governance

These principles guide project planning, implementation, research, and publication. Amendments must be documented in a way that preserves reproducibility and explains their effect on existing work.

**Version**: 1.0.0 | **Ratified**: 2026-10-26 | **Last Amended**: 2026-10-26
