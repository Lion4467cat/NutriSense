"""Wire contract for /analyze — the single source of truth.

Python owns the result shape; the TypeScript side consumes a Zod schema
generated from these vocabularies by tools/gen_contract_ts.py (regenerate:
``python -m tools.gen_contract_ts``).

Wire keys (16):
  verdict, reasons, failures, lint, anchor, segmentation, classification,
  dish, portion, nutrition, coverage, assumptions, advisory, compliance,
  model_versions, policy

Rules:
  * reasons    — canonical, human-readable explanations for EVERY verdict
                 (including PASS). Each hard failure generates its own reason.
  * failures   — hard failures only (stage crashes, rejected gates). Silent
                 degradations stay in assumptions / coverage.factors.
  * nullables  — a null detail block means "this stage was never reached".
  * paths      — never appear in error or reason text (redacted here, at the
                 single point every Failure/Reason passes through).
  * policy     — thresholds + coverage factors + capture limits as served, so
                 the UI renders thresholds from the backend, not constants.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from enum import StrEnum
from pathlib import Path
from typing import Literal

_DATA = Path(__file__).resolve().parents[1] / "data"

log = logging.getLogger("nutrisense")

Verdict = Literal["PASS", "BORDERLINE", "FAIL", "cannot_verify", "out_of_scope"]

WIRE_KEYS = frozenset({
    "verdict", "reasons", "failures", "lint", "anchor", "segmentation",
    "classification", "dish", "portion", "nutrition", "coverage",
    "assumptions", "advisory", "compliance", "model_versions", "policy",
})


# --- vocabularies ---------------------------------------------------------

class FailureKind(StrEnum):
    GATE_REJECTED = "gate_rejected"
    INPUT_UNREADABLE = "input_unreadable"
    STAGE_FAILED = "stage_failed"


class ReasonKind(StrEnum):
    ZOOM = "zoom"
    UNKNOWN_DAY = "unknown_day"
    UNKNOWN_BAND = "unknown_band"
    OUT_OF_SCOPE = "out_of_scope"
    UNRECOGNIZED = "unrecognized"
    UNREADABLE = "unreadable"
    STAGE_FAILED = "stage_failed"
    IN_ZONE = "in_zone"
    BELOW_MIN = "below_min"
    COVERAGE_GATE = "coverage_gate"


class Stage(StrEnum):
    INPUT = "input"
    ANCHOR = "anchor"
    SEGMENT = "segment"
    CLASSIFY = "classify"
    DEPTH = "depth"
    PORTION = "portion"
    NUTRITION = "nutrition"
    COMPLIANCE = "compliance"


# --- redaction ------------------------------------------------------------

_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s,;)\']+|/(?:[\w.\-]+/)+[\w.\-]*")


def _redact(text) -> str:
    if not isinstance(text, str):
        return text
    return _PATH_RE.sub("<path>", text)


# --- contract objects -----------------------------------------------------

@dataclass(frozen=True)
class Failure:
    kind: FailureKind
    stage: Stage
    error: str

    def __post_init__(self):
        object.__setattr__(self, "kind", FailureKind(self.kind))
        object.__setattr__(self, "stage", Stage(self.stage))
        object.__setattr__(self, "error", _redact(self.error))

    def to_wire(self) -> dict:
        return {"kind": str(self.kind), "stage": str(self.stage),
                "error": self.error}


@dataclass(frozen=True)
class Reason:
    kind: ReasonKind
    text: str

    def __post_init__(self):
        object.__setattr__(self, "kind", ReasonKind(self.kind))
        object.__setattr__(self, "text", _redact(self.text))

    def to_wire(self) -> dict:
        return {"kind": str(self.kind), "text": self.text}


def gate_reject(reason_kind, stage, text) -> tuple[Failure, Reason]:
    """One call, one canonical text: gates emit both objects from a single
    source string so failure and reason can never drift apart."""
    failure = Failure(FailureKind.GATE_REJECTED, stage, text)
    reason = Reason(reason_kind, text)
    return failure, reason


def reason_for_failure(failure: Failure) -> Reason:
    """Canonical reason generated for every hard failure."""
    if failure.kind is FailureKind.INPUT_UNREADABLE:
        return Reason(ReasonKind.UNREADABLE, failure.error)
    if failure.kind is FailureKind.GATE_REJECTED:
        return Reason(ReasonKind.STAGE_FAILED, failure.error)
    return Reason(ReasonKind.STAGE_FAILED,
                  f"{failure.stage} failed: {failure.error}")


# --- policy ---------------------------------------------------------------

@dataclass(frozen=True)
class Policy:
    pass_p: float
    fail_p: float
    pass_min: float
    fail_min: float
    anchor_prior_cap: float
    base_table_prior: float
    quality_degraded: float
    lint_min_side_px: int
    policy_version: str

    def to_wire(self) -> dict:
        return asdict(self)


_POLICY_CACHE: Policy | None = None


def load_policy() -> Policy:
    """Thresholds + coverage factors + capture limits, read from the yaml
    sources. policy_version = sha256 of the source values (12 hex chars) so
    stored records can tell which rule set produced them."""
    global _POLICY_CACHE
    if _POLICY_CACHE is None:
        import yaml
        with open(_DATA / "standards.yaml") as f:
            standards = yaml.safe_load(f)
        with open(_DATA / "params_status.yaml") as f:
            ledger = yaml.safe_load(f)["params"]
        thr = standards["compliance"]["thresholds"]
        cov = standards["compliance"]["coverage"]
        sources = {
            "pass_p": float(thr["pass_p"]),
            "fail_p": float(thr["fail_p"]),
            "pass_min": float(cov["pass_min"]),
            "fail_min": float(cov["fail_min"]),
            "anchor_prior_cap": float(ledger["coverage_anchor_prior"]["value"]),
            "base_table_prior": float(ledger["coverage_base_table_prior"]["value"]),
            "quality_degraded": float(ledger["coverage_quality_degraded"]["value"]),
            "lint_min_side_px": int(ledger["lint_min_side_px"]["value"]),
        }
        digest = hashlib.sha256(
            repr(sorted(sources.items())).encode()).hexdigest()[:12]
        _POLICY_CACHE = Policy(**sources, policy_version=digest)
    return _POLICY_CACHE


# --- stage guard ----------------------------------------------------------

@dataclass(frozen=True)
class Fatal:
    pass


@dataclass(frozen=True)
class Degrade:
    fallback: str


STAGE_POLICY: dict[Stage, Fatal | Degrade] = {
    Stage.INPUT: Fatal(),
    Stage.ANCHOR: Degrade("prior_anchor"),
    Stage.SEGMENT: Fatal(),
    Stage.CLASSIFY: Fatal(),
    Stage.DEPTH: Fatal(),
    Stage.PORTION: Fatal(),
    Stage.NUTRITION: Fatal(),
    Stage.COMPLIANCE: Fatal(),
}

_FALLBACKS: dict[str, object] = {}


def register_fallback(name: str, fn) -> None:
    _FALLBACKS[name] = fn


def stage(name, fn, *args, timings=None, **kwargs):
    """Run one guarded stage.

    Returns (value, failure). Fatal stages log at ERROR and return the
    failure (value None) so the caller can exit with cannot_verify — never a
    500. Degrade stages log at WARNING, run their registered fallback, and
    return (fallback_value, None): a silent degradation with no failures[]
    entry (observable via the stage's own detail block).
    """
    stage_v = Stage(name)
    entry = STAGE_POLICY[stage_v]
    t0 = time.perf_counter()
    value, failure = None, None
    try:
        value = fn(*args, **kwargs)
    except Exception as e:
        failure = Failure(FailureKind.STAGE_FAILED, stage_v,
                          f"{type(e).__name__}: {e}")
        if isinstance(entry, Degrade):
            log.warning("stage=%s degraded, fallback=%s error=%s",
                        stage_v, entry.fallback, failure.error, exc_info=True)
            try:
                value = _FALLBACKS[entry.fallback]()
                failure = None
            except Exception:
                log.exception("stage=%s fallback=%s failed", stage_v,
                              entry.fallback)
        else:
            log.exception("stage=%s failed: %s", stage_v, failure.error)
    finally:
        if timings is not None:
            timings[stage_v.value] = (timings.get(stage_v.value, 0.0)
                                      + time.perf_counter() - t0)
    return value, failure


# --- analysis envelope ----------------------------------------------------

@dataclass
class Analysis:
    verdict: Verdict
    reasons: list[Reason] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)
    lint: dict | None = None
    anchor: dict | None = None
    segmentation: dict | None = None
    classification: dict | None = None
    dish: dict | None = None
    portion: dict | None = None
    nutrition: dict | None = None
    coverage: dict | None = None
    assumptions: list = field(default_factory=list)
    advisory: dict | None = None
    compliance: dict | None = None
    model_versions: dict = field(default_factory=dict)
    policy: Policy = field(default_factory=load_policy)

    def to_wire(self) -> dict:
        return {
            "verdict": str(self.verdict),
            "reasons": [r.to_wire() for r in self.reasons],
            "failures": [f.to_wire() for f in self.failures],
            "lint": self.lint,
            "anchor": self.anchor,
            "segmentation": self.segmentation,
            "classification": self.classification,
            "dish": self.dish,
            "portion": self.portion,
            "nutrition": self.nutrition,
            "coverage": self.coverage,
            "assumptions": list(self.assumptions),
            "advisory": self.advisory,
            "compliance": self.compliance,
            "model_versions": self.model_versions,
            "policy": self.policy.to_wire(),
        }


def unreadable_analysis(detail: str = "unreadable image") -> Analysis:
    """Full-shape cannot_verify for an image that would not decode — every
    detail block null (stage never reached)."""
    failure = Failure(FailureKind.INPUT_UNREADABLE, Stage.INPUT, detail)
    return Analysis(verdict="cannot_verify",
                    reasons=[Reason(ReasonKind.UNREADABLE, detail)],
                    failures=[failure])


def log_analysis(verdict, day, band, timings: dict) -> None:
    """One INFO line per analysis (failures log separately at ERROR)."""
    stages = " ".join(f"{k}={v * 1000:.0f}ms" for k, v in timings.items())
    log.info("analysis day=%s band=%s verdict=%s %s", day, band, verdict,
             stages)
