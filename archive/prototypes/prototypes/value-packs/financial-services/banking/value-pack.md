# Banking Vertical Subpack (banking-v1)

**Parent Master:** financial-services-master-v1  
**Version:** 1.0.0  
**Last Updated:** 2025-01-28  
**Agent Swarm ID:** banking-subpack-s4-1  
**Confidence Level:** HIGH  
**Approved for Customer-Facing Output:** Yes  

---

## 1. Overview

The Banking Vertical Subpack provides vertical-specialized value intelligence for Banking sub-segments: Retail, Commercial, Investment, Community/Regional, Credit Unions, Digital Banks, Private Banking, Treasury, Payments/Cards, and Lending (Mortgage/Auto/SMB).

This subpack **extends** the Financial Services Master Pack with banking-specific components only. All master pack components remain valid and applicable.

---

## 2. Vertical Focus

| Segment | Description |
|---------|-------------|
| Retail Banking | Consumer deposit and lending products, branch and digital channels |
| Commercial/Corporate Banking | Middle-market and large corporate lending, treasury, trade |
| Investment Banking | M&A advisory, underwriting, capital markets |
| Community/Regional Banks | Sub-$100B asset institutions, relationship banking |
| Credit Unions | Member-owned cooperative financial institutions |
| Digital Banks/Neobanks | Branchless, mobile-first banking models |
| Private Banking/Wealth Management | HNW/UHNW client advisory and portfolio management |
| Treasury Services/Cash Management | Corporate liquidity, payments, receivables |
| Payments/Cards | Consumer and commercial card issuing, interchange, RTP |
| Mortgage Lending | Residential mortgage origination and servicing |
| Auto Lending | Direct and indirect auto loans and leases |
| Small Business Lending | SMB term loans, lines of credit, SBA products |

---

## 3. Inheritance Manifest

### Inherited from Master Pack (read-only reference)
- **Value Driver Framework** (VD001-VD051)
- **Base Persona Archetypes** (PER001-PER014)
- **Evidence Source Types** (regulatory_filing, industry_research, data_provider, etc.)
- **Formula Templates** (VF001-VF025)
- **Signal Source Taxonomy** (financial_statement, news_sentiment, macro_indicator, etc.)
- **Benchmark Methodology** (peer_quartile, industry_average, regulatory_minimum)
- **Governance Framework** (source_coverage, confidence, approval flags)

### Created by This Subpack
| Component | Count | ID Range |
|-----------|-------|----------|
| Pains | 18 | P_BNK_001 to P_BNK_018 |
| KPIs | 54 | K_BNK_001 to K_BNK_054 |
| Value Drivers | 36 | VD_BNK_001 to VD_BNK_036 |
| Formulas | 15 | VF_BNK_001 to VF_BNK_015 |
| Benchmarks | 25 | B_BNK_001 to B_BNK_025 |
| Signal Rules | 20 | SR_BNK_001 to SR_BNK_020 |
| Personas | 6 NEW | PER_BNK_001 to PER_BNK_006 |
| Discovery Questions | 20 | DQ_BNK_001 to DQ_BNK_020 |
| Objections | 10 | OBJ_BNK_001 to OBJ_BNK_010 |
| Technology Systems | 15 | TS_BNK_001 to TS_BNK_015 |
| Regulatory Factors | 12 | RF_BNK_001 to RF_BNK_012 |
| Competitor Factors | 7 | CF_BNK_001 to CF_BNK_007 |
| Buying Triggers | 15 | BT_BNK_001 to BT_BNK_015 |
| Worked Examples | 3 | WE_BNK_001 to WE_BNK_003 |
| Evidence Sources | 12 | ES_BNK_001 to ES_BNK_012 |

### Overridden Components
**None.** This subpack contains only vertical-specialized additions. All master pack components remain valid and applicable to the banking vertical without conflict.

---

## 4. Business Pains (18)

### P_BNK_001: NIM Compression from Deposit Beta >70%
- **Symptoms:** NIM declining >15bps YoY, deposit beta >70%, CD promotional rates rising >50bps, brokered deposit share >10%, cost of funds increasing >20bps per quarter
- **Affected Segments:** Banking, Credit Unions, Community/Regional Banks
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** FDIC Quarterly Banking Profile Q3 2024, Federal Reserve H.8 Release, S&P Global Market Intelligence Bank Scorecards

### P_BNK_002: Mortgage Origination Cost >$12,000 per Loan
- **Symptoms:** Cost-to-close >$12,000, cycle time >45 days, pull-through rate <65%, rework rate >15%, processor throughput <3 loans/day
- **Affected Segments:** Banking, Mortgage Lending
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** Mortgage Bankers Association Performance Reports 2024, ICE Mortgage Technology Origination Insight Report, Fannie Mae Lender Sentiment Survey

### P_BNK_003: Branch Network Operating Cost Inflation
- **Symptoms:** Branch transactions declining >10% YoY, cost-per-branch >$800K annually, digital transaction share >85%, branch FTE cost >50% of retail ops, lease renewal decisions pending >20% of network
- **Affected Segments:** Retail Banking, Community/Regional Banks
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** J.D. Power Retail Banking Satisfaction Study 2024, Novantas Branch Analytics, FDIC Deposit Market Share Data

### P_BNK_004: CRE Concentration and Refinancing Cliff
- **Symptoms:** CRE concentration >300% of risk-based capital, office vacancy rate >20% in portfolio, CRE watch list >8% of portfolio, refinancing pipeline >$500M maturing within 12 months, appraisal reductions >15% on renewal
- **Affected Segments:** Commercial Banking, Community/Regional Banks
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** Federal Reserve Senior Loan Officer Opinion Survey, Trepp CMBS Delinquency Report, CoStar Office Market Analytics

### P_BNK_005: Auto Lending Lease-End and Residual Value Risk
- **Symptoms:** Residual value losses >$500 per unit, auto delinquency rate >3.5%, lease return volume >20% of auto portfolio, remarketing days-to-sell >45 days, subprime charge-off rate >8%
- **Affected Segments:** Auto Lending, Retail Banking
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** Cox Automotive Manheim Index, Experian Auto Finance Market Report, S&P Global Auto ABS Performance

### P_BNK_006: Digital Account Opening Abandonment and IDV Friction
- **Symptoms:** Digital onboarding abandonment >60%, identity verification failure rate >25%, manual review queue >48 hours, KYC false reject rate >15%, NPS <25 for onboarding experience
- **Affected Segments:** Retail Banking, Digital Banks, Credit Unions
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** J.D. Power Digital Banking Satisfaction, Forrester Digital Onboarding Benchmark, Aite-Novarica KYC Friction Study

### P_BNK_007: Treasury Management Client Deposit Beta Erosion
- **Symptoms:** Operating deposit outflows >8% quarterly, ECR spread to Fed Funds <50bps, Treasury client NPS <30, RFP loss rate >25%, compensating balance credits declining >10%
- **Affected Segments:** Treasury Services, Commercial Banking
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** AFP Treasury Benchmark Survey, Treasury Strategies Deposit Analysis, Federal Reserve H.8 Release

### P_BNK_008: Card Interchange Revenue Compression and Rewards Cost Inflation
- **Symptoms:** Interchange yield declining >5bps annually, rewards cost >45% of interchange revenue, card CAC >$300, Durbin 2.0 legislative risk flagged, active card rate <65%
- **Affected Segments:** Payments/Cards, Retail Banking
- **Prevalence:** MEDIUM | **Confidence:** MEDIUM
- **Sources:** Nilson Report Card Industry Data, Mercator Advisory Group Payments Dashboard, Congressional Durbin Amendment Proposals

### P_BNK_009: Commercial Lending RFP Win Rate Decline
- **Symptoms:** RFP win rate <30%, credit decision time >14 days, relationship manager turnover >15%, commitment fee utilization <60%, cross-sell ratio <2.5 products per client
- **Affected Segments:** Commercial Banking, Investment Banking
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** AFP Corporate Banking Satisfaction, S&P Global C&I Lending Data, Greenwich Associates Commercial Banking Study

### P_BNK_010: Private Banking Client Acquisition and Succession Crisis
- **Symptoms:** Average advisor age >55, AUM per advisor <$100M, next-gen client engagement rate <20%, advisor recruitment <3% annually, client attrition >10% post-advisor retirement
- **Affected Segments:** Private Banking, Retail Banking
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** Cerulli Private Banking Metrics, McKinsey Wealth Management Report 2024, Morgan Stanley Private Wealth 10-K

### P_BNK_011: Core Banking System API Limitations and Vendor Lock-in
- **Symptoms:** API response time >500ms, batch processing windows >4 hours, vendor contract renewal >$50M, product launch cycle >12 months, real-time payment unavailable
- **Affected Segments:** Retail Banking, Digital Banks, Credit Unions
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** Celent Core Banking Report 2024, Gartner Core Banking Vendor Analysis, FFIEC IT Examination Handbook

### P_BNK_012: Community Bank Efficiency Ratio Deterioration >65%
- **Symptoms:** Efficiency ratio >65%, non-interest expense growing >7% YoY, revenue per employee <$350K, compliance cost >8% of non-interest expense, technology spend <3% of revenue
- **Affected Segments:** Community/Regional Banks, Credit Unions
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** FDIC Community Banking Study, ICBA Community Bank Performance Report, S&P Global Regional Bank Data

### P_BNK_013: Real-Time Payment Fraud Detection Latency Gap
- **Symptoms:** Fraud detection latency >300ms, APP scam losses >0.2% of RTP volume, false positive rate on real-time >15%, chargeback rights unavailable on RTP, customer reimbursement rate >40%
- **Affected Segments:** Payments/Cards, Retail Banking, Digital Banks
- **Prevalence:** HIGH | **Confidence:** HIGH
- **Sources:** Nilson Report Fraud Statistics, Javelin Strategy Identity Fraud Study, FedNow Service Provider Risk Guidelines

### P_BNK_014: Small Business Deposit and Lending Relationship Fragmentation
- **Symptoms:** SMB primary bank share <40%, SMB deposit outflows >10% annually, cross-sell to SMB <2 products, SMB loan abandonment >55%, NPS <20 among SMB clients
- **Affected Segments:** Small Business Lending, Commercial Banking, Retail Banking
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** Fed Small Business Credit Survey, J.D. Power Small Business Banking Study, SBA Lending Statistics

### P_BNK_015: Credit Card Portfolio Yield Compression and Charge-off Creep
- **Symptoms:** Portfolio yield <18%, charge-off rate >4.5%, 30+ delinquency rate >3%, promotional balance share >25%, cost of funds on card funding >5%
- **Affected Segments:** Payments/Cards, Retail Banking
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** Federal Reserve G.19 Consumer Credit Report, TransUnion Credit Industry Insights, S&P Global Credit Card ABS Performance

### P_BNK_016: Investment Banking Deal Pipeline Compression and Fee Pressure
- **Symptoms:** Advisory revenue decline >20% YoY, underwriting fees <2.5% on equity deals, M&A league table rank declining, pitch-to-win ratio <15%, MD compensation as % of revenue >35%
- **Affected Segments:** Investment Banking
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** Dealogic League Tables, Bloomberg Investment Banking Fee Analysis, McKinsey Investment Banking Annual Review

### P_BNK_017: Digital Bank Unit Economics and Path-to-Profitability Failure
- **Symptoms:** CAC >$200 per account, monthly burn rate >$10M, interchange revenue per account <$15/month, deposit balance per account <$1,500, NPS high but CLV/CAC <2x
- **Affected Segments:** Digital Banks, Fintech
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** CB Insights State of Fintech Q2 2024, Simon-Kucher Neobank Economics Study, Chime/MoneyLion Public Filings

### P_BNK_018: Credit Union Membership Growth Stagnation and Demographic Aging
- **Symptoms:** Membership growth <2% annually, average member age >50, digital engagement rate <30%, young member acquisition <10% of new members, technology spend <2.5% of assets
- **Affected Segments:** Credit Unions
- **Prevalence:** MEDIUM | **Confidence:** HIGH
- **Sources:** NCUA Credit Union Data, CUNA Mutual Group Trends Report, Callahan & Associates Credit Union Analytics

---

## 5. KPIs (54)

### Deposit and NIM KPIs
| ID | Name | Formula | Benchmark |
|----|------|---------|-----------|
| K_BNK_001 | Deposit Beta | (Change in Cost of Deposits / Change in FFR) * 100 | 30-55 (optimal) |
| K_BNK_002 | Net Interest Margin | (Interest Income - Interest Expense) / Avg Earning Assets | 3.0-4.5 |
| K_BNK_003 | Cost of Funds | Total Interest Expense / Avg Interest-Bearing Liabilities | 1.5-3.5 |
| K_BNK_019 | Treasury Client Deposit Beta | (Change in Commercial Deposit Cost / Change in Market Rate) * 100 | 25-45 |
| K_BNK_020 | ECR Spread to Fed Funds | ECR Rate - Effective FFR | 0.6-1.2 |
| K_BNK_041 | SMB Deposit Growth Rate | YoY change in SMB deposits | +5 to +15 |

### Mortgage KPIs
| ID | Name | Formula | Benchmark |
|----|------|---------|-----------|
| K_BNK_004 | Mortgage Cost-to-Close | Total Origination Cost / Closed Loan Count | $5,000-8,000 |
| K_BNK_005 | Mortgage Cycle Time | Avg Days from Application to Funding | 20-35 days |
| K_BNK_006 | Mortgage Pull-Through Rate | Funded Loans / Approved Applications | 70-85 |

### Branch and Digital KPIs
| ID | Name | Formula | Benchmark |
|----|------|---------|-----------|
| K_BNK_007 | Branch Cost per Transaction | Total Branch Cost / Total Transactions | $2.50-4.50 |
| K_BNK_008 | Digital Transaction Share | Digital / Total Transactions | 85-95 |
| K_BNK_009 | Branch FTE Cost Ratio | Branch FTE Cost / Total Retail Ops Cost | 25-40 |
| K_BNK_016 | Digital Onboarding Abandonment | Abandoned / Total Started | 25-35 |
| K_BNK_017 | IDV Failure Rate | Failed / Total IDV Attempts | 5-12 |
| K_BNK_018 | Digital Onboarding NPS | NPS Score | 40-60 |

### Credit Risk KPIs
| ID | Name | Formula | Benchmark |
|----|------|---------|-----------|
| K_BNK_010 | CRE Concentration Ratio | CRE Loans / Risk-Based Capital | 150-250 |
| K_BNK_011 | CRE Watch List Ratio | Watch List / Total CRE | 2-6 |
| K_BNK_012 | Office Vacancy Rate (Portfolio) | Vacant SF / Total SF | 8-15 |
| K_BNK_013 | Auto Lease Residual Loss | Actual - Projected per Unit | $0-300 |
| K_BNK_014 | Auto Delinquency Rate (60+ DPD) | 60+ DPD / Total Auto Loans | 1.5-3.0 |
| K_BNK_015 | Auto Remarketing Days-to-Sell | Avg Days to Sale | 20-35 |
| K_BNK_043 | Credit Card Portfolio Yield | (Interest + Fees) / Avg Receivables | 18-22 |
| K_BNK_044 | Credit Card Charge-Off Rate | Charge-Offs / Avg Receivables | 2.5-3.5 |
| K_BNK_045 | Credit Card 30+ Delinquency | 30+ DPD / Total Receivables | 1.8-3.0 |

### Commercial and Treasury KPIs
| ID | Name | Formula | Benchmark |
|----|------|---------|-----------|
| K_BNK_021 | Treasury RFP Win Rate | Won / Total Submitted | 45-60 |
| K_BNK_022 | Card Interchange Yield | Interchange Revenue / Purchase Volume | 140-180 bps |
| K_BNK_023 | Rewards Cost % of Interchange | Rewards Expense / Interchange Revenue | 25-40 |
| K_BNK_024 | Card CAC | Marketing Cost / New Accounts | $150-300 |
| K_BNK_025 | Commercial RFP Win Rate | Won / Total RFPs | 40-55 |
| K_BNK_026 | Commercial Credit Decision Time | Avg Days to Decision | 3-7 |
| K_BNK_027 | Commercial Cross-Sell Ratio | Products per Client | 3.5-5.0 |
| K_BNK_040 | SMB Primary Bank Share | SMB Naming Bank as Primary / Total | 55-70 |
| K_BNK_042 | SMB Loan Application Abandonment | Abandoned / Total Started | 25-40 |

### Efficiency and Operations KPIs
| ID | Name | Formula | Benchmark |
|----|------|---------|-----------|
| K_BNK_028 | Private Banking AUM per Advisor | Total AUM / Advisor Count | $150-300M |
| K_BNK_029 | Next-Gen Client Engagement | Engaged Next-Gen / Total Next-Gen | 40-60 |
| K_BNK_030 | Advisor Attrition Rate | Lost / Average Count | 3-7 |
| K_BNK_031 | Core System API Availability | API Uptime / Total | 99.95-99.999 |
| K_BNK_032 | Product Time-to-Market | Days Concept to Production | 60-120 |
| K_BNK_033 | Core Vendor Contract Inflation | (Current - Prior) / Prior | 2-5 |
| K_BNK_034 | Efficiency Ratio | Non-Interest Expense / (NII + NII) | 45-58 |
| K_BNK_035 | Revenue per Employee | Total Revenue / FTE | $450K-650K |
| K_BNK_036 | Compliance Cost Ratio | Compliance Cost / Non-Interest Expense | 4-8 |

### Fraud and Digital Bank KPIs
| ID | Name | Formula | Benchmark |
|----|------|---------|-----------|
| K_BNK_037 | Real-Time Fraud Detection Latency | ms from Transaction to Decline | 50-150 |
| K_BNK_038 | APP Scam Loss Rate | Scam Losses / RTP Volume | 5-15 bps |
| K_BNK_039 | Fraud False Positive Rate | False Positives / Total Declines | 3-10 |
| K_BNK_046 | IB Advisory Revenue per MD | Advisory Revenue / MD Count | $5-10M |
| K_BNK_047 | Pitch-to-Win Ratio | Won / Total Pitches | 20-35 |
| K_BNK_048 | Underwriting Fee Margin | Revenue / Capital Raised | 3.0-5.0 |
| K_BNK_049 | Digital Bank CAC | Marketing Cost / New Accounts | $80-140 |
| K_BNK_050 | Deposit Balance per Account | Total Deposits / Accounts | $2,500-5,000 |
| K_BNK_051 | Monthly Burn per Account | Operating Loss / Active Accounts | $0-5 |
| K_BNK_052 | Credit Union Membership Growth | YoY Change | 4-8 |
| K_BNK_053 | Average Member Age | Average Age | 38-45 |
| K_BNK_054 | Digital Engagement Rate (CU) | Digital Login in 30 Days / Total | 50-70 |

---

## 6. Value Drivers (36)

| ID | Signal Pattern | Category | Pain | Confidence |
|----|----------------|----------|------|------------|
| VD_BNK_001 | Deposit beta >70% with NIM declining >15bps YoY | Revenue Uplift | P_BNK_001 | HIGH |
| VD_BNK_002 | Brokered deposit dependence >10% with cost of funds rising >20bps quarterly | Working Capital | P_BNK_001 | HIGH |
| VD_BNK_003 | Cost-to-close >$8,000 with cycle time >45 days | Cost Savings | P_BNK_002 | HIGH |
| VD_BNK_004 | Pull-through rate <65% with rework rate >15% | Revenue Uplift | P_BNK_002 | HIGH |
| VD_BNK_005 | Branch cost per transaction >$6 with digital share >85% | Cost Savings | P_BNK_003 | HIGH |
| VD_BNK_006 | Branch FTE cost ratio >50% with lease renewals pending >20% | Cost Savings | P_BNK_003 | HIGH |
| VD_BNK_007 | CRE concentration >300% of capital with watch list >8% | Risk Reduction | P_BNK_004 | HIGH |
| VD_BNK_008 | Office vacancy >20% with refinancing pipeline >$500M | Risk Reduction | P_BNK_004 | HIGH |
| VD_BNK_009 | Residual losses >$500 per unit with auto delinquency >3.5% | Risk Reduction | P_BNK_005 | HIGH |
| VD_BNK_010 | Remarketing days-to-sell >45 with subprime charge-off >8% | Cost Savings | P_BNK_005 | HIGH |
| VD_BNK_011 | Onboarding abandonment >60% with IDV failure >25% | Revenue Uplift | P_BNK_006 | HIGH |
| VD_BNK_012 | Manual review queue >48 hours with KYC false reject >15% | Cost Savings | P_BNK_006 | HIGH |
| VD_BNK_013 | Operating deposit outflows >8% with ECR spread <50bps | Working Capital | P_BNK_007 | HIGH |
| VD_BNK_014 | Treasury RFP loss rate >25% with client NPS <30 | Revenue Uplift | P_BNK_007 | HIGH |
| VD_BNK_015 | Interchange yield declining >5bps with rewards cost >45% | Revenue Uplift | P_BNK_008 | MEDIUM |
| VD_BNK_016 | Card CAC >$300 with active card rate <65% | Cost Savings | P_BNK_008 | MEDIUM |
| VD_BNK_017 | Commercial RFP win rate <30% with decision time >14 days | Revenue Uplift | P_BNK_009 | HIGH |
| VD_BNK_018 | Cross-sell ratio <2.5 with RM turnover >15% | Revenue Uplift | P_BNK_009 | HIGH |
| VD_BNK_019 | Average advisor age >55 with AUM per advisor <$100M | Revenue Uplift | P_BNK_010 | HIGH |
| VD_BNK_020 | Next-gen engagement <20% with attrition >10% post-retirement | Revenue Uplift | P_BNK_010 | HIGH |
| VD_BNK_021 | API response time >500ms with batch windows >4 hours | Cost Savings | P_BNK_011 | HIGH |
| VD_BNK_022 | Vendor contract >$50M with product launch cycle >12 months | Revenue Uplift | P_BNK_011 | HIGH |
| VD_BNK_023 | Efficiency ratio >65% with compliance cost >8% | Cost Savings | P_BNK_012 | HIGH |
| VD_BNK_024 | Technology spend <3% with revenue per employee <$350K | Cost Savings | P_BNK_012 | HIGH |
| VD_BNK_025 | Fraud detection latency >300ms on RTP rails | Risk Reduction | P_BNK_013 | HIGH |
| VD_BNK_026 | APP scam losses >0.2% with reimbursement rate >40% | Risk Reduction | P_BNK_013 | HIGH |
| VD_BNK_027 | SMB primary bank share <40% with deposit outflows >10% | Working Capital | P_BNK_014 | HIGH |
| VD_BNK_028 | SMB loan abandonment >55% with cross-sell <2 products | Revenue Uplift | P_BNK_014 | HIGH |
| VD_BNK_029 | Portfolio yield <18% with charge-off rate >4.5% | Revenue Uplift | P_BNK_015 | HIGH |
| VD_BNK_030 | 30+ delinquency >3% with promotional balance share >25% | Risk Reduction | P_BNK_015 | HIGH |
| VD_BNK_031 | Advisory revenue decline >20% with MD comp >35% of revenue | Cost Savings | P_BNK_016 | HIGH |
| VD_BNK_032 | Pitch-to-win <15% with underwriting fees <2.5% | Revenue Uplift | P_BNK_016 | HIGH |
| VD_BNK_033 | CAC >$200 with monthly burn >$10M | Cost Savings | P_BNK_017 | HIGH |
| VD_BNK_034 | Interchange revenue <$15/month with deposit balance <$1,500 | Revenue Uplift | P_BNK_017 | HIGH |
| VD_BNK_035 | Membership growth <2% with average age >50 | Revenue Uplift | P_BNK_018 | HIGH |
| VD_BNK_036 | Digital engagement <30% with technology spend <2.5% of assets | Cost Savings | P_BNK_018 | HIGH |

---

## 7. Formulas (15)

### VF_BNK_001: Deposit Beta Improvement NIM Value
```
(Deposit_Beta_Current - Deposit_Beta_Target) * Rate_Change * Deposit_Base * Margin_Factor
```
**Example:** (0.75 - 0.55) * 0.025 * $30B * 0.85 = $127.5M annual pre-tax improvement

### VF_BNK_002: Mortgage Cost-to-Close and Cycle Time Reduction
```
(Current_Cost - Target_Cost) * Volume + (Current_Cycle - Target_Cycle) * Cost_Per_Day * Volume
```
**Example:** ($10,500 - $6,500) * 40,000 + (45 - 25) * $90 * 40,000 = $232M annual value

### VF_BNK_003: Branch Network Rationalization Savings
```
(Branches_Closed * Avg_Branch_Cost) + (FTE_Reduction * Loaded_FTE_Cost) + Digital_Growth_Value - Lease_Termination_Costs
```
**Example:** (50 * $750K) + (200 * $85K) + $15M - $8M = $61.5M annual value

### VF_BNK_004: CRE Risk Mitigation and Provision Avoidance
```
(CRE_Reduction * Provision_Rate * CRE_Loans) + (Watch_List_Reduction * LGD * Exposure) + Capital_Relief
```
**Example:** $2.5M + $21M + $10M = $33.5M annual value

### VF_BNK_005: Auto Lease Residual Value Protection
```
(Residual_Reduction * Lease_End_Volume) + (Delinquency_Reduction * Avg_Balance * Charge_Off_Rate) + Remarketing_Value
```
**Example:** ($400 * 50,000) + $6M + $5M = $31M annual value

### VF_BNK_006: Digital Onboarding Conversion Improvement
```
(Target_Conversion - Current_Conversion) * Volume * CLV + (Manual_Review_Reduction * Cost_Per_Review)
```
**Example:** (0.45 - 0.30) * 500,000 * $1,200 + (20,000 * $45) = $90.9M annual value

### VF_BNK_007: Treasury Deposit Retention Value
```
(Outflow_Reduction * Deposit_Balance * NIM) + (Win_Rate_Improvement * RFP_Value * Fee_Ratio) + Retention_Value
```
**Example:** $5.5M + $3M + $12M = $20.5M annual value

### VF_BNK_008: Card Interchange and Rewards Optimization
```
(Interchange_BPS_Improvement * Purchase_Volume) + (Rewards_Reduction * Rewards_Budget) + Active_Card_Revenue
```
**Example:** $18M + $18M + $2.5M = $38.5M annual value

### VF_BNK_009: Commercial Banking RFP and Speed Value
```
(Win_Rate_Improvement * Pipeline * Deal_Size) + (Speed_Reduction * Cost_Per_Day * Pipeline) + Cross_Sell_Gain
```
**Example:** $300M + $14M + $8M = $322M annual value

### VF_BNK_010: Private Banking Advisor Productivity
```
(Target_AUM - Current_AUM) * Advisor_Count * Fee_Rate + Next_Gen_Revenue + Recruitment_Savings
```
**Example:** $81M + $15M + $3M = $99M annual revenue uplift

### VF_BNK_011: Core Banking Modernization ROI
```
Product_Launch_Revenue + IT_Maintenance_Reduction + Vendor_Avoidance + Real_Time_Revenue
```
**Example:** $45M + $22M + $8M + $12M = $87M annual value

### VF_BNK_012: Community Bank Efficiency Improvement
```
(Efficiency_Improvement * Revenue) + Compliance_Reduction + Tech_Optimization + Revenue_Per_Employee_Gain
```
**Example:** $40M + $5M + $3M + $4M = $52M annual value

### VF_BNK_013: Real-Time Payment Fraud Prevention Value
```
(Fraud_Reduction * RTP_Volume) + (APP_Reduction * Scam_Volume) + (False_Positive_Reduction * CX_Value) + Penalty_Avoidance
```
**Example:** $24M + $12.5M + $3M + $2M = $41.5M annual value

### VF_BNK_014: SMB Banking Revenue Recovery
```
(Primary_Share_Gain * SMB_Deposits * NIM) + (Abandonment_Reduction * Avg_Loan * Yield) + Cross_Sell_Revenue
```
**Example:** $5M + $26.25M + $10M = $41.25M annual value

### VF_BNK_015: Credit Union Digital Transformation Value
```
Membership_Growth_Revenue + Digital_Engagement_Savings + Young_Member_LTV + Tech_Optimization
```
**Example:** $12M + $6M + $8M + $3M = $29M annual value

---

## 8. Benchmarks (25)

See full JSON for complete benchmark specifications. Key benchmarks include:

| Benchmark | Value | Segment |
|-----------|-------|---------|
| Top Quartile NIM (>$10B) | 3.45-3.80% | Banking |
| Top Quartile NIM (Community) | 3.65-4.10% | Community Banks |
| Deposit Beta (Optimal) | 30-55% | Banking |
| Mortgage Cost-to-Close (Best) | $5,000-7,000 | Banking |
| Mortgage Cycle Time (Best) | 20-30 days | Banking |
| Digital Transaction Share (Top) | 88-95% | Banking |
| CRE Concentration (Comfort Zone) | 200-300% RBC | Banking |
| Digital Onboarding Abandonment (Best) | 25-35% | Banking |
| Commercial Decision Time (Best) | 2-5 days | Commercial |
| Efficiency Ratio (Top National) | 48-55% | Banking |
| Efficiency Ratio (Top Community) | 52-58% | Community |
| Card Charge-Off (Prime) | 2.5-3.5% | Payments |
| Private Banking AUM/Advisor (Top) | $200-350M | Private Banking |
| Digital Bank CAC (Best) | $80-140 | Digital Banks |
| CU Membership Growth (Top) | 5-9% | Credit Unions |

---

## 9. Signal Rules (20)

### Top Signal Rules

| ID | Trigger | Pattern | Action | Confidence |
|----|---------|---------|--------|------------|
| SR_BNK_001 | Deposit Beta Surge | Beta >70% for 2 quarters | ALCO deep-dive | HIGH |
| SR_BNK_002 | Mortgage Cost Escalation | Cost-to-close >$10K or cycle >50 days | LOS optimization | HIGH |
| SR_BNK_003 | Branch Rationalization | Cost/txn >$7 + digital >88% + lease pending | Optimization study | HIGH |
| SR_BNK_004 | CRE Concentration Warning | CRE >300% RBC OR watch list >8% | Concentration reduction | HIGH |
| SR_BNK_006 | Digital Onboarding Friction | Abandonment >60% OR IDV failure >25% | UX audit + A/B test | HIGH |
| SR_BNK_007 | Treasury Deposit Alert | Outflows >8% quarterly OR ECR spread <50bps | ECR review + outreach | HIGH |
| SR_BNK_011 | Core System Bottleneck | API >500ms OR launch cycle >14 months | Modernization business case | HIGH |
| SR_BNK_013 | RTP Fraud Gap | Detection latency >300ms OR APP losses >0.25% | Sub-100ms monitoring upgrade | HIGH |
| SR_BNK_015 | Card Portfolio Deterioration | Charge-off >4.5% OR 30+ delinquency >3.2% | Underwriting tightening | HIGH |
| SR_BNK_017 | Digital Bank Burn Crisis | Burn >$15M OR CAC >$250 for 2 quarters | Path-to-profitability initiative | HIGH |

---

## 10. Personas (6 NEW)

### PER_BNK_001: Chief Lending Officer (CLO)
- **Role:** All lending portfolios, credit policy, underwriting standards
- **KPIs:** K_BNK_025, K_BNK_026, K_BNK_027, K_BNK_004, K_BNK_005, K_BNK_006, K_BNK_010, K_BNK_011
- **Trusted Evidence:** ABA Commercial Lending Committee, RMA Statement Studies, Fed SLOOS
- **Disliked Claims:** Fully automated credit decisions, generic ROI without loan-level analysis, dismissal of relationship underwriting
- **Budget:** $5M-50M | **Level:** C-Suite

### PER_BNK_002: Branch Operations Manager
- **Role:** Branch network operations, staffing, customer experience, P&L
- **KPIs:** K_BNK_007, K_BNK_008, K_BNK_009, K_BNK_034, K_BNK_035
- **Trusted Evidence:** J.D. Power Retail Banking, Novantas Branch Analytics, FFIEC Call Report
- **Disliked Claims:** Branches obsolete, digital-only without human escalation, ignoring community relationships
- **Budget:** $2M-10M | **Level:** VP/Director

### PER_BNK_003: Digital Banking Product Owner
- **Role:** Digital product roadmap, mobile app, onboarding, self-service
- **KPIs:** K_BNK_016, K_BNK_017, K_BNK_018, K_BNK_008, K_BNK_031, K_BNK_032, K_BNK_052, K_BNK_054
- **Trusted Evidence:** Forrester Digital Experience, J.D. Power Digital, App Annie rankings, Aite-Novarica
- **Disliked Claims:** Launch in weeks without core integration, feature parity with neobanks ignoring compliance, seamless integration claims
- **Budget:** $3M-15M | **Level:** VP/Director

### PER_BNK_004: Treasury Sales Officer / Head of Treasury Management
- **Role:** Treasury management sales, deposit acquisition, ECR pricing, payment solutions
- **KPIs:** K_BNK_019, K_BNK_020, K_BNK_021, K_BNK_040, K_BNK_041
- **Trusted Evidence:** AFP Treasury Benchmark, Greenwich Associates, Fed H.8, competitive pricing intel
- **Disliked Claims:** Best-in-class without API evidence, ignoring switching costs, disregarding ECR sensitivity
- **Budget:** $2M-8M | **Level:** VP/Director

### PER_BNK_005: Mortgage Operations VP
- **Role:** End-to-end mortgage origination, LOS, vendor management, TRID compliance
- **KPIs:** K_BNK_004, K_BNK_005, K_BNK_006, K_BNK_034
- **Trusted Evidence:** MBA studies, ICE Mortgage Technology, Fannie Mae Lender Sentiment, STRATMOR
- **Disliked Claims:** Fully automated to <10 days, LOS migration without data risk, cost savings excluding vendor fees
- **Budget:** $5M-25M | **Level:** VP/Director

### PER_BNK_006: Payments Product Manager
- **Role:** Card and payment product strategy, debit/credit, RTP/FedNow, fraud prevention
- **KPIs:** K_BNK_022, K_BNK_023, K_BNK_024, K_BNK_037, K_BNK_038, K_BNK_039, K_BNK_043, K_BNK_044, K_BNK_045
- **Trusted Evidence:** Nilson Report, Fed Payments Study, Mercator, Javelin, Durbin studies
- **Disliked Claims:** Interchange projections ignoring Durbin 2.0, fraud prevention without latency specs, rewards ROI without breakage
- **Budget:** $3M-12M | **Level:** VP/Director

---

## 11. Discovery Questions (20)

1. How has your deposit beta trended over the last four quarters, and what is your target in the current rate environment?
2. What is your current cost-to-close and cycle time for mortgage originations, and how do those compare to your top three competitors?
3. What percentage of your branch network is currently cash-flow positive, and how many lease renewals are you facing in the next 24 months?
4. What is your current CRE concentration relative to risk-based capital, and how has your watch list trended in the last two quarters?
5. How are you managing lease-end volume and residual value risk in your auto portfolio given current used vehicle price trends?
6. What is your digital account opening abandonment rate, and where in the funnel do you see the highest dropout?
7. How has your commercial operating deposit balance trended, and what ECR spread are you currently offering relative to Fed Funds?
8. What is your current interchange yield trend, and how much of that revenue is being consumed by rewards program costs?
9. What is your commercial RFP win rate, and what are the top three reasons you lose deals to competitors?
10. What is the average age and AUM productivity of your private banking advisors, and what is your strategy for next-generation client engagement?
11. How many APIs does your core banking system support, and what is your average product time-to-market for new digital features?
12. What is your efficiency ratio trend, and what percentage of non-interest expense is consumed by compliance and regulatory costs?
13. What is your current fraud detection latency on real-time payment rails, and what percentage of APP scam losses are you absorbing?
14. What percentage of your SMB clients name you as their primary bank, and how many financial providers do they typically use?
15. How has your credit card portfolio yield trended, and what is your charge-off rate by FICO segment?
16. What is your investment banking pitch-to-win ratio, and how has your MD compensation as a percentage of revenue trended?
17. What is your current customer acquisition cost per account, and what is your monthly burn rate relative to active account base?
18. What is your membership growth rate, average member age, and what percentage of your technology budget is allocated to digital?
19. How are you preparing for Basel III endgame capital requirements, and what is your current CET1 ratio relative to your buffer target?
20. What is your current mortgage pipeline pull-through rate, and what percentage of locks are expiring before closing?

---

## 12. Objection Patterns (10)

### OBJ_BNK_001: "Our core vendor says they can add APIs next year"
**Response:** API roadmaps from legacy core vendors typically take 18-36 months with limited endpoint coverage. The cost of waiting includes lost digital revenue, higher vendor lock-in, and competitive disadvantage. What is the penalty cost of delaying a product launch by 12 months?

### OBJ_BNK_002: "We already looked at mortgage automation and the ROI wasn't there"
**Response:** Many mortgage automation assessments underestimate cycle time reduction on pull-through rates and the compounding effect of cost-per-loan at volume. Let's recalculate using your current pull-through and cost-to-close against 2024 benchmarks.

### OBJ_BNK_003: "Our regulators won't let us reduce branches that fast"
**Response:** Regulators evaluate branch reductions against CRA performance and community impact, not arbitrary limits. Banks with strong CRA ratings have successfully consolidated 15-25% of networks. What does your CRA exam history show?

### OBJ_BNK_004: "We're a relationship bank--automation would hurt our service model"
**Response:** Automation supports relationship banking by freeing RMs from administrative tasks and accelerating credit decisions. Top relationship banks achieve 3-5 day decision times while maintaining relationship quality. What percentage of RM time is spent on non-client-facing tasks?

### OBJ_BNK_005: "Our depositors are sticky--we don't need to worry about beta"
**Response:** Deposit stickiness varies by segment and rate environment. Historical beta may not predict behavior in sustained high-rate environments. Brokered deposit growth and CD promotional rates are early warning signals. What is your deposit outflow rate in the last two rate cycles?

### OBJ_BNK_006: "Real-time payments fraud is the customer's responsibility"
**Response:** While RTP settlement is irrevocable, regulatory and reputational risk increasingly places liability on banks for APP scams. UK Faster Payments experience shows banks absorbing 40-60% of losses. What is your current APP scam reimbursement policy?

### OBJ_BNK_007: "We can't justify the technology spend as a community bank"
**Response:** Community banks are increasingly leveraging cloud-native, API-first platforms with subscription models that reduce upfront CapEx. Shared service models and consortium approaches reduce per-bank cost by 40-60%. What is your current technology spend as a percentage of assets?

### OBJ_BNK_008: "Our current LOS vendor says they'll add AI features in their next release"
**Response:** Vendor AI roadmaps for legacy LOS typically deliver incremental features rather than transformative workflow automation. The opportunity cost of waiting is 12-18 months of elevated cost-to-close. Let's model the cost of delay against your current pipeline.

### OBJ_BNK_009: "We're too small to benefit from treasury management upgrades"
**Response:** SMB treasury clients are increasingly demanding API integrations, real-time reporting, and self-service capabilities. Losing 2-3 treasury clients to a competitor with modern capabilities can exceed $5M in deposit value. What is your average treasury client lifetime value?

### OBJ_BNK_010: "Digital banks don't need branches, so our cost structure is already optimized"
**Response:** While digital banks avoid branch costs, CAC and unit economics often remain challenging. Top digital banks achieve profitability through deposit balance growth, interchange optimization, and lending product cross-sell. What is your CLV-to-CAC ratio and monthly burn per active account?

---

## 13. Technology Systems (15)

| ID | System | Category | Key Function | Pain Links |
|----|--------|----------|--------------|------------|
| TS_BNK_001 | Core Banking (Fiserv/FIS/Jack Henry) | Core Platform | GL, deposits, loans, transactions | P_BNK_011, P_BNK_012 |
| TS_BNK_002 | Loan Origination System (LOS) | Lending | Application, underwriting, closing | P_BNK_002, P_BNK_014 |
| TS_BNK_003 | Digital Banking Platform | Customer Experience | Mobile, online, onboarding | P_BNK_006, P_BNK_003 |
| TS_BNK_004 | Treasury Management System | Commercial | Cash positioning, payments, forecasting | P_BNK_007, P_BNK_014 |
| TS_BNK_005 | Card Management Platform | Payments | Issuing, authorization, rewards | P_BNK_008, P_BNK_015 |
| TS_BNK_006 | RTP/FedNow Rails | Payments Infrastructure | Instant payment, 24/7 settlement | P_BNK_013, P_BNK_007 |
| TS_BNK_007 | Fraud Detection & Monitoring | Risk Management | Real-time scoring, AML, sanctions | P_BNK_013, P_BNK_006 |
| TS_BNK_008 | Commercial CRM | Commercial | Pipeline, RFP tracking, cross-sell | P_BNK_009, P_BNK_007 |
| TS_BNK_009 | Wealth Management Platform | Private Banking | Portfolio, reporting, advisor tools | P_BNK_010 |
| TS_BNK_010 | Document Management / eVault | Operations | E-sign, eNotes, audit trail | P_BNK_002, P_BNK_012 |
| TS_BNK_011 | Credit Decisioning Engine | Lending | Automated underwriting, risk scoring | P_BNK_009, P_BNK_002 |
| TS_BNK_012 | Regulatory Reporting Platform | RegTech | Call Report, Basel, CECL, BSA/AML | P_BNK_012, P_BNK_011 |
| TS_BNK_013 | Data Warehouse / Analytics | Data Infrastructure | Enterprise BI, customer analytics | P_BNK_011, P_BNK_010 |
| TS_BNK_014 | API Gateway / Integration | Integration | API management, fintech connectivity | P_BNK_011, P_BNK_017 |
| TS_BNK_015 | IDV and KYC Platform | Compliance | Document verification, biometrics | P_BNK_006, P_BNK_013 |

---

## 14. Regulatory Factors (12)

| ID | Regulation | Body | Impact | Cost | Status |
|----|------------|------|--------|------|--------|
| RF_BNK_001 | Basel III Endgame / Basel IV | Fed/FDIC/OCC | 10-20% RWA increase for large banks | $2M-50M/yr | Proposed; 2025-2028 |
| RF_BNK_002 | DFAST/CCAR | Federal Reserve | Annual stress testing >$100B | $5M-30M/yr | Active |
| RF_BNK_003 | CRA Modernization | FDIC/Fed/OCC | New evaluation framework | $1M-5M | Final rule; 2024-2026 |
| RF_BNK_004 | TRID / Regulation Z | CFPB | Mortgage disclosure timing/accuracy | $500K-3M/yr | Active |
| RF_BNK_005 | BSA/AML | FinCEN/OCC/FDIC | Transaction monitoring, beneficial ownership | $3M-25M/yr | Active; AML Act ongoing |
| RF_BNK_006 | CECL | FASB | Forward-looking lifetime credit loss | $2M-10M | Effective; CUs 2024-2025 |
| RF_BNK_007 | Durbin Amendment | Fed/Congress | Debit interchange cap; credit proposed | Revenue loss $5M-100M/yr | Debit active; credit proposed |
| RF_BNK_008 | Fair Lending / ECOA / HMDA | CFPB/DOJ/HUD | Anti-discrimination, AI underwriting scrutiny | $1M-5M/yr | Active |
| RF_BNK_009 | Section 1071 SMB Lending Data | CFPB | Demographic data collection for SMB loans | $2M-8M | Phased through 2025 |
| RF_BNK_010 | FedNow Participation | Federal Reserve | Instant payment rail compliance | $1M-10M | Live July 2023 |
| RF_BNK_011 | ASC 820 Fair Value | FASB | Illiquid asset valuation, CRE securities | $500K-3M | Active |
| RF_BNK_012 | NCUA Cybersecurity Framework | NCUA | IT examination, cybersecurity, vendor mgmt | $500K-2M | Active |

---

## 15. Worked Examples (3)

### WE_BNK_001: Regional Bank NIM Recovery
**Scenario:** $25B regional bank, deposit beta at 78%, NIM compressed to 2.85%
**Formula:** VF_BNK_001
**Calculation:** (0.78 - 0.55) * 0.025 * $25B * 0.85 = $122.2M annual pre-tax improvement
**Sensitivity:** $95M-$150M depending on rate trajectory
**Risks:** Competitive pricing war, rate reversal, deposit migration to MMFs

### WE_BNK_002: Mid-Size Bank Mortgage Operations Transformation
**Scenario:** $50B bank, 45,000 loans/year, cost-to-close $10,800, cycle 48 days, pull-through 62%
**Formula:** VF_BNK_002
**Calculation:** ($10,800 - $6,500) * 45,000 + (48 - 28) * $85 * 45,000 + pull-through improvement = $281.25M
**Sensitivity:** $220M-$340M
**Risks:** LOS migration, appraisal delays, regulatory exam during transition

### WE_BNK_003: National Bank RTP Fraud Prevention
**Scenario:** $200B bank, $15B RTP volume, detection latency 450ms, APP losses $42M/year
**Formula:** VF_BNK_013
**Calculation:** $60M + $14.7M + $5M + $3M = $82.7M annual value; net $70.7M after $12M implementation
**Sensitivity:** $55M-$105M
**Risks:** New fraud vectors, over-decline customer experience, legacy auth integration

---

## 16. Buying Triggers (15)

| ID | Trigger | Pain | Persona | Time | Budget |
|----|---------|------|---------|------|--------|
| BT_BNK_001 | NIM Compression Crisis | P_BNK_001 | CFO | HIGH | Medium |
| BT_BNK_002 | Mortgage Operations Cost Overrun | P_BNK_002 | Mortgage Ops VP | HIGH | High |
| BT_BNK_003 | Branch Network Rationalization Mandate | P_BNK_003 | Branch Ops Manager | MEDIUM | Medium |
| BT_BNK_004 | CRE Refinancing Cliff | P_BNK_004 | CLO | HIGH | Medium |
| BT_BNK_005 | Auto Lease Residual Crisis | P_BNK_005 | CLO | HIGH | Medium |
| BT_BNK_006 | Digital Onboarding Crisis | P_BNK_006 | Digital Product Owner | HIGH | High |
| BT_BNK_007 | Treasury Client Exodus | P_BNK_007 | Treasury Sales Officer | HIGH | High |
| BT_BNK_008 | Interchange Revenue Cliff | P_BNK_008 | Payments PM | MEDIUM | Medium |
| BT_BNK_009 | Commercial RFP Crisis | P_BNK_009 | CLO | HIGH | High |
| BT_BNK_010 | Private Banking Succession Event | P_BNK_010 | Head of Private Banking | MEDIUM | Medium |
| BT_BNK_011 | Core Vendor Lock-in Renewal | P_BNK_011 | CIO | MEDIUM | High |
| BT_BNK_012 | Efficiency Ratio Board Mandate | P_BNK_012 | CFO | HIGH | Medium |
| BT_BNK_013 | RTP Fraud Loss Spike | P_BNK_013 | Payments PM | HIGH | High |
| BT_BNK_014 | SMB Primary Bank Loss | P_BNK_014 | Head of SMB Banking | HIGH | Medium |
| BT_BNK_015 | Digital Bank Runway Crisis | P_BNK_017 | CFO | HIGH | Low |

---

## 17. Governance

| Attribute | Value |
|-----------|-------|
| Source Coverage | Mixed (public + subscription sources) |
| Confidence Level | HIGH |
| Last Updated | 2025-01-28 |
| Approved for Customer-Facing | Yes |
| Review Owner | Banking Vertical Subpack Creator (Phase 2) |
| Agent Swarm ID | banking-subpack-s4-1 |
| Parent Master Swarm ID | financial-services-master-v1 |

---

## 18. Evidence Sources (12)

| ID | Source | Type | Frequency | Access |
|----|--------|------|-----------|--------|
| ES_BNK_001 | FDIC Quarterly Banking Profile | Regulatory | Quarterly | Public |
| ES_BNK_002 | Federal Reserve H.8 Release | Regulatory | Weekly | Public |
| ES_BNK_003 | MBA Performance Reports | Industry Association | Quarterly | Membership |
| ES_BNK_004 | J.D. Power Banking Studies | Industry Research | Annual | Purchase |
| ES_BNK_005 | S&P Global Market Intelligence | Data Provider | Quarterly | Subscription |
| ES_BNK_006 | Nilson Report | Industry Publication | Monthly | Subscription |
| ES_BNK_007 | AFP Treasury Benchmark | Industry Association | Annual | Membership |
| ES_BNK_008 | CoStar / Trepp CRE Analytics | Data Provider | Monthly | Subscription |
| ES_BNK_009 | Experian / TransUnion / Equifax | Data Provider | Quarterly | Subscription |
| ES_BNK_010 | Cerulli Associates | Industry Research | Annual | Purchase |
| ES_BNK_011 | NCUA Credit Union Data | Regulatory | Quarterly | Public |
| ES_BNK_012 | CB Insights / PitchBook | Industry Research | Quarterly | Subscription |

---

*End of Banking Vertical Subpack documentation*
