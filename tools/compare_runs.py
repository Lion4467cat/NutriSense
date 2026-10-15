"""Paired comparison of two run_eval reports (same tier): candidate − baseline.

Both reports must come from tools/run_eval.py, which records `per_plate`
aggregates (n, sum_abs_err, n_sigma, n_covered per plate). The comparison is
a PAIRED bootstrap: each replicate draws a multiset of PLATES (not views)
and evaluates BOTH runs on that same multiset, so plate-to-plate difficulty
cancels and the CI answers "did this change move the metric", not "how hard
is WED". Seed is fixed, so a re-comparison is reproducible.

Reports:
  * MAE (g)       — paired difference + 95% CI
  * coverage_90   — paired difference + 95% CI    * every stress perturbation present in BOTH reports (same two statistics)

Pairwise stress (same report, when --stress-x is set):
  * --stress-x KEY --stress-y KEY  paired CI on two stress perturbations
    within ONE report (both flags; identical K is refused).
  * --stress-x KEY  auto-picks the first other perturbation in the report.
  * Without --stress-x  the usual cross-report paired comparison.

Refuses (exit 2) to compare:
  * runs from different tiers (dev / train / locked)
  * runs scored over different plate sets (different carve, different rows,
    or a --limit smoke run)
  * reports without per_plate aggregates (older format — re-run run_eval)

Run:
  .venv/bin/python -m tools.compare_runs baseline.json candidate.json \
      [--seed 42] [--out data/reports/compare.json]
  .venv/bin/python -m tools.compare_runs single_stress.json \
      single_stress.json --stress-x KEY [ --stress-y OTHER_KEY ]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.run_eval import BOOTSTRAP_REPS  # noqa: E402

DEFAULT_SEED = 42


class CompareRefused(ValueError):
    """Different tiers, different plate sets, or unusable reports."""


def _plates(report: dict, where: str) -> dict[str, dict]:
    pc = report.get("per_plate")
    if not isinstance(pc, dict) or not pc:
        raise CompareRefused(
            f"{where}: no per_plate aggregates — re-run tools/run_eval.py "
            "with the current code (older reports cannot be paired)")
    return pc


def _point(base_pc: dict[str, dict], cand_pc: dict[str, dict]) -> dict:
    b_abs = sum(v["sum_abs_err"] for v in base_pc.values())
    b_n = sum(v["n"] for v in base_pc.values())
    c_abs = sum(v["sum_abs_err"] for v in cand_pc.values())
    c_n = sum(v["n"] for v in cand_pc.values())
    b_ns = sum(v["n_sigma"] for v in base_pc.values())
    c_ns = sum(v["n_sigma"] for v in cand_pc.values())
    b_cov = sum(v["n_covered"] for v in base_pc.values())
    c_cov = sum(v["n_covered"] for v in cand_pc.values())
    return {
        "mae_g": {"baseline": round(b_abs / b_n, 3),
                  "candidate": round(c_abs / c_n, 3),
                  "diff": round(c_abs / c_n - b_abs / b_n, 3)},
        "coverage_90": {
            "baseline": round(b_cov / b_ns, 4) if b_ns else None,
            "candidate": round(c_cov / c_ns, 4) if c_ns else None,
            "diff": (round(c_cov / c_ns - b_cov / b_ns, 4)
                     if b_ns and c_ns else None)},
        "n_plates": len(base_pc),
        "n_samples": b_n,
    }


def paired_bootstrap(base_pc: dict[str, dict], cand_pc: dict[str, dict],
                     *, seed: int, reps: int) -> dict:
    """Point estimates + percentile 95% CIs of the paired differences."""
    plates = sorted(base_pc)
    rng = np.random.default_rng(seed)
    mae_diffs: list[float] = []
    cov_diffs: list[float] = []
    for _ in range(reps):
        pick = rng.integers(0, len(plates), size=len(plates))
        b_abs = b_n = c_abs = c_n = 0.0
        b_cov = b_ns = c_cov = c_ns = 0.0
        for j in pick:
            p = plates[int(j)]
            bp, cp = base_pc[p], cand_pc[p]
            b_abs += bp["sum_abs_err"]; b_n += bp["n"]
            c_abs += cp["sum_abs_err"]; c_n += cp["n"]
            b_cov += bp["n_covered"]; b_ns += bp["n_sigma"]
            c_cov += cp["n_covered"]; c_ns += cp["n_sigma"]
        mae_diffs.append(c_abs / c_n - b_abs / b_n)
        if b_ns and c_ns:
            cov_diffs.append(c_cov / c_ns - b_cov / b_ns)
    out = _point(base_pc, cand_pc)
    out["reps"] = reps
    out["seed"] = seed

    def ci(vals: list[float], nd: int) -> list[float] | None:
        if not vals:
            return None
        return [round(float(x), nd) for x in np.percentile(vals, [2.5, 97.5])]
    out["mae_g"]["diff_ci95"] = ci(mae_diffs, 3)
    out["coverage_90"]["diff_ci95"] = ci(cov_diffs, 4)
    return out


def _stress_pair(base: dict, cand: dict, *, seed: int, reps: int) -> dict:
    b_st = base.get("stress") or {}
    c_st = cand.get("stress") or {}
    shared = [k for k in sorted(set(b_st) & set(c_st))]
    paired = {}
    for name in shared:
        b_pc = _plates(b_st[name], f"baseline stress {name}")
        c_pc = _plates(c_st[name], f"candidate stress {name}")
        if sorted(b_pc) != sorted(c_pc):
            raise CompareRefused(
                f"stress {name}: plate sets differ between the two runs")
        paired[name] = paired_bootstrap(b_pc, c_pc, seed=seed, reps=reps)
    return {"paired": paired,
            "missing_in_baseline": sorted(set(c_st) - set(b_st)),
            "missing_in_candidate": sorted(set(b_st) - set(c_st))}


def _stress_pairwise_single_report(report: dict, *, key_x: str, key_y: str | None,
                                   seed: int, reps: int) -> dict:
    st = report.get("stress") or {}
    if key_x not in st:
        raise CompareRefused(f"stress perturbation {key_x!r} not in report")
    if key_y is None:
        missing = [k for k in sorted(st) if k != key_x]
        if not missing:
            raise CompareRefused(
                "single stress perturbation in report — cannot form a pairwise pair")
        key_y = missing[0]
    if key_y not in st:
        raise CompareRefused(
            f"stress perturbation {key_y!r} not in report (need {key_x!r} and {key_y!r})")
    if key_x == key_y:
        raise CompareRefused(
            f"stress perturbations {key_x!r} and {key_y!r} are the same; "
            f"use two distinct perturbations for a pairwise comparison")
    a_pc = _plates(st[key_x], f"stress {key_x}")
    b_pc = _plates(st[key_y], f"stress {key_y}")
    if sorted(a_pc) != sorted(b_pc):
        raise CompareRefused(f"stress {key_x} vs {key_y}: plate sets differ")
    block = paired_bootstrap(a_pc, b_pc, seed=seed, reps=reps)
    block["y"] = key_y
    return {
        "paired_single": {key_x: block},
        "missing_in_baseline": [],
        "missing_in_candidate": [],
    }


def _build_result_for_single_report_stress(report: dict, *, seed: int,
                                                 reps: int, stress_x: str,
                                                 stress_y: str | None) -> dict:
    tier = report.get("tier")
    pc = _plates(report, "baseline")
    pc2 = _plates(report, "candidate")
    if sorted(pc) != sorted(pc2):
        raise CompareRefused("baseline and candidate plate sets differ within the same report")
    out = {
        "tier": tier,
        "seed": seed,
        "baseline": {
            "mae_g": round(
                sum(v["sum_abs_err"] for v in pc.values()) /
                sum(v["n"] for v in pc.values()), 3),
            "coverage_90": (
                round(
                    sum(v["n_covered"] for v in pc.values()) /
                    sum(v["n_sigma"] for v in pc.values()), 4)
                if sum(v["n_sigma"] for v in pc.values())
                else None),
        },
        "candidate": {
            "mae_g": None,
            "coverage_90": None,
        },
    }
    out["baseline"]["coverage_90"] = (
        round(
            sum(v["n_covered"] for v in pc.values()) /
            sum(v["n_sigma"] for v in pc.values()), 4)
        if sum(v["n_sigma"] for v in pc.values())
        else None)
    pb = paired_bootstrap(pc, pc2, seed=seed, reps=reps)
    out.update(pb)
    out["stress"] = _stress_pairwise_single_report(
        report, key_x=stress_x, key_y=stress_y, seed=seed, reps=reps)
    out["n_plates"] = len(pc)
    out["n_samples"] = sum(v["n"] for v in pc.values())
    return out


def compare(baseline: dict, candidate: dict, *, seed: int = DEFAULT_SEED,
            reps: int = BOOTSTRAP_REPS) -> dict:
    tier_b, tier_c = baseline.get("tier"), candidate.get("tier")
    if tier_b != tier_c:
        raise CompareRefused(f"different tiers: baseline={tier_b!r} "
                             f"candidate={tier_c!r}")
    base_pc = _plates(baseline, "baseline")
    cand_pc = _plates(candidate, "candidate")
    if sorted(base_pc) != sorted(cand_pc):
        only_b = sorted(set(base_pc) - set(cand_pc))[:5]
        only_c = sorted(set(cand_pc) - set(base_pc))[:5]
        raise CompareRefused(
            f"different plate sets ({len(base_pc)} vs {len(cand_pc)} plates); "
            f"only baseline: {only_b}; only candidate: {only_c}")
    out = {"tier": tier_b, "seed": seed,
           "baseline": {"mae_g": baseline.get("mae_g"),
                        "coverage_90": baseline.get("coverage_90")},
           "candidate": {"mae_g": candidate.get("mae_g"),
                         "coverage_90": candidate.get("coverage_90")}}
    out.update(paired_bootstrap(base_pc, cand_pc, seed=seed, reps=reps))
    out["stress"] = _stress_pair(baseline, candidate, seed=seed, reps=reps)
    return out


def _print_result(res: dict) -> None:
    t = res["tier"]
    m, c = res["mae_g"], res["coverage_90"]
    print(f"tier={t} plates={res['n_plates']} samples={res['n_samples']} "
          f"seed={res['seed']} reps={res['reps']}", flush=True)
    print(f"tier={t} mae_g: baseline {m['baseline']} -> candidate "
          f"{m['candidate']}  diff {m['diff']}  paired_ci95 {m['diff_ci95']}",
          flush=True)
    print(f"tier={t} coverage_90: baseline {c['baseline']} -> candidate "
          f"{c['candidate']}  diff {c['diff']}  paired_ci95 {c['diff_ci95']}",
          flush=True)
    st = res["stress"]
    if "paired" in st:
        for name, block in st["paired"].items():
            sm = block["mae_g"]
            print(f"tier={t} stress={name} mae_g: baseline {sm['baseline']} -> "
                  f"candidate {sm['candidate']}  diff {sm['diff']}  "
                  f"paired_ci95 {sm['diff_ci95']}", flush=True)
    if "paired_single" in st:
        for name, block in st["paired_single"].items():
            sm = block["mae_g"]
            print(f"tier={t} stress-pair={name}(x) <-> {block.get('y', '???')}: "
                  f"baseline {sm['baseline']} -> candidate {sm['candidate']}  "
                  f"diff {sm['diff']}  paired_ci95 {sm['diff_ci95']}", flush=True)
    for key in ("missing_in_baseline", "missing_in_candidate"):
        if st.get(key):
            print(f"tier={t} stress {key}: {st[key]}", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("baseline", type=Path, help="run_eval JSON (baseline)")
    ap.add_argument("candidate", type=Path, help="run_eval JSON (candidate)")
    ap.add_argument("--stress-x", type=str, default=None,
                    help="pairwise stress perturbation key (single-report mode when set)")
    ap.add_argument("--stress-y", type=str, default=None,
                    help="pairwise stress perturbation key (with --stress-x; if omitted, auto-picks another in the same report)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--reps", type=int, default=BOOTSTRAP_REPS)
    ap.add_argument("--out", type=Path, default=None,
                    help="also write the comparison JSON here")
    args = ap.parse_args(argv)
    try:
        baseline = json.loads(args.baseline.read_text())
        candidate = json.loads(args.candidate.read_text())
        if args.stress_x is not None:
            if not args.baseline.samefile(args.candidate):
                raise CompareRefused(
                    "--stress-x/--stress-y pairwise mode requires a single report "
                    "(baseline and candidate must be the same file)")
            res = _build_result_for_single_report_stress(
                baseline, seed=args.seed, reps=args.reps,
                stress_x=args.stress_x, stress_y=args.stress_y)
        else:
            res = compare(baseline, candidate, seed=args.seed, reps=args.reps)
    except CompareRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    _print_result(res)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, indent=2) + "\n")
        print(f"tier={res['tier']} wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
