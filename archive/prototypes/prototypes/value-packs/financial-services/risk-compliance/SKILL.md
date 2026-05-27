# Risk, Compliance, and Financial Crime Subpack

**Pack ID:** `risk-compliance-v1`  
**Parent Master:** `financial-services-master-v1`  
**Version:** 1.0.0  
**Last Updated:** 2024-12-19  
**Confidence Level:** HIGH  
**Approved for Customer-Facing Output:** Yes

---

## 1. Skill Identity Block

| Field | Value |
|---|---|
| **skill_name** | Risk, Compliance, and Financial Crime Subpack |
| **description** | Vertical-specialized value intelligence for Risk, Compliance, and Financial Crime functions in financial services. Covers AML/KYC, sanctions, fraud detection, credit/market/operational risk, model risk, regulatory reporting, SOX, consumer compliance, data governance, cyber risk, and third-party risk. Additional components only; inherits base framework from master. |
| **version** | 1.0.0 |
| **domain** | financial-services |
| **pack_type** | subpack |
| **parent_master** | financial-services-master-v1 |

---

## 2. Triggers

Auto-load this skill when queries contain patterns like:

1. "AML false positive rate"
2. "sanctions screening latency"
3. "regulatory reporting automation"
4. "model risk SR 11-7"
5. "third-party vendor concentration"
6. "KYC onboarding friction"
7. "SOX compliance cost reduction"
8. "real-time fraud detection FedNow"
9. "credit model Gini decay"
10. "consumer compliance UDAAP"
11. "operational risk loss event capture"
12. "trade surveillance alert fatigue"

---

## 3. Reasoning Flow

### Step 1: Identify Relevant Signals
Scan the prospect/account for indicators across these categories:

- **Regulatory Signals:** Active MRAs, consent orders, CFPB supervision, SEC cyber disclosures, SOX material weaknesses, late filings
- **Operational Signals:** KPIs breaching typical ranges (false positive rates >90%, screening latency >300ms, onboarding >10 days, model overrides >15%)
- **Technology Signals:** Legacy screening engines >5 years old, batch-based fraud detection on real-time rails, missing UEBA deployment, no FAIR quantification
- **Financial Signals:** CECL volatility >$50M/qtr, fraud losses >10bps on instant payments, external audit fees increasing >10% annually
- **Governance Signals:** Model inventory growing >30% annually, RCSA update cycle >18 months, data lineage coverage <50%

### Step 2: Map Signals to Pains
Apply the 18 signal rules (RC-SR001 to RC-SR018) to match detected signals to specific pains. Each signal rule contains:
- Confidence level and rationale
- Required evidence checklist
- Linked KPIs and personas
- Financial impact category and range

### Step 3: Cross-Reference with KPIs
Validate signal strength using the 25 vertical KPIs. Compare prospect values against:
- **Typical Range:** Industry median performance
- **Benchmark Range:** Best-in-class / target performance
- **Gap Size:** Difference between current state and benchmark

### Step 4: Calculate Value Hypotheses
Apply the 12 vertical formulas (RC-VF001 to RC-VF012) to quantify financial impact. Formulas connect to four value categories:
- **Cost Savings:** Investigator labor, testing hours, remediation, reconciliation
- **Risk Reduction:** Penalty avoidance, provision volatility, fraud loss, capital buffer
- **Revenue Uplift:** Onboarding abandonment recovery, correspondent banking revenue
- **Working Capital:** FRTB capital reduction, RWA optimization

### Step 5: Confidence Scoring
Score each hypothesis using this matrix:

| Evidence Quality | HIGH | MEDIUM | LOW |
|---|---|---|---|
| **Direct data from prospect** | 90-95% | 75-85% | 60-70% |
| **Industry benchmark + segment match** | 80-90% | 65-75% | 50-60% |
| **Anecdotal / proxy** | 60-70% | 45-55% | 30-40% |

Rules:
- Require 2+ data points to score HIGH
- Single data point scores MEDIUM maximum
- No evidence = LOW, do not present without validation plan

### Step 6: Inheritance Guidance
- **Always load the master first** (`financial-services-master-v1`) to establish base framework
- **Load this subpack second** to overlay vertical specialization
- **Do not duplicate master content** (value drivers, personas, formulas)
- **Use master personas** (CRO, CCO, CISO, CDO, CFO, etc.) plus the 6 new vertical personas (BSA/AML Officer, Model Risk Manager, Regulatory Reporting Director, Fraud Prevention Director, Third-Party Risk Manager, Cyber Risk Lead)

---

## 4. Inheritance Map

### Master Skill to Load First
```
financial-services-master-v1
```

### What This Subpack Adds

| Category | Master | This Subpack |
|---|---|---|
| Pains | Base framework (generic) | 18 vertical pains (RC-P001 to RC-P018) |
| KPIs | Base metrics | 25 vertical KPIs (RC-K001 to RC-K025) |
| Value Drivers | 5 categories | 36 vertical mappings (RC-VD001 to RC-VD036) |
| Formulas | NPV, ROI templates | 12 vertical formulas (RC-VF001 to RC-VF012) |
| Benchmarks | Methodology | 18 vertical benchmarks (RC-B001 to RC-B018) |
| Signal Rules | Taxonomy | 18 vertical signal rules (RC-SR001 to RC-SR018) |
| Personas | 15 base archetypes | +6 specialized personas (RC-PER001 to RC-PER006) |
| Buying Triggers | Framework | 14 vertical triggers (RC-BT001 to RC-BT014) |
| Regulatory Factors | Taxonomy | 11 specific regulations (RC-RF001 to RC-RF011) |
| Technology Systems | Framework | 13 systems (RC-TS001 to RC-TS013) |

### When to Use Master vs. Subpack

| Scenario | Recommendation |
|---|---|
| Generic financial services discovery | Master only |
| Risk/Compliance/Financial Crime specific conversation | Master + this subpack |
| Unknown vertical focus | Master first, then load subpack if signals detected |
| Pre-call research for CRO/CCO meeting | Master + this subpack |

---

## 5. Structured Output Template

### Signals Analysis Enrichment JSON

```json
{
  "pack_id": "risk-compliance-v1",
  "pack_type": "subpack",
  "parent_master": "financial-services-master-v1",
  "analysis_timestamp": "2024-12-19T00:00:00Z",
  "prospect_signals": {
    "detected_pains": [
      {
        "pain_id": "RC-P001",
        "pain_name": "Sanctions Screening Alert Overflow and Name Matching Errors",
        "confidence": "HIGH",
        "triggering_signals": ["RC-SR001", "RC-SR002"],
        "detected_kpis": [
          {
            "kpi_id": "RC-K001",
            "kpi_name": "Sanctions Alert False Positive Rate",
            "prospect_value": 96,
            "typical_range": "90-98",
            "benchmark_range": "60-85",
            "gap_severity": "HIGH"
          }
        ],
        "affected_personas": ["RC-PER001", "PER004"],
        "financial_impact": {
          "category": "Cost Savings",
          "estimated_range": "$5M-$50M annually",
          "calculated_value": "$48.3M"
        }
      }
    ],
    "value_hypotheses": [
      {
        "formula_id": "RC-VF001",
        "formula_name": "Sanctions False Positive Reduction Value",
        "inputs_used": {
          "Current_FP_Rate": 0.96,
          "Target_FP_Rate": 0.75,
          "Annual_Alert_Volume": 3000000,
          "Cost_Per_Alert": 75,
          "Investigator_Headcount_Reduction": 7,
          "Loaded_Cost": 150000
        },
        "result": 48300000,
        "unit": "USD per year",
        "confidence": "HIGH"
      }
    ],
    "buying_triggers": [
      {
        "trigger_id": "RC-BT001",
        "trigger_name": "Regulatory examination findings (MRA/MRIA)",
        "timing": "6-18 months",
        "urgency": "HIGH"
      }
    ],
    "recommended_discovery_questions": [
      "RC-DQ001",
      "RC-DQ002"
    ]
  },
  "overall_confidence": "HIGH",
  "governance": {
    "source_coverage": "Mixed (public regulatory data + paid industry benchmarks)",
    "customer_facing_approved": true,
    "review_owner": "Risk-Compliance-Subpack-Agent",
    "last_updated": "2024-12-19"
  }
}
```

---

## 6. Governance Metadata

| Attribute | Value |
|---|---|
| **Confidence Level** | HIGH |
| **Source Coverage** | Mixed (public regulatory data + paid industry benchmarks) |
| **Customer-Facing Approval Status** | Yes |
| **Review Owner** | Risk-Compliance-Subpack-Agent |
| **Last Updated** | 2024-12-19 |
| **Agent Swarm ID** | swarm-rc-v1-2024 |
| **Parent Master Swarm ID** | swarm-master-fs-v1-2024 |

---

## 7. Quick Reference

### Top 5 Pains (by prevalence and confidence)

| ID | Pain | Prevalence | Confidence | Impact Range |
|---|---|---|---|---|
| RC-P001 | Sanctions Screening Alert Overflow | HIGH | HIGH | $5M-$50M |
| RC-P002 | KYC Onboarding Friction | HIGH | HIGH | $10M-$100M |
| RC-P003 | Credit Model Performance Decay | HIGH | HIGH | $20M-$200M |
| RC-P006 | Fraud Detection Latency on Real-Time Rails | HIGH | HIGH | $15M-$80M |
| RC-P007 | SOX ICFR Control Deficiency | HIGH | HIGH | $5M-$25M |

### Top 5 KPIs (by signal strength)

| ID | KPI | Typical | Benchmark | Unit |
|---|---|---|---|---|
| RC-K001 | Sanctions Alert False Positive Rate | 90-98% | 60-85% | percentage |
| RC-K004 | KYC Onboarding Cycle Time | 8-15 days | 2-5 days | days |
| RC-K007 | Credit Model Gini Coefficient | 0.50-0.75 | 0.65-0.85 | ratio |
| RC-K010 | VaR Backtesting Exception Rate | 2-6% | 0.4-1.6% | percentage |
| RC-K016 | Real-Time Fraud Detection Latency | 150-400ms | 30-100ms | milliseconds |

### Top 3 Personas

| ID | Persona | Focus Area | Master/Vertical |
|---|---|---|---|
| RC-PER001 | BSA/AML Officer | AML program governance, sanctions, SAR filing | Vertical |
| RC-PER002 | Chief Model Risk Officer / Model Risk Manager | SR 11-7 compliance, AI/ML governance | Vertical |
| RC-PER004 | Fraud Prevention Director | Real-time fraud, APP scams, insider threat | Vertical |

### Key Value Formulas

| ID | Formula | Example Result |
|---|---|---|
| RC-VF001 | Sanctions False Positive Reduction | $48.3M annual savings |
| RC-VF003 | Credit Model Performance Improvement | $33M annual value |
| RC-VF006 | Fraud Loss and Reimbursement Reduction | $97.25M annual value |
| RC-VF011 | Regulatory Reporting Automation ROI | $21.4M annual savings |
| RC-VF012 | Model Risk Management Efficiency | $25.3M annual value |

---

## Usage Notes

1. **Do not duplicate master content.** Reference the master pack for base value drivers, generic personas, and framework definitions.
2. **All KPIs have formulas.** Every benchmark has a source citation. Every signal rule has a confidence level with rationale.
3. **Assumptions requiring validation:** Customer lifetime value (CLV), average alert disposition cost, loaded FTE cost, and model override cost vary significantly by institution. Use customer-specific data when available; industry benchmarks are marked with confidence flags.
4. **Financial outcomes:** All formulas connect to one of: Cost Savings, Risk Reduction, Revenue Uplift, or Working Capital Improvement.
5. **Persona overlap:** The 6 new personas (RC-PER001-006) specialize sub-functions within master personas (CRO, CCO, CISO, CDO). Use both in discovery conversations for complete stakeholder mapping.
