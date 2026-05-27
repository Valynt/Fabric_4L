# Providers / Care Delivery ValuePack (S3.1)

**ID:** `providers-v1`  
**Version:** 1.0.0  
**Domain:** Industry  
**Pack Type:** Subpack  
**Parent Master ID:** `healthcare-master-v1`  
**Last Updated:** 2026-04-25  
**Agent Swarm ID:** `kimi-k2.6-swarm-healthcare-providers-s3.1`  
**Confidence:** High  
**Approved for Customer-Facing Output:** No  

---

## Table of Contents

1. [Overview & Purpose](#1-overview--purpose)
2. [Inheritance Manifest](#2-inheritance-manifest)
3. [Vertical Focus](#3-vertical-focus)
4. [Business Pains (20)](#4-business-pains)
5. [KPI Definitions (25)](#5-kpi-definitions)
6. [Value Drivers (20)](#6-value-drivers)
7. [Value Formulas (12)](#7-value-formulas)
8. [Benchmarks (18)](#8-benchmarks)
9. [Signal Interpretation Rules (20)](#9-signal-interpretation-rules)
10. [Persona Profiles (6 New)](#10-persona-profiles)
11. [Buying Triggers (15)](#11-buying-triggers)
12. [Technology Systems (15)](#12-technology-systems)
13. [Regulatory Factors (12)](#13-regulatory-factors)
14. [Competitor Factors (8)](#14-competitor-factors)
15. [Discovery Questions (18)](#15-discovery-questions)
16. [Objection Patterns (10)](#16-objection-patterns)
17. [Worked Examples (3)](#17-worked-examples)
18. [Evidence Sources (8)](#18-evidence-sources)
19. [Governance](#19-governance)

---

## 1. Overview & Purpose

The Providers / Care Delivery Subpack extends the Healthcare Master ValuePack with vertical-specialized intelligence for organizations that directly deliver clinical care. This subpack focuses on operational, clinical, and financial pain points unique to hospitals, academic medical centers, ambulatory clinics, ASCs, behavioral health, home health, hospice, telehealth, rural/community health, and FQHCs.

### Financial Outcome Mapping
Every component maps to one of four financially meaningful outcomes:

| Category | Definition | Example Drivers |
|----------|------------|-----------------|
| **Revenue Uplift** | Increasing top-line through better throughput, capture, or pricing | OR utilization improvement, no-show reduction, swing bed capture, hospice LOS optimization |
| **Cost Savings** | Reducing operating expense without quality degradation | ED boarding reduction, ICU step-down efficiency, ASC supply cost control, telehealth platform consolidation |
| **Risk Reduction** | Minimizing regulatory, legal, safety, or reputational exposure | CMS CoP compliance, Joint Commission accreditation, HACRP penalty avoidance, EMTALA compliance |
| **Working Capital / Cash Flow Improvement** | Accelerating cash conversion and improving liquidity | FQHC grant revenue capture, ASC case mix optimization, anesthesia billing capture |

---

## 2. Inheritance Manifest

### Inherited Components (Read-Only from Master)
- Value Driver Framework (4-category outcome taxonomy)
- Base Persona Archetypes (CFO, COO, CMO, CNO, CIO, CISO, VP Revenue Cycle, CCO, Population Health VP, CSO, CHRO, CMIO, Chief Pharmacy Officer/340B Director)
- Evidence Source Taxonomy (10-K, earnings calls, CMS Hospital Compare, HHS OCR, bond ratings, industry surveys, press releases)
- Formula Templates (denial reduction, LOS reduction, turnover cost avoidance, contract labor substitution, readmission penalty avoidance)
- Signal Source Taxonomy (job postings, earnings call mentions, bond rating changes, regulatory actions, leadership changes)
- Benchmark Methodology (HFMA, CMS, Crowe, NSI, Kaufman Hall, SullivanCotter)
- Governance Framework (confidence levels, validation rules, source citations)

### Created Components (Vertical-Specialized)
- 20 Vertical Pains (ED boarding, OR delays, clinic no-shows, ICU step-down, home health readmissions, telehealth failures, swing bed underutilization, etc.)
- 25 Vertical KPIs (OR first-case on-time %, turnover time, PACU LOS, clinic cycle time, telehealth completion rate, swing bed occupancy, etc.)
- 20 Vertical Signal Rules (CMS CoP findings, Joint Commission sentinel events, OR block release patterns, ED diversion spikes, etc.)
- 6 New Personas (CMIO-specialist, Nurse Manager, Patient Access Director, Bed Manager, OR Director, Telehealth Medical Director)
- 12 Vertical Formulas (OR throughput, ED flow, no-show recovery, ICU step-down, swing bed revenue, etc.)
- 18 Vertical Benchmarks (OR metrics, ED metrics, clinic metrics, home health, hospice, behavioral health, FQHC)
- 12 Vertical Regulatory Factors (CMS CoP, Joint Commission, HCAHPS/VBP, No Surprises Act, EMTALA, CON, HACRP, USP <797>/<800>, HHVBP, HRSA 330, state staffing ratios)
- 15 Vertical Technology Systems (EHR, CPOE, RTLS, Nurse Call, Bed Management, RIS/PACS, AIMS, Surgical Scheduling, EDIS, Telehealth, Home Health EMR, BH EHR, ASC PM, FQHC UDS, CAH Cost Reporting)
- 18 Discovery Questions (provider-operational, clinical, financial)
- 10 Objection Patterns (physician resistance, OR block politics, ED silos, telehealth failure PTSD, rural IT constraints, etc.)
- 3 Worked Examples (OR throughput, ED flow, clinic no-show with full calculations)
- 15 Buying Triggers (CMS CoP citations, Joint Commission conditional, ED diversion mandate, HACRP penalty, etc.)

### Overridden Components
| Component | Override Reason |
|-----------|-----------------|
| K009 ED Boarding Time benchmark range | Subpack narrows from 60-240 min to 60-180 min; adds sub-segment ranges for community (<45 min) vs AMC (<90 min) |
| Persona set | Adds 6 new operational personas with specialized KPI links and evidence preferences |
| Benchmark source weighting | Elevates AORN, OR Manager, Press Ganey, CMS Hospital Compare as primary sources |

---

## 3. Vertical Focus

- Hospitals / Health Systems
- Academic Medical Centers (AMCs)
- Ambulatory Care / Clinics
- Primary Care Networks
- Specialty Care (Cardiology, Oncology, Orthopedics, etc.)
- Urgent Care Chains
- Emergency Care / Trauma Centers
- Ambulatory Surgery Centers (ASCs)
- Behavioral Health (Inpatient / Outpatient / PHP / IOP)
- Home Health Agencies
- Hospice / Palliative Care
- Telehealth Platforms
- Rural Health Clinics (RHCs)
- Community Health Centers / FQHCs
- Critical Access Hospitals (CAHs)

---

## 4. Business Pains (20)

### PROV-P001: ED Boarding Time Exceeding 8 Hours
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** ED boarding > 8h average, LWBS > 4%, ambulance diversion > 50h/month, HCAHPS communication < 60th percentile, inpatient bed request-to-occupy > 4h
- **Segments:** Care Delivery (Providers)
- **Personas:** COO, CMO, Bed Manager, ED Director, CNO
- **KPIs:** PROV-K001, PROV-K002, PROV-K003
- **Sources:** ACEP Emergency Department Boarding Report 2024, CMS Hospital Compare 2024

### PROV-P002: OR First-Case Start Delay > 20%
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** First-case delay > 20%, OR utilization < 75%, PACU holds > 30 min, cancellation > 5%, block release < 48h
- **Segments:** Care Delivery (Providers)
- **Personas:** OR Director, COO, CNO, CFO
- **KPIs:** PROV-K004, PROV-K005, PROV-K006
- **Sources:** AORN Perioperative Standards 2024, OR Manager Data Survey 2024

### PROV-P003: Clinic No-Show Rate > 15%
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** No-show > 15%, provider utilization < 80%, overbooking > 1.3x, new patient wait > 21 days, reminder not automated
- **Segments:** Care Delivery (Providers)
- **Personas:** Patient Access Director, CMO, Nurse Manager, CFO
- **KPIs:** PROV-K007, PROV-K008, PROV-K009
- **Sources:** MGMA DataDive 2024, Press Ganey Ambulatory Benchmarks

### PROV-P004: ICU Step-Down Delay and Capacity Stranding
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** Step-down delay > 24h, ICU occupancy > 90%, ED ICU holds > 12h, ICU cost > $6,000/day, nurse ratio 1:3
- **Segments:** Care Delivery (Providers)
- **Personas:** Bed Manager, COO, CMO, CNO, CFO
- **KPIs:** PROV-K010, PROV-K011, PROV-K001
- **Sources:** Society of Critical Care Medicine 2024, Kaufman Hall ICU Benchmarks

### PROV-P005: Home Health 30-Day Unplanned Readmission > 18%
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** 30-day readmission > 18%, HHVBP score < 5, med rec < 80%, home safety < 60%, ED within 60 days > 25%
- **Segments:** Care Delivery (Providers)
- **Personas:** CMO, Population Health VP, Nurse Manager, CFO
- **KPIs:** PROV-K012, PROV-K013, PROV-K014
- **Sources:** CMS Home Health Compare 2024, CMS HHVBP Final Rule

### PROV-P006: Telehealth No-Show and Technical Failure > 20%
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** Telehealth no-show > 12%, technical difficulty > 8%, completion < 80%, provider satisfaction < 60%, denial > 5%
- **Segments:** Care Delivery (Providers)
- **Personas:** Telehealth Medical Director, CIO, CMIO, Patient Access Director, CFO
- **KPIs:** PROV-K015, PROV-K016, PROV-K017
- **Sources:** AMA Digital Health Research 2024, CMS Telehealth Claims Data

### PROV-P007: Critical Access Hospital Swing Bed Underutilization
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Symptoms:** Swing bed occupancy < 50%, SNF transfer > 40%, swing bed LOS < 10 days, Medicare bad debt, staffing not optimized
- **Segments:** Care Delivery (Providers)
- **Personas:** CFO, COO, CNO, Nurse Manager
- **KPIs:** PROV-K018, PROV-K019, PROV-K020
- **Sources:** Flex Monitoring Team CAH Reports 2024, CMS Cost Report Data

### PROV-P008: Ambulatory Surgery Center Case Mix and Reimbursement Compression
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** Revenue per case declining > 3% YoY, EBITDA < 15%, payer mix shift > 60% Medicare/Medicaid, supply cost > 22%, turnover > 20%
- **Segments:** Care Delivery (Providers)
- **Personas:** CFO, COO, OR Director, CMO
- **KPIs:** PROV-K021, PROV-K022, PROV-K023
- **Sources:** Ambulatory Surgery Center Association 2024, Medicare ASC Fee Schedule Final Rule

### PROV-P009: Hospice Average Length of Stay < 14 Days
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** Average LOS < 14 days, live discharge > 15%, referral-to-admission > 48h, physician certification delay > 24h, palliative consult < 10%
- **Segments:** Care Delivery (Providers)
- **Personas:** CMO, CFO, Population Health VP, Nurse Manager
- **KPIs:** PROV-K024, PROV-K025, PROV-K026
- **Sources:** NHPCO Facts and Figures 2024, MedPAC Hospice Report 2024

### PROV-P010: Behavioral Health ED Boarding > 48 Hours
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** Psychiatric ED boarding > 48h, inpatient psych holds > medical necessity, ED staff injury > baseline, EMTALA complaints, psych bed occupancy > 95%
- **Segments:** Care Delivery (Providers)
- **Personas:** CMO, COO, CNO, VP Behavioral Health, Bed Manager
- **KPIs:** PROV-K027, PROV-K028, PROV-K029
- **Sources:** ACEP Psychiatric Boarding Task Force 2024, Joint Commission Sentinel Event Database

### PROV-P011: FQHC / Community Health Center Productivity Gap
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** Visits per FTE < 3,500/year, sliding fee < 30%, UDS quality < 50th percentile, no-show > 18%, grant score < 75%
- **Segments:** Care Delivery (Providers)
- **Personas:** CEO, CMO, Patient Access Director, CFO
- **KPIs:** PROV-K030, PROV-K031, PROV-K032
- **Sources:** HRSA UDS 2024, National Association of Community Health Centers

### PROV-P012: Rural Hospital Emergency Department Closure Risk
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** ED volume declining > 5% YoY, operating margin < -5%, transport > 30 min to alternative, Medicare bad debt > 8%, CMS 96-hour rule gaps
- **Segments:** Care Delivery (Providers)
- **Personas:** CEO, CFO, COO, CMO
- **KPIs:** PROV-K033, PROV-K034, PROV-K035
- **Sources:** NC Rural Health Research Program 2024, Rural Hospital Closure Tracker

### PROV-P013: Sepsis Bundle Compliance < 80%
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** SEP-1 < 80%, sepsis mortality index > 1.0, antibiotics > 3h, lactate not within 3h, CMS HVBP penalty
- **Segments:** Care Delivery (Providers)
- **Personas:** CMO, CNO, Quality Director, Nurse Manager
- **KPIs:** PROV-K036, PROV-K037, PROV-K038
- **Sources:** CMS Hospital Compare SEP-1 2024, SCCM Surviving Sepsis Campaign

### PROV-P014: CAUTI / CLABSI Rate Above CMS National Average
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** CAUTI > national average, CLABSI > NHSN 50th percentile, HACRP bottom quartile, device ratio > 0.5, bundle < 90%
- **Segments:** Care Delivery (Providers)
- **Personas:** CNO, CMO, Quality Director, Nurse Manager, Infection Prevention Director
- **KPIs:** PROV-K039, PROV-K040, PROV-K041
- **Sources:** CDC NHSN 2024, CMS HACRP Final Rule

### PROV-P015: Patient Access Scheduling Backlog > 14 Days for New Patients
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** New patient wait > 14 days (PCP), > 21 days (specialty), same-day < 10%, ED for primary care > 15%, complaints > baseline
- **Segments:** Care Delivery (Providers)
- **Personas:** Patient Access Director, CMO, COO, CFO
- **KPIs:** PROV-K042, PROV-K043, PROV-K044
- **Sources:** MGMA DataDive 2024, Merritt Hawkins Physician Appointment Wait Times

### PROV-P016: Inpatient Pharmacy IV Compounding Safety and USP <800> Compliance
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** USP <797> gaps > 5, USP <800> gaps > 5, compounding error > 0.5%, cleanroom failures, hazardous drug spills > 0
- **Segments:** Care Delivery (Providers)
- **Personas:** Chief Pharmacy Officer, CMO, CNO, Compliance Officer
- **KPIs:** PROV-K045, PROV-K046, PROV-K047
- **Sources:** USP <797>/<800> Official Text, ASHP Sterile Compounding Survey 2024

### PROV-P017: Anesthesia Group Revenue Leakage and OR Billing Capture Gap
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Symptoms:** Anesthesia capture < 97%, ASA units below peer, concurrency errors > 2%, cancelled case capture < 80%, denial > 10%
- **Segments:** Care Delivery (Providers)
- **Personas:** OR Director, CFO, VP Revenue Cycle, CMO
- **KPIs:** PROV-K048, PROV-K049, PROV-K050
- **Sources:** MGMA Anesthesia Compensation Survey 2024, AANA OR Management Data

### PROV-P018: Post-Acute Care Network Fragmentation and SNF Quality Variability
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Symptoms:** SNF 30-day readmission > 20%, SNF ALOS > 25 days, Five-Star < 3 for > 40% of partners, transition info < 80% within 24h, network occupancy < 80%
- **Segments:** Care Delivery (Providers)
- **Personas:** CMO, COO, Population Health VP, Case Management Director
- **KPIs:** PROV-K051, PROV-K052, PROV-K053
- **Sources:** CMS SNF Compare 2024, MedPAC SNF Report 2024

### PROV-P019: Blood Product Waste and Transfusion Safety Compliance
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Symptoms:** C:T ratio > 2.0, discard > 3%, transfusion reaction > 0.5%, AABB gaps, type-and-screen hold > 72h
- **Segments:** Care Delivery (Providers)
- **Personas:** CMO, CNO, OR Director, Chief Pharmacy Officer
- **KPIs:** PROV-K054, PROV-K055, PROV-K056
- **Sources:** AABB Standards 2024, FDA Biologics Inspection Guide

### PROV-P020: Nurse Manager Span of Control and Burnout Cascade
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Symptoms:** Span > 60 FTEs, Nurse Manager turnover > 20%, unit RN turnover > 25%, HCAHPS nurse communication < 50th percentile, absenteeism > 6%
- **Segments:** Care Delivery (Providers)
- **Personas:** CNO, Nurse Manager, CHRO, CFO
- **KPIs:** PROV-K057, PROV-K058, PROV-K059
- **Sources:** AONE Nurse Manager Survey 2024, NSI Nursing Solutions 2024, Gallup Nurse Engagement Data

---

## 5. KPI Definitions (25)

| ID | Name | Formula | Unit | Typical Range | Benchmark |
|----|------|---------|------|---------------|-----------|
| PROV-K001 | ED Boarding Time (Decision-to-Admit to Physical Bed) | Sum of Minutes from Decision-to-Admit to Bed Transfer / Total ED Admissions | minutes | 60-480 | <60 (community); <90 (AMC); >180 (CMS CoP risk) |
| PROV-K002 | ED Left Without Being Seen (LWBS) Rate | (Left Without Being Seen / Total ED Arrivals) x 100 | % | 1-8 | <2% (best practice); >5% (access crisis) |
| PROV-K003 | ED Ambulance Diversion Hours per Month | Sum of Diversion Hours / Days in Month | hours/month | 0-200 | 0 (target); <20 (acceptable); >50 (significant) |
| PROV-K004 | OR First-Case On-Time Start % | (Started Within 15 Min of Schedule / Total First Cases) x 100 | % | 40-85 | >80% (best practice); <60% (significant delay) |
| PROV-K005 | OR Turnover Time (Wheels Out to Wheels In) | (Out + Ready to Next In) averaged per room | minutes | 25-75 | <30 (best practice); >50 (throughput risk) |
| PROV-K006 | OR Utilization (% of Scheduled Block Time) | (Scheduled Case Minutes / Block Minutes) x 100 | % | 65-90 | >80% (best practice); <70% (underutilization) |
| PROV-K007 | Clinic No-Show Rate | (Not Kept Without 24h Notice / Total Scheduled) x 100 | % | 5-25 | <8% (best practice); >15% (significant) |
| PROV-K008 | Clinic Cycle Time (Door-to-Door) | Sum of In-Room to Exit Times / Total Completed Visits | minutes | 30-90 | <45 (best practice); >75 (satisfaction risk) |
| PROV-K009 | Provider Productivity (wRVUs per FTE per Year) | Total wRVUs / Total Provider FTEs | wRVUs/FTE/year | 4,000-7,500 | >6,000 (primary care best practice) |
| PROV-K010 | ICU Step-Down Delay Time | Sum of Hours from Medical Readiness to Transfer / Total Transfers | hours | 2-48 | <6h (best practice); >24h (capacity stranding) |
| PROV-K011 | ICU Occupancy Rate | (ICU Patient Days / (Licensed Beds x Days)) x 100 | % | 70-95 | 78-85% (optimal); >90% (diversion risk) |
| PROV-K012 | Home Health 30-Day Unplanned Readmission Rate | (Unplanned Readmissions / Total Episodes) x 100 | % | 10-22 | <14% (best practice); >18% (HHVBP risk) |
| PROV-K013 | Home Health Episodic Cost per Episode | Total Cost / Total 60-Day Episodes | USD | 3,500-7,500 | Trend vs. self; < $5,000 (efficient) |
| PROV-K014 | Home Health Medication Reconciliation Completion Rate | (Completed Within 48h / Total Episodes) x 100 | % | 60-95 | >90% (best practice); <80% (readmission risk) |
| PROV-K015 | Telehealth Completion Rate | (Completed / Scheduled) x 100 | % | 70-92 | >85% (best practice); <75% (failure) |
| PROV-K016 | Telehealth Technical Difficulty Rate | (Visits with Platform Failure / Total Scheduled) x 100 | % | 2-15 | <3% (best practice); >8% (platform candidate) |
| PROV-K017 | Telehealth Provider Satisfaction Score | Average Usability Rating (1-5 scale) | score | 2.5-4.5 | >4.0 (adoptable); <3.0 (resistance risk) |
| PROV-K018 | Swing Bed Occupancy Rate | (Swing Bed Days / (Licensed Beds x Days)) x 100 | % | 30-80 | >65% (best practice); <50% (underutilization) |
| PROV-K019 | Swing Bed Average Length of Stay | Total Swing Bed Days / Total Discharges | days | 8-25 | 12-18 (optimal); <10 (early discharge risk) |
| PROV-K020 | Swing Bed Medicare Bad Debt Rate | (Unpaid Deductible + Coinsurance / Total Charges) x 100 | % | 3-12 | <5% (best practice); >8% (financial distress) |
| PROV-K021 | ASC Revenue per Case | Total Net Revenue / Total Cases | USD | 1,800-4,500 | Trend vs. self; > $2,500 (specialty avg) |
| PROV-K022 | ASC EBITDA Margin | (Revenue - OpEx) / Revenue x 100 | % | 8-28 | >18% (strong); <12% (distress) |
| PROV-K023 | ASC Supply Cost per Case | Total Supply Cost / Total Cases | USD | 280-750 | <20% of revenue (best practice) |
| PROV-K024 | Hospice Average Length of Stay | Total Hospice Days / Total Discharges | days | 12-75 | >60 (optimal); <14 (late referral) |
| PROV-K025 | Hospice Live Discharge Rate | (Live Discharges / Total Discharges) x 100 | % | 8-22 | <12% (best practice); >18% (quality gap) |

---

## 6. Value Drivers (20)

All value drivers map raw signal patterns to interpreted pains, value categories, KPIs, and personas. See JSON for complete detail. Representative drivers:

| ID | Signal Pattern | Interpreted Pain | Category | KPIs | Personas | Confidence |
|----|---------------|-----------------|----------|------|----------|------------|
| PROV-V001 | ED boarding > 120 min with LWBS > 3% | ED throughput crisis causing access delays and diversion | Revenue Uplift | K001, K002, K003 | COO, Bed Manager, ED Director | HIGH |
| PROV-V003 | OR first-case on-time < 60% with turnover > 50 min | Surgical services underutilization destroying margin | Revenue Uplift | K004, K005, K006 | OR Director, COO, CNO | HIGH |
| PROV-V005 | Clinic no-show > 15% with cycle time > 60 min | Access and scheduling failure destroying productivity | Revenue Uplift | K007, K008 | Patient Access Director, CMO | HIGH |
| PROV-V007 | ICU step-down delay > 18h with ED ICU holds > 8h | Critical care bottleneck causing throughput collapse | Cost Savings | K010, K011 | Bed Manager, COO, CNO | HIGH |
| PROV-V009 | Home health 30-day readmission > 16% with med rec < 75% | Post-acute transition failure driving HHVBP penalty | Revenue Uplift | K012, K014 | CMO, Population Health VP | HIGH |
| PROV-V011 | Telehealth completion < 78% with technical difficulty > 8% | Platform inadequacy destroying virtual care ROI | Cost Savings | K015, K016 | Telehealth Medical Director, CIO | HIGH |
| PROV-V013 | Swing bed occupancy < 50% with SNF transfer > 35% | Medicare swing bed revenue uncaptured | Revenue Uplift | K018, K019 | CFO, COO | MEDIUM |
| PROV-V015 | ASC revenue per case declining > 3% with supply > 22% | Reimbursement compression outpacing cost control | Cost Savings | K021, K022, K023 | CFO, OR Director | HIGH |
| PROV-V017 | Hospice LOS < 14 days with live discharge > 15% | Late referral destroying per-patient revenue | Revenue Uplift | K024, K025 | CMO, Population Health VP | HIGH |
| PROV-V019 | Psychiatric ED boarding > 24h with inpatient psych LOS > 12 days | Behavioral health capacity crisis | Risk Reduction | K027, K029 | COO, CMO, VP Behavioral Health | HIGH |

---

## 7. Value Formulas (12)

| ID | Name | Formula Expression | Output | Example |
|----|------|-------------------|--------|---------|
| PROV-F001 | ED Flow Optimization Value | (LWBS reduction x Volume x Revenue) + (Boarding reduction x Admissions x Cost/hr) | USD | $4.05M |
| PROV-F002 | OR Throughput Value | (Additional Cases x CM) + (Overtime reduction x Staff cost) | USD | $1.45M |
| PROV-F003 | Clinic No-Show Revenue Recovery | (No-show reduction x Visits x Revenue) + (Overbooking x Revenue) | USD | $2.66M |
| PROV-F004 | ICU Step-Down Value | (Delay hours avoided x ICU cost x Transfers/24) + (ED hold hours avoided x ED cost) | USD | $1.16M |
| PROV-F005 | Home Health Readmission Penalty Avoidance | (Excess readmissions avoided x Cost) + (HHVBP score improvement x Episodes x Bonus) | USD | $2.05M |
| PROV-F006 | Telehealth Program ROI | (Visits x Revenue) - Platform cost - Training - Support FTE | USD | $2.66M net |
| PROV-F007 | Swing Bed Revenue Capture | (Additional days x Medicare PPS per diem) - (Variable cost x Additional days) | USD | $756,000 |
| PROV-F008 | ASC Margin Improvement | (Revenue/case improvement x Cases) + (Supply reduction x Cases) - Implementation | USD | $1.29M |
| PROV-F009 | Hospice Revenue per Patient | (Target LOS - Current LOS) x Admissions x Per diem x (1 - Live discharge) | USD | $1.90M |
| PROV-F010 | Behavioral Health Boarding Cost Avoidance | (Boarding hours avoided x ED cost x Cases) + (Safety events avoided x Cost) | USD | $2.20M |
| PROV-F011 | Sepsis Bundle Value | (Compliance improvement x Cases x (Mortality reduction x Cost + VBP bonus)) | USD | $10.82M |
| PROV-F012 | FQHC Grant Performance | (UDS visit improvement x Grant revenue/visit) + Quality bonus + Sliding fee improvement | USD | $857,500 |

---

## 8. Benchmarks (18)

| ID | Name | Value | Range | Unit | Source | Segment | Confidence |
|----|------|-------|-------|------|--------|---------|------------|
| PROV-B001 | ED Boarding Time (Community) | 55 | 35-75 | min | CMS Hospital Compare 2024 | Community hospitals | HIGH |
| PROV-B002 | ED Boarding Time (AMC) | 85 | 60-120 | min | CMS Hospital Compare 2024 | AMCs / Tertiary | HIGH |
| PROV-B003 | ED LWBS Rate | 2.8 | 1.0-5.0 | % | Press Ganey 2024 | All hospitals | HIGH |
| PROV-B004 | OR First-Case On-Time Start | 76 | 60-90 | % | AORN 2024 | All hospitals/ASCs | HIGH |
| PROV-B005 | OR Turnover Time | 32 | 22-50 | min | OR Manager 2024 | All hospitals/ASCs | HIGH |
| PROV-B006 | OR Block Utilization | 78 | 65-90 | % | AORN 2024 | All hospitals/ASCs | HIGH |
| PROV-B007 | Clinic No-Show (Primary Care) | 11 | 5-18 | % | MGMA 2024 | All practices | HIGH |
| PROV-B008 | Clinic No-Show (Behavioral Health) | 22 | 12-35 | % | MGMA 2024 | All practices | HIGH |
| PROV-B009 | Clinic Cycle Time (PCP) | 42 | 30-65 | min | Press Ganey 2024 | All practices | HIGH |
| PROV-B010 | Provider wRVUs per FTE (PCP) | 6,200 | 4,500-7,500 | wRVUs | MGMA 2024 | All practices | HIGH |
| PROV-B011 | ICU Step-Down Delay | 8 | 3-18 | hours | SCCM / Kaufman Hall 2024 | All hospitals | HIGH |
| PROV-B012 | Home Health 30-Day Readmission | 15.2 | 10-22 | % | CMS Home Health Compare 2024 | All HH agencies | HIGH |
| PROV-B013 | Telehealth Completion Rate | 84 | 72-92 | % | AMA 2024 | All providers | MEDIUM |
| PROV-B014 | Swing Bed Occupancy (CAH) | 62 | 35-85 | % | Flex Monitoring Team 2024 | CAHs | MEDIUM |
| PROV-B015 | ASC EBITDA Margin | 19 | 10-28 | % | ASCA 2024 | All ASCs | HIGH |
| PROV-B016 | Hospice Average LOS | 55 | 18-95 | days | NHPCO 2024 | All hospices | HIGH |
| PROV-B017 | Psychiatric ED Boarding | 22 | 8-72 | hours | ACEP / SAMHSA 2024 | All hospitals | HIGH |
| PROV-B018 | FQHC Visits per FTE | 4,200 | 2,800-5,500 | visits | HRSA UDS 2024 | FQHCs/CHCs | HIGH |

---

## 9. Signal Interpretation Rules (20)

| ID | Signal Name | Raw Signal Pattern | Confidence | Linked Pains |
|----|------------|-------------------|------------|-------------|
| PROV-S001 | CMS CoP Survey Deficiency | CMS survey citation for hospital-wide CoP deficiency | 0.95 | P001, P004, P010 |
| PROV-S002 | Joint Commission Conditional | Sentinel event or conditional accreditation status | 0.94 | P001, P010, P014 |
| PROV-S003 | ED Diversion Frequency Spike | ED on diversion > 40 hours in 30 days | 0.91 | P001, P004 |
| PROV-S004 | OR Block Release Non-Utilization | Block release-to-fill < 50% with first-case delay > 25% | 0.89 | P002 |
| PROV-S005 | Clinic No-Show Surge | No-show rate increases > 5 pts over 90 days | 0.87 | P003 |
| PROV-S006 | ICU Census > 92% Sustained | ICU occupancy > 92% for > 5 days with ED holds > 8h | 0.90 | P004, P001 |
| PROV-S007 | Home Health Star Rating Decline | CMS HH Compare star rating < 3.0 | 0.88 | P005 |
| PROV-S008 | Telehealth Platform Change RFP | RFP for telehealth replacement with incumbent < 12 months | 0.85 | P006 |
| PROV-S009 | CAH Swing Bed Census < 40% | Swing bed < 40% for > 90 days with SNF transfers > 30% | 0.82 | P007 |
| PROV-S010 | ASC CON Challenge | State CON commission receives competing ASC application | 0.80 | P008 |
| PROV-S011 | Hospice Live Discharge Spike | Live discharge rate increases > 5 pts over 6 months | 0.86 | P009 |
| PROV-S012 | Behavioral Health ED Revisit Surge | BH ED revisit rate > 30% with psychiatric boarding > 36h | 0.92 | P010 |
| PROV-S013 | FQHC HRSA Site Visit | HRSA announces operational site visit with prior UDS gaps | 0.88 | P011 |
| PROV-S014 | Rural Hospital ED Closure | Rural hospital announces ED closure or 96-hour rule suspension | 0.93 | P012 |
| PROV-S015 | CMS SEP-1 Decline | SEP-1 compliance drops below 75th percentile or > 5 pts YoY | 0.89 | P013 |
| PROV-S016 | HACRP Bottom Quartile | CMS HACRP total score in bottom 25% with 1% penalty | 0.91 | P014 |
| PROV-S017 | New Patient Wait > 30 Days | Average new patient wait > 30 days for PCP | 0.85 | P015 |
| PROV-S018 | USP <797>/<800> Cleanroom Failure | Cleanroom certification failure with > 5 findings | 0.90 | P016 |
| PROV-S019 | Anesthesia Billing Audit Finding | External audit identifies capture rate < 95% | 0.87 | P017 |
| PROV-S020 | Nurse Manager Vacancy Crisis | Nurse Manager vacancy > 15% or span > 60 FTEs | 0.88 | P020 |

---

## 10. Persona Profiles (6 New)

### PROV-PER001: Chief Medical Information Officer (CMIO)
- **Seniority:** VP / SVP | **Influence:** Technical
- **Goals:** Optimize EHR usability, advance CDS, enable quality reporting, drive interoperability and AI validation
- **Pressures:** Physician EHR burnout, regulatory reporting burden, interoperability timelines, AI governance, informatics FTE shortage
- **Trusted Evidence:** AMA EHR usability studies, JAMIA peer-reviewed research, KLAS EHR satisfaction data, ONC metrics, internal EHR surveys
- **Disliked Claims:** EHR optimization without physician co-design; AI diagnosis without FDA clearance; interoperability promises without API specifics

### PROV-PER002: Nurse Manager
- **Seniority:** Manager | **Influence:** User
- **Goals:** Maintain safe staffing ratios, reduce turnover and call-outs, improve nursing-sensitive quality, achieve patient satisfaction targets
- **Pressures:** Span of control > 40 FTEs, floating/agency integration, mandatory overtime legislation, patient acuity escalation, workplace violence, Magnet redesignation
- **Trusted Evidence:** AONE Nurse Manager Competencies, NDNQI nursing-sensitive metrics, unit-level staffing data, Magnet appraisal feedback
- **Disliked Claims:** Technology replacing clinical judgment; staffing 'optimization' that means cuts; generic benchmarks without acuity adjustment

### PROV-PER003: Patient Access Director
- **Seniority:** Director / VP | **Influence:** Economic
- **Goals:** Minimize new patient wait times, reduce no-shows, maximize PA approval rates, ensure clean registration, optimize call center performance
- **Pressures:** No-show > 15%, PA turnaround > 72h, registration accuracy < 92%, high call abandonment, self-pay growth, No Surprises Act complexity
- **Trusted Evidence:** MGMA DataDive, Press Ganey access studies, HFMA MAP Keys, payer-specific authorization data, call center quality metrics
- **Disliked Claims:** Automation without exception handling; scheduling optimization without patient preference; self-service as replacement for human support

### PROV-PER004: Bed Manager
- **Seniority:** Manager / Director | **Influence:** Technical
- **Goals:** Maintain ED boarding < 60 min, minimize diversion, optimize unit occupancy, coordinate discharge timeliness, manage surge
- **Pressures:** ED boarding > 120 min, surgical holds > 4h, ICU step-down delays > 24h, weekend discharge resistance, data fragmentation
- **Trusted Evidence:** Kaufman Hall bed management benchmarks, SullivanCotter throughput data, CMS Hospital Compare ED metrics, internal dashboards
- **Disliked Claims:** Capacity solutions without discharge planning; ED boarding framed as ED problem alone; predictive models without real-time integration

### PROV-PER005: OR Director
- **Seniority:** Director | **Influence:** Technical
- **Goals:** Maximize block utilization and first-case starts, minimize turnover and PACU holds, reduce cancellations, optimize staffing, maintain surgeon satisfaction
- **Pressures:** First-case delay > 20%, block utilization < 70%, PACU holds > 30 min, instrument shortages, anesthesia contract negotiations, add-on volume > 15%
- **Trusted Evidence:** AORN perioperative data, OR Manager benchmarks, Press Ganey surgical services, surgeon satisfaction surveys, contribution margin by case
- **Disliked Claims:** OR optimization without surgeon block committee input; standardized scheduling ignoring case complexity; staffing cuts framed as efficiency

### PROV-PER006: Telehealth Medical Director
- **Seniority:** Director / VP | **Influence:** Technical
- **Goals:** Achieve > 85% completion rate, ensure reimbursement capture, maintain provider satisfaction, expand virtual care specialties, manage interstate licensure
- **Pressures:** Technical difficulty > 8%, reimbursement denials, provider resistance, licensure complexity, platform limitations, digital literacy gaps
- **Trusted Evidence:** AMA digital health research, CMS telehealth claims data, state telehealth parity laws, provider satisfaction surveys, platform SLA data
- **Disliked Claims:** Telehealth as replacement for in-person care; one platform fits all specialties; virtual care without reimbursement validation

---

## 11. Buying Triggers (15)

| ID | Trigger | Urgency | Typical Timing | Linked Pains |
|----|---------|---------|---------------|--------------|
| PROV-BT001 | CMS CoP Citation | CRITICAL | Immediate; 30-90 days | P001, P004, P010 |
| PROV-BT002 | Joint Commission Conditional or Preliminary Denial | CRITICAL | Immediate; 45-120 days | P001, P014, P010 |
| PROV-BT003 | ED Diversion Mandate from State EMS | HIGH | 30-60 days | P001 |
| PROV-BT004 | CMS HACRP Penalty Notification | HIGH | Annual; Q4 notification | P014 |
| PROV-BT005 | New OR Director from Outside | MEDIUM | Month 3-9 post-hire | P002 |
| PROV-BT006 | Anesthesia Group Contract Renewal | HIGH | 12-18 months before expiration | P002, P017 |
| PROV-BT007 | Telehealth Platform Contract Expiration | MEDIUM | 9-12 months before expiration | P006 |
| PROV-BT008 | Rural Hospital Distress Designation | CRITICAL | Immediate; 60-120 days | P012 |
| PROV-BT009 | Hospice CAP Exceedance Warning | HIGH | Q3-Q4 fiscal year | P009 |
| PROV-BT010 | Behavioral Health Boarding Class Action | CRITICAL | Immediate; 30-60 days | P010 |
| PROV-BT011 | FQHC HRSA Operational Site Visit Scheduled | HIGH | 60-90 days before visit | P011 |
| PROV-BT012 | ASC New CON Approval | MEDIUM | 90-180 days post-approval | P008 |
| PROV-BT013 | USP <797>/<800> Remediation Deadline | HIGH | 6-12 months before deadline | P016 |
| PROV-BT014 | New Patient Access Director Hired | MEDIUM | Month 3-8 post-hire | P003, P015 |
| PROV-BT015 | Nurse Manager Mass Exodus or Union Action | HIGH | Immediate; 30-60 days | P020 |

---

## 12. Technology Systems (15)

| ID | System | Category | Key Vendors | Integration Points |
|----|--------|----------|-------------|-------------------|
| PROV-T001 | EHR | Clinical | Epic, Oracle Health, MEDITECH, athenahealth | CPOE, Bed Mgmt, Nurse Call, PACS |
| PROV-T002 | CPOE | Clinical | Epic Beacon, Oracle PowerOrders | EHR, Pharmacy, LIS, RIS/PACS |
| PROV-T003 | RTLS | Operations | CenTrak, Versus, AiRISTA | Bed Mgmt, EHR, Nurse Call |
| PROV-T004 | Nurse Call | Clinical | Rauland, Hillrom/Vocera, Ascom | EHR, RTLS, Bed Mgmt |
| PROV-T005 | Bed Management | Operations | Epic, TeleTracking, Central Logic | EHR, ADT, RTLS, ED Tracking |
| PROV-T006 | RIS / PACS | Clinical | Philips, GE, Fuji, Sectra | EHR, CPOE, VNA, AI Diagnostics |
| PROV-T007 | AIMS | Clinical | Epic, Mediware, DocuMed | EHR, OR Scheduling, Billing |
| PROV-T008 | Surgical Scheduling / Block Mgmt | Operations | SurgiNet, Picis, iQueue, Optime | EHR, Bed Mgmt, AIMS, Supply Chain |
| PROV-T009 | ED Information System | Clinical | Epic ED, Cerner FirstNet, T-System | EHR, Bed Mgmt, ADT, Registration |
| PROV-T010 | Telehealth Platform | Care Delivery | Teladoc, Amwell, Epic Telehealth | EHR, Scheduling, Billing, Portal |
| PROV-T011 | Home Health / Hospice EMR | Clinical | Homecare Homebase, MatrixCare, WellSky | EHR, Billing, OASIS, EVV |
| PROV-T012 | Behavioral Health EHR | Clinical | Epic Wisdom, Netsmart, Qualifacts | EHR, State Reporting, Billing |
| PROV-T013 | ASC PM / EHR | Clinical | SurgiSource, HST Pathways, ModMed | EHR, Supply Chain, Billing |
| PROV-T014 | FQHC UDS Reporting | Analytics | Epic, eClinicalWorks, Greenway | EHR, PM, Grant Management |
| PROV-T015 | CAH Cost Reporting / Swing Bed | Financial | CostReportData.com, HRG, EPSi | EHR, GL, Patient Accounting |

---

## 13. Regulatory Factors (12)

| ID | Regulation | Applicability | Deadline | Penalty |
|----|-----------|--------------|----------|---------|
| PROV-REG001 | CMS Conditions of Participation (42 CFR 482) | Medicare/Medicaid hospitals | Ongoing; survey every 3-4 years | Termination from programs; CMP up to $100K |
| PROV-REG002 | Joint Commission Accreditation | Seeking/maintaining TJC accreditation | Triennial survey | Conditional accreditation; CMS deemed status loss |
| PROV-REG003 | HCAHPS / Hospital VBP | IPPS acute care hospitals | Annual FY; Oct 1 payment | Payment reduction up to 2% of DRG |
| PROV-REG004 | No Surprises Act (IDR) | Hospitals, ASCs, air ambulance | Jan 2022 ongoing | CMP up to $10,000 per violation |
| PROV-REG005 | EMTALA | Hospitals with dedicated EDs | Ongoing | CMP up to $119,942 per violation; exclusion |
| PROV-REG006 | State Certificate of Need (CON) | CON states (35 states) | Per project; 6-24 months | Project denial; revocation; fines up to $50K+ |
| PROV-REG007 | CMS HACRP | IPPS acute care hospitals | Annual FY; Oct 1 | 1% payment reduction on all DRGs |
| PROV-REG008 | USP <797> Sterile Compounding | All sterile compounding pharmacies | Nov 2023 ongoing | FDA warning letter; Board of Pharmacy action |
| PROV-REG009 | USP <800> Hazardous Drugs | All settings handling hazardous drugs | Nov 2023 ongoing | OSHA; Board of Pharmacy; worker comp claims |
| PROV-REG010 | CMS HHVBP | Medicare-certified home health agencies | Annual; Jan 1 payment | Payment reduction up to 5% (max 8%) |
| PROV-REG011 | HRSA 330 Grant Requirements | FQHCs receiving Section 330 funding | Annual UDS; triennial visit | Grant reduction or termination |
| PROV-REG012 | State Nurse Staffing Ratio Laws | Enacted states (CA, MA, OR, CT, IL, NY, NJ, WA) | Varies; 2024-2028 | $10K-$100K+ per violation; licensure action |

---

## 14. Competitor Factors (8)

| ID | Competitor Factor | Impact on Buying Behavior | Confidence |
|----|------------------|--------------------------|------------|
| PROV-CF001 | Epic Systems Dominance | Provider buyers prioritize Epic-certified solutions; integration barrier for non-Epic | HIGH |
| PROV-CF002 | Oracle Health (Cerner) Transition | Customers delaying investments until roadmap clarity; competitors targeting dissatisfied sites | HIGH |
| PROV-CF003 | Amazon One Medical / Clinic Entry | Accelerates digital front door and same-day access competition | HIGH |
| PROV-CF004 | CVS MinuteClinic / HealthHUB | Primary care and urgent care competitive pressure in suburban markets | HIGH |
| PROV-CF005 | UnitedHealth / Optum Care Vertical Integration | Independent providers seek technology to compete with integrated network data advantage | HIGH |
| PROV-CF006 | Private Equity ASC Chains | Consolidated platforms demand standardized, cloud-native, multi-site technology | HIGH |
| PROV-CF007 | Rural Hospital Closure and CON Relaxation | Remaining hospitals seek federal grant-funded technology; new entrants drive procurement | MEDIUM |
| PROV-CF008 | Specialty Telehealth Platforms | Health systems building owned telehealth; white-label platform demand rising | HIGH |

---

## 15. Discovery Questions (18)

| ID | Question | Target Personas | Linked Pains | Timing |
|----|----------|----------------|-------------|--------|
| PROV-DQ001 | Walk me through your ED patient flow. What is average boarding time, and where do delays accumulate? | Bed Manager, COO, ED Director | P001 | Early |
| PROV-DQ002 | What percentage of first surgical cases start within 15 minutes of schedule, and top three delay reasons? | OR Director, COO | P002 | Early |
| PROV-DQ003 | What is your clinic no-show rate by specialty, and what reminder interventions have you tested? | Patient Access Director, CMO | P003 | Early |
| PROV-DQ004 | How many hours do ICU patients remain after medical readiness for step-down, and what prevents transfer? | Bed Manager, CMO, CNO | P004 | Middle |
| PROV-DQ005 | What is your home health 30-day readmission rate, and HHVBP performance threshold comparison? | CMO, Population Health VP | P005 | Early |
| PROV-DQ006 | What is your telehealth completion rate, and failed encounter breakdown (technical vs no-show)? | Telehealth Medical Director, CIO | P006 | Early |
| PROV-DQ007 | How many swing bed days utilized vs. licensed capacity, and SNF transfer rate for eligible patients? | CFO, COO, Nurse Manager | P007 | Middle |
| PROV-DQ008 | What is your ASC EBITDA margin, and revenue per case trend over three years? | CFO, OR Director | P008 | Early |
| PROV-DQ009 | What is your hospice average LOS, and percentage of live discharges within 7 days of admission? | CMO, Population Health VP | P009 | Middle |
| PROV-DQ010 | How long do psychiatric patients board in ED, and current inpatient psych bed capacity vs. community need? | CMO, COO, VP Behavioral Health | P010 | Early |
| PROV-DQ011 | What is provider visit productivity per FTE, and HRSA UDS benchmark comparison? | CEO, CMO, Patient Access Director | P011 | Middle |
| PROV-DQ012 | If your ED closed or reduced hours, what is EMS transport time to the next nearest facility? | CEO, CFO, COO | P012 | Middle |
| PROV-DQ013 | What is your current SEP-1 bundle compliance rate, and sepsis antibiotic administration timeline? | CMO, Quality Director, Nurse Manager | P013 | Early |
| PROV-DQ014 | How do CAUTI and CLABSI rates compare to NHSN national benchmarks, and device utilization ratio? | CNO, Quality Director, Infection Prevention Director | P014 | Early |
| PROV-DQ015 | What is new patient appointment wait time for primary care and top three specialties? | Patient Access Director, CMO | P015 | Early |
| PROV-DQ016 | When was last USP <797> and <800> gap assessment, and what remediation items remain open? | Chief Pharmacy Officer, Compliance Officer | P016 | Middle |
| PROV-DQ017 | What is anesthesia billing capture rate, and ASA units per case vs. national benchmarks? | OR Director, CFO, VP Revenue Cycle | P017 | Middle |
| PROV-DQ018 | What is Nurse Manager span of control, vacancy rate, and unit turnover in highest-turnover units? | CNO, Nurse Manager, CHRO | P020 | Early |

---

## 16. Objection Patterns (10)

| ID | Objection | Common From | Underlying Concern | Reframe Strategy |
|----|-----------|-------------|-------------------|-----------------|
| PROV-OBJ001 | Physicians already overwhelmed with EHR documentation | CMIO, CMO, Nurse Manager | New tech adds clicks and burnout | Position as click-reduction and voice AI; demonstrate EHR-integrated workflow |
| PROV-OBJ002 | Can't change surgical block schedule—surgeons own blocks | OR Director, CMO | Surgeon political power and resistance | Frame as surgeon productivity enablement; use surgeon-specific utilization data; auto-release-to-fill |
| PROV-OBJ003 | ED boarding is inpatient bed problem, not ED problem | Bed Manager, COO, CMO | Silo mentality preventing accountability | Agree; position as enterprise throughput platform spanning ED, bed management, discharge, post-acute |
| PROV-OBJ004 | Tried telehealth before and adoption failed | Telehealth Medical Director, CIO | Post-traumatic failure from prior platform | Diagnose root cause; differentiate on provider-native design and reimbursement guarantee; phased pilot |
| PROV-OBJ005 | Rural hospitals don't have IT infrastructure for analytics | CFO, CIO | Bandwidth, staffing, budget constraints | Offer cloud-native lightweight deployment; reference CAH success stories; Medicare revenue protection framing |
| PROV-OBJ006 | Home health nurses in field can't use complex software | CMO, Nurse Manager | Mobile usability and connectivity gaps | Demonstrate offline-capable mobile app with voice-first documentation; home health-specific workflow |
| PROV-OBJ007 | Behavioral health is different—can't apply standard workflows | VP Behavioral Health, CMO | BH stigma, involuntary hold complexity | Reference BH-specific modules; demonstrate state hold form integration and 42 CFR Part 2 compliance |
| PROV-OBJ008 | Must get through EHR upgrade before anything new | CIO, CMIO | Sequential preference and change fatigue | Map mutual reinforcement; offer parallel track; reference EHR-integrated deployment |
| PROV-OBJ009 | FQHC grant funding is fixed—can't afford new technology | CEO, CFO | Perceived capital requirement without flexibility | Position as HRSA-approved health IT investment; demonstrate UDS visit productivity improvement |
| PROV-OBJ010 | ASC and hospital systems don't talk—data too fragmented | CIO, OR Director | Integration complexity and silos | Offer FHIR-based integration layer; demonstrate ASC-specific interoperability with major EHRs |

---

## 17. Worked Examples (3)

### PROV-WE001: OR Throughput Optimization — 8-OR Community Hospital

**Scenario:** Community hospital with 8 ORs experiencing first-case delay rate of 28%, turnover time averaging 55 minutes, and block utilization of 68%. Annual surgical volume 4,200 cases with contribution margin of $2,400 per case.

**Inputs:**
- Current first-case delay rate: 28%
- Target first-case delay rate: 12%
- Current turnover: 55 min
- Target turnover: 32 min
- Current block utilization: 68%
- Target block utilization: 82%
- Annual cases: 4,200
- Contribution margin per case: $2,400
- OR minutes per day: 480
- Operating days per year: 250
- Cost per OR minute: $65

**Formula Applied:** PROV-F002 (OR Throughput Value)

**Calculation:**
1. Additional cases from block utilization improvement: (0.82 - 0.68) x 8 x 480 x 250 / 120 = 1,120 additional cases/year
2. Revenue from additional cases: 1,120 x $2,400 = $2.69M
3. Overtime reduction: 23 min saved x 4,200 / 60 = 1,610 hours x $65 = $104,650
4. **Total annual value = $2.69M + $105K = $2.80M**

**Confidence:** MEDIUM. HIGH with actual hospital-specific contribution margin and case time data.

---

### PROV-WE002: ED Flow Optimization — 35,000-Visit Community Hospital ED

**Scenario:** Community hospital ED with 35,000 annual visits, 5.2% LWBS rate, 145-minute average boarding time, 18,000 annual admissions. Average ED visit revenue $425; inpatient hold cost $185/hour.

**Inputs:**
- Annual ED visits: 35,000
- Current LWBS rate: 5.2%
- Target LWBS rate: 2.5%
- Avg revenue per ED visit: $425
- Current boarding minutes: 145
- Target boarding minutes: 55
- Annual ED admissions: 18,000
- Inpatient hold cost per hour: $185

**Formula Applied:** PROV-F001 (ED Flow Optimization Value)

**Calculation:**
1. LWBS revenue recovery: (5.2% - 2.5%) x 35,000 x $425 = $401,625
2. Boarding time reduction: (145 - 55) min x 18,000 / 60 x $185 = 27,000 hours x $185 = $4.995M
3. **Total annual value = $401,625 + $4,995,000 = $5.40M**

**Confidence:** MEDIUM. Requires validation with actual hospital capacity constraint and admission demand data.

---

### PROV-WE003: Clinic No-Show Reduction — Multi-Specialty Group (120 Providers)

**Scenario:** Multi-specialty group with 120 providers, 180,000 annual scheduled visits, 16% no-show rate, $195 average revenue per visit. Behavioral health no-show rate 24%. Current reminder system is manual phone calls only.

**Inputs:**
- Annual scheduled visits: 180,000
- Current no-show rate: 16%
- Target no-show rate: 8%
- Avg revenue per visit: $195
- Overbooking optimization visits: 3,600
- Implementation cost: $120,000

**Formula Applied:** PROV-F003 (Clinic No-Show Revenue Recovery)

**Calculation:**
1. No-show reduction value: (16% - 8%) x 180,000 x $195 = $2.808M
2. Overbooking optimization: 3,600 x $195 = $702,000
3. Gross value: $2.808M + $702K = $3.51M
4. **Net annual value after implementation: $3.51M - $120K = $3.39M**

**Confidence:** HIGH. No-show reduction from 16% to 8% is well-documented outcome of automated multi-channel reminders.

---

## 18. Evidence Sources (8)

| ID | Source | Reliability | Accessibility | Lag | Applicable For |
|----|--------|-------------|--------------|-----|---------------|
| PROV-ES001 | CMS Hospital Compare / Care Compare | HIGH | Public | 6-12 months | ED boarding, HCAHPS, readmissions, HACRP, SEP-1 |
| PROV-ES002 | AORN / OR Manager Perioperative Data | HIGH | Member/Subscription | Annual | OR utilization, first-case starts, turnover, staffing |
| PROV-ES003 | MGMA DataDive / AMGA Survey | HIGH | Member/Purchase | Annual | Provider productivity, no-show rates, revenue per visit |
| PROV-ES004 | Press Ganey National Database | HIGH | Subscription/Client | Quarterly | Patient satisfaction, ED, ambulatory, surgical services |
| PROV-ES005 | CMS Home Health / Hospice Compare | HIGH | Public | Quarterly | Home health quality, hospice quality, HHVBP |
| PROV-ES006 | HRSA UDS (Uniform Data System) | HIGH | Public | Annual | FQHC productivity, quality, visit volume, grant performance |
| PROV-ES007 | Flex Monitoring Team / Rural Health Research | HIGH | Public | Annual | CAH financials, swing bed, rural ED viability |
| PROV-ES008 | State EMS / Health Department Diversion Logs | HIGH | Public/FOI | Real-time to monthly | ED diversion frequency, EMS routing, rural access gaps |

---

## 19. Governance

| Attribute | Value |
|-----------|-------|
| Source Coverage | Mixed (public filings, government data, industry surveys, proprietary benchmarks) |
| Confidence Level | High |
| Last Updated | 2026-04-25 |
| Approved for Customer-Facing Output | No (internal intelligence asset; requires review before external use) |
| Review Owner | healthcare-providers-subpack-architect |
| Agent Swarm ID | kimi-k2.6-swarm-healthcare-providers-s3.1 |
| Parent Master Swarm ID | kimi-k2.6-swarm-healthcare-m3 |
| Version | 1.0.0 |

### Confidence Flags Used
- **HIGH:** Multiple corroborating sources, quantified data, direct regulatory or financial reporting
- **MEDIUM:** Industry survey data, partial quantification, or single-source but authoritative
- **LOW:** Estimates, directional indicators, or emerging trends with limited data

### Validation Required Before Customer Use
1. Verify OR benchmarks against latest AORN and OR Manager publications
2. Confirm ED boarding benchmarks against CMS Hospital Compare and ACEP data
3. Validate clinic no-show benchmarks against MGMA DataDive specialty breakouts
4. Update state-specific regulatory deadlines (staffing ratios, CON, USP <797>/<800>)
5. Validate organization-specific financial metrics before citing in proposals
6. Review signal rules for false positive rate against historical conversion data
7. Update competitor landscape quarterly (M&A, market exits, new entrants)

---

*End of Providers / Care Delivery ValuePack (S3.1)*
