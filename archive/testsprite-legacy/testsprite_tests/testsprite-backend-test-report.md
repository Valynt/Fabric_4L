# TestSprite AI Testing Report — Backend (MCP)

---

## 1️⃣ Document Metadata

- **Project Name:** Fabric_4L
- **Project Type:** Backend (Python FastAPI / Multi-layer microservices)
- **Date:** 2026-05-13
- **Prepared by:** TestSprite AI Team
- **Server Mode:** Production (no backend services running)
- **Local Endpoint:** http://localhost:3001 (frontend preview server)
- **Total Tests Planned:** 10
- **Tests Executed:** 10
- **Tests Passed:** 0
- **Tests Failed:** 10
- **Tests Blocked:** 0

---

## 2️⃣ Requirement Validation Summary

### Requirement: Tenant Registration

**Description:** Verify that the POST /tenants/register endpoint successfully registers a new tenant with valid data.

| Test ID | Title | Status | Analysis |
|---------|-------|--------|----------|
| TC001 | POST /tenants/register should register new tenant | FAILED | Expected 200/201 but received 404. The frontend preview server on port 3001 does not expose this backend endpoint. |

**Requirement Status:** NOT VALIDATED — no backend service running.

---

### Requirement: Authentication (OIDC Callback)

**Description:** Verify that the POST /auth/token endpoint exchanges authorization codes for JWT tokens.

| Test ID | Title | Status | Analysis |
|---------|-------|--------|----------|
| TC002 | POST /auth/token OIDC callback should exchange code for JWT | FAILED | Expected 200 OK, got 404. No authentication service (Layer 4) was running on the tested port. |

**Requirement Status:** NOT VALIDATED — no backend service running.

---

### Requirement: Account Management

**Description:** Verify account listing and creation via REST API endpoints.

| Test ID | Title | Status | Analysis |
|---------|-------|--------|----------|
| TC003 | GET /api/v1/accounts should return account list | FAILED | Expected 200 or 401, got 404. The accounts API endpoint was not available on the frontend server. |
| TC004 | POST /api/v1/accounts should create account | FAILED | Unexpected status code 404. Account creation endpoint was not reachable. |

**Requirement Status:** NOT VALIDATED — no backend service running.

---

### Requirement: Intelligence Workspace

**Description:** Verify signals retrieval for a selected account.

| Test ID | Title | Status | Analysis |
|---------|-------|--------|----------|
| TC005 | GET /api/v1/intelligence/signals should return account signals | FAILED | JSONDecodeError: the response body was empty. The endpoint returned a non-JSON 404 response from the frontend server. |

**Requirement Status:** NOT VALIDATED — no backend service running.

---

### Requirement: Driver Tree

**Description:** Verify driver tree retrieval and update for a specified account.

| Test ID | Title | Status | Analysis |
|---------|-------|--------|----------|
| TC006 | GET /api/v1/drivers/:accountId should return driver tree | FAILED | Account creation failed (404 from /api/v1/accounts), so the dependent driver tree test could not proceed. |
| TC007 | PUT /api/v1/drivers/:accountId should update driver tree | FAILED | 404 Client Error for /api/v1/accounts. No backend service to create test accounts or update driver trees. |

**Requirement Status:** NOT VALIDATED — no backend service running.

---

### Requirement: ROI Calculator

**Description:** Verify ROI calculation retrieval and execution endpoints.

| Test ID | Title | Status | Analysis |
|---------|-------|--------|----------|
| TC008 | GET /api/v1/calculator/roi should return ROI calculations | FAILED | Authentication failed: 404 for /auth/token. Could not obtain a token to test the calculator endpoint. |
| TC009 | POST /api/v1/calculate should perform calculations | FAILED | Expected 200, got 404. The calculation endpoint was not available on the frontend server. |

**Requirement Status:** NOT VALIDATED — no backend service running.

---

### Requirement: Business Cases (Deliverables)

**Description:** Verify business case listing endpoint.

| Test ID | Title | Status | Analysis |
|---------|-------|--------|----------|
| TC010 | GET /api/v1/deliverables/cases should return business cases | FAILED | 404 Client Error for /api/v1/deliverables/cases. The deliverables API was not running. |

**Requirement Status:** NOT VALIDATED — no backend service running.

---

## 3️⃣ Coverage & Matching Metrics

| Requirement | Total Tests | Passed | Failed | Blocked |
|-------------|-------------|--------|--------|---------|
| Tenant Registration | 1 | 0 | 1 | 0 |
| Authentication (OIDC Callback) | 1 | 0 | 1 | 0 |
| Account Management | 2 | 0 | 2 | 0 |
| Intelligence Workspace | 1 | 0 | 1 | 0 |
| Driver Tree | 2 | 0 | 2 | 0 |
| ROI Calculator | 2 | 0 | 2 | 0 |
| Business Cases (Deliverables) | 1 | 0 | 1 | 0 |
| **TOTAL** | **10** | **0** | **10** | **0** |

- **Pass Rate:** 0.00%
- **Fail Rate:** 100.00%
- **Coverage:** 0% of requirements validated

---

## 4️⃣ Key Gaps / Risks

### Critical Finding: No Backend Services Running

**Root Cause:**
All 10 backend tests failed because the target endpoint (`http://localhost:3001`) was the **frontend Vite preview server**, not the backend API services. Every HTTP request to backend API paths returned HTTP 404 because the frontend server does not proxy or serve those routes.

**Expected Backend Architecture:**
Per `AGENTS.md` and `docker-compose.dev.yml`, the backend is a multi-layer microservices architecture:

| Layer | Service | Port | Responsibility |
|-------|---------|------|----------------|
| Layer 1 | layer1-ingestion | 8001 | Playwright crawling, Celery jobs, Redis queues |
| Layer 2 | layer2-extraction | 8002 | Pydantic v2 extraction, LLM extraction, RDF/OWL |
| Layer 3 | layer3-knowledge | 8003 | Neo4j, GraphRAG, hybrid retrieval, pgvector |
| Layer 4 | layer4-agents | 8004 | LangGraph workflows, ROI calculator, business case generation |
| Layer 5 | layer5-ground-truth | 8005 | TruthObject validation, maturity ladder |
| Layer 6 | layer6-benchmarks | 8006 | Peer comparison, statistical validation |

The frontend (`apps/web`) proxies API calls to these layers via `VITE_PROXY_L1_URL` through `VITE_PROXY_L6_URL` environment variables during development.

**Why Tests Failed:**
1. The tests were configured to run against `http://localhost:3001` (frontend preview)
2. Backend services on ports 8001–8006 were not started
3. The frontend preview server (`vite preview`) does NOT proxy API requests to backend services
4. Every backend API call returned `404 Not Found`

**Recommendations:**

1. **Start Backend Services Before Testing**
   Run the full development stack with Docker Compose:
   ```bash
   docker compose -f docker-compose.dev.yml up --build
   ```
   This starts PostgreSQL, Redis, Neo4j, Layer 4 (FastAPI), and the frontend with proper API proxying.

2. **Point Tests to the Correct Backend Port**
   Once services are running, backend tests should target the specific layer ports:
   - Layer 4 (Auth, Accounts, Workflows): `http://localhost:8004`
   - Layer 3 (Graph, Intelligence): `http://localhost:8003`
   - Layer 2 (Extraction): `http://localhost:8002`
   - Layer 5 (Ground Truth): `http://localhost:8005`
   - Layer 6 (Benchmarks): `http://localhost:8006`

3. **Enable DEV_AUTH_BYPASS for Test Automation**
   The `docker-compose.dev.yml` sets `DEV_AUTH_BYPASS=true`, which pre-populates tenant/user context without JWT. This is ideal for automated testing.

4. **Consider Contract Testing Instead**
   The project already has contract tests in `apps/web/src/api/__tests__/contract/` and `tests/contract/`. These are a more reliable way to validate API shapes without needing live services.

5. **Seed Test Data Before Running API Tests**
   The project provides E2E seed scripts:
   ```bash
   pnpm --dir apps/web run seed:e2e
   ```
   This creates demo accounts, users, and data needed for API tests.

**Risk Rating:** HIGH — Backend API testing cannot proceed without the multi-layer service stack running. The current test results reflect infrastructure misconfiguration, not application bugs.
