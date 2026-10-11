"""Central model registry: one load per process, thread-safe, explicit unload.

Replaces the ad hoc per-module caches (dish_segmenter._STATE,
food_classifier._STATE, MonocularDepth._model, pipeline's
_default_weight_head/_default_depth globals). Loading is lazy: the first
get_or_create() for a name runs the factory under a lock and caches the
result; later calls return the same instance. A factory that raises marks
the name sticky-failed: the first failure re-raises (callers may log it),
every later call returns None without retrying — the behaviour the weight
head loader already had. unload() drops every cached instance, runs gc and
torch.cuda.empty_cache() so VRAM is actually returned to the driver.

Factories are passed at the call site (or pre-registered with register(),
which also replaces any cached instance — used by tests to install fakes
without importing model code).
"""
from __future__ import annotations

import gc
import threading
from typing import Any, Callable

_lock = threading.RLock()
_instances: dict[str, Any] = {}
_factories: dict[str, Callable[[], Any]] = {}
_failed: set[str] = set()


def register(name: str, factory: Callable[[], Any]) -> None:
    """(Re)install the factory for name and drop any cached instance."""
    with _lock:
        _factories[name] = factory
        _instances.pop(name, None)
        _failed.discard(name)


def get_or_create(name: str, factory: Callable[[], Any] | None = None) -> Any:
    """Return the singleton for name, loading it once.

    A factory registered via register() takes precedence over the inline
    one. Returns None for a sticky-failed name. Raises the original factory
    error on the first failure.
    """
    with _lock:
        if name in _failed:
            return None
        if name not in _instances:
            fn = _factories.get(name) or factory
            if fn is None:
                raise KeyError(f"no factory for model {name!r}")
            try:
                _instances[name] = fn()
            except Exception:
                _failed.add(name)
                raise
        return _instances[name]


def peek(name: str) -> Any:
    """The cached instance without loading; None if absent or failed."""
    with _lock:
        return _instances.get(name)


def loaded() -> tuple[str, ...]:
    with _lock:
        return tuple(sorted(_instances))


def unload(name: str | None = None) -> None:
    """Free one model (or all) and return GPU memory to the driver."""
    with _lock:
        if name is None:
            _instances.clear()
            _failed.clear()
        else:
            _instances.pop(name, None)
            _failed.discard(name)
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
