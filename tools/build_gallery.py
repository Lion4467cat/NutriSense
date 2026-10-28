"""Build the SigLIP2 gallery used by models.food_classifier (S2 + spec 002).

Usage:
    .venv/bin/python -m tools.build_gallery --source ../DATASET --out data/gallery.npz
    .venv/bin/python -m tools.build_gallery --source ../DATASET --wed data/wed
    .venv/bin/python -m tools.build_gallery --out data/gallery.npz --loo   (after a build)

Two entry sources, assembled into one artifact:
  * `--source`   menu-dish gold photos: <source>/<menu-id-or-alias dir>/*.jpg
                 labelled with the menu dish key (behaviour unchanged).
  * `--wed`      WED train ROI crops: for every train-manifest row, each
                 dish class's labelIds-mask region is bbox-cropped and
                 embedded, labelled with the WED class name (recognition
                 label -> serving target via data/wed_dishes.yaml serving:).
                 Embeddings + relative source paths only land in the
                 artifact — no WED image data enters the repo
                 (docs/licenses.md: WED terms absent -> cite, never
                 redistribute; RASOI CC BY-NC-SA is cleared for gallery use
                 by ticket 00 but deliberately not used this run, ledger
                 003).

Entry rules (models.food_classifier.build_gallery): every label must be a
menu id/alias or a WED class name; `background` is not a dish. Near-duplicate
frames (multi-view bursts) are dropped with the descending similarity guard.

`--loo` evaluates the gallery-method leave-one-out on the CURRENT artifact
at --out: per entry, exclude it, score with the same top-3 mean, check the
predicted serving target; prints accuracy, min/mean correct-class match
score (the abstain-threshold ceiling) and the min wrong-class score.
"""
import argparse
import glob
import json
import os

import cv2
import numpy as np

from config import GALLERY_PATH
from models.food_classifier import (MODEL_ID, build_gallery, load_gallery,
                                    menu_aliases, menu_dish_keys,
                                    serving_targets, save_gallery)

DUP_SIM = 0.9995


def scan_source(source):
    """-> list of (path, label); raises on unknown class dirs."""
    if not os.path.isdir(source):
        raise SystemExit(f"source directory does not exist: {source}")
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


def scan_wed_crops(wed_root, per_class_cap=24):
    """WED train ROI crops -> [(crop_bgr, class_name, source_rel)].

    Uses data/wed_manifest.jsonl train rows + labelIds masks (mask ids ==
    index_map ids 1..41; `background` never crops). Capped per class at
    per_class_cap, evenly spread over the class's crop list (sorted,
    deterministic) so the cap balances the gallery."""
    root = os.path.normpath(os.path.join(os.getcwd(), wed_root))
    manifest = os.path.normpath(os.path.join(root, "..", "wed_manifest.jsonl"))
    if not os.path.isfile(manifest):
        raise SystemExit(f"wed manifest not found at {manifest}")

    pool: dict[str, list[tuple[str, str, str, int]]] = {}
    with open(manifest) as fh:
        for line in fh:
            row = json.loads(line)
            if row["split"] != "train":
                continue
            rel_img, rel_mask = row["image"], row["mask"]
            for d in row["dishes"]:
                name = d["name"]
                if name == "background":
                    continue
                pool.setdefault(name, []).append(
                    (rel_img, rel_mask, name, int(d["class_id"])))
    entries = []
    for name in sorted(pool):
        pool[name].sort()
        cap = min(per_class_cap, len(pool[name]))
        idx = {round(i * (len(pool[name]) - 1) / max(cap - 1, 1))
               for i in range(cap)}
        for i in sorted(idx):
            rel_img, rel_mask, _, cid = pool[name][i]
            img = cv2.imread(os.path.join(root, rel_img))
            if img is None:
                raise SystemExit(f"wed image failed to decode: {rel_img}")
            mask = cv2.imread(os.path.join(root, rel_mask), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                raise SystemExit(f"wed mask failed to decode: {rel_mask}")
            vs, us = np.nonzero(mask == cid)
            if vs.size == 0:
                continue            # mask row drift: skip, never guess
            crop = img[vs.min():vs.max() + 1, us.min():us.max() + 1]
            entries.append((np.ascontiguousarray(crop), name, rel_img))
    if not entries:
        raise SystemExit("no wed crops extracted — check the manifest")
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="../DATASET",
                    help="menu-dish gold-photo root (menu id/alias dirs)")
    ap.add_argument("--wed", default=None, metavar="WED_ROOT",
                    help="data/wed root: add WED train ROI crops (spec 002)")
    ap.add_argument("--cap", type=int, default=24,
                    help="max WED crops per class (balance guard)")
    ap.add_argument("--out", default=str(GALLERY_PATH))
    ap.add_argument("--dedupe", type=float, default=DUP_SIM)
    ap.add_argument("--loo", action="store_true",
                    help="no build: evaluate LOO on the artifact at --out")
    args = ap.parse_args()

    if args.loo:
        return loo(args.out)

    entries = scan_source(args.source)
    print(f"gallery inputs: {len(entries)} gold images from {args.source}")
    if args.wed:
        crops = scan_wed_crops(args.wed, per_class_cap=args.cap)
        print(f"gallery inputs: {len(crops)} WED train crops from {args.wed}")
        entries += crops        # (img, label), (crop, name, source) tuples

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
    print(f"wrote {args.out} | model={back['model']} | per-label: {counts}")
    return 0


def loo(gallery_path):
    """Leave-one-out over a built artifact: accuracy on serving targets,
    min/mean correct-class match score, min wrong-class match score."""
    gal = load_gallery(gallery_path)
    E = gal["emb"]
    labels = [str(x) for x in gal["labels"]]
    targets = serving_targets()
    n = len(labels)
    correct, correct_score, wrong_score = 0, [], []
    misses = []
    for i in range(n):
        keep = [j for j in range(n) if j != i]
        sub = {k: (v[keep] if isinstance(v, np.ndarray) and v.ndim >= 1
                   and len(v) == n else v)
               for k, v in gal.items()}
        sims = E[keep] @ E[i]
        by_lab: dict[str, list[int]] = {}
        for k, j in enumerate(keep):
            lab = labels[j]
            if lab in targets:
                by_lab.setdefault(lab, []).append(k)
        scores: dict[str, float] = {}
        for lab, idxs in by_lab.items():
            vals = sims[idxs]
            kk = min(3, len(vals))
            s = float(np.sort(vals)[-kk:].mean())
            key = targets[lab]
            cur = scores.get(key)
            scores[key] = s if cur is None or s > cur else cur
        if not scores:
            raise SystemExit("LOO: no evaluable scores — check artifact labels")
        want = targets.get(labels[i])
        if want is None:
            continue
        best = max(scores.items(), key=lambda kv: kv[1])[0]
        if best == want:
            correct += 1
            correct_score.append(scores[want])
        else:
            misses.append((labels[i], best))
        wrong_score.append(scores[best])
    n_eval = len(correct_score) + len(misses)
    acc = correct / n_eval if n_eval else float("nan")
    print(f"LOO entries={n_eval} correct={correct} accuracy={acc:.4f}")
    if correct_score:
        print(f"min correct match={min(correct_score):.4f} "
              f"mean={float(np.mean(correct_score)):.4f}")
    if wrong_score:
        print(f"min wrong match={min(wrong_score):.4f}")
    if misses:
        shown = ", ".join(f"{a}->{b}" for a, b in misses[:10])
        more = " …" if len(misses) > 10 else ""
        print(f"misses: {shown}{more}")
    return 0


if __name__ == "__main__":
    main()
