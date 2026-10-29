"""Ingredient-conditional head — serving loader for the 07b/07e teacher.

Loads `data/ingredient_head.pt` (saved by `tools/train_ingredient_head.py`:
head-only state dict + the slot name list + encoder/seed it was trained
with) and predicts per-ingredient grams from a full overhead frame.

The serving recipe matches the trainer exactly: full-frame ROI over the
frozen encoder's 16x16 (DINOv2) / 8x8 (ResNet-50) feature grid at 224x224,
ImageNet-normalised RGB, output clamped at 0 (`sqrt(grams)` regression ->
grams = pred^2). Unlike `WeightHead.predict`, the ROI is the whole frame:
Nutrition5k supervision was per-plate with the food filling the frame, and
the general-mode route (engine/general_mode.py) keys composition off the
per-ingredient profile, not one segmented blob.

Checkpoint absent -> load() raises FileNotFoundError and every caller
falls back to the pre-07e behaviour (engine handles the None case); a
checkpoint that loads but fails at predict time raises a plain exception
for the caller to convert.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

CKPT_PATH = Path("data") / "ingredient_head.pt"

# Same normalisation the trainer applies to every encoder choice (100-255
# scaled RGB, ImageNet stats; the head was trained on this exact domain).
_MEAN = [0.485, 0.456, 0.406]
_STD = [0.229, 0.224, 0.225]
RESIZE = (224, 224)


class IngredientHead:
    """Thin serving wrapper: `predict` -> {ingredient_name: grams}."""

    def __init__(self, head, slots: list[str], encoder: str, seed: int,
                 meta: dict | None = None):
        self.head = head          # models.weight_head.WeightHead (head-only)
        self.slots = list(slots)
        self.encoder = encoder
        self.seed = seed
        self.meta = meta or {}

    @classmethod
    def load(cls, path: str | Path = CKPT_PATH,
             device: str = "cpu") -> "IngredientHead":
        """Absent checkpoint -> FileNotFoundError (callers disable the route)."""
        from models.weight_head import WeightHead
        ckpt = WeightHead.load(path, device=device)
        slots = ckpt.meta.get("slots")
        if not slots:
            raise ValueError(f"{path}: checkpoint has no slot list")
        return cls(ckpt, slots, str(ckpt.meta.get("encoder", "dinov2")),
                   int(ckpt.meta.get("seed", 0)), ckpt.meta)

    @property
    def device(self):
        return self.head.device

    def predict(self, image_bgr: np.ndarray) -> dict[str, float]:
        """{slot_name: grams} for one frame; full-frame ROI (build_eval rule:
        clamp min 0 then square, i.e. sqrt-target regression inverted)."""
        import torch
        from PIL import Image
        from torchvision import transforms

        device = self.device
        rgb = Image.fromarray(np.ascontiguousarray(image_bgr[:, :, ::-1]))
        tf = transforms.Compose([
            transforms.Resize(RESIZE),
            transforms.ToTensor(),
            transforms.Normalize(_MEAN, _STD),
        ])
        img_t = tf(rgb).unsqueeze(0).to(device)
        with torch.no_grad():
            feats = self.head.encode(img_t)
            fh, fw = feats.shape[2:]
            roi = torch.tensor([[0.0, 0.0, 0.0, float(fw), float(fh)]],
                               dtype=torch.float32, device=device)
            preds = self.head.forward(feats, roi)[0]
        grams = torch.clamp(preds, min=0) ** 2
        return {name: float(grams[i].item())
                for i, name in enumerate(self.slots)}
