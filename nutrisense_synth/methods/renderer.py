"""Deterministic analytic renderer method."""
from __future__ import annotations

from nutrisense_synth.methods.base import GenerationContext
from nutrisense_synth.scene import render_scene


class RendererMethod:
    name = "renderer"
    revision = "analytic-heightfield-v1"

    def generate(self, context: GenerationContext):
        # For the renderer control, condition_rgb is the scene-owned render.
        return render_scene(context.metadata["scene_config"])["image_rgb"]
