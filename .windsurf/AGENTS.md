# Autonomous Agent Fleet Registry

This file is the coordination entry point for automated agents working in Value Fabric. It is
not a policy source: the repository-root [`AGENTS.md`](../AGENTS.md) routes shared guidance,
nearest package `AGENTS.md` files own scoped conventions, and canonical docs own architecture
and governance policy.

## Fleet roles

| Role | Responsibility | Boundary |
|---|---|---|
| Primary agent | Own the user request, plan, integration, validation, and final report. | Must preserve contract, tenant, layer, and governance invariants. |
| Task agent | Complete an explicitly delegated, bounded subtask. | Must not broaden scope or overwrite another agent's work. |
| Review agent | Check a proposed change against repository contracts and evidence. | Reports findings; changes code only when explicitly assigned. |

## Coordination contract

1. The primary agent remains accountable for the complete result and delegates only work that
   can be isolated safely.
2. Every task assignment names its scope, source-of-truth files, expected output, and validation.
3. Agents communicate discoveries that affect shared contracts before making dependent changes.
4. Agents preserve unrelated work and never assume an uncommitted change belongs to them.
5. Conflicts are resolved in this order: user instruction, root `AGENTS.md`, the nearest nested
   `AGENTS.md`, then supporting `.windsurf/` documentation.
6. The primary agent integrates results, runs the required verification, and reports residual
   risk. Delegation never substitutes for verification.

Runtime-specific plans and workflows under `.windsurf/` may describe execution tactics, but they
cannot weaken or replace the canonical repository instructions.
