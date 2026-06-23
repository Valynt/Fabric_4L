# Tutorial: Run an Agent Workflow

> **Goal:** Start a Layer 4 agent workflow, monitor its state, and inspect the generated artifacts.
> **Time:** 25 minutes
> **Prerequisites:**
> - Fabric_4L running locally (see [Quickstart](../getting-started/quickstart.md))
> - A tenant and account created from [First Account Setup](./first-account-setup.md)
> - Valid JWT token or API key for that tenant

---

## Step 1: Set Request Context

Export the tenant and account identifiers you will use throughout the tutorial.
Tenant identity must match the authenticated context configured for your token.

```bash
export TENANT_ID="<tenant-id>"
export ACCOUNT_ID="<account-id>"
export AUTH_HEADER="Authorization: Bearer <token>"
```

---

## Step 2: Confirm Layer 4 Is Healthy

Layer 4 owns agent orchestration and workflow state.

```bash
curl "http://localhost:8004/health" \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Expected result:

```json
{
  "status": "healthy"
}
```

---

## Step 3: Start a Workflow

Create a workflow run for account value realization. The exact workflow type
may vary by enabled packs, but the request must stay tenant-scoped.

```bash
curl -X POST "http://localhost:8004/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "workflow_type": "business_case",
    "account_id": "'"$ACCOUNT_ID"'",
    "input": {
      "objective": "Identify value opportunities and draft a business case",
      "time_horizon_months": 12
    }
  }'
```

Expected result:

```json
{
  "workflow_id": "workflow-uuid",
  "status": "queued",
  "account_id": "account-id"
}
```

Save the returned `workflow_id`.

---

## Step 4: Monitor Workflow State

Poll the workflow status until it reaches `completed`, `failed`, or
`needs_review`.

```bash
export WORKFLOW_ID="<workflow-id>"

curl "http://localhost:8004/api/v1/workflows/$WORKFLOW_ID" \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Expected running result:

```json
{
  "workflow_id": "workflow-uuid",
  "status": "running",
  "current_step": "ground_evidence",
  "account_id": "account-id"
}
```

---

## Step 5: Inspect Generated Artifacts

When the workflow completes, fetch its artifacts. The response should include
business-case, evidence, or value-driver references depending on enabled packs.

```bash
curl "http://localhost:8004/api/v1/workflows/$WORKFLOW_ID/artifacts" \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Expected result:

```json
{
  "workflow_id": "workflow-uuid",
  "artifacts": [
    {
      "artifact_type": "business_case",
      "artifact_id": "business-case-id",
      "status": "draft"
    }
  ]
}
```

---

## Step 6: Check Tenant Isolation

Repeat the artifact request with a different tenant header. The request must be
denied or return no cross-tenant data.

```bash
curl "http://localhost:8004/api/v1/workflows/$WORKFLOW_ID/artifacts" \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-ID: other-tenant"
```

Expected result: `401`, `403`, `404`, or an empty tenant-scoped result.

---

## Verification Checklist

- [ ] Layer 4 health endpoint responds.
- [ ] Workflow run is created for the intended tenant and account.
- [ ] Workflow state can be polled by `workflow_id`.
- [ ] Generated artifacts are visible only to the owning tenant.
- [ ] No request trusts tenant IDs from the body instead of authenticated context.

---

## Troubleshooting

### Workflow stays queued

Check Layer 4 worker logs:

```bash
docker compose logs layer4
```

Confirm Redis and the database are reachable.

### Workflow fails during evidence grounding

Confirm Layer 3 and Layer 5 are healthy and that your account has ingested
evidence.

### Artifact request returns 404

Verify `WORKFLOW_ID`, `TENANT_ID`, and token scope. A 404 is expected when the
workflow belongs to another tenant.

---

## Next Steps

| Goal | Next Tutorial |
|------|---------------|
| Review generated claims | [Validate a Business Case](./validate-business-case.md) |
| Add more source evidence | [First Account Setup](./first-account-setup.md) |
| Understand workflow contracts | [Layer 4 API Reference](../reference/layer4-agents-api.md) |

---

*Last updated: 2026-06-05*
