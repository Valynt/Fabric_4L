#!/usr/bin/env python3
"""
Fabric_4L Production Path Certification Harness

This script implements the `make certify-production-path` target.
It executes a single end-to-end test that proves the complete production path:

1. Starts the canonical topology (6 layers + infra)
2. Authenticates 2 tenants
3. Creates an account
4. Submits a real source
5. Waits for L1 completion
6. Verifies L2 extraction
7. Verifies L3 graph population
8. Executes L4 workflow
9. Verifies L5 schema-valid Ground Truth with evidence
10. Verifies L6 benchmark participation
11. Retrieves value case via public gateway
12. Validates frontend contract
13. Proves cross-tenant isolation
14. Exports evidence manifest tied to commit SHA

The harness must not manually call the next layer to compensate for missing
production handoffs — the system must automatically hand off work between layers
via ratified contracts and events.

Usage:
    python scripts/certify_production_path.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from collections.abc import Awaitable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

import httpx
from value_fabric.shared.models import JSONDict

# ─── Constants ───
REPO_ROOT = Path(__file__).parent.parent
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "certification"
EVIDENCE_DIR = ARTIFACTS_DIR / "evidence"
MANIFEST_PATH = ARTIFACTS_DIR / "certification_manifest.json"

DEFAULT_TIMEOUT = 300  # 5 minutes for full certification

SERVICE_URLS = {
    "l1": os.getenv("LAYER1_API_URL", "http://localhost:8001").rstrip("/"),
    "l2": os.getenv("LAYER2_API_URL", "http://localhost:8002").rstrip("/"),
    "l3": os.getenv("LAYER3_API_URL", "http://localhost:8003").rstrip("/"),
    "l4": os.getenv("LAYER4_API_URL", "http://localhost:8004").rstrip("/"),
    "l5": os.getenv("LAYER5_API_URL", "http://localhost:8005").rstrip("/"),
    "l6": os.getenv("LAYER6_API_URL", "http://localhost:8006").rstrip("/"),
    "gateway": os.getenv("GATEWAY_API_URL", "http://localhost:8000").rstrip("/"),
}

TENANT_HEADER = "X-Tenant-ID"
USER_HEADER = "X-User-ID"
ROLE_HEADER = "X-Role"
SERVICE_AUTH_HEADER = "X-Service-Auth"
SERVICE_AUTH_SECRET = os.getenv("SERVICE_AUTH_SECRET", "release-smoke-service-auth-secret-with-more-than-32-characters")

# ─── Data Classes ───
@dataclass
class CertificationEvidence:
    """Evidence collected during certification."""
    layer: str
    operation: str
    input_data: JSONDict
    output_data: JSONDict
    status: str  # success, failed
    timestamp: str
    duration_ms: float
    tenant_id: str | None = None
    correlation_id: str | None = None

@dataclass
class CertificationResult:
    """Final certification result."""
    commit_sha: str
    timestamp: str
    overall_status: str  # PASS, FAIL
    layers_verified: list[str]
    evidence: list[CertificationEvidence]
    cross_tenant_isolation: bool
    manifest_path: str
    notes: str = ""

@dataclass
class TestContext:
    """Shared test context."""
    tenant_a: str
    tenant_b: str
    user_admin: str
    account_id: str
    source_id: str
    source_version_id: str | None = None
    job_id: str | None = None
    extraction_job_id: str | None = None
    kg_node_ids: list[str] = field(default_factory=list)
    truth_object_ids: list[str] = field(default_factory=list)
    workflow_id: str | None = None
    value_case_id: str | None = None
    benchmark_comparison_id: str | None = None


# ─── Helper Functions ───
def get_commit_sha() -> str:
    """Get the current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, cwd=REPO_ROOT
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"

def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")

def run_cmd(cmd: list[str], cwd: Path = REPO_ROOT, timeout: int = 60, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Run a command and return result."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout, env=merged_env, check=False)

def make_headers(tenant_id: str, user_id: str = "admin", role: str = "super_admin") -> dict[str, str]:
    return {
        TENANT_HEADER: tenant_id,
        USER_HEADER: user_id,
        ROLE_HEADER: role,
        SERVICE_AUTH_HEADER: SERVICE_AUTH_SECRET,
        "Content-Type": "application/json",
    }


# ─── Certification Harness ───
class ProductionPathCertifier:
    """Orchestrates the complete production path certification."""

    def __init__(self, commit_sha: str):
        self.commit_sha = commit_sha
        self.evidence: list[CertificationEvidence] = []
        self.ctx = TestContext(
            tenant_a="cert-tenant-a-" + uuid.uuid4().hex[:8],
            tenant_b="cert-tenant-b-" + uuid.uuid4().hex[:8],
            user_admin="cert-admin",
            account_id="cert-account-" + uuid.uuid4().hex[:8],
            source_id="",
        )
        self.start_time = time.time()

    def record_evidence(self, layer: str, operation: str, input_data: JSONDict, output_data: JSONDict,
                        status: str, duration_ms: float, tenant_id: str | None = None,
                        correlation_id: str | None = None) -> CertificationEvidence:
        ev = CertificationEvidence(
            layer=layer,
            operation=operation,
            input_data=input_data,
            output_data=output_data,
            status=status,
            timestamp=now_iso(),
            duration_ms=duration_ms,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        self.evidence.append(ev)
        return ev

    async def _request(self, layer: str, method: str, path: str,
                       tenant_id: str, json_data: JSONDict | None = None,
                       expected: tuple[int, ...] = (200,)) -> tuple[JSONDict, httpx.Response]:
        url = f"{SERVICE_URLS[layer]}{path}"
        headers = make_headers(tenant_id)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.request(method, url, headers=headers, json=json_data)
            if resp.status_code not in expected:
                raise AssertionError(f"{layer} {method} {path} expected {expected}, got {resp.status_code}: {resp.text[:500]}")
            if resp.content:
                ct = resp.headers.get("content-type", "")
                if "json" in ct:
                    return resp.json(), resp
            return {}, resp

    async def _gateway_request(self, method: str, path: str,
                               tenant_id: str, json_data: JSONDict | None = None,
                               expected: tuple[int, ...] = (200,)) -> tuple[JSONDict, httpx.Response]:
        """Make a request through the public API gateway.

        User-facing operations should be routed through the gateway to ensure
        the public contract is exercised during certification.
        """
        return await self._request("gateway", method, path, tenant_id, json_data, expected)

    # ─── Phase 1: Start canonical topology ───
    async def start_topology(self) -> bool:
        """Start the canonical docker-compose topology."""
        print("🔧 Starting canonical topology...")
        start = time.time()
        try:
            # Required environment variables for docker-compose.full.yml
            compose_env = {
                "GRAFANA_ADMIN_PASSWORD": os.getenv("GRAFANA_ADMIN_PASSWORD", "admin"),
                "POSTGRES_USER": os.getenv("POSTGRES_USER", "postgres"),
                "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
                "REDIS_PASSWORD": os.getenv("REDIS_PASSWORD", "redis"),
                "SECRET_KEY": os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
                "JWT_ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
                "CORS_ORIGINS": os.getenv("CORS_ORIGINS", "http://localhost:3001"),
                "AUTH_PROVIDER": os.getenv("AUTH_PROVIDER", "clerk"),
                "CLERK_ISSUER": os.getenv("CLERK_ISSUER", "https://clerk.example.com"),
                "CLERK_JWT_AUDIENCE": os.getenv("CLERK_JWT_AUDIENCE", "value-fabric"),
                "CLERK_AUTHORIZED_PARTIES": os.getenv("CLERK_AUTHORIZED_PARTIES", "http://localhost:3001"),
                "CLERK_JWKS_URL": os.getenv("CLERK_JWKS_URL", "https://clerk.example.com/.well-known/jwks.json"),
                "CLERK_SECRET_KEY": os.getenv("CLERK_SECRET_KEY", "sk_test_fake"),
                "CLERK_WEBHOOK_SIGNING_SECRET": os.getenv("CLERK_WEBHOOK_SIGNING_SECRET", "whsec_test_dummy_fake"),
                "FABRIC_AUTH_SIGNING_KEY": os.getenv("FABRIC_AUTH_SIGNING_KEY", "dev-signing-key"),
                "FABRIC_AUTH_PUBLIC_KEYS": os.getenv("FABRIC_AUTH_PUBLIC_KEYS", "[]"),
                "FABRIC_AUTH_ISSUER": os.getenv("FABRIC_AUTH_ISSUER", "value-fabric-internal"),
                "BASE_IMAGE": os.getenv("BASE_IMAGE", "python:3.11.11-slim-bookworm"),
                "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "neo4jpassword"),
                "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "fake-key-for-testing"),
                "JWT_SECRET": os.getenv("JWT_SECRET", "dev-jwt-secret-key-change-in-production"),
                "SERVICE_AUTH_SECRET": os.getenv("SERVICE_AUTH_SECRET", "service-auth-secret"),
                "LAYER3_SERVICE_AUTH_SECRET": os.getenv("LAYER3_SERVICE_AUTH_SECRET", "service-auth-secret"),
                "API_KEY_HMAC_SECRET": os.getenv("API_KEY_HMAC_SECRET", "api-key-hmac-secret"),
                "CLERK_PINNED_JWT_PEM": os.getenv("CLERK_PINNED_JWT_PEM", ""),
                "CLERK_WEBHOOK_RATE_LIMIT_PER_MINUTE": os.getenv("CLERK_WEBHOOK_RATE_LIMIT_PER_MINUTE", "100"),
                "FABRIC_AUTH_SIGNING_KID": os.getenv("FABRIC_AUTH_SIGNING_KID", "test-kid"),
                "FABRIC_AUTH_AUDIENCE": os.getenv("FABRIC_AUTH_AUDIENCE", "value-fabric"),
                "FABRIC_AUTH_ENVELOPE_TTL_SECONDS": os.getenv("FABRIC_AUTH_ENVELOPE_TTL_SECONDS", "3600"),
                "LAYER4_DATABASE_URL": os.getenv("LAYER4_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/layer4"),
                "LAYER1_API_URL": os.getenv("LAYER1_API_URL", "http://layer1-ingestion:8000"),
                "LAYER2_API_URL": os.getenv("LAYER2_API_URL", "http://layer2-extraction:8000"),
                "LAYER3_API_URL": os.getenv("LAYER3_API_URL", "http://layer3-knowledge:8001"),
                "LAYER5_API_URL": os.getenv("LAYER5_API_URL", "http://layer5-ground-truth:8005"),
                "LAYER6_API_URL": os.getenv("LAYER6_API_URL", "http://layer6-benchmarks:8006"),
                "GATEWAY_API_URL": os.getenv("GATEWAY_API_URL", "http://api-gateway:8000"),
            }
            # Use the full compose file that includes all 6 layers + infra
            # Need sudo for docker access with -E to preserve env vars
            result = run_cmd([
                "sudo", "-E", "docker", "compose",
                "-f", "infra/compose/docker-compose.full.yml",
                "up", "-d", "--wait"
            ], timeout=300, env=compose_env)
            if result.returncode != 0:
                print(f"❌ Topology start failed: {result.stderr}")
                return False

            # Wait for all services to be healthy
            print("⏳ Waiting for services to be healthy...")
            for layer in ["l1", "l2", "l3", "l4", "l5", "l6", "gateway"]:
                await self.wait_for_service(layer)

            self.record_evidence("infra", "start_topology", {}, {"services": list(SERVICE_URLS.keys())},
                                 "success", (time.time() - start) * 1000)
            print("✅ Topology started")
            return True
        except Exception as e:  # noqa: BLE001
            self.record_evidence("infra", "start_topology", {}, {"error": str(e)},
                                 "failed", (time.time() - start) * 1000)
            return False

    async def wait_for_service(self, layer: str, max_attempts: int = 30, delay_seconds: float = 1.0) -> bool:
        """Wait for a service to be healthy."""
        return await self.wait_for_service_ready(layer, max_attempts, delay_seconds)

    async def wait_for_service_ready(self, layer: str, max_attempts: int = 30, delay_seconds: float = 0.1) -> bool:
        """Wait for a service to report both healthy and ready."""
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    health = await client.get(f"{SERVICE_URLS[layer]}/health")
                    if health.status_code != 200:
                        continue
                    ready = await client.get(f"{SERVICE_URLS[layer]}/ready")
                    if ready.status_code == 200:
                        return True
            except Exception:  # noqa: BLE001
                print(f"⏳ Service {layer} not ready yet (attempt {attempt})")
            await asyncio.sleep(delay_seconds)
        return False

    # ─── Phase 2: Create tenants ───
    async def create_tenants(self) -> bool:
        """Create two tenants for cross-tenant isolation testing."""
        print("👥 Creating tenants...")
        start = time.time()
        try:
            # Create tenant A
            payload_a = {
                "name": f"Certification Tenant A {self.ctx.tenant_a}",
                "slug": self.ctx.tenant_a,
                "settings": {"plan": "enterprise", "certification_run": True},
            }
            body, _ = await self._gateway_request("POST", "/v1/tenants", self.ctx.tenant_a, payload_a, (200, 201))
            self.record_evidence("l4", "create_tenant", payload_a, body, "success",
                                (time.time() - start) * 1000, self.ctx.tenant_a)

            # Create tenant B
            payload_b = {
                "name": f"Certification Tenant B {self.ctx.tenant_b}",
                "slug": self.ctx.tenant_b,
                "settings": {"plan": "enterprise", "certification_run": True},
            }
            body, _ = await self._gateway_request("POST", "/v1/tenants", self.ctx.tenant_b, payload_b, (200, 201))
            self.record_evidence("l4", "create_tenant", payload_b, body, "success",
                                (time.time() - start) * 1000, self.ctx.tenant_b)

            print("✅ Tenants created")
            return True
        except Exception as e:  # noqa: BLE001
            self.record_evidence("l4", "create_tenant", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000)
            return False

    # ─── Phase 3: Create account ───
    async def create_account(self) -> bool:
        """Create an account in tenant A."""
        print("🏢 Creating account...")
        start = time.time()
        try:
            payload = {
                "id": self.ctx.account_id,
                "provider": "salesforce",
                "provider_record_id": self.ctx.account_id,
                "name": "Certification Account",
                "domain": "cert.example.com",
                "industry": "Software",
                "region": "North America",
                "company_size": 1200,
                "owner_id": self.ctx.user_admin,
                "owner_name": "Cert Admin",
                "owner_email": "cert@example.com",
                "stage": "qualified",
                "segment": "enterprise",
            }
            body, _ = await self._gateway_request("POST", "/v1/accounts", self.ctx.tenant_a, payload, (200, 201))
            self.record_evidence("l4", "create_account", payload, body, "success",
                                (time.time() - start) * 1000, self.ctx.tenant_a)
            print("✅ Account created")
            return True
        except Exception as e:  # noqa: BLE001
            self.record_evidence("l4", "create_account", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            return False

    # ─── Phase 4: Submit source (L1 ingestion) ───
    async def submit_source(self) -> bool:
        """Submit a source document for ingestion via L1."""
        print("📄 Submitting source document...")
        start = time.time()
        try:
            payload = {
                "account_id": self.ctx.account_id,
                "source_type": "notes",
                "title": "Certification Discovery Notes",
                "content": "Pipeline conversion improved 11% after guided value discovery. Cost savings of $500K/year confirmed.",
                "external_reference": f"cert-doc-{uuid.uuid4().hex[:8]}",
                "idempotency_key": f"cert-doc-{uuid.uuid4().hex[:8]}",
                "requested_outputs": ["fabric_found_summary"],
                "metadata": {"certification_run": True},
            }
            body, _ = await self._gateway_request("POST", "/api/v1/ingestion/sources", self.ctx.tenant_a, payload, (200, 201, 202))
            source_version_id = body.get("source_version_id")
            if not source_version_id:
                raise AssertionError("Source creation response missing source_version_id")
            self.ctx.source_version_id = str(source_version_id)
            self.ctx.source_id = self.ctx.source_version_id
            self.record_evidence("l1", "create_source", payload, body, "success",
                                (time.time() - start) * 1000, self.ctx.tenant_a)
            print(f"✅ Source submitted: {self.ctx.source_id}")
            return True
        except AssertionError as e:
            self.record_evidence("l1", "create_source", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            raise
        except Exception as e:  # noqa: BLE001
            self.record_evidence("l1", "create_source", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            return False

    # ─── Phase 5: Start ingestion job ───
    async def start_ingestion_job(self) -> bool:
        """Start the L1 ingestion job."""
        print("🚀 Starting ingestion job...")
        start = time.time()
        try:
            payload = {
                "source_version_id": self.ctx.source_id,
                "config": {"extraction_config": {"method": "llm"}},
            }
            body, _ = await self._request("l1", "POST", "/api/v1/ingestion/runs", self.ctx.tenant_a, payload, (200, 201, 202))
            self.ctx.job_id = body.get("run_id") or body.get("id") or ""
            self.record_evidence("l1", "start_ingestion_job", payload, body, "success",
                                (time.time() - start) * 1000, self.ctx.tenant_a)
            print(f"✅ Ingestion job started: {self.ctx.job_id}")
            return True
        except Exception as e:  # noqa: BLE001
            self.record_evidence("l1", "start_ingestion_job", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            return False

    # ─── Phase 6: Wait for L1 completion ───
    async def wait_for_l1_completion(self) -> bool:
        """Wait for L1 ingestion job to complete."""
        print("⏳ Waiting for L1 completion...")
        start = time.time()
        try:
            if not self.ctx.job_id:
                raise ValueError("No job ID")

            for attempt in range(60):  # 5 minutes max
                body, _ = await self._request("l1", "GET", f"/api/v1/ingestion/runs/{self.ctx.job_id}",
                                             self.ctx.tenant_a, expected=(200,))
                status = str(body).lower()
                if "completed" in status or "success" in status:
                    self.record_evidence("l1", "wait_for_completion", {}, body, "success",
                                        (time.time() - start) * 1000, self.ctx.tenant_a)
                    print("✅ L1 ingestion completed")
                    return True
                if "failed" in status or "error" in status:
                    raise AssertionError(f"L1 job failed: {body}")
                await asyncio.sleep(5)

            raise TimeoutError("L1 job did not complete in time")
        except Exception as e:  # noqa: BLE001
            self.record_evidence("l1", "wait_for_completion", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            return False

    # ─── Phase 7: Verify L2 extraction ───
    async def verify_l2_extraction(self, sleep_seconds: float = 5.0) -> bool:
        """Verify L2 extracted entities from the source."""
        print("🔍 Verifying L2 extraction...")
        start = time.time()
        try:
            # Query L2 for extraction jobs related to our source
            body, _ = await self._request("l2", "GET", "/v1/extractions", self.ctx.tenant_a,
                                         expected=(200,))
            # Find our extraction
            extractions = body if isinstance(body, list) else body.get("items", [])
            our_extraction = None
            for ext in extractions:
                if self.ctx.source_id in str(ext):
                    our_extraction = ext
                    break

            if not our_extraction:
                raise AssertionError(
                    f"No extraction found for source_version_id {self.ctx.source_id}"
                )

            self.ctx.extraction_job_id = our_extraction.get("job_id") or our_extraction.get("id")

            # Wait for extraction to complete
            completed = False
            for attempt in range(30):
                body, _ = await self._request("l2", "GET", f"/v1/extractions/{self.ctx.extraction_job_id}",
                                             self.ctx.tenant_a, expected=(200,))
                status = body.get("status", "").lower()
                if status in ("completed", "success"):
                    completed = True
                    break
                if status in ("failed", "error"):
                    raise AssertionError(f"L2 extraction failed: {body}")
                await asyncio.sleep(sleep_seconds)

            if not completed:
                raise AssertionError("L2 extraction timed out without reaching completed status")

            entities = body.get("entities") or body.get("items") or []
            if not entities:
                raise AssertionError("L2 extraction completed but no entities extracted")

            self.record_evidence("l2", "verify_extraction", {}, body, "success",
                                (time.time() - start) * 1000, self.ctx.tenant_a)
            print("✅ L2 extraction verified")
            return True
        except AssertionError as e:
            self.record_evidence("l2", "verify_extraction", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            raise
        except Exception as e:  # noqa: BLE001
            self.record_evidence("l2", "verify_extraction", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            return False

    # ─── Phase 8: Verify L3 graph population ───
    async def verify_l3_graph(self) -> bool:
        """Verify L3 knowledge graph has entities from our source."""
        print("🕸️ Verifying L3 graph population...")
        start = time.time()
        try:
            # Query L3 for entities with our source version ID
            body, _ = await self._request("l3", "GET", "/v1/query/entities",
                                         self.ctx.tenant_a,
                                         expected=(200,))
            entities = body.get("items", body) if isinstance(body, dict) else body
            our_entities = [e for e in entities if self.ctx.source_id in str(e)]

            if not our_entities:
                # Try with source_version_id filter
                body, _ = await self._request("l3", "POST", "/v1/search",
                                             self.ctx.tenant_a,
                                             json_data={"query": self.ctx.source_id, "limit": 10},
                                             expected=(200,))
                entities = body.get("results", body.get("items", []))
                our_entities = [e for e in entities if self.ctx.source_id in str(e)]

            self.ctx.kg_node_ids = [e.get("id") for e in our_entities if e.get("id")]

            self.record_evidence("l3", "verify_graph", {},
                                {"entities_found": len(our_entities), "node_ids": self.ctx.kg_node_ids},
                                "success" if our_entities else "failed",
                                (time.time() - start) * 1000, self.ctx.tenant_a)

            if our_entities:
                print(f"✅ L3 graph populated: {len(our_entities)} entities")
                return True
            else:
                print("❌ L3 graph has no entities from our source")
                return False
        except Exception as e:  # noqa: BLE001
            self.record_evidence("l3", "verify_graph", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            return False

    # ─── Phase 9: Execute L4 workflow ───
    async def execute_l4_workflow(self, sleep_seconds: float = 5.0) -> bool:
        """Execute L4 business case generation workflow."""
        print("🤖 Executing L4 workflow...")
        start = time.time()
        try:
            payload = {
                "workflow_type": "business_case_generation",
                "inputs": {
                    "account_id": self.ctx.account_id,
                    "use_case_ids": ["cost_savings", "efficiency_gain"],
                    "source_version_id": self.ctx.source_id,
                },
            }
            body, _ = await self._gateway_request("POST", "/v1/workflows", self.ctx.tenant_a, payload, (200, 201))
            self.ctx.workflow_id = body.get("workflow_id") or body.get("id") or ""
            if not self.ctx.workflow_id:
                raise AssertionError("L4 workflow submission did not return a workflow_id")

            # Wait for workflow completion (direct layer postcondition inspection)
            terminal = False
            for attempt in range(60):
                body, _ = await self._request("l4", "GET", f"/v1/workflows/{self.ctx.workflow_id}",
                                             self.ctx.tenant_a, expected=(200,))
                status = body.get("status", "").lower()
                if status in ("completed", "success"):
                    terminal = True
                    self.ctx.value_case_id = body.get("value_case_id") or body.get("output", {}).get("value_case_id")
                    break
                if status in ("failed", "error"):
                    raise AssertionError(f"L4 workflow failed: {body}")
                await asyncio.sleep(sleep_seconds)

            if not terminal:
                raise AssertionError("L4 workflow timed out without reaching a terminal status")
            if not self.ctx.value_case_id:
                raise AssertionError(f"L4 workflow completed but no value_case_id produced: {body}")

            self.record_evidence("l4", "execute_workflow", payload, body, "success",
                                (time.time() - start) * 1000, self.ctx.tenant_a,
                                correlation_id=self.ctx.workflow_id)
            print(f"✅ L4 workflow completed: {self.ctx.workflow_id}")
            return True
        except AssertionError as e:
            self.record_evidence("l4", "execute_workflow", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            raise
        except Exception as e:  # noqa: BLE001
            self.record_evidence("l4", "execute_workflow", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            return False

    # ─── Phase 10: Verify L5 Ground Truth ───
    async def verify_l5_ground_truth(self) -> bool:
        """Verify L5 has schema-valid Ground Truth with evidence."""
        print("📋 Verifying L5 Ground Truth...")
        start = time.time()
        try:
            # Query L5 for TruthObjects
            body, _ = await self._request("l5", "GET", "/api/v1/truths",
                                         self.ctx.tenant_a,
                                         expected=(200,))
            truths = body.get("items", body) if isinstance(body, dict) else body

            # Find truths related to our workflow
            our_truths = []
            for t in truths:
                applies_to = t.get("applies_to", {})
                if (applies_to.get("source_version_id") in (self.ctx.source_id, self.ctx.source_version_id) or
                    applies_to.get("workflow_id") == self.ctx.workflow_id):
                    our_truths.append(t)

            self.ctx.truth_object_ids = [t.get("id") for t in our_truths]

            # Verify schema validity and evidence
            valid_truths = []
            for t in our_truths:
                if t.get("status") in ("validated", "approved") and t.get("sources"):
                    valid_truths.append(t)

            if not valid_truths:
                raise AssertionError(
                    f"no validated TruthObjects found for source_version_id={self.ctx.source_id} "
                    f"workflow_id={self.ctx.workflow_id} (validated={len(valid_truths)})"
                )

            self.record_evidence("l5", "verify_ground_truth", {},
                                {"total_truths": len(our_truths), "validated_truths": len(valid_truths),
                                 "truth_ids": self.ctx.truth_object_ids},
                                "success",
                                (time.time() - start) * 1000, self.ctx.tenant_a)

            print(f"✅ L5 Ground Truth verified: {len(valid_truths)} validated truths")
            return True
        except AssertionError as e:
            self.record_evidence("l5", "verify_ground_truth", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            raise
        except Exception as e:  # noqa: BLE001
            self.record_evidence("l5", "verify_ground_truth", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            return False

    # ─── Phase 11: Verify L6 benchmark participation ───
    async def verify_l6_benchmark(self) -> bool:
        """Verify L6 benchmark comparison was performed."""
        print("📊 Verifying L6 benchmark participation...")
        start = time.time()
        try:
            # Query L6 for benchmark comparisons
            body, _ = await self._request("l6", "GET", "/v1/benchmarks/compare",
                                         self.ctx.tenant_a,
                                         expected=(200,))
            comparisons = body.get("items", body) if isinstance(body, dict) else body

            # Find comparisons for our value case
            our_comparisons = [c for c in comparisons
                             if c.get("value_case_id") == self.ctx.value_case_id or
                                c.get("account_id") == self.ctx.account_id]

            if not our_comparisons:
                raise AssertionError(
                    f"no comparisons found for value_case_id={self.ctx.value_case_id}"
                )

            self.record_evidence("l6", "verify_benchmark", {},
                                {"comparisons_found": len(our_comparisons),
                                 "comparison_ids": [c.get("id") for c in our_comparisons]},
                                "success",
                                (time.time() - start) * 1000, self.ctx.tenant_a)

            print(f"✅ L6 benchmark verified: {len(our_comparisons)} comparisons")
            return True
        except AssertionError as e:
            self.record_evidence("l6", "verify_benchmark", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            raise
        except Exception as e:  # noqa: BLE001
            self.record_evidence("l6", "verify_benchmark", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            return False

    # ─── Phase 12: Retrieve value case via gateway ───
    async def retrieve_value_case_via_gateway(self) -> bool:
        """Retrieve the value case via the public gateway."""
        print("🌐 Retrieving value case via gateway...")
        start = time.time()
        try:
            # Use gateway to get the value case
            body, _ = await self._gateway_request("GET",
                                                  f"/v1/accounts/{self.ctx.account_id}/value-cases",
                                                  self.ctx.tenant_a, expected=(200,))

            cases = body.get("items", body) if isinstance(body, dict) else body
            our_case = None
            for c in cases:
                if c.get("account_id") == self.ctx.account_id:
                    our_case = c
                    break

            self.record_evidence("gateway", "retrieve_value_case", {},
                                {"case_found": our_case is not None, "case": our_case},
                                "success" if our_case else "failed",
                                (time.time() - start) * 1000, self.ctx.tenant_a)

            if our_case:
                print("✅ Value case retrieved via gateway")
                return True
            else:
                print("❌ Value case not found via gateway")
                return False
        except Exception as e:  # noqa: BLE001
            self.record_evidence("gateway", "retrieve_value_case", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000, self.ctx.tenant_a)
            return False

    # ─── Phase 13: Validate frontend contract ───
    async def validate_frontend_contract(self) -> bool:
        """Validate the frontend contract matches the gateway."""
        print("🔗 Validating frontend contract...")
        start = time.time()
        try:
            # Check that the frontend's typed client endpoints match gateway routes
            # This is a static check - verify the OpenAPI contract is in sync
            result = run_cmd(["pnpm", "--dir", "apps/web", "run", "typecheck"], timeout=120)
            if result.returncode != 0:
                raise AssertionError(f"Frontend typecheck failed: {result.stderr}")

            self.record_evidence("frontend", "validate_contract", {},
                                {"typecheck": "passed"}, "success",
                                (time.time() - start) * 1000)
            print("✅ Frontend contract validated")
            return True
        except Exception as e:  # noqa: BLE001
            self.record_evidence("frontend", "validate_contract", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000)
            return False

    # ─── Phase 14: Prove cross-tenant isolation ───
    async def prove_cross_tenant_isolation(self) -> bool:
        """Prove tenant B cannot access tenant A's data."""
        print("🔒 Proving cross-tenant isolation...")
        start = time.time()
        try:
            checks: JSONDict = {}

            # Check L4: tenant B cannot see tenant A's account
            try:
                await self._request("l4", "GET", f"/v1/accounts/{self.ctx.account_id}",
                                   self.ctx.tenant_b, expected=(401, 403, 404))
                checks["l4_accounts"] = {"passed": True}
            except AssertionError:
                checks["l4_accounts"] = {"passed": False}

            # Check L4: tenant B cannot see tenant A's workflow
            if self.ctx.workflow_id:
                try:
                    await self._request("l4", "GET", f"/v1/workflows/{self.ctx.workflow_id}",
                                       self.ctx.tenant_b, expected=(401, 403, 404))
                    checks["l4_workflows"] = {"passed": True}
                except AssertionError:
                    checks["l4_workflows"] = {"passed": False}

            # Check L5: tenant B cannot see tenant A's truths
            try:
                body, _ = await self._request("l5", "GET", "/api/v1/truths", self.ctx.tenant_b, expected=(200,))
                items = body.get("items", body) if isinstance(body, dict) else body
                cross_tenant_truth = self._find_cross_tenant_item(items)
                checks["l5_truths"] = {"passed": cross_tenant_truth is None}
            except Exception:  # noqa: BLE001
                checks["l5_truths"] = {"passed": False}

            # Check L3: tenant B cannot query tenant A's entities
            try:
                body, _ = await self._request("l3", "GET", "/v1/query/entities",
                                   self.ctx.tenant_b, expected=(200,))
                items = body.get("items", body) if isinstance(body, dict) else body
                cross_tenant_entity = self._find_cross_tenant_item(items)
                checks["l3_entities"] = {"passed": cross_tenant_entity is None}
            except Exception:  # noqa: BLE001
                checks["l3_entities"] = {"passed": False}

            all_passed = all(c.get("passed", False) for c in checks.values())

            self.record_evidence("security", "cross_tenant_isolation", {},
                                {"checks": checks, "all_passed": all_passed},
                                "success" if all_passed else "failed",
                                (time.time() - start) * 1000)

            if all_passed:
                print("✅ Cross-tenant isolation proven")
            else:
                failed = [name for name, c in checks.items() if not c.get("passed")]
                print(f"❌ Cross-tenant isolation failed: {failed}")
            return all_passed
        except Exception as e:  # noqa: BLE001
            self.record_evidence("security", "cross_tenant_isolation", {}, {"error": str(e)},
                                "failed", (time.time() - start) * 1000)
            return False

    def _find_cross_tenant_item(self, items: object) -> JSONDict | None:
        """Return the first item that appears to belong to tenant A, or None."""
        if not isinstance(items, list):
            return None
        for item in items:
            if not isinstance(item, dict):
                continue
            applies_to = item.get("applies_to", {}) if isinstance(item.get("applies_to"), dict) else {}
            if (applies_to.get("source_version_id") in (self.ctx.source_id, self.ctx.source_version_id) or
                applies_to.get("workflow_id") == self.ctx.workflow_id or
                item.get("source_version_id") in (self.ctx.source_id, self.ctx.source_version_id) or
                item.get("account_id") == self.ctx.account_id):
                return item
        return None

    # ─── Phase 15: Export evidence manifest ───
    def export_manifest(self) -> str:
        """Export the certification manifest."""
        total_duration = time.time() - self.start_time

        result = CertificationResult(
            commit_sha=self.commit_sha,
            timestamp=now_iso(),
            overall_status="PASS" if all(e.status == "success" for e in self.evidence) else "FAIL",
            layers_verified=list({e.layer for e in self.evidence}),
            evidence=self.evidence,
            cross_tenant_isolation=any(e.layer == "security" and e.status == "success" for e in self.evidence),
            manifest_path=str(MANIFEST_PATH),
            notes=f"Total duration: {total_duration:.1f}s. Evidence items: {len(self.evidence)}"
        )

        # Ensure directories exist
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

        # Write manifest
        manifest_data = asdict(result)
        with open(MANIFEST_PATH, "w") as f:
            json.dump(manifest_data, f, indent=2, default=str)

        # Write individual evidence files
        for i, ev in enumerate(self.evidence):
            ev_path = EVIDENCE_DIR / f"{i:03d}_{ev.layer}_{ev.operation}_{ev.timestamp.replace(':', '-')}.json"
            with open(ev_path, "w") as f:
                json.dump(asdict(ev), f, indent=2, default=str)

        print(f"📄 Manifest exported to {MANIFEST_PATH}")
        return str(MANIFEST_PATH)

    # ─── Main orchestration ───
    async def run(self) -> CertificationResult:
        """Run the complete certification."""
        print(f"🚀 Starting Production Path Certification (commit: {self.commit_sha[:8]})")
        print("=" * 60)

        # Phase 1: Start topology
        result = await self._run_phase("Topology start", self.start_topology())
        if result:
            return result

        # Phase 2: Create tenants
        result = await self._run_phase("Tenant creation", self.create_tenants())
        if result:
            return result

        # Phase 3: Create account
        result = await self._run_phase("Account creation", self.create_account())
        if result:
            return result

        # Phase 4: Submit source
        result = await self._run_phase("Source submission", self.submit_source())
        if result:
            return result

        # Phase 5: Start ingestion job
        result = await self._run_phase("Ingestion job start", self.start_ingestion_job())
        if result:
            return result

        # Phase 6: Wait for L1 completion
        result = await self._run_phase("L1 completion", self.wait_for_l1_completion())
        if result:
            return result

        # Phase 7: Verify L2 extraction
        result = await self._run_phase("L2 extraction verification", self.verify_l2_extraction())
        if result:
            return result

        # Phase 8: Verify L3 graph
        result = await self._run_phase("L3 graph verification", self.verify_l3_graph())
        if result:
            return result

        # Phase 9: Execute L4 workflow
        result = await self._run_phase("L4 workflow execution", self.execute_l4_workflow())
        if result:
            return result

        # Phase 10: Verify L5 Ground Truth
        result = await self._run_phase("L5 Ground Truth verification", self.verify_l5_ground_truth())
        if result:
            return result

        # Phase 11: Verify L6 benchmark
        result = await self._run_phase("L6 benchmark verification", self.verify_l6_benchmark())
        if result:
            return result

        # Phase 12: Retrieve value case via gateway
        result = await self._run_phase("Value case retrieval", self.retrieve_value_case_via_gateway())
        if result:
            return result

        # Phase 13: Validate frontend contract
        result = await self._run_phase("Frontend contract validation", self.validate_frontend_contract())
        if result:
            return result

        # Phase 14: Prove cross-tenant isolation
        result = await self._run_phase("Cross-tenant isolation", self.prove_cross_tenant_isolation())
        if result:
            return result

        # Phase 15: Export manifest
        self.export_manifest()

        print("=" * 60)
        print("🎉 CERTIFICATION PASSED")
        print("=" * 60)

        return CertificationResult(
            commit_sha=self.commit_sha,
            timestamp=now_iso(),
            overall_status="PASS",
            layers_verified=list({e.layer for e in self.evidence}),
            evidence=self.evidence,
            cross_tenant_isolation=True,
            manifest_path=str(MANIFEST_PATH),
            notes="All phases completed successfully"
        )

    async def _run_phase(self, phase_name: str, coro: Awaitable[bool]) -> CertificationResult | None:
        """Run a phase and return a failure result if it raises or returns False."""
        try:
            if not await coro:
                return self._fail_result(f"{phase_name} failed")
            return None
        except Exception as e:  # noqa: BLE001
            return self._fail_result(f"{phase_name} failed: {e}")

    def _fail_result(self, reason: str) -> CertificationResult:
        self.export_manifest()
        print(f"❌ CERTIFICATION FAILED: {reason}")
        return CertificationResult(
            commit_sha=self.commit_sha,
            timestamp=now_iso(),
            overall_status="FAIL",
            layers_verified=list({e.layer for e in self.evidence}),
            evidence=self.evidence,
            cross_tenant_isolation=False,
            manifest_path=str(MANIFEST_PATH),
            notes=reason
        )


async def main():
    commit_sha = get_commit_sha()
    certifier = ProductionPathCertifier(commit_sha)
    result = await certifier.run()

    # Print summary
    print("\n📋 CERTIFICATION SUMMARY")
    print(f"  Commit: {result.commit_sha[:8]}")
    print(f"  Status: {result.overall_status}")
    print(f"  Layers: {', '.join(result.layers_verified)}")
    print(f"  Evidence items: {len(result.evidence)}")
    print(f"  Cross-tenant isolation: {'✅' if result.cross_tenant_isolation else '❌'}")
    print(f"  Manifest: {result.manifest_path}")

    # Exit code
    sys.exit(0 if result.overall_status == "PASS" else 1)


if __name__ == "__main__":
    asyncio.run(main())