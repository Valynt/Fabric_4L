# Federal Government Subpack (S5.1)

**Version:** 1.0.0  
**Domain:** Public Sector — Federal Government  
**Parent Master:** public-sector-master-v1  
**Last Updated:** 2026-04-25  
**Review Owner:** Federal Subpack Architect — Vertical Intelligence Swarm  
**Agent Swarm ID:** kimi-k2.6-elevated-swarm-federal  
**Source Coverage:** Mixed (GAO reports, OMB data, agency OIG, FedRAMP PMO, DoD CMMC, FPDS, SBA, NARA)  
**Overall Confidence:** High  
**Approved for Customer-Facing Output:** No (requires validation with live prospects)

---

## Table of Contents

1. [Inheritance Manifest](#inheritance-manifest)
2. [Vertical Focus](#vertical-focus)
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

## Inheritance Manifest

### Master Pack ID
`public-sector-master-v1`

### Inherited Components (Read-Only Reference)
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

### Created Components (This Subpack)
- Federal Pains (FED-PAIN-001 through FED-PAIN-018)
- Federal KPIs (FED-KPI-001 through FED-KPI-022)
- Federal Signal Rules (FED-SIG-001 through FED-SIG-018)
- Federal Personas (FED-PERS-001 through FED-PERS-006)
- Federal Formulas (FED-VF-001 through FED-VF-014)
- Federal Benchmarks (FED-BENCH-001 through FED-BENCH-018)
- Federal Regulatory Factors (FED-REG-001 through FED-REG-012)
- Federal Technology Systems (FED-TECH-001 through FED-TECH-015)
- Federal Discovery Questions (FED-DQ-001 through FED-DQ-018)
- Federal Objection Patterns (FED-OBJ-001 through FED-OBJ-010)
- Federal Worked Examples (FED-EX-001 through FED-EX-003)
- Federal Buying Triggers (FED-TRIG-001 through FED-TRIG-015)

### Overridden Components
| Component | Override Reason |
|-----------|-----------------|
| Procurement Cycle Time Benchmark | Federal acquisition cycle has unique defense-specific DFARS/FAR clauses, DAU requirements, and protest pathways (GAO vs COFC). Federal IT procurement median is 210 days vs state median ~120 days. |
| Cybersecurity Compliance Framework | Federal agencies operate under FISMA, OMB M-22-09 Zero Trust mandates, CISA BODs, and agency-specific ISSO/ISSM structures. State/local use NIST CSF voluntarily. Regulatory drivers and roles differ materially. |
| Cloud Migration Complexity Pain | Federal cloud migration is gated by FedRAMP ATO (typically 12-18 months), agency-specific Cloud Smart strategies, and CSP selection constraints. Cost overrun patterns differ from state/local. |

---

## Vertical Focus

| Sub-Segment | Description | Typical Budget Scale | Key Regulatory Drivers |
|-------------|-------------|---------------------|----------------------|
| DoD / Military Branches | Army, Navy, Air Force, Marine Corps, Space Force | $800B+ annually | DFARS, CMMC, FISMA, ITAR |
| Intelligence Community | CIA, NSA, NRO, DIA, NGA, FBI (intel) | $60B+ aggregate (classified) | ICD 503, ICD 705, ITAR, SCI |
| Homeland Security / Border Protection | CBP, ICE, USCIS, TSA, FEMA, USCG | $100B+ | FISMA, CISA BODs, Privacy Act |
| Civilian Agencies | GSA, SBA, State, Interior | $1B-$30B each | FISMA, FITARA, Section 508 |
| Treasury / Tax Administration | IRS, FinCEN, OCC | $14B+ IRS budget | FISMA, Taxpayer Privacy, FITARA |
| HHS (CMS, CDC, FDA, NIH) | Medicare/Medicaid, public health, research | $1.7T CMS outlays | FISMA, HIPAA, 2 CFR 200 |
| Transportation (DOT, FAA) | Aviation, highways, rail, motor carrier | $90B+ | FISMA, Safety Regulations |
| Energy (DOE, NNSA) | Nuclear security, science, energy | $45B+ | FISMA, ITAR, EAR, classified |
| EPA | Environmental protection, regulation | $9B+ | FISMA, environmental regs |
| Justice / Law Enforcement | DOJ, FBI, DEA, BOP | $35B+ | FISMA, CJIS Security Policy |
| Veterans Services (VA) | Health care, benefits, cemeteries | $300B+ | FISMA, VA-specific regulations |
| Space / Research (NASA, NSF, NOAA) | Space exploration, fundamental science | $35B+ aggregate | FISMA, ITAR, export control |

---

## Business Pains


### FED-PAIN-001: ATO Timeline Exceeding 18 Months

| Attribute | Detail |
|-----------|--------|
| **Name** | ATO Timeline Exceeding 18 Months |
| **Description** | Federal Risk Management Framework (RMF) authorization packages take >18 months from categorization to ATO, delaying system deployment and creating operational risk for programs awaiting accredited environments. |
| **Symptoms** | RMF Step 1 initiation >6 months old with no SAP; POA&M items >90 days open; eMASS package rejection >2 times; ISSO/ISSM turnover during ATO process; System deployed on interim ATO >12 months |
| **Affected Segments** | All Federal Agencies |
| **Affected Personas** | FED-PERS-003, FED-PERS-002, FED-PERS-001 |
| **Linked KPIs** | FED-KPI-001, FED-KPI-009, FED-KPI-013 |
| **Linked Value Drivers** | Risk Reduction, Working Capital, Mission Effectiveness |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (GAO-22-104999; DoD CIO RMF metrics; FedRAMP PMO annual report) |


### FED-PAIN-002: Legacy O&M Consuming >70% of IT Budget

| Attribute | Detail |
|-----------|--------|
| **Name** | Legacy O&M Consuming >70% of IT Budget |
| **Description** | Federal agencies spend 70-80% of IT budgets on operations and maintenance of legacy systems, squeezing modernization, development, and DME funding. CIOs cannot reallocate without congressional reprogramming or FITARA waiver. |
| **Symptoms** | O&M ratio >72% per FITARA scorecard; Systems >20 years old still in production; COBOL/mainframe dependencies; Vendor support at premium pricing; No DME funding in 3+ years |
| **Affected Segments** | DoD, Treasury, VA, HHS, DHS, Justice |
| **Affected Personas** | FED-PERS-002, FED-PERS-001, PS-PERS-006 |
| **Linked KPIs** | PS-KPI-001, FED-KPI-003, FED-KPI-014 |
| **Linked Value Drivers** | Cost Savings, Risk Reduction, Mission Effectiveness |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (GAO-19-336; GAO-23-105492; OMB FITARA scorecard 2023) |


### FED-PAIN-003: Continuing Resolution Planning Paralysis

| Attribute | Detail |
|-----------|--------|
| **Name** | Continuing Resolution Planning Paralysis |
| **Description** | Operating under CR for 3+ months freezes new starts, prevents multi-year planning, and forces Q4 obligation surges. Agencies lose 15-25% of effective planning time annually. |
| **Symptoms** | CR in effect >3 months; New start freeze invoked; Q4 obligation rate >40% of annual total; Contract stop-work orders issued; Employee morale survey scores declining |
| **Affected Segments** | All Federal Civilian, DoD |
| **Affected Personas** | FED-PERS-001, FED-PERS-002, FED-PERS-006 |
| **Linked KPIs** | FED-KPI-007, FED-KPI-014, FED-KPI-006 |
| **Linked Value Drivers** | Working Capital, Cost Savings, Risk Reduction |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (GAO-23-106309; CBO Budget Outlook 2024; OMB CR guidance memos) |


### FED-PAIN-004: FedRAMP ATO Bottleneck for SaaS/PaaS

| Attribute | Detail |
|-----------|--------|
| **Name** | FedRAMP ATO Bottleneck for SaaS/PaaS |
| **Description** | Commercial cloud providers face 12-24 month FedRAMP authorization timelines. Agencies cannot adopt innovative SaaS until CSP achieves P-ATO or agency ATO, creating shadow IT and on-prem lock-in. |
| **Symptoms** | FedRAMP marketplace <300 authorized products; Agency ATO queue >20 pending; Shadow IT cloud detected via CASB; Rejected JAB submissions >2 per agency; CSPs withdrawing from FedRAMP |
| **Affected Segments** | All Federal Agencies |
| **Affected Personas** | FED-PERS-003, FED-PERS-002, PS-PERS-004 |
| **Linked KPIs** | FED-KPI-009, PS-KPI-029, PS-KPI-028 |
| **Linked Value Drivers** | Cost Savings, Risk Reduction, Mission Effectiveness |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (FedRAMP PMO FY2023 report; GAO-22-104999; MeriTalk Cloudy with a Chance of Insight 2023) |


### FED-PAIN-005: CMMC / DFARS Compliance Gap (Defense Industrial Base)

| Attribute | Detail |
|-----------|--------|
| **Name** | CMMC / DFARS Compliance Gap (Defense Industrial Base) |
| **Description** | DOD contractors and primes face CMMC Level 2/3 requirements with 110+ NIST SP 800-171 controls. Assessment backlog, C3PAO capacity constraints, and flow-down requirements create supply chain accreditation risk. |
| **Symptoms** | SPRSSP score <110; POA&M items >50 open; C3PAO assessment wait time >6 months; Subcontractor compliance unverified; Contract award eligibility at risk |
| **Affected Segments** | DoD, Intelligence Community, DHS |
| **Affected Personas** | FED-PERS-003, FED-PERS-004, PS-PERS-004 |
| **Linked KPIs** | FED-KPI-004, FED-KPI-011, PS-KPI-004 |
| **Linked Value Drivers** | Risk Reduction, Cost Savings, Working Capital |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (DoD CMMC Announcement 2023; NIST SP 800-171 Rev 2; Defense Industrial Base Cyber Strategy) |


### FED-PAIN-006: 1102 Contracting Officer Workforce Vacancy Crisis

| Attribute | Detail |
|-----------|--------|
| **Name** | 1102 Contracting Officer Workforce Vacancy Crisis |
| **Description** | Federal acquisition workforce (1102 series) faces 20%+ vacancy rates. Complex IT and professional services procurements require specialized skills (Agile, cloud, cybersecurity) that traditional DAU training doesn't cover. |
| **Symptoms** | 1102 vacancy rate >18%; Procurement action lead time >250 days; Protest rate >5% on IT acquisitions; Requirements packages requiring >3 revisions; Reliance on external support contractors for acquisition support |
| **Affected Segments** | All Federal Agencies |
| **Affected Personas** | FED-PERS-004, FED-PERS-001, PS-PERS-013 |
| **Linked KPIs** | PS-KPI-013, PS-KPI-014, FED-KPI-015 |
| **Linked Value Drivers** | Working Capital, Cost Savings, Mission Effectiveness |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (GAO-21-256; DAU workforce studies; OFPP Myth-Busting memos) |


### FED-PAIN-007: ITAR / Export Control Compliance Burden

| Attribute | Detail |
|-----------|--------|
| **Name** | ITAR / Export Control Compliance Burden |
| **Description** | Defense, intelligence, and space agencies face ITAR, EAR, and classified material handling requirements that add 20-40% to procurement cycle time and limit vendor pools. Violations carry criminal and debarment penalties. |
| **Symptoms** | ITAR compliance staffing >5% of program office; License application processing time >90 days; Violations in last 3 years; Commingled ITAR/unclassified environments; Foreign vendor exclusion from competitions |
| **Affected Segments** | DoD, Intelligence Community, NASA, DOE/NNSA |
| **Affected Personas** | FED-PERS-003, FED-PERS-004, FED-PERS-001 |
| **Linked KPIs** | FED-KPI-011, PS-KPI-021, FED-KPI-001 |
| **Linked Value Drivers** | Risk Reduction, Cost Savings, Working Capital |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (State Directorate of Defense Trade Controls annual report; DDTC compliance letters; GAO export control reviews) |


### FED-PAIN-008: Grant Closeout Backlog and Deobligation Risk

| Attribute | Detail |
|-----------|--------|
| **Name** | Grant Closeout Backlog and Deobligation Risk |
| **Description** | Federal grant-making agencies accumulate physical and administrative closeout backlogs. Funds deobligation due to unexpended balances or lapsed timelines returns appropriated dollars to Treasury, reducing program impact. |
| **Symptoms** | Physically incomplete grants >180 days past end date; Deobligation rate >8%; Recipient single audit findings recurring; Grant system reconciliation errors >5%; Closeout staffing <2 FTE per $1B portfolio |
| **Affected Segments** | HHS, NSF, ED, DOJ/OJJDP, DHS/FEMA |
| **Affected Personas** | FED-PERS-005, PS-PERS-006, FED-PERS-002 |
| **Linked KPIs** | FED-KPI-006, PS-KPI-009, PS-KPI-031 |
| **Linked Value Drivers** | Working Capital, Cost Savings, Risk Reduction |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (GAO-22-104238; OMB Uniform Guidance 2 CFR 200; HHS Grants Closeout Reports) |


### FED-PAIN-009: Interoperability Failure Across Classified-Unclassified Boundaries

| Attribute | Detail |
|-----------|--------|
| **Name** | Interoperability Failure Across Classified-Unclassified Boundaries |
| **Description** | Intelligence and defense agencies struggle with cross-domain solutions, multi-level security (MLS), and data tagging (CUI, FOUO, SECRET) that prevent seamless information sharing while maintaining security boundaries. |
| **Symptoms** | Cross-domain transfer requests >30 days approval; Manual data transfer (sneakernet) observed; ICD 503 compliance gaps; CUI mishandling incidents; JWICS-SIPRNet-NIPRNet friction points |
| **Affected Segments** | Intelligence Community, DoD, DHS, DOJ |
| **Affected Personas** | FED-PERS-003, FED-PERS-002, PS-PERS-001 |
| **Linked KPIs** | PS-KPI-032, FED-KPI-011, PS-KPI-004 |
| **Linked Value Drivers** | Mission Effectiveness, Risk Reduction, Cost Savings |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (ODNI ICITE reports; DoD CIO cross-domain strategy; ICD 503 assessment findings) |


### FED-PAIN-010: VA Claims and Appeals Backlog

| Attribute | Detail |
|-----------|--------|
| **Name** | VA Claims and Appeals Backlog |
| **Description** | VA disability compensation and appeals backlog creates veteran dissatisfaction, congressional scrutiny, and overtime costs. Legacy VBA systems (VBMS, VA.gov) face integration challenges with new digital tools. |
| **Symptoms** | Pending disability claims >200K; Average processing time >125 days; Appeals backlog >100K at BVA; Error rate on original claims >10%; Congressional inquiry volume increasing |
| **Affected Segments** | VA |
| **Affected Personas** | FED-PERS-001, PS-PERS-003, PS-PERS-008 |
| **Linked KPIs** | FED-KPI-019, PS-KPI-006, PS-KPI-007 |
| **Linked Value Drivers** | Mission Effectiveness, Cost Savings, Risk Reduction |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (VA OIG reports; VBA performance dashboards; GAO-23-106309) |


### FED-PAIN-011: IRS Tax Gap and Service Delivery Strain

| Attribute | Detail |
|-----------|--------|
| **Name** | IRS Tax Gap and Service Delivery Strain |
| **Description** | IRS faces $600B+ annual tax gap with paper return processing backlog, legacy system modernization needs (CADE 2, MEIS), and customer service wait times. Inflation Reduction Act funding creates modernization opportunity but execution risk. |
| **Symptoms** | Paper return backlog >1M during filing season; Customer service Level of Service <70%; Tax gap >$600B annually; CADE 2 transition delays; Telephone wait time >20 minutes |
| **Affected Segments** | Treasury/IRS |
| **Affected Personas** | FED-PERS-002, PS-PERS-003, FED-PERS-006 |
| **Linked KPIs** | FED-KPI-020, PS-KPI-015, PS-KPI-027 |
| **Linked Value Drivers** | Revenue Uplift, Cost Savings, Mission Effectiveness |
| **Prevalence** | HIGH |
| **Confidence** | HIGH (IRS Tax Gap estimates 2023; Treasury IG reports; GAO-23-106309 IRS) |


### FED-PAIN-012: Section 508 Accessibility Compliance Failure

| Attribute | Detail |
|-----------|--------|
| **Name** | Section 508 Accessibility Compliance Failure |
| **Description** | Federal agencies face recurring Section 508 noncompliance with digital products, documents, and procurement. DOJ settlement agreements and accessibility complaints create legal exposure and procurement delays. |
| **Symptoms** | Section 508 complaints >10 per year; DOJ settlement or mediation active; Procurement evaluations lack 508 conformance testing; Legacy PDF documents inaccessible; Video content without captions |
| **Affected Segments** | All Federal Agencies |
| **Affected Personas** | FED-PERS-002, FED-PERS-003, PS-PERS-005 |
| **Linked KPIs** | FED-KPI-012, PS-KPI-021, PS-KPI-020 |
| **Linked Value Drivers** | Risk Reduction, Cost Savings, Mission Effectiveness |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (DOJ Section 508 report to Congress; Accessibility complaint data; Agency OIG 508 findings) |


### FED-PAIN-013: Contract Closeout and Physical Completion Backlog

| Attribute | Detail |
|-----------|--------|
| **Name** | Contract Closeout and Physical Completion Backlog |
| **Description** | Federal agencies accumulate physically complete but administratively open contracts due to inadequate closeout staffing, DCAA audit delays, and documentation gaps. DCMA closeout backlog exceeds 100K actions. |
| **Symptoms** | Physically complete contracts >180 days not closed; DCAA incurred cost backlog >2 years; Final indirect cost rate negotiations >12 months; Contract closeout staffing vacancy >20%; Contract writing system data quality errors |
| **Affected Segments** | DoD, DHS, VA, GSA |
| **Affected Personas** | FED-PERS-004, FED-PERS-001, PS-PERS-013 |
| **Linked KPIs** | FED-KPI-021, PS-KPI-013, FED-KPI-015 |
| **Linked Value Drivers** | Working Capital, Cost Savings, Risk Reduction |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (DCMA closeout reports; DCAA workload metrics; GAO contract management reviews) |


### FED-PAIN-014: EIS / NS2020 Network Transition Delay

| Attribute | Detail |
|-----------|--------|
| **Name** | EIS / NS2020 Network Transition Delay |
| **Description** | GSA Enterprise Infrastructure Solutions (EIS) and DoD NS2020 transition deadlines have passed for many agencies with incomplete cutovers. Legacy FTS2001/Networx contracts extended at premium pricing. |
| **Symptoms** | EIS transition completion <80%; Legacy network contract extension fees >10%; Agency transition plan not approved; Telecom inventory data quality issues; Circuit cutover failures requiring rollback |
| **Affected Segments** | All Federal Agencies |
| **Affected Personas** | FED-PERS-002, FED-PERS-001, PS-PERS-001 |
| **Linked KPIs** | FED-KPI-022, PS-KPI-030, PS-KPI-001 |
| **Linked Value Drivers** | Cost Savings, Risk Reduction, Mission Effectiveness |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (GSA EIS transition dashboard; DoD CIO network modernization reports; GAO telecommunications reviews) |


### FED-PAIN-015: Congressional Mandate Implementation Lag

| Attribute | Detail |
|-----------|--------|
| **Name** | Congressional Mandate Implementation Lag |
| **Description** | Agencies receive 100+ new statutory mandates annually with GAO reporting requirements. Implementation tracking, congressional briefing preparation, and deadline compliance create policy office overload. |
| **Symptoms** | Open congressional mandates >50 pending; GAO reporting requirements >10 per year; Statutory deadline compliance rate <80%; OMB passback comments on implementation plans; IG findings on mandate noncompliance |
| **Affected Segments** | All Federal Agencies |
| **Affected Personas** | FED-PERS-006, FED-PERS-001, PS-PERS-005 |
| **Linked KPIs** | FED-KPI-018, PS-KPI-020, PS-KPI-021 |
| **Linked Value Drivers** | Risk Reduction, Cost Savings, Mission Effectiveness |
| **Prevalence** | MEDIUM |
| **Confidence** | MEDIUM (GAO High Risk Series; OMB mandate tracking; Congressional Research Service reports) |


### FED-PAIN-016: Small Business Set-Aside Execution Failure

| Attribute | Detail |
|-----------|--------|
| **Name** | Small Business Set-Aside Execution Failure |
| **Description** | Federal agencies fail to meet small business prime contracting goals (23% overall, 5% WOSB, 3% HUBZone, 3% SDVOSB). Bundling, consolidated contracts, and subcontracting plan noncompliance trigger SBA protests and OIG findings. |
| **Symptoms** | SB prime goal achievement <90% of target; Bundling determinations >5 per year; Subcontracting plan defaults >3; SBA size protest sustain rate increasing; OSDBU staffing vacancy >15% |
| **Affected Segments** | All Federal Agencies |
| **Affected Personas** | FED-PERS-004, FED-PERS-006, PS-PERS-007 |
| **Linked KPIs** | FED-KPI-005, PS-KPI-013, PS-KPI-014 |
| **Linked Value Drivers** | Cost Savings, Risk Reduction, Mission Effectiveness |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (SBA Goaling Report FY2023; GAO small business reviews; OFPP bundling reports) |


### FED-PAIN-017: NARA Electronic Records Compliance (M-19-21 / M-23-07)

| Attribute | Detail |
|-----------|--------|
| **Name** | NARA Electronic Records Compliance (M-19-21 / M-23-07) |
| **Description** | Federal agencies face NARA mandates to transition to fully electronic records management by 2022/2024 with extensions. Paper records, legacy email systems, and unstructured data create compliance gaps and storage costs. |
| **Symptoms** | Paper records volume >20% of total holdings; Email archive not NARA-compliant; Records schedule not approved; Electronic records transfer failure to NARA; e-discovery costs >$500K per litigation |
| **Affected Segments** | All Federal Agencies |
| **Affected Personas** | FED-PERS-002, PS-PERS-012, FED-PERS-003 |
| **Linked KPIs** | PS-KPI-024, FED-KPI-012, PS-KPI-021 |
| **Linked Value Drivers** | Risk Reduction, Cost Savings, Mission Effectiveness |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (NARA M-19-21; NARA M-23-07; Agency OIG records management findings) |


### FED-PAIN-018: NASA/DoD Supply Chain / Counterfeit Parts Risk

| Attribute | Detail |
|-----------|--------|
| **Name** | NASA/DoD Supply Chain / Counterfeit Parts Risk |
| **Description** | Space, defense, and nuclear programs face counterfeit electronic parts, supplier obsolescence, and foreign dependency risks. DFARS 252.246-7007 and NASA SE requirements add inspection and traceability costs. |
| **Symptoms** | Counterfeit parts detected in last 3 years; Single-source critical suppliers >10; Foreign dependency for microelectronics; Supplier quality escape rate >2%; GIDEP alerts requiring action >5 per year |
| **Affected Segments** | DoD, NASA, DOE/NNSA |
| **Affected Personas** | FED-PERS-001, FED-PERS-004, PS-PERS-009 |
| **Linked KPIs** | FED-KPI-011, PS-KPI-005, FED-KPI-004 |
| **Linked Value Drivers** | Risk Reduction, Cost Savings, Mission Effectiveness |
| **Prevalence** | MEDIUM |
| **Confidence** | HIGH (GAO-23-106472 counterfeit parts; DoD DMSMS reports; NASA SE supply chain assessments) |

---

## KPI Definitions


### FED-KPI-001: RMF ATO Timeline (Months)

| Attribute | Detail |
|-----------|--------|
| **Name** | RMF ATO Timeline (Months) |
| **Formula** | `(ATO Date - Categorization Date) / 30.44` |
| **Unit** | Months |
| **Typical Range** | 12-36 months |
| **Benchmark Range** | Best practice: <12 months; concerning: >18 months |
| **Value Driver Links** | Risk Reduction, Working Capital, Mission Effectiveness |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Per ATO package |


### FED-KPI-002: CDRL On-Time Delivery Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | CDRL On-Time Delivery Rate |
| **Formula** | `CDRLs Delivered On Time / Total CDRLs Due * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 60%-95% |
| **Benchmark Range** | Target: >90%; DoD expectation: >95% |
| **Value Driver Links** | Mission Effectiveness, Risk Reduction |
| **Segment Applicability** | DoD, DHS |
| **Calculation Frequency** | Monthly |


### FED-KPI-003: FITARA Score (OMB Quarterly)

| Attribute | Detail |
|-----------|--------|
| **Name** | FITARA Score (OMB Quarterly) |
| **Formula** | `SUM(Scoring Category Points) / Total Possible Points * 100%; categories: Data Center, Portfolio Review, Modernizing Federal IT, Cybersecurity, Transparency, IT Workforce, Working Capital Fund, Digital Services` |
| **Unit** | Score (0-100) |
| **Typical Range** | 40-85 |
| **Benchmark Range** | Target: >80; failing: <50 |
| **Value Driver Links** | Cost Savings, Risk Reduction, Mission Effectiveness |
| **Segment Applicability** | All Federal Civilian Agencies |
| **Calculation Frequency** | Quarterly |


### FED-KPI-004: CMMC / NIST SP 800-171 Compliance Score

| Attribute | Detail |
|-----------|--------|
| **Name** | CMMC / NIST SP 800-171 Compliance Score |
| **Formula** | `Implemented Controls / 110 Required Controls * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 40%-100% |
| **Benchmark Range** | CMMC Level 2: 100%; acceptable interim: >80% with POA&M |
| **Value Driver Links** | Risk Reduction, Working Capital |
| **Segment Applicability** | DoD, Defense Industrial Base |
| **Calculation Frequency** | Annual / Per assessment |


### FED-KPI-005: Small Business Prime Contracting Achievement Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | Small Business Prime Contracting Achievement Rate |
| **Formula** | `SB Prime Obligations / Total Eligible Obligations * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 15%-30% |
| **Benchmark Range** | Statutory goal: 23%; DoD goal: 20% |
| **Value Driver Links** | Mission Effectiveness, Cost Savings |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Annual |


### FED-KPI-006: Deobligation Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | Deobligation Rate |
| **Formula** | `Deobligated Funds / Total Obligations * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 2%-15% |
| **Benchmark Range** | Best practice: <5%; concerning: >10% |
| **Value Driver Links** | Working Capital, Cost Savings |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Annual |


### FED-KPI-007: Continuing Resolution Impact Factor

| Attribute | Detail |
|-----------|--------|
| **Name** | Continuing Resolution Impact Factor |
| **Formula** | `Days Under CR / 365 * (Frozen_New_Starts_Count / Total_Planned_New_Starts)` |
| **Unit** | Index (0-1) |
| **Typical Range** | 0.15-0.45 |
| **Benchmark Range** | Target: <0.10; disruptive: >0.30 |
| **Value Driver Links** | Working Capital, Cost Savings |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Annual |


### FED-KPI-008: FISMA Audit Finding Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | FISMA Audit Finding Rate |
| **Formula** | `FISMA Audit Findings / Security Controls Tested * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 5%-30% |
| **Benchmark Range** | Target: <5%; material weakness threshold varies by agency |
| **Value Driver Links** | Risk Reduction, Cost Savings |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Annual |


### FED-KPI-009: FedRAMP ATO Time (Months)

| Attribute | Detail |
|-----------|--------|
| **Name** | FedRAMP ATO Time (Months) |
| **Formula** | `(Authorization Date - FedRAMP Initiation Date) / 30.44` |
| **Unit** | Months |
| **Typical Range** | 12-24 months |
| **Benchmark Range** | Target: <12 months; concerning: >18 months |
| **Value Driver Links** | Risk Reduction, Cost Savings, Mission Effectiveness |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Per authorization |


### FED-KPI-010: Defense Working Capital Fund Turnover

| Attribute | Detail |
|-----------|--------|
| **Name** | Defense Working Capital Fund Turnover |
| **Formula** | `Cost of Goods Sold / Average Fund Balance` |
| **Unit** | Ratio |
| **Typical Range** | 2.0-4.5 |
| **Benchmark Range** | Target: >3.0; inefficient: <2.0 |
| **Value Driver Links** | Working Capital, Cost Savings |
| **Segment Applicability** | DoD |
| **Calculation Frequency** | Annual |


### FED-KPI-011: ITAR Compliance Incident Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | ITAR Compliance Incident Rate |
| **Formula** | `ITAR Violations or Escapes / Total Export Transactions * 1,000` |
| **Unit** | Per 1,000 transactions |
| **Typical Range** | 0.1-5.0 |
| **Benchmark Range** | Target: 0; acceptable with immediate remediation: <0.5 |
| **Value Driver Links** | Risk Reduction, Cost Savings |
| **Segment Applicability** | DoD, Intelligence Community, NASA, DOE/NNSA |
| **Calculation Frequency** | Quarterly |


### FED-KPI-012: Section 508 Conformance Score

| Attribute | Detail |
|-----------|--------|
| **Name** | Section 508 Conformance Score |
| **Formula** | `(WCAG 2.1 AA Compliant Pages / Total Pages) * 0.4 + (Accessible Documents / Total Documents) * 0.3 + (Procurement VPAT Availability Rate) * 0.3` |
| **Unit** | Score (0-100) |
| **Typical Range** | 30-80 |
| **Benchmark Range** | Target: >90; DOJ settlement threshold: <50 |
| **Value Driver Links** | Risk Reduction, Mission Effectiveness |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Annual |


### FED-KPI-013: RMF Control Implementation Coverage

| Attribute | Detail |
|-----------|--------|
| **Name** | RMF Control Implementation Coverage |
| **Formula** | `Implemented + Inherited Controls / Total Required Controls * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 60%-100% |
| **Benchmark Range** | ATO requirement: 100% with POA&M for gaps; interim: >85% |
| **Value Driver Links** | Risk Reduction, Working Capital |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Annual / Per system |


### FED-KPI-014: Obligation Rate by Quarter (Q4 Surge Index)

| Attribute | Detail |
|-----------|--------|
| **Name** | Obligation Rate by Quarter (Q4 Surge Index) |
| **Formula** | `Q4 Obligations / Annual Obligations * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 25%-55% |
| **Benchmark Range** | Target: <30% (smooth spending); concerning: >45% |
| **Value Driver Links** | Working Capital, Cost Savings |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Annual |


### FED-KPI-015: GAO Bid Protest Sustain Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | GAO Bid Protest Sustain Rate |
| **Formula** | `GAO Sustained Protests / Total GAO Protest Decisions * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 10%-20% |
| **Benchmark Range** | GAO historical average: ~15%; target: <10% via better requirements |
| **Value Driver Links** | Cost Savings, Working Capital |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Annual |


### FED-KPI-016: SAM Unique Entity Identifier Accuracy

| Attribute | Detail |
|-----------|--------|
| **Name** | SAM Unique Entity Identifier Accuracy |
| **Formula** | `Accurate and Active UEI Records / Total UEI Records in SAM * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 85%-98% |
| **Benchmark Range** | Target: >95%; award eligibility risk: <90% |
| **Value Driver Links** | Working Capital, Risk Reduction |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Quarterly |


### FED-KPI-017: Intergovernmental Transfer Reconciliation Error Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | Intergovernmental Transfer Reconciliation Error Rate |
| **Formula** | `Unreconciled Transfer Amounts / Total Transfer Volume * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 1%-8% |
| **Benchmark Range** | Target: <2%; audit risk: >5% |
| **Value Driver Links** | Working Capital, Risk Reduction |
| **Segment Applicability** | HHS, Treasury, DOT, DOJ |
| **Calculation Frequency** | Monthly |


### FED-KPI-018: Congressional Mandate Implementation Timeliness

| Attribute | Detail |
|-----------|--------|
| **Name** | Congressional Mandate Implementation Timeliness |
| **Formula** | `Mandates Implemented On Time / Total Mandates with Deadlines * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 60%-90% |
| **Benchmark Range** | Target: >90%; GAO concern: <75% |
| **Value Driver Links** | Risk Reduction, Mission Effectiveness |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Annual |


### FED-KPI-019: VA Disability Claims Pending Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | VA Disability Claims Pending Rate |
| **Formula** | `Pending Claims >125 Days / Total Pending Claims * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 20%-60% |
| **Benchmark Range** | VA target: <10%; congressional concern: >30% |
| **Value Driver Links** | Mission Effectiveness, Cost Savings |
| **Segment Applicability** | VA |
| **Calculation Frequency** | Weekly |


### FED-KPI-020: IRS Tax Gap Enforcement Yield

| Attribute | Detail |
|-----------|--------|
| **Name** | IRS Tax Gap Enforcement Yield |
| **Formula** | `Additional Revenue Collected via Enforcement / Estimated Tax Gap * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 5%-15% |
| **Benchmark Range** | Target: increasing trend; current baseline: ~10% |
| **Value Driver Links** | Revenue Uplift, Cost Savings |
| **Segment Applicability** | Treasury/IRS |
| **Calculation Frequency** | Annual |


### FED-KPI-021: Contract Closeout Backlog Ratio

| Attribute | Detail |
|-----------|--------|
| **Name** | Contract Closeout Backlog Ratio |
| **Formula** | `Physically Complete but Not Closed Contracts / Total Active Contracts * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 5%-25% |
| **Benchmark Range** | Target: <10%; DCMA concern: >20% |
| **Value Driver Links** | Working Capital, Cost Savings |
| **Segment Applicability** | DoD, DHS, VA |
| **Calculation Frequency** | Quarterly |


### FED-KPI-022: EIS Transition Completion Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | EIS Transition Completion Rate |
| **Formula** | `EIS Circuits Cutover / Total Legacy Circuits * 100%` |
| **Unit** | Percentage |
| **Typical Range** | 40%-95% |
| **Benchmark Range** | GSA deadline: 100% by FY2023 (extended); target: >95% |
| **Value Driver Links** | Cost Savings, Risk Reduction |
| **Segment Applicability** | All Federal Agencies |
| **Calculation Frequency** | Quarterly |

---

## Value Drivers


### FED-VD-001: RMF ATO timeline >18 months; eMASS package rejected >2 times...

| Attribute | Detail |
|-----------|--------|
| **Signal Pattern** | RMF ATO timeline >18 months; eMASS package rejected >2 times; POA&M items aging >120 days |
| **Interpreted Pain** | FED-PAIN-001 |
| **Value Driver Category** | Risk Reduction + Working Capital |
| **Linked KPIs** | FED-KPI-001, FED-KPI-013 |
| **Affected Personas** | FED-PERS-003, FED-PERS-002, FED-PERS-001 |
| **Confidence** | HIGH |
| **Required Evidence** | eMASS status report, POA&M age analysis, ISSO staffing plan, SCA availability schedule |


### FED-VD-002: FITARA score <65; O&M ratio >72%; legacy system age >20 year...

| Attribute | Detail |
|-----------|--------|
| **Signal Pattern** | FITARA score <65; O&M ratio >72%; legacy system age >20 years |
| **Interpreted Pain** | FED-PAIN-002 |
| **Value Driver Category** | Cost Savings + Risk Reduction |
| **Linked KPIs** | FED-KPI-003, PS-KPI-001, PS-KPI-002 |
| **Affected Personas** | FED-PERS-002, FED-PERS-001, PS-PERS-006 |
| **Confidence** | HIGH |
| **Required Evidence** | OMB FITARA scorecard, Budget justification IT section, System inventory with ages, Vendor EOL notices |


### FED-VD-003: CR in effect >3 months; Q4 obligation rate >45%; new start f...

| Attribute | Detail |
|-----------|--------|
| **Signal Pattern** | CR in effect >3 months; Q4 obligation rate >45%; new start freeze invoked |
| **Interpreted Pain** | FED-PAIN-003 |
| **Value Driver Category** | Working Capital + Cost Savings |
| **Linked KPIs** | FED-KPI-007, FED-KPI-014 |
| **Affected Personas** | FED-PERS-001, FED-PERS-006, PS-PERS-002 |
| **Confidence** | HIGH |
| **Required Evidence** | OMB CR guidance, Agency obligation timing data (FPDS), Contract stop-work history, New start list |


### FED-VD-004: FedRAMP ATO queue >20; shadow IT cloud detected; CSP withdra...

| Attribute | Detail |
|-----------|--------|
| **Signal Pattern** | FedRAMP ATO queue >20; shadow IT cloud detected; CSP withdrawn from marketplace |
| **Interpreted Pain** | FED-PAIN-004 |
| **Value Driver Category** | Cost Savings + Risk Reduction + Mission Effectiveness |
| **Linked KPIs** | FED-KPI-009, PS-KPI-029 |
| **Affected Personas** | FED-PERS-003, FED-PERS-002, PS-PERS-004 |
| **Confidence** | HIGH |
| **Required Evidence** | FedRAMP ATO tracker, CASB shadow IT report, Cloud procurement pipeline, CSP engagement status |


### FED-VD-005: SPRSSP score <100; POA&M items >50; C3PAO assessment not sch...

| Attribute | Detail |
|-----------|--------|
| **Signal Pattern** | SPRSSP score <100; POA&M items >50; C3PAO assessment not scheduled |
| **Interpreted Pain** | FED-PAIN-005 |
| **Value Driver Category** | Risk Reduction + Working Capital |
| **Linked KPIs** | FED-KPI-004, FED-KPI-011 |
| **Affected Personas** | FED-PERS-003, FED-PERS-004, PS-PERS-004 |
| **Confidence** | HIGH |
| **Required Evidence** | SPRSSP report, C3PAO engagement letter, Subcontractor compliance attestations, DoD contract eligibility review |


### FED-VD-006: 1102 vacancy rate >18%; procurement lead time >250 days; pro...

| Attribute | Detail |
|-----------|--------|
| **Signal Pattern** | 1102 vacancy rate >18%; procurement lead time >250 days; protest rate >5% on IT |
| **Interpreted Pain** | FED-PAIN-006 |
| **Value Driver Category** | Working Capital + Cost Savings |
| **Linked KPIs** | PS-KPI-013, PS-KPI-014, FED-KPI-015 |
| **Affected Personas** | FED-PERS-004, FED-PERS-001, PS-PERS-013 |
| **Confidence** | HIGH |
| **Required Evidence** | FPDS procurement timeline data, DAU workforce reports, GAO protest docket, Requirements revision log |


### FED-VD-007: Deobligation rate >8%; physically incomplete grants >180 day...

| Attribute | Detail |
|-----------|--------|
| **Signal Pattern** | Deobligation rate >8%; physically incomplete grants >180 days; closeout staffing <2 FTE per $1B |
| **Interpreted Pain** | FED-PAIN-008 |
| **Value Driver Category** | Working Capital + Cost Savings |
| **Linked KPIs** | FED-KPI-006, PS-KPI-009, PS-KPI-031 |
| **Affected Personas** | FED-PERS-005, PS-PERS-006, FED-PERS-002 |
| **Confidence** | HIGH |
| **Required Evidence** | Grant system deobligation report, Closeout staffing analysis, Recipient audit history, Physical completion backlog |


### FED-VD-008: Pending VA claims >200K; processing time >125 days; error ra...

| Attribute | Detail |
|-----------|--------|
| **Signal Pattern** | Pending VA claims >200K; processing time >125 days; error rate >10%; BVA appeals >100K |
| **Interpreted Pain** | FED-PAIN-010 |
| **Value Driver Category** | Mission Effectiveness + Cost Savings |
| **Linked KPIs** | FED-KPI-019, PS-KPI-006, PS-KPI-007 |
| **Affected Personas** | FED-PERS-001, PS-PERS-003, PS-PERS-008 |
| **Confidence** | HIGH |
| **Required Evidence** | VBA performance dashboard, Congressional inquiry log, Staffing analysis, Error rate report |


### FED-VD-009: Paper return backlog >1M; customer service LOS <70%; telepho...

| Attribute | Detail |
|-----------|--------|
| **Signal Pattern** | Paper return backlog >1M; customer service LOS <70%; telephone wait time >20 min |
| **Interpreted Pain** | FED-PAIN-011 |
| **Value Driver Category** | Revenue Uplift + Mission Effectiveness |
| **Linked KPIs** | FED-KPI-020, PS-KPI-015, PS-KPI-016 |
| **Affected Personas** | FED-PERS-002, PS-PERS-003, FED-PERS-006 |
| **Confidence** | HIGH |
| **Required Evidence** | IRS operational reports, Customer service metrics, CADE 2 project status, Tax gap estimates |


### FED-VD-010: Physically complete contracts >180 days not closed; DCAA inc...

| Attribute | Detail |
|-----------|--------|
| **Signal Pattern** | Physically complete contracts >180 days not closed; DCAA incurred cost backlog >2 years; closeout staffing vacancy >20% |
| **Interpreted Pain** | FED-PAIN-013 |
| **Value Driver Category** | Working Capital + Cost Savings |
| **Linked KPIs** | FED-KPI-021, PS-KPI-013 |
| **Affected Personas** | FED-PERS-004, FED-PERS-001, PS-PERS-013 |
| **Confidence** | HIGH |
| **Required Evidence** | Contract writing system report, DCAA workload metrics, Closeout staffing plan, Final indirect cost rate status |

---

## Value Formulas


### FED-VF-001: RMF ATO Acceleration Value

| Attribute | Detail |
|-----------|--------|
| **Name** | RMF ATO Acceleration Value |
| **Formula Expression** | `V = (Baseline_ATO_Months - Target_ATO_Months) * Program_Delay_Cost_Per_Month + Avoided_Interim_ATO_Risk_Cost` |
| **Required Inputs** | Baseline ATO timeline (months), Target ATO timeline (months), Program delay cost per month ($), Avoided interim ATO risk cost ($) |
| **Output Unit** | USD (3-year NPV) |
| **Applicable Segments** | All Federal Agencies |
| **Confidence Rules** | HIGH if eMASS and project schedule data available; MEDIUM if using agency averages; LOW if no program cost data |
| **Example Calculation** | Baseline 24 months → 12 months, $500K/month delay cost, $2M interim risk: 12 * $500K + $2M = $8M |


### FED-VF-002: FedRAMP Authorization Portfolio Value

| Attribute | Detail |
|-----------|--------|
| **Name** | FedRAMP Authorization Portfolio Value |
| **Formula Expression** | `V = (Avoided_Agency_ATO_Effort_Per_CSP * CSPs_Authorized) + (Shadow_IT_Risk_Avoidance) + (SaaS_Adoption_Value)` |
| **Required Inputs** | Agency ATO effort per CSP (FTE-hours), Number of CSPs requiring authorization, Shadow IT risk avoidance value ($), SaaS adoption value from faster procurement ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | All Federal Agencies |
| **Confidence Rules** | HIGH if CSP pipeline and ATO cost data available; MEDIUM if using FedRAMP averages; LOW if no pipeline visibility |
| **Example Calculation** | 500 FTE-hours per CSP @ $150/hr, 10 CSPs, $1M shadow risk, $2M adoption: $750K + $1M + $2M = $3.75M |


### FED-VF-003: Continuing Resolution Efficiency Loss

| Attribute | Detail |
|-----------|--------|
| **Name** | Continuing Resolution Efficiency Loss |
| **Formula Expression** | `V = (CR_Days / 365) * Annual_IT_Modernization_Budget * Planning_Inefficiency_Factor + Q4_Surge_Premium_Cost` |
| **Required Inputs** | Days under CR annually, Annual IT modernization budget ($), Planning inefficiency factor (0.15-0.30), Q4 obligation surge premium cost ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | All Federal Agencies |
| **Confidence Rules** | HIGH if budget actuals and obligation timing data available; MEDIUM if using historical averages; LOW if no modernization budget breakout |
| **Example Calculation** | 120 CR days, $100M modernization budget, 20% inefficiency, $3M surge premium: (120/365)*$100M*0.20 + $3M = $9.6M |


### FED-VF-004: CMMC Compliance Cost Avoidance

| Attribute | Detail |
|-----------|--------|
| **Name** | CMMC Compliance Cost Avoidance |
| **Formula Expression** | `V = (Baseline_Compliance_Cost - Target_Compliance_Cost) * Number_of_Affected_Contracts + Avoided_Debarment_Risk_Value` |
| **Required Inputs** | Baseline compliance cost per contract ($), Target compliance cost per contract ($), Number of affected contracts, Avoided debarment risk value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | DoD, Defense Industrial Base |
| **Confidence Rules** | HIGH if SPRSSP and contract data available; MEDIUM if using industry estimates; LOW if contract count unknown |
| **Example Calculation** | $150K→$80K per contract, 50 contracts, $5M debarment risk: (70K * 50) + $5M = $8.5M |


### FED-VF-005: 1102 Workforce Productivity Recovery

| Attribute | Detail |
|-----------|--------|
| **Name** | 1102 Workforce Productivity Recovery |
| **Formula Expression** | `V = (Target_Procurements_Per_1102 - Baseline_Procurements_Per_1102) * 1102_Headcount * Avg_Procurement_Value * Schedule_Compression_Value + Avoided_Protest_Cost` |
| **Required Inputs** | Baseline procurements per 1102 annually, Target procurements per 1102, 1102 headcount, Average procurement value ($), Schedule compression value (%), Avoided protest cost ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | All Federal Agencies |
| **Confidence Rules** | MEDIUM if FPDS and workforce data available; LOW if headcount or procurement volume unknown |
| **Example Calculation** | 8→12 procurements/1102, 500 1102s, $2M avg, 10% compression, $2M protest: 2,000 * $2M * 0.10 + $2M = $402M (requires normalization for realism) |


### FED-VF-006: ITAR Compliance Efficiency Value

| Attribute | Detail |
|-----------|--------|
| **Name** | ITAR Compliance Efficiency Value |
| **Formula Expression** | `V = (License_Processing_Time_Reduction * Applications_Per_Year * Staff_Cost_Per_Hour) + Avoided_Violation_Penalty + Faster_Program_Delivery_Value` |
| **Required Inputs** | License processing time reduction (hours), Annual applications, Staff cost per hour ($), Avoided violation penalty ($), Faster program delivery value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | DoD, NASA, DOE/NNSA |
| **Confidence Rules** | HIGH if DDTC license data and staffing cost available; MEDIUM if using estimates; LOW if application volume unknown |
| **Example Calculation** | 40 hours→10 hours reduction, 200 apps/year, $75/hr, $1M penalty avoidance, $500K delivery: (30 * 200 * $75) + $1M + $500K = $1.95M |


### FED-VF-007: Grant Deobligation Retention Value

| Attribute | Detail |
|-----------|--------|
| **Name** | Grant Deobligation Retention Value |
| **Formula Expression** | `V = (Baseline_Deobligation_Rate - Target_Deobligation_Rate) * Total_Annual_Grant_Obligations + Closeout_Efficiency_Savings` |
| **Required Inputs** | Baseline deobligation rate (%), Target deobligation rate (%), Annual grant obligations ($), Closeout efficiency savings ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | HHS, NSF, ED, DOJ, DHS |
| **Confidence Rules** | HIGH if grant system data available; MEDIUM if using agency averages; LOW if obligation volume unknown |
| **Example Calculation** | 10%→4% deobligation, $500M obligations, $1M closeout savings: $500M * 0.06 + $1M = $31M |


### FED-VF-008: VA Claims Processing Backlog Elimination

| Attribute | Detail |
|-----------|--------|
| **Name** | VA Claims Processing Backlog Elimination |
| **Formula Expression** | `V = (Baseline_Backlog - Target_Backlog) * Cost_Per_Claim_Processed + Overtime_Avoidance + Error_Rate_Reduction_Value + Veteran_Satisfaction_Value` |
| **Required Inputs** | Baseline backlog (claims), Target backlog, Cost per claim ($), Overtime avoidance ($), Error rate reduction value ($), Veteran satisfaction value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | VA |
| **Confidence Rules** | HIGH if VBA operational data available; MEDIUM if using VBA public reports; LOW if no cost data |
| **Example Calculation** | 200K→50K backlog, $300/claim, $2M overtime, $1M error reduction, $500K satisfaction: 150K*$300 + $2M + $1M + $500K = $50M |


### FED-VF-009: IRS Tax Gap Enforcement ROI

| Attribute | Detail |
|-----------|--------|
| **Name** | IRS Tax Gap Enforcement ROI |
| **Formula Expression** | `V = (Additional_Enforcement_Revenue - Enforcement_Cost_Increase) + Customer_Service_Improvement_Value + Paper_Processing_Reduction_Savings` |
| **Required Inputs** | Additional enforcement revenue ($), Enforcement cost increase ($), Customer service improvement value ($), Paper processing reduction savings ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | Treasury/IRS |
| **Confidence Rules** | HIGH if IRS operational and revenue data available; MEDIUM if using published tax gap estimates; LOW if no enforcement cost data |
| **Example Calculation** | $50M additional revenue - $20M cost + $5M service + $10M paper = $45M net |


### FED-VF-010: Section 508 Compliance Cost Avoidance

| Attribute | Detail |
|-----------|--------|
| **Name** | Section 508 Compliance Cost Avoidance |
| **Formula Expression** | `V = (Avoided_DOJ_Settlement_Cost) + (Remediation_Cost_Reduction) + (Procurement_Efficiency_Gain_from_VPAT_Automation)` |
| **Required Inputs** | DOJ settlement cost avoidance ($), Remediation cost reduction ($), Procurement efficiency gain ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | All Federal Agencies |
| **Confidence Rules** | HIGH if complaint history and remediation cost data available; MEDIUM if using DOJ published settlements; LOW if no complaint history |
| **Example Calculation** | $2M settlement avoidance + $1M remediation + $500K procurement = $3.5M |


### FED-VF-011: Contract Closeout Acceleration Value

| Attribute | Detail |
|-----------|--------|
| **Name** | Contract Closeout Acceleration Value |
| **Formula Expression** | `V = (Closed_Contracts - Baseline_Closeout_Rate) * Avg_Final_Indirect_Cost_Release_Value + DCAA_Audit_Efficiency_Savings + Staff_Productivity_Gain` |
| **Required Inputs** | Additional contracts closed annually, Average final indirect cost release value ($), DCAA audit efficiency savings ($), Staff productivity gain ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | DoD, DHS, VA |
| **Confidence Rules** | HIGH if contract writing system and DCAA data available; MEDIUM if using agency estimates; LOW if no closeout backlog data |
| **Example Calculation** | 500 additional closures, $50K avg release, $1M DCAA savings, $500K productivity: 500*$50K + $1M + $500K = $26.5M |


### FED-VF-012: EIS Transition Cost Avoidance

| Attribute | Detail |
|-----------|--------|
| **Name** | EIS Transition Cost Avoidance |
| **Formula Expression** | `V = (Legacy_Contract_Premium_Avoided) + (Network_Efficiency_Gain) + (Consolidation_Savings) - (Transition_Implementation_Cost)` |
| **Required Inputs** | Legacy contract premium avoided ($), Network efficiency gain ($), Consolidation savings ($), Transition implementation cost ($) |
| **Output Unit** | USD (annual, net of transition) |
| **Applicable Segments** | All Federal Agencies |
| **Confidence Rules** | HIGH if GSA billing and transition cost data available; MEDIUM if using GSA estimates; LOW if no legacy contract data |
| **Example Calculation** | $3M premium + $2M efficiency + $1M consolidation - $2M transition = $4M net annual |


### FED-VF-013: Congressional Mandate Tracking Efficiency

| Attribute | Detail |
|-----------|--------|
| **Name** | Congressional Mandate Tracking Efficiency |
| **Formula Expression** | `V = (Baseline_Mandate_Tracking_FTE_Cost - Target_FTE_Cost) + Avoided_GAO_Escalation_Cost + Faster_Implementation_Delivery_Value` |
| **Required Inputs** | Baseline FTE cost for mandate tracking ($), Target FTE cost with automation ($), Avoided GAO escalation cost ($), Faster implementation delivery value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | All Federal Agencies |
| **Confidence Rules** | MEDIUM if policy office staffing and GAO history available; LOW if no mandate tracking cost data |
| **Example Calculation** | $1.5M→$800K FTE, $500K GAO avoidance, $200K delivery: $700K + $500K + $200K = $1.4M |


### FED-VF-014: Small Business Goal Achievement Value

| Attribute | Detail |
|-----------|--------|
| **Name** | Small Business Goal Achievement Value |
| **Formula Expression** | `V = (SB_Obligation_Gap_Closure * Average_SB_Contract_Margin) + Avoided_SBA_Protest_Cost + Congressional_Relations_Value` |
| **Required Inputs** | SB obligation gap to goal ($), Average small business contract margin/value multiplier, Avoided SBA protest cost ($), Congressional relations value ($) |
| **Output Unit** | USD (annual) |
| **Applicable Segments** | All Federal Agencies |
| **Confidence Rules** | HIGH if FPDS SB data available; MEDIUM if using SBA goaling reports; LOW if no obligation data |
| **Example Calculation** | $10M gap closure * 1.2 multiplier + $500K protest + $200K relations = $12.7M |

---

## Benchmarks


### FED-BENCH-001: Federal RMF ATO Median Timeline

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal RMF ATO Median Timeline |
| **Value** | 18 |
| **Range** | 12-36 |
| **Unit** | Months |
| **Source** | GAO-22-104999; DoD CIO RMF metrics |
| **Source Type** | GAO Report / Federal Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | 2023 |


### FED-BENCH-002: FedRAMP Agency ATO Average Time

| Attribute | Detail |
|-----------|--------|
| **Name** | FedRAMP Agency ATO Average Time |
| **Value** | 14 |
| **Range** | 9-24 |
| **Unit** | Months |
| **Source** | FedRAMP PMO FY2023 Annual Report |
| **Source Type** | Federal Government Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | FY2023 |


### FED-BENCH-003: FedRAMP JAB P-ATO Average Time

| Attribute | Detail |
|-----------|--------|
| **Name** | FedRAMP JAB P-ATO Average Time |
| **Value** | 18 |
| **Range** | 12-30 |
| **Unit** | Months |
| **Source** | FedRAMP PMO FY2023 Annual Report |
| **Source Type** | Federal Government Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | FY2023 |


### FED-BENCH-004: OMB FITARA Scorecard Median Score

| Attribute | Detail |
|-----------|--------|
| **Name** | OMB FITARA Scorecard Median Score |
| **Value** | 65 |
| **Range** | 45-85 |
| **Unit** | Score (0-100) |
| **Source** | OMB FITARA Scorecard FY2023 Q4 |
| **Source Type** | Federal Government Data |
| **Segment Applicability** | All Federal Civilian Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | FY2023 |


### FED-BENCH-005: DoD CMMC Level 2 Control Baseline

| Attribute | Detail |
|-----------|--------|
| **Name** | DoD CMMC Level 2 Control Baseline |
| **Value** | 110 |
| **Range** | 110 |
| **Unit** | NIST SP 800-171 Controls |
| **Source** | DoD CMMC 2.0 Final Rule; NIST SP 800-171 Rev 2 |
| **Source Type** | Federal Regulation / NIST |
| **Segment Applicability** | DoD, Defense Industrial Base |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | 2023 |


### FED-BENCH-006: Federal 1102 Series Vacancy Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal 1102 Series Vacancy Rate |
| **Value** | 18 |
| **Range** | 12-25 |
| **Unit** | Percentage |
| **Source** | GAO-21-256; DAU Workforce Studies |
| **Source Type** | GAO Report / Federal Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | 2023 |


### FED-BENCH-007: Federal Procurement Cycle Time (Complex IT)

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal Procurement Cycle Time (Complex IT) |
| **Value** | 250 |
| **Range** | 180-365 |
| **Unit** | Days |
| **Source** | GAO-21-256; FPDS analysis |
| **Source Type** | GAO Report / Federal Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | 2021 |


### FED-BENCH-008: GAO Bid Protest Sustain Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | GAO Bid Protest Sustain Rate |
| **Value** | 15 |
| **Range** | 12-18 |
| **Unit** | Percentage |
| **Source** | GAO Bid Protest Annual Report FY2023 |
| **Source Type** | Federal Government Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | FY2023 |


### FED-BENCH-009: Federal Q4 Obligation Surge Rate

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal Q4 Obligation Surge Rate |
| **Value** | 42 |
| **Range** | 35-55 |
| **Unit** | Percentage of annual obligations in Q4 |
| **Source** | FPDS; OMB obligation timing analysis |
| **Source Type** | Federal Government Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | FY2023 |


### FED-BENCH-010: Federal IT Contractor Dependency

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal IT Contractor Dependency |
| **Value** | 58 |
| **Range** | 50-65 |
| **Unit** | Percentage of IT spend via contractors |
| **Source** | GAO-23-105492; FPDS |
| **Source Type** | GAO Report / Federal Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | 2023 |


### FED-BENCH-011: DDTC ITAR License Processing Time

| Attribute | Detail |
|-----------|--------|
| **Name** | DDTC ITAR License Processing Time |
| **Value** | 75 |
| **Range** | 45-120 |
| **Unit** | Days |
| **Source** | State Department DDTC annual report |
| **Source Type** | Federal Agency Data |
| **Segment Applicability** | DoD, NASA, DOE/NNSA |
| **Geographic Scope** | United States |
| **Confidence** | MEDIUM |
| **Date Sourced** | 2023 |


### FED-BENCH-012: VA Disability Claims Pending (Target)

| Attribute | Detail |
|-----------|--------|
| **Name** | VA Disability Claims Pending (Target) |
| **Value** | 125 |
| **Range** | 90-180 |
| **Unit** | Days average processing time |
| **Source** | VBA Performance Dashboard; VA OIG |
| **Source Type** | Federal Agency Data |
| **Segment Applicability** | VA |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | 2024 |


### FED-BENCH-013: IRS Customer Service Level of Service

| Attribute | Detail |
|-----------|--------|
| **Name** | IRS Customer Service Level of Service |
| **Value** | 68 |
| **Range** | 55-85 |
| **Unit** | Percentage |
| **Source** | IRS National Taxpayer Advocate Report FY2023 |
| **Source Type** | Federal Agency Data |
| **Segment Applicability** | Treasury/IRS |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | FY2023 |


### FED-BENCH-014: Federal Contract Closeout Backlog (DCMA)

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal Contract Closeout Backlog (DCMA) |
| **Value** | 125000 |
| **Range** | 100000-150000 |
| **Unit** | Physically complete but not closed actions |
| **Source** | DCMA closeout reports |
| **Source Type** | Federal Agency Data |
| **Segment Applicability** | DoD |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | 2023 |


### FED-BENCH-015: GSA EIS Transition Completion (Federal-wide)

| Attribute | Detail |
|-----------|--------|
| **Name** | GSA EIS Transition Completion (Federal-wide) |
| **Value** | 85 |
| **Range** | 70-95 |
| **Unit** | Percentage |
| **Source** | GSA EIS Transition Dashboard |
| **Source Type** | Federal Agency Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | 2024 |


### FED-BENCH-016: Federal Small Business Prime Achievement

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal Small Business Prime Achievement |
| **Value** | 23.4 |
| **Range** | 20-26 |
| **Unit** | Percentage of eligible obligations |
| **Source** | SBA Goaling Report FY2023 |
| **Source Type** | Federal Agency Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | FY2023 |


### FED-BENCH-017: NARA Electronic Records Transfer Compliance

| Attribute | Detail |
|-----------|--------|
| **Name** | NARA Electronic Records Transfer Compliance |
| **Value** | 45 |
| **Range** | 30-60 |
| **Unit** | Percentage of agencies fully compliant |
| **Source** | NARA annual report to Congress |
| **Source Type** | Federal Agency Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | MEDIUM |
| **Date Sourced** | 2023 |


### FED-BENCH-018: Federal FISMA Audit Finding Rate (Median)

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal FISMA Audit Finding Rate (Median) |
| **Value** | 12 |
| **Range** | 8-20 |
| **Unit** | Percentage of controls with findings |
| **Source** | OMB FISMA Annual Report to Congress 2023 |
| **Source Type** | Federal Government Data |
| **Segment Applicability** | All Federal Agencies |
| **Geographic Scope** | United States |
| **Confidence** | HIGH |
| **Date Sourced** | 2023 |

---

## Signal Interpretation Rules


### FED-SIG-001: RMF ATO Delay Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | RMF ATO Delay Signal |
| **Raw Signal Pattern** | eMASS package status unchanged >90 days; POA&M items aging >120 days; ISSO turnover detected; interim ATO >12 months |
| **Interpreted Meaning** | RMF process bottlenecked by control implementation gaps, SCA review delays, or resource constraints. System deployment and program schedule at risk. |
| **Linked Pains** | FED-PAIN-001 |
| **Linked KPIs** | FED-KPI-001, FED-KPI-013 |
| **Confidence Score** | 0.88 |
| **Required Confirmation Signals** | eMASS status report, ISSO staffing plan, SCA availability schedule, POA&M age analysis |


### FED-SIG-002: FITARA Score Decline Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | FITARA Score Decline Signal |
| **Raw Signal Pattern** | OMB scorecard score declined QoQ; data center consolidation behind plan; working capital fund underutilized; CIO authority gaps in budget formulation |
| **Interpreted Meaning** | Agency IT governance underperforming. Modernization funding, consolidation, and workforce management face structural barriers. Congressional scrutiny likely. |
| **Linked Pains** | FED-PAIN-002, FED-PAIN-003 |
| **Linked KPIs** | FED-KPI-003, PS-KPI-001 |
| **Confidence Score** | 0.85 |
| **Required Confirmation Signals** | OMB scorecard, Budget justification IT section, Data center closure schedule, CIO org chart |


### FED-SIG-003: Continuing Resolution Planning Freeze Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | Continuing Resolution Planning Freeze Signal |
| **Raw Signal Pattern** | CR in effect >3 months; new start freeze invoked by OMB; Q1 obligation rate <15% of annual; Q4 obligation rate >45% |
| **Interpreted Meaning** | Agency cannot execute multi-year planning. Procurement timelines compressed. Q4 spend surge creates waste and suboptimal awards. |
| **Linked Pains** | FED-PAIN-003 |
| **Linked KPIs** | FED-KPI-007, FED-KPI-014 |
| **Confidence Score** | 0.92 |
| **Required Confirmation Signals** | OMB CR guidance, Agency contingency plan, FPDS obligation timing data, Contract stop-work history |


### FED-SIG-004: FedRAMP Marketplace Gap Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | FedRAMP Marketplace Gap Signal |
| **Raw Signal Pattern** | Agency ATO queue >20 pending; CSP withdrawn from FedRAMP in last 12 months; shadow IT cloud detected via CASB; SaaS procurement blocked pending ATO |
| **Interpreted Meaning** | FedRAMP authorization capacity insufficient for agency cloud demand. Shadow IT risk rising. Innovation adoption constrained. |
| **Linked Pains** | FED-PAIN-004 |
| **Linked KPIs** | FED-KPI-009, PS-KPI-029 |
| **Confidence Score** | 0.85 |
| **Required Confirmation Signals** | FedRAMP ATO tracker, CASB shadow IT report, Cloud procurement pipeline, CSP engagement status |


### FED-SIG-005: CMMC Compliance Gap Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | CMMC Compliance Gap Signal |
| **Raw Signal Pattern** | SPRSSP score <100; POA&M items >50; C3PAO assessment not scheduled; subcontractor compliance unverified; contract award eligibility at risk |
| **Interpreted Meaning** | DOD contractor (prime or sub) not ready for CMMC Level 2/3. Supply chain accreditation risk. Potential contract loss or stop-work. |
| **Linked Pains** | FED-PAIN-005 |
| **Linked KPIs** | FED-KPI-004, FED-KPI-011 |
| **Confidence Score** | 0.9 |
| **Required Confirmation Signals** | SPRSSP report, C3PAO engagement letter, Subcontractor compliance attestations, DoD contract eligibility review |


### FED-SIG-006: 1102 Workforce Crisis Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | 1102 Workforce Crisis Signal |
| **Raw Signal Pattern** | 1102 vacancy rate >18%; procurement action lead time >250 days; protest rate >5% on IT acquisitions; requirements packages >3 revisions |
| **Interpreted Meaning** | Acquisition workforce cannot meet demand. Complex IT procurements failing. Schedule and capability delivery at risk. |
| **Linked Pains** | FED-PAIN-006 |
| **Linked KPIs** | PS-KPI-011, PS-KPI-012, FED-KPI-015 |
| **Confidence Score** | 0.88 |
| **Required Confirmation Signals** | FPDS procurement timeline data, DAU workforce reports, GAO protest docket, Requirements revision log |


### FED-SIG-007: ITAR License Delay Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | ITAR License Delay Signal |
| **Raw Signal Pattern** | DDTC license application processing time >90 days; ITAR staffing turnover >20%; violations in last 3 years; commingled ITAR/unclassified environments |
| **Interpreted Meaning** | Export control compliance operations understaffed or under-resourced. Program delays and legal/debarment risk rising. |
| **Linked Pains** | FED-PAIN-007 |
| **Linked KPIs** | FED-KPI-011, PS-KPI-021 |
| **Confidence Score** | 0.82 |
| **Required Confirmation Signals** | DDTC license queue, ITAR compliance audit, Export transaction logs, Commingled environment assessment |


### FED-SIG-008: Grant Deobligation Surge Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | Grant Deobligation Surge Signal |
| **Raw Signal Pattern** | Deobligation rate >8%; physically incomplete grants >180 days past end; closeout staffing <2 FTE per $1B; recipient audit findings recurring |
| **Interpreted Meaning** | Grant management lifecycle broken at closeout stage. Appropriated funds returning to Treasury. Program impact reduced. |
| **Linked Pains** | FED-PAIN-008 |
| **Linked KPIs** | FED-KPI-006, PS-KPI-009, PS-KPI-031 |
| **Confidence Score** | 0.85 |
| **Required Confirmation Signals** | Grant system deobligation report, Closeout staffing analysis, Recipient audit history, Physical completion backlog |


### FED-SIG-009: Cross-Domain Friction Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | Cross-Domain Friction Signal |
| **Raw Signal Pattern** | Cross-domain transfer approval time >30 days; manual data transfer (sneakernet) observed; ICD 503 compliance gaps; CUI mishandling incidents |
| **Interpreted Meaning** | Information sharing across classification boundaries impeded by inadequate cross-domain solutions or data tagging. Mission effectiveness and security both compromised. |
| **Linked Pains** | FED-PAIN-009 |
| **Linked KPIs** | PS-KPI-032, FED-KPI-011 |
| **Confidence Score** | 0.85 |
| **Required Confirmation Signals** | Cross-domain transfer logs, ICD 503 assessment, CUI incident reports, Data tagging audit |


### FED-SIG-010: VA Claims Backlog Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | VA Claims Backlog Signal |
| **Raw Signal Pattern** | Pending disability claims >200K; average processing time >125 days; error rate >10%; appeals backlog >100K at BVA |
| **Interpreted Meaning** | VBA processing capacity insufficient for demand. Veteran satisfaction and congressional scrutiny rising. Overtime and temp staffing costs increasing. |
| **Linked Pains** | FED-PAIN-010 |
| **Linked KPIs** | FED-KPI-019, PS-KPI-006, PS-KPI-007 |
| **Confidence Score** | 0.9 |
| **Required Confirmation Signals** | VBA performance dashboard, Congressional inquiry log, Staffing analysis, Error rate report |


### FED-SIG-011: IRS Service Delivery Strain Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | IRS Service Delivery Strain Signal |
| **Raw Signal Pattern** | Paper return backlog >1M; customer service LOS <70%; telephone wait time >20 min; CADE 2 transition behind schedule |
| **Interpreted Meaning** | IRS operational infrastructure overwhelmed during filing season. Taxpayer service degraded. Tax gap enforcement capacity constrained. |
| **Linked Pains** | FED-PAIN-011 |
| **Linked KPIs** | FED-KPI-020, PS-KPI-015, PS-KPI-016 |
| **Confidence Score** | 0.88 |
| **Required Confirmation Signals** | IRS operational reports, Customer service metrics, CADE 2 project status, Tax gap estimates |


### FED-SIG-012: Section 508 Settlement Risk Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | Section 508 Settlement Risk Signal |
| **Raw Signal Pattern** | Section 508 complaints >10 per year; DOJ settlement active; procurement lacking VPAT; video without captions |
| **Interpreted Meaning** | Agency at risk of DOJ enforcement action, complaint-driven litigation, or OIG finding. Digital accessibility compliance immature. |
| **Linked Pains** | FED-PAIN-012 |
| **Linked KPIs** | FED-KPI-012, PS-KPI-020, PS-KPI-021 |
| **Confidence Score** | 0.85 |
| **Required Confirmation Signals** | DOJ complaint log, 508 conformance testing results, Procurement VPAT inventory, Video caption audit |


### FED-SIG-013: Contract Closeout Backlog Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | Contract Closeout Backlog Signal |
| **Raw Signal Pattern** | Physically complete contracts >180 days not closed; DCAA incurred cost backlog >2 years; closeout staffing vacancy >20% |
| **Interpreted Meaning** | Contract closeout process broken due to staffing, DCAA audit delays, or documentation gaps. Working capital tied up. Final indirect cost rates unresolved. |
| **Linked Pains** | FED-PAIN-013 |
| **Linked KPIs** | FED-KPI-021, PS-KPI-013 |
| **Confidence Score** | 0.8 |
| **Required Confirmation Signals** | Contract writing system report, DCAA workload metrics, Closeout staffing plan, Final indirect cost rate status |


### FED-SIG-014: EIS Transition Stalled Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | EIS Transition Stalled Signal |
| **Raw Signal Pattern** | EIS transition <80% complete; legacy contract extension fees >10%; telecom inventory data quality issues; circuit cutover failures |
| **Interpreted Meaning** | GSA EIS transition behind schedule. Legacy FTS/Networx contracts extended at premium. Network modernization and cost savings delayed. |
| **Linked Pains** | FED-PAIN-014 |
| **Linked KPIs** | FED-KPI-022, PS-KPI-030 |
| **Confidence Score** | 0.85 |
| **Required Confirmation Signals** | GSA EIS dashboard, Legacy contract billing analysis, Telecom inventory audit, Cutover failure log |


### FED-SIG-015: Congressional Mandate Overload Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | Congressional Mandate Overload Signal |
| **Raw Signal Pattern** | Open mandates >50; GAO reporting requirements >10 per year; mandate compliance rate <80%; IG findings on noncompliance |
| **Interpreted Meaning** | Policy office overwhelmed by statutory mandates. Implementation tracking inadequate. Risk of missed deadlines and GAO/IG escalation. |
| **Linked Pains** | FED-PAIN-015 |
| **Linked KPIs** | FED-KPI-018, PS-KPI-020 |
| **Confidence Score** | 0.82 |
| **Required Confirmation Signals** | Mandate tracking system, GAO recommendation database, OMB passback comments, IG correspondence |


### FED-SIG-016: Small Business Goal Miss Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | Small Business Goal Miss Signal |
| **Raw Signal Pattern** | SB prime achievement <90% of 23% goal; bundling determinations >5 per year; subcontracting plan defaults >3; SBA protests increasing |
| **Interpreted Meaning** | Agency failing to meet statutory small business contracting goals. SBA and congressional scrutiny likely. Bundling reducing competition. |
| **Linked Pains** | FED-PAIN-016 |
| **Linked KPIs** | FED-KPI-005, PS-KPI-014 |
| **Confidence Score** | 0.85 |
| **Required Confirmation Signals** | SBA Goaling Report, FPDS small business data, Bundling justification files, Subcontracting plan database |


### FED-SIG-017: NARA Electronic Records Noncompliance Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | NARA Electronic Records Noncompliance Signal |
| **Raw Signal Pattern** | Paper records >20% of holdings; email archive not NARA-compliant; records schedule not approved; e-discovery costs >$500K per case |
| **Interpreted Meaning** | Records management not transitioned to electronic per M-19-21/M-23-07. NARA compliance risk. Legal discovery costs excessive. |
| **Linked Pains** | FED-PAIN-017 |
| **Linked KPIs** | PS-KPI-024, FED-KPI-012 |
| **Confidence Score** | 0.8 |
| **Required Confirmation Signals** | NARA appraisal status, Records retention schedule, e-discovery cost history, Email archive assessment |


### FED-SIG-018: Counterfeit Parts / Supply Chain Risk Signal

| Attribute | Detail |
|-----------|--------|
| **Name** | Counterfeit Parts / Supply Chain Risk Signal |
| **Raw Signal Pattern** | Counterfeit parts detected in last 3 years; single-source critical suppliers >10; GIDEP alerts >5 per year; foreign microelectronics dependency |
| **Interpreted Meaning** | Supply chain integrity at risk for space, defense, or nuclear programs. DFARS compliance gaps. Program failure or safety risk possible. |
| **Linked Pains** | FED-PAIN-018 |
| **Linked KPIs** | FED-KPI-011, FED-KPI-004 |
| **Confidence Score** | 0.85 |
| **Required Confirmation Signals** | GIDEP alert log, Supplier audit results, DFARS 252.246-7007 compliance report, Foreign dependency assessment |

---

## Evidence Sources


### FED-EVID-001: GAO Federal IT Reports

| Attribute | Detail |
|-----------|--------|
| **Name** | GAO Federal IT Reports |
| **Description** | GAO assessments of federal IT acquisition, modernization, and cybersecurity. High-confidence evidence on legacy systems, cloud adoption, and workforce gaps. |
| **Access Method** | GAO.gov; search by report number (GAO-XX-XXXXX) |
| **Confidence Level** | HIGH |
| **Update Frequency** | Continuous (new reports weekly) |
| **Applicable Segments** | All Federal Agencies |
| **Key Uses** | Legacy system quantification, Procurement cycle benchmarking, Cybersecurity gap identification |


### FED-EVID-002: OMB FITARA Scorecard

| Attribute | Detail |
|-----------|--------|
| **Name** | OMB FITARA Scorecard |
| **Description** | Quarterly CIO performance scorecard covering data center consolidation, portfolio review, IT workforce, working capital fund, and cybersecurity. |
| **Access Method** | OMB.gov / CIO.gov |
| **Confidence Level** | HIGH |
| **Update Frequency** | Quarterly |
| **Applicable Segments** | All Federal Civilian Agencies |
| **Key Uses** | CIO accountability benchmarking, Modernization priority identification, IT governance gap analysis |


### FED-EVID-003: FedRAMP PMO Reports

| Attribute | Detail |
|-----------|--------|
| **Name** | FedRAMP PMO Reports |
| **Description** | FedRAMP authorization statistics, marketplace inventory, and agency ATO timeline data. |
| **Access Method** | fedramp.gov / marketplace |
| **Confidence Level** | HIGH |
| **Update Frequency** | Monthly/Annual |
| **Applicable Segments** | All Federal Agencies |
| **Key Uses** | Cloud authorization bottleneck quantification, CSP availability assessment, Shadow IT justification |


### FED-EVID-004: DoD CMMC and SPRSSP Data

| Attribute | Detail |
|-----------|--------|
| **Name** | DoD CMMC and SPRSSP Data |
| **Description** | Defense contractor cybersecurity readiness assessments and CMMC implementation status. |
| **Access Method** | DoD OSBP / DIBNet / C3PAO reports |
| **Confidence Level** | HIGH |
| **Update Frequency** | Annual / Per assessment |
| **Applicable Segments** | DoD, Defense Industrial Base |
| **Key Uses** | CMMC compliance gap sizing, Contract eligibility risk, Supply chain security assessment |


### FED-EVID-005: FPDS / USASpending.gov Contract Data

| Attribute | Detail |
|-----------|--------|
| **Name** | FPDS / USASpending.gov Contract Data |
| **Description** | Federal contract transaction-level data including competition, socio-economic achievement, and obligation timing. |
| **Access Method** | USASpending.gov / FPDS.gov |
| **Confidence Level** | HIGH |
| **Update Frequency** | Near real-time |
| **Applicable Segments** | All Federal Agencies |
| **Key Uses** | Small business goal tracking, Procurement timeline benchmarking, Obligation surge analysis |


### FED-EVID-006: Agency OIG Reports

| Attribute | Detail |
|-----------|--------|
| **Name** | Agency OIG Reports |
| **Description** | Agency-specific audit, inspection, and investigation reports. Reveals internal control weaknesses and program integrity issues. |
| **Access Method** | Oversight.gov / individual agency OIG websites |
| **Confidence Level** | HIGH |
| **Update Frequency** | Quarterly to annual |
| **Applicable Segments** | All Federal Agencies |
| **Key Uses** | Repeat finding identification, Fraud/waste indicators, Compliance gap documentation |


### FED-EVID-007: CISA BODs and Alerts

| Attribute | Detail |
|-----------|--------|
| **Name** | CISA BODs and Alerts |
| **Description** | Binding Operational Directives and emergency directives requiring federal agency action on cybersecurity. |
| **Access Method** | cisa.gov / binding-operational-directives |
| **Confidence Level** | HIGH |
| **Update Frequency** | Ad-hoc (event-driven) |
| **Applicable Segments** | All Federal Agencies |
| **Key Uses** | Vulnerability exposure quantification, Patch compliance gaps, Security tool procurement triggers |


### FED-EVID-008: NARA Records Management Reports

| Attribute | Detail |
|-----------|--------|
| **Name** | NARA Records Management Reports |
| **Description** | Agency records management compliance status, electronic records transfer data, and appraisal backlogs. |
| **Access Method** | archives.gov / NARA reports to Congress |
| **Confidence Level** | HIGH |
| **Update Frequency** | Annual |
| **Applicable Segments** | All Federal Agencies |
| **Key Uses** | Electronic records compliance gap, Paper records volume, NARA enforcement risk |

---

## Buying Triggers


### FED-TRIG-001: GAO High Risk List Update

| Attribute | Detail |
|-----------|--------|
| **Name** | GAO High Risk List Update |
| **Trigger Event** | GAO releases biennial High Risk List update with agency-specific recommendations |
| **Urgency Level** | HIGH |
| **Typical Timing** | 30-90 days post-release (agency response period) |
| **Affected Segments** | All Federal Agencies on High Risk List |
| **Linked Pains** | FED-PAIN-002, FED-PAIN-010, FED-PAIN-011, PS-PAIN-001 |
| **Procurement Implications** | Directed procurements for remediation; IG monitoring; congressional hearing preparation; sole-source justification possible for urgent fixes |


### FED-TRIG-002: OMB FITARA Scorecard Release

| Attribute | Detail |
|-----------|--------|
| **Name** | OMB FITARA Scorecard Release |
| **Trigger Event** | OMB releases quarterly FITARA scorecard showing agency score decline or persistent low performance |
| **Urgency Level** | HIGH |
| **Typical Timing** | 30-60 days post-scorecard (agency remediation window) |
| **Affected Segments** | All Federal Civilian Agencies |
| **Linked Pains** | FED-PAIN-002, FED-PAIN-003 |
| **Procurement Implications** | CIO-driven remediation procurements; data center consolidation contracts; working capital fund requests; modernization SOWs |


### FED-TRIG-003: CISA Binding Operational Directive (BOD)

| Attribute | Detail |
|-----------|--------|
| **Name** | CISA Binding Operational Directive (BOD) |
| **Trigger Event** | CISA issues BOD requiring specific action (e.g., BOD 22-01 KEV patching, BOD 23-02 asset management) |
| **Urgency Level** | CRITICAL |
| **Typical Timing** | Compliance deadline-driven; typically 30-180 days |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | PS-PAIN-002, FED-PAIN-001, FED-PAIN-012 |
| **Procurement Implications** | Emergency procurement authority; COTS security tools; vulnerability management platforms; EDR/XDR; asset discovery |


### FED-TRIG-004: FedRAMP Marketplace Gap / Agency ATO Need

| Attribute | Detail |
|-----------|--------|
| **Name** | FedRAMP Marketplace Gap / Agency ATO Need |
| **Trigger Event** | Agency identifies mission-critical SaaS need with no FedRAMP-authorized equivalent; or CSP withdraws from marketplace |
| **Urgency Level** | HIGH |
| **Typical Timing** | 60-120 days to sponsor or pursue agency ATO |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-004, PS-PAIN-023 |
| **Procurement Implications** | FedRAMP Fast Track sponsorship; agency ATO support contract; hybrid deployment; sole-source if only viable vendor |


### FED-TRIG-005: DoD CMMC Rule Effective Date / Contract Clause Insertion

| Attribute | Detail |
|-----------|--------|
| **Name** | DoD CMMC Rule Effective Date / Contract Clause Insertion |
| **Trigger Event** | DoD inserts CMMC clause into RFP or contract; CMMC assessment deadline approaches |
| **Urgency Level** | HIGH |
| **Typical Timing** | 6-18 months before contract award or assessment deadline |
| **Affected Segments** | DoD, Defense Industrial Base |
| **Linked Pains** | FED-PAIN-005 |
| **Procurement Implications** | C3PAO assessment contracts; cybersecurity consulting; SPRSSP remediation; GRC platform procurement |


### FED-TRIG-006: Continuing Resolution Resolution / Full Appropriation

| Attribute | Detail |
|-----------|--------|
| **Name** | Continuing Resolution Resolution / Full Appropriation |
| **Trigger Event** | CR ends with full-year appropriation; shutdown ends with retroactive funding |
| **Urgency Level** | HIGH |
| **Typical Timing** | 30-90 days post-resolution (compressed obligation window) |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-003, PS-PAIN-007, FED-PAIN-006 |
| **Procurement Implications** | Compressed procurement timelines; use-it-or-lose-it spending surge; simplified acquisition threshold utilization; pre-positioned proposals execute |


### FED-TRIG-007: 1102 Workforce Retirement Wave / Vacancy Surge

| Attribute | Detail |
|-----------|--------|
| **Name** | 1102 Workforce Retirement Wave / Vacancy Surge |
| **Trigger Event** | >20% of contracting workforce eligible for retirement within 3 years; vacancy rate spikes >15% |
| **Urgency Level** | HIGH |
| **Typical Timing** | 2-5 year horizon; immediate when surge hits |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-006, PS-PAIN-006 |
| **Procurement Implications** | Acquisition support services (AAS); staff augmentation; knowledge management systems; automated procurement tools; DAU training technology |


### FED-TRIG-008: NARA Electronic Records Deadline Extension / Enforcement

| Attribute | Detail |
|-----------|--------|
| **Name** | NARA Electronic Records Deadline Extension / Enforcement |
| **Trigger Event** | NARA issues noncompliance notice; records management deadline extension expires; litigation requires e-discovery |
| **Urgency Level** | HIGH |
| **Typical Timing** | Deadline-driven; litigation immediate |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-017, PS-PAIN-014 |
| **Procurement Implications** | Records management platform; email archiving; e-discovery tools; NARA-compliant storage; digitization services |


### FED-TRIG-009: TMF Board Funding Round Approval

| Attribute | Detail |
|-----------|--------|
| **Name** | TMF Board Funding Round Approval |
| **Trigger Event** | TMF Board approves agency project for repayable capital funding |
| **Urgency Level** | HIGH |
| **Typical Timing** | 90-180 days post-approval (procurement planning window) |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-002, PS-PAIN-001, PS-PAIN-023 |
| **Procurement Implications** | Modernization services; cloud migration; legacy replacement; agile development; repayment-plan-aware pricing |


### FED-TRIG-010: Recompete / Contract Option Decline

| Attribute | Detail |
|-----------|--------|
| **Name** | Recompete / Contract Option Decline |
| **Trigger Event** | Major contract within 12-18 months of expiration; option years not exercised; CPARS rating below satisfactory |
| **Urgency Level** | MEDIUM |
| **Typical Timing** | 12-24 months before expiration for capture planning |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-006, PS-PAIN-007, FED-PAIN-013 |
| **Procurement Implications** | Full and open competition; incumbent displacement opportunity; past performance requirements; transition planning |


### FED-TRIG-011: Congressional Hearing / Committee Inquiry

| Attribute | Detail |
|-----------|--------|
| **Name** | Congressional Hearing / Committee Inquiry |
| **Trigger Event** | House or Senate committee schedules oversight hearing on agency program with documented failures |
| **Urgency Level** | HIGH |
| **Typical Timing** | 30-90 days pre-hearing (remediation scramble) |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-010, FED-PAIN-011, FED-PAIN-015, PS-PAIN-003 |
| **Procurement Implications** | Urgent remediation services; dashboard/analytics for hearing prep; consulting for response strategy; rapid deployment |


### FED-TRIG-012: OIG Report with Management Commitment

| Attribute | Detail |
|-----------|--------|
| **Name** | OIG Report with Management Commitment |
| **Trigger Event** | Agency OIG issues report with management decision to implement recommendations within 12 months |
| **Urgency Level** | HIGH |
| **Typical Timing** | 30-90 days post-report (management response window) |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | PS-PAIN-011, FED-PAIN-001, FED-PAIN-012, FED-PAIN-017 |
| **Procurement Implications** | Directed procurement for remediation; IG may monitor vendor selection; corrective action plan drives requirements |


### FED-TRIG-013: New Administration Priority Alignment

| Attribute | Detail |
|-----------|--------|
| **Name** | New Administration Priority Alignment |
| **Trigger Event** | New administration publishes technology or program priorities (e.g., AI, quantum, clean energy, cybersecurity) |
| **Urgency Level** | MEDIUM |
| **Typical Timing** | 90-180 days post-inauguration or policy release |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-015, FED-PAIN-002, PS-PAIN-011 |
| **Procurement Implications** | Strategic alignment messaging; policy-aware solution positioning; OMB guidance-responsive proposals; early engagement with policy offices |


### FED-TRIG-014: Zero Trust Implementation Milestone

| Attribute | Detail |
|-----------|--------|
| **Name** | Zero Trust Implementation Milestone |
| **Trigger Event** | OMB M-22-09 milestone deadline approaching; CISA Zero Trust maturity assessment scheduled; agency score <2.0 |
| **Urgency Level** | HIGH |
| **Typical Timing** | 6-12 months before milestone |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | PS-PAIN-002, FED-PAIN-001, FED-PAIN-012 |
| **Procurement Implications** | Identity platform (ICAM); EDR/XDR; network segmentation; PIV/CAC integration; privileged access management |


### FED-TRIG-015: GSA EIS Contract Extension Expiration

| Attribute | Detail |
|-----------|--------|
| **Name** | GSA EIS Contract Extension Expiration |
| **Trigger Event** | Agency legacy telecom contract extension expires; GSA imposes premium pricing or discontinues support |
| **Urgency Level** | HIGH |
| **Typical Timing** | 6-12 months before extension expiration |
| **Affected Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-014, PS-PAIN-001 |
| **Procurement Implications** | EIS transition services; network modernization; unified communications; SD-WAN; cloud connectivity |

---

## Persona Profiles


### FED-PERS-001: Program Manager (Federal)

| Attribute | Detail |
|-----------|--------|
| **Name** | Program Manager (Federal) |
| **GS Series** | 1101/0343/2210/0340 |
| **Grade Range** | GS-13 to GS-15 |
| **Role Description** | Manages federal program lifecycle from requirements development through contract execution and CDRL delivery. Accountable for schedule, budget, and performance metrics. PMP-certified or DAWIA Level III preferred. |
| **Trusted Evidence** | GAO program assessments, OMB performance.gov metrics, DCMA contract performance reports, Earned value management data |
| **Disliked Claims** | Vendor promises without past performance references, Solutions that bypass federal acquisition regulations, Black-box AI without auditability, Proposals ignoring CDRL requirements |
| **Budget Influence** | Program level ($5M-$500M) |
| **Linked Pains** | FED-PAIN-001, FED-PAIN-002, FED-PAIN-006, FED-PAIN-013 |
| **Linked KPIs** | FED-KPI-002, FED-KPI-006, PS-KPI-013 |
| **Communication Preferences** | Briefings with structured agendas; data-driven ROI calculations; compliance with FAR/DFARS |


### FED-PERS-002: CIO (Civilian Agency)

| Attribute | Detail |
|-----------|--------|
| **Name** | CIO (Civilian Agency) |
| **GS Series** | 2210 |
| **Grade Range** | SES or GS-15 with SES potential |
| **Role Description** | Agency chief information officer accountable to OMB FITARA scorecard, TMF investment decisions, Zero Trust implementation (M-22-09), and enterprise architecture. Reports to Secretary/Deputy Secretary. |
| **Trusted Evidence** | OMB FITARA scorecard, CISA assessments, GAO IT reports, NIST frameworks, TMF project outcomes |
| **Disliked Claims** | Rip-and-replace without transition plan, Cloud-first ignoring data gravity, Solutions without FedRAMP path, Vendor lock-in without exit strategy |
| **Budget Influence** | Enterprise IT ($50M-$2B) |
| **Linked Pains** | FED-PAIN-002, FED-PAIN-004, FED-PAIN-012, FED-PAIN-014, FED-PAIN-017 |
| **Linked KPIs** | FED-KPI-003, FED-KPI-009, FED-KPI-012, PS-KPI-028 |
| **Communication Preferences** | Executive summaries with risk framing; OMB-compatible metrics; reference architecture alignment |


### FED-PERS-003: ISSO / ISSM (Information System Security Officer/Manager)

| Attribute | Detail |
|-----------|--------|
| **Name** | ISSO / ISSM (Information System Security Officer/Manager) |
| **GS Series** | 2210 |
| **Grade Range** | GS-13 to GS-15 |
| **Role Description** | Owns RMF package for one or more systems. Manages eMASS entry, POA&M lifecycle, continuous monitoring, and ATO maintenance. Coordinates with AO, SCAs, and CSPs for authorization actions. |
| **Trusted Evidence** | NIST SP 800-53 controls, CISA BODs, eMASS metrics, ICD 503/DCID 6/3, DISA STIGs |
| **Disliked Claims** | Tools without RMF integration, Cloud security claims without evidence, Automated compliance without manual validation, Solutions that bypass ISSO review |
| **Budget Influence** | System-level security ($500K-$10M) |
| **Linked Pains** | FED-PAIN-001, FED-PAIN-004, FED-PAIN-005, FED-PAIN-007, FED-PAIN-009, FED-PAIN-012 |
| **Linked KPIs** | FED-KPI-001, FED-KPI-004, FED-KPI-008, FED-KPI-009, FED-KPI-011, FED-KPI-013 |
| **Communication Preferences** | STIG-aligned configurations; NIST control mapping; POA&M automation; eMASS integration APIs |


### FED-PERS-004: Contracting Officer (KO)

| Attribute | Detail |
|-----------|--------|
| **Name** | Contracting Officer (KO) |
| **GS Series** | 1102 |
| **Grade Range** | GS-12 to GS-15 (warranted authority) |
| **Role Description** | Federal contracting officer with warranted authority to obligate government funds. Interprets FAR, DFARS, and agency supplements. Manages procurement lifecycle from acquisition planning to contract closeout. |
| **Trusted Evidence** | FPDS data, GAO bid protest decisions, FAR provisions, CPSR results, DCAA audit findings |
| **Disliked Claims** | Solutions that circumvent full and open competition, Sole-source justifications without market research, Proposals with ambiguous IP rights, Vendors unfamiliar with federal contracting |
| **Budget Influence** | Contract level ($1M-$500M) |
| **Linked Pains** | FED-PAIN-006, FED-PAIN-013, FED-PAIN-016, PS-PAIN-007 |
| **Linked KPIs** | PS-KPI-013, PS-KPI-014, FED-KPI-015, FED-KPI-021 |
| **Communication Preferences** | FAR-compliant proposals; clear CLIN structure; past performance references; realistic delivery schedules |


### FED-PERS-005: Grants Management Specialist

| Attribute | Detail |
|-----------|--------|
| **Name** | Grants Management Specialist |
| **GS Series** | 1109 |
| **Grade Range** | GS-12 to GS-14 |
| **Role Description** | Manages federal grant lifecycle from NOFO development through award, monitoring, and closeout. Expert in 2 CFR 200 (Uniform Guidance), grant systems (Grants.gov, SAM.gov, HHS PSC), and recipient risk assessment. |
| **Trusted Evidence** | Federal Audit Clearinghouse data, 2 CFR 200 compliance reviews, Recipient monitoring reports, OMB grant training data |
| **Disliked Claims** | One-size-fits-all grant solutions, Platforms without 2 CFR 200 compliance, Tools that bypass recipient risk scoring, Solutions lacking drawdown integration |
| **Budget Influence** | Grant portfolio ($10M-$1B) |
| **Linked Pains** | FED-PAIN-008, PS-PAIN-005, FED-PAIN-017 |
| **Linked KPIs** | PS-KPI-009, PS-KPI-010, FED-KPI-006, PS-KPI-031 |
| **Communication Preferences** | 2 CFR 200 compliance automation; recipient portal usability; audit trail completeness; subaward transparency |


### FED-PERS-006: Policy Analyst (Federal)

| Attribute | Detail |
|-----------|--------|
| **Name** | Policy Analyst (Federal) |
| **GS Series** | 0301/0343 |
| **Grade Range** | GS-13 to GS-15 (SES potential) |
| **Role Description** | Analyzes legislative mandates, regulatory impacts, and policy implementation. Liaises with OMB, Congress, and IG. Tracks GAO recommendations, statutory deadlines, and rulemaking timelines. |
| **Trusted Evidence** | GAO reports, Congressional Research Service analyses, OMB circulars and memos, Federal Register rulemaking, CBO scoring |
| **Disliked Claims** | Solutions that create new regulatory obligations without analysis, Vendors unfamiliar with APA rulemaking, Tools without legislative tracking, Proposals that conflict with statutory requirements |
| **Budget Influence** | Policy office budget ($1M-$20M); indirect influence on agency-wide programs |
| **Linked Pains** | FED-PAIN-015, FED-PAIN-016, PS-PAIN-011, FED-PAIN-012 |
| **Linked KPIs** | FED-KPI-018, PS-KPI-020, FED-KPI-012 |
| **Communication Preferences** | Regulatory impact assessments; legislative mandate tracking; GAO recommendation mapping; OMB A-11 alignment |

---

## Discovery Questions


### FED-DQ-001: What is your current RMF timeline from categorization to ATO, and how ...

| Attribute | Detail |
|-----------|--------|
| **Question** | What is your current RMF timeline from categorization to ATO, and how many systems are on interim ATO exceeding 12 months? |
| **Target Persona** | FED-PERS-003 |
| **Linked Pain** | FED-PAIN-001 |
| **Expected Signal** | RMF timeline >18 months or interim ATO >12 months indicates ATO bottleneck |
| **Confidence** | HIGH |
| **Category** | Security / Compliance |


### FED-DQ-002: What percentage of your IT budget is consumed by O&M versus DME/modern...

| Attribute | Detail |
|-----------|--------|
| **Question** | What percentage of your IT budget is consumed by O&M versus DME/modernization, and has that ratio changed in the last 3 years? |
| **Target Persona** | FED-PERS-002 |
| **Linked Pain** | FED-PAIN-002 |
| **Expected Signal** | O&M ratio >70% with declining DME indicates legacy trap |
| **Confidence** | HIGH |
| **Category** | Budget / Modernization |


### FED-DQ-003: How many days this fiscal year has your agency operated under a contin...

| Attribute | Detail |
|-----------|--------|
| **Question** | How many days this fiscal year has your agency operated under a continuing resolution, and what new starts remain frozen? |
| **Target Persona** | FED-PERS-001 |
| **Linked Pain** | FED-PAIN-003 |
| **Expected Signal** | CR >90 days with frozen new starts indicates planning paralysis |
| **Confidence** | HIGH |
| **Category** | Budget / Planning |


### FED-DQ-004: How many cloud service providers are in your agency ATO queue, and wha...

| Attribute | Detail |
|-----------|--------|
| **Question** | How many cloud service providers are in your agency ATO queue, and what is the average time from CSP engagement to authorization? |
| **Target Persona** | FED-PERS-003 |
| **Linked Pain** | FED-PAIN-004 |
| **Expected Signal** | Queue >20 or average >12 months indicates FedRAMP bottleneck |
| **Confidence** | HIGH |
| **Category** | Cloud / Security |


### FED-DQ-005: What is your current SPRSSP score, and do you have a C3PAO assessment ...

| Attribute | Detail |
|-----------|--------|
| **Question** | What is your current SPRSSP score, and do you have a C3PAO assessment scheduled for CMMC Level 2? |
| **Target Persona** | FED-PERS-003 |
| **Linked Pain** | FED-PAIN-005 |
| **Expected Signal** | SPRSSP <110 without scheduled C3PAO indicates compliance gap |
| **Confidence** | HIGH |
| **Category** | Defense / Cybersecurity |


### FED-DQ-006: What is your 1102 series vacancy rate, and how many procurement action...

| Attribute | Detail |
|-----------|--------|
| **Question** | What is your 1102 series vacancy rate, and how many procurement actions are currently pending beyond 200 days? |
| **Target Persona** | FED-PERS-004 |
| **Linked Pain** | FED-PAIN-006 |
| **Expected Signal** | Vacancy >15% with pending >200 days indicates workforce crisis |
| **Confidence** | HIGH |
| **Category** | Acquisition / Workforce |


### FED-DQ-007: How many ITAR license applications are currently pending, and what is ...

| Attribute | Detail |
|-----------|--------|
| **Question** | How many ITAR license applications are currently pending, and what is your average processing time from submission to DDTC response? |
| **Target Persona** | FED-PERS-003 |
| **Linked Pain** | FED-PAIN-007 |
| **Expected Signal** | Pending queue >20 or processing time >90 days indicates compliance strain |
| **Confidence** | MEDIUM |
| **Category** | Export Control / Compliance |


### FED-DQ-008: What is your agency's deobligation rate for grants, and how many physi...

| Attribute | Detail |
|-----------|--------|
| **Question** | What is your agency's deobligation rate for grants, and how many physically complete grants remain administratively open beyond 180 days? |
| **Target Persona** | FED-PERS-005 |
| **Linked Pain** | FED-PAIN-008 |
| **Expected Signal** | Deobligation >8% or open >180 days indicates closeout breakdown |
| **Confidence** | HIGH |
| **Category** | Grants / Financial |


### FED-DQ-009: How do you currently handle cross-domain transfers between NIPRNet, SI...

| Attribute | Detail |
|-----------|--------|
| **Question** | How do you currently handle cross-domain transfers between NIPRNet, SIPRNet, and JWICS, and what is the average approval time? |
| **Target Persona** | FED-PERS-003 |
| **Linked Pain** | FED-PAIN-009 |
| **Expected Signal** | Manual transfer or approval >30 days indicates cross-domain friction |
| **Confidence** | HIGH |
| **Category** | Security / Information Sharing |


### FED-DQ-010: What is the current backlog of disability compensation claims pending ...

| Attribute | Detail |
|-----------|--------|
| **Question** | What is the current backlog of disability compensation claims pending >125 days, and what automation tools are in use for claims development? |
| **Target Persona** | FED-PERS-001 |
| **Linked Pain** | FED-PAIN-010 |
| **Expected Signal** | Backlog >200K or processing time >125 days indicates capacity gap |
| **Confidence** | HIGH |
| **Category** | Benefits / Case Processing |


### FED-DQ-011: During last filing season, what was your customer service Level of Ser...

| Attribute | Detail |
|-----------|--------|
| **Question** | During last filing season, what was your customer service Level of Service, and how many paper returns required manual processing? |
| **Target Persona** | FED-PERS-002 |
| **Linked Pain** | FED-PAIN-011 |
| **Expected Signal** | LOS <70% or paper backlog >1M indicates service delivery strain |
| **Confidence** | HIGH |
| **Category** | Citizen Service / Operations |


### FED-DQ-012: How many Section 508 complaints has your agency received in the last 1...

| Attribute | Detail |
|-----------|--------|
| **Question** | How many Section 508 complaints has your agency received in the last 12 months, and do you have active remediation plans? |
| **Target Persona** | FED-PERS-003 |
| **Linked Pain** | FED-PAIN-012 |
| **Expected Signal** | Complaints >10 or active DOJ settlement indicates compliance failure |
| **Confidence** | HIGH |
| **Category** | Accessibility / Compliance |


### FED-DQ-013: What percentage of your physically complete contracts remain administr...

| Attribute | Detail |
|-----------|--------|
| **Question** | What percentage of your physically complete contracts remain administratively open, and what is the average age of your closeout backlog? |
| **Target Persona** | FED-PERS-004 |
| **Linked Pain** | FED-PAIN-013 |
| **Expected Signal** | Open rate >15% or average age >1 year indicates closeout crisis |
| **Confidence** | HIGH |
| **Category** | Contract Management |


### FED-DQ-014: What percentage of your agency's legacy circuits have transitioned to ...

| Attribute | Detail |
|-----------|--------|
| **Question** | What percentage of your agency's legacy circuits have transitioned to EIS, and what premium are you paying for legacy contract extensions? |
| **Target Persona** | FED-PERS-002 |
| **Linked Pain** | FED-PAIN-014 |
| **Expected Signal** | Transition <80% or premium >10% indicates EIS delay |
| **Confidence** | HIGH |
| **Category** | Telecommunications / Infrastructure |


### FED-DQ-015: How many open congressional mandates does your agency have, and what p...

| Attribute | Detail |
|-----------|--------|
| **Question** | How many open congressional mandates does your agency have, and what percentage were implemented by statutory deadline? |
| **Target Persona** | FED-PERS-006 |
| **Linked Pain** | FED-PAIN-015 |
| **Expected Signal** | Open >50 or compliance <80% indicates mandate overload |
| **Confidence** | MEDIUM |
| **Category** | Policy / Governance |


### FED-DQ-016: What percentage of your eligible procurement dollars went to small bus...

| Attribute | Detail |
|-----------|--------|
| **Question** | What percentage of your eligible procurement dollars went to small business primes last year, and how many bundling determinations did you make? |
| **Target Persona** | FED-PERS-004 |
| **Linked Pain** | FED-PAIN-016 |
| **Expected Signal** | Achievement <90% of 23% goal or bundling >5 indicates goal miss |
| **Confidence** | HIGH |
| **Category** | Acquisition / Socio-Economic |


### FED-DQ-017: What percentage of your agency's records holdings remain in paper form...

| Attribute | Detail |
|-----------|--------|
| **Question** | What percentage of your agency's records holdings remain in paper format, and has NARA approved your records schedule? |
| **Target Persona** | FED-PERS-002 |
| **Linked Pain** | FED-PAIN-017 |
| **Expected Signal** | Paper >20% or unapproved schedule indicates NARA noncompliance |
| **Confidence** | HIGH |
| **Category** | Records Management / Compliance |


### FED-DQ-018: How many GIDEP alerts has your program received in the last 12 months,...

| Attribute | Detail |
|-----------|--------|
| **Question** | How many GIDEP alerts has your program received in the last 12 months, and what percentage of critical electronic parts come from single-source suppliers? |
| **Target Persona** | FED-PERS-001 |
| **Linked Pain** | FED-PAIN-018 |
| **Expected Signal** | GIDEP >5 or single-source >10 indicates supply chain risk |
| **Confidence** | HIGH |
| **Category** | Supply Chain / Defense |

---

## Objection Patterns


### FED-OBJ-001: Our acquisition cycle is too long to justify a pilot or proof of conce...

| Attribute | Detail |
|-----------|--------|
| **Objection** | Our acquisition cycle is too long to justify a pilot or proof of concept. |
| **Translation** | The prospect fears procurement bureaucracy will delay value realization beyond their planning horizon. |
| **Response Strategy** | Reference GSA Schedule, OTA, or SBIR pathways that compress procurement to <60 days; propose phased delivery with off-ramp clauses; cite FPDS data on similar procurements' actual timeline. |
| **Linked Pain** | FED-PAIN-006 |
| **Linked Persona** | FED-PERS-004 |
| **Confidence** | HIGH |


### FED-OBJ-002: We already have an incumbent under a long-term contract with option ye...

| Attribute | Detail |
|-----------|--------|
| **Objection** | We already have an incumbent under a long-term contract with option years. |
| **Translation** | The prospect has contractual and political lock-in with an existing vendor. Change requires justification and risk. |
| **Response Strategy** | Map incumbent gaps to specific federal pains (ATO delays, cost overruns, FITARA score decline); position as complementary enhancement or bridge solution; cite contract option non-exercise language. |
| **Linked Pain** | FED-PAIN-002 |
| **Linked Persona** | FED-PERS-001 |
| **Confidence** | HIGH |


### FED-OBJ-003: FedRAMP authorization is a prerequisite, and you don't have it yet....

| Attribute | Detail |
|-----------|--------|
| **Objection** | FedRAMP authorization is a prerequisite, and you don't have it yet. |
| **Translation** | The agency cannot procure cloud/SaaS without FedRAMP. This is a hard gate. |
| **Response Strategy** | Propose agency-sponsored FedRAMP Fast Track (target 6-9 months); offer on-prem or hybrid deployment as interim path; reference FedRAMP-ready or In Process status; suggest sponsor engagement letter. |
| **Linked Pain** | FED-PAIN-004 |
| **Linked Persona** | FED-PERS-003 |
| **Confidence** | HIGH |


### FED-OBJ-004: Our budget is frozen under the continuing resolution — no new starts a...

| Attribute | Detail |
|-----------|--------|
| **Objection** | Our budget is frozen under the continuing resolution — no new starts allowed. |
| **Translation** | Prospect cannot obligate funds for new programs while CR is in effect. Timing issue, not rejection. |
| **Response Strategy** | Position as planning engagement funded by O&M or B&P dollars; propose CR-resolution procurement package ready to execute; offer use of working capital fund or TMF if applicable. |
| **Linked Pain** | FED-PAIN-003 |
| **Linked Persona** | FED-PERS-001 |
| **Confidence** | HIGH |


### FED-OBJ-005: We need to see past performance on federal contracts of similar size a...

| Attribute | Detail |
|-----------|--------|
| **Objection** | We need to see past performance on federal contracts of similar size and complexity. |
| **Translation** | Federal procurement evaluation criteria weight past performance heavily. New entrant disadvantage. |
| **Response Strategy** | Present subcontractor past performance, team member federal experience, or CPARS excerpts; propose small business set-aside, SBIR Phase III, or GSA Schedule where past performance requirements are lighter; offer no-cost pilot. |
| **Linked Pain** | FED-PAIN-006 |
| **Linked Persona** | FED-PERS-004 |
| **Confidence** | HIGH |


### FED-OBJ-006: Our ISSO will never approve this because it doesn't map to NIST contro...

| Attribute | Detail |
|-----------|--------|
| **Objection** | Our ISSO will never approve this because it doesn't map to NIST controls out of the box. |
| **Translation** | Security team lacks bandwidth to perform control mapping and testing for non-standard solutions. |
| **Response Strategy** | Provide pre-mapped NIST SP 800-53 control matrix; offer eMASS importable package; include POA&M templates; propose shared security responsibility model; reference ATO on comparable systems. |
| **Linked Pain** | FED-PAIN-001 |
| **Linked Persona** | FED-PERS-003 |
| **Confidence** | HIGH |


### FED-OBJ-007: We are waiting for the new administration's technology priorities befo...

| Attribute | Detail |
|-----------|--------|
| **Objection** | We are waiting for the new administration's technology priorities before making decisions. |
| **Translation** | Political uncertainty is delaying procurement. Prospect seeks alignment with likely policy direction. |
| **Response Strategy** | Map solution to bipartisan priorities (cybersecurity, modernization, AI governance, workforce); reference GAO High Risk List items that persist across administrations; offer low-risk pilot with off-ramp. |
| **Linked Pain** | FED-PAIN-015 |
| **Linked Persona** | FED-PERS-006 |
| **Confidence** | MEDIUM |


### FED-OBJ-008: Our current system is 'good enough' and replacing it would be too disr...

| Attribute | Detail |
|-----------|--------|
| **Objection** | Our current system is 'good enough' and replacing it would be too disruptive. |
| **Translation** | Status quo bias. Prospect underestimates technical debt and overestimates transition risk. |
| **Response Strategy** | Quantify risk of status quo (vendor EOL, security CVEs, knowledge concentration, OIG findings); phased migration plan with parallel operations; reference GAO reports on legacy system failures. |
| **Linked Pain** | FED-PAIN-002 |
| **Linked Persona** | FED-PERS-002 |
| **Confidence** | HIGH |


### FED-OBJ-009: We need to stay with GSA schedules and can't do a sole-source award....

| Attribute | Detail |
|-----------|--------|
| **Objection** | We need to stay with GSA schedules and can't do a sole-source award. |
| **Translation** | Prospect believes only GSA Schedule purchases are permissible. Limited understanding of other contracting vehicles. |
| **Response Strategy** | Educate on FAR 8.4 (GSA Schedules), FAR 13 (Simplified Acquisition), FAR 16.5 (IDIQ/task orders), and OTA for R&D; position as competition among schedule holders or as task order under existing BPA. |
| **Linked Pain** | FED-PAIN-006 |
| **Linked Persona** | FED-PERS-004 |
| **Confidence** | HIGH |


### FED-OBJ-010: Our IG just issued a finding on this area, so we need to be cautious a...

| Attribute | Detail |
|-----------|--------|
| **Objection** | Our IG just issued a finding on this area, so we need to be cautious about new vendors. |
| **Translation** | IG scrutiny creates risk aversion. Prospect fears new vendor will compound audit exposure. |
| **Response Strategy** | Acknowledge IG finding and position solution as remediation enabler; reference IG recommendation language that supports the approach; offer compliance documentation package; propose IG-monitored pilot if needed. |
| **Linked Pain** | PS-PAIN-011 |
| **Linked Persona** | FED-PERS-003 |
| **Confidence** | HIGH |

---

## Technology Systems


### FED-TECH-001: eMASS (Enterprise Mission Assurance Support Service)

| Attribute | Detail |
|-----------|--------|
| **Name** | eMASS (Enterprise Mission Assurance Support Service) |
| **Description** | DoD/DISA-hosted system for RMF package management, control implementation tracking, POA&M lifecycle, and ATO workflow. Integrates with STIGs, SCAP, and ACAS. |
| **Owner** | DISA / DoD CIO |
| **Applicable Segments** | DoD, Intelligence Community |
| **Linked Pains** | FED-PAIN-001, FED-PAIN-005 |
| **Linked KPIs** | FED-KPI-001, FED-KPI-013 |
| **Integration Points** | STIGs, SCAP, ACAS, CMRS, VRAMS |
| **Confidence** | HIGH |


### FED-TECH-002: FedRAMP Marketplace / ATO Repository

| Attribute | Detail |
|-----------|--------|
| **Name** | FedRAMP Marketplace / ATO Repository |
| **Description** | GSA-managed repository of cloud service providers with FedRAMP authorization status. Includes JAB P-ATO and agency ATO packages with continuous monitoring reports. |
| **Owner** | GSA / FedRAMP PMO |
| **Applicable Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-004, PS-PAIN-023 |
| **Linked KPIs** | FED-KPI-009, PS-KPI-029 |
| **Integration Points** | SAM.gov, USASpending.gov, CSP APIs |
| **Confidence** | HIGH |


### FED-TECH-003: ICAM / IdM (Identity, Credential, and Access Management)

| Attribute | Detail |
|-----------|--------|
| **Name** | ICAM / IdM (Identity, Credential, and Access Management) |
| **Description** | Federal identity framework including PIV/CAC cards, HSPD-12 compliance, and Zero Trust identity pillar implementation. Covers physical and logical access. |
| **Owner** | GSA / CISA / OMB |
| **Applicable Segments** | All Federal Agencies |
| **Linked Pains** | PS-PAIN-002, FED-PAIN-009 |
| **Linked KPIs** | PS-KPI-028, FED-KPI-008 |
| **Integration Points** | PIV systems, Active Directory, SailPoint, Okta, Azure AD |
| **Confidence** | HIGH |


### FED-TECH-004: GSA Enterprise Infrastructure Solutions (EIS)

| Attribute | Detail |
|-----------|--------|
| **Name** | GSA Enterprise Infrastructure Solutions (EIS) |
| **Description** | GSA-managed telecommunications and network services contract replacing FTS2001 and Networx. Provides voice, data, wireless, and cloud connectivity to federal agencies. |
| **Owner** | GSA / FAS |
| **Applicable Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-014, PS-PAIN-001 |
| **Linked KPIs** | FED-KPI-022, PS-KPI-030 |
| **Integration Points** | Agency NOCs, CSPs, FirstNet, JWICS |
| **Confidence** | HIGH |


### FED-TECH-005: GSA Schedules / MAS (Multiple Award Schedule)

| Attribute | Detail |
|-----------|--------|
| **Name** | GSA Schedules / MAS (Multiple Award Schedule) |
| **Description** | Pre-negotiated contracting vehicles for commercial products and services. Includes IT Schedule 70, Professional Services, and specialized vertical schedules. |
| **Owner** | GSA / FAS |
| **Applicable Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-006, PS-PAIN-007 |
| **Linked KPIs** | PS-KPI-013, FED-KPI-005 |
| **Integration Points** | SAM.gov, eBuy, GSA Advantage, FPDS |
| **Confidence** | HIGH |


### FED-TECH-006: SAM.gov (System for Award Management)

| Attribute | Detail |
|-----------|--------|
| **Name** | SAM.gov (System for Award Management) |
| **Description** | Central registry for federal awards, contract opportunities, entity registration (UEI), and exclusion checks. Replaced CCR/FedReg, ORCA, EPLS. |
| **Owner** | GSA / IAE |
| **Applicable Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-006, FED-PAIN-016 |
| **Linked KPIs** | FED-KPI-016, FED-KPI-005 |
| **Integration Points** | USASpending.gov, FPDS, Grants.gov, beta.SAM.gov |
| **Confidence** | HIGH |


### FED-TECH-007: USASpending.gov / FPDS (Federal Procurement Data System)

| Attribute | Detail |
|-----------|--------|
| **Name** | USASpending.gov / FPDS (Federal Procurement Data System) |
| **Description** | Federal spending transparency portal and contract reporting system. Tracks obligations, competition, contract type, and socio-economic data. |
| **Owner** | Treasury / OMB / GSA |
| **Applicable Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-006, FED-PAIN-016 |
| **Linked KPIs** | FED-KPI-005, FED-KPI-015, PS-KPI-014 |
| **Integration Points** | SAM.gov, FPDS, Treasury DATA Act broker |
| **Confidence** | HIGH |


### FED-TECH-008: Grants.gov / Grant Solutions

| Attribute | Detail |
|-----------|--------|
| **Name** | Grants.gov / Grant Solutions |
| **Description** | Federal grant application and management platform. Includes NOFO publication, application receipt, award notification, and post-award reporting. |
| **Owner** | HHS / NSF (Grant Solutions) |
| **Applicable Segments** | HHS, NSF, ED, DOJ, DHS |
| **Linked Pains** | FED-PAIN-008, PS-PAIN-005 |
| **Linked KPIs** | PS-KPI-009, PS-KPI-031, FED-KPI-006 |
| **Integration Points** | SAM.gov, Federal Audit Clearinghouse, Payment Management System |
| **Confidence** | HIGH |


### FED-TECH-009: CADE 2 / MEIS (IRS Modernization Systems)

| Attribute | Detail |
|-----------|--------|
| **Name** | CADE 2 / MEIS (IRS Modernization Systems) |
| **Description** | IRS Customer Account Data Engine 2 (modernizing Master File) and Modernized e-File and Integrated Systems. Core tax processing infrastructure modernization. |
| **Owner** | IRS / Treasury |
| **Applicable Segments** | Treasury/IRS |
| **Linked Pains** | FED-PAIN-011, PS-PAIN-001 |
| **Linked KPIs** | FED-KPI-020, PS-KPI-027 |
| **Integration Points** | Modernized e-File, Return Review Program, IDRS |
| **Confidence** | HIGH |


### FED-TECH-010: VBMS / VA.gov (Veterans Benefits Systems)

| Attribute | Detail |
|-----------|--------|
| **Name** | VBMS / VA.gov (Veterans Benefits Systems) |
| **Description** | Veterans Benefits Management System for disability claims processing and VA.gov digital front door. Includes claims intake, development, rating, and appeals tracking. |
| **Owner** | VA / VBA |
| **Applicable Segments** | VA |
| **Linked Pains** | FED-PAIN-010, PS-PAIN-003 |
| **Linked KPIs** | FED-KPI-019, PS-KPI-006, PS-KPI-007 |
| **Integration Points** | VA.gov, Benefits Delivery at Discharge, Board of Veterans Appeals |
| **Confidence** | HIGH |


### FED-TECH-011: NARA ERA (Electronic Records Archives)

| Attribute | Detail |
|-----------|--------|
| **Name** | NARA ERA (Electronic Records Archives) |
| **Description** | National Archives system for federal agency electronic records transfer, preservation, and public access. Includes records schedule submission and approval workflow. |
| **Owner** | NARA |
| **Applicable Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-017, PS-PAIN-014 |
| **Linked KPIs** | PS-KPI-024, FED-KPI-012 |
| **Integration Points** | Agency records management systems, FOIA processing, e-discovery platforms |
| **Confidence** | HIGH |


### FED-TECH-012: CDM (Continuous Diagnostics and Mitigation)

| Attribute | Detail |
|-----------|--------|
| **Name** | CDM (Continuous Diagnostics and Mitigation) |
| **Description** | DHS CISA program providing cybersecurity tools, dashboards, and sensors for federal agency asset management, vulnerability management, and threat detection. |
| **Owner** | CISA / DHS |
| **Applicable Segments** | All Federal Agencies |
| **Linked Pains** | PS-PAIN-002, FED-PAIN-001 |
| **Linked KPIs** | PS-KPI-003, PS-KPI-004, PS-KPI-005 |
| **Integration Points** | CISA BODs, Einstein, ACAS, Splunk, Tenable |
| **Confidence** | HIGH |


### FED-TECH-013: Cross-Domain Solutions (CDS) / MLS

| Attribute | Detail |
|-----------|--------|
| **Name** | Cross-Domain Solutions (CDS) / MLS |
| **Description** | High-assurance guards and one-way transfers enabling data flow between classified and unclassified networks. Includes NCDSMO-approved solutions. |
| **Owner** | NSA / DoD CIO / IC CIO |
| **Applicable Segments** | DoD, Intelligence Community, DHS |
| **Linked Pains** | FED-PAIN-009, FED-PAIN-007 |
| **Linked KPIs** | PS-KPI-032, FED-KPI-011 |
| **Integration Points** | JWICS, SIPRNet, NIPRNet, ICD 503 compliance |
| **Confidence** | HIGH |


### FED-TECH-014: TMF (Technology Modernization Fund)

| Attribute | Detail |
|-----------|--------|
| **Name** | TMF (Technology Modernization Fund) |
| **Description** | OMB-managed fund providing repayable capital for federal IT modernization projects. Requires board approval, agile delivery, and repayable structure. |
| **Owner** | OMB / GSA |
| **Applicable Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-002, PS-PAIN-001, PS-PAIN-023 |
| **Linked KPIs** | PS-KPI-001, PS-KPI-002, FED-KPI-003 |
| **Integration Points** | OMB budget formulation, Agency CFO, FITARA scorecard |
| **Confidence** | HIGH |


### FED-TECH-015: Cloud Smart / Agency Cloud Strategy

| Attribute | Detail |
|-----------|--------|
| **Name** | Cloud Smart / Agency Cloud Strategy |
| **Description** | Federal cloud policy framework replacing Cloud First. Emphasizes fit-for-purpose cloud decisions, data center consolidation, and hybrid/multi-cloud governance. |
| **Owner** | OMB / CISA / Agency CIOs |
| **Applicable Segments** | All Federal Agencies |
| **Linked Pains** | FED-PAIN-004, PS-PAIN-023, FED-PAIN-002 |
| **Linked KPIs** | PS-KPI-029, FED-KPI-009, FED-KPI-003 |
| **Integration Points** | FedRAMP, EIS, Data center closures, TMF |
| **Confidence** | HIGH |

---

## Regulatory Factors


### FED-REG-001: Federal Information Security Modernization Act (FISMA)

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal Information Security Modernization Act (FISMA) |
| **Authority** | 44 U.S.C. § 3551 et seq.; OMB M-17-25, M-21-31, M-22-09 |
| **Applicability** | All Federal Agencies |
| **Compliance Implications** | Annual IG FISMA audits; OMB reporting; continuous monitoring; incident reporting to CISA within 1 hour |
| **Violation Penalties** | OIG findings; congressional oversight; budget restrictions; potential criminal liability for willful concealment |
| **Linked Pains** | FED-PAIN-001, PS-PAIN-002, FED-PAIN-012 |
| **Linked KPIs** | FED-KPI-008, FED-KPI-013, PS-KPI-028 |
| **Confidence** | HIGH |


### FED-REG-002: Federal Risk and Authorization Management Program (FedRAMP)

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal Risk and Authorization Management Program (FedRAMP) |
| **Authority** | OMB M-11-32, M-15-13, M-17-26; FedRAMP Authorization Act 2022 (P.L. 117-163) |
| **Applicability** | All Federal Agencies using cloud services |
| **Compliance Implications** | Cloud SaaS/PaaS/IaaS must obtain FedRAMP authorization before agency use; JAB or agency ATO required; continuous monitoring |
| **Violation Penalties** | Cloud services cannot be procured; shadow IT risk; ATO revocation; OIG findings on noncompliant systems |
| **Linked Pains** | FED-PAIN-004, PS-PAIN-023 |
| **Linked KPIs** | FED-KPI-009, PS-KPI-029 |
| **Confidence** | HIGH |


### FED-REG-003: NIST SP 800-53 (Security and Privacy Controls)

| Attribute | Detail |
|-----------|--------|
| **Name** | NIST SP 800-53 (Security and Privacy Controls) |
| **Authority** | FISMA; OMB Circular A-130; NIST FIPS 200 |
| **Applicability** | All Federal Agencies |
| **Compliance Implications** | RMF requires implementation of baseline controls (Low/Moderate/High) with 18 control families; continuous monitoring; POA&M for gaps |
| **Violation Penalties** | ATO denial; IG findings; system shutdown orders; adverse FISMA audit opinion |
| **Linked Pains** | FED-PAIN-001, FED-PAIN-005 |
| **Linked KPIs** | FED-KPI-001, FED-KPI-013, FED-KPI-008 |
| **Confidence** | HIGH |


### FED-REG-004: Defense Federal Acquisition Regulation Supplement (DFARS)

| Attribute | Detail |
|-----------|--------|
| **Name** | Defense Federal Acquisition Regulation Supplement (DFARS) |
| **Authority** | 48 CFR Parts 201-225; DoD Class Deviation memos |
| **Applicability** | DoD, Defense Industrial Base |
| **Compliance Implications** | Contract clauses for cybersecurity (252.204-7012), supply chain (252.246-7007), data rights, and cost accounting. Flow-down to subcontractors. |
| **Violation Penalties** | Contract termination; debarment; False Claims Act liability; criminal prosecution for fraud |
| **Linked Pains** | FED-PAIN-005, FED-PAIN-007, FED-PAIN-018 |
| **Linked KPIs** | FED-KPI-004, FED-KPI-011, PS-KPI-014 |
| **Confidence** | HIGH |


### FED-REG-005: International Traffic in Arms Regulations (ITAR)

| Attribute | Detail |
|-----------|--------|
| **Name** | International Traffic in Arms Regulations (ITAR) |
| **Authority** | 22 CFR Parts 120-130; Arms Export Control Act; State Department DDTC |
| **Applicability** | DoD, NASA, DOE/NNSA, Intelligence Community |
| **Compliance Implications** | Registration with DDTC; licensing for defense articles/technical data; exclusion of foreign persons from access; commingling restrictions |
| **Violation Penalties** | Criminal penalties up to $1M per violation; debarment from export privileges; contract termination; individual liability |
| **Linked Pains** | FED-PAIN-007, FED-PAIN-018 |
| **Linked KPIs** | FED-KPI-011, PS-KPI-021 |
| **Confidence** | HIGH |


### FED-REG-006: Federal Acquisition Regulation (FAR)

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal Acquisition Regulation (FAR) |
| **Authority** | 48 CFR Chapter 1; Competition in Contracting Act; Service Contract Labor Standards |
| **Applicability** | All Federal Agencies |
| **Compliance Implications** | Full and open competition; socio-economic goals; cost accounting standards; contract clauses for IP, data rights, and termination |
| **Violation Penalties** | GAO bid protest sustain; contract rescission; debarment; False Claims Act liability; OIG findings |
| **Linked Pains** | FED-PAIN-006, FED-PAIN-013, FED-PAIN-016, PS-PAIN-007 |
| **Linked KPIs** | PS-KPI-013, PS-KPI-014, FED-KPI-015, FED-KPI-005 |
| **Confidence** | HIGH |


### FED-REG-007: Section 508 of Rehabilitation Act (Accessibility)

| Attribute | Detail |
|-----------|--------|
| **Name** | Section 508 of Rehabilitation Act (Accessibility) |
| **Authority** | 29 U.S.C. § 794d; 36 CFR 1194; WCAG 2.1 AA |
| **Applicability** | All Federal Agencies |
| **Compliance Implications** | All EIT procured, developed, or used by federal agencies must be accessible; VPAT required; complaint-driven enforcement |
| **Violation Penalties** | DOJ settlement; administrative complaint; procurement suspension; OIG findings; civil litigation |
| **Linked Pains** | FED-PAIN-012 |
| **Linked KPIs** | FED-KPI-012, PS-KPI-021 |
| **Confidence** | HIGH |


### FED-REG-008: Cybersecurity Maturity Model Certification (CMMC)

| Attribute | Detail |
|-----------|--------|
| **Name** | Cybersecurity Maturity Model Certification (CMMC) |
| **Authority** | 32 CFR Part 170; DFARS 252.204-7021; NIST SP 800-171 Rev 2 |
| **Applicability** | DoD contractors and subcontractors |
| **Compliance Implications** | Self-assessment (Level 1) or C3PAO assessment (Level 2/3) required for contract eligibility; SPRSSP scoring; POA&M for gaps |
| **Violation Penalties** | Loss of contract eligibility; stop-work orders; suspension; debarment |
| **Linked Pains** | FED-PAIN-005 |
| **Linked KPIs** | FED-KPI-004, FED-KPI-011 |
| **Confidence** | HIGH |


### FED-REG-009: 2 CFR 200 (Uniform Guidance for Grants)

| Attribute | Detail |
|-----------|--------|
| **Name** | 2 CFR 200 (Uniform Guidance for Grants) |
| **Authority** | 2 CFR Part 200; OMB Super Circular |
| **Applicability** | All Federal grant-making agencies and recipients |
| **Compliance Implications** | Cost principles; audit requirements; procurement standards; property management; closeout timelines; data retention |
| **Violation Penalties** | Grant suspension; termination; recovery of funds; single audit findings; debarment from future awards |
| **Linked Pains** | FED-PAIN-008, PS-PAIN-005 |
| **Linked KPIs** | PS-KPI-009, PS-KPI-010, FED-KPI-006 |
| **Confidence** | HIGH |


### FED-REG-010: Federal Information Technology Acquisition Reform Act (FITARA)

| Attribute | Detail |
|-----------|--------|
| **Name** | Federal Information Technology Acquisition Reform Act (FITARA) |
| **Authority** | 40 U.S.C. § 11301 et seq.; OMB M-15-14 |
| **Applicability** | All Federal Civilian Agencies |
| **Compliance Implications** | CIO authority over IT budget; quarterly scorecard reporting; data center consolidation; working capital fund requirements; software licensing |
| **Violation Penalties** | OMB scorecard downgrade; congressional hearing; budget hold; FITARA waiver required for exceptions |
| **Linked Pains** | FED-PAIN-002, FED-PAIN-003 |
| **Linked KPIs** | FED-KPI-003, PS-KPI-001 |
| **Confidence** | HIGH |


### FED-REG-011: National Archives Records Management (M-19-21 / M-23-07)

| Attribute | Detail |
|-----------|--------|
| **Name** | National Archives Records Management (M-19-21 / M-23-07) |
| **Authority** | 44 U.S.C. Chapter 21; NARA M-19-21; NARA M-23-07; OMB M-23-07 |
| **Applicability** | All Federal Agencies |
| **Compliance Implications** | Transition to fully electronic records management; NARA-compliant email archiving; records scheduling; transfer to NARA |
| **Violation Penalties** | NARA noncompliance notice; OIG finding; litigation hold failure; e-discovery sanctions |
| **Linked Pains** | FED-PAIN-017 |
| **Linked KPIs** | PS-KPI-024, FED-KPI-012 |
| **Confidence** | HIGH |


### FED-REG-012: Executive Order 14110 (AI Governance)

| Attribute | Detail |
|-----------|--------|
| **Name** | Executive Order 14110 (AI Governance) |
| **Authority** | EO 14110; OMB M-24-10; NIST AI RMF |
| **Applicability** | All Federal Agencies using AI |
| **Compliance Implications** | AI inventory; risk management; bias testing; procurement guidelines; safety testing for dual-use foundation models |
| **Violation Penalties** | OMB enforcement; OIG findings; procurement suspension; reputational risk; litigation |
| **Linked Pains** | PS-PAIN-011, FED-PAIN-012 |
| **Linked KPIs** | PS-KPI-021, FED-KPI-012 |
| **Confidence** | MEDIUM |

---

## Competitor Factors


### FED-COMP-001: Large System Integrator Incumbency

| Attribute | Detail |
|-----------|--------|
| **Name** | Large System Integrator Incumbency |
| **Description** | Major SIs (Lockheed, Northrop, Booz Allen, Leidos, SAIC) hold multi-year IDIQ and task order relationships. Incumbent knowledge and past performance create switching costs. |
| **Impact** | New entrants face 18-24 month capture cycles; incumbents have 60%+ win rate on recompetes |
| **Counter Strategy** | Position as innovation partner for specific technology gaps; team with incumbent as subcontractor; target set-aside competitions |


### FED-COMP-002: GSA Schedule Holder Concentration

| Attribute | Detail |
|-----------|--------|
| **Name** | GSA Schedule Holder Concentration |
| **Description** | Top 100 GSA Schedule holders capture 40%+ of schedule spend. Small and disadvantaged vendors compete on price within schedule pools. |
| **Impact** | Price competition intense on commodity IT; differentiation through technical innovation difficult |
| **Counter Strategy** | Seek specialized vertical schedules; leverage OTA or SBIR for pre-competitive engagement; build past performance through subcontracts |


### FED-COMP-003: FedRAMP-Authorized CSP Oligopoly

| Attribute | Detail |
|-----------|--------|
| **Name** | FedRAMP-Authorized CSP Oligopoly |
| **Description** | AWS, Azure, and Google hold majority of FedRAMP authorizations. Smaller CSPs struggle with authorization cost and timeline. |
| **Impact** | Agencies default to Big 3 cloud; niche CSPs face adoption barrier regardless of technical merit |
| **Counter Strategy** | Position as SaaS layer on authorized IaaS; pursue FedRAMP Fast Track with agency sponsor; target hybrid/multi-cloud management |


### FED-COMP-004: Protest-Driven Procurement Delay

| Attribute | Detail |
|-----------|--------|
| **Name** | Protest-Driven Procurement Delay |
| **Description** | GAO and Court of Federal Claims protests delay awards by 90-180 days. Incumbents file protective protests to extend performance period. |
| **Impact** | Award timeline uncertainty; proposal investment risk; incumbent advantage from protest experience |
| **Counter Strategy** | Pre-award engagement and debrief preparation; protest-resistant requirements development; alternative dispute resolution clauses |

---

## Worked Examples


### FED-EX-001: DoD Contractor CMMC Compliance Acceleration

| Attribute | Detail |
|-----------|--------|
| **Name** | DoD Contractor CMMC Compliance Acceleration |
| **Scenario** | A mid-tier defense contractor (500 employees, $150M revenue) holds 12 active DoD contracts. SPRSSP assessment shows 73/110 NIST SP 800-171 controls implemented. C3PAO assessment not scheduled. Two prime contracts up for recompete in 18 months. |
| **Formula Applied** | FED-VF-004: CMMC Compliance Cost Avoidance |

**Inputs:**
- `currentSPRSSP`: 73
- `targetSPRSSP`: 110
- `affectedContracts`: 12
- `avgContractValue`: $8M
- `baselineComplianceCostPerContract`: $120K
- `targetComplianceCostPerContract`: $75K
- `debarmentRiskValue`: $5M

**Calculation Steps:**
- Step 1: Compliance cost reduction per contract: $120K - $75K = $45K
- Step 2: Total compliance savings: $45K × 12 contracts = $540K
- Step 3: Avoided debarment risk value = $5M (estimated value of contracts at risk)
- Step 4: Total 3-year value: $540K × 3 + $5M = $6.62M
- Step 5: Implementation cost estimate: $800K (consulting, tools, training)
- Step 6: Net 3-year NPV: $6.62M - $800K = $5.82M

**Result:** $5.82M net value over 3 years; 14% of contract portfolio debarment risk mitigated; C3PAO assessment scheduled within 6 months

**Confidence:** HIGH

**Sources:** SPRSSP scoring data, Contract values from FPDS, C3PAO pricing estimates


### FED-EX-002: Civilian Agency FedRAMP Cloud Migration

| Attribute | Detail |
|-----------|--------|
| **Name** | Civilian Agency FedRAMP Cloud Migration |
| **Scenario** | A civilian cabinet agency (5,000 FTE, $300M IT budget) has 25 SaaS applications awaiting agency ATO. Average queue time is 16 months. Shadow IT cloud usage detected via CASB at $2M annual spend. Legacy data center costs $8M/year. |
| **Formula Applied** | FED-VF-002: FedRAMP Authorization Portfolio Value + FED-VF-012: EIS Transition Cost Avoidance (adapted) |

**Inputs:**
- `pendingSaaS`: 25
- `avgATOTimeMonths`: 16
- `targetATOTimeMonths`: 6
- `shadowITAnnualSpend`: $2M
- `dataCenterAnnualCost`: $8M
- `cloudMigrationSavingsRate`: 0.25
- `agencyATOCostPerSaaS`: $75K

**Calculation Steps:**
- Step 1: ATO acceleration value: (16-6) months × 25 SaaS × $6.25K/month opportunity cost = $1.56M
- Step 2: Avoided agency ATO effort: 25 × $75K = $1.88M (shift to FedRAMP marketplace reuse)
- Step 3: Shadow IT risk avoidance: $2M × 0.5 (risk factor) = $1M
- Step 4: Data center/cloud savings: $8M × 25% = $2M annually
- Step 5: Total annual value: $1.56M + $1.88M + $1M + $2M = $6.44M
- Step 6: Implementation cost (FedRAMP sponsor, migration): $1.5M
- Step 7: Net annual value: $6.44M - $1.5M = $4.94M

**Result:** $4.94M net annual value; 25 SaaS ATO timeline reduced from 16 to 6 months; shadow IT normalized; $2M data center cost avoidance

**Confidence:** MEDIUM

**Sources:** FedRAMP PMO timeline data, CASB shadow IT report, OMB data center cost benchmarks


### FED-EX-003: VA Claims Processing Automation ROI

| Attribute | Detail |
|-----------|--------|
| **Name** | VA Claims Processing Automation ROI |
| **Scenario** | VBA regional office processes 50,000 disability claims annually. Current backlog is 8,000 claims >125 days. Average processing time is 142 days. Error rate on original claims is 12%. Staffing is 120 FTE with 15% vacancy. Overtime costs $1.2M annually. |
| **Formula Applied** | FED-VF-008: VA Claims Processing Backlog Elimination |

**Inputs:**
- `annualClaims`: 50000
- `backlogOver125`: 8000
- `avgProcessingDays`: 142
- `targetProcessingDays`: 90
- `errorRate`: 0.12
- `targetErrorRate`: 0.05
- `fteCount`: 120
- `vacancyRate`: 0.15
- `overtimeAnnual`: $1.2M
- `costPerClaim`: $320
- `avgClaimValue`: $2500

**Calculation Steps:**
- Step 1: Backlog elimination value: (142-90) days × 50K claims × $320/claim × (52/365) efficiency factor = $2.37M
- Step 2: Overtime avoidance: $1.2M × 0.6 = $720K
- Step 3: Error rate reduction value: (12%-5%) × 50K × $250 avg rework cost = $875K
- Step 4: Veteran satisfaction/retention value (proxy): $500K (reduced congressional inquiry cost, fewer appeals)
- Step 5: Vacancy fill productivity: 18 FTE filled × $80K loaded cost × 15% productivity gain = $216K
- Step 6: Total annual value: $2.37M + $720K + $875K + $500K + $216K = $4.68M
- Step 7: Implementation cost (RPA, case mgmt, training): $1.8M
- Step 8: Net annual value: $4.68M - $1.8M = $2.88M

**Result:** $2.88M net annual value; processing time reduced from 142 to 90 days; error rate from 12% to 5%; overtime reduced 60%; vacancy impact mitigated

**Confidence:** HIGH

**Sources:** VBA performance dashboard, VA OIG cost reports, RPA vendor benchmarks

---

## Governance

| Attribute | Detail |
|-----------|--------|
| **Source Coverage** | Mixed |
| **Confidence** | High |
| **Last Updated** | 2026-04-25 |
| **Approved for Customer-Facing Output** | No |
| **Review Owner** | Federal Subpack Architect — Vertical Intelligence Swarm |
| **Agent Swarm ID** | kimi-k2.6-elevated-swarm-federal |
| **Parent Master Swarm ID** | kimi-k2.6-elevated-swarm |

---

*End of Federal Government Subpack (S5.1)*
