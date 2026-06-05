# Tutorial: First Account Setup

> **Goal:** Create your first tenant, ingest a document, and query the resulting knowledge graph.
> **Time:** 20 minutes
> **Prerequisites:**
> - Fabric_4L running locally (see [Quickstart](../getting-started/quickstart.md))
> - `curl` or an HTTP client (e.g. [HTTPie](https://httpie.io/), [Postman](https://www.postman.com/))
> - Valid JWT token or API key

---

## Step 1: Verify Services Are Running

From the repository root, check that all services are healthy:

```bash
docker compose ps
```

You should see all containers in `running` or `healthy` state.

If any service is down:

```bash
docker compose -f docker-compose.full.yml up -d
```

---

## Step 2: Create a Tenant

Tenants are the top-level isolation boundary in Fabric_4L. All data (ingestion jobs, entities, signals) is scoped to a tenant.

```bash
curl -X POST http://localhost:8004/api/v1/tenants \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "name": "acme-corp",
    "display_name": "Acme Corporation",
    "plan": "pro"
  }'
```

**Expected response:**

```json
{
  "id": "tenant-uuid-here",
  "name": "acme-corp",
  "display_name": "Acme Corporation",
  "plan": "pro",
  "created_at": "2026-06-04T10:00:00Z"
}
```

Save the `id` — you will use it as `X-Tenant-ID` in all subsequent requests.

---

## Step 3: Submit an Ingestion Job

Now ingest a document into your tenant. Layer 1 accepts web URLs, uploaded files, or S3 objects.

```bash
export TENANT_ID="<tenant-uuid-from-step-2>"

curl -X POST http://localhost:8000/api/v1/ingestion/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "source_url": "https://example.com/sample-document.html",
    "source_type": "web",
    "priority": "normal"
  }'
```

**Expected response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2026-06-04T10:05:00Z"
}
```

---

## Step 4: Monitor Ingestion Progress

Poll the job status until it reaches `completed`:

```bash
curl "http://localhost:8000/api/v1/ingestion/jobs/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer test-token" \
  -H "X-Tenant-ID: $TENANT_ID"
```

**Expected final status:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "extracted_entities": 12,
  "completed_at": "2026-06-04T10:06:30Z"
}
```

Typical processing time is 30–90 seconds depending on document size.

---

## Step 5: Query the Knowledge Graph

Once ingestion completes, extracted entities are available in the Layer 3 Knowledge Graph.

### List all entities for your tenant

```bash
curl "http://localhost:8001/api/v1/entities?limit=10" \
  -H "Authorization: Bearer test-token" \
  -H "X-Tenant-ID: $TENANT_ID"
```

### Search by keyword

```bash
curl "http://localhost:8001/api/v1/entities?query=sample" \
  -H "Authorization: Bearer test-token" \
  -H "X-Tenant-ID: $TENANT_ID"
```

### Get a specific entity

```bash
curl "http://localhost:8001/api/v1/entities/<entity-id>" \
  -H "Authorization: Bearer test-token" \
  -H "X-Tenant-ID: $TENANT_ID"
```

---

## Step 6: Explore Value Signals (Layer 2.5)

The Signal Refinery has normalized the raw extraction output into trusted ValueSignals.

```bash
curl "http://localhost:8007/api/v1/signals?limit=10" \
  -H "Authorization: Bearer test-token" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Each signal includes a `trust_score` (0–1) and `lifecycle_state`. Signals with `trust_score >= 0.7` are ready for agent consumption.

---

## Verification Checklist

- [ ] Tenant created successfully
- [ ] Ingestion job submitted and completed
- [ ] Entities visible in Knowledge Graph (Layer 3)
- [ ] ValueSignals visible in Signal Refinery (Layer 2.5)
- [ ] All requests include `X-Tenant-ID` header and return 200

---

## Troubleshooting

### "Connection refused" on any endpoint

Check service status:
```bash
docker compose ps
# If layer1 or layer3 is unhealthy:
docker compose logs <service-name>
```

### "401 Unauthorized"

Verify your `Authorization` header and that the JWT secret matches between `.env` and the running services.

### "403 Forbidden" or missing tenant data

Confirm you are passing the correct `X-Tenant-ID` header. RLS silently filters data for other tenants — this is by design.

### No entities after ingestion completes

Wait 60 seconds for async processing, then check:
```bash
# Layer 2 logs
docker compose logs layer2

# Layer 2.5 logs
docker compose logs layer2-5-signal-refinery
```

---

## Next Steps

| Goal | Next Tutorial |
|------|---------------|
| Run an agent workflow | [Run an Agent Workflow](./agent-workflow-run.md) |
| Validate generated claims | [Validate a Business Case](./validate-business-case.md) |
| Create a custom ontology | See [Value Packs](../../packs/) |
| Deploy to production | [Kubernetes Deployment](../../k8s/README.md) |

---

*Last updated: 2026-06-04*
