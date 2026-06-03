---
skill_id: value-engine-e2e-validation
name: value-engine-e2e-validation
version: 1.0.0
description: Bootstrap the full development stack, seed a demo tenant and user, authenticate, execute the complete 7-step Value Engine workflow end-to-end, autonomously fix blockers, and produce a final validation report.
side_effects: exec
timeout_ms: 1800000
required_context:
  - project_graph
  - test_inventory
allowed_agents: ["*"]
---

# Value Engine E2E Workflow Validation

Executes a complete end-to-end validation of the 7-step Value Engine workflow in a fresh development environment, autonomously fixing mechanical blockers and producing a comprehensive validation report with a Go/No-Go decision.

## When to Use

- **Pre-release validation**: Before shipping features that touch multiple workflow steps
- **Integration testing**: After significant backend/frontend changes that affect the value creation pipeline
- **Environment verification**: When onboarding new developers or verifying CI/CD pipeline health
- **Regression detection**: After dependency updates or architectural changes
- **Demo preparation**: To ensure demo environments are fully functional before presentations

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `demo_tenant_slug` | string | No | `demo-acme` | Slug for the demo tenant |
| `demo_user_email` | string | No | `sarah.chen@acmerobotics.com` | Email for demo user |
| `demo_user_password` | string | No | `Demo1234!` | Password for demo user |
| `prospect_company` | string | No | `Axiom Robotics` | Company name for test prospect |
| `prospect_domain` | string | No | `axiomrobotics.com` | Domain for test prospect |
| `max_fix_attempts` | number | No | `3` | Maximum retry attempts per step |
| `fix_timebox_minutes` | number | No | `15` | Time limit per fix attempt |
| `skip_phases` | string[] | No | `[]` | Phases to skip (e.g., `["1", "2"]` if services already running) |
| `output_format` | string | No | `markdown` | Report format: `markdown` or `json` |

## Steps

### Pre-Flight Checks

Before starting, verify the environment is suitable:

1. Check for required files:
   ```bash
   ls -la docker-compose.yml compose.yaml Makefile package.json 2>/dev/null || echo "WARNING: No standard orchestration files found"
   ```

2. Check available ports (avoid conflicts):
   ```bash
   lsof -i :3000 :8000 :8080 :5432 :6379 2>/dev/null | grep LISTEN || echo "Ports appear available"
   ```

3. Verify Git status (ensure clean working directory for reproducibility):
   ```bash
   git status --porcelain | head -5 || echo "Not a git repo or clean"
   ```

---

### Phase 1: Bootstrap Dev Infrastructure

**Goal**: Start all required services and verify they're healthy.

**Timeout**: 10 minutes
**Checkpoint**: All health checks must pass before proceeding

#### 1.1 Discover Service Configuration

**Discovery Priority** (inspect in order):
1. README.md or docs/development-setup.md
2. Makefile targets (`make dev`, `make api`, `make worker`, `make seed`)
3. docker-compose.yml or compose.yaml
4. package.json scripts
5. pyproject.toml, requirements.txt
6. .env.example or .env.dev

**Action**: Document the discovered startup approach:
```markdown
| Service | Discovery Source | Startup Command | Port |
|---------|-----------------|-----------------|------|
| Layer 1 | {source} | {command} | {port} |
| Layer 4 | {source} | {command} | {port} |
| Frontend | {source} | {command} | {port} |
| Redis | {source} | {command} | {port} |
| Database | {source} | {command} | {port} |
```

#### 1.2 Start Required Services

**Critical Rule**: Start services in dependency order

1. **Database & Redis** (if not using external):
   ```bash
   docker-compose up -d postgres redis  # or equivalent
   ```

2. **Layer 1 (Ingestion)**:
   ```bash
   # Common patterns to try:
   make layer1-dev
   # OR
   cd services/layer1-ingestion && uvicorn src.main:app --reload --port 8001
   ```

3. **Layer 4 (Agents/Orchestration)**:
   ```bash
   make layer4-dev
   # OR
   cd services/layer4-agents && uvicorn src.main:app --reload --port 8004
   ```

4. **Layer 6 (Benchmarks)** - if referenced:
   ```bash
   make layer6-dev
   # OR
   cd services/layer6-benchmarks && uvicorn src.main:app --reload --port 8006
   ```

5. **Celery Worker** (if async jobs required):
   ```bash
   make worker
   # OR
   cd services/layer4-agents && celery -A tasks worker --loglevel=info
   ```

6. **Frontend**:
   ```bash
   cd frontend && pnpm dev  # or npm/yarn equivalent
   ```

**Rollback**: If any service fails to start:
- Check logs with `docker-compose logs {service}` or service-specific log files
- Fix first actionable error (port conflict, missing env var, missing migration)
- Retry up to `max_fix_attempts` times
- If still failing, document blocker and halt

#### 1.3 Verify Service Health

**Checkpoint**: All services must respond to health checks before proceeding

| Service | Health Check | Expected Response | Timeout |
|---------|-------------|-------------------|---------|
| Layer 1 | `GET http://localhost:{port}/health` | `{"status": "healthy"}` or HTTP 200 | 30s |
| Layer 4 | `GET http://localhost:{port}/health` | `{"status": "healthy"}` or HTTP 200 | 30s |
| Layer 6 | `GET http://localhost:{port}/health` | `{"status": "healthy"}` or HTTP 200 | 30s (if running) |
| Frontend | `GET http://localhost:3000/` | HTML response with status 200 | 30s |
| Redis | `redis-cli ping` | `PONG` | 10s |
| Database | `pg_isready -h localhost -p 5432` | `accepting connections` | 10s |

**Failure Protocol**:
- If health endpoint missing but service responds: Document canonical health route gap
- If tables missing: Run migrations (`make migrate` or `alembic upgrade head`)
- If Redis missing: Start Redis or enable local dev queue mode
- If ports conflict: Update `.env` with new ports, propagate to all configs
- If CORS errors: Fix backend `allowed_origins` to include frontend URL

**Verification Command**:
```bash
curl -s http://localhost:8004/health | jq .status || echo "Layer 4 health check failed"
```

#### 1.4 Fix Frontend-Backend Connectivity

**Common Issues & Fixes**:

| Issue | Fix |
|-------|-----|
| CORS preflight fails | Add frontend origin to backend CORS config |
| Wrong API URL | Set `VITE_API_URL`, `REACT_APP_API_URL`, or proxy in `vite.config.ts` |
| Proxy timeout | Increase timeout in `vite.config.ts` proxy config |
| SSL/HTTPS mismatch | Disable SSL for local dev or use consistent scheme |

**Verification**: Frontend can reach Layer 4 health endpoint:
```javascript
// From browser console on frontend origin
fetch('/api/health').then(r => r.json()).then(console.log)
```

---

### Phase 2: Seed Demo Data and Authentication

**Goal**: Create demo tenant, user, and verify authentication works.

**Timeout**: 10 minutes
**Checkpoint**: Login must succeed and return valid tenant-scoped token

#### 2.1 Discover Seed Mechanisms

**Search Order**:
1. `scripts/seed.py`, `scripts/demo_data.py`
2. `scripts/seed.ts`, `prisma/seed.ts`
3. `Makefile` seed targets
4. Backend management commands (`python manage.py seed`)
5. SQL seed files in `migrations/seed*.sql`
6. Alembic seed utilities

#### 2.2 Create Demo Tenant and User

**Minimum Required Data**:
```yaml
tenant:
  slug: demo-acme
  name: Acme Corp

user:
  email: sarah.chen@acmerobotics.com
  password: Demo1234!  # hashed appropriately
  role: admin

prospect:
  company_name: Axiom Robotics
  domain: axiomrobotics.com
  tenant_id: demo-acme
```

**If Seed Script Exists**:
```bash
make seed
# OR
python scripts/seed.py --tenant demo-acme --user sarah.chen@acmerobotics.com
```

**If No Seed Script** (create minimal non-destructive script):
```python
# scripts/e2e_demo_seed.py - minimal version
# Creates tenant, user, prospect; fails gracefully if already exists
```

**Rollback**: If seed fails:
- Check schema mismatches against current DB
- Verify tenant_id foreign key constraints
- Check for existing data conflicts (use upsert pattern)
- Retry after fixes (max `max_fix_attempts`)

#### 2.3 Verify Login

**Action**: Attempt login via discovered auth route:

```bash
# Discover auth route
grep -rn "def login\|@router.post.*login\|/auth/login" services/layer*/src/api/routes/ --include="*.py"

# Attempt login
curl -X POST http://localhost:8004/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"sarah.chen@acmerobotics.com","password":"Demo1234!"}' \
  -v | tee login_response.json
```

**Pass Criteria**:
- HTTP 200 or 201 response
- Response contains `token`, `access_token`, or session cookie
- Token/session can be used in subsequent requests

**Failure Debugging**:
- Check auth route exists: `grep -rn "auth" services/layer4-agents/src/api/router.py`
- Verify password hashing: Check bcrypt/argon2 configuration
- Check user status: Verify user is active and belongs to tenant
- Check role assignment: Verify user has required role
- Check auth middleware: Verify tenant context extraction

#### 2.4 Verify Tenant Context Propagation

**Checkpoint**: Ensure tenant context carries through to API calls

```bash
# Test with tenant header
curl -H "Authorization: Bearer {token}" \
     -H "X-Tenant-ID: demo-acme" \
     http://localhost:8004/v1/prospects \
     -v | jq .
```

**Pass Criteria**:
- Response returns 200 (not 401/403)
- Response includes tenant-scoped data (empty array is OK if no prospects yet)
- Logs show tenant context was recognized

**Failure**: Inspect auth middleware and tenant resolution logic

#### 2.5 Store Credentials for Workflow Test

Store for use in subsequent phases:
```yaml
auth_context:
  tenant_id: demo-acme
  token: {jwt_token}
  headers:
    Authorization: Bearer {jwt_token}
    X-Tenant-ID: demo-acme
    Content-Type: application/json
```

---

### Phase 3: Execute 7-Step Workflow

**Goal**: Complete all workflow steps with valid persisted data.

**Global Rule**: Each step is done only when the UI can navigate to the next step with valid persisted data. If a step fails, fix it before proceeding.

**Timeout**: 20 minutes total for all 7 steps
**Fix Policy**: Up to `max_fix_attempts` per step, `fix_timebox_minutes` per attempt

---

#### Step 1: Prospect Setup

**UI Goal**: User fills company name, selects or confirms inferred buyer, and confirms objective.

**API Verification**:

```bash
# 1. Create prospect
PROSPECT_RESPONSE=$(curl -s -X POST http://localhost:8004/v1/prospects \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Axiom Robotics",
    "domain": "axiomrobotics.com",
    "objective": "cost_reduction"
  }')
PROSPECT_ID=$(echo $PROSPECT_RESPONSE | jq -r '.id')

# 2. Trigger enrichment
curl -X POST "http://localhost:8004/v1/prospects/${PROSPECT_ID}/enrich" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme"

# 3. Get context
curl -s "http://localhost:8004/v1/prospects/${PROSPECT_ID}/context" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" | jq .
```

**Pass Criteria**:
| Check | Expected |
|-------|----------|
| Company profile returned | `company_name` matches input |
| Inferred buyer role present | `inferred_buyer` or `buyer_role` field exists |
| Enrichment confidence | `confidence_score` >= 0.5 or equivalent |
| UI actions available | Confirm/Adjust/Edit actions rendered |
| Persistence on refresh | Same prospect ID returns on page reload |

**Common Failures & Fixes**:

| Failure | Diagnosis | Fix |
|---------|-----------|-----|
| `/v1/prospects` 404 | Route prefix mismatch | Try `/prospects`, `/api/prospects`, check `api/router.py` |
| No context endpoint | Missing composite endpoint | Build adapter in `frontend_compat.py` aggregating L1/L2/L3 calls |
| Enrichment hangs | Async worker issue | Verify Redis running, Celery worker connected, queue names match |
| Data doesn't persist | DB write failure | Check `tenant_id` in INSERT, transaction commits, table exists |
| Schema mismatch | UI expects different shape | Add response transform adapter, preserve UI contract |

**Persistence Verification**:
```sql
-- Verify in database
SELECT id, company_name, tenant_id FROM prospects WHERE company_name = 'Axiom Robotics';
```

---

#### Step 2: Intelligence Gathering

**UI Goal**: Intelligence findings populate for the selected prospect.

**API Verification**:

```bash
# 1. Start intelligence workflow
WORKFLOW_RESPONSE=$(curl -s -X POST http://localhost:8004/v1/workflows/intelligence \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": "'${PROSPECT_ID}'",
    "objective": "cost_reduction"
  }')
WORKFLOW_ID=$(echo $WORKFLOW_RESPONSE | jq -r '.workflow_id')

# 2. Poll workflow status (with timeout)
for i in {1..30}; do
  STATUS=$(curl -s "http://localhost:8004/v1/workflows/${WORKFLOW_ID}/status" \
    -H "Authorization: Bearer {token}" \
    -H "X-Tenant-ID: demo-acme" | jq -r '.status')
  echo "Attempt $i: Status = $STATUS"
  [[ "$STATUS" == "completed" ]] && break
  [[ "$STATUS" == "failed" ]] && echo "Workflow failed" && exit 1
  sleep 2
done

# 3. Get findings
curl -s "http://localhost:8004/v1/intelligence/findings?prospect_id=${PROSPECT_ID}" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" | jq .
```

**Pass Criteria**:
| Check | Expected |
|-------|----------|
| Workflow starts | Returns `workflow_id` with HTTP 201/200 |
| Workflow completes | Status becomes `completed` within reasonable time |
| Pain points present | Array with at least 1 pain point |
| Opportunities present | Array with at least 1 opportunity |
| Stakeholder signals | `stakeholders` or `stakeholder_map` exists |
| UI displays findings | Non-empty findings in Intelligence/Evidence tab |

**Common Failures & Fixes**:

| Failure | Diagnosis | Fix |
|---------|-----------|-----|
| Route 404 | Wrong prefix | Try `/workflows`, check `api/router.py` for route registration |
| No findings | Pipeline broken | Verify L1 → L4 data flow, check ingestion job status |
| Status pending | Worker issue | Check Redis connectivity, Celery worker logs, task registration |
| Workflow fails | Agent error | Check Layer 4 logs for LangGraph/agent errors, API key issues |

---

#### Step 3: AI Model / Value Hypothesis

**UI Goal**: AI generates value hypotheses based on intelligence.

**API Verification**:

```bash
# 1. Generate hypotheses
HYPOTHESIS_RESPONSE=$(curl -s -X POST http://localhost:8004/v1/intelligence/hypotheses \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": "'${PROSPECT_ID}'",
    "intelligence_summary": "{summary_from_step_2}"
  }')

# 2. List hypotheses
curl -s "http://localhost:8004/v1/intelligence/hypotheses?prospect_id=${PROSPECT_ID}" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" | jq '.hypotheses'
```

**Pass Criteria**:
| Check | Expected |
|-------|----------|
| At least one hypothesis | Array length >= 1 |
| Title/name present | Each has `title` or `name` field |
| Confidence/rationale | Each has `confidence` or `rationale` field |
| UI renders | Hypothesis tab shows hypotheses, not empty evidence message |

**Common Failures & Fixes**:

| Failure | Diagnosis | Fix |
|---------|-----------|-----|
| No hypotheses | Agent tools not registered | Verify tool/skill registration in Layer 4 |
| LangGraph fails | LLM/config issue | Check model provider API keys, fallback behavior |
| Schema mismatch | UI expects different structure | Add transform adapter, preserve UI contract |
| Timeout | Long generation | Increase timeout or check if generation is actually running |

---

#### Step 4: Driver Tree

**UI Goal**: Value driver tree is generated and navigable.

**API Verification**:

```bash
HYPOTHESIS_ID=$(echo $HYPOTHESIS_RESPONSE | jq -r '.hypotheses[0].id')

# 1. Generate driver tree
TREE_RESPONSE=$(curl -s -X POST http://localhost:8004/v1/value-engine/driver-tree \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": "'${PROSPECT_ID}'",
    "hypothesis_id": "'${HYPOTHESIS_ID}'"
  }')
TREE_ID=$(echo $TREE_RESPONSE | jq -r '.id')

# 2. Get tree
curl -s "http://localhost:8004/v1/value-engine/driver-tree/${TREE_ID}" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" | jq '.tree'
```

**Pass Criteria**:
| Check | Expected |
|-------|----------|
| Tree structure | Has `root` with `branches` and `leaves` |
| Node names | Each node has `name` field |
| Impact estimates | Each leaf has `impact_estimate` or placeholder |
| Evidence linkage | Nodes have `evidence_count` or `evidence_ids` |
| UI renders tree | Driver Tree page shows tree, not "Account Unknown" or N/A |

**Common Failures & Fixes**:

| Failure | Diagnosis | Fix |
|---------|-----------|-----|
| Empty tree | Knowledge graph disconnected | Inspect L3 graph connections, verify nodes exist |
| Account Unknown | Context passing broken | Fix account context in API layer, check request headers |
| Schema mismatch | Different structure expected | Add compatibility mapping for frontend tree structure |

---

#### Step 5: Evidence Library

**UI Goal**: Evidence is attached to driver tree nodes.

**API Verification**:

```bash
NODE_ID=$(echo $TREE_RESPONSE | jq -r '.tree.root.branches[0].leaves[0].id')

# 1. Get available evidence
curl -s "http://localhost:8004/v1/evidence?prospect_id=${PROSPECT_ID}&driver_node_id=${NODE_ID}" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" | jq '.evidence'

# 2. Attach evidence (if available)
EVIDENCE_ID=$(curl -s "http://localhost:8004/v1/evidence?prospect_id=${PROSPECT_ID}" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" | jq -r '.evidence[0].id')

if [ "$EVIDENCE_ID" != "null" ]; then
  curl -X POST http://localhost:8004/v1/evidence/attach \
    -H "Authorization: Bearer {token}" \
    -H "X-Tenant-ID: demo-acme" \
    -H "Content-Type: application/json" \
    -d '{
      "driver_node_id": "'${NODE_ID}'",
      "evidence_id": "'${EVIDENCE_ID}'"
    }'
fi
```

**Pass Criteria**:
| Check | Expected |
|-------|----------|
| Evidence items exist | Array with at least 1 item |
| Source present | Each has `source` field |
| Credibility/confidence | Each has `credibility` or `confidence` field |
| Relevance | Evidence relates to driver nodes |
| Attach/detach works | Can attach evidence to node and retrieve it |
| UI displays | Evidence Library tab shows non-empty evidence |

**Common Failures & Fixes**:

| Failure | Diagnosis | Fix |
|---------|-----------|-----|
| No evidence | No ingestion | Trigger L1 evidence crawl or seed demo evidence |
| Evidence missing | Tenant scoping | Check `tenant_id` filters on evidence queries |
| Attach fails | Relationship issue | Inspect graph edge model or join table |
| Wrong evidence | Filter issue | Check `driver_node_id` filter in query |

---

#### Step 6: Calculator / ROI

**UI Goal**: User builds ROI scenarios with evidence-backed numbers.

**API Verification**:

```bash
# 1. Create scenario
SCENARIO_RESPONSE=$(curl -s -X POST http://localhost:8004/v1/value-engine/scenarios \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": "'${PROSPECT_ID}'",
    "driver_tree_id": "'${TREE_ID}'"
  }')
SCENARIO_ID=$(echo $SCENARIO_RESPONSE | jq -r '.id')

# 2. Run calculation
curl -X POST "http://localhost:8004/v1/value-engine/scenarios/${SCENARIO_ID}/calculate" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme"

# 3. Get results
curl -s "http://localhost:8004/v1/value-engine/scenarios/${SCENARIO_ID}" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" | jq '.calculation'
```

**Pass Criteria**:
| Check | Expected |
|-------|----------|
| Input variables | Scenario has `inputs` populated from driver tree |
| ROI calculated | `roi` field present with numeric value |
| Payback period | `payback_period` field present |
| NPV/financial output | `npv` or equivalent financial metric present |
| UI interactive | Calculator shows inputs and calculated outputs |

**Common Failures & Fixes**:

| Failure | Diagnosis | Fix |
|---------|-----------|-----|
| Calculate fails | Formula engine error | Inspect formula/math expression parsing |
| Empty inputs | Data flow broken | Verify driver tree → calculator data flow |
| Missing benchmarks | L6 unavailable | Check L6 availability or implement safe fallback defaults |
| Division by zero | Formula issue | Add guards in formula evaluation |

---

#### Step 7: Value Case / Narrative Generation

**UI Goal**: Final generated value case includes narrative, charts, and executive summary.

**API Verification**:

```bash
# 1. Generate value case
CASE_RESPONSE=$(curl -s -X POST http://localhost:8004/v1/value-engine/cases \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": "'${PROSPECT_ID}'",
    "scenario_id": "'${SCENARIO_ID}'"
  }')
CASE_ID=$(echo $CASE_RESPONSE | jq -r '.id')

# 2. Get case
curl -s "http://localhost:8004/v1/value-engine/cases/${CASE_ID}" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" | jq '.case'

# 3. Get preview
curl -s "http://localhost:8004/v1/value-engine/cases/${CASE_ID}/preview" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: demo-acme" | jq '.'
```

**Pass Criteria**:
| Check | Expected |
|-------|----------|
| Executive summary | `executive_summary` or `summary` field present |
| Problem statement | `problem_statement` or equivalent present |
| Proposed solution | `solution` or `proposed_solution` present |
| ROI summary | Financial summary included |
| Next steps | `next_steps` or `action_items` present |
| UI renders | Value Case page shows complete document |
| Navigation persistence | Can navigate back to previous steps, data persists |

**Common Failures & Fixes**:

| Failure | Diagnosis | Fix |
|---------|-----------|-----|
| Generation fails | LLM/template issue | Check Layer 4 LLM tool config, template system |
| Incomplete case | Data mapping broken | Inspect scenario → case data mapping |
| Preview fails | Renderer issue | Check renderer route, serialization, frontend document component |
| Missing sections | Template incomplete | Add missing template sections |

---

### Phase 4: Autonomous Troubleshooting Protocol

**When a step fails**, follow this decision tree:

```
START: Step failed after max_fix_attempts?
│
├─ YES → Document blocker → Halt for manual decision
│
└─ NO → Identify failure type:
    │
    ├─ Missing API endpoint
    │   └─ Check frontend_compat.py → Add alias if exists
    │      └─ Search for equivalent functionality → Add adapter
    │         └─ Document canonical path gap
    │
    ├─ Data persistence issue
    │   └─ Inspect DB tables, migrations
    │      └─ Verify tenant_id filtering
    │         └─ Check foreign keys
    │            └─ Fix non-destructively → Retry
    │
    ├─ Async/worker issue
    │   └─ Verify Redis running
    │      └─ Verify worker running
    │         └─ Check queue names match
    │            └─ Inspect task registration
    │               └─ Fix root cause → Retry
    │
    ├─ CORS/network issue
    │   └─ Fix backend allowed_origins
    │      └─ Fix frontend API base URL
    │         └─ Fix dev proxy
    │            └─ Verify connectivity → Retry
    │
    ├─ Null/empty response
    │   └─ Trace UI → API → Integration → L1/L2/L3/L5/L6
    │      └─ Identify data drop location
    │         └─ Fix connector/adapter/fallback → Retry
    │
    ├─ Schema mismatch
    │   └─ Compare UI expected vs actual API response
    │      └─ Add transform adapter
    │         └─ Retry (preserve UI contract)
    │
    └─ Auth/tenant scoping rejection
        └─ Verify X-Tenant-ID header present
           └─ Verify user belongs to tenant
              └─ Verify route middleware
                 └─ DO NOT disable production auth
                    └─ Fix properly → Retry
```

**Logging Commands for Diagnosis**:

| Service | Log Command |
|---------|-------------|
| Layer 4 | `docker-compose logs -f layer4` or `tail -f logs/layer4.log` |
| Worker | `docker-compose logs -f worker` or `celery -A tasks worker --loglevel=debug` |
| Frontend | Browser DevTools Network tab |
| Database | `docker-compose exec postgres psql -U user -d db -c "SELECT * FROM ..."` |

---

### Phase 5: Final Report

**Produce a concise but complete validation report.**

**Report Template**:

```markdown
# E2E Workflow Validation Report — {YYYY-MM-DD HH:MM}

## Executive Summary

**Result**: {Go / Conditional Go / No-Go}
**Duration**: {X} minutes
**Fixes Applied**: {N} autonomous fixes
**Remaining Blockers**: {N}

---

## Environment Status

| Service | Status | URL | Health | Notes |
|---------|--------|-----|--------|-------|
| Database | ✅/❌ | localhost:5432 | accepting | |
| Redis | ✅/❌ | localhost:6379 | PONG | |
| Layer 1 | ✅/❌ | http://localhost:8001 | {status} | |
| Layer 4 | ✅/❌ | http://localhost:8004 | {status} | |
| Layer 6 | ✅/❌ | http://localhost:8006 | {status} | |
| Frontend | ✅/❌ | http://localhost:3000 | 200 | |
| Worker | ✅/❌ | N/A | {status} | |

---

## Authentication

| Check | Status | Details |
|-------|--------|---------|
| Demo user created | ✅/❌ | {email} |
| Login successful | ✅/❌ | Token type: {jwt/session} |
| Tenant context verified | ✅/❌ | X-Tenant-ID: {value} |

---

## 7-Step Workflow Results

| Step | Name | Status | API Used | Duration | Issues Fixed |
|------|------|--------|----------|----------|--------------|
| 1 | Prospect Setup | ✅/❌ | POST /v1/prospects | {X}s | {N} |
| 2 | Intelligence | ✅/❌ | POST /v1/workflows/intelligence | {X}s | {N} |
| 3 | Hypothesis | ✅/❌ | POST /v1/intelligence/hypotheses | {X}s | {N} |
| 4 | Driver Tree | ✅/❌ | POST /v1/value-engine/driver-tree | {X}s | {N} |
| 5 | Evidence | ✅/❌ | GET /v1/evidence | {X}s | {N} |
| 6 | Calculator | ✅/❌ | POST /v1/value-engine/scenarios | {X}s | {N} |
| 7 | Value Case | ✅/❌ | POST /v1/value-engine/cases | {X}s | {N} |

---

## Critical Evidence

### Data Persistence Verification
```
Prospect ID: {id}
Scenario ID: {id}
Case ID: {id}
Tenant-scoped: YES/NO
```

### Frontend-Backend Integration
```
API Base URL: {url}
CORS Working: YES/NO
Health Check Passes: YES/NO
```

---

## Autonomous Fixes Applied

| # | Phase | Issue | Fix Applied |
|---|-------|-------|-------------|
| 1 | {phase} | {description} | {fix} |
| 2 | ... | ... | ... |

---

## Remaining Blockers

| # | Step | Blocker | Severity | Recommended Action |
|---|------|---------|----------|-------------------|
| 1 | {step} | {description} | 🔴 Critical / 🟡 Warning | {action} |

---

## Go/No-Go Decision

{Go: All seven workflow steps pass with authenticated, tenant-scoped, persisted data and the final value case renders in the UI.}

{Conditional Go: All seven workflow steps pass, but compatibility adapters, fallback data, or documented automated workarounds were required.}

{No-Go: One or more steps remain blocked after fix attempts, or further progress requires architectural, security, encryption, or destructive-data decisions.}

---

## Next Steps

- [ ] Address remaining blockers
- [ ] Review autonomous fixes for production readiness
- [ ] Add regression tests for fixed issues
- [ ] Update documentation with discovered configuration
- [ ] Schedule follow-up validation
```

---

## Output

The skill produces:

1. **Validation Report** (markdown or JSON) containing:
   - Environment status table
   - Authentication verification
   - Step-by-step results with pass/fail status
   - List of autonomous fixes applied
   - Remaining blockers with severity
   - Go/No-Go decision with rationale

2. **Test Artifacts** (stored in temp or specified directory):
   - API response samples
   - Log excerpts from failures
   - Screenshots (if browser automation used)
   - Curl commands for reproduction

3. **Return Code**:
   - `0` = Go (success)
   - `1` = Conditional Go (success with workarounds)
   - `2` = No-Go (blocking issues remain)

---

## Edge Cases

### Partial Environment
If some services are already running:
- Use `skip_phases` parameter to skip Phase 1
- Verify existing services meet version/health requirements
- Only start missing services

### Existing Demo Data
If demo tenant/user already exists:
- Reuse existing data (non-destructive)
- Log warning about pre-existing state
- Continue with workflow validation

### Slow/Resource-Constrained Environment
- Increase `fix_timebox_minutes` parameter
- Reduce parallel service startup
- Add retry delays between health checks
- Document performance constraints in report

### Auth Method Variations
If JWT not used:
- Adapt to session cookies
- Adapt to API keys
- Document auth mechanism used

---

## Anti-Patterns

**NEVER**:
- Fake success by returning mock data without real API calls
- Disable production-grade authentication to make tests pass
- Make destructive database changes (dropping tables, wiping data)
- Modify encryption or secret-handling architecture
- Weaken CORS to `*` without documenting the security implication
- Bypass tenant isolation for convenience
- Edit files without understanding the change's impact
- Continue past a critical failure without documenting it

**AVOID**:
- Adding heavy dependencies just for validation
- Making changes that break other workflows
- Hardcoding credentials in scripts (use env vars)
- Leaving services running in a broken state
- Creating non-reproducible manual workarounds
