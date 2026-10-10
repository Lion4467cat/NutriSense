"""Contract unit tests: closed Python vocabularies, path redaction, policy."""
import json

import pytest

import config
from engine.contract import (Analysis, Failure, FailureKind, Reason,
                             ReasonKind, STAGE_POLICY, Stage, WIRE_KEYS,
                             gate_reject, load_policy, reason_for_failure,
                             unreadable_analysis)


# --- closed vocabularies --------------------------------------------------

def test_reason_kinds_are_closed():
    with pytest.raises(ValueError):
        Reason(kind="not_a_kind", text="x")
    with pytest.raises(ValueError):
        Failure(kind="not_a_kind", stage=Stage.INPUT, error="x")
    with pytest.raises(ValueError):
        Failure(kind=FailureKind.STAGE_FAILED, stage="not_a_stage", error="x")


def test_every_stage_has_policy():
    assert set(STAGE_POLICY) == set(Stage)


# --- paths never survive --------------------------------------------------

def test_redaction_on_every_failure_kind():
    for kind in FailureKind:
        f = Failure(kind=kind, stage=Stage.INPUT,
                    error="cannot open /home/tinkerer/Desktop/Nutrisense/data/img.jpg for reading")
        assert "<path>" in f.error and "/home/" not in f.error
        f2 = Failure(kind=kind, stage=Stage.INPUT,
                     error="no C:\\Users\\jiya\\plate\\lunch.png on disk")
        assert "<path>" in f2.error and "C:\\" not in f2.error


def test_redaction_on_every_reason_kind():
    for kind in ReasonKind:
        r = Reason(kind=kind, text="failed reading /tmp/nutrisense/plate.jpg")
        assert "<path>" in r.text and "/tmp/" not in r.text


def test_reason_for_failure_is_redacted():
    f = Failure(FailureKind.STAGE_FAILED, Stage.SEGMENT,
                "RuntimeError: could not read /var/data/plate.jpg")
    r = reason_for_failure(f)
    assert r.kind is ReasonKind.STAGE_FAILED
    assert r.text.startswith("segment failed:")
    assert "/var/" not in r.text


def test_unreadable_analysis_full_shape():
    a = unreadable_analysis()
    wire = a.to_wire()
    assert set(wire) == set(WIRE_KEYS)
    assert wire["verdict"] == "cannot_verify"
    assert wire["reasons"][0]["kind"] == "unreadable"
    assert wire["failures"][0]["kind"] == "input_unreadable"
    for key in ("lint", "anchor", "segmentation", "classification", "dish",
                "portion", "nutrition", "coverage", "advisory", "compliance"):
        assert wire[key] is None


# --- gates emit failure + reason from one call ---------------------------

def test_gate_reject_single_source():
    f, r = gate_reject(ReasonKind.ZOOM, Stage.INPUT, "digital zoom 2.0 != 1.0")
    assert f.kind is FailureKind.GATE_REJECTED
    assert f.stage is Stage.INPUT
    assert f.error == r.text == "digital zoom 2.0 != 1.0"


# --- wire shape -----------------------------------------------------------

def test_analysis_wire_keys():
    wire = Analysis(verdict="cannot_verify").to_wire()
    assert set(wire) == set(WIRE_KEYS)
    assert wire["reasons"] == [] and wire["failures"] == []
    assert wire["policy"]["policy_version"]


def test_wire_json_serialisable():
    json.dumps(unreadable_analysis().to_wire())


# --- policy ---------------------------------------------------------------

def test_policy_matches_yaml_sources():
    p = load_policy()
    standards = config.load_standards()
    ledger = config.load_params()
    assert p.pass_p == standards["compliance"]["thresholds"]["pass_p"]
    assert p.fail_p == standards["compliance"]["thresholds"]["fail_p"]
    assert p.pass_min == standards["compliance"]["coverage"]["pass_min"]
    assert p.fail_min == standards["compliance"]["coverage"]["fail_min"]
    assert p.anchor_prior_cap == ledger["coverage_anchor_prior"]["value"]
    assert p.depth_uncalibrated == ledger["coverage_depth_uncalibrated"]["value"]
    assert p.lint_min_side_px == ledger["lint_min_side_px"]["value"]


def test_policy_version_is_stable_digest():
    a, b = load_policy(), load_policy()
    assert len(a.policy_version) == 12
    assert all(c in "0123456789abcdef" for c in a.policy_version)
    assert b.policy_version == a.policy_version
