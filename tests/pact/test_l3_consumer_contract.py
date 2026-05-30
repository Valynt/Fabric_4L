"""Consumer-side Pact contract tests for Layer 3 Knowledge API.

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
def l3_consumer_pact(pact_dir: Path) -> Any:
    """Build a Pact between a consumer and Layer 3 provider."""
    pytest.importorskip("pact")
    from pact import Consumer, Provider

    pact = Consumer("value-fabric-knowledge-client").has_pact_with(
        Provider("layer3-knowledge-api"),
        pact_dir=str(pact_dir),
        log_dir=str(pact_dir / "logs"),
    )
    return pact


class TestL3RootEndpoint:
    """Pact contract for the L3 root endpoint."""

    def test_root_returns_service_metadata(self, l3_consumer_pact: Any) -> None:
        expected_body = {
            "service": "layer3-knowledge",
            "status": "ok",
        }

        (l3_consumer_pact
         .given("Layer 3 is healthy")
         .upon_receiving("a request for the root endpoint")
         .with_request("GET", "/")
         .will_respond_with(200, body=expected_body))

        with l3_consumer_pact:
            result = requests.get(l3_consumer_pact.uri + "/")
            assert result.status_code == 200
            assert result.json()["service"] == "layer3-knowledge"
