/**
 * Healthcare Master ValuePack — Signal-to-Hypothesis Worked Examples
 * Pack ID: healthcare-master-v1
 * Version: 1.0.0
 * Date: 2026-04-25
 *
 * These 3 worked examples demonstrate the complete signal interpretation pipeline:
 *   Raw Signal -> Interpreted Signal -> Relevant Pains -> Affected Personas ->
 *   KPIs Impacted -> Value Hypothesis -> Confidence -> Evidence Needed ->
 *   Discovery Questions
 */

// =============================================================================
// TYPE DEFINITIONS (mirroring the MasterValuePack schema)
// =============================================================================

type ValueDriverCategory = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";

type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

type PrevalenceLevel = "HIGH" | "MEDIUM" | "LOW";

type UrgencyLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

interface RawSignal {
  id: string;
  sourceType: "earnings_call" | "job_postings" | "regulatory_filing" | "news" | "bond_rating" | "security_incident" | "10k_filing" | "clinical_trial_registry" | "procurement_notice";
  sourceUrl: string;
  dateObserved: string;
  signalDescription: string;
  extractedDataPoints: Record<string, string | number | boolean>;
}

interface InterpretedSignal {
  signalRuleId: string;
  signalName: string;
  interpretedMeaning: string;
  confidenceScore: number; // 0.0 to 1.0
  linkedPains: string[]; // pain IDs
  linkedKPIs: string[]; // KPI IDs
  affectedPersonas: string[]; // persona IDs
  valueDriverCategory: ValueDriverCategory;
  urgencyLevel: UrgencyLevel;
  requiredConfirmationSignals: string[];
}

interface BusinessPainRef {
  painId: string;
  painName: string;
  prevalence: PrevalenceLevel;
  symptomsObserved: string[];
}

interface KPIImpact {
  kpiId: string;
  kpiName: string;
  currentValueEstimate: string;
  benchmarkComparison: string;
  financialImpactEstimate: string;
  confidence: ConfidenceLevel;
}

interface PersonaEngagement {
  personaId: string;
  personaName: string;
  role: string;
  relevanceRationale: string;
  decisionInfluence: "economic" | "technical" | "user";
  engagementPriority: number; // 1-10
}

interface ValueHypothesis {
  hypothesisId: string;
  hypothesisStatement: string;
  valueDriverCategory: ValueDriverCategory;
  formulaId: string;
  formulaName: string;
  estimatedAnnualValue: string;
  valueRangeLow: string;
  valueRangeHigh: string;
  confidence: ConfidenceLevel;
  confidenceRationale: string;
  requiredEvidenceForValidation: string[];
  validationTimeline: string;
}

interface EvidenceNeeded {
  evidenceType: string;
  source: string;
  howToObtain: string;
  estimatedEffort: string;
  blockingRisk: boolean;
}

interface DiscoveryQuestion {
  questionId: string;
  question: string;
  targetPersona: string;
  insightSought: string;
  recommendedCallStage: "early" | "middle" | "late" | "any";
  linkedPainId: string;
  linkedKpiId: string;
}

interface SignalToHypothesisExample {
  exampleId: string;
  exampleName: string;
  scenarioDescription: string;
  segmentFocus: string;
  rawSignal: RawSignal;
  interpretedSignal: InterpretedSignal;
  relevantPains: BusinessPainRef[];
  affectedPersonas: PersonaEngagement[];
  kpisImpacted: KPIImpact[];
  valueHypothesis: ValueHypothesis;
  evidenceNeeded: EvidenceNeeded[];
  discoveryQuestions: DiscoveryQuestion[];
}

// =============================================================================
// EXAMPLE 1: Hospital System — Revenue Cycle Denial Crisis Signal
// =============================================================================

const example1: SignalToHypothesisExample = {
  exampleId: "EX-001",
  exampleName: "Revenue Cycle Denial Crisis from Job Posting Surge + Earnings Call",
  scenarioDescription:
    "A 12-hospital regional health system ($2.8B revenue) shows a sudden 340% increase in RCM-related job postings over 90 days. Their CFO mentions 'revenue cycle challenges and payer complexity' on the Q3 earnings call. A/R days have trended from 38 to 54 over 8 months per HFMA benchmark submissions.",
  segmentFocus: "Care Delivery (Providers)",

  rawSignal: {
    id: "RS-001",
    sourceType: "job_postings",
    sourceUrl: "https://example-health-system.com/careers",
    dateObserved: "2026-04-15",
    signalDescription:
      "14 open positions for denials specialists, patient access supervisors, Epic billing analysts, and RCM technology managers posted within 90 days. Prior 90-day baseline: 3 similar postings.",
    extractedDataPoints: {
      postingsCount: 14,
      baselinePostings: 3,
      postingSurgePct: 367,
      timeWindowDays: 90,
      roles: "denials specialist, patient access supervisor, Epic billing analyst, RCM technology manager",
      locations: "system-wide across 12 hospitals",
    },
  },

  interpretedSignal: {
    signalRuleId: "S001",
    signalName: "Job Posting Surge – Revenue Cycle Technology",
    interpretedMeaning:
      "Organization experiencing revenue cycle stress and investing in human capital to address denials, patient access, or technology modernization. Indicates pain magnitude justifying FTE expansion.",
    confidenceScore: 0.82,
    linkedPains: ["P001", "P006", "P009"],
    linkedKPIs: ["K001", "K002", "K003", "K004", "K005"],
    affectedPersonas: ["PER001", "PER007", "PER003"],
    valueDriverCategory: "Revenue Uplift",
    urgencyLevel: "HIGH",
    requiredConfirmationSignals: [
      "A/R days trending upward from 38 to 54 (confirmed via HFMA submission)",
      "Denial rate above benchmark of 8.5% (to be confirmed)",
      "Recent EHR or RCM implementation or upgrade (to be confirmed)",
    ],
  },

  relevantPains: [
    {
      painId: "P001",
      painName: "Revenue Cycle Denial Rate Escalation",
      prevalence: "HIGH",
      symptomsObserved: [
        "Job posting surge for denials and RCM roles (340% increase)",
        "CFO mentioning revenue cycle challenges on earnings call",
        "A/R days trending upward from 38 to 54 over 8 months",
        "System-wide postings suggest enterprise-level problem, not isolated facility",
      ],
    },
    {
      painId: "P006",
      painName: "Prior Authorization Burden and Delayed Care",
      prevalence: "HIGH",
      symptomsObserved: [
        "Patient access supervisor roles suggest front-end registration and authorization gaps",
        "Prior authorization frequently contributes to downstream denials",
      ],
    },
    {
      painId: "P009",
      painName: "Medical Necessity Denials and Clinical Documentation Gaps",
      prevalence: "HIGH",
      symptomsObserved: [
        "Denials specialists often handle clinical validation and medical necessity appeals",
        "Epic billing analyst roles suggest mid-cycle coding/charge capture issues",
      ],
    },
  ],

  affectedPersonas: [
    {
      personaId: "PER001",
      personaName: "Chief Financial Officer (CFO)",
      role: "Finance and capital allocation leader with P&L accountability",
      relevanceRationale:
        "CFO directly accountable for A/R days, denial rate, and cash flow. Earnings call comment signals personal engagement. Board likely pressing for improvement. Owns ROI threshold for any RCM investment.",
      decisionInfluence: "economic",
      engagementPriority: 10,
    },
    {
      personaId: "PER007",
      personaName: "VP Revenue Cycle Management",
      role: "Revenue cycle operations leader",
      relevanceRationale:
        "VP RCM owns the operational execution of denials management. Job postings likely originated from their budget. They understand root cause codes, payer-specific patterns, and rework costs. Technical buyer for solution.",
      decisionInfluence: "economic",
      engagementPriority: 9,
    },
    {
      personaId: "PER003",
      personaName: "Chief Medical Officer (CMO)",
      role: "Senior physician leader accountable for clinical quality",
      relevanceRationale:
        "CMO must engage physicians on clinical documentation improvement and query response. If P009 (documentation gaps) is contributing, CMO is key to change management. Often overlooked in RCM sales but critical for sustainable improvement.",
      decisionInfluence: "technical",
      engagementPriority: 7,
    },
    {
      personaId: "PER004",
      personaName: "Chief Nursing Officer (CNO)",
      role: "Executive nursing leader",
      relevanceRationale:
        "CNO influences front-line documentation quality at point of care. Nursing documentation frequently supports medical necessity and level-of-care justification. Engagement needed for CDI query response improvement.",
      decisionInfluence: "technical",
      engagementPriority: 6,
    },
  ],

  kpisImpacted: [
    {
      kpiId: "K001",
      kpiName: "Net Days in Accounts Receivable",
      currentValueEstimate: "54 days (trended from 38 over 8 months)",
      benchmarkComparison: "54 vs. benchmark 42 days (HFMA); 28% above top quartile (30 days)",
      financialImpactEstimate:
        "Each day of A/R reduction = ~$769K in accelerated cash for $2.8B system. Reducing from 54 to 42 days = $9.2M working capital improvement.",
      confidence: "HIGH",
    },
    {
      kpiId: "K002",
      kpiName: "Initial Denial Rate",
      currentValueEstimate: "Estimated 11-13% based on posting patterns and A/R trend",
      benchmarkComparison: "11-13% vs. benchmark 8.5% (Crowe); 35-53% above benchmark",
      financialImpactEstimate:
        "At 12% denial rate on $2.8B gross charges with 60% contractual adjustment and 85% collectible yield: reducing to 6% = $11.4M annual recovery.",
      confidence: "MEDIUM",
    },
    {
      kpiId: "K003",
      kpiName: "Final Denial Write-off Rate",
      currentValueEstimate: "Estimated 2.5-3.5% based on typical correlation with initial denial rate",
      benchmarkComparison: "2.5-3.5% vs. benchmark <1.5% (top quartile)",
      financialImpactEstimate:
        "Each 1% write-off reduction on $2.8B = $11.2M at gross; net ~$4.5M after contractual adjustment. Target 2% reduction = ~$9M annual value.",
      confidence: "MEDIUM",
    },
    {
      kpiId: "K004",
      kpiName: "Cost to Collect",
      currentValueEstimate: "Estimated 4.2-4.8% (typical when A/R > 50 and denials elevated)",
      benchmarkComparison: "4.2-4.8% vs. benchmark 3.2% (HFMA); 31-50% above benchmark",
      financialImpactEstimate:
        "Reducing cost to collect from 4.5% to 3.2% on $2.8B net revenue = $36.4M annual savings.",
      confidence: "MEDIUM",
    },
  ],

  valueHypothesis: {
    hypothesisId: "VH-001",
    hypothesisStatement:
      "By implementing intelligent denials prevention (front-end eligibility, mid-cycle CDI, and back-end appeals automation), the health system can reduce initial denial rate from ~12% to 6%, reduce A/R days from 54 to 38, and reduce cost-to-collect from 4.5% to 3.2%, generating $15-25M in annual value through revenue recovery and cost avoidance.",
    valueDriverCategory: "Revenue Uplift",
    formulaId: "F001",
    formulaName: "Denial Reduction Value",
    estimatedAnnualValue: "$18.5M (midpoint of range)",
    valueRangeLow: "$12M",
    valueRangeHigh: "$28M",
    confidence: "MEDIUM",
    confidenceRationale:
      "HIGH confidence on A/R and cost-to-collect estimates (directly observable). MEDIUM on denial rate and recovery yield because we lack actual payer mix and reason code breakdown. Value range reflects uncertainty in collectible yield percentage.",
    requiredEvidenceForValidation: [
      "Actual 12-month denial rate and reason code breakdown by payer",
      "Current A/R aging report with payer-specific detail",
      "Cost-to-collect breakdown by function (patient access, coding, billing, collections)",
      "Physician query response rate and CDI program metrics",
      "Payer contract terms and reimbursement rate schedule",
    ],
    validationTimeline: "90-day assessment phase with baseline measurement; 6-month pilot for denial reduction; 12-month full deployment",
  },

  evidenceNeeded: [
    {
      evidenceType: "Denial reason code analysis",
      source: "Internal RCM system (Epic Resolute, Waystar, or clearinghouse)",
      howToObtain: "Request through VP Revenue Cycle or request in discovery call with data export",
      estimatedEffort: "2-4 hours if system access available; 1-2 weeks if requiring IT extraction",
      blockingRisk: false,
    },
    {
      evidenceType: "A/R aging report by payer and service line",
      source: "Internal financial system or RCM platform",
      howToObtain: "Standard monthly report available to CFO or VP Revenue Cycle",
      estimatedEffort: "30 minutes if standard report; 2 hours if custom",
      blockingRisk: false,
    },
    {
      evidenceType: "Payer mix and reimbursement rate schedule",
      source: "Managed care contracts or payer relations department",
      howToObtain: "Requires CFO or payer relations VP approval; may be restricted due to confidentiality",
      estimatedEffort: "1-2 weeks with legal/contract review",
      blockingRisk: true,
    },
    {
      evidenceType: "Cost-to-collect breakdown",
      source: "Finance department cost accounting",
      howToObtain: "Request through CFO or FP&A director; may require time-motion study supplement",
      estimatedEffort: "1-2 weeks",
      blockingRisk: false,
    },
    {
      evidenceType: "CDI query rate and physician response rate",
      source: "HIM/CDI department monthly report",
      howToObtain: "Request through HIM Director or CDI manager; typically available as standard KPI",
      estimatedEffort: "1-2 hours",
      blockingRisk: false,
    },
  ],

  discoveryQuestions: [
    {
      questionId: "DQ001-EX1",
      question: "What is your current initial denial rate, and which three denial reason codes represent the largest volume?",
      targetPersona: "VP Revenue Cycle",
      insightSought: "Quantify denial problem magnitude and identify root cause categories",
      recommendedCallStage: "early",
      linkedPainId: "P001",
      linkedKpiId: "K002",
    },
    {
      questionId: "DQ002-EX1",
      question: "How has your A/R days trended over the last 12 months, and what's driving the change?",
      targetPersona: "CFO",
      insightSought: "Validate A/R trend and identify whether driven by denials, payer delays, or registration issues",
      recommendedCallStage: "early",
      linkedPainId: "P001",
      linkedKpiId: "K001",
    },
    {
      questionId: "DQ004-EX1",
      question: "What's your current cost-to-collect, and how does that compare to the HFMA top-quartile benchmark of 3%?",
      targetPersona: "CFO",
      insightSought: "Quantify collection efficiency gap and validate cost structure assumptions",
      recommendedCallStage: "early",
      linkedPainId: "P001",
      linkedKpiId: "K004",
    },
    {
      questionId: "DQ007-EX1",
      question: "What percentage of your denials are overturned on first appeal vs. requiring second/third appeal or write-off?",
      targetPersona: "VP Revenue Cycle",
      insightSought: "Understand appeal success rate and identify lowest-yield denial categories",
      recommendedCallStage: "middle",
      linkedPainId: "P001",
      linkedKpiId: "K003",
    },
    {
      questionId: "DQ008-EX1",
      question: "How does your physician query response rate compare to the ACDIS benchmark of 70%+? What barriers do physicians cite?",
      targetPersona: "CMO",
      insightSought: "Assess clinical documentation improvement opportunity and physician engagement barriers",
      recommendedCallStage: "middle",
      linkedPainId: "P009",
      linkedKpiId: "K031",
    },
  ],
};

// =============================================================================
// EXAMPLE 2: Medicare Advantage Plan — Star Rating Decline Signal
// =============================================================================

const example2: SignalToHypothesisExample = {
  exampleId: "EX-002",
  exampleName: "MA Star Rating Decline Below 4.0 from CMS Annual Release",
  scenarioDescription:
    "A regional Medicare Advantage plan with 180,000 members learns in October that its Star rating dropped from 4.0 to 3.5 stars. The plan's triple-weighted medication adherence measures (PDC for diabetes, hypertension, cholesterol) all declined. CAHPS member experience scores fell below the 50th percentile. The plan faces loss of quality bonus payment (~$85 PMPM) and potential marketing restriction.",
  segmentFocus: "Payers and Health Insurance",

  rawSignal: {
    id: "RS-002",
    sourceType: "regulatory_filing",
    sourceUrl: "https://www.cms.gov/medicare/prescription-drug-coverage/prescriptiondrugcovgenin/performance-data",
    dateObserved: "2026-10-08",
    signalDescription:
      "CMS 2026 Star Ratings published. Plan ID H1234 drops from 4.0 to 3.5 stars. Triple-weighted medication adherence measures declined 4-6 percentage points. CAHPS scores at 46th percentile.",
    extractedDataPoints: {
      currentStarRating: 3.5,
      priorStarRating: 4.0,
      memberCount: 180000,
      pdcDiabetesDeclinePct: -4.2,
      pdcHypertensionDeclinePct: -5.1,
      pdcCholesterolDeclinePct: -3.8,
      cahpsPercentile: 46,
      estimatedBonusPMPM: 85,
    },
  },

  interpretedSignal: {
    signalRuleId: "S005",
    signalName: "CMS Star Rating Decline Announcement",
    interpretedMeaning:
      "MA plan quality and member experience underperformance threatening bonus revenue, member retention, and marketing privileges. Immediate action required before next measurement cycle.",
    confidenceScore: 0.91,
    linkedPains: ["P011", "P022", "P012"],
    linkedKPIs: ["K036", "K037", "K038", "K039", "K040", "K071", "K073"],
    affectedPersonas: ["PER011", "PER009", "PER001"],
    valueDriverCategory: "Revenue Uplift",
    urgencyLevel: "HIGH",
    requiredConfirmationSignals: [
      "HEDIS measure gap analysis confirmed (medication adherence, care gaps, screenings)",
      "CAHPS score breakdown confirmed (access, doctor communication, care coordination)",
      "Member attrition rate increasing confirmed",
    ],
  },

  relevantPains: [
    {
      painId: "P011",
      painName: "Medicare Advantage Star Rating Erosion",
      prevalence: "HIGH",
      symptomsObserved: [
        "Star rating declined from 4.0 to 3.5 (below 4.0 bonus threshold)",
        "Triple-weighted medication adherence measures declined 4-6 percentage points",
        "CAHPS scores below 50th percentile",
        "Marketing restriction risk for upcoming Annual Election Period",
      ],
    },
    {
      painId: "P022",
      painName: "Care Gap Closure and Preventive Care Underperformance",
      prevalence: "HIGH",
      symptomsObserved: [
        "Medication adherence decline directly linked to care gap closure failure",
        "HEDIS measure gaps likely present across preventive and chronic measures",
        "Member outreach response likely below benchmark",
      ],
    },
    {
      painId: "P012",
      painName: "Medical Loss Ratio (MLR) Pressure and Administrative Cost Squeeze",
      prevalence: "HIGH",
      symptomsObserved: [
        "Loss of quality bonus payment reduces revenue without corresponding cost reduction",
        "May need to increase administrative investment in quality programs while revenue declines",
        "Competitive premium pressure makes rate increases difficult",
      ],
    },
  ],

  affectedPersonas: [
    {
      personaId: "PER011",
      personaName: "Chief Strategy Officer (CSO)",
      role: "Strategic leader responsible for MA growth and market positioning",
      relevanceRationale:
        "CSO owns Star rating strategy, member acquisition/retention, and competitive positioning. Marketing restriction directly impacts AEP performance. Must drive cross-functional response involving quality, pharmacy, and member experience.",
      decisionInfluence: "economic",
      engagementPriority: 10,
    },
    {
      personaId: "PER009",
      personaName: "Population Health / Value-Based Care VP",
      role: "Leader of population health strategy and care management",
      relevanceRationale:
        "Population Health VP directly accountable for HEDIS measure performance, care gap closure, and medication adherence programs. Owns care management staffing, outreach strategy, and quality reporting infrastructure.",
      decisionInfluence: "economic",
      engagementPriority: 9,
    },
    {
      personaId: "PER001",
      personaName: "Chief Financial Officer (CFO)",
      role: "Finance leader with P&L accountability for MA plan",
      relevanceRationale:
        "CFO must quantify bonus payment loss ($85 PMPM × 180K members × 12 months = ~$183M annually). Also needs to approve quality program investment budget. Financial impact drives urgency.",
      decisionInfluence: "economic",
      engagementPriority: 9,
    },
    {
      personaId: "PER012",
      personaName: "Chief Pharmacy Officer / 340B Program Director",
      role: "Pharmacy and medication management leader",
      relevanceRationale:
        "Triple-weighted medication adherence measures are pharmacy-centric. Pharmacy leadership influences formulary design, MTM programs, adherence packaging, and pharmacy network incentives.",
      decisionInfluence: "technical",
      engagementPriority: 8,
    },
  ],

  kpisImpacted: [
    {
      kpiId: "K036",
      kpiName: "Medicare Advantage Star Rating",
      currentValueEstimate: "3.5 stars (declined from 4.0)",
      benchmarkComparison: "3.5 vs. national average 4.04; below 4.0 bonus threshold",
      financialImpactEstimate:
        "Each 0.5 star = ~$85 PMPM × 180,000 members × 12 months = $183.6M annual bonus payment at risk. Additionally, rebate enhancement loss of ~$30-50M.",
      confidence: "HIGH",
    },
    {
      kpiId: "K038",
      kpiName: "Medication Adherence (PDC) – Triple-Weighted Conditions",
      currentValueEstimate: "Diabetes ~74%, Hypertension ~73%, Cholesterol ~76% (declined 4-6 pts)",
      benchmarkComparison: "74-76% vs. 80% Stars threshold; vs. national average ~78%",
      financialImpactEstimate:
        "Improving all three measures by 6 percentage points to reach 80%+ threshold contributes significantly to Star rating improvement. Each measure carries triple weight in rating calculation.",
      confidence: "HIGH",
    },
    {
      kpiId: "K037",
      kpiName: "HEDIS Compliance Rate",
      currentValueEstimate: "Estimated 72% (inferred from Star decline and adherence gaps)",
      benchmarkComparison: "72% vs. target 85% for NCQA accreditation; vs. national average 78%",
      financialImpactEstimate:
        "HEDIS improvement to 85%+ required for competitive positioning and employer group retention. Each percentage point improvement affects multiple Star measures.",
      confidence: "MEDIUM",
    },
    {
      kpiId: "K039",
      kpiName: "CAHPS Patient Experience Score",
      currentValueEstimate: "46th percentile (below median)",
      benchmarkComparison: "46th percentile vs. 75th percentile target for Stars competitiveness",
      financialImpactEstimate:
        "CAHPS improvement to 75th percentile contributes ~0.3-0.5 Star points. Member experience drives both Star rating and retention.",
      confidence: "HIGH",
    },
  ],

  valueHypothesis: {
    hypothesisId: "VH-002",
    hypothesisStatement:
      "By deploying integrated care gap closure, medication adherence outreach, and member experience improvement programs, the MA plan can recover 0.5-1.0 Star points within 18-24 months, restoring quality bonus payments of $150-220M annually and avoiding marketing restrictions that would impair AEP member acquisition.",
    valueDriverCategory: "Revenue Uplift",
    formulaId: "F012",
    formulaName: "Medicare Advantage Stars Bonus Value",
    estimatedAnnualValue: "$195M (midpoint of range)",
    valueRangeLow: "$150M",
    valueRangeHigh: "$220M",
    confidence: "HIGH",
    confidenceRationale:
      "HIGH confidence because: (1) CMS Star methodology is public and deterministic, (2) bonus PMPM values are published in rate announcements, (3) member count is known, (4) measure weights are fixed. Range reflects uncertainty in exact rating trajectory and timing of improvement.",
    requiredEvidenceForValidation: [
      "CMS 2026 Star Ratings measure-by-measure scorecard",
      "HEDIS 2025 rate book with measure-specific performance",
      "Current care gap closure rate by measure and channel performance",
      "Medication adherence program current state (MTM, outreach, pharmacy network incentives)",
      "CAHPS dimension-level scores and trending",
      "Member attrition rate and AEP forecast",
      "Current quality program budget and staffing",
    ],
    validationTimeline: "30-day baseline assessment; 6-month pilot on top 3 measures; 18-month full Stars improvement cycle",
  },

  evidenceNeeded: [
    {
      evidenceType: "CMS Star Ratings measure-level scorecard",
      source: "CMS published data (public)",
      howToObtain: "Download from CMS.gov or request from plan's quality department",
      estimatedEffort: "1 hour (public data)",
      blockingRisk: false,
    },
    {
      evidenceType: "HEDIS rate book with current measure rates",
      source: "NCQA HEDIS reporting (plan-internal)",
      howToObtain: "Request from VP Quality or Population Health; may require NDA",
      estimatedEffort: "1-2 days",
      blockingRisk: false,
    },
    {
      evidenceType: "Current care gap closure rates by measure",
      source: "Population health analytics platform",
      howToObtain: "Request from Population Health VP; standard operational report",
      estimatedEffort: "2-4 hours",
      blockingRisk: false,
    },
    {
      evidenceType: "Medication adherence program details",
      source: "Pharmacy/clinical programs department",
      howToObtain: "Request from Chief Pharmacy Officer or pharmacy operations director",
      estimatedEffort: "1-2 days",
      blockingRisk: false,
    },
    {
      evidenceType: "Member attrition rate and AEP forecast",
      source: "Sales/marketing and membership analytics",
      howToObtain: "Request from Chief Strategy Officer or membership VP; may be sensitive",
      estimatedEffort: "1-2 days",
      blockingRisk: true,
    },
  ],

  discoveryQuestions: [
    {
      questionId: "DQ001-EX2",
      question: "Which specific Star measures declined the most, and what's the root cause analysis for each?",
      targetPersona: "Chief Strategy Officer",
      insightSought: "Identify highest-impact improvement opportunities and whether declines are data, process, or engagement-driven",
      recommendedCallStage: "early",
      linkedPainId: "P011",
      linkedKpiId: "K036",
    },
    {
      questionId: "DQ002-EX2",
      question: "What's your current medication adherence PDC for the triple-weighted conditions, and what adherence interventions are currently in place?",
      targetPersona: "Population Health VP",
      insightSought: "Baseline adherence performance and intervention maturity assessment",
      recommendedCallStage: "early",
      linkedPainId: "P011",
      linkedKpiId: "K038",
    },
    {
      questionId: "DQ003-EX2",
      question: "How much quality bonus payment and rebate enhancement are at risk with the 3.5-star rating, and what's the board's expectation for recovery?",
      targetPersona: "CFO",
      insightSought: "Quantify financial stakes and board urgency to validate investment appetite",
      recommendedCallStage: "early",
      linkedPainId: "P011",
      linkedKpiId: "K036",
    },
    {
      questionId: "DQ004-EX2",
      question: "What's your current member outreach response rate by channel (phone, text, mail, portal), and which channels perform best for different age segments?",
      targetPersona: "Population Health VP",
      insightSought: "Assess engagement strategy effectiveness and identify channel optimization opportunities",
      recommendedCallStage: "middle",
      linkedPainId: "P022",
      linkedKpiId: "K073",
    },
    {
      questionId: "DQ005-EX2",
      question: "Which CAHPS dimensions are weakest, and what member journey mapping have you done to understand friction points?",
      targetPersona: "Chief Strategy Officer",
      insightSought: "Identify patient experience improvement priorities and existing research",
      recommendedCallStage: "middle",
      linkedPainId: "P011",
      linkedKpiId: "K039",
    },
  ],
};

// =============================================================================
// EXAMPLE 3: Life Sciences — Clinical Trial Enrollment Crisis Signal
// =============================================================================

const example3: SignalToHypothesisExample = {
  exampleId: "EX-003",
  exampleName: "Biotech Phase 2 Enrollment Crisis from ClinicalTrials.gov Status Update",
  scenarioDescription:
    "A mid-cap biotech ($800M market cap) with a phase 2b pivotal trial for a novel autoimmune therapy posts a status update to ClinicalTrials.gov indicating enrollment is at 42% of target with 4 months remaining in the planned enrollment window. Screen failure rate is 48%. Two top-enrolling sites have paused recruitment due to PI departure. The company has $280M cash runway and this asset represents ~60% of pipeline NPV.",
  segmentFocus: "Life Sciences",

  rawSignal: {
    id: "RS-003",
    sourceType: "clinical_trial_registry",
    sourceUrl: "https://clinicaltrials.gov/ct2/show/NCT12345678",
    dateObserved: "2026-04-10",
    signalDescription:
      "Phase 2b trial NCT12345678 status update shows enrollment at 42% with 4 months remaining in planned 18-month window. Screen failure rate 48% (vs. industry average 42%). Two sites paused. Estimated enrollment completion delay: 8-12 months.",
    extractedDataPoints: {
      trialPhase: "Phase 2b",
      enrollmentPctComplete: 42,
      monthsRemainingInWindow: 4,
      screenFailureRatePct: 48,
      sitesPaused: 2,
      estimatedDelayMonths: 10,
      companyMarketCapMillion: 800,
      cashRunwayMillion: 280,
      assetPctOfPipelineNPV: 60,
    },
  },

  interpretedSignal: {
    signalRuleId: "S010",
    signalName: "Clinical Trial Pause or Protocol Amendment",
    interpretedMeaning:
      "Trial execution or safety issue threatening development timeline. Signals patient recruitment, data quality, site management, or safety surveillance gaps requiring technology or operational intervention.",
    confidenceScore: 0.87,
    linkedPains: ["P013", "P014"],
    linkedKPIs: ["K043", "K044", "K045", "K046"],
    affectedPersonas: ["PER010", "PER001"],
    valueDriverCategory: "Revenue Uplift",
    urgencyLevel: "HIGH",
    requiredConfirmationSignals: [
      "Enrollment rate vs. target confirmed at 42% (from ClinicalTrials.gov)",
      "Screen failure rate 48% confirmed (to be validated with sponsor)",
      "Site activation timeline and PI departure root cause (to be confirmed)",
    ],
  },

  relevantPains: [
    {
      painId: "P013",
      painName: "Clinical Trial Recruitment and Retention Failure",
      prevalence: "HIGH",
      symptomsObserved: [
        "Enrollment at 42% with only 4 months remaining in planned window",
        "Screen failure rate 48% (above 42% industry average)",
        "Two top-enrolling sites paused due to PI departure",
        "Estimated 8-12 month enrollment delay threatening milestone timeline",
      ],
    },
    {
      painId: "P014",
      painName: "Drug Development Cost Escalation and Timeline Overruns",
      prevalence: "HIGH",
      symptomsObserved: [
        "Enrollment delay of 8-12 months extends overall development timeline",
        "Asset represents 60% of pipeline NPV—delay severely impacts enterprise value",
        "$280M cash runway; extended timeline increases burn rate and may require financing",
        "Competitive assets in same mechanism class may reach market first",
      ],
    },
  ],

  affectedPersonas: [
    {
      personaId: "PER010",
      personaName: "Head of Clinical Development / CMO (Life Sciences)",
      role: "Clinical trial portfolio and regulatory strategy leader",
      relevanceRationale:
        "Head of Clinical Development owns trial execution, CRO management, and enrollment strategy. Must decide whether to amend protocol, add sites, change inclusion criteria, or deploy new recruitment technology. Direct accountability for timeline.",
      decisionInfluence: "technical",
      engagementPriority: 10,
    },
    {
      personaId: "PER001",
      personaName: "Chief Financial Officer (CFO)",
      role: "Finance leader with capital allocation and investor relations accountability",
      relevanceRationale:
        "CFO must model cash runway extension, potential dilutive financing, and NPV impact. 60% pipeline NPV concentration creates investor relations risk. May need to allocate emergency budget for rescue strategies.",
      decisionInfluence: "economic",
      engagementPriority: 9,
    },
    {
      personaId: "PER011",
      personaName: "Chief Strategy Officer (CSO)",
      role: "Strategic leader responsible for portfolio and business development",
      relevanceRationale:
        "CSO must assess whether to double down on this asset, seek partnership to share risk, or deprioritize. Asset concentration risk (60% of NPV) may trigger BD discussions for co-development or licensing.",
      decisionInfluence: "economic",
      engagementPriority: 8,
    },
    {
      personaId: "PER003",
      personaName: "Chief Medical Officer (CMO) — Life Sciences",
      role: "Medical and scientific leader",
      relevanceRationale:
        "CMO may need to reconsider inclusion/exclusion criteria, biomarker stratification, or dosing regimen if screen failures are driven by safety or efficacy signals. Medical judgment central to protocol amendment decisions.",
      decisionInfluence: "technical",
      engagementPriority: 7,
    },
  ],

  kpisImpacted: [
    {
      kpiId: "K043",
      kpiName: "Clinical Trial Enrollment Rate",
      currentValueEstimate: "42% at midpoint (should be ~75-80% at midpoint for on-time completion)",
      benchmarkComparison: "42% vs. 78% industry average at midpoint (Tufts CSDD); 46% below benchmark",
      financialImpactEstimate:
        "10-month enrollment delay × $600K-$8M/day opportunity cost = $180M-$2.4B NPV impact (range reflects market size and competitive dynamics). For $800M market cap company with 60% NPV concentration: ~$200-400M enterprise value at risk.",
      confidence: "MEDIUM",
    },
    {
      kpiId: "K044",
      kpiName: "Screen Failure Rate",
      currentValueEstimate: "48% (vs. 42% industry average)",
      benchmarkComparison: "48% vs. 42% average; 14% above benchmark",
      financialImpactEstimate:
        "Each 1% screen failure reduction on 1,000-patient trial = 10 additional enrolled patients. At $50K per screened patient, 6% improvement = $300K cost avoidance + faster enrollment.",
      confidence: "HIGH",
    },
    {
      kpiId: "K045",
      kpiName: "Study Activation Time",
      currentValueEstimate: "Estimated 8-10 months for new site activation (industry average)",
      benchmarkComparison: "8-10 months vs. 4-6 month best practice",
      financialImpactEstimate:
        "Each month of site activation acceleration = 1 month earlier database lock and NDA submission. At $600K/day for peak asset = $18M per month.",
      confidence: "MEDIUM",
    },
    {
      kpiId: "K046",
      kpiName: "Clinical Trial Dropout Rate",
      currentValueEstimate: "Not directly observed; estimated 18-22% based on autoimmune therapeutic area norms",
      benchmarkComparison: "18-22% vs. 18% best practice; may increase with extended timeline",
      financialImpactEstimate:
        "Dropout rate increase from 18% to 25% on 500-patient trial = 35 additional patients needed = $1.75M additional cost + timeline extension.",
      confidence: "LOW",
    },
  ],

  valueHypothesis: {
    hypothesisId: "VH-003",
    hypothesisStatement:
      "By deploying AI-driven patient identification, decentralized trial capabilities, and site activation acceleration, the biotech can reduce enrollment timeline by 6-8 months, reduce screen failure rate from 48% to 35%, and avoid $150-300M in NPV erosion and financing dilution. Additional value from earlier NDA submission and extended market exclusivity.",
    valueDriverCategory: "Revenue Uplift",
    formulaId: "F014",
    formulaName: "Clinical Trial Acceleration Value",
    estimatedAnnualValue: "$220M (NPV impact over development horizon)",
    valueRangeLow: "$100M",
    valueRangeHigh: "$400M",
    confidence: "MEDIUM",
    confidenceRationale:
      "MEDIUM confidence because: (1) trial delay magnitude is observable but exact recovery timeline is uncertain, (2) NPV impact depends on market size assumptions and competitive dynamics, (3) screen failure reduction achievable but depends on protocol amendment feasibility, (4) financing dilution avoidance is contingent on capital market conditions. HIGH confidence on direct trial cost avoidance.",
    requiredEvidenceForValidation: [
      "Current enrollment funnel metrics by site, country, and month",
      "Screen failure reason categorization (eligibility, biomarker, safety, withdrawal)",
      "Site performance dashboard and site activation timeline",
      "CRO contract terms and performance SLAs",
      "Protocol amendment history and regulatory feedback",
      "Patient journey mapping and site burden assessment",
      "Competitive landscape timeline for same indication/mechanism",
      "Investor presentation and analyst coverage assumptions",
    ],
    validationTimeline: "2-week rapid assessment of enrollment data; 4-week pilot at 2-3 sites; 6-month expansion if pilot shows 30%+ enrollment acceleration",
  },

  evidenceNeeded: [
    {
      evidenceType: "Enrollment funnel metrics by site and month",
      source: "CTMS (Veeva, Medidata, or Oracle Clinical One)",
      howToObtain: "Request from Head of Clinical Development; typically shared under CDA for vendor evaluation",
      estimatedEffort: "1-2 days if CTMS access available",
      blockingRisk: false,
    },
    {
      evidenceType: "Screen failure reason categorization",
      source: "EDC system and site logs",
      howToObtain: "Requires sponsor data analytics team extraction; may require protocol team review",
      estimatedEffort: "3-5 days",
      blockingRisk: false,
    },
    {
      evidenceType: "Site activation timeline and performance",
      source: "CRO and sponsor project management records",
      howToObtain: "Request from clinical operations director; may be in CRO performance reports",
      estimatedEffort: "2-3 days",
      blockingRisk: false,
    },
    {
      evidenceType: "CRO contract terms and SLAs",
      source: "Procurement or clinical operations",
      howToObtain: "Confidential; requires senior leadership approval and NDA",
      estimatedEffort: "1-2 weeks with legal review",
      blockingRisk: true,
    },
    {
      evidenceType: "Competitive landscape timeline",
      source: "Evaluate Pharma, analyst reports, ClinicalTrials.gov competitive trials",
      howToObtain: "Public sources + analyst reports (may require subscription)",
      estimatedEffort: "2-3 days",
      blockingRisk: false,
    },
    {
      evidenceType: "Investor assumptions and analyst models",
      source: "Company IR presentations, sell-side analyst reports",
      howToObtain: "Public for public companies; request IR deck for private",
      estimatedEffort: "1 day (public) to 1 week (private)",
      blockingRisk: false,
    },
  ],

  discoveryQuestions: [
    {
      questionId: "DQ001-EX3",
      question: "What's the root cause of the enrollment shortfall— is it site activation delays, patient population scarcity, protocol eligibility criteria, or site execution issues?",
      targetPersona: "Head of Clinical Development",
      insightSought: "Diagnose whether problem is supply (sites/patients) or demand (recruitment execution) to tailor solution",
      recommendedCallStage: "early",
      linkedPainId: "P013",
      linkedKpiId: "K043",
    },
    {
      questionId: "DQ002-EX3",
      question: "What percentage of screen failures are due to inclusion/exclusion criteria vs. patient withdrawal vs. safety findings? Which criterion drives the most failures?",
      targetPersona: "Head of Clinical Development",
      insightSought: "Identify whether protocol amendment or pre-screening optimization would have highest impact",
      recommendedCallStage: "early",
      linkedPainId: "P013",
      linkedKpiId: "K044",
    },
    {
      questionId: "DQ003-EX3",
      question: "How many sites are activated vs. planned, and what's the typical time from site selection to first patient in? How does that compare to your CRO's SLA?",
      targetPersona: "Head of Clinical Development",
      insightSought: "Assess site activation bottleneck and CRO accountability for timeline recovery",
      recommendedCallStage: "early",
      linkedPainId: "P013",
      linkedKpiId: "K045",
    },
    {
      questionId: "DQ004-EX3",
      question: "What's your current monthly burn rate, and how does the enrollment delay affect your cash runway and next financing milestone?",
      targetPersona: "CFO",
      insightSought: "Quantify financial urgency and validate budget availability for rescue investment",
      recommendedCallStage: "middle",
      linkedPainId: "P014",
      linkedKpiId: "K043",
    },
    {
      questionId: "DQ005-EX3",
      question: "Have you evaluated decentralized trial elements (remote monitoring, telemedicine visits, direct-to-patient shipping) for this study? What's been the barrier?",
      targetPersona: "Head of Clinical Development",
      insightSought: "Assess DCT maturity and identify regulatory/operational barriers to hybrid trial model",
      recommendedCallStage: "middle",
      linkedPainId: "P013",
      linkedKpiId: "K043",
    },
  ],
};

// =============================================================================
// EXPORT ALL EXAMPLES
// =============================================================================

export const healthcareSignalExamples: SignalToHypothesisExample[] = [
  example1,
  example2,
  example3,
];

export type {
  RawSignal,
  InterpretedSignal,
  BusinessPainRef,
  KPIImpact,
  PersonaEngagement,
  ValueHypothesis,
  EvidenceNeeded,
  DiscoveryQuestion,
  SignalToHypothesisExample,
  ValueDriverCategory,
  ConfidenceLevel,
  PrevalenceLevel,
  UrgencyLevel,
};

// =============================================================================
// USAGE EXAMPLE (for reference)
// =============================================================================
/*
// Import and access a worked example:
import { healthcareSignalExamples } from './signals-examples';

const ex1 = healthcareSignalExamples[0]; // Revenue cycle denial crisis
console.log(ex1.valueHypothesis.estimatedAnnualValue); // "$18.5M (midpoint of range)"
console.log(ex1.discoveryQuestions[0].question); // First discovery question

// Traverse the full pipeline:
// ex1.rawSignal -> ex1.interpretedSignal -> ex1.relevantPains -> ex1.affectedPersonas
// -> ex1.kpisImpacted -> ex1.valueHypothesis -> ex1.evidenceNeeded -> ex1.discoveryQuestions
*/
