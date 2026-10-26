# Paper Data Model

This feature produces a scholarly manuscript, not a software data store. These entities describe the information that must be represented and checked in the manuscript.

## Manuscript

- **Purpose**: The editable conference paper and its compiled review version.
- **Fields**: Working title, abstract, index terms, sections, equations, figures, tables, references, template source/version, compiled PDF.
- **Rules**: Uses the official IEEE conference template in conference mode; template guidance is removed; final venue requirements override generic defaults.
- **Relationships**: Has one or more authors, methods, evaluation results, and references.

## Author

- **Purpose**: Identifies a paper contributor and the supplied institutional contact.
- **Fields**: Name, affiliation, email, email verification state.
- **Records**:
  - SS Gokula Swamy — BMS College of Engineering — `gokulaswamyss@gmail.com` — supplied address.
  - Roshanth V — BMS College of Engineering — `roshanth.v@example.com` — placeholder; confirm before submission.
  - Somanath S.D — BMS College of Engineering — `somanath.sd@example.com` — placeholder; confirm before submission.
  - Aryan Kumar — BMS College of Engineering — `aryan.kumar@example.com` — placeholder; confirm before submission.
- **Rules**: Keep author names and affiliation as supplied. Never present `example.com` placeholders as verified addresses.

## Method Component

- **Purpose**: Describes one stage in the NutriSense pipeline.
- **Fields**: Stage name, input, output, method/model, measurement path, failure behavior, evidence source.
- **Relationships**: Components form the sequence from meal image through dish recognition and portion estimation to nutrient uncertainty and compliance scoring.
- **Rules**: Distinguish the 60 mm marker-based measured tier from the prior tier; accurately describe the marker as printed on A4; avoid claiming the legacy A6 fixture was used for field capture.

## Evaluation Result

- **Purpose**: Records a quantitative result without losing its evaluation context.
- **Fields**: Metric, value, unit, encoder/checkpoint, dataset, split, views/plates/ROIs, confidence interval, evaluation date, source report, evidence category.
- **Evidence categories**: DEV, TRAIN, LOCKED/test, gallery leave-one-out, synthetic/rendered, or published baseline.
- **Rules**: Do not merge categories. For the current DINOv2-S head, report WED DEV only (108 views, 21 plates, 1,218 ROIs); do not create a LOCKED/test result. Label historical ResNet-50 results and published baseline results explicitly.

## Reference

- **Purpose**: Supports a method, dataset, standard, or formatting rule.
- **Fields**: Authors/organization, title, year, venue, DOI or stable URL, claim supported, source type.
- **Rules**: Prefer primary papers and official IEEE/government sources. Correct the DINOv2 arXiv identifier to 2304.07193. Check metadata before final bibliography export.

## Relationships

```text
Manuscript ── has ──> Author
Manuscript ── describes ──> Method Component
Manuscript ── reports ──> Evaluation Result ── supported by ──> Reference or repository report
Manuscript ── cites ──> Reference
```
