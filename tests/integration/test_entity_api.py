"""Integration tests for Entity Browser canonical API.

Tests the /v1/entities endpoints with comprehensive coverage of:
- List entities with filtering
- Get entity detail
- Pagination
- Edge cases

Note: These tests require Neo4j. When Neo4j is unavailable, they are skipped.
"""

import importlib.util
import os

import pytest

# neo4j driver is a production dep (layer3-knowledge). Tests are infra-gated:
# skip locally when the driver is absent, fail in CI where it must be present.
_neo4j_missing = importlib.util.find_spec("neo4j") is None
if _neo4j_missing and os.getenv("CI") == "true":
    pytest.fail("neo4j driver not installed in CI — add neo4j to layer3-knowledge[dev]")

pytestmark = pytest.mark.skipif(
    _neo4j_missing,
    reason="neo4j driver not installed — optional infra dep (layer3-knowledge[dev])",
)


class TestEntityListAPI:
    """Tests for GET /v1/entities endpoint."""

    @pytest.fixture
    async def neo4j_test_data(self, neo4j_driver):
        """Create test entities and clean up after test."""
        entities = []
        
        # Create test entities with diverse properties
        test_entities = [
            {
                "id": "test-cap-001",
                "name": "AI Analytics Engine",
                "entity_type": "Capability",
                "domain": "Finance",
                "status": "validated",
                "confidence": 0.94,
                "description": "AI-powered predictive analytics",
                "source_name": "acmecorp.com",
            },
            {
                "id": "test-cap-002", 
                "name": "Cloud Infrastructure",
                "entity_type": "Capability",
                "domain": "IT",
                "status": "pending",
                "confidence": 0.75,
                "description": "Cloud-native infrastructure platform",
                "source_name": "internal",
            },
            {
                "id": "test-uc-001",
                "name": "Customer Onboarding",
                "entity_type": "UseCase",
                "domain": "Finance",
                "status": "draft",
                "confidence": 0.45,
                "description": "Streamlined customer onboarding flow",
                "source_name": "survey-data",
            },
            {
                "id": "test-per-001",
                "name": "CFO Persona",
                "entity_type": "Persona",
                "domain": "Finance",
                "status": "validated",
                "confidence": 0.92,
                "description": "Chief Financial Officer persona",
                "source_name": "interviews",
            },
        ]
        
        async with neo4j_driver.session() as session:
            for entity in test_entities:
                await session.run(
                    """
                    CREATE (e:Entity {
                        id: $id,
                        name: $name,
                        entity_type: $entity_type,
                        domain: $domain,
                        status: $status,
                        confidence: $confidence,
                        description: $description,
                        source_name: $source_name,
                        updated_at: datetime(),
                        created_at: datetime()
                    })
                    """,
                    entity
                )
                entities.append(entity["id"])
        
        yield entities
        
        # Cleanup
        async with neo4j_driver.session() as session:
            await session.run(
                "MATCH (e:Entity) WHERE e.id IN $ids DELETE e",
                {"ids": entities}
            )

    async def test_list_entities_no_filters(self, client, neo4j_test_data):
        """Test basic entity listing without filters."""
        response = await client.get("/v1/entities")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "total_count" in data
        assert "filtered_count" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data
        assert "available_domains" in data
        assert "available_sources" in data
        
        # Verify default pagination
        assert data["limit"] == 25  # Default limit
        assert data["offset"] == 0
        
        # Verify entity shape
        if data["results"]:
            entity = data["results"][0]
            assert "id" in entity
            assert "name" in entity
            assert "entity_type" in entity
            assert "domain" in entity
            assert "status" in entity
            assert "confidence" in entity
            assert "confidence_label" in entity
            assert "updated_at" in entity
            assert "source_name" in entity

    async def test_list_entities_filter_by_domain(self, client, neo4j_test_data):
        """Test filtering entities by domain."""
        response = await client.get("/v1/entities?domains=Finance")
        assert response.status_code == 200
        
        data = response.json()
        for entity in data["results"]:
            assert entity["domain"] == "Finance"
        
        # Should include Finance entities
        finance_entities = [e for e in data["results"] if e["domain"] == "Finance"]
        assert len(finance_entities) > 0

    async def test_list_entities_filter_by_status(self, client, neo4j_test_data):
        """Test filtering entities by status."""
        response = await client.get("/v1/entities?statuses=validated")
        assert response.status_code == 200
        
        data = response.json()
        for entity in data["results"]:
            assert entity["status"] == "validated"

    async def test_list_entities_filter_by_type(self, client, neo4j_test_data):
        """Test filtering entities by entity type."""
        response = await client.get("/v1/entities?entity_types=Capability")
        assert response.status_code == 200
        
        data = response.json()
        for entity in data["results"]:
            assert entity["entity_type"] == "Capability"

    async def test_list_entities_filter_by_confidence_range(self, client, neo4j_test_data):
        """Test filtering entities by confidence range."""
        response = await client.get("/v1/entities?min_confidence=0.8&max_confidence=1.0")
        assert response.status_code == 200
        
        data = response.json()
        for entity in data["results"]:
            assert 0.8 <= entity["confidence"] <= 1.0

    async def test_list_entities_filter_combined(self, client, neo4j_test_data):
        """Test combining multiple filters with AND logic."""
        response = await client.get(
            "/v1/entities?domains=Finance&statuses=validated&entity_types=Capability"
        )
        assert response.status_code == 200
        
        data = response.json()
        for entity in data["results"]:
            assert entity["domain"] == "Finance"
            assert entity["status"] == "validated"
            assert entity["entity_type"] == "Capability"

    async def test_list_entities_pagination(self, client, neo4j_test_data):
        """Test pagination with limit and offset."""
        # First page
        response = await client.get("/v1/entities?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 2
        assert data["limit"] == 2
        assert data["offset"] == 0
        
        # Second page
        if data["has_more"]:
            response2 = await client.get("/v1/entities?limit=2&offset=2")
            data2 = response2.json()
            assert data2["offset"] == 2
            # Results should differ
            if data["results"] and data2["results"]:
                assert data["results"][0]["id"] != data2["results"][0]["id"]

    async def test_list_entities_sorting(self, client, neo4j_test_data):
        """Test sorting by different fields."""
        # Sort by name ascending
        response = await client.get("/v1/entities?sort_by=name&sort_order=asc")
        assert response.status_code == 200
        
        # Sort by confidence descending  
        response = await client.get("/v1/entities?sort_by=confidence&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        
        if len(data["results"]) >= 2:
            # Verify descending order
            confidences = [e["confidence"] for e in data["results"]]
            assert confidences == sorted(confidences, reverse=True)

    async def test_list_entities_search_text(self, client, neo4j_test_data):
        """Test text search across entity fields."""
        response = await client.get("/v1/entities?search_text=AI")
        assert response.status_code == 200
        
        data = response.json()
        # Should find entities matching "AI" in name or description
        found = any("AI" in e["name"] or (e.get("description") and "AI" in e["description"])
                    for e in data["results"])
        assert found, "Should find entities matching search text"

    async def test_list_entities_empty_result(self, client):
        """Test empty result set handling."""
        response = await client.get("/v1/entities?domains=NonExistentDomain")
        assert response.status_code == 200
        
        data = response.json()
        assert data["results"] == []
        assert data["total_count"] >= 0
        assert data["filtered_count"] == 0
        assert data["has_more"] is False

    async def test_list_entities_pagination_limits(self, client):
        """Test pagination limits are enforced."""
        # Test max limit exceeded
        response = await client.get("/v1/entities?limit=200")
        assert response.status_code == 422  # Validation error
        
        # Test negative offset
        response = await client.get("/v1/entities?offset=-1")
        assert response.status_code == 422


class TestEntityDetailAPI:
    """Tests for GET /v1/entities/{id} endpoint."""

    @pytest.fixture
    async def test_entity_with_relationships(self, neo4j_driver):
        """Create entity with relationships for detail testing."""
        entity_id = "test-detail-001"
        related_id = "test-detail-002"
        
        async with neo4j_driver.session() as session:
            # Create main entity
            await session.run(
                """
                CREATE (e:Entity {
                    id: $id,
                    name: "Test Entity",
                    entity_type: "Capability",
                    domain: "Finance",
                    status: "validated",
                    confidence: 0.9,
                    description: "Test entity for detail view",
                    source_name: "test",
                    updated_at: datetime(),
                    created_at: datetime()
                })
                """,
                {"id": entity_id}
            )
            
            # Create related entity
            await session.run(
                """
                CREATE (r:Entity {
                    id: $id,
                    name: "Related Entity",
                    entity_type: "UseCase",
                    domain: "Finance",
                    status: "validated",
                    confidence: 0.85,
                    source_name: "test"
                })
                """,
                {"id": related_id}
            )
            
            # Create relationship
            await session.run(
                """
                MATCH (e:Entity {id: $entity_id}), (r:Entity {id: $related_id})
                CREATE (e)-[:ENABLES {confidence: 0.9}]->(r)
                """,
                {"entity_id": entity_id, "related_id": related_id}
            )
        
        yield entity_id
        
        # Cleanup
        async with neo4j_driver.session() as session:
            await session.run(
                "MATCH (e:Entity) WHERE e.id IN $ids DETACH DELETE e",
                {"ids": [entity_id, related_id]}
            )

    async def test_get_entity_detail_success(self, client, test_entity_with_relationships):
        """Test successful entity detail retrieval."""
        entity_id = test_entity_with_relationships
        response = await client.get(f"/v1/entities/{entity_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all EntitySummary fields present
        assert data["id"] == entity_id
        assert "name" in data
        assert "entity_type" in data
        assert "domain" in data
        assert "status" in data
        assert "confidence" in data
        assert "confidence_label" in data
        assert "updated_at" in data
        assert "source_name" in data
        
        # Verify EntityDetail extended fields
        assert "created_at" in data
        assert "provenance" in data
        assert "relationships" in data
        assert "properties" in data

    async def test_get_entity_detail_relationships(self, client, test_entity_with_relationships):
        """Test that relationships are correctly included."""
        entity_id = test_entity_with_relationships
        response = await client.get(f"/v1/entities/{entity_id}")
        assert response.status_code == 200
        
        data = response.json()
        relationships = data["relationships"]
        
        assert "total_count" in relationships
        assert "incoming" in relationships
        assert "outgoing" in relationships
        
        # Should have outgoing relationship
        assert relationships["total_count"] > 0

    async def test_get_entity_detail_not_found(self, client):
        """Test 404 response for non-existent entity."""
        response = await client.get("/v1/entities/non-existent-id-12345")
        assert response.status_code == 404


class TestEntityQueryAPI:
    """Tests for POST /v1/entities/query endpoint."""

    async def test_post_entities_query(self, client):
        """Test advanced filtering via POST request."""
        query = {
            "search_text": "AI",
            "entity_types": ["Capability"],
            "domains": ["Finance"],
            "min_confidence": 0.8,
            "limit": 10
        }
        
        response = await client.post("/v1/entities/query", json=query)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data


class TestContractValidation:
    """Tests for API contract shape validation."""

    def test_entity_summary_schema(self):
        """Verify EntitySummary model structure."""
        from src.api.models import EntitySummary
        
        # Required fields
        required = ["id", "name", "entity_type", "domain", "status", 
                    "confidence", "confidence_label", "updated_at"]
        
        for field in required:
            assert hasattr(EntitySummary, field), f"EntitySummary missing {field}"

    def test_entity_detail_schema(self):
        """Verify EntityDetail model structure."""
        from src.api.models import EntityDetail
        
        # Extended fields
        extended = ["created_at", "provenance", "relationships", "properties"]
        
        for field in extended:
            assert hasattr(EntityDetail, field), f"EntityDetail missing {field}"

    def test_entity_status_enum_values(self):
        """Verify status enum contains expected values."""
        from src.api.models import EntityStatus
        
        expected = ["validated", "pending", "draft", "deprecated"]
        for status in expected:
            assert status in EntityStatus.__args__, f"Missing status: {status}"
