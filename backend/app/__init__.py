"""HS_WitchArena - backend."""
import os
import sys

_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vendor")
_VENDOR = os.path.normpath(_VENDOR)
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)
