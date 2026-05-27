# Contract Manufacturing Subpack ValuePack

**ID:** `contract-manufacturing-v1` | **Version:** 1.0.0 | **Domain:** Industry | **Pack Type:** Subpack | **Parent:** `manufacturing-master-v1`

## Overview

The Contract Manufacturing Subpack provides vertical-specialized intelligence for CMOs, EMS, CDMOs, private label, co-packing, toll manufacturing, ODMs, and OEMs. It extends the Manufacturing Master ValuePack with segment-specific pains, KPIs, benchmarks, personas, signal rules, formulas, and buying triggers tailored to the unique dynamics of third-party production: customer-mandated compliance, multi-site consolidation, customer audit readiness, margin compression, technology transfer, and multi-tenant operational models.

---

## Inheritance Manifest

### Inherited from Master (Read-Only Reference)
- **Value Driver Framework** — 10 base drivers (downtime, yield, scrap, throughput, labor, working capital, cost, revenue, risk, warranty)
- **Base Persona Archetypes** — 17 personas (COO, CFO, CIO, Plant Manager, Quality, Maintenance, Planning, Supply Chain, EHS, HR, Engineering, Customer Success, CISO, Sustainability, Procurement, Logistics, OpEx)
- **Evidence Source Types** — 12 public/mixed source categories
- **Formula Templates** — 25 base formulas
- **Signal Source Taxonomy** — 30 signal rules
- **Benchmark Methodology** — Range-based with source attribution
- **Governance Framework** — Confidence scoring, approval gates, review cycles

### Created by Subpack (Vertical-Specialized)
- **Vertical Pains** — 18 pains (pain-cm-001 through pain-cm-018)
- **Vertical KPIs** — 22 KPIs (kpi-cm-001 through kpi-cm-022)
- **Vertical Signal Rules** — 18 rules (sig-cm-001 through sig-cm-018)
- **Vertical Personas** — 6 personas (pers-cm-001 through pers-cm-006)
- **Vertical Formulas** — 13 formulas (vf-cm-001 through vf-cm-013)
- **Vertical Benchmarks** — 18 benchmarks (bench-cm-001 through bench-cm-018)
- **Vertical Regulatory Factors** — 10 factors (reg-cm-001 through reg-cm-010)
- **Vertical Technology Systems** — 13 systems (tech-cm-001 through tech-cm-013)
- **Vertical Discovery Questions** — 18 questions (dq-cm-001 through dq-cm-018)
- **Vertical Objection Patterns** — 9 patterns (obj-cm-001 through obj-cm-009)
- **Vertical Worked Examples** — 3 examples (we-cm-001 through we-cm-003)
- **Vertical Buying Triggers** — 14 triggers (bt-cm-001 through bt-cm-014)
- **Vertical Value Drivers** — 5 extensions (vdrv-cm-001 through vdrv-cm-005)
- **Vertical Evidence Sources** — 7 sources (ev-cm-001 through ev-cm-007)
- **Competitor Factors** — 5 factors (comp-cm-001 through comp-cm-005)

### Overridden Components
| Component | Override Reason |
|---|---|
| kpi-capacity-util benchmark range | Contract manufacturers operate with higher volatility; baseline range widened from 50-95% to 45-90% |
| pain-022 Contract Manufacturing Margin Compression | Expanded to include EMS-specific operating margin dynamics, toll manufacturing material pass-through complexity, and CDMO development-phase margin challenges |
| Value Driver vdrv-revenue-uplift | Extended mechanism: includes customer contract renewal value, toll fee escalation clauses, and new customer qualification win rate |

---

## 1. Vertical Business Pains (18)

| ID | Pain | Prevalence | Confidence | Top Segments |
|---|---|---|---|---|
| pain-cm-001 | Customer Audit Finding Closure Delays | HIGH | HIGH | CMO, EMS, CDMO, Private Label |
| pain-cm-002 | Multi-Site ERP Consolidation for Toll Operations | HIGH | HIGH | Toll, CMO, CDMO |
| pain-cm-003 | Technology Transfer Delays and Knowledge Loss | HIGH | HIGH | CDMO, CMO, EMS, ODM |
| pain-cm-004 | Customer-Specific Quality Agreement Management | HIGH | HIGH | CMO, EMS, CDMO, Private Label |
| pain-cm-005 | Customer-Owned Inventory and Consignment Tracking Gaps | HIGH | HIGH | EMS, CMO, Toll, Co-Pack |
| pain-cm-006 | Quoting and Costing Accuracy Deficits | HIGH | HIGH | CMO, EMS, CDMO, ODM, Toll |
| pain-cm-007 | Customer Concentration and Contract Renewal Risk | HIGH | HIGH | EMS, CMO, Private Label, Toll |
| pain-cm-008 | Multi-Site Standardization and Best Practice Diffusion | MEDIUM | HIGH | CMO, EMS, CDMO, Private Label |
| pain-cm-009 | Regulatory Inspection Readiness Gaps | HIGH | HIGH | CMO, CDMO, Private Label |
| pain-cm-010 | Batch Record and Documentation Cycle Time | HIGH | HIGH | CMO, CDMO, Private Label |
| pain-cm-011 | Customer Portal and Data Exchange Friction | MEDIUM | HIGH | EMS, CMO, CDMO, Co-Pack |
| pain-cm-012 | Co-Packing and Assembly Line Changeover Complexity | MEDIUM | HIGH | Co-Pack, Private Label, EMS |
| pain-cm-013 | Toll Manufacturing Yield Variance and Reconciliation | MEDIUM | HIGH | Toll, CMO, CDMO |
| pain-cm-014 | Customer Scorecard and QBR Preparation Burden | MEDIUM | HIGH | EMS, CMO, CDMO, Private Label |
| pain-cm-015 | Excess and Obsolete Customer-Owned Inventory Liability | MEDIUM | MEDIUM | EMS, CMO, Toll, ODM |
| pain-cm-016 | Private Label NPI and Artwork Approval Delays | MEDIUM | HIGH | Private Label, Co-Pack, CMO |
| pain-cm-017 | On-Time-In-Full (OTIF) Performance Gaps | HIGH | HIGH | EMS, CMO, Co-Pack, Private Label |
| pain-cm-018 | Customer-Specific Regulatory and GDP Compliance | HIGH | HIGH | CDMO, CMO, Private Label |

**Full Pain Details:** See `value-pack.json` for complete metadata including symptoms, affected personas, linked KPIs, and sources.

---

## 2. Vertical KPI Definitions (22)

| ID | KPI | Formula | Unit | Typical Range | Benchmark |
|---|---|---|---|---|---|
| kpi-cm-001 | Customer Audit Score | (100 - weighted findings) / 100 x 100 | % | 60-95% | >90% |
| kpi-cm-002 | Quote Win Rate | Won / Total x 100 | % | 15-45% | 30-50% |
| kpi-cm-003 | Customer Concentration Index | Sum of (Rev%)^2 | Herfindahl | 0.15-0.80 | <0.25 |
| kpi-cm-004 | Technology Transfer Cycle Time | Days to PPQ completion | days | 90-270 | 90-150 |
| kpi-cm-005 | Contract Amendment Rate | Amendments / Active x 100 | % | 10-60% | <20% |
| kpi-cm-006 | Multi-Site OEE Variance | Max - Min OEE | % points | 10-35 | <15 |
| kpi-cm-007 | Customer NCR Rate | NCR / Shipments x 1M | PPM | 100-5000 | <500 |
| kpi-cm-008 | COGS per Customer SKU | Direct Cost / Active SKUs | $/SKU | Varies | Top quartile |
| kpi-cm-009 | Customer Portal Data Latency | Event to portal update | minutes | 60-1440 | <15 |
| kpi-cm-010 | Toll Material Yield Variance | (Theoretical - Actual) x Value | % + $/batch | 0.5-5% | <1% |
| kpi-cm-011 | Customer Escalation Rate | Escalations / Interactions x 100 | % | 1-10% | <2% |
| kpi-cm-012 | Site-to-Site Standardization Score | Weighted alignment index | 0-100 | 40-80 | >85 |
| kpi-cm-013 | Customer QBR Prep Hours | Hours/customer/quarter | hours/qtr | 40-200 | <30 |
| kpi-cm-014 | Batch Record Review Cycle Time | Batch complete to QA release | days | 3-21 | <5 |
| kpi-cm-015 | Co-Packing Line Efficiency | Actual / Scheduled x 100 | % | 50-85% | >80% |
| kpi-cm-016 | Private Label NPI Cycle Time | Brief to first batch | weeks | 8-24 | <12 |
| kpi-cm-017 | Customer Scorecard Compliance | Meeting Target / Total x 100 | % | 70-95% | >95% |
| kpi-cm-018 | Transfer Pricing Dispute Rate | Disputed / Total x 100 | % | 2-15% | <3% |
| kpi-cm-019 | Customer-Owned E&O | E&O / Total Consignment x 100 | % | 1-8% | <1% |
| kpi-cm-020 | Regulatory Inspection Readiness Score | Weighted composite | 0-100 | 50-85 | >90 |
| kpi-cm-021 | OTIF to Customer | OTIF Orders / Total x 100 | % | 75-98% | >98% |
| kpi-cm-022 | Capacity Commitment Accuracy | Actual within Commit / Total x 100 | % | 70-95% | >95% |

---

## 3. Vertical Signal Rules (18)

| ID | Signal | Confidence | Linked Pains |
|---|---|---|---|
| sig-cm-001 | Customer Audit Finding Surge | 0.85 | Audit delays, quality agreements, inspection readiness |
| sig-cm-002 | Customer Portal Integration Job Postings | 0.78 | Portal friction, QBR burden |
| sig-cm-003 | Technology Transfer Staff Expansion | 0.82 | Tech transfer delays, NPI delays |
| sig-cm-004 | Quote Win Rate Decline | 0.80 | Quoting accuracy, customer concentration |
| sig-cm-005 | Customer Concentration Risk Disclosure | 0.88 | Customer concentration, margin compression |
| sig-cm-006 | Multi-Site Acquisition or Expansion | 0.84 | Multi-site ERP, standardization |
| sig-cm-007 | Regulatory Inspection Observation Increase | 0.90 | Inspection readiness, batch records |
| sig-cm-008 | Customer OTIF Penalty Increase | 0.83 | OTIF gaps, schedule disruption |
| sig-cm-009 | EBR Implementation Signal | 0.79 | Batch records, inspection readiness |
| sig-cm-010 | Co-Packing Line Investment | 0.76 | Changeover complexity, NPI delays |
| sig-cm-011 | Customer-Owned Inventory Write-Off | 0.81 | Inventory tracking, E&O liability |
| sig-cm-012 | Toll Manufacturing Margin Compression | 0.77 | Yield variance, quoting accuracy |
| sig-cm-013 | Serialization or Track-and-Trace Mandate | 0.87 | GDP compliance, data exchange |
| sig-cm-014 | QBR Preparation Job Surge | 0.74 | QBR burden, portal friction |
| sig-cm-015 | Capacity Commitment Miss Pattern | 0.80 | OTIF gaps, planning inefficiency |
| sig-cm-016 | Cold Chain or GDP Non-Compliance | 0.89 | GDP compliance, inspection readiness |
| sig-cm-017 | Customer Contract Renewal at Risk | 0.86 | Customer concentration, OTIF gaps |
| sig-cm-018 | Private Label NPI Pipeline Surge | 0.78 | NPI delays, tech transfer |

---

## 4. Vertical Personas (6 NEW)

| ID | Persona | Role | Seniority | Influence |
|---|---|---|---|---|
| pers-cm-001 | Customer Quality Auditor | Customer-appointed QA auditor | Manager | Technical |
| pers-cm-002 | Contract/Commercial Manager | Contract negotiator and manager | Director/Manager | Economic |
| pers-cm-003 | Site Director / GM | Site P&L owner | VP/Director | User |
| pers-cm-004 | Technology Transfer Manager | Transfer execution lead | Manager/Director | Technical |
| pers-cm-005 | Customer Program Manager | Customer relationship owner | Manager/Director | User |
| pers-cm-006 | Costing Analyst / Quoting Manager | Pricing and cost estimation | Manager/Analyst | Economic |

**Full Persona Details:** See `value-pack.json` for goals, pressures, trusted evidence, and disliked claims.

---

## 5. Vertical Formulas (13)

| ID | Formula | Output | Segments |
|---|---|---|---|
| vf-cm-001 | Customer Audit Finding Remediation Value | $/year | CMO, EMS, CDMO, Private Label |
| vf-cm-002 | Multi-Site ERP Consolidation ROI | $/year | Toll, CMO, CDMO |
| vf-cm-003 | Technology Transfer Acceleration Value | $/year | CDMO, CMO, EMS, ODM |
| vf-cm-004 | Quality Agreement Management Efficiency | $/year | CMO, EMS, CDMO, Private Label |
| vf-cm-005 | Customer-Owned Inventory Reconciliation Value | $/year | EMS, CMO, Toll, Co-Pack |
| vf-cm-006 | Quoting Accuracy Improvement Value | $/year | CMO, EMS, CDMO, ODM, Toll |
| vf-cm-007 | Customer Concentration Risk Mitigation Value | $/year | EMS, CMO, Private Label, Toll |
| vf-cm-008 | Multi-Site Standardization Value | $/year | CMO, EMS, CDMO, Private Label |
| vf-cm-009 | Batch Record Digitization Value | $/year | CMO, CDMO, Private Label |
| vf-cm-010 | OTIF Improvement and Chargeback Avoidance | $/year | EMS, CMO, Co-Pack, Private Label |
| vf-cm-011 | Co-Packing Changeover Efficiency Value | $/year | Co-Pack, Private Label, EMS |
| vf-cm-012 | Regulatory Inspection Readiness Value | $/year | CMO, CDMO, Private Label |
| vf-cm-013 | Customer Portal and Data Exchange Value | $/year | EMS, CMO, CDMO, Co-Pack |

---

## 6. Vertical Benchmarks (18)

| Benchmark | Value | Range | Source | Confidence |
|---|---|---|---|---|
| Customer Audit Score - World Class | 95% | 92-98% | GxP Audit Benchmark | HIGH |
| Customer Audit Score - Average | 78% | 65-85% | Customer Quality Audit Consortium | HIGH |
| Quote Win Rate - EMS | 28% | 20-40% | Circana EMS Report | HIGH |
| Quote Win Rate - CDMO | 35% | 25-50% | IQVIA CDMO Benchmark | HIGH |
| Tech Transfer Cycle - Pharma | 120 days | 90-180 | ISPE GPG | HIGH |
| Tech Transfer Cycle - EMS | 60 days | 30-90 | Circana EMS Ops | MEDIUM |
| Customer NCR Rate - World Class | 200 PPM | 100-300 | ASQ | HIGH |
| Customer NCR Rate - Average | 1500 PPM | 500-3000 | Customer Audit Consortium | MEDIUM |
| Multi-Site OEE Variance - Best | 10 pts | 5-15 | Gartner | HIGH |
| Batch Record Review - EBR | 2 days | 1-3 | PDA Paperless | HIGH |
| Batch Record Review - Paper | 10 days | 5-21 | FDA Quality Metrics | HIGH |
| OTIF Contract Mfg - World Class | 99% | 98-99.5% | Gartner | HIGH |
| OTIF Contract Mfg - Average | 88% | 80-95% | CSCMP | HIGH |
| Customer Concentration - Healthy | 0.20 | 0.15-0.25 | McKinsey | HIGH |
| Customer Concentration - At Risk | 0.55 | 0.40-0.80 | Gartner | HIGH |
| Co-Packing Line Efficiency | 75% | 65-85% | PMMI | MEDIUM |
| Regulatory Readiness Score | 90 | 85-95 | PDA | MEDIUM |
| Toll Material Yield Variance | 1% | 0.5-2% | Toll Mfg Association | MEDIUM |

---

## 7. Vertical Regulatory Factors (10)

| ID | Regulation | Applicability | Penalty |
|---|---|---|---|
| reg-cm-001 | FDA cGMP 21 CFR 210/211 | Pharma CMOs/CDMOs | $100M+; consent decree; debarment |
| reg-cm-002 | ICH Q7 API Manufacturing | API CMOs | Import alert; contract cancellation |
| reg-cm-003 | EU GDP Guidelines | EU distribution | WDA loss; market exclusion |
| reg-cm-004 | FDA DSCSA Serialization | US drug packaging | Contract termination; enforcement |
| reg-cm-005 | Customer-Specific Quality Agreements | All contract mfg | Contract penalties; suspension |
| reg-cm-006 | EU MDR | EU medical devices | CE loss; market exclusion |
| reg-cm-007 | FSMA Preventive Controls | Food co-packers | Shutdown; recall; $1K-$500K |
| reg-cm-008 | Conflict Minerals Dodd-Frank 1502 | EMS/electronics | Customer exclusion; SEC action |
| reg-cm-009 | EU CBAM | Exporters to EU | Carbon tariff; customer loss |
| reg-cm-010 | Customer ESG / Scope 3 | All contract mfg | Scorecard failure; non-renewal |

---

## 8. Vertical Technology Systems (13)

| ID | System | Category | Key Vendors |
|---|---|---|---|
| tech-cm-001 | Multi-Tenant MES | Production | Siemens Opcenter, Dassault Apriso, Rockwell |
| tech-cm-002 | Customer Portal Platform | Customer Interface | Salesforce, Power Apps, SAP Fiori |
| tech-cm-003 | eQMS with Multi-Customer | Quality | MasterControl, Veeva, IQVIA SmartSolve |
| tech-cm-004 | SRM / Supplier Collaboration | Supply Chain | SAP Ariba, Coupa, Ivalua |
| tech-cm-005 | Electronic Batch Records | Production Documentation | Werum PAS-X, Siemens BRAUMAT, BIOVIA |
| tech-cm-006 | Serialization / Track-and-Trace | Regulatory | TraceLink, Optel, Systech |
| tech-cm-007 | Costing and Quoting Engine | Commercial | SAP PLC, aPriori, ShouldCost |
| tech-cm-008 | Cold Chain Monitoring | Distribution | Emerson, Berlinger, Sensitech |
| tech-cm-009 | Contract Lifecycle Management | Commercial | Icertis, Agiloft, DocuSign CLM |
| tech-cm-010 | Multi-Site ERP Consolidation | Business Mgmt | SAP S/4HANA, Oracle Fusion, D365 |
| tech-cm-011 | Artwork and Label Management | Regulatory | Esko, Loftware, Kallik |
| tech-cm-012 | Customer Scorecard Automation | Customer Interface | Tableau, Power BI, SAP Analytics |
| tech-cm-013 | Tech Transfer Knowledge Mgmt | Engineering | BIOVIA, Teamcenter, SAP PLM |

---

## 9. Discovery Questions (18)

1. **Customer Audit Performance** — What is your average customer audit score, and what percentage of findings are repeat findings? *(Quality, Customer Auditor, Site Director)*
2. **Multi-Site ERP Landscape** — How many ERP instances do you operate across sites, and how do you consolidate reporting? *(CIO, CFO, Site Director)*
3. **Technology Transfer Duration** — What is your average tech transfer cycle time, and where are the bottlenecks? *(Transfer Manager, COO, Engineering)*
4. **Quality Agreement Management** — How many active customer quality agreements do you manage? *(Quality, Contract Manager, COO)*
5. **Customer-Owned Inventory** — How do you track customer-owned inventory, and what is your dispute rate? *(CFO, Supply Chain, Costing Analyst)*
6. **Quoting Accuracy** — What is your quote win rate, and how often do actuals exceed quotes by >10%? *(Costing, CFO, COO)*
7. **Customer Concentration** — What percentage of revenue comes from your top three customers? *(CFO, COO, Program Manager)*
8. **Multi-Site Standardization** — What is the OEE variance between your best and worst sites? *(COO, Site Director, Quality)*
9. **Regulatory Inspection History** — How many inspections in 24 months, and average observations? *(Quality, Auditor, Site Director)*
10. **Batch Record Review** — What is your average batch record review cycle time and rework rate? *(Quality, CIO, Site Director)*
11. **Customer Portal Landscape** — How many customer portals do you support, and what is data latency? *(CIO, Program Manager, Auditor)*
12. **Co-Packing Changeover** — How many packaging configurations, and what % of shift is changeover? *(Plant Manager, Site Director, COO)*
13. **Toll Yield Reconciliation** — What is your yield variance versus theoretical for toll operations? *(Costing, CFO, Site Director)*
14. **QBR Preparation Burden** — How many labor hours per quarter on customer QBRs? *(Program Manager, COO, CIO)*
15. **Customer Escalation Patterns** — How many monthly escalations, and top three root causes? *(Program Manager, COO, Quality)*
16. **Serialization Readiness** — What is your DSCSA/EU FMD serialization coverage? *(Quality, CIO, Auditor)*
17. **Capacity Commitment Accuracy** — How often do you miss capacity commitments? *(Planning, COO, Program Manager)*
18. **Cold Chain Compliance** — How many temperature excursions in 12 months? *(Quality, Auditor, Site Director)*

---

## 10. Objection Patterns (9)

| Objection | Response Strategy |
|---|---|
| Customer mandates our current system | Position as augmentation; demonstrate integration; cite customer data latency gaps |
| Our customers won't pay for upgrades | Quantify cost of inaction; demonstrate self-funding; offer gain-sharing |
| Each customer is too unique | Standardize underlying processes with configurable overlays; show multi-tenant examples |
| We need customer approval for any change | Map to customer benefit; provide pre-packaged change docs; pilot on non-critical product |
| Toll operations have zero margin | Focus on reconciliation accuracy and dispute avoidance; propose outcome-based pricing |
| Our data is too fragmented | Propose customer-agnostic data lake with semantic layers; offer data readiness assessment |
| We're already compliant | Reframe to competitive advantage; quantify cost of passing audits even when passing |
| Small site, can't justify enterprise solution | Offer SaaS pricing; demonstrate peer small-site success; narrow scope |
| Customer is building in-house | Position as indispensable capability; quantify switching cost; deepen relationship |

---

## 11. Buying Triggers (14)

| ID | Trigger | Urgency | Timing |
|---|---|---|---|
| bt-cm-001 | Customer audit failure or conditional pass | CRITICAL | 0-3 months |
| bt-cm-002 | Customer contract non-renewal notice | CRITICAL | 0-6 months |
| bt-cm-003 | Regulatory inspection warning letter | CRITICAL | 0-3 months |
| bt-cm-004 | New customer qualification mandate | HIGH | 3-9 months |
| bt-cm-005 | Multi-site acquisition integration | HIGH | 6-18 months |
| bt-cm-006 | Serialization regulatory deadline | HIGH | 0-12 months |
| bt-cm-007 | EBR / paperless manufacturing initiative | HIGH | 6-18 months |
| bt-cm-008 | Major customer price-down mandate | HIGH | 0-6 months |
| bt-cm-009 | New site or greenfield launch | HIGH | 12-24 months |
| bt-cm-010 | Customer scorecard decline trend | HIGH | 0-6 months |
| bt-cm-011 | Technology transfer volume surge | MEDIUM | 3-12 months |
| bt-cm-012 | PE operational improvement thesis | HIGH | 3-12 months |
| bt-cm-013 | ERP end-of-life or unsupported version | MEDIUM | 6-18 months |
| bt-cm-014 | Cold chain excursion or GDP audit failure | HIGH | 0-6 months |

---

## 12. Worked Examples (3)

### Example 1: CDMO Multi-Site EBR and QMS Consolidation
- **Scenario:** $500M pharma CDMO, 4 sites, paper batch records, separate QMS, 12 audit findings/site, 14-day batch release
- **Value:** $5.89M annual (audit remediation + release acceleration + QBR automation + IT consolidation)
- **Confidence:** HIGH

### Example 2: EMS Customer Portal and OTIF Improvement
- **Scenario:** $1.2B EMS, 25 customers, 85% OTIF, $18M chargebacks, manual data exchange
- **Value:** $16.5M direct + $20M revenue protected
- **Confidence:** HIGH

### Example 3: Toll Manufacturer Yield Reconciliation and Costing
- **Scenario:** $200M toll chemical, 3 sites, 4.5% yield variance, 6 disputes/month, 35% win rate
- **Value:** $19.25M annual
- **Confidence:** MEDIUM

---

## 13. Governance

| Field | Value |
|---|---|
| Source Coverage | Mixed (public filings, industry reports, benchmarks, regulatory databases) |
| Confidence | High |
| Last Updated | 2026-04-25 |
| Approved for Customer-Facing | No (internal intelligence only) |
| Review Owner | contract-manufacturing-subpack-architect |
| Agent Swarm ID | kimi-k2.6-elevated-swarm-s1.4 |
| Parent Master Swarm ID | kimi-k2.6-elevated-swarm |

---

## 14. Usage Notes

### Signal-to-Hypothesis Workflow
1. **Detect** raw signal (e.g., customer audit finding surge, job posting for EBR roles)
2. **Interpret** using signal rules with confidence scoring
3. **Map** to linked pains and KPIs
4. **Identify** affected personas and their pressures
5. **Quantify** using vertical formulas with customer-specific inputs
6. **Validate** with discovery questions
7. **Address** anticipated objections

### Value Quantification Discipline
- Every formula requires validated baseline and target inputs
- Confidence rules must be checked before presenting to customer
- Use ranges rather than false precision
- Always connect to one of four value categories: Revenue Uplift, Cost Savings, Risk Reduction, Working Capital

---

*End of Contract Manufacturing Subpack ValuePack*
