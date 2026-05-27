# Public Health and Human Services Subpack (S5.4)

**Version:** 1.0.0  
**Domain:** Public Sector — Health and Human Services  
**Parent Master:** public-sector-master-v1  
**Last Updated:** 2025-01-21  
**Review Owner:** Vertical Subpack Architect — Public Health & Human Services  
**Agent Swarm ID:** kimi-k2.6-elevated-swarm-phhs  
**Source Coverage:** Mixed (CMS, HHS, USDA, DOL, HUD, SAMHSA, CDC, state agencies, KFF, GAO, NASCIO)  
**Overall Confidence:** Medium  
**Approved for Customer-Facing Output:** No (requires validation with live prospects)

---

## Table of Contents

1. [Vertical Focus](#vertical-focus)
2. [Inheritance Manifest](#inheritance-manifest)
3. [Business Pains](#business-pains)
4. [KPI Definitions](#kpi-definitions)
5. [Value Drivers](#value-drivers)
6. [Value Formulas](#value-formulas)
7. [Benchmarks](#benchmarks)
8. [Signal Interpretation Rules](#signal-interpretation-rules)
9. [Evidence Sources](#evidence-sources)
10. [Buying Triggers](#buying-triggers)
11. [Persona Profiles](#persona-profiles)
12. [Discovery Questions](#discovery-questions)
13. [Objection Patterns](#objection-patterns)
14. [Technology Systems](#technology-systems)
15. [Regulatory Factors](#regulatory-factors)
16. [Competitor Factors](#competitor-factors)
17. [Worked Examples](#worked-examples)
18. [Governance](#governance)

---

## Vertical Focus

| Sub-Segment | Description | Typical Budget Scale | Key Regulatory Drivers |
|-------------|-------------|---------------------|------------------------|
| Medicaid State Agencies (SMAs) | State Medicaid agencies, $800B+ program nationally | $1B-$50B per state | CMS 438, MITA, FMAP |
| State / Local Public Health Departments | Disease control, health promotion, environmental health | $10M-$500M per state | CDC DMI, PHEP, ELR |
| Child Welfare / Foster Care Agencies | CPS, foster care, adoption, family services | $100M-$2B per state | CCWIS, AFCARS, Title IV-E |
| Unemployment Insurance Agencies | UI claims processing, trust fund management | $50M-$500M per state | DOL ETA 901/902, SSA |
| SNAP / Nutrition Assistance Administration | SNAP eligibility, EBT, nutrition education | $100B+ federal | USDA QC, FNS guidance |
| Housing Assistance (Section 8, LIHTC) | Voucher administration, project-based | $50M-$500M per PHA | HUD VMS, PHA standards |
| Behavioral Health (SAMHSA-funded) | Mental health, substance use block grants | $5B+ federal | SAMHSA block grants, 988 |
| Aging / Disability Services (ACL, ADRCs) | Aging network, disability services, HCBS | $2B+ federal | Olmstead, CMS HCBS |
| Veterans Benefits (State-level) | State veterans homes, benefits advocacy | $10M-$200M per state | VA state coordination |
| Disease Surveillance / Epidemiology | Syndromic surveillance, registries | $5M-$50M per state | CDC NNDSS, ELR |

---

## Inheritance Manifest

### Inherited from Master (Read-Only Reference)

- Value Driver Framework (Cost Savings, Risk Reduction, Mission Effectiveness, Revenue Uplift, Working Capital)
- Base Persona Archetypes (CIO, CFO, CISO, IG, Program Director, Procurement Officer)
- Evidence Source Taxonomy (GAO, OIG, Federal Budget, Census, FOIA)
- Formula Templates (NPV, annualization, confidence rules)
- Signal Source Taxonomy (budget, audit, incident, workforce)
- Benchmark Methodology (source citation, range, confidence)
- Governance Framework (confidence levels, approval workflow, source coverage)
- Cross-cutting Pains (Legacy Systems, Cybersecurity, Data Silos, Workforce Shortage, Budget Volatility)
- Cross-cutting KPIs (O&M Ratio, Time-to-Hire, Audit Finding Rate, Budget Variance)
- Cross-cutting Formulas (Legacy O&M Cost Avoidance, Cybersecurity Incident Cost Avoidance, Digital Channel Shift)
- Cross-cutting Signal Rules (Legacy System Maintenance Spending, Critical Vulnerability Exposure, Data Silo Indicators)
- Cross-cutting Buying Triggers (Annual Appropriation, Audit Finding, New Leadership, Incumbent Contract End)
- Cross-cutting Objections (Procurement Cycle Too Long, Federal Funding Uncertainty, Legacy Integration Complexity)

### Created by Subpack (Vertical-Specialized)

- **18 Vertical Pains:** Medicaid backlog, SNAP error rate, Child Welfare fragmentation, UI fraud, Surveillance latency, BH access gap, Housing waitlist, MCO oversight, HCBS waitlist, Veterans coordination, Eligibility worker crisis, TANF cost rigidity, MMIS EOL, IIS fragmentation, Cross-program silos, Emergency preparedness, CSE lag, CCDF bottleneck
- **40 Vertical KPIs:** Program-specific metrics for Medicaid, SNAP, UI, Child Welfare, Surveillance, Behavioral Health, Housing, Aging/Disability, Veterans
- **12 Vertical Value Drivers:** Domain-specific signal-to-pain mappings
- **12 Vertical Formulas:** Program-specific value calculation models
- **18 Vertical Benchmarks:** Health and human services industry benchmarks with federal data sources
- **18 Vertical Signal Rules:** Domain-specific signal interpretation rules with confidence scores
- **10 Vertical Evidence Sources:** CMS, KFF, USDA, DOL, HHS, CDC, SAMHSA, HUD, MACPAC
- **14 Vertical Buying Triggers:** Medicaid unwinding, SNAP QC penalty, CMS 438 rule, MMIS recompete, UI modernization, Child welfare RFP, CDC DMI funding, 988 expansion, HUD PHA modernization, Olmstead enforcement, Federal HHS NOFO, State HHS consolidation, ACA enrollment period, Public health emergency
- **6 NEW Vertical Personas:** Medicaid Director, Public Health Officer, Child Welfare Case Manager Supervisor, UI Claims Director, Eligibility Worker Supervisor, Behavioral Health Program Director
- **18 Discovery Questions:** Program-specific qualification questions
- **9 Objection Patterns:** CMS APD timeline, Federal funding uncertainty, Union opposition, Legacy integration, Privacy constraints, Procurement cycle, Pandemic funding cliff, Veterans federal responsibility, BH provider shortage
- **12 Technology Systems:** MMIS, E&E, CCWIS, UI Benefits, SNAP EBT, ELR/Surveillance, IIS, BH EHR/Crisis, PHA Management, ADRC, CCDF, Integrated Eligibility
- **10 Regulatory Factors:** CMS 438, Streamlined verification, SNAP QC, UI performance, CCWIS/AFCARS, CDC DMI, SAMHSA 988, HUD PHA, Olmstead, CCDF
- **4 Competitor Factors:** MMIS incumbent entrenchment, SI eligibility dominance, Open source solutions, SaaS case management disruption
- **3 Worked Examples:** Medicaid ex parte automation $34M, Child welfare consolidation $14.4M, SNAP error reduction $15M

### Overridden Components

| Component | Override Reason |
|-----------|-----------------|
| KPI: Enrollment / Churn Rate | Subpack provides more granular churn segmentation (Medicaid-specific, SNAP-specific, program-specific drivers) and adds ex parte renewal rate as companion KPI |
| Pain: Medicaid Administrative Complexity | Subpack decomposes into 5+ specific pains (eligibility backlog, MCO oversight, MMIS EOL, cross-program silos, worker retention) with program-specific symptoms and KPIs |
| Formula: Medicaid Churn Cost Avoidance | Subpack refines with post-unwinding state-specific variables (gap-in-care cost, CMS compliance avoidance) and adds ex parte renewal efficiency formula |

---

## Business Pains

### PH-PAIN-001: Medicaid Eligibility Redetermination Backlog >90 Days

| Attribute | Detail |
|-----------|--------|
| **Description** | Post-COVID unwinding and ongoing redetermination cycles create massive backlogs. States face CMS compliance risk and coverage gaps for vulnerable populations when eligibility determinations exceed statutory timeframes. |
| **Symptoms** | Eligibility determination time >45 days; ex parte renewal rate <40%; churn rate >15%; CMS corrective action plans issued; call center hold times >30 min during renewal waves |
| **Affected Sub-Segments** | Medicaid, SNAP |
| **Linked KPIs** | PH-KPI-001, PH-KPI-002, PH-KPI-003 |
| **Linked Value Drivers** | Cost Savings (admin efficiency), Mission Effectiveness (coverage continuity), Risk Reduction (CMS compliance) |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (KFF Medicaid Enrollment and Unwinding Tracker 2024; CMS T-MSIS Data; MACPAC Report on Churn) |

### PH-PAIN-002: SNAP Error Rate >6%

| Attribute | Detail |
|-----------|--------|
| **Description** | SNAP Quality Control (QC) error rates above federal thresholds trigger enhanced oversight, reduced federal funding share, and corrective action requirements. Root causes include outdated eligibility systems, insufficient verification, and worker errors. |
| **Symptoms** | QC error rate >6%; federal funding share reduction; USDA corrective action plan; high worker turnover; manual verification processes |
| **Linked KPIs** | PH-KPI-004, PH-KPI-005 |
| **Linked Value Drivers** | Cost Savings, Risk Reduction |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (USDA SNAP QC Annual Report FY2023; FNS State SNAP Error Rate Reports) |

### PH-PAIN-003: Child Welfare Case Management Data Fragmentation

| Attribute | Detail |
|-----------|--------|
| **Description** | Child welfare agencies lack unified case management across intake, investigation, foster care, adoption, and family services. Caseworkers manage 15+ separate systems, causing data gaps that endanger child safety and trigger audit findings. |
| **Symptoms** | Caseworkers accessing >10 systems per case; missing placement history during investigations; AFCARS submission errors >5%; recurrence of maltreatment rate >10%; CPS response time >statutory threshold |
| **Linked KPIs** | PH-KPI-006, PH-KPI-007, PH-KPI-008 |
| **Linked Value Drivers** | Risk Reduction, Mission Effectiveness, Cost Savings |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (HHS ACF Child Welfare Outcomes Reports; AFCARS Data; GAO-22-104238) |

### PH-PAIN-004: Unemployment Insurance Claims Backlog and Fraud Surge

| Attribute | Detail |
|-----------|--------|
| **Description** | UI agencies face conflicting pressures: clear pandemic-era backlogs while maintaining program integrity. Identity theft and organized fraud rings exploited weaknesses, leading to $100B+ in estimated improper payments nationally. |
| **Symptoms** | Claims pending >21 days >10% of volume; identity verification queue >30 days; overpayment balance growing >$1B state-level; fraud referral backlog; trust fund solvency concerns |
| **Linked KPIs** | PH-KPI-009, PH-KPI-010, PH-KPI-011 |
| **Linked Value Drivers** | Cost Savings, Risk Reduction, Working Capital |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (GAO-23-105474; DOL ETA UI Performance Data; Pandemic Response Accountability Committee) |

### PH-PAIN-005: Public Health Disease Surveillance Data Latency

| Attribute | Detail |
|-----------|--------|
| **Description** | Disease surveillance relies on fragmented, manual reporting pathways. COVID-19 exposed critical gaps: labs faxing results, inconsistent EHR extraction, and week-long delays in outbreak detection. Federal mandates (CDC Data Modernization Initiative) require transformation. |
| **Symptoms** | Reportable disease notification >7 days from event; manual data entry from faxed lab reports; no automated EHR case reporting; syndromic surveillance coverage <80% of EDs; ELR gaps |
| **Linked KPIs** | PH-KPI-012, PH-KPI-013 |
| **Linked Value Drivers** | Risk Reduction, Mission Effectiveness |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (CDC Data Modernization Initiative; CSTE Assessment; PHII Surveillance Systems Assessment) |

### PH-PAIN-006: Behavioral Health Access Gap and Provider Shortage

| Attribute | Detail |
|-----------|--------|
| **Description** | Behavioral health programs face severe provider shortages, long wait times, and disjointed care pathways. SAMHSA block grant and Medicaid reimbursement constraints limit expansion. Crisis systems (988, mobile crisis) require rapid scale-up. |
| **Symptoms** | Wait time for outpatient behavioral health >30 days; psychiatrist vacancy rate >20%; crisis call abandonment rate >5%; no integration with primary care; involuntary commitment delays |
| **Linked KPIs** | PH-KPI-014, PH-KPI-015, PH-KPI-016 |
| **Linked Value Drivers** | Mission Effectiveness, Risk Reduction |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (SAMHSA National Survey; HRSA Area Health Resource File; NAMI State Mental Health Legislation) |

### PH-PAIN-007: Housing Assistance Voucher Waitlist Backlog

| Attribute | Detail |
|-----------|--------|
| **Description** | Public Housing Authorities maintain voucher waitlists of 2-8 years. Administrative burden of HQS inspections, landlord engagement, and portability processing limits throughput. HOME and LIHTC program administration adds complexity. |
| **Symptoms** | Voucher waitlist >5,000 households; average wait time >24 months; HQS inspection backlog >30 days; landlord participation rate declining; portability processing >60 days |
| **Linked KPIs** | PH-KPI-017, PH-KPI-018 |
| **Linked Value Drivers** | Mission Effectiveness, Cost Savings |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (HUD Picture of Subsidized Households; PHA Annual Plans; NLIHC Housing Spotlight) |

### PH-PAIN-008: Medicaid Managed Care Oversight and Performance Gaps

| Attribute | Detail |
|-----------|--------|
| **Description** | States delegate 80%+ of Medicaid beneficiaries to MCOs but struggle with oversight: incomplete encounter data, quality metric gaps, network adequacy complaints, and rate-setting disputes. CMS requires state-directed payments and equity analyses. |
| **Symptoms** | Encounter data completeness <85%; MCO quality ratings below state benchmark; network adequacy complaints increasing; state-directed payment calculation errors; HEDIS/CAHPS scores declining |
| **Linked KPIs** | PH-KPI-019, PH-KPI-020 |
| **Linked Value Drivers** | Risk Reduction, Mission Effectiveness, Cost Savings |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (CMS Medicaid Managed Care Final Rule 2024; MACPAC MCO Reports; KFF Medicaid Managed Care Tracker) |

### PH-PAIN-009: Aging and Disability Services Waitlist for Long-Term Care

| Attribute | Detail |
|-----------|--------|
| **Description** | State ADRCs and No Wrong Door systems face demand exceeding capacity. Older adults and people with disabilities wait months for home and community-based services (HCBS), risking institutionalization. Olmstead compliance pressures mount. |
| **Symptoms** | HCBS waiver waitlist >12 months; nursing facility diversion rate <50%; ADRC call answer rate <80%; Olmstead plan noncompliance citations; caregiver turnover >40% |
| **Linked KPIs** | PH-KPI-021, PH-KPI-022 |
| **Linked Value Drivers** | Mission Effectiveness, Risk Reduction, Cost Savings |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (ACL State Plan on Aging; KFF HCBS State Tracker; CMS Olmstead Enforcement Data) |

### PH-PAIN-010: Veterans Benefits and Services Coordination Gaps

| Attribute | Detail |
|-----------|--------|
| **Description** | State veterans agencies struggle to coordinate with federal VA, county veterans service officers, and community providers. Benefits claims backlog, mental health access, and housing navigation require integrated case management. |
| **Symptoms** | State veterans benefits claims backlog >90 days; no shared case file with federal VA; veteran homelessness rate above state average; mental health referral drop-off >30%; county VSO coordination gaps |
| **Linked KPIs** | PH-KPI-023, PH-KPI-024 |
| **Linked Value Drivers** | Mission Effectiveness, Risk Reduction |
| **Prevalence** | MEDIUM |
| **Confidence** | MEDIUM (VA State Veterans Home Reports; NVSOR State Directory; HUD-VASH Data) |

### PH-PAIN-011: Eligibility Worker Productivity and Retention Crisis

| Attribute | Detail |
|-----------|--------|
| **Description** | High turnover (>25% annually in many states), insufficient training, and archaic systems combine to crush eligibility worker productivity. Each vacancy costs $15K-$50K to backfill and delays benefit delivery. |
| **Symptoms** | Eligibility worker turnover >25% annually; time-to-productivity >6 months; caseload per worker >statutory max; training completion <80%; overtime spend >15% of labor budget |
| **Linked KPIs** | PH-KPI-025, PH-KPI-026 |
| **Linked Value Drivers** | Cost Savings, Mission Effectiveness |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (NASCIO Workforce Reports; State HHS workforce studies; APHSA Reports) |

### PH-PAIN-012: TANF Caseload Decline vs. Administrative Cost Rigidity

| Attribute | Detail |
|-----------|--------|
| **Description** | TANF cash assistance caseloads declined 70%+ since 1996, but administrative infrastructure costs remain fixed. States face pressure to redirect TANF funds to work supports, child care, and services while maintaining compliance. |
| **Symptoms** | TANF caseload <25% of 1996 level; administrative cost per case >$500/month; work participation rate <50%; MOE compliance risk; child care co-payment collection <60% |
| **Linked KPIs** | PH-KPI-027, PH-KPI-028 |
| **Linked Value Drivers** | Cost Savings, Mission Effectiveness |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (CLASP TANF Analysis; HHS ACF TANF Financial Data; GAO TANF Reports) |

### PH-PAIN-013: MMIS (Medicaid Management Information System) End-of-Life

| Attribute | Detail |
|-----------|--------|
| **Description** | Many states operate MMIS systems built in the 1990s-2000s on outdated technology. CMS requires modularity, MITA alignment, and cloud-readiness. Replacement costs run $200M-$500M and take 3-5 years. |
| **Symptoms** | MMIS vendor support contract ending <24 months; no API layer for interoperability; claim adjudication time >30 days; system downtime >4 hrs/quarter; CMS MITA maturity <Level 3 |
| **Linked KPIs** | PH-KPI-029, PH-KPI-030 |
| **Linked Value Drivers** | Cost Savings, Risk Reduction, Mission Effectiveness |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (CMS MITA Framework; MACPAC; State MMIS procurement records) |

### PH-PAIN-014: Immunization Registry Interoperability and Coverage Gaps

| Attribute | Detail |
|-----------|--------|
| **Description** | IIS (Immunization Information Systems) lack bidirectional data exchange with EHRs, pharmacies, and federal systems (VAMS, IZ Gateway). COVID-19 highlighted gaps in adult immunization tracking and cross-jurisdictional sharing. |
| **Symptoms** | IIS-EHR bidirectional interface coverage <60%; adult immunization completeness <50%; cross-jurisdictional sharing <30% of providers; provider reporting compliance <70%; vaccine inventory management manual |
| **Linked KPIs** | PH-KPI-031, PH-KPI-032 |
| **Linked Value Drivers** | Risk Reduction, Mission Effectiveness |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (CDC IIS Standards; AIRA IIS Assessment; ONC Interoperability Metrics) |

### PH-PAIN-015: Human Services Data Integration Failure (Cross-Program)

| Attribute | Detail |
|-----------|--------|
| **Description** | Benefit programs (Medicaid, SNAP, TANF, LIHEAP, WIC) operate on separate eligibility systems. Families re-verify income, residency, and household composition multiple times. No unified beneficiary view exists. |
| **Symptoms** | Families submitting same documents to >3 programs; no cross-program eligibility rules engine; income verification conducted independently per program; duplicate benefits across programs >2%; ex parte renewal limited to single program |
| **Linked KPIs** | PH-KPI-033, PH-KPI-034 |
| **Linked Value Drivers** | Cost Savings, Mission Effectiveness, Risk Reduction |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (ACF Integration Reports; Code for America; NASCIO Cross-Program Data Sharing) |

### PH-PAIN-016: Emergency Preparedness and Health Response Coordination

| Attribute | Detail |
|-----------|--------|
| **Description** | Public health emergency preparedness (PHEP) funding has declined in real terms. Coordination between state health departments, emergency management, hospitals, and EMS remains fragmented. SNS and MCM distribution plans lack regular exercise. |
| **Symptoms** | PHEP grant drawdown <80%; HPP hospital coalition participation <70%; SNS inventory rotation backlog; no joint exercise with emergency management >24 months; after-action recommendations unimplemented >50% |
| **Linked KPIs** | PH-KPI-035, PH-KPI-036 |
| **Linked Value Drivers** | Risk Reduction, Mission Effectiveness |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (CDC PHEP Cooperative Agreement; ASPR National Health Security Strategy; FEMA National Preparedness Report) |

### PH-PAIN-017: Child Support Enforcement System Modernization Lag

| Attribute | Detail |
|-----------|--------|
| **Description** | State CSE systems built under federal IV-D requirements face modernization gaps. Intergovernmental case processing, employer interface, and collections tracking require upgrades. Federal incentive funding tied to performance. |
| **Symptoms** | Collections rate <55% of arrearage; IV-D system on unsupported platform; interstate case processing time >180 days; employer reporting interface manual; federal incentive penalty risk |
| **Linked KPIs** | PH-KPI-037, PH-KPI-038 |
| **Linked Value Drivers** | Cost Savings, Revenue Uplift, Risk Reduction |
| **Prevalence** | MEDIUM |
| **Confidence** | MEDIUM (OCSE Federal Reports; GAO Child Support Reports) |

### PH-PAIN-018: CCDF Child Care Subsidy Administration Complexity

| Attribute | Detail |
|-----------|--------|
| **Description** | Child Care and Development Fund (CCDF) administration requires complex eligibility, provider enrollment, attendance tracking, and quality rating integration. States face reauthorization compliance and parent copayment collection challenges. |
| **Symptoms** | CCDF eligibility determination time >30 days; provider reimbursement delay >45 days; attendance tracking manual or paper-based; QRIS integration gaps; parent copayment collection rate <70% |
| **Linked KPIs** | PH-KPI-039, PH-KPI-040 |
| **Linked Value Drivers** | Mission Effectiveness, Cost Savings |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (HHS ACF CCDF State Plans; CLASP CCDF Analysis; NCCIC State Profiles) |

---

## KPI Definitions

### PH-KPI-001: Medicaid Eligibility Determination Time

| Attribute | Detail |
|-----------|--------|
| **Formula** | `AVG(Determination Date - Application Date) for applications resolved in period` |
| **Unit** | Days |
| **Typical Range** | 15-90 days |
| **Benchmark Range** | Federal max: 45 days (90 for disability); best practice: <30 days |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Weekly |

### PH-KPI-002: Ex Parte Renewal Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Ex Parte Renewals Completed / Total Renewals Due * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 20%-70% |
| **Benchmark Range** | CMS target (unwinding): >75%; best practice: >80% |
| **Value Driver Links** | Cost Savings, Mission Effectiveness |
| **Calculation Frequency** | Monthly |

### PH-KPI-003: Medicaid Churn Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `(Disenrollments + Re-enrollments in period) / Average Enrollment * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 5%-30% |
| **Benchmark Range** | Best practice: <10%; concerning: >20% |
| **Value Driver Links** | Cost Savings, Mission Effectiveness |
| **Calculation Frequency** | Monthly |

### PH-KPI-004: SNAP QC Error Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Dollar Error Cases / Total QC Review Cases * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 2%-12% |
| **Benchmark Range** | USDA threshold: <6%; best practice: <3% |
| **Value Driver Links** | Risk Reduction, Cost Savings |
| **Calculation Frequency** | Monthly |

### PH-KPI-005: SNAP Application Processing Timeliness

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Applications Processed Within 30 Days / Total Applications Resolved * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 70%-95% |
| **Benchmark Range** | Federal requirement: >90% within 30 days; expedited: <7 days |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Monthly |

### PH-KPI-006: Child Welfare CPS Response Time

| Attribute | Detail |
|-----------|--------|
| **Formula** | `AVG(Initial Contact Date - Report Receipt Date) for screened-in reports` |
| **Unit** | Hours |
| **Typical Range** | 1-72 hours |
| **Benchmark Range** | Immediate risk: <1 hour; high risk: <24 hours; best practice: <50% of statutory limit |
| **Value Driver Links** | Risk Reduction, Mission Effectiveness |
| **Calculation Frequency** | Weekly |

### PH-KPI-007: AFCARS Data Quality Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `(1 - AFCARS Error Elements / Total Elements Submitted) * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 85%-98% |
| **Benchmark Range** | Federal target: >95%; best practice: >98% |
| **Value Driver Links** | Risk Reduction, Cost Savings |
| **Calculation Frequency** | Semi-annual |

### PH-KPI-008: Recurrence of Maltreatment Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Children with Substantiated Re-report Within 12 Months / Children with Initial Substantiation * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 5%-15% |
| **Benchmark Range** | Best practice: <6%; national median: ~9% |
| **Value Driver Links** | Risk Reduction, Mission Effectiveness |
| **Calculation Frequency** | Annual |

### PH-KPI-009: UI First Payment Timeliness

| Attribute | Detail |
|-----------|--------|
| **Formula** | `First Payments Within 14/21 Days of Filing / Total First Payments * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 60%-95% |
| **Benchmark Range** | Federal target: >87% within 21 days; best practice: >90% |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Weekly |

### PH-KPI-010: UI Improper Payment Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `(Improper UI Payments / Total UI Payments) * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 5%-25% |
| **Benchmark Range** | Federal target: <10%; pandemic peak: >15%; best practice: <5% |
| **Value Driver Links** | Cost Savings, Risk Reduction |
| **Calculation Frequency** | Quarterly |

### PH-KPI-011: UI Identity Verification Resolution Time

| Attribute | Detail |
|-----------|--------|
| **Formula** | `AVG(Verification Complete Date - Hold Start Date) for identity holds` |
| **Unit** | Days |
| **Typical Range** | 3-45 days |
| **Benchmark Range** | Best practice: <7 days; concerning: >21 days |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Weekly |

### PH-KPI-012: Notifiable Disease Reporting Timeliness

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Reports Submitted Within Required Timeframe / Total Notifiable Events * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 60%-95% |
| **Benchmark Range** | CDC target: >90%; best practice: >95% |
| **Value Driver Links** | Risk Reduction, Mission Effectiveness |
| **Calculation Frequency** | Weekly |

### PH-KPI-013: ELR (Electronic Lab Reporting) Coverage

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Labs Reporting Electronically / Total Reporting Labs * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 50%-95% |
| **Benchmark Range** | CMS/CDC target: >95% |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Monthly |

### PH-KPI-014: Behavioral Health Wait Time for Outpatient Services

| Attribute | Detail |
|-----------|--------|
| **Formula** | `AVG(Appointment Date - Request Date) for outpatient non-crisis` |
| **Unit** | Days |
| **Typical Range** | 7-60 days |
| **Benchmark Range** | Best practice: <14 days; concerning: >30 days |
| **Value Driver Links** | Mission Effectiveness |
| **Calculation Frequency** | Monthly |

### PH-KPI-015: 988 Crisis Call Answer Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Crisis Calls Answered / Total Crisis Calls * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 80%-98% |
| **Benchmark Range** | SAMHSA target: >90%; best practice: >95% |
| **Value Driver Links** | Risk Reduction, Mission Effectiveness |
| **Calculation Frequency** | Real-time / Weekly |

### PH-KPI-016: Behavioral Health Integration with Primary Care

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Co-located or Integrated BH-PC Practices / Total Primary Care Practices in Network * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 10%-50% |
| **Benchmark Range** | Best practice: >40%; national baseline: ~20% |
| **Value Driver Links** | Mission Effectiveness, Cost Savings |
| **Calculation Frequency** | Annual |

### PH-KPI-017: Housing Voucher Lease-Up Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Vouchers Leased / Total Vouchers Allocated * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 85%-98% |
| **Benchmark Range** | HUD target: >95%; best practice: >97% |
| **Value Driver Links** | Mission Effectiveness, Cost Savings |
| **Calculation Frequency** | Monthly |

### PH-KPI-018: HQS Inspection Pass Rate on First Inspection

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Units Passing HQS on First Inspection / Total HQS Inspections * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 60%-85% |
| **Benchmark Range** | Best practice: >80%; concerning: <70% |
| **Value Driver Links** | Cost Savings, Mission Effectiveness |
| **Calculation Frequency** | Monthly |

### PH-KPI-019: Medicaid MCO Encounter Data Completeness

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Encounters with Complete Required Data Elements / Total Encounters Submitted * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 70%-92% |
| **Benchmark Range** | CMS target: >85%; best practice: >90% |
| **Value Driver Links** | Risk Reduction, Mission Effectiveness |
| **Calculation Frequency** | Monthly |

### PH-KPI-020: MCO Network Adequacy Ratio

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Available Providers per 1,000 Enrollees / CMS Network Adequacy Standard * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 80%-150% |
| **Benchmark Range** | Federal minimum: 100%; best practice: >120% |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Quarterly |

### PH-KPI-021: HCBS Waiver Waitlist Length

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Individuals on HCBS Waiver Waitlist / Total HCBS Waiver Capacity * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 0%-200% |
| **Benchmark Range** | Best practice: 0%; concerning: >50% |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Monthly |

### PH-KPI-022: ADRC No Wrong Door Contact Resolution Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Contacts Resolved Without Transfer / Total ADRC Contacts * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 60%-90% |
| **Benchmark Range** | ACL target: >80%; best practice: >85% |
| **Value Driver Links** | Mission Effectiveness, Cost Savings |
| **Calculation Frequency** | Monthly |

### PH-KPI-023: Veterans Benefits Claims Processing Time

| Attribute | Detail |
|-----------|--------|
| **Formula** | `AVG(Determination Date - Application Date) for state veterans benefits claims` |
| **Unit** | Days |
| **Typical Range** | 30-120 days |
| **Benchmark Range** | Best practice: <45 days; concerning: >90 days |
| **Value Driver Links** | Mission Effectiveness |
| **Calculation Frequency** | Monthly |

### PH-KPI-024: Veteran Mental Health Referral Completion Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Referrals Completed / Total Referrals * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 50%-80% |
| **Benchmark Range** | Best practice: >75%; concerning: <60% |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Monthly |

### PH-KPI-025: Eligibility Worker Turnover Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Workers Separated / Average Worker Headcount * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 15%-40% |
| **Benchmark Range** | Best practice: <15%; concerning: >25% |
| **Value Driver Links** | Cost Savings, Mission Effectiveness |
| **Calculation Frequency** | Monthly |

### PH-KPI-026: Eligibility Worker Time-to-Productivity

| Attribute | Detail |
|-----------|--------|
| **Formula** | `AVG(Date of Independent Case Processing - Hire Date)` |
| **Unit** | Days |
| **Typical Range** | 60-180 days |
| **Benchmark Range** | Best practice: <90 days; concerning: >120 days |
| **Value Driver Links** | Cost Savings, Mission Effectiveness |
| **Calculation Frequency** | Quarterly |

### PH-KPI-027: TANF Work Participation Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `TANF Participants Meeting Work Requirements / Total TANF Participants * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 20%-60% |
| **Benchmark Range** | Federal target: 50%; best practice: >55% |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Quarterly |

### PH-KPI-028: TANF Administrative Cost Per Case

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Total TANF Administrative Costs / Average Monthly TANF Caseload` |
| **Unit** | USD per case per month |
| **Typical Range** | $200-$800 |
| **Benchmark Range** | Best practice: <$300; concerning: >$500 |
| **Value Driver Links** | Cost Savings |
| **Calculation Frequency** | Monthly |

### PH-KPI-029: MMIS Claim Adjudication Time

| Attribute | Detail |
|-----------|--------|
| **Formula** | `AVG(Adjudication Complete Date - Claim Receipt Date)` |
| **Unit** | Days |
| **Typical Range** | 7-35 days |
| **Benchmark Range** | Best practice: <14 days; concerning: >21 days |
| **Value Driver Links** | Mission Effectiveness, Cost Savings |
| **Calculation Frequency** | Weekly |

### PH-KPI-030: MMIS System Uptime

| Attribute | Detail |
|-----------|--------|
| **Formula** | `(Scheduled Uptime - Unplanned Downtime) / Scheduled Uptime * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 99.0%-99.95% |
| **Benchmark Range** | Best practice: >99.9%; concerning: <99.5% |
| **Value Driver Links** | Risk Reduction, Mission Effectiveness |
| **Calculation Frequency** | Real-time |

### PH-KPI-031: IIS-EHR Bidirectional Interface Coverage

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Providers with Active Bidirectional IIS Interface / Total Providers * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 30%-80% |
| **Benchmark Range** | Best practice: >80%; concerning: <50% |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Annual |

### PH-KPI-032: IIS Adult Immunization Completeness

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Adult Patients with Complete Immunization History / Total Adult Patients in IIS * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 20%-60% |
| **Benchmark Range** | Best practice: >50%; concerning: <30% |
| **Value Driver Links** | Mission Effectiveness |
| **Calculation Frequency** | Annual |

### PH-KPI-033: Cross-Program Duplicate Verification Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Duplicate Verifications Conducted / Total Verifications * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 20%-60% |
| **Benchmark Range** | Best practice: <10%; concerning: >40% |
| **Value Driver Links** | Cost Savings, Mission Effectiveness |
| **Calculation Frequency** | Quarterly |

### PH-KPI-034: Integrated Eligibility System Coverage

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Programs on Unified Eligibility Platform / Total Benefit Programs * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 10%-70% |
| **Benchmark Range** | Best practice: >80%; concerning: <30% |
| **Value Driver Links** | Cost Savings, Mission Effectiveness |
| **Calculation Frequency** | Annual |

### PH-KPI-035: PHEP Grant Drawdown Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `PHEP Funds Drawn Down / Total PHEP Award * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 60%-95% |
| **Benchmark Range** | Best practice: >90%; concerning: <80% |
| **Value Driver Links** | Working Capital, Mission Effectiveness |
| **Calculation Frequency** | Quarterly |

### PH-KPI-036: Joint Public Health-Emergency Management Exercise Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Joint Exercises Conducted / Target Exercises * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 20%-80% |
| **Benchmark Range** | Best practice: >75%; concerning: <40% |
| **Value Driver Links** | Risk Reduction, Mission Effectiveness |
| **Calculation Frequency** | Annual |

### PH-KPI-037: Child Support Collections Rate

| Attribute | Detail |
|-----------|--------|
| **Formula** | `Collections Received / Total Obligations * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 40%-65% |
| **Benchmark Range** | Best practice: >60%; concerning: <50% |
| **Value Driver Links** | Revenue Uplift, Mission Effectiveness |
| **Calculation Frequency** | Monthly |

### PH-KPI-038: Interstate Child Support Case Processing Time

| Attribute | Detail |
|-----------|--------|
| **Formula** | `AVG(Case Resolution Date - Interstate Referral Date)` |
| **Unit** | Days |
| **Typical Range** | 90-270 days |
| **Benchmark Range** | Best practice: <180 days; concerning: >240 days |
| **Value Driver Links** | Mission Effectiveness, Cost Savings |
| **Calculation Frequency** | Monthly |

### PH-KPI-039: CCDF Eligibility Determination Timeliness

| Attribute | Detail |
|-----------|--------|
| **Formula** | `CCDF Applications Processed Within 30 Days / Total Applications * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 70%-95% |
| **Benchmark Range** | Best practice: >90%; concerning: <80% |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Calculation Frequency** | Monthly |

### PH-KPI-040: CCDF Provider Reimbursement Cycle Time

| Attribute | Detail |
|-----------|--------|
| **Formula** | `AVG(Payment Date - Submission Date) for provider reimbursement claims` |
| **Unit** | Days |
| **Typical Range** | 15-60 days |
| **Benchmark Range** | Best practice: <21 days; concerning: >35 days |
| **Value Driver Links** | Mission Effectiveness, Cost Savings |
| **Calculation Frequency** | Monthly |

---

## Value Drivers

| ID | Signal Pattern | Interpreted Pain | Value Driver Category | Linked KPIs | Affected Personas | Confidence |
|----|---------------|------------------|----------------------|-------------|------------------|------------|
| PH-VD-001 | Eligibility determination time >45 days; ex parte rate <40%; churn >15% | PH-PAIN-001 | Cost Savings | PH-KPI-001, PH-KPI-002, PH-KPI-003 | Medicaid Director, Eligibility Supervisor | HIGH |
| PH-VD-002 | SNAP QC error rate >6%; USDA corrective action pending; worker turnover >25% | PH-PAIN-002 | Risk Reduction | PH-KPI-004, PH-KPI-005 | Medicaid Director, Eligibility Supervisor | HIGH |
| PH-VD-003 | Caseworkers using >10 systems; AFCARS error rate >5%; recurrence of maltreatment >10% | PH-PAIN-003 | Risk Reduction | PH-KPI-006, PH-KPI-007, PH-KPI-008 | Child Welfare Supervisor, Eligibility Supervisor | HIGH |
| PH-VD-004 | UI claims pending >21 days >10%; overpayment balance growing; identity hold queue >30 days | PH-PAIN-004 | Cost Savings | PH-KPI-009, PH-KPI-010, PH-KPI-011 | UI Claims Director, Eligibility Supervisor | HIGH |
| PH-VD-005 | Disease report notification >7 days; manual faxed lab reports; syndromic surveillance coverage <80% | PH-PAIN-005 | Risk Reduction | PH-KPI-012, PH-KPI-013 | Public Health Officer | HIGH |
| PH-VD-006 | Behavioral health wait time >30 days; psychiatrist vacancy >20%; crisis call abandonment >5% | PH-PAIN-006 | Mission Effectiveness | PH-KPI-014, PH-KPI-015, PH-KPI-016 | BH Program Director, Eligibility Supervisor | HIGH |
| PH-VD-007 | Housing voucher waitlist >5,000; wait time >24 months; landlord participation declining | PH-PAIN-007 | Mission Effectiveness | PH-KPI-017, PH-KPI-018 | Eligibility Supervisor | HIGH |
| PH-VD-008 | MCO encounter completeness <85%; network adequacy complaints up; HEDIS scores declining | PH-PAIN-008 | Risk Reduction | PH-KPI-019, PH-KPI-020 | Medicaid Director, Public Health Officer | HIGH |
| PH-VD-009 | HCBS waitlist >12 months; nursing facility diversion <50%; Olmstead plan citation | PH-PAIN-009 | Mission Effectiveness | PH-KPI-021, PH-KPI-022 | BH Program Director, Eligibility Supervisor | HIGH |
| PH-VD-010 | Eligibility worker turnover >25%; time-to-productivity >6 months; caseload >statutory max | PH-PAIN-011 | Cost Savings | PH-KPI-025, PH-KPI-026 | Medicaid Director, Eligibility Supervisor | HIGH |
| PH-VD-011 | MMIS vendor contract ending <24 months; claim adjudication >30 days; no API layer | PH-PAIN-013 | Cost Savings | PH-KPI-029, PH-KPI-030 | Medicaid Director, Public Health Officer | HIGH |
| PH-VD-012 | Families submitting same docs to >3 programs; no cross-program rules engine; duplicate benefits >2% | PH-PAIN-015 | Cost Savings | PH-KPI-033, PH-KPI-034 | Medicaid Director, Eligibility Supervisor | HIGH |

---

## Value Formulas

### PH-VF-001: Medicaid Churn Cost Avoidance

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = (Baseline_Churn_% - Target_Churn_%) * Average_Enrollment * (Admin_Cost_Per_Churn_Event + Gap_In_Care_Cost)` |
| **Required Inputs** | Baseline churn %, Target churn %, Average enrollment, Admin cost per churn event ($), Gap-in-care cost ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Medicaid, SNAP, CHIP |
| **Confidence Rules** | HIGH if state administrative data available; MEDIUM if using KFF estimates; LOW if enrollment unknown |
| **Example** | 18%→8% churn on 800K enrollees, $120/admin cost, $180 gap cost: 80K * $300 = $24M annual |

### PH-VF-002: Ex Parte Renewal Efficiency Value

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = (Renewals_Shifted_to_ExParte * Manual_Renewal_Cost) + Churn_Reduction_Value + CMS_Compliance_Avoidance` |
| **Required Inputs** | Renewals shifted to ex parte (count), Manual renewal cost ($), Churn reduction value ($), CMS compliance risk value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Medicaid, SNAP |
| **Confidence Rules** | HIGH if eligibility system data available; MEDIUM if using state averages; LOW if no renewal volume |
| **Example** | 150K renewals shifted, $30 manual cost, $2M churn value, $500K compliance: $4.5M + $2M + $500K = $7M |

### PH-VF-003: SNAP Error Rate Reduction Value

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = Total_SNAP_Outlay * (Baseline_Error_% - Target_Error_%) * Federal_Funding_Share + Avoided_USDA_Corrective_Action_Cost` |
| **Required Inputs** | Total SNAP outlay ($), Baseline error rate (%), Target error rate (%), Federal funding share (%), Corrective action cost ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | SNAP |
| **Confidence Rules** | HIGH if USDA QC data available; MEDIUM if using state average; LOW if outlay unknown |
| **Example** | $500M outlay, 8%→4% error, 50% federal share, $1M corrective action: $500M * 0.04 * 0.5 + $1M = $11M |

### PH-VF-004: Child Welfare Case Management Consolidation Value

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = Systems_Consolidated * Maintenance_Cost_Per_System + Caseworker_Hours_Saved * Loaded_Rate + Recurrence_Reduction_Value` |
| **Required Inputs** | Systems consolidated (count), Maintenance cost per system ($), Hours saved per caseworker annually, Loaded hourly rate ($), Number of caseworkers, Recurrence reduction value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Child Welfare |
| **Confidence Rules** | HIGH if system and staffing data available; MEDIUM if estimated; LOW if no case volume |
| **Example** | 8 systems consolidated @ $200K each + 500 caseworkers * 100 hrs * $45 + $2M = $5.85M |

### PH-VF-005: UI Fraud and Improper Payment Reduction

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = Total_UI_Payments * (Baseline_IP_Rate - Target_IP_Rate) * Recovery_Rate + Trust_Fund_Solvency_Improvement` |
| **Required Inputs** | Total UI payments ($), Baseline IP rate (%), Target IP rate (%), Recovery rate (%), Trust fund solvency value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Unemployment Insurance |
| **Confidence Rules** | HIGH if DOL ETA data available; MEDIUM if using GAO estimates; LOW if payment volume unknown |
| **Example** | $1B payments, 15%→6% IP, 40% recovery, $500K solvency: $1B * 0.09 * 0.4 + $500K = $36.5M |

### PH-VF-006: Disease Surveillance Modernization Value

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = (Manual_Report_Hours_Eliminated * Labor_Rate) + Outbreak_Detection_Acceleration_Value + ELR_Implementation_Rebate + Avoided_CMS_Penalty` |
| **Required Inputs** | Manual report hours eliminated annually, Loaded labor rate ($), Outbreak detection acceleration value ($), ELR rebate ($), CMS penalty avoidance ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Disease Surveillance, Public Health |
| **Confidence Rules** | HIGH if time-motion and outbreak cost data available; MEDIUM if using CDC estimates; LOW if baseline unknown |
| **Example** | 20K hrs * $55 + $3M + $500K + $200K = $4.8M |

### PH-VF-007: Behavioral Health Access Expansion Value

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = (Wait_Time_Reduction_Days * Patients_Seen_Additionally * Revenue_Per_Visit) + Crisis_Diversion_Savings + ED_Diversion_Savings` |
| **Required Inputs** | Wait time reduction (days), Additional patients seen annually, Revenue per visit ($), Crisis diversion savings ($), ED diversion savings ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Behavioral Health, Medicaid |
| **Confidence Rules** | MEDIUM if provider network and claims data available; LOW if patient volume unknown |
| **Example** | 20-day reduction * 5K patients * $200 + $2M + $3M = $15M |

### PH-VF-008: Housing Voucher Throughput Optimization

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = (Additional_Lease_Ups * Per_Voucher_Annual_Subsidy) + Inspection_Efficiency_Savings + Landlord_Retention_Value` |
| **Required Inputs** | Additional lease-ups annually, Per voucher annual subsidy ($), Inspection efficiency savings ($), Landlord retention value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Housing Assistance |
| **Confidence Rules** | HIGH if PHA data available; MEDIUM if using HUD averages; LOW if no voucher count |
| **Example** | 500 additional lease-ups * $12K + $300K + $200K = $6.5M |

### PH-VF-009: MCO Encounter Data Improvement Value

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = (Encounter_Completeness_Gain * Total_Encounters * Cost_Per_Correction) + CMS_Compliance_Avoidance + Rate_Setting_Accuracy_Gain` |
| **Required Inputs** | Encounter completeness gain (%), Total encounters, Cost per correction ($), CMS compliance value ($), Rate-setting accuracy gain ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Medicaid |
| **Confidence Rules** | HIGH if MCO data available; MEDIUM if using CMS estimates; LOW if encounter volume unknown |
| **Example** | 10% gain * 5M encounters * $2 + $1M + $2M = $4M |

### PH-VF-010: HCBS Waitlist Reduction Value

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = (Waitlist_Reduction * Cost_Per_Institutional_Day_Avoided * 365) + Olmstead_Compliance_Avoidance + Caregiver_Retention_Value` |
| **Required Inputs** | Waitlist reduction (count), Institutional cost per day avoided ($), Olmstead compliance value ($), Caregiver retention value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Aging / Disability |
| **Confidence Rules** | HIGH if state HCBS and nursing facility cost data available; MEDIUM if using KFF estimates; LOW if waitlist unknown |
| **Example** | 1,000 waitlist reduction * $250/day * 365 + $2M + $500K = $93.75M (requires confidence adjustment) |

### PH-VF-011: Eligibility Worker Retention Value

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = Turnover_Reduction_Count * (Recruitment_Cost + Training_Cost + Productivity_Loss_Cost) + Overtime_Reduction + Backlog_Cost_Avoidance` |
| **Required Inputs** | Turnover reduction (count), Recruitment cost per FTE ($), Training cost per FTE ($), Productivity loss cost ($), Overtime reduction ($), Backlog cost avoidance ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Medicaid, SNAP, UI |
| **Confidence Rules** | HIGH if HRIS and payroll data available; MEDIUM if using industry estimates; LOW if no turnover data |
| **Example** | 50 turnover reduction * ($15K + $10K + $20K) + $500K + $1M = $3.75M |

### PH-VF-012: Cross-Program Eligibility Integration Value

| Attribute | Detail |
|-----------|--------|
| **Formula** | `V = Duplicate_Verification_Hours_Eliminated * Labor_Rate + Error_Reduction_Value + Citizen_Satisfaction_Improvement_Value + ExParte_Expansion_Value` |
| **Required Inputs** | Duplicate verification hours eliminated, Loaded labor rate ($), Error reduction value ($), Citizen satisfaction value ($), Ex parte expansion value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Sub-Segments** | Medicaid, SNAP, TANF, Housing |
| **Confidence Rules** | HIGH if cross-program time-motion data available; MEDIUM if estimated; LOW if no integration scope defined |
| **Example** | 100K hrs * $50 + $2M + $1M + $3M = $11M |

---

## Benchmarks

| ID | Name | Value | Range | Unit | Source | Confidence | Year |
|----|------|-------|-------|------|--------|-----------|------|
| PH-BENCH-001 | Medicaid Eligibility Determination Time (National Median) | 28 | 15-60 days | Days | CMS T-MSIS; KFF | MEDIUM | 2023 |
| PH-BENCH-002 | Medicaid National Improper Payment Rate | 8.3% | 7%-15% | Percentage | OMB PaymentAccuracy.gov | HIGH | 2023 |
| PH-BENCH-003 | SNAP National QC Error Rate | 9.5% | 8%-12% | Percentage | USDA SNAP QC FY2023 | HIGH | 2023 |
| PH-BENCH-004 | SNAP Timeliness Rate (National) | 88% | 75%-98% | Percentage | USDA FNS | HIGH | 2023 |
| PH-BENCH-005 | UI First Payment Timeliness (National) | 82% | 60%-95% | Percentage | DOL ETA | HIGH | 2023 |
| PH-BENCH-006 | UI Improper Payment Rate (Post-Pandemic) | 12% | 5%-25% | Percentage | GAO-23-105474 | HIGH | 2023 |
| PH-BENCH-007 | CPS Response Time (High Risk) | 24 hrs | 1-72 hrs | Hours | HHS ACF | HIGH | 2022 |
| PH-BENCH-008 | Recurrence of Maltreatment (National) | 9.1% | 5%-15% | Percentage | HHS ACF | HIGH | 2022 |
| PH-BENCH-009 | Behavioral Health Wait Time (Median) | 21 days | 7-60 days | Days | SAMHSA; NAMI | MEDIUM | 2023 |
| PH-BENCH-010 | 988 Crisis Line Answer Rate (National) | 91% | 80%-98% | Percentage | SAMHSA | HIGH | 2024 |
| PH-BENCH-011 | Housing Choice Voucher Lease-Up Rate | 94% | 85%-98% | Percentage | HUD | HIGH | 2023 |
| PH-BENCH-012 | PHA HQS First Inspection Pass Rate | 75% | 60%-85% | Percentage | HUD | MEDIUM | 2023 |
| PH-BENCH-013 | Medicaid MCO Encounter Completeness | 82% | 70%-92% | Percentage | CMS | MEDIUM | 2023 |
| PH-BENCH-014 | HCBS Waiver Waitlist (States with Backlogs) | 650K | 400K-1M | Individuals | KFF | MEDIUM | 2023 |
| PH-BENCH-015 | Notifiable Disease Reporting Timeliness | 4.2 days | 1-14 days | Days | CDC NNDSS | MEDIUM | 2023 |
| PH-BENCH-016 | ELR Coverage (National) | 78% | 50%-95% | Percentage | CDC; ONC | MEDIUM | 2023 |
| PH-BENCH-017 | Eligibility Worker Turnover (Human Services) | 27% | 15%-40% | Percentage | APHSA | MEDIUM | 2023 |
| PH-BENCH-018 | MMIS Claim Adjudication Time (Legacy) | 18 days | 7-35 days | Days | State MMIS; CMS | MEDIUM | 2023 |

---

## Signal Interpretation Rules

### PH-SIG-001: Medicaid Eligibility Backlog Surge

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | Eligibility determination time >45 days growing 10%+ MoM; ex parte renewal rate <40%; CMS corrective action plan issued |
| **Interpreted Meaning** | State eligibility systems and staffing cannot handle redetermination volume; CMS compliance risk; coverage gap crisis for vulnerable populations |
| **Linked Pain** | PH-PAIN-001 |
| **Linked KPIs** | PH-KPI-001, PH-KPI-002, PH-KPI-003 |
| **Confidence Score** | 0.92 |
| **Required Confirmation Signals** | CMS-64 reports, State eligibility system backlog report, CMS T-MSIS data, Worker caseload analysis |

### PH-SIG-002: SNAP QC Error Rate Above Threshold

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | SNAP QC error rate >6% for 2+ quarters; USDA corrective action notice; worker training completion <70% |
| **Interpreted Meaning** | Eligibility determination accuracy declining; federal funding at risk; worker competency and system verification gaps |
| **Linked Pain** | PH-PAIN-002 |
| **Linked KPIs** | PH-KPI-004, PH-KPI-005 |
| **Confidence Score** | 0.88 |

### PH-SIG-003: Child Welfare System Fragmentation

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | Caseworkers using >10 systems; AFCARS error rate >5%; recurrence of maltreatment >10% |
| **Interpreted Meaning** | Child safety data scattered across silos; case history gaps endanger children; federal compliance failing; worker productivity crushed by system switching |
| **Linked Pain** | PH-PAIN-003 |
| **Linked KPIs** | PH-KPI-006, PH-KPI-007, PH-KPI-008 |
| **Confidence Score** | 0.90 |

### PH-SIG-004: UI Claims and Fraud Backlog

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | Claims pending >21 days >10% of volume; identity verification queue >30 days; overpayment balance growing >$500M |
| **Interpreted Meaning** | UI system overwhelmed by volume and fraud prevention requirements; trust fund solvency at risk; claimant experience severely degraded |
| **Linked Pain** | PH-PAIN-004 |
| **Linked KPIs** | PH-KPI-009, PH-KPI-010, PH-KPI-011 |
| **Confidence Score** | 0.89 |

### PH-SIG-005: Public Health Surveillance Data Latency

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | Notifiable disease reporting >7 days; manual fax/phone lab reporting observed; syndromic surveillance coverage <80% of EDs |
| **Interpreted Meaning** | Outbreak detection delayed by days to weeks; CDC DMI mandate unfulfilled; EHR interoperability gaps; public health risk elevated |
| **Linked Pain** | PH-PAIN-005 |
| **Linked KPIs** | PH-KPI-012, PH-KPI-013 |
| **Confidence Score** | 0.87 |

### PH-SIG-006: Behavioral Health Access Crisis

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | Outpatient wait time >30 days; psychiatrist vacancy rate >20%; 988 call abandonment >5% |
| **Interpreted Meaning** | Provider shortage and system capacity inadequate; crisis diversion to ED and law enforcement; SAMHSA block grant requirements unmet |
| **Linked Pain** | PH-PAIN-006 |
| **Linked KPIs** | PH-KPI-014, PH-KPI-015, PH-KPI-016 |
| **Confidence Score** | 0.85 |

### PH-SIG-007: Housing Voucher Utilization Decline

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | Lease-up rate <90%; waitlist growing >10% annually; landlord participation rate declining |
| **Interpreted Meaning** | PHA administrative capacity insufficient; inspection and processing bottlenecks; affordable housing crisis worsening |
| **Linked Pain** | PH-PAIN-007 |
| **Linked KPIs** | PH-KPI-017, PH-KPI-018 |
| **Confidence Score** | 0.82 |

### PH-SIG-008: Medicaid MCO Oversight Gaps

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | MCO encounter completeness <85%; network adequacy complaints increasing; HEDIS scores below 50th percentile |
| **Interpreted Meaning** | State MCO oversight infrastructure inadequate; beneficiary access at risk; CMS 438 subpart D compliance gaps; rate-setting data unreliable |
| **Linked Pain** | PH-PAIN-008 |
| **Linked KPIs** | PH-KPI-019, PH-KPI-020 |
| **Confidence Score** | 0.86 |

### PH-SIG-009: HCBS Waitlist and Olmstead Pressure

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | HCBS waiver waitlist >12 months; nursing facility admissions increasing; Olmstead plan citation or settlement |
| **Interpreted Meaning** | Community-based services capacity insufficient; institutionalization preference growing; CMS enforcement risk; civil rights compliance at stake |
| **Linked Pain** | PH-PAIN-009 |
| **Linked KPIs** | PH-KPI-021, PH-KPI-022 |
| **Confidence Score** | 0.88 |

### PH-SIG-010: Eligibility Worker Retention Crisis

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | Turnover >25% annually; time-to-productivity >6 months; caseload per worker >statutory maximum |
| **Interpreted Meaning** | Human services workforce in crisis; training investment lost; service quality and timeliness severely degraded |
| **Linked Pain** | PH-PAIN-011 |
| **Linked KPIs** | PH-KPI-025, PH-KPI-026 |
| **Confidence Score** | 0.84 |

### PH-SIG-011: MMIS End-of-Life Risk

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | MMIS contract ending <24 months; claim adjudication >30 days; no API or interoperability layer; CMS MITA <Level 3 |
| **Interpreted Meaning** | Medicaid payment system at end of life; vendor lock-in risk; modernization required for CMS compliance; $200M+ replacement pending |
| **Linked Pain** | PH-PAIN-013 |
| **Linked KPIs** | PH-KPI-029, PH-KPI-030 |
| **Confidence Score** | 0.91 |

### PH-SIG-012: Cross-Program Eligibility Silos

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | Families submitting same documents to >3 programs; no cross-program income verification; duplicate benefits detected |
| **Interpreted Meaning** | Program-centric systems creating administrative waste and beneficiary burden; integrated eligibility not implemented; federal streamlined verification mandate unfulfilled |
| **Linked Pain** | PH-PAIN-015 |
| **Linked KPIs** | PH-KPI-033, PH-KPI-034 |
| **Confidence Score** | 0.87 |

### PH-SIG-013: Public Health Emergency Preparedness Gap

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | PHEP grant drawdown <80%; HPP hospital coalition participation <70%; SNS inventory rotation backlog; no joint exercise >24 months |
| **Interpreted Meaning** | Emergency preparedness funding underutilized; coordination systems inadequate; next pandemic or bioterror event response at risk |
| **Linked Pain** | PH-PAIN-016 |
| **Linked KPIs** | PH-KPI-035, PH-KPI-036 |
| **Confidence Score** | 0.83 |

### PH-SIG-014: Immunization Registry Fragmentation

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | IIS-EHR bidirectional interface <60%; adult immunization completeness <50%; cross-jurisdictional sharing <30% |
| **Interpreted Meaning** | Immunization tracking inadequate for adult and cross-state populations; EHR integration gaps; CDC IIS functional standards unmet |
| **Linked Pain** | PH-PAIN-014 |
| **Linked KPIs** | PH-KPI-031, PH-KPI-032 |
| **Confidence Score** | 0.80 |

### PH-SIG-015: TANF Administrative Cost Rigidity

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | TANF caseload <25% of 1996 level; admin cost per case >$500/month; work participation rate <50% |
| **Interpreted Meaning** | Fixed administrative infrastructure serving shrinking caseload; TANF funds not redirected to services; federal compliance at risk |
| **Linked Pain** | PH-PAIN-012 |
| **Linked KPIs** | PH-KPI-027, PH-KPI-028 |
| **Confidence Score** | 0.81 |

### PH-SIG-016: Child Support Enforcement System Lag

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | Collections rate <55%; IV-D system on unsupported platform; interstate processing >180 days |
| **Interpreted Meaning** | Technology and process gaps limiting child support collections; federal incentive funding at risk; families not receiving support |
| **Linked Pain** | PH-PAIN-017 |
| **Linked KPIs** | PH-KPI-037, PH-KPI-038 |
| **Confidence Score** | 0.78 |

### PH-SIG-017: CCDF Subsidy Administration Bottleneck

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | CCDF eligibility determination >30 days; provider reimbursement delay >45 days; attendance tracking paper-based |
| **Interpreted Meaning** | Child care subsidy delivery inefficient; provider cash flow strained; parent employment at risk; CCDF reauthorization requirements unmet |
| **Linked Pain** | PH-PAIN-018 |
| **Linked KPIs** | PH-KPI-039, PH-KPI-040 |
| **Confidence Score** | 0.82 |

### PH-SIG-018: Veterans Services Coordination Gap

| Attribute | Detail |
|-----------|--------|
| **Raw Signal Pattern** | State veterans claims backlog >90 days; no data sharing with federal VA; veteran homelessness rate above state average |
| **Interpreted Meaning** | State-federal veterans coordination broken; benefits not reaching veterans; mental health and housing navigation siloed |
| **Linked Pain** | PH-PAIN-010 |
| **Linked KPIs** | PH-KPI-023, PH-KPI-024 |
| **Confidence Score** | 0.75 |

---

## Evidence Sources

| ID | Name | Access Method | Confidence | Update Frequency | Key Uses |
|----|------|---------------|-----------|-------------------|----------|
| PH-EVID-001 | CMS Medicaid Data (T-MSIS, MSIS, CMS-64) | CMS.gov; state requests | HIGH | Monthly to annual | Enrollment trends, eligibility timeliness, churn, financial management |
| PH-EVID-002 | KFF (Kaiser Family Foundation) | KFF.org | HIGH | Continuous | State Medicaid spending, enrollment, waiver activity, policy analysis |
| PH-EVID-003 | USDA SNAP QC and State Performance Data | FNS.USDA.gov | HIGH | Annual QC; monthly performance | Error rate baseline, timeliness, corrective action status |
| PH-EVID-004 | DOL ETA UI Performance Data (901/902 Reports) | DOL.gov/oui | HIGH | Quarterly | First payment timeliness, overpayment rates, trust fund solvency |
| PH-EVID-005 | HHS ACF Child Welfare Data (AFCARS, NCANDS) | ACF.HHS.gov | HIGH | Semi-annual/annual | Placement data, maltreatment recurrence, permanency outcomes |
| PH-EVID-006 | CDC Surveillance and DMI Data | CDC.gov | HIGH | Weekly to annual | Reporting timeliness, ELR coverage, outbreak detection |
| PH-EVID-007 | SAMHSA Behavioral Health Block Grant Reports | SAMHSA.gov | HIGH | Annual | Block grant utilization, crisis system metrics, provider capacity |
| PH-EVID-008 | HUD Housing Program Data (VMS, Picture, PHA Plans) | HUD.gov | HIGH | Annual to monthly | Voucher utilization, waitlist length, PHA performance |
| PH-EVID-009 | CMS MITA and MMIS Procurement Data | CMS.gov; state portals | HIGH | Annual/continuous | MITA maturity, MMIS replacement timing, procurement scope |
| PH-EVID-010 | MACPAC | MACPAC.gov | HIGH | Quarterly/annual | MCO oversight, payment policy, access analysis |

---

## Buying Triggers

| ID | Trigger Event | Urgency | Typical Timing | Affected Sub-Segments | Procurement Implications |
|----|---------------|---------|---------------|----------------------|------------------------|
| PH-TRIG-001 | Medicaid Redetermination / Unwinding Wave | CRITICAL | Monthly cycles; quarterly CMS reporting | Medicaid | Eligibility system procurement; call center expansion; ex parte automation; staff augmentation |
| PH-TRIG-002 | SNAP QC Error Rate Penalty | HIGH | 30-90 days after USDA notification | SNAP | Eligibility system upgrades; worker training technology; verification automation; quality monitoring |
| PH-TRIG-003 | CMS Medicaid Managed Care Final Rule Compliance | HIGH | 12-24 months before effective date | Medicaid | MCO oversight platform; encounter data validation; network adequacy monitoring; equity analysis |
| PH-TRIG-004 | MMIS Contract Recompete / End-of-Life | HIGH | 18-36 months before contract end | Medicaid | Multi-hundred-million RFP; modular MMIS; claims processing replacement; interoperability platform |
| PH-TRIG-005 | UI System Modernization Mandate (DOL) | HIGH | 6-18 months post-guidance | UI | UI benefits system replacement; identity verification platform; fraud detection analytics; cloud migration |
| PH-TRIG-006 | Child Welfare Case Management RFP | HIGH | 6-24 months post-citation or plan | Child Welfare | Unified case management system; predictive analytics; family search and engagement; mobile tools |
| PH-TRIG-007 | CDC Data Modernization Initiative (DMI) Funding | HIGH | Grant award within 90 days; implementation 12-36 months | Disease Surveillance, Public Health | Surveillance system modernization; ELR interfaces; analytics platform; cloud infrastructure |
| PH-TRIG-008 | 988 Crisis Lifeline Expansion Grant | HIGH | 90-180 days post-award | Behavioral Health | Crisis call center platform; mobile dispatch; behavioral health EHR; data reporting to SAMHSA |
| PH-TRIG-009 | HUD PHA Modernization / MTW Expansion | MEDIUM | 6-18 months post-award or declaration | Housing | PHA ERP replacement; landlord portal; inspection mobile app; waitlist management |
| PH-TRIG-010 | Olmstead Plan Enforcement or Settlement | CRITICAL | Immediate upon notice; 12-36 month compliance window | Aging / Disability, Medicaid | HCBS case management; diversion assessment tools; housing navigation; employment supports platform |
| PH-TRIG-011 | Federal HHS Grant (NOFO) | HIGH | 45-90 day response window | Medicaid, Child Welfare, Behavioral Health, Aging / Disability | Grant-funded technology procurement; compliance-driven requirements; federal approval process (APD for Medicaid) |
| PH-TRIG-012 | State HHS Agency Consolidation | MEDIUM | 12-36 months implementation | Medicaid, SNAP, Child Welfare, Behavioral Health | Enterprise integration platform; unified eligibility system; data warehouse; cross-program case management |
| PH-TRIG-013 | Federal ACA / Marketplace Special Enrollment Period | HIGH | 30-90 days before enrollment period | Medicaid | Eligibility and enrollment system scaling; marketplace interface; navigator support tools |
| PH-TRIG-014 | Public Health Emergency Declaration / Pandemic Response | CRITICAL | Immediate; procurement within 30-60 days | Public Health, Disease Surveillance, Medicaid, Behavioral Health | Emergency contact tracing; vaccine management; surveillance surge; telehealth expansion; crisis services |

---

## Persona Profiles

### PH-PERS-001: Medicaid Director / State Medicaid Director (SMD)

| Attribute | Detail |
|-----------|--------|
| **Role** | Leads State Medicaid Agency; oversees $1B-$50B program; manages CMS federal-state partnership, waivers, and MCO contracts |
| **Seniority** | Executive / Cabinet-level appointee or SES equivalent |
| **Goals** | Maintain CMS compliance and federal matching; control state share growth; improve enrollee access and outcomes; modernize MMIS and eligibility systems; optimize MCO value and network adequacy |
| **Pressures** | CMS audits and corrective action; state budget constraints; Medicaid unwinding / redetermination backlog; Olmstead and equity mandates; MMIS end-of-life; provider rate disputes; federal rule changes (438, DSH, UPL) |
| **Trusted Evidence** | CMS guidance and transmittals; MACPAC reports; KFF state comparisons; State Medical Society input; MCO performance data; GAO Medicaid reports |
| **Disliked Claims** | One-size-fits-all solutions; vendor lock-in without CMS modularity; solutions ignoring CMS approval timelines; underestimating state share impact |
| **Decision Influence** | Economic (budget, federal matching, state share) |

### PH-PERS-002: Public Health Officer / State Epidemiologist

| Attribute | Detail |
|-----------|--------|
| **Role** | Leads state or local health department; oversees disease surveillance, outbreak response, environmental health, and health promotion |
| **Seniority** | Department Head / Appointed official |
| **Goals** | Prevent and control disease outbreaks; achieve CDC surveillance targets; modernize public health data infrastructure; secure PHEP and grant funding; improve health equity outcomes |
| **Pressures** | CDC Data Modernization Initiative deadlines; EHR interoperability gaps; PHEP grant drawdown requirements; staff vacancies in epidemiology and lab; outbreak response 24/7 demands; political pressure on health mandates |
| **Trusted Evidence** | CDC guidance and DMI roadmap; CSTE standards; PHII frameworks; Peer state health department case studies; NIH/CDC research; After-action reports |
| **Disliked Claims** | Technology without epidemiologist input; solutions that don't work in outbreak conditions; data platforms without HL7/FHIR support; vendor hype without public health validation |
| **Decision Influence** | Technical (data, surveillance, interoperability) |

### PH-PERS-003: Child Welfare Case Manager Supervisor

| Attribute | Detail |
|-----------|--------|
| **Role** | Supervises frontline child welfare staff; manages caseloads, safety assessments, placement decisions, and court documentation |
| **Seniority** | Mid-level Supervisor |
| **Goals** | Ensure child safety and permanency; reduce caseworker turnover; meet court and federal timelines; maintain AFCARS data quality; support worker wellbeing |
| **Pressures** | Caseloads exceeding standards; AFCARS compliance deadlines; court filing deadlines; system downtime during critical investigations; high staff turnover and training burden; recurrence of maltreatment scrutiny |
| **Trusted Evidence** | AFCARS feedback; HHS CFSR results; Court performance data; Caseworker feedback; Case review findings; Peer state child welfare metrics |
| **Disliked Claims** | Technology that adds paperwork; systems that don't reflect field reality; caseload management without safety prioritization; solutions requiring caseworkers to be data entry clerks |
| **Decision Influence** | User (frontline operations, worker experience) |

### PH-PERS-004: Unemployment Insurance Claims Director

| Attribute | Detail |
|-----------|--------|
| **Role** | Leads UI claims processing, adjudication, overpayment recovery, and trust fund administration; reports to state labor agency head |
| **Seniority** | Director-level |
| **Goals** | Achieve DOL ETA timeliness targets; reduce improper payments and fraud; maintain trust fund solvency; modernize claims and tax systems; improve claimant experience |
| **Pressures** | DOL ETA performance targets and sanctions; pandemic-era overpayment recovery backlog; identity theft and organized fraud; benefit level legislative changes; federal UI modernization mandates; legacy system technical debt |
| **Trusted Evidence** | DOL ETA 901/902 reports; UI trust fund actuarial data; GAO UI reports; Peer state UI performance; Fraud detection analytics; Claimant satisfaction surveys |
| **Disliked Claims** | Fraud solutions that deny legitimate claimants; modernization without claims processor input; solutions ignoring federal reporting requirements; underestimating trust fund complexity |
| **Decision Influence** | Economic (trust fund solvency, federal sanctions, overpayment recovery) |

### PH-PERS-005: Eligibility Worker Supervisor

| Attribute | Detail |
|-----------|--------|
| **Role** | Supervises eligibility determination staff across Medicaid, SNAP, TANF, and other means-tested programs; manages workflow, quality, and training |
| **Seniority** | Mid-level Supervisor |
| **Goals** | Meet timeliness and accuracy standards; manage worker productivity and retention; ensure federal compliance; minimize client complaints; optimize verification processes |
| **Pressures** | Worker turnover >25%; caseload per worker exceeding max; federal QC audits; system downtime; policy changes requiring retraining; client complaints to elected officials |
| **Trusted Evidence** | State QC data; Federal audit results; Worker feedback surveys; Client complaint logs; Caseload analysis; Training completion metrics |
| **Disliked Claims** | Automation that eliminates jobs without notice; systems increasing worker burden; undocumented policy changes in software; solutions ignoring language access needs |
| **Decision Influence** | User (frontline operations, worker wellbeing, service quality) |

### PH-PERS-006: Behavioral Health Program Director

| Attribute | Detail |
|-----------|--------|
| **Role** | Leads state or county behavioral health authority; manages SAMHSA block grants, Medicaid behavioral health benefits, crisis systems, and provider network |
| **Seniority** | Director / Department Head |
| **Goals** | Expand access to mental health and SUD services; achieve SAMHSA block grant outcomes; scale crisis services (988, mobile crisis); integrate behavioral health with primary care; reduce ED and justice system diversion |
| **Pressures** | SAMHSA reporting and audit requirements; 988 crisis line implementation; provider shortage and reimbursement rates; opioid settlement fund management; criminal justice diversion mandates; Medicaid MCO behavioral health carve-out complexity |
| **Trusted Evidence** | SAMHSA National Survey; State block grant reports; Peer state behavioral health comparisons; Criminal justice diversion data; Provider network analysis; Crisis system metrics |
| **Disliked Claims** | Technology replacing therapeutic relationships; solutions without lived experience input; crisis tools without 24/7 support; underestimating SUD treatment complexity |
| **Decision Influence** | User (clinical outcomes, provider network, crisis response) |

---

## Discovery Questions

| ID | Question | Target Persona | Discovery Goal | Linked Pain | Confidence |
|----|----------|---------------|---------------|-------------|------------|
| PH-DQ-001 | What is your current Medicaid eligibility determination time, and how does it compare to the 45-day federal maximum? | Medicaid Director | Baseline eligibility processing performance; identify backlog severity | PH-PAIN-001 | HIGH |
| PH-DQ-002 | What percentage of your Medicaid renewals are completed through ex parte (automated) processes vs. requiring member action? | Medicaid Director | Assess automation maturity and churn risk | PH-PAIN-001 | HIGH |
| PH-DQ-003 | How many separate eligibility and case management systems do your caseworkers access daily across Medicaid, SNAP, TANF, and child care programs? | Eligibility Supervisor | Quantify system fragmentation and integration opportunity | PH-PAIN-015 | HIGH |
| PH-DQ-004 | What is your current SNAP QC error rate, and has USDA issued any corrective action or enhanced oversight notices? | Eligibility Supervisor | Identify federal compliance risk and funding exposure | PH-PAIN-002 | HIGH |
| PH-DQ-005 | What is your first payment timeliness rate for unemployment insurance claims, and how has it trended since the pandemic? | UI Claims Director | Baseline UI processing performance; identify modernization need | PH-PAIN-004 | HIGH |
| PH-DQ-006 | How do you currently verify claimant identity, and what is the average time to resolve identity holds? | UI Claims Director | Assess fraud prevention vs. service delivery balance | PH-PAIN-004 | HIGH |
| PH-DQ-007 | How many systems does a child welfare caseworker need to access to complete a single safety assessment or placement decision? | Child Welfare Supervisor | Quantify case management fragmentation | PH-PAIN-003 | HIGH |
| PH-DQ-008 | What is your AFCARS data quality rate, and have you had any federal compliance findings in the past two submission cycles? | Child Welfare Supervisor | Assess federal compliance posture for child welfare | PH-PAIN-003 | HIGH |
| PH-DQ-009 | What percentage of your notifiable disease reports are submitted electronically vs. via fax or phone, and what is the average reporting delay? | Public Health Officer | Baseline surveillance modernization gap | PH-PAIN-005 | HIGH |
| PH-DQ-010 | How many EDs in your jurisdiction are connected to syndromic surveillance, and what are the data quality gaps? | Public Health Officer | Assess outbreak detection coverage and readiness | PH-PAIN-005 | HIGH |
| PH-DQ-011 | What is the average wait time for non-crisis outpatient behavioral health services in your network, and how has it changed in the past year? | BH Program Director | Quantify access gap and provider shortage severity | PH-PAIN-006 | HIGH |
| PH-DQ-012 | What is your 988 crisis line answer rate, and do you have mobile crisis teams dispatched through the same system? | BH Program Director | Assess crisis system integration and performance | PH-PAIN-006 | HIGH |
| PH-DQ-013 | How many households are currently on your Housing Choice Voucher waitlist, and what is the average time from application to voucher issuance? | Program Director | Quantify housing assistance throughput bottleneck | PH-PAIN-007 | HIGH |
| PH-DQ-014 | What is your current MMIS vendor contract end date, and has CMS assessed your MITA maturity level in the past two years? | Medicaid Director | Identify Medicaid system replacement urgency | PH-PAIN-013 | HIGH |
| PH-DQ-015 | How do you currently track and manage HCBS waiver waitlists, and what percentage of individuals on the waitlist are diverted to institutional settings? | BH Program Director | Assess Olmstead compliance and community integration capacity | PH-PAIN-009 | HIGH |
| PH-DQ-016 | What is your eligibility worker annual turnover rate, and what is the average time for a new worker to process cases independently? | Eligibility Supervisor | Quantify workforce crisis and training burden | PH-PAIN-011 | HIGH |
| PH-DQ-017 | How do you currently share data between your state veterans benefits agency and federal VA systems or county veterans service officers? | Program Director | Assess veterans services coordination gap | PH-PAIN-010 | MEDIUM |
| PH-DQ-018 | What is your CCDF provider reimbursement cycle time, and what percentage of providers receive payment within 30 days of submission? | Eligibility Supervisor | Identify child care subsidy delivery efficiency | PH-PAIN-018 | HIGH |

---

## Objection Patterns

### PH-OBJ-001: CMS Approval Timeline Risk

| Attribute | Detail |
|-----------|--------|
| **Objection** | Any Medicaid system change requires CMS Advanced Planning Document (APD) approval, which takes 12-18 months. We can't move fast enough. |
| **Response Strategy** | Reference modular APD pathways (90-day review for modular components); highlight states with successful fast-track modular MMIS approvals; offer CMS relationship support |
| **Confidence** | HIGH |
| **Sources** | CMS APD guidelines; State modular MMIS examples (e.g., Illinois, Vermont) |

### PH-OBJ-002: Federal Funding Uncertainty

| Attribute | Detail |
|-----------|--------|
| **Objection** | Federal match rates and grant guidance change with each administration. We can't commit to multi-year technology investments. |
| **Response Strategy** | Emphasize modular, incremental approaches; highlight FMAP entitlements as statutory; reference 90/10 match for Medicaid eligibility/IT; offer flexible contracting terms |
| **Confidence** | HIGH |
| **Sources** | Social Security Act FMAP provisions; CMS 90/10 match guidance |

### PH-OBJ-003: Worker Union Opposition to Automation

| Attribute | Detail |
|-----------|--------|
| **Objection** | Our eligibility worker union opposes any technology that reduces headcount or changes job classifications. |
| **Response Strategy** | Frame as worker empowerment (reducing data entry, increasing client-facing time); reference AFSCME/SEIU collaborative modernization successes; offer labor-management partnership model |
| **Confidence** | MEDIUM |
| **Sources** | Code for America integrated benefits research; State union collaboration case studies |

### PH-OBJ-004: Legacy System Integration Complexity

| Attribute | Detail |
|-----------|--------|
| **Objection** | Our MMIS/eligibility system is 20+ years old and deeply intertwined with downstream systems. Rip-and-replace is too risky. |
| **Response Strategy** | Propose modular, phased replacement (CMS MITA modular architecture); offer API wrapper/adapter layer; reference successful brownfield modernization patterns |
| **Confidence** | HIGH |
| **Sources** | CMS MITA 3.0 Framework; State modular MMIS procurements |

### PH-OBJ-005: Data Sharing Privacy Constraints

| Attribute | Detail |
|-----------|--------|
| **Objection** | We can't share eligibility data across programs due to HIPAA, 42 CFR Part 2, and state privacy laws. |
| **Response Strategy** | Reference CMS streamlined verification authority; highlight privacy-preserving integration patterns (data minimization, role-based access, audit trails); cite states with successful cross-program data sharing (MN, KY) |
| **Confidence** | HIGH |
| **Sources** | CMS streamlined verification guidance; State integrated eligibility examples; 42 CFR Part 2 guidance |

### PH-OBJ-006: Procurement Cycle Too Long

| Attribute | Detail |
|-----------|--------|
| **Objection** | Our state procurement process takes 18-24 months for IT systems. By the time we implement, requirements will have changed. |
| **Response Strategy** | Reference modular SaaS procurements that fit under simplified thresholds; agile contracting vehicles; cooperative purchasing agreements (NASPO, Western States Contracting Alliance) |
| **Confidence** | MEDIUM |
| **Sources** | NASPO ValuePoint contracts; State agile procurement guides |

### PH-OBJ-007: Pandemic Funding Cliff

| Attribute | Detail |
|-----------|--------|
| **Objection** | We used ARPA/COVID relief funds for temporary staff and systems. Now that funding is ending, we can't sustain these solutions. |
| **Response Strategy** | Focus on permanent efficiency gains (ex parte automation, churn reduction) that reduce ongoing administrative costs; demonstrate FMAP savings that offset state share; reference maintenance of effort protections |
| **Confidence** | HIGH |
| **Sources** | KFF ARPA FMAP analysis; CMS unwinding guidance |

### PH-OBJ-008: Veterans Services Are Federal Responsibility

| Attribute | Detail |
|-----------|--------|
| **Objection** | Veterans benefits are a federal VA responsibility. Our state agency just does advocacy and referral. |
| **Response Strategy** | Highlight state veterans homes, employment programs, and mental health navigation as state-funded; reference federal-state partnership models; cite HUD-VASH and SSVF coordination gaps |
| **Confidence** | MEDIUM |
| **Sources** | VA State Veterans Home grants; NVSOR directory; HUD-VASH data |

### PH-OBJ-009: Behavioral Health Provider Shortage Can't Be Solved by Technology

| Attribute | Detail |
|-----------|--------|
| **Objection** | We don't need software—we need more psychiatrists and therapists. Technology won't create providers. |
| **Response Strategy** | Frame as provider productivity and reach expansion (telehealth, e-prescribing, collaborative care models); reference workforce pipeline technology (loan repayment tracking, licensure reciprocity tools); highlight crisis diversion that reduces demand on scarce providers |
| **Confidence** | MEDIUM |
| **Sources** | SAMHSA workforce reports; HRSA Area Health Resource File; Telehealth parity data |

---

## Technology Systems

| ID | Name | Category | Description | Modernization Trends | Linked Pains |
|----|------|----------|-------------|---------------------|-------------|
| PH-TECH-001 | MMIS | Core Administration | Medicaid claims processing, provider enrollment, prior authorization, and payment | Modular replacement, cloud migration, API-first, real-time adjudication | PH-PAIN-013, PH-PAIN-008 |
| PH-TECH-002 | Eligibility and Enrollment System (E&E) | Benefits Administration | Determines eligibility for Medicaid, SNAP, TANF, CHIP; often siloed by program | Integrated cross-program eligibility, ex parte automation, mobile application, real-time verification | PH-PAIN-001, PH-PAIN-015, PH-PAIN-011 |
| PH-TECH-003 | CCWIS / SACWIS | Case Management | Tracks child welfare cases from intake through permanency; federal CCWIS standards replacing SACWIS | CCWIS compliance, mobile case management, predictive analytics, family search and engagement | PH-PAIN-003 |
| PH-TECH-004 | UI Benefits System | Benefits Administration | Processes UI claims, wage verification, adjudication, and payments | Cloud migration, identity verification integration, fraud detection analytics, mobile claims filing | PH-PAIN-004 |
| PH-TECH-005 | SNAP EBT and Eligibility | Benefits Administration | SNAP eligibility determination, case management, and Electronic Benefit Transfer card management | Online purchasing integration, real-time eligibility, mobile EBT, fraud detection | PH-PAIN-002, PH-PAIN-001 |
| PH-TECH-006 | ELR / Surveillance | Public Health | Notifiable disease tracking, outbreak detection, and electronic laboratory result reporting | FHIR-based reporting, real-time outbreak detection, EHR integration, syndromic surveillance expansion | PH-PAIN-005, PH-PAIN-016 |
| PH-TECH-007 | IIS (Immunization Information System) | Public Health | Registry of immunization doses administered; supports vaccine inventory and cross-jurisdictional sharing | FHIR interfaces, adult immunization tracking, IZ Gateway connectivity, EHR bidirectional exchange | PH-PAIN-014 |
| PH-TECH-008 | BH EHR / Crisis Platform | Health Delivery | Electronic health records for mental health and SUD treatment; crisis call center and mobile crisis dispatch | Crisis continuum integration, 988 data reporting, telehealth, CJS diversion tracking | PH-PAIN-006 |
| PH-TECH-009 | PHA Management System | Housing Administration | Voucher administration, HQS inspection tracking, landlord engagement, and waitlist management | Mobile inspections, landlord portal, portability automation, waitlist self-service | PH-PAIN-007 |
| PH-TECH-010 | ADRC / No Wrong Door | Case Management | Aging and Disability Resource Center systems; long-term care options counseling; HCBS waiver management | No Wrong Door integration, HCBS self-direction, caregiver support portal, Olmstead tracking | PH-PAIN-009 |
| PH-TECH-011 | CCDF Administration | Benefits Administration | CCDF eligibility, provider enrollment, attendance tracking, and quality rating integration | Electronic attendance, QRIS integration, parent copayment portal, provider reimbursement automation | PH-PAIN-018 |
| PH-TECH-012 | Integrated Eligibility Platform | Enterprise Integration | Unified eligibility platform spanning Medicaid, SNAP, TANF, child care, housing, and other programs | Single application, streamlined verification, ex parte expansion, analytics and reporting | PH-PAIN-015, PH-PAIN-011, PH-PAIN-001 |

---

## Regulatory Factors

| ID | Name | Authority | Effective Date | Compliance Risk | Penalty Exposure | Linked Pains |
|----|------|-----------|---------------|----------------|-----------------|-------------|
| PH-REG-001 | CMS Medicaid Managed Care Final Rule (42 CFR 438) | CMS / HHS | 2024-2026 phased | HIGH | Federal funding reduction; CMS corrective action; MCO contract sanctions | PH-PAIN-008 |
| PH-REG-002 | CMS Streamlined Verification | CMS / HHS | Ongoing; unwinding accelerated | HIGH | CMS CMP; FMAP reduction; corrective action plan | PH-PAIN-001, PH-PAIN-015 |
| PH-REG-003 | SNAP QC and Federal Funding Share | USDA FNS | Continuous (annual QC cycle) | HIGH | Federal funding share reduction from 50% to 25%; corrective action requirements | PH-PAIN-002 |
| PH-REG-004 | DOL ETA UI Performance Targets | DOL ETA | Annual (performance year) | HIGH | Administrative grant reduction; enhanced oversight; technical assistance mandate | PH-PAIN-004 |
| PH-REG-005 | CCWIS / AFCARS Compliance | HHS ACF | CCWIS phased; AFCARS continuous | HIGH | Title IV-E funding penalty; CFSR compliance action; PIP requirements | PH-PAIN-003 |
| PH-REG-006 | CDC DMI and ELR Mandate | CDC / HHS | 2021-2026 funding cycle | MEDIUM | PHEP grant reduction; ELC grant conditions; emergency response gaps | PH-PAIN-005, PH-PAIN-016 |
| PH-REG-007 | SAMHSA Block Grant and 988 | SAMHSA / HHS | 2022-2024 implementation | MEDIUM | Block grant funding reduction; technical assistance; peer review | PH-PAIN-006 |
| PH-REG-008 | HUD PHA Performance and Voucher Utilization | HUD | Annual (PHA performance year) | MEDIUM | Administrative fee reduction; voucher reallocation; MTW suspension | PH-PAIN-007 |
| PH-REG-009 | CMS Olmstead Community Integration Enforcement | CMS / DOJ | Continuous enforcement | HIGH | CMS compliance action; DOJ settlement; consent decree; waiver suspension | PH-PAIN-009 |
| PH-REG-010 | CCDF Reauthorization and Compliance | HHS ACF | 2014 reauthorization; state plan updates every 3 years | MEDIUM | CCDF funding reduction; state plan disapproval; monitoring findings | PH-PAIN-018 |

---

## Competitor Factors

| ID | Name | Competitive Threat | Typical Incumbents | Differentiation Strategy |
|----|------|-------------------|---------------------|------------------------|
| PH-COMP-001 | Incumbent MMIS Vendor Entrenchment | HIGH | Gainwell, DXC, CNSI, Optum | Modular, cloud-native architecture; real-time analytics; faster implementation; lower TCO |
| PH-COMP-002 | Large SI Dominance in Eligibility | HIGH | Deloitte, Accenture, Maximus, CGI Federal | Specialized vertical expertise; pre-built accelerators; agile delivery; state staff enablement |
| PH-COMP-003 | Open Source and State-Developed Solutions | MEDIUM | State-developed (MI, VT), Free/Open Source | Commercial support; proven scalability; CMS pre-approval; faster deployment than custom build |
| PH-COMP-004 | SaaS Case Management Disruption | MEDIUM | Salesforce, Microsoft, Appian, Pegasystems | Pre-built vertical workflows; regulatory compliance templates; integration with federal systems |

---

## Worked Examples

### Example 1: Medicaid Ex Parte Renewal Automation Value Model

**Scenario:** State Medicaid agency with 1.2M enrollees processes 300K renewals annually. Baseline ex parte rate is 25%, manual renewal costs $35 each, and churn rate is 18%.

**Inputs:**
- Annual renewals: 300,000
- Baseline ex parte rate: 25%
- Target ex parte rate: 70%
- Manual renewal cost: $35
- Baseline churn rate: 18%
- Target churn rate: 10%
- Average enrollment: 1,200,000
- Churn admin cost: $120
- Gap-in-care cost: $180
- CMS compliance risk value: $500,000

**Formula:** PH-VF-002 + PH-VF-001

**Calculation Steps:**
1. Ex Parte Efficiency = (300K * (0.70 - 0.25)) * $35 = 135K * $35 = $4.725M
2. Churn Reduction = (0.18 - 0.10) * 1.2M * ($120 + $180) = 96K * $300 = $28.8M
3. CMS Compliance Avoidance = $500K
4. **Total Annual Value = $4.725M + $28.8M + $0.5M = $34.025M**

**Sensitivity Analysis:**
- Low case: $22M (ex parte only reaches 55%, churn reduces to 12%)
- Base case: $34M
- High case: $48M (ex parte reaches 80%, churn reduces to 7%)

**Confidence:** MEDIUM — Based on state-reported averages; actual values vary by state administrative cost structure and churn composition.

---

### Example 2: Child Welfare Case Management Consolidation Value Model

**Scenario:** State child welfare agency operates 8 separate case management systems for CPS, foster care, adoption, and family services. 500 caseworkers spend 15 hours/week on data entry across systems.

**Inputs:**
- Systems consolidated: 8
- Maintenance cost per system: $200,000
- Caseworkers: 500
- Hours saved per worker per week: 10
- Loaded hourly rate: $45
- Weeks per year: 48
- Recurrence reduction value: $2,000,000

**Formula:** PH-VF-004

**Calculation Steps:**
1. System Maintenance Savings = 8 * $200K = $1.6M
2. Caseworker Hours Saved = 500 * 10 hrs/week * 48 weeks * $45 = $10.8M
3. Recurrence Reduction = $2M (from better case history visibility)
4. **Total Annual Value = $1.6M + $10.8M + $2M = $14.4M**

**Sensitivity Analysis:**
- Low case: $9M (only 6 hours saved/week, limited recurrence impact)
- Base case: $14.4M
- High case: $22M (15 hrs saved, 20% recurrence reduction from predictive analytics)

**Confidence:** MEDIUM — Hours saved depends on unified system usability; recurrence reduction requires longitudinal outcome tracking.

---

### Example 3: SNAP Error Rate Reduction and Federal Funding Protection

**Scenario:** State SNAP agency with $600M annual outlay has QC error rate of 8.5% (above 6% threshold). Federal funding share is 50%. State must reduce error rate to 4% to avoid enhanced oversight.

**Inputs:**
- Total SNAP outlay: $600,000,000
- Baseline error rate: 8.5%
- Target error rate: 4%
- Federal funding share: 50%
- Corrective action cost: $1,500,000

**Formula:** PH-VF-003

**Calculation Steps:**
1. Error Reduction Value = $600M * (0.085 - 0.04) * 0.50 = $600M * 0.045 * 0.50 = $13.5M
2. Corrective Action Avoidance = $1.5M
3. **Total Annual Value = $13.5M + $1.5M = $15M**

**Sensitivity Analysis:**
- Low case: $10M (error rate only reduces to 5.5%, partial corrective action still needed)
- Base case: $15M
- High case: $21M (error rate reduces to 3%, full federal share restored with penalty reversal)

**Confidence:** HIGH — USDA SNAP QC data is standardized; federal funding share formula is statutory; calculation is deterministic.

---

## Governance

| Attribute | Detail |
|-----------|--------|
| **Source Coverage** | Mixed (public federal data, state agency reports, research organizations) |
| **Overall Confidence** | Medium |
| **Last Updated** | 2025-01-21 |
| **Approved for Customer-Facing Output** | No — requires validation with live prospects before external use |
| **Review Owner** | Vertical Subpack Architect — Public Health & Human Services |
| **Agent Swarm ID** | kimi-k2.6-elevated-swarm-phhs |
| **Parent Master Swarm ID** | kimi-k2.6-elevated-swarm |

---

*End of Public Health and Human Services Subpack (S5.4)*
*Generated by Kimi K2.6 Elevated Agent Swarm — Vertical Subpack Creator (Phase 2)*
