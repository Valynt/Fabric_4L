# Go-to-Market SaaS Subpack (S2.5)

## Skill Identity Block

| Field | Value |
|-------|-------|
| `skill_name` | Go-to-Market SaaS Subpack |
| `description` | Vertical-specialized value intelligence for Go-to-Market SaaS functions including sales productivity, pipeline generation, forecast accuracy, ABM, lead conversion, customer onboarding, customer success, renewals/expansion, churn reduction, pricing/packaging optimization, and RevOps. Designed for sellers targeting CROs, VPs of Sales, RevOps leaders, CSM directors, and pricing strategists. |
| `version` | 1.0.0 |
| `domain` | SaaS |
| `pack_type` | subpack |
| `parent_master` | saas-master-v1 |

---

## Triggers

Auto-load this skill when queries match any of these natural language patterns:

1. "SaaS churn reduction" — prospect showing retention or CS tooling interest
2. "sales forecast accuracy" — revenue operations or pipeline intelligence conversation
3. "customer success expansion" — upsell, cross-sell, NRR, or CS platform opportunity
4. "pricing optimization" — deal desk, discount governance, or packaging strategy discussion
5. "ABM account engagement signals" — account-based marketing or intent data evaluation
6. "RevOps reporting automation" — revenue operations, board reporting, or CRM data quality pain
7. "sales rep quota attainment" — sales productivity, ramp time, or enablement tooling need
8. "lead routing speed" — speed-to-lead, MQL-to-SQL conversion, or routing SLA conversation
9. "SDR pipeline generation" — outbound effectiveness, prospecting tools, or sales development
10. "enterprise onboarding time-to-value" — customer onboarding, implementation, or activation
11. "multi-threading deal coaching" — sales methodology, stakeholder mapping, or win rate
12. "commission calculation disputes" — compensation operations, SPIF tracking, or rep trust

---

## Reasoning Flow

### Step 1: Load Parent Master First

Before applying this subpack, ensure `saas-master-v1` (SaaS Master) is loaded. The master provides:

- Value Driver Framework (VD001-VD050)
- Base Persona Archetypes (CFO, CRO, CTO, CEO, CIO, CISO, COO, CHRO)
- Evidence Source Types and Formula Templates
- Signal Source Taxonomy (financial, operational, behavioral)
- Benchmark Methodology (percentile-based, segment-adjusted)

**Inheritance Guidance:** This subpack does NOT duplicate master components. Reference master definitions for base personas and high-level SaaS value drivers. Only use subpack components when the conversation centers on GTM-specific functions (sales, RevOps, CS, pricing, ABM).

### Step 2: Identify Relevant Signals

For the prospect/account, scan for these GTM-specific signal categories:

| Category | Signal Sources | Examples |
|----------|---------------|----------|
| **Forecast & RevOps** | CRM data, rep forecasts, board reporting cadence | Forecast variance >30%, reporting cycle >5 days |
| **Sales Productivity** | Quota attainment, ramp time, rep turnover, content usage | Attainment <50%, ramp >9 months, content adoption <20% |
| **Pipeline Generation** | SDR metrics, outreach response, lead routing time | SDR pipeline declining >10% QoQ, lead routing >24h |
| **Customer Success** | CSM coverage, health scores, QBR completion, churn timing | CSM ARR >$5M, health scores stale, churn surprises <30 days |
| **Expansion & Pricing** | Cross-sell rate, discount rate, deal desk presence | Cross-sell <10%, discount rate >20%, no deal desk |
| **ABM & Intent** | Account engagement, pipeline contribution, intent coverage | ABM engagement <15%, no intent data in CRM |

### Step 3: Interpret Signals Using Subpack Rules

For each detected raw signal, apply the corresponding Signal Interpretation Rule (SR_GTM_001 through SR_GTM_018). Each rule provides:

- **Raw Signal Pattern** — the observable symptom
- **Interpreted Meaning** — what the symptom reveals about the underlying process
- **Confidence Score** — base confidence (0.75-0.88) for this signal alone
- **Required Confirmation Signals** — 2-3 additional signals needed to elevate confidence
- **Linked Pains & KPIs** — specific subpack pain IDs and KPIs to reference

**Confidence Scoring Guidance:**
- **0.75-0.79** (MEDIUM): Initial signal detected; seek 1-2 confirmation signals before presenting
- **0.80-0.85** (HIGH): Strong signal with clear pattern; present if at least 1 confirmation signal present
- **0.86-0.88** (VERY HIGH): Near-certain pain; can present directly with supporting KPI data

### Step 4: Map to Pains, Personas, KPIs, and Value Hypotheses

Once a signal triad (primary signal + 1-2 confirmations) is established:

1. **Link to Pain** — use the signal rule's `linkedPains` to identify the relevant subpack pain (S2P001-S2P018)
2. **Identify Affected Personas** — check the pain's `affectedPersonas` array; prioritize the persona whose conversation you're in
3. **Select KPIs** — use the pain's `linkedKPIs` to identify the metrics to reference in discovery
4. **Formulate Value Hypothesis** — select the matching Value Formula (VF_GTM_001-VF_GTM_012) and build a quantified value estimate using prospect-provided or benchmark data

### Step 5: Validate with Discovery Questions

Use the 18 Discovery Questions (DQ_GTM_001-DQ_GTM_018) to validate signals in live conversation. Each question:
- Targets a specific persona
- Links to pains and KPIs
- Has an expected insight that confirms or denies the signal

### Step 6: Apply Worked Examples for Proof Points

Reference the 3 worked examples (WE_GTM_001-WE_GTM_003) as social proof and calculation templates:
- **WE_GTM_001:** RevOps Forecast Accuracy Improvement ($352K annual value)
- **WE_GTM_002:** CSM Coverage Optimization and Churn Reduction ($2.96M value)
- **WE_GTM_003:** Discount Governance and ASP Recovery ($1.96M net first-year value, 13x ROI)

---

## Inheritance Map

### Master Skill to Load First

**`saas-master-v1`** — the SaaS Master ValuePack must be loaded before this subpack.

### What the Master Provides (Inherited)

| Component | Master ID | How Referenced |
|-----------|-----------|---------------|
| Value Driver Framework | VD001-VD050 | Read-only reference for base value categories |
| Base Personas | CFO, CRO, CTO, CEO, CIO, CISO, COO, CHRO | Extended with 6 GTM-specific personas |
| Evidence Source Types | Industry benchmarks, vendor reports, survey data | Used for credibility in GTM conversations |
| Formula Templates | Ratio, rate, efficiency, coverage formulas | Applied in 12 GTM-specific value formulas |
| Signal Source Taxonomy | Financial, operational, behavioral signals | GTM signals are a vertical extension |
| Benchmark Methodology | Percentile-based, segment-adjusted | Applied to 18 GTM-specific benchmarks |
| Governance Framework | Confidence levels, review cycles, approval gates | Inherited approval status |

### What This Subpack Adds

| Component | Count | IDs |
|-----------|-------|-----|
| **Pains** | 18 | S2P001-S2P018 |
| **KPIs** | 22 | K_GTM_001-K_GTM_052 |
| **Signal Rules** | 18 | SR_GTM_001-SR_GTM_018 |
| **Personas** | 6 | PER_GTM_001-PER_GTM_006 |
| **Value Formulas** | 12 | VF_GTM_001-VF_GTM_012 |
| **Benchmarks** | 18 | B_GTM_001-B_GTM_018 |
| **Discovery Questions** | 18 | DQ_GTM_001-DQ_GTM_018 |
| **Objection Patterns** | 9 | OBJ_GTM_001-OBJ_GTM_009 |
| **Worked Examples** | 3 | WE_GTM_001-WE_GTM_003 |
| **Buying Triggers** | 14 | BT_GTM_001-BT_GTM_014 |

### When to Use Master vs. Subpack

| Scenario | Use |
|----------|-----|
| General SaaS company, no specific GTM focus | Master only |
| GTM function mentioned but pain is broad (e.g., "our revenue is flat") | Master + light subpack overlay |
| Specific GTM pain identified (e.g., "forecast is always wrong", "CSMs are overloaded") | Subpack primary, master for persona context |
| Deep RevOps, sales, CS, pricing, or ABM conversation | Subpack fully activated |

---

## Structured Output Template

### Expected JSON Format for Signals Analysis Enrichment

```json
{
  "analysisMetadata": {
    "packId": "go-to-market-saas-v1",
    "packVersion": "1.0.0",
    "masterPackId": "saas-master-v1",
    "analysisTimestamp": "2026-04-25T00:00:00Z",
    "confidenceLevel": "HIGH"
  },
  "detectedSignals": [
    {
      "signalId": "SR_GTM_001",
      "signalName": "Forecast Variance >30% for 2 Consecutive Quarters",
      "confidenceScore": 0.85,
      "confirmationSignalsPresent": 2,
      "rawEvidence": [
        "Forecast variance 35% in Q1 and Q2 2025",
        "Rep self-reported variance 32%",
        "No engagement scoring in CRM"
      ],
      "linkedPains": ["S2P001"],
      "linkedKPIs": ["K_GTM_001", "K_GTM_002", "K_GTM_003"],
      "suggestedDiscoveryQuestions": ["DQ_GTM_001", "DQ_GTM_002"],
      "primaryAffectedPersonas": ["CFO", "CRO", "VP RevOps"],
      "valueFormulaMatch": "VF_GTM_001"
    }
  ],
  "prioritizedPains": [
    {
      "painId": "S2P001",
      "painName": "Forecast Accuracy Below 60%",
      "prevalence": "HIGH",
      "confidence": "HIGH",
      "affectedPersonas": ["CFO", "CRO", "VP RevOps", "VP Sales", "CEO"],
      "linkedKPIs": ["K_GTM_001", "K_GTM_002", "K_GTM_003"],
      "linkedValueDrivers": ["VD021", "VD022"]
    }
  ],
  "personaMap": [
    {
      "personaId": "PER_GTM_001",
      "personaName": "RevOps Manager",
      "relevanceScore": 0.92,
      "engagementPriority": 1
    }
  ],
  "valueHypotheses": [
    {
      "formulaId": "VF_GTM_001",
      "formulaName": "Forecast Accuracy Improvement Value",
      "estimatedAnnualValue": "$320,000",
      "valueCategory": "Working Capital",
      "confidence": "HIGH",
      "requiredInputs": [
        "Prior forecast variance %",
        "New forecast variance %",
        "Quarterly quota",
        "Cost of capital (WACC)"
      ],
      "calculationExample": "(35% - 15%) x $5M x 4 x 8% = $320K annual value"
    }
  ],
  "recommendedNextSteps": [
    "Schedule discovery call with RevOps Manager using DQ_GTM_001",
    "Validate forecast variance with CFO using K_GTM_001",
    "Prepare WE_GTM_001 proof point for board credibility angle"
  ],
  "governance": {
    "sourceCoverage": "Mixed (public vendor reports, industry research, proprietary benchmarks)",
    "customerFacingApproved": true,
    "reviewOwner": "gtm-saas-subpack-creator",
    "lastUpdated": "2026-04-25"
  }
}
```

---

## Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | HIGH |
| **Source Coverage** | Mixed (public vendor reports, industry research, proprietary benchmarks) |
| **Customer-Facing Approval Status** | Yes — approved for customer-facing output |
| **Review Owner** | gtm-saas-subpack-creator |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-swarm-saas-gtm |
| **Parent Master Swarm ID** | kimi-k2.6-swarm-saas |

---

## Quick Reference

### Top 5 Pains (by Prevalence & Impact)

| # | Pain ID | Name | Prevalence | Key Symptom |
|---|---------|------|------------|-------------|
| 1 | S2P001 | Forecast Accuracy Below 60% | HIGH | Forecast variance >40% for 2+ quarters |
| 2 | S2P002 | CSM Book-of-Business Exceeds $5M per Rep | HIGH | CSM ARR coverage >$5M, QBRs <50% |
| 3 | S2P004 | Sales Rep Quota Attainment Below 50% | HIGH | <50% reps hitting quota, ramp >9 months |
| 4 | S2P005 | SDR Pipeline Generation Declining QoQ | HIGH | SDR pipeline declining >10% QoQ |
| 5 | S2P009 | Churn Surprises in Final Weeks of Quarter | HIGH | >30% churn surprises <30 days before renewal |

### Top 5 KPIs (by Diagnostic Power)

| # | KPI ID | Name | Benchmark | At-Risk Threshold |
|---|--------|------|-----------|-------------------|
| 1 | K_GTM_001 | Forecast Variance by Quarter | Excellent: <10% | >35% |
| 2 | K_GTM_010 | Quota Attainment Rate | Top quartile: >65% | <40% |
| 3 | K_GTM_004 | CSM ARR Coverage Ratio | Enterprise: $3M-$5M | >$5M |
| 4 | K_GTM_007 | ABM Target Account Engagement Rate | High performing: >25% | <10% |
| 5 | K_GTM_026 | Average Discount Rate | Median SaaS: ~18% | >20% |

### Top 3 Personas (by Decision Influence)

| # | Persona ID | Name | Decision Influence | Primary Pains |
|---|-----------|------|-------------------|---------------|
| 1 | PER_GTM_001 | RevOps Manager | Technical | S2P001, S2P011, S2P012, S2P017 |
| 2 | PER_GTM_003 | CSM Director | Technical | S2P002, S2P006, S2P007, S2P009 |
| 3 | PER_GTM_005 | Pricing Strategist | Economic | S2P010, S2P008, S2P014 |

### Key Value Formulas

| Formula ID | Name | Quick Calc | Typical Output |
|-----------|------|-----------|----------------|
| VF_GTM_001 | Forecast Accuracy Improvement | (Variance Reduction) x Quota x 4 x Cost of Capital | $200K-$500K annual |
| VF_GTM_002 | CSM Coverage Optimization | (Excess ARR / Optimal ARR) x Excess CSMs x CSM Cost | $400K-$600K annual |
| VF_GTM_004 | Quota Attainment Improvement | (Attainment Gain) x Reps x Quota | $3M-$8M ARR uplift |
| VF_GTM_008 | Discount Governance ASP Recovery | (Discount Reduction) x Deal Size x Volume x Margin | $1M-$2M margin recovery |
| VF_GTM_012 | Multi-Threading Deal Protection | (Loss Rate Delta) x Single-Threaded Pipeline x Factor | $2M-$5M protected pipeline |

---

*This subpack extends the SaaS Master ValuePack (saas-master-v1) with vertical-specialized components for Go-to-Market SaaS. All inherited components are read-only references from the master pack. Do not duplicate master content in customer-facing outputs. Refer to value-pack.json for structured data and signals-examples.ts for TypeScript type definitions.*
