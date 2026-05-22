<!-- Migrated from services/ADRs/ during legacy path cleanup. -->

# ADR-016: Neo4j for Knowledge Graph Storage

**Status:** Accepted  
**Date:** April 2026  
**Authors:** Distinguished Engineering Team  
**Reviewers:** Data Architecture Committee

---

## Context

Layer 3 (Knowledge Graph & Semantic Layer) needs to store:
- 10M+ entities (Capabilities, UseCases, Personas, ValueDrivers)
- 100M+ relationships between entities
- Vector embeddings for semantic search
- Complex graph traversals (3+ hops)
- Real-time queries with <500ms p99 latency

We evaluated:
1. **Neo4j** (Native graph database)
2. **Amazon Neptune** (Managed graph service)
3. **RDF Triple Store** (Apache Jena, GraphDB)
4. **PostgreSQL with pg_graph** (Relational with graph extension)

## Decision

We chose **Neo4j Community Edition** with the following deployment model:

```
Production: Neo4j Enterprise (clustered)
Staging:    Neo4j Community (single)
Dev:        Neo4j Community (Docker)
```

## Rationale

### Comparison Matrix

| Criteria | Neo4j | Neptune | RDF Store | PostgreSQL |
|----------|-------|---------|-----------|------------|
| Query Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Cypher Expressiveness | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ (SPARQL) | ⭐⭐ |
| Vector Search | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ (pgvector) |
| Graph Algorithms | ⭐⭐⭐⭐⭐ (GDS) | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| Operational Simplicity | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Cost (Self-Hosted) | ⭐⭐⭐⭐ | ⭐⭐ (managed) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Multi-Tenancy | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |

### Why Neo4j?

1. **Cypher Query Language**: Intuitive pattern matching for graph traversals
   ```cypher
   MATCH (c:Capability)-[:ENABLES]->(u:UseCase)-[:BENEFITS]->(p:Persona)
   WHERE c.name CONTAINS 'AI'
   RETURN c, u, p
   ```

2. **Graph Data Science (GDS)**: Built-in algorithms for:
   - Community detection (Leiden)
   - Centrality analysis (PageRank)
   - Similarity (cosine, Euclidean)
   - Pathfinding (A*, Dijkstra)

3. **Performance**: Native graph storage with index-free adjacency
   - 50ms p99 for 3-hop traversals
   - 200ms p99 for vector + graph hybrid queries

4. **Ecosystem**: Strong Python driver, visualization tools, APOC procedures

### Why Not Neptune?

- Vendor lock-in to AWS
- Less mature Cypher implementation (optimizes for Gremlin)
- Higher cost for equivalent performance
- Limited GDS equivalent

### Why Not RDF Triple Store?

- SPARQL more verbose for pattern matching
- Weaker vector search integration
- Smaller ecosystem for Python/FastAPI
- Complex ontology management overhead

### Why Not PostgreSQL?

- Poor performance for deep graph traversals (3+ hops)
- No built-in graph algorithms
- Recursive CTEs don't scale to 100M relationships

## Trade-offs

### Positive
- Optimal query performance for graph patterns
- Rich ecosystem of graph algorithms
- Excellent Python driver support
- Strong visualization and debugging tools

### Negative
- Complex clustering (Enterprise required for HA)
- Limited built-in multi-tenancy
- Memory-intensive for large graphs
- Cypher injection risk (requires careful query construction)

## Mitigations

| Risk | Mitigation |
|------|-----------|
| Multi-tenancy | Tenant ID on all nodes/relationships + query filtering |
| Cypher Injection | Parameterized queries only, never string concatenation |
| Memory | Connection pooling, result pagination, selective indexing |
| Clustering | Neo4j Enterprise in production with causal clustering |

## Implementation

### Tenant Scoping

```python
class Neo4jRepository:
    """Repository with mandatory tenant scoping."""
    
    async def find_entity(
        self,
        entity_id: str,
        tenant_id: str,
    ) -> Optional[Entity]:
        """Find entity with tenant isolation."""
        
        # SECURITY: Always include tenant filter
        query = """
        MATCH (e:Entity {id: $entity_id, tenant_id: $tenant_id})
        RETURN e
        """
        
        result = await self._driver.execute_query(
            query,
            entity_id=entity_id,
            tenant_id=tenant_id,  # Required parameter
        )
        
        return result.single()
```

### Composite Constraints

```cypher
-- Ensure entity ID uniqueness per tenant
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) 
REQUIRE (e.id, e.tenant_id) IS UNIQUE;

-- Indexes for common queries
CREATE INDEX entity_type_tenant IF NOT EXISTS
FOR (e:Entity) 
ON (e.type, e.tenant_id);

-- Vector index for semantic search
CALL db.index.vector.createNodeIndex(
  'entity_embeddings',
  'Entity',
  'embedding',
  1536,
  'cosine'
);
```

### Hybrid Search Pattern

```python
async def hybrid_search(
    self,
    query: str,
    tenant_id: str,
    top_k: int = 10,
) -> list[SearchResult]:
    """Vector search + graph traversal hybrid."""
    
    # 1. Vector similarity search
    query_embedding = await self._embed(query)
    
    vector_query = """
    CALL db.index.vector.queryNodes('entity_embeddings', $top_k, $embedding)
    YIELD node, score
    WHERE node.tenant_id = $tenant_id
    RETURN node.id as entity_id, score
    """
    
    vector_results = await self._driver.execute_query(
        vector_query,
        embedding=query_embedding,
        tenant_id=tenant_id,
        top_k=top_k,
    )
    
    # 2. Graph expansion for context
    graph_query = """
    MATCH (e:Entity)-[r:RELATES_TO*1..3]-(connected)
    WHERE e.id IN $entity_ids
    AND e.tenant_id = $tenant_id
    AND connected.tenant_id = $tenant_id
    RETURN e, r, connected
    """
    
    entity_ids = [r["entity_id"] for r in vector_results]
    
    graph_results = await self._driver.execute_query(
        graph_query,
        entity_ids=entity_ids,
        tenant_id=tenant_id,
    )
    
    return self._combine_results(vector_results, graph_results)
```

## Consequences

### Accepted
- Neo4j Enterprise licensing cost for production clustering
- Need for careful memory management
- Custom multi-tenancy implementation

### Mitigated
- Cypher injection via parameterized query enforcement
- Memory via connection pooling and pagination
- Tenant isolation via composite unique constraints

## Performance Benchmarks

| Query Type | Nodes | Relationships | p50 | p95 | p99 |
|-----------|-------|--------------|-----|-----|-----|
| Single-hop | 10M | 100M | 5ms | 15ms | 25ms |
| 3-hop traversal | 10M | 100M | 50ms | 120ms | 200ms |
| Vector + graph | 10M | 100M | 100ms | 300ms | 500ms |
| Community detection | 10M | 100M | 5s | 10s | 15s |

## Related Decisions

- ADR-003: PostgreSQL + RLS for multi-tenancy
- ADR-007: OpenTelemetry for observability

---

**Last Updated:** April 21, 2026
