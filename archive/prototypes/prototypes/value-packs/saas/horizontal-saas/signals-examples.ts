/**
 * Horizontal SaaS Subpack — Signal Interpretation Examples
 * Subpack ID: horizontal-saas-v1
 * Parent Master: saas-master-v1
 * 
 * This file provides executable TypeScript-style definitions for signal rules,
 * KPI calculations, formula applications, and persona matchers used in the
 * Horizontal SaaS vertical intelligence layer.
 */

// ============================================================================
// CORE INTERFACES (inherited from Master Pack, extended for Horizontal SaaS)
// ============================================================================

interface SignalRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  confidenceScore: number; // 0.0 - 1.0
  requiredConfirmationSignals: string[];
}

interface KPI {
  id: string;
  name: string;
  formula: string;
  unit: string;
  typicalRange: string;
  benchmarkRange: string;
  segmentApplicability: string[];
  calculationFrequency: string;
}

interface Pain {
  id: string;
  name: string;
  description: string;
  symptoms: string[];
  affectedSubVerticals: string[];
  affectedPersonas: string[];
  linkedKPIs: string[];
  prevalence: 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  sources: string[];
}

interface Persona {
  id: string;
  name: string;
  role: string;
  seniority: string;
  goals: string[];
  pressures: string[];
  trustedEvidence: string[];
  dislikedClaims: string[];
  decisionInfluence: 'economic' | 'technical' | 'user';
}

interface ValueFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  applicableSegments: string[];
  confidenceRules: string;
  exampleCalculation: string;
}

// ============================================================================
// HORIZONTAL SAAS SIGNAL RULES (20 rules)
// ============================================================================

const SIGNAL_RULES: SignalRule[] = [
  {
    id: 'HSR001',
    signalName: 'IT Director Job Posting Surge',
    rawSignalPattern: 'Company posts >3 IT operations, systems admin, or SaaS management roles in 60 days',
    interpretedMeaning: 'Organization scaling IT operations to manage SaaS proliferation or preparing for systems consolidation initiative. Likely evaluating SaaS management platforms.',
    linkedPains: ['HSP001', 'HSP002', 'HSP013'],
    linkedKPIs: ['HSK001', 'HSK004', 'HSK037'],
    confidenceScore: 0.8,
    requiredConfirmationSignals: [
      'SaaS spend growth >30% YoY',
      'Recent CIO/IT Director hire',
      'Security audit findings mentioning access gaps'
    ]
  },
  {
    id: 'HSR002',
    signalName: 'Finance Systems Admin Hiring',
    rawSignalPattern: 'Company posts roles for ERP admin, finance systems analyst, or accounting automation specialist',
    interpretedMeaning: 'Finance team investing in system modernization, automation, or ERP migration. Potential for close optimization and reconciliation tooling.',
    linkedPains: ['HSP004', 'HSP016', 'HSP018'],
    linkedKPIs: ['HSK010', 'HSK011', 'HSK012'],
    confidenceScore: 0.75,
    requiredConfirmationSignals: [
      'ERP vendor migration announcement',
      'Month-end close duration >10 days',
      'Manual journal entry rate >20%'
    ]
  },
  {
    id: 'HSR003',
    signalName: 'HR Operations Manager Expansion',
    rawSignalPattern: 'Company posts multiple HR operations, onboarding, or HRIS admin roles',
    interpretedMeaning: 'HR team scaling operations due to headcount growth or HRIS consolidation. Likely evaluating unified HR platforms or onboarding automation.',
    linkedPains: ['HSP005', 'HSP013'],
    linkedKPIs: ['HSK013', 'HSK014', 'HSK015'],
    confidenceScore: 0.7,
    requiredConfirmationSignals: [
      'Headcount growth >20% YoY',
      'Employee satisfaction scores on onboarding <70%',
      'Multiple HR systems in job description requirements'
    ]
  },
  {
    id: 'HSR004',
    signalName: 'Procurement Platform RFP',
    rawSignalPattern: 'Company publishes RFP for procurement, vendor management, or spend analytics platform',
    interpretedMeaning: 'Active procurement transformation initiative. High intent signal for source-to-pay, contract lifecycle, or SaaS spend optimization solutions.',
    linkedPains: ['HSP006', 'HSP019'],
    linkedKPIs: ['HSK016', 'HSK017', 'HSK018'],
    confidenceScore: 0.9,
    requiredConfirmationSignals: [
      'Maverick spend >15%',
      'Procurement team headcount <3 for $50M+ revenue',
      'Recent audit finding on vendor due diligence'
    ]
  },
  {
    id: 'HSR005',
    signalName: 'BI Analyst Hiring Spree',
    rawSignalPattern: 'Company posts >2 BI analyst, data analyst, or analytics engineer roles in 30 days',
    interpretedMeaning: 'Data and analytics function is scaling. May indicate dashboard demand outpacing capacity, or data platform investment following.',
    linkedPains: ['HSP011', 'HSP012', 'HSP017'],
    linkedKPIs: ['HSK031', 'HSK032', 'HSK036'],
    confidenceScore: 0.75,
    requiredConfirmationSignals: [
      'Multiple BI tools mentioned in job requirements',
      'Data team Glassdoor reviews mentioning backlog',
      'Recent data warehouse vendor announcement'
    ]
  },
  {
    id: 'HSR006',
    signalName: 'Security Engineer Surge',
    rawSignalPattern: 'Company posts >3 security engineer, SOC analyst, or IAM specialist roles in 60 days',
    interpretedMeaning: 'Security team expansion signals either incident response, compliance preparation, or tool consolidation need. Likely evaluating SIEM/SOAR, IAM, or security automation.',
    linkedPains: ['HSP014', 'HSP013', 'HSP020'],
    linkedKPIs: ['HSK040', 'HSK041', 'HSK042'],
    confidenceScore: 0.85,
    requiredConfirmationSignals: [
      'Recent security incident disclosure',
      'SOC 2 audit scheduled',
      'CISO hire in last 6 months'
    ]
  },
  {
    id: 'HSR007',
    signalName: 'DevOps Platform Engineering Roles',
    rawSignalPattern: 'Company posts platform engineer, DevOps automation, or CI/CD specialist roles',
    interpretedMeaning: 'Engineering organization maturing toward platform engineering model. Standardizing toolchain and reducing custom infrastructure work.',
    linkedPains: ['HSP015', 'HSP002'],
    linkedKPIs: ['HSK043', 'HSK044', 'HSK045'],
    confidenceScore: 0.8,
    requiredConfirmationSignals: [
      '>5 CI/CD tools mentioned in stack',
      'Kubernetes cluster count >10',
      'Engineering headcount doubling in last year'
    ]
  },
  {
    id: 'HSR008',
    signalName: 'Contract Management Tool Search',
    rawSignalPattern: 'LinkedIn activity or job postings mentioning CLM, contract analytics, or vendor management tools',
    interpretedMeaning: 'Procurement and legal teams seeking to digitize contract lifecycle. Renewal chaos likely driving urgency.',
    linkedPains: ['HSP019', 'HSP006'],
    linkedKPIs: ['HSK055', 'HSK056', 'HSK057'],
    confidenceScore: 0.75,
    requiredConfirmationSignals: [
      'Auto-renewal spend >$500K annually',
      'Legal team headcount <2 for $100M+ company',
      'Recent missed renewal negotiation'
    ]
  },
  {
    id: 'HSR009',
    signalName: 'Collaboration Tool Consolidation Signal',
    rawSignalPattern: 'Company evaluating or deprecating a collaboration tool; employee surveys mentioning tool fatigue',
    interpretedMeaning: 'IT leadership likely planning collaboration stack consolidation. Opportunity for unified workspace or knowledge management platform.',
    linkedPains: ['HSP008', 'HSP001'],
    linkedKPIs: ['HSK022', 'HSK023', 'HSK024'],
    confidenceScore: 0.7,
    requiredConfirmationSignals: [
      '>4 active collaboration tools',
      'Employee NPS on tools <20',
      'IT roadmap mentioning consolidation'
    ]
  },
  {
    id: 'HSR010',
    signalName: 'Customer Support Scaling Indicator',
    rawSignalPattern: 'Company posts >5 support agent roles or support team expansion in 60 days',
    interpretedMeaning: 'Support volume growing faster than self-service investment. May indicate knowledge base gaps or need for support automation.',
    linkedPains: ['HSP009', 'HSP003'],
    linkedKPIs: ['HSK025', 'HSK026', 'HSK027'],
    confidenceScore: 0.7,
    requiredConfirmationSignals: [
      'Ticket volume growth >30% QoQ',
      'First contact resolution declining',
      'Customer satisfaction scores <80%'
    ]
  },
  {
    id: 'HSR011',
    signalName: 'Marketing Tech Stack Audit',
    rawSignalPattern: 'Company posts marketing operations analyst, martech admin, or attribution specialist roles',
    interpretedMeaning: 'Marketing team seeking to rationalize stack and improve measurement. Likely evaluating marketing automation, CDP, or attribution platforms.',
    linkedPains: ['HSP010', 'HSP017'],
    linkedKPIs: ['HSK028', 'HSK029', 'HSK030'],
    confidenceScore: 0.75,
    requiredConfirmationSignals: [
      '>6 marketing tools in job requirements',
      'Campaign ROI reporting delay >30 days',
      'Recent CMO hire'
    ]
  },
  {
    id: 'HSR012',
    signalName: 'ERP Cloud Migration Announcement',
    rawSignalPattern: 'Company announces ERP cloud migration, S/4HANA implementation, or Oracle Cloud transition',
    interpretedMeaning: 'Major finance system transformation creating integration, data migration, and change management needs. High-value services and tooling opportunity.',
    linkedPains: ['HSP018', 'HSP004', 'HSP016'],
    linkedKPIs: ['HSK052', 'HSK053', 'HSK054'],
    confidenceScore: 0.9,
    requiredConfirmationSignals: [
      'ERP vendor partner selection announced',
      'Finance systems admin hiring',
      'Custom module count >50'
    ]
  },
  {
    id: 'HSR013',
    signalName: 'Data Residency Requirement Signal',
    rawSignalPattern: 'Company announces EU/APAC data center investment, data sovereignty initiatives, or regional expansion',
    interpretedMeaning: 'Data platform and horizontal SaaS stack must comply with regional data residency. Infrastructure and SaaS selection constrained.',
    linkedPains: ['HSP012', 'HSP002', 'HSP014'],
    linkedKPIs: ['HSK034', 'HSK004', 'HSK040'],
    confidenceScore: 0.8,
    requiredConfirmationSignals: [
      'EU customer revenue >20%',
      'Schrems II or GDPR mentioned in filings',
      'Regional hiring in data engineering'
    ]
  },
  {
    id: 'HSR014',
    signalName: 'AI Tool Governance Search',
    rawSignalPattern: 'Company searches for AI governance, AI risk management, or LLM policy tools; job postings for AI governance roles',
    interpretedMeaning: 'Shadow AI usage has reached a scale requiring formal governance. Security and compliance teams investing in AI controls.',
    linkedPains: ['HSP020', 'HSP014'],
    linkedKPIs: ['HSK058', 'HSK059', 'HSK060'],
    confidenceScore: 0.75,
    requiredConfirmationSignals: [
      'Employee surveys mentioning AI usage',
      'No AI policy on intranet',
      'Security team expressing AI data loss concerns'
    ]
  },
  {
    id: 'HSR015',
    signalName: 'SaaS Renewal Concentration Spike',
    rawSignalPattern: 'Company has >30% of SaaS contracts renewing within same 90-day window',
    interpretedMeaning: 'Procurement team faces renewal tsunami. Negotiation leverage and time constraints create urgency for contract management and optimization tools.',
    linkedPains: ['HSP019', 'HSP006', 'HSP001'],
    linkedKPIs: ['HSK055', 'HSK056', 'HSK057'],
    confidenceScore: 0.8,
    requiredConfirmationSignals: [
      'Contract repository coverage <50%',
      'Procurement team size <2',
      'Historical auto-renewal rate >30%'
    ]
  },
  {
    id: 'HSR016',
    signalName: 'Cross-Functional Project Delay Pattern',
    rawSignalPattern: 'Company earnings or public disclosures mention project delays, cost overruns, or resource constraints',
    interpretedMeaning: 'Project management and resource planning systems failing at scale. Portfolio visibility and cross-functional coordination gaps.',
    linkedPains: ['HSP007', 'HSP008'],
    linkedKPIs: ['HSK019', 'HSK020', 'HSK021'],
    confidenceScore: 0.7,
    requiredConfirmationSignals: [
      '>3 project management tools in use',
      'Resource conflict rate >20%',
      'Project milestone slippage >25%'
    ]
  },
  {
    id: 'HSR017',
    signalName: 'Finance Close Acceleration Mandate',
    rawSignalPattern: 'CFO publicly states goal to reduce close time or board mandates faster reporting',
    interpretedMeaning: 'Finance transformation initiative with clear metric target. Close optimization, automation, and reconciliation tools in scope.',
    linkedPains: ['HSP004', 'HSP016'],
    linkedKPIs: ['HSK010', 'HSK046', 'HSK047'],
    confidenceScore: 0.85,
    requiredConfirmationSignals: [
      'Days to close >8',
      'FP&A team complaining about prep time',
      'Recent ERP or consolidation project'
    ]
  },
  {
    id: 'HSR018',
    signalName: 'Knowledge Management Initiative',
    rawSignalPattern: 'Company posts knowledge management, documentation, or internal communications roles; intranet RFP',
    interpretedMeaning: 'Organizational knowledge fragmentation recognized. Collaboration and knowledge platform evaluation likely.',
    linkedPains: ['HSP008', 'HSP009'],
    linkedKPIs: ['HSK022', 'HSK023', 'HSK024'],
    confidenceScore: 0.7,
    requiredConfirmationSignals: [
      'Knowledge base search success <40%',
      'Duplicate documentation across tools',
      'Employee onboarding time >1 week'
    ]
  },
  {
    id: 'HSR019',
    signalName: 'Identity Governance Audit Finding',
    rawSignalPattern: 'Audit report or SOC 2 finding mentions access control, orphaned accounts, or provisioning delays',
    interpretedMeaning: 'Identity and access management gaps flagged by auditors. IAM and security automation tooling urgency high.',
    linkedPains: ['HSP013', 'HSP014'],
    linkedKPIs: ['HSK037', 'HSK038', 'HSK039'],
    confidenceScore: 0.85,
    requiredConfirmationSignals: [
      'Offboarding time >48 hours',
      'Orphaned account rate >5%',
      'Access reviews manual and quarterly'
    ]
  },
  {
    id: 'HSR020',
    signalName: 'Customer Data Platform Underperformance',
    rawSignalPattern: 'CDP implementation >18 months with no board-level ROI mention; CDP team turnover',
    interpretedMeaning: 'CDP investment not delivering promised value. Organization likely evaluating alternatives or seeking activation and integration support.',
    linkedPains: ['HSP017', 'HSP002'],
    linkedKPIs: ['HSK049', 'HSK050', 'HSK051'],
    confidenceScore: 0.7,
    requiredConfirmationSignals: [
      'CDP vendor contract up for renewal',
      'Marketing team still pulling manual lists',
      'Data engineering team frustrated with ingestion'
    ]
  }
];

// ============================================================================
// KPI CALCULATION EXAMPLES
// ============================================================================

/**
 * Calculate SaaS Spend Optimization Rate
 * Formula: (Identified Redundant/Unused Spend) / (Total SaaS Spend) × 100
 */
function calculateSaaSSpendOptimizationRate(
  identifiedRedundantSpend: number,
  identifiedUnusedSpend: number,
  totalSaaSSpend: number
): number {
  if (totalSaaSSpend === 0) return 0;
  return ((identifiedRedundantSpend + identifiedUnusedSpend) / totalSaaSSpend) * 100;
}

/**
 * Calculate Integration Success Rate
 * Formula: (Successful Daily Sync Jobs) / (Total Scheduled Sync Jobs) × 100
 */
function calculateIntegrationSuccessRate(
  successfulSyncJobs: number,
  totalScheduledSyncJobs: number
): number {
  if (totalScheduledSyncJobs === 0) return 0;
  return (successfulSyncJobs / totalScheduledSyncJobs) * 100;
}

/**
 * Calculate Days to Month-End Close
 * Formula: (Calendar Days from Period End to Final Close Entry)
 */
function calculateDaysToClose(periodEndDate: Date, finalCloseDate: Date): number {
  const diffTime = finalCloseDate.getTime() - periodEndDate.getTime();
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

/**
 * Calculate First Contact Resolution Rate
 * Formula: (Tickets Resolved on First Interaction) / (Total Tickets) × 100
 */
function calculateFCR(
  ticketsResolvedOnFirstContact: number,
  totalTickets: number
): number {
  if (totalTickets === 0) return 0;
  return (ticketsResolvedOnFirstContact / totalTickets) * 100;
}

/**
 * Calculate Security Alert Signal-to-Noise Ratio
 * Formula: (Actionable Alerts) / (Total Alerts) × 100
 */
function calculateAlertSignalToNoise(
  actionableAlerts: number,
  totalAlerts: number
): number {
  if (totalAlerts === 0) return 0;
  return (actionableAlerts / totalAlerts) * 100;
}

/**
 * Calculate Orphaned Account Rate
 * Formula: (Active Accounts with No Associated Active Employee) / (Total Accounts) × 100
 */
function calculateOrphanedAccountRate(
  orphanedAccounts: number,
  totalAccounts: number
): number {
  if (totalAccounts === 0) return 0;
  return (orphanedAccounts / totalAccounts) * 100;
}

// ============================================================================
// FORMULA APPLICATION EXAMPLES
// ============================================================================

/**
 * HSVF001 — SaaS Sprawl Consolidation Value
 * 
 * Example inputs:
 * - Redundant Tool Count: 5
 * - Average Annual Cost Per Tool: $15,000
 * - Consolidation Savings %: 60%
 * - Unused Licenses Value: $80,000
 * - Recovery %: 40%
 * - Integration Maintenance Hours/Month: 40
 * - Fully Loaded Hourly Rate: $125
 */
function applySaaSConsolidationFormula(inputs: {
  redundantToolCount: number;
  avgAnnualCostPerTool: number;
  consolidationSavingsPct: number;
  unusedLicensesValue: number;
  recoveryPct: number;
  integrationMaintenanceHoursPerMonth: number;
  hourlyRate: number;
}): number {
  const toolSavings = inputs.redundantToolCount * inputs.avgAnnualCostPerTool * inputs.consolidationSavingsPct;
  const licenseRecovery = inputs.unusedLicensesValue * inputs.recoveryPct;
  const integrationSavings = inputs.integrationMaintenanceHoursPerMonth * inputs.hourlyRate * 12;
  return toolSavings + licenseRecovery + integrationSavings;
}

/**
 * HSVF004 — Finance Close Acceleration Value
 * 
 * Example inputs:
 * - Days Saved Per Close: 3
 * - Finance Team Daily Cost: $2,000
 * - Late Adjustment Reduction %: 30%
 * - Adjustment Hours Saved Per Month: 20
 * - Hourly Rate: $100
 * - Board Report Prep Hours Saved: 15
 * - Board Cycles Per Year: 4
 */
function applyCloseAccelerationFormula(inputs: {
  daysSavedPerClose: number;
  financeTeamDailyCost: number;
  lateAdjustmentReductionPct: number;
  adjustmentHoursSavedPerMonth: number;
  hourlyRate: number;
  boardReportPrepHoursSaved: number;
  boardCyclesPerYear: number;
}): number {
  const closeSavings = inputs.daysSavedPerClose * inputs.financeTeamDailyCost * 12;
  const adjustmentSavings = inputs.lateAdjustmentReductionPct * inputs.adjustmentHoursSavedPerMonth * inputs.hourlyRate * 12;
  const boardSavings = inputs.boardReportPrepHoursSaved * inputs.hourlyRate * inputs.boardCyclesPerYear;
  return closeSavings + adjustmentSavings + boardSavings;
}

/**
 * HSVF013 — IAM Automation Value
 * 
 * Example inputs:
 * - Offboarding Hours Saved Per Event: 4
 * - Annual Terminations: 50
 * - Hourly Rate: $100
 * - Access Review Hours Saved Per Quarter: 20
 * - Orphaned Account Risk Reduction %: 80%
 * - Avg Security Incident Cost: $200,000
 * - Incident Risk Per Year: 0.5
 * - Provisioning Hours Saved Per Hire: 3
 * - Annual Hires: 100
 */
function applyIAMAutomationFormula(inputs: {
  offboardingHoursSaved: number;
  annualTerminations: number;
  hourlyRate: number;
  accessReviewHoursSavedPerQuarter: number;
  orphanedAccountRiskReductionPct: number;
  avgSecurityIncidentCost: number;
  incidentRiskPerYear: number;
  provisioningHoursSaved: number;
  annualHires: number;
}): number {
  const offboardingSavings = inputs.offboardingHoursSaved * inputs.annualTerminations * inputs.hourlyRate;
  const accessReviewSavings = inputs.accessReviewHoursSavedPerQuarter * 4 * inputs.hourlyRate;
  const riskReduction = inputs.orphanedAccountRiskReductionPct * inputs.avgSecurityIncidentCost * inputs.incidentRiskPerYear;
  const provisioningSavings = inputs.provisioningHoursSaved * inputs.annualHires * inputs.hourlyRate;
  return offboardingSavings + accessReviewSavings + riskReduction + provisioningSavings;
}

// ============================================================================
// PERSONA MATCHING UTILITY
// ============================================================================

/**
 * Match a prospect's signals to the most relevant persona.
 * Returns the top persona with match score.
 */
function matchPersona(
  prospectSignals: string[],
  personas: Persona[]
): { persona: Persona; score: number } | null {
  let bestMatch: { persona: Persona; score: number } | null = null;

  for (const persona of personas) {
    const signalMatches = prospectSignals.filter(sig =>
      persona.pressures.some(p => p.toLowerCase().includes(sig.toLowerCase())) ||
      persona.goals.some(g => g.toLowerCase().includes(sig.toLowerCase()))
    ).length;
    const score = signalMatches / prospectSignals.length;

    if (!bestMatch || score > bestMatch.score) {
      bestMatch = { persona, score };
    }
  }

  return bestMatch;
}

// ============================================================================
// BUYING TRIGGER DETECTION
// ============================================================================

interface BuyingTrigger {
  id: string;
  triggerEvent: string;
  buyerReadiness: number;
  timing: string;
  likelyPains: string[];
  recommendedApproach: string;
}

const BUYING_TRIGGERS: BuyingTrigger[] = [
  {
    id: 'HSBT001',
    triggerEvent: 'New IT Director / CIO Hire',
    buyerReadiness: 0.85,
    timing: 'First 90-120 days',
    likelyPains: ['HSP001', 'HSP002', 'HSP013', 'HSP014'],
    recommendedApproach: 'Engage immediately with IT audit and benchmarking offer. New leaders need quick wins and credible baseline assessments.'
  },
  {
    id: 'HSBT002',
    triggerEvent: 'SOC 2 Type II Audit Failure or Finding',
    buyerReadiness: 0.9,
    timing: 'Immediate (30-90 days)',
    likelyPains: ['HSP013', 'HSP014', 'HSP020'],
    recommendedApproach: 'Lead with remediation timeline and gap closure framework. Position as audit response enabler with pre-built control mappings.'
  },
  {
    id: 'HSBT003',
    triggerEvent: 'Series B/C Funding or PE Acquisition',
    buyerReadiness: 0.8,
    timing: 'Post-close 60-180 days',
    likelyPains: ['HSP001', 'HSP004', 'HSP007', 'HSP016'],
    recommendedApproach: 'Board-ready ROI framework. Emphasize scalability, governance, and operational maturity that investors expect.'
  },
  {
    id: 'HSBT004',
    triggerEvent: 'ERP Cloud Migration Announcement',
    buyerReadiness: 0.85,
    timing: 'Pre-migration planning (6-12 months)',
    likelyPains: ['HSP018', 'HSP004', 'HSP002', 'HSP016'],
    recommendedApproach: 'Position as migration companion and post-go-live governance layer. Integration and data quality are critical path items.'
  },
  {
    id: 'HSBT005',
    triggerEvent: 'M&A Integration Mandate',
    buyerReadiness: 0.9,
    timing: 'Day 1 to 12 months post-close',
    likelyPains: ['HSP001', 'HSP003', 'HSP005', 'HSP002', 'HSP013'],
    recommendedApproach: 'Unified systems integration and consolidation play. Speed to value critical. Offer M&A-specific deployment accelerators.'
  },
  {
    id: 'HSBT006',
    triggerEvent: 'Major Security Incident or Data Breach',
    buyerReadiness: 0.95,
    timing: 'Immediate (30-60 days)',
    likelyPains: ['HSP014', 'HSP013', 'HSP020'],
    recommendedApproach: 'Lead with incident response support and root cause remediation. Urgency is extreme; position as prevention investment.'
  },
  {
    id: 'HSBT007',
    triggerEvent: 'Board Mandate for Faster Reporting / Close',
    buyerReadiness: 0.85,
    timing: 'Next fiscal quarter',
    likelyPains: ['HSP004', 'HSP016', 'HSP011'],
    recommendedApproach: 'Close acceleration benchmark comparison. Show path to best-in-class with phased milestones tied to board cycles.'
  },
  {
    id: 'HSBT008',
    triggerEvent: 'SaaS Contract Renewal Concentration (>30% in 90 days)',
    buyerReadiness: 0.75,
    timing: '60-90 days before renewal wave',
    likelyPains: ['HSP019', 'HSP006', 'HSP001'],
    recommendedApproach: 'Spend optimization and contract analytics. Quick-win potential by identifying redundant or unused licenses before renewals.'
  },
  {
    id: 'HSBT009',
    triggerEvent: 'Headcount Growth >50% in 12 Months',
    buyerReadiness: 0.7,
    timing: 'During scaling (ongoing)',
    likelyPains: ['HSP005', 'HSP007', 'HSP008', 'HSP013'],
    recommendedApproach: 'Scale-ready operations play. Onboarding automation, IAM provisioning, and collaboration standardization are pain amplifiers during growth.'
  },
  {
    id: 'HSBT010',
    triggerEvent: 'CDP / Marketing Tech Investment Underperformance',
    buyerReadiness: 0.7,
    timing: 'Post-implementation review (12-24 months)',
    likelyPains: ['HSP017', 'HSP010', 'HSP002'],
    recommendedApproach: 'Activation and integration rescue mission. Position as making existing investment work rather than replacing it.'
  },
  {
    id: 'HSBT011',
    triggerEvent: 'GDPR / CCPA Enforcement Action or Complaint',
    buyerReadiness: 0.9,
    timing: 'Immediate (30-90 days)',
    likelyPains: ['HSP012', 'HSP014', 'HSP020'],
    recommendedApproach: 'Compliance remediation with data governance and residency capabilities. Legal and DPO engagement essential.'
  },
  {
    id: 'HSBT012',
    triggerEvent: 'DevOps Team Scaling / Platform Engineering Mandate',
    buyerReadiness: 0.8,
    timing: 'During team build-out (3-6 months)',
    likelyPains: ['HSP015', 'HSP002', 'HSP007'],
    recommendedApproach: 'Platform engineering enabler. Standardization and self-service reduce toil as team scales.'
  },
  {
    id: 'HSBT013',
    triggerEvent: 'Customer Support Volume Spike (>40% QoQ)',
    buyerReadiness: 0.75,
    timing: 'Immediate (current quarter)',
    likelyPains: ['HSP009', 'HSP003'],
    recommendedApproach: 'Deflection and self-service scaling. Avoid pure headcount scaling; position knowledge base and automation as sustainable solution.'
  },
  {
    id: 'HSBT014',
    triggerEvent: 'AI Governance Mandate from Board / C-Suite',
    buyerReadiness: 0.85,
    timing: '30-90 days post-mandate',
    likelyPains: ['HSP020', 'HSP014'],
    recommendedApproach: 'AI usage discovery, policy enforcement, and DLP. Position as proactive governance before shadow AI causes incident.'
  },
  {
    id: 'HSBT015',
    triggerEvent: 'Revenue Recognition Complexity Increase (Multi-element, usage-based, etc.)',
    buyerReadiness: 0.8,
    timing: 'Before next audit cycle',
    likelyPains: ['HSP004', 'HSP016', 'HSP011'],
    recommendedApproach: 'RevOps and finance automation play. Connect billing, CRM, and ERP for automated revenue recognition and forecasting.'
  }
];

// ============================================================================
// EXPORTS
// ============================================================================

export {
  SIGNAL_RULES,
  BUYING_TRIGGERS,
  calculateSaaSSpendOptimizationRate,
  calculateIntegrationSuccessRate,
  calculateDaysToClose,
  calculateFCR,
  calculateAlertSignalToNoise,
  calculateOrphanedAccountRate,
  applySaaSConsolidationFormula,
  applyCloseAccelerationFormula,
  applyIAMAutomationFormula,
  matchPersona,
};

export type {
  SignalRule,
  KPI,
  Pain,
  Persona,
  ValueFormula,
  BuyingTrigger,
};
