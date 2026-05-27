# SKILL.md — Public Health and Human Services Subpack

---

## 1. Skill Identity Block

| Field | Value |
|-------|-------|
| **skill_name** | Public Health and Human Services Subpack |
| **description** | Vertical-specialized value pack for Medicaid administration, public health departments, child welfare, unemployment insurance, SNAP/benefits, housing assistance, behavioral health, aging/disability/veterans services, and disease surveillance. Provides domain-specific pains, KPIs, formulas, benchmarks, signal rules, personas, and buying triggers for B2G sales and value engineering in health and human services agencies. |
| **version** | 1.0.0 |
| **domain** | Public Sector — Health and Human Services |
| **pack_type** | subpack |
| **parent_master** | public-sector-master-v1 |
| **last_updated** | 2026-04-25 |
| **review_owner** | Vertical Subpack Architect — Public Health & Human Services |

---

## 2. Triggers

The following natural language query patterns should auto-load this subpack:

1. "Medicaid eligibility redetermination" — triggers PH-PAIN-001, PH-PAIN-011, PH-PAIN-013, PH-PAIN-015
2. "SNAP error rate reduction" — triggers PH-PAIN-002, PH-PAIN-011, PH-PAIN-012
3. "Child welfare case management" — triggers PH-PAIN-003, PH-PAIN-017, PH-PAIN-018
4. "Disease surveillance modernization" — triggers PH-PAIN-005, PH-PAIN-014, PH-PAIN-016
5. "Behavioral health 988 integration" — triggers PH-PAIN-006, PH-PAIN-009
6. "Unemployment insurance fraud and backlog" — triggers PH-PAIN-004, PH-PAIN-017
7. "Housing voucher waitlist optimization" — triggers PH-PAIN-007
8. "MMIS end of life replacement" — triggers PH-PAIN-013, PH-PAIN-008
9. "Cross program eligibility integration" — triggers PH-PAIN-015, PH-PAIN-011
10. "HCBS Olmstead compliance" — triggers PH-PAIN-009
11. "Public health emergency preparedness" — triggers PH-PAIN-016
12. "TANF administrative cost reduction" — triggers PH-PAIN-012

---

## 3. Reasoning Flow

### Step 1: Load the Master Skill First
Before applying this subpack, ensure the parent master skill `public-sector-master-v1` is loaded. The master provides:
- Cross-cutting value driver framework (Cost Savings, Risk Reduction, Mission Effectiveness, Revenue Uplift, Working Capital)
- Base persona archetypes (CIO, CFO, CISO, IG, Program Director, Procurement Officer)
- Evidence source taxonomy (GAO, OIG, Federal Budget, Census, FOIA)
- Formula templates (NPV, annualization, confidence rules)
- Signal source taxonomy (budget, audit, incident, workforce)

### Step 2: Identify the Sub-Segment
Map the prospect or account to one or more vertical sub-segments:
- Medicaid State Agencies (SMAs)
- State and Local Public Health Departments
- Child Welfare / Foster Care Agencies
- Unemployment Insurance Agencies
- SNAP / Nutrition Assistance Administration
- Housing Assistance Programs (Section 8, LIHTC)
- Behavioral Health Programs (SAMHSA-funded)
- Aging / Disability / Veterans Services
- Disease Surveillance / Epidemiology

### Step 3: Detect Relevant Signals
Collect raw signals from federal/state data sources, audit reports, or prospect disclosures:
- **Budget signals:** PHEP grant drawdown <80%; HPP coalition participation <70%
- **Audit signals:** CMS corrective action plan; USDA SNAP QC penalty; DOL ETA performance sanction; AFCARS submission errors >5%
- **Incident signals:** Disease reporting >7 days; MMIS downtime >4 hrs/quarter; 988 call abandonment >5%
- **Workforce signals:** Eligibility worker turnover >25%; psychiatrist vacancy >20%; caregiver turnover >40%

Apply the **18 vertical signal interpretation rules** (PH-SIG-001 through PH-SIG-018) to convert raw signals into interpreted meanings with confidence scores.

### Step 4: Map Signals to Pains, KPIs, and Value Drivers
For each interpreted signal:
1. Link to the corresponding **pain** (PH-PAIN-001 through PH-PAIN-018)
2. Identify the **KPIs** that quantify the pain (PH-KPI-001 through PH-KPI-040)
3. Classify the **value driver category** (Cost Savings, Risk Reduction, Mission Effectiveness, Revenue Uplift, Working Capital)
4. Match the **personas** most affected (Medicaid Director, Public Health Officer, Child Welfare Supervisor, UI Claims Director, Eligibility Worker Supervisor, Behavioral Health Program Director)

### Step 5: Build the Value Hypothesis
Select the appropriate **value formula** (PH-VF-001 through PH-VF-012) based on the linked pain and sub-segment. Gather required inputs from the prospect or from federal/state benchmarks. Compute the annual value estimate with sensitivity analysis (low/base/high).

### Step 6: Confidence Scoring
- **HIGH (0.85-1.00):** Signal confirmed by multiple federal data sources (CMS T-MSIS, USDA QC, DOL ETA 901/902, HHS AFCARS); prospect-provided data available; pain prevalence is HIGH with strong source coverage.
- **MEDIUM (0.60-0.84):** Signal from single federal source or state-reported data; some prospect data missing; pain prevalence is MEDIUM or confidence is mixed.
- **LOW (0.00-0.59):** Signal from news or indirect inference only; no prospect data; benchmarks used as proxy; high variance in financial assumptions.

Override confidence downward if:
- Prospect data contradicts federal benchmarks by >30%
- Political or funding environment introduces significant uncertainty (e.g., FMAP renegotiation, federal administration change)
- Union or procurement constraints block implementation pathway

### Step 7: Generate Buying Trigger Timeline
Map confirmed pains to the **14 vertical buying triggers** (PH-TRIG-001 through PH-TRIG-014). Prioritize triggers by urgency:
- **CRITICAL:** Medicaid unwinding wave, Olmstead enforcement, public health emergency declaration
- **HIGH:** SNAP QC penalty, CMS 438 rule, MMIS recompete, UI modernization, CDC DMI funding, 988 expansion, federal NOFO
- **MEDIUM:** HUD PHA modernization, state HHS consolidation

### Step 8: Validate with Discovery Questions
Use the **18 discovery questions** (PH-DQ-001 through PH-DQ-018) to confirm signal interpretation and refine value estimates during prospect conversations.

---

## 4. Inheritance Map

### Master Skill to Load First
**`public-sector-master-v1`** must be loaded before this subpack.

### What the Master Provides
- Cross-cutting pains: Legacy Systems, Cybersecurity, Data Silos, Workforce Shortage, Budget Volatility
- Cross-cutting KPIs: O&M Ratio, Time-to-Hire, Audit Finding Rate, Budget Variance
- Cross-cutting formulas: Legacy O&M Cost Avoidance, Cybersecurity Incident Cost Avoidance, Digital Channel Shift
- Cross-cutting signal rules: Legacy System Maintenance Spending, Critical Vulnerability Exposure, Data Silo Indicators
- Cross-cutting buying triggers: Annual Appropriation, Audit Finding, New Leadership, Incumbent Contract End
- Cross-cutting objections: Procurement Cycle Too Long, Federal Funding Uncertainty, Legacy Integration Complexity

### What This Subpack Adds
- **18 vertical pains** specific to health and human services programs (Medicaid backlog, SNAP error rate, Child Welfare fragmentation, UI fraud, Surveillance latency, BH access gap, Housing waitlist, MCO oversight, HCBS waitlist, Veterans coordination, Eligibility worker crisis, TANF cost rigidity, MMIS EOL, IIS fragmentation, Cross-program silos, Emergency preparedness, CSE lag, CCDF bottleneck)
- **40 vertical KPIs** with program-specific formulas, benchmarks, and federal targets
- **12 vertical value formulas** with required inputs, confidence rules, and worked examples
- **18 vertical signal rules** with confidence scores and required confirmation signals
- **6 vertical personas** (Medicaid Director, Public Health Officer, Child Welfare Supervisor, UI Claims Director, Eligibility Worker Supervisor, Behavioral Health Program Director)
- **14 vertical buying triggers** with urgency ratings and procurement implications
- **10 regulatory factors** (CMS 438, Streamlined Verification, SNAP QC, UI Performance, CCWIS/AFCARS, CDC DMI, SAMHSA 988, HUD PHA, Olmstead, CCDF)

### When to Use Master vs. Subpack
- **Use Master alone:** When the prospect is a general government agency with no specific health/human services program focus, or when only cross-cutting pains (cybersecurity, legacy IT, budget) are relevant.
- **Use Subpack:** When the prospect is a State Medicaid Agency, HHS department, Public Health Department, Child Welfare agency, UI agency, SNAP office, Housing Authority, Behavioral Health authority, Aging/Disability services, or Veterans benefits office. Load the subpack in addition to the master.
- **Override guidance:** If the master's generic "Enrollment/Churn Rate" KPI conflicts with the subpack's granular Medicaid-specific churn segmentation, use the subpack definition. If the master's "Legacy System" pain overlaps with PH-PAIN-013 (MMIS EOL), merge both — the subpack adds CMS MITA and procurement timing specifics.

---

## 5. Structured Output Template

The following JSON structure should be used when enriching a prospect/account with Signals Analysis using this subpack:

```json
{
  "skill_loaded": "public-health-human-services-subpack-v1.0.0",
  "parent_master": "public-sector-master-v1",
  "enrichment_timestamp": "2026-04-25T00:00:00Z",
  "prospect": {
    "agency_name": "string",
    "state_or_locality": "string",
    "sub_segments": ["Medicaid", "SNAP", "Child Welfare", "UI", "Public Health", "Behavioral Health", "Housing", "Aging/Disability", "Veterans", "Disease Surveillance"]
  },
  "signals_detected": [
    {
      "signal_rule_id": "PH-SIG-XXX",
      "signal_name": "string",
      "raw_source": {
        "source_id": "string",
        "source_type": "federal_agency_data | state_agency_data | audit_report | grant_document | news | procurement_notice | workforce_data | court_document",
        "capture_date": "YYYY-MM-DD",
        "raw_metric_value": "number | string",
        "raw_metric_unit": "string",
        "geographic_scope": "string"
      },
      "confidence_score": 0.0,
      "interpreted_meaning": "string",
      "linked_pain_ids": ["PH-PAIN-XXX"],
      "linked_kpi_ids": ["PH-KPI-XXX"],
      "linked_value_driver_ids": ["PH-VD-XXX"],
      "affected_persona_ids": ["PH-PERS-XXX"],
      "financial_implication": {
        "value_category": "Cost Savings | Risk Reduction | Mission Effectiveness | Revenue Uplift | Working Capital",
        "annual_value_estimate_usd": 0,
        "value_range_low": 0,
        "value_range_high": 0,
        "confidence": "HIGH | MEDIUM | LOW",
        "confidence_rationale": "string",
        "formula_id": "PH-VF-XXX"
      },
      "recommended_action": "string",
      "required_confirmation_signals": ["string"]
    }
  ],
  "pains_summary": [
    {
      "pain_id": "PH-PAIN-XXX",
      "pain_name": "string",
      "prevalence": "HIGH | MEDIUM | LOW",
      "confidence": "HIGH | MEDIUM | LOW",
      "affected_sub_segments": ["string"],
      "linked_value_drivers": ["string"]
    }
  ],
  "kpis_baseline": [
    {
      "kpi_id": "PH-KPI-XXX",
      "kpi_name": "string",
      "baseline_value": 0,
      "baseline_unit": "string",
      "benchmark_range": "string",
      "gap_to_benchmark": "string",
      "calculation_frequency": "string"
    }
  ],
  "value_hypotheses": [
    {
      "formula_id": "PH-VF-XXX",
      "formula_name": "string",
      "annual_value_estimate_usd": 0,
      "value_range_low": 0,
      "value_range_high": 0,
      "confidence": "HIGH | MEDIUM | LOW",
      "required_inputs_status": {
        "input_name": "AVAILABLE | MISSING | ESTIMATED"
      },
      "applicable_sub_segments": ["string"]
    }
  ],
  "buying_triggers": [
    {
      "trigger_id": "PH-TRIG-XXX",
      "trigger_event": "string",
      "urgency": "CRITICAL | HIGH | MEDIUM",
      "typical_timing": "string",
      "procurement_implications": "string"
    }
  ],
  "personas_engaged": [
    {
      "persona_id": "PH-PERS-XXX",
      "persona_name": "string",
      "seniority": "string",
      "decision_influence": "string",
      "key_pressures": ["string"],
      "trusted_evidence": ["string"]
    }
  ],
  "governance": {
    "overall_confidence": "HIGH | MEDIUM | LOW",
    "source_coverage": "mixed | high | medium | low",
    "customer_facing_approved": false,
    "review_owner": "Vertical Subpack Architect — Public Health & Human Services",
    "last_updated": "2026-04-25",
    "validation_required": "Requires validation with live prospects before external use"
  }
}
```

---

## 6. Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | Medium |
| **Source Coverage** | Mixed (CMS T-MSIS/MSIS/CMS-64, KFF, USDA SNAP QC/FNS, DOL ETA 901/902, HHS ACF AFCARS/NCANDS, CDC DMI/ELR/NNDSS, SAMHSA, HUD VMS/Picture/PHA, MACPAC, NASCIO, APHSA, GAO, OMB PaymentAccuracy.gov, CLASP, AIRA, ONC) |
| **Customer-Facing Approval Status** | No — requires validation with live prospects before external use |
| **Review Owner** | Vertical Subpack Architect — Public Health & Human Services |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-elevated-swarm-phhs |
| **Parent Master Swarm ID** | kimi-k2.6-elevated-swarm |

---

## 7. Quick Reference

### Top 5 Pains

| Rank | Pain ID | Pain Name | Prevalence | Key Value Driver |
|------|---------|-----------|------------|------------------|
| 1 | PH-PAIN-001 | Medicaid Eligibility Redetermination Backlog >90 Days | HIGH | Cost Savings, Mission Effectiveness, Risk Reduction |
| 2 | PH-PAIN-002 | SNAP Error Rate >6% | HIGH | Cost Savings, Risk Reduction |
| 3 | PH-PAIN-003 | Child Welfare Case Management Data Fragmentation | HIGH | Risk Reduction, Mission Effectiveness, Cost Savings |
| 4 | PH-PAIN-004 | Unemployment Insurance Claims Backlog and Fraud Surge | HIGH | Cost Savings, Risk Reduction, Working Capital |
| 5 | PH-PAIN-005 | Public Health Disease Surveillance Data Latency | HIGH | Risk Reduction, Mission Effectiveness |

### Top 5 KPIs

| Rank | KPI ID | KPI Name | Benchmark | Unit |
|------|--------|----------|-----------|------|
| 1 | PH-KPI-001 | Medicaid Eligibility Determination Time | <30 days (best practice) | Days |
| 2 | PH-KPI-003 | Medicaid Churn Rate | <10% (best practice) | Percentage |
| 3 | PH-KPI-004 | SNAP QC Error Rate | <6% (USDA threshold) | Percentage |
| 4 | PH-KPI-010 | UI Improper Payment Rate | <10% (federal target) | Percentage |
| 5 | PH-KPI-012 | Notifiable Disease Reporting Timeliness | >90% (CDC target) | Percentage |

### Top 3 Personas

| Rank | Persona ID | Persona Name | Seniority | Primary Decision Influence |
|------|------------|--------------|-----------|---------------------------|
| 1 | PH-PERS-001 | Medicaid Director / State Medicaid Director (SMD) | Executive / Cabinet-level | Economic (budget, federal matching, state share) |
| 2 | PH-PERS-002 | Public Health Officer / State Epidemiologist | Department Head / Appointed | Technical (data, surveillance, interoperability) |
| 3 | PH-PERS-005 | Eligibility Worker Supervisor | Mid-level Supervisor | User (frontline operations, worker wellbeing, service quality) |

### Key Value Formulas

| Formula ID | Name | Example Output |
|------------|------|----------------|
| PH-VF-001 | Medicaid Churn Cost Avoidance | $24M annual (example) |
| PH-VF-002 | Ex Parte Renewal Efficiency Value | $7M annual (example) |
| PH-VF-003 | SNAP Error Rate Reduction Value | $11M-$15M annual (example) |
| PH-VF-004 | Child Welfare Case Management Consolidation Value | $14.4M annual (example) |
| PH-VF-005 | UI Fraud and Improper Payment Reduction | $36.5M annual (example) |
| PH-VF-006 | Disease Surveillance Modernization Value | $4.8M annual (example) |

---

## 8. File Manifest

| File | Purpose |
|------|---------|
| `value-pack.json` | Structured pack data (pains, KPIs, formulas, benchmarks, signals, governance) |
| `value-pack.md` | Human-readable pack documentation with full detail |
| `signals-examples.ts` | TypeScript signal interpretation examples demonstrating mapping from raw signals to financial outcomes |
| `SKILL.md` | This file — OpenClaw-compatible skill definition for agent loading |

---

*End of SKILL.md for Public Health and Human Services Subpack (S5.4)*
*Packaged by Skills Packaging Agent — Kimi K2.6 Elevated Agent Swarm*
