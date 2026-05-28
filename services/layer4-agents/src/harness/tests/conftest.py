from __future__ import annotations

"""Conftest for harness persistence tests.

Sets the minimum env vars required by Settings() so that importing
value_fabric.layer4.* at collection time does not raise a ValidationError.
These tests use SQLite (aiosqlite) — no live services are required.
"""

import os

os.environ.setdefault("LAYER4_LAYER1_API_URL", "http://localhost:8001")
os.environ.setdefault("LAYER4_LAYER2_API_URL", "http://localhost:8002")
os.environ.setdefault("LAYER4_LAYER3_API_URL", "http://localhost:8003")
os.environ.setdefault("LAYER4_LAYER5_API_URL", "http://localhost:8005")
os.environ.setdefault("LAYER4_ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT", "true")
