from __future__ import annotations

import torch
import numpy as np
import pytest

from nutrisense_synth.methods.base import validate_semantic_mask
from nutrisense_synth.methods.gan_training import (CONDITION_CHANNELS,
                                                    SemanticGenerator,
                                                    build_condition)


def test_semantic_gan_generator_maps_condition_to_rgb_at_same_resolution() -> None:
    model = SemanticGenerator().eval()
    with torch.inference_mode():
        output = model(torch.zeros((1, CONDITION_CHANNELS, 64, 64)))
    clone = SemanticGenerator().eval()
    clone.load_state_dict(model.state_dict())
    with torch.inference_mode():
        cloned_output = clone(torch.zeros((1, CONDITION_CHANNELS, 64, 64)))
    assert output.shape == (1, 3, 64, 64)
    assert cloned_output.shape == output.shape
    assert float(output.min()) >= -1.0 and float(output.max()) <= 1.0


def test_mass_condition_is_encoded_per_class_and_is_deterministic() -> None:
    mask = np.array([[0, 1], [34, 41]], dtype=np.uint8)
    first = build_condition(mask, {1: 10.0, 34: 100.0})
    second = build_condition(mask, {1: 10.0, 34: 100.0})
    assert first.shape == (2, 2, CONDITION_CHANNELS)
    assert np.array_equal(first, second)
    assert first[0, 0, 42] > 0
    assert first[0, 0, 42 + 33] > first[0, 0, 42]


def test_unknown_semantic_class_is_rejected_not_remapped() -> None:
    with pytest.raises(ValueError, match="outside WED IDs"):
        validate_semantic_mask(np.array([[0, 42]], dtype=np.uint8))
