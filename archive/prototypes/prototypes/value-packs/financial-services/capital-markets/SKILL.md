# Capital Markets Subpack

## Skill Identity Block

| Field | Value |
|-------|-------|
| **skill_name** | Capital Markets Subpack |
| **description** | Vertical-specialized value intelligence for Capital Markets institutions including asset management, wealth management, brokerage, hedge funds, PE/VC, market makers, exchanges, clearing/settlement, custody, securities lending, and research. Provides deep pain points, KPIs, formulas, benchmarks, signal rules, personas, and buying triggers specific to trading, portfolio management, fund operations, and securities servicing. |
| **version** | 1.0.0 |
| **domain** | Capital Markets / Financial Services |
| **pack_type** | subpack |
| **parent_master** | financial-services-master-v1 |
| **id** | capital-markets-v1 |
| **last_updated** | 2026-04-25 |
| **agent_swarm_id** | kimi-k2.6-swarm-s4.2-capital-markets |

**Vertical Focus:** Asset Management, Wealth Management, Brokerage, Hedge Funds, Private Equity, Venture Capital, Market Makers/Liquidity Providers, Exchanges/Trading Venues, Clearing/Settlement, Custody Services, Securities Lending, Research/Analytics

---

## Triggers

Auto-load this skill when natural language queries contain patterns like:

1. **"T+1 settlement fail rate"** – Settlement efficiency, CSDR penalties, post-trade operations
2. **"portfolio reconciliation breaks"** – NAV risk, IBOR/ABOR divergence, shadow accounting
3. **"securities lending revenue"** – Utilization optimization, collateral velocity, borrower pricing
4. **"NAV restatement risk"** – Fund admin quality, NAV production SLA, operational control
5. **"best execution review"** – TCA gaps, MiFID II compliance, venue analysis, implementation shortfall
6. **"FX transaction cost analysis"** – WM/Reuters benchmark slippage, last look, NDF settlement
7. **"derivatives margin management"** – UMR compliance, collateral optimization, margin call disputes
8. **"ESG data integration"** – SFDR PAI reporting, ESG score variance, carbon footprint calculation
9. **"quant model deployment bottleneck"** – Research-to-production pipeline, backtesting, alpha decay
10. **"liquidity stress testing gaps"** – Redemption gate risk, intraday monitoring, scenario coverage
11. **"corporate actions processing failures"** – Event notification, election processing, revenue leakage
12. **"Form PF or AIFMD reporting burden"** – Regulatory filing timeliness, data quality, aggregation workflow

---

## Reasoning Flow

### Step 1: Load Parent Master First
Before applying Capital Markets-specific reasoning, ensure the **financial-services-master-v1** skill is loaded. The master provides foundational value drivers (VD001-VD051), base persona archetypes (PER001-PER014), evidence taxonomy, formula templates, base regulatory factors, and signal taxonomy.

### Step 2: Identify the Target Sub-Segment
Classify the prospect into one or more Capital Markets sub-segments:
- Asset Management (active/passive, mutual funds, ETFs, SMAs)
- Wealth Management (HNW, UHNW, advisory platforms)
- Brokerage (retail, institutional, prime brokerage)
- Hedge Funds (multi-strategy, quant, macro, credit)
- Private Equity / Venture Capital (GPs, fund-of-funds)
- Market Makers / Liquidity Providers
- Exchanges / Trading Venues
- Clearing / Settlement
- Custody Services
- Securities Lending
- Research / Analytics

### Step 3: Map Raw Signals to Signal Interpretation Rules
Match observed signals against the 20 Capital Markets signal rules (CM-SR001 to CM-SR020). For each matched signal:
1. Note the confidence score (0.78-0.93 range)
2. Identify required confirmation signals
3. Map to linked pains (CM-P001 to CM-P018)
4. Map to linked KPIs (CM-K001 to CM-K024)

**Confidence Scoring Guidance:**
- **HIGH (0.88-0.93):** Direct operational data (reconciliation breaks, NAV restatements, margin call disputes, settlement fails)
- **MEDIUM-HIGH (0.84-0.87):** Regulatory filing patterns, proxy voting records, research budget trends
- **MEDIUM (0.78-0.82):** Quant team hiring patterns, ESG score changes, market data spend trends
- Use confirmation signals to upgrade confidence; missing confirmation signals downgrade by one level

### Step 4: Interpret Signals Using Pack Rules
Apply the signal-to-pain mapping:

| Signal Category | Signal Rule | Linked Pain | Primary KPI |
|-----------------|-------------|-------------|-------------|
| Reconciliation break spike | CM-SR001 | CM-P001 | CM-K001 |
| IBOR/ABOR divergence | CM-SR002 | CM-P002 | CM-K002 |
| Securities lending revenue decline | CM-SR003 | CM-P003 | CM-K003 |
| Best execution review findings | CM-SR004 | CM-P004 | CM-K005 |
| MiFID II research payment pressure | CM-SR005 | CM-P005 | CM-K007 |
| Proxy voting season failures | CM-SR006 | CM-P006 | CM-K008 |
| Derivatives margin call spike | CM-SR007 | CM-P007 | CM-K009 |
| FX transaction cost complaint | CM-SR008 | CM-P008 | CM-K010 |
| ESG rating downgrade impact | CM-SR009 | CM-P009 | CM-K011 |
| Risk aggregation system outage | CM-SR010 | CM-P010 | CM-K012 |
| Fund admin SLA breach | CM-SR011 | CM-P011 | CM-K013 |
| NAV restatement event | CM-SR012 | CM-P011, CM-P002 | CM-K014 |
| Corporate actions processing delay | CM-SR013 | CM-P013 | CM-K016 |
| Form PF filing delay | CM-SR014 | CM-P014 | CM-K017 |
| AIFMD reporting breach | CM-SR015 | CM-P014 | CM-K018 |
| Quant model deployment bottleneck | CM-SR016 | CM-P015 | CM-K019 |
| Client report SLA miss | CM-SR017 | CM-P016 | CM-K020 |
| Liquidity stress test failure | CM-SR018 | CM-P017 | CM-K021 |
| Market data cost inflation | CM-SR019 | CM-P018 | CM-K012 |
| Custody asset servicing break spike | CM-SR020 | CM-P013, CM-P001 | CM-K024 |

### Step 5: Map to Personas and Value Drivers
For each identified pain, determine:
- **Affected Personas:** Use the pain's affectedPersonas field (CM-PER001-PER006 + master personas)
- **Value Driver Category:** Cost Savings, Risk Reduction, Revenue Uplift, Working Capital
- **Required Evidence:** Document what proof is needed to validate the hypothesis

### Step 6: Quantify with Value Formulas
Select the appropriate formula from CM-VF001 to CM-VF012:
1. Gather required inputs from customer or benchmark data
2. Apply confidence rules to determine output reliability
3. Run sensitivity analysis on key variables
4. Present annual value in USD with confidence label

### Step 7: Assess Buying Readiness
Map to buying triggers (CM-BT001 to CM-BT015) to determine urgency:
- **CRITICAL:** 0-3 months procurement window (regulatory events, NAV restatements, client SLA breaches)
- **HIGH:** 3-6 months window (contract renewals, revenue declines, PM turnover)
- **MEDIUM:** 6-12 months window (infrastructure scaling, competitive displacement)

### Step 8: Inheritance-Aware Value Hypothesis
Combine master-level value drivers with vertical-specific additions:
- Use master formulas for base operational metrics (settlement efficiency, trade matching)
- Use Capital Markets formulas for specialized metrics (reconciliation, NAV production, securities lending, TCA)
- Override master benchmarks with Capital Markets-specific benchmarks (e.g., post-T+1 settlement fail rate targets)

---

## Inheritance Map

### Master Skill to Load First
**financial-services-master-v1**

### What This Subpack Adds Beyond the Master

| Component | Master Provides | Subpack Adds |
|-----------|----------------|--------------|
| **Pains** | 5 base pains (P001, P008, P009, P015, P024) | 18 vertical pains (CM-P001 to CM-P018) covering reconciliation, IBOR/ABOR, securities lending, best execution, research unbundling, proxy voting, derivatives margin, FX slippage, ESG fragmentation, risk aggregation latency, fund admin, PE/VC waterfalls, corporate actions, Form PF/AIFMD, quant deployment, client reporting, liquidity stress testing, market data costs |
| **KPIs** | Base KPIs (K001-K002, K024-K029, etc.) | 24 vertical KPIs (CM-K001 to CM-K024) with Capital Markets-specific formulas |
| **Signal Rules** | Base rules (SR002, SR008-SR009, SR015, SR024) | 20 vertical signal rules (CM-SR001 to CM-SR020) |
| **Personas** | Base archetypes (PER001-PER014) | 6 new personas: Portfolio Manager, Trade Operations Manager, Middle Office Director, Research Analyst/Quant, Fund Administrator, Securities Lending Trader |
| **Formulas** | Base templates (VF001-VF025) | 12 vertical formulas (CM-VF001 to CM-VF012) |
| **Benchmarks** | Base benchmarks | 18 vertical benchmarks (CM-B001 to CM-B018) |
| **Technology Systems** | Base systems (TS004-TS005, TS008-TS009, etc.) | 15 vertical systems (CM-TS001 to CM-TS015): OMS, PMS, IBOR, ABOR, Reconciliation Engine, Risk Analytics, Securities Lending Platform, Custody Platform, Fund Admin System, Market Data Platform, Best Execution/TCA, ESG Platform, Transfer Agency, Derivatives Margin, Corporate Actions Engine |
| **Regulatory Factors** | Base factors (RF003, RF010-RF011, RF013) | 10 vertical factors (CM-RF001 to CM-RF010): T+1 Settlement, MiFID II/MiFIR, SEC Rule 15c3-3, Form PF, AIFMD, CSDR, SFDR, SEC Marketing Rule, EMIR/Dodd-Frank, SEC Short Sale Disclosure |
| **Buying Triggers** | Base triggers (BT004, BT008, BT010, BT017, BT024) | 15 vertical triggers (CM-BT001 to CM-BT015) |
| **Discovery Questions** | – | 20 targeted questions (CM-DQ001 to CM-DQ020) |
| **Objections** | – | 10 objection patterns with reframes (CM-OBJ001 to CM-OBJ010) |
| **Worked Examples** | – | 3 worked examples with sensitivity analysis (CM-WE001 to CM-WE003) |

### When to Use Master vs. Subpack
- **Use Master Only:** For general financial services firms (commercial banking, insurance, retail banking) with no Capital Markets operations
- **Use Master + Subpack:** For firms with Capital Markets operations (always load master first, then subpack)
- **Use Subpack Only:** When the query is explicitly Capital Markets-specific (e.g., "securities lending revenue optimization") and master context is already loaded

### Overridden Components
- **Settlement Fail Rate Benchmark (B018):** Updated for post-T+1 transition period (May 2024+); CSDR penalty context added; target range reduced from 3-7% to 2-5%
- **Trade Matching Automation Rate Benchmark (B019):** Extended to include post-trade affirmation and ALERT matching for T+1; expanded segment applicability to clearing firms

---

## Structured Output Template

### Signals Analysis Enrichment (JSON)

```json
{
  "skill_loaded": "capital-markets-v1",
  "parent_master": "financial-services-master-v1",
  "analysis_timestamp": "2026-04-25T00:00:00Z",
  "prospect_segmentation": {
    "primary_segments": ["Asset Management", "Hedge Funds"],
    "secondary_segments": ["Brokerage"],
    "confidence": "HIGH"
  },
  "detected_signals": [
    {
      "signal_id": "CM-SR001",
      "signal_name": "Portfolio Reconciliation Break Spike",
      "raw_signal": "Daily reconciliation breaks increased >50% above 90-day baseline with >10% aged >3 days",
      "confidence": 0.9,
      "confirmation_status": "confirmed",
      "confirmation_sources": ["Break aging report", "NAV production timeline", "System change log"],
      "linked_pains": ["CM-P001"],
      "linked_kpis": ["CM-K001", "CM-K002"],
      "linked_personas": ["CM-PER002", "CM-PER003", "COO"],
      "value_driver_category": "Cost Savings",
      "urgency": "high"
    }
  ],
  "pain_analysis": [
    {
      "pain_id": "CM-P001",
      "pain_name": "Portfolio Reconciliation Break Escalation",
      "prevalence": "HIGH",
      "confidence": "HIGH",
      "affected_personas": ["CM-PER002", "CM-PER003", "COO", "CIO"],
      "symptoms_matched": 3,
      "symptoms_total": 5,
      "sources": ["ISDA Operations Benchmarking 2024", "SS&C Advent Industry Survey", "DTCC Data Analytics"]
    }
  ],
  "kpi_benchmarks": [
    {
      "kpi_id": "CM-K001",
      "kpi_name": "Portfolio Reconciliation Break Rate",
      "current_value": 2.5,
      "current_unit": "percentage",
      "typical_range": "0.5-3.0",
      "benchmark_range": "0.1-0.5",
      "gap_to_benchmark": 2.0,
      "benchmark_source": "CM-B001"
    }
  ],
  "value_hypothesis": {
    "formula_id": "CM-VF001",
    "formula_name": "Reconciliation Automation Value",
    "annual_value_usd": 22100000,
    "confidence": "HIGH",
    "inputs": {
      "Break_Reduction_Per_Day": 300,
      "Cost_Per_Break": 250,
      "Trading_Days": 252,
      "FTE_Reduction": 8,
      "Loaded_Cost_Per_FTE": 150000,
      "NAV_Restatement_Avoidance_Value": 2000000
    },
    "sensitivity_analysis": {
      "conservative_value_usd": 15000000,
      "optimistic_value_usd": 30000000
    }
  },
  "persona_engagement_map": [
    {
      "persona_id": "CM-PER002",
      "persona_name": "Trade Operations Manager",
      "decision_influence": "technical",
      "engagement_priority": 1,
      "recommended_discovery_questions": ["CM-DQ001", "CM-DQ012"],
      "trusted_evidence_types": ["DTCC/NSCC settlement data", "ISDA operations benchmarking", "Vendor SLA performance reports"]
    }
  ],
  "buying_triggers": [
    {
      "trigger_id": "CM-BT001",
      "trigger_name": "T+1 Settlement Penalty Spike",
      "urgency_level": "critical",
      "typical_timing": "0-3 months post-spike",
      "procurement_implications": "Emergency procurement authorized; STP and matching platform priority"
    }
  ],
  "regulatory_factors": [
    {
      "reg_id": "CM-RF001",
      "reg_name": "T+1 Settlement (US Securities)",
      "applicability": "Applicable",
      "deadline": "May 28, 2024 (implemented); ongoing optimization required",
      "penalty_exposure": "CSDR cash penalties (0.5-1% of trade value); settlement fails"
    }
  ],
  "competitor_threats": [
    {
      "threat_id": "CM-CF001",
      "threat_name": "Zero-Fee ETF and Index Fund Displacement",
      "confidence": "HIGH",
      "impact": "AUM migration to passive; fee compression on active strategies"
    }
  ],
  "next_actions": [
    "Validate reconciliation break data with prospect operations team",
    "Request NAV production timeline and restatement history",
    "Confirm FTE allocation in trade operations and middle office",
    "Map current technology stack against CM-TS001-CM-TS015",
    "Schedule discovery call with Trade Operations Manager (CM-PER002)"
  ]
}
```

---

## Governance Metadata

| Field | Value |
|-------|-------|
| **Confidence Level** | High (most signals 0.84-0.93; sources include DTCC, SEC filings, ISDA, AIMA, ESMA) |
| **Source Coverage** | Mixed – Regulatory data (HIGH), Industry surveys (HIGH/MEDIUM), Vendor benchmarks (MEDIUM), Proprietary data (HIGH) |
| **Customer-Facing Approval Status** | **NOT APPROVED** – All value formulas, benchmarks, and signal interpretations must be validated with customer-specific data before use in revenue-facing situations |
| **Review Owner** | Capital Markets Vertical Intelligence Architect |
| **Last Updated** | 2026-04-25 |
| **Disclaimer** | This pack contains intelligence synthesized from public sources. Confidence ratings indicate source reliability, not outcome certainty. The Capital Markets vertical is subject to rapid regulatory and technological change; verify all regulatory deadlines and applicability with current regulatory guidance. |

### Confidence and Validation Rules
- **HIGH confidence:** Direct regulatory filing (Form PF, SEC 10-K), DTCC operational data, or first-party reconciliation metrics
- **MEDIUM confidence:** Industry surveys (AIMA, ISDA, SIFMA), vendor benchmarks, or earnings call statements
- **LOW confidence:** Social sentiment, job posting inference, or speculative market analysis
- **Customer validation required:** All value formulas, benchmark applicability, and signal interpretations must be validated with customer-specific data before use in customer-facing business cases

---

## Quick Reference

### Top 5 Pains

| ID | Pain | Prevalence | Primary Segments |
|----|------|------------|------------------|
| CM-P001 | Portfolio Reconciliation Break Escalation | HIGH | Asset Management, Hedge Funds, Wealth Management, Brokerage |
| CM-P004 | Best Execution and TCA Gaps | HIGH | Asset Management, Brokerage, Hedge Funds, Market Makers |
| CM-P007 | Derivatives Collateral and Margin Management Complexity | HIGH | Asset Management, Hedge Funds, Brokerage, Market Makers |
| CM-P011 | Fund Administration Cost and SLA Erosion | HIGH | Asset Management, Hedge Funds, Private Equity |
| CM-P018 | Market Data Cost Inflation and Vendor Lock-in | HIGH | Asset Management, Hedge Funds, Brokerage, Market Makers, Exchanges |

### Top 5 KPIs

| ID | KPI | Formula | Typical | Benchmark | Unit |
|----|-----|---------|---------|-----------|------|
| CM-K001 | Portfolio Reconciliation Break Rate | `(Unreconciled Breaks / Total Positions) * 100` | 0.5-3.0 | 0.1-0.5 | percentage |
| CM-K006 | TCA Slippage (Implementation Shortfall) | `((Actual Execution Price - Decision Price) / Decision Price) * 10000` | 15-40 | 5-15 | basis points |
| CM-K009 | Derivatives Margin Efficiency | `(Net Margin Required / Gross Exposure) * 100` | 8-20 | 5-12 | percentage |
| CM-K014 | NAV Accuracy Rate | `((NAVs Correct First Time / Total NAVs Produced) * 100)` | 95-98 | 99.5-99.9 | percentage |
| CM-K012 | Risk Aggregation Latency | `Minutes from market data close to consolidated risk report availability` | 120-360 | 10-60 | minutes |

### Top 3 Personas

| ID | Persona | Role | Decision Influence | Key Pressure |
|----|---------|------|-------------------|--------------|
| CM-PER001 | Portfolio Manager | Portfolio Management | economic | Fee compression; best execution scrutiny; ESG mandates |
| CM-PER003 | Middle Office Director | Middle Office / Investment Operations | technical | IBOR/ABOR reconciliation; NAV timeline compression; regulatory reporting |
| CM-PER005 | Fund Administrator | Fund Administration / Transfer Agency | economic | NAV production SLA; complex instrument coverage; fee compression |

### Key Value Formulas

| ID | Formula | Example Output | Confidence Rule |
|----|---------|---------------|-----------------|
| CM-VF001 | Reconciliation Automation Value | $22.1M/year | HIGH with current break data |
| CM-VF002 | Securities Lending Revenue Optimization | $24.5M/year | HIGH with lending program data |
| CM-VF003 | TCA-Driven Execution Cost Reduction | $107M/year | HIGH with transaction data |
| CM-VF004 | Fund Administration Cost Efficiency | $9.5M/year | HIGH with admin contract data |
| CM-VF006 | Derivatives Margin Optimization | $15.5M/year | HIGH with derivatives portfolio data |

---

*End of SKILL.md – Capital Markets Subpack (S4.2)*
