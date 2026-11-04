# Paper Data Model

This feature produces a scholarly manuscript, not a software data store. These entities describe the information that must be represented and checked in the manuscript.

## Manuscript

- **Purpose**: The editable conference paper and its compiled review version.
- **Fields**: Working title, abstract, index terms, sections, equations, figures, tables, references, template source/version, compiled PDF.
- **Rules**: Uses the official IEEE conference template in conference mode; template guidance is removed; final venue requirements override generic defaults.
- **Relationships**: Has one or more authors, methods, evaluation results, and references.

## Author

- **Purpose**: Identifies each paper contributor and supplied institutional affiliation.
- **Fields**: Name, affiliation, verified email when required by the venue.
- **Records**: SS Gokula Swamy, Roshanth V, Somanath S.D, and Aryan Kumar — BMS College of Engineering.
- **Rules**: Keep names and affiliation as supplied. Omit contact addresses until verified; do not include temporary or fabricated addresses.

## Method Component

- **Purpose**: Describes one stage in the NutriSense pipeline.
- **Fields**: Stage name, input, output, method/model, measurement path, failure behavior, evidence source.
- **Relationships**: Components form the sequence from meal image through food regions, recognition, per-region portion estimation, nutrient uncertainty, and conditional meal-level scoring. The optional meal critique follows analysis and cannot affect the score.
- **Rules**: Distinguish the 60 mm marker-based measured tier from prior tiers; describe the marker as printed on A4; describe overlap partitioning and estimate-only fallback; do not imply validated real-photo multi-item accuracy or use the legacy A6 fixture as the field protocol.

## Evaluation Result

- **Purpose**: Records a quantitative result without losing its evaluation context.
- **Fields**: Metric, value, unit, encoder/checkpoint, dataset, split, views/plates/ROIs, confidence interval, evaluation date, source report, evidence category.
- **Evidence categories**: DEV, TRAIN, LOCKED/test, gallery leave-one-out, synthetic/rendered, or published baseline.
- **Rules**: Do not merge categories. Report the DINOv2-S WED DEV result and the existing one-time LOCKED report only with their distinct scope, sample counts, interval coverage, and no-retuning caveat. Label gallery diagnostics and the pre-change EVAL-ONLY pilot separately. Do not use any closed split to validate current changes.

## Reference

- **Purpose**: Supports a method, dataset, standard, or formatting rule.
- **Fields**: Authors/organization, title, year, venue, DOI or stable URL, claim supported, source type.
- **Rules**: Prefer primary papers and official IEEE/government sources. Correct the DINOv2 arXiv identifier to 2304.07193. Check metadata before final bibliography export.

## Relationships

```text
Manuscript ── has ──> Author
Manuscript ── describes ──> Method Component
Manuscript ── reports ──> Evaluation Result ── described by ──> Protocol and scope
Manuscript ── cites ──> Reference
```
