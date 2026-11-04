"""Local-only ControlNet diffusion adapter with renderer-owned labels."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image

from nutrisense_synth.methods.base import (GenerationContext, restore_scene_owned_pixels,
                                           validate_semantic_mask)


class DiffusionMethod:
    name = "diffusion"

    def __init__(self, model_dir: Path, revision: str, device: str = "cuda"):
        if not model_dir.is_dir():
            raise FileNotFoundError(f"Local diffusion model directory not found: {model_dir}")
        provenance_path = model_dir / "PROVENANCE.json"
        if not provenance_path.is_file():
            raise ValueError("Diffusion model requires local PROVENANCE.json; remote loading is disabled")
        self.provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        for field in ("license", "training_data_disclosure", "base_revision",
                      "control_revision", "model_tree_sha256"):
            if not self.provenance.get(field):
                raise ValueError(f"Diffusion provenance must include {field}")
        self.promotable = bool(self.provenance.get("wed_overlap_reviewed", False))
        try:
            import torch
            from diffusers import ControlNetModel, StableDiffusionControlNetPipeline
        except ImportError as exc:
            raise RuntimeError("Install the reviewed diffusers runtime on the approved GPU host") from exc
        self.revision = revision
        local = str(model_dir)
        control_path = model_dir / "controlnet"
        base_path = model_dir / "base"
        if not control_path.is_dir() or not base_path.is_dir():
            raise ValueError("Expected local model_dir/base and model_dir/controlnet folders")
        expected_hash = self.provenance["model_tree_sha256"]
        digest = hashlib.sha256()
        for file in sorted(path for path in model_dir.rglob("*") if path.is_file()
                           and path.name != "PROVENANCE.json"):
            digest.update(file.relative_to(model_dir).as_posix().encode())
            with file.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
        self.checkpoint_sha256 = digest.hexdigest()
        if self.checkpoint_sha256 != expected_hash:
            raise ValueError("Diffusion checkpoint tree SHA-256 does not match provenance")
        control = ControlNetModel.from_pretrained(str(control_path), local_files_only=True)
        self.pipeline = StableDiffusionControlNetPipeline.from_pretrained(
            str(base_path), controlnet=control, local_files_only=True,
            safety_checker=None, requires_safety_checker=False,
        )
        self.device = device if device == "cpu" or torch.cuda.is_available() else "cpu"
        self.pipeline.to(self.device)

    def generate(self, context: GenerationContext) -> np.ndarray:
        import torch
        labels = validate_semantic_mask(context.semantic_mask)
        mask = (labels.astype(np.float32) / 41.0 * 255.0).astype(np.uint8)
        depth = np.asarray(context.depth_m, dtype=np.float32)
        finite = depth[np.isfinite(depth)]
        if finite.size == 0:
            raise ValueError("Renderer depth condition contains no finite pixels")
        low, high = np.percentile(finite, [1, 99])
        depth8 = (np.clip((depth - low) / max(float(high - low), 1e-6), 0, 1) * 255).astype(np.uint8)
        control = np.stack([mask, depth8, np.zeros_like(mask)], axis=-1)
        height, width = context.condition_rgb.shape[:2]
        generator = torch.Generator(device=self.device).manual_seed(context.seed)
        result = self.pipeline(
            prompt=str(context.metadata.get("class_name", "food")),
            image=Image.fromarray(control), height=height, width=width,
            generator=generator,
        ).images[0]
        return restore_scene_owned_pixels(np.asarray(result.convert("RGB")), context)
