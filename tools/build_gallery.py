"""Build the SigLIP2 gallery used by models.food_classifier (S2).

Usage:
    .venv/bin/python -m tools.build_gallery --source ../DATASET --out data/gallery.npz

Source layout: <source>/<class_dir>/*.jpg where class_dir maps to a
data/menu.yaml dish id or alias. Embeddings only are stored (never images),
so the gallery artifact stays inside the repo's redistribution rules.
"""
import argparse
import glob
import os

import cv2
import numpy as np

from models.food_classifier import (MODEL_ID, build_gallery, load_gallery,
                                    menu_aliases, menu_dish_keys, save_gallery)

DUP_SIM = 0.9995


def scan_source(source):
    """-> list of (path, dish_key); raises on unknown class dirs."""
    entries = []
    dirs = sorted(d for d in os.listdir(source)
                  if os.path.isdir(os.path.join(source, d)))
    known = {}
    for key in menu_dish_keys():
        known[key] = key
        for a in menu_aliases(key):
            known[a] = key
    for d in dirs:
        if d not in known:
            raise SystemExit(f"unknown class dir {d!r} — not a menu id/alias")
        for f in sorted(glob.glob(os.path.join(source, d, "*.jpg"))):
            entries.append((f, known[d]))
    if not entries:
        raise SystemExit(f"no jpgs under {source}")
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="../DATASET")
    ap.add_argument("--out", default="data/gallery.npz")
    ap.add_argument("--dedupe", type=float, default=DUP_SIM)
    args = ap.parse_args()

    entries = scan_source(args.source)
    print(f"gallery inputs: {len(entries)} images from {args.source}")
    gal = build_gallery(entries)
    n0 = len(gal["labels"])

    # drop near-duplicates (collage reposts of the same capture)
    E = gal["emb"]
    keep = []
    for i in range(len(E)):
        if keep:
            sims = E[keep] @ E[i]
            if float(sims.max()) >= args.dedupe:
                continue
        keep.append(i)
    if len(keep) != n0:
        gal = {k: (v[keep] if isinstance(v, np.ndarray) and len(v) == n0 else v)
               for k, v in gal.items()}
        gal["emb"] = E[keep]
        print(f"deduped {n0} -> {len(keep)}")
    save_gallery(gal, args.out)
    back = load_gallery(args.out)
    counts = {k: int((back["labels"] == k).sum()) for k in sorted(set(back["labels"]))}
    print(f"wrote {args.out} | model={back['model']} | per-dish: {counts}")


if __name__ == "__main__":
    main()
