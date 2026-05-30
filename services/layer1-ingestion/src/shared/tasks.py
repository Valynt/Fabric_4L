"""Re-export shim — canonical implementation lives in layer1_ingestion.shared.tasks.

This file preserves backward compatibility for imports from ``src.shared.tasks``
when ``services/layer1-ingestion/src/`` is present on ``PYTHONPATH`` (development
mode).  In production the installed package ``layer1_ingestion.shared.tasks`` is
used exclusively.
"""

from layer1_ingestion.shared.tasks import *  # noqa: F401,F403
from layer1_ingestion.shared.tasks import celery_app  # noqa: F401
