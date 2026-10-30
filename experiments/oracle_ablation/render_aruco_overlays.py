"""Render saved ArUco masks into full-frame overlays/contact sheets."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from run_aruco_eval import _draw_overlay, _write_contact_sheets

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "aruco_mask_capture.jsonl"


def main() -> None:
    rows = [json.loads(line) for line in RAW.read_text().splitlines()
            if json.loads(line).get("event") == "image_result"
            and json.loads(line).get("mode") == "default"]
    for row in rows:
        image_path = Path(row["image"])
        artifact = row["mask_artifacts"]
        with np.load(artifact["npz"]) as data:
            top = data["top_mask"].astype(bool) if "top_mask" in data else None
            item_masks = [data[f"item_mask_{i}"].astype(bool)
                          for i in range(len(row["result"].get("items") or []))
                          if f"item_mask_{i}" in data]
        import cv2
        image = cv2.imread(str(image_path))
        overlay = _draw_overlay(
            image, top, item_masks, row["result"].get("items") or [],
            artifact.get("marker_quad_px"),
            f"{row['plate']} / {image_path.name}")
        out = Path(artifact["overlay"])
        out.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out), overlay)
    _write_contact_sheets(rows)
    print(f"rendered_overlays={len(rows)}")
    print(f"contact_sheets={len(list((ROOT / 'overlays').glob('*contact_sheet.png')))}")


if __name__ == "__main__":
    main()
