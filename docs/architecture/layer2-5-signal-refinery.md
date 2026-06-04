# Layer 2.5: Signal Refinery

> **Service:** `services/layer2-5-signal-refinery/`
> **Port:** 8007
> **Package:** `layer2_5_signal_refinery`

---

## Purpose

Layer 2.5 sits between **Layer 2 (Extraction)** and **Layer 3 (Knowledge Graph)**. It transforms raw extraction output into trusted, evidence-backed `ValueSignal` objects that downstream layers can consume with confidence.

### Core Responsibilities

1. **Signal Normalization** — Normalize raw L2 extraction output into a canonical `ValueSignal` model
2. **Trust Scoring** — Compute a composite trust score from evidence quality, provenance, and lifecycle state
3. **Lifecycle Management** — Advance signals through a formal state machine (draft → extracted → validated → promoted → superseded)
4. **Evidence Provenance** — Maintain a structured audit trail for every signal
5. **Best-effort L3 Push** — Push refined signals to L3 as Neo4j graph nodes without blocking on L3 availability

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Extraction        Raw ontology-guided entities  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2.5: Signal Refinery (port 8007)                   │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Type Classification  → canonical ValueSignalType   │ │
│  │  Trust Scoring        → composite 0–1 score         │ │
│  │  Lifecycle State      → draft → extracted → ...     │ │
│  │  Evidence Provenance  → structured audit trail       │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Knowledge Graph   Neo4j signal nodes + links    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Agents          Hypothesis / ROI / Business   │
└─────────────────────────────────────────────────────────┘
```

---

## Trust Score Formula

```
trust_score = (
    0.40 * confidence
  + 0.30 * evidence_quality_score
  + 0.20 * provenance_weight
  + 0.10 * lifecycle_bonus
)
```

| Component | Source | Range |
|-----------|--------|-------|
| confidence | L2 extractor output | 0–1 |
| evidence_quality_score | mean(confidence * relevance) across evidence items | 0–1 |
| provenance_weight | human=1.0, ai=0.7, system=0.5 | discrete |
| lifecycle_bonus | validated=1.0, extracted=0.5, draft=0.0 | discrete |

---

## Lifecycle States

| State | Meaning | Who transitions |
|-------|---------|-----------------|
| draft | Initial placeholder or fallback | system |
| extracted | Passed through refinery | L2.5 service |
| validated | Human-reviewed and approved | reviewer via API |
| promoted | Linked to a value driver/hypothesis | agent or analyst |
| rejected | Reviewed and discarded | reviewer via API |
| superseded | Replaced by a newer signal | agent or system |
| expired | Time-bounded signal past TTL | system (planned) |

---

## API Surface

### REST Endpoints (port 8007)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/signals` | Create a ValueSignal |
| GET | `/api/v1/signals` | List signals for account |
| GET | `/api/v1/signals/{signal_id}` | Get single signal |
| PATCH | `/api/v1/signals/{signal_id}` | Partial update |
| DELETE | `/api/v1/signals/{signal_id}` | Soft-delete |
| POST | `/api/v1/signals/{signal_id}/review` | Human review |
| POST | `/api/v1/signals/{signal_id}/promote` | Promote to hypothesis |
| POST | `/api/v1/signals/refine` | Batch refinement from L2 output |
| GET | `/health` | Service health check |

### Authentication

All endpoints require:
- `Authorization: Bearer <token>` header (JWT or API key)
- `X-Tenant-ID: <tenant>` header (RLS-enforced multi-tenancy)

---

## Service Structure

```
services/layer2-5-signal-refinery/
  src/layer2_5_signal_refinery/
    api/
      main.py              # FastAPI app entrypoint
      routes/
        signals.py         # REST API handlers
      auth.py              # JWT/API-key authentication
    services/
      signal_refinery.py   # Core scoring & classification logic
    clients/
      l3_graph_client.py   # Best-effort L3 push client
    repositories/
      signal_repository.py # PostgreSQL persistence
    models/
      db_models.py         # SQLAlchemy models (ValueSignal, EvidenceItem)
    database.py            # Async SQLAlchemy session factory with RLS
    config.py              # Settings (layer3_base_url, db_url, etc.)
    migrations/
      versions/            # Alembic migrations
  tests/                   # Unit & integration tests
  Dockerfile
  pyproject.toml
```

---

## Dependencies

| Dependency | Purpose |
|------------|---------|
| PostgreSQL (asyncpg) | Primary persistence with RLS |
| Redis | Caching and rate limiting |
| Neo4j (via HTTP client) | Best-effort graph push |
| FastAPI + Uvicorn | HTTP API |
| Alembic | Database migrations |
| OpenTelemetry | Observability |

---

## Operational Notes

### Startup

```bash
# Run migrations
uv run --package layer2-5-signal-refinery alembic upgrade head

# Start service
uv run --package layer2-5-signal-refinery uvicorn layer2_5_signal_refinery.api.main:app --port 8007
```

### Health Check

```bash
curl http://localhost:8007/health
```

### Testing

```bash
# Run all L2.5 tests
pytest services/layer2-5-signal-refinery/tests/ -v

# Verify trust score computation
pytest services/layer2-5-signal-refinery/tests/test_signal_refinery.py -v

# Verify L3 push resilience (L2.5 should survive L3 being down)
pytest services/layer2-5-signal-refinery/tests/test_l3_client.py -v
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `REDIS_URL` | — | Redis connection string |
| `LAYER3_BASE_URL` | `http://layer3:8001` | L3 service URL for graph push |
| `JWT_SECRET` | — | Shared JWT secret for auth |
| `API_PORT` | 8007 | Service listen port |

---

## L3 Push Behavior

- After create/refine, L2.5 pushes the signal to L3 via `POST /api/v1/graph/signals`
- Push is **best-effort, non-blocking** — created via `asyncio.create_task()`
- L2.5 remains fully operational if L3 is down
- L3 persists signals as Neo4j nodes with `MERGE` on `(id, tenant_id)` for idempotency

---

## Related

- [ADR-020: Layer 2.5 Signal Refinery](../explanations/adr/ADR-020-layer-2-5-signal-refinery.md) — Decision record
- [Layer 2 Extraction API](../reference/layer2-extraction-api.md) — Raw extraction output format
- [Layer 3 Knowledge Graph API](../reference/layer3-knowledge-api.md) — Signal persistence endpoint
- [Layer 4 Agents API](../reference/layer4-agents-api.md) — Signal consumption

---

*Last updated: 2026-06-04*
