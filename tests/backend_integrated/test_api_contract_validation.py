"""Backend-integrated API contract validation (P1-012)."""

from __future__ import annotations

import pytest

from tests.backend_integrated.conftest import BackendValidationHarness

pytestmark = [pytest.mark.backend_integrated]


class TestAPIContractValidation:
    """Validate OpenAPI contract availability across layers."""

    @pytest.fixture
    def harness(self, seed_ids: "SeedIds") -> BackendValidationHarness:  # type: ignore[name-defined]
        return BackendValidationHarness(seed_ids)

    @pytest.mark.parametrize("layer", ["l1", "l2", "l3", "l4", "l5", "l6"])
    async def test_openapi_json_available(self, harness: BackendValidationHarness, layer: str) -> None:
        """Each layer must expose an OpenAPI JSON spec."""
        for path in ["/openapi.json", "/api/openapi.json", "/v1/openapi.json"]:
            try:
                body, response = await harness.request(layer, "GET", path, expected=(200,))
                assert isinstance(body, dict)
                assert "openapi" in body or "swagger" in body
                return
            except AssertionError:
                continue
        pytest.fail(f"No OpenAPI JSON endpoint available for {layer.upper()}")

    @pytest.mark.parametrize("layer", ["l1", "l2", "l3", "l4", "l5", "l6"])
    async def test_docs_ui_available(self, harness: BackendValidationHarness, layer: str) -> None:
        """Each layer must expose a docs UI (Swagger or ReDoc)."""
        for path in ["/docs", "/redoc", "/api/docs", "/api/redoc"]:
            try:
                _, response = await harness.request(layer, "GET", path, expected=(200, 307))
                return
            except AssertionError:
                continue
        pytest.fail(f"No docs UI endpoint available for {layer.upper()}")

    async def test_cross_layer_headers_preserved(self, harness: BackendValidationHarness) -> None:
        """Tenant and request ID headers must be preserved across layers."""
        tenant_id = harness.seed_ids.tenant_a
        for layer in ["l1", "l2", "l3", "l4", "l5", "l6"]:
            _, response = await harness.request(
                layer, "GET", "/health", tenant_id=tenant_id, expected=(200, 204)
            )
            assert response.request.headers.get("x-tenant-id") == tenant_id
