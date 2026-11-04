"""Application boundary between the HTTP layer and an analysis pipeline.

This module deliberately knows nothing about model registries or checkpoints.
The production pipeline and lightweight test/demo pipelines implement the same
callable interface and receive decoded image pixels plus request metadata.
"""
from __future__ import annotations

from contextlib import nullcontext
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ContextManager, Protocol


@dataclass(frozen=True)
class AnalysisRequest:
    day: str
    band: str
    mode: str = "school"
    serving_style: str | None = None


class AnalysisPipeline(Protocol):
    def __call__(
        self,
        image_bgr: Any,
        *,
        day: str,
        band: str,
        exif: dict | None = None,
        serving_style: str | None = None,
        mode: str = "school",
    ) -> dict[str, Any]: ...


class AnalysisService:
    """Pass one validated request to an injected pipeline implementation."""

    def __init__(
        self,
        pipeline: AnalysisPipeline,
        *,
        inference_guard: Callable[[], ContextManager[Any]] = nullcontext,
    ) -> None:
        self._pipeline = pipeline
        self._inference_guard = inference_guard

    def analyze(
        self,
        image_bgr: Any,
        request: AnalysisRequest,
        *,
        exif: dict | None = None,
    ) -> dict[str, Any]:
        with self._inference_guard():
            return self._pipeline(
                image_bgr,
                day=request.day,
                band=request.band,
                exif=exif,
                serving_style=request.serving_style,
                mode=request.mode,
            )
