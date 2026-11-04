# Data Model: Synthetic Food Data and Model Evaluation

## Source Group

Represents one physical WED plate/session or one ArUco meal. All views and derived samples from a group share its identity.

| Field | Type | Constraint |
|---|---|---|
| `source` | string | `wed` or `aruco` |
| `source_group_id` | string | Stable within source; WED uses the existing plate key, ArUco uses the dish folder |
| `source_record_id` | string | Original image/annotation record reference |
| `source_split` | enum | `train`, `dev`, `locked`, or `aruco_eval` |
| `source_image_sha256` | hex string | SHA-256 of original image bytes |
| `source_label_sha256` | hex string or null | SHA-256 of source mask/weight metadata when present |

WED TRAIN groups are eligible as generator sources after excluding the repository’s fixed seed-42, 10% plate-group DEV carve from manifest rows labeled `train`. WED DEV, WED LOCKED, and all ArUco groups are never eligible as generator or candidate-model training inputs. ArUco split labels describe evaluation provenance only.

## Scene Definition

Describes the deterministic scene that owns geometry and physical targets.

| Field | Type | Constraint |
|---|---|---|
| `scene_id` | string | Stable hash of source group, class, scene parameters, and seed |
| `scene_kind` | enum | `isolated_dish` or `composed_thali` |
| `class_id` | integer | One of the 41 non-background WED class slots |
| `class_name` | string | Exact WED index-map name; no new aliases or classes |
| `components` | array | One or more `{class_id, class_name, mask_id, volume_ml, density_g_ml, grams}` records |
| `card_present` | boolean | Paired scenes share all scene parameters and differ only in this field/card pixels |
| `card_pair_id` | string or null | Same ID for one card-present and one no-card render |
| `marker` | object or null | If present: dictionary `DICT_4X4_50`, ID 7, 60 mm physical size, corners and pose |
| `camera` | object | Intrinsics, pose, distance/angle, resolution, and capture seed |
| `illumination` | object | Light/background/material seed and settings |
| `portion_range` | enum | `wed_observed` or `broader_exploratory` |
| `scene_seed` | integer | Stable integer used by deterministic render path |

Each component’s renderer mass is `volume_ml × density_g_ml`. A mass target includes `density_source`, `density_source_ref`, `assumption_status`, `uncertainty_range`, and `measurement_kind: synthetic_physical`. Inferred image-model weights use a separate field with `measurement_kind: model_prediction` and cannot replace the physical target.

## Synthetic Sample Manifest Row

One JSON Lines record binds the output image to its source and task-specific labels.

| Field | Type | Constraint |
|---|---|---|
| `sample_id` | string | Stable unique ID derived from source group, scene, method/version, and output hash |
| `scene_id` | string | References the immutable scene definition |
| `source` | object | Source Group fields |
| `generation` | object | Method (`renderer`, `gan`, `diffusion`), method/checkpoint revision, seed, config hash, training-source hashes, license/provenance record |
| `output` | object | Relative path, image hash, width, height, color format |
| `labels` | object | WED class, semantic/instance masks, metric depth, marker annotations, component/total grams, and per-task valid flags |
| `pair` | object or null | `card_pair_id`, paired sample ID, and asserted changed field `card_present` |
| `quality` | object | Automated check versions/results, per-task validity/rejection reason, reviewer stratum/status |
| `created_at` | timestamp | UTC ISO-8601 generation time |

Every generated sample inherits `source.source_split` and `source.source_group_id`. Only rows with `source_split: train` may appear in model training input. Per-task invalid samples may be retained for an unaffected task only if its label validity is independently established.

## Experiment Condition

| Field | Type | Constraint |
|---|---|---|
| `experiment_id` | string | Unique immutable run ID |
| `stage` | enum | `classification`, `segmentation`, `depth_geometry`, `weight`, `end_to_end` |
| `method` | enum | `renderer`, `gan`, `diffusion`, or `real_only` |
| `synthetic_fraction` | number | One of `0`, `0.25`, `0.5`, `0.75`, `1` |
| `training_budget` | object | Total samples/steps, epochs, resolution, class quotas, optimizer/config hash |
| `data_hashes` | object | Source manifest, synthetic manifest, and split hashes |
| `model_hashes` | object | Initialization, trained candidate, and serving revision |
| `metrics` | object | Per-stage, per-class, end-to-end metrics and grouped uncertainty |
| `guardrails` | object | Pre-registered target threshold, non-regression status, failure count |
| `decision` | enum | `keep`, `reject`, `research_only`, `pending` |

WED LOCKED results are recorded only in the final report after candidate selection and cannot populate `metrics` used for selection. The six ArUco groups are reported in a separate final exploratory mass report.
