"""Learned weight head — port of FusionWeightNet_ROI_Conditional_Heavy
(baseline config: ResNet-50, RGB only, no attention, no geom features).

Architecture source: Arora et al., "What is there in an Indian Thali?",
ICVGIP 2025 (MIT) — weight_estimation/train.py in their repository. The
published baseline (14.51 g MAE on WED) is: frozen ImageNet-V2 ResNet-50
feature map -> ROI-align 7x7 per dish bbox -> global average pool ->
MLP(2048 -> 512 -> num_classes). The head is class-conditional: it emits
one gram value per WED class per ROI; the dish identity selects the slot.

Backbone weights come from torchvision at load time (not stored in the
checkpoint); the checkpoint holds only the trained MLP head (~4 MB).

Inference (production, no reference card):
    head = WeightHead.load("data/weight_head.pt")
    out  = head.predict(image_bgr, mask, slot_ids=[...])   # slots from
           data/wed_dishes.yaml -> grams (summed across composite slots)

Training: tools/train_weight_head.py (data/wed_manifest.jsonl).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torchvision import models
from torchvision.ops import roi_align

WED_NUM_CLASSES = 41          # index_map.json minus background
RESIZE = (224, 224)
ROI_RES = 7


class WeightHead(nn.Module):
    """Frozen ResNet-50 encoder + ROI-aligned class-conditional gram head."""

    def __init__(self, num_classes: int = WED_NUM_CLASSES,
                 roi_res: int = ROI_RES, pretrained: bool = True):
        super().__init__()
        backbone = models.resnet50(
            weights=models.ResNet50_Weights.IMAGENET1K_V2 if pretrained else None)
        self.encoder = nn.Sequential(*list(backbone.children())[:-2])
        for p in self.encoder.parameters():
            p.requires_grad = False
        self.roi_res = roi_res
        self.num_classes = num_classes
        feat_c = 2048
        self.head_mlp = nn.Sequential(
            nn.Linear(feat_c, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.1),
            nn.Linear(512, num_classes),
        )

    def forward(self, feats: torch.Tensor, rois: torch.Tensor) -> torch.Tensor:
        """feats: (B, 2048, h, w) encoder map; rois: (K, 5) = [b, x1, y1, x2, y2]
        in feature-map coordinates. Returns (K, num_classes)."""
        r = roi_align(feats, rois, output_size=(self.roi_res, self.roi_res))
        r = torch.nn.functional.adaptive_avg_pool2d(r, 1).view(r.size(0), -1)
        return self.head_mlp(r)

    def encode(self, images: torch.Tensor) -> torch.Tensor:
        """images: (B, 3, H, W) ImageNet-normalised RGB in [0,1]. Frozen encoder."""
        with torch.no_grad():
            return self.encoder(images)

    @property
    def device(self) -> torch.device:
        return next(self.head_mlp.parameters()).device

    # --- checkpoint I/O (head-only; backbone rebuilt from torchvision) ----
    def save(self, path: str | Path, meta: dict | None = None) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"head_mlp": self.head_mlp.state_dict(),
                    "num_classes": self.num_classes,
                    "roi_res": self.roi_res,
                    "meta": meta or {}}, path)

    @classmethod
    def load(cls, path: str | Path, device: str | torch.device = "cpu") -> "WeightHead":
        """Rebuild the frozen backbone from torchvision (IMAGENET1K_V2) and
        swap in the trained head. The checkpoint stores the head only, so the
        encoder MUST be the same pretrained weights training used — a random
        encoder feeds untrained features to the head and yields kilogram-scale
        garbage predictions."""
        ckpt = torch.load(Path(path), map_location=device, weights_only=True)
        model = cls(num_classes=ckpt.get("num_classes", WED_NUM_CLASSES),
                    roi_res=ckpt.get("roi_res", ROI_RES), pretrained=True)
        model.head_mlp.load_state_dict(ckpt["head_mlp"])
        model.to(device).eval()
        model.meta = ckpt.get("meta", {})
        return model

    # --- production inference --------------------------------------------
    @staticmethod
    def _bbox_px(mask: np.ndarray) -> tuple[int, int, int, int] | None:
        vs, us = np.nonzero(mask)
        if vs.size == 0:
            return None
        return int(us.min()), int(vs.min()), int(us.max()), int(vs.max())

    @torch.no_grad()
    def predict(self, image_bgr: np.ndarray, mask: np.ndarray,
                slot_ids: list[int], device: str | torch.device | None = None) -> dict:
        """Estimate grams for one food region.

        image_bgr: full image; mask: bool (H, W) food region; slot_ids: WED
        class indices (0-based, index_map id - 1) whose values sum to the
        dish grams (composite dishes read two slots). Returns dict with
        per-slot grams and the summed point estimate.
        """
        from PIL import Image
        from torchvision import transforms

        box = self._bbox_px(np.asarray(mask, dtype=bool))
        if box is None:
            raise ValueError("empty mask")
        device = device if device is not None else self.device
        x1, y1, x2, y2 = box
        rgb = Image.fromarray(image_bgr[:, :, ::-1])  # BGR -> RGB
        tf = transforms.Compose([
            transforms.Resize(RESIZE),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406],
                                 [0.229, 0.224, 0.225]),
        ])
        img_t = tf(rgb).unsqueeze(0).to(device)
        H, W = image_bgr.shape[:2]
        feats = self.encode(img_t)
        fh, fw = feats.shape[2:]
        roi = torch.tensor([[0.0, x1 / W * fw, y1 / H * fh,
                             x2 / W * fw, y2 / H * fh]],
                           dtype=torch.float32, device=device)
        preds = self.forward(feats, roi)[0]  # (num_classes,)
        slots = [int(s) for s in slot_ids]
        values = {s: float(preds[s].clamp(min=0).item()) for s in slots}
        return {"grams": float(sum(values.values())),
                "slots": values,
                "slots_clamped": any(preds[s] < 0 for s in slots)}
