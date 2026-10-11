"""Pyright error-count gate: fail CI only on NEW type errors.

STAGE 5: the tree ships with a known pyright baseline (basic mode — see
pyrightconfig.json; counted 2026-10-12 into pyright.baseline). Existing
findings must not block CI; any increase above the recorded count fails.
When errors are genuinely fixed, re-record the lower count:

  .venv/bin/python -m tools.pyright_gate --update
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
BASELINE = _ROOT / "pyright.baseline"


def count_errors() -> int:
    exe = Path(sys.executable).with_name("pyright")
    proc = subprocess.run([str(exe), "--outputjson"], cwd=_ROOT,
                          capture_output=True, text=True)
    payload = proc.stdout
    start = payload.find("{")
    if start < 0:
        sys.stderr.write(payload + proc.stderr)
        raise SystemExit("pyright produced no JSON output")
    summary = json.loads(payload[start:])["summary"]
    return int(summary["errorCount"])


def main(argv: list[str]) -> int:
    n = count_errors()
    if "--update" in argv:
        BASELINE.write_text(f"{n}\n")
        print(f"pyright.baseline updated: {n}")
        return 0
    baseline = int(BASELINE.read_text().strip())
    print(f"pyright: {n} errors (baseline {baseline})")
    if n > baseline:
        print(f"FAIL: {n - baseline} new error(s) above baseline — fix them, "
              "or re-record with --update if the increase is intentional")
        return 1
    if n < baseline:
        print(f"note: {baseline - n} error(s) fixed — "
              "re-record with --update to lock the improvement in")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
