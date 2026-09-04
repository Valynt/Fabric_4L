# AI Repository Memory

<!-- markdownlint-disable MD013 -->

This file records a small set of verified, durable repository facts. It is not a task log or the
live remediation ledger. Before acting on a status claim, consult the canonical source and verify
it against the current tree.

## Stable Decisions

- The platform is contract-first. Cross-layer behavior is governed by
  [`docs/contract.md`](../docs/contract.md) and the schemas under [`contracts/`](../contracts/).
- Maintained shared identity imports use `value_fabric.shared.identity.*`.
- Canonical architecture decisions live in
  [`docs/explanations/adr/`](../docs/explanations/adr/).
- The monorepo uses pnpm `10.34.5`; npm and yarn are not supported for canonical workspaces.
- The root [`AGENTS.md`](../AGENTS.md) is the authoritative agent and contributor instruction file.

## Canonical Live Status

| Topic | Source of truth |
| --- | --- |
| Remediation status and closure evidence | [`docs/governance/audit-remediation-sprint-register.md`](../docs/governance/audit-remediation-sprint-register.md) |
| Remediation board and high-risk queue | [`docs/governance/audit-remediation-board.md`](../docs/governance/audit-remediation-board.md) |
| CI gates, owners, and local commands | [`docs/development/CI_GATES.md`](../docs/development/CI_GATES.md) |
| Compatibility debt | [`docs/governance/compatibility-debt-registry.md`](../docs/governance/compatibility-debt-registry.md) |
| Code ownership | [`CODEOWNERS`](../CODEOWNERS) |

Do not copy open-item lists into this file. Those lists become stale and can cause agents to repeat
completed work.

## Repository-Health Reconciliation

The following older audit items are resolved on `main` and must not be presented as open work:

- `SEC-001`: PR workflow permissions were reduced and are covered by workflow-permission tests.
- `AGENT-001`: the `.windsurf/AGENTS.md` coordination entry point exists.
- `DOC-002`: setup documentation separates dependency installation, infrastructure startup, and
  migrations.
- `QUAL-001`: the type-escape baseline and ratchet exist under `config/ci/` and `scripts/ci/`.
- `CICD-001`: [`docs/development/CI_GATES.md`](../docs/development/CI_GATES.md) is the authoritative
  CI inventory.

`ARCH-001` is incremental remediation, not a single closure claim. Consult current tests, merged
PR evidence, and the live remediation register before scheduling additional hotspot work.

## Documentation Reconciliation Rule

PR #1010 (`docs/refactor-methodology`) was superseded because it mixed useful documentation ideas
with stale status, invalid security examples, and changes already replaced on `main`. Reuse ideas
only after checking current canonical files and executable behavior; never cherry-pick that branch
wholesale.
