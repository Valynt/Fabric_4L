/**
 * Advanced Manufacturing Subpack — Signal-to-Value TypeScript Examples
 * 
 * These examples demonstrate how to use the Advanced Manufacturing signal rules,
 * persona profiles, KPIs, pains, and value formulas in code to:
 *  1. Interpret raw market/operational signals into structured hypotheses
 *  2. Map signals to vertical pains, KPIs, and personas
 *  3. Quantify value using vertical formulas with customer-specific inputs
 *  4. Generate discovery question sequences for sales/advisory engagements
 * 
 * ID: advanced-manufacturing-v1
 * Parent: manufacturing-master-v1
 */

// =============================================================================
// 1. TYPE DEFINITIONS (from Master Pack + Subpack)
// =============================================================================

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
  affectedPersonas: string[];
  linkedKPIs: string[];
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

interface ValueFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  exampleCalculation: string;
  confidenceRules: Array<{ condition: string; confidence: number }>;
}

interface ValueHypothesis {
  signalId: string;
  signalName: string;
  confidence: number;
  linkedPains: BusinessPain[];
  linkedKPIs: KPIDefinition[];
  affectedPersonas: PersonaProfile[];
  estimatedValueRange?: { low: number; high: number; unit: string };
  discoveryQuestions: string[];
  recommendedFormula?: ValueFormula;
}

// =============================================================================
// 2. SAMPLE DATA — Advanced Manufacturing Signal Rules (Subset)
// =============================================================================

const ADVANCED_SIGNAL_RULES: SignalInterpretationRule[] = [
  {
    id: "adv-sig-001",
    signalName: "EUV resist supplier diversification",
    rawSignalPattern: "Multiple job postings for EUV resist chemists; new supplier qualification announcements; patent filings in EUV resist chemistry",
    interpretedMeaning: "Primary EUV resist supplier facing yield/availability constraints; customer seeking supply chain resilience at advanced nodes",
    linkedPains: ["adv-pain-001", "adv-pain-016"],
    linkedKPIs: ["adv-kpi-wafer-yield", "adv-kpi-defect-density"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: ["TSMC/Samsung capacity expansion at N3+", "ASML backlog data"]
  },
  {
    id: "adv-sig-002",
    signalName: "Battery gigafactory expansion pause",
    rawSignalPattern: "Construction halt announcements; capex guidance reduction; hiring freeze in cell manufacturing; equipment order cancellations",
    interpretedMeaning: "Overcapacity in Li-ion cells or funding constraints; customer may pivot to process efficiency/cost reduction rather than greenfield expansion",
    linkedPains: ["adv-pain-002", "adv-pain-007"],
    linkedKPIs: ["adv-kpi-formation-ct", "adv-kpi-chamber-util", "adv-kpi-cell-yield"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: ["Commodity price trends (lithium, nickel)", "EV demand forecasts"]
  },
  {
    id: "adv-sig-005",
    signalName: "APC/FDC vendor evaluation or replacement",
    rawSignalPattern: "RFP for advanced process control; POC announcements with ML/AI vendors; FDC-related conference presentations",
    interpretedMeaning: "Legacy rule-based FDC inadequate; customer seeking ML-enhanced fault detection with lower false alarm rates",
    linkedPains: ["adv-pain-005"],
    linkedKPIs: ["adv-kpi-fdc-false-alarm", "adv-kpi-excursion-containment", "adv-kpi-r2r-adoption"],
    confidenceScore: 0.84,
    requiredConfirmationSignals: ["Yield stagnation at mature nodes", "CIO/CTO from semiconductor background"]
  },
  {
    id: "adv-sig-008",
    signalName: "Digital twin platform vendor selection",
    rawSignalPattern: "Siemens/Dassault/AVEVA digital twin POC announcements; smart factory/digital thread strategy documents; Industry 4.0 architect hires",
    interpretedMeaning: "Customer building connected factory infrastructure; digital twin accuracy and IIoT integration are likely pain points",
    linkedPains: ["adv-pain-008", "adv-pain-014", "adv-pain-018"],
    linkedKPIs: ["adv-kpi-twin-accuracy", "adv-kpi-data-utilization"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: ["CIO change", "Digital transformation mandate in annual report"]
  },
  {
    id: "adv-sig-014",
    signalName: "OT cybersecurity incident or audit",
    rawSignalPattern: "CISA ICS advisory citing specific manufacturer; insurance premium increases for cyber; OT security vendor selections",
    interpretedMeaning: "Manufacturing OT security exposure recognized; zero-trust segmentation and anomaly detection needed",
    linkedPains: ["adv-pain-018"],
    linkedKPIs: ["adv-kpi-ot-segmentation", "adv-kpi-csf-level", "adv-kpi-anomaly-coverage"],
    confidenceScore: 0.90,
    requiredConfirmationSignals: ["Ransomware incident in peer company", "New CISO/OT security director hire"]
  }
];

const ADVANCED_PAINS: BusinessPain[] = [
  {
    id: "adv-pain-001",
    name: "Yield Fallout at 7nm and Below Nodes",
    description: "Critical yield degradation at advanced semiconductor nodes due to defect density, process variation, and equipment matching issues.",
    symptoms: ["Wafer yield <85% at N7/N5 nodes", "Defect density >0.1/cm²", "Equipment matching variation >2%", "Process window shrinking below 10%"],
    affectedPersonas: ["pers-fab-eng", "pers-coo", "pers-cfo", "pers-metrology"],
    linkedKPIs: ["adv-kpi-wafer-yield", "adv-kpi-defect-density", "adv-kpi-equip-matching"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "adv-pain-002",
    name: "Battery Cell Formation Cycle Time Variability",
    description: "Inconsistent formation and aging cycle times in lithium-ion battery manufacturing limiting throughput and causing capacity underutilization.",
    symptoms: ["Formation cycle time CV >15%", "Chamber utilization <75%", "Cell capacity spread >5% within batch", "Formation energy recovery <60%"],
    affectedPersonas: ["pers-batt-design", "pers-plant", "pers-coo", "pers-cfo"],
    linkedKPIs: ["adv-kpi-formation-ct", "adv-kpi-cell-yield", "adv-kpi-chamber-util"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "adv-pain-005",
    name: "FDC (Fault Detection and Classification) Alarm Fatigue",
    description: "Legacy APC/FDC systems generating excessive false-positive alarms leading to operator desensitization and suboptimal excursion containment.",
    symptoms: ["False alarm rate >80%", "Alarm response time >30 minutes", "Excursion containment >24 hours", "SPC rules manually overridden >20%"],
    affectedPersonas: ["pers-fab-eng", "pers-plant", "pers-ind4-arch", "pers-coo"],
    linkedKPIs: ["adv-kpi-fdc-false-alarm", "adv-kpi-excursion-containment", "adv-kpi-r2r-adoption"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "adv-pain-007",
    name: "Battery Electrode Coating Thickness Variation",
    description: "Inconsistent calendering and coating thickness in electrode manufacturing causing cell capacity mismatch and downstream yield loss.",
    symptoms: ["Coating thickness CV >5% across web", "Calendering gap variation >2µm", "Areal capacity spread >3% within batch", "Coating weight out-of-spec >2%"],
    affectedPersonas: ["pers-batt-design", "pers-quality", "pers-metrology", "pers-coo"],
    linkedKPIs: ["adv-kpi-coating-uniformity", "adv-kpi-calender-consistency"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "adv-pain-008",
    name: "Digital Twin Model Accuracy Drift",
    description: "Digital twin models drifting from physical reality due to uncalibrated parameters, unmodeled degradation, and lack of continuous validation.",
    symptoms: ["Digital twin prediction error >10% vs actual", "Model update frequency <weekly", "What-if scenario accuracy declining", "Operator trust in twin <50%"],
    affectedPersonas: ["pers-ind4-arch", "pers-cio", "pers-plant", "pers-coo"],
    linkedKPIs: ["adv-kpi-twin-accuracy", "adv-kpi-data-utilization"],
    prevalence: "MEDIUM",
    confidence: "MEDIUM"
  },
  {
    id: "adv-pain-014",
    name: "IIoT Data Overload Without Edge Analytics",
    description: "Smart factories generating petabytes of sensor data with insufficient edge computing/analytics infrastructure.",
    symptoms: ["Edge-to-cloud data volume >10TB/day", "Analytics latency >5 minutes", "Cloud storage cost growing >30% YoY", "<10% of data analyzed"],
    affectedPersonas: ["pers-ind4-arch", "pers-cio", "pers-coo", "pers-cfo"],
    linkedKPIs: ["adv-kpi-data-utilization", "adv-kpi-edge-latency", "adv-kpi-storage-cost"],
    prevalence: "HIGH",
    confidence: "HIGH"
  },
  {
    id: "adv-pain-018",
    name: "Industry 4.0 Cyber-Physical Security Exposure",
    description: "Expanded attack surface from connected OT/IT convergence creating ransomware, IP theft, and safety risks.",
    symptoms: ["OT networks without segmentation", "Legacy PLCs without patch capability", "No anomaly detection", "Remote access without zero-trust"],
    affectedPersonas: ["pers-ciso", "pers-ind4-arch", "pers-cio", "pers-coo"],
    linkedKPIs: ["adv-kpi-ot-segmentation", "adv-kpi-csf-level", "adv-kpi-anomaly-coverage"],
    prevalence: "HIGH",
    confidence: "HIGH"
  }
];

const ADVANCED_KPIS: KPIDefinition[] = [
  { id: "adv-kpi-wafer-yield", name: "Wafer Yield", formula: "Good Die / Total Die × 100", unit: "%", typicalRange: "75-98%", benchmarkRange: "N7: 85-92%" },
  { id: "adv-kpi-defect-density", name: "Defect Density (D0)", formula: "Random Defects / Area", unit: "defects/cm²", typicalRange: "0.05-1.0", benchmarkRange: "N7: <0.15" },
  { id: "adv-kpi-equip-matching", name: "Equipment Matching", formula: "3σ of Critical Param Across Tools", unit: "%", typicalRange: "1-5%", benchmarkRange: "<2%" },
  { id: "adv-kpi-formation-ct", name: "Formation Cycle Time", formula: "Avg Charge Start to Grading", unit: "hours", typicalRange: "72-240", benchmarkRange: "72-96 cyl" },
  { id: "adv-kpi-chamber-util", name: "Chamber Utilization", formula: "Actual / Available Hours", unit: "%", typicalRange: "60-85%", benchmarkRange: "80-90%" },
  { id: "adv-kpi-fdc-false-alarm", name: "FDC False Alarm Rate", formula: "False / Total Alarms", unit: "%", typicalRange: "30-85%", benchmarkRange: "<20%" },
  { id: "adv-kpi-excursion-containment", name: "Excursion Containment Time", formula: "Signal to Containment", unit: "hours", typicalRange: "2-72", benchmarkRange: "<4h" },
  { id: "adv-kpi-r2r-adoption", name: "R2R Control Coverage", formula: "Steps under R2R / Total", unit: "%", typicalRange: "20-80%", benchmarkRange: ">75%" },
  { id: "adv-kpi-coating-uniformity", name: "Coating Uniformity", formula: "3σ / Mean Thickness", unit: "% CV", typicalRange: "2-8%", benchmarkRange: "<3%" },
  { id: "adv-kpi-twin-accuracy", name: "Digital Twin Accuracy", formula: "(1 - |Pred - Actual|/Actual) × 100", unit: "%", typicalRange: "80-98%", benchmarkRange: ">95%" },
  { id: "adv-kpi-data-utilization", name: "Data Utilization Rate", formula: "Analyzed Data / Total Collected", unit: "%", typicalRange: "5-15%", benchmarkRange: ">50%" },
  { id: "adv-kpi-ot-segmentation", name: "OT Network Segmentation", formula: "Segmented Zones / Total Zones", unit: "%", typicalRange: "0-100%", benchmarkRange: "100%" }
];

const ADVANCED_PERSONAS: PersonaProfile[] = [
  {
    id: "pers-fab-eng",
    name: "Fab Process Engineer",
    role: "Senior Process Engineer / Module Owner",
    seniority: "Director/Manager/PE",
    goals: ["Maximize wafer yield at target node", "Minimize excursion containment time", "Reduce equipment matching variation"],
    pressures: ["Yield accountable to node targets", "24/7 on-call for excursion response", "Constant node migration learning curve"],
    trustedEvidence: ["SPIE/AVS proceedings", "SEMI standards", "OEM technical notes"],
    dislikedClaims: ["Black-box AI without physics grounding", "Vendor claims without peer review", "Solutions ignoring SEMI standards"],
    decisionInfluence: "technical"
  },
  {
    id: "pers-batt-design",
    name: "Battery Cell Designer",
    role: "Cell Design Engineer / Electrochemist",
    seniority: "Director/Manager/SrE",
    goals: ["Achieve energy density targets", "Design for manufacturing scalability", "Reduce formation time and cost"],
    pressures: ["Cost per kWh target pressure", "Safety requirements", "Fast charge performance demands"],
    trustedEvidence: ["Journal of Power Sources", "DOE/ARPA-E", "IDTechEx reports"],
    dislikedClaims: ["Unsubstantiated energy density", "Ignoring safety margins", "Unrealistic solid-state timelines"],
    decisionInfluence: "technical"
  },
  {
    id: "pers-ind4-arch",
    name: "Industry 4.0 Architect",
    role: "Smart Factory / Digital Transformation Lead",
    seniority: "Director/Principal",
    goals: ["Define digital transformation roadmap", "Integrate OT/IT systems", "Deploy AI/ML at edge and cloud"],
    pressures: ["Board/CEO expectations", "Legacy system integration", "Cybersecurity requirements", "Vendor consolidation tension"],
    trustedEvidence: ["Gartner/IDC reports", "WEF Lighthouse Network", "ISA-95, OPC UA"],
    dislikedClaims: ["Rip-and-replace", "Undifferentiated AI buzzwords", "Proprietary protocols", "ROI without baseline"],
    decisionInfluence: "technical"
  },
  {
    id: "pers-ciso",
    name: "CISO",
    role: "Chief Information Security Officer",
    seniority: "VP/Director",
    goals: ["Protect OT/IT infrastructure", "Ensure regulatory compliance", "Manage cyber risk"],
    pressures: ["Board-level security accountability", "OT security skills shortage", "Insurance premium pressure"],
    trustedEvidence: ["NIST SP 800-82", "CISA advisories", "ISA-62443", "Dragos reports"],
    dislikedClaims: ["IT security solutions repackaged for OT", "Unrealistic air-gap promises", "Compliance checkbox tools"],
    decisionInfluence: "technical"
  },
  {
    id: "pers-coo",
    name: "COO",
    role: "Chief Operating Officer / EVP Operations",
    seniority: "C-Suite",
    goals: ["Hit production targets", "Reduce unit cost", "Manage capex", "Ensure quality"],
    pressures: ["Board production commitments", "Margin pressure", "Customer delivery penalties", "Regulatory compliance"],
    trustedEvidence: ["Peer benchmarking", "Consulting firm studies", "10-K risk factors", "APQC data"],
    dislikedClaims: ["Unrealistic payback periods", "Solutions without operational validation", "ROI without scenario analysis"],
    decisionInfluence: "economic"
  },
  {
    id: "pers-cfo",
    name: "CFO",
    role: "Chief Financial Officer / VP Finance",
    seniority: "C-Suite",
    goals: ["Improve gross margin", "Optimize working capital", "Reduce operating costs", "Manage capex ROI"],
    pressures: ["Analyst earnings expectations", "Debt covenant compliance", "Audit and SOX requirements"],
    trustedEvidence: ["Industry benchmarks", "SEC filings", "APQC", "Credit ratings"],
    dislikedClaims: ["Soft ROI without NPV", "Savings without baseline validation", "Revenue uplift without absorption analysis"],
    decisionInfluence: "economic"
  }
];

const ADVANCED_FORMULAS: ValueFormula[] = [
  {
    id: "adv-form-001",
    name: "Semiconductor Yield Loss Cost",
    formulaExpression: "(BaselineYield - TargetYield) / 100 × AnnualWaferStarts × DiePerWafer × DieRevenue",
    requiredInputs: ["BaselineYield", "TargetYield", "AnnualWaferStarts", "DiePerWafer", "DieRevenue"],
    outputUnit: "$/year",
    exampleCalculation: "(88% - 92%) × 100,000 × 400 × $15 = $24M/year",
    confidenceRules: [
      { condition: "Customer provides actual wafer start data", confidence: 0.90 },
      { condition: "Using industry-average die per wafer", confidence: 0.65 }
    ]
  },
  {
    id: "adv-form-002",
    name: "Battery Formation Capacity Value",
    formulaExpression: "(BaselineCT - TargetCT) / BaselineCT × FormationChamberCount × ChamberCapacityGWh × ContributionMarginPerGWh",
    requiredInputs: ["BaselineCT", "TargetCT", "FormationChamberCount", "ChamberCapacityGWh", "ContributionMarginPerGWh"],
    outputUnit: "$/year",
    exampleCalculation: "(120h - 96h) / 120h × 200 × 0.05 × $35M = $70M/year",
    confidenceRules: [
      { condition: "Customer provides actual chamber count and CT distribution", confidence: 0.85 },
      { condition: "Using published gigafactory benchmarks", confidence: 0.60 }
    ]
  },
  {
    id: "adv-form-005",
    name: "FDC False Alarm Cost",
    formulaExpression: "AnnualFalseAlarms × (ToolStoppageMinutes × ToolThroughputValuePerMin + OperatorInvestigationMinutes × LoadedLaborRate)",
    requiredInputs: ["AnnualFalseAlarms", "ToolStoppageMinutes", "ToolThroughputValuePerMin", "OperatorInvestigationMinutes", "LoadedLaborRate"],
    outputUnit: "$/year",
    exampleCalculation: "2,000 × (15 × $200 + 30 × $1.50) = $6.1M/year",
    confidenceRules: [
      { condition: "Alarm log data available for classification", confidence: 0.85 },
      { condition: "Tool value per minute validated with customer", confidence: 0.75 }
    ]
  }
];

// =============================================================================
// 3. EXAMPLE 1 — Signal Interpretation Engine
// =============================================================================

/**
 * Interpret a raw signal using the Advanced Manufacturing signal rules.
 * Returns a structured hypothesis with confidence scoring.
 */
function interpretSignal(
  rawSignal: string,
  rules: SignalInterpretationRule[],
  pains: BusinessPain[],
  kpis: KPIDefinition[],
  personas: PersonaProfile[]
): ValueHypothesis | null {
  
  // Find matching rule (simplified keyword matching)
  const matchedRule = rules.find(rule => {
    const keywords = rule.signalName.toLowerCase().split(" ");
    const signalLower = rawSignal.toLowerCase();
    return keywords.some(kw => signalLower.includes(kw)) && signalLower.length > 10;
  });

  if (!matchedRule) {
    console.warn(`[SignalEngine] No matching rule for: ${rawSignal.substring(0, 80)}...`);
    return null;
  }

  // Resolve linked pains
  const linkedPains = pains.filter(p => matchedRule.linkedPains.includes(p.id));
  
  // Resolve linked KPIs
  const linkedKPIs = kpis.filter(k => matchedRule.linkedKPIs.includes(k.id));
  
  // Resolve affected personas (union of all linked pain personas)
  const affectedPersonaIds = new Set<string>();
  linkedPains.forEach(p => p.affectedPersonas.forEach(ap => affectedPersonaIds.add(ap)));
  const affectedPersonas = personas.filter(p => affectedPersonaIds.has(p.id));

  // Select recommended formula (formula linked to first pain's first KPI)
  const recommendedFormula = ADVANCED_FORMULAS.find(f => {
    // Simple heuristic: match formula applicable to pain context
    if (matchedRule.id === "adv-sig-005" && f.id === "adv-form-005") return true;
    if (matchedRule.id === "adv-sig-002" && f.id === "adv-form-002") return true;
    if (matchedRule.id === "adv-sig-001" && f.id === "adv-form-001") return true;
    return false;
  });

  // Generate discovery questions from linked pains
  const discoveryQuestions = linkedPains.map(p => {
    return `Can you quantify the annual cost of "${p.name}"? (e.g., scrap, downtime, rework)`;
  });

  return {
    signalId: matchedRule.id,
    signalName: matchedRule.signalName,
    confidence: matchedRule.confidenceScore,
    linkedPains,
    linkedKPIs,
    affectedPersonas,
    discoveryQuestions,
    recommendedFormula
  };
}

// =============================================================================
// 4. EXAMPLE 2 — Value Quantification Engine
// =============================================================================

/**
 * Calculate value using a vertical formula with customer-specific inputs.
 * Returns annual value with confidence score.
 */
interface ValueCalculationResult {
  formulaId: string;
  formulaName: string;
  annualValue: number;
  unit: string;
  confidence: number;
  confidenceRationale: string[];
  missingInputs: string[];
  exampleCalculation: string;
}

function calculateValue(
  formula: ValueFormula,
  inputs: Record<string, number>,
  overrides?: { [key: string]: number }
): ValueCalculationResult {
  
  const allInputs = { ...inputs, ...overrides };
  const missingInputs = formula.requiredInputs.filter(req => !(req in allInputs));
  
  // Evaluate confidence based on input coverage
  let confidence = 0.5;
  const confidenceRationale: string[] = [];
  
  if (missingInputs.length === 0) {
    confidence = 0.85;
    confidenceRationale.push("All required inputs provided by customer");
  } else if (missingInputs.length <= formula.requiredInputs.length / 3) {
    confidence = 0.65;
    confidenceRationale.push(`Missing ${missingInputs.length} inputs; using industry benchmarks for gaps`);
  } else {
    confidence = 0.40;
    confidenceRationale.push(`Missing ${missingInputs.length}/${formula.requiredInputs.length} inputs; estimate is highly speculative`);
  }

  // Formula-specific calculation logic
  let annualValue = 0;
  
  if (formula.id === "adv-form-005" && !missingInputs.includes("AnnualFalseAlarms")) {
    const alarms = allInputs["AnnualFalseAlarms"] || 0;
    const stopMin = allInputs["ToolStoppageMinutes"] || 15;
    const valPerMin = allInputs["ToolThroughputValuePerMin"] || 200;
    const invMin = allInputs["OperatorInvestigationMinutes"] || 30;
    const labor = allInputs["LoadedLaborRate"] || 1.5;
    annualValue = alarms * (stopMin * valPerMin + invMin * labor);
  }
  else if (formula.id === "adv-form-002" && !missingInputs.includes("BaselineCT")) {
    const baseCT = allInputs["BaselineCT"] || 120;
    const targetCT = allInputs["TargetCT"] || 96;
    const chambers = allInputs["FormationChamberCount"] || 400;
    const cap = allInputs["ChamberCapacityGWh"] || 0.1;
    const margin = allInputs["ContributionMarginPerGWh"] || 35000000;
    annualValue = ((baseCT - targetCT) / baseCT) * chambers * cap * margin;
  }
  else if (formula.id === "adv-form-001" && !missingInputs.includes("BaselineYield")) {
    const base = allInputs["BaselineYield"] || 88;
    const target = allInputs["TargetYield"] || 92;
    const starts = allInputs["AnnualWaferStarts"] || 100000;
    const die = allInputs["DiePerWafer"] || 400;
    const rev = allInputs["DieRevenue"] || 15;
    annualValue = ((target - base) / 100) * starts * die * rev;
  }
  else {
    // Fallback: use example calculation value as proxy
    const match = formula.exampleCalculation.match(/=\s*\$?([0-9,.]+)([KMBT]?)/);
    if (match) {
      let val = parseFloat(match[1].replace(/,/g, ""));
      if (match[2] === "K") val *= 1000;
      if (match[2] === "M") val *= 1000000;
      if (match[2] === "B") val *= 1000000000;
      annualValue = val;
      confidenceRationale.push("Using example calculation as proxy due to missing inputs");
    }
  }

  return {
    formulaId: formula.id,
    formulaName: formula.name,
    annualValue: Math.round(annualValue),
    unit: formula.outputUnit,
    confidence,
    confidenceRationale,
    missingInputs,
    exampleCalculation: formula.exampleCalculation
  };
}

// =============================================================================
// 5. EXAMPLE 3 — Discovery Question Sequencer
// =============================================================================

/**
 * Generate a prioritized discovery question sequence for a target persona
 * based on the most relevant pains and KPIs.
 */
function generateDiscoverySequence(
  targetPersonaId: string,
  pains: BusinessPain[],
  kpis: KPIDefinition[],
  maxQuestions: number = 5
): Array<{ question: string; pain: string; kpi: string; priority: number }> {
  
  // Filter pains affecting this persona, sorted by prevalence
  const personaPains = pains
    .filter(p => p.affectedPersonas.includes(targetPersonaId))
    .sort((a, b) => {
      const prevalenceOrder = { HIGH: 3, MEDIUM: 2, LOW: 1 };
      return prevalenceOrder[b.prevalence] - prevalenceOrder[a.prevalence];
    });

  const sequence: Array<{ question: string; pain: string; kpi: string; priority: number }> = [];
  let priority = 1;

  for (const pain of personaPains) {
    if (sequence.length >= maxQuestions) break;
    
    // Find the most relevant KPI for this pain
    const linkedKpi = kpis.find(k => pain.linkedKPIs.includes(k.id));
    
    if (linkedKpi) {
      sequence.push({
        question: `For "${pain.name}": What is your current ${linkedKpi.name} (${linkedKpi.unit}) compared to the benchmark of ${linkedKpi.benchmarkRange}?`,
        pain: pain.name,
        kpi: linkedKpi.name,
        priority
      });
      priority++;
    }
    
    // Add a cost/impact question
    if (sequence.length < maxQuestions) {
      sequence.push({
        question: `What is the estimated annual cost (scrap, downtime, rework, lost margin) attributed to "${pain.name}"?`,
        pain: pain.name,
        kpi: "Cost Impact",
        priority
      });
      priority++;
    }
  }

  return sequence.slice(0, maxQuestions);
}

// =============================================================================
// 6. EXAMPLE 4 — Persona-Specific Messaging Generator
// =============================================================================

/**
 * Generate tailored messaging for a specific persona based on their
 * trusted evidence and disliked claims.
 */
function generatePersonaMessaging(
  persona: PersonaProfile,
  pain: BusinessPain,
  valueRange: { low: number; high: number; unit: string }
): { opening: string; evidence: string; avoid: string; cta: string } {
  
  const isEconomic = persona.decisionInfluence === "economic";
  
  const opening = isEconomic
    ? `${persona.name}, we have identified a ${pain.prevalence.toLowerCase()}-prevalence operational issue — "${pain.name}" — that typically impacts ${valueRange.unit} ${valueRange.low.toLocaleString()}-${valueRange.high.toLocaleString()} annually in comparable operations.`
    : `${persona.name}, your peers at comparable fabs/factories are seeing ${pain.symptoms[0]?.toLowerCase() || "measurable degradation"} due to "${pain.name}". We have a physics-informed approach that respects your existing standards.`;

  const evidence = isEconomic
    ? `This estimate is based on ${persona.trustedEvidence.slice(0, 2).join(" and ")} benchmarks. We can validate with your specific data in a 2-week assessment.`
    : `Our approach aligns with ${persona.trustedEvidence.slice(0, 2).join(" and ")} and does not require ${persona.dislikedClaims.slice(0, 1)}.`;

  const avoid = `Please note: We avoid ${persona.dislikedClaims.slice(0, 2).join(" and ")}.`;

  const cta = isEconomic
    ? `Would you be open to a 30-minute session to validate the baseline inputs and refine the NPV?`
    : `Would you be open to a technical walkthrough with your team to validate the approach against your process constraints?`;

  return { opening, evidence, avoid, cta };
}

// =============================================================================
// 7. DEMONSTRATION / TEST RUNS
// =============================================================================

// Demo 1: Signal Interpretation
console.log("=== DEMO 1: Signal Interpretation ===");
const signal1 = "Customer RFP for ML-enhanced FDC platform with false alarm reduction targets";
const hypothesis1 = interpretSignal(signal1, ADVANCED_SIGNAL_RULES, ADVANCED_PAINS, ADVANCED_KPIS, ADVANCED_PERSONAS);
if (hypothesis1) {
  console.log(`Signal: ${hypothesis1.signalName}`);
  console.log(`Confidence: ${hypothesis1.confidence}`);
  console.log(`Linked Pains: ${hypothesis1.linkedPains.map(p => p.name).join(", ")}`);
  console.log(`Affected Personas: ${hypothesis1.affectedPersonas.map(p => p.name).join(", ")}`);
  console.log(`Recommended Formula: ${hypothesis1.recommendedFormula?.name || "None"}`);
}

// Demo 2: Value Calculation
console.log("\n=== DEMO 2: Value Calculation ===");
const fdcFormula = ADVANCED_FORMULAS.find(f => f.id === "adv-form-005")!;
const fdcInputs = {
  AnnualFalseAlarms: 5200,
  ToolStoppageMinutes: 15,
  ToolThroughputValuePerMin: 180,
  OperatorInvestigationMinutes: 30,
  LoadedLaborRate: 1.50
};
const fdcResult = calculateValue(fdcFormula, fdcInputs);
console.log(`Formula: ${fdcResult.formulaName}`);
console.log(`Annual Value: $${fdcResult.annualValue.toLocaleString()}`);
console.log(`Confidence: ${fdcResult.confidence}`);
console.log(`Rationale: ${fdcResult.confidenceRationale.join("; ")}`);

// Demo 3: Discovery Sequence
console.log("\n=== DEMO 3: Discovery Sequence ===");
const fabEngQuestions = generateDiscoverySequence("pers-fab-eng", ADVANCED_PAINS, ADVANCED_KPIS, 5);
fabEngQuestions.forEach((q, i) => {
  console.log(`${i + 1}. [P${q.priority}] ${q.question}`);
});

// Demo 4: Persona Messaging
console.log("\n=== DEMO 4: Persona Messaging ===");
const fabEng = ADVANCED_PERSONAS.find(p => p.id === "pers-fab-eng")!;
const yieldPain = ADVANCED_PAINS.find(p => p.id === "adv-pain-001")!;
const messaging = generatePersonaMessaging(fabEng, yieldPain, { low: 12000000, high: 36000000, unit: "$" });
console.log(`Opening: ${messaging.opening}`);
console.log(`Evidence: ${messaging.evidence}`);
console.log(`CTA: ${messaging.cta}`);

// =============================================================================
// 8. EXPORT TYPES (for integration)
// =============================================================================

export {
  // Types
  SignalInterpretationRule,
  BusinessPain,
  KPIDefinition,
  PersonaProfile,
  ValueFormula,
  ValueHypothesis,
  ValueCalculationResult,
  
  // Data
  ADVANCED_SIGNAL_RULES,
  ADVANCED_PAINS,
  ADVANCED_KPIS,
  ADVANCED_PERSONAS,
  ADVANCED_FORMULAS,
  
  // Functions
  interpretSignal,
  calculateValue,
  generateDiscoverySequence,
  generatePersonaMessaging
};
