"""Inventory existing ArUco captures and conservatively audit filename labels.

No new images are collected or altered. A filename label is only a candidate
reference; this tool does not infer whether a vessel value is tare or loaded
mass and does not mark any example as evaluation-ready without that evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT.parent / "Aruco_7ID_60mm_with_food"
GRAM = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*g\b", re.IGNORECASE)


def audit(root: Path = DEFAULT_SOURCE) -> dict:
    if not root.is_dir():
        raise FileNotFoundError(f"ArUco capture directory not found: {root}")
    images = sorted(path for path in root.rglob("*")
                    if path.is_file() and path.suffix.casefold() in {".jpg", ".jpeg", ".png"})
    rows = []
    for path in images:
        label_text = path.stem
        values = [float(match.group("value")) for match in GRAM.finditer(label_text)]
        rows.append({
            "relative_path": path.relative_to(root).as_posix(),
            "group_id": path.parent.name,
            "filename_contains_weight_values": values,
            "label_status": "candidate_only_tare_semantics_unverified" if values else "no_filename_weight",
            "mass_evaluation_eligible": False,
        })
    return {
        # Report collection identity, not the user's machine-local path.
        "source": root.name,
        "n_images": len(images),
        "n_groups": len({row["group_id"] for row in rows}),
        "n_filename_weight_candidates": sum(bool(row["filename_contains_weight_values"])
                                             for row in rows),
        "n_mass_evaluation_eligible": 0,
        "limitation": "Filename values do not establish food-only mass, tare semantics, or per-image correspondence; manual source records are required before scoring.",
        "images": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "data" / "reports" / "aruco_audit.json")
    args = parser.parse_args(argv)
    report = audit(args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"images={report['n_images']} groups={report['n_groups']} "
          f"weight_filename_candidates={report['n_filename_weight_candidates']} "
          "mass_evaluation_eligible=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
