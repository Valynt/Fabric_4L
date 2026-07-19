# AGENTS.md — Contributor Guide for AI Agents and Developers

This file explains how to work safely and effectively in the Value Fabric repository,
whether you are a human developer or an AI coding agent. Read this before making changes.

---

## Codex + Windsurf Bridge

This repository also includes a `.devin/` runtime workspace with agent rules, skills,
workflows, and memory artifacts (renamed from `.windsurf/` in commit `342c3249d`). Codex
should treat `.devin/` as a reference source of project-specific operating guidance, not as
an executable runtime. The remaining `.windsurf/` directory holds Repowise-generated plans
and workflows plus the autonomous fleet coordination contract (`.windsurf/AGENTS.md`).

When working in this repo:

- Read `.devin/README.md` for the runtime layout when the task touches agent behavior.
- Use `.devin/AGENTS.md`, `.devin/CONTEXT.md`, and `.devin/MEMORY.md` as supporting
  guidance for planning, context assembly, and artifact discovery.
- Treat `.devin/rules/`, `.devin/registry/`, `.devin/skills/`, and
  `.devin/workflows/` as versioned project documentation unless the user explicitly asks to
  modify them.
- Prefer this root `AGENTS.md` and `packages/platform-contract/CONTRACT.md` when there is any
  conflict with guidance inside `.devin/` or `.windsurf/`.
- Never assume `.devin/mcp/` manifests are live Codex tools in the current session; use only
  tools actually exposed in the environment.

---

## Repository structure at a glance

```
services/                     # Maintained service deployment layer (apps, migrations, manifests)
  layer1-ingestion/           # Layer 1 service entrypoint + infra wrapper
  layer2-extraction/          # Layer 2 service entrypoint + infra wrapper
  layer3-knowledge/           # Layer 3 service entrypoint + infra wrapper
  layer4-agents/              # Layer 4 service entrypoint + agent artifacts
  layer5-ground-truth/        # Layer 5 service entrypoint + infra wrapper
  layer6-benchmarks/          # Layer 6 service entrypoint + infra wrapper

packages/shared/src/value_fabric/shared/
                              # Shared runtime packages exposed as value_fabric.shared.*

contracts/             # Source of truth for all interfaces
  tool-manifests/      # JSON Schema for every agent tool/skill
  openapi/             # Generated OpenAPI specs per layer (do not hand-edit)
  jsonschema/          # Shared data model schemas

apps/web/              # React + TypeScript UI (Vite)
k8s/                   # Kubernetes manifests
monitoring/            # Prometheus + Grafana
packs/                 # Domain vertical extensions
docs/                  # Architecture docs and runbooks
tests/                 # Cross-layer integration and agent evals
```

---

## Change safety rules

These rules exist because this is a production multi-agent system where behavior
emerges from interactions between agents, tools, and the knowledge graph.

### P0 — Never do these

1. **Do not commit secrets.** No API keys, passwords, or tokens in any file. Use `.env` (gitignored).
2. **Do not modify `packages/shared/src/value_fabric/shared/identity/` without a security review.** This is the
   cross-layer authentication and authorization library. Bugs here affect every service.
3. **Do not modify `services/layer4-agents/migrations/` by hand.** Use Alembic to generate
   new migration files: `alembic revision --autogenerate -m "description"`.
4. **Do not change a tool manifest in `contracts/tool-manifests/` without updating the
   corresponding skill definition in `layer4-agents/skills/`.** Contracts and skills must stay in sync.
5. **Do not remove or weaken existing tests.** If a test is blocking you, understand why before
   touching it. Tests encode behavioral contracts.

### P1 — Be careful with these

- **Provider changes** (`services/layer*/src/`) — These affect live data flows. Changing
  extraction logic can alter the shape of the knowledge graph, breaking downstream agents.
- **Ontology changes** (`packs/*/ontology.json`) — Entity type and relationship changes are
  effectively schema migrations for the knowledge graph.
- **Agent/skill definitions** (`layer4-agents/agents/`, `layer4-agents/skills/`) — Prompt changes
  alter agent behavior. Always add or update evals in `tests/evals/` when changing prompts.

---

## Platform Contract (NEW — read this first)

All cross-layer patterns are governed by the **Platform Contract** in
packages/platform-contract/CONTRACT.md. Before adding any code that touches:

- tenant context propagation
- DB session creation
- middleware / auth flow
- tool invocation boundaries
- agent output shapes
- UI state / routing

Read the contract. The canonical patterns are enforced in CI. Violations block merge.

Key files:
- packages/platform-contract/CONTRACT.md — the contract document
- packages/platform-contract/src/python/canonical/ — reference Python signatures
- packages/platform-contract/src/typescript/ — reference TypeScript types
- docs/platform-contract/DEPRECATION_MAP.md — what not to use and when it becomes an error
- docs/governance/compatibility-debt-registry.md — active compatibility wrappers/shims and removal targets
- docs/reference/migration-reproducibility-invariants.md — mandatory migration invariants, time-travel, and incident reconstruction checklist

## Required verification steps

Before opening a PR, run:

```bash
make verify
```

This runs: conflict-marker scan → NUL-byte scans (`check-no-nul-bytes` across tracked source/config files and `check-python-no-nul-bytes` across tracked `*.py`) → lint → type-check → unit tests → contract tests → build.

### Troubleshooting: merge conflict marker failures

If `make verify` fails in `check-conflict-markers`, open the reported `file:line` entries and remove unresolved Git merge markers (`<<<<<<<`, `=======`, `>>>>>>>`) by completing or redoing the merge, then rerun `make verify`.

For agent/skill changes, also run:

```bash
make evals
```

This runs the golden-trace evaluation suite in `tests/evals/`.

Individual layer commands:

```bash
make test-layer1    # Layer 1 unit + integration tests
make test-layer2    # Layer 2 unit + integration tests
make test-layer3    # Layer 3 unit + integration tests
make test-layer4    # Layer 4 unit + integration tests
make test-frontend  # Frontend unit + type-check
```

### Layer 5 source-contract gate (required)

Before running Layer 5 tests, run:

```bash
python services/layer5-ground-truth/scripts/check_no_duplicate_modules.py
```

This check fails if the canonical Layer 5 tree contains self-recursive shims, mutates `sys.path`, or if the compatibility tree drifts from thin re-export shims:

- `services/layer5-ground-truth/src/layer5_ground_truth` (canonical source-of-truth)
- `value_fabric/layer5` (compatibility shims only)

If it fails, keep the canonical implementation in `services/layer5-ground-truth/src/layer5_ground_truth` and update `value_fabric/layer5` to thin compatibility shims.

---

## How to add a new agent skill

1. Create a skill definition in `layer4-agents/skills/<name>.md`:
   ```markdown
   ---
   name: my-skill
   description: What this skill does
   ---
   # My Skill
   ## Parameters
   - `param1`: Type and description (required)
   ## Steps
   1. Step one
   ## Output
   What is returned
   ```

2. Create the corresponding tool manifest in `contracts/tool-manifests/<name>.json`:
   ```json
   {
     "$schema": "https://json-schema.org/draft/2020-12/schema",
     "name": "my_skill",
     "description": "What this skill does",
     "parameters": {
       "type": "object",
       "properties": {
         "param1": { "type": "string", "description": "..." }
       },
       "required": ["param1"]
     }
   }
   ```

3. Implement the tool function in `services/layer4-agents/src/layer4_agents/tools/`.

4. Register the tool in `services/layer4-agents/src/layer4_agents/tools/__init__.py`.

5. Add a golden-trace eval in `tests/evals/skills/test_<name>.py`.

6. Run `make verify && make evals`.

---

## How to add a new agent

1. Create the agent definition in `layer4-agents/agents/<name>_agent.md` with frontmatter
   listing its allowed skills.
2. Implement the agent in `services/layer4-agents/src/layer4_agents/agents/<name>.py`.
3. Register it in the agent router.
4. Add integration tests in `services/layer4-agents/tests/`.
5. Document its purpose and constraints in the definition file.

---

## How to add a new provider

1. Create the provider adapter in the relevant layer's `src/` directory.
2. Accept configuration via environment variables only — never hardcode credentials.
3. Add the new env vars to `.env.example` if using the legacy template path, or to the relevant service-local env template where applicable.
4. Document the provider in `Providers.md`.
5. Write integration tests that can run without the real provider (use mocks/fixtures).

---

## Debugging with traces

Layer 4 emits OpenTelemetry traces for every agent run and tool call.

To inspect traces locally:
```bash
docker compose up -d jaeger
# Open http://localhost:16686
```

To correlate a failed agent run:
1. Find the `trace_id` in the response or agent log output.
2. Search for it in Jaeger or your observability backend.
3. Inspect the tool call sequence and intermediate outputs.

For production traces, see `monitoring/` for Grafana dashboards.

---

## Coding standards

- **Python**: Follow `ruff` rules (configured in each layer's `pyproject.toml`). Type hints required.
- **TypeScript**: Follow ESLint config in `apps/web/`. No `any` unless unavoidable.
- **Tests**: Deterministic unit tests only — no external calls. Use `pytest-mock` or `unittest.mock`.
- **Commits**: Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `chore:`, `test:`.
- **Secrets**: Use `.env.example` for templates. Never put real values anywhere tracked by git.

## Runtime request limiting canonical module

- Canonical implementation: `packages/shared/src/value_fabric/shared/rate_limiting/tenant_rate_limiter.py`.
- Non-canonical adapters (for compatibility only):
  - `packages/shared/src/value_fabric/shared/identity/rate_limiter.py`
- Rule: adapter modules must delegate through a narrow interface and must not duplicate
  sliding-window state math or Redis counter semantics.
- Contract: HTTP adapters return `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
  `X-RateLimit-Reset`, and `Retry-After` on throttled requests, with body fields
  `detail`, `error`, and `retry_after`.


## Reports/ Artifact Policy and Launch Evidence Authority

`reports/` is a generated diagnostics area, not a default source-of-truth for ship/no-ship decisions.

### Policy

- `reports/` artifacts should only be committed when they are tied to a passing gate/check and include build metadata (at minimum: UTC timestamp, commit SHA, and command/check name).
- Historical failing snapshots (for example pytest outputs containing `errors during collection`) must not remain in active `reports/` paths.
- Historical failing snapshots may be retained only under `reports/archive/<YYYY-MM-DD>-<context>/` with a short README describing date, purpose, and why retention is needed.
- CI enforces this rule through `scripts/ci/check_reports_evidence_policy.py`.

### Authoritative ship/no-ship evidence

For launch decisions, treat the following as authoritative in this order:
1. `docs/launch/launch-blocker-register.md`
2. `docs/launch/environment-dependent-evidence-matrix.md`
3. `docs/launch/final-testing-launch-checklist.md`
4. Gate validator outputs referenced by the checklist (for example `scripts/ci/validate_final_testing_launch_gate.py`)

`reports/` documents can support context but do not override the launch docs above.

### Canonical release evidence packet

Use `scripts/ci/generate_release_evidence_packet.py` as the canonical repository-owned evidence-pack generator. Its canonical outputs are:

- `artifacts/release/evidence-packet/release-evidence-packet.json`
- `artifacts/release/evidence-packet/release-evidence-summary.md`

Do not duplicate evidence-generation logic for alternate layouts. If an external consumer requires `./evidence_pack/`, add an explicit wrapper or documented copy step that copies the canonical outputs into `./evidence_pack/` after generation.

---

## QA audit reproducibility requirement (PR merge triage)

When running `scripts/audit/pr_bug_triage.py`, contributors must use explicit upstream history from `origin/main` (not local branch `HEAD` assumptions).

Required behavior:

- Preflight must verify `origin/main` exists locally; fail fast with a clear remediation message if unavailable.
- The "last 20 PRs" retrieval must be executed against `origin/main`.
- Audit output must record the exact commit window used, including:
  - `start_sha` (oldest commit in the sampled window)
  - `end_sha` (newest commit in the sampled window)
  - full `retrieval_command`

This is required so audit results are reproducible and independently verifiable across machines and CI environments.
