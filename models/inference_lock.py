"""Host-wide admission lock for expensive inference in multiple API workers."""
from __future__ import annotations

import fcntl
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def _lock_path() -> Path:
    configured = os.environ.get("NUTRISENSE_INFERENCE_LOCK_FILE")
    return Path(configured) if configured else Path(tempfile.gettempdir()) / (
        f"nutrisense-inference-{os.getuid()}.lock"
    )


@contextmanager
def inference_lock(path: Path | None = None) -> Iterator[None]:
    """Serialize model inference between NutriSense workers on this host.

    The lock file contains no data and is intentionally outside the project
    tree. It coordinates processes that share the same filesystem and UID;
    it cannot account for unrelated programs using the accelerator.
    """
    lock_path = path or _lock_path()
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
