# L2 Component — layer4-agents

## Purpose

Agent orchestration layer (`services/layer4-agents/`). Coordinates durable workflows, human
interrupts/review gates, retries, truth gates, narrative generation, and document assembly.
Orchestrates — never redefines — L3 deterministic math (R-4). Consequential AI output requires
Accept/Edit/Reject human disposition (R-3); no silent fallback or mock substitution in production
(R-5, GAP-09).

## Owned journey stages / behaviors

- BEH-02 hypothesis-capture — hypothesis generation/ranking/promotion workflows
  (`src/agents/signal_detection.py`, `src/agents/taxonomy.py`)
- BEH-06 business-case-generation — governed business-case and narrative workflows
- BEH-07 deliverable-rendering — document assembly via tool manifests
  (`contracts/tool-manifests/assemble_document.json`, `generate_section.json`,
  `document_export.json`) — serving path not fully verified; see card BEH-07
- BEH-08 approval-and-publication — human review interrupts and publication gates
- Cross-cutting — agent monitoring surfaces feed `apps/web` pages
  (`AgentWorkflows.tsx`, `CommandCenter.tsx`, `DecisionTrace.tsx`, `IngestionJobs.tsx`)

## Key verified paths

- `services/layer4-agents/src/main.py` — main entry
- `services/layer4-agents/src/api/` — HTTP surface: `main.py`, `app_factory.py`,
  `core_routes.py`, `routers.py`, `middleware.py`, `startup.py`, `tenants.py`, plus
  `routes/`, `schemas/`, `security/`, `websocket/`, `common/`
- `services/layer4-agents/src/agents/` — `base.py`, `signal_detection.py`, `taxonomy.py`
- Other src subdirs: `adapters/`, `config/`, `contexts/`, `contracts/`, `engine/`,
  `feature_flags/`, `harness/`, `integration/`, `interfaces/`, `messaging/`, `metrics/`,
  `models/`, `policies/`, `provenance/`, `registry/`, `services/`, `skills/`, `startup/`
- Top level: `config/`, `manifests/`, `migrations/`, `prompts/`, `skills/`, `tests/`,
  `alembic.ini`, `README.md`, `AGENTS.md`

## Dependencies

- Calls L3 (`services/layer3-knowledge`) for retrieval and deterministic calculation; calls L5
  (`services/layer5-ground-truth`) for truth gates and claim governance.
- Tool surface constrained by `contracts/tool-manifests/` and
  `contracts/agent-registry/` (`compatibility-matrix.json`, `layer4-route-contract-matrix.json`).
- Reached only through `services/api` gateway.

## Primary gates

- **AG-04** security-gates — prompt-injection, tool allowlists, least-privilege, production
  mock-mode prohibition.
- **AG-05** tenant-isolation-and-behavior — tenant-safe prompts, memory, traces, tool arguments.
- **AG-02** code-quality-and-tests — workflow state transitions, deterministic fallback tests.
- **AG-06** production-readiness — durable workflow resume, no duplicate side effects.
