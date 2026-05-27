# Fintech Subpack (S4.4) - OpenClaw SKILL.md

## Skill Identity Block

```yaml
skill_name: Fintech Subpack ValuePack
version: 1.0.0
domain: financial-services
pack_type: subpack
parent_master: financial-services-master-v1
description: >
  Vertical-specialized value intelligence for Fintech companies across Payments,
  Embedded Finance, Lending, BNPL, WealthTech, RegTech, InsurTech, Crypto/Digital
  Assets, Stablecoins, and Fraud/ID Verification. Provides AI-driven discovery,
  qualification, and value articulation for technology vendors and service providers
  targeting fintech operators. Extends the Financial Services Master with
  segment-specific pains, KPIs, signal rules, personas, formulas, benchmarks,
  regulatory factors, and technology systems.
```

---

## Triggers

Auto-load this skill when queries match any of the following patterns:

1. **"fraud chargeback rate"** / "Visa Mastercard monitoring program"
2. **"KYC onboarding friction"** / "identity verification drop-off"
3. **"embedded finance BaaS"** / "banking-as-a-service integration"
4. **"BNPL credit loss optimization"** / "buy-now-pay-later warehouse facility"
5. **"crypto custody compliance"** / "SEC Wells notice crypto"
6. "neobank unit economics" / "interchange revenue dependency"
7. "real-time payment rail adoption" / "FedNow RTP ISO 20022 migration"
8. "stablecoin reserve management" / "MiCA stablecoin authorization"
9. "RegTech alert fatigue" / "SAR filing backlog AML"
10. "lending platform warehouse line" / "fintech lending covenant pressure"
11. "payment authorization latency" / "false decline rate p99"
12. "cross-border payment FX margin" / "remittance settlement delay"

---

## Reasoning Flow

### Step 1: Detect Vertical Segment (Master First)
**Always load the Financial Services Master (`financial-services-master-v1`) before this subpack.**

The master provides:
- Value Driver Framework (Revenue Uplift, Cost Savings, Risk Reduction, Working Capital)
- Base Persona Archetypes (CFO, COO, CIO, CISO, CRO, CMO, CCO, Head of Digital, Head of Growth, General Counsel, Head of Operations, Controller, Treasurer, Head of Product, CDO, Head of AI/ML, Chief Model Risk Officer)
- Evidence Source Types and Benchmark Methodology
- Formula Templates, Signal Source Taxonomy, and Governance Framework
- KPI Base Schema and Taxonomy Segment "Fintech" with 12 sub-segments

**Determine the fintech sub-segment** from prospect signals:
- Payments, Embedded Finance, Lending Platforms, BNPL, Personal Finance/Neobank, BaaS, WealthTech, RegTech, InsurTech, Crypto/Digital Assets, Stablecoin Infrastructure, Fraud/ID Verification

### Step 2: Identify Relevant Signals
Apply the 20 vertical signal rules (FT-S001 through FT-S020) to detect specific fintech pain patterns:

| Signal Rule | Pattern | Confidence | Linked Pain |
|---|---|---|---|
| FT-S001 | p99 auth latency >500ms for 3+ days | 0.85 | FT-P001 |
| FT-S002 | KYC doc upload failure >30% in 7 days | 0.80 | FT-P002 |
| FT-S003 | Partner API volume down >20% MoM | 0.75 | FT-P003 |
| FT-S004 | BNPL 30+ DPD on 6mo vintages up >25% | 0.90 | FT-P004 |
| FT-S005 | Chargeback rate >0.80% rising | 0.88 | FT-P005 |
| FT-S006 | Crypto outflows >5% AUC in 48hrs | 0.82 | FT-P006 |
| FT-S007 | Alert volume >3 sigma above 90d mean | 0.78 | FT-P007 |
| FT-S008 | DAU/MAU down >15% over 90 days | 0.72 | FT-P008 |
| FT-S009 | Sponsor bank receives OCC consent order | 0.92 | FT-P009 |
| FT-S010 | Stablecoin de-peg >50bps for >1hr | 0.88 | FT-P010 |
| FT-S011 | Claims volume >2x forecast | 0.80 | FT-P011 |
| FT-S012 | ISO 20022 share <30%, deadline <12mo | 0.85 | FT-P012 |
| FT-S013 | Interchange revenue >85% for 3 quarters | 0.75 | FT-P013 |
| FT-S014 | Advance rate down >3pts or headroom <8% | 0.87 | FT-P014 |
| FT-S015 | FX spread >120bps vs competitor <60bps | 0.82 | FT-P015 |
| FT-S016 | Consent withdrawal >12% in 30 days | 0.76 | FT-P016 |
| FT-S017 | Third-party API failure >2x in 30 days | 0.83 | FT-P017 |
| FT-S018 | Operating in >5 unlicensed states, >$1M/mo | 0.90 | FT-P018 |
| FT-S019 | Monthly burn >$25M, runway <15mo | 0.86 | FT-P019 |
| FT-S020 | SEC Wells notice or banking partner terminates | 0.93 | FT-P020 |

**Confidence scoring guidance:**
- Requires at least 2 of 3 confirmation signals to elevate from MEDIUM to HIGH
- Requires at least 1 confirmation signal to trigger at LOW confidence
- Critical buying triggers (FT-BT001, BT002, BT003, BT007) elevate overall opportunity score regardless of individual signal confidence

### Step 3: Map Signals to Pains, KPIs, and Value Drivers
For each triggered signal:
1. Look up linked pain by ID (FT-P001 - FT-P020)
2. Retrieve linked KPIs with formulas, typical ranges, and benchmarks
3. Identify applicable value drivers (FT-VD001 - FT-VD040)
4. Categorize into Revenue Uplift, Cost Savings, Risk Reduction, or Working Capital

### Step 4: Identify Target Personas
Apply vertical personas from this subpack (6 specialized archetypes):

| Persona | ID | Primary Concerns |
|---|---|---|
| Fintech Product Manager | FT-PS001 | Feature adoption, time-to-value, monetization, quarterly OKRs |
| Payments Architect | FT-PS002 | Latency p99, uptime, scale, vendor lock-in, compliance |
| Crypto Compliance Officer | FT-PS003 | MTL coverage, regulatory exams, Travel Rule, SAR filing |
| Embedded Finance Partnerships Lead | FT-PS004 | Partner activation speed, bank diversification, revenue share |
| Fraud Ops Manager | FT-PS005 | Fraud losses, chargeback thresholds, false positives, APP scams |
| Growth/Growth Hacker | FT-PS006 | CAC efficiency, signup conversion, viral loops, payback period |

Inherited master personas (CFO, COO, CTO, CRO, CISO, General Counsel, etc.) apply for cross-cutting concerns.

### Step 5: Formulate Value Hypotheses
Use the 15 vertical value formulas (FT-VF001 - FT-VF015) with required inputs:

| Formula | Pain | Segment | Confidence Rules |
|---|---|---|---|
| FT-VF001 | Payment Authorization Value Uplift | Payments, Fintech | HIGH with auth logs |
| FT-VF002 | KYC Onboarding Efficiency | Fintech, Crypto | HIGH with funnel data |
| FT-VF003 | Embedded Finance Partner Activation | BaaS, Embedded Finance | HIGH with partner pipeline |
| FT-VF004 | BNPL Credit Loss Reduction | BNPL | HIGH with 24+ mo vintage |
| FT-VF005 | Fraud Chargeback Cost Avoidance | Payments, Fintech | HIGH with chargeback history |
| FT-VF006 | Crypto Custody Security Value | Crypto | HIGH with incident history |
| FT-VF007 | RegTech AML Efficiency | RegTech, Crypto | HIGH with 12-mo alert history |
| FT-VF008 | WealthTech AUM Growth | WealthTech | HIGH with cohort data |
| FT-VF009 | BaaS Sponsor Bank Diversification | BaaS | HIGH with deposit data |
| FT-VF010 | Stablecoin Reserve Risk Mitigation | Stablecoins | MED with attestation history |
| FT-VF011 | InsurTech Claims Speed Value | InsurTech | HIGH with claims cost data |
| FT-VF012 | Real-Time Payment Migration Revenue | Payments | HIGH with payment P&L |
| FT-VF013 | PFM Engagement Monetization | Personal Finance | HIGH with engagement data |
| FT-VF014 | Lending Warehouse Optimization | Lending, BNPL | HIGH with facility terms |
| FT-VF015 | Cross-Border Payment Margin Expansion | Payments | HIGH with corridor economics |

### Step 6: Validate with Discovery Questions
Use the 20 vertical discovery questions (FT-DQ001 - FT-DQ020) to confirm signal validity and quantify impact. Prioritize questions linked to triggered pains.

### Step 7: Address Objections
Apply the 10 vertical objection reframe patterns (FT-OBJ001 - FT-OBJ010) when encountering resistance.

---

## Inheritance Map

### Master Skill to Load First
**`financial-services-master-v1`** - Load this master before applying any fintech subpack reasoning.

### What This Subpack Adds Beyond the Master

| Component | Master | Fintech Subpack |
|---|---|---|
| Pains | Generic financial services pains | 20 vertical pains with segment-specific symptoms |
| KPIs | Base financial KPIs | 60 KPIs with fintech-specific formulas and benchmarks |
| Value Drivers | 4 base categories | 40 drivers mapped to fintech outcomes |
| Formulas | Base templates | 15 formulas with fintech input schemas |
| Personas | 17 base archetypes | 6 new vertical personas + inherited master archetypes |
| Signal Rules | Generic financial signals | 20 rules tuned for fintech velocity and risk patterns |
| Buying Triggers | Cross-industry triggers | 15 triggers for fintech-specific events (Wells notices, MTL gaps, warehouse renewals, ISO 20022 deadlines) |
| Technology Systems | Generic financial systems | 15 systems mapped to fintech vendor landscape |
| Regulatory Factors | Broad financial regulations | 12 factors specific to fintech (MiCA, MTL, BaaS guidance, APP scams) |

### When to Use Master vs. Subpack

| Scenario | Use |
|---|---|
| Traditional bank, insurer, or asset manager with no fintech operations | Master only |
| Mixed institution with fintech division | Master + Fintech Subpack |
| Pure-play fintech (Stripe, Klarna, Chime, Coinbase, etc.) | Fintech Subpack first, Master for cross-industry context |
| Technology vendor targeting fintech operators | Fintech Subpack for vertical-specific value articulation |

---

## Structured Output Template

### Expected JSON Format for Signals Analysis Enrichment

```json
{
  "pack_id": "fintech-v1",
  "pack_version": "1.0.0",
  "parent_master": "financial-services-master-v1",
  "analysis_timestamp": "2025-01-15T00:00:00Z",
  "prospect_segment": "Payments | Embedded Finance | Lending | BNPL | WealthTech | RegTech | InsurTech | Crypto | Stablecoins | Personal Finance | BaaS | Fraud/ID",
  "signal_analysis": {
    "triggered_signals": [
      {
        "rule_id": "FT-S001",
        "signal_name": "Payment Authorization Latency Spike",
        "confidence": 0.85,
        "raw_pattern_matched": "p99 authorization latency >500ms for 3+ consecutive days",
        "confirmation_signals_present": ["Processor status page degradation", "Transaction volume spike correlation"],
        "linked_pain_id": "FT-P001",
        "linked_kpi_ids": ["FT-K001", "FT-K002"]
      }
    ],
    "overall_opportunity_score": 0.82,
    "urgency_level": "HIGH | CRITICAL | MEDIUM | LOW"
  },
  "pain_profile": {
    "primary_pains": [
      {
        "pain_id": "FT-P001",
        "name": "Payment Authorization Latency and False Declines",
        "prevalence": "HIGH",
        "confidence": "HIGH",
        "symptoms_present": ["Authorization latency >500ms p99", "False decline rate >15%"],
        "affected_personas": ["Payments Architect", "Head of Product", "CTO", "CRO"]
      }
    ],
    "pain_count": 3,
    "coverage_score": 0.75
  },
  "kpi_baseline": {
    "kpis_assessed": [
      {
        "kpi_id": "FT-K001",
        "name": "Payment Authorization Latency (p99)",
        "current_value": 650,
        "unit": "milliseconds",
        "typical_range": "300-800",
        "benchmark_range": "80-200",
        "gap_from_benchmark": 450,
        "value_driver_links": ["FT-VD001", "FT-VD002"]
      }
    ]
  },
  "value_hypotheses": {
    "formulas_applied": [
      {
        "formula_id": "FT-VF001",
        "name": "Payment Authorization Value Uplift",
        "estimated_annual_value": 157200000,
        "currency": "USD",
        "confidence": "HIGH",
        "required_inputs_status": "complete | partial | missing",
        "inputs": {
          "false_decline_rate_reduction": 0.11,
          "transaction_volume": 2000000000,
          "latency_improvement_revenue": 15000000,
          "conversion_uplift": 0.03
        }
      }
    ],
    "total_estimated_value": 157200000,
    "value_categories": {
      "revenue_uplift": 144200000,
      "cost_savings": 3000000,
      "risk_reduction": 5000000,
      "working_capital": 0
    }
  },
  "persona_targeting": {
    "primary_personas": ["Payments Architect", "CTO", "CRO"],
    "inherited_personas": ["CFO", "Head of Product"],
    "persona_specific_messaging": {
      "Payments Architect": "Sub-100ms p99 authorization with failover architecture",
      "CRO": "$143M annual revenue recovery from false decline reduction"
    }
  },
  "buying_trigger_alignment": {
    "trigger_detected": "FT-BT001: Card Network Monitoring Program Enrollment",
    "urgency": "CRITICAL",
    "timing_window": "0-30 days from notification",
    "procurement_implications": "Emergency procurement with simplified vendor selection; budget reallocation from growth to risk"
  },
  "regulatory_factors": {
    "applicable_regulations": ["FT-RF008: PCI DSS Level 1", "FT-RF009: UK APP Scam Reimbursement"],
    "compliance_deadlines": ["PCI DSS v4.0 migration: March 2025"],
    "penalty_exposure": 5000000
  },
  "governance": {
    "confidence_level": "HIGH",
    "source_coverage": "Mixed",
    "customer_facing_approved": false,
    "review_owner": "Fintech Subpack Architect - Vertical Intelligence Swarm"
  }
}
```

---

## Governance Metadata

| Attribute | Value |
|---|---|
| **Confidence Level** | High |
| **Source Coverage** | Mixed (industry research, regulatory guidance, public filings, technology provider benchmarks) |
| **Customer-Facing Approval Status** | No - Not approved for direct customer-facing use without review owner sign-off |
| **Review Owner** | Fintech Subpack Architect - Vertical Intelligence Swarm |
| **Agent Swarm ID** | kimi-k2.6-swarm-s4.4-fintech |
| **Parent Master Swarm ID** | kimi-k2.6-swarm-m4-financial-services |
| **Last Updated** | 2025-01-15 |
| **Next Review Date** | 2025-04-15 |

---

## Quick Reference

### Top 5 Pains (by Prevalence and Confidence)

| # | ID | Pain | Segment |
|---|---|---|---|
| 1 | FT-P005 | Fraud Chargeback Rate Exceeding Card Network Thresholds | Payments |
| 2 | FT-P001 | Payment Authorization Latency and False Declines | Payments |
| 3 | FT-P002 | KYC Onboarding Drop-off and Compliance Friction | Fintech, Crypto |
| 4 | FT-P003 | Embedded Finance Integration Complexity | BaaS, Embedded Finance |
| 5 | FT-P004 | BNPL Credit Loss Escalation and Funding Cost Pressure | BNPL |

### Top 5 KPIs (by Revenue Impact Potential)

| # | ID | KPI | Typical | Benchmark | Unit |
|---|---|---|---|---|---|
| 1 | FT-K001 | Payment Authorization Latency (p99) | 300-800 | 80-200 | ms |
| 2 | FT-K002 | False Decline Rate | 10-25 | 3-8 | % |
| 3 | FT-K013 | Fraud Chargeback Rate | 0.6-1.5 | 0.2-0.5 | % |
| 4 | FT-K010 | BNPL Net Loss Rate | 5-12 | 2-5 | % |
| 5 | FT-K004 | KYC Onboarding Completion Rate | 30-55 | 65-85 | % |

### Top 3 Personas (by Decision Authority)

| # | ID | Persona | Influence | Primary Concern |
|---|---|---|---|---|
| 1 | FT-PS005 | Fraud Ops Manager | technical | Keep fraud losses <0.30% volume, chargebacks below thresholds |
| 2 | FT-PS003 | Crypto Compliance Officer | economic | MTL coverage, pass exams, Travel Rule, defensible AML |
| 3 | FT-PS002 | Payments Architect | technical | Sub-100ms p99 latency, 99.999% uptime, 10x scale |

### Key Value Formulas

| ID | Formula | Segment | Example Output |
|---|---|---|---|
| FT-VF001 | `(False_Decline_Reduction * Volume) + (Latency_Improvement * Conversion)` | Payments | $500M+ annual recovery |
| FT-VF004 | `(Net_Loss_Reduction * Receivables) + (Collection_Savings) + (Spread_Reduction * Borrowed)` | BNPL | $79M annual value |
| FT-VF005 | `(Chargeback_Reduction * Volume) + (Recovery_Improvement) + (Fine_Avoidance) + (Retention)` | Payments | $27M annual avoidance |
| FT-VF009 | `(Risk_Premium_Reduction * Deposits) + (Termination_Avoidance) + (Compliance_Savings)` | BaaS | $70M annual value |
| FT-VF007 | `(False_Positive_Reduction * Alerts * Cost) + (FTE_Reduction * Loaded_Cost) + (SAR_Avoidance)` | RegTech | $20M annual savings |

---

*This subpack is a vertical specialization of the Financial Services Master ValuePack (financial-services-master-v1). Do not duplicate master content. Reference master components for base frameworks, shared personas, and cross-industry benchmarks.*
