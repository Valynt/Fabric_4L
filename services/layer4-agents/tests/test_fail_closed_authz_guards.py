from __future__ import annotations

"""Regression tests for authentication and governance fail-closed safeguards.

These tests intentionally inspect the route source text instead of importing the
FastAPI modules because the route imports require the full service dependency
set. The assertions protect against the specific production blocker fixed in
C-03: optional security/governance imports that silently degraded into
permissive runtime behavior.
"""


import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
HEALTH_BADGES_ROUTE = REPO_ROOT / "services/layer4-agents/src/api/routes/health_badges.py"
TOOLS_ROUTE = REPO_ROOT / "services/layer4-agents/src/api/routes/tools.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class FailClosedAuthzGuardTests(unittest.TestCase):
    def test_health_badges_route_does_not_define_permissive_auth_fallback(self) -> None:
        """Health-badge endpoints must always depend on shared authentication."""
        source = _read(HEALTH_BADGES_ROUTE)

        self.assertNotIn("SECURITY_AVAILABLE", source)
        self.assertNotIn("if SECURITY_AVAILABLE else", source)
        self.assertNotIn("lambda: None", source)
        self.assertIn("Depends(require_authenticated)", source)
        self.assertIn("from value_fabric.shared.identity.dependencies import", source)

    def test_tool_invocation_route_does_not_fallback_to_direct_registry_execution(self) -> None:
        """Tool execution must not bypass GATE if the governance gateway is unavailable."""
        source = _read(TOOLS_ROUTE)

        self.assertNotIn("registry.execute(request.tool_name", source)
        self.assertNotIn('registry.execute("export_document"', source)
        self.assertNotIn("invoked without policy enforcement", source)
        self.assertIn("require_tool_gateway_available()", source)
        self.assertIn("Tool governance gateway unavailable; refusing ungoverned tool execution", source)

    def test_tool_route_preserves_deliberate_http_fail_closed_errors(self) -> None:
        """HTTPException raised by fail-closed checks must not be swallowed as 200 responses."""
        source = _read(TOOLS_ROUTE)

        self.assertIn("except HTTPException:\n        raise", source)
        self.assertLess(
            source.index("require_tool_gateway_available()"),
            source.index("except HTTPException:\n        raise"),
        )


if __name__ == "__main__":
    unittest.main()
