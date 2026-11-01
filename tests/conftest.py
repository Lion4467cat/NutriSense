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

#: Compliant capture metadata for synthetic runs. Since the zoom-gate
#: enforcement (AUDIT P1) an absent DigitalZoomRatio is a hard input reject,
#: so tests that do not target the zoom gate must pass this explicitly —
#: synthetic fixtures carry no real EXIF.
OK_EXIF = {"focal_mm": None, "subject_distance_cm": None,
           "digital_zoom": 1.0, "camera": None}

from models import registry as _registry  # noqa: E402

_registry.register("weight_head", lambda: None)
# Hermetic ingredient head (07e): off-menu seam tests inject their own head
# through deps={"ingredient_head": ...}; a real data/ingredient_head.pt must
# never change test behaviour when it lands (ledger 012).
_registry.register("ingredient_head", lambda: None)
# Hermetic multi-item detection (spec 003): seam tests inject their own
# detector through deps={"segment_items": ...}; the real SAM2 grid9 pass must
# never run (or load a model) inside the hermetic suite.
_registry.register("segment_items", lambda: None)

# JPEG magic + a parsable SOF (768x1025) but no scan data: main.py parses the
# dimensions, cv2 fails to decode, and the upload falls through to the
# unreadable_analysis envelope (200 with the full wire shape) instead of the
# magic-byte 415/422 rejects. The unreadable-fixture tests send this.
UNREADABLE_JPEG = (b"\xff\xd8\xff\xc0\x00\x08\x08\x03\x00\x05\x01"
                   + b"\xff\xd9")
