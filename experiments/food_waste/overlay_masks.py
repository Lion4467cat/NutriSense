"""Render an ignored visual overlay for the first multi-item DEV example."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = HERE / "raw.jsonl"
OUT = HERE / "overlays" / "receipt-480660-row-0192.png"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; refusing CPU fallback")
    from models import registry
    from models.dish_segmenter import segment_food, segment_items

    row = next(
        json.loads(line) for line in RAW.read_text().splitlines()
        if line.strip() and (lambda r: r.get("source_row_idx") == 192)(json.loads(line))
    )
    image = cv2.imread(row["path"])
    if image is None:
        raise RuntimeError(f"unreadable image: {row['path']}")
    top = np.asarray(segment_food(image)["mask"], dtype=bool)
    items = segment_items(image).get("items") or []
    colors = [(0, 0, 255), (0, 220, 0), (255, 80, 0), (0, 220, 220)]
    overlay = image.copy()
    for index, item in enumerate(items):
        mask = np.asarray(item["mask"], dtype=bool)
        color = colors[index % len(colors)]
        overlay[mask] = (0.55 * overlay[mask] + 0.45 * np.array(color)).astype(np.uint8)
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, color, 3)
        x, y, _, _ = item["bbox"]
        cv2.putText(overlay, f"item {index+1}", (x, max(28, y-8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
    contours, _ = cv2.findContours(top.astype(np.uint8), cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (255, 255, 0), 4)
    cv2.putText(overlay, "top-level food mask: cyan", (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(OUT), overlay):
        raise RuntimeError(f"failed to write overlay: {OUT}")
    print(json.dumps({
        "overlay": str(OUT),
        "top_mask_area_px": int(top.sum()),
        "top_mask_area_frac": float(top.mean()),
        "item_areas_px": [int(np.asarray(item["mask"], dtype=bool).sum())
                          for item in items],
        "item_area_fracs": [float(np.asarray(item["mask"], dtype=bool).mean())
                             for item in items],
    }, sort_keys=True))
    registry.unload()
    torch.cuda.synchronize()


if __name__ == "__main__":
    main()
