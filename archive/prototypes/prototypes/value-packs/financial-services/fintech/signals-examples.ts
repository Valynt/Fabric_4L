/**
 * Fintech Subpack Signal Examples (fintech-v1)
 * 
 * TypeScript-style interface definitions and signal interpretation examples
 * for the Fintech vertical subpack of the Financial Services Master ValuePack.
 * 
 * Parent Master: financial-services-master-v1
 * Agent Swarm: kimi-k2.6-swarm-s4.4-fintech
 */

// ============================================================================
// CORE INTERFACES (Vertical-specialized extensions of Master schema)
// ============================================================================

interface FintechSignalRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  confidenceScore: number; // 0.0 - 1.0
  requiredConfirmationSignals: string[];
}

interface FintechKPI {
  id: string;
  name: string;
  formula: string;
  unit: string;
  typicalRange: string;
  benchmarkRange: string;
  valueDriverLinks: string[];
  segmentApplicability: string[];
  calculationFrequency: string;
}

interface FintechPain {
  id: string;
  name: string;
  description: string;
  symptoms: string[];
  affectedSegments: string[];
  affectedPersonas: string[];
  linkedKPIs: string[];
  linkedValueDrivers: string[];
  prevalence: "HIGH" | "MEDIUM" | "LOW";
  confidence: "HIGH" | "MEDIUM" | "LOW";
}

interface FintechValueFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  applicableSegments: string[];
  confidenceRules: string;
  exampleCalculation: string;
}

interface SignalInterpretationResult {
  ruleId: string;
  triggered: boolean;
  confidence: number;
  linkedPain: FintechPain | null;
  linkedKPIs: FintechKPI[];
  recommendedAction: string;
  financialImpactEstimate: string;
}

// ============================================================================
// SIGNAL RULES REGISTRY
// ============================================================================

export const FINTECH_SIGNAL_RULES: FintechSignalRule[] = [
  {
    id: "FT-S001",
    signalName: "Payment Authorization Latency Spike",
    rawSignalPattern: "p99 authorization latency >500ms for 3+ consecutive days",
    interpretedMeaning: "Payment infrastructure capacity constraint or processor degradation threatening customer experience and revenue",
    linkedPains: ["FT-P001"],
    linkedKPIs: ["FT-K001", "FT-K002"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: [
      "Processor status page degradation",
      "Transaction volume spike correlation",
      "Error rate increase"
    ]
  },
  {
    id: "FT-S002",
    signalName: "KYC Document Upload Failure Surge",
    rawSignalPattern: "Document upload failure rate >30% in 7-day rolling window",
    interpretedMeaning: "Identity verification vendor reliability issue or UX friction causing onboarding abandonment and CAC erosion",
    linkedPains: ["FT-P002"],
    linkedKPIs: ["FT-K004", "FT-K005"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: [
      "Vendor incident report",
      "Device type breakdown",
      "Geographic concentration"
    ]
  },
  {
    id: "FT-S003",
    signalName: "Embedded Finance Partner Churn Risk",
    rawSignalPattern: "Partner API call volume declining >20% MoM with support tickets increasing >30%",
    interpretedMeaning: "Partner dissatisfaction or competitive switching indicating integration quality or relationship management issues",
    linkedPains: ["FT-P003"],
    linkedKPIs: ["FT-K007", "FT-K008"],
    confidenceScore: 0.75,
    requiredConfirmationSignals: [
      "Partner NPS survey",
      "Competitor win/loss data",
      "Contract renewal dates"
    ]
  },
  {
    id: "FT-S004",
    signalName: "BNPL Vintage Deterioration",
    rawSignalPattern: "30+ day delinquency on 6-month vintages increasing >25% sequentially",
    interpretedMeaning: "Credit risk model degradation or macro stress requiring underwriting tightening and reserve increases",
    linkedPains: ["FT-P004"],
    linkedKPIs: ["FT-K010", "FT-K012"],
    confidenceScore: 0.90,
    requiredConfirmationSignals: [
      "Vintage loss curves",
      "FICO distribution shift",
      "Macro unemployment data"
    ]
  },
  {
    id: "FT-S005",
    signalName: "Chargeback Rate Approaching Network Threshold",
    rawSignalPattern: "Rolling 30-day chargeback rate >0.80% with upward trend",
    interpretedMeaning: "Fraud control inadequacy or merchant quality issues risking monitoring program enrollment and processor relationship",
    linkedPains: ["FT-P005"],
    linkedKPIs: ["FT-K013", "FT-K014"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: [
      "Reason code analysis",
      "Merchant category breakdown",
      "Fraud detection alert volume"
    ]
  },
  {
    id: "FT-S006",
    signalName: "Crypto Exchange Unusual Outflows",
    rawSignalPattern: "Net outflows >5% of AUC in 48 hours with social media sentiment decline",
    interpretedMeaning: "Customer confidence erosion potentially driven by security incident rumor or regulatory news",
    linkedPains: ["FT-P006", "FT-P020"],
    linkedKPIs: ["FT-K016", "FT-K059"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: [
      "On-chain flow analysis",
      "News sentiment monitoring",
      "Customer service inquiry spike"
    ]
  },
  {
    id: "FT-S007",
    signalName: "RegTech Alert Volume Explosion",
    rawSignalPattern: "Daily alert volume >3 standard deviations above 90-day mean",
    interpretedMeaning: "Transaction monitoring system tuning failure or genuine AML event requiring immediate investigation capacity surge",
    linkedPains: ["FT-P007"],
    linkedKPIs: ["FT-K020", "FT-K019"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: [
      "TM rule change log",
      "Transaction pattern analysis",
      "Investigator queue depth"
    ]
  },
  {
    id: "FT-S008",
    signalName: "WealthTech Engagement Decline",
    rawSignalPattern: "DAU/MAU declining >15% over 90 days with AUM outflows accelerating",
    interpretedMeaning: "Product-market fit erosion or competitive switching requiring feature investment or pricing review",
    linkedPains: ["FT-P008"],
    linkedKPIs: ["FT-K022", "FT-K024"],
    confidenceScore: 0.72,
    requiredConfirmationSignals: [
      "Feature usage heatmap",
      "Competitor launch timeline",
      "Customer exit survey data"
    ]
  },
  {
    id: "FT-S009",
    signalName: "BaaS Sponsor Bank Regulatory Action",
    rawSignalPattern: "Sponsor bank receives OCC consent order or FDIC MRA with BaaS program mention",
    interpretedMeaning: "Existential program risk requiring immediate alternative bank sourcing and compliance enhancement",
    linkedPains: ["FT-P009"],
    linkedKPIs: ["FT-K025", "FT-K026"],
    confidenceScore: 0.92,
    requiredConfirmationSignals: [
      "Regulatory order text",
      "Sponsor bank public response",
      "Program contract termination clauses"
    ]
  },
  {
    id: "FT-S010",
    signalName: "Stablecoin De-peg Event",
    rawSignalPattern: "Stablecoin price deviates >50bps from peg for >1 hour with volume surge",
    interpretedMeaning: "Reserve adequacy concern or redemption capacity constraint threatening market confidence and regulatory scrutiny",
    linkedPains: ["FT-P010"],
    linkedKPIs: ["FT-K029", "FT-K028"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: [
      "Reserve composition breakdown",
      "Redemption queue depth",
      "Secondary market depth"
    ]
  }
];

// ============================================================================
// KPI REGISTRY (Sample - first 15 of 60)
// ============================================================================

export const FINTECH_KPIS: FintechKPI[] = [
  {
    id: "FT-K001",
    name: "Payment Authorization Latency (p99)",
    formula: "99th Percentile of Authorization Response Time in Milliseconds",
    unit: "milliseconds",
    typicalRange: "300-800",
    benchmarkRange: "80-200",
    valueDriverLinks: ["FT-VD001", "FT-VD002"],
    segmentApplicability: ["Payments", "Fintech"],
    calculationFrequency: "daily"
  },
  {
    id: "FT-K002",
    name: "False Decline Rate",
    formula: "(False Declines / Total Declined Transactions) * 100",
    unit: "percentage",
    typicalRange: "10-25",
    benchmarkRange: "3-8",
    valueDriverLinks: ["FT-VD001"],
    segmentApplicability: ["Payments", "Fintech"],
    calculationFrequency: "daily"
  },
  {
    id: "FT-K003",
    name: "Cart Abandonment Rate (Post-Decline)",
    formula: "(Abandoned Sessions After Decline / Total Sessions with Decline) * 100",
    unit: "percentage",
    typicalRange: "60-85",
    benchmarkRange: "30-50",
    valueDriverLinks: ["FT-VD002"],
    segmentApplicability: ["Payments", "Fintech"],
    calculationFrequency: "daily"
  },
  {
    id: "FT-K004",
    name: "KYC Onboarding Completion Rate",
    formula: "(Completed Onboardings / Started Onboardings) * 100",
    unit: "percentage",
    typicalRange: "30-55",
    benchmarkRange: "65-85",
    valueDriverLinks: ["FT-VD003", "FT-VD004"],
    segmentApplicability: ["Fintech", "Payments", "Crypto/Digital Assets"],
    calculationFrequency: "daily"
  },
  {
    id: "FT-K005",
    name: "KYC Manual Review Rate",
    formula: "(Manual Reviews Required / Total KYC Submissions) * 100",
    unit: "percentage",
    typicalRange: "20-40",
    benchmarkRange: "5-12",
    valueDriverLinks: ["FT-VD003"],
    segmentApplicability: ["Fintech", "Payments", "Lending Platforms"],
    calculationFrequency: "daily"
  },
  {
    id: "FT-K006",
    name: "Verification Cost Per User",
    formula: "Total KYC Operations Cost / Users Verified",
    unit: "USD",
    typicalRange: "6-15",
    benchmarkRange: "2-5",
    valueDriverLinks: ["FT-VD004"],
    segmentApplicability: ["Fintech", "Payments", "Crypto/Digital Assets"],
    calculationFrequency: "monthly"
  },
  {
    id: "FT-K010",
    name: "BNPL Net Loss Rate",
    formula: "(Charge-offs - Recoveries) / Average Receivables * 100",
    unit: "percentage",
    typicalRange: "5-12",
    benchmarkRange: "2-5",
    valueDriverLinks: ["FT-VD007"],
    segmentApplicability: ["BNPL"],
    calculationFrequency: "monthly"
  },
  {
    id: "FT-K013",
    name: "Fraud Chargeback Rate",
    formula: "(Fraud Chargebacks / Total Transaction Volume) * 100",
    unit: "percentage",
    typicalRange: "0.6-1.5",
    benchmarkRange: "0.2-0.5",
    valueDriverLinks: ["FT-VD009"],
    segmentApplicability: ["Payments", "Fintech"],
    calculationFrequency: "monthly"
  },
  {
    id: "FT-K016",
    name: "Crypto Hot Wallet Exposure Ratio",
    formula: "(Hot Wallet Balance / Total AUC) * 100",
    unit: "percentage",
    typicalRange: "3-10",
    benchmarkRange: "0.5-2.0",
    valueDriverLinks: ["FT-VD011"],
    segmentApplicability: ["Crypto/Digital Assets"],
    calculationFrequency: "daily"
  },
  {
    id: "FT-K019",
    name: "Alert-to-SAR Conversion Rate",
    formula: "(SARs Filed / Total Alerts Generated) * 100",
    unit: "percentage",
    typicalRange: "0.5-3.0",
    benchmarkRange: "3-8",
    valueDriverLinks: ["FT-VD013"],
    segmentApplicability: ["RegTech", "Fintech", "Crypto/Digital Assets"],
    calculationFrequency: "monthly"
  },
  {
    id: "FT-K022",
    name: "Robo-Advisor CAC",
    formula: "Total Sales & Marketing Spend / New Funded Accounts",
    unit: "USD",
    typicalRange: "300-600",
    benchmarkRange: "100-250",
    valueDriverLinks: ["FT-VD015"],
    segmentApplicability: ["WealthTech", "Fintech"],
    calculationFrequency: "quarterly"
  },
  {
    id: "FT-K025",
    name: "BaaS Sponsor Bank Concentration",
    formula: "(Deposits with Top Sponsor Bank / Total Deposits) * 100",
    unit: "percentage",
    typicalRange: "70-95",
    benchmarkRange: "30-50",
    valueDriverLinks: ["FT-VD017"],
    segmentApplicability: ["BaaS", "Embedded Finance"],
    calculationFrequency: "monthly"
  },
  {
    id: "FT-K028",
    name: "Stablecoin Reserve Liquidity Ratio",
    formula: "(Liquid Treasuries and Cash / Total Reserves) * 100",
    unit: "percentage",
    typicalRange: "60-85",
    benchmarkRange: "90-100",
    valueDriverLinks: ["FT-VD019"],
    segmentApplicability: ["Stablecoin Infrastructure"],
    calculationFrequency: "daily"
  },
  {
    id: "FT-K034",
    name: "Real-Time Payment Share",
    formula: "(RTP+FedNow Volume / Total Payment Volume) * 100",
    unit: "percentage",
    typicalRange: "2-8",
    benchmarkRange: "15-30",
    valueDriverLinks: ["FT-VD023"],
    segmentApplicability: ["Payments"],
    calculationFrequency: "monthly"
  },
  {
    id: "FT-K040",
    name: "Warehouse Facility Utilization",
    formula: "(Outstanding Advances / Total Facility Size) * 100",
    unit: "percentage",
    typicalRange: "70-90",
    benchmarkRange: "40-65",
    valueDriverLinks: ["FT-VD027"],
    segmentApplicability: ["Lending Platforms"],
    calculationFrequency: "daily"
  }
];

// ============================================================================
// PAIN REGISTRY (Sample - first 10 of 20)
// ============================================================================

export const FINTECH_PAINS: FintechPain[] = [
  {
    id: "FT-P001",
    name: "Payment Authorization Latency and False Declines",
    description: "High latency in payment authorization (>500ms) and excessive false declines (>15%) driving cart abandonment, customer churn, and issuer switch behavior in card programs.",
    symptoms: [
      "Authorization latency >500ms p99",
      "False decline rate >15%",
      "Cart abandonment >70% after decline",
      "Customer complaints to issuer >5% monthly",
      "Revenue loss from declined legitimate transactions >$10M/year"
    ],
    affectedSegments: ["Payments", "Fintech"],
    affectedPersonas: ["Payments Architect", "Head of Product", "CTO", "CRO"],
    linkedKPIs: ["FT-K001", "FT-K002", "FT-K003"],
    linkedValueDrivers: ["FT-VD001", "FT-VD002"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "FT-P002",
    name: "KYC Onboarding Drop-off and Compliance Friction",
    description: "Multi-step identity verification, document upload failures, and manual review backlogs causing >60% onboarding abandonment before first transaction.",
    symptoms: [
      "KYC onboarding drop-off >60%",
      "Document upload failure rate >25%",
      "Manual review queue >48 hours",
      "Verification cost per user >$8",
      "Regulatory rejection rate >5% on submitted KYC packets"
    ],
    affectedSegments: ["Fintech", "Payments", "Lending Platforms", "Crypto/Digital Assets"],
    affectedPersonas: ["Fintech Product Manager", "Crypto Compliance Officer", "Head of Fraud", "COO"],
    linkedKPIs: ["FT-K004", "FT-K005", "FT-K006"],
    linkedValueDrivers: ["FT-VD003", "FT-VD004"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "FT-P003",
    name: "Embedded Finance Integration Complexity and Time-to-Partner",
    description: "API fragmentation, certification cycles, and bespoke integration work extending time-to-first-transaction for embedded finance partners beyond 90 days.",
    symptoms: [
      "Integration cycle >90 days per partner",
      "API error rate >2% in production",
      "Partner certification backlog >6 months",
      "Developer support tickets >500/month",
      "Revenue recognition delay >30 days post-contract"
    ],
    affectedSegments: ["Embedded Finance", "BaaS", "Fintech"],
    affectedPersonas: ["Embedded Finance Partnerships Lead", "CTO", "Head of Product", "VP Engineering"],
    linkedKPIs: ["FT-K007", "FT-K008", "FT-K009"],
    linkedValueDrivers: ["FT-VD005", "FT-VD006"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "FT-P004",
    name: "BNPL Credit Loss Escalation and Funding Cost Pressure",
    description: "Thin-file underwriting models deteriorating in stressed credit environments, pushing net loss rates >8% while warehouse facility spreads widen.",
    symptoms: [
      "Net loss rate >8% on BNPL portfolio",
      "Repeat delinquency rate >35%",
      "Warehouse funding spread >300bps over SOFR",
      "Collection agency costs >20% of recoveries",
      "90+ day delinquency growing >2x originations"
    ],
    affectedSegments: ["BNPL", "Fintech"],
    affectedPersonas: ["CRO", "CFO", "Head of Product", "Fintech Product Manager"],
    linkedKPIs: ["FT-K010", "FT-K011", "FT-K012"],
    linkedValueDrivers: ["FT-VD007", "FT-VD008"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "FT-P005",
    name: "Fraud Chargeback Rate Exceeding Card Network Thresholds",
    description: "Fraud chargeback ratios exceeding 1% of transaction volume, triggering card network monitoring programs, fines, and potential termination of processing privileges.",
    symptoms: [
      "Chargeback rate >1% of volume",
      "Fraud-to-sales ratio >0.90%",
      "Card network monitoring program enrollment",
      "Chargeback fees >$50 per incident",
      "Revenue holdback by processor >10%"
    ],
    affectedSegments: ["Payments", "Fintech"],
    affectedPersonas: ["Fraud Ops Manager", "CRO", "Head of Risk", "Payments Architect"],
    linkedKPIs: ["FT-K013", "FT-K014", "FT-K015"],
    linkedValueDrivers: ["FT-VD009", "FT-VD010"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "FT-P006",
    name: "Crypto Wallet and Exchange Custody Security Breaches",
    description: "Hot wallet compromise, private key management failures, and insufficient multi-sig controls causing customer fund losses and regulatory enforcement.",
    symptoms: [
      "Hot wallet balance >5% of AUC",
      "No hardware security module (HSM) deployment",
      "Key ceremony lacks multi-party computation (MPC)",
      "Incident response plan untested >12 months",
      "Insurance coverage <50% of AUC"
    ],
    affectedSegments: ["Crypto/Digital Assets", "Fintech"],
    affectedPersonas: ["Crypto Compliance Officer", "CISO", "CTO", "CRO"],
    linkedKPIs: ["FT-K016", "FT-K017", "FT-K018"],
    linkedValueDrivers: ["FT-VD011", "FT-VD012"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "FT-P007",
    name: "RegTech Alert Fatigue and SAR Filing Backlogs",
    description: "Transaction monitoring systems generating excessive alerts with poor tuning, causing investigator fatigue and SAR filing delays beyond regulatory deadlines.",
    symptoms: [
      "Alert-to-SAR conversion rate <2%",
      "False positive rate >95%",
      "SAR filing backlog >30 days",
      "Investigator attrition >25% annually",
      "Regulatory MRAs on BSA/AML program"
    ],
    affectedSegments: ["RegTech", "Fintech", "Crypto/Digital Assets"],
    affectedPersonas: ["Crypto Compliance Officer", "Fraud Ops Manager", "Head of Compliance", "COO"],
    linkedKPIs: ["FT-K019", "FT-K020", "FT-K021"],
    linkedValueDrivers: ["FT-VD013", "FT-VD014"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "FT-P008",
    name: "WealthTech Robo-Advisor AUM Stagnation and Unit Economics",
    description: "Customer acquisition costs exceeding revenue per user, low account funding rates, and poor engagement causing negative unit economics in robo-advisory platforms.",
    symptoms: [
      "CAC >$400 per funded account",
      "Account funding rate <40% of signups",
      "AUM per user <$5,000",
      "Monthly active user rate <20%",
      "Gross margin per account negative"
    ],
    affectedSegments: ["WealthTech", "Fintech"],
    affectedPersonas: ["Growth/Growth Hacker", "CFO", "Head of Product", "CMO"],
    linkedKPIs: ["FT-K022", "FT-K023", "FT-K024"],
    linkedValueDrivers: ["FT-VD015", "FT-VD016"],
    prevalence: "MEDIUM",
    confidence: "MEDIUM"
  },
  {
    id: "FT-P009",
    name: "BaaS Sponsor Bank Dependency and Program Manager Risk",
    description: "Concentration in single sponsor banks, regulatory pressure on BaaS models, and sponsor bank termination risk threatening program viability.",
    symptoms: [
      ">80% deposits with single sponsor bank",
      "Sponsor bank regulatory enforcement action received",
      "Program manager oversight gaps identified by OCC/FDIC",
      "Contract renewal <12 months with no alternative",
      "Customer account transition cost >$50 per account"
    ],
    affectedSegments: ["BaaS", "Embedded Finance", "Fintech"],
    affectedPersonas: ["Embedded Finance Partnerships Lead", "General Counsel", "CFO", "COO"],
    linkedKPIs: ["FT-K025", "FT-K026", "FT-K027"],
    linkedValueDrivers: ["FT-VD017", "FT-VD018"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "FT-P010",
    name: "Stablecoin Reserve Management and Redemption Run Risk",
    description: "Inadequate liquidity buffers, non-transparent reserve composition, and redemption surge capacity creating systemic stability and regulatory compliance risks.",
    symptoms: [
      "Reserve attestation lag >30 days",
      "Liquid Treasuries <80% of reserves",
      "Redemption processing capacity <10% of supply daily",
      "De-peg event >50bps lasting >1 hour",
      "No independent custodian for reserves"
    ],
    affectedSegments: ["Stablecoin Infrastructure", "Fintech", "Crypto/Digital Assets"],
    affectedPersonas: ["Crypto Compliance Officer", "CFO", "Treasurer", "Risk Manager"],
    linkedKPIs: ["FT-K028", "FT-K029", "FT-K030"],
    linkedValueDrivers: ["FT-VD019", "FT-VD020"],
    prevalence: "MEDIUM",
    confidence: "MEDIUM"
  }
];

// ============================================================================
// VALUE FORMULAS (Sample - first 5 of 15)
// ============================================================================

export const FINTECH_FORMULAS: FintechValueFormula[] = [
  {
    id: "FT-VF001",
    name: "Payment Authorization Value Uplift",
    formulaExpression: "(False_Decline_Rate_Reduction * Transaction_Volume) + (Latency_Improvement_Revenue * Conversion_Uplift)",
    requiredInputs: ["False_Decline_Rate_Reduction", "Transaction_Volume", "Latency_Improvement_Revenue", "Conversion_Uplift"],
    outputUnit: "USD per year",
    applicableSegments: ["Payments", "Fintech"],
    confidenceRules: "HIGH with authorization logs; MEDIUM with processor benchmark; LOW for new payment types",
    exampleCalculation: "(0.10 * $5B) + ($15M * 0.05) = $500M + $0.75M = $500.75M annual revenue recovery"
  },
  {
    id: "FT-VF002",
    name: "KYC Onboarding Efficiency Value",
    formulaExpression: "(Manual_Review_Reduction * Cost_Per_Manual_Review) + (Completion_Rate_Uplift * Starts * CLV) + (Time_To_First_Transaction_Reduction_Value)",
    requiredInputs: ["Manual_Review_Reduction", "Cost_Per_Manual_Review", "Completion_Rate_Uplift", "Starts", "CLV", "Time_To_First_Transaction_Reduction_Value"],
    outputUnit: "USD per year",
    applicableSegments: ["Fintech", "Payments", "Crypto/Digital Assets"],
    confidenceRules: "HIGH with funnel data; MEDIUM using industry benchmark; LOW for new geographies",
    exampleCalculation: "(500,000 * $12) + (0.15 * 2M * $850) + $5M = $6M + $255M + $5M = $266M annual value"
  },
  {
    id: "FT-VF004",
    name: "BNPL Credit Loss Reduction",
    formulaExpression: "(Net_Loss_Rate_Reduction * Avg_Receivables) + (Collection_Cost_Reduction) + (Funding_Spread_Reduction * Borrowed_Amount)",
    requiredInputs: ["Net_Loss_Rate_Reduction", "Avg_Receivables", "Collection_Cost_Reduction", "Funding_Spread_Reduction", "Borrowed_Amount"],
    outputUnit: "USD per year",
    applicableSegments: ["BNPL"],
    confidenceRules: "HIGH with 24+ month vintage; MEDIUM with 12-month vintage; LOW in growth phase",
    exampleCalculation: "(0.03 * $2B) + $12M + (0.005 * $1.5B) = $60M + $12M + $7.5M = $79.5M annual value"
  },
  {
    id: "FT-VF006",
    name: "Crypto Custody Security Value",
    formulaExpression: "(Breach_Probability_Reduction * AUC * Loss_Rate) + (Insurance_Premium_Reduction) + (Regulatory_Penalty_Avoidance) + (Customer_Attraction_Value)",
    requiredInputs: ["Breach_Probability_Reduction", "AUC", "Loss_Rate", "Insurance_Premium_Reduction", "Regulatory_Penalty_Avoidance", "Customer_Attraction_Value"],
    outputUnit: "USD per year",
    applicableSegments: ["Crypto/Digital Assets"],
    confidenceRules: "HIGH with incident history; MEDIUM using security benchmark; LOW for new custody operations",
    exampleCalculation: "(0.05 * $500M * 0.30) + $3M + $10M + $5M = $7.5M + $3M + $10M + $5M = $25.5M annual value"
  },
  {
    id: "FT-VF009",
    name: "BaaS Sponsor Bank Diversification Value",
    formulaExpression: "(Concentration_Risk_Premium_Reduction * Deposit_Base) + (Partner_Termination_Avoidance_Value) + (Compliance_Cost_Reduction)",
    requiredInputs: ["Concentration_Risk_Premium_Reduction", "Deposit_Base", "Partner_Termination_Avoidance_Value", "Compliance_Cost_Reduction"],
    outputUnit: "USD per year",
    applicableSegments: ["BaaS", "Embedded Finance"],
    confidenceRules: "HIGH with deposit data; MEDIUM using risk premium benchmark; LOW for single-bank models",
    exampleCalculation: "(0.0025 * $5B) + $50M + $8M = $12.5M + $50M + $8M = $70.5M annual value"
  }
];

// ============================================================================
// SIGNAL INTERPRETER FUNCTION
// ============================================================================

/**
 * Evaluates a raw signal against the Fintech signal rule registry.
 * Returns interpretation results with confidence scoring and recommended actions.
 */
export function interpretFintechSignal(
  signalName: string,
  rawValue: number,
  context: Record<string, any>
): SignalInterpretationResult {
  const rule = FINTECH_SIGNAL_RULES.find(r => r.signalName === signalName);

  if (!rule) {
    return {
      ruleId: "UNKNOWN",
      triggered: false,
      confidence: 0,
      linkedPain: null,
      linkedKPIs: [],
      recommendedAction: "No matching signal rule found. Register new rule or escalate to master pack.",
      financialImpactEstimate: "UNKNOWN"
    };
  }

  // Simple threshold-based trigger logic (production would use more sophisticated evaluation)
  const triggered = rawValue > 0.7; // Example threshold
  const confidence = triggered ? rule.confidenceScore : rule.confidenceScore * 0.5;

  const linkedPain = triggered ? FINTECH_PAINS.find(p => p.id === rule.linkedPains[0]) || null : null;
  const linkedKPIs = FINTECH_KPIS.filter(k => rule.linkedKPIs.includes(k.id));

  let recommendedAction = "Monitor signal and collect confirmation data.";
  let financialImpactEstimate = "To be calculated upon confirmation.";

  if (triggered && confidence > 0.8) {
    recommendedAction = `URGENT: Investigate ${rule.signalName}. Confirm with: ${rule.requiredConfirmationSignals.join(", ")}. Escalate to affected personas: ${linkedPain?.affectedPersonas.join(", ") || "N/A"}.`;
    financialImpactEstimate = `HIGH confidence signal. Potential annual impact in range: ${linkedPain?.linkedValueDrivers.map(vd => vd).join(", ") || "TBD"}`;
  } else if (triggered && confidence > 0.6) {
    recommendedAction = `MEDIUM priority: Validate ${rule.signalName} with confirmation signals within 48 hours.`;
    financialImpactEstimate = "MEDIUM confidence. Requires additional evidence for value quantification.";
  }

  return {
    ruleId: rule.id,
    triggered,
    confidence,
    linkedPain,
    linkedKPIs,
    recommendedAction,
    financialImpactEstimate
  };
}

// ============================================================================
// USAGE EXAMPLES
// ============================================================================

// Example 1: Payment authorization latency spike
const paymentLatencySignal = interpretFintechSignal(
  "Payment Authorization Latency Spike",
  0.92, // High confidence trigger
  { p99Latency: 650, threshold: 500, consecutiveDays: 5 }
);
console.log("Payment Latency Signal:", paymentLatencySignal);

// Example 2: BNPL vintage deterioration
const bnplVintageSignal = interpretFintechSignal(
  "BNPL Vintage Deterioration",
  0.95,
  { delinquencyIncrease: 0.32, vintageMonth: 6 }
);
console.log("BNPL Vintage Signal:", bnplVintageSignal);

// Example 3: Stablecoin de-peg event
const stablecoinDepegSignal = interpretFintechSignal(
  "Stablecoin De-peg Event",
  0.88,
  { depegBps: 65, durationMinutes: 90, volumeSurge: 2.5 }
);
console.log("Stablecoin De-peg Signal:", stablecoinDepegSignal);

export { FintechSignalRule, FintechKPI, FintechPain, FintechValueFormula, SignalInterpretationResult };
