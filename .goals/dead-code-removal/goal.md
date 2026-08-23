# Goal: Remove confirmed dead code and add a guard

## User Request

Perform a comprehensive dead code sweep across the codebase, identifying all
unused variables, functions, classes, imports, and code blocks. Provide a
detailed report (removal/refactoring suggestions) while not flagging code that
is conditionally used or reserved for the future. After the analysis phase
(complete), remove the confirmed-dead code and add a regression guard.

## Refined Goal

Remove the ~73 verified-confirmed dead-code symbols identified in the analysis
phase across the six-layer monorepo (Layer1..Layer6, services/api, apps/web,
packages), preserving any public-surface symbol that is re-exported through a
barrel/`__init__.py` or documented as public even if it has no in-repo callers.
Add a dead-code regression guard so new dead symbols fail CI. Run the full repo
quality gates to prove no behavior is broken, then re-run dead-code analysis to
catch any cascading findings.

## Acceptance Criteria

- [ ] Criterion 1: All confirmed-dead symbols with no public/re-export surface are hard-deleted (7 `*_executeResult` TypedDictModel classes in taxonomy.py; Layer2 `ExtractionService` and `SignalExtractionResult`; ~31 confirmed-unused apps/web hooks/mappers/types/constants; remaining confirmed dead symbols across Layer1/Layer3/Layer4/Layer5/services/api and packages that are private or non-re-exported).
- [ ] Criterion 2: Public-surface symbols that ARE re-exported through a barrel/`__init__.py` or documented public for external consumers are preserved (e.g. `add_security_headers`, `close_cache`, `reset_distributed_store`, `invalidate_api_key_cache`, `notify_secret_rotation`, `get_governance_core` — only if verification confirms a public/barrel surface; otherwise deleted).
- [ ] Criterion 3: Dynamic-reference and intentionally-unreachable files are NOT deleted (`.agent/tools/*.py`, `examples/canonical/python/*`, `platform-contract/src/typescript/negative/*.ts`, `docs/runbooks/*.py`, `.githooks/pre-push`, and `ROUTE_MAP`/`ROUTE_TIER_MAP`/`entityColors` which are used internally).
- [ ] Criterion 4: Full repo quality gates pass after removal (ruff lint, mypy typecheck, tsc frontend typecheck, pytest, OpenAPI contract checks) with zero regressions.
- [ ] Criterion 5: A dead-code regression guard is added (e.g. a `check-dead-code` Makefile/lint target wired into CI that fails on newly introduced dead symbols).
- [ ] Criterion 6: Dead-code analysis is re-run and no cascading/new dead-code findings are introduced by the removals.

## Scope Boundaries

**In scope:**
- Hard-delete confirmed-dead private/non-exported symbols across services/*, services/api, apps/web, packages.
- Remove confirmed-unused frontend hooks, mappers, types, constants from apps/web.
- Remove 7 `*_executeResult` TypedDictModel classes from `services/layer4-agents/src/layer4_agents/agents/taxonomy.py`.
- Remove Layer2 `ExtractionService` and `SignalExtractionResult`.
- Add a dead-code regression guard wired into CI.
- Run full-repo quality gates and re-run dead-code analysis to verify no cascade.

**Out of scope:**
- Deleting any symbol that is re-exported through a barrel/`__init__.py` or documented as public for external consumers.
- Deleting dynamic-reference or intentionally-unreachable files (`.agent/*`, `examples/*`, `scripts/*`, `negative/` fixtures, `docs/runbooks/*`, `.githooks/*`).
- Deleting online utilities confirmed used internally (`ROUTE_MAP`, `ROUTE_TIER_MAP`, `entityColors`).
- Broad rewrites, refactoring, or behavior changes beyond symbol removal.
- The 185 medium-confidence "manual_review" findings are NOT auto-deleted; they remain deferred for human review unless re-verified as safely removable.

## Applicable Project Conventions

**Quality gate command:**
- `make verify` (full platform gate: lint, typecheck, contract-compliance, production-readiness).
- Per-layer: `make lint-layer<N>`, `make typecheck-layer<N>`, `make test-layer<N>`.
- Frontend: `pnpm --dir apps/web run lint`, `pnpm --dir apps/web run typecheck`, `pnpm --dir apps/web run test`.
- Contract: `pnpm run check:contract-compliance`, `make contract-tests`, `make check-migration-heads`.

**Commit convention:**
- Conventional commits (default). Builder commits use `type(scope): [B] description`; Inspector commits use `chore(scope): [I] description`. Title ≤72 chars.
- Assisted-by trailer required: `Assisted-by: <PROVIDER>:<MODEL>`. Builder = `OpenAI:GPT-5.6 Luna`; Inspector = `OpenAI:GPT-5.6 Sol`.
- Repo also uses `Co-authored-by: Ona <no-reply@ona.com>` for AI-assisted commits; include both trailers.

**Guidelines:**
- `DESIGN.md` — required reading before modifying `apps/web/`.
- `docs/governance/behavior-first-testing.md` — no critical behavior exists unless tested.
- `docs/contract.md` — canonical platform contract (do not alter response shapes).
- `docs/development/BUILD_SYSTEM.md`, `docs/development/COMMANDS.md`, `docs/development/DISCOVERY_MAP.md`.
- `.agent/AGENTS.md`, `.agent/protocols/permissions.md` — read before any tool call; never modify permissions.md.

**Rules:**
- pnpm-only frontend package manager (no npm/yarn).
- Preserve tenant isolation, API contracts, layer boundaries, source-of-truth paths.
- Do not remove tests; do not weaken governance; do not silently change API response shapes.
- Fail closed for security, tenant isolation, money, workflow, and governance paths.
- Never force push to main/production/staging.