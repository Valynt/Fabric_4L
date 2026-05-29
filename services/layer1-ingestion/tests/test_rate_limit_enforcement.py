"""P0-009: Layer 1 API rate limiting must be in ENFORCE mode.

Verifies that both main.py and app_monolith.py configure rate limiting
with EnforcementMode.ENFORCE rather than AUDIT.
"""

from __future__ import annotations

from pathlib import Path

import pytest


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_MAIN_PY = _PROJECT_ROOT / "services/layer1-ingestion/src/api/main.py"
_APP_MONOLITH_PY = _PROJECT_ROOT / "services/layer1-ingestion/src/api/app_monolith.py"


class TestRateLimitEnforcementMode:
    """Rate limiting must be enforced, not merely audited."""

    def _read_source(self, path: Path) -> str:
        assert path.exists(), f"{path} must exist"
        return path.read_text(encoding="utf-8")

    def test_main_py_uses_enforce_for_rate_limiting(self):
        source = self._read_source(_MAIN_PY)
        assert "EnforcementMode.ENFORCE" in source, (
            "main.py must use EnforcementMode.ENFORCE for rate limiting"
        )
        # Ensure the old AUDIT mode for rate_limiting is gone
        assert "rate_limiting=EnforcementControlConfig(mode=EnforcementMode.AUDIT)" not in source, (
            "main.py must not leave rate_limiting in AUDIT mode"
        )
        assert "rate_limit=FrameworkRateLimitConfig(\n        mode=EnforcementMode.AUDIT" not in source, (
            "main.py must not leave FrameworkRateLimitConfig in AUDIT mode"
        )

    def test_app_monolith_py_uses_enforce_for_rate_limiting(self):
        source = self._read_source(_APP_MONOLITH_PY)
        assert "EnforcementMode.ENFORCE" in source, (
            "app_monolith.py must use EnforcementMode.ENFORCE for rate limiting"
        )
        assert "rate_limiting=EnforcementControlConfig(mode=EnforcementMode.ENFORCE)" in source, (
            "app_monolith.py must explicitly set rate_limiting to ENFORCE"
        )
        assert "rate_limit=FrameworkRateLimitConfig(\n        mode=EnforcementMode.ENFORCE" in source, (
            "app_monolith.py must explicitly set FrameworkRateLimitConfig to ENFORCE"
        )
