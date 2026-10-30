#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
if [[ -n "${PYTHON:-}" ]]; then
  python_bin="$PYTHON"
elif [[ -x .venv/bin/python ]]; then
  python_bin=".venv/bin/python"
else
  python_bin="python3"
fi
"$python_bin" -c 'import huggingface_hub' 2>/dev/null || { echo "Missing huggingface_hub for $python_bin." >&2; exit 1; }

mkdir -p datasets/raw/portion/ecustfd datasets/raw/portion/fpb

# ECUSTFD image/annotation mirror is ~144 MB in this download. Its upstream reuse terms remain unclear.
"$python_bin" - <<'PY'
import os
from huggingface_hub import snapshot_download

downloads = [
    (
        "ai5labsOfficial/ecustfd",
        "datasets/raw/portion/ecustfd",
        ["README.md", "annotations.csv", "food_types.csv", "images/**"],
    ),
]

# FPB has 28,155 separate files in the Hub snapshot; require explicit opt-in.
if os.environ.get("DOWNLOAD_FPB") == "1":
    downloads.append(
        (
            "issai/Food_Portion_Benchmark",
            "datasets/raw/portion/fpb",
            ["README.md", "FPB_Dataset/**"],
        )
    )

for repo, dest, patterns in downloads:
    snapshot_download(
        repo_id=repo,
        repo_type="dataset",
        local_dir=dest,
        max_workers=4,
        allow_patterns=patterns,
    )
PY

if [[ "${DOWNLOAD_FPB:-0}" == "1" ]]; then
  echo "Downloaded ECUSTFD and FPB under datasets/raw/portion/. Review each dataset's README/license before use."
else
  echo "Downloaded ECUSTFD under datasets/raw/portion/ecustfd/. FPB is an optional multi-hour download; set DOWNLOAD_FPB=1 to fetch it."
fi
