---
title: "Value Fabric Architecture"
category: "core-concepts"
audience: "intermediate"
last-reviewed: "2026-05-04"
freshness: "current"
related: ["../getting-started/quickstart", "../getting-started/environment", "../reference/layer1-ingestion-api", "security-model", "ontology-system", "../explanations/adr/ADR-001-six-layer-architecture", "../explanations/adr/ADR-002-hybrid-graph-database"]
---

# Value Fabric System Architecture

> **In this guide, you will:**
> - Understand the 6-layer pipeline architecture
> - Learn how data flows through the system
> - Explore container and component-level designs
> - See deployment topology for production

---

## Prerequisites

Before reading this document:

1. Complete the [Quickstart Guide](../getting-started/quickstart.md)
2. Basic understanding of:
   - REST APIs and microservices
   - Graph databases (Neo4j)
   - Docker and containerization

---

## System Context (C4 Level 1)

Value Fabric is an enterprise agentic SaaS platform that transforms unstructured data into structured, actionable knowledge.

```mermaid
graph TB
    subgraph "Enterprise Environment"
        U[Business Analyst<br/>👤 Person]
        D[Data Sources<br/>📄 Documents, Web, APIs]
    end
    
    subgraph "Value Fabric Platform"
        VF[Value Fabric System<br/>🏢 Enterprise SaaS]
    end
    
    subgraph "External Services"
        AI[LLM Provider<br/>🤖 OpenAI/Anthropic]
        IDP[Identity Provider<br/>🔐 SSO/OIDC]
    end
    
    U -->|Creates workflows,<br/>reviews insights| VF
    D -->|Ingested, processed| VF
    VF -->|Extraction,<br/>analysis| AI
    VF -->|Authentication| IDP
    VF -->|Reports,<br/>recommendations| U
    
    style U fill:#4a90d9,color:white
    style VF fill:#2ecc71,color:white
    style AI fill:#95a5a6,color:white
    style IDP fill:#95a5a6,color:white
```

**Key Actors:**
- **Business Analyst**: Creates extraction workflows, reviews generated insights
- **System Integrator**: Connects external data sources, configures SSO
- **Platform Administrator**: Monitors health, manages tenants

---

## Container Architecture (C4 Level 2)

The system follows a 6-layer pipeline architecture with clear separation of concerns:

```mermaid
graph TB
    subgraph "Client Layer"
        FE[Frontend<br/>React + TypeScript<br/>Port 5173]
        CLI[CLI Tools<br/>Python SDK]
    end
    
    subgraph "API Gateway"
        GW[API Gateway<br/>Authentication<br/>Rate Limiting]
    end
    
    subgraph "Service Layer"
        L1[Layer 1: Ingestion<br/>FastAPI + Playwright<br/>Port 8001]
        L2[Layer 2: Extraction<br/>FastAPI + LLM<br/>Port 8002]
        L3[Layer 3: Knowledge<br/>FastAPI + Neo4j<br/>Port 8003]
        L4[Layer 4: Agents<br/>FastAPI + LangGraph<br/>Port 8004]
        L5[Layer 5: Ground Truth<br/>FastAPI + PostgreSQL<br/>Port 8005]
        L6[Layer 6: Benchmarks<br/>FastAPI + Statistical Libraries<br/>Port 8006]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL<br/>Relational Data)]
        NEO[(Neo4j<br/>Knowledge Graph)]
        RED[(Redis<br/>Caching + Queues)]
        S3[S3/MinIO<br/>Document Storage]
    end
    
    subgraph "External"
        OPENAI[OpenAI API]
        VAULT[HashiCorp Vault]
    end
    
    FE -->|GraphQL/REST| GW
    CLI -->|REST| GW
    GW -->|Route + Auth| L1
    GW -->|Route + Auth| L2
    GW -->|Route + Auth| L3
    GW -->|Route + Auth| L4
    GW -->|Route + Auth| L5
    GW -->|Route + Auth| L6
    
    L1 -->|Ingest jobs| RED
    L1 -->|Metadata| PG
    L1 -->|Documents| S3
    
    L2 -->|Poll jobs| RED
    L2 -->|LLM calls| OPENAI
    L2 -->|Extraction state| PG
    
    L3 -->|Graph queries| NEO
    L3 -->|Vector search| PG
    L3 -->|Cache| RED
    
    L4 -->|Agent state| RED
    L4 -->|LLM calls| OPENAI
    L4 -->|Workflows| PG
    
    L5 -->|Truth objects| PG
    L6 -->|Benchmark results| PG
    
    L1 -.->|Progress updates| L4
    L2 -.->|Extractions| L3
    L3 -.->|Context| L4
    L4 -.->|Agent outputs| L5
    L5 -.->|Validated truth| L6
    
    style FE fill:#4a90d9,color:white
    style L1 fill:#2ecc71,color:white
    style L2 fill:#2ecc71,color:white
    style L3 fill:#2ecc71,color:white
    style L4 fill:#2ecc71,color:white
    style L5 fill:#2ecc71,color:white
    style L6 fill:#2ecc71,color:white
    style GW fill:#e74c3c,color:white
    style PG fill:#9b59b6,color:white
    style NEO fill:#9b59b6,color:white
    style RED fill:#9b59b6,color:white
    style OPENAI fill:#95a5a6,color:white
```

---

## Layer 1: Intelligent Data Ingestion

**Purpose:** Convert unstructured source materials into processable content units

```mermaid
flowchart LR
    subgraph "Input"
        WEB[Web URLs]
        DOC[Documents<br/>PDF/DOCX/HTML]
        API[External APIs]
    end
    
    subgraph "Processing"
        CRAWLER[Playwright<br/>Crawler]
        PARSER[Document<br/>Parser]
        CHUNKER[Text<br/>Chunker]
    end
    
    subgraph "Output"
        CHUNKS[Content Chunks<br/>+ Metadata]
        S3_DOC[Raw Documents<br/>S3 Storage]
    end
    
    WEB --> CRAWLER
    DOC --> PARSER
    API --> PARSER
    
    CRAWLER --> CHUNKER
    PARSER --> CHUNKER
    PARSER --> S3_DOC
    CHUNKER --> CHUNKS
    
    style CRAWLER fill:#2ecc71,color:white
    style PARSER fill:#2ecc71,color:white
    style CHUNKER fill:#2ecc71,color:white
    style CHUNKS fill:#4a90d9,color:white
```

**Key Components:**
| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Crawler | Playwright | JavaScript-rendered page capture |
| Document Parser | pdfplumber, python-docx | Binary document extraction |
| PII Scanner | Presidio | Sensitive data detection |
| Chunker | Sentence-transformers | Semantic text segmentation |

---

## Layer 2: Ontology-Guided Extraction

**Purpose:** Identify entities and relationships using LLM-guided extraction

```mermaid
sequenceDiagram
    participant Q as Redis Queue
    participant L2 as Layer 2 API
    participant EX as LLM Extractor
    participant OA as Ontology Aligner
    participant RDF as RDF Generator
    participant L3 as Layer 3
    
    Q->>L2: Poll ingestion job
    L2->>L2: Load ontology schema
    
    loop For each chunk
        L2->>EX: Extract entities<br/>with function calling
        EX-->>L2: Typed entities<br/>+ confidence scores
        L2->>OA: Semantic alignment<br/>(deduplication)
        OA-->>L2: Merged entities<br/>+ provenance
    end
    
    L2->>RDF: Generate RDF/OWL
    RDF-->>L2: Semantic triples
    L2->>L3: POST /entities/batch
    L3-->>L2: Storage confirmation
    L2->>Q: Mark job complete
```

**Entity Taxonomy:**
```
Capability → UseCase → Persona → ValueDriver
     ↓           ↓          ↓           ↓
  What the    How it's   Who uses   Business
  system does  applied    it         benefit
```

---

## Layer 3: Knowledge Graph & Semantic Layer

**Purpose:** Store, query, and reason over extracted knowledge

```mermaid
graph TB
    subgraph "Storage"
        NEO[(Neo4j<br/>Graph Database)]
        PG_VEC[(PostgreSQL<br/>pgvector)]
    end
    
    subgraph "Query Engine"
        HYBRID[Hybrid Retriever]
        GRAG[GraphRAG]
        VEC[Vector Search]
    end
    
    subgraph "API"
        GQL[GraphQL
        /entity
        /relationship]
        REST[REST
        /search
        /subgraph]
    end
    
    NEO -->|Graph structure| HYBRID
    PG_VEC -->|Embeddings| VEC
    HYBRID -->|Combined results| GRAG
    VEC -->|Combined results| GRAG
    GRAG -->|Enriched context| REST
    GRAG -->|Enriched context| GQL
    
    style NEO fill:#9b59b6,color:white
    style PG_VEC fill:#9b59b6,color:white
    style GRAG fill:#2ecc71,color:white
```

**Retrieval Pattern:**
1. **Vector Search**: Semantic similarity using pgvector
2. **Graph Traversal**: 1-3 hop neighbor expansion in Neo4j
3. **Hybrid Reranking**: Combine semantic + structural relevance

---

## Layer 4: Agentic Workflow Engine

**Purpose:** Orchestrate multi-agent workflows with business logic

```mermaid
stateDiagram-v2
    [*] --> Idle: Workflow submitted
    
    Idle --> Planning: Agent receives task
    Planning --> Executing: Plan approved
    
    Executing --> Paused: User pause
    Paused --> Executing: User resume
    
    Executing --> ToolCall: Tool needed
    ToolCall --> Executing: Tool result
    
    Executing --> AwaitingApproval: Human gate
    AwaitingApproval --> Executing: Approved
    AwaitingApproval --> Failed: Rejected
    
    Executing --> Complete: Task finished
    Executing --> Failed: Error
    
    Complete --> [*]
    Failed --> [*]
    
    Complete: ✅ Complete
    Failed: ❌ Failed
```

**Agent Types:**
| Agent | Responsibility | Tools |
|-------|---------------|-------|
| Business Analyst | ROI analysis, case building | Query, Calculate, Generate |
| Data Engineer | Extraction monitoring | Ingest, Validate |
| Auditor | Compliance checking | AuditLog, Verify |

---

## Data Flow: End-to-End

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Frontend
    participant L1 as Layer 1
    participant L2 as Layer 2
    participant L3 as Layer 3
    participant L4 as Layer 4
    participant AI as LLM Provider
    
    U->>FE: Submit document URL
    FE->>L1: POST /ingestion/jobs
    L1-->>FE: job_id: abc-123
    
    loop Async Processing
        L1->>L1: Crawl & chunk
        L1->>L2: Queue extraction
        L2->>AI: LLM extraction
        AI-->>L2: Entities + relationships
        L2->>L3: Store in knowledge graph
        L3-->>L2: Confirmation
    end
    
    L1-->>FE: SSE: Job complete
    FE-->>U: Notification
    
    U->>FE: Request analysis
    FE->>L4: POST /workflows
    L4->>L3: Query context
    L3-->>L4: Relevant entities
    L4->>AI: Reasoning request
    AI-->>L4: Analysis results
    L4-->>FE: Workflow complete
    FE-->>U: Display insights
```

---

## Deployment Topology (Production)

```mermaid
graph TB
    subgraph "Client"
        CDN[CloudFront/Cloudflare<br/>Static Assets]
        USERS[Users/Browsers]
    end
    
    subgraph "AWS/Azure/GCP"
        LB[Load Balancer<br/>SSL Termination]
        
        subgraph "Kubernetes Cluster"
            ING[Ingress Controller<br/>nginx/cert-manager]
            
            subgraph "Application Tier"
                FE_POD[Frontend Pods<br/>3 replicas]
                L1_POD[L1 Pods<br/>2 replicas]
                L2_POD[L2 Pods<br/>2 replicas]
                L3_POD[L3 Pods<br/>3 replicas]
                L4_POD[L4 Pods<br/>2 replicas]
            end
            
            subgraph "Data Tier"
                PG_CLUSTER[PostgreSQL<br/>Primary-Replica]
                NEO_CLUSTER[Neo4j Cluster<br/>3 cores]
                RED_CLUSTER[Redis Cluster<br/>6 nodes]
            end
        end
        
        VAULT[HashiCorp Vault<br/>Secret Management]
        S3[S3 Object Storage<br/>Documents + Backups]
    end
    
    subgraph "External"
        OPENAI[OpenAI/Anthropic<br/>API]
        IDP[Okta/Azure AD<br/>SSO]
    end
    
    USERS --> CDN
    CDN --> LB
    LB --> ING
    ING --> FE_POD
    ING --> L1_POD
    ING --> L2_POD
    ING --> L3_POD
    ING --> L4_POD
    
    L1_POD --> S3
    L1_POD --> PG_CLUSTER
    L2_POD --> RED_CLUSTER
    L2_POD --> OPENAI
    L3_POD --> NEO_CLUSTER
    L3_POD --> PG_CLUSTER
    L4_POD --> RED_CLUSTER
    L4_POD --> OPENAI
    
    FE_POD --> IDP
    L1_POD --> VAULT
    L2_POD --> VAULT
    L3_POD --> VAULT
    L4_POD --> VAULT
    
    style CDN fill:#4a90d9,color:white
    style LB fill:#e74c3c,color:white
    style FE_POD fill:#2ecc71,color:white
    style L1_POD fill:#2ecc71,color:white
    style L2_POD fill:#2ecc71,color:white
    style L3_POD fill:#2ecc71,color:white
    style L4_POD fill:#2ecc71,color:white
    style PG_CLUSTER fill:#9b59b6,color:white
    style NEO_CLUSTER fill:#9b59b6,color:white
    style OPENAI fill:#95a5a6,color:white
```

---

## Component Dependencies

| Layer | Upstream | Downstream | Data Stores |
|-------|----------|------------|-------------|
| L1: Ingestion | External sources, User uploads | L2 via Redis | PostgreSQL, S3 |
| L2: Extraction | L1 via Redis | L3 via HTTP | PostgreSQL |
| L3: Knowledge | L2 via HTTP, L4 queries | L4 context | Neo4j, PostgreSQL, Redis |
| L4: Agents | L3 context, User workflows | Frontend SSE | PostgreSQL, Redis |

---

## Security Boundaries

```mermaid
graph TB
    subgraph "Public Zone"
        CLIENT[Client Browser]
    end
    
    subgraph "DMZ"
        LB[Load Balancer]
        CDN[CDN]
    end
    
    subgraph "Application Zone"
        GW[API Gateway<br/>Auth/Rate Limit]
        SVC[Services L1-L4]
    end
    
    subgraph "Data Zone"
        DB[(Databases)]
        CACHE[(Redis)]
    end
    
    subgraph "Secure Zone"
        VAULT[Vault]
        SECRETS[Secrets]
    end
    
    CLIENT -->|HTTPS| CDN
    CDN -->|HTTPS| LB
    LB -->|mTLS| GW
    GW -->|Internal mTLS| SVC
    SVC -->|TLS| DB
    SVC -->|TLS| CACHE
    SVC -->|Vault Agent| VAULT
    
    style CLIENT fill:#4a90d9,color:white
    style GW fill:#e74c3c,color:white
    style DB fill:#9b59b6,color:white
    style VAULT fill:#9b59b6,color:white
```

---

## Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| 6-layer separation | Clear boundaries, independent scaling | Network overhead between layers |
| Neo4j for knowledge | Native graph operations, Cypher | Operational complexity |
| PostgreSQL + pgvector | Unified relational + vector store | Not specialized vector DB |
| LangGraph for agents | Stateful orchestration, pause/resume | Learning curve |
| Redis for queues | Simple, fast job queuing | Not persistent by default |

See [Architecture Decision Records](../explanations/adr/) for detailed rationale.

---

## Performance Characteristics

| Metric | Target | Achieved |
|--------|--------|----------|
| Ingestion throughput | 100 docs/min | 85 docs/min |
| Extraction latency (p95) | <30s | 25s |
| Graph query latency (p99) | <100ms | 75ms |
| Agent workflow response | <5s | 3.2s |
| System availability | 99.9% | 99.95% |

---

## Next Steps

| Goal | Next Document |
|------|---------------|
| Understand security model | [Security Model](./security-model.md) |
| Learn about ontology | [Ontology System](./ontology-system.md) |
| Deploy to production | [Kubernetes Deployment](../../k8s/README.md) |
| Read design decisions | [ADR Index](../explanations/adr/) |

---

## Related Documentation

- [Quickstart Guide](../getting-started/quickstart.md) — Get running in 15 minutes
- [API Reference](../../API_REFERENCE.md) — Endpoint documentation
- [Troubleshooting Index](../troubleshooting/index.md) — Common issues
- [Security Model](./security-model.md) — Authentication and authorization
- [Ontology System](./ontology-system.md) — Entity and relationship types

---

*Last updated: 2026-05-04 | [Edit this page](https://github.com/bmsull560/Fabric_4L/edit/main/docs/core-concepts/architecture.md)*
