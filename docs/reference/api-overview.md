---
title: "Value Fabric API Overview"
category: "reference"
audience: "intermediate"
last-reviewed: "2026-04-19"
freshness: "current"
related: ["layer1-ingestion-api", "layer2-extraction-api", "layer3-knowledge-api", "layer4-agents-api", "layer5-ground-truth-api", "../core-concepts/security-model", "../core-concepts/architecture", "../getting-started/quickstart", "../troubleshooting/authentication-errors"]
---

# API Reference Overview

> **In this guide, you will:**
> - Understand the multi-layer API structure
> - Learn authentication patterns across all layers
> - See common request/response patterns
> - Find layer-specific API documentation

---

## Frontend dependency mapping

For frontend route-family to Layer 1–6 dependency ownership and failure fallback contracts, see [`apps/web/docs/route-layer-dependency-map.md`](../../apps/web/docs/route-layer-dependency-map.md).

## API Architecture

Value Fabric exposes a layered API architecture where each layer provides specialized capabilities:

```mermaid
graph TB
    subgraph "Client Applications"
        FE[Frontend<br/>React SPA]
        SDK[Python SDK<br/>pip install value-fabric]
        CLI[CLI Tool<br/>vfctl]
        INTEGRATION[External Systems<br/>Your App]
    end
    
    subgraph "API Gateway"
        GW[Gateway<br/>Auth + Rate Limit + Routing]
    end
    
    subgraph "Service APIs"
        L1[Layer 1 API<br/>Port 8001<br/>Ingestion]
        L2[Layer 2 API<br/>Port 8002<br/>Extraction]
        L3[Layer 3 API<br/>Port 8003<br/>Knowledge Graph]
        L4[Layer 4 API<br/>Port 8004<br/>Agents]
    end
    
    subgraph "Health & Metrics"
        HEALTH[/health<br/>Liveness]
        READY[/ready<br/>Readiness]
        METRICS[/metrics<br/>Prometheus]
    end
    
    FE -->|REST + SSE| GW
    SDK -->|REST| GW
    CLI -->|REST| GW
    INTEGRATION -->|REST| GW
    
    GW --> L1
    GW --> L2
    GW --> L3
    GW --> L4
    
    L1 -.-> HEALTH
    L2 -.-> HEALTH
    L3 -.-> HEALTH
    L4 -.-> HEALTH
    
    style FE fill:#4a90d9,color:white
    style GW fill:#e74c3c,color:white
    style L1 fill:#2ecc71,color:white
    style L2 fill:#2ecc71,color:white
    style L3 fill:#2ecc71,color:white
    style L4 fill:#2ecc71,color:white
```

---

## Base URLs

| Environment | Layer 1 | Layer 2 | Layer 3 | Layer 4 |
|-------------|---------|---------|---------|---------|
| Local | `http://localhost:8001` | `http://localhost:8002` | `http://localhost:8003` | `http://localhost:8004` |
| Staging | `https://l1.staging.valuefabric.io` | `https://l2.staging.valuefabric.io` | `https://l3.staging.valuefabric.io` | `https://l4.staging.valuefabric.io` |
| Production | `https://l1.valuefabric.io` | `https://l2.valuefabric.io` | `https://l3.valuefabric.io` | `https://l4.valuefabric.io` |

---

## Authentication

All API requests require authentication via JWT or API key.

### JWT Authentication

```http
GET /api/v1/entities HTTP/1.1
Host: l3.valuefabric.io
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000
```

### API Key Authentication

```http
GET /api/v1/entities HTTP/1.1
Host: l3.valuefabric.io
X-API-Key: vf_test_dummy_550e8400e29b41d4a716446655440000
X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant GW as API Gateway
    participant IDP as Identity Provider
    participant S as Service
    
    C->>IDP: POST /auth/login
    IDP-->>C: JWT token
    
    C->>GW: API request + JWT
    GW->>GW: Validate signature
    GW->>GW: Check expiration
    GW->>GW: Extract tenant
    GW->>S: Forward request
    S-->>GW: Response
    GW-->>C: Response
```

---

## Common Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes* | `Bearer <jwt>` for JWT auth |
| `X-API-Key` | Yes* | API key for service-to-service |
| `X-Tenant-ID` | Yes | UUID of the tenant |
| `X-Request-ID` | No | Trace ID for request correlation |
| `Content-Type` | Yes (POST/PUT) | `application/json` |
| `Accept` | No | `application/json` (default) |

*One of `Authorization` or `X-API-Key` is required

---

## Response Format

All responses follow a consistent envelope structure:

### Success Response

```json
{
  "data": {
    // Response-specific content
  },
  "meta": {
    "request_id": "req_550e8400e29b",
    "timestamp": "2026-04-19T12:00:00Z"
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    }
  },
  "meta": {
    "request_id": "req_550e8400e29b",
    "timestamp": "2026-04-19T12:00:00Z"
  }
}
```

---

## Error Codes

| Code | HTTP Status | Meaning | Resolution |
|------|-------------|---------|------------|
| `UNAUTHORIZED` | 401 | Invalid/missing credentials | Check JWT/API key |
| `FORBIDDEN` | 403 | Valid auth, insufficient permissions | Verify role assignments |
| `NOT_FOUND` | 404 | Resource doesn't exist | Verify resource ID |
| `VALIDATION_ERROR` | 422 | Invalid request format | Check API reference |
| `RATE_LIMITED` | 429 | Too many requests | Implement backoff |
| `INTERNAL_ERROR` | 500 | Server error | Contact support |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily down | Retry with backoff |

---

## Pagination

List endpoints support cursor-based pagination:

### Request

```http
GET /api/v1/entities?limit=20&cursor=eyJpZCI6MTAwfQ== HTTP/1.1
```

### Response

```json
{
  "data": {
    "items": [...],
    "pagination": {
      "limit": 20,
      "cursor": "eyJpZCI6MTAwfQ==",
      "next_cursor": "eyJpZCI6MTIwfQ==",
      "has_more": true
    }
  }
}
```

---

## Rate Limiting

| Tier | Requests/Min | Burst |
|------|-------------|-------|
| Free | 60 | 10 |
| Pro | 600 | 100 |
| Enterprise | 6000 | 1000 |

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 599
X-RateLimit-Reset: 1713532800
```

---

## Layer-Specific APIs

### Layer 1: Ingestion API

**Purpose:** Document crawling, chunking, and ingestion job management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ingestion/jobs` | POST | Create ingestion job |
| `/api/v1/ingestion/jobs/{id}` | GET | Get job status |
| `/api/v1/ingestion/jobs/{id}/cancel` | POST | Cancel running job |

**Full documentation:** [Layer 1 API](./layer1-api.md)

### Layer 2: Extraction API

**Purpose:** LLM-guided entity and relationship extraction

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/extraction/jobs` | POST | Start extraction workflow |
| `/api/v1/extraction/entities` | GET | List extracted entities |
| `/api/v1/extraction/validate` | POST | Validate extraction quality |

**Full documentation:** [Layer 2 API](./layer2-api.md)

### Layer 3: Knowledge Graph API

**Purpose:** Graph queries, entity management, and semantic search

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/entities` | GET | Search entities |
| `/api/v1/entities/{id}` | GET | Get entity by ID |
| `/api/v1/graph/subgraph` | GET | Query subgraph |
| `/api/v1/search` | POST | Semantic search |

**Full documentation:** [Layer 3 API](./layer3-api.md)

### Layer 4: Agent API

**Purpose:** Workflow orchestration and agent management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/workflows` | POST | Create workflow |
| `/api/v1/workflows/{id}` | GET | Get workflow status |
| `/api/v1/workflows/{id}/pause` | POST | Pause workflow |
| `/api/v1/workflows/{id}/resume` | POST | Resume workflow |
| `/api/v1/agents/skills` | GET | List available skills |

**Full documentation:** [Layer 4 API](./layer4-api.md)

---

## Health Endpoints

Each layer exposes health check endpoints:

```bash
# Liveness probe (is the process running?)
curl http://localhost:8001/health

# Readiness probe (is it ready to accept traffic?)
curl http://localhost:8001/ready

# Prometheus metrics
curl http://localhost:8001/metrics
```

**Response format:**

```json
{
  "status": "healthy",
  "version": "1.2.3",
  "checks": {
    "database": "ok",
    "cache": "ok"
  }
}
```

---

## SDK Examples

### Python SDK

```python
from value_fabric import Client

# Initialize client
client = Client(
    api_key="vf_live_...",
    tenant_id="550e8400-...",
    base_url="https://l3.valuefabric.io"
)

# Search entities
entities = client.entities.search(query="AI capabilities")

# Create workflow
workflow = client.workflows.create(
    name="ROI Analysis",
    skills=["analyze_roi", "generate_report"]
)
```

### JavaScript/TypeScript SDK

```typescript
import { ValueFabricClient } from '@valuefabric/sdk';

const client = new ValueFabricClient({
  apiKey: 'vf_live_...',
  tenantId: '550e8400-...',
  baseURL: 'https://l3.valuefabric.io'
});

// Search entities
const entities = await client.entities.search({ query: 'AI capabilities' });
```

---

## Deprecation Policy

When endpoints are deprecated:

1. **90 days notice** — Deprecation announced in changelog
2. **Warning headers** — Added to API responses:
   ```http
   Warning: 299 - "Deprecated since 2026-04-01"
   X-Deprecated-Since: 2026-04-01
   X-Target-Removal-Date: 2026-07-01
   ```
3. **Migration guide** — Published in documentation
4. **Final removal** — After 90-day migration period

See [Deprecation Inventory](../deprecation_inventory.md) for current deprecations.

---

## Next Steps

| Goal | Next Document |
|------|---------------|
| Layer 1 endpoints | [Layer 1 API](./layer1-api.md) |
| Layer 2 endpoints | [Layer 2 API](./layer2-api.md) |
| Layer 3 endpoints | [Layer 3 API](./layer3-api.md) |
| Layer 4 endpoints | [Layer 4 API](./layer4-api.md) |
| Set up authentication | [Configure SSO](../how-to-guides/configure-sso.md) |
| Troubleshoot API errors | [Troubleshooting Index](../troubleshooting/index.md) |

---

## Related Documentation

- [Architecture Overview](../core-concepts/architecture.md) — Understanding the system
- [Security Model](../core-concepts/security-model.md) — Authentication deep dive
- [Troubleshooting Index](../troubleshooting/index.md) — Common API issues
- [Deprecation Inventory](../deprecation_inventory.md) — API lifecycle

---

*Last updated: 2026-04-19 | [Edit this page](https://github.com/bmsull560/Fabric_4L/edit/main/docs/reference/api-overview.md)*
