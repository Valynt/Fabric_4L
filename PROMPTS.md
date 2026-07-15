# Fabric_4L Agent Remediation Prompts

This document contains repo-native, finding-scoped execution prompts for Codex/AI agents to autonomously execute the remediation roadmap. Each prompt is structured with explicit constraints, validation commands, and Definition of Done (DoD) to ensure safe, verifiable execution within the repository's governance framework.

---

## Sprint 1: Safety Baseline and Visibility

### Task SEC-002: Rotate Exposed MCP Token
```yaml
---
mode: agent
description: Document the requirement to rotate the exposed MCP/Repowise token and update security guidelines.
tools: ['codebase', 'search', 'editFiles']
---
```
**Task:** SEC-002 documentation and verification support only.

The MCP bearer token was exposed in a prior prompt. Do not print it. Do not use it.
Create a short security note in the appropriate docs explaining:
- Repowise/MCP tokens must never be pasted into prompts or committed files.
- They must be stored in an approved secret manager or local uncommitted env file.
- Exposed tokens must be revoked and replaced.

**Workflow:**
1. Inspect `SECURITY.md` and `docs/development/REPOWISE.md` if present.
2. Make the smallest documentation change.
3. Run docs/static checks only if available.
4. Commit and prepare PR.

**Human action required:**
- Revoke old token.
- Issue replacement.
- Store replacement securely.

---

### Task SEC-001: Least-Privilege PR Workflow Permissions
```yaml
---
mode: agent
description: Reduce GitHub Actions permissions in the PR workflow to least privilege.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** SEC-001 only.

**Goal:** Reduce `.github/workflows/pr-checks.yml` top-level GitHub Actions permissions to least privilege.

**Constraints:**
- Preserve workflow name and job names.
- Preserve required check names.
- If any job needs write permissions, scope permissions at that job only and add a short comment explaining why.
- Do not change unrelated workflow logic.
- Do not modify `security-gates.yml` in this task.

**Validation:**
- `make check-workflow-references`
- `make check-workflow-registry`
- `python scripts/ci/generate_workflow_index.py --check` (if dependencies are available)

*If validation cannot run due to missing environment deps, report it as warning, not pass.*

**Commit:** `fix(ci): reduce pr workflow permissions`

---

### Task AGENT-001: Fix Missing .windsurf/AGENTS.md Reference
```yaml
---
mode: agent
description: Resolve the root AGENTS.md reference to .windsurf/AGENTS.md.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** AGENT-001 only.

**Goal:** Resolve the root `AGENTS.md` reference to `.windsurf/AGENTS.md`.

**Steps:**
1. Inspect `AGENTS.md`, `CLAUDE.md`, `docs/AGENTS.md`, and any `.windsurf` files.
2. If `.windsurf/AGENTS.md` is intentionally absent, update `AGENTS.md` to point to the actual canonical agent registry.
3. If the registry should exist, create the minimal `.windsurf/AGENTS.md` with pointers to canonical instructions, without duplicating the entire root `AGENTS.md`.

**Validation:**
- `rg --files -g 'AGENTS.md' -g 'CLAUDE.md' -g '.windsurf/**' -g '.cursor/**' -g '.github/copilot-instructions.md'`
- markdown/link check if available

**Commit:** `docs(agents): fix agent registry reference`

---

### Task DOC-002: Reconcile README Quickstart
```yaml
---
mode: agent
description: Make README.md Quickstart align with AGENTS.md and docs/development setup guidance.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** DOC-002 only.

**Goal:** Make `README.md` Quickstart align with `AGENTS.md` and `docs/development` setup guidance.

**Constraints:**
- Do not invent commands.
- Do not claim `make setup` starts infra or applies migrations unless Makefile proves it.
- Prefer linking to `docs/development/BUILD_SYSTEM.md`, `docs/development/COMMANDS.md`, and `AGENTS.md`.
- Keep README quickstart short.

**Validation:**
- Inspect Makefile setup target
- No tests required unless docs check exists

**Commit:** `docs(readme): align quickstart with canonical setup`

---

## Sprint 2: Testing and Type Trust

### Task TEST-001: Skip/Xfail Governance Ratchet
```yaml
---
mode: agent
description: Improve pytest skip/xfail governance without removing tests.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** TEST-001 only.

**Goal:** Improve pytest skip/xfail governance without removing tests.

**Files likely involved:**
- `config/ci/pytest_skip_allowlist.yaml`
- `config/ci/pytest_skip_baseline.json`
- `config/ci/test_skip_register.yaml`
- `scripts/ci/check_pytest_skip_governance.py`
- `scripts/ci/check_test_skip_governance.py`
- `Makefile`
- `.github/workflows/pr-checks.yml` (only if needed)

**Constraints:**
- Do not delete skips just to reduce counts.
- Add owners, expiry, category, and rationale where missing.
- Preserve existing CI behavior unless tightening is explicitly safe.
- Add tests for the governance checker if changing checker logic.

**Validation:**
- `make check-pytest-skip-governance`
- `python scripts/ci/check_test_skip_governance.py --register config/ci/test_skip_register.yaml --write-report artifacts/test-skip-governance.json`
- targeted pytest for checker tests if present

**Commit:** `test(ci): ratchet pytest skip governance`

---

### Task QUAL-001: Type-Escape Baseline and Ratchet
```yaml
---
mode: agent
description: Add a CI ratchet for net-new Any/type-ignore/as-any usage, excluding generated files.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** QUAL-001 only.

**Goal:** Add a CI ratchet for net-new `Any`/`type: ignore`/`as any` usage, excluding generated files.

**Constraints:**
- Do not attempt to fix all type escapes.
- Exclude generated directories:
  - `apps/web/src/api/generated/**`
  - `packages/platform-contract/src/typescript/generated/**`
  - `sdk/python/src/valuefabric/generated/**`
- Add a baseline file under `config/ci/`.
- Add a script under `scripts/ci/`.
- Add tests for the script.
- Add Makefile target.
- Optionally wire into PR checks only after local target passes.

**Validation:**
- `python scripts/ci/<new_script>.py --check`
- `pytest tests/ci/<new_test>.py`
- `make typecheck` if feasible
- `pnpm --dir apps/web run typecheck` if feasible

**Commit:** `test(ci): add type escape ratchet`

---

### Task DOC-THREAT: Add Root Threat Model
```yaml
---
mode: agent
description: Add a root THREAT_MODEL.md as an index and initial threat model.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** Add a root `THREAT_MODEL.md` as an index and initial threat model.

**Scope:**
- No source code changes.
- Read `SECURITY.md`, `AGENTS.md`, `docs/contract.md`, docs/governance docs, `tests/security` README.
- Cover auth, tenant isolation, contracts, AI-agent workflows, CI supply chain, data stores, secrets, frontend trust boundaries, and operational controls.
- Link to existing tests and CI gates where possible.
- Mark unverified areas explicitly.

**Validation:**
- markdown link check if available
- `rg` to confirm linked files exist

**Commit:** `docs(security): add repository threat model`

---

## Sprint 3: Ownership and CI Clarity

### Task DOC-CODEOWNERS: Add CODEOWNERS
```yaml
---
mode: agent
description: Create CODEOWNERS with sensible ownership groups/placeholders.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** Add CODEOWNERS.

**Goal:** Create `CODEOWNERS` with sensible ownership groups/placeholders for:
- `apps/web`
- `services/layer1-ingestion`
- `services/layer2-extraction`
- `services/layer3-knowledge`
- `services/layer4-agents`
- `services/layer5-ground-truth`
- `services/layer6-benchmarks`
- `contracts`
- `packages/shared`
- `infra/k8s/terraform/compose`
- `.github/workflows`
- security and CI scripts
- docs

**Constraints:**
- If actual GitHub teams are unknown, use clearly marked placeholder teams and include `TODO` requiring org owner replacement before enforcement.
- Do not pretend owners are real if they are inferred.

**Validation:**
- Ensure `CODEOWNERS` syntax is valid if a local checker exists.
- Otherwise perform static review.

**Commit:** `chore(governance): add code ownership map`

---

### Task CICD-001: CI Gate Map
```yaml
---
mode: agent
description: Create an authoritative CI gate map.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** CICD-001 only.

**Goal:** Create `docs/development/CI_GATES.md` or update existing development docs with an authoritative CI gate map.

**Inspect:**
- `.github/workflows/*.yml`
- `Makefile`
- `package.json`
- `docs/development/COMMANDS.md`
- `docs/development/BUILD_SYSTEM.md`

**Include:**
- workflow name
- trigger
- required/advisory/scheduled/release-only classification
- owner
- main command(s)
- artifact(s)
- expected runtime if known
- common failure triage
- whether it requires secrets, Docker, or live services

**Validation:**
- `rg` for workflow names
- markdown link check if available

**Commit:** `docs(ci): document quality gate map`

---

### Task REL-001: Root Runbook / Operations Entry Point
```yaml
---
mode: agent
description: Add root RUNBOOK.md or OPERATIONS.md that routes responders to canonical operational docs.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** REL-001 only.

**Goal:** Add root `RUNBOOK.md` or `OPERATIONS.md` that routes responders to canonical operational docs.

**Inspect:**
- `ops/README.md`
- `ops/incident/README.md`
- `docs/operations/README.md`
- `docs/operations/runbooks/README.md`
- `docs/runbooks/README.md`
- `production-readiness/README.md`
- `.github/workflows/dr-drill.yml`
- `.github/workflows/prod-readiness.yml` if present

**Include:**
- first 15 minutes of incident response
- where to find runbooks
- rollback/deploy pointers
- DR/backup verification pointers
- secret/credential expiration pointers
- escalation placeholders

**Validation:**
- markdown links
- no runtime tests required

**Commit:** `docs(ops): add root runbook entry point`

---

## Sprint 4: Hotspot Refactors

### Task ARCH-001A: Characterize Layer 4 Analysis Route
```yaml
---
mode: agent
description: Add characterization tests for services/layer4-agents/src/layer4_agents/api/routes/analysis.py before any refactor.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** ARCH-001A only.

**Goal:** Add characterization tests for `services/layer4-agents/src/layer4_agents/api/routes/analysis.py` before any refactor.

**Constraints:**
- Do not refactor implementation in this task unless needed for testability and approved.
- Focus on current behavior, response shape, error shape, auth/tenant behavior, and contract expectations.
- Check existing Layer 4 tests first and avoid duplicates.

**Validation:**
- `pytest services/layer4-agents/tests/<targeted_tests>.py`
- `make test-layer4` if feasible
- `make contract-tests` if feasible

**Commit:** `test(layer4): characterize analysis route behavior`

---

### Task ARCH-001B: Refactor Layer 4 Analysis Route
```yaml
---
mode: agent
description: Refactor Layer 4 analysis route into smaller internal modules without changing behavior.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** ARCH-001B only.

**Goal:** Refactor Layer 4 analysis route into smaller internal modules without changing behavior.

**Prerequisite:** ARCH-001A tests must exist and pass.

**Constraints:**
- No public API shape changes.
- No OpenAPI drift unless contract update is explicit.
- Preserve tenant context and auth behavior.
- Keep provider-specific logic out of core orchestration.

**Validation:**
- targeted Layer 4 tests
- `make test-layer4`
- `make contract-tests`
- check generated API drift if applicable

**Commit:** `refactor(layer4): split analysis route internals`

---

### Task ARCH-001C: Frontend Hotspot Refactor
```yaml
---
mode: agent
description: Safely modularize frontend hotspot.
tools: ['codebase', 'search', 'runCommands', 'editFiles']
---
```
**Task:** ARCH-001C only.

**Goal:** Refactor frontend hotspot into smaller internal modules without changing behavior.

**Constraints:**
- Before modifying `apps/web`, read `DESIGN.md` and `apps/web/DESIGN.md` if present.
- Reuse existing components and patterns.
- Do not introduce a new UI library.
- Preserve horizontal tabs/right-rail conventions.
- Test behavior, not implementation details.

**Validation:**
- targeted component tests
- `pnpm --dir apps/web run test`

**Commit:** `refactor(web): split frontend hotspot`
