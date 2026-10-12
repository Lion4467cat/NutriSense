"""Append one JSON line per evaluated run to runs/experiments.jsonl.

Bookkeeping only — no new dependencies, no MLflow, no network. Reads a
tools/run_eval.py JSON report and appends a compact record:

  ts · git · branch · tier · config · metrics (with the plate-bootstrap CIs)
  · latency_s · peak_vram_mb · source · note

`runs/` is gitignored: the log is local scratch, the evidence is the report
JSON under data/reports/ plus the ledger entry under docs/ledger/. The
record deliberately carries the tier and the CIs so a later session can tell
a DEV number from a locked one without re-reading the report.

Run:
  .venv/bin/python -m tools.log_run data/reports/run_eval_dev.json \
      [--note "baseline before idea X"] [--runs runs/experiments.jsonl]
Exit: 0 = appended · 2 = not a run_eval report
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

DEFAULT_RUNS = _ROOT / "runs" / "experiments.jsonl"


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=_ROOT, text=True,
                                       timeout=10).strip()
    except Exception:
        return "unknown"


def build_record(report: dict, source: Path, note: str | None = None) -> dict:
    if "tier" not in report or "mae_g" not in report:
        raise ValueError("not a run_eval report (no tier/mae_g)")
    stress = {}
    for name, block in (report.get("stress") or {}).items():
        stress[name] = {"mae_g": block.get("mae_g"),
                        "mae_g_ci95": block.get("mae_g_bootstrap_95ci"),
                        "coverage_90": block.get("coverage_90"),
                        "label": block.get("label")}
    return {
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git": _git("rev-parse", "--short", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "tier": report["tier"],
        "config": {k: report.get(k) for k in
                   ("seed", "split_seed", "val_frac", "bootstrap_reps",
                    "device", "checkpoint", "limit", "stress_label")},
        "metrics": {
            "mae_g": report.get("mae_g"),
            "mae_g_ci95": report.get("mae_g_bootstrap_95ci"),
            "coverage_90": report.get("coverage_90"),
            "coverage_90_ci95": report.get("coverage_bootstrap_95ci"),
            "mape_pct": report.get("mape_pct"),
            "mean_interval_width_g": report.get("mean_interval_width_g"),
            "n_views": report.get("n_views"),
            "n_plates": report.get("n_plates"),
            "n_samples": report.get("n_samples"),
            "n_skipped_no_sigma": report.get("n_skipped_no_sigma"),
        },
        "stress": stress or None,
        "latency_s": report.get("wall_s"),
        "peak_vram_mb": report.get("peak_vram_mb"),
        "source": str(source),
        "note": note,
    }


def append(record: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", type=Path, help="run_eval JSON report")
    ap.add_argument("--note", default=None,
                    help="one-line context, e.g. 'baseline before idea X'")
    ap.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    args = ap.parse_args(argv)
    try:
        report = json.loads(args.report.read_text())
        record = build_record(report, args.report, args.note)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    append(record, args.runs)
    m = record["metrics"]
    print(f"logged tier={record['tier']} git={record['git']} "
          f"branch={record['branch']} mae_g={m['mae_g']} "
          f"mae_g_ci95={m['mae_g_ci95']} latency_s={record['latency_s']} "
          f"peak_vram_mb={record['peak_vram_mb']} -> {args.runs}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
