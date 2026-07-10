# Web Vitals Telemetry API Specification

**Version:** 1.0.0  
**Status:** draft  
**Owner:** frontend-platform  
**Reviewers:** backend-platform, observability, security

---

## 1. Overview

The Web Vitals Telemetry API receives Core Web Vitals (CWV) measurements from the Fabric_4L React frontend. It is a write-only, best-effort ingestion endpoint designed for high-volume, low-latency client-side telemetry.

## 2. Endpoint

```
POST /api/v1/telemetry/web-vitals
```

### 2.1 Authentication

| Aspect | Value |
|---|---|
| Required | No (anonymous) |
| Reason | CWV data contains no PII; auth overhead would add latency and bias samples |
| Rate limiting | IP-based bucket (see §4) |

### 2.2 Request Headers

| Header | Required | Value |
|---|---|---|
| `Content-Type` | Yes | `application/json` |
| `Accept` | No | `application/json` |

### 2.3 Request Body

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["name", "value", "rating", "delta", "navigationType", "timestamp", "path", "sessionId"],
  "properties": {
    "name": {
      "type": "string",
      "enum": ["CLS", "FID", "FCP", "LCP", "TTFB", "INP"]
    },
    "value": {
      "type": "number",
      "description": "Raw metric value. CLS is unitless; others are milliseconds."
    },
    "rating": {
      "type": "string",
      "enum": ["good", "needs-improvement", "poor"]
    },
    "delta": {
      "type": "number",
      "description": "Change from previous value (for cumulative metrics like CLS)."
    },
    "navigationType": {
      "type": "string",
      "enum": ["navigate", "reload", "back-forward", "back-forward-cache", "prerender", "restore"]
    },
    "timestamp": {
      "type": "integer",
      "description": "Unix epoch milliseconds at capture time."
    },
    "path": {
      "type": "string",
      "description": "URL pathname at capture time. No query strings, hashes, or origin.",
      "maxLength": 2048
    },
    "sessionId": {
      "type": "string",
      "description": "Anonymous session-scoped ID for grouping events.",
      "maxLength": 64
    }
  }
}
```

### 2.4 Response

**Success — 202 Accepted**

```json
{
  "status": "accepted",
  "receivedAt": "2024-01-15T09:30:00.000Z"
}
```

**Validation Error — 422 Unprocessable Entity**

```json
{
  "status": "error",
  "message": "Invalid field 'rating': expected one of [good, needs-improvement, poor]",
  "field": "rating"
}
```

**Rate Limited — 429 Too Many Requests**

```json
{
  "status": "error",
  "message": "Rate limit exceeded",
  "retryAfter": 60
}
```

## 3. Delivery Semantics

| Property | Value |
|---|---|
| Durability | Best-effort (fire-and-forget) |
| Ordering | No ordering guarantees |
| Duplication | Idempotent on `(sessionId, name, timestamp)` |
| Retries | Client does not retry; beacon queue handles retries at transport layer |

## 4. Rate Limits

| Scope | Limit | Window |
|---|---|---|
| Per IP | 60 requests | 1 minute |
| Per sessionId | 30 requests | 1 minute |
| Global burst | 10,000 requests | 10 seconds |

## 5. Data Retention

| Stage | Retention | Notes |
|---|---|---|
| Raw events | 30 days | In ClickHouse / TimescaleDB |
| Hourly aggregates | 90 days | Rollup tables |
| Daily aggregates | 1 year | Long-term trend analysis |
| Quarterly reports | Indefinite | Compressed, sampled |

## 6. Privacy & Compliance

- **No PII**: The `path` field must be stripped of query parameters, hashes, and path-embedded identifiers before ingestion.
- **No cookies**: Session tracking uses ephemeral `sessionId` values stored in `sessionStorage`.
- **GDPR**: CWV telemetry is anonymous and falls under legitimate interest. No consent banner required.
- **SOC2**: Data classified as "public" (Tier 1). No encryption-at-rest requirement beyond standard disk encryption.

## 7. Monitoring & Alerting

| Alert | Threshold | Action |
|---|---|---|
| Ingestion rate drop | < 50% of 7-day rolling average for 5 min | Page on-call |
| P95 latency | > 200 ms for 10 min | Page on-call |
| Error rate (5xx) | > 1% for 5 min | Page on-call |
| Rate-limit hit rate | > 10% of total traffic | Create ticket |

## 8. Implementation Notes

### 8.1 Backend (Python / FastAPI)

```python
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

app = FastAPI()

class WebVitalsPayload(BaseModel):
    name: str = Field(..., pattern="^(CLS|FID|FCP|LCP|TTFB|INP)$")
    value: float
    rating: str = Field(..., pattern="^(good|needs-improvement|poor)$")
    delta: float
    navigationType: str
    timestamp: int
    path: str = Field(..., max_length=2048)
    sessionId: str = Field(..., max_length=64)

@app.post("/api/v1/telemetry/web-vitals", status_code=202)
async def ingest_web_vitals(payload: WebVitalsPayload, request: Request):
    # Apply rate limit check here (Redis sliding window)
    # Strip any remaining PII from path
    # Write to Kafka / ClickHouse / TimescaleDB
    return {"status": "accepted", "receivedAt": datetime.utcnow().isoformat()}
```

### 8.2 Client (React)

See `apps/web/src/lib/web-vitals.ts` for the production client implementation.

## 9. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2024-01-15 | Initial specification |
