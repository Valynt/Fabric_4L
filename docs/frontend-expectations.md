# Frontend UI Expectations & Backend Mapping

**Generated:** May 2, 2026  

---

## Navigation Domain Mapping

### Home (Dashboard)
**UI Location:** `/`  
**Expectations:**
- KPI cards (usage, accounts, workflows)
- Recent activity feed
- System health status

**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useSystemHealth` | Health monitoring | L4 | `/v1/health` |
| `useUsage` | Usage tracking | L4 | `/v1/billing/usage` |
| `useAccounts` | Account summary | L4 | `/v1/accounts` |

---

### Accounts
**UI Location:** `/accounts`  
**Expectations:**
- Account list with CRM sync status
- Account detail with enrichment data
- Manual sync triggers

**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useAccounts` | Account CRUD | L4 | `/v1/accounts` |
| `useAccount` | Account detail | L4 | `/v1/accounts/{id}` |
| `useSyncAccounts` | CRM sync trigger | L4 | `/v1/accounts/sync` |
| `useAccountSyncStatus` | Sync status | L4 | `/v1/accounts/{id}/sync-status` |
| `useRefreshAccount` | Manual refresh | L4 | `/v1/accounts/{id}/refresh` |

---

### Intelligence Workspace
**UI Location:** `/intelligence/:accountId/*`  
**Tabs:** Signals, Drivers, Evidence, Stakeholders

#### Signals Tab
**Expectations:** AI-surfaced pain points for account  
**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useSignals` | Signal detection | L4 | `/v1/signals` |
| `useProductSignalMatching` | Product-signal match | L3 | `/v1/products/matching/signals` |

#### Drivers Tab
**Expectations:** Root cause analysis  
**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useDrivers` | Driver analysis | L4 | `/v1/analysis/drivers` |
| `useGraphQuery` | Graph relationships | L3 | `/v1/entities/subgraph` |

#### Evidence Tab
**Expectations:** Source documents, confidence grading  
**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useCaseStudies` | Case study library | L3 | `/v1/evidence/case-studies` |
| `useEvidenceSearch` | Search evidence | L3 | `/v1/evidence/search` |
| `useEvidenceIndustryStats` | Stats by industry | L3 | `/v1/evidence/stats/by-industry` |

#### Stakeholders Tab
**Expectations:** Persona-mapped findings  
**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useStakeholders` | Stakeholder mapping | L4 | `/v1/analysis/stakeholders` |

---

### Value Studio Workspace
**UI Location:** `/studio/:accountId/*`  
**Tabs:** Action Plan, Value Model, Narrative

#### Action Plan Tab
**Expectations:** Product-anchored recommendations  
**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useProducts` | Product portfolio | L3 | `/v1/products` |
| `useProductSignalMatching` | Signal-product match | L3 | `/v1/products/matching/signals` |
| `useRecommendations` | AI recommendations | L4 | `/v1/analysis/recommendations` |

#### Value Model Tab
**Expectations:** Quantified business case  
**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useFormulas` | Formula registry | L3 | `/v1/formulas` |
| `useCalculateROI` | ROI calculation | L3 | `/v1/roi/calculate` |
| `useIndustryBenchmarks` | Benchmark data | L3 | `/v1/roi/benchmarks/{industry}` |
| `useValueTrees` | Value tree traversal | L3 | `/v1/value-trees` |

#### Narrative Tab
**Expectations:** Stakeholder-ready packaging  
**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useNarratives` | Generated narratives | L4 | `/v1/narratives` |
| `useGenerateNarrative` | Narrative generation | L4 | `/v1/narratives/generate` |
| `useDealReadiness` | Deal readiness score | L4 | `/v1/intelligence/deal-readiness` |

---

### Context Engine
**UI Location:** `/context-engine`  
**Expectations:** Vendor knowledge base (products, evidence, competitive intel)

**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useProducts` | Product catalog | L3 | `/v1/products` |
| `useCaseStudies` | Evidence library | L3 | `/v1/evidence/case-studies` |
| `useCompetitors` | Competitive intel | L3 | `/v1/competitive/competitors` |
| `useBattlecards` | Battlecard library | L3 | `/v1/competitive/competitors/{id}/battlecards` |
| `usePortfolioSummary` | Analytics summary | L3 | `/v1/products/analytics/summary` |
| `useCapabilityCoverage` | Feature coverage | L3 | `/v1/products/analytics/coverage` |

---

### Deliverables
**UI Location:** `/deliverables`  
**Expectations:** Artifact library, exports

**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useNarratives` | Saved narratives | L4 | `/v1/narratives` |
| `useBusinessCases` | Business case exports | L4 | `/v1/workflows/business-cases` |
| `useValuePacks` | Value pack deployments | L3 | `/v1/value-packs` |

---

### Governance
**UI Location:** `/governance`  
**Expectations:** Audit trails, compliance, formula governance

**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useFormulaApprovals` | Formula governance | L3 | `/v1/formula-governance` |
| `useTruths` | Ground truth validation | L5 (via L4) | `/v1/truths` |
| `useProvenance` | Audit trails | L3 | `/v1/entities/provenance` |
| `useGroundTruthGovernance` | L5 governance | L4 | `/v1/governance/l5` |

---

### Settings
**UI Location:** `/settings`  
**Expectations:** Admin control plane, billing, integrations

**Required APIs:**
| Hook | Backend Service | Layer | Endpoint |
|------|----------------|-------|----------|
| `useBilling` | Stripe billing | L4 | `/v1/billing/*` |
| `useIntegrations` | CRM integrations | L4 | `/v1/integrations` |
| `usePlatformSettings` | Tenant settings | L4 | `/v1/tenants/settings` |
| `useExtractionConfig` | L1/L2 config | L2 | `/v1/ontology/config` |

---

## Hook-to-Backend Matrix

### Data Intelligence Layer (DIL) - 52 Endpoints

| Domain | Hooks | Backend File | Endpoints | Status |
|--------|-------|--------------|-----------|--------|
| **Products** | 13 hooks | `products.py` | 12 | ✅ Integrated |
| **Evidence** | 9 hooks | `evidence.py` | 9 | ✅ Integrated |
| **Competitive Intel** | 10 hooks | `competitive_intel.py` | 10 | ✅ Integrated |
| **ROI Calculator** | 8 hooks | `roi_calculator.py` | 7 | ✅ Integrated |
| **Enrichment** | 4 hooks | `enrichment.py` (L4) | 4 | ✅ Integrated |
| **Hypotheses** | 7 hooks | `value_hypotheses.py` | 7 | ✅ Integrated |
| **Narratives** | 5 hooks | `narratives.py` | 5 | ✅ Integrated |
| **Intelligence** | 3 hooks | `intelligence.py` | 3 | ⚠️ Partial |

### Formula Governance

| Hook | Backend File | Endpoints |
|------|--------------|-----------|
| `useFormulas` | `formulas.py` | 8 |
| `useFormulaApprovals` | `formula_governance.py` | 10 |
| `useFormulaVersions` | `formulas.py` | 3 |
| `useFormulaDependents` | `formulas.py` | 2 |

### Graph & Entity

| Hook | Backend File | Endpoints |
|------|--------------|-----------|
| `useGraphQuery` | `main.py`, `entities.py` | 6 |
| `useEntities` | `entities.py` | 4 |
| `useSubgraph` | `entities.py` | 2 |

### Workflow & Agents

| Hook | Backend File | Endpoints |
|------|--------------|-----------|
| `useWorkflows` | `workflows.py` | 11 |
| `useAgentEvents` | `agent_stream.py` | 1 (SSE) |
| `useSignals` | `signals.py` | 4 |

---

## Frontend Page Inventory

| Page | Location | Primary Hooks | Backend Layer |
|------|----------|---------------|---------------|
| LandingPage | `pages/LandingPage.tsx` | None (static) | - |
| Accounts | `pages/Accounts.tsx` | useAccounts, useCreateAccount | L4 |
| EntityBrowser | `pages/EntityBrowser.tsx` | useGraphQuery, useEntities | L3 |
| GraphExplorer | `pages/GraphExplorer.tsx` | useGraphQuery, useGraphCanvas | L3 |
| ValuePacks | `pages/ValuePacks.tsx` | useValuePacks, useApplyValuePack | L3 |
| FormulaBuilder | `pages/FormulaBuilder.tsx` | useFormulas, useVariables | L3 |
| FormulaList | `pages/FormulaList.tsx` | useFormulas, useFormulaApprovals | L3 |
| IngestionJobs | `pages/IngestionJobs.tsx` | useIngestion, useJobStream | L1/L4 |
| ExtractionEngine | `pages/ExtractionEngine.tsx` | useExtraction, useOntology | L2/L3 |
| OntologyEditor | `pages/OntologyEditor.tsx` | useOntology | L2 |
| SourceConfiguration | `pages/SourceConfiguration.tsx` | useSources | L1 |
| IntelligenceWorkspace | `pages/intelligence/*` | DIL hooks (8 domains) | L3/L4 |
| ValueStudio | `pages/studio/*` | useNarratives, useROICalculator | L3/L4 |
| MyModels | `pages/MyModels.tsx` | useModels (from registry) | L3 |
| BusinessCase | `pages/BusinessCase.tsx` | useBusinessCases | L4 |
| WhitespaceAnalysis | `pages/WhitespaceAnalysis.tsx` | useWhitespace (via tools) | L4 |
| OpportunityFinder | `pages/OpportunityFinder.tsx` | useOpportunities | L4 |
| BillingSettings | `pages/BillingSettings.tsx` | useBilling | L4 |
| UsageDashboard | `pages/UsageDashboard.tsx` | useUsage | L4 |
| Integrations | `pages/Integrations.tsx` | useIntegrations | L4 |
| CommandCenter | `pages/CommandCenter.tsx` | useSystemHealth | L3/L4 |
| Admin pages | `pages/admin/*` | Tenant management | L4 |
