"""Redirect shim: value_fabric.layer6.* -> services/layer6-benchmarks/src/*.

Canonical Layer 6 code lives exclusively in ``services/layer6-benchmarks/src/``.
This shim appends that directory to ``__path__`` so that
``import value_fabric.layer6.api.main`` resolves to the canonical tree.
"""

from __future__ import annotations

from pathlib import Path

_repo_root: Path = Path(__file__).resolve().parent.parent.parent
_canonical: str = str(_repo_root / "services" / "layer6-benchmarks" / "src")

# Only register the canonical path if it exists; fail fast otherwise.
if (_repo_root / "services" / "layer6-benchmarks" / "src").exists():
    if _canonical not in __path__:
        __path__.append(_canonical)
else:
    raise FileNotFoundError(
        f"Canonical Layer 6 source tree not found at {_canonical}. "
        "Expected services/layer6-benchmarks/src/ to exist."
    )


import logging
import sys
import structlog


def configure_structured_logging() -> None:
    """Configure JSON structured logs for layer6."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
