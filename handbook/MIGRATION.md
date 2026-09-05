# Migration — legacy agent directories → handbook/

The handbook is the single agent context source of truth. Legacy per-tool directories are
deprecated as context sources; their content remains for reference until migration completes.
Stubs: each directory gets a `DEPRECATED.md` pointer (see bottom).

## Mapping

Inventory reflects verified directory listings; "unverified" dirs exist at root per repo
convention but were not listed — audit before migrating.

| Legacy dir | Verified contents | Migrate what | Handbook replacement |
|---|---|---|---|
| `.claude/` | `settings.json`, `rules/context7.md`, `skills/` (22 `clerk-*` skill dirs + `context7-mcp`) | rules → `handbook/03_implement/README.md` rule sections; clerk-* skills → behavior-card Verification sections (BEH-01 auth surfaces) and `contracts/tool-manifests/` | `handbook/INDEX.md`, `handbook/L2-components/apps-web-pages.md` (Clerk auth anchors) |
| `.kimi/` | `backlog.yaml`, `journal.md` (lightweight) | backlog items → GAP-xx register entries or issues; journal → superseded by `control-plane/product-contract/10_changelog.md` | `control-plane/product-contract/09_gap-register.md`, `10_changelog.md` |
| `.roo/` | unverified | audit; mode/config context → handbook stages | `handbook/01_understand/` … `04_verify/` |
| `.codex/` | unverified | audit; task instructions → handbook stages | `handbook/INDEX.md` + four stages |
| `.windsurf/` | unverified | audit; rules → stage READMEs | `handbook/03_implement/README.md` |
| `.gemini/` | unverified (see also `apps/web/GEMINI.md`) | audit; rules → stage READMEs | `handbook/INDEX.md` |
| `.devin/` | unverified | audit; playbooks → handbook stages | `handbook/01_understand/` … `04_verify/` |
| `.agent/` | `AGENTS.md`, `hooks.json`, `install.json`, `plugins.json`, `skills.json`, `harness/`, `memory/`, `protocols/`, `skills/`, `tools/` | memory/ → `handbook/L1-system/` + behavior cards; protocols/ → stage READMEs; skills/ → `agents/skills/` (Slice S promotion); tools/ → `contracts/tool-manifests/` + card Verification; hooks.json → CI resync job spec | `handbook/L1-system/`, `handbook/L3-implementation/README.md`, `control-plane/behaviors/` |
| `.agents/` | `hooks.json`, `mcp_config.json`, `plugins.json`, `skills.json`, `plugins/`, `rules/`, `skills/` | rules/ → stage READMEs; skills/ → card Verification sections; hooks.json/mcp_config.json → resync/CI wiring | `handbook/` stages, `control-plane/release/` |
| `.ai/` | unverified | audit | `handbook/INDEX.md` |
| `.jr/` | unverified | audit | `handbook/INDEX.md` |
| `.fabric/` | unverified | audit | `handbook/INDEX.md` |

## Migration procedure

1. **Inventory**: list the legacy dir; classify each file as rule, skill, memory, or config.
2. **Relocate semantics, not files**: rules → the matching stage README (`01`–`04`); durable
   system knowledge → `L1-system/` or the relevant `L2-components/` page; executable skills and
   tool descriptions → `contracts/tool-manifests/` or the owning behavior card's Verification
   section; backlog/history → GAP register / contract changelog.
3. **De-duplicate**: if the handbook already covers the content, record the source dir as
   migrated and move on. The handbook wins conflicts.
4. **Mark**: after migration of a dir's content, note the date in its `DEPRECATED.md` stub.
5. **Remove**: legacy dirs are deleted only after (a) all content is migrated or explicitly
   discarded, and (b) one release cycle has passed with the handbook as the sole context source.

## Deprecation rule (effective now)

- New agent context, rules, and workflow knowledge MUST be authored under `handbook/` and
  `control-plane/` only. PRs adding content to legacy agent dirs fail review.
- Existing legacy content remains readable for reference; do not delete outside step 5.
- `DEPRECATED.md` stubs exist in: `.claude/`, `.kimi/`, `.roo/`, `.codex/`, `.windsurf/`,
  `.gemini/`, `.devin/`, `.agent/`, `.agents/`.
