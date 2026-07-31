#!/usr/bin/env python3
"""
check-contract-services.py
Validates that necessary backing services for contract tests are healthy.
Polls Layer 3, Layer 4, and Layer 5 health endpoints.
"""

import sys
import time
import urllib.error
import urllib.request

SERVICES = {
    "Layer 3": "http://localhost:8003/health",
    "Layer 4": "http://localhost:8004/health",
    "Layer 5": "http://localhost:8005/health",
}

MAX_RETRIES = 60
DELAY = 2


def check_service(name, url):
    print(f"Checking {name} at {url}...")
    for i in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    print(f"  [OK] {name} is healthy.")
                    return True
        except (urllib.error.URLError, ConnectionResetError):
            # Transient connection failures are expected while services boot;
            # the bounded retry loop below reports the final health failure.
            pass

        print(f"  [WAIT] {name} not ready... ({i + 1}/{MAX_RETRIES})")
        time.sleep(DELAY)

    print(
        f"  [FAIL] {name} failed to become healthy after {MAX_RETRIES * DELAY} seconds."
    )
    return False


def main():
    print("Verifying Contract Test Infrastructure...")
    all_healthy = True

    for name, url in SERVICES.items():
        if not check_service(name, url):
            all_healthy = False

    if not all_healthy:
        print(
            "\n[ERROR] One or more required services are not healthy. Contract tests cannot proceed."
        )
        sys.exit(1)

    print("\n[SUCCESS] All contract services are healthy. Ready for tests.")
    sys.exit(0)


if __name__ == "__main__":
    main()
