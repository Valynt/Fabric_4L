/**
 * Insurance Vertical Subpack - Signal Examples (TypeScript)
 * 
 * Subpack ID: insurance-v1
 * Parent Master: financial-services-master-v1
 * 
 * These examples demonstrate concrete signal interpretation, persona matching,
 * and value calculation patterns for the Insurance vertical.
 */

// ============================================================================
// TYPE DEFINITIONS (Vertical-Specialized)
// ============================================================================

interface InsuranceSignal {
  id: string;
  signalSource: string;
  rawData: unknown;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  verticalInterpretation: string;
  financialImplication: string;
  linkedPersonas: InsurancePersonaId[];
  linkedPains: InsurancePainId[];
  linkedKPIs: InsuranceKPIId[];
  recommendedAction: string;
}

type InsurancePersonaId =
  | "IPER001" // Chief Underwriting Officer
  | "IPER002" // Chief Claims Officer
  | "IPER003" // Head of Reinsurance / CRO
  | "IPER004" // Loss Control Engineer
  | "IPER005" // Policy Admin Systems Manager
  | "IPER006" // Actuarial Director
  | "PER001" | "PER002" | "PER003" | "PER004" | "PER005"; // Master personas

type InsurancePainId =
  | "IP001" | "IP002" | "IP003" | "IP004" | "IP005"
  | "IP006" | "IP007" | "IP008" | "IP009" | "IP010"
  | "IP011" | "IP012" | "IP013" | "IP014" | "IP015"
  | "IP016" | "IP017" | "IP018"
  | "P006" | "P007" | "P010" | "P011" | "P017" | "P019" | "P021" | "P022" | "P023"; // Master pains

type InsuranceKPIId =
  | "IK001" | "IK002" | "IK003" | "IK004" | "IK005" | "IK006"
  | "IK007" | "IK008" | "IK009" | "IK010" | "IK011" | "IK012"
  | "IK013" | "IK014" | "IK015" | "IK016" | "IK017" | "IK018"
  | "IK019" | "IK020" | "IK021" | "IK022" | "IK023" | "IK024"
  | "IK025" | "IK026" | "IK027" | "IK028" | "IK029" | "IK030"
  | "IK031" | "IK032" | "IK033" | "IK034" | "IK035" | "IK036"
  | "IK037" | "IK038" | "IK039" | "IK040" | "IK041" | "IK042"
  | "IK043" | "IK044" | "IK045" | "IK046" | "IK047" | "IK048"
  | "IK049" | "IK050" | "IK051" | "IK052" | "IK053" | "IK054"
  | "K018" | "K019" | "K020" | "K021" | "K022" | "K023"; // Master KPIs

interface ValueCalculationInputs {
  annualIncurredLosses: number;
  leakageRate: number;
  targetReductionPercent: number;
  implementationRiskFactor: number; // 0-1
}

interface ReinsuranceOptimizationInputs {
  grossWrittenPremium: number;
  currentCededPercent: number;
  targetCededPercent: number;
  restructuringCost: number;
}

// ============================================================================
// SIGNAL INTERPRETATION EXAMPLES
// ============================================================================

/**
 * Example 1: Interpreting an A.M. Best downgrade signal for insurance
 * Source: A.M. Best rating action with negative outlook
 * Confidence: HIGH (public, verified regulatory data)
 */
export const interpretRatingDowngradeSignal = (
  ratingAction: {
    carrierName: string;
    oldRating: string;
    newRating: string;
    outlook: "stable" | "negative" | "positive";
    reasonCodes: string[];
  }
): InsuranceSignal => {
  const hasOperatingPerformanceMention = ratingAction.reasonCodes.some((r) =>
    /operating performance|underwriting|combined ratio|reserve adequacy/i.test(r)
  );

  const confidence: InsuranceSignal["confidence"] = hasOperatingPerformanceMention
    ? "HIGH"
    : "MEDIUM";

  return {
    id: `ISR002-${ratingAction.carrierName}`,
    signalSource: "A.M. Best Rating Actions",
    rawData: ratingAction,
    confidence,
    verticalInterpretation:
      `Rating downgrade from ${ratingAction.oldRating} to ${ratingAction.newRating} with ` +
      `${ratingAction.outlook} outlook. ${hasOperatingPerformanceMention
        ? "Operating performance cited as driver -- combined ratio and claims technology investments prioritized."
        : "Capital or business profile concerns -- capital efficiency technology relevant."
      }`,
    financialImplication:
      "Reinsurance cost increase 10-30%; competitive positioning erosion; recovery technology urgency HIGH.",
    linkedPersonas: ["IPER003", "IPER002", "IPER001"],
    linkedPains: ["P007", "IP014", "IP003"],
    linkedKPIs: ["K019", "K020", "IK040", "IK007"],
    recommendedAction:
      "Quantify technology ROI in combined ratio improvement, RBC protection, and reinsurance cost reduction terms.",
  };
};

/**
 * Example 2: Interpreting NAIC financial data for RBC stress
 * Source: NAIC Financial Statement Database
 * Confidence: HIGH (audited regulatory filing)
 */
export const interpretRBCStressSignal = (
  naicData: {
    carrierName: string;
    rbcRatioCurrent: number;
    rbcRatioPriorYear: number;
    rbcRatioTwoYearsAgo: number;
    surplus: number;
    reportingYear: number;
  }
): InsuranceSignal => {
  const declineYoY1 = naicData.rbcRatioPriorYear - naicData.rbcRatioCurrent;
  const declineYoY2 = naicData.rbcRatioTwoYearsAgo - naicData.rbcRatioPriorYear;
  const twoYearDecline = declineYoY1 > 50 && declineYoY2 > 50;
  const nearActionLevel = naicData.rbcRatioCurrent < 250;

  return {
    id: `ISR001-${naicData.carrierName}`,
    signalSource: "NAIC Financial Statement Database",
    rawData: naicData,
    confidence: twoYearDecline ? "HIGH" : "MEDIUM",
    verticalInterpretation:
      `RBC ratio ${naicData.rbcRatioCurrent}% (declined ${declineYoY1} bps YoY). ` +
      `${twoYearDecline ? "Two-year declining trend confirmed. " : ""}` +
      `${nearActionLevel
        ? "Approaching company action level (200%). Capital event risk."
        : "Monitoring required but above action level."
      }`,
    financialImplication:
      nearActionLevel
        ? `Capital raising cost $${(naicData.surplus * 0.1 / 1e6).toFixed(0)}M-$${(naicData.surplus * 0.5 / 1e6).toFixed(0)}M or business restriction. Technology ROI must show RBC protection.`
        : "Technology investment framing should include capital efficiency and RBC sensitivity.",
    linkedPersonas: ["IPER003", "IPER006"],
    linkedPains: ["IP014", "IP017"],
    linkedKPIs: ["IK040", "IK041", "IK049"],
    recommendedAction:
      "Frame technology investment as capital efficiency project with explicit RBC improvement modeling using IVF010.",
  };
};

/**
 * Example 3: Interpreting reinsurance market data
 * Source: Reinsurance broker market reports or treaty renewal results
 * Confidence: HIGH (contractual, verifiable)
 */
export const interpretReinsuranceCostSignal = (
  treatyData: {
    carrierName: string;
    lineOfBusiness: string;
    priorCededPercent: number;
    newCededPercent: number;
    gwp: number;
    coverageChange: "expanded" | "compressed" | "stable";
  }
): InsuranceSignal => {
  const costIncrease = treatyData.newCededPercent - treatyData.priorCededPercent;
  const costIncreasePercent = (costIncrease / treatyData.priorCededPercent) * 100;
  const isSevere = costIncreasePercent > 25;

  return {
    id: `ISR010-${treatyData.carrierName}`,
    signalSource: "Reinsurance Treaty Renewal Data",
    rawData: treatyData,
    confidence: "HIGH",
    verticalInterpretation:
      `Ceded premium ratio increased from ${treatyData.priorCededPercent}% to ${treatyData.newCededPercent}% ` +
      `(${costIncreasePercent.toFixed(1)}% increase). Coverage ${treatyData.coverageChange}. ` +
      `${isSevere ? "Severe cost escalation -- reinsurance optimization technology urgent." : "Moderate increase -- monitoring warranted."}`,
    financialImplication:
      `Ceded premium increase $${(treatyData.gwp * costIncrease / 100 / 1e6).toFixed(1)}M annually. ` +
      "Modeling tech ROI directly in basis points of ceded rate.",
    linkedPersonas: ["IPER003", "IPER001"],
    linkedPains: ["IP003", "IP007"],
    linkedKPIs: ["IK007", "IK008", "IK009"],
    recommendedAction:
      "Position exposure data quality and cat modeling as directly reducing ceded premium basis points. Use IVF003.",
  };
};

/**
 * Example 4: Interpreting J.D. Power digital experience decline
 * Source: J.D. Power Insurance Digital Experience Study
 * Confidence: HIGH (published, audited research)
 */
export const interpretDigitalDissatisfactionSignal = (
  digitalData: {
    carrierName: string;
    digitalExperienceScore: number;
    categoryAverage: number;
    priorYearScore: number;
    appStoreRating: number; // 1-5
    callCenterVolumeGrowth: number; // percentage
  }
): InsuranceSignal => {
  const belowAverage = digitalData.digitalExperienceScore < digitalData.categoryAverage;
  const declining = digitalData.digitalExperienceScore < digitalData.priorYearScore;
  const lowAppRating = digitalData.appStoreRating < 3.5;

  return {
    id: `ISR009-${digitalData.carrierName}`,
    signalSource: "J.D. Power Digital Experience Study",
    rawData: digitalData,
    confidence: belowAverage && declining ? "HIGH" : "MEDIUM",
    verticalInterpretation:
      `Digital experience score ${digitalData.digitalExperienceScore} ` +
      `${belowAverage ? `(below category avg ${digitalData.categoryAverage}) ` : ""}` +
      `${declining ? `(down from ${digitalData.priorYearScore}) ` : ""}` +
      `${lowAppRating ? `App rating ${digitalData.appStoreRating}/5. ` : ""}` +
      `Call center volume growing ${digitalData.callCenterVolumeGrowth}% -- self-service deflection failing.`,
    financialImplication:
      `Retention risk 5-10%; call center cost inflation 15-25%; digital platform ROI justified.`,
    linkedPersonas: ["IPER005", "PER002"],
    linkedPains: ["IP013"],
    linkedKPIs: ["IK037", "IK038", "IK039"],
    recommendedAction:
      "Quantify agent productivity improvement and retention value from portal modernization using IVF008 or IVF015.",
  };
};

/**
 * Example 5: Interpreting catastrophe event data
 * Source: NOAA / Cat loss reporting
 * Confidence: HIGH (observable, measurable)
 */
export const interpretCatastropheEventSignal = (
  catData: {
    carrierName: string;
    eventName: string;
    catLossAmount: number;
    surplus: number;
    modeledLoss: number;
    geocodingAccuracy: number;
  }
): InsuranceSignal => {
  const lossToSurplus = (catData.catLossAmount / catData.surplus) * 100;
  const modelVariance =
    (Math.abs(catData.modeledLoss - catData.catLossAmount) / catData.catLossAmount) * 100;
  const severeEvent = lossToSurplus > 30;
  const poorModeling = modelVariance > 40;

  return {
    id: `ISR012-${catData.carrierName}-${catData.eventName}`,
    signalSource: "NOAA/Catastrophe Loss Data",
    rawData: catData,
    confidence: "HIGH",
    verticalInterpretation:
      `${catData.eventName} loss $${(catData.catLossAmount / 1e6).toFixed(0)}M ` +
      `(${lossToSurplus.toFixed(1)}% of surplus). ` +
      `${severeEvent ? "Severe surplus impact. " : ""}` +
      `Modeled loss $${(catData.modeledLoss / 1e6).toFixed(0)}M ` +
      `(variance ${modelVariance.toFixed(1)}%). ` +
      `${poorModeling ? "Model accuracy failure confirmed." : "Model within acceptable range."} ` +
      `Geocoding accuracy ${catData.geocodingAccuracy}%`,
    financialImplication:
      severeEvent && poorModeling
        ? "Surplus impairment; rating downgrade risk; reinsurance renewal crisis; capital event."
        : "Reserve strengthening needed; exposure data improvement warranted.",
    linkedPersonas: ["IPER003", "IPER006", "IPER001"],
    linkedPains: ["IP007", "IP014"],
    linkedKPIs: ["IK019", "IK020", "IK021", "IK040"],
    recommendedAction:
      "Present real-time exposure management and secondary peril modeling as direct surplus protection. Use IVF007.",
  };
};

// ============================================================================
// PERSONA DETECTION AND MATCHING
// ============================================================================

interface PersonaMatchResult {
  personaId: InsurancePersonaId;
  matchScore: number; // 0-1
  evidence: string[];
  recommendedDiscoveryQuestions: string[];
}

/**
 * Detect the most relevant insurance personas based on signal data
 */
export const detectInsurancePersonas = (
  signals: InsuranceSignal[]
): PersonaMatchResult[] => {
  const personaScores: Record<string, { score: number; evidence: string[] }> = {
    IPER001: { score: 0, evidence: [] },
    IPER002: { score: 0, evidence: [] },
    IPER003: { score: 0, evidence: [] },
    IPER004: { score: 0, evidence: [] },
    IPER005: { score: 0, evidence: [] },
    IPER006: { score: 0, evidence: [] },
  };

  for (const signal of signals) {
    for (const personaId of signal.linkedPersonas) {
      if (personaScores[personaId]) {
        personaScores[personaId].score +=
          signal.confidence === "HIGH" ? 0.35 : signal.confidence === "MEDIUM" ? 0.2 : 0.1;
        personaScores[personaId].evidence.push(signal.id);
      }
    }
  }

  // Normalize scores to 0-1
  const maxScore = Math.max(...Object.values(personaScores).map((p) => p.score), 1);

  return Object.entries(personaScores)
    .filter(([, data]) => data.score > 0)
    .map(([personaId, data]) => ({
      personaId: personaId as InsurancePersonaId,
      matchScore: Math.min(data.score / maxScore, 1),
      evidence: data.evidence,
      recommendedDiscoveryQuestions: getDiscoveryQuestionsForPersona(personaId as InsurancePersonaId),
    }))
    .sort((a, b) => b.matchScore - a.matchScore);
};

const getDiscoveryQuestionsForPersona = (personaId: InsurancePersonaId): string[] => {
  const questionMap: Record<string, string[]> = {
    IPER001: ["IDQ001", "IDQ004", "IDQ005", "IDQ008", "IDQ015", "IDQ016", "IDQ017"],
    IPER002: ["IDQ002", "IDQ003", "IDQ007", "IDQ011"],
    IPER003: ["IDQ004", "IDQ014", "IDQ016"],
    IPER004: ["IDQ011"],
    IPER005: ["IDQ001", "IDQ009", "IDQ010", "IDQ013", "IDQ015"],
    IPER006: ["IDQ005", "IDQ008", "IDQ012", "IDQ014", "IDQ018"],
  };
  return questionMap[personaId] || [];
};

// ============================================================================
// VALUE CALCULATION EXAMPLES
// ============================================================================

/**
 * Example: Calculate claims leakage cost avoidance (IVF001)
 * Confidence: HIGH if leakage rate documented by external audit
 */
export const calculateClaimsLeakageValue = (
  inputs: ValueCalculationInputs
): {
  annualValue: number;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  rationale: string;
} => {
  const {
    annualIncurredLosses,
    leakageRate,
    targetReductionPercent,
    implementationRiskFactor,
  } = inputs;

  const leakageAmount = annualIncurredLosses * (leakageRate / 100);
  const potentialSavings = leakageAmount * (targetReductionPercent / 100);
  const riskAdjustedSavings = potentialSavings * (1 - implementationRiskFactor);

  // Determine confidence based on data quality
  let confidence: "HIGH" | "MEDIUM" | "LOW" = "LOW";
  let rationale = "Leakage rate based on industry benchmark only.";

  if (inputs.leakageRate < 0.15 && inputs.targetReductionPercent > 0.3) {
    confidence = "HIGH";
    rationale = "Leakage rate documented by external audit with historical validation.";
  } else if (inputs.leakageRate < 0.25) {
    confidence = "MEDIUM";
    rationale = "Leakage rate estimated by internal audit with segment-specific data.";
  }

  return {
    annualValue: riskAdjustedSavings,
    confidence,
    rationale,
  };
};

/**
 * Example: Calculate reinsurance cost optimization (IVF003)
 * Confidence: HIGH if broker validated program structure
 */
export const calculateReinsuranceOptimizationValue = (
  inputs: ReinsuranceOptimizationInputs
): {
  annualSavings: number;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  rationale: string;
} => {
  const { grossWrittenPremium, currentCededPercent, targetCededPercent, restructuringCost } =
    inputs;

  const currentCeded = grossWrittenPremium * (currentCededPercent / 100);
  const targetCeded = grossWrittenPremium * (targetCededPercent / 100);
  const annualSavings = currentCeded - targetCeded - restructuringCost;

  let confidence: "HIGH" | "MEDIUM" | "LOW" = "LOW";
  let rationale = "Industry ceded rate benchmark applied without carrier-specific validation.";

  if (targetCededPercent < currentCededPercent * 0.8 && restructuringCost < annualSavings * 0.3) {
    confidence = "HIGH";
    rationale = "Reinsurance broker validated program structure with market pricing support.";
  } else if (targetCededPercent < currentCededPercent) {
    confidence = "MEDIUM";
    rationale = "Internal actuarial model used with peer program benchmarking.";
  }

  return {
    annualSavings,
    confidence,
    rationale,
  };
};

/**
 * Example: Calculate RBC protection value (IVF010)
 * This demonstrates how technology ROI can be framed in capital terms
 */
export const calculateRBCProtectionValue = (inputs: {
  currentRBC: number;
  targetRBC: number;
  surplus: number;
  externalCapitalCost: number; // e.g., 0.12 for 12%
  internalCost: number; // e.g., 0.06 for 6%
}): {
  valueOfRBCImprovement: number;
  capitalAvoidanceValue: number;
  totalValue: number;
} => {
  const rbcImprovement = inputs.targetRBC - inputs.currentRBC;
  const rbcImprovementFactor = rbcImprovement / 100;

  // Value of improved capital position
  const valueOfRBCImprovement = rbcImprovementFactor * inputs.surplus;

  // Avoided cost of raising external capital
  const capitalAvoidanceValue =
    rbcImprovementFactor * inputs.surplus * (inputs.externalCapitalCost - inputs.internalCost);

  return {
    valueOfRBCImprovement,
    capitalAvoidanceValue,
    totalValue: valueOfRBCImprovement + capitalAvoidanceValue,
  };
};

// ============================================================================
// DISCOVERY QUESTION GENERATOR
// ============================================================================

interface GeneratedDiscoveryQuestion {
  questionId: string;
  questionText: string;
  targetPersona: InsurancePersonaId;
  expectedDataType: "percentage" | "dollar" | "days" | "count" | "ratio";
  linkedValueFormula: string;
}

/**
 * Generate discovery questions based on detected signals
 */
export const generateDiscoveryQuestions = (
  signals: InsuranceSignal[]
): GeneratedDiscoveryQuestion[] => {
  const questions: GeneratedDiscoveryQuestion[] = [];

  for (const signal of signals) {
    // Map signals to specific discovery questions
    if (signal.linkedPains.includes("IP002")) {
      questions.push({
        questionId: "IDQ002-GENERATED",
        questionText:
          "In your claims organization, what percentage of incurred losses would you attribute to leakage, and what is your average loss adjustment expense ratio by line?",
        targetPersona: "IPER002",
        expectedDataType: "percentage",
        linkedValueFormula: "IVF001",
      });
    }

    if (signal.linkedPains.includes("IP003")) {
      questions.push({
        questionId: "IDQ004-GENERATED",
        questionText:
          "What is your current combined ratio by major line of business, and what are the top three drivers preventing you from reaching your target?",
        targetPersona: "IPER001",
        expectedDataType: "ratio",
        linkedValueFormula: "IVF003",
      });
    }

    if (signal.linkedPains.includes("IP014")) {
      questions.push({
        questionId: "IDQ014-GENERATED",
        questionText:
          "What is your current RBC ratio and surplus trend? What percentage of your surplus is exposed to unrealized losses?",
        targetPersona: "IPER003",
        expectedDataType: "percentage",
        linkedValueFormula: "IVF010",
      });
    }

    if (signal.linkedPains.includes("IP007")) {
      questions.push({
        questionId: "IDQ008-GENERATED",
        questionText:
          "How accurate was your catastrophe model last year versus actuals? What percentage of your property book is accurately geocoded?",
        targetPersona: "IPER003",
        expectedDataType: "percentage",
        linkedValueFormula: "IVF007",
      });
    }
  }

  return questions;
};

// ============================================================================
// COMPETITIVE RESPONSE PATTERN
// ============================================================================

interface CompetitiveThreatResponse {
  competitorFactorId: string;
  threatDescription: string;
  recommendedPositioning: string;
  urgencyLevel: "critical" | "high" | "medium" | "low";
  linkedTechnologySystems: string[];
}

export const competitiveThreatResponses: CompetitiveThreatResponse[] = [
  {
    competitorFactorId: "ICF001",
    threatDescription: "Tesla, Amazon, Ford embedding insurance at point of sale",
    recommendedPositioning:
      "Position API-first PAS and embedded distribution platform as competitive response. Quantify speed-to-market advantage.",
    urgencyLevel: "high",
    linkedTechnologySystems: ["ITS001", "ITS004", "ITS007"],
  },
  {
    competitorFactorId: "ICF002",
    threatDescription: "Root, Lemonade, Progressive scaling UBI with telematics",
    recommendedPositioning:
      "Position telematics integration and dynamic rating engine as must-have competitive capability. Quantify displacement risk.",
    urgencyLevel: "critical",
    linkedTechnologySystems: ["ITS004", "ITS009"],
  },
  {
    competitorFactorId: "ICF006",
    threatDescription: "Tractable, Snapsheet, CCC scaling AI claims triage",
    recommendedPositioning:
      "Position AI-assisted claims triage as customer expectation baseline, not differentiator. Quantify LAE compression.",
    urgencyLevel: "high",
    linkedTechnologySystems: ["ITS002", "ITS006"],
  },
];

// ============================================================================
// EXAMPLE USAGE WORKFLOW
// ============================================================================

/**
 * Complete workflow example:
 * 1. Detect signals from multiple sources
 * 2. Match to personas
 * 3. Generate discovery questions
 * 4. Calculate value when data available
 */
export const exampleWorkflow = (): void => {
  // Step 1: Detect signals
  const signals: InsuranceSignal[] = [
    interpretRatingDowngradeSignal({
      carrierName: "Example Mutual Insurance",
      oldRating: "A",
      newRating: "A-",
      outlook: "negative",
      reasonCodes: ["operating performance", "reserve adequacy"],
    }),
    interpretRBCStressSignal({
      carrierName: "Example Mutual Insurance",
      rbcRatioCurrent: 245,
      rbcRatioPriorYear: 310,
      rbcRatioTwoYearsAgo: 365,
      surplus: 500_000_000,
      reportingYear: 2025,
    }),
  ];

  // Step 2: Match personas
  const personaMatches = detectInsurancePersonas(signals);
  console.log("Top persona match:", personaMatches[0]);

  // Step 3: Generate discovery questions
  const questions = generateDiscoveryQuestions(signals);
  console.log("Generated questions:", questions);

  // Step 4: Calculate value (when customer data available)
  const leakageValue = calculateClaimsLeakageValue({
    annualIncurredLosses: 200_000_000,
    leakageRate: 8,
    targetReductionPercent: 25,
    implementationRiskFactor: 0.2,
  });
  console.log("Claims leakage value:", leakageValue);

  const reinsuranceValue = calculateReinsuranceOptimizationValue({
    grossWrittenPremium: 800_000_000,
    currentCededPercent: 28,
    targetCededPercent: 22,
    restructuringCost: 5_000_000,
  });
  console.log("Reinsurance optimization value:", reinsuranceValue);
};
