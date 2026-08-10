# AGENTS — services/layer4-agents (L4, port 8004)

Scoped instructions; universal rules live in the root `AGENTS.md`.

## Responsibility

LangGraph workflows, ROI calculator, business case generation, checkpoints,
agent orchestration. AuditOrchestrator router mounts at `/v1/repo-audit`
(legacy audit-log router remains at `/v1/audit`).

## Canonical runtime path

`services/layer4-agents/src/layer4_agents/` — all net-new logic lands here
(see `docs/reference/layer-runtime-path-governance.md`). API routes:
`services/layer4-agents/src/layer4_agents/api/routes/`
(`src/api/routes/` contains thin compatibility shims only — do not add logic there).

## Layer rules

- Treat prompts, tools, skills, and workflow state as versioned architecture.
- Preserve checkpoint/resume behavior.
- Core orchestration stays provider-agnostic; provider-specific logic lives in
  adapters — never hardcode OpenAI/Anthropic/Together specifics in workflows.
- Agent outputs are structured, versioned, and schema-validated against the
  contracts consumed by the UI and downstream L5/L6 services.
- AI retrieval, prompts, memory, tools, and traces remain tenant-scoped;
  unauthorized tool invocations are rejected and audited.

## Validation

```bash
make test-layer4
make lint-layer4
make typecheck-layer4
make check-layer4-boundaries
make evals   # required for agent/prompt changes (needs OPENAI_API_KEY)
```
