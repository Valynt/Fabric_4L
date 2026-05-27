# AI-Native SaaS Subpack (S2.3) — OpenClaw Skill

## 1. Skill Identity Block

| Field | Value |
|-------|-------|
| **skill_name** | AI-Native SaaS Subpack (S2.3) |
| **description** | Vertical-specialized value intelligence for AI-Native SaaS companies where AI/ML is the core value proposition, not a bolt-on feature. Covers AI copilots, agentic automation, AI sales/support, AI analytics, document intelligence, coding tools, AI SecOps, compliance monitoring, AI knowledge management, and AI search/RAG platforms. Designed for enterprise sellers targeting AI Product Leads, ML Engineers, Responsible AI Officers, Prompt Engineers, AI Ops Managers, and Data/AI Architects alongside traditional C-suite buyers. |
| **version** | 1.0.0 |
| **domain** | Industry |
| **pack_type** | subpack |
| **parent_master** | saas-master-v1 |

---

## 2. Triggers

Auto-load this skill when the user query matches any of the following natural-language patterns:

1. **"LLM hallucination detection"** — prospect struggling with AI output accuracy or customer complaints about wrong AI answers
2. **"AI agent reliability"** — prospect deploying agentic workflows with high human fallback rates or task completion failures
3. **"RAG pipeline optimization"** — prospect building retrieval-augmented generation with poor accuracy, stale embeddings, or vector DB scaling issues
4. **"AI governance compliance"** — prospect blocked by enterprise deals due to missing model cards, bias audits, or lineage documentation
5. **"analyze an AI-native SaaS company"** — general prospect/account targeting where AI is core to the product
6. **"inference cost optimization"** — prospect with ballooning LLM API bills or token budget overruns
7. **"prompt injection security"** — prospect with AI security vulnerabilities or red-team jailbreak findings
8. **"AI feature adoption plateau"** — prospect with declining AI MAU, low activation, or poor AI feature NPS
9. **"multi-model LLM strategy"** — prospect locked into single provider with no failover or abstraction layer
10. **"AI support automation ROI"** — prospect with AI support agents creating escalation loops or CSAT erosion
11. **"vector database scaling"** — prospect with P99 latency degradation or vector storage cost spikes
12. **"AI talent bottleneck"** — prospect struggling to hire/retain ML engineers or with slow model iteration cycles

---

## 3. Reasoning Flow

### Step 1: Load Parent Master First
Always load `saas-master-v1` before applying this subpack. The master provides:
- Base value driver framework (VD001-VD050)
- Base persona archetypes (CFO, CRO, CTO, VP Engineering, VP Product, CISO, VP Customer Success)
- Financial formula templates (CAC, LTV, payback, retention)
- Signal source taxonomy and benchmark methodology
- Governance framework

### Step 2: Detect AI-Native Signals
Scan the prospect/account for AI-native signal patterns. Prioritize these signal categories in order of urgency:

| Priority | Signal Category | Key Indicators |
|----------|----------------|----------------|
| P0 | AI Security & Compliance | Red-team jailbreaks >10%, PII in prompt logs, missing DPAs, no bias testing |
| P1 | AI Output Quality | Hallucination rate >3%, RAG accuracy <70%, agent completion <60% |
| P1 | AI Cost Economics | Inference cost >25% COGS, surprise $50K+ monthly LLM bills, no tenant tracking |
| P2 | AI Governance Gaps | No model registry, enterprise deals stalled >45 days on governance, missing model cards |
| P2 | AI Adoption Decline | MAU declining 2+ months, activation <10%, NPS below +10 |
| P3 | Infrastructure Scaling | Vector DB P99 >500ms, embedding model >12 months stale, provider lock-in >80% |

### Step 3: Confirm Signals with Required Evidence
For each primary signal detected, validate with confirmation signals:

- **LLM bill spike (SR-AI-001)**: Confirm with tenant-level token audit, new feature launch correlation, customer usage pattern change.
- **Hallucination complaint spike (SR-AI-002)**: Confirm with automated eval benchmark, recent model/prompt change date, customer segment analysis.
- **Red-team jailbreak (SR-AI-005)**: Confirm with attack technique documentation, defense test after hardening, OWASP LLM Top 10 gap assessment.
- **Enterprise governance stall (SR-AI-004)**: Confirm with CRM opportunity notes, security questionnaire status, competitor win analysis.

Use `calculateSignalConfidence(primarySignalStrength, confirmationSignals[], dataQuality)` from `signals-examples.ts` to compute final confidence.

### Step 4: Map Signals to Pains → Personas → KPIs → Value Drivers
Apply the subpack's 36 value driver mappings (VD-AI-001 through VD-AI-036):

1. **Signal → Pain**: Match detected signal to one of 18 AI-native pains (P-AI-001 to P-AI-018).
2. **Pain → Personas**: Identify affected personas from the 6 AI-native personas plus inherited master personas.
3. **Pain → KPIs**: Reference the 52 vertical KPIs with benchmark ranges.
4. **KPIs → Value Drivers**: Connect quantified gaps to revenue uplift, cost savings, or risk reduction hypotheses.

### Step 5: Calculate Financial Impact
Select from 15 AI-native value formulas (VF-AI-001 to VF-AI-015):

- **Cost Savings**: Inference cost avoidance (VF-AI-001, VF-AI-009), agent automation ROI (VF-AI-007), vector DB cost at scale (VF-AI-008)
- **Revenue Uplift**: RAG quality revenue impact (VF-AI-003), AI feature churn reduction (VF-AI-004), compliance revenue enablement (VF-AI-011)
- **Risk Reduction**: Hallucination-induced support cost (VF-AI-002), bias audit cost avoidance (VF-AI-014), training data licensing risk (VF-AI-015)

Apply confidence rules: HIGH when based on production data; MEDIUM when from sample or validated estimates; LOW for speculative scenarios.

### Step 6: Score Confidence & Package Output
Grade the overall analysis:
- **HIGH (≥0.80)**: Multiple production signals confirmed with benchmark data and clear persona alignment
- **MEDIUM (0.60–0.79)**: Sample-based signals or partial confirmation; plausible but needs validation
- **LOW (<0.60)**: Estimated signals or conflicting evidence; use as exploratory hypothesis only

---

## 4. Inheritance Map

### Master Skill to Load First
**`saas-master-v1`** must be loaded before this subpack.

### What the Master Provides (Inherited)
| Component | Master Coverage |
|-----------|-----------------|
| Value Driver Framework | VD001-VD050 base taxonomy |
| Base Personas | CFO, CRO, CTO, VP Engineering, VP Product, CISO, VP Customer Success, CHRO, VP People, General Counsel, VP Compliance |
| Financial Formulas | CAC, LTV, CAC Payback, Net Revenue Retention, Gross Margin, Rule of 40 |
| Signal Taxonomy | Financial, operational, behavioral, competitive signal categories |
| Benchmark Methodology | Segment-scoped, confidence-graded, dated, sourced |

### What This Subpack Adds (Vertical-Specialized)
| Component | Subpack Addition | Count |
|-----------|-----------------|-------|
| Vertical Pains | LLM hallucination, model governance gaps, inference cost escalation, prompt injection, RAG failure, agent reliability, copyright liability, adoption plateau, vector DB scaling, fine-tuning complexity, talent scarcity, bias deficits, latency degradation, PII leakage, eval infrastructure absence, multi-model fragmentation, support agent escalation loops, prompt management chaos | 18 |
| Vertical KPIs | Hallucination rate, retrieval recall@K, agent task completion, prompt injection block rate, inference cost per 1K tokens, model registry coverage, vector DB latency, embedding freshness, fine-tuning deployment time, ML team capacity ratio, bias testing coverage, explainability coverage, demographic parity delta, AI feature P95 latency, PII detection coverage, automated evaluation coverage, provider abstraction coverage, prompt centralization rate, and more | 52 |
| Vertical Value Drivers | AI-specific signal-to-pain mappings connecting operational signals to financially meaningful outcomes | 36 |
| Vertical Formulas | Inference cost avoidance via caching, hallucination-induced support cost, RAG quality revenue impact, AI compliance revenue enablement, agent automation ROI, vector DB cost at scale, prompt optimization savings, multi-model resilience value, latency abandonment cost, bias audit cost avoidance, training data licensing risk-adjusted cost | 15 |
| Vertical Personas | AI Product Lead, ML Engineer/MLOps Lead, Responsible AI Officer, Prompt Engineer/AI Interaction Designer, AI Ops Manager, Data/AI Architect | 6 |
| Vertical Signal Rules | LLM bill spikes, hallucination complaint surges, AI MAU decline, enterprise governance stalls, red-team jailbreaks, vector DB latency degradation, eval pipeline absences, provider lock-in risk, agent fallback surges, ML engineer attrition, prompt chaos, PII in logs, model sprawl, embedding obsolescence, latency complaints, bias testing absence, copyright gaps, support CSAT gaps, streaming UX absence, governance documentation request surges | 20 |

### Overridden Components
1. **Cloud Cost as % of Revenue benchmark**: Master benchmark of <20% overridden to 20-40% for AI-native (inference/GPU COGS materially higher).
2. **Gross Margin benchmark**: Master benchmark of >70% overridden to 55-75% for AI-native depending on model hosting strategy.
3. **Persona Set**: 6 AI-native personas added; base personas remain valid but insufficient for AI-native buying committees.

### When to Use Master vs. Subpack
| Scenario | Skill to Use |
|----------|-------------|
| Prospect is a general SaaS company with no AI/ML core | `saas-master-v1` only |
| Prospect has bolt-on AI features (e.g., basic summarization) | `saas-master-v1` + light AI probing |
| Prospect's core value proposition IS AI/ML | `saas-master-v1` + this subpack |
| Prospect builds AI copilots, agents, RAG, or foundation model products | This subpack as primary; master for base financials |

---

## 5. Structured Output Template

When enriching a prospect/account with Signals Analysis using this skill, produce JSON in the following structure:

```json
{
  "skillId": "ai-native-saas-v1",
  "parentMasterId": "saas-master-v1",
  "analysisTimestamp": "2026-04-25T00:00:00Z",
  "confidence": {
    "overall": "HIGH",
    "score": 0.87,
    "dataQuality": "production"
  },
  "detectedSignals": [
    {
      "signalRuleId": "SR-AI-002",
      "signalName": "Hallucination Complaint Spike",
      "rawValue": 45,
      "interpretedPainId": "P-AI-001",
      "painName": "LLM Hallucination in Customer-Facing Outputs",
      "confidence": 0.90,
      "severity": "CRITICAL",
      "recommendedActions": [
        "Run automated eval benchmark on production sample",
        "Check for recent model or prompt changes",
        "Segment complaints by customer cohort and feature",
        "Activate human-in-the-loop review for affected outputs"
      ],
      "affectedPersonaIds": ["PER-AI-001", "PER-AI-002", "Responsible AI Officer"],
      "linkedKPIs": ["K-AI-001", "K-AI-003"],
      "estimatedAnnualImpact": {
        "revenueUplift": null,
        "costSavings": null,
        "riskExposure": 180000
      }
    }
  ],
  "painProfile": {
    "topPains": [
      { "painId": "P-AI-001", "name": "LLM Hallucination in Customer-Facing Outputs", "prevalence": "HIGH", "confidence": "HIGH" },
      { "painId": "P-AI-003", "name": "Inference Cost Escalation and Token Budget Overruns", "prevalence": "HIGH", "confidence": "HIGH" },
      { "painId": "P-AI-002", "name": "AI Model Governance and Audit Trail Gaps", "prevalence": "HIGH", "confidence": "HIGH" }
    ],
    "painCoverage": "3 of 18 pains detected"
  },
  "personaMap": {
    "primaryPersonas": ["PER-AI-001", "PER-AI-005", "CFO"],
    "secondaryPersonas": ["PER-AI-002", "PER-AI-003"],
    "inheritedPersonas": ["CFO", "CTO", "CRO"]
  },
  "kpiSnapshot": [
    { "kpiId": "K-AI-001", "name": "LLM Hallucination Rate", "currentValue": "4.2%", "benchmark": "At Risk: >8%", "target": "Good: 1%–3%" },
    { "kpiId": "K-AI-007", "name": "Inference Cost per 1K Tokens", "currentValue": "$0.12", "benchmark": "Standard: $0.05–$0.15", "target": "Optimized: <$0.05" }
  ],
  "valueHypotheses": [
    {
      "valueDriverId": "VD-AI-001",
      "category": "Risk Reduction",
      "hypothesis": "Reducing hallucination rate from 4.2% to <2% will cut support escalations and liability exposure",
      "formulaId": "VF-AI-002",
      "estimatedAnnualValue": 180000,
      "confidence": "MEDIUM"
    },
    {
      "valueDriverId": "VD-AI-005",
      "category": "Cost Savings",
      "hypothesis": "Implementing caching + model routing will reduce inference cost from 28% to <15% of COGS",
      "formulaId": "VF-AI-001",
      "estimatedAnnualValue": 63000,
      "confidence": "HIGH"
    }
  ],
  "buyingTriggers": [
    { "triggerId": "BT-AI-003", "name": "Viral Hallucination Incident", "matched": false },
    { "triggerId": "BT-AI-004", "name": "Inference Bill Overrun", "matched": true }
  ],
  "regulatoryExposure": [
    { "regulationId": "RF-AI-001", "name": "EU AI Act — High-Risk System Requirements", "applicable": true, "deadline": "2026-08-02" },
    { "regulationId": "RF-AI-003", "name": "NIST AI Risk Management Framework", "applicable": true, "deadline": "ongoing" }
  ],
  "competitiveContext": {
    "techSystemsPresent": ["TS-AI-001", "TS-AI-002", "TS-AI-003"],
    "techSystemsMissing": ["TS-AI-004", "TS-AI-005", "TS-AI-009"],
    "providerLockInRisk": "HIGH"
  }
}
```

---

## 6. Governance Metadata

| Field | Value |
|-------|-------|
| **Confidence Level** | HIGH |
| **Source Coverage** | 25+ evidence sources including Gartner 2025, NIST AI RMF 2024, EU AI Act 2024, OWASP LLM Top 10 2025, LangChain 2025 Surveys, Pinecone/Weaviate Benchmarks 2025, a16z/Bessemer/Menlo Ventures 2025 Reports, Arthur AI/Vectara Benchmarks |
| **Customer-Facing Approval Status** | APPROVED — all benchmarks dated, sourced, and confidence-graded. Value formulas include explicit confidence rules and required input validation. |
| **Review Owner** | ai-native-saas-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-swarm-saas-ai-native |
| **Next Review Date** | 2026-07-25 |
| **Version History** | 1.0.0 — Initial release |

---

## 7. Quick Reference

### Top 5 Pains

| Rank | Pain ID | Pain Name | Prevalence | Key Symptom |
|------|---------|-----------|------------|-------------|
| 1 | P-AI-001 | LLM Hallucination in Customer-Facing Outputs | HIGH | Customer complaints about incorrect AI-generated answers >5% of AI interactions |
| 2 | P-AI-003 | Inference Cost Escalation and Token Budget Overruns | HIGH | LLM API bill >20% of total COGS and growing faster than revenue |
| 3 | P-AI-002 | AI Model Governance and Audit Trail Gaps | HIGH | Cannot answer "what model version was used for this output?" in <5 minutes |
| 4 | P-AI-004 | Prompt Injection and Adversarial AI Security Vulnerabilities | HIGH | Red-team exercises successfully jailbreak production AI >10% of attempts |
| 5 | P-AI-008 | AI Feature Adoption Plateau After Initial Hype | HIGH | AI feature MAU declining month-over-month after launch |

### Top 5 KPIs

| Rank | KPI ID | KPI Name | Benchmark Range | Frequency |
|------|--------|----------|-----------------|-----------|
| 1 | K-AI-001 | LLM Hallucination Rate | Excellent: <1%; Good: 1%–3%; At Risk: >8% | Weekly |
| 2 | K-AI-009 | Inference Cost as % of COGS | Efficient: <15%; Standard: 15%–30%; High: 30%–50% | Monthly |
| 3 | K-AI-014 | RAG Answer Accuracy | Excellent: >85%; Good: 70%–85%; At Risk: <70% | Weekly |
| 4 | K-AI-016 | Agent Task Completion Rate | Excellent: >75%; Good: 60%–75%; At Risk: <60% | Weekly |
| 5 | K-AI-010 | Prompt Injection Block Rate | Secure: >95%; Standard: 85%–95%; Vulnerable: <85% | Weekly |

### Top 3 Personas

| Rank | Persona ID | Persona Name | Decision Influence | Primary Pain Focus |
|------|------------|--------------|-------------------|-------------------|
| 1 | PER-AI-001 | AI Product Lead | Technical | Output quality, adoption, latency, feature-market fit |
| 2 | PER-AI-005 | AI Ops Manager | Technical | Inference cost, latency, uptime, provider resilience |
| 3 | PER-AI-003 | Responsible AI Officer | Economic | Governance, compliance, bias, explainability, legal risk |

### Key Value Formulas

| Formula ID | Name | Formula | Output Unit |
|------------|------|---------|-------------|
| VF-AI-001 | Annual LLM Inference Cost Avoidance via Caching | `(Monthly Token Volume × Cache Hit Rate × (Uncached Cost – Cached Cost) / 1000) × 12` | USD per year |
| VF-AI-002 | Hallucination-Induced Support Cost | `(AI Interactions/Month × Hallucination Rate × Escalation Rate × Cost/Ticket) × 12` | USD per year |
| VF-AI-003 | RAG Quality Improvement Revenue Impact | `(Current AI MAU × (Target Accuracy – Current Accuracy) × Conversion Lift per Point × ARPU) × 12` | USD per year |
| VF-AI-007 | AI Agent Task Automation ROI | `(Tasks/Month × (Human Time – AI Time) × Hourly Labor Cost × 12) – (AI Infrastructure Cost × 12)` | USD per year |
| VF-AI-011 | AI Compliance Readiness Enterprise Revenue Enablement | `(Deals Stalled/Quarter × Average Enterprise ACV × Governance Enablement Rate) × 4` | USD per year |

---

## Appendix: File Manifest

| File | Purpose |
|------|---------|
| `value-pack.json` | Machine-readable pack definition (pains, KPIs, value drivers, formulas, benchmarks, signal rules, personas, buying triggers, tech systems, regulatory factors, discovery questions, objections, worked examples) |
| `value-pack.md` | Human-readable pack documentation with full component details |
| `signals-examples.ts` | TypeScript signal rule implementations, formula functions, persona matching rules, buying trigger detection, and confidence scoring utilities |
| `SKILL.md` | This file — OpenClaw skill manifest for orchestrator integration |
