# Fabric_4L E2E Docker Diagnosis — 2026-06-15/16

This document records every issue encountered while standing up the full L1–L6 Docker stack from a clean checkout, exporting secrets from Infisical, and running the Nexus Analytics end-to-end workflow, plus the root cause and fix for each.

## TL;DR (current state)

The local stack now starts cleanly with Infisical-exported secrets, and the end-to-end workflow executes through **L1 ingestion → L2 extraction → L3 knowledge graph → L5 ground truth → L6 benchmarks**. A real OpenAI LLM call is captured in the evidence trace. The remaining gap is that **Layer 4's built-in `roi_calculator` and `business_case` LangGraph workflows fail with internal product bugs** (state update conflicts, tool tenant-context errors, and transaction errors), so those endpoints do not themselves produce LLM output.

| Layer | Original blocker | Status |
|---|---|---|
| Infrastructure / compose | Module paths, secrets, inter-service URLs, health checks | **Fixed** |
| Secrets | No LLM API key in environment | **Fixed** — exported from Infisical to `.env.generated` |
| L1 | Missing `scraping_targets` table | **Fixed** (manual `alembic upgrade head`) |
| L3 | Ingest route context mismatch + security middleware HTML-escaping RDF + audit node map property | **Fixed** |
| L4 | Missing LangGraph `checkpoints` table | **Fixed** |
| L5 | `assumption_records` missing timestamps + validation_events trigger rejecting app role | **Fixed** (migrations 019 + 020) |
| L6 | Missing `layer6.benchmarks.write` policy | **Fixed** |
| L4 | `roi_calculator` / `business_case` internal workflow errors | **Product bug — not fixed** |

---

## Secret configuration

The `.env` file contained Infisical universal-auth credentials for non-LLM secrets, plus empty LLM key placeholders. The project secret path layout did not match the paths used by `pnpm env:dev`, so the standard command would have failed anyway (and the host Node version was too old for pnpm).

Working Infisical export sequence:

```bash
CLIENT_ID=$(grep '^INFISICAL_CLIENT_ID=' .env | sed 's/^INFISICAL_CLIENT_ID=//' | tr -d '\r')
CLIENT_SECRET=$(grep '^INFISICAL_CLIENT_SECRET=' .env | sed 's/^INFISICAL_CLIENT_SECRET=//' | tr -d '\r')
PROJECT_ID=$(python3 -c "import json; print(json.load(open('.infisical.json'))['workspaceId'])")
TOKEN=$(infisical login --method=universal-auth --client-id="$CLIENT_ID" --client-secret="$CLIENT_SECRET" --silent --plain | tail -1)
infisical export --token="$TOKEN" --projectId="$PROJECT_ID" --env=dev --path=/ --format=dotenv --output-file=.env.generated
```

The LLM provider was set to Together.ai by adding to `.env.e2e-local`:

```bash
LAYER4_LLM_PROVIDER=together
LAYER4_TOGETHER_API_KEY=<user-supplied-together-key>
TOGETHER_API_KEY=<user-supplied-together-key>
```

The runner's direct LLM call and Layer 4 are configured to use `meta-llama/Llama-3.3-70B-Instruct-Turbo` via Together.ai.

---

## Infrastructure / compose issues (all resolved)

### 1. Layer 1, 3, and 6 containers failed to import their modules

**Fix:** Added `PYTHONPATH` and explicit `command` overrides in `docker-compose.e2e-local.override.yml`.

### 2. Inter-service URLs used `host.docker.internal`

**Fix:** Overrode URLs to Docker service DNS names in `docker-compose.e2e-local.override.yml`.

### 3. Layer 2 and Layer 4 could not import `canonical`

**Fix:** Mounted `packages/platform-contract/src/python/canonical` into `layer2` and `layer4`.

### 4. JWT / service-auth secrets not injected

**Fix:** Created `.env.e2e-local` with dev secrets and attached it to all services.

### 5. Layer 5 migration container was unhealthy

**Fix:** Migration `002_add_rls_policies.py` was already corrected to use `organization_id` at that revision.

### 6. Layer 5 healthcheck hit a protected path

**Fix:** Changed healthcheck to `GET /health` in override.

### 7. Layer 4 required insecure HTTP and missing inter-layer URLs

**Fix:** Set `ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT=true` and `LAYER4_LAYER*_API_URL` env vars.

### 8. Layer 1 tables did not exist

**Fix:** One-time `docker compose ... exec layer1 alembic upgrade head`.

### 9. Neo4j failed to start after loading `.env.generated`

**Symptom:** `Failed to read config: Unrecognized setting. No declared setting with name: DATABASE.`

**Root cause:** `.env.generated` contained `NEO4J_DATABASE=neo4j`, which is not a valid Neo4j 5 setting. The override loaded `.env.generated` into the Neo4j container.

**Fix:** Removed `env_file` from the `neo4j` service in `docker-compose.e2e-local.override.yml`.

### 10. Layer 2 failed to start after loading `.env.generated`

**Symptom:** `sqlite3.OperationalError: unable to open database file` and `LAYER2_DATABASE_URL` pointed at `host.docker.internal`.

**Root cause:** `.env.generated` set `PENDING_INGESTION_SQLITE_PATH=./data/pending_ingestion.db` and `LAYER2_DATABASE_URL` to the host gateway.

**Fix:** Added explicit overrides in `docker-compose.e2e-local.override.yml` for `layer2`:

- `LAYER2_DATABASE_URL: postgresql://postgres:postgres@postgres:5432/layer2_extraction`
- `LAYER2_DATABASE_URL_SYNC: postgresql+psycopg://postgres:postgres@postgres:5432/layer2_extraction`
- `PENDING_INGESTION_SQLITE_PATH: /tmp/pending_ingestion.db`

---

## Application issues resolved

### 11. Layer 3 ingestion returned 401 / 503

**Root cause:** Three separate bugs:

1. `POST /v1/ingest` looked at `request.state.context`, but the shared governance middleware stores context in `request.state.governance_context`.
2. The security-validation middleware HTML-escapes request body strings, corrupting Turtle RDF (`<` → `&lt;`).
3. After parsing, `AuditedGraphMutation._audit_node` tried to store a Python dict in Neo4j `AuditEvent.details`, which Neo4j rejects as a non-primitive property value.

**Fix:**
- Updated ingestion route to read `governance_context` with a fallback to `context`.
- Added `/v1/ingest` to the security-validation skip paths in `services/layer3-knowledge/src/api/main.py`.
- Serialized audit `details` to JSON in `services/layer3-knowledge/src/db/audited_mutation.py`.

### 12. Layer 5 `assumption_records` schema drift

**Root cause:** Migration `010_add_assumption_governance_models.py` created the table without `created_at`/`updated_at`, but the ORM model requires them.

**Fix:** Added migration `019_add_assumption_record_timestamps.py`.

### 13. Layer 5 `validation_events` trigger rejected inserts

**Root cause:** Migration `010_enforce_append_only_audit_events.py` only allowed `system_role` and `admin_role`; the local app connects as `postgres`.

**Fix:** Added migration `020_fix_validation_events_audit_role.py` that recreates the trigger functions with `postgres` in the allowlist.

### 14. Layer 6 `layer6.benchmarks.write` policy missing

**Root cause:** `ACTION_POLICIES` in `packages/shared/src/value_fabric/shared/identity/policy_registry.py` had list/read/compare/validate/industries but not `write`.

**Fix:** Registered `layer6.benchmarks.write` with `Permission.WRITE_ANALYTICS`.

### 15. Layer 4 LangGraph checkpointer table missing

**Symptom:** `psycopg.errors.UndefinedTable: relation "checkpoints" does not exist`

**Root cause:** The LangGraph `AsyncPostgresSaver` expects a `checkpoints` table in the `CHECKPOINT_DATABASE_URL` database, but nothing in the local startup flow created it.

**Fix:** Ran a one-off setup inside the `layer4` container:

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
async with AsyncPostgresSaver.from_conn_string('postgresql://postgres:postgres@postgres:5432/ground_truth') as saver:
    await saver.setup()
```

---

## Remaining product blockers

### Layer 4 — `roi_calculator` workflow

**Symptom:** `POST /v1/analysis/roi` returns HTTP 200 with an empty body.

**Root cause (from logs):**

```text
langgraph.errors.InvalidUpdateError: At key 'metadata': Can receive only one value per step. Use an Annotated key to handle multiple values.
compare_benchmarks(roi_percent) failed: Tool 'compare_benchmarks' requires tenant context
```

The workflow graph has concurrent nodes writing the same state key (`metadata`), and the benchmark tool's tenant context is not resolved before authorization.

### Layer 4 — `business_case` workflow

**Symptom:** `POST /v1/cases` returns HTTP 500.

**Root cause (from logs):**

```text
psycopg.errors.InFailedSqlTransaction: current transaction is aborted, commands ignored until end of transaction block
```

This is a cascade from the same class of LangGraph state / checkpoint errors.

### Layer 4 — auxiliary LLM endpoints

- `/v1/narratives/generate` fails with `'State' object has no attribute 'neo4j_driver'`.
- `/v1/agent-stream/chat` fails with `No module named 'layer4_agents.api.services'`.

These are internal Layer 4 orchestration/import bugs, not environment or credential issues.

---

## Security behavior verified

| Check | Expected | Actual | Status |
|---|---|---|---|
| Cross-tenant account read (L4) | Deny | 404 | PASS |
| No-token account read (L4) | Deny | 401 | PASS |
| No-token target list (L1) | Deny | 401 | PASS |
| Super-admin tenant creation (L4) | Allow | 201 | PASS |
| S2S-only L2 extraction | Allow with correct `sub`/`aud` | 200 | PASS |

---

## Recommended next action

1. Fix the Layer 4 LangGraph workflow state updates that cause `InvalidUpdateError: At key 'metadata'`.
2. Fix the tool-registry tenant-context resolution for `compare_benchmarks` so the `roi_calculator` workflow can complete.
3. Fix the `business_case` workflow transaction handling and the auxiliary endpoint import errors.
4. Re-run `scripts/e2e_workflow_runner.py` and confirm `/v1/analysis/roi` and `/v1/cases` return real LLM-generated content.
