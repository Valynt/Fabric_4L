"""Regression tests for authorization defects identified during PR review."""

from __future__ import annotations

from pathlib import Path

from value_fabric.shared.authz.engine import DecisionEngine, load_bundle
from value_fabric.shared.authz.models import AuthzEnvironment, AuthzRequest
from value_fabric.shared.authz.principal_context import (
    PrincipalContext,
    principal_context_from_request,
)

BUNDLE_DATA = (
    Path(__file__).parents[3] / "policies" / "authorization" / "bundle" / "data"
)


def test_identity_prefixes_are_classified_as_non_human_principals() -> None:
    agent = principal_context_from_request(
        {"tenant_id": "tenant-1", "user_id": "agent:planner"}
    )
    service = principal_context_from_request(
        {"tenant_id": "tenant-1", "user_id": "service:layer5"}
    )

    assert agent.principal_type == "agent"
    assert service.principal_type == "service"


def test_static_separation_of_duties_denies_conflicting_roles() -> None:
    bundle = load_bundle(str(BUNDLE_DATA), policy_version="test")
    principal = PrincipalContext.build(
        principal_type="human",
        principal_id="reviewer",
        tenant_id="tenant-1",
        roles=["value_engineer", "finance_approver"],
    )
    request = AuthzRequest(
        action="claim.approve",
        principal=principal,
        resource={"tenant_id": "tenant-1"},
        environment=AuthzEnvironment(
            resource_attributes={
                "author_id": "author",
                "validation_complete": True,
            },
            relationships={"review_pool_binding": True},
        ),
    )

    result = DecisionEngine(bundle).evaluate(request)

    assert result.allowed is False
    assert result.deny_code == "STATIC_SOD_VIOLATION"
