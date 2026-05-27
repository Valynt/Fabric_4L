/**
 * Go-to-Market SaaS Subpack — Signal Examples (TypeScript)
 * ID: go-to-market-saas-v1
 * Parent Master: saas-master-v1
 * Generated: 2026-04-25
 */

// ============================================================
// TYPES
// ============================================================

export type SignalConfidence = "HIGH" | "MEDIUM" | "LOW";
export type ValueDriverCategory = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";
export type UrgencyLevel = "HIGH" | "MEDIUM" | "LOW";

export interface SignalRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  confidenceScore: number; // 0.0 - 1.0
  requiredConfirmationSignals: string[];
}

export interface ValueDriver {
  id: string;
  signalPattern: string;
  interpretedPain: string;
  valueDriverCategory: ValueDriverCategory;
  linkedKPIs: string[];
  affectedPersonas: string[];
  confidence: SignalConfidence;
  requiredEvidence: string[];
}

export interface BuyingTrigger {
  id: string;
  name: string;
  triggerEvent: string;
  urgencyLevel: UrgencyLevel;
  typicalTiming: string;
  linkedPains: string[];
  procurementImplications: string;
}

export interface WorkedExample {
  id: string;
  name: string;
  scenario: string;
  formulaExpression: string;
  inputs: Record<string, number | string>;
  calculationSteps: string[];
  totalValue: string;
  valueCategory: string;
  confidence: SignalConfidence;
}

// ============================================================
// SIGNAL RULES (18)
// ============================================================

export const gtmSignalRules: SignalRule[] = [
  {
    id: "SR_GTM_001",
    signalName: "Forecast Variance >30% for 2 Consecutive Quarters",
    rawSignalPattern:
      "Quarterly forecast variance exceeds 30% in two consecutive quarters; rep self-reported variance >25%",
    interpretedMeaning:
      "Forecasting process is broken. Likely causes: intuition-based calls, no leading indicators, pipeline bloat, or poor qualification.",
    linkedPains: ["S2P001", "P011"],
    linkedKPIs: ["K_GTM_001", "K_GTM_002", "K036"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: [
      "Pipeline coverage >5x",
      "Deal slippage >30%",
      "No engagement scoring in CRM",
    ],
  },
  {
    id: "SR_GTM_002",
    signalName: "CSM ARR Coverage >$5M per Rep",
    rawSignalPattern:
      "ARR per CSM exceeds $5M; QBR completion rate <60%; CS hours >70% reactive",
    interpretedMeaning:
      "CS team is overloaded. Expansion pipeline will be missed, churn risks will be invisible, and proactive engagement is impossible.",
    linkedPains: ["S2P002", "P023"],
    linkedKPIs: ["K_GTM_004", "K_GTM_005", "K_GTM_006"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: [
      "Health scores stale >30 days",
      "Expansion ARR declining",
      "QBR completion <50%",
    ],
  },
  {
    id: "SR_GTM_003",
    signalName: "ABM Account Engagement Rate <15%",
    rawSignalPattern:
      "Target account engagement <15%; ABM pipeline contribution <15%; no intent data in CRM",
    interpretedMeaning:
      "ABM program is underperforming. Marketing spend wasted on broad targeting; sales lacks account intelligence.",
    linkedPains: ["S2P003", "P021"],
    linkedKPIs: ["K_GTM_007", "K_GTM_008", "K066"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: [
      "Marketing-sourced pipeline <20%",
      "No account-level scoring",
      "Sales unaware of marketing engagement",
    ],
  },
  {
    id: "SR_GTM_004",
    signalName: "Quota Attainment <50% for 2+ Quarters",
    rawSignalPattern:
      "<50% of reps hitting quota; ramp time >9 months; top 20% generating >80% of revenue",
    interpretedMeaning:
      "Sales model is broken. Territories, comp plans, hiring profile, or enablement are misaligned. High turnover risk.",
    linkedPains: ["S2P004", "P001"],
    linkedKPIs: ["K_GTM_010", "K_GTM_011", "K_GTM_012"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: [
      "Sales turnover >25%",
      "Territory complaints from reps",
      "Comp plan changes >2x in 12 months",
    ],
  },
  {
    id: "SR_GTM_005",
    signalName: "SDR Pipeline Declining >10% QoQ",
    rawSignalPattern:
      "SDR-sourced pipeline per rep declining >10% QoQ; meeting acceptance rate <40%; outreach response <2%",
    interpretedMeaning:
      "SDR function is losing effectiveness. Channel saturation, messaging fatigue, or tooling gaps. CAC will rise.",
    linkedPains: ["S2P005", "P001", "P021"],
    linkedKPIs: ["K_GTM_013", "K_GTM_014", "K_GTM_015"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: [
      "SDR turnover increasing",
      "New SDR tool implemented <6 months ago",
      "Market segment expansion into new ICP",
    ],
  },
  {
    id: "SR_GTM_006",
    signalName: "Enterprise TTV >90 Days",
    rawSignalPattern:
      "Enterprise customers taking >90 days to first value; onboarding completion <60%; manual provisioning",
    interpretedMeaning:
      "Onboarding is a bottleneck. Early churn risk is elevated. Product may be too complex or CS under-resourced.",
    linkedPains: ["S2P006", "P010"],
    linkedKPIs: ["K_GTM_016", "K_GTM_017", "K_GTM_018"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: [
      "Early churn (<90 days) >15%",
      "No onboarding playbook",
      "Customer complaints about setup complexity",
    ],
  },
  {
    id: "SR_GTM_007",
    signalName: "Renewal Forecast Variance >25%",
    rawSignalPattern:
      "Renewal forecast misses by >25%; renewals managed <60 days before expiry; auto-renewal <40%",
    interpretedMeaning:
      "Renewal process is reactive, not predictive. Churn surprises will hit quarterly revenue. Working capital at risk.",
    linkedPains: ["S2P007", "P002", "P005"],
    linkedKPIs: ["K_GTM_019", "K_GTM_020", "K005"],
    confidenceScore: 0.83,
    requiredConfirmationSignals: [
      "Churn surprises in final 30 days >30%",
      "No predictive churn model",
      "Last-minute discounting >25%",
    ],
  },
  {
    id: "SR_GTM_008",
    signalName: "Expansion Concentration in Top 20%",
    rawSignalPattern:
      "Top 20% of accounts generate >80% of expansion; mid-tier expansion <5%; no usage-based triggers",
    interpretedMeaning:
      "Expansion motion is not scalable. Majority of customer base is under-monetized. Product-led expansion missing.",
    linkedPains: ["S2P008", "P002"],
    linkedKPIs: ["K_GTM_021", "K_GTM_022", "K018"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: [
      "No expansion playbooks for mid-tier",
      "CSMs not compensated on expansion",
      "Product usage data not in CRM",
    ],
  },
  {
    id: "SR_GTM_009",
    signalName: "Churn Surprise Rate >30% in Final 30 Days",
    rawSignalPattern:
      ">30% of churned customers gave no warning <30 days before renewal; health score false positive rate >30%",
    interpretedMeaning:
      "Churn prediction is broken. Health scores are lagging or gamed. No early warning system exists.",
    linkedPains: ["S2P009", "P005", "P023"],
    linkedKPIs: ["K_GTM_023", "K_GTM_024", "K_GTM_025"],
    confidenceScore: 0.86,
    requiredConfirmationSignals: [
      "Product usage decline not surfaced",
      "No predictive model deployed",
      "Churn reasons captured post-cancellation",
    ],
  },
  {
    id: "SR_GTM_010",
    signalName: "Average Discount Rate >20%",
    rawSignalPattern:
      "Average discount rate >20%; discounts approved without deal desk; finance learns post-signature",
    interpretedMeaning:
      "Pricing governance is absent. ASP erosion and price anchoring will persist. Deal desk function needed.",
    linkedPains: ["S2P010", "P018"],
    linkedKPIs: ["K_GTM_026", "K_GTM_027", "K057"],
    confidenceScore: 0.84,
    requiredConfirmationSignals: [
      "Price realization <70%",
      "Competitor price-matching standard practice",
      "No discount authority matrix",
    ],
  },
  {
    id: "SR_GTM_011",
    signalName: "RevOps Reporting Cycle >5 Days",
    rawSignalPattern:
      "Monthly reporting prep >5 days; >5 disconnected systems; manual CSV reconciliation",
    interpretedMeaning:
      "RevOps is trapped in manual data work. Decisions made on stale data. System integration needed.",
    linkedPains: ["S2P011", "P017"],
    linkedKPIs: ["K_GTM_029", "K_GTM_030", "K_GTM_031"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: [
      "Same metric different by department",
      "No self-service dashboards",
      "CRM-billing mismatch >5%",
    ],
  },
  {
    id: "SR_GTM_012",
    signalName: "Lead Routing Delay >24 Hours",
    rawSignalPattern:
      "Average lead routing time >24 hours; MQL-to-first-contact <60%; manual assignment",
    interpretedMeaning:
      "Speed-to-lead is critical. Every hour of delay reduces conversion. Routing automation needed.",
    linkedPains: ["S2P012", "P021"],
    linkedKPIs: ["K_GTM_032", "K_GTM_033", "K_GTM_034"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: [
      "Lead routing accuracy <80%",
      "No SLA enforcement",
      "Leads routed to wrong territory",
    ],
  },
  {
    id: "SR_GTM_013",
    signalName: "Sales Content Adoption <20%",
    rawSignalPattern:
      "Content utilization rate <20%; reps spend >2 hours/week searching; custom decks >50% of deals",
    interpretedMeaning:
      "Enablement investment is wasted. Content is not findable, relevant, or trusted. Brand inconsistency risk.",
    linkedPains: ["S2P013", "P004"],
    linkedKPIs: ["K_GTM_035", "K_GTM_036", "K_GTM_037"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: [
      "No content effectiveness tracking",
      "Content library >100 items unsorted",
      "Win rate by content usage unmeasured",
    ],
  },
  {
    id: "SR_GTM_014",
    signalName: "Multi-Product Attach Rate <10%",
    rawSignalPattern:
      "Cross-sell rate <10%; no account expansion plans; product silos prevent coordinated selling",
    interpretedMeaning:
      "Multi-product strategy is under-executed. Revenue concentration risk in single product. Land-and-expand motion broken.",
    linkedPains: ["S2P014", "P002"],
    linkedKPIs: ["K_GTM_038", "K_GTM_039", "K_GTM_040"],
    confidenceScore: 0.75,
    requiredConfirmationSignals: [
      "No cross-sell quotas",
      "Product teams don't share account data",
      "Customers unaware of other products",
    ],
  },
  {
    id: "SR_GTM_015",
    signalName: "RFP Response Time >14 Days",
    rawSignalPattern:
      "RFP response >14 days; security questionnaire >40 hours each; no template library",
    interpretedMeaning:
      "Procurement friction is destroying deal velocity. Competitive disadvantage in enterprise deals.",
    linkedPains: ["S2P015", "P009", "P003"],
    linkedKPIs: ["K_GTM_041", "K_GTM_042", "K_GTM_043"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: [
      "Deals stalled in procurement >30 days",
      "No RFP win rate tracked",
      "Security review backlog",
    ],
  },
  {
    id: "SR_GTM_016",
    signalName: "PLG-to-Sales Handoff Dropout >40%",
    rawSignalPattern:
      "PQL-to-meeting rate <20%; sales follow-up >48 hours on PQLs; PQL criteria misaligned",
    interpretedMeaning:
      "PLG-to-sales motion is broken. Product-qualified leads are not sales-ready or sales is not PLG-aware.",
    linkedPains: ["S2P016", "P012"],
    linkedKPIs: ["K_GTM_044", "K_GTM_045", "K_GTM_046"],
    confidenceScore: 0.76,
    requiredConfirmationSignals: [
      "Sales reps lack usage context",
      "PQL volume >sales capacity",
      "PLG-sourced pipeline <15%",
    ],
  },
  {
    id: "SR_GTM_017",
    signalName: "Commission Dispute Rate >10%",
    rawSignalPattern:
      "Commission cycle >10 days; >10% reps dispute monthly; no real-time commission visibility",
    interpretedMeaning:
      "Compensation operations are manual and error-prone. Rep morale and trust erode. Admin burden is high.",
    linkedPains: ["S2P017", "P017"],
    linkedKPIs: ["K_GTM_047", "K_GTM_048", "K_GTM_049"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: [
      "SPIF tracking in spreadsheets",
      "Clawbacks delayed >30 days",
      "Finance manually calculates commissions",
    ],
  },
  {
    id: "SR_GTM_018",
    signalName: "Single-Threaded Deals >70% of Pipeline",
    rawSignalPattern:
      "Single-threaded deals >70%; <2 contacts per opportunity; deals lost to champion leaving >15%",
    interpretedMeaning:
      "Sales team lacks multi-threading discipline. Pipeline is fragile. Deal coaching and methodology needed.",
    linkedPains: ["S2P018", "P004"],
    linkedKPIs: ["K_GTM_050", "K_GTM_051", "K_GTM_052"],
    confidenceScore: 0.84,
    requiredConfirmationSignals: [
      "No stakeholder mapping in CRM",
      "No executive sponsorship program",
      "Win rate by contact count unmeasured",
    ],
  },
];

// ============================================================
// VALUE DRIVERS (12)
// ============================================================

export const gtmValueDrivers: ValueDriver[] = [
  {
    id: "VD_GTM_001",
    signalPattern: "Forecast variance >30% for 2+ quarters with no leading indicators",
    interpretedPain:
      "Forecasting process broken; board and investor credibility at risk; cash planning inaccurate",
    valueDriverCategory: "Working Capital",
    linkedKPIs: ["K_GTM_001", "K_GTM_002", "K_GTM_003"],
    affectedPersonas: ["CFO", "CRO", "RevOps Manager", "CEO"],
    confidence: "HIGH",
    requiredEvidence: [
      "Quarterly forecast variance report",
      "Rep-level forecast accuracy data",
      "Pipeline inspection notes",
    ],
  },
  {
    id: "VD_GTM_002",
    signalPattern: "CSM coverage >$5M ARR per rep with reactive hours >70%",
    interpretedPain:
      "Customer success overloaded; expansion pipeline missed; churn risks invisible",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["K_GTM_004", "K_GTM_005", "K_GTM_006"],
    affectedPersonas: ["Chief Customer Officer", "CSM Director", "CRO"],
    confidence: "HIGH",
    requiredEvidence: [
      "CSM coverage report",
      "Time allocation study",
      "QBR completion rate",
    ],
  },
  {
    id: "VD_GTM_003",
    signalPattern: "ABM engagement <15% and pipeline contribution <20%",
    interpretedPain:
      "ABM investment not generating pipeline; marketing-sales alignment broken; intent data unused",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["K_GTM_007", "K_GTM_008", "K_GTM_009"],
    affectedPersonas: ["VP Marketing", "ABM Manager", "CRO"],
    confidence: "HIGH",
    requiredEvidence: [
      "Account engagement report",
      "Pipeline source analysis",
      "Intent data usage audit",
    ],
  },
  {
    id: "VD_GTM_004",
    signalPattern: "Quota attainment <50% for 2+ quarters with ramp time >9 months",
    interpretedPain:
      "Sales model broken; hiring, comp, enablement, or territory design misaligned; high turnover risk",
    valueDriverCategory: "Cost Savings",
    linkedKPIs: ["K_GTM_010", "K_GTM_011", "K_GTM_012"],
    affectedPersonas: ["CRO", "VP Sales", "Sales Enablement Lead"],
    confidence: "HIGH",
    requiredEvidence: [
      "Quota attainment trend",
      "Ramp time analysis",
      "Turnover data",
      "Territory distribution",
    ],
  },
  {
    id: "VD_GTM_005",
    signalPattern: "SDR pipeline declining >10% QoQ with response rates <2%",
    interpretedPain:
      "SDR function losing effectiveness; CAC rising; channel saturation or messaging fatigue",
    valueDriverCategory: "Cost Savings",
    linkedKPIs: ["K_GTM_013", "K_GTM_014", "K_GTM_015"],
    affectedPersonas: ["VP Sales", "CRO", "RevOps Manager"],
    confidence: "HIGH",
    requiredEvidence: [
      "SDR productivity trend",
      "Channel performance analysis",
      "Messaging test results",
    ],
  },
  {
    id: "VD_GTM_006",
    signalPattern: "Enterprise TTV >90 days and onboarding completion <60%",
    interpretedPain:
      "Onboarding is bottleneck; early churn risk elevated; product complexity not managed",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["K_GTM_016", "K_GTM_017", "K_GTM_018"],
    affectedPersonas: ["VP Customer Success", "Onboarding Specialist", "CRO"],
    confidence: "HIGH",
    requiredEvidence: [
      "TTV distribution",
      "Onboarding funnel analysis",
      "Churn correlation with TTV",
    ],
  },
  {
    id: "VD_GTM_007",
    signalPattern: "Renewal forecast variance >25% with <40% auto-renewal",
    interpretedPain:
      "Renewal process reactive; churn surprises will hit quarterly revenue; working capital at risk",
    valueDriverCategory: "Working Capital",
    linkedKPIs: ["K_GTM_019", "K_GTM_020", "K_GTM_021"],
    affectedPersonas: ["CFO", "Chief Customer Officer", "CSM Director"],
    confidence: "HIGH",
    requiredEvidence: [
      "Renewal forecast accuracy",
      "Auto-renewal rate",
      "Churn surprise analysis",
    ],
  },
  {
    id: "VD_GTM_008",
    signalPattern: "Average discount rate >20% with no deal desk function",
    interpretedPain:
      "Pricing governance absent; ASP erosion; margin compression; competitor price anchoring",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["K_GTM_026", "K_GTM_027", "K057"],
    affectedPersonas: ["CFO", "CRO", "Pricing Strategist"],
    confidence: "HIGH",
    requiredEvidence: [
      "Deal-level discount analysis",
      "ASP trend",
      "Competitor pricing intelligence",
    ],
  },
  {
    id: "VD_GTM_009",
    signalPattern: "RevOps reporting cycle >5 days with >5 disconnected systems",
    interpretedPain:
      "RevOps trapped in manual work; decisions on stale data; system integration needed",
    valueDriverCategory: "Cost Savings",
    linkedKPIs: ["K_GTM_029", "K_GTM_030", "K_GTM_031"],
    affectedPersonas: ["RevOps Manager", "CFO", "CRO"],
    confidence: "HIGH",
    requiredEvidence: [
      "Reporting cycle time study",
      "System inventory",
      "Manual process audit",
    ],
  },
  {
    id: "VD_GTM_010",
    signalPattern: "Lead routing delay >24 hours with MQL-to-first-contact <60%",
    interpretedPain:
      "Speed-to-lead critical; conversion degrading with every hour of delay; routing automation gap",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["K_GTM_032", "K_GTM_033", "K_GTM_034"],
    affectedPersonas: ["VP Marketing", "VP Sales", "RevOps Manager"],
    confidence: "HIGH",
    requiredEvidence: [
      "Lead response time analysis",
      "Conversion by response time bucket",
      "Routing accuracy report",
    ],
  },
  {
    id: "VD_GTM_011",
    signalPattern: "Sales content utilization <20% with rep custom decks >50% of deals",
    interpretedPain:
      "Enablement investment wasted; content not findable or relevant; brand inconsistency risk",
    valueDriverCategory: "Cost Savings",
    linkedKPIs: ["K_GTM_035", "K_GTM_036", "K_GTM_037"],
    affectedPersonas: ["Sales Enablement Lead", "VP Sales", "CRO"],
    confidence: "HIGH",
    requiredEvidence: [
      "Content usage analytics",
      "Win rate by content usage",
      "Rep time allocation study",
    ],
  },
  {
    id: "VD_GTM_012",
    signalPattern: "Single-threaded deals >70% with champion-loss churn >15%",
    interpretedPain:
      "Sales lacks multi-threading discipline; pipeline fragile; deal coaching needed",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["K_GTM_050", "K_GTM_051", "K_GTM_052"],
    affectedPersonas: ["VP Sales", "CRO", "Sales Enablement Lead"],
    confidence: "HIGH",
    requiredEvidence: [
      "Contact role analysis",
      "Win rate by contact count",
      "Champion turnover data",
    ],
  },
];

// ============================================================
// BUYING TRIGGERS (14)
// ============================================================

export const gtmBuyingTriggers: BuyingTrigger[] = [
  {
    id: "BT_GTM_001",
    name: "Missed Board Forecast",
    triggerEvent: "Company misses quarterly revenue forecast by >15% in board meeting",
    urgencyLevel: "HIGH",
    typicalTiming: "Within 30 days of board meeting",
    linkedPains: ["S2P001", "S2P011", "P011"],
    procurementImplications:
      "Accelerated evaluation; CFO and CEO directly involved; budget may be reallocated from other initiatives",
  },
  {
    id: "BT_GTM_002",
    name: "CRO or VP Sales Departure",
    triggerEvent:
      "Chief Revenue Officer or VP Sales departs; new leader wants to implement their methodology",
    urgencyLevel: "HIGH",
    typicalTiming: "First 60-90 days of new leader tenure",
    linkedPains: ["S2P004", "S2P018", "P001"],
    procurementImplications:
      "New leader brings vendor relationships; open to new tools that demonstrate quick wins; budget often available",
  },
  {
    id: "BT_GTM_003",
    name: "Series B/C Funding Round",
    triggerEvent:
      "Company raises Series B or C; investors demand predictable growth and efficient unit economics",
    urgencyLevel: "HIGH",
    typicalTiming: "First 6 months post-fundraise",
    linkedPains: ["S2P001", "S2P004", "P001"],
    procurementImplications:
      "Growth budget unlocked; board reporting needs drive RevOps investments; scale-ready tools prioritized",
  },
  {
    id: "BT_GTM_004",
    name: "Q4 Churn Surprise",
    triggerEvent:
      "Unexpected churn in Q4 destroys annual retention targets; panic sets in for next year",
    urgencyLevel: "HIGH",
    typicalTiming: "January-March following surprise",
    linkedPains: ["S2P007", "S2P009", "P002", "P005"],
    procurementImplications:
      "Customer success tooling budget typically unlocked; predictive churn models prioritized; may bypass normal procurement",
  },
  {
    id: "BT_GTM_005",
    name: "New Pricing Model Launch",
    triggerEvent:
      "Company decides to launch usage-based or value-based pricing; needs deal desk and CPQ support",
    urgencyLevel: "MEDIUM",
    typicalTiming: "3-6 months before pricing launch",
    linkedPains: ["S2P010", "P018"],
    procurementImplications:
      "Pricing platform and deal desk tools needed; often bundled with CPQ renewal; finance and product involved",
  },
  {
    id: "BT_GTM_006",
    name: "Enterprise Sales Motion Launch",
    triggerEvent:
      "PLG or SMB-focused company decides to add enterprise sales team and process",
    urgencyLevel: "HIGH",
    typicalTiming: "First 90 days of enterprise motion",
    linkedPains: ["S2P006", "S2P015", "S2P016", "P012"],
    procurementImplications:
      "Full GTM stack needed: forecasting, enablement, deal desk, RFP response; greenfield buying opportunity",
  },
  {
    id: "BT_GTM_007",
    name: "Sales Team Expansion >50%",
    triggerEvent:
      "Company plans to double sales headcount in 12 months; existing tools won't scale",
    urgencyLevel: "MEDIUM",
    typicalTiming: "3-6 months before expansion",
    linkedPains: ["S2P004", "S2P013", "S2P017"],
    procurementImplications:
      "Scaling requirements drive platform consolidation; onboarding and enablement tools prioritized; volume pricing leverage",
  },
  {
    id: "BT_GTM_008",
    name: "Security Questionnaire Backlog",
    triggerEvent:
      "Enterprise deals stalled due to security review backlog; SOC 2 renewal pending",
    urgencyLevel: "HIGH",
    typicalTiming: "When >5 enterprise deals are blocked",
    linkedPains: ["S2P015", "P009"],
    procurementImplications:
      "RFP response and compliance automation tools; may be emergency purchase; CISO and sales align",
  },
  {
    id: "BT_GTM_009",
    name: "ABM Budget Allocation",
    triggerEvent:
      "Marketing team receives dedicated ABM budget for the first time or significant increase",
    urgencyLevel: "MEDIUM",
    typicalTiming: "Start of fiscal year or mid-year budget reallocation",
    linkedPains: ["S2P003", "P021"],
    procurementImplications:
      "ABM platform evaluation cycle; intent data and CRM integration requirements; marketing-owns decision",
  },
  {
    id: "BT_GTM_010",
    name: "Customer Success Team Creation",
    triggerEvent:
      "Company moves from founder-led CS to dedicated CS team; needs playbooks and tooling",
    urgencyLevel: "MEDIUM",
    typicalTiming: "First 90 days of CS function standup",
    linkedPains: ["S2P002", "S2P006", "S2P009"],
    procurementImplications:
      "CS platform greenfield purchase; onboarding and health scoring prioritized; budget often from customer success initiative",
  },
  {
    id: "BT_GTM_011",
    name: "Commission Calculation Crisis",
    triggerEvent:
      "Major commission error discovered; rep trust erodes; manual process exposed",
    urgencyLevel: "HIGH",
    typicalTiming: "Within 30 days of discovery",
    linkedPains: ["S2P017", "P017"],
    procurementImplications:
      "Compensation automation urgently needed; finance and sales ops align; may bypass RFP for speed",
  },
  {
    id: "BT_GTM_012",
    name: "Post-Merger GTM Integration",
    triggerEvent:
      "Company acquires another SaaS business; needs to unify GTM processes, forecasts, and reporting",
    urgencyLevel: "HIGH",
    typicalTiming: "First 6 months post-close",
    linkedPains: ["S2P001", "S2P011", "S2P014"],
    procurementImplications:
      "Platform consolidation opportunity; single RevOps platform to replace multiple systems; enterprise deal size",
  },
  {
    id: "BT_GTM_013",
    name: "IPO Preparation",
    triggerEvent:
      "Company preparing for IPO; needs predictable revenue, accurate forecasting, and audit-ready RevOps",
    urgencyLevel: "HIGH",
    typicalTiming: "12-18 months before expected IPO",
    linkedPains: ["S2P001", "S2P010", "S2P011"],
    procurementImplications:
      "Enterprise-grade platforms preferred; audit trails and compliance critical; budget typically available",
  },
  {
    id: "BT_GTM_014",
    name: "Major Customer Churn Announcement",
    triggerEvent:
      "Largest customer or >5% of ARR churns unexpectedly; triggers reactive investment in retention tooling",
    urgencyLevel: "HIGH",
    typicalTiming: "Within 60 days of churn event",
    linkedPains: ["S2P007", "S2P009", "P002"],
    procurementImplications:
      "Customer success and predictive analytics tools; often emotional purchase driven by CEO/CRO directive",
  },
];

// ============================================================
// WORKED EXAMPLES (3)
// ============================================================

export const gtmWorkedExamples: WorkedExample[] = [
  {
    id: "WE_GTM_001",
    name: "RevOps Forecast Accuracy Improvement",
    scenario:
      "A $50M ARR B2B SaaS company has quarterly forecast variance of 35%, causing buffer hiring mistakes and board credibility issues.",
    formulaExpression:
      "(Prior Forecast Variance - New Forecast Variance) × Quota × 4 Quarters × Cost of Capital % + (Hours Saved × Cycles × Hourly Rate)",
    inputs: {
      "Prior forecast variance": 0.35,
      "New forecast variance": 0.15,
      "Quarterly quota": 5000000,
      "Cost of capital": 0.08,
      "Hours saved per cycle": 32,
      "Cycles per year": 12,
      "Hourly rate": 85,
    },
    calculationSteps: [
      "Forecast value = (35% - 15%) × $5M × 4 × 8% = $320,000 annual value",
      "RevOps time savings = 32 hours × 12 cycles × $85/hour = $32,640 annual capacity recovery",
      "Total annual value = $320,000 + $32,640 = $352,640",
    ],
    totalValue: "$352,640 annual value",
    valueCategory: "Working Capital + Cost Savings",
    confidence: "HIGH",
  },
  {
    id: "WE_GTM_002",
    name: "CSM Coverage Optimization and Churn Reduction",
    scenario:
      "A $80M ARR SaaS company has 12 CSMs each managing $6.7M ARR. Early churn is 14% and expansion ARR per CSM is declining.",
    formulaExpression:
      "(Excess ARR / Optimal ARR) × CSMs × CSM Cost + (TTV Reduction / Current TTV) × Early Churn × New Customers × ACV × Lifetime",
    inputs: {
      "Current ARR per CSM": 6700000,
      "Target ARR per CSM": 4500000,
      "CSMs over threshold": 8,
      "CSM cost": 130000,
      "Early churn rate": 0.14,
      "New customers per year": 300,
      "ACV": 30000,
      "Customer lifetime": 3.5,
      "TTV reduction": 45,
      "Current TTV": 90,
    },
    calculationSteps: [
      "CSM optimization savings = ($6.7M - $4.5M) / $4.5M × 8 × $130K = $509,333 annual savings",
      "Churn reduction value = (90 - 45) / 90 × 14% × 300 × $30K × 3.5 = $2,450,000 LTV protected",
      "Total value = $509,333 + $2,450,000 = $2,959,333",
    ],
    totalValue: "$2.96M annual + LTV value",
    valueCategory: "Cost Savings + Revenue Uplift",
    confidence: "MEDIUM",
  },
  {
    id: "WE_GTM_003",
    name: "Discount Governance and ASP Recovery",
    scenario:
      "A $120M ARR SaaS company has an average discount rate of 22%, eroding ASP and gross margin. No deal desk function exists.",
    formulaExpression:
      "(Current Discount - Target Discount) × Deal Size × Deal Volume × Gross Margin - Implementation Cost",
    inputs: {
      "Current discount rate": 0.22,
      "Target discount rate": 0.12,
      "Average deal size": 45000,
      "Annual deal volume": 600,
      "Gross margin": 0.78,
      "Implementation cost": 150000,
    },
    calculationSteps: [
      "ASP recovery = (22% - 12%) × $45K × 600 × 78% = $2,106,000 annual gross margin recovery",
      "Less deal desk implementation cost = $150,000",
      "Net first-year value = $2,106,000 - $150,000 = $1,956,000",
      "ROI = $1,956,000 / $150,000 = 13x first-year ROI",
    ],
    totalValue: "$1.96M net first-year value (13x ROI)",
    valueCategory: "Revenue Uplift + Margin Recovery",
    confidence: "MEDIUM",
  },
];

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

/**
 * Find signal rules by linked pain ID.
 */
export function findSignalsByPain(painId: string): SignalRule[] {
  return gtmSignalRules.filter((s) => s.linkedPains.includes(painId));
}

/**
 * Find value drivers by linked KPI ID.
 */
export function findDriversByKPI(kpiId: string): ValueDriver[] {
  return gtmValueDrivers.filter((v) => v.linkedKPIs.includes(kpiId));
}

/**
 * Find buying triggers by linked pain ID.
 */
export function findTriggersByPain(painId: string): BuyingTrigger[] {
  return gtmBuyingTriggers.filter((t) => t.linkedPains.includes(painId));
}

/**
 * Get all high-confidence signals (confidenceScore >= 0.80).
 */
export function getHighConfidenceSignals(): SignalRule[] {
  return gtmSignalRules.filter((s) => s.confidenceScore >= 0.80);
}

/**
 * Calculate total addressable value from a worked example by scaling inputs.
 */
export function scaleWorkedExample(
  example: WorkedExample,
  scaleFactor: number
): string {
  // This is a simplified scaler — production would parse formulaExpression
  return `Scaling ${example.name} by ${scaleFactor}x: apply scaleFactor to all monetary inputs and recalculate.`;
}

// ============================================================
// EXPORTS
// ============================================================

export const GTM_SUBPACK_ID = "go-to-market-saas-v1";
export const GTM_PARENT_MASTER_ID = "saas-master-v1";
export const GTM_SUBPACK_VERSION = "1.0.0";
