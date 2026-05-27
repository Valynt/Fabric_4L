# Skill: Advanced Manufacturing Subpack (S1.3)

---

## 1. Skill Identity

| Field | Value |
|---|---|
| **skill_name** | advanced-manufacturing-v1 |
| **description** | Vertical intelligence subpack for semiconductor fabrication, battery manufacturing, additive manufacturing, clean energy equipment, precision machining, photonics, composites, and smart factory/Industry 4.0. Provides specialized signal interpretation, KPI benchmarking, persona profiling, and value quantification for technology-intensive manufacturing enterprise sales and advisory engagements. |
| **version** | 1.0.0 |
| **domain** | Industry |
| **pack_type** | subpack |
| **parent_master** | manufacturing-master-v1 |

---

## 2. Triggers

Auto-load this skill when user queries include patterns like:

1. "semiconductor fab yield"
2. "battery cell formation"
3. "3D printing aerospace qualification"
4. "Industry 4.0 smart factory"
5. "EUV lithography resist defects"
6. "additive manufacturing build failure"
7. "cleanroom contamination events"
8. "digital twin accuracy drift"
9. "photonics active alignment yield"
10. "composite layup void content"
11. "precision machining thermal compensation"
12. "FDC fault detection alarm fatigue"

---

## 3. Reasoning Flow

### Step 1: Load Master First
Always load `manufacturing-master-v1` before this subpack. The master provides base value drivers, persona archetypes, evidence source taxonomy, formula templates, signal rules, benchmark methodology, and governance framework. This subpack extends and specializes those foundations.

### Step 2: Detect & Interpret Signals
When analyzing a prospect or account:

1. **Detect** raw signals from earnings calls, job postings, patent filings, press releases, capex announcements, and industry events.
2. **Interpret** using the 18 vertical signal rules with confidence scoring. Each signal has:
   - `confidenceScore` (0.0-1.0)
   - `requiredConfirmationSignals` that must be present to upgrade confidence
   - Direct links to pains and KPIs

3. **Confidence Scoring Guidance:**
   - **HIGH (>0.85):** Multiple confirming signals present; proceed with quantified value hypothesis.
   - **MEDIUM (0.70-0.85):** Primary signal detected; seek 1-2 confirmation signals before full hypothesis.
   - **LOW (<0.70):** Single weak signal; use for discovery question targeting only, not value claims.

### Step 3: Map to Pains, Personas, and KPIs

| Signal | Linked Pain | Primary Personas | Key KPIs |
|---|---|---|---|
| EUV resist diversification | Yield fallout, EUV resist | Fab Engineer, COO | Wafer yield, defect density |
| Gigafactory expansion pause | Formation variability | Battery Designer, COO | Formation CT, chamber util |
| AM audit findings | Build failure | AM Engineer, Quality | Build fail rate, part accuracy |
| Cleanroom RFQ surge | Contamination | Cleanroom Manager | Particle count |
| APC/FDC vendor eval | Alarm fatigue | Fab Engineer, Plant | FDC false alarm |
| AMHS retrofit | AMHS bottleneck | Plant Manager, I4.0 Arch | AMHS delivery, fab CT |
| Solid-state pilot line | Scale-up risk | Battery Designer, CFO | Pilot yield, capex/GWh |
| Digital twin vendor selection | Twin accuracy | I4.0 Architect, CIO | Twin accuracy, data utilization |
| Photonics demand surge | Alignment precision | AM Engineer, Quality | Alignment yield, coupling eff |
| Aerospace program ramp-up | Composite defects | Quality, Engineering | Void content, NDT pass rate |
| Precision machining orders | Thermal compensation | Metrology, Plant | Thermal drift, first-part yield |
| MES/EAP modernization | Integration gap | CIO, I4.0 Arch | EAP-MES sync, WIP accuracy |
| Solar efficiency acceleration | Module lamination | Quality, CFO | Cell crack rate, lamination yield |
| OT cyber incident | Cyber exposure | CISO, I4.0 Arch | OT segmentation, CSF level |
| Metrology investment | Metrology bottleneck | Metrology, Plant | Metro queue time, CMM util |
| CHIPS Act subsidy | Yield, contamination, FDC | Fab Engineer, COO | Wafer yield, defect density |
| Battery OEM vertical integration | Formation, coating | Battery Designer, COO | Formation CT, coating uniformity |
| I4.0 maturity assessment | Twin, IIoT | I4.0 Architect, CIO | Twin accuracy, data utilization |

### Step 4: Quantify Value

Use vertical-specific formulas (12 provided). Each formula requires validated baseline and target inputs. Apply confidence rules before presenting to customer.

**Value Quantification Discipline:**
- Every formula requires validated baseline and target inputs
- Confidence rules must be checked before presenting to customer
- Use ranges rather than false precision
- Always connect to one of four value categories: Revenue Uplift, Cost Savings, Risk Reduction, Working Capital Improvement

### Step 5: Validate with Discovery Questions

Deploy the 20 vertical discovery questions mapped to specific personas and pains. Use to confirm signal interpretation and refine value hypotheses.

### Step 6: Address Objections

Use the 10 objection response strategies tailored to advanced manufacturing contexts.

---

## 4. Inheritance Map

### Master Skill to Load First
**`manufacturing-master-v1`** — Load this before applying any subpack logic.

### What This Subpack Adds
| Category | Inherited from Master | Added in Subpack |
|---|---|---|
| Value Drivers | 10 base drivers | 6 vertical-specific drivers |
| Personas | 17 base archetypes | 6 new specialized personas |
| Evidence Sources | 12 source types | 8 vertical evidence sources |
| Formulas | 25 base templates | 12 vertical formulas |
| Benchmarks | 35 base benchmarks | 20 vertical benchmarks |
| Signal Rules | 30 base rules | 18 vertical signal rules |
| Pains | — | 18 vertical pains |
| KPIs | — | 30 vertical KPIs |
| Technology Systems | — | 15 specialized systems |
| Regulatory Factors | — | 12 vertical regulations |
| Discovery Questions | — | 20 vertical questions |
| Objections | — | 10 vertical objection responses |
| Buying Triggers | — | 15 vertical triggers |
| Competitive Factors | — | 7 vertical factors |

### When to Use Master vs Subpack
| Scenario | Use |
|---|---|
| Prospect is a generic manufacturer with no vertical signals | Master only |
| Prospect shows signals in multiple verticals | Master + multiple subpacks |
| Prospect shows semiconductor, battery, AM, photonics, or I4.0 signals | This subpack |
| Value quantification needed for advanced manufacturing pains | This subpack's formulas |
| Discovery into fab, gigafactory, or AM operations | This subpack's questions |

---

## 5. Structured Output Template

### Signals Analysis Enrichment — JSON Output

```json
{
  "skill_loaded": "advanced-manufacturing-v1",
  "parent_master": "manufacturing-master-v1",
  "analysis_timestamp": "2026-04-25T00:00:00Z",
  "vertical_segments": ["Semiconductor Fabrication", "Battery Manufacturing"],
  "detected_signals": [
    {
      "signal_id": "adv-sig-001",
      "signal_name": "EUV resist supplier diversification",
      "confidence": 0.82,
      "status": "confirmed",
      "confirmation_signals": ["ASML backlog data", "TSMC N3+ expansion"],
      "linked_pains": ["adv-pain-001", "adv-pain-016"],
      "linked_kpis": ["adv-kpi-wafer-yield", "adv-kpi-defect-density"],
      "affected_personas": ["pers-fab-eng", "pers-coo", "pers-cfo"],
      "value_hypothesis": {
        "formula_id": "adv-form-001",
        "estimated_annual_value": "$24M",
        "value_range": "$18M - $30M",
        "confidence": 0.75
      }
    }
  ],
  "matched_pains": [
    {
      "pain_id": "adv-pain-001",
      "pain_name": "Yield Fallout at 7nm and Below Nodes",
      "prevalence": "HIGH",
      "confidence": "HIGH",
      "symptoms_present": ["Wafer yield <85%", "Defect density >0.1/cm2"],
      "linked_value_drivers": ["vdrv-yield-improvement", "vdrv-scrap-reduction"]
    }
  ],
  "matched_kpis": [
    {
      "kpi_id": "adv-kpi-wafer-yield",
      "kpi_name": "Wafer Yield (Die Per Wafer)",
      "customer_baseline": null,
      "benchmark_target": "85-92% (N7)",
      "gap_estimate": "TBD — requires discovery"
    }
  ],
  "target_personas": [
    {
      "persona_id": "pers-fab-eng",
      "persona_name": "Fab Process Engineer",
      "relevance_score": 0.95,
      "recommended_discovery_questions": ["adv-dq-001", "adv-dq-005", "adv-dq-016"]
    }
  ],
  "buying_trigger_match": {
    "trigger_id": "adv-bt-002",
    "trigger_name": "Yield crisis at advanced node",
    "urgency": "CRITICAL",
    "timing": "0-3 months"
  },
  "governance": {
    "confidence_level": "HIGH",
    "source_coverage": "Mixed (public filings, industry reports, benchmarks, vendor data)",
    "customer_facing_approved": false,
    "review_owner": "advanced-manufacturing-subpack-architect",
    "last_updated": "2026-04-25"
  }
}
```

---

## 6. Governance Metadata

| Field | Value |
|---|---|
| **Confidence Level** | HIGH |
| **Source Coverage** | Mixed (public filings, industry reports, benchmarks, vendor data, academic research, government standards) |
| **Customer-Facing Approval Status** | No (internal intelligence only) |
| **Review Owner** | advanced-manufacturing-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-elevated-swarm |
| **Parent Master Swarm ID** | kimi-k2.6-elevated-swarm |

---

## 7. Quick Reference

### Top 5 Pains
1. **Yield Fallout at 7nm and Below Nodes** — Each 1% yield loss at 5nm can cost $50M+ annually per fab.
2. **Battery Cell Formation Cycle Time Variability** — Inconsistent formation limiting gigafactory throughput and capacity utilization.
3. **Additive Manufacturing Build Failure Rate** — >15% metal AM failure rate due to residual stress, powder contamination, parameter drift.
4. **Cleanroom Particle Contamination Events** — Uncontrolled contamination in ISO 1-5 cleanrooms causing wafer scrap and expensive shutdown cycles.
5. **FDC Alarm Fatigue** — >80% false alarm rate causing operator desensitization and delayed true fault response.

### Top 5 KPIs
1. **Wafer Yield (Die Per Wafer)** — `Good Die / Total Die x 100` | Benchmark: N7 85-92%, N5 80-88%
2. **Cell Formation Cycle Time** — Avg charge start to grading complete | Benchmark: 72-96h (cylindrical)
3. **AM Build Failure Rate** — `Failed Builds / Total Builds x 100` | Benchmark: <8% metal LPBF
4. **FDC False Alarm Rate** — `False Alarms / Total Alarms x 100` | Benchmark: <20%
5. **Fab Cycle Time Ratio** — `Actual CT / Raw Process Time` | Benchmark: <2.5 (high-volume)

### Top 3 Personas
1. **Fab Process Engineer** — Senior process/module owner; yield accountable to node targets; trusts SPIE/SEMI/OEM technical notes.
2. **Battery Cell Designer** — Electrochemist; pressure on cost/kWh and safety; trusts DOE/ARPA-E and Journal of Power Sources.
3. **Industry 4.0 Architect** — Digital transformation lead; must demonstrate ROI on I4.0 investments; trusts Gartner/IDC and WEF Lighthouse cases.

### Key Value Formulas
| Formula | Expression | Example |
|---|---|---|
| **Semiconductor Yield Loss Cost** | `(BaselineYield - TargetYield)/100 x AnnualWaferStarts x DiePerWafer x DieRevenue` | $24M/year (4pp improvement) |
| **Battery Formation Capacity Value** | `(BaselineCT - TargetCT)/BaselineCT x ChamberCount x ChamberCapacityGWh x ContributionMargin/GWh` | $70M/year (24h CT reduction) |
| **AM Build Failure Cost Avoidance** | `(BaselineFail - TargetFail)/100 x AnnualBuilds x (Material + Machine + PostProcessing)` | $1.6M/year (10pp reduction) |
| **FDC False Alarm Cost** | `AnnualFalseAlarms x (StoppageMin x $/min + InvestigationMin x LaborRate)` | $6.1M/year |
| **IIoT Data Cost Reduction** | `(StorageSave + ComputeSave) + UtilizationIncrease x AnalyticsValue` | $3.5M/year |

---

*End of SKILL.md for Advanced Manufacturing Subpack (S1.3)*
