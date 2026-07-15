# Agent Fleet Registry — Windsurf Runtime

> **Scope:** This file is the cross-agent coordination registry for the Value Fabric monorepo, specifically for agents operating within the Windsurf runtime environment.
>
> **For the full contributor and agent operating contract**, see the root [`AGENTS.md`](../AGENTS.md).
>
> **For the autonomous agent fleet definitions** (roles, skills, side-effect policies), see [`.devin/AGENTS.md`](../.devin/AGENTS.md).
>
> **For the portable agent brain** (memory, skills, protocols), see [`.agent/AGENTS.md`](../.agent/AGENTS.md).

---

## Instruction Hierarchy

```
AGENTS.md (root)                  ← Global non-negotiables, canonical commands, security,
                                     tenant, contract, package-manager rules
         ↓
.windsurf/AGENTS.md (this file)   ← Windsurf-specific runtime bridge and fleet pointer
         ↓
.devin/AGENTS.md                  ← Autonomous agent fleet registry (roles, permissions)
         ↓
.agent/AGENTS.md                  ← Portable agent brain (memory, skills, protocols)
         ↓
docs/AGENTS.md                    ← Documentation writing rules and Diataxis structure
         ↓
services/*/AGENTS.md              ← Service-specific invariants (if present)
```

**Precedence rule:** More specific files override more general ones. The root `AGENTS.md` defines invariants that cannot be overridden.

---

## Windsurf Runtime Notes

- This repository includes a `.windsurf/` runtime workspace with agent rules, skills, workflows, and memory artifacts.
- Treat `.windsurf/` as a **reference source** of project-specific operating guidance, not as an executable runtime.
- When working in this repo, prefer the root `AGENTS.md` canonical commands over any Windsurf-specific shortcuts that contradict them.
- The `.windsurf/plans/` and `.windsurf/workflows/` directories contain planning artifacts; they are **not** authoritative architecture documentation.

---

## Quick Reference

| Need | Go To |
|------|-------|
| Setup commands | [`AGENTS.md` § Setup](../AGENTS.md#setup) |
| Canonical validation commands | [`docs/development/COMMANDS.md`](../docs/development/COMMANDS.md) |
| Build system decisions | [`docs/development/BUILD_SYSTEM.md`](../docs/development/BUILD_SYSTEM.md) |
| Issue routing map | [`docs/development/DISCOVERY_MAP.md`](../docs/development/DISCOVERY_MAP.md) |
| Agent fleet roles | [`.devin/AGENTS.md`](../.devin/AGENTS.md) |
| Agent memory/skills | [`.agent/AGENTS.md`](../.agent/AGENTS.md) |
| Security rules | [`SECURITY.md`](../SECURITY.md) |
| Frontend governance | [`DESIGN.md`](../DESIGN.md) |
| Platform contract | [`packages/platform-contract/CONTRACT.md`](../packages/platform-contract/CONTRACT.md) |

---

*Created by docs/refactor-methodology phase 4 — extracted from root AGENTS.md reference and .devin/AGENTS.md content.*
