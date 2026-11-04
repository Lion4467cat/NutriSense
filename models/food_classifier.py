"""SigLIP2 dish classifier (S2) — gallery-first, text zero-shot fallback.

The plan licenses this model as the "gallery classifier": labelled example
photos are embedded once (tools/build_gallery.py -> data/gallery.npz) and a
query is matched by cosine similarity per dish (top-3 mean of the dish's
gallery embeddings).  The original 2-class gold gallery scored LOO 46/46;
since spec 002 (ledger 003) the gallery covers all 41 WED classes from WED
train ROI crops plus the gold photos, and `data/gallery.npz`'s LOO run sets
`gallery_match_threshold` (params_status.yaml, calibrated).

Open-set: a query whose best dish score is below
`gallery_match_threshold` returns dish=None (unrecognized/abstain);

Recognition returns SERVING keys: menu dish keys (data/menu.yaml) and
off-menu serving keys (data/wed_dishes.yaml `off_menu:`, routed through
`serving:`), so a recognized-but-not-on-menu dish flows to the pipeline's
off-menu path (cannot_verify + off_menu_dish; ledger 003) while menu dishes
keep their exact current verdict path.

Model: google/siglip2-base-patch16-224 (Apache-2.0, docs/licenses.md).
Weights download on first use (run with HF_HUB_DISABLE_XET=1 — the xet
backend stalls in this environment).
"""
import os

import cv2
import numpy as np

from config import (GALLERY_PATH, load_gallery as _load_gallery, load_menu,
                    load_params, load_wed_dishes, load_wed_index,
                    reset_caches)
from models.model_revisions import SIGLIP2_REVISION

MODEL_ID = "google/siglip2-base-patch16-224"
TOP_K = 3


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


# --- serving helpers (spec 002, ledger 003) ----------------------------------

def serving_targets():
    """Recognition-space label -> serving key (menu dish key | off-menu key).

    Labels are menu ids/aliases or WED class names (gallery entries from
    data/wed train crops). An unknown WED-label or a target with no entry
    both raise ValueError — config drift must fail loudly, not silently
    drop dishes."""
    targets = {k: k for k, v in _menu().items()
               if v.get("status") != "out_of_scope"}
    menu_all = set(_menu())
    wed = load_wed_dishes()
    off_menu = set(wed.get("off_menu") or {})
    unknown = sorted(set(wed.get("serving") or {}) - set(load_wed_index()))
    if unknown:
        raise ValueError(f"serving map has non-WED labels: {unknown}")
    this = wed.get("serving") or {}
    for cls, entry in this.items():
        target = entry["dish"]
        if target not in menu_all and target not in off_menu:
            raise ValueError(f"serving target {target!r} ({cls}) has no dish entry")
        targets[cls] = target
    return targets


def serving_dish_keys():
    """Every servable dish key: menu dishes (in-scope) + off-menu entries.
    At least one menu key always exists, so this is never empty."""
    targets = serving_targets()
    return sorted(set(targets.values()) | set(menu_dish_keys()))


def _text_prompt_off_menu(key):
    v = (load_wed_dishes().get("off_menu") or {})[key]
    d = v["display_name"].lower()
    return [f"a photo of {d}", f"a plate of {d}"]


def gallery_match_threshold():
    return float(load_params()["gallery_match_threshold"]["value"])


# --- model ------------------------------------------------------------------

def _device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _make_state():
    from transformers import AutoModel, AutoProcessor
    dev = _device()
    proc = AutoProcessor.from_pretrained(MODEL_ID, revision=SIGLIP2_REVISION)
    model = AutoModel.from_pretrained(
        MODEL_ID, revision=SIGLIP2_REVISION).to(dev).eval()
    return {"proc": proc, "model": model, "device": dev}


def _load():
    from models import registry
    s = registry.get_or_create("siglip2", _make_state)
    return s["proc"], s["model"], s["device"]


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



# --- gallery ----------------------------------------------------------------

def build_gallery(entries):
    """entries: [(image, label)] or [(image, label, source_override)]
    -> gallery dict.  image may be a path str, a numpy BGR frame, or (for
    WED crops) a 3-tuple carrying its own source string.

    labels are recognition-space: menu dish keys (data/menu.yaml, gold
    photos) or WED class names (data/wed train crops — spec 002, ledger
    003). Anything else is rejected so config drift fails loudly."""
    allowed = set(serving_targets())
    embs, labels, sources = [], [], []
    for entry in entries:
        img, lab = entry[0], entry[1]
        src_override = entry[2] if len(entry) == 3 else None
        if lab not in allowed:
            raise ValueError(f"label {lab!r} is not a serving/WED-class label")
        if isinstance(img, str):
            bgr = cv2.imread(img)
            if bgr is None:
                raise FileNotFoundError("gallery image failed to decode")
            src = img
        else:
            bgr, src = img, "<memory>"
        if src_override:
            src = src_override
        embs.append(embed_image(bgr))
        labels.append(lab)
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

def _align_gallery_domains(gallery):
    """Neutralize sensor/lighting domain shift between phone prototypes and WED studio crops."""
    if "_aligned_emb" in gallery:
        return gallery["_aligned_emb"], gallery.get("_delta_domain")
    E = np.asarray(gallery["emb"], dtype=np.float32).copy()
    sources = [str(s) for s in gallery.get("sources", [])]
    is_phone = np.array([s.startswith("..") or "dataset" in s.lower() for s in sources])
    if is_phone.any() and (~is_phone).any():
        mu_phone = E[is_phone].mean(axis=0)
        mu_wed = E[~is_phone].mean(axis=0)
        delta = mu_phone - mu_wed
        E[is_phone] -= delta
        norms = np.linalg.norm(E, axis=-1, keepdims=True)
        E = np.divide(E, np.maximum(norms, 1e-12))
        gallery["_aligned_emb"] = E
        gallery["_delta_domain"] = delta
        return E, delta
    return gallery["emb"], None


def _gallery_scores(emb, gallery) -> dict[str, float | None]:
    """top-3-mean cosine per gallery label (unchanged match metric), then
    aggregated to serving targets — a menu key keeps its own score, a WED
    crop label scores under its serving target (spec 002, ledger 003).
    Serving keys without entries carry None (uncovered)."""
    E, delta = _align_gallery_domains(gallery)
    labels = gallery["labels"]
    emb_aligned = emb
    if delta is not None:
        delta_norm = float(np.linalg.norm(delta))
        if delta_norm > 1e-6:
            delta_u = delta / delta_norm
            comp = float(emb @ delta_u)
            if comp > 0.05:
                emb_aligned = emb - comp * delta_u
                norm = float(np.linalg.norm(emb_aligned))
                if norm > 1e-6:
                    emb_aligned = emb_aligned / norm
    sims = E @ emb_aligned                          # (N,)
    targets = serving_targets()
    per_label: dict[str, list[int]] = {}
    for i, lab in enumerate(labels):
        lab = str(lab)
        if lab in targets:
            per_label.setdefault(lab, []).append(i)
    out: dict[str, float | None] = {}
    for lab, idxs in per_label.items():
        vals = sims[idxs]
        kk = min(TOP_K, len(vals))
        score = float(np.sort(vals)[-kk:].mean())
        key = targets[lab]
        cur = out.get(key)
        if cur is None or score > cur:
            out[key] = score
    for k in serving_dish_keys():
        out.setdefault(k, None)
    return out


def _text_scores(image_bgr) -> dict[str, float]:
    import torch
    proc, model, dev = _load()
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    scores = {}
    for k in serving_dish_keys():
        prompts = (_text_prompt(k) if k in _menu()
                   else _text_prompt_off_menu(k))
        inputs = proc(text=prompts, images=rgb, padding="max_length",
                      truncation=True, return_tensors="pt").to(dev)
        with torch.no_grad():
            out = model(**inputs)
        p = torch.sigmoid(out.logits_per_image[0]).float().cpu().numpy()
        scores[k] = float(p.mean())
    return scores


DECOY_SIDE_CLASSES: frozenset[str] = frozenset({
    "chutney", "curd", "raita", "papad", "salad", "mango-pickle", "boondi"
})
PRIMARY_MEAL_DISHES: frozenset[str] = frozenset({
    "rice_sambar", "steamed-rice", "vegetable_rice", "bisibelebath",
    "wheat_product", "veg-dum-briyani", "chicken-dum-biryani", "khichdi"
})


def classify_dish(image_bgr, gallery=None, threshold=None):
    """Classify one capture.

    gallery: dict from build_gallery/load_gallery, or None to use
    data/gallery.npz when present.  threshold: overrides
    params_status gallery_match_threshold.

    Returns dict:
      dish       serving key (menu dish key or off-menu serving key) or
                 None (no confident match)
      confidence float in [0,1] — gallery: softmax(scores, tau=0.05) top-1;
                                   text: top sigmoid probability
      scores     {serving key: float|None} in the method's own units
      method     "gallery" | "text"
      match_score float|None — gallery: best top-3-mean cosine score;
                               text: None
      margin     float|None — gap between the two best gallery scores;
                               text: None
      uncovered  serving keys with no gallery entries (gallery only)
      reason     human-readable explanation
    """
    if gallery is None and os.path.exists(GALLERY_PATH):
        gallery = load_gallery()

    if gallery is None or len(gallery["labels"]) == 0:
        scores = _text_scores(image_bgr)
        best = max(scores, key=lambda key: scores[key])
        return {"dish": best, "confidence": scores[best], "scores": scores,
                "method": "text", "match_score": None, "margin": None,
                "uncovered": [], "reason": "text zero-shot (no gallery)"}

    emb = embed_image(image_bgr)
    scores = _gallery_scores(emb, gallery)
    covered: dict[str, float] = {
        key: float(value) for key, value in scores.items() if value is not None
    }
    uncovered = sorted(set(scores) - set(covered))
    if not covered:
        raise RuntimeError("gallery has no entries for any serving key")

    # Domain saturation check on core bright pixels (plain white rice vs spiced vegetable rice)
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    bright = (hsv[:, :, 2] > 110) & (image_bgr.mean(axis=2) > 90)
    s_mean = float(np.mean(hsv[bright, 1])) if bright.any() else 100.0
    if s_mean < 50.0 and "vegetable_rice" in covered:
        covered["vegetable_rice"] -= 0.05
        scores["vegetable_rice"] = covered["vegetable_rice"]

    best = max(covered, key=lambda key: covered[key])
    ordered = sorted(covered.values(), reverse=True)
    match = covered[best]
    margin = float(ordered[0] - ordered[1]) if len(ordered) > 1 else None

    # Full-frame decoy prevention: do not label an entire meal as a condiment / decoy
    # if a main dish candidate is within 0.05
    if best in DECOY_SIDE_CLASSES and (match < 0.82 or (margin is not None and margin < 0.035)):
        non_decoys = {k: v for k, v in covered.items() if k not in DECOY_SIDE_CLASSES}
        if non_decoys:
            alt_best = max(non_decoys, key=lambda k: non_decoys[k])
            if covered[alt_best] >= match - 0.05:
                best = alt_best
                match = covered[best]

    # Meal base priority: full meal captures are anchored by a primary grain/meal dish
    # (rice_sambar, steamed-rice, wheat_product, biryani). A minor dry fry, condiment,
    # or dessert should not displace a primary meal dish that is within 0.035.
    if best not in PRIMARY_MEAL_DISHES:
        meal_cands = {k: v for k, v in covered.items() if k in PRIMARY_MEAL_DISHES}
        if meal_cands:
            best_meal = max(meal_cands, key=lambda k: meal_cands[k])
            if covered[best_meal] >= match - 0.035:
                best = best_meal
                match = covered[best]

    ordered_alt = sorted([v for k, v in covered.items() if k != best], reverse=True)
    margin = float(match - ordered_alt[0]) if ordered_alt else None

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
