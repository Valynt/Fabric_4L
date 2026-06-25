"""Make .agent/memory scripts importable as plain modules for testing."""

from __future__ import annotations

import sys
from pathlib import Path

# The memory scripts use non-package imports such as `from promote import ...`
# and `from review_state import ...`.  Add their directory to sys.path only for
# this test package so those imports resolve without changing global config.
_MEMORY_DIR = str(Path(__file__).resolve().parents[2] / ".agent" / "memory")
if _MEMORY_DIR not in sys.path:
    sys.path.insert(0, _MEMORY_DIR)
