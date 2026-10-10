"""Pytest must never write the real logs/nutrisense.log."""
import logging
from pathlib import Path

import main  # noqa: F401  — runs _configure_logging() under the conftest env


def test_file_handler_points_away_from_repo_log() -> None:
    repo_log = (Path(__file__).resolve().parents[1] / "logs" / "nutrisense.log").resolve()
    log = logging.getLogger("nutrisense")
    assert log.handlers, "expected handlers from main._configure_logging"
    file_handlers = [h for h in log.handlers if isinstance(h, logging.FileHandler)]
    assert file_handlers, "expected a file handler, redirected to a temp dir"
    for handler in file_handlers:
        assert Path(handler.baseFilename).resolve() != repo_log
