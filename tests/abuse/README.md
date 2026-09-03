# Abuse Readiness Suite

## What This Suite Validates

This suite centralizes abuse-resistance coverage for rate limits, login throttling, expensive queries, webhook replay, background job quotas, file upload limits, and external API budget limits.

## Production Risks Covered

- One tenant exhausting shared API, worker, model, or search capacity.
- Login and webhook endpoints accepting unbounded replay or brute-force traffic.
- Expensive graph/search queries bypassing tenant quota controls.
- File uploads or external API calls lacking deterministic limits.

## Existing Coverage Aggregated

- `tests/security/test_rate_limit_safety.py`
- `tests/security/test_auth_rate_limiting.py`
- `tests/shared/identity/test_rate_limit_contract.py`
- `tests/unit/l3/test_rate_limiter_algorithms.py`
- `services/layer4-agents/tests/test_tenant_rate_limits.py`
- `services/layer4-agents/src/layer4_agents/services/llm_budget_guardrails.py`
- `services/layer4-agents/tests/test_webhook_security.py`
- `config/production-readiness/tenant_quota_policy.json`

## Known Gaps

- FILE_UPLOAD_RUNTIME_LIMITS: static policy exists, but upload-size enforcement needs a dedicated local behavior seam.
- EXTERNAL_PROVIDER_BUDGET_LIVE_ENFORCEMENT: CI validates policy and model-cost tests only; provider-side budget exhaustion remains environment-specific.

## How To Run

```bash
pytest tests/abuse/
pnpm test:abuse
pnpm ops:quota:check
```

## CI Artifact

CI should publish `artifacts/production-readiness/abuse/junit.xml` and `artifacts/production-readiness/abuse/summary.md`.
