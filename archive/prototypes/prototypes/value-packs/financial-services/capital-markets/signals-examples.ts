/**
 * Capital Markets Subpack - Signal Interpretation Examples (TypeScript)
 * 
 * ID: capital-markets-v1
 * Parent Master: financial-services-master-v1
 * Description: TypeScript examples for applying Capital Markets signal rules
 * to generate value hypotheses, business cases, and persona-specific narratives.
 */

// ============================================================================
// Core Interfaces (extending Master Pack patterns with Capital Markets types)
// ============================================================================

interface CapitalMarketsSignal {
  ruleId: string;
  rawSignal: string;
  source: string;
  timestamp: Date;
  confidenceScore: number;
  dataPoints: Record<string, number | string>;
}

interface ValueHypothesis {
  hypothesisId: string;
  signalRuleId: string;
  painId: string;
  kpiIds: string[];
  personaIds: string[];
  valueDriverCategory: 'Revenue Uplift' | 'Cost Savings' | 'Risk Reduction' | 'Working Capital';
  estimatedAnnualValue: number;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  requiredEvidence: string[];
  recommendedDiscoveryQuestions: string[];
}

interface PersonaNarrative {
  personaId: string;
  painName: string;
  hook: string;
  evidenceClaims: string[];
  businessCaseSummary: string;
  objections: string[];
}

// ============================================================================
// Example 1: Portfolio Reconciliation Break Spike → Business Case
// ============================================================================

const reconciliationBreakSignal: CapitalMarketsSignal = {
  ruleId: 'CM-SR001',
  rawSignal: 'Daily reconciliation breaks increased 65% above 90-day baseline with 18% aged >3 days',
  source: 'DTCC Reconciliation Analytics',
  timestamp: new Date('2024-11-15'),
  confidenceScore: 0.9,
  dataPoints: {
    currentBreaksPerDay: 780,
    baselineBreaksPerDay: 473,
    pctAgedOver3Days: 18,
    navRestatementsQTD: 1,
    manualReconciliationFTEs: 32
  }
};

function buildReconciliationHypothesis(signal: CapitalMarketsSignal): ValueHypothesis {
  const breakReduction = signal.dataPoints.currentBreaksPerDay - 150; // target
  const fteReduction = Math.round((signal.dataPoints.manualReconciliationFTEs as number) * 0.4);

  return {
    hypothesisId: 'VH-CM-001',
    signalRuleId: 'CM-SR001',
    painId: 'CM-P001',
    kpiIds: ['CM-K001', 'CM-K002', 'CM-K014'],
    personaIds: ['CM-PER002', 'CM-PER003', 'COO'],
    valueDriverCategory: 'Cost Savings',
    estimatedAnnualValue: 
      (breakReduction * 250 * 252) + 
      (fteReduction * 140000) + 
      2500000, // NAV restatement avoidance
    confidence: 'HIGH',
    requiredEvidence: [
      'Break aging report showing >3 day aging trend',
      'NAV production timeline vs SLA',
      'FTE allocation by reconciliation function',
      'Historical NAV restatement cost analysis'
    ],
    recommendedDiscoveryQuestions: [
      'CM-DQ001: How many reconciliation breaks daily?',
      'CM-DQ002: What is IBOR/ABOR alignment time?',
      'CM-DQ011: What is your NAV accuracy rate?'
    ]
  };
}

const reconciliationHypothesis = buildReconciliationHypothesis(reconciliationBreakSignal);
console.log('Reconciliation Hypothesis:', reconciliationHypothesis);

// ============================================================================
// Example 2: Securities Lending Revenue Decline → Revenue Narrative
// ============================================================================

const securitiesLendingSignal: CapitalMarketsSignal = {
  ruleId: 'CM-SR003',
  rawSignal: 'Securities lending revenue declined 28% YoY while benchmark flat and lendable AUM stable at $12B',
  source: 'DataLend Revenue Analytics',
  timestamp: new Date('2024-10-31'),
  confidenceScore: 0.85,
  dataPoints: {
    currentRevenueYieldBPS: 14,
    priorYearRevenueYieldBPS: 19,
    lendableAUM: 12000000000,
    utilizationRate: 52,
    topQuartileUtilization: 82,
    manualTicketPct: 45
  }
};

function buildSecuritiesLendingHypothesis(signal: CapitalMarketsSignal): ValueHypothesis {
  const lendableAUM = signal.dataPoints.lendableAUM as number;
  const targetUtilization = signal.dataPoints.topQuartileUtilization as number / 100;
  const currentUtilization = signal.dataPoints.utilizationRate as number / 100;
  const revenueYieldImprovement = 0.0008; // 8bps

  return {
    hypothesisId: 'VH-CM-002',
    signalRuleId: 'CM-SR003',
    painId: 'CM-P003',
    kpiIds: ['CM-K003', 'CM-K023', 'CM-K004'],
    personaIds: ['CM-PER006', 'CM-PER001', 'CFO'],
    valueDriverCategory: 'Revenue Uplift',
    estimatedAnnualValue: 
      ((targetUtilization - currentUtilization) * lendableAUM * revenueYieldImprovement) +
      3000000 + // collateral optimization
      1500000,  // automated pricing
    confidence: 'HIGH',
    requiredEvidence: [
      'Revenue yield trend by asset class',
      'Utilization rate history vs benchmark',
      'Borrower concentration analysis',
      'Manual vs automated ticket split'
    ],
    recommendedDiscoveryQuestions: [
      'CM-DQ003: What is your securities lending revenue yield?',
      'CM-DQ007: How do you manage collateral optimization?'
    ]
  };
}

const lendingHypothesis = buildSecuritiesLendingHypothesis(securitiesLendingSignal);
console.log('Securities Lending Hypothesis:', lendingHypothesis);

// ============================================================================
// Example 3: Best Execution Review → Compliance + Cost Narrative
// ============================================================================

const bestExSignal: CapitalMarketsSignal = {
  ruleId: 'CM-SR004',
  rawSignal: 'Internal best execution review: implementation shortfall >25bps on 24% of large orders (>1% ADV)',
  source: 'Internal TCA Audit',
  timestamp: new Date('2024-09-20'),
  confidenceScore: 0.92,
  dataPoints: {
    implementationShortfallMedian: 32, // bps
    pctOrdersOverThreshold: 24,
    annualTradeValue: 45000000000,
    venueAnalysisCoverage: 3,
    totalBrokersUsed: 12,
    mifidIIGap: true
  }
};

function buildBestExHypothesis(signal: CapitalMarketsSignal): ValueHypothesis {
  const annualTradeValue = signal.dataPoints.annualTradeValue as number;
  const currentSlippage = 0.0032;
  const targetSlippage = 0.0015;

  return {
    hypothesisId: 'VH-CM-003',
    signalRuleId: 'CM-SR004',
    painId: 'CM-P004',
    kpiIds: ['CM-K005', 'CM-K006', 'CM-K022'],
    personaIds: ['CM-PER001', 'CM-PER004', 'Head of Trading', 'CCO'],
    valueDriverCategory: 'Cost Savings',
    estimatedAnnualValue: 
      ((currentSlippage - targetSlippage) * annualTradeValue) +
      5000000 +  // venue optimization
      2000000,   // compliance cost avoidance
    confidence: 'HIGH',
    requiredEvidence: [
      'TCA analysis by order size bucket',
      'Venue routing data for all executed orders',
      'MiFID II RTS 27/28 reporting completeness',
      'Client best execution query log'
    ],
    recommendedDiscoveryQuestions: [
      'CM-DQ004: Walk me through best execution monitoring',
      'CM-DQ020: How do you manage best execution documentation?'
    ]
  };
}

const bestExHypothesis = buildBestExHypothesis(bestExSignal);
console.log('Best Execution Hypothesis:', bestExHypothesis);

// ============================================================================
// Example 4: NAV Restatement Event → Board-Level Risk Narrative
// ============================================================================

const navRestatementSignal: CapitalMarketsSignal = {
  ruleId: 'CM-SR012',
  rawSignal: 'NAV restatement published affecting $450M AUM with 1.2% NAV correction requiring client notification',
  source: 'Internal NAV Quality Control',
  timestamp: new Date('2024-11-01'),
  confidenceScore: 0.93,
  dataPoints: {
    affectedAUM: 450000000,
    navCorrectionPct: 1.2,
    restatementsYTD: 2,
    clientNotificationsRequired: 340,
    compensationExposure: 850000,
    regulatoryInquiryRisk: true
  }
};

function buildNAVRestatementNarrative(signal: CapitalMarketsSignal): PersonaNarrative {
  const compensation = signal.dataPoints.compensationExposure as number;

  return {
    personaId: 'CM-PER003',
    painName: 'NAV Restatement Event',
    hook: `NAV restatements cost us $${compensation.toLocaleString()} in Q3 alone, and regulatory inquiry risk is now elevated.`,
    evidenceClaims: [
      `Industry benchmark: top-quartile managers achieve <0.1% restatement rate; our YTD rate is ${(signal.dataPoints.restatementsYTD as number) * 0.5}%`,
      'DTCC data shows 99.7% NAV accuracy for best-in-class fund administrators',
      'SS&C benchmarking: NAV production <2 hours post-close for automated platforms vs our 8-hour cycle'
    ],
    businessCaseSummary: 'Implementing automated book-of-record reconciliation and real-time NAV production could reduce restatements by 85%, eliminate $850K annual compensation exposure, and reduce NAV production time from 8 hours to 2 hours.',
    objections: [
      'CM-OBJ001: We have dedicated fund administrators',
      'CM-OBJ003: Reconciliation breaks are just part of the business'
    ]
  };
}

const navNarrative = buildNAVRestatementNarrative(navRestatementSignal);
console.log('NAV Restatement Narrative:', navNarrative);

// ============================================================================
// Example 5: T+1 Settlement Penalty Spike → Urgency-Driven Procurement
// ============================================================================

const t1PenaltySignal: CapitalMarketsSignal = {
  ruleId: 'CM-SR001', // reusing with different context
  rawSignal: 'CSDR cash penalties $1.2M in October with settlement fail rate at 4.8% post-T+1 transition',
  source: 'DTCC Settlement Analytics',
  timestamp: new Date('2024-11-01'),
  confidenceScore: 0.9,
  dataPoints: {
    monthlyPenalties: 1200000,
    settlementFailRate: 4.8,
    targetFailRate: 1.5,
    annualTradeVolume: 50000000,
    penaltyPerFail: 12.50,
    manualMatchingPct: 28
  }
};

function buildT1SettlementHypothesis(signal: CapitalMarketsSignal): ValueHypothesis {
  const annualVolume = signal.dataPoints.annualTradeVolume as number;
  const currentFailRate = signal.dataPoints.settlementFailRate as number / 100;
  const targetFailRate = signal.dataPoints.targetFailRate as number / 100;
  const penaltyPerFail = signal.dataPoints.penaltyPerFail as number;

  return {
    hypothesisId: 'VH-CM-005',
    signalRuleId: 'CM-SR001',
    painId: 'CM-P001',
    kpiIds: ['CM-K001', 'CM-K024'],
    personaIds: ['CM-PER002', 'COO', 'Head of Operations'],
    valueDriverCategory: 'Cost Savings',
    estimatedAnnualValue: 
      ((currentFailRate - targetFailRate) * annualVolume * penaltyPerFail) +
      8000000 +  // STP improvement
      5000000,   // operational headcount reduction
    confidence: 'HIGH',
    requiredEvidence: [
      'DTCC fail rate report by counterparty',
      'CSDR penalty register',
      'Matching automation gap analysis',
      'T+1 readiness assessment'
    ],
    recommendedDiscoveryQuestions: [
      'CM-DQ001: Reconciliation break daily count',
      'CM-DQ012: Corporate actions processing fail rate',
      'CM-DQ018: Custody asset servicing breaks'
    ]
  };
}

const t1Hypothesis = buildT1SettlementHypothesis(t1PenaltySignal);
console.log('T+1 Settlement Hypothesis:', t1Hypothesis);

// ============================================================================
// Example 6: ESG Data Integration → Institutional RFP Response
// ============================================================================

const esgSignal: CapitalMarketsSignal = {
  ruleId: 'CM-SR009',
  rawSignal: 'Institutional RFP requires SFDR Article 8 compliance with quarterly PAI reporting; current ESG coverage 62% of portfolio',
  source: 'Client RFP Document',
  timestamp: new Date('2024-10-15'),
  confidenceScore: 0.82,
  dataPoints: {
    esgCoveragePct: 62,
    targetCoveragePct: 95,
    sfdrPaiProcessingDays: 18,
    manualEsgFTEs: 8,
    clientAumAtRisk: 750000000,
    rfpDeadlineDays: 45
  }
};

function buildESGHypothesis(signal: CapitalMarketsSignal): ValueHypothesis {
  const clientAUM = signal.dataPoints.clientAumAtRisk as number;
  const fteReduction = Math.round((signal.dataPoints.manualEsgFTEs as number) * 0.5);

  return {
    hypothesisId: 'VH-CM-006',
    signalRuleId: 'CM-SR009',
    painId: 'CM-P009',
    kpiIds: ['CM-K011', 'K066'],
    personaIds: ['CM-PER004', 'CM-PER003', 'Head of ESG', 'Head of Distribution'],
    valueDriverCategory: 'Revenue Uplift',
    estimatedAnnualValue: 
      (fteReduction * 150000) +
      2000000 +  // SFDR PAI automation
      1500000 +  // data spend optimization
      (clientAUM * 0.005), // client retention/mandate win value
    confidence: 'MEDIUM',
    requiredEvidence: [
      'ESG data coverage report by provider',
      'SFDR PAI processing timeline',
      'Client mandate ESG requirement terms',
      'Competitor ESG capability comparison'
    ],
    recommendedDiscoveryQuestions: [
      'CM-DQ009: ESG data coverage and SFDR PAI processing time',
      'CM-DQ019: Market data spend and duplicate feeds'
    ]
  };
}

const esgHypothesis = buildESGHypothesis(esgSignal);
console.log('ESG Hypothesis:', esgHypothesis);

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Generates a discovery script for a given persona and pain combination.
 */
function generateDiscoveryScript(personaId: string, painId: string, subpack: any): string {
  const persona = subpack.personas.find((p: any) => p.id === personaId);
  const pain = subpack.pains.find((p: any) => p.id === painId);
  const questions = subpack.discoveryQuestions.filter((q: any) => 
    q.targetPersonas.includes(personaId) && q.linkedPains.includes(painId)
  );

  if (!persona || !pain) {
    return `Persona ${personaId} or Pain ${painId} not found.`;
  }

  const script = [
    `## Discovery Script: ${persona.name} — ${pain.name}`,
    '',
    `**Persona:** ${persona.role} (${persona.seniority})`,
    `**Pain:** ${pain.description}`,
    `**Prevalence:** ${pain.prevalence} | **Confidence:** ${pain.confidence}`,
    '',
    '**Opening Hook:**',
    `> "Many ${persona.role.toLowerCase()}s at ${pain.affectedSegments[0].toLowerCase()} firms are seeing ${pain.symptoms[0].toLowerCase()}. How does this compare to your experience?"`,
    '',
    '**Discovery Questions:**'
  ];

  questions.forEach((q: any, i: number) => {
    script.push(`${i + 1}. ${q.question}`);
    script.push(`   → *Expected Insight:* ${q.expectedInsight}`);
  });

  script.push('');
  script.push('**Evidence to Request:**');
  pain.symptoms.forEach((s: string) => {
    script.push(`- ${s}`);
  });

  return script.join('\n');
}

/**
 * Calculates a weighted confidence score across multiple signals.
 */
function calculateAggregateConfidence(signals: CapitalMarketsSignal[]): number {
  if (signals.length === 0) return 0;
  const weightedSum = signals.reduce((sum, s) => sum + s.confidenceScore, 0);
  return Math.round((weightedSum / signals.length) * 100) / 100;
}

/**
 * Generates an objection response script.
 */
function generateObjectionResponse(objectionId: string, subpack: any): string {
  const objection = subpack.objections.find((o: any) => o.id === objectionId);
  if (!objection) return `Objection ${objectionId} not found.`;

  const linkedPains = subpack.pains.filter((p: any) => objection.linkedPains.includes(p.id));

  return [
    `## Objection Response: ${objection.objectionText}`,
    '',
    `**Context:** ${objection.context}`,
    '',
    '**Reframe:**',
    objection.reframeApproach,
    '',
    '**Linked Pains:**',
    ...linkedPains.map((p: any) => `- ${p.id}: ${p.name}`),
    '',
    '**Recommended Pivot:**',
    `"I understand ${objection.context.toLowerCase()}. Let's look at the specific numbers for ${linkedPains[0]?.name.toLowerCase() || 'this area'} and see if the investment case holds in your environment."`
  ].join('\n');
}

// ============================================================================
// Export all examples for integration
// ============================================================================

export {
  CapitalMarketsSignal,
  ValueHypothesis,
  PersonaNarrative,
  reconciliationBreakSignal,
  reconciliationHypothesis,
  securitiesLendingSignal,
  lendingHypothesis,
  bestExSignal,
  bestExHypothesis,
  navRestatementSignal,
  navNarrative,
  t1PenaltySignal,
  t1Hypothesis,
  esgSignal,
  esgHypothesis,
  buildReconciliationHypothesis,
  buildSecuritiesLendingHypothesis,
  buildBestExHypothesis,
  buildNAVRestatementNarrative,
  buildT1SettlementHypothesis,
  buildESGHypothesis,
  generateDiscoveryScript,
  calculateAggregateConfidence,
  generateObjectionResponse
};
