# SKILL.md — Banking Vertical Subpack

## Skill Identity Block

| Attribute | Value |
|-----------|-------|
| **skill_name** | Banking Vertical Subpack |
| **description** | Vertical-specialized value intelligence for Banking sub-segments including Retail, Commercial, Investment, Community/Regional, Credit Unions, Digital Banks, Private Banking, Treasury, Payments/Cards, and Lending (Mortgage/Auto/SMB). Extends the Financial Services Master Pack with banking-specific pains, KPIs, value drivers, benchmarks, signal rules, personas, and buying triggers. |
| **version** | 1.0.0 |
| **domain** | Financial Services |
| **pack_type** | subpack |
| **parent_master** | financial-services-master-v1 |

---

## Triggers Section

Auto-load this skill when queries match any of the following patterns:

1. **"retail banking NIM compression"** — Deposit beta erosion, net interest margin decline, cost-of-funds pressure
2. **"mortgage origination cost"** — Cost-to-close escalation, cycle time delays, pull-through rate decline
3. **"digital onboarding dropout"** — Account opening abandonment, identity verification friction, KYC false rejects
4. **"commercial lending credit risk"** — CRE concentration, refinancing cliff, watch list expansion, appraisal reduction
5. **"payments real-time RTP"** — FedNow/RTP fraud detection latency, APP scam losses, real-time authorization gaps
6. **"community bank efficiency ratio"** — Non-interest expense inflation, revenue per employee decline, compliance cost burden
7. **"credit union membership growth"** — Demographic aging, digital engagement stagnation, young member acquisition
8. **"card interchange revenue compression"** — Durbin 2.0 risk, rewards cost inflation, CAC economics
9. **"treasury management deposit erosion"** — Commercial deposit outflows, ECR spread compression, RFP loss rate
10. **"auto lending residual value risk"** — Lease-end volume surge, remarketing delays, subprime delinquency
11. **"private banking advisor succession"** — Aging advisor workforce, next-gen client engagement, AUM productivity
12. **"core banking system modernization"** — API limitations, vendor lock-in, product launch delays, batch processing

---

## Reasoning Flow

### Step 1: Load Parent Master First
Always begin by loading `financial-services-master-v1` to establish the base framework:
- Value Driver Framework (VD001–VD051)
- Base Persona Archetypes (PER001–PER014)
- Evidence Source Types and Formula Templates (VF001–VF025)
- Signal Source Taxonomy and Benchmark Methodology
- Governance Framework (source coverage, confidence, approval flags)

This subpack **adds** banking-specific components without overriding any master pack content.

### Step 2: Identify Relevant Signals
For a given prospect or account, scan for evidence across these signal categories:

| Signal Category | What to Look For | Key Sources |
|-----------------|------------------|-------------|
| **Regulatory Filings** | Call Reports, FFIEC filings, NCUA data, stress test disclosures | FDIC, Fed, OCC, NCUA |
| **Industry Research** | Benchmark studies, satisfaction surveys, league tables | J.D. Power, Forrester, Cerulli, Nilson, MBA |
| **Data Providers** | Market intelligence, CRE analytics, auto indices, ABS performance | S&P Global, CoStar, Trepp, Experian, TransUnion |
| **News & Earnings** | Earnings calls, ALCO commentary, M&A activity, executive changes | Bloomberg, S&P Global, Dealogic |
| **Macro Indicators** | Fed Funds rate, H.8 releases, Manheim Index, office vacancy rates | Federal Reserve, Cox Automotive |

### Step 3: Match Signals to Pain Patterns
Apply the 18 banking-specific pains (P_BNK_001 to P_BNK_018) by threshold matching:

| Pain | Primary Thresholds | Segment Focus |
|------|-------------------|---------------|
| P_BNK_001 NIM Compression | Deposit beta >70%, NIM decline >15bps YoY | Banking, CUs, Community/Regional |
| P_BNK_002 Mortgage Cost Escalation | Cost-to-close >$12K, cycle >45 days | Banking, Mortgage Lending |
| P_BNK_003 Branch Cost Inflation | Cost/branch >$800K, digital share >85% | Retail, Community/Regional |
| P_BNK_004 CRE Concentration | CRE >300% RBC, watch list >8% | Commercial, Community/Regional |
| P_BNK_005 Auto Residual Risk | Residual losses >$500/unit, delinquency >3.5% | Auto Lending, Retail |
| P_BNK_006 Digital Onboarding Friction | Abandonment >60%, IDV failure >25% | Retail, Digital Banks, CUs |
| P_BNK_007 Treasury Deposit Erosion | Outflows >8% quarterly, ECR spread <50bps | Treasury, Commercial |
| P_BNK_008 Card Interchange Compression | Interchange yield decline >5bps, rewards >45% | Payments, Retail |
| P_BNK_009 Commercial RFP Decline | Win rate <30%, decision time >14 days | Commercial, Investment |
| P_BNK_010 Private Banking Succession | Advisor age >55, AUM/advisor <$100M | Private Banking, Retail |
| P_BNK_011 Core System Lock-in | API >500ms, launch cycle >12 months | Retail, Digital, CUs |
| P_BNK_012 Efficiency Ratio Deterioration | Efficiency ratio >65%, rev/FTE <$350K | Community/Regional, CUs |
| P_BNK_013 RTP Fraud Latency Gap | Detection latency >300ms, APP losses >0.2% | Payments, Retail, Digital |
| P_BNK_014 SMB Relationship Fragmentation | Primary bank share <40%, loan abandonment >55% | SMB Lending, Commercial |
| P_BNK_015 Credit Card Yield Compression | Portfolio yield <18%, charge-off >4.5% | Payments, Retail |
| P_BNK_016 IB Pipeline Compression | Advisory revenue decline >20%, pitch/win <15% | Investment Banking |
| P_BNK_017 Digital Bank Unit Economics | CAC >$200, burn >$10M/month | Digital Banks, Fintech |
| P_BNK_018 CU Membership Stagnation | Growth <2%, average age >50 | Credit Unions |

### Step 4: Map to Personas and Value Hypotheses
Once pain(s) are identified, match to the 6 banking-specific personas and their KPI ownership:

| Persona | Key KPIs | Pain Ownership | Budget Range |
|---------|----------|----------------|--------------|
| PER_BNK_001 Chief Lending Officer | K_BNK_025–027, K_BNK_004–006, K_BNK_010–011 | P_BNK_002, P_BNK_004, P_BNK_005, P_BNK_009 | $5M–50M |
| PER_BNK_002 Branch Operations Manager | K_BNK_007–009, K_BNK_034–035 | P_BNK_003, P_BNK_012 | $2M–10M |
| PER_BNK_003 Digital Banking Product Owner | K_BNK_016–018, K_BNK_008, K_BNK_031–032 | P_BNK_006, P_BNK_011, P_BNK_017 | $3M–15M |
| PER_BNK_004 Treasury Sales Officer | K_BNK_019–021, K_BNK_040–041 | P_BNK_007, P_BNK_014 | $2M–8M |
| PER_BNK_005 Mortgage Operations VP | K_BNK_004–006, K_BNK_034 | P_BNK_002 | $5M–25M |
| PER_BNK_006 Payments Product Manager | K_BNK_022–024, K_BNK_037–039, K_BNK_043–045 | P_BNK_008, P_BNK_013, P_BNK_015 | $3M–12M |

### Step 5: Apply Value Formulas
Use the 15 banking-specific value formulas (VF_BNK_001 to VF_BNK_015) to quantify opportunity:

1. **VF_BNK_001** — Deposit Beta Improvement NIM Value
2. **VF_BNK_002** — Mortgage Cost-to-Close + Cycle Time Reduction
3. **VF_BNK_003** — Branch Network Rationalization Savings
4. **VF_BNK_004** — CRE Risk Mitigation and Provision Avoidance
5. **VF_BNK_005** — Auto Lease Residual Value Protection
6. **VF_BNK_006** — Digital Onboarding Conversion Improvement
7. **VF_BNK_007** — Treasury Deposit Retention Value
8. **VF_BNK_008** — Card Interchange and Rewards Optimization
9. **VF_BNK_009** — Commercial Banking RFP and Speed Value
10. **VF_BNK_010** — Private Banking Advisor Productivity
11. **VF_BNK_011** — Core Banking Modernization ROI
12. **VF_BNK_012** — Community Bank Efficiency Improvement
13. **VF_BNK_013** — Real-Time Payment Fraud Prevention Value
14. **VF_BNK_014** — SMB Banking Revenue Recovery
15. **VF_BNK_015** — Credit Union Digital Transformation Value

### Step 6: Confidence Scoring Guidance

| Confidence Level | Criteria |
|-----------------|----------|
| **HIGH** | Pain threshold exceeded on 3+ symptoms with data from 2+ independent sources (e.g., FDIC Call Report + S&P Global data). Formula inputs validated by prospect disclosure or industry benchmark. |
| **MEDIUM** | Pain threshold exceeded on 2 symptoms with data from 1 primary source + 1 secondary source. Some formula inputs estimated from peer data. |
| **LOW** | Pain threshold exceeded on 1 symptom only, or data from single source with no corroboration. Formula inputs largely assumed. |

**Signal Rule Confidence Override:** When a signal rule (SR_BNK_001 to SR_BNK_020) triggers with HIGH confidence, elevate the overall pain confidence by one level (MEDIUM → HIGH, LOW → MEDIUM).

### Step 7: Discovery and Objection Handling
Use the 20 discovery questions (DQ_BNK_001 to DQ_BNK_020) to validate signals in prospect conversations. Prepare responses to the 10 objection patterns (OBJ_BNK_001 to OBJ_BNK_010) using the provided rebuttal frameworks.

---

## Inheritance Map

### Master Skill to Load First
**`financial-services-master-v1`** must be loaded before this subpack.

| Master Component | Banking Subpack Extension |
|-----------------|---------------------------|
| VD001–VD051 (Value Drivers) | VD_BNK_001–VD_BNK_036 (36 new banking-specific drivers) |
| PER001–PER014 (Personas) | PER_BNK_001–PER_BNK_006 (6 new banking personas) |
| VF001–VF025 (Formulas) | VF_BNK_001–VF_BNK_015 (15 new banking formulas) |
| Signal Source Taxonomy | SR_BNK_001–SR_BNK_020 (20 new banking signal rules) |
| Benchmark Methodology | B_BNK_001–B_BNK_025 (25 new banking benchmarks) |
| Evidence Sources | ES_BNK_001–ES_BNK_012 (12 new banking evidence sources) |

### What This Subpack Adds Beyond the Master
- **18 banking-specific pains** with segment-level prevalence and confidence
- **54 banking KPIs** with formulas, benchmark ranges, and calculation frequencies
- **15 value formulas** with worked examples showing $20M–$340M annual value ranges
- **20 signal rules** with automatic trigger thresholds and recommended actions
- **6 specialized personas** with budget ranges, trusted evidence sources, and disliked claims
- **15 buying triggers** mapped to pain, persona, urgency, and budget level
- **12 regulatory factors** including Basel III Endgame, Durbin 2.0, CECL, FedNow
- **15 technology systems** with pain links for solution mapping

### When to Use Master vs. Subpack
| Scenario | Use |
|----------|-----|
| Generic financial services prospect, no banking specialization identified | Master only |
| Prospect is a bank, credit union, neobank, or banking-adjacent fintech | **Master + Banking Subpack** |
| Deep-dive on deposit beta, NIM, mortgage ops, CRE risk, RTP fraud | Banking Subpack directly |
| Cross-industry comparison (bank vs. insurer vs. asset manager) | Master with multiple subpacks |

---

## Structured Output Template

The following JSON structure is the expected enrichment output for a Signals Analysis using this skill:

```json
{
  "skill_applied": "banking-v1",
  "parent_master": "financial-services-master-v1",
  "analysis_timestamp": "2025-01-28T00:00:00Z",
  "prospect_segment": "Community Bank | Regional Bank | Digital Bank | Credit Union | Commercial Bank | Investment Bank | etc.",
  "detected_pains": [
    {
      "pain_id": "P_BNK_001",
      "pain_name": "NIM Compression from Deposit Beta >70%",
      "confidence": "HIGH",
      "evidence_count": 3,
      "symptoms_triggered": ["NIM declining >15bps YoY", "deposit beta >70%", "brokered deposit share >10%"],
      "linked_kpis": ["K_BNK_001", "K_BNK_002", "K_BNK_003"],
      "linked_value_drivers": ["VD_BNK_001", "VD_BNK_002"],
      "affected_personas": ["CFO", "Treasurer", "CEO"]
    }
  ],
  "matched_personas": [
    {
      "persona_id": "PER_BNK_001",
      "persona_name": "Chief Lending Officer (CLO)",
      "relevance_score": 0.92,
      "owned_kpis": ["K_BNK_025", "K_BNK_026", "K_BNK_027"],
      "budget_range": "$5M-50M"
    }
  ],
  "signal_rules_triggered": [
    {
      "rule_id": "SR_BNK_001",
      "rule_name": "Deposit Beta Surge",
      "trigger": "Beta >70% for 2 quarters",
      "recommended_action": "ALCO deep-dive",
      "confidence": "HIGH"
    }
  ],
  "value_hypotheses": [
    {
      "formula_id": "VF_BNK_001",
      "formula_name": "Deposit Beta Improvement NIM Value",
      "estimated_annual_value": "$127.5M",
      "value_range": "$95M-$150M",
      "key_assumptions": ["Deposit base = $30B", "Rate change = 250bps", "Margin factor = 0.85"],
      "risks": ["Competitive pricing war", "Rate reversal", "Deposit migration to MMFs"]
    }
  ],
  "buying_triggers": [
    {
      "trigger_id": "BT_BNK_001",
      "trigger_name": "NIM Compression Crisis",
      "urgency": "HIGH",
      "budget_availability": "Medium",
      "time_to_value": "2-4 quarters"
    }
  ],
  "regulatory_factors": [
    {
      "reg_id": "RF_BNK_001",
      "regulation": "Basel III Endgame / Basel IV",
      "body": "Fed/FDIC/OCC",
      "impact": "10-20% RWA increase for large banks",
      "cost": "$2M-50M/yr",
      "status": "Proposed; 2025-2028"
    }
  ],
  "technology_systems": [
    {
      "system_id": "TS_BNK_001",
      "system_name": "Core Banking (Fiserv/FIS/Jack Henry)",
      "category": "Core Platform",
      "linked_pains": ["P_BNK_011", "P_BNK_012"]
    }
  ],
  "discovery_questions_recommended": ["DQ_BNK_001", "DQ_BNK_002", "DQ_BNK_003"],
  "objections_likely": ["OBJ_BNK_001", "OBJ_BNK_005"],
  "overall_confidence": "HIGH",
  "source_coverage": "Mixed (public + subscription sources)",
  "next_steps": ["Validate deposit beta with prospect CFO", "Request ALCO minutes", "Peer NIM comparison analysis"]
}
```

---

## Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | HIGH |
| **Source Coverage** | Mixed (public + subscription sources) |
| **Customer-Facing Approval Status** | Yes — Approved |
| **Review Owner** | Banking Vertical Subpack Creator (Phase 2) |
| **Last Updated** | 2025-01-28 |
| **Agent Swarm ID** | banking-subpack-s4-1 |
| **Parent Master Swarm ID** | financial-services-master-v1 |

---

## Quick Reference

### Top 5 Pains
| Rank | Pain | Threshold | Prevalence |
|------|------|-----------|------------|
| 1 | **NIM Compression** (P_BNK_001) | Deposit beta >70%, NIM decline >15bps | HIGH |
| 2 | **Mortgage Cost Escalation** (P_BNK_002) | Cost-to-close >$12K, cycle >45 days | HIGH |
| 3 | **Branch Cost Inflation** (P_BNK_003) | Cost/branch >$800K, digital share >85% | HIGH |
| 4 | **CRE Concentration** (P_BNK_004) | CRE >300% RBC, watch list >8% | HIGH |
| 5 | **Digital Onboarding Friction** (P_BNK_006) | Abandonment >60%, IDV failure >25% | HIGH |

### Top 5 KPIs
| Rank | KPI | Formula | Benchmark |
|------|-----|---------|-----------|
| 1 | **Deposit Beta** (K_BNK_001) | (Δ Cost of Deposits / Δ FFR) × 100 | 30–55% |
| 2 | **Net Interest Margin** (K_BNK_002) | (Interest Income − Interest Expense) / Avg Earning Assets | 3.0–4.5% |
| 3 | **Efficiency Ratio** (K_BNK_034) | Non-Interest Expense / (NII + NII) | 45–58% |
| 4 | **Mortgage Cost-to-Close** (K_BNK_004) | Total Origination Cost / Closed Loan Count | $5,000–8,000 |
| 5 | **Digital Onboarding Abandonment** (K_BNK_016) | Abandoned / Total Started | 25–35% |

### Top 3 Personas
| Rank | Persona | Primary Pains | Budget |
|------|---------|--------------|--------|
| 1 | **Chief Lending Officer (CLO)** | P_BNK_002, P_BNK_004, P_BNK_005, P_BNK_009 | $5M–50M |
| 2 | **Digital Banking Product Owner** | P_BNK_006, P_BNK_011, P_BNK_017 | $3M–15M |
| 3 | **Payments Product Manager** | P_BNK_008, P_BNK_013, P_BNK_015 | $3M–12M |

### Key Value Formulas
| Formula | Name | Example Output |
|---------|------|----------------|
| **VF_BNK_001** | Deposit Beta Improvement NIM Value | $127.5M annual pre-tax (at $30B deposit base) |
| **VF_BNK_002** | Mortgage Cost-to-Close + Cycle Reduction | $232M annual value (40K loans/year) |
| **VF_BNK_003** | Branch Network Rationalization | $61.5M annual savings (50 branches closed) |
| **VF_BNK_013** | RTP Fraud Prevention Value | $41.5M annual value (fraud + APP + CX + penalties) |
| **VF_BNK_009** | Commercial RFP and Speed Value | $322M annual value (win rate + speed + cross-sell) |

---

*End of SKILL.md — Banking Vertical Subpack (banking-v1)*
