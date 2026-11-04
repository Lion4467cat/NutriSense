"""CPU-only tests for the application-to-pipeline orchestration boundary."""
from contextlib import contextmanager

import pytest

from engine.application import AnalysisRequest, AnalysisService


def test_service_passes_request_to_injected_pipeline_without_loading_models():
    image = object()
    exif = {"digital_zoom": 1.0}
    response = {"verdict": "ESTIMATED", "items": []}
    calls = []
    guard_events = []

    @contextmanager
    def fake_guard():
        guard_events.append("enter")
        try:
            yield
        finally:
            guard_events.append("exit")

    def fake_pipeline(image_bgr, **kwargs):
        calls.append((image_bgr, kwargs))
        return response

    service = AnalysisService(fake_pipeline, inference_guard=fake_guard)
    result = service.analyze(
        image,
        AnalysisRequest(day="wed", band="6-8", mode="general",
                        serving_style="single"),
        exif=exif,
    )

    assert result is response
    assert calls == [(
        image,
        {
            "day": "wed",
            "band": "6-8",
            "exif": exif,
            "serving_style": "single",
            "mode": "general",
        },
    )]
    assert guard_events == ["enter", "exit"]


def test_service_releases_inference_guard_when_pipeline_raises():
    events = []

    @contextmanager
    def fake_guard():
        events.append("enter")
        try:
            yield
        finally:
            events.append("exit")

    def failing_pipeline(*_args, **_kwargs):
        raise RuntimeError("mock failure")

    service = AnalysisService(failing_pipeline, inference_guard=fake_guard)
    with pytest.raises(RuntimeError, match="mock failure"):
        service.analyze(object(), AnalysisRequest(day="mon", band="1-5"))
    assert events == ["enter", "exit"]
