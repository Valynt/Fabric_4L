/**
 * Financial Services Master ValuePack - Signal-to-Hypothesis Worked Examples
 * 
 * These examples demonstrate the complete reasoning chain from raw signal
 * to value hypothesis, showing how the ValuePack components interconnect.
 * 
 * Schema: raw signal → interpreted signal → relevant pains → affected personas
 * → KPIs impacted → value hypothesis → confidence → evidence needed
 * → discovery questions
 */

// ============================================================
// TYPE DEFINITIONS (Reference interfaces from value-pack.md)
// ============================================================

type SignalConfidence = "HIGH" | "MEDIUM" | "LOW";
type PainPrevalence = "HIGH" | "MEDIUM" | "LOW";
type ValueDriverCategory = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";

interface RawSignal {
  source: string;
  sourceType: "10-K" | "earnings_call" | "job_posting" | "regulatory_filing" | "news" | "benchmark";
  observedPattern: string;
  timestamp: string;
  segment: string;
}

interface InterpretedSignal {
  signalRuleId: string;
  interpretedMeaning: string;
  confidenceScore: number;
  confidenceLevel: SignalConfidence;
  confirmationSignalsNeeded: string[];
}

interface PainImpact {
  painId: string;
  painName: string;
  prevalence: PainPrevalence;
  symptomsMatched: string[];
}

interface PersonaImpact {
  personaId: string;
  personaName: string;
  influenceType: "economic" | "technical" | "user";
  relevanceRationale: string;
}

interface KPIImpact {
  kpiId: string;
  kpiName: string;
  currentEstimate: string;
  benchmarkComparison: string;
  gapDirection: "above" | "below" | "at";
}

interface ValueHypothesis {
  hypothesisStatement: string;
  valueDriverCategory: ValueDriverCategory;
  quantifiedEstimate: string;
  formulaId: string;
  applicableSegments: string[];
  timeToValue: string;
}

interface EvidenceNeeded {
  evidenceType: string;
  accessMethod: string;
  confidenceBoost: number;
  validationQuestion: string;
}

interface DiscoveryQuestionSet {
  questions: {
    questionId: string;
    questionText: string;
    targetPersona: string;
    expectedInsight: string;
  }[];
}

interface WorkedExample {
  exampleId: string;
  title: string;
  rawSignal: RawSignal;
  interpretedSignal: InterpretedSignal;
  painsImpacted: PainImpact[];
  personasAffected: PersonaImpact[];
  kpisImpacted: KPIImpact[];
  valueHypothesis: ValueHypothesis;
  evidenceNeeded: EvidenceNeeded[];
  discoveryQuestions: DiscoveryQuestionSet;
}

// ============================================================
// EXAMPLE 1: AML False Positive Fatigue Detected via Job Postings
// ============================================================

const example1_AMLJobPostingSurge: WorkedExample = {
  exampleId: "EX001",
  title: "AML False Positive Fatigue Detected via Compliance Job Posting Surge",

  rawSignal: {
    source: "LinkedIn + Burning Glass job posting aggregation",
    sourceType: "job_posting",
    observedPattern:
      "Regional bank (assets $50B-$100B) increased AML investigator job postings by 65% " +
      "over 90 days, with 3 senior AML manager roles and 8 investigator-level roles. " +
      "Prior 12-month baseline: 2 investigator postings total. Job descriptions mention " +
      "'high-volume alert review', 'SAR preparation', and 'regulatory remediation'.",
    timestamp: "2026-Q1",
    segment: "Banking"
  },

  interpretedSignal: {
    signalRuleId: "SR026",
    interpretedMeaning:
      "Sudden surge in compliance hiring, especially at senior levels, strongly suggests " +
      "either a regulatory consent order, MRA findings, or an internal control failure " +
      "that has overwhelmed existing AML operations capacity. The mention of 'regulatory remediation' " +
      "confirms this is reactive, not proactive, capacity building.",
    confidenceScore: 0.82,
    confidenceLevel: "MEDIUM",
    confirmationSignalsNeeded: [
      "Regulatory examination calendar or MRA history for the institution",
      "Recent consent order or enforcement action search (OCC/FDIC/Fed)",
      "Current alert volume and false positive rate from public disclosures or industry data",
      "LinkedIn profile analysis of recent departures in compliance leadership"
    ]
  },

  painsImpacted: [
    {
      painId: "P005",
      painName: "Anti-Money Laundering (AML) False Positive Fatigue",
      prevalence: "HIGH",
      symptomsMatched: [
        "Investigator attrition >20% annually (inverted: they are hiring because of attrition)",
        "Alert backlog >30 days (implied by need for 8+ investigators)",
        "Regulatory criticism in exam reports (implied by 'regulatory remediation')"
      ]
    }
  ],

  personasAffected: [
    {
      personaId: "PER004",
      personaName: "Chief Compliance Officer (CCO)",
      influenceType: "technical",
      relevanceRationale:
        "CCO is directly accountable for AML program adequacy. Job posting surge indicates " +
        "capacity crisis under their leadership. They need a solution that reduces investigator " +
        "dependence while satisfying regulators."
    },
    {
      personaId: "PER003",
      personaName: "Chief Risk Officer (CRO)",
      influenceType: "economic",
      relevanceRationale:
        "CRO owns aggregate operational risk and regulatory relationship. AML program " +
        "deficiency elevates operational risk profile and could trigger enforcement action " +
        "with capital or growth implications."
    },
    {
      personaId: "PER005",
      personaName: "Chief Operating Officer (COO)",
      influenceType: "economic",
      relevanceRationale:
        "COO responsible for operations efficiency. Manual alert review at scale is " +
        "operationally expensive and does not scale linearly with business growth."
    }
  ],

  kpisImpacted: [
    {
      kpiId: "K015",
      kpiName: "AML Alert False Positive Rate",
      currentEstimate: ">90% (inferred from industry median and need for mass hiring)",
      benchmarkComparison: "Best-in-class: 55-75% (B009)",
      gapDirection: "above"
    },
    {
      kpiId: "K016",
      kpiName: "SAR Filing Timeliness",
      currentEstimate: "<85% (implied by backlog pressure)",
      benchmarkComparison: "Best-in-class: 95-100%",
      gapDirection: "below"
    },
    {
      kpiId: "K017",
      kpiName: "Cost Per AML Alert",
      currentEstimate: "$120-$150 (high manual labor component)",
      benchmarkComparison: "Best-in-class: $30-80 (B010)",
      gapDirection: "above"
    }
  ],

  valueHypothesis: {
    hypothesisStatement:
      "By deploying AI-enhanced transaction monitoring with adaptive tuning, the institution " +
      "can reduce false positive rate from ~90% to ~70%, eliminate 60% of investigator FTE " +
      "growth need, and reduce cost-per-alert by 40%, while improving SAR timeliness to >95%.",
    valueDriverCategory: "Cost Savings",
    quantifiedEstimate:
      "Assuming 1.5M annual alerts, reducing false positives by 20 points eliminates 300K " +
      "unnecessary investigations. At $120/alert, this yields $36M in annual investigator " +
      "capacity savings. Additional savings from reduced regulatory remediation costs: $5-10M annually.",
    formulaId: "VF004",
    applicableSegments: ["Banking"],
    timeToValue: "6-9 months (tuning and model validation phase); 12 months for full savings realization"
  },

  evidenceNeeded: [
    {
      evidenceType: "Alert disposition statistics (last 12 months)",
      accessMethod: "Direct request during discovery; or industry benchmark inference",
      confidenceBoost: 0.15,
      validationQuestion: "What is your current monthly alert volume and false positive rate?"
    },
    {
      evidenceType: "Regulatory examination findings or MRA list",
      accessMethod: "Public regulatory database search or direct inquiry",
      confidenceBoost: 0.10,
      validationQuestion: "Have you received any recent MRAs or findings related to BSA/AML?"
    },
    {
      evidenceType: "Investigator FTE count and loaded cost",
      accessMethod: "Direct request during discovery",
      confidenceBoost: 0.10,
      validationQuestion: "How many investigator FTEs do you currently have, and what is the fully loaded annual cost per investigator?"
    }
  ],

  discoveryQuestions: {
    questions: [
      {
        questionId: "DQ005",
        questionText:
          "What is your current AML alert false positive rate, and how many investigator FTEs " +
          "are required to clear your monthly alert volume?",
        targetPersona: "Chief Compliance Officer",
        expectedInsight: "Quantifies AML program inefficiency and human capital constraint"
      },
      {
        questionId: "DQ005-FOLLOWUP",
        questionText:
          "If you could reduce your false positive rate by 20 percentage points, how would you " +
          "redeploy the investigator capacity?",
        targetPersona: "Chief Compliance Officer",
        expectedInsight: "Reveals whether capacity constraint is the real pain or if regulator satisfaction is the priority"
      },
      {
        questionId: "DQ005-FOLLOWUP-2",
        questionText:
          "What would be the regulatory consequence if your SAR filing timeliness fell below 90%?",
        targetPersona: "Chief Compliance Officer / CRO",
        expectedInsight: "Quantifies risk of inaction and regulatory enforcement exposure"
      }
    ]
  }
};

// ============================================================
// EXAMPLE 2: NIM Compression Triggering Core Banking Modernization
// ============================================================

const example2_NIMCompressionCoreModernization: WorkedExample = {
  exampleId: "EX002",
  title: "NIM Compression and Deposit Beta Escalation Triggering Core Banking Modernization",

  rawSignal: {
    source: "Q4 2025 10-K filing + earnings call transcript",
    sourceType: "10-K",
    observedPattern:
      "Regional bank disclosed NIM decline of 28bps YoY to 2.92%. Deposit beta accelerated " +
      "to 72% (up from 45% prior year). Management stated in earnings call: 'We are evaluating " +
      "our technology investments to improve deposit pricing agility and product personalization.' " +
      "IT spend increased 14% YoY but digital revenue remains <12% of total.",
    timestamp: "2026-Q1",
    segment: "Banking"
  },

  interpretedSignal: {
    signalRuleId: "SR003",
    interpretedMeaning:
      "NIM compression of >25bps with deposit beta >70% indicates structural funding cost " +
      "pressure. The 14% IT spend increase with minimal digital revenue suggests legacy maintenance " +
      "is consuming investment without enabling revenue-generating innovation. The earnings call " +
      "language ('evaluating technology investments') is a classic precursor to core modernization RFP.",
    confidenceScore: 0.90,
    confidenceLevel: "HIGH",
    confirmationSignalsNeeded: [
      "Core banking platform contract expiration date",
      "IT budget breakdown (run-the-bank vs change-the-bank)",
      "ALCO minutes or deposit repricing strategy documents",
      "Digital product launch count in past 24 months"
    ]
  },

  painsImpacted: [
    {
      painId: "P003",
      painName: "Net Interest Margin (NIM) Compression",
      prevalence: "HIGH",
      symptomsMatched: [
        "NIM declining >15bps YoY (actual: 28bps)",
        "Deposit beta >70% (actual: 72%)",
        "Loan pricing power erosion (implied by margin compression)",
        "Brokered deposit dependence rising (implied by beta acceleration)"
      ]
    },
    {
      painId: "P001",
      painName: "Legacy Core Banking Modernization Debt",
      prevalence: "HIGH",
      symptomsMatched: [
        "Product launch cycles >9 months (implied by low digital revenue)",
        "Maintenance consuming >40% of IT budget (implied by 14% IT growth with no digital revenue growth)",
        "Inability to offer real-time payments (likely given legacy constraints)"
      ]
    },
    {
      painId: "P018",
      painName: "Customer Churn and Deposit Attrition",
      prevalence: "HIGH",
      symptomsMatched: [
        "Deposit beta >60% (actual: 72%)",
        "Core deposit outflows >5% quarterly (implied by beta acceleration)",
        "Customer churn >15% annually (implied by pricing pressure)"
      ]
    }
  ],

  personasAffected: [
    {
      personaId: "PER001",
      personaName: "Chief Financial Officer (CFO)",
      influenceType: "economic",
      relevanceRationale:
        "CFO owns NIM and deposit pricing strategy. The 28bps NIM decline directly impacts " +
        "net income. CFO needs quantified path to margin recovery within 12-18 months."
    },
    {
      personaId: "PER002",
      personaName: "Chief Information Officer (CIO)",
      influenceType: "technical",
      relevanceRationale:
        "CIO owns IT spend and core platform decisions. The 14% IT increase without digital " +
        "return creates pressure to reallocate budget. CIO needs modernization roadmap that " +
        "reduces run-the-bank ratio."
    },
    {
      personaId: "PER008",
      personaName: "Head of Digital / Chief Digital Officer",
      influenceType: "technical",
      relevanceRationale:
        "Digital leader unable to launch products due to core constraints. They need platform " +
        "agility to compete with neobanks and deliver personalization."
    }
  ],

  kpisImpacted: [
    {
      kpiId: "K009",
      kpiName: "Net Interest Margin (NIM)",
      currentEstimate: "2.92% (declined 28bps YoY)",
      benchmarkComparison: "Top quartile: 3.8-4.5% (B001); Median: 2.8-3.6% (B002)",
      gapDirection: "below"
    },
    {
      kpiId: "K006",
      kpiName: "Deposit Beta",
      currentEstimate: "72%",
      benchmarkComparison: "Best-in-class: 30-55% (B007)",
      gapDirection: "above"
    },
    {
      kpiId: "K002",
      kpiName: "IT Maintenance Spend Ratio",
      currentEstimate: ">65% (inferred from 14% IT growth with minimal digital revenue)",
      benchmarkComparison: "Best-in-class: 50-65%",
      gapDirection: "above"
    }
  ],

  valueHypothesis: {
    hypothesisStatement:
      "By modernizing the core banking platform to enable real-time deposit pricing, " +
      "dynamic product bundling, and personalized rate offers, the bank can reduce deposit " +
      "beta from 72% to 50%, recovering 15-22bps of NIM on a $30B deposit base. " +
      "Core modernization also enables 3-4 new digital product launches per year, " +
      "accelerating digital revenue growth from 12% to 20%+ of total.",
    valueDriverCategory: "Revenue Uplift",
    quantifiedEstimate:
      "NIM recovery: 18bps * $30B earning assets = $54M annual pre-tax revenue. " +
      "Digital product revenue acceleration: $20M annually. " +
      "IT maintenance ratio reduction from 65% to 50%: $15M annual run-rate savings.",
    formulaId: "VF003",
    applicableSegments: ["Banking", "Credit Unions"],
    timeToValue: "18-24 months (core migration timeline); NIM benefits within 6 months of pricing engine deployment"
  },

  evidenceNeeded: [
    {
      evidenceType: "Current core banking platform contract and expiration date",
      accessMethod: "Direct inquiry or vendor contract intelligence",
      confidenceBoost: 0.10,
      validationQuestion: "What core banking platform are you on, and when does the contract expire?"
    },
    {
      evidenceType: "ALCO deposit repricing strategy and beta sensitivity model",
      accessMethod: "Direct request during executive discovery",
      confidenceBoost: 0.15,
      validationQuestion: "What is your ALCO forecast for deposit beta under a 100bps rate change scenario?"
    },
    {
      evidenceType: "IT budget breakdown (run vs grow vs transform)",
      accessMethod: "Direct request during CFO/CIO discovery",
      confidenceBoost: 0.10,
      validationQuestion: "What percentage of your IT budget is consumed by run-the-bank activities?"
    }
  ],

  discoveryQuestions: {
    questions: [
      {
        questionId: "DQ001",
        questionText:
          "What percentage of your IT budget is currently consumed by run-the-bank versus " +
          "change-the-bank activities, and how has that shifted over the past three years?",
        targetPersona: "CFO / CIO",
        expectedInsight: "Quantifies legacy maintenance burden and transformation capacity constraint"
      },
      {
        questionId: "DQ003",
        questionText:
          "How many months does it typically take to launch a new retail deposit or lending " +
          "product from concept to market, and where do the bottlenecks occur?",
        targetPersona: "CIO / Head of Digital",
        expectedInsight: "Reveals core system agility constraints and product innovation friction"
      },
      {
        questionId: "DQ018",
        questionText:
          "What is your current core deposit growth rate versus your cost of funds trend? " +
          "How much deposit outflow have you experienced to higher-yield alternatives?",
        targetPersona: "CFO / Treasurer",
        expectedInsight: "Reveals funding stability and NIM pressure dynamics"
      }
    ]
  }
};

// ============================================================
// EXAMPLE 3: Settlement Fail Spike Post T+1 Driving Operations Modernization
// ============================================================

const example3_SettlementFailOpsModernization: WorkedExample = {
  exampleId: "EX003",
  title: "Settlement Fail Rate Spike Post T+1 Driving Operations and Clearing Modernization",

  rawSignal: {
    source: "DTCC monthly settlement efficiency report + broker-dealer 10-K risk disclosures",
    sourceType: "benchmark",
    observedPattern:
      "Mid-size broker-dealer (clearing volume ~2M trades/month) reported settlement fail rate " +
      "of 7.2% in Q4 2025, up from 3.1% in Q2 2025 (pre-T+1 baseline). CSDR cash penalties " +
      "disclosed as $4.2M for the quarter. Operations headcount grew 18% while trade volume " +
      "declined 5%. Management disclosed in 10-K: 'Operational challenges following industry " +
      "transition to T+1 settlement cycles have increased manual processing requirements.'",
    timestamp: "2026-Q1",
    segment: "Capital Markets"
  },

  interpretedSignal: {
    signalRuleId: "SR009",
    interpretedMeaning:
      "Settlement fail rate more than doubled post-T+1 with penalty costs >$4M/quarter. " +
      "Operations headcount growing faster than volume is a classic sign of manual process " +
      "bloat and STP breakdown. The 10-K disclosure confirms this is a material operational " +
      "risk. This organization urgently needs trade matching automation and operational " +
      "efficiency improvements.",
    confidenceScore: 0.93,
    confidenceLevel: "HIGH",
    confirmationSignalsNeeded: [
      "DTCC fail rate trend data for the firm",
      "CSDR penalty register detail",
      "Trade matching automation rate (STP rate)",
      "Operations headcount vs volume correlation"
    ]
  },

  painsImpacted: [
    {
      painId: "P009",
      painName: "Trade and Settlement Failure Costs",
      prevalence: "MEDIUM",
      symptomsMatched: [
        "Settlement fail rate >5% (actual: 7.2%)",
        "CSDR cash penalties >$10M annually (actual: $16.8M annualized)",
        "Manual matching >20% of trades (implied by headcount growth)",
        "Operations headcount growing faster than volume (actual: +18% headcount, -5% volume)"
      ]
    }
  ],

  personasAffected: [
    {
      personaId: "PER005",
      personaName: "Chief Operating Officer (COO)",
      influenceType: "economic",
      relevanceRationale:
        "COO directly accountable for operations efficiency and settlement performance. " +
        "CSDR penalties and headcount inflation are P&L-impacting operational failures."
    },
    {
      personaId: "PER001",
      personaName: "Chief Financial Officer (CFO)",
      influenceType: "economic",
      relevanceRationale:
        "CFO must account for $16.8M annualized penalty cost plus 18% ops headcount growth " +
        "in a declining volume environment. This is unsustainable unit economics."
    },
    {
      personaId: "PER002",
      personaName: "Chief Information Officer (CIO)",
      influenceType: "technical",
      relevanceRationale:
        "CIO owns trade matching and settlement technology. STP rate of <80% indicates " +
        "technology architecture gaps that only IT can resolve."
    }
  ],

  kpisImpacted: [
    {
      kpiId: "K027",
      kpiName: "Settlement Fail Rate",
      currentEstimate: "7.2%",
      benchmarkComparison: "Best-in-class: 1-3% (B018)",
      gapDirection: "above"
    },
    {
      kpiId: "K028",
      kpiName: "Trade Matching Automation Rate",
      currentEstimate: "<75% (implied by manual processing growth)",
      benchmarkComparison: "Best-in-class: 90-98% (B019)",
      gapDirection: "below"
    },
    {
      kpiId: "K029",
      kpiName: "Cost Per Trade Settled",
      currentEstimate: "$3.50-$4.00 (inferred from headcount growth)",
      benchmarkComparison: "Best-in-class: $0.80-2.00 (B018 context)",
      gapDirection: "above"
    }
  ],

  valueHypothesis: {
    hypothesisStatement:
      "By implementing intelligent trade matching with AI-powered exception management " +
      "and straight-through processing automation, the broker-dealer can reduce settlement " +
      "fail rate from 7.2% to <3%, eliminate $10M+ in annual CSDR penalties, and reduce " +
      "operations headcount growth to match volume trends.",
    valueDriverCategory: "Cost Savings",
    quantifiedEstimate:
      "CSDR penalty avoidance: ($4.2M/Qtr * 4) reduced by 60% = $10M annual savings. " +
      "Operations efficiency: 18% headcount growth reversal saves $6M annually. " +
      "Fail rate reduction to 2%: additional $3M in avoided fails and financing costs.",
    formulaId: "VF008",
    applicableSegments: ["Capital Markets"],
    timeToValue: "3-6 months (matching engine deployment); 9-12 months for full STP rate improvement"
  },

  evidenceNeeded: [
    {
      evidenceType: "DTCC fail rate data and CSDR penalty register (last 4 quarters)",
      accessMethod: "Direct request or DTCC public reporting",
      confidenceBoost: 0.15,
      validationQuestion: "What has been your monthly settlement fail rate since T+1 implementation?"
    },
    {
      evidenceType: "Operations headcount and productivity metrics",
      accessMethod: "Direct request during COO discovery",
      confidenceBoost: 0.10,
      validationQuestion: "How has your operations headcount trended relative to trade volume over the past 12 months?"
    },
    {
      evidenceType: "Current trade matching STP rate and exception root cause analysis",
      accessMethod: "Direct request during operations discovery",
      confidenceBoost: 0.10,
      validationQuestion: "What is your current straight-through processing rate, and what are the top 3 causes of manual exceptions?"
    }
  ],

  discoveryQuestions: {
    questions: [
      {
        questionId: "DQ009",
        questionText:
          "What is your current settlement fail rate, and how much are you incurring in " +
          "CSDR penalties or manual reconciliation costs annually?",
        targetPersona: "COO / CFO",
        expectedInsight: "Quantifies post-T+1 operational readiness and cost leakage"
      },
      {
        questionId: "DQ009-FOLLOWUP",
        questionText:
          "What percentage of your trades require manual matching or intervention, and how " +
          "has that changed since T+1?",
        targetPersona: "Head of Operations / CIO",
        expectedInsight: "Reveals STP breakdown and automation gap"
      },
      {
        questionId: "DQ009-FOLLOWUP-2",
        questionText:
          "If you could reduce your fail rate by 4 percentage points, what would be the impact " +
          "on client satisfaction and correspondent banking relationships?",
        targetPersona: "COO",
        expectedInsight: "Reveals broader relationship and reputational value beyond direct cost"
      }
    ]
  }
};

// ============================================================
// EXPORTS
// ============================================================

export const workedExamples: WorkedExample[] = [
  example1_AMLJobPostingSurge,
  example2_NIMCompressionCoreModernization,
  example3_SettlementFailOpsModernization
];

export type {
  RawSignal,
  InterpretedSignal,
  PainImpact,
  PersonaImpact,
  KPIImpact,
  ValueHypothesis,
  EvidenceNeeded,
  DiscoveryQuestionSet,
  WorkedExample,
  SignalConfidence,
  PainPrevalence,
  ValueDriverCategory
};

/**
 * Usage:
 * import { workedExamples } from './signals-examples';
 * 
 * const example = workedExamples[0]; // AML Job Posting example
 * console.log(example.rawSignal.observedPattern);
 * console.log(example.valueHypothesis.quantifiedEstimate);
 */
