# Registry

Centralized manifest registry for the agent fleet. This is the **single source of truth** for skills, tools, and rules.

> **P0 Rule:** Changing a skill, tool, or rule requires updating this registry. CI validation enforces consistency.

---

## Files

| File | Purpose |
|------|---------|
| `skills.json` | All skills with input/output schemas, versions, side-effect declarations |
| `tools.json` | All tools with MCP routing, rate limits, timeouts, idempotency support |
| `rules.json` | Machine-readable rule engine manifest mapping rules to files and actions |

---

## Validation

Run validation before committing registry changes:

```bash
# When available:
python scripts/ci/validate_registry.py
```

Manual checks:
1. Every skill in `skills/` has an entry in `skills.json`
2. Every tool in `tools.json` maps to an MCP server in `mcp/`
3. Every rule in `rules/*.yaml` has an entry in `rules.json`
4. JSON Schema in `skills.json` matches `contracts/tool-manifests/*.json`

---

## Versioning

- **Skills:** SemVer (`major.minor.patch`). Bump `minor` for new parameters, `major` for breaking changes.
- **Tools:** SemVer tied to implementation version.
- **Rules:** Date-based (`2026.04.28`) with incremental revision.
