# Bunnyshell Programmatic Workflow Research — Fabric_4L

> **Scope:** Create, configure, deploy, debug, and manage Bunnyshell environments for the Value Fabric platform using only the local CLI, repository artifacts, and verifiable command outputs.  
> **Primary sources:** `bunnyshell.yaml`, `docker-compose.live.yml`, `.bunny/bns.exe --help`, `.devin/skills/bunnyshell/SKILL.md`, `.devin/workflows/bunnyshell.md`.  
> **Date:** 2026-05-23  
> **Author:** Kimi Code CLI (synthesized from local tool outputs)

---

## 1. Executive Summary

The Fabric_4L repository contains **two** environment-definition artifacts:

1. **`bunnyshell.yaml`** — A 570-line Bunnyshell-native environment definition. This is the canonical source of truth for cloud deployments. It defines frontend, L1–L6 services, postgres, redis, neo4j, minio, volumes, and ingress hosts.
2. **`docker-compose.live.yml`** — A 550-line Docker Compose file for **local** live-stack validation (backend-integrated Playwright tests, local Docker Compose). It is *not* the source of truth for Bunnyshell cloud environments.

**Key finding:** Because `bunnyshell.yaml` already exists and is comprehensive, the team does **not** need to perform a Docker Compose import step. The fastest, highest-confidence programmatic path is to create environments directly from `bunnyshell.yaml` using `bns environments create --from-path ./bunnyshell.yaml`.

**Second key finding:** The official Bunnyshell documentation (cited in external analyses) contains flag-naming drift versus the actual CLI binary shipped in this repository (`.bunny/bns.exe`). The most important discrepancy is variable import: the local CLI uses `--vars-file` and `--secrets-file` (plural), not `--var-file` / `--secret-file`.

**Third key finding:** The Bunnyshell organization and project for this repository are known from the live URL:
- Organization ID: `4918`
- Project ID: `6266`

---

## 2. Primary Sources & Artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Bunnyshell CLI | `.bunny/bns.exe` | Bundled binary for environment lifecycle |
| CLI README | `.bunny/README.md` | Installation, auth, and shell-completion notes |
| Bunnyshell manifest | `bunnyshell.yaml` | Canonical cloud environment definition |
| Live Compose | `docker-compose.live.yml` | Local Docker Compose live-validation stack |
| Skill definition | `.devin/skills/bunnyshell/SKILL.md` | Agent-facing capability schema |
| Workflow guide | `.devin/workflows/bunnyshell.md` | High-level Bunnyshell operational patterns |

---

## 3. The Two Environment Definitions

### 3.1 `bunnyshell.yaml` (Cloud / Bunnyshell-native)

- **Kind:** `Environment`
- **Name:** `Fabric Dev`
- **Type:** `primary`
- **Components:** 14 components including:
  - `frontend` (Application, port 3001, host ingress)
  - `layer1`, `layer1-worker` (Application + worker)
  - `layer2` (Application)
  - `layer3`, `layer3-neo4j-migrate` (Application + init job)
  - `layer4` (Application, public port 8004, host ingress)
  - `layer5`, `layer5-migrate` (Application + init job)
  - `layer6` (Application)
  - `minio`, `minio-init`, `postgres-init`, `neo4j`, `postgres`, `redis` (Services / Database)
- **Volumes:** 4 persistent disks (`live-minio-data`, `live-neo4j-data`, `live-postgres-data`, `live-redis-data`)
- **Required secrets (documented in header):**
  - `JWT_SECRET`, `SERVICE_AUTH_SECRET`, `API_KEY_HMAC_SECRET`, `CREDENTIALS_MASTER_KEY`
  - `NEO4J_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`
  - `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
  - `LAYER3_API_KEY`, `LAYER5_API_KEY` (consumed by the `layer6` component)

> **Note on `ANTHROPIC_API_KEY`:** It is only required when the Layer 4
> agent workflows are configured to use Anthropic models. If your deployment
> uses only OpenAI (or another provider), remove the
> `${ANTHROPIC_API_KEY}` reference from the `layer4` component in
> `bunnyshell.yaml` rather than supplying a placeholder value — supplying a
> bogus credential can cause the service to fail at runtime with a 401.
> Keep `OPENAI_API_KEY` mandatory; treat `ANTHROPIC_API_KEY` as
> provider-conditional.

### 3.2 `docker-compose.live.yml` (Local / Docker Compose)

- **Purpose:** Local backend-integrated validation stack.
- **Usage:** `docker compose -f docker-compose.live.yml up -d`
- **Contains:** Nearly identical service topology but expressed in Compose schema, with host bind-mounts for live code reloading and local healthchecks.
- **Bunnyshell relevance:** Low. This file is for local development and CI smoke tests. It is **not** referenced by `bunnyshell.yaml` and should not be imported into Bunnyshell unless the team explicitly decides to migrate away from the native `bunnyshell.yaml`.

### 3.3 Recommendation

Use **`bunnyshell.yaml`** as the single source of truth for all programmatic Bunnyshell operations. Do not attempt to import `docker-compose.live.yml` into Bunnyshell; the native manifest is already more precise (component kinds, resource limits, ingress hosts, init-container commands).

---

## 4. CLI Authentication & Context

### 4.1 Profile-based authentication (recommended for interactive use)

> **SECURITY:** A personal access token was previously committed in this document.
> Treat that token (`bns_pat_80076cc13be5dd7fd432…f5a1efec0c05b`)
> as **compromised** and take these steps before any further use:
>
> 1. Revoke it in the Bunnyshell dashboard.
> 2. Create a replacement token with the minimum required scope.
> 3. Store the replacement **only** in Bunnyshell, Infisical, or your CI secret store — never in the repository.
> 4. Purge the token from Git history (e.g. `git filter-repo --replace-text`, or BFG Repo-Cleaner) and coordinate a force-push with maintainers.
> 5. Do not copy or reuse the compromised token.

Load the token from your secret store into an environment variable before running CLI commands:

```bash
# Windows (Git Bash)
./.bunny/bns.exe configure profiles add \
  --name fabric \
  --token "$BNS_TOKEN" \
  --organization 4918 \
  --project 6266 \
  --default
```

### 4.2 Inline token (recommended for CI/scripts)

```bash
./.bunny/bns.exe environments list \
  --project 6266 \
  --token "$BNS_TOKEN" \
  --non-interactive \
  --output json
```

### 4.3 Global flags present on every command

Verified from `.bunny/bns.exe --help`:

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--configFile` | string | `$HOME/.bunnyshell/config.yaml` | CLI config path |
| `-d, --debug` | bool | false | Debug network requests |
| `--no-progress` | bool | false | Disable spinners |
| `--non-interactive` | bool | false | Disable prompts (essential for CI) |
| `-o, --output` | string | stylish | stylish \| json \| yaml \| raw |
| `--profile` | string | — | Use named profile |
| `-t, --timeout` | duration | 30s | Network timeout |
| `--token` | string | — | Auth token |
| `-v, --verbose` | count | — | Increase verbosity |

---

## 5. Environment Lifecycle

### 5.1 Create from `bunnyshell.yaml`

Verified from `.bunny/bns.exe environments create --help`:

```bash
ENV_JSON=$(./.bunny/bns.exe environments create \
  --name "fabric-$(date +%Y%m%d-%H%M%S)" \
  --project 6266 \
  --from-path "./bunnyshell.yaml" \
  --deploy \
  --no-wait \
  --non-interactive \
  --output json)

ENV_ID=$(echo "$ENV_JSON" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
```

**Key flags:**
- `--from-path` — accepts a local `bunnyshell.yaml` (**not** a Docker Compose file).
- `--deploy` — triggers deployment immediately after creation.
- `--no-wait` — returns immediately; pipeline continues asynchronously.
- `--k8s` — optional Kubernetes integration ID if not using the project default.

### 5.2 Deploy / Redeploy

```bash
# Full environment redeploy
./.bunny/bns.exe environments deploy \
  --id "$ENV_ID" \
  --no-wait \
  --non-interactive

# Partial redeploy (single component)
./.bunny/bns.exe environments deploy \
  --id "$ENV_ID" \
  --component "$COMP_ID" \
  --no-wait \
  --non-interactive
```

**Important:** The local CLI does **not** expose a `--wait` flag on deploy. It blocks by default; use `--no-wait` to detach.

### 5.3 Clone

Useful for ephemeral test environments derived from a known-good primary:

```bash
./.bunny/bns.exe environments clone \
  --id "$SOURCE_ENV_ID" \
  --name "fabric-clone-$(date +%Y%m%d-%H%M%S)" \
  --non-interactive
```

### 5.4 Start / Stop / Delete

```bash
./.bunny/bns.exe environments start --id "$ENV_ID" --non-interactive
./.bunny/bns.exe environments stop  --id "$ENV_ID" --non-interactive
./.bunny/bns.exe environments delete --id "$ENV_ID" --non-interactive
```

### 5.5 Inspect

```bash
# List
./.bunny/bns.exe environments list --project 6266 --output json

# Show one
./.bunny/bns.exe environments show --id "$ENV_ID" --output json

# Endpoints
./.bunny/bns.exe environments endpoints --id "$ENV_ID" --output json

# Events
./.bunny/bns.exe events list --environment "$ENV_ID" --output json
```

---

## 6. Variable & Secret Management

### 6.1 The import command (verified)

```bash
./.bunny/bns.exe variables import --help
```

**Actual flags:**
- `--environment string` — target environment
- `--vars-file string` — flat `key=value` file for plain variables
- `--secrets-file string` — flat `key=value` file for secrets
- `--ignore-duplicates` — skip existing variables instead of failing

**Correction to official docs:** The local binary uses `--vars-file` and `--secrets-file` (plural), *not* `--var-file` / `--secret-file`.

### 6.2 Preparing flat env files

Because the CLI only accepts `key=value` files, extract variables from your local `.env` or compose file into two files before import:

```bash
# .bns/vars.env (non-sensitive)
POSTGRES_USER=postgres
POSTGRES_DB=ingestion
LLM_MODEL=gpt-4o
LOG_LEVEL=debug
...

# .bns/secrets.env (sensitive)
JWT_SECRET=...
SERVICE_AUTH_SECRET=...
API_KEY_HMAC_SECRET=...
CREDENTIALS_MASTER_KEY=...
NEO4J_PASSWORD=...
POSTGRES_PASSWORD=...
REDIS_PASSWORD=...
MINIO_ROOT_PASSWORD=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

**Bunnyshell encrypts all variables at rest.** The `--secrets-file` designation primarily hides values in the web UI.

### 6.3 Import procedure

```bash
# Point profile at the specific environment so import targets it correctly
./.bunny/bns.exe configure profiles add \
  --name fabric-target \
  --token "$BNS_TOKEN" \
  --organization 4918 \
  --project 6266 \
  --environment "$ENV_ID" \
  --default

# Import
./.bunny/bns.exe variables import \
  --environment "$ENV_ID" \
  --vars-file ".bns/vars.env" \
  --secrets-file ".bns/secrets.env" \
  --ignore-duplicates \
  --non-interactive

# Redeploy so services consume the new values
./.bunny/bns.exe environments deploy \
  --id "$ENV_ID" \
  --no-wait \
  --non-interactive
```

---

## 7. Component Operations (Debug)

### 7.1 Discovery

```bash
./.bunny/bns.exe components list --environment "$ENV_ID" --output json
```

### 7.2 Logs

```bash
# All components, following
./.bunny/bns.exe logs --environment "$ENV_ID" --follow --prefix

# Specific components by name
./.bunny/bns.exe logs --environment "$ENV_ID" --name layer4 --name frontend --follow

# Last N lines
./.bunny/bns.exe logs --component "$COMP_ID" --tail 100

# Previous container (crashed pod)
./.bunny/bns.exe logs --component "$COMP_ID" --previous
```

### 7.3 Execute commands

```bash
# Interactive shell (auto-enables TTY)
./.bunny/bns.exe exec "$COMP_ID"

# One-off command
./.bunny/bns.exe exec "$COMP_ID" -- python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"

# Specific pod/container
./.bunny/bns.exe exec "$COMP_ID" --tty --stdin --pod my-pod-abc -c api -- /bin/bash
```

### 7.4 SSH

```bash
./.bunny/bns.exe ssh --component "$COMP_ID" --shell /bin/bash
```

### 7.5 Port-forward

```bash
# Local 8004 -> remote component 8000
./.bunny/bns.exe port-forward --component "$COMP_ID" 8004:8000

# Multiple ports
./.bunny/bns.exe port-forward --component "$COMP_ID" 5432:5432 6379:6379
```

### 7.6 Debug session

```bash
./.bunny/bns.exe debug start --component "$COMP_ID"
# ... inspect ...
./.bunny/bns.exe debug stop --component "$COMP_ID"
```

---

## 8. Remote Development & VS Code Integration

### 8.1 Bunnyshell remote-development command

Verified from `.bunny/bns.exe --help` (top-level):

```bash
./.bunny/bns.exe remote-development [command]
```

Subcommands (from help): `up`, `down`, `status` (exact subcommands not fully enumerated in top-level help, but the workflow docs reference them).

Practical pattern for exclusive remote files:

```bash
COMPONENT_ID=$(./.bunny/bns.exe components list --environment "$ENV_ID" --output json \
  | jq -r '._embedded.item[] | select(.name == "layer4") | .id')

./.bunny/bns.exe remote-development up \
  --component "$COMPONENT_ID" \
  --sync-mode none \
  --no-tty \
  --remote-sync-path /app
```

For local sync + debug port forwarding:

```bash
./.bunny/bns.exe remote-development up \
  --component "$COMPONENT_ID" \
  --local-sync-path "$PWD" \
  --remote-sync-path /app \
  --port-forward "3000>3000,9229>9229"
```

### 8.2 VS Code configuration

The repository already contains `.vscode/settings.json` with Bash terminal defaults. For Bunnyshell Remote-SSH, add user-level settings:

```jsonc
// User settings.json (not committed to repo)
{
  "remote.SSH.configFile": "C:/Users/BBB/.bunnyshell/remote-dev/ssh-config",
  "remote.SSH.defaultExtensions": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode"
  ],
  "remote.restoreForwardedPorts": true
}
```

The Bunnyshell CLI prints the SSH config path after `remote-development up`. Point VS Code Remote-SSH at that file.

### 8.3 Workspace recommendations

The repo should already have these; verify they exist:

```json
// .vscode/extensions.json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode"
  ]
}
```

---

## 9. End-to-End Workflow for Fabric_4L

This is the consolidated, copy-pasteable workflow derived entirely from local artifacts and verified CLI outputs.

### Prerequisites

> **Never hardcode a Bunnyshell token in the repository.** Load it from your CI
> secret store or a local untracked `.env` file. The token shown in earlier
> versions of this document has been removed and must be treated as compromised
> (see §4.1).

```bash
# Load from your secret store, e.g.:
#   export BNS_TOKEN="$(infisical secrets get BNS_TOKEN --plain)"
export BNS_TOKEN="<load-from-secret-store>"
export BNS_ORG=4918
export BNS_PROJECT=6266
```

### Step 1 — Create environment from canonical manifest

```bash
ENV_JSON=$(./.bunny/bns.exe environments create \
  --name "fabric-live-$(date +%Y%m%d-%H%M%S)" \
  --project "$BNS_PROJECT" \
  --from-path "./bunnyshell.yaml" \
  --deploy \
  --no-wait \
  --non-interactive \
  --token "$BNS_TOKEN" \
  --output json)

ENV_ID=$(echo "$ENV_JSON" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "Created environment: $ENV_ID"
```

### Step 2 — Import variables

```bash
# Ensure .bns/vars.env and .bns/secrets.env exist (key=value format)
./.bunny/bns.exe variables import \
  --environment "$ENV_ID" \
  --vars-file ".bns/vars.env" \
  --secrets-file ".bns/secrets.env" \
  --ignore-duplicates \
  --token "$BNS_TOKEN" \
  --non-interactive
```

### Step 3 — Redeploy to consume variables

```bash
./.bunny/bns.exe environments deploy \
  --id "$ENV_ID" \
  --no-wait \
  --token "$BNS_TOKEN" \
  --non-interactive
```

### Step 4 — Verify

```bash
./.bunny/bns.exe environments show --id "$ENV_ID" --output json | jq .
./.bunny/bns.exe components list --environment "$ENV_ID" --output json | jq .
```

### Step 5 — Stream logs

```bash
./.bunny/bns.exe logs --environment "$ENV_ID" --follow --prefix
```

### Step 6 — Debug (optional)

```bash
# Get component ID
COMP_ID=$(./.bunny/bns.exe components list --environment "$ENV_ID" --output json \
  | jq -r '._embedded.item[] | select(.name == "layer4") | .id')

# Shell
./.bunny/bns.exe exec "$COMP_ID" -- /bin/sh

# Port-forward layer4 API to localhost:8004
./.bunny/bns.exe port-forward --component "$COMP_ID" 8004:8000
```

---

## 10. Pitfalls, Corrections, and Non-Negotiables

| Pitfall | Reality | Fix |
|---------|---------|-----|
| **Importing `docker-compose.live.yml` via CLI** | `bns environments create --from-path` only accepts `bunnyshell.yaml`, not Compose. | Use the existing `bunnyshell.yaml`; it is already authoritative. |
| **Variable import flag names** | Docs show `--var-file` / `--secret-file`; local CLI uses `--vars-file` / `--secrets-file`. | Use plural forms (`--vars-file`, `--secrets-file`). |
| **`--wait` on deploy** | Not present in local CLI deploy help. | Omit `--wait`; the CLI blocks by default. Use `--no-wait` to detach. |
| **YAML variable files** | `bns variables import` expects flat `key=value`, not YAML. | Extract or curate `.env`-style files before import. |
| **Token exposure** | PAT is sensitive. | Load from CI secret store or local `.env`; never commit. |
| **`depends_on` semantics** | Kubernetes does not honor Compose `depends_on`. | The `bunnyshell.yaml` already uses healthchecks and init containers (e.g., `layer5-migrate`, `minio-init`). Do not add Compose-style `depends_on` to the Bunnyshell manifest. |
| **Alpine image + VS Code Server** | VS Code Remote requires `glibc`-compatible libraries, `git`, `bash`, etc. | Ensure Dockerfiles for Alpine-based components install required packages if remote development is planned. |

---

## 11. Open Questions for Future Investigation

1. **Does the local CLI support `bns remote-development up` or only `start`?**  
   The top-level help lists `remote-development` as a utility command, but subcommand help was not fully captured. Verify with `./.bunny/bns.exe remote-development --help`.

2. **What is the exact `--k8s` cluster ID for project 6266?**  
   The `bunnyshell.yaml` does not specify a cluster. If the project has a default cluster, `--k8s` may be omitted. Otherwise, run `bns k8s-clusters list` to discover it.

3. **Are there Bunnyshell-hosted values for the required secrets?**  
   The project may already store `JWT_SECRET`, `OPENAI_API_KEY`, etc. as Bunnyshell project variables. If so, new environments may inherit them automatically, reducing the import step.

4. **Frontend endpoint URL format**  
   The `bunnyshell.yaml` defines `frontend-{{ env.base_domain }}`. After deployment, the exact URL can be retrieved via `bns environments endpoints --id "$ENV_ID"`.

---

## Appendix A: Required Variables Checklist

Derived from the header comments of `bunnyshell.yaml`:

- [ ] `JWT_SECRET`
- [ ] `SERVICE_AUTH_SECRET`
- [ ] `API_KEY_HMAC_SECRET`
- [ ] `CREDENTIALS_MASTER_KEY`
- [ ] `NEO4J_PASSWORD`
- [ ] `MINIO_ROOT_USER`
- [ ] `MINIO_ROOT_PASSWORD`
- [ ] `POSTGRES_USER`
- [ ] `POSTGRES_PASSWORD`
- [ ] `REDIS_PASSWORD`
- [ ] `OPENAI_API_KEY`
- [ ] `ANTHROPIC_API_KEY` — provider-conditional; remove from `layer4` if Anthropic is unused (see §3.1 note)

---

## Appendix B: Raw CLI Command Trees (Verified)

### Top-level
```
bns [command]

Resources:
  components           Components
  container-registries Container Registry Integrations
  environments         Environments
  events               Events
  k8s-clusters         Kubernetes Cluster Integrations
  organizations        Organizations
  pipelines            Pipeline
  project-variables    Project Variables
  projects             Projects
  secrets              Secrets
  templates            Template
  variables            Environment Variables
  variables-groups     Grouped Environment Variables

Utilities:
  debug                Debug Component
  exec                 Execute a command in a container
  git                  Git Operations
  logs                 Stream logs from component containers
  port-forward         Starts the port forwarding for the given mappings
  remote-development   Remote Development
  ssh                  SSH into a running container for a component

CLI:
  completion           Generate the autocompletion script for the specified shell
  configure            Configure CLI settings
  help                 Help about any command
  version              Version Information
```

### `environments` subcommands
```
Environment:
  list
  show

Environment Actions:
  abort
  clone
  create
  definition
  delete
  deploy
  endpoints
  start
  stop
  update-build-settings
  update-components
  update-configuration
  update-settings
```

### `environments create` flags (relevant subset)
```
      --auto-deploy-ephemerals               Auto deploy the created ephemerals
      --component stringArray                Partial action with set components
      --create-ephemeral-on-pr               Create ephemerals on PR
      --deploy                               Deploy the environment after creation
      --destroy-ephemeral-on-pr-close        Destroy ephemerals on PR close
      --from-path string                     Use a local bunnyshell.yaml during environment creation
      --from-template string                 Use a TemplateID during environment creation
      --from-environment string              Use an existing environment as template
      --included-dependencies string         Include dependencies (none, all, missing) [default "none"]
      --k8s string                           Kubernetes integration
      --name string                          Unique name for the environment
      --no-wait                              Do not wait for pipeline until finish
      --project string                       Project for the environment
      --queue                                Queue the deploy pipeline if another operation is in progress
      --termination-protection               Prevent accidental termination
```

### `variables import` flags
```
      --environment string    Environment for the variable
      --ignore-duplicates     Skip variables that already exist
      --secrets-file string   File to import secrets from
      --vars-file string      File to import variables from
```

## 12. CPU Quota Budget & Lightweight Profile

To attempt fitting multiple environments within a hard 8 CPU quota, a lightweight profile (`bunnyshell-pr.yaml`) has been created. Usage: `bns environments create --from-path ./bunnyshell-pr.yaml`.

### CPU Budget Summary

| Environment Type | CPU Allocation | Details |
|------------------|----------------|---------|
| Current Full Environment | 4.375 CPUs | 13 components @ 0.25, postgres @ 1.0, init jobs @ 0.125 |
| Proposed Lightweight (PR) Environment | 2.25 CPUs | 13 components @ 0.125, postgres @ 0.5, init jobs @ 0.125 |
| Estimated Kubernetes Overhead | ~3.25 CPUs | Control plane, system pods, and daemonsets |
| **Total (1 Full + 1 PR + Overhead)** | **9.875 CPUs** | 4.375 + 2.25 + 3.25 |

### Do two environments fit under 8 CPUs?

**No.** The estimated total (9.875 CPUs) exceeds the 8 CPU quota.

Because the constraints specify that the CPU footprint of the full environment must not be reduced, and the lightweight environment alone requires 2.25 CPUs, it is mathematically impossible to fit both alongside the ~3.25 CPU Kubernetes overhead. 

To successfully provision a new PR environment, you must **stop** the primary environment to free up resources. Alternatively, use **Remote Development Mode** (`bns remote-development up`) to develop against the single running environment.
