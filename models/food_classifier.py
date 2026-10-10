"""SigLIP2 dish classifier (S2) — gallery-first, text zero-shot fallback.

The plan licenses this model as the "gallery classifier": labelled example
photos are embedded once (tools/build_gallery.py -> data/gallery.npz) and a
query is matched by cosine similarity per dish (top-3 mean of the dish's
gallery embeddings).  Leave-one-out on the 46 source photos: 1.000 accuracy;
text-only zero-shot tops out around 0.6 on the same set, so text is used
only when no gallery exists (cold start) or a dish has no gallery entries.

Open-set: a query whose best dish score is below
`gallery_match_threshold` (data/params_status.yaml, status assumed) returns
dish=None — synthetic renders score ~0.67 vs >=0.857 for real gallery matches.

Model: google/siglip2-base-patch16-224 (Apache-2.0, docs/licenses.md).
Weights download on first use (run with HF_HUB_DISABLE_XET=1 — the xet
backend stalls in this environment).
"""
import glob
import os

import cv2
import numpy as np

from config import (GALLERY_PATH, load_gallery as _load_gallery, load_menu,
                    load_params, reset_caches)

MODEL_ID = "google/siglip2-base-patch16-224"
TOP_K = 3

_STATE = {}


# --- menu helpers (dish truth lives in data/menu.yaml only) -----------------

def _menu():
    return load_menu()["dishes"]


def menu_dish_keys():
    return [k for k, v in _menu().items() if v.get("status") != "out_of_scope"]


def menu_aliases(key):
    return list(_menu()[key].get("aliases", []))


def _text_prompt(key):
    v = _menu()[key]
    prompts = [f"a photo of {v['display_name'].lower()}",
               f"a plate of {v['display_name'].lower()}"]
    if v.get("aliases"):
        prompts.append("a photo of " + ", ".join(a.replace("_", " ") for a in v["aliases"]))
    return prompts


def gallery_match_threshold():
    return float(load_params()["gallery_match_threshold"]["value"])


# --- model ------------------------------------------------------------------

def _device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load():
    if _STATE:
        return _STATE["proc"], _STATE["model"], _STATE["device"]
    import torch
    from transformers import AutoModel, AutoProcessor
    dev = _device()
    proc = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID).to(dev).eval()
    _STATE.update(proc=proc, model=model, device=dev)
    return proc, model, dev


def _pool(o):
    return o.pooler_output if hasattr(o, "pooler_output") else o


def embed_image(image_bgr):
    """-> L2-normalised embedding (D,) for an RGB-converted BGR image."""
    import torch
    proc, model, dev = _load()
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    inputs = proc(images=rgb, return_tensors="pt").to(dev)
    with torch.no_grad():
        e = _pool(model.get_image_features(**inputs))
    e = (e / e.norm(dim=-1, keepdim=True))[0]
    return e.cpu().numpy().astype(np.float32)


def _embed_texts(prompts):
    proc, model, dev = _load()
    inputs = proc(text=prompts, padding="max_length", truncation=True,
                  return_tensors="pt").to(dev)
    with torch.no_grad():
        t = _pool(model.get_text_features(**inputs))
    return (t / t.norm(dim=-1, keepdim=True)).cpu().numpy().astype(np.float32)


# --- gallery ----------------------------------------------------------------

def build_gallery(entries):
    """entries: [(image_bgr or path, dish_key)] -> gallery dict."""
    embs, labels, sources = [], [], []
    for img, dish in entries:
        if dish not in menu_dish_keys():
            raise ValueError(f"dish {dish!r} not in menu.yaml")
        if isinstance(img, str):
            bgr = cv2.imread(img)
            if bgr is None:
                raise FileNotFoundError("gallery image failed to decode")
            src = img
        else:
            bgr, src = img, "<memory>"
        embs.append(embed_image(bgr))
        labels.append(dish)
        sources.append(src)
    return {
        "emb": np.stack(embs).astype(np.float32),
        "labels": np.array(labels, dtype=str),
        "sources": np.array(sources, dtype=str),
        "model": MODEL_ID,
    }


def save_gallery(gallery, path=GALLERY_PATH):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    np.savez_compressed(path, **gallery)
    reset_caches()  # in-process readers must see the file just written


def load_gallery(path=None):
    gallery = _load_gallery(path)
    if str(gallery["model"]) != MODEL_ID:
        raise ValueError(f"gallery built with {gallery['model']}, expected {MODEL_ID}")
    return gallery


# --- classification ---------------------------------------------------------

def _gallery_scores(emb, gallery):
    E = gallery["emb"]
    labels = gallery["labels"]
    sims = E @ emb                          # (N,)
    out = {}
    for k in menu_dish_keys():
        vals = sims[labels == k]
        if vals.size == 0:
            out[k] = None
        else:
            kk = min(TOP_K, vals.size)
            out[k] = float(np.sort(vals)[-kk:].mean())
    return out


def _text_scores(image_bgr):
    import torch
    proc, model, dev = _load()
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    LS = float(model.logit_scale.exp().detach())
    LB = float(model.logit_bias.detach())
    scores = {}
    for k in menu_dish_keys():
        inputs = proc(text=_text_prompt(k), images=rgb, padding="max_length",
                      truncation=True, return_tensors="pt").to(dev)
        with torch.no_grad():
            out = model(**inputs)
        p = torch.sigmoid(out.logits_per_image[0]).float().cpu().numpy()
        scores[k] = float(p.mean())
    return scores


def classify_dish(image_bgr, gallery=None, threshold=None):
    """Classify one capture.

    gallery: dict from build_gallery/load_gallery, or None to use
    data/gallery.npz when present.  threshold: overrides
    params_status gallery_match_threshold.

    Returns dict:
      dish       menu dish key or None (no confident match)
      confidence float in [0,1] — gallery: softmax(scores, tau=0.05) top-1;
                                   text: top sigmoid probability
      scores     {dish: float|None} in the method's own units
      method     "gallery" | "text"
      match_score, margin (gallery only)
      uncovered  dishes with no gallery entries (gallery only)
      reason     human-readable explanation
    """
    if gallery is None and os.path.exists(GALLERY_PATH):
        gallery = load_gallery()

    if gallery is None or len(gallery["labels"]) == 0:
        scores = _text_scores(image_bgr)
        best = max(scores, key=scores.get)
        return {"dish": best, "confidence": scores[best], "scores": scores,
                "method": "text", "match_score": None, "margin": None,
                "uncovered": [], "reason": "text zero-shot (no gallery)"}

    emb = embed_image(image_bgr)
    scores = _gallery_scores(emb, gallery)
    covered = {k: v for k, v in scores.items() if v is not None}
    uncovered = sorted(set(scores) - set(covered))
    if not covered:
        raise RuntimeError("gallery has no entries for any menu dish")
    best = max(covered, key=covered.get)
    ordered = sorted(covered.values(), reverse=True)
    match = covered[best]
    margin = float(ordered[0] - ordered[1]) if len(ordered) > 1 else None
    tau = 0.05
    exp = {k: float(np.exp((v - match) / tau)) for k, v in covered.items()}
    confidence = float(exp[best] / sum(exp.values()))
    thr = gallery_match_threshold() if threshold is None else threshold
    if match < thr:
        return {"dish": None, "confidence": confidence, "scores": scores,
                "method": "gallery", "match_score": float(match),
                "margin": margin, "uncovered": uncovered,
                "reason": f"best gallery match {best}={match:.3f} < {thr:.2f}"}
    return {"dish": best, "confidence": confidence, "scores": scores,
            "method": "gallery", "match_score": float(match),
            "margin": margin, "uncovered": uncovered,
            "reason": f"gallery match {best}={match:.3f} >= {thr:.2f}"}
