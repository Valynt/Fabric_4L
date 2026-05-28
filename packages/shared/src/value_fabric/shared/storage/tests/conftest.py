"""pytest configuration for storage tests - bypasses root conftest dependency checks."""

import sys
from pathlib import Path

# Add src directory to path for imports
# File is at: packages/shared/src/value_fabric/shared/storage/tests/conftest.py
# We need to go up 4 levels to reach packages/shared/src/
SRC_DIR = Path(__file__).resolve().parents[4]  # Go up to src/
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import pytest
