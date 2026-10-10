"""Monocular metric depth provider (S3 depth source for real captures).

MoGe-2 (microsoft/MoGe, MIT weights) returns metric camera-z depth in meters.
Synthetic captures bypass this module and pass the renderer's GT depth.

Known gotchas:
  - image must be RGB float (3,H,W) in [0,1] (BGR input is converted here)
  - apply_mask=False: MoGe's predicted object mask would blank the table
  - weights: HF_HUB_DISABLE_XET=1 env needed in this environment (xet stalls)
"""
import numpy as np

MODEL_ID = "Ruicheng/moge-2-vitl"


def calibrate_depth_scale(depth_m, anchor, K):
    """Rescale monocular depth so a known anchor object matches its true size.

    Unprojects anchor pixels with the raw depth (global scale error k scales
    every 3D distance by the same k), measures card-marker edges (60 mm), and
    returns depth * factor.

    Returns (depth_calibrated, factor, source). Prior tier: (depth, 1.0, "none").
    """
    depth = np.asarray(depth_m, dtype=np.float64)
    method = anchor.get("method", "prior")
    extras = anchor.get("extras") or {}
    K = np.asarray(K, dtype=np.float64)
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]

    def _pt(u, v):
        u0, v0 = int(round(u)), int(round(v))
        win = depth[max(0, v0 - 2):v0 + 3, max(0, u0 - 2):u0 + 3]
        z = float(np.median(win))
        return np.array([(u - cx) / fx * z, (v - cy) / fy * z, z])

    ests, trues, source = [], [], "none"
    if method == "card_aruco" and extras.get("marker_corners_px"):
        c = np.asarray(extras["marker_corners_px"], dtype=np.float64)
        L = float(anchor.get("_marker_mm", 60.0)) / 1000.0  # meters
        pts = [_pt(u, v) for u, v in c]
        for i in range(4):
            ests.append(float(np.linalg.norm(pts[i] - pts[(i + 1) % 4])))
            trues.append(L)
        source = "card"

    if not ests or any(not np.isfinite(e) or e <= 0 for e in ests):
        return depth, 1.0, "none"
    factor = float(np.median([t / e for t, e in zip(trues, ests)]))
    if not np.isfinite(factor) or not (0.05 < factor < 20.0):
        return depth, 1.0, "none"
    return depth * factor, factor, source


class MonocularDepth:
    """Lazy-loaded MoGe-2 metric depth. Call like a function on a BGR image."""

    def __init__(self, model_id=MODEL_ID, device=None, resolution_level=9):
        self.model_id = model_id
        self.device = device
        self.resolution_level = resolution_level
        self._model = None

    def _load(self):
        if self._model is None:
            import torch
            from moge.model.v2 import MoGeModel

            device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
            model = MoGeModel.from_pretrained(self.model_id)
            self._model = model.to(device).eval()
        return self._model

    def __call__(self, image_bgr, fov_x=None):
        import torch

        model = self._load()
        rgb = image_bgr[..., ::-1]
        tensor = torch.from_numpy(np.ascontiguousarray(rgb, dtype=np.float32) / 255.0)
        tensor = tensor.permute(2, 0, 1).to(next(model.parameters()).device)
        with torch.inference_mode():
            out = model.infer(tensor, apply_mask=False,
                              resolution_level=self.resolution_level, fov_x=fov_x)
        depth = out["depth"]
        if isinstance(depth, torch.Tensor):
            depth = depth.float().cpu().numpy()
        depth = np.asarray(depth, dtype=np.float32)
        finite = np.isfinite(depth) & (depth > 0)
        if finite.mean() < 0.5:
            raise ValueError("monocular depth mostly invalid")
        depth[~finite] = np.median(depth[finite])
        return {
            "depth_m": depth,
            "model": self.model_id,
            "relative": False,
            "intrinsics": None if "intrinsics" not in out else out["intrinsics"],
        }
