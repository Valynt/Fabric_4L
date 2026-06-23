"""
Tests for tenant-aware Neo4j query helpers.

Verifies that all query helpers enforce mandatory tenant_id filtering
and prevent cross-tenant data leakage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.db.tenant_queries import (
    get_entity_by_id,
    get_relationships_for_entity,
    search_entities,
    get_entity_context,
    count_entity_relationships,
    update_entity_properties,
    delete_entity,
)
from value_fabric.shared.models.typed_dict import TypedDictModel


class mock_entityResult(TypedDictModel):
    confidence: float
    created_at: str
    entity_type: str
    id: str
    name: str
    tenant_id: str


@pytest.fixture
def mock_session():
    """Create a mock Neo4j async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_entity():
    """Sample entity data."""
    return mock_entityResult.model_validate({
        "id": "entity-123",
        "name": "Test Entity",
        "entity_type": "Capability",
        "tenant_id": "tenant-a",
        "confidence": 0.95,
        "created_at": "2026-04-23T10:00:00Z",
    })


class TestGetEntityById:
    """Tests for get_entity_by_id helper."""
    
    @pytest.mark.asyncio
    async def test_requires_tenant_id(self, mock_session):
        """Verify tenant_id is required."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            await get_entity_by_id(mock_session, entity_id="abc", tenant_id="")
        
        with pytest.raises(ValueError, match="tenant_id is required"):
            await get_entity_by_id(mock_session, entity_id="abc", tenant_id=None)
    
    @pytest.mark.asyncio
    async def test_includes_tenant_id_in_query(self, mock_session, mock_entity):
        """Verify query includes tenant_id predicate."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"entity": mock_entity})
        mock_session.run = AsyncMock(return_value=mock_result)
        
        entity = await get_entity_by_id(
            mock_session, 
            entity_id="entity-123", 
            tenant_id="tenant-a"
        )
        
        # Verify query was called with tenant_id
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        assert "tenant_id: $tenant_id" in query
        assert params["tenant_id"] == "tenant-a"
        assert params["entity_id"] == "entity-123"
        assert entity == mock_entity
    
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_session):
        """Verify returns None when entity not found."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        
        entity = await get_entity_by_id(
            mock_session, 
            entity_id="nonexistent", 
            tenant_id="tenant-a"
        )
        
        assert entity is None
    
    @pytest.mark.asyncio
    async def test_include_properties_flag(self, mock_session, mock_entity):
        """Verify include_properties flag controls properties field."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"entity": mock_entity})
        mock_session.run = AsyncMock(return_value=mock_result)
        
        # With properties
        await get_entity_by_id(
            mock_session, 
            entity_id="entity-123", 
            tenant_id="tenant-a",
            include_properties=True
        )
        query_with_props = mock_session.run.call_args[0][0]
        assert ".properties" in query_with_props
        
        # Without properties
        await get_entity_by_id(
            mock_session, 
            entity_id="entity-123", 
            tenant_id="tenant-a",
            include_properties=False
        )
        query_without_props = mock_session.run.call_args[0][0]
        assert ".properties" not in query_without_props


class TestGetRelationshipsForEntity:
    """Tests for get_relationships_for_entity helper."""
    
    @pytest.mark.asyncio
    async def test_requires_tenant_id(self, mock_session):
        """Verify tenant_id is required."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            await get_relationships_for_entity(
                mock_session, 
                entity_id="abc", 
                tenant_id=""
            )
    
    @pytest.mark.asyncio
    async def test_validates_direction(self, mock_session):
        """Verify direction parameter is validated."""
        with pytest.raises(ValueError, match="Invalid direction"):
            await get_relationships_for_entity(
                mock_session, 
                entity_id="abc", 
                tenant_id="tenant-a",
                direction="invalid"
            )
    
    @pytest.mark.asyncio
    async def test_outgoing_relationships_filtered_by_tenant(self, mock_session):
        """Verify outgoing relationships include tenant_id filter."""
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter([
            {"rel_type": "ENABLES", "target_id": "target-1", "target_name": "Target 1"}
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        
        rels = await get_relationships_for_entity(
            mock_session,
            entity_id="entity-123",
            tenant_id="tenant-a",
            direction="outgoing"
        )
        
        # Verify query includes tenant_id for both source and target
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        assert "tenant_id: $tenant_id" in query
        assert "target:Entity {tenant_id: $tenant_id}" in query
        assert params["tenant_id"] == "tenant-a"
        assert len(rels["outgoing"]) == 1
        assert len(rels["incoming"]) == 0
    
    @pytest.mark.asyncio
    async def test_incoming_relationships_filtered_by_tenant(self, mock_session):
        """Verify incoming relationships include tenant_id filter."""
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter([
            {"rel_type": "DRIVES", "source_id": "source-1", "source_name": "Source 1"}
        ])
        mock_session.run = AsyncMock(return_value=mock_result)
        
        rels = await get_relationships_for_entity(
            mock_session,
            entity_id="entity-123",
            tenant_id="tenant-a",
            direction="incoming"
        )
        
        # Verify query includes tenant_id for both source and target
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        
        assert "source:Entity {tenant_id: $tenant_id}" in query
        assert "tenant_id: $tenant_id" in query
        assert len(rels["incoming"]) == 1
        assert len(rels["outgoing"]) == 0
    
    @pytest.mark.asyncio
    async def test_both_directions(self, mock_session):
        """Verify both directions queries both outgoing and incoming."""
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter([])
        mock_session.run = AsyncMock(return_value=mock_result)
        
        rels = await get_relationships_for_entity(
            mock_session,
            entity_id="entity-123",
            tenant_id="tenant-a",
            direction="both"
        )
        
        # Should have called run twice (outgoing + incoming)
        assert mock_session.run.call_count == 2


class TestSearchEntities:
    """Tests for search_entities helper."""
    
    @pytest.mark.asyncio
    async def test_requires_tenant_id(self, mock_session):
        """Verify tenant_id is required."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            await search_entities(mock_session, tenant_id="")
    
    @pytest.mark.asyncio
    async def test_filters_by_tenant_id(self, mock_session):
        """Verify search includes tenant_id filter."""
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter([])
        mock_session.run = AsyncMock(return_value=mock_result)
        
        await search_entities(mock_session, tenant_id="tenant-a")
        
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        assert "tenant_id: $tenant_id" in query
        assert params["tenant_id"] == "tenant-a"
    
    @pytest.mark.asyncio
    async def test_entity_type_filter(self, mock_session):
        """Verify entity_type filter is applied."""
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter([])
        mock_session.run = AsyncMock(return_value=mock_result)
        
        await search_entities(
            mock_session, 
            tenant_id="tenant-a",
            entity_types=["Capability", "ValueDriver"]
        )
        
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        assert "e.entity_type IN $entity_types" in query
        assert params["entity_types"] == ["Capability", "ValueDriver"]
    
    @pytest.mark.asyncio
    async def test_pagination(self, mock_session):
        """Verify pagination parameters are applied."""
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter([])
        mock_session.run = AsyncMock(return_value=mock_result)
        
        await search_entities(
            mock_session, 
            tenant_id="tenant-a",
            limit=50,
            offset=100
        )
        
        call_args = mock_session.run.call_args
        params = call_args[0][1]
        
        assert params["limit"] == 50
        assert params["offset"] == 100


class TestGetEntityContext:
    """Tests for get_entity_context helper."""
    
    @pytest.mark.asyncio
    async def test_requires_tenant_id(self, mock_session):
        """Verify tenant_id is required."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            await get_entity_context(
                mock_session, 
                entity_id="abc", 
                tenant_id=""
            )
    
    @pytest.mark.asyncio
    async def test_validates_hops_range(self, mock_session):
        """Verify hops parameter is validated."""
        with pytest.raises(ValueError, match="hops must be between 1 and 3"):
            await get_entity_context(
                mock_session, 
                entity_id="abc", 
                tenant_id="tenant-a",
                hops=0
            )
        
        with pytest.raises(ValueError, match="hops must be between 1 and 3"):
            await get_entity_context(
                mock_session, 
                entity_id="abc", 
                tenant_id="tenant-a",
                hops=4
            )
    
    @pytest.mark.asyncio
    async def test_all_nodes_in_path_filtered_by_tenant(self, mock_session):
        """Verify all nodes in path must have matching tenant_id."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            "center": {"id": "center-1", "tenant_id": "tenant-a"},
            "neighbors": [],
            "all_rels": []
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        
        await get_entity_context(
            mock_session,
            entity_id="entity-123",
            tenant_id="tenant-a",
            hops=2
        )
        
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        
        # Verify both center and connected nodes have tenant_id filter
        assert "center {id: $entity_id, tenant_id: $tenant_id}" in query
        assert "connected {tenant_id: $tenant_id}" in query
    
    @pytest.mark.asyncio
    async def test_relationship_type_filter(self, mock_session):
        """Verify relationship type filter is applied."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            "center": {"id": "center-1"},
            "neighbors": [],
            "all_rels": []
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        
        await get_entity_context(
            mock_session,
            entity_id="entity-123",
            tenant_id="tenant-a",
            relationship_types=["ENABLES", "IMPACTS"]
        )
        
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        
        # params can be passed as second positional argument or kwargs
        if len(call_args[0]) > 1:
            params = call_args[0][1]
        else:
            params = call_args[1]
        
        assert "ALL(r IN relationships(path) WHERE type(r) IN $relationship_types)" in query
        assert "ENABLES" in params["relationship_types"]
        assert "IMPACTS" in params["relationship_types"]


class TestCountEntityRelationships:
    """Tests for count_entity_relationships helper."""
    
    @pytest.mark.asyncio
    async def test_requires_tenant_id(self, mock_session):
        """Verify tenant_id is required."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            await count_entity_relationships(
                mock_session, 
                entity_id="abc", 
                tenant_id=""
            )
    
    @pytest.mark.asyncio
    async def test_counts_only_tenant_scoped_relationships(self, mock_session):
        """Verify counts only include relationships where both entities have matching tenant_id."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={
            "outgoing": 5,
            "incoming": 3
        })
        mock_session.run = AsyncMock(return_value=mock_result)
        
        counts = await count_entity_relationships(
            mock_session,
            entity_id="entity-123",
            tenant_id="tenant-a"
        )
        
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        
        # Verify both source and target have tenant_id filter
        assert "Entity {id: $entity_id, tenant_id: $tenant_id}" in query
        assert "Entity {tenant_id: $tenant_id}" in query
        
        assert counts["outgoing"] == 5
        assert counts["incoming"] == 3
        assert counts["total"] == 8


class TestUpdateEntityProperties:
    """Tests for update_entity_properties helper."""
    
    @pytest.mark.asyncio
    async def test_requires_tenant_id(self, mock_session):
        """Verify tenant_id is required."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            await update_entity_properties(
                mock_session, 
                entity_id="abc", 
                tenant_id="",
                properties={}
            )
    
    @pytest.mark.asyncio
    async def test_only_updates_matching_tenant(self, mock_session):
        """Verify update only affects entities with matching tenant_id."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"entity_id": "entity-123"})
        mock_session.run = AsyncMock(return_value=mock_result)
        
        success = await update_entity_properties(
            mock_session,
            entity_id="entity-123",
            tenant_id="tenant-a",
            properties={"status": "active"}
        )
        
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        assert "id: $entity_id, tenant_id: $tenant_id" in query
        assert params["tenant_id"] == "tenant-a"
        assert params["properties"] == {"status": "active"}
        assert success is True


class TestDeleteEntity:
    """Tests for delete_entity helper."""
    
    @pytest.mark.asyncio
    async def test_requires_tenant_id(self, mock_session):
        """Verify tenant_id is required."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            await delete_entity(
                mock_session, 
                entity_id="abc", 
                tenant_id=""
            )
    
    @pytest.mark.asyncio
    async def test_only_deletes_matching_tenant(self, mock_session):
        """Verify delete only affects entities with matching tenant_id."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"deleted": 1})
        mock_session.run = AsyncMock(return_value=mock_result)
        
        success = await delete_entity(
            mock_session,
            entity_id="entity-123",
            tenant_id="tenant-a"
        )
        
        call_args = mock_session.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        assert "id: $entity_id, tenant_id: $tenant_id" in query
        assert params["tenant_id"] == "tenant-a"
        assert success is True
    
    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, mock_session):
        """Verify returns False when entity not found."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"deleted": 0})
        mock_session.run = AsyncMock(return_value=mock_result)
        
        success = await delete_entity(
            mock_session,
            entity_id="nonexistent",
            tenant_id="tenant-a"
        )
        
        assert success is False


class TestCrossTenantIsolation:
    """Integration tests verifying cross-tenant isolation."""
    
    @pytest.mark.asyncio
    async def test_cannot_read_other_tenant_entity_by_id(self, mock_session):
        """Verify Tenant A cannot read Tenant B's entity by ID."""
        # Simulate entity exists for tenant-b but not tenant-a
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        
        entity = await get_entity_by_id(
            mock_session,
            entity_id="tenant-b-entity",
            tenant_id="tenant-a"  # Wrong tenant
        )
        
        assert entity is None
    
    @pytest.mark.asyncio
    async def test_cannot_update_other_tenant_entity(self, mock_session):
        """Verify Tenant A cannot update Tenant B's entity."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        
        success = await update_entity_properties(
            mock_session,
            entity_id="tenant-b-entity",
            tenant_id="tenant-a",  # Wrong tenant
            properties={"status": "compromised"}
        )
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_cannot_delete_other_tenant_entity(self, mock_session):
        """Verify Tenant A cannot delete Tenant B's entity."""
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"deleted": 0})
        mock_session.run = AsyncMock(return_value=mock_result)
        
        success = await delete_entity(
            mock_session,
            entity_id="tenant-b-entity",
            tenant_id="tenant-a"  # Wrong tenant
        )
        
        assert success is False

