from __future__ import annotations

"""Health check script for Docker HEALTHCHECK.

Uses urllib from the standard library to avoid external dependencies.
"""
import asyncio
import logging
import sys
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


def main() -> int:
    """Check the /health endpoint and return 0 if healthy, 1 otherwise."""
    try:
        req = urllib.request.Request(
            "http://localhost:8000/health",
            method="GET",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
            if response.status == 200:
                return 0
    except urllib.error.HTTPError as e:
        logger.error(f"Health check HTTP error: {e.code}")
    except urllib.error.URLError as e:
        logger.error(f"Health check connection error: {e.reason}")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
