<!-- Migrated from services/ADRs/ during legacy path cleanup. -->

# ADR-014: Multi-Layer Architecture vs Monolith

**Status:** Accepted  
**Date:** April 2026  
**Authors:** Distinguished Engineering Team  
**Reviewers:** Platform Architecture Committee

---

## Context

Value Fabric is an AI-powered value selling platform that needs to:
- Ingest unstructured documents (websites, PDFs, filings)
- Extract structured entities using LLMs
- Store and query knowledge graphs
- Execute complex agentic workflows
- Provide real-time ROI calculations

We needed to decide between:
1. **Monolithic architecture** - Single deployable unit
2. **Microservices** - Fully independent services
3. **Multi-layer pipeline** - Logical separation with coordinated deployment

## Decision

We chose a **6-layer pipeline architecture** with the following characteristics:

```
Layer 1: Ingestion (Playwright, Celery)
Layer 2: Extraction (LLM-based entity extraction)
Layer 3: Knowledge (Neo4j graph + pgvector)
Layer 4: Agents (LangGraph orchestration)
Layer 5: Ground Truth (Validation and evidence)
Layer 6: Benchmarks (Comparative intelligence)
```

## Rationale

### Why Not Monolith?

| Concern | Monolith Impact | Multi-Layer Solution |
|---------|----------------|---------------------|
| LLM Scaling | Entire app scales with GPU needs | Only Layer 2 needs GPU scaling |
| GraphDB Performance | All code affected by Neo4j tuning | Only Layer 3 manages Neo4j |
| Crawler Isolation | Risk affects entire application | Layer 1 isolation limits blast radius |
| Team Scaling | Coordination overhead | Teams own layers independently |
| Technology Diversity | Single stack constraint | Best-of-breed per layer |

### Why Not Full Microservices?

| Concern | Microservices Impact | Multi-Layer Solution |
|---------|---------------------|---------------------|
| Operational Complexity | High (orchestration, mesh) | Medium (Docker Compose/K8s) |
| Data Consistency | Distributed transactions | Layer-to-layer handoff with retries |
| Development Velocity | Service coordination overhead | Clear contracts, simpler testing |
| Debugging | Distributed tracing complexity | Layer-level observability |
| Cost | Multiple load balancers, DBs | Shared infrastructure where appropriate |

### Why Multi-Layer?

1. **Clear Data Flow**: Unidirectional flow (L1 → L2 → L3 → L4) simplifies reasoning
2. **Independent Scaling**: Scale Layer 2 (GPU) without scaling Layer 4 (CPU)
3. **Fault Isolation**: Layer 1 failure doesn't cascade to Layer 4
4. **Technology Fit**: Each layer uses optimal technology
5. **Team Ownership**: Clear boundaries for team responsibility
6. **Progressive Deployment**: Deploy layers independently

## Trade-offs

### Positive
- Clear separation of concerns
- Independent scaling per layer
- Technology diversity per layer
- Team autonomy with defined contracts
- Reduced blast radius for failures

### Negative
- Cross-layer debugging complexity
- Contract maintenance overhead
- Network latency between layers
- Potential for version skew
- More complex integration testing

## Mitigations

| Risk | Mitigation |
|------|-----------|
| Cross-layer debugging | OpenTelemetry tracing with correlation IDs |
| Contract drift | Contract tests in CI/CD, shared OpenAPI specs |
| Network latency | Connection pooling, caching, async processing |
| Version skew | Layer versioning, backward compatibility tests |
| Integration complexity | Automated contract tests, staging environment |

## Implementation

### Layer Contracts

```python
# Shared contract between Layer 2 and Layer 3
class IngestRDFRequest(BaseModel):
    """Contract for RDF ingestion from Layer 2 to Layer 3."""
    
    tenant_id: UUID
    extraction_job_id: UUID
    entities: list[Entity]
    relationships: list[Relationship]
    provenance: ProvenanceChain
    
    # Version for backward compatibility
    schema_version: str = "1.0.0"
```

### Deployment Model

```yaml
# docker-compose.yml - Layer coordination
version: "3.8"
services:
  layer1:
    build: ./layer1-ingestion
    depends_on:
      - postgres
      - redis
  
  layer2:
    build: ./layer2-extraction
    depends_on:
      - postgres
      - layer1  # Can call for document retrieval
  
  layer3:
    build: ./layer3-knowledge
    depends_on:
      - neo4j
      - postgres
  
  layer4:
    build: ./layer4-agents
    depends_on:
      - postgres
      - redis
      - layer3
```

## Consequences

### Accepted
- Higher operational complexity than monolith
- Need for robust contract testing
- Cross-layer observability investment required

### Mitigated
- Version skew via automated contract tests
- Debugging complexity via distributed tracing
- Integration issues via staging environment

## Related Decisions

- ADR-002: Neo4j for knowledge graph storage
- ADR-004: LangGraph for workflow orchestration
- ADR-007: OpenTelemetry for observability

---

**Last Updated:** April 21, 2026
