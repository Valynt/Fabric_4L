# Healthcare Operations Subpack (S3.4)

## 1. Skill Identity Block

- **skill_name:** Healthcare Operations Subpack
- **description:** Vertical-specialized value intelligence for Healthcare Operations functions including revenue cycle, claims processing, patient access, prior authorization, clinical documentation, care coordination, workforce management, supply chain, pharmacy operations, quality reporting, and credentialing. Provides operational-level KPIs, role-specific personas, function-level benchmarks, and signal rules tuned for directors and managers running healthcare operational workflows.
- **version:** 1.0.0
- **domain:** Healthcare
- **pack_type:** subpack
- **parent_master:** healthcare-master-v1

---

## 2. Triggers

Auto-load this skill when queries match any of these patterns:

1. **Revenue cycle denial reduction** — "reduce claim denials," "denial rate above benchmark," "revenue cycle optimization"
2. **Prior authorization automation** — "prior auth automation," "PA turnaround too long," "ePA integration," "reduce PA burden"
3. **Clinical documentation improvement** — "CDI program," "query response rate," "CMI improvement," "CC/MCC capture"
4. **340B compliance optimization** — "340B savings leakage," "HRSA audit readiness," "contract pharmacy reconciliation," "duplicate discount exposure"
5. **Workforce float pool management** — "nurse scheduling optimization," "reduce overtime," "float pool utilization," "agency labor reduction"
6. **Claims first-pass rate improvement** — "clean claim rate," "charge lag reduction," "DNFB days," "revenue integrity"
7. **Patient access and scheduling** — "no-show reduction," "appointment wait times," "provider utilization," "scheduling efficiency"
8. **Credentialing cycle acceleration** — "credentialing backlog," "provider enrollment delays," "privileging turnaround," "payer panel effective date"
9. **Care coordination transitions** — "readmission reduction," "discharge planning," "post-acute handoffs," "7-day follow-up"
10. **Supply chain optimization** — "inventory turns," "expired product waste," "stockout reduction," "surgical supply management"
11. **Quality reporting and registry submission** — "eCQM submission," "MIPS penalty avoidance," "HEDIS measures," "registry backlog"
12. **Patient financial responsibility collection** — "point-of-service collections," "patient A/R aging," "bad debt reduction," "price transparency"

---

## 3. Reasoning Flow

### Step 1: Identify Relevant Signals
Scan for operational buying signals tied to function-level activity:
- **Signal Rules (OS001-OS020):** Function-specific signals like RCM job posting surges, PA vendor searches, CDI platform RFPs, credentialing system upgrades, workforce management RFPs, and 340B restructuring events.
- **Signal Confidence:** Each signal has a confidence score (0.75-0.88). Require 1-2 confirmation signals before elevating to HIGH confidence.
- **Master Pack Context:** Cross-reference enterprise signals (C-suite changes, bond downgrades, M&A) from healthcare-master-v1 to understand organizational urgency backdrop.

### Step 2: Map Signals to Pains
Apply the 20 operational pain definitions (OP001-OP020):
- Match signal patterns to pain symptoms using linkedKPIs and affectedPersonas.
- Example: OS001 (RCM job posting surge) → OP001 (denial rate >12%) or OP008 (clean claim rate <90%).
- Score pain prevalence: HIGH (denials, PA, CDI, no-shows, workforce, care coordination) vs. MEDIUM (credentialing, supply chain, 340B, quality reporting, lab, audits).

### Step 3: Decompose into Operational KPIs
Use the 25 function-level KPIs (OK001-OK060) to quantify pain severity:
- Compare current state vs. benchmark ranges documented in the pack.
- Flag metrics outside "best practice" thresholds as crisis indicators.
- Example: Denial rate >12% vs. benchmark <8%; PA turnaround >72h vs. benchmark <48h.

### Step 4: Link to Value Drivers and Financial Outcomes
Map pains/KPIs to 40 value drivers (OV001-OV040) across four outcome categories:
- **Revenue Uplift:** Denial reduction, PA automation, CMI improvement, 340B capture, referral leakage recovery, under-coding recovery.
- **Cost Savings:** Supply chain optimization, workforce float pool efficiency, HIM productivity, formulary adherence, PA staff burden reduction.
- **Risk Reduction:** HIM audit defense, 340B compliance, external audit appeal success, care transition readmission avoidance, lab quality gaps.
- **Working Capital / Cash Flow:** DNFB reduction, clean claim improvement, POS collection, charge lag reduction, eligibility verification automation.

### Step 5: Identify Primary Personas
Reference the 6 operational personas (OPER001-OPER006):
- Revenue Cycle Director (economic buyer)
- CDI Manager (technical influencer)
- HIM Director (technical influencer)
- Care Coordinator (user/influencer)
- Credentialing Specialist (technical influencer)
- Pharmacy Operations Manager (technical influencer)

### Step 6: Build Value Hypothesis with Formulas
Apply the 15 financially quantified formulas (OF001-OF015):
- Use organization-specific inputs where available; fall back to industry benchmarks with MEDIUM confidence flag.
- Example formula: Denial Reduction = (Current Rate − Target Rate) × Gross Charges × (1 − Contractual %) × Collectible % − Implementation Cost.
- Cross-check against worked examples (OWE001-OWE003) for validation.

### Step 7: Confidence Scoring Guidance
- **HIGH (0.85-1.0):** Multiple corroborating signals + organization-specific KPI data + direct regulatory/financial reporting.
- **MEDIUM (0.70-0.84):** Single strong signal + industry survey benchmarks + partial quantification.
- **LOW (<0.70):** Directional indicator only; requires discovery call validation before customer-facing use.

---

## 4. Inheritance Map

### Master Skill to Load First
**healthcare-master-v1** — This subpack inherits foundational context from the master:
- Value Driver Framework (4 outcome categories: Revenue Uplift, Cost Savings, Risk Reduction, Working Capital)
- Base Persona Archetypes (C-suite/VP level)
- Evidence Source Taxonomy and reliability flags
- Formula Templates and confidence rules
- Signal Source Taxonomy (enterprise/strategic-level)
- Benchmark Methodology
- Governance Framework (validation cycles, confidence flags, review requirements)

### What This Subpack Adds
- **20 Business Pains (OP001-OP020)** — operational-level pain definitions with function-specific symptoms
- **25 KPIs (OK001-OK060)** — frontline metrics for operations managers (denial by root cause, PA burden per physician, CC/MCC capture, DNFB days, etc.)
- **40 Value Drivers (OV001-OV040)** — signal-to-pain mappings tuned for operations workflows
- **20 Signal Rules (OS001-OS020)** — function-level buying signals (RFPs, job postings, vendor changes)
- **6 Operational Personas (OPER001-OPER006)** — Director/Manager/IC-level buyers who are primary operational decision-makers
- **15 Value Formulas (OF001-OF015)** — financially quantified improvement opportunities
- **20 Benchmarks (OB001-OB020)** — operations-specific industry benchmarks
- **12 Regulatory Factors (OREG001-OREG012)** — HIPAA, CMS CoPs, 340B, AKS/Stark, NSA, etc.
- **15 Technology Systems (OT001-OT015)** — RCM, CAC, PA automation, credentialing, supply chain, pharmacy, quality reporting
- **20 Discovery Questions (ODQ001-ODQ020)** — operations-focused qualification
- **10 Objection Patterns (OOBJ001-OOBJ010)** — specific to operations buyers
- **15 Buying Triggers (OBT001-OBT015)** — operational urgency events

### When to Use Master vs. Subpack
| Scenario | Use |
|----------|-----|
| C-suite engagement, board presentation, enterprise strategy | **Master** |
| Operational director/manager conversation, workflow pain, function-level RFP | **Subpack** |
| Enterprise financial distress + operational dysfunction | **Both** (master for context, subpack for specifics) |
| Single-function vendor evaluation (e.g., PA automation only) | **Subpack** |
| Multi-function transformation (RCM + HIM + CDI) | **Subpack with master governance** |

---

## 5. Structured Output Template

### Expected JSON Format for Signals Analysis Enrichment

```json
{
  "skill_loaded": "healthcare-operations-v1",
  "parent_master": "healthcare-master-v1",
  "analysis_timestamp": "2026-04-25T00:00:00Z",
  "prospect_context": {
    "organization_type": "hospital_system | physician_group | dsh_hospital | ambulatory_network",
    "bed_count": 0,
    "physician_count": 0,
    "annual_npr_usd": 0
  },
  "signals_detected": [
    {
      "signal_id": "OS001",
      "signal_name": "RCM Job Posting Surge with Denials Focus",
      "raw_evidence": "string",
      "confidence": 0.85,
      "confirmation_signals": ["string"],
      "linked_pains": ["OP001", "OP008"],
      "linked_kpis": ["OK001", "OK002"],
      "urgency": "HIGH | MEDIUM | LOW"
    }
  ],
  "pains_assessed": [
    {
      "pain_id": "OP001",
      "pain_name": "Denial Rate Sustained Above 12%",
      "prevalence": "HIGH",
      "confidence": "HIGH",
      "symptoms_present": ["symptom_1", "symptom_2"],
      "affected_personas": ["Revenue Cycle Director", "HIM Director"],
      "linked_kpis": ["OK001", "OK002", "OK003"],
      "linked_value_drivers": ["OV001", "OV002"]
    }
  ],
  "kpis_evaluated": [
    {
      "kpi_id": "OK001",
      "kpi_name": "Operational Denial Rate by Root Cause",
      "current_value": 0.0,
      "unit": "%",
      "benchmark_best_practice": "<8% total; <2% per category",
      "gap_severity": "CRISIS | BELOW_BENCHMARK | AT_BENCHMARK | ABOVE_BENCHMARK"
    }
  ],
  "value_hypotheses": [
    {
      "value_driver_id": "OV001",
      "category": "Revenue Uplift | Cost Savings | Risk Reduction | Working Capital",
      "formula_id": "OF001",
      "estimated_annual_value_usd": 0,
      "confidence": "HIGH | MEDIUM | LOW",
      "key_assumptions": ["string"],
      "primary_persona": "Revenue Cycle Director",
      "discovery_questions": ["ODQ001"]
    }
  ],
  "recommended_next_steps": [
    {
      "action": "discovery_call | demo | proposal | nurture",
      "target_persona": "string",
      "priority": 1
    }
  ],
  "governance": {
    "overall_confidence": "HIGH | MEDIUM | LOW",
    "customer_facing_approved": false,
    "validation_required": [
      "Verify current benchmarks against latest HFMA/CMS/CAQH publications",
      "Confirm state-specific regulatory deadlines",
      "Validate organization-specific operational metrics before citing in proposals"
    ],
    "review_owner": "healthcare-operations-subpack-architect",
    "last_updated": "2026-04-25"
  }
}
```

---

## 6. Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | High |
| **Source Coverage** | Mixed (public filings, government data, industry surveys, proprietary benchmarks) |
| **Customer-Facing Approval Status** | No (internal intelligence asset; requires review before external use) |
| **Review Owner** | healthcare-operations-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-swarm-healthcare-ops-s3.4 |
| **Parent Master Swarm ID** | kimi-k2.6-swarm-healthcare-m3 |
| **Version** | 1.0.0 |

### Confidence Flags
- **HIGH:** Multiple corroborating sources, quantified data, direct regulatory or financial reporting
- **MEDIUM:** Industry survey data, partial quantification, or single-source but authoritative
- **LOW:** Estimates, directional indicators, or emerging trends with limited data

### Validation Required Before Customer Use
1. Verify current benchmarks against latest HFMA, CMS, CAQH, and ACDIS publications
2. Confirm state-specific regulatory deadlines (staffing ratios, price transparency, 340B state policies)
3. Validate organization-specific operational metrics before citing in proposals
4. Update competitor landscape quarterly (M&A, vendor consolidation, new entrants)
5. Review signal rules for false positive rate against historical conversion data
6. Test all formulas with customer-specific inputs before presenting final business case

---

## 7. Quick Reference

### Top 5 Pains (by prevalence and impact)

| ID | Pain | Prevalence | Key Symptom | Financial Impact |
|----|------|------------|-------------|------------------|
| **OP001** | Denial Rate Sustained Above 12% | HIGH | Initial denial rate >12% | ~$2-4M per % point above benchmark for 500-bed system |
| **OP002** | Prior Auth Turnaround Exceeding 72 Hours | HIGH | PA turnaround >72h | Physician practice spends ~13 hrs/week on PA (AMA) |
| **OP003** | CDI Query Response Rate Below 65% | HIGH | Query response <65% | Suppresses CMI, increases clinical validation denials |
| **OP010** | Workforce Float Pool Underutilization with Overtime Escalation | HIGH | Float pool <60% + overtime >8% | Simultaneous internal surplus and premium external spend |
| **OP008** | Claims First-Pass Rate Below 90% | HIGH | Clean claim rate <85% | Downstream denial risk, delayed payment, inflated cost-to-collect |

### Top 5 KPIs (most commonly referenced)

| ID | KPI | Benchmark | Typical Range | Unit |
|----|-----|-----------|---------------|------|
| **OK001** | Operational Denial Rate by Root Cause | <8% total; <2% per category | 3-15% | % |
| **OK004** | PA Electronic Submission Rate | >80% | 30-75% | % |
| **OK007** | CDI Physician Query Response Rate | >75% | 55-85% | % |
| **OK008** | CC/MCC Capture Rate | >92% | 85-96% | % |
| **OK022** | Clean Claim Rate (Pre-Submission) | >88% | 75-92% | % |

### Top 3 Personas (most frequently affected)

| ID | Persona | Seniority | Influence | Top Goals |
|----|---------|-----------|-----------|-----------|
| **OPER001** | Revenue Cycle Director | Director / Senior Director | Economic | Denial rate <8%, A/R days <40, clean claim rate >92% |
| **OPER002** | CDI Manager | Manager / Senior Manager | Technical | Query response >75%, CC/MCC capture >92%, retrospective queries <15% |
| **OPER003** | HIM Director | Director | Technical | Coding backlog <3 days DNFB, chart completion >90%, coder productivity >18 charts/day |

### Key Value Formulas

| ID | Formula | Example Output | Primary Inputs |
|----|---------|----------------|----------------|
| **OF001** | Denial Reduction Operating Value | $11.7M annually | Current/target denial rate, gross charges, contractual %, collectible % |
| **OF002** | Prior Authorization Automation Value | $12.36M annually | Staff hours saved, abandonment reduction, appeal reduction |
| **OF003** | CDI Revenue Recovery Value | $11.19M annually | CMI improvement, discharges, base rate, denial avoidance |
| **OF007** | 340B Savings Recovery Value | $4.07M annually | Uncaptured claims, WAC discount, duplicate discount avoidance |
| **OF011** | Workforce Float Pool and Overtime Reduction | $2.72M annually | Overtime reduction, agency replacement, call-in reduction |

---

*This subpack is a vertical specialization of the Healthcare Master ValuePack (healthcare-master-v1). It must not be used independently without reference to the master pack for foundational context, taxonomy, and governance framework.*
