"""Sprint 5 — Provider and billing posture tests (S5-R6, S5-R7).

Verifies:
  S5-R6  Billing routes fail closed with billing_not_configured when Stripe absent
  S5-R7  Anthropic raises ProviderNotImplementedError
         Enrichment fails closed without ENRICHMENT_MOCK_MODE=true
         Enrichment returns mock-tagged data with ENRICHMENT_MOCK_MODE=true

Tests use AST/source inspection where direct imports conflict with the
top-level services/ namespace package. Runtime tests use pytest-asyncio
with the layer4 conftest path.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [pytest.mark.security, pytest.mark.unit]


# ---------------------------------------------------------------------------
# S5-R7.1/7.2 — Anthropic raises ProviderNotImplementedError (source checks)
# ---------------------------------------------------------------------------


class TestAnthropicProviderPosture:
    """Anthropic adapter raises typed ProviderNotImplementedError."""

    def test_provider_not_implemented_error_defined(self) -> None:
        """ProviderNotImplementedError is defined in llm_adapter_interfaces.py."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/llm_adapter_interfaces.py"
        ).read_text()
        assert "class ProviderNotImplementedError" in source, (
            "ProviderNotImplementedError must be defined in llm_adapter_interfaces.py"
        )
        assert "RuntimeError" in source, (
            "ProviderNotImplementedError must subclass RuntimeError"
        )

    def test_provider_not_implemented_error_has_provider_name(self) -> None:
        """ProviderNotImplementedError stores provider_name attribute."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/llm_adapter_interfaces.py"
        ).read_text()
        assert "self.provider_name" in source, (
            "ProviderNotImplementedError must store provider_name"
        )

    def test_anthropic_branch_raises_provider_not_implemented_error(self) -> None:
        """llm_provider.py raises ProviderNotImplementedError for anthropic."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/llm_provider.py"
        ).read_text()
        tree = ast.parse(source)

        # Find the anthropic branch
        found_anthropic = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                node_src = ast.get_source_segment(source, node) or ""
                if '"anthropic"' in node_src or "'anthropic'" in node_src:
                    found_anthropic = True
                    assert "ProviderNotImplementedError" in node_src, (
                        "Anthropic branch must raise ProviderNotImplementedError"
                    )
                    assert "NotImplementedError(" not in node_src or \
                           "ProviderNotImplementedError(" in node_src, (
                        "Anthropic branch must not raise bare NotImplementedError"
                    )

        assert found_anthropic, "Anthropic branch not found in llm_provider.py"

    def test_llm_provider_imports_provider_not_implemented_error(self) -> None:
        """llm_provider.py imports ProviderNotImplementedError from llm_adapter_interfaces."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/llm_provider.py"
        ).read_text()
        assert "ProviderNotImplementedError" in source, (
            "llm_provider.py must import and use ProviderNotImplementedError"
        )

    def test_provider_not_implemented_error_inherits_runtime_error(self) -> None:
        """ProviderNotImplementedError(RuntimeError) — verified via AST class hierarchy."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/llm_adapter_interfaces.py"
        ).read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "ProviderNotImplementedError":
                bases = [ast.get_source_segment(source, b) or "" for b in node.bases]
                assert any("RuntimeError" in b for b in bases), (
                    f"ProviderNotImplementedError must subclass RuntimeError, got bases: {bases}"
                )
                # Check __init__ sets provider_name and calls super().__init__
                class_src = ast.get_source_segment(source, node) or ""
                assert "self.provider_name" in class_src, (
                    "ProviderNotImplementedError.__init__ must set self.provider_name"
                )
                assert "super().__init__" in class_src, (
                    "ProviderNotImplementedError.__init__ must call super().__init__ with message"
                )
                return

        pytest.fail("ProviderNotImplementedError class not found in llm_adapter_interfaces.py")


# ---------------------------------------------------------------------------
# S5-R7.3/7.4 — Enrichment mock-mode guard (source checks)
# ---------------------------------------------------------------------------


class TestEnrichmentMockModeGuard:
    """Enrichment fails closed without ENRICHMENT_MOCK_MODE=true."""

    def test_domain_enrichment_checks_mock_mode_env(self) -> None:
        """_enrich_from_domain checks ENRICHMENT_MOCK_MODE before returning data."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/enrichment_orchestrator.py"
        ).read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_enrich_from_domain":
                fn_src = ast.get_source_segment(source, node) or ""
                assert "ENRICHMENT_MOCK_MODE" in fn_src, (
                    "_enrich_from_domain must check ENRICHMENT_MOCK_MODE env var"
                )
                assert "mock_mode" in fn_src, (
                    "_enrich_from_domain must use a mock_mode variable"
                )
                assert '"success": False' in fn_src or "'success': False" in fn_src, (
                    "_enrich_from_domain must return success=False when not in mock mode"
                )
                assert '"mock": True' in fn_src or "'mock': True" in fn_src, (
                    "_enrich_from_domain must tag mock responses with mock=True"
                )
                return

        pytest.fail("_enrich_from_domain not found in enrichment_orchestrator.py")

    def test_news_enrichment_checks_mock_mode_env(self) -> None:
        """_enrich_from_news checks ENRICHMENT_MOCK_MODE before returning data."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/enrichment_orchestrator.py"
        ).read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_enrich_from_news":
                fn_src = ast.get_source_segment(source, node) or ""
                assert "ENRICHMENT_MOCK_MODE" in fn_src, (
                    "_enrich_from_news must check ENRICHMENT_MOCK_MODE env var"
                )
                assert "mock_mode" in fn_src, (
                    "_enrich_from_news must use a mock_mode variable"
                )
                assert '"success": False' in fn_src or "'success': False" in fn_src, (
                    "_enrich_from_news must return success=False when not in mock mode"
                )
                assert '"mock": True' in fn_src or "'mock': True" in fn_src, (
                    "_enrich_from_news must tag mock responses with mock=True"
                )
                return

        pytest.fail("_enrich_from_news not found in enrichment_orchestrator.py")

    def test_enrichment_fail_closed_error_shape(self) -> None:
        """Enrichment not-configured response has error key with not_configured value."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/enrichment_orchestrator.py"
        ).read_text()
        assert "not_configured" in source, (
            "enrichment_orchestrator.py must use 'not_configured' in error responses"
        )

    def test_enrichment_mock_response_tagged_with_source_mock(self) -> None:
        """Mock responses set source='mock' and mock=True."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/enrichment_orchestrator.py"
        ).read_text()
        assert '"source": "mock"' in source or "'source': 'mock'" in source, (
            "Mock enrichment responses must set source='mock'"
        )
        assert '"mock": True' in source or "'mock': True" in source, (
            "Mock enrichment responses must set mock=True"
        )


# ---------------------------------------------------------------------------
# S5-R6 — Billing fail-closed (source checks)
# ---------------------------------------------------------------------------


class TestBillingFailClosed:
    """Billing routes return billing_not_configured when Stripe is absent."""

    def test_stripe_not_configured_error_defined(self) -> None:
        """StripeNotConfiguredError is defined in stripe_client.py."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/stripe_client.py"
        ).read_text()
        assert "class StripeNotConfiguredError" in source, (
            "StripeNotConfiguredError must be defined in stripe_client.py"
        )

    def test_billing_route_imports_stripe_not_configured_error(self) -> None:
        """routers.py imports StripeNotConfiguredError for route-level handling."""
        source = pathlib.Path(
            "services/layer4-agents/src/api/routers.py"
        ).read_text()
        assert "StripeNotConfiguredError" in source, (
            "routers.py must import StripeNotConfiguredError"
        )

    def test_billing_not_configured_response_shape(self) -> None:
        """billing.py raises 402; routers.py handles billing_not_configured."""
        billing_source = pathlib.Path(
            "services/layer4-agents/src/api/routes/billing.py"
        ).read_text()
        routers_source = pathlib.Path(
            "services/layer4-agents/src/api/routers.py"
        ).read_text()
        assert "billing_not_configured" in routers_source, (
            "routers.py must define the billing_not_configured error response"
        )
        assert (
            "402" in billing_source
            or "HTTP_402" in billing_source
            or "PAYMENT_REQUIRED" in billing_source
        ), (
            "billing.py must use HTTP 402 for billing_not_configured"
        )

    def test_routers_registers_billing_always(self) -> None:
        """routers.py always registers billing routes (fail-closed, not absent)."""
        source = pathlib.Path(
            "services/layer4-agents/src/api/routers.py"
        ).read_text()
        assert "billing_router" in source, (
            "routers.py must include billing_router"
        )
        assert "StripeNotConfiguredError" in source, (
            "routers.py must register a StripeNotConfiguredError exception handler"
        )
        assert "billing_not_configured" in source, (
            "routers.py exception handler must return billing_not_configured"
        )

    def test_stripe_client_uses_env_get_for_key(self) -> None:
        """stripe_client.py uses os.environ.get for STRIPE_SECRET_KEY (no crash on missing)."""
        source = pathlib.Path(
            "services/layer4-agents/src/services/stripe_client.py"
        ).read_text()
        assert (
            'os.environ.get("STRIPE_SECRET_KEY"' in source
            or "os.environ.get('STRIPE_SECRET_KEY'" in source
            or "os.getenv(" in source
        ), (
            "stripe_client.py must use os.environ.get or os.getenv for STRIPE_SECRET_KEY "
            "to avoid KeyError on missing env var"
        )
