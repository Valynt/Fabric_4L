"""Production Neo4j Aura validation guardrails."""

from __future__ import annotations

import pytest
from value_fabric.shared.security.neo4j import validate_neo4j_aura_config


@pytest.mark.parametrize("environment", ["production", "prod", "staging", "stage"])
@pytest.mark.parametrize(
    "uri",
    [
        "bolt://neo4j:7687",
        "bolt://localhost:7687",
        "neo4j://neo4j.value-fabric.svc.cluster.local:7687",
    ],
)
def test_production_like_environments_reject_insecure_neo4j_targets(
    environment: str, uri: str
) -> None:
    with pytest.raises(ValueError):
        validate_neo4j_aura_config(
            uri=uri,
            password="strong-password",
            environment=environment,
        )


def test_production_like_environment_accepts_aura_uri() -> None:
    validate_neo4j_aura_config(
        uri="neo4j+s://example.databases.neo4j.io",
        password="strong-password",
        environment="production",
    )


def test_development_allows_local_neo4j() -> None:
    validate_neo4j_aura_config(
        uri="bolt://neo4j:7687",
        password="password",
        environment="development",
    )
