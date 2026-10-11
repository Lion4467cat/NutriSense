"""Test-session side effects.

main._configure_logging() creates a rotating file handler at import time, so
tests import main — redirect the log directory to a throwaway path *before*
any test module imports main. This keeps pytest from writing (or rotating)
the real logs/nutrisense.log.

Hermetic weight head: never auto-load data/weight_head.pt in tests — seam
tests inject their own head through deps={"weight_head": ...}. Without this,
training would change test behaviour as soon as the checkpoint lands.
"""
import os
import tempfile

os.environ.setdefault(
    "NUTRISENSE_LOG_DIR",
    tempfile.mkdtemp(prefix="nutrisense-pytest-logs-"),
)

import engine.pipeline as _pipeline  # noqa: E402

_pipeline._weight_head_missing = True
