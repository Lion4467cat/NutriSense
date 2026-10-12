"""Hash-based protection for the WED evaluation (docs/eval_protocol.md).

docs/locked_manifest.txt pins a SHA-256 for:

  (a) eval code     — tools/run_eval.py (tiers, metrics, bootstrap),
                      tools/stress_suite.py (frozen perturbations),
                      tools/compare_runs.py (paired candidate-vs-baseline),
                      tools/check_locked.py (this guard),
                      tools/build_wed_manifest.py (builds the split definition)
  (b) eval data     — data/wed_manifest.jsonl (the train/test row set the
                      tiers are carved from)
  (c) locked images — every file under data/wed/test/ (present locally only;
                      the dataset is git-ignored, so CI sees none of them)

NOT pinned, deliberately — the model is what gets evaluated, so model and
training artifacts may change between runs (retraining, new sigma, new
architecture) without invalidating the evaluation harness:

  models/weight_head.py, tools/train_weight_head.py,
  data/weight_head_sigma.yaml, data/weight_head.pt

Those four are listed in MODEL_ARTIFACTS below and are REJECTED if they ever
re-appear in the manifest.

Any entry whose hash differs, or any (a)/(b) entry that is missing, exits 1.
(c) entries that are absent locally are reported as SKIP and do not fail —
CI runs without the dataset. Everything else must match.

Regenerating the manifest re-pins what the evaluation is allowed to be:
  .venv/bin/python -m tools.check_locked --write
That is a deliberate, approved act (docs/eval_protocol.md "Changing the
evaluation"), not an ordinary fix.

Run:  .venv/bin/python -m tools.check_locked [--write] [--quiet]
Exit: 0 = pinned files match · 1 = changed / missing / unreadable
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

MANIFEST = _ROOT / "docs" / "locked_manifest.txt"
LOCAL_ONLY = "data/wed/test/"          # git-ignored: absent locally is SKIP

CODE = (
    "tools/run_eval.py",
    "tools/stress_suite.py",
    "tools/compare_runs.py",
    "tools/check_locked.py",
    "tools/build_wed_manifest.py",
    "tools/card_stress.py",
)
DATA = (
    "data/wed_manifest.jsonl",
)
# Model / training artifacts — may change with a retrain, so they are NOT
# part of the lock. Presence in the manifest is itself a failure.
MODEL_ARTIFACTS = (
    "models/weight_head.py",
    "tools/train_weight_head.py",
    "data/weight_head_sigma.yaml",
    "data/weight_head.pt",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def locked_paths(root: Path) -> list[str]:
    """Deterministic file list: (a) + (b) + (c), sorted, repo-relative."""
    paths = [p for p in [*CODE, *DATA] if (root / p).is_file()]
    test_dir = root / LOCAL_ONLY
    if test_dir.is_dir():
        paths += sorted(str(p.relative_to(root))
                        for p in test_dir.rglob("*") if p.is_file())
    return sorted(paths)


def read_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, rel = line.partition("  ")
        if len(digest) != 64 or not rel:
            raise ValueError(f"malformed manifest line: {line!r}")
        entries[rel] = digest
    return entries


def write_manifest(path: Path = MANIFEST, root: Path = _ROOT) -> int:
    from datetime import UTC, datetime
    rows = locked_paths(root)
    lines = [
        "# docs/locked_manifest.txt — SHA-256 pins for the WED evaluation.",
        "# Scope: eval code (tools/run_eval, tools/stress_suite,",
        "# tools/compare_runs, tools/check_locked, tools/build_wed_manifest),",
        "# the split definition data/wed_manifest.jsonl, and every file under",
        "# data/wed/test/ (git-ignored — present locally only).",
        "# Model/training artifacts are deliberately NOT pinned: models/weight_head.py,",
        "# tools/train_weight_head.py, data/weight_head_sigma.yaml, data/weight_head.pt.",
        "# Verify: .venv/bin/python -m tools.check_locked",
        "# Regenerate ONLY deliberately, with approval:",
        "#   .venv/bin/python -m tools.check_locked --write",
        f"# written: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}  files: {len(rows)}",
    ]
    lines += [f"{sha256(root / rel)}  {rel}" for rel in rows]
    path.write_text("\n".join(lines) + "\n")
    return len(rows)


def check(path: Path = MANIFEST, root: Path = _ROOT, *, quiet: bool = False) -> int:
    if not path.exists():
        print(f"MISSING manifest {path}", file=sys.stderr)
        return 1
    try:
        entries = read_manifest(path)
    except ValueError as exc:
        print(f"BAD manifest: {exc}", file=sys.stderr)
        return 1
    failed = skipped = ok = 0
    for rel, want in entries.items():
        if rel in MODEL_ARTIFACTS:
            failed += 1
            print(f"MODEL_ARTIFACT_PINNED {rel} "
                  "(model/training artifact must not be pinned)")
            continue
        target = root / rel
        if not target.exists():
            if rel.startswith(LOCAL_ONLY):
                skipped += 1
                if not quiet:
                    print(f"SKIP {rel} (absent — dataset not present)")
                continue
            failed += 1
            print(f"MISSING {rel}")
            continue
        got = sha256(target)
        if got != want:
            failed += 1
            print(f"CHANGED {rel}\n  want {want}\n  got  {got}")
        else:
            ok += 1
    extra = [rel for rel in locked_paths(root) if rel not in entries]
    for rel in extra:
        failed += 1
        print(f"UNPINNED {rel} (in lock scope but absent from the manifest)")
    if not quiet:
        print(f"check_locked: {ok} ok, {skipped} skipped, {failed} failed "
              f"({len(entries)} pinned)")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true",
                    help="regenerate docs/locked_manifest.txt (approved changes only)")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--root", type=Path, default=_ROOT)
    args = ap.parse_args(argv)
    if args.write:
        n = write_manifest(args.manifest, args.root)
        print(f"wrote {args.manifest} ({n} files)")
        return 0
    return check(args.manifest, args.root, quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
