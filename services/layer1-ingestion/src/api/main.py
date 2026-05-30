"""Compatibility shim for the canonical Layer 1 FastAPI application.

The runtime implementation lives in ``layer1_ingestion.api.main``. Keep this
module thin so legacy ``api.main`` import paths cannot drift from the canonical
service entrypoint.
"""

from __future__ import annotations

from layer1_ingestion.api import main as _canonical_main

for _name in dir(_canonical_main):
    if not (_name.startswith("__") and _name.endswith("__")):
        globals()[_name] = getattr(_canonical_main, _name)

__all__ = [
    _name
    for _name in dir(_canonical_main)
    if not _name.startswith("_") and not (_name.startswith("__") and _name.endswith("__"))
]
