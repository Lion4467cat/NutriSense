"""models.registry unit tests — fakes only, no GPU, no model downloads.

The registry is the single load-once point for SAM2, SigLIP2, MoGe-2 and
the weight head (STAGE 2). These tests pin its contract: factory runs once,
repeated calls return the same instance (including under concurrency),
a failing factory is sticky, register() overrides, unload() frees and
resets.
"""
from __future__ import annotations

import threading
import time

import pytest

from models import registry


@pytest.fixture
def clean():
    registry.unload()
    yield
    registry.unload()


def test_factory_runs_once_and_returns_same_instance(clean):
    calls = []

    def factory():
        calls.append(1)
        return object()

    a = registry.get_or_create("t1", factory)
    b = registry.get_or_create("t1", factory)
    assert a is b
    assert len(calls) == 1


def test_concurrent_get_or_create_loads_once(clean):
    calls = []
    guard = threading.Lock()

    def factory():
        with guard:
            calls.append(1)
        time.sleep(0.02)
        return object()

    results = []

    def worker():
        results.append(registry.get_or_create("t2", factory))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1
    assert all(r is results[0] for r in results)


def test_failed_factory_is_sticky_and_returns_none(clean):
    calls = []

    def factory():
        calls.append(1)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        registry.get_or_create("t3", factory)
    assert registry.get_or_create("t3", factory) is None
    assert len(calls) == 1  # no retry after the first failure


def test_registered_factory_overrides_inline(clean):
    registry.register("t4", lambda: "fake")
    assert registry.get_or_create("t4", lambda: "real") == "fake"


def test_unload_resets_instance_and_failed_state(clean):
    registry.get_or_create("t5", lambda: object())
    registry.unload("t5")
    assert registry.peek("t5") is None
    fresh = registry.get_or_create("t5", lambda: object())
    assert registry.peek("t5") is fresh

    def boom():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        registry.get_or_create("t6", boom)
    registry.unload()  # clears sticky failures too
    assert registry.get_or_create("t6", lambda: "recovered") == "recovered"


def test_unload_is_idempotent_and_peek_is_non_loading(clean):
    assert registry.peek("t7") is None
    registry.unload()
    registry.unload()
    assert registry.loaded() == ()
