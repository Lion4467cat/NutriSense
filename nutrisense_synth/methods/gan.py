"""Local adapter for a mass-conditioned semantic GAN checkpoint."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from nutrisense_synth.methods.base import (GenerationContext, restore_scene_owned_pixels,
                                           validate_semantic_mask)
from nutrisense_synth.methods.gan_training import (CONDITION_CHANNELS,
                                                    SemanticGenerator,
                                                    build_condition)


class GANMethod:
    name = "gan"

    def __init__(self, checkpoint: Path, revision: str, device: str = "cuda"):
        import torch
        if not checkpoint.is_file():
            raise FileNotFoundError(f"Local GAN checkpoint not found: {checkpoint}")
        self.checkpoint_sha256 = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        provenance_path = checkpoint.with_suffix(checkpoint.suffix + ".provenance.json")
        if not provenance_path.is_file():
            raise ValueError(f"GAN checkpoint provenance sidecar required: {provenance_path}")
        self.provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        if self.provenance.get("sha256") != self.checkpoint_sha256:
            raise ValueError("GAN checkpoint provenance SHA-256 does not match its weights")
        if not self.provenance.get("license") or not self.provenance.get("training_data_disclosure"):
            raise ValueError("GAN provenance must state license and training data")
        if set(self.provenance.get("training_source_splits", [])) != {"train"}:
            raise ValueError("GAN training source splits must contain WED TRAIN only")
        self.revision = revision
        self.promotable = True
        self.device = torch.device(device if device == "cpu" or torch.cuda.is_available() else "cpu")
        payload = torch.load(checkpoint, map_location=self.device, weights_only=True)
        if payload.get("architecture") != "semantic_unet_83ch_mass_conditioned_v2":
            raise ValueError("Unsupported GAN checkpoint architecture")
        if payload.get("condition_channels") != CONDITION_CHANNELS:
            raise ValueError("GAN checkpoint condition channels do not match the adapter")
        self.model = SemanticGenerator(condition_channels=CONDITION_CHANNELS).to(self.device)
        self.model.load_state_dict(payload["generator_state_dict"], strict=True)
        self.model.eval()

    def generate(self, context: GenerationContext) -> np.ndarray:
        import torch
        mask = validate_semantic_mask(context.semantic_mask)
        mass_by_class = {
            int(class_id): float(grams)
            for class_id, grams in context.metadata.get("mass_by_class_g", {}).items()
        }
        condition = build_condition(mask, mass_by_class)
        tensor = torch.from_numpy(condition.transpose(2, 0, 1)[None]).to(self.device)
        dev_idx = self.device.index if self.device.index is not None else (torch.cuda.current_device() if torch.cuda.is_available() else 0)
        with torch.random.fork_rng(devices=[dev_idx] if self.device.type == "cuda" else []):
            torch.manual_seed(context.seed)
            with torch.inference_mode():
                output = self.model(tensor)
        image = output[0].detach().float().cpu().numpy().transpose(1, 2, 0)
        image = np.clip((image + 1.0) * 127.5, 0, 255).astype(np.uint8)
        return restore_scene_owned_pixels(image, context)
