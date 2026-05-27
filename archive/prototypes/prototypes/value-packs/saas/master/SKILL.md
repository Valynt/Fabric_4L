# SaaS Master ValuePack — SKILL.md

## 1. Skill Identity Block

```yaml
skill_name: SaaS Master (M2)
description: |
  Comprehensive value-pack for analyzing SaaS companies across all segments 
  (Horizontal, Vertical, AI-Native, Infrastructure/Platform, Go-to-Market Specialties). 
  Covers 25 core pains, 80 KPIs, 50 value drivers, 25 value formulas, and 30 signal 
  interpretation rules with 35 industry benchmarks. Use this pack to diagnose SaaS 
  unit economics, growth efficiency, retention, infrastructure scaling, and go-to-market 
  maturity for any subscription software business.
version: 1.0.0
domain: SaaS / Software
pack_type: master
parent_master: null
```

---

## 2. Triggers Section

Auto-load this skill when user queries match any of the following patterns:

| # | Trigger Query |
|---|---------------|
| 1 | "analyze a SaaS company" |
| 2 | "SaaS churn signals" |
| 3 | "cloud infrastructure cost optimization" |
| 4 | "SaaS unit economics" / "LTV:CAC" / "CAC payback" |
| 5 | "Net Revenue Retention analysis" / "NRR below 100%" |
| 6 | "SaaS sales cycle lengthening" / "win rate decline" |
| 7 | "product-led growth pivot" / "PLG-to-enterprise conversion" |
| 8 | "AI-native SaaS valuation" / "AI feature adoption" |
| 9 | "SaaS compliance SOC 2" / "security review bottleneck" |
| 10 | "customer success proactive engagement" / "CS health scoring" |
| 11 | "SaaS data pipeline reliability" / "data quality issues" |
| 12 | "SaaS sprawl shadow IT" / "unused software licenses" |

---

## 3. Reasoning Flow

### Step 1: Segment Identification
Determine which segment(s) the target company belongs to:
- **Horizontal SaaS** — broad cross-industry applicability (CRM, HRIS, marketing)
- **Vertical SaaS** — industry-specific (Toast, Shopify, Procore)
- **AI-Native SaaS** — AI/ML as core value proposition
- **Infrastructure & Platform SaaS** — developer tools, data platforms, APIs
- **Go-to-Market SaaS Specialties** — sales/marketing enablement tools

### Step 2: Signal Ingestion & Classification
Collect raw signals from the following evidence sources and map to signal rules:

| Evidence Source | Lag | Reliability | Best For |
|-------------------|-----|-------------|----------|
| SEC 10-K / 10-Q | 45-90 days | HIGH | Financial health, margin trends |
| Earnings Call Transcripts | Same day | HIGH | Strategic priorities, metric disclosure |
| Job Postings (LinkedIn, career pages) | Real-time | MEDIUM | Growth vectors, team expansion |
| Industry Benchmark Reports | Annual/Quarterly | HIGH | Peer comparison, benchmark targets |
| Vendor Security/Trust Pages | Annual update | MEDIUM | Compliance posture, audit status |
| Product Analytics (Mixpanel, Amplitude) | Real-time | HIGH | Adoption, activation, engagement |
| CRM Data (Salesforce, HubSpot) | Real-time | HIGH | Pipeline, forecast, cycle length |
| Glassdoor / Blind Reviews | Real-time | MEDIUM | Culture, technical debt signals |
| G2 / Capterra / TrustRadius | Real-time | MEDIUM | Customer satisfaction, competitive gaps |
| Conference Presentations / Blog Posts | Event-driven | MEDIUM | Technical priorities, scaling challenges |

Apply the 30 Signal Interpretation Rules (SR001–SR030) to convert raw signals into interpreted meanings with confidence scores (0.65–0.90).

### Step 3: Pain Identification
Match confirmed signals to the 25 Core Pains (P001–P025). Prioritize by:
- **Prevalence** (HIGH > MEDIUM > LOW)
- **Confidence** (HIGH > MEDIUM)
- **Affected segments matching target company**

Top pain clusters to evaluate first:
1. **Growth & Acquisition** — P001 (CAC Efficiency), P003 (Sales Cycle), P015 (Engineering Talent)
2. **Retention & Expansion** — P002 (NRR Decline), P005 (Churn Volatility), P010 (Onboarding Failure)
3. **Infrastructure & Cost** — P007 (Cloud Cost Growth), P014 (AI Inference Cost), P006 (Engineering Velocity)
4. **Compliance & Risk** — P009 (Compliance Burden), P016 (Observability Gaps)
5. **Data & Operations** — P017 (RevOps Data Silos), P024 (Data Pipeline Issues), P025 (SaaS Sprawl)

### Step 4: KPI Baseline & Benchmarking
For each identified pain, pull the linked KPIs and compare against segment-specific benchmarks:

| KPI Category | Key Metrics | Benchmark Source |
|--------------|-------------|------------------|
| Unit Economics | CAC, LTV:CAC, CAC Payback, Cost/Net New ARR | High Alpha 2025, Phoenix Strategy Group |
| Retention | NRR, GRR, Logo Churn, Expansion Rate | SaaS Capital, T2D3, Proven SaaS |
| Sales Efficiency | Cycle Length, Win Rate, Pipeline Velocity, No-Decision Rate | Optifai 2025, Gradient Works, Ebsta |
| Engineering Velocity | Deployment Frequency, Lead Time, MTTR, Change Failure Rate | DORA 2024 |
| Cloud Efficiency | Cloud Cost % Revenue, Utilization Rate, Cost/Customer | FinOps Foundation 2024 |
| Data Quality | Integration Coverage, Data Quality Score, System of Truth Rate | MuleSoft, Monte Carlo |
| Customer Success | TTFV, Onboarding Completion, Activation Rate, CSAT | Gainsight, ChurnZero |
| Financial Health | Gross Margin, Services % Revenue, Revenue/Employee | SaaS Capital, Battery Ventures |

### Step 5: Value Driver Mapping
Map confirmed pains and KPI deviations to the 50 Value Drivers (VD001–VD050), categorized as:
- **Cost Savings** — Reduce waste, optimize spend, automate manual work
- **Revenue Uplift** — Increase retention, expansion, win rates, pricing power
- **Risk Reduction** — Improve compliance, security, reliability, data trust
- **Working Capital** — Accelerate cycles, improve forecast accuracy, reduce DSO

For each value driver, identify:
- **Affected Personas** — Who feels the pain and controls budget
- **Required Evidence** — What proof points are needed to validate the hypothesis
- **Confidence** — HIGH (direct data), MEDIUM (benchmark inference), LOW (market assumption)

### Step 6: Value Quantification
Apply the 25 Value Formulas (VF001–VF025) to convert pain severity into dollar-impact estimates. Select formulas based on pain category:

| Pain Category | Primary Formulas |
|---------------|------------------|
| CAC / Growth Efficiency | VF001 (ARR Growth Efficiency), VF018 (Lead Quality) |
| Retention / NRR | VF002 (NRR Improvement), VF005 (Churn Reduction), VF010 (TTFV Acceleration) |
| Sales Velocity | VF003 (Sales Cycle Reduction), VF004 (Win Rate Improvement), VF016 (Multi-Threading) |
| Cloud / Infrastructure | VF006 (Cloud Cost Optimization), VF007 (Engineering Productivity), VF017 (Downtime Avoidance) |
| Compliance / Security | VF011 (Compliance Automation) |
| Data / Integration | VF012 (Data Integration Cost Avoidance), VF024 (Pipeline Reliability) |
| Pricing | VF019 (Pricing Optimization), VF014 (Gross Margin Improvement) |
| AI | VF020 (AI Feature Monetization) |
| Support / CS | VF009 (Support Cost Reduction), VF013 (Expansion Revenue Uplift) |
| RevOps | VF022 (RevOps Automation), VF008 (Forecast Accuracy) |

### Step 7: Confidence Scoring Guidance
Score the overall analysis confidence using this rubric:

| Score | Criteria |
|-------|----------|
| 0.90–1.00 | Direct financial data (10-K, CRM, product analytics) + confirmed signals + benchmark match |
| 0.75–0.89 | Partial direct data + strong signal correlation + industry benchmarks |
| 0.60–0.74 | Signal-based inference + benchmark proxies + no direct financials |
| 0.40–0.59 | Weak signal correlation + speculative assumptions |
| <0.40 | Insufficient data — flag for additional research |

Weight by evidence reliability:
- HIGH reliability sources (10-K, earnings, CRM, product analytics): full weight
- MEDIUM reliability sources (job postings, Glassdoor, peer reviews): 0.7× weight
- Qualitative signals (conferences, blogs): 0.5× weight

---

## 4. Structured Output Template

```json
{
  "skill_loaded": "saas-master-m2",
  "analysis_timestamp": "2025-01-15T10:00:00Z",
  "target_company": {
    "name": "Example SaaS Inc",
    "segment": "Horizontal SaaS",
    "arr_range": "$10M-$50M",
    "stage": "Growth"
  },
  "signals_detected": [
    {
      "signal_id": "SR001",
      "signal_name": "Job Posting Surge in Sales",
      "raw_evidence": "8 sales roles posted in 30 days",
      "confidence": 0.75,
      "linked_pains": ["P001", "P003", "P015"],
      "confirmation_status": "PARTIALLY_CONFIRMED"
    }
  ],
  "pains_identified": [
    {
      "pain_id": "P001",
      "pain_name": "Customer Acquisition Cost (CAC) Inflation",
      "severity": "HIGH",
      "confidence": "HIGH",
      "symptoms_observed": ["CAC >$25K for mid-market", "LTV:CAC <3:1"],
      "linked_kpis": ["K001", "K002", "K003", "K004"],
      "linked_value_drivers": ["VD001", "VD002"],
      "affected_personas": ["CFO", "CRO", "VP Marketing"]
    }
  ],
  "kpis_analyzed": [
    {
      "kpi_id": "K001",
      "kpi_name": "Customer Acquisition Cost (CAC)",
      "current_value": "$28,000",
      "benchmark_range": "$10,000–$25,000",
      "status": "ABOVE_BENCHMARK",
      "trend": "WORSENING",
      "linked_value_drivers": ["VD001", "VD002"]
    }
  ],
  "value_drivers_activated": [
    {
      "vd_id": "VD001",
      "pattern": "Rising CAC with flat or declining LTV",
      "category": "Cost Savings",
      "interpreted_pain": "Unit economics deterioration threatening sustainable growth",
      "affected_personas": ["CFO", "CRO", "VP Marketing"],
      "required_evidence": ["CAC trend analysis", "Channel-level CAC breakdown", "LTV cohort analysis"],
      "confidence": "HIGH"
    }
  ],
  "value_quantified": [
    {
      "formula_id": "VF001",
      "formula_name": "ARR Growth Efficiency Value",
      "inputs": {
        "delta_arr": 5000000,
        "current_cac_payback_months": 18,
        "target_cac_payback_months": 12,
        "gross_margin_pct": 75
      },
      "output_usd": 11250000,
      "output_description": "3-year NPV",
      "confidence": "MEDIUM"
    }
  ],
  "personas_engaged": [
    {
      "persona_id": "PER001",
      "persona": "Chief Financial Officer (CFO)",
      "relevance": "economic",
      "primary_pains": ["P001", "P007", "P011"],
      "engagement_priority": 1
    }
  ],
  "buying_triggers_present": [
    {
      "trigger_id": "BT001",
      "trigger_name": "Series B/C Funding Close",
      "urgency": "HIGH",
      "timing": "0-6 months post-close",
      "linked_pains": ["P001", "P003", "P007"]
    }
  ],
  "recommended_next_steps": [
    "Validate CAC trend with channel-level breakdown",
    "Confirm LTV cohort analysis by customer segment",
    "Engage CFO with unit economics benchmark comparison",
    "Map cloud cost growth vs. revenue growth trend"
  ],
  "overall_confidence": 0.82,
  "analysis_completeness": "PARTIAL — 3 of 6 signal categories investigated"
}
```

---

## 5. Governance Metadata

| Field | Value |
|-------|-------|
| **Confidence Level** | HIGH (35 industry benchmarks, 30 signal rules, 25 validated formulas) |
| **Source Coverage** | 10 evidence source types; 14+ industry research providers (SaaS Capital, High Alpha, Bessemer, DORA, Optifai, Battery Ventures, Coffee.ai, etc.) |
| **Customer-Facing Approval** | APPROVED — all benchmarks sourced from published reports; formulas use standard SaaS math |
| **Review Owner** | ValuePack Architecture Team |
| **Last Updated** | 2025-04-25 |
| **Version** | 1.0.0 |
| **Pack Type** | MASTER |
| **Subpacks Available** | None (this is the root master) |

---

## 6. Quick Reference

### Top 5 Pains (by prevalence × impact)

| # | Pain | ID | Prevalence | Primary Segment |
|---|------|-----|------------|-----------------|
| 1 | Customer Acquisition Cost (CAC) Inflation | P001 | HIGH | All |
| 2 | Net Revenue Retention (NRR) Decline | P002 | HIGH | All |
| 3 | Sales Cycle Lengthening & Pipeline Stagnation | P003 | HIGH | All |
| 4 | Competitive Differentiation Erosion | P004 | HIGH | All |
| 5 | Logo Churn Volatility | P005 | HIGH | SMB/Mid-Market |

### Top 5 KPIs (universal diagnostic power)

| # | KPI | ID | Benchmark | Formula |
|---|-----|-----|-----------|---------|
| 1 | Net Revenue Retention (NRR) | K005 | >110% great, >120% excellent | `(Start ARR + Expansion – Contraction – Churn) / Start ARR × 100` |
| 2 | LTV:CAC Ratio | K002 | Healthy 3:1–5:1; Elite >5:1 | `LTV / CAC` |
| 3 | CAC Payback Period | K003 | Best <12mo; Acceptable 12–18mo | `CAC / (ARPU × Gross Margin)` |
| 4 | Gross Margin | K045 | SaaS standard >70% | `(Revenue – COGS) / Revenue × 100` |
| 5 | Pipeline Velocity | K010 | Track trend over absolute | `(Opps × Deal Value × Win Rate) / Cycle Length` |

### Top 3 Personas (by decision influence frequency)

| # | Persona | ID | Influence | Primary Value Categories |
|---|---------|-----|-----------|--------------------------|
| 1 | Chief Revenue Officer (CRO) | PER002 | economic | Revenue Uplift, Working Capital |
| 2 | Chief Financial Officer (CFO) | PER001 | economic | Cost Savings, Working Capital |
| 3 | Chief Technology Officer (CTO) | PER003 | technical | Cost Savings, Risk Reduction |

### Key Value Formulas (5 most versatile)

| Formula | ID | Use Case | Output |
|---------|-----|----------|--------|
| NRR Improvement Value | VF002 | Retention/Expansion ROI | `Base_ARR × ΔNRR% × 3yr × GM%` |
| ARR Growth Efficiency | VF001 | Unit economics improvement | `ΔARR × (1 – CAC_Payback/12) × GM% × 3yr` |
| Cloud Cost Optimization | VF006 | Infrastructure waste recovery | `Annual_Cloud_Spend × Waste% × Recovery%` |
| Churn Reduction Value | VF005 | Retention ROI | `Customers × ARPA × ΔChurn% × Lifespan` |
| Sales Cycle Reduction | VF003 | Velocity improvement | `ΔCycle% × Pipeline_Velocity × 12mo` |

---

## Appendix: Segment-Specific Guidance

| Segment | Key Pains | Key KPIs | Key Formulas |
|---------|-----------|----------|--------------|
| **Horizontal SaaS** | P001-P005, P011, P017 | K001-K014, K026, K036-K038 | VF001-VF005, VF008, VF022 |
| **Vertical SaaS** | P001-P005, P008, P018 | K001-K014, K026, K040 | VF001-VF005, VF013, VF019 |
| **AI-Native SaaS** | P001, P006, P014, P019 | K045-K046, K060-K062 | VF014, VF020, VF006 |
| **Infrastructure/Platform** | P006, P007, P016, P020 | K019-K025, K051-K053 | VF006, VF007, VF017, VF023 |
| **Go-to-Market Specialties** | P003, P011, P012, P017 | K009-K015, K036-K038, K054-K056 | VF003, VF004, VF008, VF016, VF018 |

---

*This SKILL.md is auto-generated from the SaaS Master ValuePack (M2). Refer to `value-pack.json` for structured data and `signals-examples.ts` for TypeScript type definitions.*
