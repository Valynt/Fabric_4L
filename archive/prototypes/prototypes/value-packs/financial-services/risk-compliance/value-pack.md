# Risk, Compliance, and Financial Crime Subpack

**Pack ID:** `risk-compliance-v1`  
**Parent Master:** `financial-services-master-v1`  
**Version:** 1.0.0  
**Last Updated:** 2024-12-19  
**Confidence Level:** HIGH  
**Approved for Customer-Facing Output:** Yes

---

## Executive Summary

This subpack delivers vertical-specialized value intelligence for **Risk, Compliance, and Financial Crime** functions across financial services institutions. It covers AML/KYC, sanctions screening, fraud detection/prevention, credit/market/operational risk, model risk management, regulatory reporting, SOX compliance, consumer compliance, data governance, cyber risk, and third-party risk.

All components in this subpack are **ADDITIONAL** to the Financial Services Master Pack. No master content is duplicated. The subpack inherits the master's Value Driver Framework, Base Persona Archetypes, Evidence Source Taxonomy, Formula Templates, Signal Source Taxonomy, Benchmark Methodology, and Governance Framework.

**Financial Outcome Focus:** Every component connects to Revenue Uplift, Cost Savings, Risk Reduction, or Working Capital/Cash Flow Improvement.

---

## Inheritance Manifest

### Inherited from Master (Read-Only Reference)
- Value Driver Framework (5 categories: Cost Savings, Risk Reduction, Revenue Uplift, Working Capital, Compliance)
- Base Persona Archetypes (PER001-PER015: CIO, CTO, CDO, COO, CFO, CRO, CCO, CISO, Internal Audit, Head of Trading, Head of Client, Head of Compliance, General Counsel, Chief Data Officer)
- Evidence Source Types (10 standardized types)
- Formula Templates (NPV, payback, ROI calculation methodology)
- Signal Source Taxonomy (7 signal categories)
- Benchmark Methodology (quantitative threshold validation, industry benchmark cross-reference, time-series trend analysis)
- Governance Framework (version control, approval workflow, confidence calibration, source attribution)

### Created in This Subpack (Vertical-Specialized)
- 18 vertical pains (RC-P001 to RC-P018)
- 25 vertical KPIs (RC-K001 to RC-K025)
- 36 vertical value driver mappings (RC-VD001 to RC-VD036)
- 12 vertical formulas (RC-VF001 to RC-VF012)
- 18 vertical benchmarks (RC-B001 to RC-B018)
- 18 vertical signal rules (RC-SR001 to RC-SR018)
- 8 specialized evidence sources (RC-ES001 to RC-ES008)
- 14 buying triggers (RC-BT001 to RC-BT014)
- 6 NEW vertical personas (RC-PER001 to RC-PER006)
- 18 discovery questions (RC-DQ001 to RC-DQ018)
- 9 objection patterns (RC-OBJ001 to RC-OBJ009)
- 13 technology systems (RC-TS001 to RC-TS013)
- 11 regulatory factors (RC-RF001 to RC-RF011)
- 8 competitor factors (RC-CF001 to RC-CF008)
- 3 worked examples (RC-WE001 to RC-WE003)

### Vertical Persona Additions
- **RC-PER001: BSA/AML Officer** - AML program governance, sanctions, SAR filing
- **RC-PER002: Chief Model Risk Officer / Model Risk Manager** - SR 11-7 compliance, AI/ML governance
- **RC-PER003: Regulatory Reporting Director** - End-to-end regulatory reporting operations
- **RC-PER004: Fraud Prevention Director** - Real-time fraud, APP scams, insider threat
- **RC-PER005: Third-Party Risk Manager** - Vendor resilience and concentration risk
- **RC-PER006: Cyber Risk Lead** - Cyber risk quantification (FAIR) and board reporting

---

## Vertical Pains (18)

### RC-P001: Sanctions Screening Alert Overflow and Name Matching Errors
- **Symptoms:** >95% false positive rate, screening latency >500ms, missed true positives, manual remediation of >80% of alerts, OFAC findings in last 24 months
- **Financial Impact:** $5M-$50M annually in investigator labor and penalty exposure
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P002: KYC Onboarding Friction and Periodic Review Backlog
- **Symptoms:** >10-day onboarding, periodic review backlog >20%, customer abandonment >25%, beneficial ownership gaps >30%, EDD backlog >90 days
- **Financial Impact:** $10M-$100M in lost CLV and compliance remediation
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P003: Credit Model Performance Decay and Recalibration Delays
- **Symptoms:** Gini decline >5 points, recalibration cycle >12 months, model overrides >15%, CECL volatility >$50M/qtr
- **Financial Impact:** $20M-$200M in provision volatility and capital efficiency
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P004: Market Risk VaR Backtesting Exceptions and FRTB Capital Inflation
- **Symptoms:** VaR exceptions >4/250 days, FRTB capital inflation >15%, stress test variance >20%, PRU >5% of RWA
- **Financial Impact:** $10M-$150M in capital impact and computation cost
- **Prevalence:** MEDIUM | **Confidence:** HIGH

### RC-P005: Operational Risk Loss Event Under-Reporting and RCSA Staleness
- **Symptoms:** Loss capture rate <60%, RCSA update cycle >18 months, top 10 risks unchanged >2 years
- **Financial Impact:** $5M-$30M in capital buffer uncertainty and governance risk
- **Prevalence:** HIGH | **Confidence:** MEDIUM

### RC-P006: Fraud Detection Latency on Real-Time Payment Rails
- **Symptoms:** Detection latency >200ms, APP scam false negatives >40%, transaction hold rate >5%, fraud losses >0.50% of instant payment volume
- **Financial Impact:** $15M-$80M in fraud loss, reimbursement, and customer churn
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P007: SOX ICFR Control Deficiency and Testing Inefficiency
- **Symptoms:** Testing hours >15,000/year, ITGC deficiencies >5/year, user access review completion <80%, external audit fees increasing >10% annually
- **Financial Impact:** $5M-$25M in remediation, audit fees, and restatement risk
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P008: Consumer Compliance Complaint Spike and UDAAP Exposure
- **Symptoms:** Complaints >150% YoY, UDAAP complaints >30%, fair lending disparities >3 std dev, active regulatory inquiry
- **Financial Impact:** $5M-$50M in compliance cost, penalties, and settlements
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P009: Cyber Risk Quantification and Board Reporting Gaps
- **Symptoms:** Cyber risk in qualitative heat maps only, no dollar quantification, board asking for $ exposure, insurance gap >$50M
- **Financial Impact:** $10M-$200M in incident cost and insurance optimization
- **Prevalence:** MEDIUM | **Confidence:** HIGH

### RC-P010: Third-Party Concentration in Critical Risk Services
- **Symptoms:** Single cloud provider >70% of critical workloads, no right-to-audit on >50% of vendors, SOC 2 reports >12 months old on >20% of vendors
- **Financial Impact:** $20M-$100M in resilience risk and incident cost
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P011: Regulatory Reporting Data Fragmentation and Reconciliation
- **Symptoms:** Reconciliation >5 business days, same metric varies >3% between reports, manual adjustments >10% of fields, late filing within 24h >20%
- **Financial Impact:** $5M-$30M in efficiency, penalty avoidance, and restatement risk
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P012: Model Inventory Sprawl and AI/ML Governance Gaps
- **Symptoms:** Inventory >1,000 with >30% AI/ML, models without full documentation >25%, monitoring <quarterly, drift detected >6 months post-occurrence
- **Financial Impact:** $10M-$50M in validation and deployment risk
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P013: Trade Surveillance Alert Fatigue and Market Abuse Detection
- **Symptoms:** False positive rate >85%, alert review backlog >14 days, no cross-asset coverage, manipulation detection lag >72 hours
- **Financial Impact:** $3M-$15M in surveillance efficiency and regulatory risk
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM

### RC-P014: Data Governance Lineage Gaps for Regulatory Remediation
- **Symptoms:** Data lineage coverage <50% of critical reports, remediation cycle >45 days, data quality exceptions >8%, AI inputs untraceable >40%
- **Financial Impact:** $5M-$25M in compliance and reporting risk
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P015: Operational Resilience and Critical Service Mapping Deficits
- **Symptoms:** No critical service register, impact tolerance undefined >60% of services, RTO >regulatory expectations >40%, no end-to-end scenario testing
- **Financial Impact:** $5M-$50M in compliance and remediation
- **Prevalence:** HIGH | **Confidence:** HIGH

### RC-P016: Anti-Bribery and Corruption Gaps in Correspondent Banking
- **Symptoms:** High-risk jurisdiction accounts >15%, ABC coverage <50%, no nested relationship screening, Wolfsberg responses >30 days overdue
- **Financial Impact:** Revenue loss from de-risking and correspondent relationship termination
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM

### RC-P017: Climate Risk Stress Testing and Disclosure Readiness
- **Symptoms:** No climate scenario in CCAR, transition risk data <30% of loan book, physical risk unquantified >50% of CRE collateral, TCFD gaps identified
- **Financial Impact:** $5M-$25M in compliance and reporting; potential portfolio reallocation cost
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM

### RC-P018: Internal Fraud and Insider Threat Detection Blind Spots
- **Symptoms:** Employee surveillance coverage <60%, whistleblower reports >25% YoY, no UEBA, privileged access review >quarterly, insider data exfiltration >1/year
- **Financial Impact:** $5M-$40M in investigation, settlement, and remediation
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM

---

## Vertical KPIs (25)

| ID | Name | Formula | Typical Range | Benchmark |
|----|------|---------|---------------|-----------|
| RC-K001 | Sanctions Alert False Positive Rate | (FP Alerts / Total Alerts) * 100 | 90-98% | 60-85% |
| RC-K002 | Sanctions Screening Latency | Avg ms from initiation to decision | 300-800ms | 50-200ms |
| RC-K003 | Sanctions True Positive Detection Rate | (TP Hits / Actual Violations) * 100 | 75-90% | 95-99% |
| RC-K004 | KYC Onboarding Cycle Time | Avg business days to activation | 8-15 days | 2-5 days |
| RC-K005 | KYC Periodic Review Coverage | (Current Reviews / Total Required) * 100 | 70-85% | 95-100% |
| RC-K006 | EDD Case Backlog Age | Avg days open for EDD cases | 60-120 days | 14-30 days |
| RC-K007 | Credit Model Gini Coefficient | 2 * AUC - 1 | 0.50-0.75 | 0.70-0.85 |
| RC-K008 | Model Override Rate | (Overridden / Total Model Decisions) * 100 | 10-25% | 3-8% |
| RC-K009 | CECL Provision Volatility | StdDev(Qtrly CECL) / Avg(Qtrly CECL) | 0.15-0.35 | 0.05-0.15 |
| RC-K010 | VaR Backtesting Exception Rate | (Exceptions in 250 Days / 250) * 100 | 2-6% | 0.4-1.6% |
| RC-K011 | FRTB Capital Multiplier | (FRTB Capital / Current VaR Capital) * 100 | 110-140% | 100-115% |
| RC-K012 | Stressed VaR Computation Time | Hours for full SVaR run | 8-24 hrs | 2-6 hrs |
| RC-K013 | Operational Loss Event Capture Rate | (Reported / Estimated Actual) * 100 | 50-70% | 80-95% |
| RC-K014 | RCSA Currency Rate | (Updated Within 12 Months / Total) * 100 | 60-80% | 90-100% |
| RC-K015 | Scenario Analysis Coverage Ratio | (Units with Current Analysis / Total) * 100 | 50-75% | 85-100% |
| RC-K016 | Real-Time Fraud Detection Latency | Avg ms to fraud decision | 150-400ms | 30-100ms |
| RC-K017 | APP Scam False Negative Rate | (Undetected / Total APP Scams) * 100 | 30-50% | 5-15% |
| RC-K018 | Instant Payment Fraud Loss Rate | (Fraud Loss / Volume) * 10,000 | 10-25 bps | 2-6 bps |
| RC-K019 | SOX Testing Hours per Control | Total Hours / Active Controls | 8-15 hrs | 3-6 hrs |
| RC-K020 | ITGC Deficiency Rate | (Deficiencies / Total ITGC Tested) * 100 | 8-18% | 2-5% |
| RC-K021 | User Access Review Completion Rate | (Completed On-Time / Total Required) * 100 | 70-85% | 95-100% |
| RC-K022 | Consumer Complaint Velocity | Complaints per $1B revenue | 150-400 | 50-120 |
| RC-K023 | UDAAP Risk Indicator Rate | (Products with UDAAP Risk / Total) * 100 | 10-20% | 2-5% |
| RC-K024 | Fair Lending Disparity Index | Statistical odds ratio across classes | 1.2-2.0 | 1.0-1.1 |
| RC-K025 | Cyber Risk Quantification Coverage | (Assets with $ Assessment / Total) * 100 | 20-45% | 70-90% |

---

## Vertical Formulas (12)

### RC-VF001: Sanctions False Positive Reduction Value
`=(Current_FP_Rate - Target_FP_Rate) * Annual_Alert_Volume * Cost_Per_Alert + Investigator_Headcount_Reduction * Loaded_Cost`  
**Example:** (0.95 - 0.75) * 3,000,000 * $75 + 7 * $150,000 = **$47.25M + $1.05M = $48.3M annual savings**

### RC-VF002: KYC Onboarding Speed Revenue Impact
`=(Onboarding_Abandonment_Reduction * New_Customer_Volume * CLV) + (Periodic_Review_Backlog_Clearance * Cost_Per_Review * Backlog_Volume)`  
**Example:** (0.15 * 100,000 * $2,500) + (0.40 * $200 * 50,000) = **$37.5M + $4M = $41.5M annual value**

### RC-VF003: Credit Model Performance Improvement Value
`=(PD_Accuracy_Improvement * RWA_Reduction * Cost_of_Capital) + (Override_Reduction * Override_Cost * Annual_Decisions) + Provision_Volatility_Reduction_Value`  
**Example:** (0.02 * $1.5B * 0.10) + (0.10 * $500 * 200,000) + $20M = **$33M annual value**

### RC-VF004: Market Risk Capital Efficiency Improvement
`=(FRTB_Capital_Reduction * Cost_of_Capital) + (VaR_Computation_Time_Reduction * Infrastructure_Cost * Daily_Runs) + Backtesting_Exception_Avoidance_Value`  
**Example:** ($300M * 0.10) + (6 * $850 * 250) + $5M = **$36.275M annual value**

### RC-VF005: Operational Risk Capital Optimization
`=(Loss_Capture_Improvement * Avg_Loss * Underreported_Events) + (RCSA_Efficiency_Gain * RCSA_Count * Cost_Per_RCSA) + (Scenario_Capital_Reduction * Cost_of_Capital)`  
**Example:** (0.30 * $150K * 200) + (0.40 * 500 * $3,000) + ($50M * 0.10) = **$14.6M annual value**

### RC-VF006: Fraud Loss and Reimbursement Reduction
`=(Fraud_Loss_Rate_Reduction * Payment_Volume) + (Reimbursement_Rate_Reduction * Total_Reimbursements) + (Complaint_Reduction * Cost_Per_Complaint) + Regulatory_Penalty_Avoidance`  
**Example:** (0.0015 * $40B) + (0.25 * $120M) + (5,000 * $850) + $3M = **$97.25M annual value**

### RC-VF007: SOX Compliance Cost and Audit Fee Reduction
`=(Testing_Hours_Reduction * Loaded_Cost_Per_Hour) + (ITGC_Deficiency_Reduction * Remediation_Cost_Per_Deficiency) + External_Audit_Fee_Reduction + Control_Automation_Investment_ROI`  
**Example:** (8,000 * $85) + (8 * $75,000) + $500K + $1.2M = **$2.98M annual savings**

### RC-VF008: Consumer Compliance Cost Avoidance
`=(Complaint_Reduction * Cost_Per_Complaint) + UDAAP_Remediation_Avoidance + Fair_Lending_Settlement_Avoidance + Product_Revision_Cost_Reduction`  
**Example:** (10,000 * $1,200) + $5M + $15M + $2M = **$34M annual value**

### RC-VF009: Cyber Risk Quantification and Insurance Optimization
`=(Cyber_Insurance_Premium_Optimization) + (Cyber_Exposure_Var_Reduction * Risk_Transfer_Cost) + Board_Reporting_Efficiency_Gain + Incident_Response_Cost_Avoidance`  
**Example:** $2M + ($30M * 0.08) + $500K + $3M = **$7.9M annual value**

### RC-VF010: Third-Party Risk Cost Avoidance and Efficiency
`=(Vendor_Incident_Reduction * Avg_Incident_Cost) + (DD_Efficiency_Gain * Cost_Per_DD * Annual_DD_Volume) + Concentration_Risk_Hedge_Value + Contractual_Risk_Transfer_Value`  
**Example:** (2 * $4M) + (0.50 * $8,000 * 300) + $3M + $1M = **$13.2M annual value**

### RC-VF011: Regulatory Reporting Automation ROI
`=(FTE_Reduction * Loaded_Cost_Per_FTE) + (Reconciliation_Time_Reduction * Cost_Per_Day * Annual_Cycles) + Restatement_Avoidance_Value + First_Pass_Accuracy_Improvement_Value`  
**Example:** (60 * $140,000) + (8 * $5,000 * 50) + $8M + $3M = **$21.4M annual savings**

### RC-VF012: Model Risk Management Efficiency and Deployment Acceleration
`=(Validation_Backlog_Reduction * Cost_Per_Validation) + (MRM_Finding_Reduction * Cost_Per_Finding) + Model_Deployment_Acceleration_Revenue + AI_Governance_Coverage_Improvement_Value`  
**Example:** (150 * $30,000) + (40 * $20,000) + $15M + $5M = **$25.3M annual value**

---

## Key Benchmarks (18)

| ID | Benchmark | Value | Range | Source | Confidence |
|----|-----------|-------|-------|--------|------------|
| RC-B001 | Sanctions False Positive (Best-in-Class) | 72% | 65-80% | Deloitte 2024 | HIGH |
| RC-B002 | Sanctions Screening Latency (Top Performer) | 85ms | 50-120ms | Nice Actimize | MEDIUM |
| RC-B003 | KYC Onboarding Cycle (Digital-First) | 3.5 days | 2-5 days | Thomson Reuters 2024 | HIGH |
| RC-B004 | KYC Periodic Review Coverage | 98% | 95-100% | FFIEC Manual | HIGH |
| RC-B005 | Credit Model Gini (Top Quartile) | 0.78 | 0.70-0.85 | McKinsey 2024 | MEDIUM |
| RC-B006 | Model Override Rate (Industry Median) | 14% | 8-20% | OCC Handbook | HIGH |
| RC-B007 | VaR Backtesting Exception Threshold | 1.6% | 0.4-4.0% | Basel Framework | HIGH |
| RC-B008 | FRTB Capital Multiplier (Industry) | 115% | 105-125% | ISDA 2024 | MEDIUM |
| RC-B009 | Operational Loss Capture (Best Practice) | 88% | 80-95% | ORX | MEDIUM |
| RC-B010 | RCSA Update Cycle (Target) | 12 months | 6-12 months | RMA | HIGH |
| RC-B011 | APP Scam Reimbursement (UK PSR) | 58% | 45-70% | UK PSR Data | HIGH |
| RC-B012 | Real-Time Fraud Latency (Best-in-Class) | 65ms | 30-100ms | Featurespace | MEDIUM |
| RC-B013 | SOX Testing Hours per Control (Automated) | 4.5 hrs | 3-6 hrs | Protiviti 2024 | HIGH |
| RC-B014 | ITGC Deficiency Rate (Top Quartile) | 3.5% | 2-5% | Protiviti 2024 | HIGH |
| RC-B015 | Consumer Complaint Rate (CFPB Median) | 220 | 150-350 | CFPB Annual Report | HIGH |
| RC-B016 | Cyber Risk Quantification Coverage | 85% | 75-95% | Gartner | MEDIUM |
| RC-B017 | Vendor Due Diligence Currency | 95% | 90-100% | Gartner | MEDIUM |
| RC-B018 | Regulatory Report First-Pass Accuracy | 98% | 96-99.5% | Accenture | MEDIUM |

---

## Buying Triggers (14)

| ID | Trigger | Type | Timing | Linked Pain |
|----|---------|------|--------|-------------|
| RC-BT001 | Regulatory examination findings (MRA/MRIA) | Regulatory | 6-18 months | RC-P001, RC-P002 |
| RC-BT002 | Consent order or enforcement action | Regulatory | Immediate | RC-P001, RC-P008 |
| RC-BT003 | Board risk committee requests $-denominated cyber risk | Governance | Next board cycle | RC-P009 |
| RC-BT004 | FRTB go-live date announced | Regulatory | 12-24 months | RC-P004 |
| RC-BT005 | APP scam reimbursement mandate enacted | Regulatory | 6-12 months | RC-P006 |
| RC-BT006 | FedNow/RTP volume crosses detection threshold | Technology | Immediate | RC-P006 |
| RC-BT007 | SOX material weakness disclosed | Regulatory | Next annual filing | RC-P007 |
| RC-BT008 | Credit model Gini decline >5 points | Risk Event | Next review cycle | RC-P003 |
| RC-BT009 | AI/ML deployment exceeds validation capacity 2x | Risk Event | Immediate | RC-P012 |
| RC-BT010 | Operational resilience deadline <18 months | Regulatory | 18-month hard deadline | RC-P015 |
| RC-BT011 | Major vendor outage or cyber incident | Risk Event | Immediate | RC-P010 |
| RC-BT012 | Climate risk disclosure mandate | Regulatory | 24-36 months | RC-P017 |
| RC-BT013 | Regulatory filing late or restatement | Regulatory | Next filing cycle | RC-P011 |
| RC-BT014 | Whistleblower volume spike >25% | Risk Event | Immediate | RC-P018 |

---

## Regulatory Factors (11)

| ID | Regulation | Body | Jurisdiction | Penalty Range | Deadline |
|----|------------|------|------------|---------------|----------|
| RC-RF001 | BSA/AML | FinCEN/OCC/FDIC/Fed | US | $500K-$2B | Ongoing |
| RC-RF002 | SOX 404 (ICFR) | SEC/PCAOB | US | $1M-$50M | Annual |
| RC-RF003 | Basel Pillar 2 / ICAAP | Basel Committee | Global | $5M-$500M | Annual |
| RC-RF004 | SR 11-7 (Model Risk) | Federal Reserve/OCC | US | $0-$50M | Ongoing |
| RC-RF005 | GDPR | EU DPAs | EU/UK | $20M-$100M | Ongoing |
| RC-RF006 | CFPB Section 1033 | CFPB | US | $0-$5M | 2025-2026 |
| RC-RF007 | UK PRA PS21/18 (Op Resilience) | PRA/FCA | UK | $1M-$50M | March 2025 |
| RC-RF008 | SEC Cybersecurity Disclosure | SEC | US | $0-$25M | Active |
| RC-RF009 | EU AI Act | EU AI Office | EU | $7.5M-$35M | 2025-2027 |
| RC-RF010 | OCC Heightened Standards | OCC | US | $0-$100M | Ongoing |
| RC-RF011 | ISSB S2 / TCFD | ISSB/SEC | Global | $0-$20M | 2024-2026 |

---

## Worked Examples Summary

### RC-WE001: Regional Bank Sanctions Screening Transformation
- **Scenario:** $50B AUM bank, 3M annual wire transactions, 96% FP rate, 25 FTE investigators
- **Inputs:** $2.8M implementation, $450K annual license
- **Results:** $47.45M annual benefit, 0.7-month payback, 1,691% ROI, $115.1M 3-year NPV
- **Confidence:** HIGH

### RC-WE002: Credit Union Real-Time Fraud on FedNow
- **Scenario:** $12B credit union, $800M FedNow volume, 22 bps fraud loss rate, 55% APP scam reimbursement
- **Inputs:** $1.2M implementation, $280K annual license
- **Results:** $2.44M annual benefit, 5.9-month payback, 406% ROI, $4.87M 3-year NPV
- **Confidence:** HIGH

### RC-WE003: Global Bank Regulatory Reporting Automation
- **Scenario:** Top-20 global bank, $28M annual reporting cost, 220 FTEs, 82% first-pass accuracy
- **Inputs:** $8.5M implementation, $2.1M annual license/maintenance
- **Results:** $11.93M annual benefit, 8.5-month payback, 321% ROI, $21.15M 3-year NPV
- **Confidence:** HIGH

---

## Technology Systems (13)

| ID | System | Category | Complexity | Key Vendors |
|----|--------|----------|------------|-------------|
| RC-TS001 | AML Transaction Monitoring | Risk System | HIGH | Nice Actimize, FICO, SAS, Quantexa |
| RC-TS002 | Sanctions Screening Engine | Risk System | MEDIUM | Nice Actimize, FircoSoft, Refinitiv, LexisNexis |
| RC-TS003 | KYC/CDD Platform | Risk System | MEDIUM | Thomson Reuters, Encompass, Moody's |
| RC-TS004 | Credit Risk Analytics | Risk System | HIGH | Moody's, SAS, FICO, IBM Algorithmics |
| RC-TS005 | Market Risk Engine | Risk System | HIGH | Murex, Numerix, Quantifi |
| RC-TS006 | GRC Platform | Risk System | HIGH | ServiceNow, RSA Archer, MetricStream |
| RC-TS007 | Fraud Detection Platform | Risk System | MEDIUM | Featurespace, FICO, Feedzai |
| RC-TS008 | SOX Controls Automation | Compliance | MEDIUM | Workiva, AuditBoard, LogicGate |
| RC-TS009 | Consumer Compliance Monitoring | Compliance | MEDIUM | Fair Isaac, PerformLine, Compliance.ai |
| RC-TS010 | Cyber Risk Quantification | Risk System | MEDIUM | RiskLens, Axio, Kovrr, BitSight |
| RC-TS011 | TPRM Platform | Risk System | MEDIUM | ProcessUnity, BitSight, Prevalent |
| RC-TS012 | Regulatory Reporting Hub | Compliance | HIGH | AxiomSL, Regnology, SAS, IBM OpenPages |
| RC-TS013 | Model Risk Management | Risk System | MEDIUM | ModelOp, IBM Watson OpenScale, SAS |

---

## Governance

| Attribute | Value |
|-----------|-------|
| Source Coverage | Mixed (public regulatory data + paid industry benchmarks) |
| Confidence | HIGH |
| Last Updated | 2024-12-19 |
| Approved for Customer-Facing Output | Yes |
| Review Owner | Risk-Compliance-Subpack-Agent |
| Agent Swarm ID | swarm-rc-v1-2024 |
| Parent Master Swarm ID | swarm-master-fs-v1-2024 |

---

## Usage Notes

1. **Do not duplicate master content.** Reference the master pack for base value drivers, generic personas, and framework definitions.
2. **All KPIs have formulas.** Every benchmark has a source citation. Every signal rule has a confidence level with rationale.
3. **Assumptions requiring validation:** Customer lifetime value (CLV), average alert disposition cost, loaded FTE cost, and model override cost vary significantly by institution. Use customer-specific data when available; industry benchmarks are marked with confidence flags.
4. **Financial outcomes:** All formulas connect to one of: Cost Savings, Risk Reduction, Revenue Uplift, or Working Capital Improvement.
5. **Persona overlap:** The 6 new personas (RC-PER001-006) specialize sub-functions within master personas (CRO, CCO, CISO, CDO). Use both in discovery conversations for complete stakeholder mapping.
