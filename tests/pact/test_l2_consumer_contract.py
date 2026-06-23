"""Consumer-side Pact contract tests for Layer 2 Extraction API.

P2-009: Expand Pact coverage beyond L4.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import requests

pytestmark = [pytest.mark.pact, pytest.mark.contract_static]


@pytest.fixture
def l2_consumer_pact(pact_dir: Path) -> Any:
    """Build a Pact between a consumer and Layer 2 provider."""
    pytest.importorskip("pact")
    from pact import Consumer, Provider

    pact = Consumer("value-fabric-extraction-client").has_pact_with(
        Provider("layer2-extraction-api"),
        pact_dir=str(pact_dir),
        log_dir=str(pact_dir / "logs"),
    )
    return pact


class TestL2RootEndpoint:
    """Pact contract for the L2 root endpoint."""

    def test_root_returns_service_metadata(self, l2_consumer_pact: Any) -> None:
        expected_body = {
            "service": "layer2-extraction",
            "status": "ok",
        }

        (l2_consumer_pact
         .given("Layer 2 is healthy")
         .upon_receiving("a request for the root endpoint")
         .with_request("GET", "/")
         .will_respond_with(200, body=expected_body))

        with l2_consumer_pact:
            result = requests.get(l2_consumer_pact.uri + "/")
            assert result.status_code == 200
            assert result.json()["service"] == "layer2-extraction"
