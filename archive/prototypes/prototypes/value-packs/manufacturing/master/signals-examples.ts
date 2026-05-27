/**
 * Manufacturing Master ValuePack — Signal-to-Hypothesis Worked Examples
 * 
 * This file demonstrates the end-to-end reasoning chain:
 *   Raw Signal → Interpreted Signal → Relevant Pains → Affected Personas → 
 *   KPIs Impacted → Value Hypothesis → Confidence → Evidence Needed → Discovery Questions
 * 
 * Pack ID: manufacturing-master-v1
 * Version: 1.0.0
 * Last Updated: 2026-04-25
 */

// ============================================================
// BASE TYPE DEFINITIONS (mirrored from value-pack.json schema)
// ============================================================

type Prevalence = "HIGH" | "MEDIUM" | "LOW";
type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
type ValueCategory = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";
type PersonaInfluence = "economic" | "technical" | "user";

interface RawSignal {
  id: string;
  source: string;
  sourceType: "10-K" | "job_posting" | "earnings_call" | "regulatory_filing" | "news" | "industry_report" | "financial_data";
  signalText: string;
  detectedDate: string;
  companyContext: {
    companyName: string;
    segment: string;
    subSegment: string;
    annualRevenueM: number;
    employeeCount: number;
  };
}

interface InterpretedSignal {
  signalRuleId: string;
  signalName: string;
  interpretedMeaning: string;
  confidenceScore: number; // 0.0 - 1.0
  confidenceRationale: string;
  requiredConfirmationSignals: string[];
  linkedPains: string[];
  linkedKPIs: string[];
}

interface AffectedPersona {
  personaId: string;
  personaName: string;
  role: string;
  decisionInfluence: PersonaInfluence;
  relevanceRationale: string;
  priority: number; // 1-10
}

interface KPIImpact {
  kpiId: string;
  kpiName: string;
  baselineValue: number | string;
  benchmarkValue: number | string;
  gapDescription: string;
  financialImpactEstimate: string;
}

interface ValueHypothesis {
  hypothesisId: string;
  valueDriverCategory: ValueCategory;
  hypothesisStatement: string;
  formulaId: string;
  formulaName: string;
  estimatedAnnualValue: string;
  valueRangeLow: string;
  valueRangeHigh: string;
  confidence: ConfidenceLevel;
  confidenceRationale: string;
  criticalAssumptions: string[];
  validationRequired: boolean;
}

interface EvidenceNeeded {
  evidenceType: string;
  description: string;
  source: string;
  priority: "critical" | "important" | "nice_to_have";
  estimatedEffort: string;
}

interface DiscoveryQuestion {
  questionId: string;
  questionText: string;
  targetPersona: string;
  intent: string;
  expectedInsight: string;
  followUpQuestions: string[];
}

interface WorkedExample {
  exampleId: string;
  title: string;
  description: string;
  rawSignal: RawSignal;
  interpretedSignal: InterpretedSignal;
  relevantPains: Array<{
    painId: string;
    painName: string;
    prevalence: Prevalence;
    relevanceScore: number;
  }>;
  affectedPersonas: AffectedPersona[];
  kpisImpacted: KPIImpact[];
  valueHypothesis: ValueHypothesis;
  evidenceNeeded: EvidenceNeeded[];
  discoveryQuestions: DiscoveryQuestion[];
  recommendedNextActions: string[];
}

// ============================================================
// EXAMPLE 1: FDA WARNING LETTER → QMS MODERNIZATION OPPORTUNITY
// ============================================================

const example1: WorkedExample = {
  exampleId: "ex-001",
  title: "FDA Warning Letter Trigger → Pharmaceutical QMS & Traceability Modernization",
  description:
    "A contract pharmaceutical manufacturer receives an FDA warning letter citing data integrity deficiencies " +
    "and inadequate batch records. This signal triggers a comprehensive quality system modernization opportunity.",

  rawSignal: {
    id: "raw-001",
    source: "FDA Warning Letter Database (public)",
    sourceType: "regulatory_filing",
    signalText:
      "FDA issued Warning Letter WL-2026-0342 to Acme Pharma Manufacturing LLC on March 15, 2026. " +
      "Observations include: (1) Failure to maintain complete batch production and control records (21 CFR 211.188); " +
      "(2) Inadequate validation of computer systems used for quality control data (21 CFR 211.68); " +
      "(3) Insufficient investigation of unexplained discrepancies (21 CFR 211.192). " +
      "Company has 15 working days to respond with corrective action plan.",
    detectedDate: "2026-03-20",
    companyContext: {
      companyName: "Acme Pharma Manufacturing LLC",
      segment: "Process Manufacturing",
      subSegment: "Pharmaceuticals",
      annualRevenueM: 180,
      employeeCount: 850,
    },
  },

  interpretedSignal: {
    signalRuleId: "sig-004",
    signalName: "FDA Warning Letter or Consent Decree",
    interpretedMeaning:
      "Critical quality system failure at a regulated pharmaceutical manufacturer. The warning letter specifically cites " +
      "data integrity, batch record completeness, and computer system validation — all core QMS and MES capabilities. " +
      "Response is mandatory within 15 days. Remediation timeline likely 6-18 months. Budget pressure from legal, " +
      "compliance, and potential customer audits. This is a HIGH-URGENCY trigger with clear solution mapping.",
    confidenceScore: 0.92,
    confidenceRationale:
      "FDA warning letters are public, specific, and legally enforceable. The cited CFR sections directly map to " +
      "QMS/MES functionality. Historical pattern: 80%+ of warning-letter recipients invest in quality system " +
      "modernization within 12 months.",
    requiredConfirmationSignals: [
      "483 observation count and severity from preceding inspection",
      "Company's historical compliance record (prior warning letters?)",
      "Customer notification requirements (big pharma partners?)",
      "Existing QMS vendor and system age",
    ],
    linkedPains: ["pain-008", "pain-018", "pain-024"],
    linkedKPIs: ["kpi-capa-cycle-time", "kpi-audit-findings", "kpi-copq", "kpi-traceability-coverage"],
  },

  relevantPains: [
    {
      painId: "pain-008",
      painName: "Regulatory Compliance and Audit Burden",
      prevalence: "HIGH",
      relevanceScore: 10,
    },
    {
      painId: "pain-018",
      painName: "Product Traceability and Genealogy Gaps",
      prevalence: "HIGH",
      relevanceScore: 9,
    },
    {
      painId: "pain-024",
      painName: "Quality Management System Inefficiency",
      prevalence: "HIGH",
      relevanceScore: 10,
    },
    {
      painId: "pain-010",
      painName: "Poor Production Visibility and Data Silos",
      prevalence: "HIGH",
      relevanceScore: 7,
    },
  ],

  affectedPersonas: [
    {
      personaId: "pers-quality",
      personaName: "VP/Director Quality",
      role: "VP Quality / Director QA",
      decisionInfluence: "technical",
      relevanceRationale:
        "Direct ownership of warning letter response. Career risk if remediation fails. Controls QMS vendor selection.",
      priority: 10,
    },
    {
      personaId: "pers-coo",
      personaName: "Chief Operating Officer",
      role: "COO / EVP Operations",
      decisionInfluence: "economic",
      relevanceRationale:
        "Operational shutdown risk if consent decree follows. Must ensure production continuity during remediation.",
      priority: 9,
    },
    {
      personaId: "pers-cfo",
      personaName: "Chief Financial Officer",
      role: "CFO / VP Finance",
      decisionInfluence: "economic",
      relevanceRationale:
        "Budget approval for remediation. Potential revenue loss from customer suspensions. Insurance implications.",
      priority: 8,
    },
    {
      personaId: "pers-cio",
      personaName: "Chief Information Officer",
      role: "CIO / CTO",
      decisionInfluence: "technical",
      relevanceRationale:
        "Computer system validation (CSV) cited. IT infrastructure for QMS/MES integration. Data integrity architecture.",
      priority: 7,
    },
    {
      personaId: "pers-plant",
      personaName: "Plant Manager / GM",
      role: "Plant Manager / General Manager",
      decisionInfluence: "user",
      relevanceRationale:
        "Daily production impact from new batch record processes. Must train operators on electronic systems.",
      priority: 6,
    },
  ],

  kpisImpacted: [
    {
      kpiId: "kpi-capa-cycle-time",
      kpiName: "CAPA Cycle Time",
      baselineValue: "120 days (estimated from warning letter context)",
      benchmarkValue: "<30 days",
      gapDescription: "CAPA process takes 4x benchmark. Root cause: manual tracking, no workflow automation.",
      financialImpactEstimate:
        "Each delayed CAPA extends batch hold time. Estimated $50K per CAPA in hold inventory + labor. " +
        "50 open CAPAs = $2.5M working capital impact annually.",
    },
    {
      kpiId: "kpi-audit-findings",
      kpiName: "Regulatory Audit Findings",
      baselineValue: "8+ findings per inspection (implied by warning letter severity)",
      benchmarkValue: "0-3 findings",
      gapDescription: "Quality system lacks closed-loop control. Findings recur because root cause not systematically addressed.",
      financialImpactEstimate:
        "Each finding requires 200+ hours remediation at $150/hr = $30K. Plus potential customer audit failures " +
        "threatening $50M+ contract revenue.",
    },
    {
      kpiId: "kpi-copq",
      kpiName: "Cost of Poor Quality",
      baselineValue: "18% of revenue (estimated for warning-letter firm)",
      benchmarkValue: "5-15%",
      gapDescription: "High external failure costs from rework, retesting, regulatory response, and customer penalties.",
      financialImpactEstimate:
        "$180M revenue × 3pp reduction = $5.4M annual COPQ reduction potential.",
    },
    {
      kpiId: "kpi-traceability-coverage",
      kpiName: "Traceability Coverage",
      baselineValue: "<60% electronic (paper batch records dominant)",
      benchmarkValue: ">95%",
      gapDescription: "Paper batch records cited in warning letter. No real-time lot genealogy. Recall scope unmanageable.",
      financialImpactEstimate:
        "A Class II recall with 60-day paper-based traceability scope = 5x affected units vs electronic. " +
        "Potential $10M+ recall cost differential.",
    },
  ],

  valueHypothesis: {
    hypothesisId: "vh-001",
    valueDriverCategory: "Risk Reduction",
    hypothesisStatement:
      "Implementing an integrated QMS with electronic batch records (EBR) and automated CAPA workflow will reduce " +
      "regulatory risk, cut CAPA cycle time by 60%, and improve traceability coverage from <60% to >95%, " +
      "delivering $3-8M annual value through avoided penalties, reduced COPQ, and faster release cycles.",
    formulaId: "vf-020",
    formulaName: "Compliance Automation Value",
    estimatedAnnualValue: "$5.2M",
    valueRangeLow: "$3.0M",
    valueRangeHigh: "$8.5M",
    confidence: "HIGH",
    confidenceRationale:
      "Warning letter creates mandatory action. QMS modernization is standard remediation. Peer data from similar " +
      "pharma warning letters shows $3-10M remediation spend with 2-3 year payback. Low customer validation risk " +
      "because pain is externally validated by FDA.",
    criticalAssumptions: [
      "Company has budget authority for $1-3M QMS investment within 6 months",
      "Existing MES/ERP can integrate with modern QMS via API",
      "Validation team has capacity for CSV protocol execution",
      "No ongoing consent decree that would freeze vendor selection",
    ],
    validationRequired: true,
  },

  evidenceNeeded: [
    {
      evidenceType: "483 observation details",
      description: "Full Form 483 with all observations and company response",
      source: "FDAzilla or FOIA request",
      priority: "critical",
      estimatedEffort: "2 hours (public database)",
    },
    {
      evidenceType: "Existing QMS vendor and version",
      description: "Current quality system vendor, version, and years in service",
      source: "LinkedIn skills, job postings, or discovery call",
      priority: "critical",
      estimatedEffort: "1 hour research + discovery",
    },
    {
      evidenceType: "Customer concentration and audit requirements",
      description: "Top 3 customers and their supplier audit frequency/standards",
      source: "10-K customer concentration + discovery",
      priority: "important",
      estimatedEffort: "2 hours research",
    },
    {
      evidenceType: "Current CAPA volume and age",
      description: "Number of open CAPAs, average age, and overdue rate",
      source: "Discovery question during first meeting",
      priority: "critical",
      estimatedEffort: "Discovery call",
    },
    {
      evidenceType: "Historical warning letter pattern",
      description: "Has this facility received prior warning letters?",
      source: "FDA warning letter database history",
      priority: "important",
      estimatedEffort: "30 minutes",
    },
  ],

  discoveryQuestions: [
    {
      questionId: "dq-009",
      questionText: "How many regulatory audits do you face annually, and what is the average preparation time and finding remediation cycle?",
      targetPersona: "pers-quality",
      intent: "Validate audit burden and compliance cost baseline",
      expectedInsight: "Audit count, prep hours, finding severity distribution",
      followUpQuestions: [
        "What was your CAPA backlog before the warning letter?",
        "How do you currently track CAPA aging and effectiveness?",
        "What is your current batch record format — paper, hybrid, or electronic?",
      ],
    },
    {
      questionId: "dq-cust-001",
      questionText: "Have any customers suspended shipments or requested additional audits following the warning letter?",
      targetPersona: "pers-coo",
      intent: "Quantify revenue-at-risk from customer reaction",
      expectedInsight: "Customer suspension status, audit requests, contract clauses",
      followUpQuestions: [
        "What is the contract value of customers requiring remediation evidence?",
        "Do customers require specific QMS certifications (e.g., EXCiPACT, IPEC)?",
      ],
    },
    {
      questionId: "dq-budget-001",
      questionText: "Has a remediation budget been allocated, and what is the approval process for capital investments in quality systems?",
      targetPersona: "pers-cfo",
      intent: "Validate budget availability and procurement timeline",
      expectedInsight: "Budget size, approval authority, competing priorities",
      followUpQuestions: [
        "Is there a board-level compliance committee overseeing this?",
        "What is your typical capital approval threshold for IT/system investments?",
      ],
    },
  ],

  recommendedNextActions: [
    "Contact VP Quality within 5 days with specific warning-letter response support offering",
    "Prepare case study from similar pharma warning letter remediation (anonymized)",
    "Offer complimentary 'CAPA maturity assessment' as entry point",
    "Schedule call with CFO to discuss budget timing and compliance ROI model",
    "Prepare FDA response timeline showing how QMS automation accelerates remediation milestones",
    "Map current QMS vendor ecosystem to identify integration complexity",
  ],
};

// ============================================================
// EXAMPLE 2: PE ACQUISITION → OPERATIONAL EXCELLENCE TRANSFORMATION
// ============================================================

const example2: WorkedExample = {
  exampleId: "ex-002",
  title: "PE Acquisition Signal → Discrete Manufacturing Operational Excellence Program",
  description:
    "A mid-market automotive parts manufacturer was acquired by a private equity firm with a documented " +
    "operational improvement thesis. This signals a 12-24 month window for efficiency, OEE, and working capital solutions.",

  rawSignal: {
    id: "raw-002",
    source: "PitchBook + SEC Schedule 13D + Press Release",
    sourceType: "news",
    signalText:
      "On January 10, 2026, Apex Industrial Partners announced the acquisition of Precision Stampings Inc. " +
      "for $420M (8.5x EBITDA). Press release states: 'Apex will work with management to drive operational " +
      "improvement initiatives targeting 400+ basis points of EBITDA expansion through lean manufacturing, " +
      "inventory optimization, and procurement excellence.' Precision Stampings operates 4 plants with " +
      "$280M revenue, serving automotive Tier 1 customers.",
    detectedDate: "2026-01-15",
    companyContext: {
      companyName: "Precision Stampings Inc.",
      segment: "Discrete Manufacturing",
      subSegment: "Automotive/EV",
      annualRevenueM: 280,
      employeeCount: 1200,
    },
  },

  interpretedSignal: {
    signalRuleId: "sig-020",
    signalName: "Private Equity Acquisition",
    interpretedMeaning:
      "PE buyout with explicit operational improvement thesis. 400+ bps EBITDA expansion target implies " +
      "aggressive cost reduction and efficiency programs. Apex Industrial Partners has track record of " +
      "implementing OEE programs, lean transformations, and working capital reduction in portfolio companies. " +
      "Typical investment horizon 3-5 years. First 100 days critical for quick wins.",
    confidenceScore: 0.85,
    confidenceRationale:
      "PE acquisition announcements are public and specific. EBITDA expansion targets are contractual with LPs. " +
      "Apex Industrial Partners has 3 prior automotive portfolio companies with similar thesis — all implemented " +
      "MES/OEE programs within 18 months. Track record is predictive.",
    requiredConfirmationSignals: [
      "Apex portfolio company case studies (public or through network)",
      "Operating partner background and expertise",
      "Current EBITDA margin vs acquisition multiple",
      "100-day plan themes from management meeting",
    ],
    linkedPains: ["pain-001", "pain-003", "pain-006", "pain-012"],
    linkedKPIs: ["kpi-oee", "kpi-inv-turns", "kpi-labor-prod", "kpi-capacity-util"],
  },

  relevantPains: [
    {
      painId: "pain-001",
      painName: "Unplanned Equipment Downtime",
      prevalence: "HIGH",
      relevanceScore: 8,
    },
    {
      painId: "pain-003",
      painName: "Inventory Overstock and Obsolescence",
      prevalence: "HIGH",
      relevanceScore: 9,
    },
    {
      painId: "pain-006",
      painName: "Labor Shortage and Skill Gaps",
      prevalence: "HIGH",
      relevanceScore: 7,
    },
    {
      painId: "pain-012",
      painName: "Capacity Constraint and Bottleneck Management",
      prevalence: "MEDIUM",
      relevanceScore: 8,
    },
    {
      painId: "pain-011",
      painName: "Inefficient Changeover and Setup Times",
      prevalence: "MEDIUM",
      relevanceScore: 7,
    },
  ],

  affectedPersonas: [
    {
      personaId: "pers-coo",
      personaName: "Chief Operating Officer",
      role: "COO / EVP Operations",
      decisionInfluence: "economic",
      relevanceRationale:
        "Direct owner of EBITDA expansion target. Performance tied to PE operating partner evaluation. " +
        "Must deliver quick wins in Year 1.",
      priority: 10,
    },
    {
      personaId: "pers-cfo",
      personaName: "Chief Financial Officer",
      role: "CFO / VP Finance",
      decisionInfluence: "economic",
      relevanceRationale:
        "Owns working capital optimization. Inventory reduction directly frees cash for debt service. " +
        "Budget approver for capital projects.",
      priority: 9,
    },
    {
      personaId: "pers-plant",
      personaName: "Plant Manager / GM",
      role: "Plant Manager / General Manager",
      decisionInfluence: "user",
      relevanceRationale:
        "Four plant managers must execute improvement initiatives. Resistance if solutions imposed without input. " +
        "Need plant-specific data for buy-in.",
      priority: 8,
    },
    {
      personaId: "pers-ops-ex",
      personaName: "Operations Excellence Lead",
      role: "OpEx Director / Lean Six Sigma MBB",
      decisionInfluence: "user",
      relevanceRationale:
        "May already be hired or planned by PE firm. Controls kaizen event calendar. Could be champion or blocker.",
      priority: 7,
    },
    {
      personaId: "pers-cio",
      personaName: "Chief Information Officer",
      role: "CIO / CTO",
      decisionInfluence: "technical",
      relevanceRationale:
        "IT infrastructure for OEE visibility, MES integration, and analytics platforms. May face PE pressure " +
        "to reduce IT spend while enabling operations.",
      priority: 6,
    },
  ],

  kpisImpacted: [
    {
      kpiId: "kpi-oee",
      kpiName: "Overall Equipment Effectiveness",
      baselineValue: "58% (estimated for automotive stampings mid-market)",
      benchmarkValue: "75-85%",
      gapDescription: "17-27 point OEE gap. Typical causes: unplanned downtime 15%, speed losses 10%, quality losses 8%.",
      financialImpactEstimate:
        "$280M revenue × 60% throughput contribution × 15pp OEE gain × 22% margin = $5.5M annual contribution. " +
        "Plus deferred press replacement capital of $8M.",
    },
    {
      kpiId: "kpi-inv-turns",
      kpiName: "Inventory Turns",
      baselineValue: "4.5 turns (estimated)",
      benchmarkValue: "8-10 turns",
      gapDescription: "Slow raw material inventory and large finished goods safety stock for automotive customers.",
      financialImpactEstimate:
        "($280M COGS / 4.5 = $62M inventory) → target 8 turns = $35M inventory. $27M cash release at 12% WACC = $3.2M annually.",
    },
    {
      kpiId: "kpi-labor-prod",
      kpiName: "Labor Productivity",
      baselineValue: "8.5 stampings per labor hour",
      benchmarkValue: "11-13 per hour",
      gapDescription: "Overtime running 28% of hours. High turnover in press operator roles. Limited cross-training.",
      financialImpactEstimate:
        "1,200 employees × $55K avg total comp = $66M labor. 20% productivity gain = $11M effective capacity, " +
        "or 15% OT reduction = $1.2M direct savings.",
    },
    {
      kpiId: "kpi-capacity-util",
      kpiName: "Overall Capacity Utilization",
      baselineValue: "72%",
      benchmarkValue: "85-90%",
      gapDescription: "Bottleneck at heat treat operation. Stamping capacity underutilized due to downstream constraint.",
      financialImpactEstimate:
        "Heat treat bottleneck elevation via scheduling optimization and outsourced overflow = $15M incremental " +
        "revenue capacity at 22% margin = $3.3M.",
    },
  ],

  valueHypothesis: {
    hypothesisId: "vh-002",
    valueDriverCategory: "Cost Savings",
    hypothesisStatement:
      "Deploying an integrated OEE and production visibility platform across 4 plants, combined with APS " +
      "scheduling optimization and inventory right-sizing, will deliver $6-12M annual value through " +
      "OEE improvement (15pp), inventory turn improvement (3.5x), and labor productivity gain (15%), " +
      "while positioning the company for exit at higher EBITDA multiple.",
    formulaId: "vf-002",
    formulaName: "OEE Improvement Value",
    estimatedAnnualValue: "$8.5M",
    valueRangeLow: "$6.0M",
    valueRangeHigh: "$12.0M",
    confidence: "MEDIUM",
    confidenceRationale:
      "PE track record is strong, but execution risk exists across 4 plants. Precision Stampings may have " +
      "union constraints or aging equipment that limits improvement speed. Customer contracts (OEM price-downs) " +
      "may compress realized margin. Need to validate baseline OEE data and plant conditions.",
    criticalAssumptions: [
      "Current OEE baseline is measured and accurate (not estimated)",
      "Plants have IoT/connectivity infrastructure or will accept retrofit",
      "OEM customers will not impose offsetting price reductions",
      "Union agreements allow flexibility in work rules and overtime",
      "Heat treat bottleneck can be elevated without major capital",
    ],
    validationRequired: true,
  },

  evidenceNeeded: [
    {
      evidenceType: "Apex portfolio company precedents",
      description: "Case studies from Apex's 3 prior automotive investments showing OEE and inventory outcomes",
      source: "PE firm public disclosures, portfolio company press releases, industry network",
      priority: "important",
      estimatedEffort: "4 hours research",
    },
    {
      evidenceType: "Plant-by-plant OEE data",
      description: "Current OEE by plant, shift, and product family",
      source: "Discovery call with COO or Plant Managers",
      priority: "critical",
      estimatedEffort: "Discovery call + data request",
    },
    {
      evidenceType: "Inventory composition",
      description: "Raw, WIP, finished goods breakdown by plant and age",
      source: "ERP extract or discovery",
      priority: "critical",
      estimatedEffort: "2 hours discovery",
    },
    {
      evidenceType: "Labor cost and overtime detail",
      description: "Total labor cost, OT rate, turnover by role, and contract terms",
      source: "HR / CFO discovery",
      priority: "important",
      estimatedEffort: "Discovery call",
    },
    {
      evidenceType: "Customer concentration and contracts",
      description: "Top 5 customers, revenue share, and price-down terms",
      source: "10-K or discovery",
      priority: "important",
      estimatedEffort: "1 hour research",
    },
    {
      evidenceType: "Union status and agreements",
      description: "Union representation by plant, contract expiration, work rule flexibility",
      source: "Discovery with HR/Plant Managers",
      priority: "important",
      estimatedEffort: "Discovery call",
    },
  ],

  discoveryQuestions: [
    {
      questionId: "dq-001",
      questionText: "How do you currently measure and report OEE, and what is your plant-by-plant variation?",
      targetPersona: "pers-coo",
      intent: "Validate OEE baseline and measurement maturity",
      expectedInsight: "OEE by plant, method (manual vs automatic), data accuracy",
      followUpQuestions: [
        "What are the top 3 reasons for OEE loss at your lowest-performing plant?",
        "How often do you review OEE at the executive level?",
        "Have you attempted OEE improvement programs before? What happened?",
      ],
    },
    {
      questionId: "dq-003",
      questionText: "Can you quantify your Cost of Poor Quality as a percentage of revenue, and how is it distributed?",
      targetPersona: "pers-cfo",
      intent: "Quantify quality cost and validate improvement potential",
      expectedInsight: "COPQ breakdown, scrap cost, rework cost, warranty reserve trend",
      followUpQuestions: [
        "How much of your inventory is slow-moving or obsolete?",
        "What is your target inventory turn rate post-acquisition?",
      ],
    },
    {
      questionId: "dq-006",
      questionText: "How many of your direct materials are single-sourced, and what is your process for identifying alternatives?",
      targetPersona: "pers-sc",
      intent: "Map supply risk and procurement opportunity",
      expectedInsight: "Single-source exposure, supplier concentration, dual-source progress",
      followUpQuestions: [
        "What is your annual freight and logistics cost?",
        "Have you evaluated nearshoring any categories?",
      ],
    },
  ],

  recommendedNextActions: [
    "Research Apex Industrial Partners portfolio track record and operating partners",
    "Request introductory meeting with COO framing '100-day operational quick wins'",
    "Prepare plant-specific OEE benchmark comparison (anonymized peer data)",
    "Develop 'Working Capital Release Calculator' tool for CFO conversation",
    "Map 4-plant IT infrastructure to identify connectivity gaps for OEE platform",
    "Schedule plant tours at 2 facilities to validate baseline conditions",
  ],
};

// ============================================================
// EXAMPLE 3: ENERGY COST SPIKE → PROCESS MANUFACTURING EFFICIENCY
// ============================================================

const example3: WorkedExample = {
  exampleId: "ex-003",
  title: "Energy Price Spike Signal → Cement Manufacturer Efficiency & Decarbonization Program",
  description:
    "A major US cement producer faces a 45% natural gas price increase in its primary production region, " +
    "combined with pending EU CBAM compliance requirements for exports. This creates dual pressure for " +
    "energy efficiency and carbon reduction investment.",

  rawSignal: {
    id: "raw-003",
    source: "EIA Natural Gas Price Data + Company Earnings Commentary",
    sourceType: "financial_data",
    signalText:
      "Natural gas prices at Henry Hub increased 45% from $3.20/MMBtu (Q3 2025) to $4.65/MMBtu (Q1 2026). " +
      "In Q4 2025 earnings call, Midwest Cement Corp CEO stated: 'Energy costs now exceed 22% of our COGS, " +
      "up from 15% two years ago. We are evaluating all options including alternative fuels, process optimization, " +
      "and kiln efficiency upgrades. Our Scope 1 emissions are 0.85 MT CO2e per ton, and we need a credible " +
      "path to 0.70 by 2028 for both CBAM compliance and customer ESG requirements.' Revenue $1.2B, 8 plants.",
    detectedDate: "2026-02-10",
    companyContext: {
      companyName: "Midwest Cement Corp",
      segment: "Process Manufacturing",
      subSegment: "Cement & Building Materials",
      annualRevenueM: 1200,
      employeeCount: 2400,
    },
  },

  interpretedSignal: {
    signalRuleId: "sig-015",
    signalName: "Energy Price Spike in Key Regions",
    interpretedMeaning:
      "Severe energy cost escalation (45% increase, now 22% of COGS) creating margin crisis for energy-intensive " +
      "process manufacturer. CEO public commitment to 0.70 MT CO2e/ton target by 2028. Dual driver: cost reduction " +
      "AND regulatory/customer compliance. Cement sector has clear technology pathways: alternative fuels (AF)", " +
      "waste heat recovery, process control optimization, and clinker substitution. 8-plant network creates " +
      "both complexity and portfolio effect for pilot-to-scale.",
    confidenceScore: 0.79,
    confidenceRationale:
      "Energy prices are publicly tracked. CEO commentary on earnings call is direct and specific. 22% COGS " +
      "for energy is well above cement industry norm (12-18%), indicating above-average exposure or inefficiency. " +
      "CBAM implementation timeline (2026) is fixed. Customer ESG requirements are increasingly binding. " +
      "Confidence reduced slightly because cement technology transitions are capital-intensive and slow.",
    requiredConfirmationSignals: [
      "Plant-by-plant energy mix and cost breakdown",
      "Alternative fuel current utilization %",
      "EU export volume and CBAM exposure calculation",
      "Customer ESG scorecard requirements (e.g., CDP, Science Based Targets)",
    ],
    linkedPains: ["pain-007", "pain-025", "pain-010"],
    linkedKPIs: ["kpi-energy-intensity", "kpi-carbon-intensity", "kpi-utility-cost", "kpi-scope1-2-emissions"],
  },

  relevantPains: [
    {
      painId: "pain-007",
      painName: "Energy Cost Escalation and Carbon Pressure",
      prevalence: "HIGH",
      relevanceScore: 10,
    },
    {
      painId: "pain-025",
      painName: "Sustainability Reporting and Scope 3 Complexity",
      prevalence: "MEDIUM",
      relevanceScore: 8,
    },
    {
      painId: "pain-010",
      painName: "Poor Production Visibility and Data Silos",
      prevalence: "HIGH",
      relevanceScore: 7,
    },
    {
      painId: "pain-003",
      painName: "Inventory Overstock and Obsolescence",
      prevalence: "MEDIUM",
      relevanceScore: 5,
    },
  ],

  affectedPersonas: [
    {
      personaId: "pers-coo",
      personaName: "Chief Operating Officer",
      role: "COO / EVP Operations",
      decisionInfluence: "economic",
      relevanceRationale:
        "Owns kiln operations and energy procurement. Must balance production continuity with efficiency investments. " +
        "Plant manager relationships critical for AF/co-processing adoption.",
      priority: 10,
    },
    {
      personaId: "pers-cfo",
      personaName: "Chief Financial Officer",
      role: "CFO / VP Finance",
      decisionInfluence: "economic",
      relevanceRationale:
        "Energy now 22% of COGS = $264M annually. Each 10% reduction = $26M. Must evaluate capex vs opex tradeoffs " +
        "for kiln upgrades. CBAM cost exposure needs financial modeling.",
      priority: 9,
    },
    {
      personaId: "pers-sustainability",
      personaName: "Chief Sustainability Officer",
      role: "CSO / VP Sustainability",
      decisionInfluence: "economic",
      relevanceRationale:
        "Owns 0.70 MT CO2e/ton target. Needs credible pathway and interim milestones. Customer ESG scorecards " +
        "require data infrastructure. CDP score at risk if no progress.",
      priority: 8,
    },
    {
      personaId: "pers-plant",
      personaName: "Plant Manager / GM",
      role: "Plant Manager / General Manager",
      decisionInfluence: "user",
      relevanceRationale:
        "8 plant managers must execute alternative fuel trials and process optimization. Union concerns about " +
        "waste-derived fuels. Need training and safety protocols.",
      priority: 7,
    },
    {
      personaId: "pers-cio",
      personaName: "Chief Information Officer",
      role: "CIO / CTO",
      decisionInfluence: "technical",
      relevanceRationale:
        "Energy and emissions data collection currently manual/spreadsheet-based. Real-time metering and " +
        "DCS integration needed for accurate Scope 1 reporting.",
      priority: 6,
    },
  ],

  kpisImpacted: [
    {
      kpiId: "kpi-energy-intensity",
      kpiName: "Energy Intensity",
      baselineValue: "950 kWh/ton (estimated from context)",
      benchmarkValue: "800-900 kWh/ton (IEA best practice)",
      gapDescription: "Above IEA benchmark. Kiln efficiency losses from aging preheater/calciner. Limited waste heat recovery.",
      financialImpactEstimate:
        "8 plants × 1.5M tons = 12M tons. 50 kWh/ton reduction × $0.12/kWh = $72M annual savings potential at full implementation.",
    },
    {
      kpiId: "kpi-carbon-intensity",
      kpiName: "Carbon Intensity",
      baselineValue: "0.85 MT CO2e/ton",
      benchmarkValue: "0.70 MT CO2e/ton (CEO target) / 0.60 (industry leader)",
      gapDescription: "CEO target of 0.70 requires 18% reduction. Clinker factor, alternative fuels, and CCS levers.",
      financialImpactEstimate:
        "CBAM exposure: $50/ton CO2 differential × 0.15 MT/ton × 2M tons EU export = $15M annual CBAM cost by 2026. " +
        "Avoided cost = $15M/year.",
    },
    {
      kpiId: "kpi-utility-cost",
      kpiName: "Utility Cost per Unit",
      baselineValue: "$22/ton (estimated from 22% of COGS)",
      benchmarkValue: "$15-18/ton",
      gapDescription: "Above benchmark due to natural gas exposure and limited alternative fuel use.",
      financialImpactEstimate:
        "$4/ton reduction × 12M tons = $48M annual savings. Plus demand response and peak shaving.",
    },
    {
      kpiId: "kpi-scope1-2-emissions",
      kpiName: "Scope 1 & 2 Emissions",
      baselineValue: "10.2M MT CO2e (12M tons × 0.85)",
      benchmarkValue: "8.4M MT (0.70 target)",
      gapDescription: "1.8M MT reduction needed. Requires multi-lever strategy: AF, clinker substitution, efficiency, electrification.",
      financialImpactEstimate:
        "Carbon credit value at $30/ton × 1.8M MT = $54M potential. Plus avoided CBAM $15M. Total $69M.",
    },
  ],

  valueHypothesis: {
    hypothesisId: "vh-003",
    valueDriverCategory: "Cost Savings",
    hypothesisStatement:
      "Implementing an integrated energy management and process optimization platform across 8 cement plants, " +
      "combined with alternative fuel program enablement and real-time carbon accounting, will reduce energy " +
      "intensity by 8-12%, cut carbon intensity from 0.85 to 0.72 MT/ton, and avoid $15M annual CBAM costs, " +
      "delivering $40-70M annual value through reduced energy spend, carbon credit opportunities, and compliance cost avoidance.",
    formulaId: "vf-022",
    formulaName: "Carbon Reduction Financial Value",
    estimatedAnnualValue: "$52M",
    valueRangeLow: "$40M",
    valueRangeHigh: "$70M",
    confidence: "MEDIUM",
    confidenceRationale:
      "Energy cost crisis is real and CEO-acknowledged. Cement efficiency technology is proven. However, " +
      "alternative fuel adoption faces permitting, community acceptance, and union safety concerns. " +
      "Kiln retrofits are capital-intensive ($10-30M per plant). Payback depends on energy price trajectory " +
      "and CBAM implementation speed. Need plant-specific engineering assessment.",
    criticalAssumptions: [
      "Natural gas prices remain elevated (> $4/MMBtu) for 3+ years",
      "Alternative fuel permits can be secured within 12-18 months",
      "EU CBAM applies to cement imports as scheduled",
      "Customer ESG requirements become binding (not aspirational)",
      "Kiln retrofits can be executed without extended shutdowns",
    ],
    validationRequired: true,
  },

  evidenceNeeded: [
    {
      evidenceType: "Plant-by-plant energy cost and mix",
      description: "Natural gas, coal, electricity, and alternative fuel use by plant and cost per ton",
      source: "Discovery with COO/CFO or sustainability report",
      priority: "critical",
      estimatedEffort: "2 hours discovery",
    },
    {
      evidenceType: "Kiln age and technology profile",
      description: "Kiln type, age, preheater stages, and last major upgrade by plant",
      source: "Engineering records or plant tour",
      priority: "critical",
      estimatedEffort: "Plant tour + engineering interview",
    },
    {
      evidenceType: "EU export volume and customer ESG requirements",
      description: "Tons exported to EU, customer list, and ESG scorecard requirements",
      source: "Sales/CSO discovery",
      priority: "important",
      estimatedEffort: "1 hour discovery",
    },
    {
      evidenceType: "Alternative fuel current status",
      description: "Current AF substitution rate, waste stream contracts, and permitting status",
      source: "COO/Plant discovery",
      priority: "critical",
      estimatedEffort: "Discovery call",
    },
    {
      evidenceType: "Carbon accounting data maturity",
      description: "Scope 1 data collection method, verification status, and baseline year",
      source: "CSO/sustainability team discovery",
      priority: "important",
      estimatedEffort: "1 hour discovery",
    },
    {
      evidenceType: "Capital project approval thresholds",
      description: "Board approval limits, typical project payback requirements, and current capex plan",
      source: "CFO discovery",
      priority: "important",
      estimatedEffort: "Discovery call",
    },
  ],

  discoveryQuestions: [
    {
      questionId: "dq-008",
      questionText: "Do you have a validated baseline for Scope 1, 2, and 3 emissions, and what is your largest source of energy consumption by facility?",
      targetPersona: "pers-sustainability",
      intent: "Validate emissions baseline and energy data maturity",
      expectedInsight: "Scope 1/2/3 coverage, verification status, data collection method",
      followUpQuestions: [
        "What is your current CDP score, and what would improve it?",
        "Which customers have imposed ESG requirements with deadlines?",
        "Have you calculated your CBAM exposure under the 2026 rules?",
      ],
    },
    {
      questionId: "dq-energy-001",
      questionText: "What is your current alternative fuel substitution rate, and what are the barriers to increasing it?",
      targetPersona: "pers-coo",
      intent: "Map AF opportunity and implementation barriers",
      expectedInsight: "AF rate, waste stream availability, permitting status, union/union attitudes",
      followUpQuestions: [
        "Which plant has the highest AF potential and why?",
        "What is your permitting timeline for new waste streams?",
        "How do you manage community and regulator relationships on AF?",
      ],
    },
    {
      questionId: "dq-capex-001",
      questionText: "What is your capital approval threshold for plant-level efficiency projects, and what payback period does your board expect?",
      targetPersona: "pers-cfo",
      intent: "Validate investment decision process and financial criteria",
      expectedInsight: "Approval authority, payback requirements, competing capex demands",
      followUpQuestions: [
        "How do you evaluate energy efficiency vs alternative fuel investments?",
        "Have you modeled the NPV of kiln upgrades under different energy price scenarios?",
      ],
    },
  ],

  recommendedNextActions: [
    "Schedule meeting with CSO presenting 'Cement Decarbonization Pathway' framework with 0.85→0.70 milestones",
    "Prepare plant-specific energy benchmark analysis comparing 8 plants to identify quick-win sites",
    "Develop CBAM cost calculator showing exposure under current vs target carbon intensity",
    "Propose 'Alternative Fuel Readiness Assessment' at 2 highest-potential plants",
    "Map DCS/SCADA infrastructure to identify data collection gaps for real-time energy analytics",
    "Engage CFO with multi-scenario energy price model showing NPV of efficiency investments",
  ],
};

// ============================================================
// EXAMPLE COLLECTION EXPORT
// ============================================================

export const manufacturingSignalExamples: WorkedExample[] = [
  example1,
  example2,
  example3,
];

export type {
  RawSignal,
  InterpretedSignal,
  AffectedPersona,
  KPIImpact,
  ValueHypothesis,
  EvidenceNeeded,
  DiscoveryQuestion,
  WorkedExample,
  Prevalence,
  ConfidenceLevel,
  ValueCategory,
  PersonaInfluence,
};

/**
 * USAGE EXAMPLE:
 * 
 * import { manufacturingSignalExamples } from './signals-examples';
 * 
 * const example = manufacturingSignalExamples[0]; // FDA Warning Letter example
 * console.log(example.interpretedSignal.confidenceScore); // 0.92
 * console.log(example.valueHypothesis.estimatedAnnualValue); // "$5.2M"
 */
