from __future__ import annotations

"""Health check script for Docker HEALTHCHECK.

Uses urllib from the standard library to avoid external dependencies.
"""


import sys
import urllib.error
import urllib.request


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
        print(f"Health check HTTP error: {e.code}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"Health check connection error: {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"Health check failed: {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
