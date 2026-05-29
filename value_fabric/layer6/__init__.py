"""Redirect shim: value_fabric.layer6.* -> services/layer6-benchmarks/src/layer6_benchmarks/*.

Canonical Layer 6 code lives in ``services/layer6-benchmarks/src/layer6_benchmarks/``.
This shim appends the canonical package path to ``__path__`` so that
``import value_fabric.layer6.api.main`` resolves to the canonical tree.

**DEPRECATED:** Use canonical imports ``layer6_benchmarks.*`` instead.
This facade will be removed in a future release.
"""

from __future__ import annotations

import warnings
from pathlib import Path

_repo_root: Path = Path(__file__).resolve().parent.parent.parent
_canonical_pkg: str = str(_repo_root / "services" / "layer6-benchmarks" / "src" / "layer6_benchmarks")

# Register the canonical package path for import resolution
if (_repo_root / "services" / "layer6-benchmarks" / "src" / "layer6_benchmarks").exists():
    if _canonical_pkg not in __path__:
        __path__.append(_canonical_pkg)
else:
    raise FileNotFoundError(
        f"Canonical Layer 6 package not found at {_canonical_pkg}. "
        "Expected services/layer6-benchmarks/src/layer6_benchmarks/ to exist."
    )

# Emit deprecation warning on import
warnings.warn(
    "value_fabric.layer6 is deprecated. Use canonical imports: layer6_benchmarks.*",
    DeprecationWarning,
    stacklevel=2,
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
