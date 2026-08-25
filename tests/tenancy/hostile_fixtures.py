"""Two-seeded-tenant hostile harness.

Provides deterministic test fixtures, seeded entities, tokens, signed URLs,
and hostile isolation assert helpers for two real seeded tenants:
- Tenant Alpha (tenant-alpha-001)
- Tenant Beta (tenant-beta-002)

Rule: Every tenant-negative test asserts the foreign resource exists for the
foreign tenant prior to testing hostile access, preventing false positives
from 404-not-found ambiguity.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta


TENANT_ALPHA_ID = "tenant-alpha-001"
TENANT_BETA_ID = "tenant-beta-002"

USER_ALPHA_ID = "user-alpha-101"
USER_BETA_ID = "user-beta-202"

ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
ROLE_SUPPORT = "support_admin"


@dataclass
class SeededResource:
    resource_id: str
    tenant_id: str
    resource_type: str
    content: str
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SignedUrlRecord:
    url_id: str
    tenant_id: str
    object_key: str
    signature: str
    expires_at: datetime
    used: bool = False
    max_uses: int = 1


@dataclass
class ImpersonationGrant:
    grant_id: str
    actor_id: str
    target_tenant_id: str
    target_user_id: str
    scope: str
    expires_at: datetime
    revoked: bool = False


class HostileTenancyHarness:
    """In-memory hostile test harness seeding real resources for Alpha and Beta."""

    def __init__(self) -> None:
        self.tenants = {
            TENANT_ALPHA_ID: {
                "name": "Alpha Corp",
                "slug": "alpha-corp",
                "status": "active",
            },
            TENANT_BETA_ID: {
                "name": "Beta Industries",
                "slug": "beta-ind",
                "status": "active",
            },
        }

        # Seeded resources map: (resource_type, resource_id) -> SeededResource
        self.resources: dict[tuple[str, str], SeededResource] = {}

        # Signed URLs map: signature -> SignedUrlRecord
        self.signed_urls: dict[str, SignedUrlRecord] = {}

        # Object storage map: (tenant_id, prefix_key) -> bytes
        self.object_store: dict[tuple[str, str], bytes] = {}

        # Graph entities map: (tenant_id, entity_id) -> dict
        self.graph_entities: dict[tuple[str, str], dict[str, object]] = {}

        # Vector retrieval store: tenant_id -> list of (vector_id, embedding, document)
        self.vector_store: dict[str, list[dict[str, object]]] = {
            TENANT_ALPHA_ID: [],
            TENANT_BETA_ID: [],
        }

        # AI session memory and cache: (tenant_id, session_id) -> history
        self.ai_sessions: dict[tuple[str, str], list[str]] = {}
        self.ai_cache: dict[tuple[str, str], str] = {}
        self.ai_traces: dict[tuple[str, str], dict[str, object]] = {}

        # Queue envelopes: list of dicts
        self.queue_envelopes: list[dict[str, object]] = []

        # Impersonation grants: grant_id -> ImpersonationGrant
        self.impersonation_grants: dict[str, ImpersonationGrant] = {}

        # Populate initial seeded resources
        self._seed_initial_state()

    def _seed_initial_state(self) -> None:
        # 1. Object storage / documents
        self.seed_resource(
            TENANT_ALPHA_ID,
            "document",
            "doc-alpha-001",
            "Alpha Financial Model Q3",
            {"key": "exports/2026/alpha-q3.csv"},
        )
        self.seed_resource(
            TENANT_BETA_ID,
            "document",
            "doc-beta-002",
            "Beta Acquisition Target List",
            {"key": "exports/2026/beta-mna.csv"},
        )
        self.put_object(TENANT_ALPHA_ID, "exports/2026/alpha-q3.csv", b"revenue,margin\n1000,0.4")
        self.put_object(TENANT_BETA_ID, "exports/2026/beta-mna.csv", b"target,valuation\nsecret,500m")

        # 2. Graph entities
        self.seed_resource(TENANT_ALPHA_ID, "graph_entity", "node-alpha-101", "Alpha Core Node")
        self.seed_resource(TENANT_BETA_ID, "graph_entity", "node-beta-202", "Beta Core Node")
        self.graph_entities[(TENANT_ALPHA_ID, "node-alpha-101")] = {
            "id": "node-alpha-101",
            "tenant_id": TENANT_ALPHA_ID,
            "label": "Company",
            "name": "Alpha Corp Entity",
        }
        self.graph_entities[(TENANT_BETA_ID, "node-beta-202")] = {
            "id": "node-beta-202",
            "tenant_id": TENANT_BETA_ID,
            "label": "Company",
            "name": "Beta Industries Entity",
        }

        # 3. Vector embeddings
        self.vector_store[TENANT_ALPHA_ID].append({
            "id": "vec-alpha-1",
            "embedding": [0.1, 0.2, 0.3],
            "document": "Alpha proprietary algorithm patent details",
        })
        self.vector_store[TENANT_BETA_ID].append({
            "id": "vec-beta-1",
            "embedding": [0.1, 0.2, 0.3],
            "document": "Beta proprietary formula details",
        })

        # 4. AI Sessions, cache & traces
        self.ai_sessions[(TENANT_ALPHA_ID, "sess-alpha-1")] = ["User: summarize Alpha Q3", "Assistant: Here is Alpha Q3 summary"]
        self.ai_sessions[(TENANT_BETA_ID, "sess-beta-1")] = ["User: show Beta executive payroll", "Assistant: Beta payroll data"]
        self.ai_cache[(TENANT_ALPHA_ID, "cache-key-q3")] = "Alpha Cached Result"
        self.ai_cache[(TENANT_BETA_ID, "cache-key-q3")] = "Beta Cached Result"
        self.ai_traces[(TENANT_ALPHA_ID, "trace-alpha-001")] = {"tenant_id": TENANT_ALPHA_ID, "step": "agent_execution", "secrets": "alpha-token"}
        self.ai_traces[(TENANT_BETA_ID, "trace-beta-002")] = {"tenant_id": TENANT_BETA_ID, "step": "agent_execution", "secrets": "beta-token"}

        # 5. Signed URLs
        now = datetime.now(timezone.utc)
        self.create_signed_url("sig-alpha-valid", TENANT_ALPHA_ID, "exports/2026/alpha-q3.csv", now + timedelta(minutes=15))
        self.create_signed_url("sig-alpha-expired", TENANT_ALPHA_ID, "exports/2026/alpha-q3.csv", now - timedelta(minutes=5))
        self.create_signed_url("sig-beta-valid", TENANT_BETA_ID, "exports/2026/beta-mna.csv", now + timedelta(minutes=15))

    def seed_resource(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> SeededResource:
        res = SeededResource(
            resource_id=resource_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            content=content,
            metadata=metadata or {},
        )
        self.resources[(resource_type, resource_id)] = res
        return res

    def assert_foreign_resource_exists(self, foreign_tenant_id: str, resource_type: str, resource_id: str) -> SeededResource:
        key = (resource_type, resource_id)
        if key not in self.resources:
            raise AssertionError(f"Test prerequisite failed: resource ({resource_type}, {resource_id}) does not exist")
        res = self.resources[key]
        if res.tenant_id != foreign_tenant_id:
            raise AssertionError(
                f"Test prerequisite failed: resource ({resource_type}, {resource_id}) belongs to {res.tenant_id}, expected {foreign_tenant_id}"
            )
        return res

    # --- Storage & Signed URLs ---
    def put_object(self, tenant_id: str, key: str, data: bytes) -> None:
        # Enforce tenant-prefix isolation in internal storage
        normalized_key = f"{tenant_id}/{key.lstrip('/')}"
        self.object_store[(tenant_id, key)] = data

    def get_object(self, requesting_tenant_id: str, target_tenant_id: str, key: str) -> bytes:
        if requesting_tenant_id != target_tenant_id:
            raise PermissionError(f"Cross-tenant object access denied: {requesting_tenant_id} -> {target_tenant_id}")
        if (target_tenant_id, key) not in self.object_store:
            raise KeyError(f"Object not found: {key}")
        return self.object_store[(target_tenant_id, key)]

    def create_signed_url(self, signature: str, tenant_id: str, object_key: str, expires_at: datetime) -> SignedUrlRecord:
        record = SignedUrlRecord(
            url_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            object_key=object_key,
            signature=signature,
            expires_at=expires_at,
        )
        self.signed_urls[signature] = record
        return record

    def access_signed_url(self, signature: str, requesting_tenant_id: str | None = None) -> bytes:
        if signature not in self.signed_urls:
            raise PermissionError("Invalid signed URL signature")
        rec = self.signed_urls[signature]
        now = datetime.now(timezone.utc)
        if now > rec.expires_at:
            raise PermissionError("Signed URL has expired")
        if rec.used and rec.max_uses <= 1:
            raise PermissionError("Signed URL replay denied (already used)")
        if requesting_tenant_id and requesting_tenant_id != rec.tenant_id:
            raise PermissionError(f"Cross-tenant signed URL access denied: {requesting_tenant_id} != {rec.tenant_id}")

        rec.used = True
        return self.get_object(rec.tenant_id, rec.tenant_id, rec.object_key)

    # --- Export Jobs & Deletions ---
    def get_export_job(self, requesting_tenant_id: str, export_id: str) -> SeededResource:
        key = ("export_job", export_id)
        if key not in self.resources:
            raise KeyError(f"Export job not found: {export_id}")
        res = self.resources[key]
        if res.tenant_id != requesting_tenant_id:
            raise PermissionError(f"Cross-tenant export job access denied: {requesting_tenant_id} -> {res.tenant_id}")
        return res

    def delete_export_job(self, requesting_tenant_id: str, export_id: str) -> None:
        key = ("export_job", export_id)
        if key not in self.resources:
            raise KeyError(f"Export job not found: {export_id}")
        res = self.resources[key]
        if res.tenant_id != requesting_tenant_id:
            raise PermissionError(f"Cross-tenant export job deletion denied: {requesting_tenant_id} -> {res.tenant_id}")
        del self.resources[key]

    # --- Graph & Vector Isolation ---
    def get_graph_entity(self, requesting_tenant_id: str, entity_id: str) -> dict[str, object]:
        key = (requesting_tenant_id, entity_id)
        if key not in self.graph_entities:
            # Check if entity belongs to another tenant to prove isolation vs 404
            foreign_matches = [e for (t, eid), e in self.graph_entities.items() if eid == entity_id and t != requesting_tenant_id]
            if foreign_matches:
                raise PermissionError(f"Cross-tenant graph entity access denied for entity {entity_id}")
            raise KeyError(f"Graph entity not found: {entity_id}")
        return self.graph_entities[key]

    def query_vectors(self, requesting_tenant_id: str, embedding: list[float], top_k: int = 5) -> list[dict[str, object]]:
        # Hard isolation: only query within requesting_tenant_id partition
        entries = self.vector_store.get(requesting_tenant_id, [])
        return entries[:top_k]

    # --- AI Context, Memory & Trace Isolation ---
    def get_ai_session_memory(self, requesting_tenant_id: str, session_id: str) -> list[str]:
        if (requesting_tenant_id, session_id) not in self.ai_sessions:
            foreign = [s for (t, sid), s in self.ai_sessions.items() if sid == session_id and t != requesting_tenant_id]
            if foreign:
                raise PermissionError(f"Cross-tenant AI session access denied for session {session_id}")
            raise KeyError(f"AI session not found: {session_id}")
        return self.ai_sessions[(requesting_tenant_id, session_id)]

    def get_ai_trace(self, requesting_tenant_id: str, trace_id: str) -> dict[str, object]:
        if (requesting_tenant_id, trace_id) not in self.ai_traces:
            foreign = [tr for (t, tid), tr in self.ai_traces.items() if tid == trace_id and t != requesting_tenant_id]
            if foreign:
                raise PermissionError(f"Cross-tenant AI trace access denied for trace {trace_id}")
            raise KeyError(f"AI trace not found: {trace_id}")
        return self.ai_traces[(requesting_tenant_id, trace_id)]

    # --- Queue Envelopes ---
    def dispatch_queue_message(self, authenticated_tenant_id: str, payload_envelope: dict[str, object]) -> dict[str, object]:
        envelope_tenant = payload_envelope.get("tenant_id")
        if not envelope_tenant:
            raise ValueError("Missing tenant context in queue envelope")
        if envelope_tenant != authenticated_tenant_id:
            raise PermissionError(
                f"Queue envelope tenant mismatch: authenticated={authenticated_tenant_id}, envelope={envelope_tenant}"
            )
        msg_record = {
            "msg_id": str(uuid.uuid4()),
            "tenant_id": authenticated_tenant_id,
            "payload": payload_envelope,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
        }
        self.queue_envelopes.append(msg_record)
        return msg_record

    # --- Impersonation ---
    def create_impersonation_grant(
        self,
        actor_id: str,
        actor_role: str,
        target_tenant_id: str,
        target_user_id: str,
        scope: str,
        duration_minutes: int = 30,
    ) -> ImpersonationGrant:
        if actor_role != ROLE_SUPPORT:
            raise PermissionError("Only support admin role can request tenant impersonation")
        if target_tenant_id not in self.tenants:
            raise ValueError(f"Unknown target tenant: {target_tenant_id}")

        grant = ImpersonationGrant(
            grant_id=f"grant-{uuid.uuid4()}",
            actor_id=actor_id,
            target_tenant_id=target_tenant_id,
            target_user_id=target_user_id,
            scope=scope,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=duration_minutes),
        )
        self.impersonation_grants[grant.grant_id] = grant
        return grant

    def execute_with_impersonation(
        self,
        grant_id: str,
        action_tenant_id: str,
        action_scope: str,
    ) -> dict[str, object]:
        if grant_id not in self.impersonation_grants:
            raise PermissionError("Invalid impersonation grant ID")
        grant = self.impersonation_grants[grant_id]
        if grant.revoked:
            raise PermissionError("Impersonation grant has been revoked")
        now = datetime.now(timezone.utc)
        if now > grant.expires_at:
            raise PermissionError("Impersonation grant has expired")
        if action_tenant_id != grant.target_tenant_id:
            raise PermissionError(
                f"Impersonation scope violation: grant is for {grant.target_tenant_id}, attempted action for {action_tenant_id}"
            )
        if action_scope != grant.scope:
            raise PermissionError(
                f"Impersonation scope mismatch: grant allows '{grant.scope}', requested '{action_scope}'"
            )
        return {
            "status": "success",
            "impersonated_tenant": grant.target_tenant_id,
            "audit_actor": grant.actor_id,
        }
