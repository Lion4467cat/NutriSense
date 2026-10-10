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



def test_every_verdict_rule_change_moves_the_digest(monkeypatch):
    """Strict rule-set test: mutate each rule assess() reads (thresholds,
    gates, mandatory set, band minima/directions, factors, lint) and the
    digest must move — a stored record can never keep the old policy_version.
    Iterates the yaml itself, so a rule added later is covered automatically."""
    import copy

    base = load_policy().policy_version
    std0 = copy.deepcopy(config.load_standards())
    ledger0 = copy.deepcopy(config.load_params())
    n = 0

    def moved(label, std=None, ledger=None):
        nonlocal n
        n += 1
        if std is not None:
            monkeypatch.setitem(config._CACHE, "standards", std)
        if ledger is not None:
            monkeypatch.setitem(config._CACHE, "params", ledger)
        got = load_policy().policy_version
        assert got != base, f"digest ignores {label}"
        return got

    thr = std0["compliance"]["thresholds"]
    for k in thr:
        std = copy.deepcopy(std0)
        std["compliance"]["thresholds"][k] = float(thr[k]) + 0.01
        moved(f"thresholds.{k}", std=std)
    cov = std0["compliance"]["coverage"]
    for k in cov:
        std = copy.deepcopy(std0)
        std["compliance"]["coverage"][k] = float(cov[k]) + 0.01
        moved(f"coverage.{k}", std=std)
    std = copy.deepcopy(std0)
    std["compliance"]["mandatory_nutrients"] = ["kcal"]
    moved("mandatory_nutrients membership", std=std)
    for band, bandrow in std0["bands"].items():
        for key, row in bandrow.items():
            if not (isinstance(row, dict) and "value" in row):
                continue
            std = copy.deepcopy(std0)
            std["bands"][band][key]["value"] = row["value"] + 1
            moved(f"bands.{band}.{key}.value", std=std)
            std = copy.deepcopy(std0)
            std["bands"][band][key]["direction"] = "max"
            moved(f"bands.{band}.{key}.direction", std=std)
    for key in ("coverage_anchor_prior", "coverage_base_table_prior",
                "coverage_quality_degraded", "coverage_depth_uncalibrated",
                "lint_min_side_px"):
        ledger = copy.deepcopy(ledger0)
        step = 64 if key == "lint_min_side_px" else 0.05
        ledger[key]["value"] = float(ledger[key]["value"]) + step
        moved(f"params.{key}", ledger=ledger)

    # enough mutations actually ran (yaml has 2+2+1+6+4+1 = 16 rule moves)
    assert n >= 16, f"only {n} rule mutations exercised"
    monkeypatch.setitem(config._CACHE, "standards", std0)
    monkeypatch.setitem(config._CACHE, "params", ledger0)
    assert load_policy().policy_version == base  # restores cleanly
