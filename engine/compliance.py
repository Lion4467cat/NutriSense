"""S5: MDM compliance verdict (plan v5 decision rules).

  P_nutrient = fraction of MC samples >= band minimum
  PASS   iff every mandatory nutrient P >= 0.90 AND coverage C >= 0.85
  FAIL   iff any  mandatory nutrient P <= 0.10 AND coverage C >= 0.90
  BORDERLINE otherwise (including zone-met but C short of the zone gate)

Coverage C = product of degradation factors (prior anchor, table-prior base,
quality flags). The prior anchor tier can never PASS or FAIL (C caps out at
0.60). Salt is advisory only; raw-gram rows are diagnostic only.
"""
import numpy as np
from dataclasses import dataclass, field

from config import load_params, load_standards
from engine.contract import (Failure, FailureKind, Reason, ReasonKind, Stage,
                             reason_for_failure)


@dataclass
class AssessResult:
    """What assess() hands back. The pipeline builds the wire Analysis from
    these fields directly, so every key — failures included — propagates
    structurally instead of being re-picked by hand at the call site."""
    verdict: str
    reasons: list
    failures: list = field(default_factory=list)
    coverage: dict | None = None
    probs: dict = field(default_factory=dict)
    nutrients: dict = field(default_factory=dict)
    assumptions: list = field(default_factory=list)
    advisory: dict | None = None
    diagnostics: dict | None = None
    day: str | None = None
    band: str | None = None


def coverage(portion, anchor_label, params=None):
    """(score, factors) — multiplicative degradation model."""
    params = params if params is not None else load_params()
    factors = {}
    if anchor_label != "measured":
        factors["anchor_prior"] = params["coverage_anchor_prior"]["value"]
    if portion.get("base_method") == "table_prior":
        factors["base_table_prior"] = params["coverage_base_table_prior"]["value"]
    flags = set(portion.get("flags") or [])
    if flags & {"depth_partial", "thin_layer"}:
        factors["quality_degraded"] = params["coverage_quality_degraded"]["value"]
    score = float(np.prod(list(factors.values()))) if factors else 1.0
    return round(score, 4), factors


def _p_ge(samples, threshold):
    return float(np.mean(np.asarray(samples) >= threshold))


def assess(mc, portion, dish, band, anchor_label,
           params=None, standards=None, day=None):
    """Score one admitted plate. Hard gates are consulted by analyze() only
    (engine/gates.py) — by the time we get here the plate is admitted."""
    params = params if params is not None else load_params()
    standards = standards if standards is not None else load_standards()

    if mc is None:
        f = Failure(FailureKind.STAGE_FAILED, Stage.NUTRITION,
                    "no nutrient samples")
        return AssessResult(verdict="cannot_verify",
                            reasons=[reason_for_failure(f)], failures=[f],
                            day=day, band=band)

    rules = standards["compliance"]
    thr = rules["thresholds"]
    cov_min = rules["coverage"]
    band_row = standards["bands"][band]  # band validity is the gate's job

    # --- probabilities per mandatory nutrient ----------------------------
    nutrients, probs, reasons = {}, {}, []
    all_pass, any_fail = True, False
    for key in rules["mandatory_nutrients"]:
        row = band_row[key]
        if row.get("direction", "min") != "min":
            raise ValueError(f"unsupported direction for {key}")
        minimum = float(row["value"])
        samples = mc[f"{key}_samples"]
        p = _p_ge(samples, minimum)
        summary = mc[key]
        probs[key] = p
        nutrients[key] = {
            "min": minimum,
            "p_at_or_above_min": round(p, 4),
            "mean": summary["mean"],
            "interval_90": (summary["p05"], summary["p95"]),
            "headroom_at_interval_low": round(summary["p05"] - minimum, 2),
        }
        all_pass &= p >= thr["pass_p"]
        any_fail |= p <= thr["fail_p"]
        if p < thr["pass_p"]:
            reasons.append(Reason(ReasonKind.BELOW_MIN,
                                  f"{key}: P={p:.2f} < {thr['pass_p']} pass zone"))
        if p <= thr["fail_p"]:
            reasons.append(Reason(ReasonKind.BELOW_MIN,
                                  f"{key}: P={p:.2f} <= {thr['fail_p']} fail zone"))

    # --- coverage ---------------------------------------------------------
    cov_score, cov_factors = coverage(portion, anchor_label, params)

    if any_fail and cov_score >= cov_min["fail_min"]:
        verdict = "FAIL"
        reasons.insert(0, Reason(ReasonKind.BELOW_MIN,
                                 "mandatory nutrient below minimum with sufficient coverage"))
    elif all_pass and cov_score >= cov_min["pass_min"]:
        verdict = "PASS"
        reasons = [Reason(ReasonKind.IN_ZONE,
                          "all mandatory nutrients in pass zone with sufficient coverage")]
    elif any_fail or all_pass:
        verdict = "BORDERLINE"
        reasons.append(Reason(ReasonKind.COVERAGE_GATE,
                              f"probability zone met but coverage {cov_score:.2f} < "
                              f"{'fail' if any_fail else 'pass'} gate "
                              f"{cov_min['fail_min' if any_fail else 'pass_min']}"))
    else:
        verdict = "BORDERLINE"

    # --- assumptions actually in play ------------------------------------
    assumptions = []
    if anchor_label != "measured":
        assumptions.append("size_prior_food_diameter_mm (assumed) — prior anchor tier")
        assumptions.append("prior_tilt_deg (assumed) — prior anchor tier")
    if portion.get("base_method") == "table_prior":
        assumptions.append("base_prior_height_mm + base_prior_sigma_mm (assumed) — no ring evidence")
    for gid in mc.get("assumed_nutrients", []):
        assumptions.append(f"nutrient table row {gid} (assumed)")
    if dish.get("ranges_wider"):
        assumptions.append(dish.get("mandatory_report_line", "generic nutrient estimates (wider ranges)"))

    advisory = {
        "sodium_salt": standards["advisory"]["sodium_salt"],
        "note": "advisory only — salt is never a verdict nutrient",
    }

    return AssessResult(
        verdict=verdict,
        reasons=reasons,
        coverage={"score": cov_score, "factors": cov_factors,
                  "pass_min": cov_min["pass_min"], "fail_min": cov_min["fail_min"]},
        probs={k: round(v, 4) for k, v in probs.items()},
        nutrients=nutrients,
        assumptions=assumptions,
        advisory=advisory,
        diagnostics=mc.get("diagnostics"),
        day=day,
        band=band,
    )
