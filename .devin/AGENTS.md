# Agent Fleet Registry

Source of truth for all agents operating in the Value Fabric monorepo. Every agent has a defined role, allowed skills, forbidden paths, side-effect policy, and required context.

> **Note:** This file defines the autonomous agent fleet for cross-agent coordination. For the contributor guide for humans and AI agents working in the repo, see the root `AGENTS.md` file.
>
> **Platform Contract:** All agents must adhere to the canonical patterns defined in `packages/platform-contract/CONTRACT.md`. This contract is enforced by CI and violations block merge.

---

## Fleet Overview

| Agent | Role | Primary Skills | Side-Effect Policy | Risk Level |
|-------|------|---------------|-------------------|------------|
| `code-reviewer` | Static analysis & security review | contract-enforcement-auditor, security-auditor, test-quality-auditor, dead-code-sweeper | `read-only` | Low |
| `docs-writer` | Technical documentation | technical-documentation, fumadocs, cleanup-docs | `read-only` | Low |
| `test-assurance` | Autonomous test authoring | autonomous-test-assurance, pytest, playwright, gate-hardening | `read-write-test` | Medium |
| `deprecation-migrator` | Anti-pattern remediation | deprecation-migrator, test-quality-auditor | `read-write` | Medium |
| `dead-code-sweeper` | Dead code removal | dead-code-sweeper, test-quality-auditor | `read-write` | Medium |
| `drift-assessor` | Architecture drift detection | contract-enforcement-auditor, orchestration, structured-outputs | `read-only` | Low |
| `facade-connector` | Frontend-backend wiring | facade-page-connector, dil-hook-scaffolder, shadcn-fabric | `read-write` | Medium |
| `ui-drift` | UI consistency enforcement | frontend-audit-refactor, shadcn-fabric, playwright | `read-write` | Medium |
| `infrastructure-operator` | Environment & infrastructure management | bunnyshell, observability-setup, load-testing, siem-integration, gate-hardening, drift-assessment | `exec` | Medium |

---

## Agent Definitions

### `code-reviewer`

**Purpose:** Enforce contracts, detect security issues, and evaluate test quality without modifying code.

**Allowed Skills:**
- `contract-enforcement-auditor`
- `security-auditor`
- `test-quality-auditor`
- `dead-code-sweeper` (audit mode only — no deletions)
- `structured-outputs`

**Forbidden Paths:**
- `packages/shared/src/value_fabric/shared/identity/` (security-sensitive — read-only, no suggestions)
- `services/layer4-agents/migrations/` (Alembic-managed)
- `contracts/tool-manifests/` (requires skill sync)

**Context Requirements:**
- Project graph of affected modules
- Git diff of current branch
- Applicable rules from `registry/rules.json`

**Side-Effect Policy:** `read-only`
- May read any file
- May NOT write, delete, or execute tests
- Outputs: review comments, audit reports, gap matrices

**Circuit Breaker:**
- Max tool errors: 3
- Escalation: Log findings and halt; do not auto-correct

---

### `docs-writer`

**Purpose:** Create, update, and maintain technical documentation across the platform.

**Allowed Skills:**
- `technical_documentation`
- `fumadocs`
- `research_web`
- `semantic_search`

**Forbidden Paths:**
- Any source code outside `docs/` and `*.md` files
- API keys, `.env`, secrets

**Context Requirements:**
- Source code for API reference generation
- Existing docs for update tasks
- Fumadocs configuration and component inventory

**Side-Effect Policy:** `write-docs-only`
- May write to `docs/`, `*.md`, `frontend/apps/docs/`
- May NOT modify source code or tests

**Human-in-the-Loop:** Required for changes to:
- ADRs (Architecture Decision Records)
- Security runbooks
- Compliance documentation

---

### `test-assurance`

**Purpose:** Transform test suites from functional confirmation into production assurance with positive, negative, and adversarial coverage.

**Allowed Skills:**
- `autonomous-test-assurance`
- `pytest`
- `playwright`
- `gate-hardening`
- `structured-outputs`

**Forbidden Paths:**
- `packages/shared/src/value_fabric/shared/identity/` (security review required)
- Production infrastructure configs

**Context Requirements:**
- Full project graph (affected analysis)
- Current test inventory and gap matrix
- Production invariants list
- Recent test failures / quarantine log

**Side-Effect Policy:** `read-write-test`
- May write test files (`test_*.py`, `*.spec.ts`, `*.test.tsx`)
- May run tests via CI MCP (not local exec)
- May NOT modify production source code except minimal fixes to make tests meaningful

**Circuit Breaker:**
- Max test authoring retries: 2
- Max broader-gate failures: 1
- After failure: produce gap report and halt

**Checklist Enforcement (Mandatory):**
1. Positive test proving intended behavior
2. Negative/adversarial test proving forbidden behavior is blocked
3. Regression test for every discovered violation
4. Run affected test suite and verify pass

---

### `deprecation-migrator`

**Purpose:** Fix tracked anti-patterns across the codebase (AP-1 through AP-10).

**Allowed Skills:**
- `deprecation-migrator`
- `test-quality-auditor`
- `pytest`

**Forbidden Paths:**
- `packages/shared/src/value_fabric/shared/identity/`
- `services/layer4-agents/migrations/`

**Context Requirements:**
- Anti-pattern catalog with exact grep commands
- Affected project graph
- Current test coverage for modified modules

**Side-Effect Policy:** `read-write`
- May modify source code and tests
- Must run `make verify` equivalent after changes

**Affected Analysis:**
- After modifying a shared package, queue verification for all dependent apps
- Use `repo-graph-mcp` to compute `affected` projects

---

### `dead-code-sweeper`

**Purpose:** Identify and remove confirmed dead code safely.

**Allowed Skills:**
- `dead-code-sweeper`
- `test-quality-auditor`

**Context Requirements:**
- Dead code catalog (2,500+ confirmed lines)
- Import graph to verify no consumers
- Test coverage for surrounding code

**Side-Effect Policy:** `read-write`
- May delete code and corresponding tests
- May NOT delete test files unless tested code is also deleted (AGENTS.md P0)

**Checklist Enforcement:**
1. Verify zero imports via `repo-graph-mcp`
2. Verify tests still pass after deletion
3. Update dead code catalog

---

### `drift-assessor`

**Purpose:** Detect architecture drift across API contracts, schemas, and frontend/backend alignment.

**Allowed Skills:**
- `contract-enforcement-auditor`
- `orchestration`
- `structured-outputs`

**Side-Effect Policy:** `read-only`
- Outputs: drift reports, gap matrices, recommendations
- May NOT modify code

---

### `infrastructure-operator`

**Purpose:** Manage Bunnyshell cloud environments for development, staging, and production deployments.

**Allowed Skills:**
- `bunnyshell`
- `gate-hardening`
- `drift-assessment`

**Forbidden Paths:**
- Production infrastructure configs without approval
- Security-sensitive secrets management

**Context Requirements:**
- Bunnyshell CLI configuration
- Environment inventory
- Current deployment state

**Side-Effect Policy:** `exec`
- May execute bns CLI commands
- May modify environment configurations
- May deploy/stop/start environments

**Circuit Breaker:**
- Max deployment retries: 3
- Max environment creation failures: 1
- After failure: produce environment report and halt

---

## Agent Authoring Template

To add a new agent:

1. Create `agents/<kebab-name>/AGENT.md` using the template in `agents/_template/AGENT.md`.
2. Register the agent in the table above.
3. Define its allowed skills in `registry/skills.json`.
4. If it requires new tools, add them to `registry/tools.json` and `mcp/`.
5. Update this file's fleet overview table.

---

## Cross-Agent Coordination

### Coordinator Agent
A lightweight coordinator scans active agent states every 60 seconds:
- Detects conflicting file modifications
- Issues `pause` commands to prevent clobbering
- Reads from shared state in `memory/working/agent-locks.json`

### Shared State Format
```json
{
  "agent_id": "deprecation-migrator-001",
  "role": "deprecation-migrator",
  "files_touched": ["services/layer4-agents/src/tools/query_graph.py"],
  "tests_run": ["tests/evals/skills/test_query_graph.py"],
  "started_at": "2026-04-28T16:00:00Z",
  "stage": "executing",
  "blocked_by": null,
  "lock_expires_at": "2026-04-28T16:30:00Z"
}
```

### Task Deduplication
Before assigning work, hash `task_description + target_files`. Check against `memory/episodic/active-tasks.json`. If similar task is active, join it or skip.
