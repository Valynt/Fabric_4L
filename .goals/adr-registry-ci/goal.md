# Goal: ADR Registry + CI Gate

## User Request

> | **ADR Registry + CI** | Existing ADRs + link ADR→code (auto-verify decision conformance) | Architecture | `make check-adr` | docs/decisions |

## Refined Goal

Ship a machine-checked ADR registry that links existing architecture and implementation decisions to code and fails CI when numbering, indexes, related paths, or declared content rules drift. Canonical architecture ADRs remain in `docs/explanations/adr/`. `docs/decisions/` is a second corpus, not a migration target. The public gate is `make check-adr` (`python scripts/ci/check_adr.py`), wired into GitHub and Depot PR checks in lockstep. Accepted ADRs must name at least one existing related path; `must_contain` / `must_not_contain` apply only where the registry declares them.

## Acceptance Criteria

- [ ] AC1 — Registry file `docs/decisions/adr-registry.yaml` lists every architecture ADR (`ADR-001`…`ADR-047` as present on disk) and every implementation ADR (`0001`…`0005` as present on disk), with `id`, `corpus`, `path`, `status`, and `related[]`. Decision ids that are zero-padded must remain strings in YAML (quoted), not coerced to integers.
- [ ] AC2 — `scripts/ci/check_adr.py` is the public checker. It fails closed on: architecture numbering (reuse `check_adr_numbering.py`), decisions numbering, registry completeness vs files on disk, missing related paths, declared content-rule mismatches, and README index drift (`## ADR Index` / `## Index`).
- [ ] AC3 — `make check-adr` exists, is `.PHONY`, has a `##` help comment, and runs `python scripts/ci/check_adr.py`. It is documented in `docs/development/COMMANDS.md`. It is **not** added to `check-health-ratchets`.
- [ ] AC4 — Both `.github/workflows/pr-checks.yml` and `.depot/workflows/pr-checks.yml` run `python scripts/ci/check_adr.py` (install PyYAML in the step if needed). Commands stay in lockstep (ADR-047).
- [ ] AC5 — `tests/ci/test_check_adr.py` covers pass and fail cases (missing related path, content-rule miss, registry incompleteness and/or index drift) plus a live-repo smoke that the real registry currently passes. Fresh `python -m pytest tests/ci/test_check_adr.py` exits 0.
- [ ] AC6 — Fresh `python scripts/ci/check_adr.py` and `python scripts/ci/check_adr_numbering.py` exit 0 on this worktree. `python scripts/ci/generate_make_task_inventory.py --check` exits 0. `python -m pytest tests/docs/test_command_map.py tests/ci/test_workflow_task_parity.py` exits 0.
- [ ] AC7 — Docs updated so contributors can find the gate: `docs/development/COMMANDS.md`, `docs/governance.md` (or equivalent ADR numbering policy), `docs/development/DISCOVERY_MAP.md`, and both ADR corpus READMEs / template as needed. Architecture ADRs are **not** moved into `docs/decisions/`.
- [ ] AC8 — Inspector independently runs the AC5–AC6 commands and records stdout plus exit codes. Prior-session claims without a fresh run do not count.

## Scope Boundaries

**In scope:**
- Dual-corpus ADR registry YAML and checker
- Tests, Makefile target, GitHub + Depot PR wiring, command inventory/docs
- Optional content rules only where already intended (seeded where the registry declares them)
- Completing any gaps in the in-progress worktree so the Inspector can verify

**Out of scope:**
- Migrating the 47 architecture ADRs into `docs/decisions/`
- Adding `check-adr` to `check-health-ratchets`
- Rewriting stale `docs/explanations/architecture-decisions.md` unless a gate requires it
- Expanding content rules to every ADR
- Frontend/UI work
- Unrelated refactors, dependency upgrades, or weakening other CI gates

## Applicable Project Conventions

**Quality gate command:**
- `python scripts/ci/check_adr.py`
- `python scripts/ci/check_adr_numbering.py`
- `python -m pytest tests/ci/test_check_adr.py`
- `python scripts/ci/generate_make_task_inventory.py --check`
- `python -m pytest tests/docs/test_command_map.py tests/ci/test_workflow_task_parity.py`
- On Unix/make: `make check-adr` (Makefile is Bash-bound; Windows may run the Python entrypoints directly)

**Commit convention:**
- Conventional commits, imperative, ≤72 char title
- Builder: `type(scope): [B] description` plus `Assisted-by: OpenAI:GPT-5.6 Luna`
- Inspector: `chore(scope): [I] description` plus `Assisted-by: OpenAI:GPT-5.6 Sol`
- Project trailer also required: `Co-authored-by: Ona <no-reply@ona.com>`
- Copilot trailer if the environment requires it: `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>`
- One commit per agent per iteration

**Guidelines:**
- `AGENTS.md` (repo root)
- `docs/development/COMMANDS.md`
- `docs/development/DISCOVERY_MAP.md`
- `docs/governance.md`

**Rules:**
- Contract-first; do not silently change API shapes
- GitHub and Depot PR check commands stay in lockstep (ADR-047)
- Public Make targets with `##` must appear in COMMANDS.md
- Never commit secrets
- `CONSTITUTION.md` is not present
