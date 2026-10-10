"""One gate table, one owner (review #1).

analyze() is the only caller: input gates are consulted once before the
stages, the scope gate once immediately after classification (its result is
only known then). Each entry abstains through engine.contract.gate_reject —
the single helper that derives Failure and Reason from one text — so failure
and reason can never drift. assess() never consults this table; it only
scores admitted plates.
"""
from typing import Callable, NamedTuple

from engine.contract import Failure, Reason, ReasonKind, Stage, gate_reject

_BANDS = ("1-5", "6-8", "9-10")


class GateOutcome(NamedTuple):
    admitted: bool
    failure: Failure | None = None
    reason: Reason | None = None


class Gate(NamedTuple):
    name: str
    stage: Stage          # stage attribution for the abstention
    kind: ReasonKind      # wire reason kind
    verdict: str          # verdict the abstention reports
    detail: Callable[[dict], str | None]  # None -> admitted


def _zoom(ctx: dict) -> str | None:
    zoom = (ctx.get("lint") or {}).get("digital_zoom")
    if zoom is None or float(zoom) == 1.0:
        return None
    return f"digital zoom {zoom} != 1.0 (protocol requires zoom==1)"


def _day(ctx: dict) -> str | None:
    day = ctx.get("day")
    if day in ctx["menu"]["days"]:
        return None
    return f"unknown day {day!r}"


def _band(ctx: dict) -> str | None:
    band = ctx.get("band")
    if band in _BANDS:
        return None
    return f"unknown class band {band!r}"


def _scope(ctx: dict) -> str | None:
    dish = ctx.get("dish") or {}
    if dish.get("status") == "out_of_scope" or dish.get("nutrition_source") == "out_of_scope":
        return "dish is out of scope (not portion-scored)"
    return None


ZOOM = Gate("zoom", Stage.INPUT, ReasonKind.ZOOM, "cannot_verify", _zoom)
DAY = Gate("day", Stage.INPUT, ReasonKind.UNKNOWN_DAY, "cannot_verify", _day)
BAND = Gate("band", Stage.INPUT, ReasonKind.UNKNOWN_BAND, "cannot_verify", _band)
SCOPE = Gate("scope", Stage.CLASSIFY, ReasonKind.OUT_OF_SCOPE, "out_of_scope", _scope)

GATE_TABLE = (ZOOM, DAY, BAND, SCOPE)

#: consulted once in analyze() before the stages
INPUT_GATES = (ZOOM, DAY, BAND)
#: consulted once in analyze() immediately after classification
SCOPE_GATE = SCOPE


def admit(gate: Gate, **ctx) -> GateOutcome:
    """Admitted, or an abstention carrying Failure + Reason from gate_reject."""
    detail = gate.detail(ctx)
    if detail is None:
        return GateOutcome(True)
    failure, reason = gate_reject(gate.kind, gate.stage, detail)
    return GateOutcome(False, failure, reason)
