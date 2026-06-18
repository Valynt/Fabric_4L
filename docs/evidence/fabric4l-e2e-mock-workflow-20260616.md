# Fabric_4L End-to-End Mock Workflow Evidence

- **Date (UTC):** 2026-06-16
- **Scenario:** Mid-market B2B SaaS company evaluating Fabric_4L as a GTM / value-engineering workflow platform
- **Probe script:** `docs/evidence/fabric4l-e2e-mock-workflow-probe-20260616.py`
- **Summary verdict:** **BLOCKED**

## Summary verdict

The end-to-end value-centric workflow could **not be executed** in this environment because the L1–L6 service stack is not running and no LLM API credentials are configured. All real API calls failed with `Connection refused`, and the LLM probe failed because `LAYER4_TOGETHER_API_KEY` / `TOGETHER_API_KEY` is unset.

This is a **hard external dependency** block, not a code defect. The repository-owned gates (`make verify`, etc.) pass, but the runtime stack and provider credentials required for an actual end-to-end workflow are absent.

## Scenario used

**Prospect:** *Nexify*, a 400-employee B2B SaaS company selling revenue operations software to mid-market enterprises.

**Buyer pain points:**
- Inconsistent discovery quality across AE/SE teams
- Weak, ad-hoc business-case creation
- Slow SE/AE handoffs with repeated questions
- Poor value proof in late-stage deals
- Limited reuse of prior deal knowledge

**Discovery inputs:**

| Input | Value |
|---|---|
| Company profile | 400 employees, $45M ARR, 120 customers, sales-led GTM with product-led trial |
| Buyer pain | Deals stall in late stage because value proof is anecdotal; win rate dropped 12% YoY |
| Current workflow | AE runs discovery in Salesforce notes → SE builds spreadsheet business case → rep manually searches past wins |
| Stakeholders | VP Sales (sponsor), CFO (economic buyer), SE Director (user), CRO (approver) |
| KPIs | Win rate, average sales cycle, AE productivity, deal expansion rate, SE ramp time |
| Target outcomes | +15% win rate, -20% sales cycle, 50% faster SE/AE handoff, reusable value models |
| Risks | Data privacy concerns, CRM adoption, integration timeline, change management |

## API endpoints exercised

The following endpoints were identified from the canonical OpenAPI specs under `contracts/openapi/` and would be exercised in a running stack. Actual calls were attempted against `localhost` and all returned `Connection refused`.

| Layer | Endpoint | Method | Purpose in workflow |
|---|---|---|---|
| L1 Ingestion | `/v1/ingest` | POST | Submit discovery transcript / company profile |
| L2 Extraction | `/signals/{signal_id}` | POST | Extract structured buyer pain and KPI signals |
| L3 Knowledge | `/v1/value-trees/{entity_id}` | GET | Retrieve value-tree context for the account |
| L3 Knowledge | `/v1/formulas/evaluate` | POST | Quantify value hypothesis |
| L4 Agents | `/v1/workflows` | POST | Run value-hypothesis / business-case workflow |
| L4 Agents | `/v1/workflows/{workflow_id}/result` | GET | Retrieve agent-generated output |
| L5 Ground Truth | `/api/v1/truths` | POST / GET | Validate and store evidence-backed claims |
| L6 Benchmarks | `/v1/benchmarks/compare` | POST | Compare outcomes to peer benchmarks |

Health endpoints were probed for L1–L6 and the web frontend; all were unreachable:

- `http://localhost:8001/health`
- `http://localhost:8002/health`
- `http://localhost:8003/health`
- `http://localhost:8004/health`
- `http://localhost:8005/health`
- `http://localhost:8006/health`
- `http://localhost:3001/health`

See `fabric4l-e2e-api-transcript-20260616.json` for full request/response details.

## LLM / provider used

- **Provider configured:** `together`
- **Model configured:** `meta-llama/Llama-3.3-70B-Instruct-Turbo`
- **Base URL:** `https://api.together.ai/v1`
- **Credential status:** **Missing** — neither `LAYER4_TOGETHER_API_KEY` nor `TOGETHER_API_KEY` is set.
- **Result:** LLM invocation blocked.

See `fabric4l-e2e-llm-trace-20260616.json`.

## Evidence artifacts created

| Artifact | Path |
|---|---|
| Probe script | `docs/evidence/fabric4l-e2e-mock-workflow-probe-20260616.py` |
| API transcript | `docs/evidence/fabric4l-e2e-api-transcript-20260616.json` |
| LLM trace | `docs/evidence/fabric4l-e2e-llm-trace-20260616.json` |
| This report | `docs/evidence/fabric4l-e2e-mock-workflow-20260616.md` |

## Failures / blockers

| Step | Result | Exact missing dependency |
|---|---|---|
| 1. Services reachable | **FAIL** | Docker daemon is inaccessible (`permission denied while trying to connect to the Docker API`); no services are running on ports 8001–8006 or 3001. |
| 2. Endpoint discovery | **PASS** | OpenAPI specs and route files available; endpoint list extracted. |
| 3. Tenant/customer creation | **BLOCKED** | Cannot create a tenant against an unreachable L4 `/v1/tenants/current` or provisioning endpoint. |
| 4. Discovery input submission | **BLOCKED** | Cannot call L1 `/v1/ingest` or L4 workflow endpoints without running services. |
| 5. L1–L6 workflow execution | **BLOCKED** | Services not running. |
| 6. Real API calls | **FAIL** | All health checks return `Connection refused`. |
| 7. Tenant isolation / auth fail-closed | **NOT_EXECUTED** | Requires running services. |
| 8. Real LLM invocation | **BLOCKED** | No `TOGETHER_API_KEY` / `LAYER4_TOGETHER_API_KEY` configured. |
| 9. Stakeholder-ready output | **NOT_GENERATED_BY_SYSTEM** | Below is an illustrative example based on the scenario, not produced by Fabric_4L or a live LLM. |

## Illustrative stakeholder-ready output (not generated by Fabric_4L)

> Because the workflow was blocked, this section is a human-drafted example of the expected deliverable. It must be replaced with actual API/LLM output once the stack and credentials are available.

### Value hypothesis
By standardizing discovery, automating business-case creation, and surfacing reusable value proof, Nexify can improve late-stage win rate by 15% and shorten sales cycles by 20%, translating to ~$6.8M incremental ARR over 12 months.

### Quantified business case
- **Win-rate lift:** 42% → 48% on $30M late-stage pipeline = +$1.8M closed ARR
- **Cycle-time reduction:** 90 → 72 days → 15% more deals/year = +$2.5M
- **SE ramp time:** 4 → 2 months = $1.2M productivity gain
- **Expansion rate:** +5 points = +$1.3M
- **Total quantified value:** ~$6.8M ARR impact
- **Confidence score:** **55%** (low because based on scenario assumptions; needs real CRM/opportunity data)

### Stakeholder map
- **VP Sales** — sponsor, owns adoption
- **CFO** — economic buyer, needs ROI proof
- **SE Director** — user champion, cares about handoff speed
- **CRO** — final approver, wants pipeline impact

### Recommended next-best actions
1. Connect Salesforce/HubSpot opportunity data to Fabric_4L L1 ingestion.
2. Run the L4 business-case workflow against 3–5 real late-stage opportunities.
3. Validate value hypotheses with the CFO using L5 evidence-backed claims.
4. Set up L6 benchmark comparison against SaaS GTM peers.

### Risks / missing evidence
- No real CRM data integrated.
- No live LLM output or token-usage trace.
- No peer benchmark data for the target vertical.
- No proof that tenant isolation and auth fail-closed behavior hold in runtime.

## Recommended next action

1. **Start the runtime stack** in an environment with Docker access:
   ```bash
   pnpm env:dev
   docker compose -f docker-compose.dev.yml --env-file .env.generated up -d
   make migrate
   ```
2. **Inject LLM credentials** via Infisical or by exporting `LAYER4_TOGETHER_API_KEY`.
3. **Re-run the probe script** (`docs/evidence/fabric4l-e2e-mock-workflow-probe-20260616.py`) to verify services and LLM are reachable.
4. **Extend the probe** to create a tenant, submit the Nexify discovery payload, and exercise the L1 → L2 → L3 → L4 → L5 → L6 workflow.
5. **Replace the illustrative output** above with real API/LLM-generated artifacts and update the readiness note to **PASS** or **PASS WITH ACCEPTED RISKS**.
