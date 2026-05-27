# SKILL.md — Horizontal SaaS Subpack (S2.1)

## 1. Skill Identity Block

| Field | Value |
|---|---|
| **skill_name** | Horizontal SaaS Subpack (S2.1) |
| **description** | Vertical-specialized value intelligence for organizations managing CRM, ERP, HRIS, finance, procurement, project management, collaboration, support, marketing automation, BI/analytics, data platforms, cybersecurity, IAM/PAM, and DevOps tooling stacks. Adds 20 function-specific pains, 60 KPIs, 20 signal rules, 6 personas, 15 formulas, 30 benchmarks, and 15 buying triggers atop the SaaS Master Pack baseline. |
| **version** | 1.0.0 |
| **domain** | Horizontal SaaS / Enterprise Software |
| **pack_type** | subpack |
| **parent_master** | saas-master-v1 |

---

## 2. Triggers

Auto-load this skill when queries match any of the following natural language patterns:

1. **SaaS sprawl consolidation** — e.g., "reduce duplicate SaaS subscriptions," "consolidate our software stack"
2. **CRM ERP integration** — e.g., "connect CRM to ERP," "fix revenue reconciliation between systems"
3. **Finance close automation** — e.g., "speed up month-end close," "automate finance reconciliation"
4. **IAM security overhaul** — e.g., "automate user access provisioning," "reduce orphaned accounts"
5. "marketing attribution across channels" or "unify marketing performance data"
6. "BI dashboard sprawl" or "single source of truth for metrics"
7. "procurement approval bottlenecks" or "maverick spend control"
8. "HRIS fragmentation" or "employee data silos"
9. "support ticket escalation" or "knowledge base deflection"
10. "DevOps toolchain standardization" or "platform engineering"
11. "shadow AI governance" or "unvetted AI tool proliferation"
12. "contract lifecycle management" or "SaaS renewal chaos"

---

## 3. Reasoning Flow

### Step 1: Load Master Baseline
Before applying this subpack, ensure the **saas-master-v1** master skill is loaded. The master provides:
- Base value driver framework (cost_efficiency, revenue_uplift, risk_reduction, strategic_capability)
- Base persona archetypes (Economic Buyer, Technical Buyer, User Buyer, Champion, Coach, Executive Sponsor)
- Formula templates for ROI, payback, TCO, and net benefit calculations
- Signal source taxonomy (firmographic, technographic, behavioral, intent)
- Benchmark methodology (triangulated from Gartner, Forrester, IDC, vendor reports)
- Governance framework (confidence scoring, source coverage, approval workflows)

### Step 2: Identify Horizontal SaaS Signals
Scan for any of the 20 signal rules (HSR001–HSR020) categorized by function:

| Signal Category | Example Signals | Confidence Range |
|---|---|---|
| IT / SaaS Management | HSR001, HSR009 | 0.70–0.80 |
| Finance / ERP | HSR002, HSR012, HSR017 | 0.75–0.90 |
| HR / People Ops | HSR003 | 0.70 |
| Procurement | HSR004, HSR008, HSR015 | 0.75–0.90 |
| Data / BI / Analytics | HSR005, HSR020 | 0.70–0.75 |
| Security / IAM | HSR006, HSR014, HSR019 | 0.75–0.85 |
| DevOps / Platform Eng | HSR007 | 0.80 |
| Collaboration / Knowledge | HSR009, HSR018 | 0.70 |
| Project / Portfolio | HSR016 | 0.70 |
| Marketing / CDP | HSR011 | 0.75 |

**Confidence Scoring Guidance:**
- **0.85–1.00 (HIGH):** Active RFP, public ERP migration announcement, security audit finding, or CFO close mandate.
- **0.70–0.84 (MEDIUM):** Hiring patterns, tool evaluation signals, or survey mentions requiring 1–2 confirmation signals.
- **0.50–0.69 (LOW):** Single signal without confirmation; treat as hypothesis requiring qualification.

### Step 3: Map Signals to Pains
For each confirmed signal, map to the relevant pain(s) using the `linkedPains` array. Example mappings:

| Signal | Primary Pain(s) | Secondary Pain(s) |
|---|---|---|
| HSR001 — IT Director Hiring Surge | HSP001 (SaaS Sprawl) | HSP002 (Integration Debt), HSP013 (IAM Inconsistency) |
| HSR002 — Finance Systems Admin Hiring | HSP004 (ERP-Finance Latency) | HSP016 (Close Manual Burden), HSP018 (Legacy ERP Lock-In) |
| HSR006 — Security Engineer Surge | HSP014 (Security Tool Sprawl) | HSP013 (IAM Inconsistency), HSP020 (Shadow AI) |
| HSR012 — ERP Cloud Migration | HSP018 (Legacy ERP Lock-In) | HSP004 (ERP-Finance Latency), HSP016 (Close Manual Burden) |

### Step 4: Identify Affected Personas
For each confirmed pain, identify the primary personas from the 6 vertical personas:

| Pain | Primary Persona(s) |
|---|---|
| HSP001, HSP002 | IT Director |
| HSP003 | VP Sales / CRO |
| HSP004, HSP016, HSP018 | Finance Systems Admin, CFO |
| HSP005 | HR Operations Manager |
| HSP006, HSP019 | Procurement Lead |
| HSP007 | COO, PMO Lead |
| HSP008 | COO, IT Director |
| HSP009 | VP Support |
| HSP010, HSP017 | VP Marketing |
| HSP011, HSP012 | BI Analyst, Data/Analytics Leader |
| HSP013, HSP014, HSP020 | Security Engineer, CISO |
| HSP015 | VP DevOps, Platform Engineering Lead |

### Step 5: Extract or Estimate KPIs
For each linked pain, calculate or estimate the relevant KPIs. Use the `benchmarkRange` to assess severity:

- **GREEN / Optimized:** KPI within "best-in-class" range.
- **YELLOW / At Risk:** KPI within median range; opportunity exists.
- **RED / Critical:** KPI exceeds danger threshold; urgent pain.

### Step 6: Apply Value Formulas
Select the appropriate formula from HSVF001–HSVF015 based on the dominant pain cluster:

| Pain Cluster | Formula | Output |
|---|---|---|
| SaaS Sprawl | HSVF001 | Annual consolidation savings |
| Integration Debt | HSVF002 | Annual maintenance + capacity freed |
| CRM Data Quality | HSVF003 | Admin savings + revenue uplift |
| Finance Close | HSVF004 | Close acceleration + board prep savings |
| HRIS Unification | HSVF005 | Onboarding + payroll + admin savings |
| Procurement Optimization | HSVF006 | Maverick recovery + negotiation + onboarding savings |
| Project Visibility | HSVF007 | Executive time + resource conflict + slippage reduction |
| Collaboration Efficiency | HSVF008 | Context switching + search + meeting productivity |
| Support Deflection | HSVF009 | Ticket deflection + escalation + attrition savings |
| Marketing Attribution | HSVF010 | Attribution optimization + velocity + MQL quality |
| BI Governance | HSVF011 | Reconciliation + decision quality + self-service |
| Data Pipeline Reliability | HSVF012 | SLA miss reduction + schema breakage + backlog |
| IAM Automation | HSVF013 | Offboarding + access review + provisioning + risk |
| Security Consolidation | HSVF014 | Tool savings + MTTR + SOC analyst time |
| Platform Engineering | HSVF015 | Pipeline standardization + failure reduction + backlog |

### Step 7: Build Value Hypothesis
Combine pains, personas, KPIs, and formula output into a structured value hypothesis:

> **For [Persona]** at **[Company]** running **[Sub-vertical Stack]**, the pain of **[Pain Name]** is costing approximately **[Formula Output]** annually, driven by **[KPI Evidence]**. Addressing this through **[Solution Category]** will deliver **[Value Driver]** within **[Payback Period]**.

---

## 4. Inheritance Map

### Master Skill to Load First
**saas-master-v1** — SaaS Master Pack

### What the Master Provides (Read-Only Reference)
| Component | Master Content |
|---|---|
| Value Driver Framework | Base categories: cost_efficiency, revenue_uplift, risk_reduction, strategic_capability |
| Persona Archetypes | Economic Buyer, Technical Buyer, User Buyer, Champion, Coach, Executive Sponsor |
| Evidence Source Types | Public financial filings, industry reports, customer testimonials |
| Formula Templates | ROI, payback, TCO, net benefit calculations |
| Signal Source Taxonomy | Firmographic, technographic, behavioral, intent |
| Benchmark Methodology | Triangulated from Gartner, Forrester, IDC, vendor reports |
| Governance Framework | Confidence scoring, source coverage, approval workflows |

### What This Subpack Adds
| Component | Subpack Addition |
|---|---|
| **20 Vertical Pains** | HSP001–HSP020 (SaaS sprawl, integration debt, CRM decay, ERP latency, HRIS silos, procurement bottlenecks, project gaps, collaboration overload, support escalation, marketing attribution fragmentation, BI dashboard sprawl, data platform latency, IAM inconsistency, security alert fatigue, DevOps fragmentation, finance close burden, CDP gap, legacy ERP lock-in, contract renewal chaos, shadow AI) |
| **60 Vertical KPIs** | HSK001–HSK060 (SaaS app count, duplicate tool rate, integration success, CRM completeness, days to close, HRIS coverage, PO cycle time, project health score, KB search success, FCR, attribution coverage, semantic layer governance, data freshness, offboarding time, alert SNR, deployment standardization, FP&A prep ratio, CDP time-to-value, ERP customization index, contract coverage, shadow AI adoption) |
| **20 Vertical Signal Rules** | HSR001–HSR020 (hiring surges by function, RFP signals, audit findings, migration announcements, renewal concentration) |
| **6 Vertical Personas** | IT Director, HR Operations Manager, Finance Systems Admin, Procurement Lead, BI Analyst, Security Engineer |
| **15 Value Formulas** | HSVF001–HSVF015 (sprawl consolidation, integration debt reduction, CRM quality, close acceleration, HRIS unification, procurement optimization, project visibility, collaboration efficiency, support deflection, marketing attribution, BI governance, pipeline reliability, IAM automation, security consolidation, platform engineering) |
| **30 Benchmarks** | HSB001–HSB030 (industry-specific benchmarks from Gartner, vendor reports, analyst research) |
| **12 Regulatory Factors** | HSREG001–HSREG012 (GDPR, SOC 2, EU AI Act, SEC Cybersecurity Disclosure, NIS2, DORA, state privacy laws) |
| **15 Technology Systems** | HSTS001–HSTS015 (CRM, ERP, HRIS, BI, IAM, DevOps toolchain maps) |
| **20 Discovery Questions** | HSDQ001–HSDQ020 (function-specific qualification questions) |
| **10 Objection Patterns** | HSOBJ001–HSOBJ010 (horizontal SaaS-specific buyer objections) |
| **3 Worked Examples** | HSWE001–HSWE003 (mid-market sprawl, finance close automation, enterprise security consolidation) |
| **15 Buying Triggers** | HSBT001–HSBT015 (function-specific urgency triggers) |

### When to Use Master vs. Subpack
| Scenario | Recommendation |
|---|---|
| Prospect is a SaaS company but horizontal function unknown | Use **saas-master-v1** only |
| Prospect manages 10+ horizontal SaaS tools with known pain area | Load **saas-master-v1** + **horizontal-saas-v1** (this subpack) |
| Deep-dive on CRM data quality, ERP close, or security consolidation | Use this subpack; master provides baseline context |
| Cross-functional engagement spanning multiple horizontal tools | Master for framework; subpack for each function-specific module |

---

## 5. Structured Output Template

The expected JSON output for a Signals Analysis enrichment using this subpack:

```json
{
  "pack_id": "horizontal-saas-v1",
  "parent_master": "saas-master-v1",
  "analysis_timestamp": "2025-01-15T00:00:00Z",
  "prospect": {
    "company_name": "string",
    "industry": "string",
    "employee_count": "number",
    "revenue_range": "string"
  },
  "signals_detected": [
    {
      "signal_id": "HSR00X",
      "signal_name": "string",
      "confidence_score": 0.0,
      "confirmation_signals_matched": ["string"],
      "raw_evidence": "string"
    }
  ],
  "pain_analysis": [
    {
      "pain_id": "HSP00X",
      "pain_name": "string",
      "severity": "HIGH|MEDIUM|LOW",
      "confidence": "HIGH|MEDIUM|LOW",
      "linked_signals": ["HSR00X"],
      "symptoms_present": ["string"],
      "affected_personas": ["string"],
      "affected_sub_verticals": ["string"]
    }
  ],
  "kpi_assessment": [
    {
      "kpi_id": "HSK00X",
      "kpi_name": "string",
      "estimated_value": "number|string",
      "benchmark_status": "GREEN|YELLOW|RED",
      "benchmark_source": "string",
      "calculation_method": "actual|estimated|benchmark"
    }
  ],
  "persona_map": [
    {
      "persona_id": "HSPER00X",
      "persona_name": "string",
      "role": "string",
      "decision_influence": "economic|technical|user",
      "priority_pains": ["HSP00X"],
      "engagement_recommendation": "string"
    }
  ],
  "value_hypothesis": {
    "primary_formula_id": "HSVF00X",
    "formula_name": "string",
    "annual_value_estimate_usd": 0,
    "payback_period_months": 0,
    "confidence_level": "HIGH|MEDIUM|LOW",
    "key_assumptions": ["string"],
    "value_drivers": ["cost_efficiency|revenue_uplift|risk_reduction|strategic_capability"]
  },
  "inheritance_metadata": {
    "master_pack_loaded": true,
    "master_pack_id": "saas-master-v1",
    "subpack_components_used": ["pains", "kpis", "signals", "personas", "formulas"],
    "overridden_components": ["personas", "value_drivers", "regulatory_factors"]
  },
  "governance": {
    "source_coverage": "Mixed (public industry reports, vendor benchmarks, analyst research)",
    "overall_confidence": "HIGH|MEDIUM|LOW",
    "customer_facing_approved": true,
    "review_owner": "S2.1-HorizontalSaaS-Subpack-Agent",
    "last_updated": "2025-01-15"
  }
}
```

---

## 6. Governance Metadata

| Attribute | Value |
|---|---|
| **Confidence Level** | High (most claims backed by 2024–2025 industry reports; speculative content marked LOW or MEDIUM) |
| **Source Coverage** | Mixed — public industry reports (Gartner, Forrester, IDC), vendor benchmarks (Salesforce, HubSpot, Workday, Okta, CrowdStrike), analyst research (Productiv, Zylo, MuleSoft), and proprietary survey data |
| **Customer-Facing Approval Status** | Yes — approved for direct customer conversation, sales collateral, and executive presentations |
| **Review Owner** | S2.1-HorizontalSaaS-Subpack-Agent |
| **Last Updated** | 2025-01-15 |
| **Agent Swarm ID** | k2.6-saas-swarm-s2.1 |
| **Parent Master Swarm ID** | k2.6-saas-swarm-master |

---

## 7. Quick Reference

### Top 5 Pains (by prevalence × impact)

| # | Pain ID | Pain Name | Prevalence | Primary Persona |
|---|---------|-----------|------------|-----------------|
| 1 | **HSP001** | SaaS Sprawl Causing Duplicate Data and Redundant Spend | HIGH | IT Director, CFO |
| 2 | **HSP002** | Integration Debt Across 15+ Horizontal Tools | HIGH | IT Director, CTO |
| 3 | **HSP003** | CRM Data Decay and Pipeline Hygiene Failure | HIGH | VP Sales, CRO |
| 4 | **HSP004** | ERP-Finance System Reconciliation Latency | HIGH | Finance Systems Admin, CFO |
| 5 | **HSP014** | Security Tool Sprawl and Alert Fatigue | HIGH | Security Engineer, CISO |

### Top 5 KPIs (most diagnostic)

| # | KPI ID | KPI Name | Benchmark (Good / Median / At Risk) |
|---|--------|----------|-------------------------------------|
| 1 | **HSK001** | SaaS Application Count | SMB: 30–80 / Mid-Market: 80–150 / Enterprise: 150–300+ |
| 2 | **HSK002** | Duplicate Tool Rate | Optimized: <15% / Median: 20–30% / High sprawl: >35% |
| 3 | **HSK010** | Days to Month-End Close | Best-in-class: <5 days / Median: 8–12 days / Slow: >12 days |
| 4 | **HSK040** | Security Alert Signal-to-Noise Ratio | Effective: >30% / Noisy: 10–20% / Broken: <10% |
| 5 | **HSK031** | Single Source of Truth Coverage | Governed: >70% / Partial: 40–70% / Fragmented: <40% |

### Top 3 Personas (highest engagement frequency)

| # | Persona ID | Persona Name | Role | Decision Influence |
|---|------------|--------------|------|-------------------|
| 1 | **HSPER001** | IT Director | IT Operations and Systems Leader | Technical |
| 2 | **HSPER003** | Finance Systems Admin | ERP and Financial Systems Technical Owner | Technical |
| 3 | **HSPER006** | Security Engineer | Security Operations and IAM Technical Implementer | Technical |

### Key Value Formulas (highest reuse)

| # | Formula ID | Formula Name | Typical Annual Output Range |
|---|------------|--------------|----------------------------|
| 1 | **HSVF001** | SaaS Sprawl Consolidation Value | $200K–$2M |
| 2 | **HSVF002** | Integration Debt Reduction Value | $300K–$1.5M |
| 3 | **HSVF004** | Finance Close Acceleration Value | $85K–$500K |
| 4 | **HSVF013** | IAM Automation Value | $100K–$600K |
| 5 | **HSVF014** | Security Tool Consolidation Value | $200K–$800K |

---

*This subpack is an extension of the SaaS Master Pack (`saas-master-v1`). All base frameworks, taxonomies, and governance standards are inherited from the master. Refer to the master pack for core value driver categories, formula templates, and signal source taxonomy. Do not use this subpack without first loading the master.*
