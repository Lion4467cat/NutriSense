from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from models.inference_lock import inference_lock


def _hold_lock(path: str, ready, acquired, release) -> None:
    ready.set()
    with inference_lock(Path(path)):
        acquired.set()
        release.wait(3)


def test_inference_lock_serializes_api_workers(tmp_path):
    context = multiprocessing.get_context("fork")
    path = str(tmp_path / "inference.lock")
    first_ready, second_ready = context.Event(), context.Event()
    first_acquired, second_acquired = context.Event(), context.Event()
    first_release, second_release = context.Event(), context.Event()
    first = context.Process(target=_hold_lock,
                            args=(path, first_ready, first_acquired,
                                  first_release))
    second = context.Process(target=_hold_lock,
                             args=(path, second_ready, second_acquired,
                                   second_release))
    first.start()
    try:
        assert first_ready.wait(2)
        assert first_acquired.wait(2)
        # The child signals before attempting flock; give it time to block.
        time.sleep(0.05)
        second.start()
        assert second_ready.wait(2)
        assert not second_acquired.wait(0.05)
        first_release.set()
        assert second_acquired.wait(2)
        second_release.set()
        second.join(2)
        assert second.exitcode == 0
    finally:
        first_release.set()
        second_release.set()
        first.join(2)
        if second.pid is not None:
            second.join(2)
