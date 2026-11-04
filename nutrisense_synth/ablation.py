"""Matched-budget real/synthetic experiment condition construction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

SYNTHETIC_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)
METHODS = ("renderer", "gan", "diffusion")
STAGE_ORDER = ("classification", "segmentation", "depth_geometry", "weight", "end_to_end")


@dataclass(frozen=True)
class ExperimentCondition:
    method: str
    synthetic_fraction: float
    total_examples: int
    real_examples: int
    synthetic_examples: int
    class_quotas: dict[int, int]
    real_class_quotas: dict[int, int]
    synthetic_class_quotas: dict[int, int]


def build_conditions(total_examples: int, class_counts: dict[int, int],
                     methods: Iterable[str] = METHODS) -> list[ExperimentCondition]:
    if total_examples <= 0 or not class_counts:
        raise ValueError("Positive total budget and non-empty class counts are required")
    classes = sorted(class_counts)
    if any(class_counts[c] < 0 for c in classes):
        raise ValueError("Class counts cannot be negative")
    base, remainder = divmod(total_examples, len(classes))
    quotas = {class_id: base + (i < remainder) for i, class_id in enumerate(classes)}
    conditions = []
    for method in methods:
        if method not in METHODS:
            raise ValueError(f"Unsupported method: {method}")
        for fraction in SYNTHETIC_FRACTIONS:
            synthetic = round(total_examples * fraction)
            class_synthetic = {class_id: int(round(quota * fraction))
                               for class_id, quota in quotas.items()}
            delta = synthetic - sum(class_synthetic.values())
            for class_id in classes:
                if delta == 0:
                    break
                if delta > 0 and class_synthetic[class_id] < quotas[class_id]:
                    class_synthetic[class_id] += 1
                    delta -= 1
                elif delta < 0 and class_synthetic[class_id] > 0:
                    class_synthetic[class_id] -= 1
                    delta += 1
            if delta:
                raise ValueError("Unable to distribute synthetic quota across classes")
            class_real = {class_id: quota - class_synthetic[class_id]
                          for class_id, quota in quotas.items()}
            conditions.append(ExperimentCondition(
                method=method, synthetic_fraction=fraction,
                total_examples=total_examples,
                real_examples=total_examples - synthetic,
                synthetic_examples=synthetic,
                class_quotas=quotas.copy(),
                real_class_quotas=class_real,
                synthetic_class_quotas=class_synthetic,
            ))
    return conditions
