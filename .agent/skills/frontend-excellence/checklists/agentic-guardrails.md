# Agentic Guardrails Checklist

Guardrails govern the agentic component layer: everything between the user's
intent and the backend call must fail **closed** and be **recoverable**.
Apply this to any agent workflow, tool, or streaming integration.

## Input Validation
- [ ] Agent/user input validated against a schema (Zod/JSON Schema) before use
- [ ] Unknown enum values / wrong types → structured rejection, never silent coercion
- [ ] Required fields enforced; optional fields have safe defaults
- [ ] Injection/escaping handled at the boundary (UI text is inert, not rendered as HTML)
- [ ] Tenant ID derived from auth context — never trusted from request body

## Output Validation
- [ ] Agent/tool output validated against the declared output schema
- [ ] Schema mismatch → surfaced as a structured error, not a broken render
- [ ] Sensitive fields (secrets, tokens, PII, cross-tenant data) never rendered

## Timeouts & Resilience
- [ ] Every async call has an explicit timeout (SSE, fetch, agent step)
- [ ] Retry logic with backoff for transient failures (idempotent where possible)
- [ ] Graceful degradation: connection loss → reconnect or clear error state
- [ ] Streaming closes/cleans up on unmount (no leaked EventSource/socket)

## Human-in-the-Loop & Escape Hatches
- [ ] Destructive/irreversible actions require explicit confirmation (or are gated)
- [ ] Long-running agent tasks expose cancel/abort
- [ ] User can always exit a modal flow (Esc, close button, back)
- [ ] Partial/progressive output shown for agentic steps (per streaming reference)

## Security & Governance
- [ ] No dev-auth bypass flags in production paths
- [ ] Audit/logging preserved where applicable (trace ID, tenant ID)
- [ ] Rate limiting considered on agent endpoints
- [ ] Error messages don't leak stack traces, internal tokens, or raw provider output

## Verification
- [ ] Hostile test present: malformed input → structured rejection
- [ ] Denied-behavior test: unauthorized/out-of-tenant access → 401/403
- [ ] `evals` suite runs and passes after any prompt/schema change
