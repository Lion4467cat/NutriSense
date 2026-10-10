"""Test-session side effects.

main._configure_logging() creates a rotating file handler at import time, so
tests import main — redirect the log directory to a throwaway path *before*
any test module imports main. This keeps pytest from writing (or rotating)
the real logs/nutrisense.log.
"""
import os
import tempfile

os.environ.setdefault(
    "NUTRISENSE_LOG_DIR",
    tempfile.mkdtemp(prefix="nutrisense-pytest-logs-"),
)
