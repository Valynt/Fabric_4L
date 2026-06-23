"""Pytest configuration for Layer 1 Ingestion tests."""

import os
import sys
from pathlib import Path

# Add src directory to Python path for imports (at the very beginning)
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Ensure PYTHONPATH includes src for subprocesses
os.environ["PYTHONPATH"] = src_path + os.pathsep + os.environ.get("PYTHONPATH", "")

# Provide safe test defaults for required S3/MinIO credentials so that importing
# the settings module does not fail at collection time. Tests that need to assert
# missing-credential behavior should explicitly remove these variables.
os.environ.setdefault("LAYER1_S3_ACCESS_KEY", "test-access-key")
os.environ.setdefault("LAYER1_S3_SECRET_KEY", "test-secret-key")
