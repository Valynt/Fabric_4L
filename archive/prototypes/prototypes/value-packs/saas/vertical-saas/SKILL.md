# Vertical SaaS Subpack (S2.2) - SKILL.md

## Skill Identity Block

| Field | Value |
|-------|-------|
| **skill_name** | Vertical SaaS Subpack |
| **description** | Industry-specific value intelligence for 14 vertical SaaS segments including Healthcare, Fintech, GovTech, EdTech, PropTech, LegalTech, InsurTech, ConstructionTech, AgTech, RetailTech, RestaurantTech, LogisticsTech, EnergyTech, and Manufacturing SaaS. Covers vertical-specific pains, compliance requirements, legacy system integrations, seasonal dynamics, workflow-embedded value propositions, and regulatory frameworks. Designed for enterprise sellers targeting vertical SaaS buyers where horizontal tools fail on industry nuance. |
| **version** | 1.0.0 |
| **domain** | industry |
| **pack_type** | subpack |
| **parent_master** | saas-master-v1 |
| **id** | vertical-saas-v1 |
| **last_updated** | 2025-04-25 |

---

## Triggers

Auto-load this skill when queries match these natural language patterns:

1. **"healthcare SaaS workflow"** - Targets Healthcare SaaS (EHR, practice management, RCM) with HIPAA compliance, HL7 FHIR integration, and patient intake workflow gaps.
2. **"fintech embedded finance"** - Targets Fintech SaaS with embedded payments, lending, core banking integrations, PCI-DSS, and money transmission licensing.
3. **"GovTech permitting"** - Targets GovTech with FedRAMP, RFP procurement cycles, public bidding, and government IT modernization.
4. **"EdTech student success"** - Targets EdTech with FERPA compliance, SIS integrations, institutional learning analytics, and campus-wide deployments.
5. **"PropTech MLS integration"** - Targets PropTech with RESO data standards, MLS connectivity, title insurance workflows, and multi-state regulatory requirements.
6. **"ConstructionTech field operations"** - Targets ConstructionTech with offline mobile, BIM integration, project management, and OSHA compliance.
7. **"vertical SaaS compliance burden"** - Cross-vertical regulatory pain mapping to HIPAA, SOX, FedRAMP, FERPA, GLBA, DOT, OSHA.
8. **"restaurant POS payments monetization"** - Targets RestaurantTech with embedded payments, take rate optimization, delivery aggregator integrations.
9. **"vertical SaaS TAM saturation"** - Market penetration analysis, adjacent vertical expansion, and horizontal competitor encroachment.
10. **"AgTech seasonal revenue volatility"** - Targets AgTech with seasonality, field IoT, farm management, and harvest-cycle infrastructure scaling.
11. **"InsurTech policy administration"** - Targets InsurTech with ACORD standards, claims processing, underwriting automation, and state DOI compliance.
12. **"vertical SaaS legacy system replacement"** - Legacy EOL signals, integration backlogs, and horizontal-to-vertical migration pain.

---

## Reasoning Flow

### Step 1: Identify the Target Vertical
Determine which of the 14 vertical segments the prospect/account operates in:
- Healthcare SaaS | Fintech SaaS | GovTech | EdTech | PropTech | LegalTech | InsurTech
- ConstructionTech | AgTech | RetailTech | RestaurantTech | LogisticsTech | EnergyTech | Manufacturing SaaS

If the account spans multiple verticals, score each vertical independently and prioritize the core revenue vertical.

### Step 2: Inheritance Check - Load Master First
Before applying this subpack, ensure the master skill `saas-master-v1` is loaded. The master provides:
- Base value driver taxonomy (VD001-VD050): Revenue Uplift, Cost Savings, Risk Reduction, Working Capital
- 14 generic SaaS persona archetypes (CFO, CRO, CTO, VP Sales, VP Marketing, CIO, CISO, CHRO, COO, VP Product, VP Engineering, VP Customer Success, VP RevOps, Controller)
- Base benchmark methodology and governance framework
- Horizontal SaaS signal taxonomy and formula templates (CAC, LTV, NRR, GRR, Win Rate, Churn, Gross Margin, Pipeline Velocity)

This subpack **does not replace** the master; it **extends** it with vertical-specialized components.

### Step 3: Detect Vertical-Specific Signals
Scan for signals using the 20 vertical signal rules (VS-S001 to VS-S020):

| Signal Category | Key Rules | Confidence |
|-------------------|-----------|------------|
| Regulatory | VS-S003 (Regulatory Deadline), VS-S007 (Security Incident), VS-S013 (AI Regulation) | 83-88% |
| Legacy Systems | VS-S004 (Legacy EOL), VS-S016 (Interoperability Mandate) | 84-88% |
| Competitive | VS-S002 (Horizontal Module Launch), VS-S005 (PE Roll-Up), VS-S017 (M&A) | 71-80% |
| Operational | VS-S006 (Seasonal Surge), VS-S015 (Mobile Decline), VS-S011 (Q1 Churn Spike) | 76-82% |
| Market Dynamics | VS-S001 (Trade Show Decline), VS-S008 (Hiring Spree), VS-S018 (Localization Failure) | 72-80% |
| Financial | VS-S012 (Payments Scrutiny), VS-S010 (IoT Mandate) | 77-79% |
| Platform | VS-S020 (API/Platform Demand), VS-S014 (Marketplace Launch) | 71-77% |
| Talent | VS-S019 (Talent Poaching) | 73% |

**Confirmation Protocol:** Each signal has required confirmation signals. Only elevate confidence above the base score when 1+ confirmation signals are present. Cap confidence at 0.95.

### Step 4: Map Signals to Pains
Use the `linkedPains` field on each signal rule to identify which of the 20 vertical pains (VS-P001 to VS-P020) are active. Filter by whether the pain's `affectedVerticals` includes the target vertical.

**Priority Pain Framework:**
- **HIGH prevalence pains** (apply to most accounts in vertical): VS-P001, VS-P002, VS-P003, VS-P004, VS-P005, VS-P008, VS-P010, VS-P011, VS-P017
- **MEDIUM prevalence pains** (context-dependent): VS-P006, VS-P007, VS-P009, VS-P012, VS-P013, VS-P014, VS-P015, VS-P016, VS-P018, VS-P019, VS-P020

### Step 5: Map Pains to Personas
Each pain lists `affectedPersonas`. Cross-reference with the 6 vertical-specific personas:

| Persona | ID | Influence | Primary Pains |
|---------|-----|-----------|---------------|
| Vertical SaaS Product Manager | VS-PE001 | Technical | VS-P001, VS-P011, VS-P016, VS-P018 |
| Industry Solutions Engineer | VS-PE002 | Technical | VS-P001, VS-P005, VS-P016, VS-P019 |
| Vertical GTM Lead | VS-PE003 | Economic | VS-P004, VS-P006, VS-P010, VS-P015 |
| Vertical Compliance and Risk Officer | VS-PE004 | Economic | VS-P002, VS-P003, VS-P013, VS-P014 |
| Vertical Customer Success Director | VS-PE005 | User | VS-P007, VS-P008, VS-P011, VS-P019 |
| Vertical SaaS CFO / Finance VP | VS-PE006 | Economic | VS-P006, VS-P007, VS-P008, VS-P009, VS-P010 |

**Note:** The master pack's 14 base personas are also relevant. Use vertical personas when the account shows vertical-specific pain intensity; use base personas for generic SaaS economics.

### Step 6: Quantify with KPIs and Formulas
For each active pain, calculate impact using linked KPIs and value formulas:

1. **Select KPIs** from the pain's `linkedKPIs` array (VS-K001 to VS-K060)
2. **Compare against benchmarks** (VS-B001 to VS-B020) to determine severity
3. **Apply value formula** (VS-VF001 to VS-VF015) to quantify annual impact in USD
4. **Document inputs and confidence** per formula's `confidenceRules`

### Step 7: Build Value Hypotheses
Structure value hypotheses using the Value Driver Maps (VS-VD001 to VS-VD010):

| Category | Driver Maps | Formula Examples |
|----------|-------------|-------------------|
| Cost Savings | VS-VD001 (Workflow Gap), VS-VD003 (Tenant Isolation), VS-VD005 (Legacy Integration) | VS-VF001, VS-VF003, VS-VF005 |
| Revenue Uplift | VS-VD002 (Compliance Delay), VS-VD004 (Sales Talent), VS-VD006 (TAM Saturation), VS-VD009 (Payments Margin) | VS-VF002, VS-VF004, VS-VF006, VS-VF008 |
| Working Capital | VS-VD007 (Seasonality Cash Flow), VS-VD010 (GovTech Sales Cycle) | VS-VF007, VS-VF009 |
| Risk Reduction | VS-VD008 (Customer Concentration) | VS-VF014 |

### Step 8: Confidence Scoring Guidance

| Factor | Scoring Rule |
|--------|-------------|
| Signal confidence | Base score from signal rule (0.71-0.88) + 0.1 if confirmation signals present |
| Pain confidence | Inherited from pain definition (HIGH/MEDIUM/LOW) |
| Formula confidence | HIGH if inputs from customer time-motion study; MEDIUM if estimated from benchmarks; LOW if speculative |
| Overall pack confidence | Weighted average: 40% signal confidence + 30% pain confidence + 30% formula input quality |

**Customer-facing threshold:** Only present quantified value when overall confidence >= 0.75. For 0.60-0.74, present as directional estimate with caveats. Below 0.60, use for internal prioritization only.

---

## Inheritance Map

### Master Skill to Load First
**`saas-master-v1`** - The SaaS Master ValuePack must be loaded before this subpack. It provides the foundational framework that this subpack extends.

### What This Subpack Adds Beyond the Master

| Component | Master Base | Subpack Addition |
|-----------|-------------|------------------|
| **Business Pains** | 0 (horizontal) | +20 vertical-specific pains (VS-P001 to VS-P020) |
| **KPIs** | 0 (horizontal) | +25 vertical-specific KPIs with formulas and benchmarks (VS-K001 to VS-K025) |
| **Signal Rules** | 0 (horizontal) | +20 vertical signal interpretation rules (VS-S001 to VS-S020) |
| **Personas** | 14 base SaaS personas | +6 vertical-specialized personas (VS-PE001 to VS-PE006) |
| **Value Formulas** | Horizontal templates | +15 vertical-specific formulas (VS-VF001 to VS-VF015) |
| **Benchmarks** | Horizontal ranges | +20 vertical-specific benchmarks (VS-B001 to VS-B020) |
| **Regulatory Factors** | Generic (SOC 2, GDPR) | +12 vertical-specific regulations (VS-RF001 to VS-RF012) |
| **Technology Systems** | Generic stack | +15 vertical-specific systems (VS-TS001 to VS-TS015) |
| **Discovery Questions** | Generic SaaS | +20 vertical discovery questions (VS-DQ001 to VS-DQ020) |
| **Objection Patterns** | Generic SaaS | +10 vertical objection patterns (VS-OBJ001 to VS-OBJ010) |
| **Buying Triggers** | Generic triggers | +15 vertical buying triggers (VS-BT001 to VS-BT015) |
| **Value Driver Maps** | Horizontal framework | +10 vertical value driver mappings (VS-VD001 to VS-VD010) |
| **Evidence Sources** | Generic types | +10 vertical-specific sources (VS-ES001 to VS-ES010) |
| **Competitor Factors** | Generic competitive | +5 vertical competitive dynamics (VS-CF001 to VS-CF005) |

### When to Use Master vs. Subpack

| Scenario | Skill to Use |
|----------|-----------|
| Selling horizontal SaaS platform (CRM, ERP, HRIS) to any industry | **saas-master-v1 only** |
| Target account is a vertical SaaS company (e.g., Toast, Shopify, Procore, Veeva) | **saas-master-v1 + vertical-saas-v1** |
| Selling into a regulated industry (healthcare, fintech, gov, ed) where compliance is deal-critical | **vertical-saas-v1** (compliance depth not in master) |
| Generic SaaS metrics discussion (Rule of 40, NRR, CAC payback) | **saas-master-v1** |
| Vertical-specific workflow, integration, or talent discussion | **vertical-saas-v1** |
| Account shows both horizontal SaaS pains AND vertical-specific pains | **Load both; map horizontal pains to master, vertical pains to subpack** |

**Prefix Convention:** All subpack components use the `VS-` prefix to avoid ID collision with the master pack's `VD-`, `P-`, `K-`, etc.

---

## Structured Output Template

Expected JSON format for Signals Analysis enrichment:

```json
{
  "pack_id": "vertical-saas-v1",
  "pack_name": "Vertical SaaS Subpack",
  "parent_master": "saas-master-v1",
  "version": "1.0.0",
  "analysis_timestamp": "2025-04-25T00:00:00Z",
  "target_account": {
    "name": "string",
    "primary_vertical": "string",
    "secondary_verticals": ["string"]
  },
  "signals_detected": [
    {
      "signal_id": "VS-S00X",
      "signal_name": "string",
      "confidence": 0.85,
      "confirmation_signals_present": ["string"],
      "linked_pains": ["VS-P00X"],
      "linked_kpis": ["VS-K00X"],
      "active": true
    }
  ],
  "pains_active": [
    {
      "pain_id": "VS-P00X",
      "pain_name": "string",
      "prevalence": "HIGH|MEDIUM|LOW",
      "confidence": "HIGH|MEDIUM|LOW",
      "affected_personas": ["VS-PE00X"],
      "linked_kpis": ["VS-K00X"],
      "linked_value_drivers": ["VS-VD00X"]
    }
  ],
  "kpis_calculated": [
    {
      "kpi_id": "VS-K00X",
      "kpi_name": "string",
      "calculated_value": "number|string",
      "unit": "string",
      "benchmark_status": "Below|Within|Above",
      "vertical_applicability": ["string"]
    }
  ],
  "value_hypotheses": [
    {
      "value_driver_map_id": "VS-VD00X",
      "category": "Revenue Uplift|Cost Savings|Risk Reduction|Working Capital",
      "formula_id": "VS-VF00X",
      "annual_impact_usd": 0,
      "confidence": "HIGH|MEDIUM|LOW",
      "inputs_used": {
        "key": "value"
      }
    }
  ],
  "personas_engaged": [
    {
      "persona_id": "VS-PE00X",
      "persona_name": "string",
      "influence": "technical|economic|user",
      "relevance_score": 0.0,
      "primary_pains": ["VS-P00X"]
    }
  ],
  "buying_triggers_active": [
    {
      "trigger_id": "VS-BT00X",
      "trigger_name": "string",
      "urgency": "HIGH|MEDIUM|LOW",
      "days_to_act": 0,
      "affected_verticals": ["string"]
    }
  ],
  "competitive_threats": [
    {
      "competitor_factor_id": "VS-CF00X",
      "threat_level": "HIGH|MEDIUM|LOW",
      "response_timeline_months": 0,
      "description": "string"
    }
  ],
  "overall_confidence": 0.85,
  "source_coverage": [
    "VS-ES001",
    "VS-ES002"
  ],
  "governance": {
    "confidence_level": "HIGH",
    "customer_facing_approved": true,
    "review_owner": "vertical-saas-subpack-architect"
  }
}
```

---

## Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | HIGH |
| **Source Coverage** | Mixed (public reports, subscription research, vendor data, government sources) |
| **Customer-Facing Approval Status** | Yes - Approved |
| **Review Owner** | vertical-saas-subpack-architect |
| **Last Updated** | 2025-04-25 |
| **Agent Swarm ID** | kimi-k2.6-swarm-saas-vertical |
| **Parent Master Swarm ID** | kimi-k2.6-swarm-saas |
| **Evidence Sources** | 10 vertical-specific (VS-ES001 to VS-ES010) |
| **Source Quality Breakdown** | 6 HIGH confidence, 4 MEDIUM confidence |

---

## Quick Reference

### Top 5 Pains (by prevalence and impact)

| Rank | Pain ID | Pain Name | Prevalence | Key Symptom |
|------|---------|-----------|------------|-------------|
| 1 | VS-P001 | Industry-Specific Workflow Gaps in Generic CRM/ERP | HIGH | >40 custom fields needed per standard object |
| 2 | VS-P002 | Vertical Regulatory Compliance Burden | HIGH | Security questionnaires >80 hours per deal |
| 3 | VS-P003 | Multi-Tenant Data Isolation for Vertical Customers | HIGH | Tenant isolation consuming >25% of infra budget |
| 4 | VS-P004 | Vertical Sales Talent Scarcity and Long Ramp Times | HIGH | Rep ramp time >9 months for vertical roles |
| 5 | VS-P005 | Integration with Legacy Industry Systems | HIGH | Integration backlog >12 months for core systems |

### Top 5 KPIs (most frequently referenced)

| Rank | KPI ID | KPI Name | Benchmark |
|------|--------|----------|-----------|
| 1 | VS-K001 | Vertical Workflow Fit Score | Strong: >80%; Vertical-native: >90% |
| 2 | VS-K004 | Vertical Compliance Coverage Rate | Market-ready: >80%; Complete: 100% |
| 3 | VS-K003 | Time-to-Vertical-Value (TTVV) | Enterprise: <60 days; At Risk: >90 days |
| 4 | VS-K010 | Vertical Sales Rep Ramp Time | Fast: <120 days; Concerning: >270 days |
| 5 | VS-K013 | Legacy System Integration Success Rate | Good: 70%-85%; Excellent: >85% |

### Top 3 Personas (highest decision influence)

| Rank | Persona ID | Persona Name | Influence | Decision Role |
|------|-----------|--------------|-----------|---------------|
| 1 | VS-PE006 | Vertical SaaS CFO / Finance VP | Economic | Budget authority, unit economics, investor relations |
| 2 | VS-PE004 | Vertical Compliance and Risk Officer | Economic | Compliance certification, audit, legal review |
| 3 | VS-PE003 | Vertical GTM Lead | Economic | Sales strategy, CAC optimization, market expansion |

### Key Value Formulas (quick reference)

| Formula ID | Name | Example Output |
|-----------|------|----------------|
| VS-VF001 | Vertical Workflow Gap Cost | $125,000/month = (8 hrs x $75 x 200 users) + amortization + opportunity cost |
| VS-VF002 | Vertical Compliance Delay Cost | $2,185,000/year = (15 deals x $85K ACV) + audit + legal + delayed market entry |
| VS-VF003 | Tenant Isolation Infrastructure ROI | 567% ROI = ($3.2M revenue - $480K cost) / $480K |
| VS-VF008 | Embedded Payments Margin Contribution | $270,000/year = ($45M x 1.2%) - (processor + compliance + fraud + chargebacks) |
| VS-VF009 | GovTech Sales Cycle Working Capital Impact | $117,192/deal = (sales cycle financing) + (proposal cost x win rate inverse) + payment delay |

---

## Associated Files

| File | Purpose |
|------|---------|
| `value-pack.json` | Structured pack definition (pains, KPIs, signals, personas, formulas, benchmarks, regulations, tech systems, discovery questions, objections, buying triggers, evidence sources, competitor factors) |
| `value-pack.md` | Human-readable documentation with full pain descriptions, worked examples, and governance |
| `signals-examples.ts` | TypeScript executable examples for signal evaluation, value formula calculation, and buying trigger detection |
