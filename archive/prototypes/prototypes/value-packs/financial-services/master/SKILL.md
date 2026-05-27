# Financial Services Master (M4) - OpenClaw Skill Definition

---

## 1. Skill Identity Block

```yaml
skill_name: Financial Services Master
skill_id: financial-services-master-v1
description: |
  Comprehensive value intelligence foundation for the Financial Services industry, covering Banking, Capital Markets, Insurance, Fintech, and Risk/Compliance & Financial Crime. Enables AI-driven discovery, qualification, and value articulation for enterprise technology and service providers.
  
  This master skill provides cross-segment signal interpretation, persona mapping, KPI benchmarking, and quantifiable value formulas to accelerate enterprise sales cycles in regulated financial institutions.
version: "1.0.0"
domain: industry
pack_type: master
parent_master: null
segments:
  - Banking (12 sub-segments)
  - Capital Markets (12 sub-segments)
  - Insurance (12 sub-segments)
  - Fintech (12 sub-segments)
  - Risk, Compliance, and Financial Crime (13 sub-segments)
subpacks:
  - banking
  - capital-markets
  - insurance
  - fintech
  - risk-compliance-financial-crime
```

---

## 2. Triggers Section

The following natural language query patterns should auto-load this master skill:

| # | Trigger Query |
|---|---------------|
| 1 | "analyze a bank" or "analyze a credit union" |
| 2 | "fintech fraud detection opportunity" |
| 3 | "insurance claims leakage" or "insurance underwriting profitability" |
| 4 | "capital markets settlement failure costs" |
| 5 | "AML false positive reduction" or "transaction monitoring modernization" |
| 6 | "mortgage origination cost optimization" |
| 7 | "wealth management advisor productivity" |
| 8 | "BNPL credit losses and regulatory scrutiny" |
| 9 | "core banking modernization debt" |
| 10 | "financial services cybersecurity incident response" |
| 11 | "regulatory reporting accuracy and timeliness" |
| 12 | "cross-border payment friction" |

**Load Conditions:**
- Prospect operates in Banking, Capital Markets, Insurance, Fintech, or Risk/Compliance
- Keywords: NIM, CAC, deposit beta, combined ratio, AUM, settlement fail, AML, claims leakage, CECL, T+1, IFRS 17, BNPL, FedNow, APP scam, model risk, TPRM

---

## 3. Reasoning Flow

### Step 1: Segment Classification
1. Identify the prospect's primary segment using taxonomy definitions:
   - **Banking**: Deposit-taking, lending, payments (revenue $50M-$100B+)
   - **Capital Markets**: Trading, asset management, custody (revenue $25M-$50B+)
   - **Insurance**: Risk transfer, underwriting, claims (revenue $100M-$200B+)
   - **Fintech**: Technology-first financial services (revenue $10M-$10B+)
   - **Risk/Compliance**: Risk management and regulatory functions (spend 5-15% of firm revenue)

### Step 2: Signal Discovery & Evidence Gathering
Priority evidence sources (in descending confidence):
1. **SEC 10-K/10-Q** / **FFIEC Call Reports** / **NAIC Annual Statements** — HIGH confidence
2. **Regulatory enforcement databases** (OCC, FDIC, CFPB, FINRA) — HIGH confidence
3. **Earnings call transcripts** — MEDIUM confidence
4. **Job posting analytics** — MEDIUM confidence
5. **Industry benchmark surveys** — MEDIUM confidence
6. **Cybersecurity incident databases** — HIGH confidence

### Step 3: Signal-to-Pain Mapping
Match discovered signals against the 25 documented business pains:
- **HIGH prevalence pains (>15 across segments):** Legacy core banking (P001), CAC escalation (P002), NIM compression (P003), AML false positives (P005), Claims leakage (P006), Underwriting erosion (P007), Cybersecurity incidents (P010), Regulatory reporting deficits (P011), Payments fraud (P012), Credit portfolio deterioration (P014), Deposit attrition (P018)
- **MEDIUM prevalence pains:** Trade settlement failures (P009), SMB lending speed (P013), BNPL credit losses (P016), Wealth advisor succession (P015), Model risk backlogs (P019), Cross-border friction (P020), InsurTech disintermediation (P021), Hedge fund operational alpha (P024), Stablecoin custody (P025)

### Step 4: KPI Benchmarking & Gap Analysis
For each identified pain, calculate or estimate the relevant KPIs and compare against benchmarks:
- Red flag = outside "typical range" and trending toward "benchmark range" gap
- Use 35 sourced benchmarks (B001-B035) for peer comparison

### Step 5: Persona Identification
Map confirmed pains to affected personas using the 14 archetype profiles:
- **Economic buyers:** CFO, CRO, COO, CMO, Head of Distribution, Chief Claims Officer
- **Technical buyers:** CIO, CTO, CISO, Chief Data Officer, Head of Digital
- **User influencers:** Chief Compliance Officer, Chief Actuary, General Counsel

### Step 6: Value Hypothesis Construction
Select applicable value formulas (VF001-VF025) from the master pack:
1. Match formula to segment and pain
2. Gather required inputs from prospect data or industry benchmarks
3. Apply confidence rules based on data quality
4. Calculate annual value and present with sensitivity analysis

### Step 7: Confidence Scoring
Apply the following confidence scoring guidance:

| Score | Criteria |
|-------|----------|
| **0.90-1.00** | Regulatory enforcement confirmed + financial disclosure data + 2+ confirming signals |
| **0.75-0.89** | Public filing evidence + 1 confirming signal + benchmark gap identified |
| **0.60-0.74** | Industry benchmark deviation + anecdotal evidence (earnings call, job postings) |
| **0.40-0.59** | Single signal only; requires prospect interview to confirm |
| **<0.40** | Speculative; insufficient evidence for customer-facing claims |

### Step 8: Buying Trigger Timing Assessment
Check for active buying triggers (BT001-BT025):
- **Critical urgency:** Consent orders, cyber incidents, SOX material weakness, redemption gates, cross-border de-risking (0-6 months)
- **High urgency:** Contract expirations, CEO/CIO change, NIM crisis, AUM outflows, IFRS 17 deadlines, T+1 transition (6-18 months)

---

## 4. Inheritance Map

This is a **master skill**. Subpacks inherit all master definitions and add segment-specific depth:

| Subpack | What It Adds Beyond Master |
|---------|---------------------------|
| banking | Deeper retail/commercial banking pains, community bank benchmarks, neobank competitive dynamics |
| capital-markets | Asset manager workflow specifics, prime brokerage, custody, securities finance details |
| insurance | Life vs P&C line distinctions, reinsurance, catastrophe modeling, state regulatory variations |
| fintech | Embedded finance, BaaS, stablecoin, crypto custody, rapid scaling pains, thin-file underwriting |
| risk-compliance-financial-crime | SR 11-7 specifics, sanctions, fraud orchestration, TPRM frameworks, regulatory change management |

**When to use master vs subpack:**
- **Master only:** Multi-segment prospect, early discovery, cross-industry solution, insufficient data for sub-segment classification
- **Master + Subpack:** Segment identified, need deeper benchmarks, persona-specific discovery questions, or segment-specific value formulas

---

## 5. Structured Output Template

```json
{
  "skill_id": "financial-services-master-v1",
  "analysis_timestamp": "2026-04-25T00:00:00Z",
  "prospect": {
    "name": "string",
    "segment": "Banking | Capital Markets | Insurance | Fintech | Risk/Compliance",
    "sub_segment": "string",
    "revenue_range": "string",
    "geography": "string"
  },
  "signals_analysis": {
    "signals_discovered": [
      {
        "signal_id": "SR###",
        "signal_name": "string",
        "raw_evidence": "string",
        "evidence_source": "SEC_10K | FFIEC | NAIC | Earnings_Call | Job_Postings | Enforcement | Other",
        "confidence": 0.0,
        "linked_pains": ["P###"],
        "linked_kpis": ["K###"],
        "confirmation_signals_required": ["string"]
      }
    ],
    "pain_profile": {
      "confirmed_pains": [
        {
          "pain_id": "P###",
          "pain_name": "string",
          "prevalence": "HIGH | MEDIUM | LOW",
          "confidence": "HIGH | MEDIUM | LOW",
          "symptoms_observed": ["string"],
          "affected_personas": ["string"],
          "linked_value_drivers": ["VD###"]
        }
      ],
      "pain_score": 0
    },
    "kpi_gaps": [
      {
        "kpi_id": "K###",
        "kpi_name": "string",
        "current_value": "number | unknown",
        "typical_range": "string",
        "benchmark_range": "string",
        "gap_direction": "above | below | within",
        "gap_severity": "critical | significant | moderate | minor"
      }
    ]
  },
  "persona_map": {
    "primary_economic_buyer": {
      "persona_id": "PER###",
      "name": "string",
      "goals": ["string"],
      "pressures": ["string"],
      "trusted_evidence": ["string"],
      "disliked_claims": ["string"]
    },
    "technical_buyers": [
      {
        "persona_id": "PER###",
        "name": "string",
        "decision_influence": "technical"
      }
    ],
    "user_influencers": [
      {
        "persona_id": "PER###",
        "name": "string",
        "decision_influence": "user"
      }
    ]
  },
  "value_hypotheses": [
    {
      "formula_id": "VF###",
      "formula_name": "string",
      "applicable_segments": ["string"],
      "required_inputs": {
        "input_name": "value | unknown"
      },
      "calculated_value": "number | unknown",
      "value_unit": "USD per year",
      "confidence": "HIGH | MEDIUM | LOW",
      "value_driver_category": "Revenue Uplift | Cost Savings | Risk Reduction | Working Capital"
    }
  ],
  "buying_triggers": [
    {
      "trigger_id": "BT###",
      "trigger_name": "string",
      "urgency_level": "critical | high | medium",
      "typical_timing": "string",
      "is_active": true,
      "procurement_implications": "string"
    }
  ],
  "recommended_next_steps": [
    "Validate [specific KPI] with CFO or Controller",
    "Request regulatory examination history from CCO",
    "Conduct discovery call with [persona] on [pain topic]",
    "Deliver benchmark comparison deck for [segment]"
  ]
}
```

---

## 6. Governance Metadata

```yaml
governance:
  confidence_level: Medium
  source_coverage: Mixed
    - SEC 10-K/10-Q (HIGH)
    - FFIEC Call Reports (HIGH)
    - NAIC Annual Statements (HIGH)
    - Regulatory enforcement databases (HIGH)
    - Earnings call transcripts (MEDIUM)
    - Job posting analytics (MEDIUM)
    - Industry benchmark surveys (MEDIUM)
    - Social/executive sentiment (LOW)
  customer_facing_approval: false
  review_owner: Master Pack Foundation Architect - Financial Services
  last_updated: "2026-04-25"
  agent_swarm_id: kimi-k2.6-swarm-m4-financial-services
  version_control:
    current: "1.0.0"
    schema: MasterValuePack
  data_completeness:
    taxonomies: 5 segments, 60 sub-segments
    pains: 25 documented
    kpis: 77 with formulas
    value_drivers: 51 mapped
    value_formulas: 25 quantified
    benchmarks: 35 sourced
    signal_rules: 30 with confidence
    personas: 14 archetypes
    buying_triggers: 25 events
    technology_systems: 20 mapped
    regulatory_factors: 15 covered
    competitor_factors: 10 disruptive forces
    value_domains: 12 quantifiable
    discovery_questions: 20 targeted
    objections: 10 with reframes
```

---

## 7. Quick Reference

### Top 5 Pains (by prevalence and cross-segment impact)

| # | Pain | ID | Prevalence | Key Symptom |
|---|------|-----|-----------|-------------|
| 1 | Legacy Core Banking Modernization Debt | P001 | HIGH | Maintenance >40% of IT budget |
| 2 | AML False Positive Fatigue | P005 | HIGH | >90% false positive rate |
| 3 | Cybersecurity Incident Frequency | P010 | HIGH | >1 material incident/year |
| 4 | Net Interest Margin Compression | P003 | HIGH | NIM declining >15bps YoY |
| 5 | Claims Leakage and Inflated LAE | P006 | HIGH | Claims leakage >8% of incurred losses |

### Top 5 KPIs (by analytical utility)

| # | KPI | ID | Formula | Benchmark |
|---|-----|-----|---------|-----------|
| 1 | Net Interest Margin | K009 | (Interest Income - Interest Expense) / Avg Earning Assets * 100 | 3.0-4.5% |
| 2 | AML Alert False Positive Rate | K015 | False Positive Alerts / Total Alerts * 100 | 60-85% |
| 3 | Combined Ratio | K021 | (Incurred Losses + LAE + UW Expenses) / Net Earned Premium * 100 | 85-95% |
| 4 | Customer Acquisition Cost | K005 | Total S&M Spend / New Customers | $80-200 |
| 5 | Core System Availability | K001 | Uptime Minutes / Calendar Minutes * 100 | 99.95-99.999% |

### Top 3 Personas (by decision influence)

| # | Persona | ID | Influence | Trusted Evidence |
|---|---------|-----|-----------|------------------|
| 1 | Chief Financial Officer | PER001 | Economic | Peer benchmarking, ROI with sensitivity |
| 2 | Chief Information Officer | PER002 | Technical | Gartner MQs, reference architectures |
| 3 | Chief Risk Officer | PER003 | Economic | Regulatory guidance, stress test results |

### Key Value Formulas (Top 5 by applicability)

| # | Formula | ID | Output | Example Value |
|---|---------|-----|--------|---------------|
| 1 | Fraud Loss Reduction Value | VF001 | USD/year | $162.5M annual |
| 2 | AML False Positive Reduction | VF004 | USD/year | $39.65M annual savings |
| 3 | NIM Expansion from Deposit Beta | VF003 | USD/year | $144M pre-tax |
| 4 | Claims Leakage Reduction | VF005 | USD/year | $270M annual |
| 5 | Mortgage Cost-to-Close Reduction | VF002 | USD/year | $260M annual |

### Critical Buying Triggers (Immediate Action)

| Trigger | ID | Urgency | Timing |
|---------|-----|---------|--------|
| Regulatory Consent Order | BT001 | Critical | 0-6 months |
| Cybersecurity Material Incident | BT006 | Critical | 0-3 months |
| SOX Material Weakness Disclosure | BT022 | Critical | 0-6 months |
| Core Banking Contract Expiration | BT002 | High | 12-24 months |
| NIM Compression Crisis | BT007 | High | 1-3 months |

---

*End of SKILL.md for Financial Services Master (M4)*
*Corresponding files: value-pack.json, value-pack.md, signals-examples.ts*