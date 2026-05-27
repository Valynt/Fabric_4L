# Payers and Health Insurance Subpack (S3.2)

**ID:** `payers-v1`  
**Version:** 1.0.0  
**Domain:** Industry  
**Pack Type:** Subpack  
**Parent Master ID:** `healthcare-master-v1`  
**Vertical Focus:** Commercial plans, Medicare Advantage, Medicaid managed care, employer plans, TPAs, PBMs, dental/vision, stop-loss, VBC/ACOs  
**Last Updated:** 2026-04-25  
**Agent Swarm ID:** `kimi-k2.6-swarm-payers-s3.2`  

---

## Table of Contents

1. [Overview & Inheritance Manifest](#1-overview--inheritance-manifest)
2. [Vertical Pains (18)](#2-vertical-pains)
3. [Vertical KPIs (22)](#3-vertical-kpis)
4. [Value Drivers (Payer-Specific)](#4-value-drivers)
5. [Value Formulas (12)](#5-value-formulas)
6. [Vertical Benchmarks (18)](#6-vertical-benchmarks)
7. [Signal Interpretation Rules (18)](#7-signal-rules)
8. [Persona Profiles (6 New)](#8-persona-profiles)
9. [Buying Triggers (14)](#9-buying-triggers)
10. [Technology Systems (12)](#10-technology-systems)
11. [Regulatory Factors (10)](#11-regulatory-factors)
12. [Discovery Questions (18)](#12-discovery-questions)
13. [Objection Patterns (9)](#13-objection-patterns)
14. [Competitor Factors](#14-competitor-factors)
15. [Worked Examples (3)](#15-worked-examples)
16. [Governance](#16-governance)

---

## 1. Overview & Inheritance Manifest

### Purpose
This subpack extends the Healthcare Master ValuePack with vertical-specialized intelligence for payers and health insurance organizations. It provides machine-parseable definitions tailored to the unique economics, regulatory constraints, and operational models of risk-bearing and administrative health plans.

### Inherited Context (Read-Only from Master)
- **Value Driver Framework** (Revenue Uplift / Cost Savings / Risk Reduction / Working Capital)
- **Base Persona Archetypes** (CFO, COO, Chief Strategy Officer, CISO, CCO)
- **Evidence Source Types** (10-K, CMS data, earnings calls, job postings, breach portals)
- **Formula Templates** (improvement × volume × unit value)
- **Signal Source Taxonomy** (financial, operational, regulatory, competitive)
- **Benchmark Methodology** (industry survey, government, financial ratings, academic)
- **Governance Framework** (confidence levels, validation rules, approval gates)

### Inheritance Manifest

| Component | Status | Details |
|-----------|--------|---------|
| **Inherited Components** | Read-Only | Value Driver Framework; Base Persona Archetypes (CFO, COO, CSO, CISO, CCO); Evidence Source Types; Formula Templates; Signal Source Taxonomy; Benchmark Methodology; Governance Framework; Pains P006, P008, P010-P012, P017, P021-P022; KPIs K021-K023, K027-K029, K033-K042, K068-K073; Value Drivers V015, V019, V025, V029; Signal Rules S005, S012, S018, S030; Tech Systems T016-T017; Regulatory REG001-REG004, REG011-REG012 |
| **Created Components** | New | 18 Pains; 22 KPIs; 12 Formulas; 18 Benchmarks; 18 Signal Rules; 6 Personas; 14 Buying Triggers; 12 Tech Systems; 10 Regulatory Factors; 18 Discovery Questions; 9 Objections; 3 Worked Examples; Payer-Specific Competitor Factors |
| **Overridden Components** | Extended | MA Star Rating Erosion (P011) — extended with new measures and bonus mechanics; Claims Adjudication (P010) — extended with auto-adjudication sub-causes; MLR Pressure (P012) — extended with reinsurance and COVID-era unwind |
| **Vertical Persona Additions** | New | Chief Medical Officer (Plan), Chief Actuary, Network Contracting Director, Grievances & Appeals Manager, Population Health Analyst, Risk Adjustment Director |
| **Vertical KPI Extensions** | New | Member churn rate, grievance resolution rate, COB recovery rate, network adequacy ratio, PMPM pharmacy trend, MA member growth rate, HEDIS hybrid measure rate, appeals overturn rate |

---

## 2. Vertical Pains

### PP001: Medicare Advantage Star Rating Erosion
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** Star rating < 4.0 or declining YoY; HEDIS measure gap in 3+ domains; CAHPS < 75th percentile; PDC < 80% for triple-weighted measures; HOS measure decline; QBP bonus at risk > $50M
- **Affected Segments:** Medicare Advantage, Part D
- **Affected Personas:** Chief Strategy Officer, CMO (Plan), VP Quality, Chief Actuary
- **Linked KPIs:** PK001, PK002, PK003, PK004
- **Linked Value Drivers:** PV001, PV002
- **Sources:** CMS 2025 Star Ratings, CMS Medicare Advantage Rate Announcement, McKinsey MA Stars Analysis 2024
- **Financial Outcome:** Revenue Uplift (QBP bonus + rebate retention)

### PP002: Medical Loss Ratio (MLR) Compression Below 85%
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** MLR > 87% with admin cost PMPM > median + 10%; SG&A as % of premium > 12%; reinsurance costs increasing > 15% YoY; COVID-era morbidity unwind pressuring trend; competitive premium pressure from new entrants (Oscar, Clover, Devoted)
- **Affected Segments:** Commercial, MA, Medicaid MCOs
- **Affected Personas:** CFO, COO, Chief Actuary, Chief Strategy Officer
- **Linked KPIs:** PK005, PK006, PK007
- **Linked Value Drivers:** PV003, PV004
- **Sources:** CMS MLR Reporting, NAIC Financial Reporting, KFF Health Insurance Marketplace Trends 2024, S&P Global Health Insurance Outlook
- **Financial Outcome:** Cost Savings (admin cost reduction, medical cost management)

### PP003: Claims Auto-Adjudication Gap and Backlog
- **Prevalence:** MEDIUM-HIGH | **Confidence:** HIGH
- **Symptoms:** Auto-adjudication rate < 85%; claims backlog > 10 days; call center volume increasing > 20% YoY; provider dispute rate > 3%; first-pass resolution rate < 70%; manual touch rate > 15% for routine claims
- **Affected Segments:** All payer operations
- **Affected Personas:** COO, VP Claims, CIO, Chief Actuary
- **Linked KPIs:** PK008, PK009, PK010
- **Linked Value Drivers:** PV005, PV006
- **Sources:** CAQH Index 2024, AHIP Operational Efficiency Survey, Gartner Payer Operations Benchmark
- **Financial Outcome:** Cost Savings (FTE reduction, call center avoidance)

### PP004: Fraud Waste Abuse (FWA) Detection Gap
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** FWA detection rate < 1% of claims; false positive rate > 90%; recovery rate < 3x SIU cost; hotline reports backlog > 30 days; DOJ settlement history or qui tam exposure; prepay detection < 20% of recoveries
- **Affected Segments:** All payer types, PBMs
- **Affected Personas:** Chief Compliance Officer, SIU Director, General Counsel, CFO
- **Linked KPIs:** PK011, PK012, PK013
- **Linked Value Drivers:** PV007, PV008
- **Sources:** HCFAC Annual Report DOJ/HHS, CMS Program Integrity Reports, NHCAA Healthcare Fraud Estimate
- **Financial Outcome:** Risk Reduction (DOJ settlement avoidance, recovery maximization)

### PP005: Care Gap Closure and HEDIS Underperformance
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** Care gap closure rate < 60%; HEDIS measure gap in 5+ measures; preventable ED utilization > 100/1000 members; chronic disease registry incomplete; outreach response rate < 15%; hybrid measure reporting errors > 10%
- **Affected Segments:** MA, Medicaid MCOs, Commercial
- **Affected Personas:** Population Health Analyst, CMO (Plan), VP Quality, VP Care Management
- **Linked KPIs:** PK014, PK015, PK016
- **Linked Value Drivers:** PV009, PV010
- **Sources:** NCQA HEDIS 2024, CMS Medicare Advantage CBI Data, Optum Care Gap Analysis
- **Financial Outcome:** Revenue Uplift (Stars bonus, quality withhold recovery)

### PP006: Risk Adjustment Revenue Leakage and RADV Exposure
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** RAF score gap > 0.08 vs. expected; HCC recapture rate < 85%; suspecting rate < 40% of eligible encounters; retrospective chart review yield < $500 per chart; RADV audit exposure > $20M; ICD-10 coding specificity gaps in 3+ HCC categories
- **Affected Segments:** Medicare Advantage, ACA, Medicaid
- **Affected Personas:** Risk Adjustment Director, CFO, Chief Actuary, CMO (Plan)
- **Linked KPIs:** PK017, PK018, PK019
- **Linked Value Drivers:** PV011, PV012
- **Sources:** CMS RADV Results 2024, CMS-HCC Model V28 Documentation, AHIMA Risk Adjustment Accuracy Studies
- **Financial Outcome:** Revenue Uplift (RAF optimization, RADV penalty avoidance)

### PP007: Medicare Advantage Member Churn & Retention Crisis
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** Voluntary disenrollment rate > 12% annually; broker-driven churn > 40% of total disenrollment; NPS < 25; call center satisfaction < 70%; digital engagement < 30% of members; SNP retention < 80%
- **Affected Segments:** Medicare Advantage, Part D
- **Affected Personas:** Chief Strategy Officer, VP Member Experience, Chief Actuary
- **Linked KPIs:** PK020, PK021, PK022
- **Linked Value Drivers:** PV013, PV014
- **Sources:** CMS Monthly Enrollment by Plan, J.D. Power Medicare Advantage Study 2024, Deft Research MA Shopping Study
- **Financial Outcome:** Revenue Uplift (retention = LTV preservation)

### PP008: Medicaid MCO Margin Compression & Rate Pressure
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** State rate increase < medical trend + 2%; MLR > 90% in Medicaid; administrative cap < 5% of premium; high-cost member pool growing (LTSS, I/DD, SMI); encounter data rejection rate > 15%; retroactive rate adjustments > $5M annually
- **Affected Segments:** Medicaid MCOs
- **Affected Personas:** CFO, Chief Actuary, VP Government Programs
- **Linked KPIs:** PK005, PK023, PK024
- **Linked Value Drivers:** PV015, PV016
- **Sources:** KFF Medicaid MCO Trends 2024, CMS Medicaid Managed Care Financial Report, State Health Reform Tracking
- **Financial Outcome:** Cost Savings (encounter efficiency, care management ROI)

### PP009: Employer Group RFP Loss & Commercial Risk Erosion
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** Employer group loss ratio > 80% for > 2 years; RFP win rate < 30%; premium increase requests > 8% driving broker defection; self-insured ASO migration > 10% of risk book; stop-loss attachment point escalation > $150K; direct primary care carve-outs increasing
- **Affected Segments:** Commercial Health Plans, TPAs, Stop-Loss
- **Affected Personas:** Chief Strategy Officer, VP Sales, Chief Actuary
- **Linked KPIs:** PK025, PK026, PK027
- **Linked Value Drivers:** PV017, PV018
- **Sources:** KFF Employer Health Benefits Survey 2024, AHIP Commercial Market Report, Mercer National Survey of Employer-Sponsored Health Plans
- **Financial Outcome:** Revenue Uplift (retention + new business margin)

### PP010: PBM Drug Cost Escalation & Rebate Transparency Pressure
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** Specialty drug spend > 45% of pharmacy budget; rebate retention under pressure (PBM reform legislation); GDR (generic dispense rate) < 84%; biosimilar adoption < 30% of eligible volume; DIR fee accumulation > $8 PMPM; accumulator / maximizer program member complaints increasing
- **Affected Segments:** PBMs, Health Plans with insourced PBM
- **Affected Personas:** CFO, Chief Pharmacy Officer, VP Contracting, Chief Actuary
- **Linked KPIs:** PK028, PK029, PK030
- **Linked Value Drivers:** PV019, PV020
- **Sources:** Drug Channels Institute 2024, CMS PBM Transparency Rule, FTC PBM Interim Report 2024
- **Financial Outcome:** Cost Savings (drug trend management, rebate optimization)

### PP011: Network Adequacy & Provider Contracting Disputes
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** Network adequacy complaints > CMS/state threshold; OON rate > 8% of claims; provider dispute rate > 5% of in-network claims; contract renegotiation frequency increasing (annual vs. biennial); narrow network legal challenges; directory accuracy < 85%; No Surprises Act arbitration backlog
- **Affected Segments:** All payer types
- **Affected Personas:** Network Contracting Director, Chief Strategy Officer, General Counsel
- **Linked KPIs:** PK031, PK032, PK033
- **Linked Value Drivers:** PV021, PV022
- **Sources:** CMS Network Adequacy Standards, State DOI Complaint Data, No Surprises Act Federal IDR Reports
- **Financial Outcome:** Risk Reduction (regulatory penalty avoidance) + Cost Savings (network cost optimization)

### PP012: Stop-Loss Premium Escalation & LASER Proliferation
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Symptoms:** Stop-loss premium trend > 12% annually; LASER (laser) rate > 15% of covered employees; aggregate attachment point breaches increasing; high-cost claimant frequency > 2 per 1,000 employees; specific deductible requests > $500K; captive formation inquiries increasing
- **Affected Segments:** Stop-Loss Carriers, Self-Insured Employers, TPAs
- **Affected Personas:** Chief Actuary, VP Underwriting, CFO
- **Linked KPIs:** PK034, PK035, PK036
- **Linked Value Drivers:** PV023, PV024
- **Sources:** Stop Loss Insurance Market Report 2024, Sun Life High-Cost Claims Analysis, Self-Insurance Institute of America (SIIA) Data
- **Financial Outcome:** Revenue Uplift (underwriting precision) + Cost Savings (claimant management)

### PP013: Grievances & Appeals Backlog / State DOI Complaints
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** Grievance resolution time > 30 days; overturn rate on appeal > 40%; state DOI complaints per 1,000 members > industry median; CMS sanctions or CMP for untimely determinations; member call escalations > 15% of total volume; IRO (Independent Review Organization) referral rate increasing
- **Affected Segments:** All payer types
- **Affected Personas:** Grievances & Appeals Manager, Chief Compliance Officer, General Counsel
- **Linked KPIs:** PK037, PK038, PK039
- **Linked Value Drivers:** PV025, PV026
- **Sources:** NAIC Consumer Complaint Database, CMS Medicare Advantage Compliance Activity, State DOI Annual Reports
- **Financial Outcome:** Risk Reduction (CMP avoidance, reputation protection)

### PP014: Value-Based Contracting Performance & Shared Savings Shortfall
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Symptoms:** ACO shared savings rate < 50% of target; total cost of care (TCC) trend > benchmark + 2%; quality measure attainment < 70%; provider administrative burden complaints increasing; attribution methodology disputes; downside risk exposure > $10M annually; MSSP ACO exit consideration
- **Affected Segments:** ACOs, MA Plans, Commercial VBC, Medicaid MCOs
- **Affected Personas:** Population Health Analyst, CFO, CMO (Plan), VP Contracting
- **Linked KPIs:** PK040, PK041, PK042
- **Linked Value Drivers:** PV027, PV028
- **Sources:** CMS MSSP Financial & Quality Results 2024, NAACOS ACO Survey, Health Affairs VBC Performance Studies
- **Financial Outcome:** Revenue Uplift (shared savings) + Cost Savings (medical cost trend reduction)

### PP015: Digital Member Engagement & Portal Underutilization
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Symptoms:** Member portal registration rate < 40%; mobile app MAU < 15% of members; telehealth utilization < 5% of eligible encounters; digital care gap closure rate < 20% of total; HEDIS e-measure gap; CAHPS health plan information measure < 60th percentile
- **Affected Segments:** MA, Commercial, Medicaid, Exchange
- **Affected Personas:** VP Member Experience, CIO, Chief Strategy Officer
- **Linked KPIs:** PK043, PK044, PK045
- **Linked Value Drivers:** PV029, PV030
- **Sources:** J.D. Power U.S. Commercial Member Health Plan Study 2024, CMS CAHPS Health Plan Survey, Forrester Digital Experience Index
- **Financial Outcome:** Cost Savings (call center deflection, digital self-service)

### PP016: COB / Subrogation Recovery Gap
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** COB recovery rate < 60% of identified overpayments; subrogation identification rate < 50% of accident-related claims; other insurance verification < 70% at point of service; MSP (Medicare Secondary Payer) compliance errors > 5% of eligible claims; conditional payment recovery backlog > 90 days
- **Affected Segments:** Medicare Advantage, Commercial, Medicaid
- **Affected Personas:** CFO, VP Claims, Chief Actuary
- **Linked KPIs:** PK046, PK047, PK048
- **Linked Value Drivers:** PV031, PV032
- **Sources:** CMS MSP Compliance, CAQH Index COB Metrics, Healthcare Subrogation Industry Association Data
- **Financial Outcome:** Revenue Uplift (recovery maximization)

### PP017: Pharmacy DIR Fee & Reimbursement Timing Compression
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** DIR fee drag > $12 PMPM; retroactive DIR adjustments > $5M annually; pharmacy reimbursement < AWP - 20%; 340B contract pharmacy exclusion list impact; specialty pharmacy network narrowing; LDD (lowest dispensing cost) reimbursement pressure; CMS True OOP / counting rule uncertainty
- **Affected Segments:** Medicare Part D, MA-PD, PBMs
- **Affected Personas:** Chief Pharmacy Officer, CFO, Chief Actuary
- **Linked KPIs:** PK049, PK050, PK051
- **Linked Value Drivers:** PV033, PV034
- **Sources:** CMS Part D DIR Reporting, PQA Pharmacy Quality Alliance, CMS Contract Year 2025 Final Rule
- **Financial Outcome:** Revenue Uplift (DIR optimization) + Cost Savings (network efficiency)

### PP018: Medicare Advantage RADV Audit and Risk Adjustment Compliance Exposure
- **Prevalence:** MEDIUM-HIGH | **Confidence:** HIGH
- **Symptoms:** RADV extrapolation error rate > 10%; condition-specific documentation gaps in HCC categories 87/88/96/111; physician coding education compliance < 60%; EMR-based suspecting tool underutilization; HCC invalidation rate > 15% on audit; conditional payment demand received
- **Affected Segments:** Medicare Advantage
- **Affected Personas:** Risk Adjustment Director, CCO, CMO (Plan), CFO
- **Linked KPIs:** PK052, PK053, PK054
- **Linked Value Drivers:** PV035, PV036
- **Sources:** CMS RADV Final Rule 2023, CMS HCC Model V28, OIG MA Risk Adjustment Audits
- **Financial Outcome:** Risk Reduction (RADV penalty avoidance, extrapolation protection)

---

## 3. Vertical KPIs

| ID | Name | Formula | Unit | Typical Range | Benchmark |
|----|------|---------|------|---------------|-----------|
| PK001 | Medicare Advantage Star Rating | CMS weighted composite of 40+ measures across 5 domains | stars | 3.0–4.5 | >4.0 (bonus threshold) |
| PK002 | HEDIS Hybrid Measure Rate | (HEDIS Hybrid Measures Met / Total Applicable Hybrid Measures) × 100 | % | 55–90 | >80% (best practice) |
| PK003 | Medication Adherence (PDC) | Days Covered by Supply / Days in Period (diabetes, HTN, cholesterol) | % | 68–85 | >80% (Stars threshold) |
| PK004 | CAHPS Health Plan Score | Medicare CAHPS / Commercial CAHPS composite score | score | 70–85 | >80 (75th percentile target) |
| PK005 | Medical Loss Ratio (MLR) | (Medical Claims + QI Expenses) / Total Premium Revenue × 100 | % | 80–90 | 80-88% (varies by market) |
| PK006 | Administrative Cost PMPM | Total Administrative Expenses / Total Member Months | USD PMPM | $35–$75 | <$40 (efficient) |
| PK007 | SG&A as % of Premium Revenue | SG&A Expenses / Total Premium Revenue × 100 | % | 8–14 | <10% (best practice) |
| PK008 | Claims Auto-Adjudication Rate | (Claims Auto-Adjudicated / Total Claims Received) × 100 | % | 78–92 | >90% (best practice) |
| PK009 | Average Claims Processing Time | Sum of Days from Receipt to Adjudication / Total Claims Processed | days | 3–14 | <5 days (best practice) |
| PK010 | First-Pass Resolution Rate | (Claims Paid Correctly on First Submission / Total Claims Submitted) × 100 | % | 85–96 | >95% (best practice) |
| PK011 | FWA Detection Rate | (Identified FWA Claims / Total Claims Processed) × 100 | % | 0.5–2.5 | >1.5% (best practice) |
| PK012 | FWA Recovery Ratio | Total FWA Recoveries / Total SIU Operating Costs | ratio | 3:1 to 12:1 | >6:1 (best practice) |
| PK013 | Prepay Detection Rate | (FWA Claims Stopped Prepayment / Total FWA Identified) × 100 | % | 20–50 | >40% (best practice) |
| PK014 | Care Gap Closure Rate | (Closed Care Gaps / Total Identified Care Gaps) × 100 | % | 45–75 | >70% (best practice) |
| PK015 | Preventable ED Utilization Rate | (Preventable ED Visits / Total Member Months) × 1,000 | per 1K | 60–140 | <80 (best practice) |
| PK016 | HEDIS Measure Attainment | (Measures Meeting Target / Total Applicable Measures) × 100 | % | 60–92 | >85% (best practice) |
| PK017 | Risk Adjustment Factor (RAF) Score | Sum of CMS-HCC Risk Scores / Total Enrollees | index | 0.85–1.35 | Gap vs. expected drives value |
| PK018 | HCC Recapture Rate | (HCCs Documented Current Year / Total Prior Year HCCs) × 100 | % | 75–92 | >90% (best practice) |
| PK019 | Suspecting Rate | (Encounters with HCC-Suspecting Documentation / Total Eligible Encounters) × 100 | % | 30–60 | >50% (best practice) |
| PK020 | Voluntary Disenrollment Rate | (Voluntary Disenrollments / Average Member Count) × 100 | % | 6–18 | <10% (best practice) |
| PK021 | Member NPS | Net Promoter Score from member satisfaction survey | score | 10–40 | >25 (best practice) |
| PK022 | Digital Engagement Rate | (Active Digital Users / Total Members) × 100 | % | 15–45 | >35% (best practice) |

---

## 4. Value Drivers (Payer-Specific)

| ID | Signal Pattern | Interpreted Pain | Category | KPIs | Personas | Confidence |
|----|---------------|-----------------|----------|------|----------|------------|
| PV001 | Star rating < 4.0 with HEDIS gap in 3+ domains | Quality underperformance threatening QBP bonus | Revenue Uplift | PK001, PK002, PK003 | CSO, CMO (Plan), VP Quality | HIGH |
| PV002 | CAHPS score < 75th percentile with churn > 12% | Member experience driving disenrollment and LTV loss | Revenue Uplift | PK004, PK020, PK021 | CSO, VP Member Experience | HIGH |
| PV003 | MLR > 87% with admin PMPM > $65 | Administrative cost burden eroding competitive pricing | Cost Savings | PK005, PK006, PK007 | CFO, COO, Chief Actuary | HIGH |
| PV004 | SG&A > 12% with auto-adjudication < 85% | Operational inefficiency in claims driving admin bloat | Cost Savings | PK007, PK008, PK009 | COO, VP Claims | HIGH |
| PV005 | Auto-adjudication < 85% with backlog > 10 days | Manual claims processing creating cost and provider abrasion | Cost Savings | PK008, PK009, PK010 | COO, VP Claims, CIO | HIGH |
| PV006 | First-pass resolution < 90% with call volume increasing | Rework loop consuming FTEs and member satisfaction | Cost Savings | PK010, PK009 | COO, VP Claims | HIGH |
| PV007 | FWA detection < 1% with recovery < 3:1 | Inadequate fraud detection leaving money on table | Risk Reduction | PK011, PK012 | CCO, SIU Director | HIGH |
| PV008 | Prepay detection < 25% with false positive > 90% | Post-pay recovery model is expensive and provider-abrasive | Cost Savings | PK013, PK011 | SIU Director, CCO | HIGH |
| PV009 | Care gap closure < 60% with preventable ED > 100/1K | Unmanaged chronic disease driving medical cost trend | Cost Savings | PK014, PK015 | Population Health Analyst, CMO (Plan) | HIGH |
| PV010 | HEDIS attainment < 70% with Stars < 4.0 | Quality measure failure blocking bonus and retention | Revenue Uplift | PK016, PK001, PK002 | VP Quality, CMO (Plan) | HIGH |
| PV011 | RAF gap > 0.08 with recapture < 85% | Under-documentation causing underpayment vs. CMS benchmark | Revenue Uplift | PK017, PK018, PK019 | Risk Adjustment Director, CFO | HIGH |
| PV012 | Suspecting rate < 40% with EMR tool underutilization | Missed encounter opportunities for HCC capture | Revenue Uplift | PK019, PK017 | Risk Adjustment Director, CMO (Plan) | HIGH |
| PV013 | Churn > 15% with broker-driven > 40% | Distribution instability threatening membership base | Revenue Uplift | PK020, PK021 | CSO, Chief Actuary | HIGH |
| PV014 | NPS < 20 with digital engagement < 20% | Member experience and digital maturity lagging competitors | Revenue Uplift | PK021, PK022 | VP Member Experience, CIO | MEDIUM |
| PV015 | State rate increase < medical trend + 2% with MLR > 90% | Medicaid MCO margin unsustainable without intervention | Cost Savings | PK005, PK023 | CFO, VP Government Programs | HIGH |
| PV016 | Encounter rejection > 15% with retroactive adjustments > $5M | Encounter data quality undermining state reporting and payment | Cost Savings | PK023, PK024 | COO, VP Government Programs | HIGH |
| PV017 | RFP win rate < 30% with self-insured migration > 10% | Commercial risk book erosion threatening top-line | Revenue Uplift | PK025, PK026 | CSO, VP Sales | HIGH |
| PV018 | Premium increase > 8% with broker defection > 5% | Pricing pressure creating retention spiral | Revenue Uplift | PK026, PK027 | CSO, Chief Actuary | HIGH |
| PV019 | Specialty spend > 45% with GDR < 84% | Drug mix shift toward high-cost specialty without generic optimization | Cost Savings | PK028, PK029 | Chief Pharmacy Officer, CFO | HIGH |
| PV020 | DIR fee drag > $12 PMPM with retroactive adjustments > $5M | Pharmacy reimbursement timing and fee structure compressing margin | Cost Savings | PK049, PK050 | Chief Pharmacy Officer, CFO | HIGH |
| PV021 | OON rate > 8% with directory accuracy < 85% | Network adequacy and accuracy issues driving regulatory risk | Risk Reduction | PK031, PK032 | Network Contracting Director, General Counsel | HIGH |
| PV022 | Provider dispute rate > 5% with arbitration backlog | Contracting friction increasing cost and abrasion | Cost Savings | PK032, PK033 | Network Contracting Director, CSO | HIGH |
| PV023 | Stop-loss premium trend > 12% with LASER > 15% | Underwriting precision declining; high-cost claimant identification poor | Revenue Uplift | PK034, PK035 | Chief Actuary, VP Underwriting | MEDIUM |
| PV024 | Aggregate attachment breach frequency increasing with specific > $500K | Large claim management and reinsurance placement suboptimal | Cost Savings | PK036, PK034 | VP Underwriting, CFO | MEDIUM |
| PV025 | Grievance resolution > 30 days with overturn rate > 40% | Determination quality issues creating compliance and cost exposure | Risk Reduction | PK037, PK038 | Grievances Manager, CCO | HIGH |
| PV026 | State DOI complaints > median with CMS sanctions history | Regulatory escalation threatening license and contract eligibility | Risk Reduction | PK039, PK038 | CCO, General Counsel | HIGH |
| PV027 | ACO shared savings < 50% of target with TCC trend > benchmark + 2% | Value-based contract underperformance eroding provider trust | Revenue Uplift | PK040, PK041 | Population Health Analyst, CFO | MEDIUM |
| PV028 | Quality attainment < 70% with provider admin burden complaints | Quality program design creating friction without results | Cost Savings | PK042, PK040 | Population Health Analyst, CMO (Plan) | MEDIUM |
| PV029 | Digital engagement < 20% with portal registration < 40% | Digital maturity gap increasing service cost and member dissatisfaction | Cost Savings | PK022, PK043 | VP Member Experience, CIO | MEDIUM |
| PV030 | Telehealth utilization < 5% with CAHPS information < 60th percentile | Virtual care underutilization and information access gaps | Cost Savings | PK044, PK045 | CIO, VP Member Experience | MEDIUM |
| PV031 | COB recovery < 60% with MSP errors > 5% | Coordination of benefits leakage and Medicare compliance exposure | Revenue Uplift | PK046, PK047 | VP Claims, CFO | HIGH |
| PV032 | Subrogation identification < 50% with recovery backlog > 90 days | Accident-related claim recovery underperforming | Revenue Uplift | PK048, PK046 | VP Claims, Chief Actuary | HIGH |
| PV033 | DIR fee drag > $12 PMPM with LDD pressure | Pharmacy reimbursement compression threatening Part D viability | Cost Savings | PK049, PK050 | Chief Pharmacy Officer, CFO | HIGH |
| PV034 | 340B exclusion impact > $3M with specialty network narrowing | Contract pharmacy disruption and network adequacy tension | Cost Savings | PK051, PK031 | Chief Pharmacy Officer, Network Contracting Director | HIGH |
| PV035 | RADV error rate > 10% with HCC invalidation > 15% | Documentation quality creating extrapolation penalty risk | Risk Reduction | PK052, PK053 | Risk Adjustment Director, CCO | HIGH |
| PV036 | Conditional payment demand received with coding education < 60% | CMS recovery action indicating systematic documentation failure | Risk Reduction | PK054, PK052 | Risk Adjustment Director, CFO | HIGH |

---

## 5. Value Formulas

| ID | Name | Formula Expression | Required Inputs | Output Unit | Confidence Rules | Example Calculation |
|----|------|-------------------|-----------------|-------------|------------------|-------------------|
| PF001 | MA Stars Bonus Value | (Rating Improvement × Member Months × Bonus PMPM) + QBP Enhancement + Rebate Retention | Current stars, target stars, member months, bonus PMPM, rebate rate | USD annually | HIGH when using CMS published QBP tables; MEDIUM when projecting member months | 0.5 × 1.2M × $85 + $12M = $63M |
| PF002 | MLR Admin Cost Reduction | (Current Admin PMPM – Target) × Member Months + (SG&A Reduction × Premium Revenue) | Current admin PMPM, target, member months, SG&A %, premium revenue | USD annually | HIGH when based on internal GL; MEDIUM when using industry benchmarks | ($62 – $45) × 800K + (11.5% – 9.5%) × $4B = $93.6M |
| PF003 | Claims Auto-Adjudication Value | (Volume × Manual Cost per Claim × Automation Lift %) + (Backlog Reduction × Interest Cost) + (Provider Satisfaction Impact on Network Cost) | Annual claim volume, manual cost per claim, automation lift %, backlog days, interest rate | USD annually | HIGH when vendor provides automated measurement; MEDIUM for provider satisfaction quantification | 24M × $3.20 × 0.65 + $1.2M + $2.8M = $53.9M |
| PF004 | FWA Recovery Value | (Prepay Stopped × Avg Claim Value) + (Postpay Recovery × Recovery Rate) – (SIU Operating Cost × (1 + Target ROI)) | Prepay stopped count, avg claim value, postpay recovery $, recovery rate, SIU cost | USD annually | HIGH when SIU costs are tracked; MEDIUM for prepay valuation | $8.4M + $18.2M – $4.2M = $22.4M net |
| PF005 | Care Gap Closure Value | (Gaps Closed × Avg Cost per Gap) + (Preventable ED Avoided × Avg ED Cost) + (Stars Improvement × Bonus PMPM × Member Months) | Gap closure improvement, cost per gap, preventable ED reduction, avg ED cost, stars impact | USD annually | HIGH when linked to HEDIS/Stars; MEDIUM for standalone commercial | 45K × $1,200 + 12K × $3,800 + $8M = $105.2M |
| PF006 | RAF Optimization Value | (Target RAF – Current RAF) × Member Months × Benchmark Rate × Coding Adjustment – RADV Penalty Risk | Target RAF, current RAF, member months, benchmark rate, coding adjustment, RADV exposure | USD annually | HIGH when retrospective chart review data available; MEDIUM for suspecting-only programs | 0.08 × 150K × $950 × 0.955 – $5M = $5.86M net |
| PF007 | Member Retention Value | (Churn Reduction × Member Months × LTV per Member) + (Broker Churn Reduction × Acquisition Cost Savings) | Current churn, target churn, member months, LTV, broker churn %, acquisition cost | USD annually | HIGH when LTV model exists; MEDIUM when using industry LTV estimates | (14% – 10%) × 200K × $3,600 + $4.2M = $33M |
| PF008 | Medicaid MCO Margin Protection | (Encounter Rejection Reduction × Avg Claim Value × 12) + (Rate Appeal Success × Retroactive Adjustment $) + (Administrative Cap Efficiency) | Rejection rate, avg claim value, rate appeal success, retroactive $, admin cap | USD annually | HIGH when state reporting exists; MEDIUM for rate appeal projections | $6.2M + $4.8M + $2.1M = $13.1M |
| PF009 | Employer Group Retention Value | (Group Retention Improvement × Group Premium) + (RFP Win Rate Improvement × Pipeline Value × Win Probability) | Retention improvement, group premium, RFP win rate delta, pipeline, win probability | USD annually | HIGH when pipeline CRM data available; MEDIUM for win probability | $28M + $42M = $70M |
| PF010 | PBM Drug Trend Management | (Specialty Trend Reduction × Specialty Spend) + (Biosimilar Adoption Increase × Brand Spend) + (DIR Fee Reduction × Part D Membership) | Specialty trend delta, specialty spend, biosimilar adoption delta, brand spend, DIR reduction, Part D membership | USD annually | HIGH when PBM contract data available; MEDIUM for trend attribution | $45M + $18M + $6.4M = $69.4M |
| PF011 | Network Adequacy & Dispute Cost Avoidance | (Dispute Reduction × Avg Dispute Resolution Cost) + (No Surprises Act Arbitration Avoidance × Avg Arbitration Cost) + (Directory Accuracy Improvement × Member Complaint Cost) | Dispute count, resolution cost, arbitration count, arbitration cost, complaint count, complaint cost | USD annually | HIGH when legal department tracks; MEDIUM for complaint cost quantification | $3.8M + $2.4M + $1.1M = $7.3M |
| PF012 | Grievance & Appeals Efficiency Value | (Resolution Time Reduction × FTE Cost Savings) + (Overturn Rate Reduction × Avg Overturn Cost) + (CMP Avoidance × Probability) | Resolution time delta, FTE cost, overturn rate delta, avg overturn cost, CMP exposure, probability | USD annually | HIGH when compliance tracks; MEDIUM for CMP probability | $2.1M + $4.5M + $1.5M EV = $8.1M |

---

## 6. Vertical Benchmarks

| ID | Name | Value | Range | Unit | Source | Segment | Geographic Scope | Company Size | Confidence | Date Sourced |
|----|------|-------|-------|------|--------|---------|-----------------|--------------|------------|-------------|
| PB001 | MA Star Rating (National Average) | 4.04 | 3.5–4.5 | stars | CMS 2025 Star Ratings | Medicare Advantage | US | All | HIGH | Oct 2024 |
| PB002 | HEDIS Measure Attainment (National) | 76 | 65–88 | % | NCQA HEDIS 2024 | All Payers | US | All | HIGH | Sep 2024 |
| PB003 | Medication Adherence PDC (Triple-Weighted) | 79 | 72–85 | % | CMS Stars Technical Notes | Medicare Advantage | US | All | HIGH | Oct 2024 |
| PB004 | Commercial MLR (Individual) | 86.5 | 80–92 | % | CMS MLR Reporting | Commercial Exchange | US | All | HIGH | Apr 2024 |
| PB005 | MA MLR (Average) | 87.2 | 83–91 | % | CMS Medicare Advantage Financial Reports | Medicare Advantage | US | All | HIGH | Apr 2024 |
| PB006 | Medicaid MCO MLR | 89.5 | 85–93 | % | KFF Medicaid MCO Trends | Medicaid MCO | US | All | HIGH | Dec 2024 |
| PB007 | Admin Cost PMPM (Large Commercial) | 42 | 32–58 | USD | AHIP Cost and Utilization Report | Commercial | US | >100K lives | HIGH | Jun 2024 |
| PB008 | Claims Auto-Adjudication Rate | 88 | 82–94 | % | CAQH Index 2024 | All Payers | US | All | HIGH | Mar 2024 |
| PB009 | First-Pass Resolution Rate | 92 | 85–96 | % | CAQH Index 2024 | All Payers | US | All | HIGH | Mar 2024 |
| PB010 | FWA Recovery Ratio | 6.5 | 3:1 to 12:1 | ratio | NHCAA / HCFAC | All Payers | US | All | HIGH | Nov 2024 |
| PB011 | Care Gap Closure Rate (MA) | 68 | 50–82 | % | CMS CBI Data | Medicare Advantage | US | All | HIGH | Jul 2024 |
| PB012 | Preventable ED Utilization (MA) | 95 | 70–140 | per 1K | CMS Medicare Advantage CBI | Medicare Advantage | US | All | HIGH | Jul 2024 |
| PB013 | HCC Recapture Rate (MA) | 88 | 80–95 | % | CMS RADV / AHIMA | Medicare Advantage | US | All | HIGH | Mar 2024 |
| PB014 | MA Voluntary Disenrollment Rate | 10.5 | 6–18 | % | CMS Monthly Enrollment | Medicare Advantage | US | All | HIGH | Jan 2025 |
| PB015 | Member NPS (Health Plans) | 24 | 10–40 | score | J.D. Power MA Study 2024 | All Payers | US | All | HIGH | Oct 2024 |
| PB016 | Digital Engagement Rate (Health Plans) | 28 | 15–45 | % | Forrester Digital Experience Index | All Payers | US | All | MEDIUM | Jun 2024 |
| PB017 | Grievance Resolution Time (Medicare) | 18 | 10–35 | days | CMS Medicare Compliance Activity | Medicare Advantage | US | All | HIGH | Dec 2024 |
| PB018 | Employer Group RFP Win Rate (National) | 32 | 20–45 | % | AHIP Commercial Market Report | Commercial | US | All | MEDIUM | Sep 2024 |

---

## 7. Signal Interpretation Rules

| ID | Signal Name | Raw Signal Pattern | Interpreted Meaning | Linked Pains | Linked KPIs | Confidence | Required Confirmation |
|----|------------|-------------------|---------------------|--------------|-------------|------------|----------------------|
| PS001 | CMS Star Rating Decline | MA plan declines 0.5+ stars or below 4.0 | Quality underperformance threatening QBP and marketing rights | PP001 | PK001, PK002 | 0.91 | HEDIS measure detail; CAHPS breakdown |
| PS002 | MLR Filing – Admin Cost Spike | NAIC filing shows admin cost PMPM increase > 15% YoY | Administrative bloat or operational crisis pressuring MLR compliance | PP002 | PK006, PK007 | 0.87 | Compare to premium trend; check SG&A line |
| PS003 | CMS Sanctions / CMP Notice | CMS issues sanctions, CMP, or marketing suspension | Compliance failure with direct financial and operational penalties | PP013, PP018 | PK039, PK052 | 0.93 | Read sanction type; check history |
| PS004 | MA Member Growth Plateau | Quarterly enrollment flat or declining vs. market growth | Product-market fit or broker relationship deterioration | PP007 | PK020, PK021 | 0.85 | Compare to county-level market data; broker commission analysis |
| PS005 | State DOI Complaint Surge | NAIC complaint index > 1.5x median for 2+ quarters | Service quality or claims handling issues escalating to regulators | PP013 | PK038, PK039 | 0.89 | Complaint category breakdown; trend analysis |
| PS006 | Medicaid MCO Contract Loss | State awards contract to competitor or reduces service area | Revenue and margin pressure from core government book | PP008 | PK023, PK005 | 0.86 | Check protest status; remaining contract duration |
| PS007 | PBM Contract RFP / Termination | PBM client issues RFP or announces non-renewal | Rebate transparency or service quality pressure | PP010 | PK028, PK029 | 0.84 | Check contract value; competing PBMs |
| PS008 | High-Cost Claimant Notification | Stop-loss carrier reports claimant exceeding specific deductible | Laser rate pressure and aggregate attachment risk | PP012 | PK034, PK036 | 0.82 | Claimant count; diagnosis trend; LASER history |
| PS009 | RADV Audit Letter Received | CMS issues RADV audit or conditional payment demand | Documentation quality failure with extrapolation risk | PP018 | PK052, PK053 | 0.94 | Audit scope; sample size; HCC categories targeted |
| PS010 | Employer Group Defection Announcement | Employer announces plan switch or self-insured migration | Commercial risk erosion and pricing competitiveness gap | PP009 | PK025, PK026 | 0.88 | Group size; reason cited; broker involvement |
| PS011 | FWA Whistleblower / Qui Tam Filing | DOJ unseals qui tam or announces settlement | Systematic fraud detection or coding practice failure | PP004 | PK011, PK012 | 0.92 | Allegation scope; plan response; settlement range |
| PS012 | Network Provider Termination Spree | > 5% of network providers terminated or not renewed | Network adequacy risk and member disruption | PP011 | PK031, PK032 | 0.81 | Provider type; replacement rate; member notification |
| PS013 | HEDIS Audit Finding / NCQA Accreditation Risk | NCQA issues deferral or HEDIS audit finding | Quality reporting integrity at risk; Stars/HEDIS measure jeopardy | PP005 | PK016, PK002 | 0.90 | Finding type; measures affected; remediation timeline |
| PS014 | DIR Fee Regulation Comment Letter | Plan submits CMS comment on DIR / True OOP / counting rules | Pharmacy reimbursement timing and fee structure uncertainty | PP017 | PK049, PK050 | 0.78 | Comment position; CMS response trajectory |
| PS015 | Digital Member Engagement Vendor RFP | RFP for member portal, app, or CRM platform | Digital maturity gap driving service cost or member dissatisfaction | PP015 | PK022, PK043 | 0.76 | Check incumbent; scope; timeline |
| PS016 | ACO Shared Savings Shortfall | MSSP or commercial ACO misses savings target | Value-based contract underperformance eroding provider relationships | PP014 | PK040, PK041 | 0.83 | ACO track record; measure performance; provider sentiment |
| PS017 | COB / Subrogation Vendor Search | Job postings or RFP for COB/subrogation services | Recovery gap or MSP compliance concern | PP016 | PK046, PK047 | 0.79 | Check current vendor; recovery rate; MSP error rate |
| PS018 | Risk Adjustment Vendor Consolidation | Job postings for in-house risk adjustment or vendor RFP | RAF optimization pressure or RADV response need | PP006 | PK017, PK019 | 0.86 | Current vendor; RAF trend; RADV status |

---

## 8. Persona Profiles (6 New)

### PER-P001: Chief Medical Officer (Plan)
- **Seniority:** C-Suite | **Influence:** Technical
- **Goals:** Improve HEDIS/Stars measures, close care gaps, advance value-based care, ensure network clinical quality, manage population health outcomes
- **Pressures:** Stars bonus at risk, HEDIS reporting burden, provider network quality disputes, member health equity mandates, SDOH integration demands
- **Trusted Evidence:** CMS Star Ratings technical notes, NCQA HEDIS specifications, peer-reviewed population health studies, Milliman care guidelines, internal clinical analytics
- **Disliked Claims:** Population health without data integration, quality improvement without provider partnership, "one size fits all" care management programs
- **Decision Influence:** Technical (drives clinical program design; needs CFO/CSO for budget)

### PER-P002: Chief Actuary
- **Seniority:** C-Suite / SVP | **Influence:** Economic
- **Goals:** Ensure pricing adequacy, manage reserve adequacy, optimize MLR, support Stars bonus forecasting, minimize forecast variance, enable competitive bidding
- **Pressures:** Morbidity trend uncertainty, reserve adequacy scrutiny (NAIC/state DOI), CMS rate announcement timing, rebate projections, VBC contract financial modeling
- **Trusted Evidence:** CMS rate announcements, NAIC financial reporting, Milliman / Oliver Wyman trend reports, internal claim cost triangles, S&P / Moody's rating commentary
- **Disliked Claims:** Unquantified risk-sharing proposals, technology ROI without actuarial validation, trend predictions without confidence intervals
- **Decision Influence:** Economic (controls pricing, reserves, financial projections; must validate all major financial commitments)

### PER-P003: Network Contracting Director
- **Seniority:** VP / SVP | **Influence:** Economic
- **Goals:** Optimize network cost position, ensure network adequacy compliance, minimize provider disputes, negotiate value-based contracts, manage OON exposure
- **Pressures:** Provider rate inflation (hospital systems > 8% annual asks), No Surprises Act arbitration backlog, narrow network regulatory scrutiny, ACO contract complexity, directory accuracy mandates
- **Trusted Evidence:** FAIR Health benchmarks, CMS network adequacy standards, state DOI guidance, internal network cost analytics, competitor network filings
- **Disliked Claims:** Network "optimization" that means access reduction, value-based contracts without shared savings evidence, arbitrary rate cuts without quality linkage
- **Decision Influence:** Economic (controls significant portion of medical spend; needs legal/CSO for strategy)

### PER-P004: Grievances & Appeals Manager
- **Seniority:** Director / VP | **Influence:** User
- **Goals:** Resolve grievances within regulatory timeframes, minimize overturn rate, maintain CMS/state compliance, reduce member abrasion, prevent escalation to DOI/CMS sanctions
- **Pressures:** Increasing grievance volume, complex clinical determination requirements, CMS marketing and compliance sanctions, state DOI complaint index scrutiny, IRO cost escalation
- **Trusted Evidence:** CMS Medicare Advantage compliance activity reports, NAIC complaint database, internal grievance analytics, state DOI guidance, NCQA accreditation standards
- **Disliked Claims:** Automation replacing clinical judgment in determinations, "standardized" approaches to complex cases, solutions without regulatory expertise
- **Decision Influence:** User (operational owner; escalates to CCO/General Counsel for sanctions; needs IT for workflow)

### PER-P005: Population Health Analyst
- **Seniority:** Manager / Director | **Influence:** Technical
- **Goals:** Identify care gaps, predict high-risk members, measure HEDIS/Stars performance, model VBC contract outcomes, integrate SDOH data, enable care management targeting
- **Pressures:** Data fragmentation (claims + EHR + HIE), HEDIS hybrid measure complexity, attribution methodology disputes, SDOH data availability, predictive model accuracy scrutiny
- **Trusted Evidence:** CMS CBI data, NCQA HEDIS technical specifications, internal A/B test results, published predictive model validations, CMS ACO REACH data
- **Disliked Claims:** AI/ML predictions without explainability, care gap lists without outreach integration, population health analytics without closed-loop workflow
- **Decision Influence:** Technical (provides analytical foundation; needs CMO/VP Quality for program activation; needs IT for data pipelines)

### PER-P006: Risk Adjustment Director
- **Seniority:** Director / VP | **Influence:** Technical
- **Goals:** Maximize RAF accuracy, ensure HCC recapture > 90%, minimize RADV audit exposure, optimize suspecting programs, manage physician coding education, ensure documentation integrity
- **Pressures:** CMS-HCC model V28 transition, RADV extrapolation risk, retrospective chart review ROI pressure, EMR integration complexity, physician coding compliance, suspecting tool accuracy
- **Trusted Evidence:** CMS RADV results, CMS-HCC model documentation, AHIMA coding accuracy studies, internal RAF trending, retrospective chart review yield data
- **Disliked Claims:** RAF "optimization" that suggests upcoding, automated suspecting without clinical validation, coding education without physician engagement
- **Decision Influence:** Technical (owns RAF methodology; needs CFO for budget; needs CMO for physician engagement; needs IT for EMR integration)

---

## 9. Buying Triggers

| ID | Trigger | Urgency | Typical Timing | Linked Pains | Procurement Implications |
|----|---------|---------|---------------|-------------|------------------------|
| PBT001 | CMS Star Rating Decline Below 4.0 | HIGH | Oct announcement; Jan-Mar procurement | PP001, PP005 | Board-level priority; quality vendor selection; 6-9 month implementation |
| PBT002 | MLR Filing Shows Admin Cost Spike | HIGH | Q1-Q2 following NAIC filing | PP002, PP003 | CFO-driven; operational efficiency RFP; 3-6 month decision |
| PBT003 | CMS Sanctions or CMP Notice | CRITICAL | Immediate; 30-60 day response | PP013, PP018 | Compliance-driven; limited vendor pool; accelerated procurement |
| PBT004 | MA Member Growth Plateau or Decline | HIGH | Q1-Q2 following quarterly enrollment | PP007, PP001 | CSO-driven; retention/experience platform; 6-12 month cycle |
| PBT005 | State DOI Complaint Index Surge | HIGH | Immediate; 60-90 day remediation | PP013 | Compliance-driven; grievance/appeals system; 3-6 month decision |
| PBT006 | Medicaid MCO Contract Rebid or Loss | HIGH | 6-12 months before effective date | PP008, PP002 | Strategic; platform consolidation; 9-18 month cycle |
| PBT007 | PBM Contract RFP or Non-Renewal | HIGH | 12-18 months before expiration | PP010, PP017 | Procurement-driven; pricing transparency focus; 12-18 month cycle |
| PBT008 | High-Cost Claimant / LASER Event | MEDIUM | Immediate; strategic 60-90 days | PP012 | Underwriting-driven; clinical management vendor; 3-6 month cycle |
| PBT009 | RADV Audit Letter or Conditional Payment Demand | CRITICAL | Immediate; 30-60 day response | PP018, PP006 | Compliance-driven; risk adjustment vendor; 1-3 month accelerated |
| PBT010 | Employer Group Defection or Self-Insured Migration | HIGH | Immediate; 90-180 days before effective | PP009, PP002 | CSO/Sales-driven; pricing and service platform; 6-12 month cycle |
| PBT011 | FWA Whistleblower or DOJ Investigation | CRITICAL | Immediate; 15-30 day response | PP004 | Legal-driven; SIU technology and services; 1-3 month accelerated |
| PBT012 | Network Provider Termination Crisis | HIGH | Immediate; 60-90 days | PP011 | Network/CSO-driven; directory and adequacy platform; 3-6 month cycle |
| PBT013 | HEDIS Audit Finding or NCQA Deferral | HIGH | Immediate; 60-120 day remediation | PP005, PP001 | Quality-driven; HEDIS/quality reporting platform; 3-6 month cycle |
| PBT014 | ACO Shared Savings Miss or Provider Exit | MEDIUM | Q3-Q4 following performance year | PP014, PP011 | VBC-driven; population health and analytics platform; 6-9 month cycle |

---

## 10. Technology Systems

| ID | System | Category | Description | Typical Vendors | Integration Points |
|----|--------|----------|-------------|-----------------|-------------------|
| PT001 | Core Administration Platform (Claims) | Core Operations | Policy admin, claims adjudication, benefits configuration, enrollment management | HealthEdge, Cognizant TriZetto (Facets/QNXT), Pega, Guidewire, Salesforce Health Cloud | T016 (master), CRM, provider directory, FWA engine |
| PT002 | FWA Detection & SIU Platform | Compliance | Prepay and postpay fraud detection, predictive analytics, case management, investigative workflow | SAS, Pondera, NTT DATA, FICO, Shift Technology, Codoxo | Core claims platform, provider data, clinical systems |
| PT003 | Risk Adjustment / HCC Suspecting Engine | Analytics | RAF optimization, HCC recapture tracking, suspecting algorithms, chart review workflow, coding education | Optum, Cotiviti, Inovalon, Episource, 3M, Watson Health | EMR data, claims data, provider portals, quality systems |
| PT004 | HEDIS / Quality Reporting Engine | Quality | HEDIS measure calculation, hybrid measure data collection, NCQA submission, Stars simulation | MedInsight, Inovalon, Verscend, Cotiviti, NCQA Certified | Claims, EMR, lab data, member roster, CAHPS vendor |
| PT005 | Member Engagement / CRM Platform | Consumer | Member portal, mobile app, omnichannel outreach, digital care gap closure, preference management | Salesforce Health Cloud, Pegasystems, Wellframe, mPulse, HealthEquity | Core admin, population health, HEDIS engine, telehealth |
| PT006 | Provider Directory & Network Management | Network | Provider data management, credentialing, network adequacy monitoring, directory accuracy, contract management | Kyruus, Andes Health, Salesforce Health Cloud, Quest Analytics | Core admin, provider portals, state reporting |
| PT007 | Value-Based Care / ACO Analytics | Analytics | Shared savings calculation, total cost of care trending, attribution logic, provider scorecards, VBC contract modeling | Arcadia, Lumeris, Signify Health, MedInsight, Clarify Health | Claims, EMR, pharmacy data, member roster |
| PT008 | PBM / Pharmacy Management System | Pharmacy | Formulary management, claims adjudication, rebate administration, DIR tracking, specialty pharmacy | CVS/caremark, Express Scripts, OptumRx, Prime Therapeutics, Magellan Rx | Core admin, member engagement, rebate accounting |
| PT009 | Grievances & Appeals Management | Compliance | Grievance intake, tracking, determination workflow, appeal escalation, regulatory reporting, IRO coordination | Pega, Salesforce, Guidewire, FINEOS, HPMS-compliant custom | Core admin, clinical systems, legal document management |
| PT010 | COB / Subrogation Recovery System | Financial | Other insurance identification, MSP compliance, subrogation case management, recovery tracking, conditional payment | Conduent, Optum, HMS, Trover Solutions, Equian | Core claims, eligibility, legal, accounting |
| PT011 | Prior Authorization Automation | Clinical | PA intake, clinical decision support, auto-approval pathways, provider portal, turnaround tracking | Cohere Health, Evicore, Invaio, AZOVA, MCG/Evidence-based | Core admin, clinical criteria engines, EMR integration |
| PT012 | Actuarial & Pricing Workbench | Financial | Trend analysis, reserve modeling, rating development, MLR simulation, bid optimization, VBC financial modeling | Milliman, Oliver Wyman, SAS, R/Python stacks, Guidewire | Core admin, GL, claims warehouse, CMS rate files |

---

## 11. Regulatory Factors

| ID | Regulation | Applicability | Deadline / Cadence | Penalty for Non-Compliance | Affected Segments |
|----|-----------|--------------|-------------------|--------------------------|-------------------|
| PREG001 | ACA Section 1557 (Nondiscrimination) | All health plans receiving federal funds | Ongoing; complaint-driven | OCR investigation; CMP; contract termination risk | All Payers |
| PREG002 | CMS Star Ratings (42 CFR 422.166) | All MA and Part D plans | Annual Oct release; measurement year prior | Bonus loss $50-150 PMPM; marketing restriction; contract termination | Medicare Advantage, Part D |
| PREG003 | MLR Reporting (ACA 2718 / 45 CFR 158) | Commercial, MA, Part D, Medicaid MCOs | Annual filing (Jun for prior year) | Rebate obligation to enrollees/state; CMS corrective action | All Payers |
| PREG004 | CMS Medicare Advantage & Part D Final Rule (CY 2025+) | All MA/PDP plans | Annual contract year effective Jan 1 | Marketing suspension; CMP; Star rating reduction; contract non-renewal | Medicare Advantage, Part D |
| PREG005 | NAIC Financial Reporting / Risk-Based Capital | All licensed health plans | Quarterly / Annual NAIC statements | Regulatory action; license restriction; receivership | All Licensed Payers |
| PREG006 | State DOI / Medicaid Agency Reporting | State-licensed plans; Medicaid MCOs | Varies by state (monthly/quarterly/annual) | Contract termination; CMP; restriction on new business | All Payers, Medicaid MCOs |
| PREG007 | No Surprises Act (NSA) / Federal Independent Dispute Resolution | Plans covering OON emergency and air ambulance; IDR entities | Jan 2022 ongoing; IDR process ongoing | Federal CMP; arbitration award; state enforcement | Commercial, Exchange, MA |
| PREG008 | CMS RADV (Risk Adjustment Data Validation) | Medicare Advantage | Annual audits; targeted and national | Extrapolated repayment; conditional payment demand; Star rating impact | Medicare Advantage |
| PREG009 | PBM Transparency / FTC 6(b) Study | PBMs; health plans with insourced PBM | Ongoing; proposed rulemaking | FTC enforcement; state PBM licensure action; contract ineligibility | PBMs, MA-PD, Part D |
| PREG010 | HIPAA / HITECH (45 CFR 160, 164) | All covered entities and business associates | Ongoing; breach notification 60 days | $137-$2.068M per category; criminal up to $250K + 10 years; OCR settlement | All Payers |

---

## 12. Discovery Questions

| ID | Question | Target Personas | Linked Pains | Insight Sought | Timing |
|----|----------|----------------|-------------|----------------|--------|
| PDQ001 | What is your current Medicare Advantage Star rating, and which three measures moved most year-over-year? | CMO (Plan), Chief Strategy Officer, VP Quality | PP001 | Stars vulnerability and QBP exposure | Early |
| PDQ002 | Walk me through your MLR trend over the last three years. What is your admin cost PMPM vs. premium trend? | CFO, Chief Actuary | PP002 | Margin compression severity and admin cost opportunity | Early |
| PDQ003 | What is your auto-adjudication rate, and what percentage of claims require manual touch for non-complex reasons? | COO, VP Claims | PP003 | Operational efficiency gap and automation potential | Early |
| PDQ004 | How do you identify and close HCC coding gaps? What is your recapture rate, RAF trend, and current RADV status? | Risk Adjustment Director, CFO | PP006, PP018 | RAF optimization opportunity and audit exposure | Middle |
| PDQ005 | What is your voluntary disenrollment rate, and what percentage is broker-driven vs. member-initiated? | Chief Strategy Officer, VP Member Experience | PP007 | Retention dynamics and LTV risk | Early |
| PDQ006 | What was your last state rate increase for Medicaid, and how does it compare to your medical cost trend? | CFO, Chief Actuary, VP Government Programs | PP008 | Medicaid margin sustainability | Early |
| PDQ007 | What is your employer group RFP win rate, and what are the top three reasons cited for losses? | Chief Strategy Officer, VP Sales | PP009 | Commercial competitiveness gaps | Middle |
| PDQ008 | How is your PBM managing specialty drug trend, and what is your current DIR fee impact on Part D? | Chief Pharmacy Officer, CFO | PP010, PP017 | Pharmacy cost management and fee transparency | Middle |
| PDQ009 | What is your network adequacy complaint rate, and how many No Surprises Act arbitrations are pending? | Network Contracting Director, General Counsel | PP011 | Network regulatory exposure and dispute volume | Middle |
| PDQ010 | What is your stop-loss LASER rate, and how has your high-cost claimant frequency trended over three years? | Chief Actuary, VP Underwriting | PP012 | Underwriting precision and reinsurance need | Middle |
| PDQ011 | What is your average grievance resolution time, and what is your appeal overturn rate by level? | Grievances Manager, CCO | PP013 | Compliance and determination quality | Early |
| PDQ012 | How are your ACO shared savings performing vs. target? What is your total cost of care trend vs. benchmark? | Population Health Analyst, CFO | PP014 | VBC contract performance and provider trust | Middle |
| PDQ013 | What is your digital member engagement rate (portal, app, telehealth), and how does it correlate with satisfaction? | VP Member Experience, CIO | PP015 | Digital maturity and self-service opportunity | Middle |
| PDQ014 | What is your COB recovery rate and subrogation identification rate? How much recovery is left on the table? | VP Claims, CFO | PP016 | Recovery gap and MSP compliance | Middle |
| PDQ015 | What is your FWA detection rate, false positive rate, and recovery ratio? How much is prepay vs. postpay? | SIU Director, CCO | PP004 | Fraud detection maturity and ROI | Early |
| PDQ016 | How are you preparing for the CMS-HCC Model V28 transition? What is your expected RAF impact? | Risk Adjustment Director, Chief Actuary | PP006 | Risk model transition readiness | Middle |
| PDQ017 | What is your HEDIS hybrid measure reporting process, and what was your last NCQA audit outcome? | VP Quality, Population Health Analyst | PP005 | Quality reporting integrity | Early |
| PDQ018 | What are your top three strategic initiatives for the next 18 months, and how will technology enable them? | Chief Strategy Officer, CIO | PP001, PP002, PP014 | Strategic priority alignment | Late |

---

## 13. Objection Patterns

| ID | Objection | Common From | Underlying Concern | Reframe Strategy | Supporting Evidence |
|----|-----------|-------------|-------------------|-------------------|-------------------|
| POBJ001 | We already have a PBM/vendor that handles pharmacy | Chief Pharmacy Officer, CFO | Fear of disruption, rebate loss, contract complexity | Position as complementary analytics layer; demonstrate PBM-agnostic value; reference PBM clients | PBM transparency reports, DIR analytics case studies |
| POBJ002 | Our Stars score is good enough; we don't need change | CMO (Plan), VP Quality | Complacency, change fatigue, budget constraints | Quantify QBP at risk from measure drift; show competitor improvement; reference 0.1 star = $X PMPM | CMS QBP tables, McKinsey Stars analysis, peer comparison |
| POBJ003 | The state sets our rates; we can't control margin | CFO, VP Government Programs | Fatalism about Medicaid economics, resistance to operational solutions | Reframe to encounter efficiency, care management ROI, administrative cap optimization; show state MCO peers | KFF Medicaid MCO margin data, encounter efficiency benchmarks |
| POBJ004 | Our actuaries need to validate any financial projection | Chief Actuary, CFO | Skepticism of vendor ROI claims, professional risk aversion | Provide actuarial-ready models with confidence intervals; offer actuary-to-actuary review; reference actuarial firm validations | Milliman/Oliver Wyman endorsements, actuarial memo templates |
| POBJ005 | We tried risk adjustment and it didn't move the needle | Risk Adjustment Director, CFO | Past vendor failure, EMR integration trauma, physician resistance | Diagnose prior failure (suspecting vs. in-home assessment vs. coding education); differentiate with closed-loop workflow; offer pilot with yield guarantee | Retrospective chart review yield data, physician engagement metrics |
| POBJ006 | Our network team handles contracting; we don't need help | Network Contracting Director, CSO | Territory protection, skepticism of external benchmarks | Position as data and analytics augmentation, not replacement; offer FAIR Health benchmark access; show dispute prediction value | FAIR Health data, No Surprises Act arbitration analytics |
| POBJ007 | Grievances and appeals is a compliance function, not a tech function | Grievances Manager, CCO | Fear of automation replacing compliance judgment | Emphasize workflow automation and tracking, not determination automation; show CMS sanction avoidance value; reference compliant deployments | CMS sanction case studies, resolution time reduction data |
| POBJ008 | We don't have budget for a new platform this year | CFO, COO | Budget cycle rigidity, unproven ROI | Frame as self-funding via MLR reduction or recovery increase; phased implementation; success fee model | Self-funding case studies, phased ROI timeline |
| POBJ009 | Our data is too fragmented across claims, EMR, and pharmacy | CIO, Population Health Analyst | Data integration anxiety, past project failure | Include data readiness assessment; demonstrate entity resolution and master data capabilities; reference fragmented environment success | Multi-source integration case studies, data quality guarantees |

---

## 14. Competitor Factors

| ID | Competitor Factor | Impact on Buying Behavior | Confidence |
|----|------------------|--------------------------|------------|
| PCF001 | UnitedHealth / Optum Vertical Integration (payer + provider + PBM + data) | Independent payers must differentiate on provider neutrality, data portability, or specialty network depth | HIGH |
| PCF002 | CVS Health / Aetna + Caremark Integration | Accelerates PBM-medical integration; drives medical cost management and pharmacy trend collaboration | HIGH |
| PCF003 | Cigna / Express Scripts + Evernorth | Employer market consolidation; drives whole-health and behavioral health bundling; independent vendors must show integration value | HIGH |
| PCF004 | Humana CenterWell + MA Focus | MA market concentration; drives provider-primary care integration; competitors seek clinical differentiation | HIGH |
| PCF005 | Oscar Health / Clover Health / Devoted Health (Tech-Native MA) | Digital-first member experience and risk adjustment sophistication pressures legacy plans to modernize | HIGH |
| PCF006 | Centene / WellCare Medicaid MCO Scale | Medicaid market concentration; state procurements favor scale; niche players serve carve-outs (LTSS, behavioral health) | HIGH |
| PCF007 | Amazon Pharmacy / One Medical / PillPack Entry | Employer and MA pharmacy cost transparency pressure; drives PBM RFP activity and rebate scrutiny | HIGH |
| PCF008 | Medicaid MCO Consolidation (top 5 ~60% lives) | State procurements favor scale; niche players serve supplements or specialized populations | HIGH |

---

## 15. Worked Examples

### Example 1: Medicare Advantage Star Rating Recovery

**Context:** Regional MA plan with 180,000 members dropped from 4.0 to 3.5 stars. QBP bonus at risk = $85 PMPM.

**Pain:** PP001 (MA Star Rating Erosion)

**KPIs:** PK001 (Stars 3.5), PK002 (HEDIS hybrid gap in 4 domains), PK003 (PDC 76%)

**Formula Applied:** PF001 — MA Stars Bonus Value

**Calculation:**
- Current QBP at 3.5 stars: $0 PMPM (no bonus for < 4.0)
- Target: 4.0 stars = $85 PMPM QBP
- Member months: 180,000 × 12 = 2.16M
- Value of 0.5 star improvement: 2.16M × $85 = $183.6M annually
- Implementation cost estimate: $18M (quality programs, HEDIS data collection, CAHPS intervention)
- Net 3-year value: $550M – $54M = $496M

**Confidence:** HIGH — CMS QBP tables are public and deterministic; member months are known.

**Validation Required:** Confirm current HEDIS measure-level gaps; validate CAHPS improvement feasibility; assess whether 0.5 star is achievable in single measurement year or requires multi-year trajectory.

---

### Example 2: Medicaid MCO Operational Efficiency

**Context:** State Medicaid MCO with 400,000 members. MLR at 91%, admin cap at 4.8%, encounter rejection rate at 18%.

**Pain:** PP008 (Medicaid MCO Margin Compression)

**KPIs:** PK005 (MLR 91%), PK023 (encounter rejection 18%), PK008 (auto-adjudication 78%)

**Formula Applied:** PF002 (MLR Admin Cost Reduction) + PF003 (Claims Auto-Adjudication Value)

**Calculation:**
- Admin cost reduction: ($52 – $42) PMPM × 4.8M member months = $48M
- Encounter rejection reduction: 18% → 8% = 10% × 24M encounters × $45 avg = $108M annual revenue protection
- Auto-adjudication lift: 78% → 88% = 10% × 36M claims × $2.80 manual cost = $10.1M
- Total annual value: $48M + $108M + $10.1M = $166.1M
- Implementation cost: $22M (platform upgrade, encounter data quality program)
- Net 3-year value: $498M – $66M = $432M

**Confidence:** HIGH — State rate and encounter data are contractual; admin cap is regulatory.

**Validation Required:** Confirm state encounter acceptance criteria; validate encounter volume and rejection root causes; assess state timeline for rate reconsideration.

---

### Example 3: Commercial Employer Group Retention + PBM Optimization

**Context:** Commercial health plan losing employer groups to self-insured migration. 50,000 risk lives at risk. PBM specialty trend at 16% with DIR fee drag at $14 PMPM.

**Pain:** PP009 (Employer Group RFP Loss) + PP010 (PBM Drug Cost Escalation)

**KPIs:** PK025 (RFP win rate 28%), PK026 (group loss ratio 82%), PK028 (specialty spend 48%), PK049 (DIR drag $14 PMPM)

**Formula Applied:** PF009 (Employer Group Retention Value) + PF010 (PBM Drug Trend Management)

**Calculation:**
- Group retention: Prevent loss of 15K lives × $450 PMPM × 12 = $81M premium retention
- RFP win rate improvement: 28% → 35% on $200M pipeline × 40% win probability = $5.6M incremental
- Specialty trend reduction: 16% → 12% on $180M specialty spend = $7.2M
- Biosimilar adoption: 25% → 50% on $60M eligible brand spend = $15M
- DIR fee reduction: $14 → $8 PMPM on 80K Part D members × 12 = $5.8M
- Total annual value: $81M + $5.6M + $7.2M + $15M + $5.8M = $114.6M
- Implementation cost: $16M (employer retention platform, PBM analytics layer)
- Net 3-year value: $344M – $48M = $296M

**Confidence:** MEDIUM — RFP win rate improvement depends on competitive dynamics; PBM rebate structures are proprietary.

**Validation Required:** Confirm employer contract renewal calendar; validate PBM contract terms (rebate guarantees, DIR pass-through); assess biosimilar formulary positioning.

---

## 16. Governance

| Attribute | Value |
|-----------|-------|
| Source Coverage | Mixed (public filings, CMS data, NAIC reporting, industry surveys, proprietary benchmarks) |
| Confidence Level | High |
| Last Updated | 2026-04-25 |
| Approved for Customer-Facing Output | No (internal intelligence asset; requires review before external use) |
| Review Owner | payers-subpack-architect |
| Agent Swarm ID | kimi-k2.6-swarm-payers-s3.2 |
| Parent Master Swarm ID | kimi-k2.6-swarm-healthcare-m3 |
| Version | 1.0.0 |

### Confidence Flags Used
- **HIGH:** Multiple corroborating sources, quantified data, direct regulatory or financial reporting (CMS, NAIC, CAQH, NCQA)
- **MEDIUM:** Industry survey data, partial quantification, or single-source but authoritative (J.D. Power, KFF, McKinsey)
- **LOW:** Estimates, directional indicators, or emerging trends with limited data (digital engagement benchmarks, biosimilar adoption projections)

### Validation Required Before Customer Use
1. Verify current CMS Star Ratings and QBP tables against latest CMS announcements
2. Confirm MLR and admin cost benchmarks against NAIC/CAQH latest publications
3. Validate organization-specific member months, premium rates, and RAF scores before citing in proposals
4. Update Medicaid state rate and contract timelines quarterly
5. Review PBM contract terms and DIR structures for client-specific accuracy
6. Confirm RADV audit status and extrapolation methodology with client legal/compliance
7. Validate FWA recovery ratios against SIU internal tracking (often not public)
8. Update competitor landscape quarterly (M&A, market exits, new MA entrants)
9. Review signal rules for false positive rate against historical conversion data

---

*End of Payers and Health Insurance Subpack v1.0.0*
