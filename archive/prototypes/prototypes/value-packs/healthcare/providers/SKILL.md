# SKILL.md — Providers / Care Delivery Subpack (S3.1)

---

## Skill Identity Block

| Field | Value |
|-------|-------|
| `skill_name` | Providers / Care Delivery ValuePack |
| `description` | Vertical-specialized value intelligence for care delivery organizations: hospitals, academic medical centers, ambulatory and primary/specialty care, urgent/emergency care, surgery centers, behavioral health, home health, hospice, telehealth, and rural/community health. Provides machine-parseable definitions of operational, clinical, and financial pain points, quantified KPIs, signal rules, persona profiles, value formulas, benchmarks, discovery frameworks, and objection handling specific to provider settings. |
| `version` | 1.0.0 |
| `domain` | healthcare |
| `pack_type` | subpack |
| `parent_master` | healthcare-master-v1 |

---

## Triggers

Auto-load this skill when queries match any of the following natural-language patterns:

1. "hospital ED boarding" — Emergency department throughput, diversion, LWBS, or capacity crisis
2. "OR throughput optimization" — Surgical services first-case delays, block utilization, turnover, or PACU holds
3. "clinic no-show reduction" — Outpatient access failure, scheduling backlog, or provider productivity gaps
4. "telehealth platform scaling" — Virtual care completion rates, technical failure, or provider adoption barriers
5. "rural hospital closure risk" — Critical Access Hospital distress, swing bed underutilization, or ED closure threat
6. "ICU step-down bottleneck" — Capacity stranding, ED holds awaiting ICU, or bed management failure
7. "home health readmission penalty" — HHVBP risk, post-acute transition failure, or OASIS quality gaps
8. "behavioral health ED boarding" — Psychiatric patient holds > 24h, EMTALA risk, or BH capacity crisis
9. "ASC reimbursement compression" — Ambulatory Surgery Center margin decline, supply cost overrun, or CON pressure
10. "sepsis bundle compliance" — SEP-1 performance, CMS HACRP penalty, or infection prevention gaps
11. "FQHC productivity gap" — HRSA UDS underperformance, sliding fee enrollment, or grant compliance risk
12. "nurse manager burnout cascade" — Span-of-control crisis, unit turnover, or leadership vacuum

---

## Reasoning Flow

### Step 1: Prospect / Account Segmentation
Identify which care delivery sub-segments apply to the target organization. This subpack covers:
- Hospitals and Health Systems (including AMCs and Critical Access Hospitals)
- Ambulatory Care / Clinics (primary, specialty, urgent care, FQHCs)
- Surgery Centers (hospital ORs and ASCs)
- Post-Acute & Community (home health, hospice, swing beds, SNF networks)
- Behavioral Health (inpatient, outpatient, PHP/IOP)
- Telehealth Platforms (standalone or embedded)

> **Inheritance Note:** Always load `healthcare-master-v1` first to establish baseline regulatory context (CMS, Joint Commission, HIPAA), base persona archetypes (CFO, COO, CMO, CNO, CIO, CISO), and master-level value formulas (denial reduction, LOS reduction, turnover cost avoidance). Then apply this subpack to overlay provider-specific operational and clinical signals.

### Step 2: Signal Detection & Relevance Scoring
Scan for raw signals and map them to the 20 signal rules (PROV-S001 to PROV-S020). Each signal carries a confidence score (0.80–0.95). Prioritize signals with:
- **CRITICAL buying triggers** (CMS CoP citation, Joint Commission conditional, ED diversion mandate, rural hospital distress)
- **HIGH confidence scores** (>0.90)
- **Multiple linked pains** (cross-functional impact)

**Confidence Scoring Guidance:**
- **HIGH (≥0.90):** Regulatory citations, public CMS data, sentinel events, sustained operational metrics (>5 days). Proceed with direct outreach.
- **MEDIUM (0.85–0.89):** Industry survey patterns, 90-day trend shifts, single-source audit findings. Require 1–2 confirmation signals before high-confidence engagement.
- **LOW (<0.85):** RFP activity, leadership changes, directional indicators. Use as conversation openers; validate with discovery questions.

### Step 3: Pain Identification
For each confirmed signal, map to the 20 vertical pains (PROV-P001 to PROV-P020). Key pain categories:
- **Flow & Throughput:** ED boarding (P001), OR delays (P002), ICU step-down (P004), patient access backlog (P015)
- **Revenue & Margin:** Clinic no-shows (P003), ASC compression (P008), anesthesia leakage (P017), hospice LOS (P009)
- **Post-Acute & Community:** Home health readmissions (P005), swing bed underutilization (P007), SNF fragmentation (P018)
- **Quality & Safety:** Sepsis bundle (P013), CAUTI/CLABSI (P014), pharmacy compounding (P016), blood product waste (P019)
- **Workforce & Leadership:** Nurse manager burnout (P020)
- **Behavioral Health:** Psychiatric ED boarding (P010)
- **Regulatory & Compliance:** FQHC productivity (P011), telehealth failure (P006), rural closure risk (P012)

### Step 4: KPI Mapping & Benchmarking
For each identified pain, extract the linked KPIs and compare against subpack benchmarks (PROV-B001 to PROV-B018). Use benchmark ranges to quantify severity:
- **Green (at or above best practice):** Deprioritize; monitor only.
- **Yellow (typical range but below best practice):** Opportunity for optimization; moderate urgency.
- **Red (outside typical range or approaching regulatory risk):** Immediate engagement; buying trigger likely active.

### Step 5: Persona Targeting
Map pains to the most relevant personas. This subpack adds 6 provider-specific personas beyond the master set:
1. **CMIO** — EHR usability, CDS, interoperability, AI governance
2. **Nurse Manager** — Staffing ratios, turnover, nursing-sensitive quality
3. **Patient Access Director** — Scheduling, no-shows, PA, registration
4. **Bed Manager** — ED boarding, diversion, occupancy, throughput
5. **OR Director** — Block utilization, first-case starts, turnover, surgeon satisfaction
6. **Telehealth Medical Director** — Virtual care completion, reimbursement, provider adoption

Combine with master personas (CFO, COO, CMO, CNO, CIO, CHRO, CISO, VP Revenue Cycle, Chief Pharmacy Officer) for multi-threaded engagement.

### Step 6: Value Hypothesis Construction
Select the appropriate value formula (PROV-F001 to PROV-F012) based on pain + KPI combination. Every value hypothesis must tie to one of four outcome categories:
- **Revenue Uplift:** Better throughput, capture, or pricing (e.g., OR cases added, no-show recovery, swing bed days)
- **Cost Savings:** Operating expense reduction without quality degradation (e.g., ICU step-down efficiency, ED hold cost avoidance)
- **Risk Reduction:** Regulatory, legal, safety, or reputational exposure mitigation (e.g., HACRP penalty avoidance, EMTALA compliance)
- **Working Capital / Cash Flow Improvement:** Faster cash conversion (e.g., anesthesia billing capture, FQHC grant revenue)

### Step 7: Discovery & Validation
Use the 18 discovery questions (PROV-DQ001 to DQ018) to validate signal-driven hypotheses with the prospect. Sequence questions by recommended timing (Early → Middle → Late) and target persona.

### Step 8: Objection Handling
Anticipate 10 provider-specific objection patterns (PROV-OBJ001 to OBJ010). Prepare reframe strategies aligned to persona pressures and trusted evidence sources.

---

## Inheritance Map

### Master Skill to Load First
`healthcare-master-v1` — Provides:
- Regulatory baseline (CMS, HIPAA, Joint Commission, state laws)
- Base persona archetypes (C-suite, clinical, technical, financial)
- Master value formula templates
- Signal taxonomy and evidence framework
- Governance and confidence methodology

### What This Subpack Adds
| Category | Subpack Contribution |
|----------|----------------------|
| **Pains** | 20 provider-specific operational, clinical, and financial pains |
| **KPIs** | 25+ vertical KPIs with segment-specific benchmark ranges |
| **Signal Rules** | 20 vertical signal rules with confidence scoring |
| **Personas** | 6 new roles: CMIO, Nurse Manager, Patient Access Director, Bed Manager, OR Director, Telehealth Medical Director |
| **Value Formulas** | 12 provider-oriented formulas (OR throughput, ED flow, no-show recovery, swing bed capture, etc.) |
| **Benchmarks** | 18 vertical benchmarks (OR, ED, clinic, home health, hospice, behavioral health, FQHC, CAH) |
| **Buying Triggers** | 15 urgency-ranked triggers (regulatory, leadership, contractual, distress) |
| **Discovery** | 18 targeted questions by persona and pain |
| **Objections** | 10 provider-specific rebuttal frameworks |
| **Technology Systems** | 15 system categories with vendor landscapes and integration points |
| **Regulatory Factors** | 12 provider-specific regulations (CoP, HACRP, USP <797>/<800>, HHVBP, HRSA 330, etc.) |
| **Competitor Factors** | 8 market dynamics (Epic dominance, Oracle transition, Amazon/CVS entry, PE ASC chains) |

### When to Use Master vs. Subpack
| Scenario | Recommendation |
|----------|----------------|
| General healthcare industry context, payer dynamics, regulatory overview | Use **healthcare-master-v1** only |
| Specific care delivery organization (hospital, clinic, ASC, home health, telehealth, CAH, FQHC) | Load **healthcare-master-v1**, then **this subpack** |
| Payer, PBM, or life sciences prospect | Use **healthcare-master-v1** with appropriate *other* subpacks; do NOT load this providers subpack |
| Multi-segment health system (hospital + payer + pharma) | Load **healthcare-master-v1**, then **this subpack** + relevant sibling subpacks |

---

## Structured Output Template

The following JSON structure is the expected output format for a Signals Analysis enrichment using this subpack:

```json
{
  "skill_loaded": "providers-v1",
  "parent_master": "healthcare-master-v1",
  "analysis_timestamp": "2026-01-15T09:00:00Z",
  "prospect": {
    "name": "Example Health System",
    "segment": "Hospital and Health System",
    "bed_count": 320,
    "annual_ed_visits": 45000,
    "or_count": 12
  },
  "signals_detected": [
    {
      "signal_id": "PROV-S003",
      "signal_name": "ED Diversion Frequency Spike",
      "raw_evidence": "EMS dispatch log shows 62 diversion hours in past 30 days",
      "confidence": 0.91,
      "linked_pains": ["PROV-P001", "PROV-P004"],
      "linked_kpis": ["PROV-K001", "PROV-K003"],
      "buying_trigger_active": true,
      "trigger_id": "PROV-BT003",
      "urgency": "HIGH"
    }
  ],
  "pains_identified": [
    {
      "pain_id": "PROV-P001",
      "pain_name": "ED Boarding Time Exceeding 8 Hours",
      "severity": "HIGH",
      "symptoms_present": [
        "ED boarding time > 8h average",
        "LWBS rate > 4%",
        "ambulance diversion hours > 50/month"
      ],
      "affected_personas": ["COO", "CMO", "Bed Manager", "ED Director", "CNO"],
      "linked_value_drivers": ["PROV-V001", "PROV-V002"],
      "prevalence": "HIGH",
      "confidence": "HIGH"
    }
  ],
  "kpis_assessed": [
    {
      "kpi_id": "PROV-K001",
      "kpi_name": "ED Boarding Time (Decision-to-Admit to Physical Bed)",
      "current_value": 185,
      "unit": "minutes",
      "benchmark_best": 60,
      "benchmark_risk": 180,
      "status": "RED",
      "trend": "increasing"
    }
  ],
  "value_hypotheses": [
    {
      "formula_id": "PROV-F001",
      "formula_name": "ED Flow Optimization Value",
      "estimated_annual_value": 4050000,
      "currency": "USD",
      "confidence": "MEDIUM",
      "required_validation": [
        "actual ED volume and revenue data",
        "admission cost accounting"
      ],
      "value_driver_category": "Revenue Uplift"
    }
  ],
  "target_personas": [
    {
      "persona_id": "PROV-PER004",
      "persona_name": "Bed Manager",
      "relevance_score": 0.95,
      "recommended_discovery_questions": ["PROV-DQ001", "PROV-DQ004"]
    }
  ],
  "competitive_factors": [
    {
      "factor_id": "PROV-CF003",
      "factor_name": "Amazon One Medical / Clinic Entry",
      "impact": "Accelerates digital front door and same-day access competition"
    }
  ],
  "regulatory_exposure": [
    {
      "regulation_id": "PROV-REG001",
      "regulation_name": "CMS Conditions of Participation (42 CFR 482)",
      "applicable": true,
      "deadline_status": "Active survey window",
      "penalty_risk": "Termination from Medicare; CMP up to $100K"
    }
  ],
  "next_actions": [
    {
      "action": "Validate ED boarding and diversion data with prospect",
      "owner": "AE",
      "priority": 1,
      "timeline": "48 hours"
    },
    {
      "action": "Schedule Bed Manager + COO discovery call using PROV-DQ001",
      "owner": "SE",
      "priority": 2,
      "timeline": "5 business days"
    }
  ],
  "overall_confidence": 0.88,
  "customer_facing_ready": false,
  "review_required": true
}
```

---

## Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | High |
| **Source Coverage** | Mixed — public filings (CMS Hospital Compare, HH Compare, SNF Compare), government data (HRSA UDS, Flex Monitoring Team), industry surveys (MGMA DataDive, AORN, Press Ganey, OR Manager), proprietary benchmarks (Kaufman Hall, SullivanCotter), and regulatory sources (Joint Commission, CDC NHSN) |
| **Customer-Facing Approval Status** | **No** — Internal intelligence asset; requires review before external use |
| **Review Owner** | healthcare-providers-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-swarm-healthcare-providers-s3.1 |
| **Parent Master Swarm ID** | kimi-k2.6-swarm-healthcare-m3 |

### Validation Checklist (Before Customer-Facing Use)
1. Verify OR benchmarks against latest AORN and OR Manager publications
2. Confirm ED boarding benchmarks against CMS Hospital Compare and ACEP data
3. Validate clinic no-show benchmarks against MGMA DataDive specialty breakouts
4. Update state-specific regulatory deadlines (staffing ratios, CON, USP <797>/<800>)
5. Validate organization-specific financial metrics before citing in proposals
6. Review signal rules for false positive rate against historical conversion data
7. Update competitor landscape quarterly (M&A, market exits, new entrants)

### Confidence Flags
- **HIGH:** Multiple corroborating sources, quantified data, direct regulatory or financial reporting
- **MEDIUM:** Industry survey data, partial quantification, or single-source but authoritative
- **LOW:** Estimates, directional indicators, or emerging trends with limited data

---

## Quick Reference

### Top 5 Pains
| # | ID | Pain | Prevalence | Affected Personas |
|---|----|------|------------|-------------------|
| 1 | PROV-P001 | ED Boarding Time Exceeding 8 Hours | HIGH | COO, CMO, Bed Manager, ED Director, CNO |
| 2 | PROV-P002 | OR First-Case Start Delay > 20% | HIGH | OR Director, COO, CNO, CFO |
| 3 | PROV-P003 | Clinic No-Show Rate > 15% | HIGH | Patient Access Director, CMO, Nurse Manager, CFO |
| 4 | PROV-P004 | ICU Step-Down Delay and Capacity Stranding | HIGH | Bed Manager, COO, CMO, CNO, CFO |
| 5 | PROV-P010 | Behavioral Health ED Boarding > 48 Hours | HIGH | CMO, COO, CNO, VP Behavioral Health, Bed Manager |

### Top 5 KPIs
| # | ID | KPI | Best Practice Benchmark | Risk Threshold |
|---|----|-----|------------------------|----------------|
| 1 | PROV-K001 | ED Boarding Time | <60 min (community); <90 min (AMC) | >180 min (CMS CoP risk) |
| 2 | PROV-K004 | OR First-Case On-Time Start % | >80% | <60% (significant delay) |
| 3 | PROV-K007 | Clinic No-Show Rate | <8% | >15% (significant); >20% (BH crisis) |
| 4 | PROV-K010 | ICU Step-Down Delay Time | <6 hours | >24h (capacity stranding) |
| 5 | PROV-K012 | Home Health 30-Day Readmission Rate | <14% | >18% (HHVBP penalty risk) |

### Top 3 Personas
| # | ID | Persona | Decision Influence | Primary Pain Focus |
|---|----|---------|-------------------|---------------------|
| 1 | PROV-PER004 | Bed Manager | Technical | ED boarding, ICU step-down, diversion, throughput |
| 2 | PROV-PER005 | OR Director | Technical | Block utilization, first-case starts, turnover, cancellations |
| 3 | PROV-PER003 | Patient Access Director | Economic | No-shows, wait times, PA, registration accuracy |

### Key Value Formulas
| ID | Name | Formula Type | Example Output |
|----|------|-------------|----------------|
| PROV-F001 | ED Flow Optimization Value | Revenue Uplift | $4.05M annually |
| PROV-F002 | OR Throughput Value | Revenue Uplift | $1.45M – $2.80M annually |
| PROV-F003 | Clinic No-Show Revenue Recovery | Revenue Uplift | $2.66M annually |
| PROV-F005 | Home Health Readmission Penalty Avoidance | Revenue Uplift | $2.05M annually |
| PROV-F011 | Sepsis Bundle Value | Revenue + Lives Saved | $10.82M annually |

---

*SKILL.md generated from ValuePack sources: `value-pack.json`, `value-pack.md`. Companion files `signals-examples.ts` retained as-is.*
