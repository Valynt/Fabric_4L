#!/usr/bin/env python3
"""Cross-layer production smoke test launcher.

This is the canonical entry point referenced by `.github/workflows/smoke-gate.yml`
and launch-readiness documentation. It delegates to the operational smoke-test
implementation in `docs/runbooks/operational/production_smoke.py` and ensures the
report is written under `artifacts/smoke/`.

Usage:
    python scripts/smoke/production_smoke.py
    python scripts/smoke/production_smoke.py --l2-url http://localhost:8002 --l3-url http://localhost:8003 --l4-url http://localhost:8004
    python scripts/smoke/production_smoke.py --output-dir artifacts/smoke
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ORIGINAL_SCRIPT = Path("docs/runbooks/operational/production_smoke.py").resolve()


def main(argv: list[str] | None = None) -> int:
    if not ORIGINAL_SCRIPT.exists():
        print(f"ERROR: operational smoke test implementation not found: {ORIGINAL_SCRIPT}", file=sys.stderr)
        return 2

    args = list(argv) if argv is not None else sys.argv[1:]

    # Default output directory to the canonical smoke artifact location.
    if not any(arg.startswith("--output-dir") for arg in args):
        args.extend(["--output-dir", "artifacts/smoke"])

    return subprocess.run([sys.executable, str(ORIGINAL_SCRIPT), *args]).returncode


if __name__ == "__main__":
    sys.exit(main())
