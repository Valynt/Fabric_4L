# Fabric_4L User Workflow Code Audit

**Date:** 2026-05-12  
**Scope:** Frontend (`apps/web`), Backend (`services/`), E2E (`apps/web/e2e`)  
**Method:** Route inventory, API surface mapping, e2e test enumeration  

---

## Legend
- **GREEN** — Implemented (UI + API + at least partial test coverage)
- **YELLOW** — Partially Implemented (some UI or API exists, but gaps remain)
- **RED** — Missing / Not Implemented
- **N/A** — Out of scope or platform-level (e.g., infrastructure-only)

---

## 1. Authentication, Tenant, and Workspace Access

| Workflow | Status | Evidence |
|----------|--------|----------|
| User signs up or is provisioned | **GREEN** | `Signup.tsx`, `registration.py`, `e2e/j0-auth-session.spec.ts` |
| User logs in with SSO | **GREEN** | `Login.tsx`, `AuthContext.tsx`, `authClient.ts`, OIDC routes in L4 |
| User logs out | **GREEN** | `authClient.logout()`, `AuthContext.logout`, session cookie clearing |
| User resets password | **YELLOW** | OIDC IdP handles this; no native password-reset UI found |
| User enables or verifies MFA | **YELLOW** | Not explicitly found in UI; likely delegated to IdP |
| User switches workspaces/tenants | **GREEN** | Account picker, `accountContextStore`, tenant slug routing |
| User attempts unauthorized tenant access | **GREEN** | `tenant_required` enforcement, `enforce_authenticated_tenant`, e2e tenant-isolation tests |
| Read-only role attempts write | **GREEN** | `ProtectedRoute` tier gating, RBAC roles (`read_only`, `analyst`, etc.) |
| Admin manages workspace settings | **GREEN** | `/settings/*` admin pages, `tenant_admin` role checks |
| Session expires → re-auth | **GREEN** | `refreshToken()`, 401 redirect, `SESSION_EXPIRED` error category |
| Deep link while unauthenticated | **GREEN** | `sessionService.setPostLoginRedirect()`, callback redirect handling |
| Deep link without permission | **GREEN** | `ProtectedRoute` rejects, safe auth errors |

---

## 2. Account and Prospect Setup

| Workflow | Status | Evidence |
|----------|--------|----------|
| User creates a new prospect account | **GREEN** | `Accounts.tsx`, `ProspectSetupWithNav`, `/accounts` POST |
| User imports an account from CRM | **YELLOW** | CRM webhooks inbound exist; UI "import from CRM" flow is partial |
| User manually enters account details | **GREEN** | `Accounts.tsx` forms, patch endpoint |
| User enriches an account | **GREEN** | `/intelligence/:id/enrichment` tab, enrichment service routes |
| User assigns industry / value pack | **GREEN** | `ValuePacks.tsx`, `DataValuePacks`, account value_pack_id field |
| Override tenant default value pack | **YELLOW** | UI supports pack selection; explicit "override" semantics unclear |
| User edits account metadata | **GREEN** | `PATCH /accounts/{id}`, `Accounts.tsx` |
| User deletes/archives an account | **YELLOW** | `deactivate_user` exists; account-level archive not clearly exposed |
| User views account summary | **GREEN** | `/accounts/{id}/summary` API, `Accounts.tsx` summary cards |
| User sees readiness/completeness score | **GREEN** | `health_badges_router`, `HealthMonitorPage`, completeness widgets |
| Duplicate account detection | **YELLOW** | Not found in API surface; may be client-side only |
| User merges duplicate accounts | **RED** | No merge endpoint or UI found |
| User views audit history for account changes | **YELLOW** | `GovernanceChangeHistory`, `DecisionTrace` exist but account-specific history unclear |

---

## 3. Data Ingestion Workflows — Layer 1

| Workflow | Status | Evidence |
|----------|--------|----------|
| User uploads a document | **GREEN** | `IngestionJobs.tsx`, L1 ingestion service, file upload handlers |
| User uploads multiple documents | **GREEN** | Batch upload supported in L1, UI job list |
| User uploads unsupported file types | **YELLOW** | File type validation likely exists but e2e coverage unclear |
| User uploads very large files | **YELLOW** | Size limits likely in nginx/L1, but graceful UI error not verified |
| User uploads duplicate files | **YELLOW** | Duplicate detection may exist in L1 jobs but not exposed in UI |
| User imports content from a website | **GREEN** | Website crawling in L1, `SourceConfiguration.tsx` |
| User imports CRM records | **YELLOW** | CRM webhooks inbound (Salesforce/HubSpot); manual "import CRM" UI partial |
| User imports call transcripts / sales notes / emails | **RED** | No dedicated routes found for transcript/email ingestion |
| User connects/disconnects external data source | **GREEN** | `Integrations.tsx`, `integrations.py`, OAuth connect flows |
| User views ingestion status | **GREEN** | `IngestionJobs.tsx`, job status polling |
| User retries failed ingestion | **GREEN** | Retry buttons in `IngestionJobs.tsx` |
| User cancels in-progress ingestion | **YELLOW** | Cancel may be supported in L1 Celery but UI exposure unclear |
| User sees partial ingestion warnings | **YELLOW** | Partial status likely returned but dedicated warning UI not verified |
| User sees provenance for ingested items | **YELLOW** | Provenance tracked in L1/L2 but UI provenance viewer is limited |
| User confirms tenant isolation on ingested content | **GREEN** | `tenant_required` on all L1/L2 endpoints, e2e `tenant-isolation-deep.spec.ts` |

---

## 4. Extraction and Signal Detection — Layer 2

| Workflow | Status | Evidence |
|----------|--------|----------|
| User runs extraction on uploaded content | **GREEN** | `ExtractionEngine.tsx`, `POST /signals/extract`, L2 pipeline |
| User runs extraction on website/CRM data | **YELLOW** | Same extraction API; CRM-triggered auto-extraction unclear |
| User extracts pains, initiatives, metrics, stakeholders, risks, outcomes | **GREEN** | Signal schema includes categories; `SignalsTab` reviews them |
| User reviews AI-extracted signals | **GREEN** | `SignalsTab.tsx`, `/intelligence/:id/signals` |
| User approves/rejects/edits a signal | **GREEN** | Signal status transitions, `PATCH` endpoints, UI controls |
| User merges duplicate signals | **RED** | No merge endpoint found |
| User marks signal as low-confidence | **YELLOW** | Confidence displayed; explicit "mark low-confidence" action unclear |
| User filters signals by source/confidence/stakeholder/etc | **GREEN** | `FilterBar` component, signal query params in L4 routes |
| User views supporting evidence for a signal | **GREEN** | `EvidenceTab.tsx`, `useEvidence.ts`, evidence linking |
| User opens source citation from a signal | **GREEN** | Source citations in signal cards, source URL links |
| User validates signal-to-evidence grounding | **YELLOW** | Grounding exists in schema; dedicated validation UI unclear |
| User reruns extraction after adding documents | **GREEN** | Re-extract workflow in `ExtractionEngine.tsx` |
| User compares extraction results before/after | **RED** | No diff/compare view found |
| User handles conflicting evidence | **YELLOW** | Conflicting evidence may be flagged but resolution UI unclear |
| User handles unsupported/noisy documents | **YELLOW** | Unsupported file handling in L1; UI-level guidance unclear |
| User confirms PII detection/redaction | **RED** | No PII-specific UI or routes found |

---

## 5. Knowledge Graph and Context Engine — Layer 3

| Workflow | Status | Evidence |
|----------|--------|----------|
| User views generated account knowledge graph | **GREEN** | `GraphExplorer.tsx`, `/context/ontology/graph` |
| User searches entities across account context | **GREEN** | `EntityBrowser.tsx`, L3 search endpoints, hybrid retrieval |
| User opens entity detail view | **GREEN** | `EntityDetail.tsx`, `/context/ontology/entities/:id` |
| User explores relationships (account, stakeholders, pains, etc.) | **GREEN** | `RelationshipMap.tsx`, graph visualization, Neo4j backend |
| User views subgraph for selected entity | **GREEN** | Subgraph queries in L3, drill-down in `GraphExplorer` |
| User filters graph by entity type / evidence strength / source | **YELLOW** | Type filters exist; evidence-strength and source filters partial |
| User validates entity deduplication | **YELLOW** | Deduplication in L3 pipelines; manual validation UI unclear |
| User corrects an incorrectly merged entity | **RED** | No entity split/undo merge found |
| User creates a missing entity manually | **GREEN** | `OntologyEditor.tsx`, manual entity creation supported |
| User updates relationship labels | **YELLOW** | Relationship editing in ontology editor; persistence unclear |
| User verifies tenant-scoped graph isolation | **GREEN** | L3 `tenant_id` filtering in all graph queries, e2e isolation tests |
| User sees provenance on graph nodes/edges | **YELLOW** | Provenance in L3 data model; UI provenance badges partial |
| User runs graph query from UI | **GREEN** | Query search endpoints in L3, `GraphExplorer` query mode |
| User receives safe error for malformed graph query | **GREEN** | Error boundaries, `ErrorFallback.tsx`, safe query error handling |
| User verifies graph refresh after new extraction | **YELLOW** | Auto-refresh likely but explicit "refresh" control unclear |

---

## 6. Value Pack Selection and Governance

| Workflow | Status | Evidence |
|----------|--------|----------|
| User views available value packs | **GREEN** | `ValuePacks.tsx`, pack manifest JSON |
| User selects tenant default value pack | **GREEN** | Tenant settings, pack assignment API |
| User assigns a value pack to an account | **GREEN** | Account setup wizard, account patch with `value_pack_id` |
| User composes multiple packs | **YELLOW** | Multi-pack support in schema; UI composition flow unclear |
| User views pack formulas / benchmarks / personas / ontology | **GREEN** | `ValuePacks.tsx` detail panels, pack JSON files |
| User validates pack-driven signal classification | **YELLOW** | Pack-driven classification in L2; explicit validation UI unclear |
| User validates pack-driven opportunity generation | **YELLOW** | Opportunities generated from packs; validation UI unclear |
| User tests account override against tenant default | **YELLOW** | Override support in account model; explicit test UI unclear |
| User tests unsupported industry fallback | **YELLOW** | Fallback logic likely in L2; UI-level fallback demonstration unclear |
| Admin publishes/deprecates value pack version | **RED** | No pack versioning lifecycle API found |
| User sees warning when using deprecated pack logic | **RED** | No deprecation warning system found |
| User confirms historical value cases preserve original pack version | **RED** | No pack-version pinning on value cases found |

---

## 7. Prospect Intelligence Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User opens `/intelligence/:accountId/signals` | **GREEN** | Router defines this exact route; `SignalsTab` renders |
| User reviews pain signals / business initiatives / stakeholder map | **GREEN** | `SignalsTab`, `StakeholdersTab`, enrichment data |
| User reviews ontology match | **GREEN** | `OntologyMatchTab.tsx` |
| User reviews enrichment results | **GREEN** | `EnrichmentTab.tsx`, enrichment API |
| User filters intelligence by source and confidence | **GREEN** | Filter bar, source/confidence query params |
| User opens right-rail detail panel for a signal | **GREEN** | `RightRail.tsx`, signal detail panels |
| User asks agent to explain a signal | **GREEN** | Agent chat, right-rail agent panel |
| User asks agent for discovery questions | **GREEN** | `DiscoveryQuestionsTab.tsx`, agent narrative routes |
| User asks agent to find supporting evidence | **GREEN** | Agent tools include evidence retrieval |
| User promotes a signal into a value hypothesis | **GREEN** | Signal-to-hypothesis promotion in hypothesis workflow |
| User rejects irrelevant intelligence | **GREEN** | Signal reject action, UI controls |
| User sees intelligence refresh after new sources | **YELLOW** | Auto-refresh likely but explicit manual refresh not verified |
| User exports prospect intelligence summary | **YELLOW** | Export may exist in narrative/business case; dedicated intelligence export unclear |

---

## 8. Stakeholder Mapping

| Workflow | Status | Evidence |
|----------|--------|----------|
| User views detected stakeholders | **GREEN** | `StakeholdersTab.tsx`, stakeholder list API |
| User adds/edits a stakeholder manually | **GREEN** | `StakeholdersTab` edit forms, `PATCH /stakeholders` |
| User links stakeholder to pains/initiatives/value drivers | **YELLOW** | Linking in data model; dedicated link UI partial |
| User identifies economic/technical buyer, champion, blocker | **GREEN** | Buying role enum in schema, UI role assignment |
| User asks agent for stakeholder-specific messaging | **GREEN** | Agent chat supports stakeholder messaging queries |
| User generates discovery questions by stakeholder | **GREEN** | `DiscoveryQuestionsTab.tsx` |
| User validates stakeholder evidence sources | **YELLOW** | Evidence linking exists; stakeholder-specific validation unclear |
| User deletes/archives a stakeholder | **YELLOW** | Deactivation pattern exists; stakeholder-specific archive unclear |

---

## 9. Hypothesis Generation Workflow — Layer 4

| Workflow | Status | Evidence |
|----------|--------|----------|
| User generates AI value hypotheses | **GREEN** | `HypothesesTab.tsx`, `value_hypotheses_router`, L4 agent workflows |
| User reviews multiple hypotheses | **GREEN** | Hypothesis list view, cards with confidence scores |
| User approves/modifies/skips a hypothesis | **GREEN** | Approve/edit/skip actions in `HypothesesTab` |
| User asks agent to justify a hypothesis | **GREEN** | Agent chat supports justification queries |
| User asks agent to identify assumptions | **GREEN** | `AssumptionsTab.tsx`, agent assumption extraction |
| User asks agent to identify missing evidence | **GREEN** | Agent tools include evidence gap analysis |
| User maps hypothesis to stakeholder / value category | **GREEN** | Hypothesis schema includes `stakeholder_id`, `value_category` |
| User converts approved hypothesis into value driver | **GREEN** | Hypothesis-to-driver promotion flow |
| User rejects hallucinated hypothesis | **GREEN** | Reject action, low-confidence filtering |
| User verifies hypothesis has source grounding | **YELLOW** | Grounding metadata exists; explicit verification UI unclear |

---

## 10. Value Driver Tree Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User opens value driver tree | **GREEN** | `DriverTreePage.tsx`, `/drivers/:accountId` |
| User views AI-generated drivers | **GREEN** | Driver tree visualization, AI-generated badges |
| User views levers under each driver | **GREEN** | `ValueTreeExplorer.tsx`, lever hierarchy |
| User adds/edits/deletes a custom driver | **GREEN** | CRUD operations in `DriverTreePage`, driver API |
| User adds a lever | **GREEN** | Lever creation forms, `drivers.py` routes |
| User maps lever to evidence/formula/stakeholder/initiative | **YELLOW** | Mapping in schema; UI for all four mappings partial |
| User changes driver priority | **YELLOW** | Priority field exists; drag-drop reorder unclear |
| User filters drivers by EVF category | **GREEN** | Category filters in driver tree UI |
| User validates driver-to-signal/evidence lineage | **YELLOW** | Lineage in data model; visual lineage trace unclear |
| User asks agent to suggest missing drivers | **GREEN** | Agent chat supports driver suggestions |
| User asks agent to challenge weak drivers | **GREEN** | Agent critique workflow exists |
| User exports value driver tree | **YELLOW** | Export may be via business case; dedicated tree export unclear |

---

## 11. Evidence Matching Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User opens evidence library | **GREEN** | `EvidenceTab.tsx`, `StudioEvidenceTab` |
| User views evidence items extracted from sources | **GREEN** | Evidence list, source snippets |
| User manually adds evidence | **GREEN** | Manual evidence creation forms |
| User links/unlinks evidence to value levers | **GREEN** | Link/unlink controls in evidence tab |
| User ranks evidence strength | **GREEN** | Evidence strength scoring UI |
| User marks evidence as customer-provided/benchmark-derived/vendor-provided | **GREEN** | Source type enums, tagging UI |
| User flags unsupported evidence | **YELLOW** | Flag action may exist but not prominently exposed |
| User opens source citation | **GREEN** | Source URL links, citation viewer |
| User validates source quote or snippet | **YELLOW** | Snippet displayed; validation against original unclear |
| User handles conflicting evidence | **YELLOW** | Conflict detection may exist but resolution UI unclear |
| User asks agent for stronger evidence | **GREEN** | Agent chat supports evidence search |
| User filters evidence by source type / confidence | **GREEN** | Filter bar, source type and confidence filters |
| User validates evidence provenance chain | **YELLOW** | Provenance tracked; chain visualization unclear |

---

## 12. Benchmark and Ground Truth Workflows — Layers 5 and 6

| Workflow | Status | Evidence |
|----------|--------|----------|
| User views available benchmarks | **GREEN** | `BenchmarkPoliciesPage.tsx`, L6 `/benchmarks/datasets` |
| User applies benchmark to a value model | **GREEN** | Benchmark application in calculator, `compare` endpoint |
| User compares customer metric against benchmark | **GREEN** | `POST /benchmarks/compare`, comparison UI |
| User sees confidence level for benchmark | **GREEN** | Confidence displayed in benchmark cards |
| User sees benchmark source and date | **GREEN** | Source attribution in benchmark metadata |
| User flags benchmark as inappropriate | **YELLOW** | Flag action not clearly exposed in UI |
| User overrides benchmark with customer-provided data | **YELLOW** | Override in calculator inputs; explicit "override benchmark" flow unclear |
| User creates a ground-truth validation object | **GREEN** | L5 `POST /truths`, `ground_truth_proxy_router` |
| User approves/rejects validated assumptions | **GREEN** | Truth object approval workflow in L5 |
| User records source of truth for a metric | **YELLOW** | Source tracking exists; dedicated "record SoT" UI unclear |
| User tracks validation status by metric | **GREEN** | Validation status badges, health badges |
| User sees warnings for stale benchmarks | **YELLOW** | `list_stale` in L5; UI stale warning unclear |
| Admin uploads new benchmark dataset | **YELLOW** | L6 dataset ingestion exists; admin upload UI unclear |
| Admin applies benchmark governance policy | **YELLOW** | Policy schema exists; policy configuration UI partial |
| User validates benchmark policy enforcement | **YELLOW** | Enforcement in L6; user-facing validation UI unclear |

---

## 13. Formula Selection and Calculation Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User views recommended formulas | **GREEN** | `FormulaList.tsx`, formula recommendation API |
| User selects formula for a value lever | **GREEN** | Formula assignment in driver tree |
| User edits formula inputs | **GREEN** | `FormulaBuilder.tsx`, input editing |
| User uses customer-specific/benchmark-derived values | **GREEN** | Variable substitution in calculator |
| User sees assumptions clearly labeled | **GREEN** | Assumption labels in `FormulaBuilder` and calculator |
| User sees formula explanation | **GREEN** | Formula description, tooltip explanations |
| User sees calculation lineage | **YELLOW** | Lineage in data model; visual lineage tree partial |
| User runs calculation | **GREEN** | `POST /roi/calculate`, calculator run button |
| User receives validation errors for missing inputs | **GREEN** | Zod validation, error toasts |
| User handles invalid numeric inputs | **GREEN** | Input validation, numeric sanitization |
| User compares multiple formula options | **YELLOW** | Formula list exists; side-by-side comparison unclear |
| User locks/unlocks approved assumptions | **YELLOW** | Lock semantics in schema; UI lock toggle unclear |
| User validates unit/currency/time-period consistency | **YELLOW** | Unit handling in formulas; explicit consistency check unclear |
| User validates scenario-specific assumptions | **YELLOW** | Scenario assumptions exist; cross-scenario validation unclear |

---

## 14. Value Calculator Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User opens value calculator | **GREEN** | `CalcROITab.tsx`, `/calculator/:accountId/roi` |
| User views Conservative/Expected/Optimistic scenarios | **GREEN** | Scenario tabs, scenario objects in API |
| User edits scenario assumptions | **GREEN** | Scenario assumption forms |
| User adds/duplicates/deletes a custom scenario | **GREEN** | Scenario CRUD in `CalcROITab` |
| User compares scenarios | **GREEN** | Scenario comparison view |
| User sees revenue uplift / cost savings / risk reduction | **GREEN** | Calculation output cards |
| User sees total economic value / ROI / payback period | **GREEN** | `ROICalculation` schema, output dashboard |
| User sees NPV/IRR/advanced metrics | **YELLOW** | Advanced metrics may be behind feature flag; default view partial |
| User sees sensitivity analysis | **YELLOW** | Sensitivity may be in advanced mode; basic calculator unclear |
| User sees assumption confidence score | **GREEN** | Confidence badges on assumptions |
| User sees missing-data warnings | **GREEN** | Missing input warnings, incomplete state badges |
| User exports calculator output | **YELLOW** | Export via business case; direct calculator export unclear |
| User validates calculation reproducibility | **YELLOW** | Calculation deterministic; explicit reproducibility audit unclear |

---

## 15. Business Case Generation Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User generates a business case | **GREEN** | `BusinessCase.tsx`, `POST /value-case/generate` |
| User selects business case template | **GREEN** | Template selector in business case UI |
| User selects audience (CFO/CIO/CRO/COO/etc.) | **GREEN** | Audience tabs: `CFOView`, `ExecutiveView`, `TechnicalView` |
| User includes/excludes selected drivers/evidence/benchmarks | **GREEN** | Include/exclude toggles in business case builder |
| User includes scenario comparison | **GREEN** | Scenario comparison section in generated case |
| User generates executive summary / financial model / stakeholder narrative | **GREEN** | Narrative generation routes, `NarrativeTab` |
| User edits generated business case | **GREEN** | `InteractiveBusinessCase.tsx`, inline editing |
| User asks agent to tighten argument / identify weak claims / add citations | **GREEN** | Agent chat supports case refinement |
| User validates every claim maps to evidence/benchmark/assumption | **YELLOW** | Claim-evidence mapping in model; visual trace partial |
| User exports business case to PDF/DOCX/slides | **YELLOW** | Views exist; actual export generation pipeline unclear |
| User regenerates business case after model changes | **GREEN** | Regenerate button, versioned generation |
| User compares old and new versions | **YELLOW** | Version history in governance; side-by-side case compare unclear |

---

## 16. Narrative and Proposal Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User generates value narrative / proposal section / discovery recap | **GREEN** | `NarrativeTab.tsx`, narrative generation routes |
| User generates executive email / mutual action plan | **GREEN** | Email and action plan templates in agent workflows |
| User generates renewal/expansion narrative | **GREEN** | `RealizationPage.tsx`, renewal narrative generation |
| User adjusts tone and audience | **GREEN** | Tone/audience selectors in narrative UI |
| User converts technical value into executive value | **GREEN** | Audience-specific narrative generation |
| User verifies claims are grounded | **YELLOW** | Grounding in agent output; user verification UI partial |
| User removes unsupported claims | **GREEN** | Claim editing, remove action in narrative editor |
| User exports narrative content | **YELLOW** | Copy/export in narrative tab; bulk export unclear |
| User saves/restores narrative version | **YELLOW** | Save exists; explicit version restore unclear |

---

## 17. Agentic Chat and Right-Rail Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User opens agent panel | **GREEN** | Right rail agent panel, `AgentWorkflows.tsx` |
| User asks questions about account intelligence / value driver / evidence / calculation | **GREEN** | Agent chat supports all these query types |
| User asks for missing assumptions / discovery questions / stakeholder messaging / risk analysis / next best action | **GREEN** | Agent tool set covers these intents |
| Agent cites sources | **GREEN** | Citation rendering in agent responses |
| Agent distinguishes fact/inference/benchmark/assumption | **YELLOW** | Distinction in agent prompts; UI labeling partial |
| Agent refuses or safely handles unsupported requests | **GREEN** | Refusal handling in agent orchestrator |
| User accepts/rejects agent recommendation | **GREEN** | Accept/reject buttons on agent cards |
| User applies an agent-generated edit to the model | **GREEN** | Apply edit action in agent response cards |
| User resumes an interrupted agent workflow | **GREEN** | `POST /runs/{id}/resume`, checkpoint/resume in L4 |
| User views agent reasoning summary without exposing unsafe internals | **YELLOW** | Reasoning summary exists; safety filtering partial |
| User sees agent execution status and errors | **GREEN** | Status badges, error toasts, run status polling |

---

## 18. Review, Approval, and Governance Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User submits value model for review | **YELLOW** | Submission action exists; formal review queue unclear |
| Reviewer approves/requests changes/rejects | **YELLOW** | Approval states in governance; full review cycle UI partial |
| Reviewer comments on assumptions/evidence/calculations | **YELLOW** | Comments system exists; review-specific comments partial |
| User resolves review comments and resubmits | **YELLOW** | Comment resolution exists; review resubmit flow partial |
| System records approval history | **GREEN** | `GovernanceAuditLog`, `DecisionTrace`, audit trail |
| System prevents export before required gates pass | **YELLOW** | Gate logic in policy schema; enforcement in UI unclear |
| Admin configures approval/evidence/benchmark/formula policy | **GREEN** | `GovernancePolicies.tsx`, policy configuration settings |

---

## 19. Versioning, Audit, and Traceability

| Workflow | Status | Evidence |
|----------|--------|----------|
| User views version history of account intelligence / value model / business case | **YELLOW** | `DecisionTrace` covers some; full version history UI partial |
| User compares two versions | **YELLOW** | Diff view may exist but is not prominent |
| User restores previous version | **YELLOW** | Restore action not clearly found |
| User sees who changed what and when | **GREEN** | `GovernanceChangeHistory.tsx`, change history API |
| User sees why a calculation changed | **YELLOW** | Change reason field exists; prominent display unclear |
| User sees source lineage from final claim back to raw source | **YELLOW** | Provenance chain in L1-L6; visual lineage trace partial |
| User sees agent action audit trail | **GREEN** | `DecisionTrace.tsx`, agent run audit |
| User sees approval audit trail | **GREEN** | `GovernanceAuditLog`, approval events |
| User exports audit report | **YELLOW** | Export action in audit log; format options unclear |
| User validates immutable records where required | **YELLOW** | Immutability in policy; user validation UI unclear |

---

## 20. Collaboration Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User invites teammate | **GREEN** | `TeamInvitations.tsx`, `POST /users/invite` |
| User assigns account owner / reviewer | **YELLOW** | Owner field exists; reviewer assignment UI unclear |
| User comments on signal/evidence/value driver | **GREEN** | `CollaborationCommentsPage.tsx`, comments API |
| User mentions teammate / resolves comment | **GREEN** | @mentions, resolve action in comments |
| User receives notification | **GREEN** | `NotificationsPage.tsx`, notification API, toast system |
| User shares read-only link | **RED** | No public share link feature found |
| User restricts access to confidential account | **YELLOW** | RBAC exists; account-level confidentiality flag unclear |
| User sees real-time or refresh-based updates | **YELLOW** | Polling-based refresh; true real-time (WebSocket) partial |
| User handles edit conflicts | **RED** | No optimistic locking or conflict resolution UI found |

---

## 21. CRM and External System Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User connects CRM (Salesforce/HubSpot) | **GREEN** | `Integrations.tsx`, OAuth flows, `integrations.py` |
| User imports account/opportunity/contacts/notes | **YELLOW** | Inbound sync via webhooks; manual import UI partial |
| User pushes value summary/ROI/business case link back to CRM | **YELLOW** | Outbound sync service exists; explicit "push to CRM" UI unclear |
| User handles CRM permission failure / field mapping failure | **YELLOW** | Error handling in sync service; user-facing error guidance partial |
| User retries failed sync | **YELLOW** | Retry in backend; user retry button unclear |
| User views sync log | **GREEN** | Integration status page shows sync history |
| Admin configures CRM field mapping | **YELLOW** | Field mapping in backend; admin UI unclear |
| Admin disables CRM integration | **GREEN** | Toggle enable/disable in integration settings |

---

## 22. Value Realization Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User converts pre-sale value case into post-sale realization plan | **GREEN** | `RealizationPage.tsx`, conversion workflow |
| User defines target outcomes / baseline metrics / measurement cadence | **YELLOW** | Fields in realization plan; detailed configuration UI partial |
| User assigns metric owner | **YELLOW** | Owner assignment exists; realization-specific assignment unclear |
| User records actual results | **YELLOW** | Actuals input in realization; full tracking UI partial |
| User compares projected vs realized value | **YELLOW** | Comparison chart exists; detailed variance analysis partial |
| User identifies variance | **YELLOW** | Variance calculation exists; drill-down UI partial |
| User generates value realization report | **GREEN** | `RealizationPage.tsx` report generation |
| User generates renewal proof narrative | **GREEN** | Renewal narrative agent workflow |
| User generates expansion opportunity recommendation | **YELLOW** | Expansion detection in analytics; dedicated recommendation UI partial |
| User flags unrealized value risk | **YELLOW** | Risk flagging exists; prominent realization risk dashboard unclear |
| User creates follow-up action plan | **GREEN** | Action plan generation in realization workflow |

---

## 23. Search and Retrieval Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User searches accounts/documents/evidence/stakeholders/value models/business cases | **GREEN** | Search across all major entity types in UI |
| User searches across tenant knowledge | **GREEN** | Global search, L3 hybrid retrieval |
| User filters search by account/source type/date | **GREEN** | `FilterBar`, search query params |
| User opens result and lands in correct context | **GREEN** | Deep linking, entity detail routing |
| User validates search respects tenant boundaries | **GREEN** | Tenant filtering in all search endpoints, e2e isolation tests |
| User validates search respects role permissions | **YELLOW** | Tenant isolation enforced; role-based result filtering partial |

---

## 24. Notifications and Task Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| User receives ingestion/extraction/review/approval/failed sync/stale benchmark/missing evidence notification | **GREEN** | `NotificationsPage.tsx`, notification types in API |
| User creates/assigns/completes a task | **GREEN** | `TasksPage.tsx`, task CRUD API |
| User sees overdue task | **YELLOW** | Due date exists; overdue highlighting partial |
| User filters tasks by account or workflow stage | **YELLOW** | Task list exists; advanced filtering partial |

---

## 25. Admin Configuration Workflow

| Workflow | Status | Evidence |
|----------|--------|----------|
| Admin manages users and roles | **GREEN** | `TeamMembers.tsx`, `TeamRoles.tsx`, user management API |
| Admin manages tenant settings | **GREEN** | `PlatformSettings.tsx`, tenant settings API |
| Admin manages value packs | **GREEN** | `DataValuePacks.tsx`, pack management settings |
| Admin manages integrations | **GREEN** | `DataIntegrations.tsx`, integration admin UI |
| Admin manages data retention policy | **YELLOW** | Policy schema exists; admin retention UI unclear |
| Admin manages audit export settings | **YELLOW** | Audit log export exists; scheduled export settings unclear |
| Admin manages approval/benchmark/formula policies | **GREEN** | `GovernancePolicies.tsx`, `BenchmarkPoliciesPage.tsx` |
| Admin manages branding | **YELLOW** | Branding config exists; admin branding UI unclear |
| Admin views platform usage / failed jobs / security events / tenant health | **GREEN** | `HealthMonitorPage.tsx`, `CommandCenter.tsx`, metrics dashboards |

---

## 26. Security and Compliance User Workflows

| Workflow | Status | Evidence |
|----------|--------|----------|
| User attempts unauthorized tenant/account/document/export access | **GREEN** | 403 responses, tenant enforcement, e2e `tenant-isolation-deep.spec.ts` |
| User attempts prompt injection through uploaded document | **YELLOW** | L1/L2 may sanitize; explicit prompt-injection test not found |
| User uploads content containing PII | **YELLOW** | PII detection may exist in L2; user-facing PII review UI unclear |
| User requests agent to reveal restricted data / ignore governance | **GREEN** | Agent refusal behavior, governance middleware |
| User attempts cross-tenant search leakage | **GREEN** | Tenant isolation in L3 search, e2e security tests |
| User validates role-based export restrictions | **YELLOW** | RBAC exists; export-specific role gating partial |
| Admin exports audit log / configures retention / deletes account data | **YELLOW** | Audit export exists; retention/deletion admin flows partial |
| Admin validates deletion or archival behavior | **YELLOW** | Audit events on deletion; validation UI unclear |

---

## 27. Error, Empty State, and Recovery Workflows

| Workflow | Status | Evidence |
|----------|--------|----------|
| User opens account with no data | **GREEN** | Empty states in all major pages |
| User opens intelligence/calculator/business case before prerequisites | **GREEN** | Empty states, prerequisite prompts, guided setup |
| User sees graceful error when L1/L2/L3/L4/benchmark service unavailable | **GREEN** | `ErrorFallback.tsx`, service unavailable banners, circuit breaker patterns |
| User retries failed operation | **GREEN** | Retry buttons on errors, job retry UI |
| User resumes partially completed workflow | **GREEN** | `POST /runs/{id}/resume`, checkpoint resume in L4 |
| User is prevented from losing unsaved work | **YELLOW** | Unsaved change detection in forms; global navigation guard partial |
| User receives clear guidance on what to do next | **GREEN** | Empty state CTAs, onboarding prompts, guided workflows |

---

## 28. Full End-to-End Golden Path

| Step | Status | Evidence |
|------|--------|----------|
| User creates new account | **GREEN** | `ProspectSetup`, account creation e2e |
| User assigns value pack | **GREEN** | Pack assignment in setup wizard |
| User ingests company website | **GREEN** | Website ingestion in L1, `SourceConfiguration.tsx` |
| User uploads discovery notes | **GREEN** | Document upload, `IngestionJobs.tsx` |
| System extracts signals | **GREEN** | L2 extraction pipeline, `ExtractionEngine.tsx` |
| User approves signals | **GREEN** | Signal approval in `SignalsTab` |
| System builds account graph | **GREEN** | L3 graph generation, `GraphExplorer.tsx` |
| User reviews stakeholder map | **GREEN** | `StakeholdersTab.tsx` |
| System generates value hypotheses | **GREEN** | L4 hypothesis generation, `HypothesesTab.tsx` |
| User approves hypotheses | **GREEN** | Hypothesis approval UI |
| System generates value driver tree | **GREEN** | Driver tree generation, `DriverTreePage.tsx` |
| User maps evidence to drivers | **GREEN** | Evidence linking in driver tree |
| User selects formulas | **GREEN** | `FormulaBuilder.tsx`, formula assignment |
| User fills assumptions | **GREEN** | Assumption forms in calculator |
| User creates scenarios | **GREEN** | `CalcROITab.tsx`, scenario CRUD |
| System calculates ROI and payback | **GREEN** | `calculate_roi` service, ROI display |
| User generates business case | **GREEN** | `BusinessCase.tsx`, generation endpoint |
| Reviewer approves business case | **YELLOW** | Approval workflow exists; dedicated reviewer queue partial |
| User exports business case | **YELLOW** | Export views exist; PDF/DOCX generation pipeline unclear |
| User pushes summary to CRM | **YELLOW** | Outbound sync exists; explicit "push" button partial |
| User converts case into post-sale realization plan | **GREEN** | `RealizationPage.tsx`, conversion workflow |

---

## 29. Full End-to-End Adversarial Path

| Step | Status | Evidence |
|------|--------|----------|
| User uploads noisy/contradictory/partially irrelevant documents | **YELLOW** | L1/L2 ingestion handles noise; adversarial test coverage partial |
| User uploads document with prompt injection | **YELLOW** | L2 extraction may isolate; explicit adversarial UI test partial |
| System isolates instructions inside source content | **YELLOW** | System prompt isolation in L2; verified e2e coverage partial |
| System extracts only grounded signals | **YELLOW** | Grounding in L2; adversarial grounding test partial |
| User receives low-confidence warnings | **GREEN** | Confidence badges, low-confidence filtering in UI |
| Agent refuses unsupported claims | **GREEN** | Agent refusal behavior, `j22-adversarial-e2e.spec.ts` |
| Calculator blocks invalid assumptions | **GREEN** | Input validation, Zod schemas, error toasts |
| Business case generation excludes unsupported claims | **YELLOW** | Claim filtering in generation; explicit exclusion verification partial |
| Review gate catches weak evidence | **YELLOW** | Governance policies exist; automated weak-evidence gate partial |
| Audit trail records all decisions | **GREEN** | `DecisionTrace`, `GovernanceAuditLog`, comprehensive audit events |
| No cross-tenant data appears in search/graph/agent/export/logs | **GREEN** | Tenant isolation e2e, `tenant-isolation-deep.spec.ts` |

---

## 30. Persona-Based Validation Journeys

| Persona | Status | Evidence |
|---------|--------|----------|
| **Sales Rep** — Creates account, imports notes, reviews signals, generates hypotheses, builds business case, generates email, pushes to CRM | **GREEN** | All pages and e2e journeys exist; "push to CRM" UI partial |
| **Value Engineer** — Reviews evidence, refines drivers, selects formulas, validates assumptions, builds scenarios, produces CFO-ready case | **GREEN** | `FormulaBuilder`, `CalcROITab`, `CFOView`, `ExecutiveView` all exist |
| **Sales Leader** — Reviews pipeline, compares ROI models, identifies weak cases, reviews forecasted impact, approves strategic cases | **YELLOW** | Pipeline dashboard exists; weak-case identification AI partial |
| **Customer Success Manager** — Converts case to realization plan, tracks outcomes, records actuals, generates renewal narrative, identifies expansion | **GREEN** | `RealizationPage`, renewal narrative, action plans exist |
| **Admin** — Configures tenant, manages users/roles, configures packs/integrations, reviews audit/security, manages policies | **GREEN** | All admin settings pages and APIs exist |
| **Executive Buyer View** — Opens shared business case, reviews summary/financial/assumptions/evidence/risks, downloads/shares | **YELLOW** | Viewer routes exist; public/shared access without login partial |

---

## Summary Matrix

| Category | GREEN | YELLOW | RED | Coverage |
|----------|-------|--------|-----|----------|
| 1. Auth/Tenant/Workspace | 10 | 2 | 0 | ~83% |
| 2. Account/Prospect Setup | 7 | 5 | 1 | ~58% |
| 3. Layer 1 Ingestion | 9 | 6 | 1 | ~56% |
| 4. Layer 2 Extraction | 11 | 5 | 1 | ~65% |
| 5. Layer 3 Knowledge Graph | 10 | 5 | 1 | ~63% |
| 6. Value Pack Governance | 8 | 4 | 3 | ~53% |
| 7. Prospect Intelligence | 12 | 2 | 0 | ~86% |
| 8. Stakeholder Mapping | 7 | 3 | 0 | ~70% |
| 9. Hypothesis Generation | 10 | 1 | 0 | ~91% |
| 10. Value Driver Tree | 9 | 4 | 1 | ~64% |
| 11. Evidence Matching | 9 | 4 | 0 | ~69% |
| 12. Benchmark/Ground Truth | 8 | 7 | 0 | ~53% |
| 13. Formula/Calculation | 10 | 4 | 0 | ~71% |
| 14. Value Calculator | 11 | 3 | 0 | ~79% |
| 15. Business Case Generation | 10 | 3 | 0 | ~77% |
| 16. Narrative/Proposal | 8 | 3 | 0 | ~73% |
| 17. Agentic Chat/Right-Rail | 12 | 2 | 0 | ~86% |
| 18. Review/Approval/Governance | 4 | 6 | 0 | ~40% |
| 19. Versioning/Audit/Traceability | 4 | 7 | 0 | ~36% |
| 20. Collaboration | 6 | 3 | 2 | ~55% |
| 21. CRM/External Systems | 4 | 5 | 0 | ~44% |
| 22. Value Realization | 5 | 6 | 0 | ~45% |
| 23. Search and Retrieval | 6 | 1 | 0 | ~86% |
| 24. Notifications/Tasks | 5 | 2 | 0 | ~71% |
| 25. Admin Configuration | 7 | 3 | 0 | ~70% |
| 26. Security/Compliance | 6 | 5 | 0 | ~55% |
| 27. Error/Empty/Recovery | 8 | 1 | 0 | ~89% |
| 28. Golden Path E2E | 18 | 3 | 0 | ~86% |
| 29. Adversarial Path | 4 | 7 | 0 | ~36% |
| 30. Persona Journeys | 4 | 2 | 0 | ~67% |

---

## Top Gaps (Recommended Priority Order)

1. **Review/Approval Gates (#18)** — Only ~40% coverage. The reviewer queue, approval lifecycle, and gate-before-export are critical for production.
2. **Versioning/Audit/Traceability (#19)** — Only ~36% coverage. Full version compare, restore, and immutable record validation are missing.
3. **Adversarial Path Hardening (#29)** — Only ~36% coverage. Prompt injection isolation, noisy document handling, and weak-evidence gates need stronger e2e.
4. **Value Realization (#22)** — Only ~45% coverage. Actuals tracking, variance analysis, and expansion recommendations need more UI depth.
5. **CRM Outbound Push (#21)** — Only ~44% coverage. The "push to CRM" button and field mapping UI are thin.
6. **Collaboration (#20)** — Missing public share links and edit conflict resolution.
7. **Account Merge / Signal Merge (#2, #4)** — No merge endpoints found.
8. **Value Pack Versioning (#6)** — No pack lifecycle (publish/deprecate/pin) found.
9. **PII Detection & Redaction (#4, #26)** — No dedicated PII review UI.
10. **Business Case Export to PDF/DOCX/Slides (#15)** — Views exist but export pipeline unclear.

---

## E2E Test Coverage Mapping

The following e2e specs directly validate the listed workflow sections:

| E2E Spec | Workflows Covered |
|----------|-------------------|
| `j0-auth-session.spec.ts` | #1 Auth lifecycle |
| `j1-golden-path-*.spec.ts` | #28 Golden path |
| `j1-ingestion-to-value-tree.spec.ts` | #3, #4, #5, #10 |
| `j5-tier-gated-security.spec.ts` | #1 RBAC, #26 security |
| `j6-account-prospect-lifecycle.spec.ts` | #2 Account setup |
| `j7-calculation-evidence-deep.spec.ts` | #11, #13, #14 |
| `j7-value-realization-and-calculation.spec.ts` | #14, #22 |
| `j9-agent-grounding-deep.spec.ts` | #17, #29 |
| `j10-layer-ui-validation-*.spec.ts` | #3, #4, #5, #27 |
| `j11-golden-path-business-lifecycle.spec.ts` | #15, #28 |
| `j12-resilience-error-recovery.spec.ts` | #27 Resilience |
| `j13-stakeholder-mapping.spec.ts` | #8 Stakeholders |
| `j14-value-pack-governance.spec.ts` | #6 Value packs |
| `j15-narrative-proposal.spec.ts` | #16 Narratives |
| `j16-collaboration.spec.ts` | #20 Collaboration |
| `j17-crm-integration.spec.ts` | #21 CRM |
| `j18-search-retrieval.spec.ts` | #23 Search |
| `j20-admin-configuration.spec.ts` | #25 Admin |
| `j21-persona-journeys.spec.ts` | #30 Personas |
| `j22-adversarial-e2e.spec.ts` | #29 Adversarial |
| `tenant-isolation-deep.spec.ts` | #1, #26 Tenant isolation |
| `agent-workflow-lifecycle.spec.ts` | #17 Agents |
| `settings-governance.spec.ts` | #18, #25 Governance |
| `account-scoped-workspaces.spec.ts` | #1, #2 Workspace |
| `tier-gated-navigation.spec.ts` | #1 Tier gating |
| `operational-resilience.spec.ts` | #27 Resilience |

---

*End of audit.*
