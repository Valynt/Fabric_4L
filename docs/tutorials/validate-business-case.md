# Tutorial: Validate a Business Case

> **Goal:** Review a generated business case, inspect its evidence, and promote validated claims.
> **Time:** 30 minutes
> **Prerequisites:**
> - A completed workflow from [Run an Agent Workflow](./agent-workflow-run.md)
> - Access to Layer 4 and Layer 5 APIs
> - Valid JWT token or API key for the owning tenant

---

## Step 1: Set Context

Use the same tenant and workflow context from the workflow tutorial.

```bash
export TENANT_ID="<tenant-id>"
export BUSINESS_CASE_ID="<business-case-id>"
export AUTH_HEADER="Authorization: Bearer <token>"
```

---

## Step 2: Fetch the Draft Business Case

Layer 4 owns the draft business-case artifact.

```bash
curl "http://localhost:8004/api/v1/business-cases/$BUSINESS_CASE_ID" \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Expected result:

```json
{
  "id": "business-case-id",
  "status": "draft",
  "claims": [
    {
      "claim_id": "claim-1",
      "statement": "The account can reduce onboarding cycle time.",
      "evidence_ids": ["evidence-1"],
      "confidence": 0.78
    }
  ]
}
```

---

## Step 3: Inspect Evidence

Each claim should link to evidence or provenance. Fetch the evidence before
approving any claim.

```bash
curl "http://localhost:8004/api/v1/business-cases/$BUSINESS_CASE_ID/evidence" \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Check that every material claim has:

- A source reference or content hash.
- A tenant-matching evidence owner.
- A confidence score or validation status.
- No unsupported provider raw response in the public payload.

---

## Step 4: Submit Claim Review

Promote only claims that are evidence-backed. Send rejected or ambiguous claims
back for revision.

```bash
curl -X POST "http://localhost:8005/api/v1/truth/reviews" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "business_case_id": "'"$BUSINESS_CASE_ID"'",
    "claim_id": "claim-1",
    "decision": "approve",
    "review_notes": "Evidence references match the tenant and support the claim."
  }'
```

Expected result:

```json
{
  "review_id": "review-uuid",
  "decision": "approve",
  "truth_object_id": "truth-object-id"
}
```

---

## Step 5: Confirm Ground Truth Promotion

Layer 5 should expose the promoted TruthObject.

```bash
curl "http://localhost:8005/api/v1/truth/truth-object-id" \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Expected result:

```json
{
  "id": "truth-object-id",
  "tenant_id": "tenant-id",
  "status": "validated",
  "evidence_count": 1
}
```

---

## Step 6: Check Audit Trail

Validated claims must be auditable.

```bash
curl "http://localhost:8005/api/v1/truth/truth-object-id/audit" \
  -H "$AUTH_HEADER" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Expected result: an audit entry with reviewer, decision, timestamp, and
business-case or claim reference.

---

## Verification Checklist

- [ ] Draft business case is visible only to the owning tenant.
- [ ] Each approved claim has evidence and provenance.
- [ ] Layer 5 creates or updates a TruthObject for approved claims.
- [ ] Rejected claims are not promoted.
- [ ] Audit entries identify the reviewer, tenant, and reviewed claim.

---

## Troubleshooting

### Evidence is missing

Return the claim to draft and rerun evidence grounding from Layer 4. Do not
approve unsupported claims.

### Layer 5 rejects the review

Check that the claim ID belongs to the business case and that the request uses
the same tenant as the authenticated context.

### Audit trail is empty

Confirm audit persistence is enabled and inspect Layer 5 logs:

```bash
docker compose logs layer5
```

---

## Next Steps

| Goal | Next Document |
|------|---------------|
| Understand validation semantics | [Layer 5 API Reference](../reference/layer5-ground-truth-api.md) |
| Operate production review flows | [Operators Guide](../how-to-guides/operators.md) |
| Review governance rules | [Governance](../governance.md) |

---

*Last updated: 2026-06-05*
