# Contributing to Value Fabric

Thank you for your interest in contributing. Read [`AGENTS.md`](AGENTS.md) first — it covers
repo structure, change safety rules, and how to add agents, skills, and providers.

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 22+ (>=22.12.0) and pnpm 10+
- Docker + Docker Compose
- `make`

### Local development

```bash
# 1. Clone
git clone https://github.com/bmsull560/Fabric_4L.git && cd Fabric_4L

# 2. Configure environment
cp .env.example .env
# Edit .env — fill in OPENAI_API_KEY (or LAYER4_TOGETHER_API_KEY) and JWT_SECRET at minimum

# 3. Start infrastructure
make up
# Or directly: docker compose -f docker-compose.dev.yml up -d

# 4. Install all service dev dependencies (installs into the pytest pipx venv)
make setup

# 5. Install frontend dependencies
pnpm --dir apps/web install

# 6. Run migrations
make migrate

# 7. Verify everything passes
make setup && make test-layer1 test-layer2 test-layer3 test-layer4 test-layer5 test-layer6
make verify
```

---

## Canonical Contract And Governance

Before making architecture, API, frontend, or tenant-boundary changes, read the canonical platform
contract in [`docs/contract.md`](docs/contract.md). It defines the repo's enforced direction for
tenant context propagation, database isolation, middleware/auth flow, tool boundaries, agent output
shape, and UI route/state progression.

Use these companion governance references during onboarding and before opening a PR:

- [`docs/governance.md`](docs/governance.md) for the engineering governance entry points
- [`docs/governance/launch-drift-prevention-sop.md`](docs/governance/launch-drift-prevention-sop.md)
  for required approvals on contract, tenant-isolation, and compatibility-shim changes
- [`.github/pull_request_template.md`](.github/pull_request_template.md) for the required PR
  confirmations covering contract-shape, tenant-isolation, and compatibility-shim impact

If your change affects backend routes, frontend API consumers, or compatibility shims, complete the
governance confirmations in the PR body and update linked contracts, docs, and tests before review.

---


## Workspace scope: canonical vs experimental

The monorepo defaults are scoped to **canonical production roots only**:

- `apps/web`
- `packages/*`
- `services/*`

Directories such as `archive/` and `prototypes/` are treated as **experimental/non-canonical** and are intentionally excluded from default workspace commands. If you need to work there, invoke those paths explicitly instead of relying on root scripts.

Before adding compatibility wrappers or legacy aliases in runtime code, add/update an entry in `docs/governance/compatibility-debt-registry.md` (owner, reason, target removal date).

### Layer 6 placement rule

- Canonical Layer 6 runtime code belongs in `value_fabric/layer6/`.
- `services/layer6-benchmarks/src/` is wrapper-only. Do not add business logic there.
- When a new Layer 6 module needs a compatibility import path, register the wrapper in `scripts/mirrored_files.json` and run:

```bash
python scripts/ci/check_layer6_wrapper_drift.py
python scripts/check_mirrored_files.py
```

Before opening a PR, run:

```bash
pnpm run check:default-scope
```

This sanity check fails if CI would pick up excluded directories through default workspace tooling.

### Lockfile expectations by directory class

- **Canonical runtime/workspace directories** (`apps/web`, `packages/*`, `services/*`): use pnpm/uv only. Commit `pnpm-lock.yaml`/approved `uv.lock` files and do **not** add `package-lock.json` or `yarn.lock`.
- **Prototype/archive directories** (for example `prototypes/`, `archive/`): npm/yarn lockfiles are allowed only when explicitly justified. Current approved exception: `prototypes/ui-prototype/app/package-lock.json`, retained to preserve reproducible prototype setup outside the canonical pnpm workspace.

Any new exception must be added with rationale to `scripts/ci/check_package_manager_policy.mjs` and documented here in `CONTRIBUTING.md`.

---

## Repository root file policy

To keep the repository root stable for discovery and automation, only the following file types are allowed at repo root:

- Core project governance/spec markdown files (for example: `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `RUNBOOK.md`)
- Top-level release/version metadata (`CHANGELOG.md`, `version.txt`, `VERSIONING.md`)
- Required project configuration files used by tooling/CI

Historical or ad hoc outputs (quality reports, test dumps, diagnostics, temporary tables, and one-off audits) must **not** remain at repo root. Archive them under `docs/archive/quality-reports/` instead.

## Coding standards

### Python

- Formatter and linter: **ruff** (configured in each `pyproject.toml`)
- Do **not** add new global Ruff ignores in `[tool.ruff.lint].ignore` for correctness rules
  (especially `F821`, `F811`, `F841`); suppressions must be scoped to the exact line with
  `# noqa: <rule>` and include a short justification.
- Type checker: **mypy** — type hints required on all public functions
- Test runner: **pytest** — 80%+ coverage required on all layers
- No bare `except:` — always catch specific exception types
- Use `async/await` throughout; no blocking I/O in async contexts

### TypeScript / React

- Linter: **ESLint** (configured in `frontend/`)
- Formatter: **Prettier**
- Avoid `any` unless strictly necessary and documented
- Co-locate tests with components using Vitest

### All languages

- No secrets in code — use environment variables
- No commented-out code in PRs
- Keep functions small and focused

---

## Testing requirements

Before submitting a PR:

```bash
make verify   # lint + type-check + unit tests + contract tests
```

If your change touches API routes, OpenAPI contracts, generated clients, or frontend consumers of generated API types, the local pre-push sequence is required:

```bash
pnpm run generate:contracts
pnpm run check:contract-compliance -- --mode fast
```

Use full mode before merge or release preparation:

```bash
pnpm run check:contract-compliance
```

For agent or skill changes, also run:

```bash
make evals    # golden-trace agent evaluations
```

Test categories:

| Category | Location | Rules |
|----------|----------|-------|
| Unit | `services/*/tests/` | Deterministic, no external calls, fast |
| Integration | `services/*/tests/` | May use Docker services, marked `@pytest.mark.integration` |
| E2E | `frontend/e2e/` | Playwright, critical flows only |
| Contract | `tests/contract/` | Validate tool manifest schemas |
| Evals | `tests/evals/` | Golden traces for agent skills |

---

## Pull request process

1. Branch from `main`: `git checkout -b feat/my-feature`
2. Make focused changes — one logical change per PR
3. Ensure `make verify` passes
4. Update `CHANGELOG.md` under `## [Unreleased]`
5. Open a PR with a clear description of **what** and **why**
6. Request review from at least one maintainer

### Commit message format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(layer4): add sensitivity-analysis skill
fix(layer3): correct graph traversal depth limit
docs: update AGENTS.md with provider guide
test(layer2): add extraction golden trace
chore(deps): update ruff to 0.4.x
```

Prefixes: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`, `ci`

---

## Release process

Releases follow [Semantic Versioning](https://semver.org/):

- `MAJOR` — breaking contract or API changes
- `MINOR` — new capabilities, backward compatible
- `PATCH` — bug fixes, no behavior changes

Releases are tagged `vMAJOR.MINOR.PATCH` and documented in `CHANGELOG.md`.
