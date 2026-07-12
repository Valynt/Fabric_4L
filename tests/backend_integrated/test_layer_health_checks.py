"""Backend-integrated health check validation across all layers (P1-012)."""

from __future__ import annotations

import pytest
from tests.backend_integrated.conftest import SERVICE_URLS, BackendValidationHarness

pytestmark = [pytest.mark.backend_integrated]


class TestLayerHealthChecks:
    """Verify all Fabric layers expose a working health endpoint."""

    @pytest.fixture
    def harness(self, seed_ids: SeedIds) -> BackendValidationHarness:  # type: ignore[name-defined]
        return BackendValidationHarness(seed_ids)

    @pytest.mark.parametrize("layer", ["l1", "l2", "l3", "l4", "l5", "l6"])
    async def test_layer_health(self, harness: BackendValidationHarness, layer: str) -> None:
        path, body = await harness.first_healthy(layer)
        assert path is not None
        assert isinstance(body, dict)

    @pytest.mark.parametrize("layer", ["l1", "l2", "l3", "l4", "l5", "l6"])
    async def test_layer_readiness(self, harness: BackendValidationHarness, layer: str) -> None:
        """Readiness endpoints must return 200 when healthy."""
        base_url = SERVICE_URLS[layer]
        readiness_paths = ["/ready", "/api/v1/ready", "/v1/ready"]
        for path in readiness_paths:
            try:
                body, _ = await harness.request(layer, "GET", path, expected=(200,))
                assert isinstance(body, dict)
                return
            except AssertionError:
                continue
        pytest.fail(f"No readiness endpoint returned 200 for {layer.upper()}")

    async def test_all_layers_respond(self, harness: BackendValidationHarness) -> None:
        """All six layers must respond within timeout."""
        for layer in ["l1", "l2", "l3", "l4", "l5", "l6"]:
            path, body = await harness.first_healthy(layer)
            assert body is not None
