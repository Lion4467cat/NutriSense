"""Kill switch for the iteration loop.

Exits 1 if a file named STOP exists in the repo root, else 0.

Every loop iteration MUST run this first and exit cleanly when it fails:

  .venv/bin/python -m tools.should_stop || exit 0

STOP is gitignored (local scratch), so it is never committed and never
exists on CI. Create/remove it to pause and resume the loop:

  touch STOP     # pause — the next iteration halts before touching anything
  rm STOP        # resume

Run:  .venv/bin/python -m tools.should_stop
Exit: 0 = proceed · 1 = STOP present, halt
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
STOP_FILE = _ROOT / "STOP"


def should_stop(stop_file: Path = STOP_FILE) -> bool:
    return stop_file.exists()


def main() -> int:
    if should_stop():
        print(f"STOP: {STOP_FILE} exists — halting this loop iteration",
              file=sys.stderr)
        return 1
    print("should_stop: clear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
