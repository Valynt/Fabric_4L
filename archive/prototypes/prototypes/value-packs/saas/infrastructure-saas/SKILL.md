# Infrastructure and Platform SaaS ValuePack (S2.4)

## Skill Identity Block

| Attribute | Value |
|---|---|
| **skill_name** | Infrastructure and Platform SaaS ValuePack |
| **description** | Vertical-specialized value intelligence for Infrastructure and Platform SaaS companies. Covers cloud management, observability, APM, data pipelines, data warehouses/lakehouses, API platforms, integration/iPaaS, CI/CD, feature flags, testing, K8s management, FinOps, and DX platforms. Provides 20 vertical pains, 25 vertical KPIs, 20 signal rules, 6 specialized personas, 15 value formulas, and 15 buying triggers. |
| **version** | 1.0.0 |
| **domain** | industry |
| **pack_type** | subpack |
| **parent_master** | saas-master-v1 |
| **agent_swarm** | kimi-k2.6-swarm-saas-infra |

---

## Triggers

Auto-load this skill when queries match any of the following patterns:

1. **"cloud cost optimization"** -- Company struggling with FinOps, cloud waste, RI underutilization, or tagging compliance
2. **"K8s cluster sprawl"** -- Kubernetes governance failure, orphaned clusters, or platform team bottleneck
3. **"observability consolidation"** -- Multiple observability tools, observability cost >15% of cloud budget, or data explosion
4. **"FinOps tagging"** -- Cloud tagging chaos, chargeback failure, or cost allocation disputes between finance and engineering
5. **"CI/CD pipeline fragility"** -- Pipeline failures >15%, flaky tests, deployment anxiety, or rollback time >30 minutes
6. **"data pipeline reliability"** -- ETL/ELT failures, stale data dashboards, or data quality incidents >2% monthly
7. **"API platform scalability"** -- API latency degradation, error rate spikes, or partner integration backlog >6 months
8. **"feature flag governance"** -- Flag chaos >200 active flags, stale flags, or flag-related production incidents
9. **"platform engineering bottleneck"** -- No IDP or self-service portal, ticket backlog >8 weeks, or provisioning >2 weeks
10. **"developer experience friction"** -- New engineer onboarding >2 weeks, build time >10 minutes, or internal DX NPS <0
11. **"incident response inefficiency"** -- MTTD >15 minutes, alert fatigue, or >30% deployment-related incidents
12. **"MLOps infrastructure scaling"** -- GPU utilization <40%, no model registry, or inference latency >500ms P99

---

## Reasoning Flow

### Step 1: Load Master Skill First
Before applying this subpack, load `saas-master-v1` (SaaS Master ValuePack) to establish:
- Base segment taxonomy (Infrastructure and Platform SaaS, Horizontal SaaS, AI-Native SaaS, etc.)
- Value Driver Framework (VD001-VD050)
- Evidence Source Types and confidence scoring methodology
- Discovery question patterns and objection frameworks

### Step 2: Identify Infrastructure-Specific Signals
Scan the prospect/account for vertical-specific signals using these categories:

| Signal Category | Source Examples | Priority |
|---|---|---|
| **Observability Signals** | Datadog/Splunk pricing changes, log volume growth >30% MoM, trace sampling <1% | HIGH |
| **Cloud Cost Signals** | 10-K budget breach mentions, FinOps Foundation 32% waste benchmark, untagged spend >30% | HIGH |
| **K8s & Platform Signals** | CNCF survey data, cluster-to-team ratio >4, orphaned clusters >15%, node utilization <20% | HIGH |
| **CI/CD Signals** | DORA metrics below high tier, pipeline failure rate >15%, deployment frequency <1/week | HIGH |
| **Incident Response Signals** | MTTD >15 min, alert actionability <10%, SEV-2 post-mortem completion <50% | HIGH |
| **Data Pipeline Signals** | Fivetran/Monte Carlo benchmarks, SLA achievement <85%, data freshness >4 hours | MEDIUM |
| **API Platform Signals** | Postman API Report, P99 latency >500ms, developer onboarding >14 days | MEDIUM |
| **DX & IDP Signals** | DX Community benchmarks, onboarding >14 days, build time >10 minutes, platform adoption <50% | MEDIUM |
| **Feature Flag Signals** | LaunchDarkly/Split reports, active flags >200, stale rate >30%, flag incidents | MEDIUM |
| **FinOps Tagging Signals** | Tagging compliance <50%, manual cost allocation >3 days, finance-engineering disputes | HIGH |
| **Security & DevSecOps Signals** | Snyk/Aqua Security reports, unremediated CVEs >500, SAST/DAST not in CI/CD | HIGH |

### Step 3: Map Signals to Pains Using Subpack Rules
Apply the 20 vertical signal interpretation rules (INF-SR001 to INF-SR020):

1. **Match raw signal** → **Find rule** → **Check required confirmation signals** → **Score confidence**
2. Map confirmed signals to one or more pains (INF-P001 to INF-P020)
3. Each pain links to specific KPIs, personas, and value drivers

**Confidence Scoring Guidance:**
- **HIGH (0.80-1.00):** Signal confirmed by prospect data + multiple independent sources + public evidence
- **MEDIUM (0.55-0.79):** Single reliable source or strong proxy signal; requires discovery call validation
- **LOW (0.30-0.54):** Emerging trend, limited sample size, or forward-looking projection

### Step 4: Identify Relevant Personas
Select from 6 vertical-specific personas + inherited base personas:

| Persona | Primary Pains | Decision Role |
|---|---|---|
| Platform Engineer | INF-P002, INF-P003, INF-P015, INF-P017 | Technical influencer |
| SRE Lead | INF-P001, INF-P012, INF-P018, INF-P019 | Technical influencer |
| Data Platform Architect | INF-P004, INF-P010, INF-P014, INF-P020 | Technical influencer |
| FinOps Analyst | INF-P007, INF-P016 | Economic buyer |
| API Product Manager | INF-P005, INF-P013 | Technical influencer |
| DevEx Lead | INF-P003, INF-P008, INF-P009, INF-P015 | Technical influencer |
| CTO | All pains | Executive sponsor |
| VP Engineering | INF-P003, INF-P008, INF-P009, INF-P015 | Economic buyer |
| VP DevOps | INF-P001, INF-P007, INF-P012 | Technical influencer |
| CFO | INF-P007, INF-P016 | Economic buyer |
| CISO | INF-P014, INF-P017 | Risk/compliance buyer |

### Step 5: Map to Value Hypotheses
Use vertical-specific value driver interpretation:

| Value Driver | Signal Pattern | Value Category |
|---|---|---|
| VD011 | DORA metrics below 'high' tier | Cost Savings (velocity) |
| VD012 | Engineering team >30% on maintenance | Cost Savings (capacity) |
| VD013 | Cloud spend growing faster than revenue | Cost Savings (efficiency) |
| VD014 | Idle/underutilized resources >20% | Cost Savings (waste) |
| VD028 | AI inference costs spiking unpredictably | Cost Savings (AI infra) |
| VD031 | Customer-reported incidents >15% | Risk Reduction (MTTR) |
| VD032 | No SLO/SLI framework | Risk Reduction (reliability) |
| VD039 | K8s cluster sprawl >4 per team | Cost Savings (complexity) |
| VD040 | Platform engineering backlog >8 weeks | Cost Savings (bottleneck) |
| VD043 | API uptime <99.9% for 3 months | Risk Reduction (platform) |
| VD044 | Integration requests unresolved >6 months | Revenue Uplift (ecosystem) |
| VD047 | Data pipeline SLA achievement <85% | Risk Reduction (data trust) |
| VD048 | Data quality incidents >2% monthly | Risk Reduction (governance) |

### Step 6: Build Value Case with Vertical Formulas
Select from 15 specialized formulas based on confirmed pains:

| Formula | Use Case | Confidence Driver |
|---|---|---|
| INF-VF001 | Observability cost optimization | Observability cost breakdown available |
| INF-VF002 | K8s cluster consolidation | Cluster inventory and cost allocation complete |
| INF-VF003 | CI/CD failure cost avoidance | Incident tracking + revenue impact data |
| INF-VF004 | Data pipeline reliability | Pipeline incident tracking in place |
| INF-VF005 | API platform revenue uplift | API revenue tracked separately |
| INF-VF006 | Feature flag governance | Flag registry and incident tracking exist |
| INF-VF007 | Cloud commitment optimization | Cloud billing data with RI utilization |
| INF-VF008 | Test automation quality | Bug cost and QA time tracked |
| INF-VF009 | Developer experience productivity | DX metrics tracked (time-to-first-commit, build times) |
| INF-VF010 | Data warehouse performance | Warehouse query logs and cost reports |
| INF-VF011 | Service mesh/network cost avoidance | Cloud networking cost allocation available |
| INF-VF012 | Incident response efficiency | Incident costs and MTTR tracked |
| INF-VF013 | API ecosystem expansion | API revenue and partner metrics tracked |
| INF-VF014 | Data governance and compliance | Compliance team time and audit history tracked |
| INF-VF015 | Platform engineering self-service | Platform request queue tracked |

### Step 7: Prioritize Buying Triggers
Rank opportunities by urgency using 15 buying triggers:

| Urgency | Trigger IDs | Timing |
|---|---|---|
| **HIGH** | INF-BT001-BT005, BT007-BT009, BT011, BT013, BT015 | 0-90 days |
| **MEDIUM** | INF-BT006, BT010, BT012, BT014 | 3-12 months |

### Step 8: Formulate Discovery Questions
Match confirmed pains to the 20 vertical discovery questions (INF-DQ001 to INF-DQ020). Each question is tagged by:
- Target persona(s)
- Type (metric_validation, process_diagnostic)
- Expected insight to surface

### Step 9: Prepare for Objections
Pre-load the 10 vertical objection patterns (INF-OBJ001 to INF-OBJ010) with reframing strategies:
- Tool sprawl → TCO analysis with 3-year NPV
- Build vs. buy → Total cost of build including maintenance + opportunity cost
- Cloud cost denial → FinOps 32% waste benchmark in dollars
- Vendor lock-in → Break-even point calculation + migration assistance
- Developer slowdown → Time-to-value metrics from pilot customers
- K8s/open source free → Engineer FTE cost vs. managed platform cost

---

## Inheritance Map

### Load Master First
**Always load `saas-master-v1` before this subpack.** The master provides the foundational taxonomy, base personas, value driver framework, governance model, and cross-vertical benchmarks.

### What This Subpack Adds

| Category | Master Base | Subpack Addition |
|---|---|---|
| **Pains** | Cross-vertical SaaS pains (14) | +20 Infrastructure-specific pains (INF-P001 to INF-P020) |
| **KPIs** | Base KPIs with generic benchmarks | +25 Infrastructure KPIs with per-GB, per-cluster, per-pipeline benchmarks |
| **Personas** | PER001-PER014 (CTO, CFO, CISO, VP Eng, etc.) | +6 vertical personas: Platform Engineer, SRE Lead, Data Platform Architect, FinOps Analyst, API Product Manager, DevEx Lead |
| **Signal Rules** | SR001-SR030 (generic SaaS signals) | +20 vertical signal rules (INF-SR001 to INF-SR020) |
| **Value Formulas** | VF001-VF025 (generic templates) | +15 vertical formulas (INF-VF001 to INF-VF015) |
| **Buying Triggers** | 10 base triggers | +15 vertical triggers (INF-BT001 to INF-BT015) |
| **Discovery Questions** | 12 base question patterns | +20 vertical questions (INF-DQ001 to INF-DQ020) |
| **Objection Patterns** | 8 base objections | +10 vertical objections (INF-OBJ001 to INF-OBJ010) |
| **Technology Systems** | Base SaaS stack taxonomy | +15 Infrastructure systems (INF-TS001 to INF-TS015) |
| **Regulatory Factors** | Base compliance taxonomy | +12 Infrastructure regulations (INF-REG001 to INF-REG012) including DORA/NIS2 |
| **Benchmarks** | Generic SaaS benchmarks | +20 Infrastructure benchmarks (INF-B001 to INF-B020) from CNCF, FinOps, DORA |

### When to Use Master vs. Subpack

| Scenario | Recommendation |
|---|---|
| Prospects identified as generic SaaS without vertical clarity | Use `saas-master-v1` only |
| Infrastructure SaaS prospect (observability, CI/CD, K8s, cloud cost, API platform) | Load `saas-master-v1` + this subpack |
| Mixed portfolio including Infrastructure + other verticals | Load `saas-master-v1` + this subpack + relevant other subpacks |
| Existing Infrastructure customer expanding into AI/ML | Load `saas-master-v1` + this subpack + AI-Native SaaS subpack |
| Need general SaaS benchmarks or cross-vertical comparison | Use `saas-master-v1` only |
| Need Infrastructure-specific benchmarks, formulas, or signal rules | Use this subpack |

### Overridden Components

| Component | Override Reason |
|---|---|
| Segment Applicability on Base KPIs | Infrastructure SaaS has different benchmark ranges for engineering, cloud cost, and observability KPIs |
| Persona definitions for CTO/VP Engineering | Added Infrastructure-specific pressures, trusted evidence, and goals |
| Value Driver interpretation for Cloud Cost/Observability | Reframed to reflect per-GB, per-node, per-cluster unit economics |

---

## Structured Output Template

When enriching a prospect/account with this skill, output the following JSON structure:

```json
{
  "skill_loaded": "infrastructure-saas-v1",
  "parent_master": "saas-master-v1",
  "enrichment_timestamp": "2026-04-25T00:00:00Z",
  "signals_analysis": {
    "prospect_id": "<prospect-id>",
    "vertical_match": "Infrastructure and Platform SaaS",
    "confidence": "HIGH|MEDIUM|LOW",
    "detected_signals": [
      {
        "signal_id": "INF-SR001",
        "signal_name": "Observability Vendor Pricing Change",
        "raw_evidence": "Datadog announced 15% per-GB price increase effective Q3",
        "confirmation_status": "confirmed|partial|unverified",
        "linked_pains": ["INF-P001", "INF-P018"],
        "linked_personas": ["SRE Lead", "FinOps Analyst"],
        "urgency": "HIGH",
        "confidence_score": 0.85,
        "timing": {
          "trigger_window": "30-90 days before renewal",
          "procurement_window": "Q3 2025",
          "budget_cycle": "FY2026 planning"
        }
      }
    ],
    "pain_analysis": [
      {
        "pain_id": "INF-P001",
        "pain_name": "Observability Data Explosion and Cost Spiral",
        "present": true,
        "confidence": "HIGH",
        "severity": "HIGH",
        "symptoms_detected": [
          "Observability spend >15% of total cloud budget",
          "Monthly log volume growth >30% MoM"
        ],
        "affected_personas": ["CTO", "VP DevOps", "SRE Lead", "FinOps Analyst"],
        "linked_kpis": ["INF-K001", "INF-K002", "INF-K003"],
        "linked_value_drivers": ["VD013", "VD014"]
      }
    ],
    "kpi_snapshot": [
      {
        "kpi_id": "INF-K001",
        "kpi_name": "Observability Cost per GB Ingested",
        "current_value": 2.80,
        "current_unit": "USD per GB",
        "benchmark_range": "Efficient: <$1.00; Median: $1.50-$2.50; High: >$3.00",
        "status": "high",
        "gap_from_efficient": 1.80
      }
    ],
    "persona_map": [
      {
        "persona_id": "INF-PER001",
        "persona_name": "Platform Engineer",
        "relevance": "HIGH",
        "identified_signals": ["INF-SR002", "INF-SR014"],
        "engagement_priority": 1,
        "discovery_questions": ["INF-DQ002", "INF-DQ015"]
      }
    ],
    "value_hypotheses": [
      {
        "formula_id": "INF-VF001",
        "formula_name": "Observability Cost Optimization Value",
        "applicable": true,
        "estimated_annual_value": 2095000,
        "value_category": "Cost Savings",
        "confidence": "HIGH",
        "required_inputs_status": "complete|partial|missing",
        "inputs": {
          "annual_observability_spend": 3500000,
          "current_waste_pct": 25,
          "current_per_gb": 2.80,
          "target_per_gb": 1.50
        }
      }
    ],
    "buying_triggers": [
      {
        "trigger_id": "INF-BT001",
        "trigger_name": "Observability Vendor Price Increase",
        "active": true,
        "urgency": "HIGH",
        "recommended_action": "Accelerate TCO comparison with 3-year NPV; offer migration assessment",
        "procurement_timing": "30-90 days"
      }
    ],
    "recommended_discovery": ["INF-DQ001", "INF-DQ018", "INF-DQ007"],
    "recommended_objection_prep": ["INF-OBJ001", "INF-OBJ004", "INF-OBJ007"],
    "competitor_factors": ["INF-CF003", "INF-CF006"],
    "next_steps": [
      "Validate observability spend with FinOps Analyst",
      "Confirm contract renewal timing",
      "Schedule SRE Lead for technical discovery"
    ]
  }
}
```

---

## Governance Metadata

| Attribute | Value |
|---|---|
| **Confidence Level** | HIGH |
| **Source Coverage** | mixed (18 primary sources: DORA, FinOps Foundation, Datadog, CNCF, PagerDuty, Platform Engineering Community, DX Community, Postman, Kong, Fivetran, Monte Carlo, CircleCI, GitLab, Snowflake, Gartner, Snyk, NVIDIA, dbt Labs) |
| **Customer-Facing Approval Status** | **NOT APPROVED** -- Internal use and agent reasoning only. Requires review owner sign-off before customer-facing use. |
| **Review Owner** | infrastructure-saas-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-swarm-saas-infra |
| **Parent Master Swarm ID** | kimi-k2.6-swarm-saas |
| **Pack Status** | ACTIVE |
| **Governance Rules** | All benchmarks carry explicit confidence ratings (HIGH = multiple independent sources; MEDIUM = single reliable source; LOW = emerging trend). Do not present LOW-confidence claims as fact. |

---

## Quick Reference

### Top 5 Pains (by prevalence and confidence)

| Rank | Pain ID | Name | Prevalence | Confidence |
|---|---|---|---|---|
| 1 | INF-P001 | Observability Data Explosion and Cost Spiral | HIGH | HIGH |
| 2 | INF-P002 | Kubernetes Cluster Sprawl and Governance Failure | HIGH | HIGH |
| 3 | INF-P003 | CI/CD Pipeline Fragility and Deployment Anxiety | HIGH | HIGH |
| 4 | INF-P007 | Cloud Cost Overrun with Reserved Instance Underutilization | HIGH | HIGH |
| 5 | INF-P015 | Platform Engineering Team Bottleneck and Self-Service Deficit | HIGH | HIGH |

### Top 5 KPIs (most diagnostic)

| Rank | KPI ID | Name | Benchmark | Frequency |
|---|---|---|---|---|
| 1 | INF-K001 | Observability Cost per GB Ingested | Efficient: <$1.00; High: >$3.00 | Monthly |
| 2 | INF-K004 | Kubernetes Cluster Density Ratio | Managed: 1-2; Uncontrolled: >5 | Monthly |
| 3 | INF-K007 | CI/CD Pipeline Failure Rate | Elite: <5%; Low: >30% | Weekly |
| 4 | INF-K019 | Cloud Cost per Deployed Service | Efficient: <$5K; High: >$20K | Monthly |
| 5 | INF-K034 | Mean Time to Detect (MTTD) | Elite: <5 min; At Risk: >30 min | Per Incident |

### Top 3 Personas (most common in Infrastructure deals)

| Rank | Persona ID | Name | Decision Role | Primary Pains |
|---|---|---|---|---|
| 1 | INF-PER001 | Platform Engineer | Technical influencer | INF-P002, INF-P003, INF-P015, INF-P017 |
| 2 | INF-PER002 | SRE Lead | Technical influencer | INF-P001, INF-P012, INF-P018, INF-P019 |
| 3 | INF-PER004 | FinOps Analyst | Economic buyer | INF-P007, INF-P016 |

### Key Value Formulas (quick lookup)

| Formula ID | Name | Output | Key Inputs (3) |
|---|---|---|---|
| INF-VF001 | Observability Cost Optimization | Annual savings ($) | Annual spend, waste %, $/GB current vs. target |
| INF-VF002 | K8s Cluster Consolidation | Annual savings ($) | Orphaned clusters, underutilized clusters, avg cluster cost |
| INF-VF007 | Cloud Commitment Optimization | Annual savings ($) | Underutilized RI hours, predictable hours, savings plan discount |
| INF-VF009 | Developer Experience Productivity | Annual gain ($) | New engineers/yr, setup days delta, build time saved |
| INF-VF012 | Incident Response Efficiency | Annual value ($) | Incidents/yr, MTTR delta, alert noise reduction % |

---

## File Manifest

This skill pack includes the following files (do not modify):

| File | Purpose |
|---|---|
| `value-pack.json` | Complete pack data (pains, KPIs, formulas, benchmarks, signals) in structured JSON |
| `value-pack.md` | Human-readable reference document with full descriptions, worked examples, and governance |
| `signals-examples.ts` | TypeScript-style signal rule definitions with interpretation logic |
| `SKILL.md` | This file -- OpenClaw-compatible skill definition |

---

*Generated by Kimi K2.6 Elevated Agent Swarm. Packaging Agent: Skills Packaging Agent. Last packaged: 2026-04-25.*
