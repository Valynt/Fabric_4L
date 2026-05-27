# OpenClaw SKILL.md — Federal Government Subpack (S5.1)

## 1. Skill Identity Block

| Field | Value |
|---|---|
| **skill_name** | Federal Government Subpack (S5.1) |
| **description** | Vertical-specialized value pack for the U.S. Federal Government segment covering defense, intelligence, homeland security, civilian agencies, Treasury/IRS, HHS, VA, transportation, energy, and space/research. Provides federal-specific pains, KPIs, formulas, benchmarks, signal rules, personas, discovery questions, objections, technology systems, regulatory factors, worked examples, and buying triggers. |
| **version** | 1.0.0 |
| **domain** | Public Sector — Federal Government |
| **pack_type** | subpack |
| **parent_master** | public-sector-master-v1 |

---

## 2. Triggers

The following natural-language query patterns should auto-load this skill:

1. "FedRAMP ATO timeline"
2. "RMF authorization bottleneck"
3. "CMMC compliance gap"
4. "legacy O&M budget drain"
5. "VA claims backlog"
6. "1102 contracting officer workforce crisis"
7. "continuing resolution planning paralysis"
8. "FITARA scorecard remediation"
9. "Section 508 accessibility settlement risk"
10. "EIS network transition delay"
11. "ITAR export control compliance burden"
12. "federal contract closeout backlog"

---

## 3. Reasoning Flow

### Step 1: Load Parent Master First
Before applying this subpack, ensure the **public-sector-master-v1** master skill is loaded. The master provides base value drivers, persona archetypes, evidence taxonomy, formula templates, signal source taxonomy, benchmark methodology, governance framework, and base pains/KPIs/signal rules/triggers. This subpack extends and overrides select components for the federal vertical.

### Step 2: Identify Relevant Federal Signals
Scan for raw signal patterns that map to federal-specific pains. Key signal sources include:
- **OMB FITARA scorecard** (quarterly civilian agency IT governance scores)
- **GAO reports** (High Risk List, IT assessments, bid protest data)
- **FedRAMP PMO reports** (authorization timelines, marketplace inventory)
- **DoD CMMC / SPRSSP data** (defense contractor cybersecurity readiness)
- **FPDS / USASpending.gov** (procurement timelines, obligation timing, small business achievement)
- **Agency OIG reports** (repeat findings, compliance gaps)
- **CISA BODs and alerts** (binding operational directives)
- **NARA records management reports** (electronic records compliance)
- **Agency-specific dashboards** (VBA performance, IRS customer service metrics)

Apply the **18 Federal Signal Rules (FED-SIG-001 through FED-SIG-018)** to interpret raw signals into structured pain hypotheses.

### Step 3: Map Signals to Pains, Personas, and KPIs
For each confirmed signal:
- **Link to Pain**: Use the `linkedPains` field on the signal rule to identify the relevant federal pain (FED-PAIN-001 through FED-PAIN-018).
- **Link to Persona**: Use the `affectedPersonas` on the pain to determine which federal personas are involved (FED-PERS-001 through FED-PERS-006, plus inherited PS-PERS-xxx).
- **Link to KPI**: Use the `linkedKPIs` on the pain to identify quantifiable metrics that validate severity.
- **Link to Value Driver**: Use the value driver definitions to categorize the opportunity (Cost Savings, Risk Reduction, Working Capital, Mission Effectiveness, Revenue Uplift).

### Step 4: Validate with Discovery Questions
Deploy the **18 Federal Discovery Questions (FED-DQ-001 through FED-DQ-018)** to confirm signals with the target persona. Each question is mapped to a specific pain and includes an expected signal threshold and confidence level.

### Step 5: Calculate Value Hypotheses
Apply the **14 Federal Value Formulas (FED-VF-001 through FED-VF-014)** to translate confirmed pains into quantified value hypotheses. Formulas cover:
- RMF ATO acceleration
- FedRAMP authorization portfolio value
- Continuing resolution efficiency loss
- CMMC compliance cost avoidance
- 1102 workforce productivity recovery
- ITAR compliance efficiency
- Grant deobligation retention
- VA claims backlog elimination
- IRS tax gap enforcement ROI
- Section 508 compliance cost avoidance
- Contract closeout acceleration
- EIS transition cost avoidance
- Congressional mandate tracking efficiency
- Small business goal achievement value

### Step 6: Confidence Scoring Guidance
Score each analysis using the following rubric:

| Confidence Level | Criteria |
|---|---|
| **HIGH (0.85–1.0)** | Multiple confirming signals from primary sources (eMASS, FPDS, OIG, agency dashboards); pain symptoms present; persona confirmed; discovery question thresholds met |
| **MEDIUM (0.60–0.84)** | One strong signal + secondary confirmation; some data gaps; reliance on industry benchmarks or agency averages |
| **LOW (0.40–0.59)** | Single weak signal; significant data gaps; inferred from proxy indicators; requires live validation |
| **REJECT (<0.40)** | Signal contradicted by evidence; pain not applicable to segment; persona mismatch |

Confidence score for each signal rule is pre-calculated in the pack (range: 0.80–0.92). Adjust based on availability of required confirmation signals.

### Step 7: Map to Buying Triggers and Procurement Timing
Overlay the **15 Federal Buying Triggers (FED-TRIG-001 through FED-TRIG-015)** to determine urgency and procurement pathway. Critical triggers include:
- GAO High Risk List updates (30–90 day response window)
- CISA Binding Operational Directives (30–180 day compliance deadlines)
- OMB FITARA scorecard release (30–60 day remediation window)
- CMMC rule effective dates (6–18 month horizon)
- Congressional hearings / OIG reports with management commitments (30–90 day windows)
- Contract recompetes / option declines (12–24 month capture cycles)

---

## 4. Inheritance Map

### Master Skill to Load First
**public-sector-master-v1** must be loaded before this subpack. It provides the foundational framework:
- Value Driver Framework (PS-VD-001 through PS-VD-025)
- Base Persona Archetypes (PS-PERS-001 through PS-PERS-014)
- Evidence Source Taxonomy (PS-EVID-001 through PS-EVID-015)
- Formula Templates (structural patterns)
- Signal Source Taxonomy (raw signal categories)
- Benchmark Methodology (sourcing, confidence grading, range derivation)
- Governance Framework (approval, review, swarm ID hierarchy)
- Base Pains (PS-PAIN-001 through PS-PAIN-025)
- Base KPIs (PS-KPI-001 through PS-KPI-040)
- Base Signal Rules (PS-SIG-001 through PS-SIG-030)
- Base Buying Triggers (PS-TRIG-001 through PS-TRIG-025)

### What This Subpack Adds Beyond the Master
| Category | Master Base | Federal Subpack Addition |
|---|---|---|
| **Pains** | 25 public-sector base pains | 18 federal-specific pains (FED-PAIN-001–018) |
| **KPIs** | 40 public-sector base KPIs | 22 federal-specific KPIs (FED-KPI-001–022) |
| **Signal Rules** | 30 base signal rules | 18 federal signal rules (FED-SIG-001–018) |
| **Personas** | 14 base personas | 6 federal personas (FED-PERS-001–006) |
| **Formulas** | Structural templates | 14 federal value formulas (FED-VF-001–014) |
| **Benchmarks** | Methodology only | 18 federal benchmarks (FED-BENCH-001–018) |
| **Regulatory Factors** | Generic public-sector | 12 federal regulations (FED-REG-001–012) |
| **Technology Systems** | Generic public-sector | 15 federal systems (FED-TECH-001–015) |
| **Discovery Questions** | Generic public-sector | 18 federal questions (FED-DQ-001–018) |
| **Objections** | Generic public-sector | 10 federal objection patterns (FED-OBJ-001–010) |
| **Worked Examples** | None | 3 federal worked examples (FED-EX-001–003) |
| **Buying Triggers** | 25 base triggers | 15 federal triggers (FED-TRIG-001–015) |

### Overridden Components
| Component | Override Reason |
|---|---|
| Procurement Cycle Time Benchmark | Federal acquisition cycle has unique DFARS/FAR clauses, DAU requirements, and protest pathways (GAO vs COFC). Federal IT procurement median is 210 days vs. state median ~120 days. |
| Cybersecurity Compliance Framework | Federal agencies operate under FISMA, OMB M-22-09 Zero Trust mandates, CISA BODs, and agency-specific ISSO/ISSM structures. State/local use NIST CSF voluntarily. Regulatory drivers and roles differ materially. |
| Cloud Migration Complexity Pain | Federal cloud migration is gated by FedRAMP ATO (typically 12–18 months), agency-specific Cloud Smart strategies, and CSP selection constraints. Cost overrun patterns differ from state/local. |

### When to Use Master vs. Subpack
- **Use master alone** when analyzing a generic public-sector prospect with no identifiable federal, state, or local vertical orientation.
- **Use this subpack** when the prospect is a U.S. federal agency (civilian or defense), a federal contractor/subcontractor, or a vendor selling into the federal market via FedRAMP, GSA Schedule, or FAR-based vehicles.
- **Do not use this subpack** for state/local government, K-12, or higher-education prospects — those require their own subpacks.

---

## 5. Structured Output Template

The following JSON structure is the expected output format for Signals Analysis enrichment when this skill is applied:

```json
{
  "skill_loaded": "federal-v1",
  "parent_master": "public-sector-master-v1",
  "analysis_timestamp": "2026-04-25T00:00:00Z",
  "prospect_segment": "DoD / Civilian / IC / VA / Treasury / HHS / etc.",
  "confidence_summary": {
    "overall_score": 0.0,
    "method": "weighted_average_of_signal_confidences",
    "data_quality": "HIGH | MEDIUM | LOW"
  },
  "signals_detected": [
    {
      "signal_id": "FED-SIG-001",
      "signal_name": "RMF ATO Delay Signal",
      "raw_pattern": "eMASS package status unchanged >90 days; POA&M items aging >120 days",
      "confidence": 0.88,
      "confirmation_status": "confirmed | partial | unconfirmed",
      "linked_pain": {
        "pain_id": "FED-PAIN-001",
        "pain_name": "ATO Timeline Exceeding 18 Months"
      },
      "linked_kpis": ["FED-KPI-001", "FED-KPI-013"],
      "linked_personas": ["FED-PERS-003", "FED-PERS-002", "FED-PERS-001"],
      "value_driver_category": "Risk Reduction + Working Capital",
      "required_evidence": ["eMASS status report", "POA&M age analysis", "ISSO staffing plan", "SCA availability schedule"],
      "evidence_status": "available | requested | missing"
    }
  ],
  "pains_validated": [
    {
      "pain_id": "FED-PAIN-001",
      "pain_name": "ATO Timeline Exceeding 18 Months",
      "prevalence": "HIGH",
      "confidence": "HIGH",
      "symptoms_present": ["RMF Step 1 initiation >6 months old with no SAP", "POA&M items >90 days open"],
      "segment_applicability": ["All Federal Agencies"],
      "linked_value_drivers": ["Risk Reduction", "Working Capital", "Mission Effectiveness"]
    }
  ],
  "kpis_measured": [
    {
      "kpi_id": "FED-KPI-001",
      "kpi_name": "RMF ATO Timeline (Months)",
      "value": 24,
      "unit": "Months",
      "benchmark_range": "Best practice: <12 months; concerning: >18 months",
      "status": "above_concern_threshold",
      "value_driver_links": ["Risk Reduction", "Working Capital", "Mission Effectiveness"]
    }
  ],
  "personas_engaged": [
    {
      "persona_id": "FED-PERS-003",
      "persona_name": "ISSO / ISSM",
      "relevance_score": 0.95,
      "communication_preferences": "STIG-aligned configurations; NIST control mapping; POA&M automation; eMASS integration APIs",
      "budget_influence": "System-level security ($500K–$10M)"
    }
  ],
  "value_hypotheses": [
    {
      "formula_id": "FED-VF-001",
      "formula_name": "RMF ATO Acceleration Value",
      "inputs": {
        "baseline_ato_months": 24,
        "target_ato_months": 12,
        "program_delay_cost_per_month": 500000,
        "avoided_interim_ato_risk_cost": 2000000
      },
      "calculated_value": 8000000,
      "output_unit": "USD (3-year NPV)",
      "confidence": "HIGH",
      "applicable_segments": ["All Federal Agencies"]
    }
  ],
  "buying_triggers_active": [
    {
      "trigger_id": "FED-TRIG-002",
      "trigger_name": "OMB FITARA Scorecard Release",
      "urgency_level": "HIGH",
      "typical_timing": "30-60 days post-scorecard",
      "procurement_implications": "CIO-driven remediation procurements; data center consolidation contracts; working capital fund requests; modernization SOWs"
    }
  ],
  "discovery_questions_recommended": [
    {
      "question_id": "FED-DQ-001",
      "question": "What is your current RMF timeline from categorization to ATO, and how many systems are on interim ATO exceeding 12 months?",
      "target_persona": "FED-PERS-003",
      "expected_signal": "RMF timeline >18 months or interim ATO >12 months indicates ATO bottleneck",
      "category": "Security / Compliance"
    }
  ],
  "objections_anticipated": [
    {
      "objection_id": "FED-OBJ-003",
      "objection": "FedRAMP authorization is a prerequisite, and you don't have it yet.",
      "linked_pain": "FED-PAIN-004",
      "linked_persona": "FED-PERS-003",
      "response_strategy": "Propose agency-sponsored FedRAMP Fast Track (target 6-9 months); offer on-prem or hybrid deployment as interim path; reference FedRAMP-ready or In Process status; suggest sponsor engagement letter."
    }
  ],
  "regulatory_factors_relevant": [
    {
      "reg_id": "FED-REG-001",
      "reg_name": "Federal Information Security Modernization Act (FISMA)",
      "authority": "44 U.S.C. § 3551 et seq.; OMB M-17-25, M-21-31, M-22-09",
      "violation_penalties": "OIG findings; congressional oversight; budget restrictions; potential criminal liability for willful concealment"
    }
  ],
  "governance": {
    "source_coverage": "Mixed (GAO reports, OMB data, agency OIG, FedRAMP PMO, DoD CMMC, FPDS, SBA, NARA)",
    "confidence": "High",
    "approved_for_customer_facing": false,
    "review_owner": "Federal Subpack Architect — Vertical Intelligence Swarm",
    "last_updated": "2026-04-25"
  }
}
```

---

## 6. Governance Metadata

| Attribute | Value |
|---|---|
| **Confidence Level** | High |
| **Source Coverage** | Mixed (GAO reports, OMB data, agency OIG, FedRAMP PMO, DoD CMMC, FPDS, SBA, NARA) |
| **Customer-Facing Approval Status** | No — requires validation with live prospects |
| **Review Owner** | Federal Subpack Architect — Vertical Intelligence Swarm |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-elevated-swarm-federal |
| **Parent Master Swarm ID** | kimi-k2.6-elevated-swarm |

---

## 7. Quick Reference

### Top 5 Pains

| ID | Pain | Prevalence | Key Segments |
|---|---|---|---|
| **FED-PAIN-001** | ATO Timeline Exceeding 18 Months | HIGH | All Federal Agencies |
| **FED-PAIN-002** | Legacy O&M Consuming >70% of IT Budget | HIGH | DoD, Treasury, VA, HHS, DHS, Justice |
| **FED-PAIN-003** | Continuing Resolution Planning Paralysis | HIGH | All Federal Civilian, DoD |
| **FED-PAIN-004** | FedRAMP ATO Bottleneck for SaaS/PaaS | HIGH | All Federal Agencies |
| **FED-PAIN-005** | CMMC / DFARS Compliance Gap (DIB) | HIGH | DoD, Intelligence Community, DHS |

### Top 5 KPIs

| ID | KPI | Benchmark | Value Drivers |
|---|---|---|---|
| **FED-KPI-001** | RMF ATO Timeline (Months) | Concerning: >18 months | Risk Reduction, Working Capital, Mission Effectiveness |
| **FED-KPI-003** | FITARA Score (OMB Quarterly) | Failing: <50; Target: >80 | Cost Savings, Risk Reduction, Mission Effectiveness |
| **FED-KPI-004** | CMMC / NIST SP 800-171 Compliance Score | CMMC Level 2: 100% | Risk Reduction, Working Capital |
| **FED-KPI-009** | FedRAMP ATO Time (Months) | Concerning: >18 months | Risk Reduction, Cost Savings, Mission Effectiveness |
| **FED-KPI-014** | Obligation Rate by Quarter (Q4 Surge Index) | Concerning: >45% | Working Capital, Cost Savings |

### Top 3 Personas

| ID | Persona | Grade / Series | Budget Influence |
|---|---|---|---|
| **FED-PERS-002** | CIO (Civilian Agency) | SES or GS-15 (2210) | Enterprise IT ($50M–$2B) |
| **FED-PERS-003** | ISSO / ISSM | GS-13 to GS-15 (2210) | System-level security ($500K–$10M) |
| **FED-PERS-004** | Contracting Officer (KO) | GS-12 to GS-15 (1102) | Contract level ($1M–$500M) |

### Key Value Formulas

| ID | Formula | Example Output |
|---|---|---|
| **FED-VF-001** | RMF ATO Acceleration Value: `V = (Baseline_ATO_Months - Target_ATO_Months) * Program_Delay_Cost_Per_Month + Avoided_Interim_ATO_Risk_Cost` | $8M (3-year NPV) |
| **FED-VF-002** | FedRAMP Authorization Portfolio Value: `V = (Avoided_Agency_ATO_Effort_Per_CSP * CSPs_Authorized) + Shadow_IT_Risk_Avoidance + SaaS_Adoption_Value` | $3.75M (annual) |
| **FED-VF-004** | CMMC Compliance Cost Avoidance: `V = (Baseline_Compliance_Cost - Target_Compliance_Cost) * Number_of_Affected_Contracts + Avoided_Debarment_Risk_Value` | $8.5M (annual) |
| **FED-VF-008** | VA Claims Processing Backlog Elimination: `V = (Baseline_Backlog - Target_Backlog) * Cost_Per_Claim + Overtime_Avoidance + Error_Rate_Reduction_Value + Veteran_Satisfaction_Value` | $50M (annual) |
| **FED-VF-009** | IRS Tax Gap Enforcement ROI: `V = (Additional_Enforcement_Revenue - Enforcement_Cost_Increase) + Customer_Service_Improvement_Value + Paper_Processing_Reduction_Savings` | $45M (annual) |

---

*End of SKILL.md — Federal Government Subpack (S5.1)*
