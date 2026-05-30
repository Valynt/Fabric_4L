# Live LLM Provider Evidence Handoff

This handoff documents the launch evidence required for live or provider-sandbox LLM validation. It prepares the evidence path only; it does not call a live provider, create launch evidence, or close the Live LLM provider gate.

## Current Repository Coverage

Repository-local coverage exists for several behavior contracts:

- Layer 4 OpenAI provider wiring in `services/layer4-agents/src/layer4_agents/services/llm_provider.py`.
- Mock-disabled live frontend guardrails through `apps/web/scripts/live-env-guard.mjs` and live Playwright scripts.
- Grounding, refusal, fact/assumption labels, tenant-scoped evidence, and prompt-injection behavior in `services/layer4-agents/tests/test_agent_grounding_and_refusal.py`.
- LLM token and cost tracking in `services/layer4-agents/tests/test_llm_cost_tracking.py` and `services/layer4-agents/tests/test_llm_cost_metrics.py`.

These tests are not live/provider-sandbox evidence. They prove local behavior contracts only.

## Open Implementation Gap

No canonical live/provider-sandbox LLM evidence runner was found in the repository. The launch gate remains open until a real provider or approved provider sandbox run is executed and the redacted evidence bundle is attached.

A non-evidence schema example is available at:

```text
docs/examples/live-llm-provider-evidence.example.json
```

The example is marked `template_only=true` and `evidence_status=NOT_EVIDENCE`. It must not be attached as launch evidence.

## Required Environment

A real evidence run requires:

- live or provider-sandbox LLM credentials from an approved secret manager
- `OPENAI_API_KEY` or the approved provider-specific equivalent, never printed or committed
- release-candidate SHA
- mock fallback disabled: `VITE_USE_MOCKS=false`, `VITE_ENABLE_MOCK_FALLBACK=false`, `MSW` unset or false, and `MOCKS_ENABLED` unset or false
- tenant, account, workflow, and trace context for the launch workflow under test
- Layer 4 running in a staging, provider-sandbox, or production-like environment
- redacted logs and artifacts retained outside raw terminal scrollback

OpenAI is the currently discoverable Layer 4 live provider path. Anthropic appears in cost tables and documentation, but no Layer 4 Anthropic provider implementation was found in this pass.

## Required Checks

A passing provider evidence bundle must prove all of the following:

| Check | Minimum evidence required |
|---|---|
| Grounded citations | Response includes tenant-scoped citation IDs or evidence references that can be resolved to the workflow/account context. |
| Fact vs assumption labeling | Output explicitly distinguishes facts, inferences, assumptions, and benchmarks where applicable. |
| Refusal for unsupported claims | Unsupported ROI, fabricated benchmark, cross-tenant, approval-bypass, secret-exfiltration, and similar unsafe requests are refused. |
| Prompt-injection resistance | Hostile user or document instructions do not override system/tool governance. |
| Cost/token tracking | Prompt tokens, completion tokens, model, provider, and cost are captured or emitted through approved metrics/evidence. |
| Traceability | Evidence links provider output to tenant ID, account ID, workflow ID, trace/request ID, and release-candidate SHA. |
| Mock fallback disabled | Run metadata and logs prove no mock provider, MSW, or frontend mock fallback was used. |

## Required Artifact Fields

A real evidence artifact should include, at minimum:

- `release_candidate_sha`
- `environment`
- `provider_configuration.provider`
- `provider_configuration.model`
- `provider_configuration.credentials_redacted=true`
- `provider_configuration.provider_reachable=true`
- mock-control fields proving mocks were disabled
- `workflow_context.tenant_id`
- `workflow_context.account_id`
- `workflow_context.workflow_id`
- `workflow_context.trace_id` or request ID
- grounded citation IDs or redacted resolvable references
- fact/assumption/refusal/prompt-injection check results
- prompt/completion token counts and cost value or metric reference
- redaction statement
- owner sign-off

## Redaction Rules

Do not attach:

- raw provider credentials
- bearer tokens
- private keys
- full customer documents or sensitive prompt payloads
- unredacted production tenant data
- provider raw responses containing sensitive customer content

Attach redacted snippets, hash IDs, metric samples, and resolvable internal artifact references instead.

## What Counts As Evidence

Real Live LLM provider evidence must include:

- output from a real provider or approved provider sandbox
- release-candidate SHA
- mock-disabled proof
- redacted run logs or command transcript
- provider/model and token/cost metadata
- tenant/account/workflow traceability
- grounding/refusal/prompt-injection check outcomes
- owner sign-off

## What Does Not Count As Evidence

The following must not be treated as launch evidence:

- `docs/examples/live-llm-provider-evidence.example.json`
- local unit tests or mocked provider tests
- hand-authored JSON
- runs with `VITE_USE_MOCKS`, `VITE_ENABLE_MOCK_FALLBACK`, `MSW`, or `MOCKS_ENABLED` enabled
- reports without release-candidate SHA
- logs that expose secrets or sensitive customer content
- provider connectivity checks that do not exercise grounded/refusal/cost/traceability behavior

## Status

Live LLM provider evidence remains open until real provider or provider-sandbox output exists and is attached with redacted artifacts, release-candidate SHA, cost/token data, workflow/account/tenant traceability, and owner sign-off.

This handoff does not prove production readiness, does not unblock paid GA, and does not close CI/staging reproducibility.
