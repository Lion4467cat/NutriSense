"""Render the exact padded item classifier crops as inspection contact sheets."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "aruco_mask_capture.jsonl"
OUT = ROOT / "classifier_crops"
TILE_W, TILE_H, COLS = 400, 300, 4


def main() -> None:
    rows = [json.loads(line) for line in RAW.read_text().splitlines()
            if json.loads(line).get("event") == "image_result"
            and json.loads(line).get("mode") == "default"]
    OUT.mkdir(exist_ok=True)
    total = 0
    for plate in sorted({row["plate"] for row in rows}):
        tiles = []
        for row in rows:
            if row["plate"] != plate:
                continue
            image = Image.open(row["image"]).convert("RGB")
            items = (row.get("result") or {}).get("items") or []
            for i, item in enumerate(items):
                x0, y0, x1, y1 = [int(v) for v in item.get("bbox", [0, 0, *image.size])]
                padx, pady = int((x1 - x0) * 0.10), int((y1 - y0) * 0.10)
                crop = image.crop((max(0, x0 - padx), max(0, y0 - pady),
                                   min(image.width, x1 + padx), min(image.height, y1 + pady)))
                crop.thumbnail((TILE_W - 12, TILE_H - 42))
                tile = Image.new("RGB", (TILE_W, TILE_H), "white")
                tile.paste(crop, ((TILE_W - crop.width) // 2, 34 + (TILE_H - 42 - crop.height) // 2))
                d = ImageDraw.Draw(tile)
                label = (item.get("classification") or {}).get("dish") or "unrecognized"
                d.text((5, 4), f"{row['plate']} | {Path(row['image']).name[:34]} | item {i}", fill="black")
                d.text((5, 20), f"label={label} grams={(item.get('portion') or {}).get('grams')}", fill="black")
                tiles.append(tile)
                total += 1
        if not tiles:
            continue
        out = Image.new("RGB", (COLS * TILE_W,
                                ((len(tiles) + COLS - 1) // COLS) * TILE_H),
                        "#bbbbbb")
        for i, tile in enumerate(tiles):
            out.paste(tile, ((i % COLS) * TILE_W, (i // COLS) * TILE_H))
        path = OUT / f"{plate.replace(' ', '_')}.png"
        out.save(path)
        print(f"{path} crops={len(tiles)} size={out.width}x{out.height}")
    print(f"total_classifier_crops={total}")


if __name__ == "__main__":
    main()
