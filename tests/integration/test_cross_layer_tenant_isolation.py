"""
Cross-Layer Tenant Boundary Smoke Tests (Task 4).

End-to-end tests verifying tenant isolation across all layers:
- L1 (Ingestion) → L2 (Extraction) → L3 (Knowledge) → L4 (Agents)
- PostgreSQL RLS enforcement
- Neo4j tenant filtering
- WebSocket tenant propagation
- Background job tenant context
- Cross-tenant access prevention

These tests run against live services in integration environment.
"""

import asyncio
from datetime import datetime
from uuid import uuid4

import httpx
import pytest
import websockets
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# ═══════════════════════════════════════════════════════════════════════════
# Test Configuration
# ═══════════════════════════════════════════════════════════════════════════

L1_BASE_URL = "http://localhost:8001"
L2_BASE_URL = "http://localhost:8002"
L3_BASE_URL = "http://localhost:8003"
L4_BASE_URL = "http://localhost:8004"

POSTGRES_URL = "postgresql+asyncpg://test:test@localhost:5432/fabric_test"
NEO4J_URL = "bolt://localhost:7687"


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def tenant_a_token(jwt_encode):
    """JWT token for tenant A signed with test auth config."""
    return jwt_encode(tenant_id="00000000-0000-0000-0000-0000000000a1", user_id="integration-user-a")


@pytest.fixture
def tenant_b_token(jwt_encode):
    """JWT token for tenant B signed with test auth config."""
    return jwt_encode(tenant_id="00000000-0000-0000-0000-0000000000b2", user_id="integration-user-b")


@pytest.fixture
async def db_session():
    """PostgreSQL async session."""
    engine = create_async_engine(POSTGRES_URL)
    async with engine.begin() as conn:
        session = AsyncSession(bind=conn)
        yield session
        await session.close()
    await engine.dispose()


@pytest.fixture
async def http_client():
    """Async HTTP client."""
    async with httpx.AsyncClient() as client:
        yield client


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: L1 → L2 → L3 → L4 Data Flow
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossLayerTenantIsolation:
    """End-to-end tenant isolation tests across all layers."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_l1_to_l4_tenant_data_flow(
        self,
        http_client: httpx.AsyncClient,
        tenant_a_token: str,
    ):
        """Verify tenant data flows correctly from L1 through L4.
        
        Flow:
        1. L1: Ingest document for tenant A
        2. L2: Extract entities from document
        3. L3: Store entities in knowledge graph
        4. L4: Query entities via agent
        
        Assertion: All layers maintain tenant_id correctly
        """
        tenant_id = str(uuid4())
        document_id = str(uuid4())
        
        # Step 1: L1 - Ingest document
        ingest_response = await http_client.post(
            f"{L1_BASE_URL}/v1/documents/ingest",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={
                "document_id": document_id,
                "content": "Test document for tenant isolation",
                "source": "test",
            },
        )
        assert ingest_response.status_code == 201
        
        # Step 2: L2 - Trigger extraction
        extraction_response = await http_client.post(
            f"{L2_BASE_URL}/v1/extraction/extract",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={"document_id": document_id},
        )
        assert extraction_response.status_code == 200
        extraction_job_id = extraction_response.json()["job_id"]
        
        # Wait for extraction to complete
        await asyncio.sleep(5)
        
        # Step 3: L3 - Verify entities stored
        entities_response = await http_client.get(
            f"{L3_BASE_URL}/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            params={"source_document_id": document_id},
        )
        assert entities_response.status_code == 200
        entities = entities_response.json()["entities"]
        assert len(entities) > 0
        
        # Verify all entities have correct tenant_id
        for entity in entities:
            assert entity["tenant_id"] == tenant_id
        
        # Step 4: L4 - Query via agent
        agent_response = await http_client.post(
            f"{L4_BASE_URL}/v1/agents/query",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={
                "query": f"Find entities from document {document_id}",
                "agent_type": "search",
            },
        )
        assert agent_response.status_code == 200
        agent_results = agent_response.json()["results"]
        
        # Verify agent only returns tenant A's entities
        for result in agent_results:
            assert result["tenant_id"] == tenant_id
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cross_tenant_data_leakage_prevention(
        self,
        http_client: httpx.AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
    ):
        """Verify tenant B cannot access tenant A's data.
        
        Scenario:
        1. Tenant A creates entity
        2. Tenant B attempts to read entity by ID
        3. Assertion: 404 or 403, not 200 with data
        """
        # Tenant A creates entity
        entity_response_a = await http_client.post(
            f"{L3_BASE_URL}/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={
                "name": "Tenant A Secret Entity",
                "entity_type": "Organization",
            },
        )
        assert entity_response_a.status_code == 201
        entity_id = entity_response_a.json()["id"]
        
        # Tenant B attempts to read entity
        entity_response_b = await http_client.get(
            f"{L3_BASE_URL}/v1/entities/{entity_id}",
            headers={"Authorization": f"Bearer {tenant_b_token}"},
        )
        
        # Should return 404 (not found) or 403 (forbidden), never 200
        assert entity_response_b.status_code in (403, 404)
        
        # Verify no data leaked in error response
        if entity_response_b.status_code == 404:
            assert "Secret Entity" not in entity_response_b.text


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: PostgreSQL RLS Enforcement
# ═══════════════════════════════════════════════════════════════════════════

class TestPostgreSQLRLSEnforcement:
    """Verify PostgreSQL Row-Level Security policies enforce tenant isolation."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rls_prevents_cross_tenant_reads(self, db_session: AsyncSession):
        """Verify RLS policies prevent reading other tenant's rows."""
        tenant_a_id = uuid4()
        tenant_b_id = uuid4()
        
        # Insert data for both tenants
        await db_session.execute(
            text("""
                INSERT INTO documents (id, tenant_id, content, created_at)
                VALUES 
                    (:id_a, :tenant_a, 'Tenant A document', NOW()),
                    (:id_b, :tenant_b, 'Tenant B document', NOW())
            """),
            {
                "id_a": uuid4(),
                "tenant_a": tenant_a_id,
                "id_b": uuid4(),
                "tenant_b": tenant_b_id,
            },
        )
        await db_session.commit()
        
        # Set tenant context to tenant A
        await db_session.execute(
            text("SET app.current_tenant = :tenant_id"),
            {"tenant_id": str(tenant_a_id)},
        )
        
        # Query documents - should only see tenant A's
        result = await db_session.execute(text("SELECT content FROM documents"))
        rows = result.fetchall()
        
        assert len(rows) == 1
        assert rows[0][0] == "Tenant A document"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rls_prevents_cross_tenant_updates(self, db_session: AsyncSession):
        """Verify RLS policies prevent updating other tenant's rows."""
        tenant_a_id = uuid4()
        tenant_b_id = uuid4()
        doc_b_id = uuid4()
        
        # Insert document for tenant B
        await db_session.execute(
            text("""
                INSERT INTO documents (id, tenant_id, content, created_at)
                VALUES (:id, :tenant_id, 'Original content', NOW())
            """),
            {"id": doc_b_id, "tenant_id": tenant_b_id},
        )
        await db_session.commit()
        
        # Set tenant context to tenant A
        await db_session.execute(
            text("SET app.current_tenant = :tenant_id"),
            {"tenant_id": str(tenant_a_id)},
        )
        
        # Attempt to update tenant B's document
        result = await db_session.execute(
            text("""
                UPDATE documents 
                SET content = 'Hacked content'
                WHERE id = :doc_id
            """),
            {"doc_id": doc_b_id},
        )
        
        # Should update 0 rows
        assert result.rowcount == 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_rls_prevents_cross_tenant_deletes(self, db_session: AsyncSession):
        """Verify RLS policies prevent deleting other tenant's rows."""
        tenant_a_id = uuid4()
        tenant_b_id = uuid4()
        doc_b_id = uuid4()
        
        # Insert document for tenant B
        await db_session.execute(
            text("""
                INSERT INTO documents (id, tenant_id, content, created_at)
                VALUES (:id, :tenant_id, 'To be protected', NOW())
            """),
            {"id": doc_b_id, "tenant_id": tenant_b_id},
        )
        await db_session.commit()
        
        # Set tenant context to tenant A
        await db_session.execute(
            text("SET app.current_tenant = :tenant_id"),
            {"tenant_id": str(tenant_a_id)},
        )
        
        # Attempt to delete tenant B's document
        result = await db_session.execute(
            text("DELETE FROM documents WHERE id = :doc_id"),
            {"doc_id": doc_b_id},
        )
        
        # Should delete 0 rows
        assert result.rowcount == 0


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Neo4j Tenant Filtering
# ═══════════════════════════════════════════════════════════════════════════

class TestNeo4jTenantFiltering:
    """Verify Neo4j queries enforce tenant filtering."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_neo4j_entity_queries_filtered_by_tenant(
        self,
        http_client: httpx.AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
    ):
        """Verify Neo4j entity queries only return tenant's data."""
        # Tenant A creates entity
        entity_a = await http_client.post(
            f"{L3_BASE_URL}/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={"name": "Tenant A Entity", "entity_type": "Person"},
        )
        assert entity_a.status_code == 201
        
        # Tenant B creates entity with same name
        entity_b = await http_client.post(
            f"{L3_BASE_URL}/v1/entities",
            headers={"Authorization": f"Bearer {tenant_b_token}"},
            json={"name": "Tenant A Entity", "entity_type": "Person"},
        )
        assert entity_b.status_code == 201
        
        # Tenant A searches - should only see their entity
        search_a = await http_client.get(
            f"{L3_BASE_URL}/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            params={"name": "Tenant A Entity"},
        )
        assert search_a.status_code == 200
        results_a = search_a.json()["entities"]
        
        assert len(results_a) == 1
        assert results_a[0]["id"] == entity_a.json()["id"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_neo4j_relationship_queries_filtered_by_tenant(
        self,
        http_client: httpx.AsyncClient,
        tenant_a_token: str,
    ):
        """Verify Neo4j relationship traversal respects tenant boundaries."""
        # Create two entities for tenant A
        entity1 = await http_client.post(
            f"{L3_BASE_URL}/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={"name": "Entity 1", "entity_type": "Person"},
        )
        entity2 = await http_client.post(
            f"{L3_BASE_URL}/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={"name": "Entity 2", "entity_type": "Organization"},
        )
        
        entity1_id = entity1.json()["id"]
        entity2_id = entity2.json()["id"]
        
        # Create relationship
        await http_client.post(
            f"{L3_BASE_URL}/v1/relationships",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={
                "source_id": entity1_id,
                "target_id": entity2_id,
                "relationship_type": "WORKS_FOR",
            },
        )
        
        # Query relationships - should only see tenant A's
        relationships = await http_client.get(
            f"{L3_BASE_URL}/v1/entities/{entity1_id}/relationships",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
        )
        
        assert relationships.status_code == 200
        rels = relationships.json()["relationships"]
        
        # All relationships should be within tenant
        for rel in rels:
            assert rel["source_tenant_id"] == rel["target_tenant_id"]


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: WebSocket Tenant Propagation
# ═══════════════════════════════════════════════════════════════════════════

class TestWebSocketTenantPropagation:
    """Verify WebSocket connections maintain tenant context."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_websocket_tenant_isolation(
        self,
        http_client: httpx.AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
    ):
        """Verify dual-tenant WebSocket connections do not leak cross-tenant events."""
        websocket_url = "ws://localhost:8004/v1/agents/stream"
        headers_a = {"Authorization": f"Bearer {tenant_a_token}"}
        headers_b = {"Authorization": f"Bearer {tenant_b_token}"}

        async with (
            websockets.connect(websocket_url, additional_headers=headers_a) as tenant_a_ws,
            websockets.connect(websocket_url, additional_headers=headers_b) as tenant_b_ws,
        ):
            await tenant_a_ws.send('{"type":"subscribe","topic":"entity_updates"}')
            await tenant_b_ws.send('{"type":"subscribe","topic":"entity_updates"}')

            unique_entity_name = f"TenantAOnly_{uuid4().hex[:8]}"
            create_resp = await http_client.post(
                f"{L3_BASE_URL}/v1/entities",
                headers={"Authorization": f"Bearer {tenant_a_token}"},
                json={"name": unique_entity_name, "entity_type": "Organization"},
            )
            assert create_resp.status_code == 201

            tenant_a_event = await asyncio.wait_for(tenant_a_ws.recv(), timeout=5)
            assert unique_entity_name in tenant_a_event

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(tenant_b_ws.recv(), timeout=2)


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Background Job Tenant Context
# ═══════════════════════════════════════════════════════════════════════════

class TestBackgroundJobTenantContext:
    """Verify background jobs maintain tenant context."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_extraction_job_tenant_context(
        self,
        http_client: httpx.AsyncClient,
        tenant_a_token: str,
    ):
        """Verify extraction jobs maintain tenant context."""
        # Trigger extraction job
        job_response = await http_client.post(
            f"{L2_BASE_URL}/v1/extraction/extract",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={"document_id": str(uuid4()), "content": "Test content"},
        )
        assert job_response.status_code == 200
        job_id = job_response.json()["job_id"]
        
        # Wait for job completion
        await asyncio.sleep(5)
        
        # Check job status
        status_response = await http_client.get(
            f"{L2_BASE_URL}/v1/extraction/jobs/{job_id}",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
        )
        assert status_response.status_code == 200
        
        # Verify job has tenant_id
        job_data = status_response.json()
        assert "tenant_id" in job_data
        assert job_data["tenant_id"] is not None


# ═══════════════════════════════════════════════════════════════════════════
# Test Suite: Cross-Tenant Access Prevention
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossTenantAccessPrevention:
    """Verify all cross-tenant access attempts are blocked."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_direct_id_access_blocked(
        self,
        http_client: httpx.AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
    ):
        """Verify direct access by ID is blocked across tenants."""
        # Tenant A creates resource
        resource = await http_client.post(
            f"{L3_BASE_URL}/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={"name": "Secret Resource", "entity_type": "Document"},
        )
        resource_id = resource.json()["id"]
        
        # Tenant B attempts direct access
        access_attempt = await http_client.get(
            f"{L3_BASE_URL}/v1/entities/{resource_id}",
            headers={"Authorization": f"Bearer {tenant_b_token}"},
        )
        
        assert access_attempt.status_code in (403, 404)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_search_does_not_leak_tenant_data(
        self,
        http_client: httpx.AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
    ):
        """Verify search results are tenant-scoped."""
        # Tenant A creates entity with unique name
        unique_name = f"UniqueEntity_{uuid4().hex[:8]}"
        await http_client.post(
            f"{L3_BASE_URL}/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={"name": unique_name, "entity_type": "Person"},
        )
        
        # Tenant B searches for that name
        search = await http_client.get(
            f"{L3_BASE_URL}/v1/entities",
            headers={"Authorization": f"Bearer {tenant_b_token}"},
            params={"query": unique_name},
        )
        
        assert search.status_code == 200
        results = search.json()["entities"]
        
        # Should return 0 results
        assert len(results) == 0
