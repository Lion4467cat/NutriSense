# Data Model: Accuracy and Production Readiness

## Dataset Observation

One input image/view and source-level reference. Images remain in their raw source location; generated manifests reference paths instead of copying image bytes.

| Field | Type | Meaning |
|---|---|---|
| `observation_id` | string | Stable manifest key |
| `dataset_id`, `release_id` | string | Source and exact release |
| `source_record_id` | string | Original filename/row/dish identifier |
| `sample_group_id` | string | Physical plate, portion, snack identity, or capture group for split isolation |
| `session_id` | string/null | Capture session, when available |
| `image_path` | relative path | Local source image reference |
| `view_kind` | enum/null | overhead, side, RGB-D, marker capture, or unknown |
| `camera_metadata` | object/null | Intrinsics/EXIF, depth alignment/units, camera and geometry metadata if available |
| `split` | enum | source-native train/dev/test or project train/dev/calibration/locked/external |
| `license_ref` | string | Source license/provenance record |

## Target Value

Targets are typed and never overloaded. One observation may have zero or more targets.

| Field | Type | Meaning |
|---|---|---|
| `target_kind` | enum | item_mass, meal_mass, volume, energy, protein, fat, carbohydrate, food_class, mask, marker_pose |
| `value` | number/object | Numeric value or structured annotation |
| `unit` | string | g, ml/cm3, kcal, mask pixels, class ID, etc. |
| `measurement_method` | string/null | scale, computed from per-100-g label, annotation, sensor, or inferred |
| `food_or_component_id` | string/null | Item/component linkage |
| `confidence_or_quality` | object/null | Annotation or measurement quality, never model confidence |
| `loss_eligible` | boolean | Explicitly indicates whether target semantics support a given training task |

Derived nutrition must retain a calculation trace: food-composition entry/version, mass estimate in grams, nutrient density per 100 g, and calculated kcal/macros. FinnFoodPics calorie-tier labels are image/portion-level targets; per-100-g nutrition is a separate density target.

## Evaluation Run

| Field | Type | Meaning |
|---|---|---|
| `run_id` | string | Immutable run identifier |
| `checkpoint_hash`, `code_revision` | string | Model and source revision |
| `dataset_manifest_hash`, `split_manifest_hash` | string | Exact data and group assignment |
| `config_hash`, `environment` | string/object | Training/evaluation setup |
| `metrics` | object | Overall and stratified prediction/error/coverage metrics |
| `bootstrap_unit`, `ci_method` | string | Statistical resampling details |
| `runtime` | object | Device, p50/p95 latency, memory, errors |
| `promotion_decision` | enum/string | candidate, accepted, rejected, or report-only plus rationale |

## Split rules

Split by the largest related acquisition identity before augmentation: WED plate/session, Nutrition5k dish ID and official split, ECUSTFD physical portion (paired views), FinnFoodPics snack identity (all portion tiers), and local capture session/plate. Store one split assignment per group, then derive observations. Deduplicate exact and near-duplicate images before reporting cross-split checks.
