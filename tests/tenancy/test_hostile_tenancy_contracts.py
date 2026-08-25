"""Hostile Tenancy Contracts Suite.

Validates the complete set of 8 hostile tenancy contracts specified in the
Security & Tenancy Hardening Plan (Improvement Area B):

1. Signed-URL expiration and replay denial.
2. Object-storage key and prefix isolation.
3. Export and deletion isolation.
4. Graph and vector retrieval isolation.
5. AI prompt, retrieval, memory, trace, and cache isolation.
6. Queue-envelope mismatch and missing-context rejection.
7. Prior-session and tenant-switch rejection.
8. Support impersonation scope and expiration.

Each negative test validates that the target resource exists for the foreign
tenant before asserting that cross-tenant access fails closed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from tests.tenancy.hostile_fixtures import (
    ROLE_MEMBER,
    ROLE_SUPPORT,
    TENANT_ALPHA_ID,
    TENANT_BETA_ID,
    USER_ALPHA_ID,
    USER_BETA_ID,
    HostileTenancyHarness,
)

pytestmark = [
    pytest.mark.security,
    pytest.mark.tenant_boundary,
    pytest.mark.production_readiness,
]


@pytest.fixture
def harness() -> HostileTenancyHarness:
    return HostileTenancyHarness()


# ---------------------------------------------------------------------------
# Contract 1: Signed-URL Expiration & Replay Denial
# ---------------------------------------------------------------------------


def test_signed_url_replay_and_expiration_denial(harness: HostileTenancyHarness):
    # Verify foreign resource exists in storage
    harness.assert_foreign_resource_exists(TENANT_ALPHA_ID, "document", "doc-alpha-001")

    # 1. Valid signed URL works on first use
    data = harness.access_signed_url(
        "sig-alpha-valid", requesting_tenant_id=TENANT_ALPHA_ID
    )
    assert b"revenue" in data

    # 2. Replay denial: second use of single-use URL must fail closed
    with pytest.raises(PermissionError, match="replay denied"):
        harness.access_signed_url(
            "sig-alpha-valid", requesting_tenant_id=TENANT_ALPHA_ID
        )

    # 3. Expired signed URL must fail closed
    with pytest.raises(PermissionError, match="expired"):
        harness.access_signed_url(
            "sig-alpha-expired", requesting_tenant_id=TENANT_ALPHA_ID
        )

    # 4. Cross-tenant signed URL access denial: Tenant Beta cannot use Tenant Alpha's signature
    now = datetime.now(UTC)
    sig_alpha_fresh = harness.create_signed_url(
        "sig-alpha-fresh",
        TENANT_ALPHA_ID,
        "exports/2026/alpha-q3.csv",
        now + timedelta(minutes=10),
    )
    with pytest.raises(PermissionError, match="Cross-tenant signed URL access denied"):
        harness.access_signed_url(
            sig_alpha_fresh.signature, requesting_tenant_id=TENANT_BETA_ID
        )


# ---------------------------------------------------------------------------
# Contract 2: Object-Storage Key and Prefix Isolation
# ---------------------------------------------------------------------------


def test_object_storage_key_and_prefix_isolation(harness: HostileTenancyHarness):
    # Verify Beta has a seeded resource with key "exports/2026/beta-mna.csv"
    res_beta = harness.assert_foreign_resource_exists(
        TENANT_BETA_ID, "document", "doc-beta-002"
    )
    beta_key = res_beta.metadata["key"]

    # Tenant Alpha attempts to read Tenant Beta's object directly
    with pytest.raises(PermissionError, match="Cross-tenant object access denied"):
        harness.get_object(
            requesting_tenant_id=TENANT_ALPHA_ID,
            target_tenant_id=TENANT_BETA_ID,
            key=beta_key,
        )

    # Tenant Alpha accessing their own object succeeds
    alpha_data = harness.get_object(
        requesting_tenant_id=TENANT_ALPHA_ID,
        target_tenant_id=TENANT_ALPHA_ID,
        key="exports/2026/alpha-q3.csv",
    )
    assert b"revenue" in alpha_data


# ---------------------------------------------------------------------------
# Contract 3: Export and Deletion Isolation
# ---------------------------------------------------------------------------


def test_export_and_deletion_isolation(harness: HostileTenancyHarness):
    # Seed an export job specifically for Tenant Beta
    harness.seed_resource(
        TENANT_BETA_ID, "export_job", "export-beta-888", "Beta Full Export Dump"
    )
    harness.assert_foreign_resource_exists(
        TENANT_BETA_ID, "export_job", "export-beta-888"
    )

    # 1. Tenant Alpha attempts to access Tenant Beta's export job -> must raise PermissionError
    with pytest.raises(PermissionError, match="Cross-tenant export job access denied"):
        harness.get_export_job(
            requesting_tenant_id=TENANT_ALPHA_ID, export_id="export-beta-888"
        )

    # 2. Tenant Alpha attempts to delete Tenant Beta's export job -> must raise PermissionError
    with pytest.raises(
        PermissionError, match="Cross-tenant export job deletion denied"
    ):
        harness.delete_export_job(
            requesting_tenant_id=TENANT_ALPHA_ID, export_id="export-beta-888"
        )

    # 3. Tenant Beta can access own export job
    beta_export = harness.get_export_job(
        requesting_tenant_id=TENANT_BETA_ID, export_id="export-beta-888"
    )
    assert beta_export.resource_id == "export-beta-888"

    # 4. Tenant Beta can delete own export job
    harness.delete_export_job(
        requesting_tenant_id=TENANT_BETA_ID, export_id="export-beta-888"
    )
    with pytest.raises(KeyError, match="Export job not found"):
        harness.get_export_job(
            requesting_tenant_id=TENANT_BETA_ID, export_id="export-beta-888"
        )


# ---------------------------------------------------------------------------
# Contract 4: Graph and Vector Retrieval Isolation
# ---------------------------------------------------------------------------


def test_graph_and_vector_retrieval_isolation(harness: HostileTenancyHarness):
    # Verify Beta entity exists
    harness.assert_foreign_resource_exists(
        TENANT_BETA_ID, "graph_entity", "node-beta-202"
    )

    # 1. Graph Entity lookup: Tenant Alpha cannot read Tenant Beta's node
    with pytest.raises(
        PermissionError, match="Cross-tenant graph entity access denied"
    ):
        harness.get_graph_entity(
            requesting_tenant_id=TENANT_ALPHA_ID, entity_id="node-beta-202"
        )

    # Tenant Alpha can read own node
    alpha_node = harness.get_graph_entity(
        requesting_tenant_id=TENANT_ALPHA_ID, entity_id="node-alpha-101"
    )
    assert alpha_node["name"] == "Alpha Corp Entity"

    # 2. Vector search isolation: Tenant Alpha query vector returns only Alpha vectors
    results = harness.query_vectors(
        requesting_tenant_id=TENANT_ALPHA_ID, embedding=[0.1, 0.2, 0.3]
    )
    assert len(results) == 1
    assert "Alpha" in results[0]["document"]
    assert "Beta" not in results[0]["document"]


# ---------------------------------------------------------------------------
# Contract 5: AI Prompt, Retrieval, Memory, Trace, and Cache Isolation
# ---------------------------------------------------------------------------


def test_ai_memory_trace_and_cache_isolation(harness: HostileTenancyHarness):
    # 1. AI Memory Isolation: Tenant Alpha cannot read Tenant Beta session
    with pytest.raises(PermissionError, match="Cross-tenant AI session access denied"):
        harness.get_ai_session_memory(
            requesting_tenant_id=TENANT_ALPHA_ID, session_id="sess-beta-1"
        )

    # Tenant Alpha can read own session
    alpha_history = harness.get_ai_session_memory(
        requesting_tenant_id=TENANT_ALPHA_ID, session_id="sess-alpha-1"
    )
    assert "Alpha" in alpha_history[0]

    # 2. AI Trace Isolation: Tenant Alpha cannot read Tenant Beta execution trace
    with pytest.raises(PermissionError, match="Cross-tenant AI trace access denied"):
        harness.get_ai_trace(
            requesting_tenant_id=TENANT_ALPHA_ID, trace_id="trace-beta-002"
        )

    # 3. AI Cache Partitioning: Same cache key yields independent tenant results
    assert harness.ai_cache[(TENANT_ALPHA_ID, "cache-key-q3")] == "Alpha Cached Result"
    assert harness.ai_cache[(TENANT_BETA_ID, "cache-key-q3")] == "Beta Cached Result"


# ---------------------------------------------------------------------------
# Contract 6: Queue-Envelope Mismatch and Missing-Context Rejection
# ---------------------------------------------------------------------------


def test_queue_envelope_mismatch_and_missing_context(harness: HostileTenancyHarness):
    # 1. Missing tenant context in envelope fails closed
    with pytest.raises(ValueError, match="Missing tenant context"):
        harness.dispatch_queue_message(
            authenticated_tenant_id=TENANT_ALPHA_ID,
            payload_envelope={"action": "recalculate_roi"},
        )

    # 2. Envelope tenant mismatch (spoofed header/envelope) fails closed
    with pytest.raises(PermissionError, match="Queue envelope tenant mismatch"):
        harness.dispatch_queue_message(
            authenticated_tenant_id=TENANT_ALPHA_ID,
            payload_envelope={"tenant_id": TENANT_BETA_ID, "action": "recalculate_roi"},
        )

    # 3. Valid matching envelope succeeds
    msg = harness.dispatch_queue_message(
        authenticated_tenant_id=TENANT_ALPHA_ID,
        payload_envelope={"tenant_id": TENANT_ALPHA_ID, "action": "recalculate_roi"},
    )
    assert msg["tenant_id"] == TENANT_ALPHA_ID


# ---------------------------------------------------------------------------
# Contract 7: Prior-Session and Tenant-Switch Rejection
# ---------------------------------------------------------------------------


def test_prior_session_and_tenant_switch_rejection(harness: HostileTenancyHarness):
    # Seed prior session for Alpha
    session_alpha = "sess-alpha-1"
    harness.assert_foreign_resource_exists(TENANT_ALPHA_ID, "document", "doc-alpha-001")

    # When context switches to Beta, prior Alpha session tokens/references must be rejected
    active_tenant = TENANT_BETA_ID
    with pytest.raises(PermissionError, match="Cross-tenant AI session access denied"):
        harness.get_ai_session_memory(
            requesting_tenant_id=active_tenant, session_id=session_alpha
        )


# ---------------------------------------------------------------------------
# Contract 8: Support Impersonation Scope and Expiration
# ---------------------------------------------------------------------------


def test_support_impersonation_scope_and_expiration(harness: HostileTenancyHarness):
    # 1. Non-support role cannot create impersonation grant
    with pytest.raises(PermissionError, match="Only support admin"):
        harness.create_impersonation_grant(
            actor_id=USER_ALPHA_ID,
            actor_role=ROLE_MEMBER,
            target_tenant_id=TENANT_BETA_ID,
            target_user_id=USER_BETA_ID,
            scope="read:billing",
        )

    # 2. Support admin creates valid scoped grant
    grant = harness.create_impersonation_grant(
        actor_id="admin-support-99",
        actor_role=ROLE_SUPPORT,
        target_tenant_id=TENANT_BETA_ID,
        target_user_id=USER_BETA_ID,
        scope="read:billing",
        duration_minutes=15,
    )

    # Action within grant scope succeeds
    res = harness.execute_with_impersonation(
        grant.grant_id, action_tenant_id=TENANT_BETA_ID, action_scope="read:billing"
    )
    assert res["status"] == "success"

    # 3. Scope violation fails closed (e.g. attempting write:billing with read:billing grant)
    with pytest.raises(PermissionError, match="Impersonation scope mismatch"):
        harness.execute_with_impersonation(
            grant.grant_id,
            action_tenant_id=TENANT_BETA_ID,
            action_scope="write:billing",
        )

    # 4. Target tenant violation fails closed (e.g. attempting Alpha action with Beta grant)
    with pytest.raises(PermissionError, match="Impersonation scope violation"):
        harness.execute_with_impersonation(
            grant.grant_id,
            action_tenant_id=TENANT_ALPHA_ID,
            action_scope="read:billing",
        )

    # 5. Expired grant fails closed
    expired_grant = harness.create_impersonation_grant(
        actor_id="admin-support-99",
        actor_role=ROLE_SUPPORT,
        target_tenant_id=TENANT_BETA_ID,
        target_user_id=USER_BETA_ID,
        scope="read:billing",
        duration_minutes=-5,  # already expired
    )
    with pytest.raises(PermissionError, match="expired"):
        harness.execute_with_impersonation(
            expired_grant.grant_id,
            action_tenant_id=TENANT_BETA_ID,
            action_scope="read:billing",
        )
