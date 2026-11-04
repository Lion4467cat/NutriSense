"""Promotion decisions that keep target gains and pipeline guardrails separate."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from nutrisense_synth.ablation import STAGE_ORDER


@dataclass(frozen=True)
class PromotionDecision:
    promoted: bool
    target_stage: str
    reason: str
    metrics: dict[str, float]


def evaluate_candidate(target_stage: str, baseline: Mapping[str, float],
                       candidate: Mapping[str, float], thresholds: Mapping[str, float],
                       critical_regressions: list[str] | None = None,
                       direction: str = "higher") -> PromotionDecision:
    if target_stage not in STAGE_ORDER:
        raise ValueError(f"Unknown target stage: {target_stage}")
    if STAGE_ORDER.index(target_stage) > 0 and any(
            stage not in baseline for stage in STAGE_ORDER[:STAGE_ORDER.index(target_stage)]):
        raise ValueError("Freeze earlier-stage baselines before tuning a later stage")
    if target_stage not in baseline or target_stage not in candidate:
        return PromotionDecision(False, target_stage, "target metric missing", {})
    if target_stage not in thresholds:
        return PromotionDecision(False, target_stage, "target threshold not registered", {})
    if direction not in {"higher", "lower"}:
        raise ValueError("direction must be 'higher' or 'lower'")
    raw_delta = candidate[target_stage] - baseline[target_stage]
    gain = raw_delta if direction == "higher" else -raw_delta
    if gain < thresholds[target_stage]:
        return PromotionDecision(False, target_stage, "registered target gain not met",
                                 {"target_gain": gain})
    failures = critical_regressions or []
    if failures:
        return PromotionDecision(False, target_stage,
                                 "critical stage/end-to-end guardrail failed: " + ", ".join(failures),
                                 {"target_gain": gain})
    return PromotionDecision(True, target_stage, "target gate and critical guardrails passed",
                             {"target_gain": gain})
