"""Read-only exact-hash overlap check for the eval photos and local image sets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT.parent / "Aruco_7ID_60mm_with_food"
SOURCES = [ROOT / "data/wed", ROOT.parent / "DATASET"]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    eval_files = sorted(p for p in EVAL.rglob("*")
                        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    eval_hashes = {_sha(p): p for p in eval_files}
    for root in SOURCES:
        scanned = 0
        matches = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            scanned += 1
            digest = _sha(path)
            if digest in eval_hashes:
                matches.append({"eval": str(eval_hashes[digest]), "source": str(path),
                                "sha256": digest})
        print(json.dumps({"event": "hash_overlap_check", "eval_images": len(eval_files),
                          "source_root": str(root), "source_images_scanned": scanned,
                          "matches": matches}, sort_keys=True))


if __name__ == "__main__":
    main()
