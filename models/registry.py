"""Central model registry: one load per process, thread-safe, explicit unload.

Replaces the ad hoc per-module caches (dish_segmenter._STATE,
food_classifier._STATE, MonocularDepth._model, pipeline's
_default_weight_head/_default_depth globals). Loading is lazy: the first
get_or_create() for a name runs the factory under a lock and caches the
result; later calls return the same instance. A factory failure is surfaced
to the first caller; later calls return None during an exponential backoff,
then retry automatically. unload() drops every cached instance, runs gc and
torch.cuda.empty_cache() so VRAM is actually returned to the driver.

Factories are passed at the call site (or pre-registered with register(),
which also replaces any cached instance — used by tests to install fakes
without importing model code).
"""
from __future__ import annotations

import gc
import threading
import time
from typing import Any, Callable

_lock = threading.RLock()
_instances: dict[str, Any] = {}
_factories: dict[str, Callable[[], Any]] = {}
_failed: dict[str, tuple[int, float]] = {}
_RETRY_BASE_SECONDS = 5.0
_RETRY_MAX_SECONDS = 300.0


def register(name: str, factory: Callable[[], Any]) -> None:
    """(Re)install the factory for name and drop any cached instance."""
    with _lock:
        _factories[name] = factory
        _instances.pop(name, None)
        _failed.pop(name, None)


def get_or_create(name: str, factory: Callable[[], Any] | None = None) -> Any:
    """Return the singleton for name, loading it once.

    A factory registered via register() takes precedence over the inline
    one. Failed loads raise on the failing request, return None during a
    bounded backoff, and retry automatically when that backoff expires.
    """
    with _lock:
        failure_state = _failed.get(name)
        attempts_before = 0
        if failure_state is not None:
            attempts_before, retry_at = failure_state
            if time.monotonic() < retry_at:
                return None
            _failed.pop(name, None)
        if name not in _instances:
            fn = _factories.get(name) or factory
            if fn is None:
                raise KeyError(f"no factory for model {name!r}")
            try:
                _instances[name] = fn()
            except Exception:
                attempts = attempts_before + 1
                delay = min(
                    _RETRY_BASE_SECONDS * (3 ** (attempts - 1)),
                    _RETRY_MAX_SECONDS,
                )
                _failed[name] = (attempts, time.monotonic() + delay)
                raise
            _failed.pop(name, None)
        return _instances[name]


def peek(name: str) -> Any:
    """The cached instance without loading; None if absent or failed."""
    with _lock:
        return _instances.get(name)


def loaded() -> tuple[str, ...]:
    with _lock:
        return tuple(sorted(_instances))


def failed() -> tuple[str, ...]:
    """Model names waiting for their next bounded load retry."""
    with _lock:
        return tuple(sorted(_failed))


def clear_cache() -> None:
    """Run gc and return cached VRAM to the driver WITHOUT dropping
    instances — used by the OOM recovery path after unload() (and alone when
    only fragmentation needs clearing)."""
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def unload(name: str | None = None) -> None:
    """Free one model (or all), clear retry state, and return GPU memory."""
    with _lock:
        if name is None:
            _instances.clear()
            _failed.clear()
        else:
            _instances.pop(name, None)
            _failed.pop(name, None)
    clear_cache()
