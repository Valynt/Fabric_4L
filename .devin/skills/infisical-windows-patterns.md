export MSYS_NO_PATHCONV=1
infisical secrets get --env=dev --path=/layer4-agents OPENAI_API_KEY
```

#### Option 2: Double Slash Prefix
```bash
# Use // to prevent path conversion
infisical secrets get --env=dev --path=//layer4-agents OPENAI_API_KEY
```

#### Option 3: Python Script Path Fix
When calling infisical from Python on Windows, implement path extraction:

```python
def fix_path_for_git_bash(path: str) -> str:
    """Fix paths mangled by Git Bash path translation."""
    import re
    # Check if path was mangled (contains Windows drive letter or tools/Git)
    if re.match(r'^[A-Za-z]:', path) or 'tools/Git' in path or 'tools\\Git' in path:
        # Extract everything after the drive/tools prefix
        match = re.search(r'[tT]ools[/\\][gG]it[/\\](.+)$', path)
        if match:
            actual_path = match.group(1).replace('\\', '/')
            return '/' + actual_path
    return path

# Use in subprocess calls
cmd = ["infisical", "secrets", "get", 
       f"--path={fix_path_for_git_bash('/layer4-agents')}", 
       "OPENAI_API_KEY"]
```

## .infisical.json Configuration

### Minimum Required Fields
```json
{
  "workspaceId": "d0dde515-abae-4f6a-a01c-75e7b713a9ff",
  "defaultEnvironment": "dev",
  "gitBranchToEnvironmentMapping": null
}
```

### Rules
- ✅ Commit `.infisical.json` to git (no secrets, just workspace binding)
- ❌ NEVER commit `.env`, `.env.local`, or files with secret values
- ❌ NEVER hardcode secrets in code

### Common Issues
| Error | Cause | Fix |
|-------|-------|-----|
| "You must provide projectSlug or workspaceId" | Empty workspaceId in .infisical.json | Add workspaceId from Infisical dashboard |
| "Folder with path '/xxx' was not found" | Path doesn't exist OR path mangling | Check path exists in dashboard; use MSYS_NO_PATHCONV=1 |
| "Invalid secret path" | Git Bash converted path | Use MSYS_NO_PATHCONV=1 or // prefix |

## Secret Naming Convention

Use **UPPER_SNAKE_CASE** for all secret names:

```bash
# ✅ Correct
OPENAI_API_KEY
THESYS_API_KEY
CLERK_SECRET_KEY
GHCR_PAT
DATABASE_URL

# ❌ Wrong
databaseUrl          # camelCase
redis-host           # kebab-case
stripe.secret.key    # dotted
```

## Folder Organization Patterns

### Pattern A: By Layer (Canonical)

Fabric_4L uses a single by-layer secret path taxonomy. Each layer/service reads
only the secrets it needs, and runtime injection is driven by `--path=` flags in
`package.json` (`dev:layer1` … `dev:layer6`, `env:dev`, `compose:dev`). This is
the sole supported schema — see `docs/security/secrets-management.md`.

```
/ (root)                     → (unused; secrets live under named paths below)
├── /shared                  → Cross-service config (JWT, rate limits, tenant defaults)
│   └── /shared/auth         → Backend gateway auth (JWT, Clerk, HMAC)
├── /infra                   → Infrastructure credentials (Postgres, Redis, Neo4j, S3)
├── /layer1-ingestion        → L1 crawling + ingestion
├── /layer2-extraction       → L2 extraction + RDF
├── /layer2-5-signal-refinery→ L2.5 signal refinery
├── /layer3-knowledge        → L3 Neo4j / GraphRAG / pgvector
├── /layer4-agents           → L4 LangGraph + LLM provider keys (OPENAI_API_KEY, …)
├── /layer5-ground-truth     → L5 TruthObject validation
├── /layer6-benchmarks       → L6 peer comparison + benchmarks
├── /layer7-billing          → L7 billing
├── /apps/web                → Frontend runtime / build (public VITE_* only)
├── /monitoring              → Observability config
└── /ci                      → CI/CD-only secrets (DEPLOY_KEY, DOCKER_TOKEN)
```

**Why this works:**
- `infisical run --env=dev --path=/layer4-agents -- pnpm dev:layer4` injects
  `/layer4-agents` secrets (plus any inherited) for the L4 service.
- Machine identities scoped to `/layer4-agents` can't read `/ci` secrets.
- Maps 1:1 to the six-layer pipeline and the `package.json` dev scripts.

### Pattern B: By Environment (Single-service, not used here)
For monoliths or when secrets are organized by environment. Fabric_4L does
**not** use this pattern — environments are selected via `--env=dev|staging|prod`,
not via path.

## Authentication Patterns

### Development (Interactive)
```bash
infisical login
# Follow browser authentication flow
```

### CI/CD (Machine Identity - Universal Auth)
```bash
export INFISICAL_CLIENT_ID=<client-id>
export INFISICAL_CLIENT_SECRET=<client-secret>

# Login
infisical login --method=universal-auth \
  --client-id=$INFISICAL_CLIENT_ID \
  --client-secret=$INFISICAL_CLIENT_SECRET
```

### Using Project ID Directly (without login)
```bash
infisical secrets get \
  --env=prod \
  --projectId=d0dde515-abae-4f6a-a01c-75e7b713a9ff \
  --path=/layer4-agents \
  OPENAI_API_KEY
```

## Common CLI Commands

### Get Secret
```bash
# Basic (requires login and .infisical.json)
infisical secrets get --env=dev OPENAI_API_KEY

# With path
infisical secrets get --env=dev --path=/layer4-agents OPENAI_API_KEY

# With project ID (no .infisical.json needed)
MSYS_NO_PATHCONV=1 infisical secrets get \
  --env=dev \
  --projectId=xxx \
  --path=/layer4-agents \
  OPENAI_API_KEY
```

### Set Secret
```bash
MSYS_NO_PATHCONV=1 infisical secrets set \
  --env=prod \
  --path=/layer4-agents \
  OPENAI_API_KEY="sk-xxx"
```

### Runtime Injection
```bash
# Inject secrets into application
MSYS_NO_PATHCONV=1 infisical run --env=dev -- npm run dev

# With watch mode (re-injects when secrets change)
MSYS_NO_PATHCONV=1 infisical run --watch --env=dev -- npm run dev
```

### Export to .env
```bash
# When tools require a .env file
MSYS_NO_PATHCONV=1 infisical export --env=dev > .env

# Keep .env.example up to date
MSYS_NO_PATHCONV=1 infisical secrets generate-example-env --env=dev > .env.example
```

## Key Rotation Workflow

### Prerequisites
1. Infisical CLI installed at `C:\tools\Infisical\`
2. Logged in: `infisical login`
3. `.infisical.json` configured with workspaceId

### Environment Variables for Rotation
```bash
# OpenAI
export OPENAI_MANUAL_KEY="sk-proj-xxx"

# Thesys
export THESYS_MANUAL_KEY="thesys_xxx"

# Clerk
export CLERK_MANUAL_KEY="sk_test_dummy_xxx"

# Registry
export REGISTRY_MANUAL_KEY="ghp_xxx"
```

### Run Rotation
```bash
# Set Git Bash path conversion fix
export MSYS_NO_PATHCONV=1

# Rotate specific provider
python scripts/security/key_rotation.py --provider openai --env prod

# Verify rotation
python scripts/security/verify-keys.py --provider openai --env prod
```

## Anti-Patterns

- ❌ Never commit `.env` files
- ❌ Never hardcode secrets in code
- ❌ Never use same secrets across environments
- ❌ Never pass secrets as CLI arguments (visible in process list)
- ❌ Never bake secrets into Docker images
- ❌ Never use overly broad permissions for machine identities
- ❌ Never ignore Git Bash path mangling on Windows

## Troubleshooting Checklist

1. **"Invalid secret path" error**
   - Set `MSYS_NO_PATHCONV=1`
   - Check path exists in Infisical dashboard

2. **"Folder not found" error**
   - Verify path exists in correct environment
   - Check `.infisical.json` has correct `workspaceId`

3. **"Unauthorized" error**
   - Run `infisical login` again
   - Check machine identity has access to path

4. **CLI not found on Windows**
   - Add `C:\tools\Infisical\` to PATH
   - Or use full path: `/c/tools/Infisical/infisical`

## Python Integration Example

```python
import os
import subprocess
import sys

def get_infisical_base_cmd() -> list[str]:
    """Get infisical binary path for Windows."""
    if sys.platform == "win32" or os.name == "nt":
        common_paths = [
            r"C:\tools\Infisical\infisical.exe",
            os.path.expanduser(r"~\bin\infisical.exe"),
        ]
        for path in common_paths:
            if os.path.exists(path):
                return [path]
    return ["infisical"]

def fix_path_for_git_bash(path: str) -> str:
    """Fix Git Bash path mangling."""
    import re
    if re.match(r'^[A-Za-z]:', path) or 'tools/Git' in path:
        match = re.search(r'[tT]ools[/\\][gG]it[/\\](.+)$', path)
        if match:
            return '/' + match.group(1).replace('\\', '/')
    return path

# Usage
os.environ['MSYS_NO_PATHCONV'] = '1'
cmd = [
    *get_infisical_base_cmd(),
    "secrets", "set",
    "--env=prod",
    f"--path={fix_path_for_git_bash('/layer4-agents')}",
    "OPENAI_API_KEY=sk-xxx"
]
subprocess.run(cmd, check=True)
```
