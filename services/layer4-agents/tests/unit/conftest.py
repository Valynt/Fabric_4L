from __future__ import annotations

"""Unit test conftest — adds src/ to sys.path so bare harness.* imports resolve."""


import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[2] / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
