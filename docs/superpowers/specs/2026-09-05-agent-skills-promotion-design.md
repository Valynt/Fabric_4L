# Slice S — `.agent/skills/` → `agents/skills/` Promotion

**Date:** 2026-09-05
**Status:** Approved (autopilot)
**Effort:** ~1 week, 1 engineer
**Provenance:** v3 plan item S10-B1, pulled forward.

## Problem

The first-party agent skills live in the dot-directory `.agent/skills/`. The
`.agent/` brain is deprecated as the agent-context source of truth
(`.agent/DEPRECATED.md`), and dot-directories are harness-specific, hard to
discover, and invisible to tooling that scans canonical top-level paths.
Promoting the skills to a first-class `agents/skills/` directory makes them
discoverable, gives each skill a versioned machine-readable manifest, and lets
the old path be retired on a tracked schedule via the Compatibility Debt
Registry (CDR).

## Goals

1. Move the 15 first-party skills from `.agent/skills/` to a new top-level
   `agents/skills/` directory.
2. Add a `skill.yaml` manifest to every skill with `apiVersion`,
   `compatibleAgents`, and `deprecatedSince`.
3. Leave a path shim at `.agent/skills/` so existing references keep resolving
   during a transition window, and register that shim in the CDR with a target
   removal date.
4. Update the one runtime consumer (Layer 4 `audit_orchestrator`) to the new
   canonical path with a legacy fallback.
5. Update all live references (agent entry points, lock files, in-skill
   self-references, migration docs).

## Non-Goals

- Moving third-party / vendor skills (`.agents/skills/` clerk, superpowers,
  infisical-*; `.devin/skills/`; `.claude/skills/`). Those are managed by their
  own lock files and install records and are out of scope.
- Colliding with the Layer 4 shim tree. `services/layer4-agents/src/skills/`
  (and `services/layer4-agents/skills/`) is a **different path** and is owned
  by FAB-106. There is **zero overlap** with the new `agents/skills/`.
- Consolidating all skill metadata into `skill.yaml`. Triggers, tools,
  preconditions, and constraints remain in `SKILL.md` frontmatter and
  `_manifest.jsonl` to avoid two sources of truth.

## Scope

**In scope** — the 15 first-party skill directories in `.agent/skills/`:

| Skill | Version (from `_manifest.jsonl`) | Category |
|---|---|---|
| code-quality-improvement | 2026-06-25 | engineering |
| context7-mcp | 2026-06-25 | engineering |
| data-flywheel | 2026-04-25 | operations |
| data-layer | 2026-04-26 | operations |
| debug-investigator | 2026-01-01 | engineering |
| deploy-checklist | 2026-01-01 | operations |
| design-md | 2026-04-26 | design |
| frontend-excellence | 2026-08-28 | engineering |
| git-proxy | 2026-01-01 | operations |
| memory-manager | 2026-01-01 | meta |
| repo-audit | 2026-06-25 | engineering |
| saas-product-design | 2026-05-06 | design |
| skillforge | 2026-01-01 | meta |
| source-intelligence | 2026-05-13 | engineering |
| tldraw | 2026-04-21 | visualization |

Plus the two registry files `_index.md` (human) and `_manifest.jsonl`
(machine). Note: `_manifest.jsonl` lists a 16th entry,
`repowise-production-readiness`, which has **no directory** — it is metadata
only and moves with the manifest, not as a directory.

**Out of scope** — `.agents/skills/`, `.devin/skills/`, `.claude/skills/`, and
the Layer 4 `services/layer4-agents/**/skills/` trees.

## Target Layout

```
agents/
  skills/
    _index.md                 # human registry (moved from .agent/skills/)
    _manifest.jsonl           # machine metadata (moved from .agent/skills/)
    code-quality-improvement/
      SKILL.md                # moved, content unchanged
      skill.yaml              # NEW manifest
    context7-mcp/
      SKILL.md
      skill.yaml
    ...                       # (all 15 skills)
    repo-audit/
      SKILL.md
      config.yaml             # moved
      prompts/                # moved (5 .txt files)
      skill.yaml
    tldraw/
      SKILL.md
      store.py                # moved
      skill.yaml

.agent/skills/
  MOVED.md                    # path shim — pointer only, no skill content
```

The move is a `git mv` so history is preserved.

## `skill.yaml` Manifest

Each skill gains a `skill.yaml` at its root. The manifest carries the three
required promotion fields plus lightweight identity. It deliberately does **not**
duplicate `triggers` / `tools` / `preconditions` / `constraints` — those remain
authoritative in `SKILL.md` frontmatter and `_manifest.jsonl`.

```yaml
apiVersion: fabric.skill/v1
kind: Skill
metadata:
  name: repo-audit
  version: 2026-06-25
  description: Autonomous repository health auditing with scorecard tracking.
  category: engineering
compatibleAgents:
  - claude-code
  - copilot
  - cursor
  - windsurf
  - opencode
  - openclaw
  - hermes
deprecatedSince: null
source: SKILL.md
```

Field semantics:

- `apiVersion: fabric.skill/v1` — manifest schema version. Bump to `v2` on any
  breaking change to the manifest shape.
- `kind: Skill` — fixed discriminator.
- `metadata.name` — must equal the directory name.
- `metadata.version` — copied from the skill's `_manifest.jsonl` entry (the
  single existing source of version truth).
- `metadata.description` — one-line summary from `SKILL.md` frontmatter.
- `metadata.category` — copied from `_manifest.jsonl`.
- `compatibleAgents` — the harnesses that can mount and run the skill. Derived
  from the portable-brain's documented harness support
  (`.agent/AGENTS.md`: Claude Code, Cursor, Windsurf, OpenCode, OpenClaw,
  Hermes) plus `copilot` (this repository's active harness). Extensible list.
- `deprecatedSince` — `null` for all 15 skills (none are deprecated). When a
  skill is later deprecated, set this to the ISO date and mirror it in the CDR.
- `source: SKILL.md` — pointer to the human-readable, trigger-bearing
  definition.

A small generator script (or a one-shot loop) produces the 15 manifests from
`_manifest.jsonl` + each `SKILL.md` frontmatter, so the values are derived, not
hand-typed.

## Path Shim

`.agent/skills/` becomes a **pointer-only** directory containing a single
`MOVED.md`:

```markdown
# Moved

The first-party skills have been promoted to [`agents/skills/`](../../agents/skills/).

This directory is a compatibility shim (CDR entry **COMPAT-SKILLS-001**) and
will be removed by **2026-12-31**. Update references to point at
`agents/skills/<skill-name>/`.
```

Rationale for a pointer file (not a symlink): symlinks are unreliable on
Windows checkouts and are not portable across harnesses. A `MOVED.md` is
deterministic, human- and agent-readable, and trivially removed at end of life.

The shim is **not** a skill source. Lock files point at the canonical
`agents/skills`, not the shim.

## CDR Registration

A new row is added to
[`docs/governance/compatibility-debt-registry.md`](../../governance/compatibility-debt-registry.md)
(the canonical Compatibility Debt Registry). The row must satisfy the parser in
`scripts/ci/compatibility_registry.py` (path in backticks; review metadata must
contain "Platform Architecture" + an ISO date to pass
`has_platform_architecture_approval`):

| ID | Runtime path | Type | Owner | Reason | Target removal date | Review metadata | Post-launch removal ticket |
|---|---|---|---|---|---|---|---|
| COMPAT-SKILLS-001 | `.agent/skills/` | Path shim (directory relocation pointer) | platform-architecture | First-party skills promoted from `.agent/skills/` to `agents/skills/` (Slice S / S10-B1); old path retained as a `MOVED.md` pointer until all consumers migrate. | 2026-12-31 | Platform Architecture approved 2026-09-05. | PLATARCH-REMOVE-SKILLS-001 |

Notes:

- `deprecations.json` is the machine mirror for **contract anti-patterns**
  (`DEP-*`), not for `COMPAT-*` runtime shims — no change needed there.
- `tests/baselines/deprecation-budget.json` tracks deprecated **symbols**
  (doc-comment markers), not path shims — no change needed there.
- **CI label gate:** `scripts/ci/check_shim_change_ack.py` requires the PR
  labels `compat-shim-change` and `compat-owner-ack` when files under a
  registered shim path change. Because this change moves files out of
  `.agent/skills/`, the PR must carry both labels. This is a PR-time action,
  tracked in the plan.

## Layer 4 Runtime Dependency

The only runtime consumer of the old path is the `audit_orchestrator` agent,
which hardcodes `.agent/skills/repo-audit`. It audits **arbitrary** repos, so
the checks must accept both the new canonical layout and the legacy layout
(repos that have not yet migrated).

Changes:

1. **`config.py`**
   - `DEFAULT_YAML_PATH` → `"agents/skills/repo-audit/config.yaml"`.
   - Add `LEGACY_YAML_PATH = ".agent/skills/repo-audit/config.yaml"`.
   - In `ConfigManager.load()`, resolve the YAML path: use the configured path
     if it exists; otherwise fall back to `LEGACY_YAML_PATH` if that exists
     (debug log); otherwise keep the configured path (preserves the existing
     "not found → defaults" behavior).

2. **`catalog_checks.py`**
   - Add a helper `_resolve_skills_root(repo_path) -> Path | None` that returns
     `repo_path / "agents" / "skills"` if it exists, else
     `repo_path / ".agent" / "skills"` if it exists, else `None`.
   - `_check_missing_repo_audit_skill`: resolve the skill dir via the helper
     (`<root>/repo-audit`); present if `SKILL.md` + `config.yaml` exist.
   - `_check_skill_prompts_complete`: resolve the prompts dir via the helper
     (`<root>/repo-audit/prompts`).
   - `_check_llm_guardrails`: scan `<root>` (resolved) for `*.txt` prompt
     guardrails instead of hardcoding `.agent/skills`.
   - Update the human-facing `evidence` / `observed_fact` strings to reference
     the canonical `agents/skills/repo-audit` (mentioning the legacy fallback).

3. **`catalog_definitions.py`**
   - `AGENT-001` `recommended_fix` → "Create `agents/skills/repo-audit` with
     `SKILL.md`, `config.yaml`, and `prompts/`."
   - `AGENT-002` `recommended_fix` → "Add all required prompt files under
     `agents/skills/repo-audit/prompts/`."

A focused unit test is added for `_resolve_skills_root` and the
`_check_missing_repo_audit_skill` fallback (new path present, legacy path
present, neither present) so the dual-layout behavior is pinned.

## Reference Updates

Live references (actively read by harnesses/agents) are updated to the new
path:

| File | Change |
|---|---|
| `CLAUDE.md` | `.agent/skills/_index.md` → `agents/skills/_index.md` |
| `.agent/AGENTS.md` | `skills/_index.md`, `skills/_manifest.jsonl`, `skills/design-md/SKILL.md` → `agents/skills/...` (repo-root-relative), with a note that skills moved out of the brain |
| `skills-lock.json` (root) | entry `.agent/skills` → `agents/skills` |
| `.agents/skills.json` | entry `.agent/skills` → `agents/skills` |
| `.agent/skills.json` | entry `.agent/skills` → `agents/skills` |
| `agents/skills/tldraw/SKILL.md` | `python3 .agent/skills/tldraw/store.py` → `python3 agents/skills/tldraw/store.py` |
| `agents/skills/frontend-excellence/SKILL.md` | `.agent/skills/design-md/` → `agents/skills/design-md/` |
| `agents/skills/frontend-excellence/references/subagent-orchestration.md` | `.agent/skills` → `agents/skills` |
| `agents/skills/_index.md` | internal `skills/...` path references → `agents/skills/...` |
| `handbook/MIGRATION.md` | `.agent/` row: skills target corrected from `contracts/tool-manifests/` to `agents/skills/` (Slice S is authoritative) |
| `.agent/DEPRECATED.md` | add a line noting skills were relocated to `agents/skills/` |

Historical references are **left as-is** (they are records, not live pointers):
`.agent/memory/semantic/DECISIONS.md`, `.goals/**`, and
`docs/maintenance/repo-organization-cleanup-audit.md`.

## Assumptions

1. Scope is the 15 first-party skills in `.agent/skills/` only; vendor skills
   in other dot-directories are untouched.
2. The shim is a `MOVED.md` pointer file, not a symlink (Windows-safe,
   portable).
3. `apiVersion` is `fabric.skill/v1`.
4. `compatibleAgents` is the portable-brain's documented harness set plus
   `copilot`.
5. `deprecatedSince` is `null` for all 15 skills.
6. Lock files reference the canonical `agents/skills`, not the shim.
7. The CDR target removal date is 2026-12-31 (consistent with the quarter-end
   dates used by neighboring entries).

## Validation Plan

1. **Move integrity:** `git status` shows 15 skill dirs + 2 registry files as
   renames (R100) under `agents/skills/`; `.agent/skills/` contains only
   `MOVED.md`.
2. **Manifests:** all 15 `skill.yaml` files parse as YAML and contain
   `apiVersion`, `compatibleAgents`, `deprecatedSince`; `metadata.name` matches
   the directory name.
3. **CDR parse:** `python scripts/ci/compatibility_registry.py`-based parse
   (or a direct `parse_registry` call) returns the new `COMPAT-SKILLS-001`
   entry with a valid ISO target date and Platform-Architecture approval.
4. **L4 behavior:** the new `_resolve_skills_root` unit test passes for
   new-path / legacy-path / neither; the existing
   `test_audit_orchestrator_api.py` suite still passes (no regressions).
5. **Reference sweep:** a repo-wide grep for `.agent/skills` returns only the
   shim (`MOVED.md`), the CDR entry, the L4 legacy-fallback code, and the
   intentionally-untouched historical docs.
6. **Lock files:** all three lock files list `agents/skills` and no longer list
   `.agent/skills`.

## Risks & Mitigations

- **CI shim-label gate** (`check_shim_change_ack.py`): the PR must carry
  `compat-shim-change` + `compat-owner-ack`. Mitigation: add both labels when
  the PR is created (tracked in the plan).
- **A harness still reads `.agent/skills` directly** (bypassing lock files):
  the `MOVED.md` shim tells it where to look, and the L4 fallback keeps the one
  runtime consumer working. Residual risk is low and time-boxed to the shim
  window.
- **`_manifest.jsonl` phantom entry** (`repowise-production-readiness`): no
  directory to move; it stays as metadata. No action beyond moving the file.

## Out-of-Slice Follow-ups (not done here)

- Removing the `.agent/skills/` shim after 2026-12-31 (ticket
  `PLATARCH-REMOVE-SKILLS-001`).
- Promoting vendor skills (`.agents/skills/`, etc.) if ever desired.
- Reconciling `handbook/MIGRATION.md`'s broader `.agent/` → `handbook/`
  migration (separate effort).
