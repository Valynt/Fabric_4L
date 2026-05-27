# SKILL.md — Education and Public Institutions Subpack

## Skill Identity Block

| Field | Value |
|-------|-------|
| **skill_name** | Education and Public Institutions Value Subpack |
| **description** | Vertical-specialized value pack for K-12 districts, public universities, community colleges, research institutions, workforce boards, and public libraries. Covers $800B+ annual public education spending with focus on enrollment management, student success, research administration, financial aid compliance, and campus operations. |
| **version** | 1.0.0 |
| **domain** | Public Sector — Education |
| **pack_type** | subpack |
| **parent_master** | public-sector-master-v1 |

---

## Triggers

Auto-load this subpack when the user query includes any of these patterns:

1. `student information system unification` — SIS fragmentation, roster sync, state reporting automation
2. `research grant admin cost` — NIH/NSF compliance, effort reporting, closeout backlog, indirect cost recovery
3. `K-12 cybersecurity readiness` — EdTech app governance, FERPA compliance, data privacy vetting
4. `FERPA compliance audit` — Student data privacy breach, vendor data-sharing agreements, OCR investigation
5. `workforce board WIOA reporting` — Performance data fragmentation, credential attainment tracking, wage record matching
6. `financial aid verification bottleneck` — Title IV processing, disbursement delays, R2T4 accuracy
7. `enrollment cliff tuition revenue` — Demographic decline, discount rate growth, program closure risk
8. `teacher shortage substitute crisis` — K-12 vacancy rates, hiring cycle length, retention loss
9. `Title IX Clery compliance` — Campus safety systems, case resolution time, Annual Security Report
10. `special education IEP compliance` — IDEA deadlines, service delivery minutes, due process complaints
11. `deferred maintenance energy efficiency` — Facilities backlog, HVAC age, EPA Energy Star gap
12. `transfer credit articulation loss` — Community college to 4-year pathway, excess credit accumulation

---

## Reasoning Flow

### Step 1: Identify Institution Segment
Determine which vertical segment the prospect belongs to:
- **K-12 Public School Districts** — SIS, ESSER, teacher staffing, IEP, facilities
- **Public Universities / State Colleges** — Financial aid, enrollment, research admin, Title IX/Clery
- **Community Colleges** — Completion rates, transfer articulation, WIOA, financial aid
- **Public Research Institutions** — Grant administration, DMP compliance, effort reporting, closeout
- **Workforce Development Boards** — WIOA quarterly reporting, credential tracking, wage matching
- **Public Libraries** — Digital equity, hotspot lending, broadband access, digital skills

### Step 2: Scan for Raw Signals
Apply the 18 vertical signal rules (EDU-SIG-101 to EDU-SIG-118). Look for:
- **Data/Systems Signals** — Duplicate records, sync failures, app count, SLDS coverage
- **Compliance Signals** — ED OCR complaints, Clery ASR delays, Title IX resolution time, ESSER obligation rate
- **Operational Signals** — Teacher vacancy, substitute fill, counseling waitlist, deferred maintenance backlog
- **Financial Signals** — Verification queue size, disbursement delay, closeout backlog, unspent ESSER balance

### Step 3: Confirm Signal with Required Evidence
Each signal requires 2-4 confirmation signals. Example confirmation sources:
- System inventory + data quality audit + API error logs (for SIS fragmentation)
- ESSER dashboard + procurement schedule + supplement-not-supplant docs (for spend-down risk)
- Case tracker + geography audit + test log (for Clery/Title IX gap)

### Step 4: Map to Pains, Personas, and KPIs
| Signal | Pain | Primary Persona | Key KPI |
|--------|------|-----------------|---------|
| EDU-SIG-101 | EDU-PAIN-101 | EDU-PERS-102 / EDU-PERS-101 | EDU-KPI-101, EDU-KPI-103 |
| EDU-SIG-102 | EDU-PAIN-102 | EDU-PERS-104 | EDU-KPI-104, EDU-KPI-105 |
| EDU-SIG-103 | EDU-PAIN-103 | EDU-PERS-103 | EDU-KPI-107, EDU-KPI-108 |
| EDU-SIG-104 | EDU-PAIN-104 | EDU-PERS-105 | EDU-KPI-110, EDU-KPI-112 |
| EDU-SIG-105 | EDU-PAIN-105 | EDU-PERS-106 | EDU-KPI-113, EDU-KPI-114 |
| EDU-SIG-106 | EDU-PAIN-106 | EDU-PERS-102 | EDU-KPI-116, EDU-KPI-117 |
| EDU-SIG-107 | EDU-PAIN-107 | EDU-PERS-102 | EDU-KPI-119, EDU-KPI-120 |
| EDU-SIG-108 | EDU-PAIN-108 | EDU-PERS-101 | EDU-KPI-121, EDU-KPI-122 |
| EDU-SIG-109 | EDU-PAIN-109 | EDU-PERS-105 | EDU-KPI-123, EDU-KPI-124 |
| EDU-SIG-110 | EDU-PAIN-110 | EDU-PERS-102 | EDU-KPI-103 |
| EDU-SIG-111 | EDU-PAIN-111 | EDU-PERS-103 | EDU-KPI-107, EDU-KPI-108 |
| EDU-SIG-112 | EDU-PAIN-112 | EDU-PERS-102 | EDU-KPI-125 |
| EDU-SIG-113 | EDU-PAIN-113 | EDU-PERS-105 | EDU-KPI-110, EDU-KPI-111 |
| EDU-SIG-114 | EDU-PAIN-114 | EDU-PERS-106 | EDU-KPI-113, EDU-KPI-115 |
| EDU-SIG-115 | EDU-PAIN-115 | EDU-PERS-101 / EDU-PERS-105 | EDU-KPI-101, EDU-KPI-102 |
| EDU-SIG-116 | EDU-PAIN-116 | EDU-PERS-102 / EDU-PERS-101 | EDU-KPI-118 |
| EDU-SIG-117 | EDU-PAIN-117 | EDU-PERS-105 | EDU-KPI-111, EDU-KPI-112 |
| EDU-SIG-118 | EDU-PAIN-118 | EDU-PERS-103 | EDU-KPI-102, EDU-KPI-103 |

### Step 5: Select Value Formula
Match confirmed pain to the appropriate vertical formula:
- **SIS / Data Integration** → EDU-VF-101 (SIS Integration Administrative Savings)
- **Financial Aid** → EDU-VF-102 (Disbursement Acceleration Value)
- **Research Grants** → EDU-VF-103 (Grant Admin Cost Reduction)
- **Completion / Retention** → EDU-VF-104 (Degree Completion Revenue Retention)
- **Safety / Compliance** → EDU-VF-105 (Title IX / Clery Cost Avoidance)
- **Teacher Staffing** → EDU-VF-106 (Hiring & Retention Cost Savings)
- **ESSER** → EDU-VF-107 (Fund Retention Value)
- **Privacy / Security** → EDU-VF-108 (EdTech Privacy Risk Reduction)
- **WIOA** → EDU-VF-109 (Performance Reporting Efficiency)
- **Special Education** → EDU-VF-110 (IEP Compliance Cost Avoidance)
- **Research Data** → EDU-VF-111 (DMP Compliance Value)
- **Library Digital Equity** → EDU-VF-112 (Digital Equity Program Value)
- **Facilities** → EDU-VF-113 (Energy & Maintenance Optimization)

### Step 6: Confidence Scoring Guidance
| Score | Criteria |
|-------|----------|
| **90-100%** | Direct customer data available; time-motion study or institutional audit confirms signal |
| **75-89%** | Federal/industry benchmark data + partial customer confirmation |
| **60-74%** | Benchmark data only; no direct customer confirmation |
| **<60%** | Signal pattern suggests pain but requires discovery call validation |

Apply confidence modifiers:
- **+10%** if multiple independent sources confirm the same signal
- **-15%** if the institution is an outlier (e.g., Ivy-equivalent selectivity, well-funded district)
- **-10%** if recent technology investment (<18 months) suggests pain may be addressed

---

## Inheritance Map

### Master Skill to Load First
**`public-sector-master-v1`** must be loaded before this subpack. It provides:
- Base value driver framework (6 categories)
- Base persona archetypes (PS-PERS-001 through PS-PERS-014)
- Evidence source taxonomy (GAO, OIG, budget documents)
- Formula templates (NPV, annual, per-unit)
- Signal source taxonomy (financial, operational, compliance, external)
- Benchmark methodology (source-cited, ranged, confidence-graded)
- Governance framework (approval, review, confidence, source coverage)

### What This Subpack Adds
| Component | Count | Description |
|-----------|-------|-------------|
| Vertical Pains | 18 | EDU-PAIN-101 to EDU-PAIN-118 — Segment-specific enrollment, compliance, staffing, and operational pains |
| Vertical KPIs | 25 | EDU-KPI-101 to EDU-KPI-125 — Formulas with typical ranges and benchmarks |
| Vertical Signal Rules | 18 | EDU-SIG-101 to EDU-SIG-118 — Raw signal patterns with confidence scores |
| Vertical Personas | 6 | EDU-PERS-101 to EDU-PERS-106 — CIO, Superintendent, Research Admin, Financial Aid Director, Registrar, Campus Safety Chief |
| Vertical Formulas | 13 | EDU-VF-101 to EDU-VF-113 — Segment-specific value formulas with worked examples |
| Vertical Benchmarks | 18 | EDU-BENCH-101 to EDU-BENCH-118 — Source-cited performance benchmarks |
| Regulatory Factors | 10 | EDU-REG-101 to EDU-REG-110 — FERPA, Title IV, Clery, Title IX, IDEA, Section 504, 2 CFR 200, NIH/NSF DMS, ESSER, WIOA |
| Technology Systems | 14 | EDU-TECH-101 to EDU-TECH-114 — Core systems with integration complexity and replacement risk |
| Discovery Questions | 18 | EDU-DQ-101 to EDU-DQ-118 — Quantitative and process-oriented discovery prompts |
| Objection Patterns | 9 | EDU-OBJ-101 to EDU-OBJ-109 — Common procurement and adoption objections with response frameworks |
| Worked Examples | 3 | EDU-WE-101 to EDU-WE-103 — Detailed ROI calculations for K-12 SIS, financial aid, and research admin |
| Buying Triggers | 14 | EDU-TRIG-101 to EDU-TRIG-114 — Regulatory, compliance, operational, financial, and risk triggers with timing and budget ranges |

### When to Use Master vs. Subpack
| Scenario | Recommendation |
|----------|----------------|
| Prospect is a public-sector organization with unclear vertical | **Use Master only** — Apply base signal taxonomy and persona archetypes |
| Prospect is a K-12 district, university, college, research institution, workforce board, or library | **Load Master + this Subpack** — Use vertical-specific pains, KPIs, and formulas |
| Prospect is a state education agency or system office | **Load Master first, then evaluate if subpack pain overlap exists** |
| Prospect is a private/for-profit education provider | **Use Master only** — This subpack is designed for public institutions; private providers may have overlapping but distinct regulatory frameworks |

---

## Structured Output Template

```json
{
  "skill_loaded": "education-v1",
  "parent_master": "public-sector-master-v1",
  "analysis_timestamp": "ISO-8601",
  "prospect_segment": "K-12 | Public University | Community College | Research Institution | Workforce Board | Public Library",
  "signals_detected": [
    {
      "signal_id": "EDU-SIG-###",
      "signal_name": "...",
      "confidence": 0.00,
      "raw_evidence": ["..."],
      "confirmation_status": "confirmed | partial | unconfirmed",
      "linked_pain": "EDU-PAIN-###",
      "linked_personas": ["EDU-PERS-###"],
      "linked_kpis": ["EDU-KPI-###"],
      "priority": "HIGH | MEDIUM | LOW"
    }
  ],
  "pains_matched": [
    {
      "pain_id": "EDU-PAIN-###",
      "pain_name": "...",
      "prevalence": "HIGH | MEDIUM | LOW",
      "confidence": "HIGH | MEDIUM | LOW",
      "affected_personas": ["..."],
      "financial_impact_estimate": "USD range or formula reference"
    }
  ],
  "personas_identified": [
    {
      "persona_id": "EDU-PERS-###",
      "persona_name": "...",
      "decision_authority": "HIGH | MEDIUM | LOW",
      "relevance_score": 0.00,
      "discovery_questions": ["EDU-DQ-###"]
    }
  ],
  "kpis_relevant": [
    {
      "kpi_id": "EDU-KPI-###",
      "kpi_name": "...",
      "prospect_value": "known value or UNKNOWN",
      "benchmark_range": "...",
      "gap_assessment": "above | within | below | unknown"
    }
  ],
  "value_hypotheses": [
    {
      "formula_id": "EDU-VF-###",
      "formula_name": "...",
      "estimated_value_range": "USD range",
      "confidence": "HIGH | MEDIUM | LOW",
      "required_inputs": ["..."],
      "value_driver_category": "Revenue Uplift | Cost Savings | Risk Reduction | Working Capital | Mission Effectiveness"
    }
  ],
  "buying_triggers_active": [
    {
      "trigger_id": "EDU-TRIG-###",
      "trigger_name": "...",
      "timing": "...",
      "budget_range": "...",
      "decision_timeline": "..."
    }
  ],
  "objections_forecast": [
    {
      "objection_id": "EDU-OBJ-###",
      "objection_text": "...",
      "target_persona": "...",
      "response_framework": "..."
    }
  ],
  "governance": {
    "overall_confidence": "HIGH | MEDIUM | LOW",
    "source_coverage": "Mixed (public + industry data)",
    "customer_facing_approved": false,
    "review_owner": "Education Subpack Architect — Public Sector Vertical",
    "last_updated": "2026-04-25"
  }
}
```

---

## Governance Metadata

| Field | Value |
|-------|-------|
| **Confidence Level** | MEDIUM |
| **Source Coverage** | Mixed (Public government data + Industry association surveys + Vendor research) |
| **Customer-Facing Approval Status** | FALSE — Internal reference only until enterprise validation |
| **Review Owner** | Education Subpack Architect — Public Sector Vertical |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-elevated-swarm-edu |
| **Parent Master Swarm ID** | kimi-k2.6-elevated-swarm |

---

## Quick Reference

### Top 5 Pains (by prevalence × financial impact)

| Rank | Pain | ID | Segment | Prevalence |
|------|------|----|---------|------------|
| 1 | Student Information System Fragmentation | EDU-PAIN-101 | K-12 | HIGH |
| 2 | Enrollment Cliff & Net Tuition Revenue Decline | EDU-PAIN-113 | Higher Ed | HIGH |
| 3 | Financial Aid Verification Bottleneck | EDU-PAIN-102 | Higher Ed | HIGH |
| 4 | K-12 Teacher Shortage & Substitute Crisis | EDU-PAIN-106 | K-12 | HIGH |
| 5 | Research Grant Administration Cost Burden | EDU-PAIN-103 | Research | HIGH |

### Top 5 KPIs (by universal applicability)

| Rank | KPI | ID | Formula | Benchmark |
|------|-----|----|---------|-----------|
| 1 | SIS Data Accuracy Rate | EDU-KPI-101 | `(1 - Duplicate/Total) * 100%` | >98% best; <90% concerning |
| 2 | State/Federal Report Error Rate | EDU-KPI-102 | `Errors / Elements * 100%` | <2% target; >8% concerning |
| 3 | 6-Year Graduation Rate (Public 4-year) | EDU-KPI-110 | `Graduates / Cohort * 100%` | >70% top quartile; <50% concerning |
| 4 | Days to Disbursement | EDU-KPI-105 | `AVG(Disbursement - Award)` | <14 days best; >45 days concerning |
| 5 | Grant Proposal Success Rate | EDU-KPI-107 | `Awards / Proposals * 100%` | >25% R1 target; 10-20% CC |

### Top 3 Personas (by decision authority)

| Rank | Persona | ID | Scope | Authority |
|------|---------|----|-------|-----------|
| 1 | K-12 Superintendent / District Leader | EDU-PERS-102 | $50M-$500M budget; 5K-50K students | HIGH (district-wide) |
| 2 | University CIO / CTO | EDU-PERS-101 | $50M-$200M IT budget; 20K-50K students | HIGH (technology) |
| 3 | Registrar / Enrollment Manager | EDU-PERS-105 | $200M-$1B tuition revenue; 50-200 staff | HIGH (student systems) |

### Key Value Formulas

| Formula | ID | Quick Formula | Typical Output |
|---------|----|---------------|----------------|
| SIS Integration Savings | EDU-VF-101 | `(Hours_Eliminated * Rate) + Rework_Cost + Intervention_Value` | $900K-$1.7M annual |
| Aid Disbursement Acceleration | EDU-VF-102 | `(Days_Reduced * Students * Retention_Lift * Tuition) + Penalty_Avoidance` | $3M-$4.7M annual |
| Grant Admin Cost Reduction | EDU-VF-103 | `(Admin_Cost_Reduction * Research_Spend) + Error_Avoidance + Closeout_Value` | $10M-$11.6M annual |
| Degree Completion Revenue | EDU-VF-104 | `(Grad_Rate_Improvement * Cohort * Tuition * Years) - Investment` | $15M+ NPV |
| Compliance Cost Avoidance | EDU-VF-105 | `(Hour_Reduction * Cases * Rate) + Litigation_Avoidance + OCR_Avoidance` | $1M-$1.25M annual |
