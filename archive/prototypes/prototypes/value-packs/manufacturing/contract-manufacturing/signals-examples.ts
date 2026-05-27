/**
 * Contract Manufacturing Subpack — Signal & Formula Examples
 * 
 * TypeScript code demonstrating signal-to-hypothesis workflows,
 * formula evaluations, and benchmark comparisons for contract
 * manufacturing engagements.
 * 
 * Pack ID: contract-manufacturing-v1
 * Parent: manufacturing-master-v1
 */

// ============================================================================
// INTERFACES — Aligned with Master Pack type system
// ============================================================================

interface SignalInterpretationRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  confidenceScore: number;
  requiredConfirmationSignals: string[];
}

interface BusinessPain {
  id: string;
  name: string;
  description: string;
  symptoms: string[];
  prevalence: "HIGH" | "MEDIUM" | "LOW";
  confidence: "HIGH" | "MEDIUM" | "LOW";
}

interface KPIDefinition {
  id: string;
  name: string;
  formula: string;
  unit: string;
  typicalRange: string;
  benchmarkRange: string;
}

interface ValueFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  exampleCalculation: string;
  confidenceRules: Array<{ condition: string; confidence: number }>;
}

interface Benchmark {
  id: string;
  name: string;
  value: string;
  range: string;
  unit: string;
  source: string;
  confidence: string;
}

interface PersonaProfile {
  id: string;
  name: string;
  role: string;
  seniority: string;
  goals: string[];
  pressures: string[];
  trustedEvidence: string[];
  dislikedClaims: string[];
  decisionInfluence: "economic" | "technical" | "user";
}

// ============================================================================
// SUBPACK DATA — Contract Manufacturing Signal Rules
// ============================================================================

const SIGNAL_RULES: SignalInterpretationRule[] = [
  {
    id: "sig-cm-001",
    signalName: "Customer Audit Finding Surge",
    rawSignalPattern: "Customer audit findings increase >50% vs prior audit cycle or repeat findings >40%",
    interpretedMeaning: "Quality system degradation or customer tightening standards; QMS modernization and CAPA remediation likely needed",
    linkedPains: ["pain-cm-001", "pain-cm-004", "pain-cm-009"],
    linkedKPIs: ["kpi-cm-001", "kpi-capa-cycle-time", "kpi-cm-007"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: ["Audit report details", "Customer communication tone", "Previous audit trend"]
  },
  {
    id: "sig-cm-002",
    signalName: "Customer Portal Integration Job Postings",
    rawSignalPattern: "Multiple postings for EDI/API developers, customer integration specialists, or portal managers",
    interpretedMeaning: "Investment in customer data exchange infrastructure; multi-tenant integration platform demand likely",
    linkedPains: ["pain-cm-011", "pain-cm-014"],
    linkedKPIs: ["kpi-cm-009", "kpi-cm-013", "kpi-cm-017"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: ["Customer count growth", "Current portal inventory", "IT budget trajectory"]
  },
  {
    id: "sig-cm-003",
    signalName: "Technology Transfer Staff Expansion",
    rawSignalPattern: "Hiring surge for tech transfer engineers, validation specialists, or process engineers in <90 days",
    interpretedMeaning: "Pipeline of new customer transfers or capacity expansion; transfer acceleration and knowledge management tools needed",
    linkedPains: ["pain-cm-003", "pain-cm-016"],
    linkedKPIs: ["kpi-cm-004", "kpi-ramp-yield", "kpi-cm-016"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: ["Customer announcement pipeline", "Capacity expansion signals", "New product categories"]
  },
  {
    id: "sig-cm-004",
    signalName: "Quote Win Rate Decline",
    rawSignalPattern: "Public or inferred data showing declining bid win rate or increasing quote turnaround time",
    interpretedMeaning: "Competitive pricing pressure or quoting capability gaps; costing accuracy and quoting tool investment trigger",
    linkedPains: ["pain-cm-006", "pain-cm-007"],
    linkedKPIs: ["kpi-cm-002", "kpi-cm-008", "kpi-cm-018"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: ["Competitor pricing intelligence", "Customer feedback on quotes", "Cost structure analysis"]
  },
  {
    id: "sig-cm-005",
    signalName: "Customer Concentration Risk Disclosure",
    rawSignalPattern: "10-K or annual report shows top customer >40% revenue or revenue from top 3 >80%",
    interpretedMeaning: "Severe customer dependency; diversification, contract protection, and margin defense strategies urgent",
    linkedPains: ["pain-cm-007", "pain-022"],
    linkedKPIs: ["kpi-cm-003", "kpi-cm-002", "kpi-cm-011"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: ["Contract renewal timeline", "Customer financial health", "Pipeline diversification efforts"]
  },
  {
    id: "sig-cm-006",
    signalName: "Multi-Site Acquisition or Expansion",
    rawSignalPattern: "Announcement of new site acquisition, greenfield facility, or major multi-site consolidation",
    interpretedMeaning: "Standardization and integration challenge; ERP/MES consolidation, SOP harmonization, and cross-site visibility tools needed",
    linkedPains: ["pain-cm-002", "pain-cm-008"],
    linkedKPIs: ["kpi-cm-006", "kpi-cm-012", "kpi-cm-020"],
    confidenceScore: 0.84,
    requiredConfirmationSignals: ["Integration timeline", "Current site count", "Technology platform decisions"]
  },
  {
    id: "sig-cm-007",
    signalName: "Regulatory Inspection Observation Increase",
    rawSignalPattern: "FDA 483 observations, EMA findings, or customer regulatory audits showing upward trend",
    interpretedMeaning: "Compliance system stress; eQMS, batch record digitization, and inspection readiness programs needed",
    linkedPains: ["pain-cm-009", "pain-cm-010"],
    linkedKPIs: ["kpi-cm-020", "kpi-audit-findings", "kpi-cm-014"],
    confidenceScore: 0.90,
    requiredConfirmationSignals: ["Observation categorization", "CAPA effectiveness history", "Regulatory inspection schedule"]
  },
  {
    id: "sig-cm-008",
    signalName: "Customer OTIF Penalty or Chargeback Increase",
    rawSignalPattern: "Earnings or operational reports showing rising customer penalties, chargebacks, or SLA credits",
    interpretedMeaning: "Delivery performance crisis; planning, scheduling, and fulfillment capability investment trigger",
    linkedPains: ["pain-cm-017", "pain-004"],
    linkedKPIs: ["kpi-cm-021", "kpi-otd", "kpi-cm-011"],
    confidenceScore: 0.83,
    requiredConfirmationSignals: ["Penalty categorization", "Root cause analysis", "Capacity vs demand balance"]
  },
  {
    id: "sig-cm-009",
    signalName: "EBR (Electronic Batch Record) Implementation Signal",
    rawSignalPattern: "Job postings for EBR specialists, MES validation engineers, or paperless manufacturing roles",
    interpretedMeaning: "Digital transformation of batch documentation; MES/eQMS integration and validation services demand",
    linkedPains: ["pain-cm-010", "pain-cm-009"],
    linkedKPIs: ["kpi-cm-014", "kpi-cm-020", "kpi-data-latency"],
    confidenceScore: 0.79,
    requiredConfirmationSignals: ["MES vendor selection", "Validation strategy", "Current documentation cost"]
  },
  {
    id: "sig-cm-010",
    signalName: "Co-Packing Line Investment Announcement",
    rawSignalPattern: "Capital expenditure or press release for new packaging lines, labeling capacity, or co-packing expansion",
    interpretedMeaning: "Capacity scaling for private label or consumer goods; packaging efficiency and changeover optimization tools needed",
    linkedPains: ["pain-cm-012", "pain-cm-016"],
    linkedKPIs: ["kpi-cm-015", "kpi-changeover-time", "kpi-cm-016"],
    confidenceScore: 0.76,
    requiredConfirmationSignals: ["Line type and speed", "Customer pipeline", "Changeover frequency projection"]
  },
  {
    id: "sig-cm-011",
    signalName: "Customer-Owned Inventory Write-Off",
    rawSignalPattern: "Financial disclosure or earnings mention of material write-offs, customer disputes, or consignment reconciliation issues",
    interpretedMeaning: "Inventory tracking and liability management gaps; WMS/ERP traceability and customer inventory visibility needed",
    linkedPains: ["pain-cm-005", "pain-cm-015"],
    linkedKPIs: ["kpi-cm-019", "kpi-cm-018", "kpi-inv-turns"],
    confidenceScore: 0.81,
    requiredConfirmationSignals: ["Inventory aging analysis", "Contract liability terms", "Customer notification patterns"]
  },
  {
    id: "sig-cm-012",
    signalName: "Toll Manufacturing Margin Compression",
    rawSignalPattern: "Toll manufacturer earnings showing declining margin despite flat revenue; material pass-through issues evident",
    interpretedMeaning: "Toll fee structure or yield reconciliation problems; costing accuracy and material tracking tools needed",
    linkedPains: ["pain-cm-013", "pain-cm-006", "pain-022"],
    linkedKPIs: ["kpi-cm-010", "kpi-cm-008", "kpi-cm-018"],
    confidenceScore: 0.77,
    requiredConfirmationSignals: ["Toll fee structure", "Yield variance trend", "Material price escalation"]
  },
  {
    id: "sig-cm-013",
    signalName: "Serialization or Track-and-Trace Mandate",
    rawSignalPattern: "Regulatory deadline approaching (e.g., DSCSA, EU FMD) or customer serialization requirements expanding",
    interpretedMeaning: "Serialization infrastructure investment urgent; aggregation, verification, and exception management tools needed",
    linkedPains: ["pain-cm-018", "pain-cm-011"],
    linkedKPIs: ["kpi-cm-020", "kpi-cm-017", "kpi-cm-007"],
    confidenceScore: 0.87,
    requiredConfirmationSignals: ["Regulatory deadline", "Customer scope", "Current serialization readiness"]
  },
  {
    id: "sig-cm-014",
    signalName: "QBR Preparation Job Surge",
    rawSignalPattern: "Hiring for customer-facing analysts, program managers, or business operations roles focused on reporting",
    interpretedMeaning: "Customer reporting and analytics burden growing; automated scorecard, BI, and customer portal tools needed",
    linkedPains: ["pain-cm-014", "pain-cm-011"],
    linkedKPIs: ["kpi-cm-013", "kpi-cm-017", "kpi-cm-009"],
    confidenceScore: 0.74,
    requiredConfirmationSignals: ["Customer count", "Report types", "Current prep hours"]
  },
  {
    id: "sig-cm-015",
    signalName: "Capacity Commitment Miss Pattern",
    rawSignalPattern: "Recurring misses on customer capacity commitments or volume forecasts in earnings/operational data",
    interpretedMeaning: "Planning and scheduling capability gaps; APS, demand sensing, and capacity planning tools needed",
    linkedPains: ["pain-cm-017", "pain-020"],
    linkedKPIs: ["kpi-cm-022", "kpi-schedule-attainment", "kpi-cm-021"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: ["Commitment accuracy history", "Demand volatility", "Planning system maturity"]
  },
  {
    id: "sig-cm-016",
    signalName: "Cold Chain or GDP Non-Compliance Event",
    rawSignalPattern: "Public temperature excursion, GDP audit failure, or customer notification on distribution compliance",
    interpretedMeaning: "Temperature-controlled logistics and GDP compliance system gaps; monitoring, validation, and documentation tools needed",
    linkedPains: ["pain-cm-018", "pain-cm-009"],
    linkedKPIs: ["kpi-cm-020", "kpi-cm-007", "kpi-cm-011"],
    confidenceScore: 0.89,
    requiredConfirmationSignals: ["Excursion root cause", "Monitoring system age", "GDP audit history"]
  },
  {
    id: "sig-cm-017",
    signalName: "Customer Contract Renewal at Risk",
    rawSignalPattern: "Customer announces dual-sourcing, competitive bidding, or contract renegotiation with volume uncertainty",
    interpretedMeaning: "Customer retention crisis; performance improvement, pricing restructure, and relationship management investment urgent",
    linkedPains: ["pain-cm-007", "pain-cm-017", "pain-cm-001"],
    linkedKPIs: ["kpi-cm-003", "kpi-cm-021", "kpi-cm-001"],
    confidenceScore: 0.86,
    requiredConfirmationSignals: ["Contract end date", "Competitor presence", "Customer satisfaction trend"]
  },
  {
    id: "sig-cm-018",
    signalName: "Private Label NPI Pipeline Surge",
    rawSignalPattern: "Customer briefs or product launches increasing >30% with flat internal NPI capacity",
    interpretedMeaning: "NPI bottleneck; artwork management, regulatory label approval, and fast-track tech transfer tools needed",
    linkedPains: ["pain-cm-016", "pain-cm-003"],
    linkedKPIs: ["kpi-cm-016", "kpi-npi-cycle-time", "kpi-cm-004"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: ["NPI backlog", "Artwork capacity", "Regulatory approval timelines"]
  }
];

// ============================================================================
// SUBPACK DATA — Contract Manufacturing KPIs
// ============================================================================

const KPIS: KPIDefinition[] = [
  { id: "kpi-cm-001", name: "Customer Audit Score", formula: "(100 - weighted findings) / 100 x 100", unit: "%", typicalRange: "60-95%", benchmarkRange: ">90%" },
  { id: "kpi-cm-002", name: "Quote Win Rate", formula: "Won / Total x 100", unit: "%", typicalRange: "15-45%", benchmarkRange: "30-50%" },
  { id: "kpi-cm-003", name: "Customer Concentration Index", formula: "Sum of (Rev%)^2", unit: "Herfindahl", typicalRange: "0.15-0.80", benchmarkRange: "<0.25" },
  { id: "kpi-cm-004", name: "Technology Transfer Cycle Time", formula: "Days to PPQ completion", unit: "days", typicalRange: "90-270", benchmarkRange: "90-150" },
  { id: "kpi-cm-005", name: "Contract Amendment Rate", formula: "Amendments / Active x 100", unit: "%", typicalRange: "10-60%", benchmarkRange: "<20%" },
  { id: "kpi-cm-006", name: "Multi-Site OEE Variance", formula: "Max - Min OEE", unit: "% points", typicalRange: "10-35", benchmarkRange: "<15" },
  { id: "kpi-cm-007", name: "Customer NCR Rate", formula: "NCR / Shipments x 1M", unit: "PPM", typicalRange: "100-5000", benchmarkRange: "<500" },
  { id: "kpi-cm-008", name: "COGS per Customer SKU", formula: "Direct Cost / Active SKUs", unit: "$/SKU", typicalRange: "Varies", benchmarkRange: "Top quartile" },
  { id: "kpi-cm-009", name: "Customer Portal Data Latency", formula: "Event to portal update", unit: "minutes", typicalRange: "60-1440", benchmarkRange: "<15" },
  { id: "kpi-cm-010", name: "Toll Material Yield Variance", formula: "(Theoretical - Actual) x Value", unit: "% + $/batch", typicalRange: "0.5-5%", benchmarkRange: "<1%" },
  { id: "kpi-cm-011", name: "Customer Escalation Rate", formula: "Escalations / Interactions x 100", unit: "%", typicalRange: "1-10%", benchmarkRange: "<2%" },
  { id: "kpi-cm-012", name: "Site-to-Site Standardization Score", formula: "Weighted alignment index", unit: "0-100", typicalRange: "40-80", benchmarkRange: ">85" },
  { id: "kpi-cm-013", name: "Customer QBR Prep Hours", formula: "Hours/customer/quarter", unit: "hours/qtr", typicalRange: "40-200", benchmarkRange: "<30" },
  { id: "kpi-cm-014", name: "Batch Record Review Cycle Time", formula: "Batch complete to QA release", unit: "days", typicalRange: "3-21", benchmarkRange: "<5" },
  { id: "kpi-cm-015", name: "Co-Packing Line Efficiency", formula: "Actual / Scheduled x 100", unit: "%", typicalRange: "50-85%", benchmarkRange: ">80%" },
  { id: "kpi-cm-016", name: "Private Label NPI Cycle Time", formula: "Brief to first batch", unit: "weeks", typicalRange: "8-24", benchmarkRange: "<12" },
  { id: "kpi-cm-017", name: "Customer Scorecard Compliance", formula: "Meeting Target / Total x 100", unit: "%", typicalRange: "70-95%", benchmarkRange: ">95%" },
  { id: "kpi-cm-018", name: "Transfer Pricing Dispute Rate", formula: "Disputed / Total x 100", unit: "%", typicalRange: "2-15%", benchmarkRange: "<3%" },
  { id: "kpi-cm-019", name: "Excess & Obsolete Customer-Owned Inventory", formula: "E&O / Total Consignment x 100", unit: "%", typicalRange: "1-8%", benchmarkRange: "<1%" },
  { id: "kpi-cm-020", name: "Regulatory Inspection Readiness Score", formula: "Weighted composite", unit: "0-100", typicalRange: "50-85", benchmarkRange: ">90" },
  { id: "kpi-cm-021", name: "OTIF to Customer", formula: "OTIF Orders / Total x 100", unit: "%", typicalRange: "75-98%", benchmarkRange: ">98%" },
  { id: "kpi-cm-022", name: "Capacity Commitment Accuracy", formula: "Actual within Commit / Total x 100", unit: "%", typicalRange: "70-95%", benchmarkRange: ">95%" }
];

// ============================================================================
// SUBPACK DATA — Contract Manufacturing Pains
// ============================================================================

const PAINS: BusinessPain[] = [
  {
    id: "pain-cm-001",
    name: "Customer Audit Finding Closure Delays",
    description: "Repeated customer quality audits generate findings that remain open beyond agreed timelines, threatening contract renewal and new business qualification.",
    symptoms: [
      "Customer audit findings >10 per visit",
      "Average closure time >45 days",
      "Repeat findings >30% of total",
      "Customer escalation to VP level",
      "Conditional approval on new product transfers"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-002",
    name: "Multi-Site ERP Consolidation for Toll Operations",
    description: "Toll manufacturers running customer-mandated ERP instances across multiple sites cannot consolidate operational visibility.",
    symptoms: [
      "Each site runs different ERP tenant or instance",
      "Intercompany reconciliation >5 days",
      "No consolidated capacity visibility",
      "Manual toll fee calculations",
      "Customer reporting in inconsistent formats"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-003",
    name: "Technology Transfer Delays and Knowledge Loss",
    description: "Slow or incomplete transfer of product/process knowledge from customer or development to manufacturing.",
    symptoms: [
      "Tech transfer cycle >6 months",
      "First production batch yield <60%",
      "Missing process parameter rationale",
      "No structured knowledge repository",
      "Key personnel dependency on transfer teams"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-004",
    name: "Customer-Specific Quality Agreement Management",
    description: "Each customer imposes unique quality agreements, inspection protocols, and documentation requirements.",
    symptoms: [
      ">20 active quality agreements",
      "No central agreement repository",
      "Customer-specific SOPs >40% of total",
      "Missed customer-specific test requirements",
      "Deviation rate from customer specs >5%"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-005",
    name: "Customer-Owned Inventory and Consignment Tracking Gaps",
    description: "Inability to accurately track customer-owned materials, WIP, and finished goods.",
    symptoms: [
      "Monthly inventory reconciliation disputes >5%",
      "Customer-owned E&O >2% of consigned value",
      "No real-time consignment visibility",
      "Manual ERP adjustments for customer splits",
      "Cycle count accuracy <95% on consigned items"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-006",
    name: "Quoting and Costing Accuracy Deficits",
    description: "Inability to accurately estimate costs for custom jobs.",
    symptoms: [
      "Quote win rate <25%",
      "Actual cost > quoted cost >15% of jobs",
      "No standard cost library by customer family",
      "Manual Excel-based quoting",
      "Turnaround time >5 days for complex quotes"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-007",
    name: "Customer Concentration and Contract Renewal Risk",
    description: "Over-dependence on one or few customers creating revenue volatility.",
    symptoms: [
      "Top 3 customers >70% revenue",
      "Contract renewal price-downs >5% annually",
      "No pipeline to replace top customer",
      "Customer notice period <90 days",
      "Volume commitments unfulfilled by customer"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-008",
    name: "Multi-Site Standardization and Best Practice Diffusion",
    description: "Acquired or greenfield sites operating with inconsistent processes.",
    symptoms: [
      "OEE variance across sites >20 points",
      "Different SOP versions by site",
      "No cross-site performance benchmarking",
      "Customer audits fail at specific sites",
      "Duplicate system licenses per site"
    ],
    prevalence: "MEDIUM",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-009",
    name: "Regulatory Inspection Readiness Gaps",
    description: "Contract manufacturers facing inspections with insufficient preparation.",
    symptoms: [
      "Inspection prep >4 weeks",
      "Missing batch records >2%",
      "No mock inspection program",
      "Data integrity ALCOA+ gaps",
      "Previous inspection observations unresolved >6 months"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-010",
    name: "Batch Record and Documentation Cycle Time",
    description: "Manual or semi-manual batch record review and approval.",
    symptoms: [
      "Batch record review >5 days",
      "First-pass review rejection rate >15%",
      "No electronic batch records (EBR)",
      "Review queue backlog >2 weeks",
      "Transcription errors >3%"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-011",
    name: "Customer Portal and Data Exchange Friction",
    description: "Multiple customer portals and reporting formats creating manual work.",
    symptoms: [
      ">5 different customer portal platforms",
      "Manual data re-entry between systems",
      "Customer scorecard data >24h old",
      "EDI/API connections <50% of customers",
      "Customer complaint on data accuracy >monthly"
    ],
    prevalence: "MEDIUM",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-012",
    name: "Co-Packing and Assembly Line Changeover Complexity",
    description: "Frequent packaging and assembly format changes causing downtime.",
    symptoms: [
      "Changeover time >40% of shift",
      "Packaging/labeling errors >1%",
      "No digital work instructions per SKU",
      "Material verification manual",
      "Customer-specific pack config >50 active"
    ],
    prevalence: "MEDIUM",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-013",
    name: "Toll Manufacturing Yield Variance and Reconciliation",
    description: "Toll manufacturers unable to reconcile theoretical vs actual yield.",
    symptoms: [
      "Yield variance >3% from theoretical",
      "Monthly toll reconciliation disputes",
      "No real-time yield tracking by batch",
      "Material loss accountability gaps",
      "Customer claims for material replacement >$500K/year"
    ],
    prevalence: "MEDIUM",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-014",
    name: "Customer Scorecard and QBR Preparation Burden",
    description: "Excessive manual effort preparing quarterly business reviews.",
    symptoms: [
      "QBR prep >80 hours per customer",
      "Data aggregation from >5 systems",
      "Scorecard metrics rejected by customer",
      "No automated KPI calculation",
      "Customer-specific report formats >10"
    ],
    prevalence: "MEDIUM",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-015",
    name: "Excess and Obsolete Customer-Owned Inventory Liability",
    description: "Contract manufacturers holding customer-owned inventory that becomes obsolete.",
    symptoms: [
      "Customer-owned E&O >$2M",
      "No contractual liability clarity",
      "Aged consignment >12 months",
      "Customer product lifecycle discontinuation notices missed",
      "Write-off approval cycle >90 days"
    ],
    prevalence: "MEDIUM",
    confidence: "MEDIUM"
  },
  {
    id: "pain-cm-016",
    name: "Private Label NPI and Artwork Approval Delays",
    description: "Slow private label product introduction due to artwork and approval cycles.",
    symptoms: [
      "NPI cycle >12 weeks",
      "Artwork revision rounds >5 per product",
      "Regulatory label approval backlog",
      "No digital artwork management",
      "Customer approval delays >50% of cycle"
    ],
    prevalence: "MEDIUM",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-017",
    name: "On-Time-In-Full (OTIF) Performance Gaps",
    description: "Failure to meet customer OTIF requirements causing chargebacks.",
    symptoms: [
      "OTIF <90% to key customer",
      "Customer chargebacks >1% of revenue",
      "Partial shipment rate >5%",
      "No OTIF root cause analytics",
      "Customer SLA penalties incurred"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "pain-cm-018",
    name: "Customer-Specific Regulatory and GDP Compliance",
    description: "Beyond-baseline requirements for GDP, serialization, and cold chain.",
    symptoms: [
      "GDP audit findings >3 per inspection",
      "Serialization aggregation errors >0.1%",
      "Cold chain excursion events >monthly",
      "No validated temperature monitoring",
      "Customer-specific SOPs >60% of quality system"
    ],
    prevalence: "HIGH",
    confidence: "HIGH"
  }
];

// ============================================================================
// SUBPACK DATA — Vertical Formulas
// ============================================================================

const FORMULAS: ValueFormula[] = [
  {
    id: "vf-cm-001",
    name: "Customer Audit Finding Remediation Value",
    formulaExpression: "(Baseline Findings - Target Findings) x Cost per Finding + Avoided Contract Loss Risk + Reduced QBR Prep",
    requiredInputs: ["Baseline findings/audit", "Target findings/audit", "Cost per finding", "Contract renewal value at risk", "QBR prep hours reduction"],
    outputUnit: "$/year",
    exampleCalculation: "15 -> 3 findings, $25K/find, $5M contract at risk, 40->10 hrs QBR = $0.3M + $0.5M + $0.05M = $0.85M",
    confidenceRules: [
      { condition: "Finding cost from historical remediation", confidence: 0.85 },
      { condition: "Contract value from CRM", confidence: 0.8 }
    ]
  },
  {
    id: "vf-cm-002",
    name: "Multi-Site ERP Consolidation ROI",
    formulaExpression: "IT License Reduction + Intercompany Reconciliation Labor Savings + Consolidated Reporting Labor Savings + Inventory Visibility Value",
    requiredInputs: ["Current ERP instances", "Target instances", "License cost per instance", "Intercompany reconciliation FTE", "Consolidated reporting FTE", "Inventory carrying cost improvement %"],
    outputUnit: "$/year",
    exampleCalculation: "8->2 instances, $200K/license, 5->1 FTE reconcile, 3->0.5 FTE report = $1.2M + $0.4M + $0.25M = $1.85M",
    confidenceRules: [
      { condition: "License costs from vendor contracts", confidence: 0.9 },
      { condition: "FTE from time studies", confidence: 0.8 }
    ]
  },
  {
    id: "vf-cm-003",
    name: "Technology Transfer Acceleration Value",
    formulaExpression: "(Baseline Cycle - Target Cycle) x Monthly Revenue per Transfer x Transfer Volume + Ramp Yield Improvement Value",
    requiredInputs: ["Baseline tech transfer days", "Target days", "Revenue per transfer/month", "Transfers per year", "Baseline ramp yield", "Target ramp yield", "Customer penalty for delay"],
    outputUnit: "$/year",
    exampleCalculation: "180->90 days, $1M/month, 12 transfers, 60%->80% yield = $12M + $2.4M = $14.4M",
    confidenceRules: [
      { condition: "Transfer cycle from project tracking", confidence: 0.85 },
      { condition: "Revenue per transfer validated", confidence: 0.8 }
    ]
  },
  {
    id: "vf-cm-004",
    name: "Quality Agreement Management Efficiency",
    formulaExpression: "Agreement Repository Labor Savings + SOP Harmonization Savings + Avoided Customer Deviation Cost",
    requiredInputs: ["Active quality agreements", "Hours per agreement management", "Customer-specific SOP count", "SOP maintenance hours", "Annual customer deviations", "Cost per deviation"],
    outputUnit: "$/year",
    exampleCalculation: "30 agreements, 10->2 hrs each, 50->20 SOPs, 20->5 deviations @ $50K = $0.24M + $0.15M + $0.75M = $1.14M",
    confidenceRules: [
      { condition: "Agreement count from contract database", confidence: 0.9 },
      { condition: "Deviation cost from quality records", confidence: 0.8 }
    ]
  },
  {
    id: "vf-cm-005",
    name: "Customer-Owned Inventory Reconciliation Value",
    formulaExpression: "Dispute Reduction Value + E&O Avoidance + Real-Time Visibility Labor Savings",
    requiredInputs: ["Monthly reconciliation disputes", "Cost per dispute", "Customer-owned E&O value", "E&O reduction target %", "FTE on consignment tracking", "Hourly rate"],
    outputUnit: "$/year",
    exampleCalculation: "10->1 disputes/month, $10K each, $2M E&O -> $0.5M, 3->0.5 FTE = $1.08M + $0.15M + $0.1M = $1.33M",
    confidenceRules: [
      { condition: "Dispute history from finance", confidence: 0.85 },
      { condition: "E&O from inventory reports", confidence: 0.8 }
    ]
  },
  {
    id: "vf-cm-006",
    name: "Quoting Accuracy Improvement Value",
    formulaExpression: "(Win Rate Gain x Pipeline Value) + Cost Variance Reduction + Quote Turnaround Labor Savings",
    requiredInputs: ["Baseline win rate", "Target win rate", "Annual pipeline value", "Cost variance %", "Annual quoted revenue", "Baseline quote days", "Target quote days", "Quoting FTE cost"],
    outputUnit: "$/year",
    exampleCalculation: "20%->35% win, $100M pipeline, 15%->5% variance, 5->2 days, 4 FTE = $15M + $2M + $0.3M",
    confidenceRules: [
      { condition: "Win rate from CRM", confidence: 0.8 },
      { condition: "Pipeline value validated", confidence: 0.75 }
    ]
  },
  {
    id: "vf-cm-007",
    name: "Customer Concentration Risk Mitigation Value",
    formulaExpression: "Avoided Revenue Volatility Cost + Diversification Pipeline Value + Contract Terms Improvement",
    requiredInputs: ["Top customer revenue %", "Target top customer %", "Annual revenue", "Revenue volatility from concentration", "New customer qualification cost", "Contract price protection %"],
    outputUnit: "$/year",
    exampleCalculation: "50%->30% top customer, $500M revenue, 8% volatility, $2M qualification, 3% price protection = $8M + $2M + $6M",
    confidenceRules: [
      { condition: "Customer concentration from financials", confidence: 0.9 },
      { condition: "Pipeline validated", confidence: 0.7 }
    ]
  },
  {
    id: "vf-cm-008",
    name: "Multi-Site Standardization Value",
    formulaExpression: "OEE Uplift Value + Audit Cost Reduction + IT Consolidation Savings + Cross-Site Labor Flexibility Value",
    requiredInputs: ["Site count", "OEE variance points", "Target variance", "Annual audit cost per site", "IT duplication cost", "Cross-training hours saved"],
    outputUnit: "$/year",
    exampleCalculation: "5 sites, 25->10 pt variance, $100K audit/site, $300K IT dup, 500 hrs = $3M + $0.5M + $0.3M + $0.04M = $3.84M",
    confidenceRules: [
      { condition: "OEE by site validated", confidence: 0.85 },
      { condition: "IT costs from vendor invoices", confidence: 0.9 }
    ]
  },
  {
    id: "vf-cm-009",
    name: "Batch Record Digitization Value",
    formulaExpression: "Review Labor Savings + Error Reduction Value + Release Acceleration Cash Benefit + Compliance Risk Reduction",
    requiredInputs: ["Batches per year", "Baseline review hours/batch", "Target hours", "Hourly rate", "Error rate baseline", "Error cost", "Days release acceleration", "WIP value", "WACC", "Penalty risk probability"],
    outputUnit: "$/year",
    exampleCalculation: "2K batches, 8->2 hrs, $75/hr, 5%->1% errors @ $5K, 3 day accel, $10M WIP, 12%, 5% penalty = $0.9M + $0.4M + $0.12M + $0.25M = $1.67M",
    confidenceRules: [
      { condition: "Batch count and review time from QA", confidence: 0.85 },
      { condition: "WIP from ERP", confidence: 0.9 }
    ]
  },
  {
    id: "vf-cm-010",
    name: "OTIF Improvement and Chargeback Avoidance",
    formulaExpression: "Chargeback Avoidance + Customer Retention Value + Expedite Cost Reduction",
    requiredInputs: ["Baseline OTIF %", "Target OTIF %", "Annual revenue", "Chargeback rate", "Customer churn risk value", "Expedite cost baseline", "Target expedite"],
    outputUnit: "$/year",
    exampleCalculation: "85%->98% OTIF, $400M revenue, 1.5%->0.2% chargeback, $20M retention, $2M->0.3M expedite = $5.2M + $20M + $1.7M",
    confidenceRules: [
      { condition: "OTIF from customer scorecards", confidence: 0.9 },
      { condition: "Chargebacks from AR", confidence: 0.85 }
    ]
  },
  {
    id: "vf-cm-011",
    name: "Co-Packing Changeover Efficiency Value",
    formulaExpression: "(Baseline Changeover Hours - Target Hours) x Production Value per Hour x Margin + Label Error Avoidance",
    requiredInputs: ["Changeovers per week", "Baseline hours", "Target hours", "Weeks/year", "Production value/hour", "Margin %", "Label error rate baseline", "Target error rate", "Cost per label error"],
    outputUnit: "$/year",
    exampleCalculation: "30->15 hrs/week, 50 weeks, $5K/hr, 20%, 2%->0.3% errors @ $10K = $3.75M + $0.26M = $4.01M",
    confidenceRules: [
      { condition: "Changeover time from time studies", confidence: 0.85 },
      { condition: "Label errors from QA records", confidence: 0.8 }
    ]
  },
  {
    id: "vf-cm-012",
    name: "Regulatory Inspection Readiness Value",
    formulaExpression: "Prep Labor Reduction + Avoided Observation Cost + Avoided Consent Decree/Warning Letter Risk",
    requiredInputs: ["Inspections per year", "Baseline prep hours", "Target hours", "Hourly rate", "Average observations", "Cost per observation", "Consent decree probability", "Consent decree cost", "Warning letter probability", "Warning letter cost"],
    outputUnit: "$/year",
    exampleCalculation: "4 inspections, 200->40 hrs, $150/hr, 8->1 obs @ $50K, 5%x$10M, 10%x$2M = $0.096M + $0.35M + $0.5M + $0.2M = $1.15M",
    confidenceRules: [
      { condition: "Inspection history from regulatory database", confidence: 0.9 },
      { condition: "Observation cost from compliance budget", confidence: 0.8 }
    ]
  },
  {
    id: "vf-cm-013",
    name: "Customer Portal and Data Exchange Value",
    formulaExpression: "Manual Data Entry Labor Elimination + Customer Satisfaction Retention Value + Scorecard Automation Savings + API Integration Fee Avoidance",
    requiredInputs: ["Customer count", "Data entry hours per customer/week", "Hourly rate", "Customer retention value", "QBR prep hours reduction", "API integration cost per customer", "Target API coverage %"],
    outputUnit: "$/year",
    exampleCalculation: "20 customers, 10->1 hrs/week, $75/hr, $10M retention, 50->10 hrs QBR, $50K API = $0.7M + $10M + $0.3M + $0.5M",
    confidenceRules: [
      { condition: "Data entry from time studies", confidence: 0.8 },
      { condition: "Customer value from CRM", confidence: 0.85 }
    ]
  }
];

// ============================================================================
// SUBPACK DATA — Benchmarks
// ============================================================================

const BENCHMARKS: Benchmark[] = [
  { id: "bench-cm-001", name: "Customer Audit Score - World Class", value: "95%", range: "92-98%", unit: "%", source: "GxP Audit Benchmark Consortium", confidence: "HIGH" },
  { id: "bench-cm-002", name: "Customer Audit Score - Average", value: "78%", range: "65-85%", unit: "%", source: "Customer Quality Audit Consortium", confidence: "HIGH" },
  { id: "bench-cm-003", name: "Quote Win Rate - EMS", value: "28%", range: "20-40%", unit: "%", source: "Circana EMS Market Report", confidence: "HIGH" },
  { id: "bench-cm-004", name: "Quote Win Rate - CDMO", value: "35%", range: "25-50%", unit: "%", source: "IQVIA CDMO Benchmark", confidence: "HIGH" },
  { id: "bench-cm-005", name: "Tech Transfer Cycle - Pharma CDMO", value: "120", range: "90-180", unit: "days", source: "ISPE GPG", confidence: "HIGH" },
  { id: "bench-cm-006", name: "Tech Transfer Cycle - EMS", value: "60", range: "30-90", unit: "days", source: "Circana EMS Operations", confidence: "MEDIUM" },
  { id: "bench-cm-007", name: "Customer NCR Rate - World Class", value: "200", range: "100-300", unit: "PPM", source: "ASQ Supplier Quality", confidence: "HIGH" },
  { id: "bench-cm-008", name: "Customer NCR Rate - Average", value: "1500", range: "500-3000", unit: "PPM", source: "Customer Quality Audit Consortium", confidence: "MEDIUM" },
  { id: "bench-cm-009", name: "Multi-Site OEE Variance - Best", value: "10", range: "5-15", unit: "% points", source: "Gartner Multi-Site Manufacturing", confidence: "HIGH" },
  { id: "bench-cm-010", name: "Batch Record Review - EBR", value: "2", range: "1-3", unit: "days", source: "PDA Paperless Manufacturing", confidence: "HIGH" },
  { id: "bench-cm-011", name: "Batch Record Review - Paper", value: "10", range: "5-21", unit: "days", source: "FDA Quality Metrics Analysis", confidence: "HIGH" },
  { id: "bench-cm-012", name: "OTIF Contract Mfg - World Class", value: "99%", range: "98-99.5%", unit: "%", source: "Gartner Supply Chain Benchmark", confidence: "HIGH" },
  { id: "bench-cm-013", name: "OTIF Contract Mfg - Average", value: "88%", range: "80-95%", unit: "%", source: "CSCMP", confidence: "HIGH" },
  { id: "bench-cm-014", name: "Customer Concentration - Healthy", value: "0.20", range: "0.15-0.25", unit: "Herfindahl", source: "McKinsey Revenue Risk Model", confidence: "HIGH" },
  { id: "bench-cm-015", name: "Customer Concentration - At Risk", value: "0.55", range: "0.40-0.80", unit: "Herfindahl", source: "Gartner Contract Manufacturing Analysis", confidence: "HIGH" },
  { id: "bench-cm-016", name: "Co-Packing Line Efficiency", value: "75%", range: "65-85%", unit: "%", source: "PMMI Packaging Benchmark", confidence: "MEDIUM" },
  { id: "bench-cm-017", name: "Regulatory Inspection Readiness", value: "90", range: "85-95", unit: "index", source: "PDA Regulatory Readiness Survey", confidence: "MEDIUM" },
  { id: "bench-cm-018", name: "Toll Material Yield Variance", value: "1%", range: "0.5-2%", unit: "%", source: "Toll Manufacturing Association", confidence: "MEDIUM" }
];

// ============================================================================
// WORKED EXAMPLE 1: CDMO Multi-Site EBR and QMS Consolidation
// ============================================================================

/**
 * Calculates the annual value of EBR and QMS consolidation for a CDMO.
 * 
 * @param revenue Annual revenue in USD
 * @param sites Number of manufacturing sites
 * @param batchesPerYear Total batches per year
 * @param baselineAuditFindings Average findings per site per audit
 * @param targetAuditFindings Target findings after improvement
 * @param baselineBatchReleaseDays Current days to release
 * @param targetBatchReleaseDays Target days to release
 * @param customers Number of active customers
 * @param baselineQbrHours Hours per customer per quarter
 * @param targetQbrHours Target hours after automation
 * @param hourlyRate Loaded hourly rate in USD
 * @param wipValue WIP inventory value in USD
 * @param wacc Weighted average cost of capital
 */
function calculateCdmoEbrConsolidationValue(
  revenue: number,
  sites: number,
  batchesPerYear: number,
  baselineAuditFindings: number,
  targetAuditFindings: number,
  baselineBatchReleaseDays: number,
  targetBatchReleaseDays: number,
  customers: number,
  baselineQbrHours: number,
  targetQbrHours: number,
  hourlyRate: number,
  wipValue: number,
  wacc: number
): { totalValue: number; breakdown: Record<string, number>; confidence: number } {
  const costPerFinding = 25000;
  const contractRetentionValue = revenue * 0.004; // Assumption: 0.4% revenue at risk
  
  const auditRemediationValue = 
    (baselineAuditFindings - targetAuditFindings) * sites * costPerFinding + contractRetentionValue;
  
  const releaseAccelerationValue = 
    (baselineBatchReleaseDays - targetBatchReleaseDays) * (wipValue * wacc / 365) * (batchesPerYear / 4) +
    (baselineBatchReleaseDays - targetBatchReleaseDays) * 0.5 * hourlyRate * (batchesPerYear / 4);
  
  const qbrAutomationValue = 
    (baselineQbrHours - targetQbrHours) * customers * 4 * hourlyRate;
  
  const itConsolidationValue = sites * 75000; // Simplified: $75K per site annual savings
  
  const totalValue = auditRemediationValue + releaseAccelerationValue + qbrAutomationValue + itConsolidationValue;
  
  return {
    totalValue,
    breakdown: {
      auditRemediation: auditRemediationValue,
      releaseAcceleration: releaseAccelerationValue,
      qbrAutomation: qbrAutomationValue,
      itConsolidation: itConsolidationValue
    },
    confidence: 0.82
  };
}

// Example invocation:
const cdmoExample = calculateCdmoEbrConsolidationValue(
  500_000_000, 4, 2500, 12, 3, 14, 4, 12, 120, 20, 85, 40_000_000, 0.12
);
console.log("CDMO EBR Consolidation Value:", cdmoExample);

// ============================================================================
// WORKED EXAMPLE 2: EMS Customer Portal and OTIF Improvement
// ============================================================================

/**
 * Calculates the annual value of customer portal implementation and OTIF improvement.
 */
function calculateEmsPortalOtifValue(
  revenue: number,
  customers: number,
  baselineOtif: number,
  targetOtif: number,
  annualChargebacks: number,
  targetChargebacks: number,
  baselineQbrHours: number,
  targetQbrHours: number,
  hourlyRate: number,
  customerRetentionValue: number,
  dataEntryFte: number,
  fteSalary: number
): { totalDirectValue: number; revenueProtected: number; breakdown: Record<string, number>; confidence: number } {
  const chargebackAvoidance = annualChargebacks - targetChargebacks;
  const qbrSavings = (baselineQbrHours - targetQbrHours) * customers * 4 * hourlyRate;
  const dataEntrySavings = dataEntryFte * fteSalary;
  const totalDirectValue = chargebackAvoidance + qbrSavings + dataEntrySavings;
  
  return {
    totalDirectValue,
    revenueProtected: customerRetentionValue,
    breakdown: {
      chargebackAvoidance,
      qbrSavings,
      dataEntrySavings
    },
    confidence: 0.85
  };
}

const emsExample = calculateEmsPortalOtifValue(
  1_200_000_000, 25, 0.85, 0.98, 18_000_000, 2_400_000,
  80, 15, 75, 20_000_000, 5, 85_000
);
console.log("EMS Portal OTIF Value:", emsExample);

// ============================================================================
// WORKED EXAMPLE 3: Toll Manufacturer Yield Reconciliation
// ============================================================================

/**
 * Calculates annual value from yield reconciliation and quoting improvement.
 */
function calculateTollYieldValue(
  revenue: number,
  baselineYieldVariance: number,
  targetYieldVariance: number,
  monthlyDisputes: number,
  disputeCost: number,
  baselineWinRate: number,
  targetWinRate: number,
  pipelineValue: number,
  costVariance: number,
  targetCostVariance: number,
  quotedRevenue: number
): { totalValue: number; breakdown: Record<string, number>; confidence: number } {
  const materialThroughput = revenue * 0.6; // Assume 60% material cost
  const yieldValue = (baselineYieldVariance - targetYieldVariance) * materialThroughput * 0.15;
  const disputeSavings = (monthlyDisputes - 1) * disputeCost * 12;
  const winRateValue = (targetWinRate - baselineWinRate) * pipelineValue * 0.25; // 25% margin
  const costVarianceValue = (costVariance - targetCostVariance) * quotedRevenue;
  const totalValue = yieldValue + disputeSavings + winRateValue + costVarianceValue;
  
  return {
    totalValue,
    breakdown: {
      yieldReconciliation: yieldValue,
      disputeAvoidance: disputeSavings,
      winRateImprovement: winRateValue,
      costVarianceReduction: costVarianceValue
    },
    confidence: 0.72
  };
}

const tollExample = calculateTollYieldValue(
  200_000_000, 0.045, 0.008, 6, 40_000, 0.35, 0.50,
  80_000_000, 0.18, 0.05, 80_000_000
);
console.log("Toll Yield Value:", tollExample);

// ============================================================================
// SIGNAL-TO-HYPOTHESIS WORKFLOW FUNCTIONS
// ============================================================================

/**
 * Evaluates a raw signal against all signal rules and returns matching
 * hypotheses with confidence scores.
 */
function evaluateSignal(
  rawSignal: string,
  context: { revenue?: number; segment?: string; customerCount?: number }
): Array<{
  ruleId: string;
  signalName: string;
  confidence: number;
  linkedPains: BusinessPain[];
  linkedKPIs: KPIDefinition[];
  recommendedDiscoveryQuestions: string[];
}> {
  const matches: ReturnType<typeof evaluateSignal> = [];
  
  for (const rule of SIGNAL_RULES) {
    const matchScore = computeSignalMatchScore(rawSignal, rule.rawSignalPattern);
    if (matchScore > 0.6) {
      const pains = PAINS.filter(p => rule.linkedPains.includes(p.id));
      const kpis = KPIS.filter(k => rule.linkedKPIs.includes(k.id));
      
      matches.push({
        ruleId: rule.id,
        signalName: rule.signalName,
        confidence: rule.confidenceScore * matchScore,
        linkedPains: pains,
        linkedKPIs: kpis,
        recommendedDiscoveryQuestions: generateDiscoveryQuestions(rule, pains, kpis)
      });
    }
  }
  
  return matches.sort((a, b) => b.confidence - a.confidence);
}

/**
 * Simple keyword-based match scorer for signal patterns.
 * In production, this would use NLP/embedding similarity.
 */
function computeSignalMatchScore(rawSignal: string, pattern: string): number {
  const rawLower = rawSignal.toLowerCase();
  const patternLower = pattern.toLowerCase();
  const keywords = patternLower.split(/\s+/).filter(w => w.length > 4);
  const matches = keywords.filter(k => rawLower.includes(k)).length;
  return Math.min(matches / Math.max(keywords.length * 0.5, 1), 1.0);
}

/**
 * Generates discovery questions based on matched rule, pains, and KPIs.
 */
function generateDiscoveryQuestions(
  rule: SignalInterpretationRule,
  pains: BusinessPain[],
  kpis: KPIDefinition[]
): string[] {
  const questions: string[] = [];
  
  for (const pain of pains.slice(0, 2)) {
    questions.push(`What is your current experience with ${pain.name.toLowerCase()}?`);
  }
  
  for (const kpi of kpis.slice(0, 2)) {
    questions.push(`How do you currently measure ${kpi.name}, and where does it stand against the ${kpi.benchmarkRange} benchmark?`);
  }
  
  if (rule.requiredConfirmationSignals.length > 0) {
    questions.push(`Can you share data on: ${rule.requiredConfirmationSignals.join(", ")}?`);
  }
  
  return questions;
}

// ============================================================================
// BENCHMARK COMPARISON UTILITY
// ============================================================================

/**
 * Compares a customer's KPI value against subpack benchmarks.
 */
function compareToBenchmark(kpiId: string, customerValue: number): {
  kpiName: string;
  customerValue: number;
  benchmarkValue: string;
  benchmarkRange: string;
  gap: string;
  riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  improvementPotential: string;
} | null {
  const kpi = KPIS.find(k => k.id === kpiId);
  const benchmark = BENCHMARKS.find(b => b.id.replace("bench-", "bench-cm-").startsWith("bench-cm-") && 
    kpi && b.name.toLowerCase().includes(kpi.name.toLowerCase().split(" ")[0].toLowerCase()));
  
  if (!kpi || !benchmark) return null;
  
  const benchmarkNum = parseFloat(benchmark.value.replace(/[^0-9.]/g, ""));
  const isHigherBetter = benchmarkRangeIsHigherBetter(kpi);
  
  let gap: number;
  let riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  
  if (isHigherBetter) {
    gap = benchmarkNum - customerValue;
    riskLevel = gap > 20 ? "CRITICAL" : gap > 10 ? "HIGH" : gap > 5 ? "MEDIUM" : "LOW";
  } else {
    gap = customerValue - benchmarkNum;
    riskLevel = gap > 20 ? "CRITICAL" : gap > 10 ? "HIGH" : gap > 5 ? "MEDIUM" : "LOW";
  }
  
  return {
    kpiName: kpi.name,
    customerValue,
    benchmarkValue: benchmark.value,
    benchmarkRange: benchmark.range,
    gap: `${gap.toFixed(1)} ${kpi.unit}`,
    riskLevel,
    improvementPotential: `Closing gap to benchmark could unlock ${(gap * 0.05).toFixed(1)}% of revenue value`
  };
}

function benchmarkRangeIsHigherBetter(kpi: KPIDefinition): boolean {
  const lowerIsBetter = ["days", "hours", "PPM", "% points", "Herfindahl", "% + $/batch"];
  return !lowerIsBetter.some(u => kpi.unit.includes(u));
}

// ============================================================================
// EXAMPLE: Full Signal-to-Value Workflow
// ============================================================================

function runFullWorkflowExample(): void {
  // Step 1: Detect raw signal
  const rawSignal = "Customer audit findings increased from 5 to 12 this quarter with 50% repeat findings";
  
  // Step 2: Evaluate signal
  const hypotheses = evaluateSignal(rawSignal, { revenue: 500000000, segment: "CDMO", customerCount: 12 });
  
  console.log("\n=== SIGNAL-TO-HYPOTHESIS RESULTS ===");
  for (const h of hypotheses.slice(0, 3)) {
    console.log(`\nRule: ${h.signalName} (confidence: ${(h.confidence * 100).toFixed(0)}%)`);
    console.log(`Linked Pains: ${h.linkedPains.map(p => p.name).join(", ")}`);
    console.log(`Linked KPIs: ${h.linkedKPIs.map(k => k.name).join(", ")}`);
    console.log("Discovery Questions:");
    h.recommendedDiscoveryQuestions.forEach((q, i) => console.log(`  ${i + 1}. ${q}`));
  }
  
  // Step 3: Benchmark comparison
  const auditComparison = compareToBenchmark("kpi-cm-001", 72);
  console.log("\n=== BENCHMARK COMPARISON ===");
  console.log(auditComparison);
  
  // Step 4: Value quantification
  const value = calculateCdmoEbrConsolidationValue(
    500_000_000, 4, 2500, 12, 3, 14, 4, 12, 120, 20, 85, 40_000_000, 0.12
  );
  console.log("\n=== VALUE QUANTIFICATION ===");
  console.log(`Total Annual Value: $${(value.totalValue / 1_000_000).toFixed(2)}M (confidence: ${(value.confidence * 100).toFixed(0)}%)`);
  console.log("Breakdown:", value.breakdown);
}

runFullWorkflowExample();

// ============================================================================
// EXPORTS
// ============================================================================

export {
  SIGNAL_RULES,
  PAINS,
  KPIS,
  FORMULAS,
  BENCHMARKS,
  evaluateSignal,
  compareToBenchmark,
  calculateCdmoEbrConsolidationValue,
  calculateEmsPortalOtifValue,
  calculateTollYieldValue,
  runFullWorkflowExample
};
