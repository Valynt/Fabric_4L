# Repowise MCP Configuration

Repowise is a remote [MCP](https://modelcontextprotocol.io/) server that gives AI
coding agents repository intelligence for this repo (health scores, security
findings, dead-code analysis, risk hotspots, architectural context). It is a
**local development tool for AI agents only** — it is never used by the Value
Fabric runtime, CI gates, or production services.

- Docs: <https://docs.repowise.dev/>
- Server URL for this repository: `https://api.repowise.dev/mcp/bmsull560/fabric_4l`

## Authentication

All clients authenticate with a bearer token supplied via the `REPOWISE_API_KEY`
environment variable. Set it in your shell (or via `infisical run` / your local
`.env`, see `.env.example`). **Never commit a real key** — the checked-in
configs only contain the `${REPOWISE_API_KEY}` placeholder.

```bash
export REPOWISE_API_KEY=<your key>
```

## Client configuration locations

| Agent client | Config file | Notes |
|---|---|---|
| Claude Code | `.mcp.json` (repo root) | Project-scoped `http` server; expands `${REPOWISE_API_KEY}` from the environment |
| Roo Code | `.roo/mcp.json` | `streamable-http` transport |
| Gemini CLI | `.gemini/settings.json` | `httpUrl` transport; expands `${REPOWISE_API_KEY}` |
| VS Code / Copilot | `.vscode/mcp.json` (not committed — `.vscode/` is gitignored) | Create locally; example below |
| Copilot coding agent | Repository **Settings → Copilot → Coding agent → MCP configuration** | Store the key as the `COPILOT_MCP_REPOWISE_API_KEY` Actions secret |

### Example `.vscode/mcp.json` (create locally, not committed)

```json
{
  "servers": {
    "repowise": {
      "type": "http",
      "url": "https://api.repowise.dev/mcp/bmsull560/fabric_4l",
      "headers": {
        "Authorization": "Bearer ${input:repowise-api-key}"
      }
    }
  },
  "inputs": [
    {
      "id": "repowise-api-key",
      "type": "promptString",
      "description": "Repowise API key",
      "password": true
    }
  ]
}
```

## Tools exposed

The server exposes tools referenced by the repo's agent skills and workflows
(e.g. `.devin/skills/repowise-production-readiness/SKILL.md`,
`.windsurf/workflows/repowise-production-readiness.md`):

`get_overview`, `get_health`, `get_security`, `get_risk`, `get_dead_code`,
`get_why`, `get_context`, `get_symbol`, `search_codebase`, `get_answer`.

## Verifying the setup

1. Export `REPOWISE_API_KEY`.
2. Start your agent client and confirm the `repowise` MCP server connects
   (e.g. `/mcp` in Claude Code, or the MCP panel in Roo Code).
3. Run a cheap tool such as `get_overview` and confirm it returns data for
   `bmsull560/fabric_4l`.

If the server fails to connect, check that the key is present in the process
environment of the client (agents launched from GUIs may not inherit shell
exports).
