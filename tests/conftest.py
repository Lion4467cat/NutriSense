"""Test-session side effects.

main._configure_logging() creates a rotating file handler at import time, so
tests import main — redirect the log directory to a throwaway path *before*
any test module imports main. This keeps pytest from writing (or rotating)
the real logs/nutrisense.log.

Hermetic weight head: never auto-load data/weight_head.pt in tests — seam
tests inject their own head through deps={"weight_head": ...}. Without this,
training would change test behaviour as soon as the checkpoint lands.
(STAGE 2: the pipeline's ad hoc _weight_head_missing global was replaced by
models.registry; the hermetic pin is now a registered factory returning
None.)
"""
import os
import tempfile

os.environ.setdefault(
    "NUTRISENSE_LOG_DIR",
    tempfile.mkdtemp(prefix="nutrisense-pytest-logs-"),
)

from models import registry as _registry  # noqa: E402

_registry.register("weight_head", lambda: None)
# Hermetic ingredient head (07e): off-menu seam tests inject their own head
# through deps={"ingredient_head": ...}; a real data/ingredient_head.pt must
# never change test behaviour when it lands (ledger 012).
_registry.register("ingredient_head", lambda: None)
