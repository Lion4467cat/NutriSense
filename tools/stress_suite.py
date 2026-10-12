"""Frozen WED stress suite — five PIL-level perturbations, DEV images only.

A verbatim copy of the `STRESS` perturbations from tools/bn_experiment.py
(the STAGE 1B robustness study), kept as its own module so a later edit to
that experiment script can never silently change published stress numbers.
tests/test_locked_eval.py checks behavioural parity (same outputs on a fixed
probe image) and fails if the two copies drift — update both, deliberately.

Scope rule: only DEV tier images may be stressed. tools/run_eval.py rejects
`--stress` for any other tier, and every stress result is labelled
"WED stress test, not real-world" (these are corruptions of WED photos, not
measurements of canteen capture conditions).

Run through the evaluation CLI (never standalone):
  .venv/bin/python -m tools.run_eval --tier dev --stress
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from torchvision.transforms import functional as TF

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.train_weight_head import MASK_TF, RGB_TF, WedPlates, plate_key  # noqa: E402


class PerturbedWedPlates(WedPlates):
    """DEV views with a PIL-level perturbation; geometric ones hit mask too."""

    def __init__(self, rows, root, perturb):
        super().__init__(rows, root, train=False)
        self.perturb = perturb

    def __getitem__(self, idx: int) -> dict:
        r = self.rows[idx]
        img = Image.open(self.wed_root / r["image"]).convert("RGB")
        mask = Image.open(self.wed_root / r["mask"]).convert("L")
        img, mask = self.perturb(img, mask)
        img_t = RGB_TF(img)
        mask_arr = np.array(MASK_TF(mask).squeeze(0))
        H, W = img_t.shape[1:]
        bboxes, weights, cls_ids = [], [], []
        for d in r["dishes"]:
            cid = d["class_id"]
            vs, us = np.nonzero(mask_arr == cid)
            if vs.size == 0:
                continue
            bboxes.append([int(us.min()), int(vs.min()), int(us.max()), int(vs.max())])
            weights.append(float(d["weight_g"]))
            cls_ids.append(cid - 1)
        return {"img": img_t, "H": H, "W": W, "bboxes": bboxes,
                "weights": weights, "cls_ids": cls_ids,
                "key": plate_key(r)}


def _brightness_contrast(img, mask):
    return (TF.adjust_contrast(TF.adjust_brightness(img, 0.7), 0.7), mask)


def _blur(img, mask):
    return TF.gaussian_blur(img, kernel_size=[9, 9], sigma=[3.0, 3.0]), mask


def _perspective(img, mask):
    W, H = img.size
    # ~30 degree oblique tilt: top edge compressed, bottom flared
    start = [[0, 0], [W, 0], [W, H], [0, H]]
    end = [[W * 0.18, H * 0.12], [W * 0.82, 0], [W, H], [0, H * 0.92]]
    img = TF.perspective(img, start, end,
                         interpolation=TF.InterpolationMode.BILINEAR)
    mask = TF.perspective(mask, start, end,
                          interpolation=TF.InterpolationMode.NEAREST)
    return img, mask


def _jpeg30(img, mask):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=30)
    buf.seek(0)
    return Image.open(buf).convert("RGB"), mask


def _half_res(img, mask):
    W, H = img.size
    nw, nh = max(1, W // 2), max(1, H // 2)
    return (img.resize((nw, nh), Image.Resampling.BILINEAR),
            mask.resize((nw, nh), Image.Resampling.NEAREST))


PERTURBATIONS = {
    "brightness_contrast_0.7": _brightness_contrast,
    "gaussian_blur_k9": _blur,
    "perspective_30deg": _perspective,
    "jpeg_q30": _jpeg30,
    "half_resolution": _half_res,
}

STRESS_LABEL = "WED stress test, not real-world"
