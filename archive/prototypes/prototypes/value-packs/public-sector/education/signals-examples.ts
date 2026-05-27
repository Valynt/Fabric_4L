/**
 * Education and Public Institutions — Signal Interpretation Examples
 * Subpack ID: education-v1
 * Parent Master ID: public-sector-master-v1
 * 
 * This file provides concrete TypeScript examples of raw signal patterns,
 * their interpretation into actionable business meanings, and linkage to
 * financially meaningful outcomes.
 */

// ============================================================================
// Core Type Definitions
// ============================================================================

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
export type FinancialOutcome = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital Improvement";
export type Segment = "K-12" | "Public Universities" | "Community Colleges" | "Research Institutions" | "Workforce Boards" | "Public Libraries";

export interface SignalThreshold {
  metric: string;
  warningThreshold: number | string;
  criticalThreshold: number | string;
  unit: string;
}

export interface RawSignalPattern {
  id: string;
  name: string;
  segment: Segment;
  thresholds: SignalThreshold[];
  dataSources: string[];
  collectionFrequency: string;
}

export interface SignalInterpretation {
  id: string;
  rawSignalId: string;
  interpretedMeaning: string;
  confidenceScore: number; // 0.00 - 1.00
  confidenceRationale: string;
  financialImpact: {
    outcome: FinancialOutcome;
    estimatedAnnualValue: string;
    valueBasis: string;
  };
  requiredConfirmationSignals: string[];
  linkedPainId: string;
  linkedKPIs: string[];
  linkedFormulaId: string;
  personaTrigger: string; // Which persona should be alerted
  recommendedAction: string;
}

// ============================================================================
// Signal Threshold Definitions
// ============================================================================

export const EDU_SIGNAL_THRESHOLDS: RawSignalPattern[] = [
  {
    id: "EDU-RAW-101",
    name: "SIS Data Fragmentation",
    segment: "K-12",
    thresholds: [
      { metric: "Duplicate_Student_Records_Rate", warningThreshold: "5%", criticalThreshold: "10%", unit: "percentage" },
      { metric: "Nightly_Sync_Failure_Rate", warningThreshold: "3%", criticalThreshold: "8%", unit: "percentage" },
      { metric: "Manual_Roster_Upload_Systems", warningThreshold: 5, criticalThreshold: 12, unit: "count" }
    ],
    dataSources: ["SIS audit logs", "State reporting error reports", "API gateway monitoring"],
    collectionFrequency: "daily"
  },
  {
    id: "EDU-RAW-102",
    name: "Financial Aid Verification Bottleneck",
    segment: "Public Universities",
    thresholds: [
      { metric: "Verification_Queue_Depth", warningThreshold: 250, criticalThreshold: 500, unit: "files" },
      { metric: "Disbursement_Delay_Days", warningThreshold: 30, criticalThreshold: 45, unit: "days" },
      { metric: "Verification_Selection_Rate", warningThreshold: "35%", criticalThreshold: "45%", unit: "percentage" }
    ],
    dataSources: ["Aid office queue reports", "COD reconciliation", "Student complaint log"],
    collectionFrequency: "weekly"
  },
  {
    id: "EDU-RAW-103",
    name: "Research Grant Admin Strain",
    segment: "Research Institutions",
    thresholds: [
      { metric: "Grant_Admin_FTE_per_$2M", warningThreshold: 1.0, criticalThreshold: 1.5, unit: "FTE" },
      { metric: "Effort_Reporting_Correction_Rate", warningThreshold: "15%", criticalThreshold: "25%", unit: "percentage" },
      { metric: "Closeout_Backlog_Months", warningThreshold: 9, criticalThreshold: 15, unit: "months" }
    ],
    dataSources: ["Sponsored programs workload reports", "Effort reporting audit", "Closeout tracker"],
    collectionFrequency: "monthly"
  },
  {
    id: "EDU-RAW-104",
    name: "Degree Completion Gap",
    segment: "Public Universities",
    thresholds: [
      { metric: "Avg_Credits_at_Graduation", warningThreshold: 130, criticalThreshold: 140, unit: "credits" },
      { metric: "Time_to_Degree_Over_5_Years", warningThreshold: "30%", criticalThreshold: "45%", unit: "percentage" },
      { metric: "First_Year_Stopout_Rate", warningThreshold: "20%", criticalThreshold: "30%", unit: "percentage" }
    ],
    dataSources: ["Degree audit system", "IPEDS reporting", "Student retention dashboards"],
    collectionFrequency: "termly"
  },
  {
    id: "EDU-RAW-105",
    name: "Campus Safety Compliance Gap",
    segment: "Public Universities",
    thresholds: [
      { metric: "Title_IX_Resolution_Days", warningThreshold: 60, criticalThreshold: 120, unit: "days" },
      { metric: "ASR_Days_Past_Oct1", warningThreshold: 5, criticalThreshold: 30, unit: "days" },
      { metric: "Emergency_Notification_Test_Days_Since_Last", warningThreshold: 90, criticalThreshold: 180, unit: "days" }
    ],
    dataSources: ["Title IX case tracker", "Clery geography audit", "Emergency notification test log"],
    collectionFrequency: "monthly"
  },
  {
    id: "EDU-RAW-106",
    name: "K-12 Teacher Crisis",
    segment: "K-12",
    thresholds: [
      { metric: "Teacher_Vacancy_Rate", warningThreshold: "5%", criticalThreshold: "10%", unit: "percentage" },
      { metric: "Substitute_Fill_Rate", warningThreshold: "85%", criticalThreshold: "70%", unit: "percentage" },
      { metric: "New_Teacher_Year1_Turnover", warningThreshold: "20%", criticalThreshold: "35%", unit: "percentage" }
    ],
    dataSources: ["HR vacancy reports", "Substitute management system", "Turnover analysis"],
    collectionFrequency: "monthly"
  },
  {
    id: "EDU-RAW-107",
    name: "ESSER Spend-Down Risk",
    segment: "K-12",
    thresholds: [
      { metric: "Unspent_Balance_Percent_at_12mo_to_Deadline", warningThreshold: "15%", criticalThreshold: "25%", unit: "percentage" },
      { metric: "Procurement_Days_to_Deadline", warningThreshold: 180, criticalThreshold: 90, unit: "days" },
      { metric: "Documentation_Gap_Rate", warningThreshold: "10%", criticalThreshold: "20%", unit: "percentage" }
    ],
    dataSources: ["ESSER tracking dashboard", "ED.gov comparison", "Procurement schedule"],
    collectionFrequency: "weekly"
  },
  {
    id: "EDU-RAW-108",
    name: "EdTech Privacy Exposure",
    segment: "K-12",
    thresholds: [
      { metric: "Unvetted_App_Count", warningThreshold: 20, criticalThreshold: 50, unit: "count" },
      { metric: "FERPA_Training_Completion_Rate", warningThreshold: "70%", criticalThreshold: "50%", unit: "percentage" },
      { metric: "Breach_Notifications_12mo", warningThreshold: 1, criticalThreshold: 3, unit: "count" }
    ],
    dataSources: ["App inventory", "FERPA training records", "Vendor breach notifications"],
    collectionFrequency: "monthly"
  },
  {
    id: "EDU-RAW-109",
    name: "WIOA Reporting Chaos",
    segment: "Workforce Boards",
    thresholds: [
      { metric: "Quarterly_Report_Hours", warningThreshold: 40, criticalThreshold: 80, unit: "hours" },
      { metric: "Wage_Record_Match_Rate", warningThreshold: "90%", criticalThreshold: "80%", unit: "percentage" },
      { metric: "Follow_Up_Loss_Rate", warningThreshold: "15%", criticalThreshold: "25%", unit: "percentage" }
    ],
    dataSources: ["Quarterly report time log", "Wage record match report", "Follow-up attempt log"],
    collectionFrequency: "quarterly"
  },
  {
    id: "EDU-RAW-110",
    name: "Special Education Compliance Risk",
    segment: "K-12",
    thresholds: [
      { metric: "IEP_Meeting_Past_Deadline_Rate", warningThreshold: "5%", criticalThreshold: "15%", unit: "percentage" },
      { metric: "Service_Delivery_Minutes_Missed", warningThreshold: "10%", criticalThreshold: "20%", unit: "percentage" },
      { metric: "Due_Process_Complaints_12mo", warningThreshold: 2, criticalThreshold: 6, unit: "count" }
    ],
    dataSources: ["IEP deadline tracker", "Service delivery log", "Due process complaint log"],
    collectionFrequency: "monthly"
  },
  {
    id: "EDU-RAW-111",
    name: "Research DMP Noncompliance",
    segment: "Research Institutions",
    thresholds: [
      { metric: "DMP_First_Submission_Approval_Rate", warningThreshold: "85%", criticalThreshold: "70%", unit: "percentage" },
      { metric: "Grants_Without_Data_Retention_Plan", warningThreshold: "20%", criticalThreshold: "35%", unit: "percentage" },
      { metric: "Faculty_Repository_Adoption", warningThreshold: "50%", criticalThreshold: "30%", unit: "percentage" }
    ],
    dataSources: ["DMP submission log", "Repository adoption data", "Award compliance audit"],
    collectionFrequency: "quarterly"
  },
  {
    id: "EDU-RAW-112",
    name: "Library Digital Access Strain",
    segment: "Public Libraries",
    thresholds: [
      { metric: "Device_Waitlist_Days", warningThreshold: 7, criticalThreshold: 14, unit: "days" },
      { metric: "Hotspot_Checkout_Hours_to_Limit", warningThreshold: 72, criticalThreshold: 48, unit: "hours" },
      { metric: "Digital_Class_Over_Enrollment_Rate", warningThreshold: "25%", criticalThreshold: "50%", unit: "percentage" }
    ],
    dataSources: ["Device/hotspot checkout log", "Class enrollment data", "Patron survey"],
    collectionFrequency: "weekly"
  },
  {
    id: "EDU-RAW-113",
    name: "Enrollment Cliff Signal",
    segment: "Public Universities",
    thresholds: [
      { metric: "First_Time_Freshman_YoY_Decline", warningThreshold: "3%", criticalThreshold: "7%", unit: "percentage" },
      { metric: "Discount_Rate_Incoming_Class", warningThreshold: "45%", criticalThreshold: "55%", unit: "percentage" },
      { metric: "Net_Tuition_Revenue_Per_FTE_Trend", warningThreshold: "-2%", criticalThreshold: "-5%", unit: "percentage" }
    ],
    dataSources: ["Enrollment reports", "Net tuition analysis", "WICHE demographic projections"],
    collectionFrequency: "termly"
  },
  {
    id: "EDU-RAW-114",
    name: "Student Mental Health Crisis",
    segment: "Public Universities",
    thresholds: [
      { metric: "Counseling_Center_Waitlist_Days", warningThreshold: 14, criticalThreshold: 28, unit: "days" },
      { metric: "Crisis_Appointment_Percentage", warningThreshold: "15%", criticalThreshold: "25%", unit: "percentage" },
      { metric: "Behavioral_Incident_YoY_Increase", warningThreshold: "10%", criticalThreshold: "20%", unit: "percentage" }
    ],
    dataSources: ["Counseling center waitlist data", "Crisis appointment log", "Behavioral incident report"],
    collectionFrequency: "weekly"
  },
  {
    id: "EDU-RAW-115",
    name: "State/Federal Reporting Burden",
    segment: "K-12",
    thresholds: [
      { metric: "SLDS_Coverage_Percentage", warningThreshold: "85%", criticalThreshold: "70%", unit: "percentage" },
      { metric: "Federal_Report_Error_Rate", warningThreshold: "3%", criticalThreshold: "8%", unit: "percentage" },
      { metric: "Data_Certification_Hours", warningThreshold: 100, criticalThreshold: 250, unit: "hours" }
    ],
    dataSources: ["SLDS gap analysis", "Federal report error log", "Time tracking for certification"],
    collectionFrequency: "per reporting cycle"
  },
  {
    id: "EDU-RAW-116",
    name: "Facilities Deferred Maintenance",
    segment: "K-12",
    thresholds: [
      { metric: "Deferred_Maintenance_Backlog", warningThreshold: 25000000, criticalThreshold: 50000000, unit: "USD" },
      { metric: "Energy_Cost_Per_SqFt_vs_EPA_Benchmark", warningThreshold: "20%", criticalThreshold: "35%", unit: "percentage above" },
      { metric: "HVAC_Age_Over_20_Years_Percentage", warningThreshold: "50%", criticalThreshold: "70%", unit: "percentage" }
    ],
    dataSources: ["Facilities condition assessment", "Energy audit", "Deferred maintenance ledger"],
    collectionFrequency: "annual"
  },
  {
    id: "EDU-RAW-117",
    name: "Transfer Credit Loss",
    segment: "Community Colleges",
    thresholds: [
      { metric: "Transfer_Credit_Acceptance_Rate", warningThreshold: "75%", criticalThreshold: "60%", unit: "percentage" },
      { metric: "Avg_Credits_Lost_Per_Transfer", warningThreshold: 15, criticalThreshold: 25, unit: "credits" },
      { metric: "Articulation_Agreement_Coverage", warningThreshold: "60%", criticalThreshold: "40%", unit: "percentage" }
    ],
    dataSources: ["Transfer credit audit", "Articulation agreement inventory", "Transfer student graduation data"],
    collectionFrequency: "annual"
  },
  {
    id: "EDU-RAW-118",
    name: "IR / Accreditation Reporting Backlog",
    segment: "Public Universities",
    thresholds: [
      { metric: "Accreditation_Self_Study_Hours", warningThreshold: 1500, criticalThreshold: 2500, unit: "hours" },
      { metric: "IPEDS_Error_Rate", warningThreshold: "2%", criticalThreshold: "5%", unit: "percentage" },
      { metric: "Ad_Hoc_Report_Backlog_Days", warningThreshold: 14, criticalThreshold: 35, unit: "days" }
    ],
    dataSources: ["Self-study hour log", "IPEDS feedback report", "Ad hoc request tracker"],
    collectionFrequency: "monthly"
  }
];

// ============================================================================
// Signal Interpretation Examples
// ============================================================================

export const EDU_SIGNAL_INTERPRETATIONS: SignalInterpretation[] = [
  {
    id: "EDU-INT-101",
    rawSignalId: "EDU-RAW-101",
    interpretedMeaning: "The district's student data ecosystem is highly fragmented, with duplicate records affecting intervention accuracy and nightly sync failures forcing manual workarounds. This creates a data governance maturity gap that will compound as edtech adoption increases.",
    confidenceScore: 0.85,
    confidenceRationale: "HIGH confidence because duplicate record rates, sync failure logs, and manual upload counts are objectively measurable from system telemetry. MEDIUM confidence on intervention delay value because it requires correlation analysis.",
    financialImpact: {
      outcome: "Cost Savings",
      estimatedAnnualValue: "$1.5M - $3.5M (for 25K-student district)",
      valueBasis: "State reporting labor ($600K-$1M) + roster remediation ($500K-$2M) + intervention delay ($200K-$500K). Formula: EDU-VF-101."
    },
    requiredConfirmationSignals: [
      "System inventory confirming 50+ disconnected systems",
      "Data quality audit showing duplicate record root causes",
      "State reporting feedback showing error categories",
      "API gateway logs showing sync failure patterns"
    ],
    linkedPainId: "EDU-PAIN-101",
    linkedKPIs: ["EDU-KPI-101", "EDU-KPI-102", "EDU-KPI-103"],
    linkedFormulaId: "EDU-VF-101",
    personaTrigger: "EDU-PERS-101 (University CIO) / EDU-PERS-102 (K-12 Superintendent)",
    recommendedAction: "Initiate data governance assessment and integration platform RFI. Prioritize real-time API connections for highest-impact systems (SIS-LMS, SIS-assessment, SIS-transportation)."
  },
  {
    id: "EDU-INT-102",
    rawSignalId: "EDU-RAW-102",
    interpretedMeaning: "The financial aid office is operating beyond capacity, with verification queues creating disbursement delays that directly threaten student retention. Title IV compliance risk is elevated due to manual R2T4 calculations and COD reconciliation gaps.",
    confidenceScore: 0.88,
    confidenceRationale: "HIGH confidence because queue depth, disbursement dates, and verification rates are directly measurable from aid office systems. HIGH confidence on retention correlation because NASFAA and institutional studies consistently link delay to stop-out.",
    financialImpact: {
      outcome: "Working Capital Improvement",
      estimatedAnnualValue: "$2M - $6M (for 15K-applicant university)",
      valueBasis: "Retention revenue from faster disbursement ($1.5M-$5M) + late penalty avoidance ($200K-$500K) + staff efficiency ($200K-$500K). Formula: EDU-VF-102."
    },
    requiredConfirmationSignals: [
      "Aid office queue report showing average age of verification files",
      "COD reconciliation report showing unmatched disbursements",
      "Student complaint log showing aid-related withdrawals",
      "Disbursement schedule showing delay distribution by student segment"
    ],
    linkedPainId: "EDU-PAIN-102",
    linkedKPIs: ["EDU-KPI-104", "EDU-KPI-105", "EDU-KPI-106"],
    linkedFormulaId: "EDU-VF-102",
    personaTrigger: "EDU-PERS-104 (Financial Aid Director)",
    recommendedAction: "Deploy automated verification document processing (OCR + ISIR matching). Implement predictive verification selection to prioritize high-risk students. Establish weekly disbursement delay dashboard with executive escalation."
  },
  {
    id: "EDU-INT-103",
    rawSignalId: "EDU-RAW-103",
    interpretedMeaning: "Research administration is under-resourced relative to award volume, with effort reporting errors and closeout backlogs indicating compliance process breakdown. Investigator satisfaction is likely declining, and indirect cost recovery is leaking due to inadequate post-award oversight.",
    confidenceScore: 0.82,
    confidenceRationale: "HIGH confidence on FTE-to-expenditure ratio because NCSES publishes this benchmark. HIGH confidence on closeout backlog because it is auditable. MEDIUM confidence on recovery leakage because it requires financial system cross-check.",
    financialImpact: {
      outcome: "Cost Savings",
      estimatedAnnualValue: "$8M - $30M (for $350M research university)",
      valueBasis: "Admin cost reduction ($10M-$20M) + effort error avoidance ($500K-$2M) + closeout working capital recovery ($3M-$10M). Formula: EDU-VF-103."
    },
    requiredConfirmationSignals: [
      "Sponsored programs staffing analysis with FTE per $1M benchmarked to peers",
      "Effort reporting audit showing correction categories and root causes",
      "Closeout backlog report with award age and sponsor type breakdown",
      "Indirect cost recovery analysis showing negotiated vs. actual recovery rates"
    ],
    linkedPainId: "EDU-PAIN-103",
    linkedKPIs: ["EDU-KPI-107", "EDU-KPI-108", "EDU-KPI-109"],
    linkedFormulaId: "EDU-VF-103",
    personaTrigger: "EDU-PERS-103 (Research Administrator)",
    recommendedAction: "Implement integrated pre-award to post-award research administration platform. Automate effort reporting with payroll integration. Establish closeout SWAT team for awards >12 months expired."
  },
  {
    id: "EDU-INT-104",
    rawSignalId: "EDU-RAW-104",
    interpretedMeaning: "Students are accumulating excess credits and extending time-to-degree due to unclear degree paths, inadequate advising, and transfer credit loss. This erodes net tuition revenue per FTE and exhausts financial aid eligibility before graduation.",
    confidenceScore: 0.85,
    confidenceRationale: "HIGH confidence on credit accumulation and time-to-degree because these are standard IPEDS metrics. MEDIUM confidence on stop-out causation because it requires multivariate analysis (financial, academic, personal factors).",
    financialImpact: {
      outcome: "Revenue Uplift",
      estimatedAnnualValue: "$5M - $20M (for 20K-student university)",
      valueBasis: "Retention revenue from faster completion ($3M-$15M) + excess credit reduction subsidy savings ($1M-$3M) + advising efficiency ($500K-$2M). Formula: EDU-VF-104."
    },
    requiredConfirmationSignals: [
      "Degree audit exceptions report showing most common unmet requirements",
      "Advising caseload data with advisor-to-student ratios",
      "Transfer credit audit showing loss patterns by sending institution",
      "Financial aid exhaustion report correlating with stop-out timing"
    ],
    linkedPainId: "EDU-PAIN-104",
    linkedKPIs: ["EDU-KPI-110", "EDU-KPI-111", "EDU-KPI-112"],
    linkedFormulaId: "EDU-VF-104",
    personaTrigger: "EDU-PERS-105 (Registrar / Enrollment Manager)",
    recommendedAction: "Deploy predictive degree audit with real-time course recommendations. Implement guided pathways for top 10 programs. Establish reverse transfer agreements with feeder community colleges."
  },
  {
    id: "EDU-INT-105",
    rawSignalId: "EDU-RAW-105",
    interpretedMeaning: "Campus safety compliance infrastructure is fragmented and manual, creating significant litigation and regulatory exposure. Title IX case delays beyond 60 days increase complainant dissatisfaction and ED OCR complaint likelihood. Late ASR publication is a direct Clery Act violation.",
    confidenceScore: 0.80,
    confidenceRationale: "HIGH confidence on ASR timeliness because publication date is public. HIGH confidence on Title IX resolution time if case management system tracks dates. MEDIUM confidence on emergency notification testing because logs may be incomplete.",
    financialImpact: {
      outcome: "Risk Reduction",
      estimatedAnnualValue: "$500K - $3M annually",
      valueBasis: "OCR investigation avoidance ($500K-$2M) + Clery penalty avoidance ($100K-$500K) + litigation settlement reduction ($200K-$1M). Formula: EDU-VF-105."
    },
    requiredConfirmationSignals: [
      "Clery geography audit confirming all required locations mapped",
      "Title IX case tracker showing resolution time distribution",
      "ASR publication history with date relative to Oct 1 deadline",
      "Emergency notification test log with multi-channel confirmation"
    ],
    linkedPainId: "EDU-PAIN-105",
    linkedKPIs: ["EDU-KPI-113", "EDU-KPI-114", "EDU-KPI-115"],
    linkedFormulaId: "EDU-VF-105",
    personaTrigger: "EDU-PERS-106 (Campus Safety Chief)",
    recommendedAction: "Implement integrated Clery geography mapping with automated crime statistics aggregation. Deploy Title IX case workflow with automated deadline alerts. Schedule mandatory multi-channel emergency notification tests each semester."
  },
  {
    id: "EDU-INT-106",
    rawSignalId: "EDU-RAW-106",
    interpretedMeaning: "The district faces a structural teacher workforce shortage with vacancy rates exceeding sustainable thresholds. Low substitute fill rates indicate instructional disruption, and high new teacher turnover suggests onboarding and support gaps. Emergency credential growth threatens instructional quality.",
    confidenceScore: 0.87,
    confidenceRationale: "HIGH confidence on vacancy and substitute fill rates because these are standard HR metrics. HIGH confidence on turnover because payroll/HRIS data is auditable. MEDIUM confidence on emergency credential impact because it requires longitudinal student outcome data.",
    financialImpact: {
      outcome: "Cost Savings",
      estimatedAnnualValue: "$1M - $4M annually (for 25K-student district)",
      valueBasis: "Vacancy cost reduction ($500K-$2M) + replacement cost avoidance ($300K-$1M) + substitute optimization ($200K-$1M). Formula: EDU-VF-106."
    },
    requiredConfirmationSignals: [
      "HR vacancy report with subject area and school-level breakdown",
      "Substitute fill data by day of week and subject area",
      "Offer/acceptance tracking with competitive district comparison",
      "Turnover analysis by year of service showing new teacher flight pattern"
    ],
    linkedPainId: "EDU-PAIN-106",
    linkedKPIs: ["EDU-KPI-116", "EDU-KPI-117", "EDU-KPI-118"],
    linkedFormulaId: "EDU-VF-106",
    personaTrigger: "EDU-PERS-102 (K-12 Superintendent)",
    recommendedAction: "Deploy teacher pipeline analytics with predictive vacancy modeling. Implement substitute management platform with real-time fill optimization. Launch retention incentive program for Years 1-3 teachers with mentorship pairing."
  },
  {
    id: "EDU-INT-107",
    rawSignalId: "EDU-RAW-107",
    interpretedMeaning: "The district is at elevated risk of ESSER fund clawback due to slow obligation velocity and documentation gaps. Rushed procurement in the final months may violate competitive bidding requirements, triggering additional compliance findings from ED-OIG.",
    confidenceScore: 0.90,
    confidenceRationale: "HIGH confidence because ED.gov publishes real-time obligation data. HIGH confidence on clawback risk because statutory deadlines are fixed. HIGH confidence on documentation gaps because supplement-not-supplant is auditable.",
    financialImpact: {
      outcome: "Working Capital Improvement",
      estimatedAnnualValue: "$1M - $10M (one-time fund retention)",
      valueBasis: "Clawback avoidance ($1M-$10M direct) + audit cost avoidance ($200K-$500K) + administrative efficiency ($100K-$300K). Formula: EDU-VF-107."
    },
    requiredConfirmationSignals: [
      "ESSER tracking dashboard showing obligation rate by fund source",
      "ED.gov dashboard comparison to peer districts",
      "Procurement schedule showing items planned vs. obligated",
      "Supplement-not-supplant documentation sample audit"
    ],
    linkedPainId: "EDU-PAIN-107",
    linkedKPIs: ["EDU-KPI-119", "EDU-KPI-120"],
    linkedFormulaId: "EDU-VF-107",
    personaTrigger: "EDU-PERS-102 (K-12 Superintendent)",
    recommendedAction: "Implement ESSER obligation tracking dashboard with weekly executive review. Expedite procurement for remaining items using cooperative contracts. Conduct supplement-not-supplant documentation audit with external validation."
  },
  {
    id: "EDU-INT-108",
    rawSignalId: "EDU-RAW-108",
    interpretedMeaning: "The district lacks centralized edtech app governance, exposing student data to privacy violations and potential FERPA breaches. The combination of unvetted apps, incomplete FERPA training, and prior breach history creates compounding regulatory and reputational risk.",
    confidenceScore: 0.78,
    confidenceRationale: "HIGH confidence on app count and vetting rate because app catalogs are auditable. HIGH confidence on FERPA training completion because LMS/HR systems track this. MEDIUM confidence on breach recurrence because vendor security practices vary.",
    financialImpact: {
      outcome: "Risk Reduction",
      estimatedAnnualValue: "$500K - $3M annually",
      valueBasis: "Breach probability reduction ($300K-$2M) + FERPA complaint avoidance ($100K-$500K) + app vetting labor savings ($50K-$300K). Formula: EDU-VF-108."
    },
    requiredConfirmationSignals: [
      "Complete app inventory with usage analytics",
      "FERPA training completion records by role",
      "Vendor breach notification history with impact assessment",
      "Data processing agreement repository completeness check"
    ],
    linkedPainId: "EDU-PAIN-108",
    linkedKPIs: ["EDU-KPI-121", "EDU-KPI-122"],
    linkedFormulaId: "EDU-VF-108",
    personaTrigger: "EDU-PERS-101 (University CIO) / EDU-PERS-102 (K-12 Superintendent)",
    recommendedAction: "Deploy centralized app governance platform with automated privacy vetting. Implement mandatory FERPA training for all staff with app approval authority. Establish data-sharing agreement repository with annual vendor recertification."
  },
  {
    id: "EDU-INT-109",
    rawSignalId: "EDU-RAW-109",
    interpretedMeaning: "Workforce board data systems are fragmented, requiring excessive manual effort for quarterly WIOA reporting. Low wage record match rates and high follow-up loss rates indicate performance tracking breakdown that threatens DOL performance funding and triggers audit findings.",
    confidenceScore: 0.83,
    confidenceRationale: "HIGH confidence on report hours and wage match rate because these are directly measurable from DOL reports. MEDIUM confidence on follow-up loss because it depends on participant contact information quality.",
    financialImpact: {
      outcome: "Cost Savings",
      estimatedAnnualValue: "$300K - $1M annually",
      valueBasis: "Reporting labor reduction ($100K-$300K) + wage match improvement ($100K-$400K) + performance funding protection ($100K-$300K). Formula: EDU-VF-109."
    },
    requiredConfirmationSignals: [
      "Quarterly report time log with task breakdown",
      "Wage record match report with unmatched record analysis",
      "Follow-up attempt log showing contact method and success rate",
      "Performance audit findings with recurring issue categories"
    ],
    linkedPainId: "EDU-PAIN-109",
    linkedKPIs: ["EDU-KPI-123", "EDU-KPI-124", "EDU-KPI-125"],
    linkedFormulaId: "EDU-VF-109",
    personaTrigger: "EDU-PERS-105 (Registrar / Enrollment Manager — for Workforce Boards, Program Director)",
    recommendedAction: "Integrate case management system with state wage record database. Implement automated credential attainment tracking across training providers. Deploy participant follow-up platform with multi-channel contact cadence."
  },
  {
    id: "EDU-INT-110",
    rawSignalId: "EDU-RAW-110",
    interpretedMeaning: "Special education compliance processes are breaking down with missed IEP deadlines and service delivery gaps. Increasing due process complaints indicate parent dissatisfaction and rising litigation risk. State OSEP monitoring is likely imminent.",
    confidenceScore: 0.85,
    confidenceRationale: "HIGH confidence on IEP deadline and service delivery metrics because these are tracked in IEP systems. HIGH confidence on due process complaints because they are public records. MEDIUM confidence on state monitoring timing because it depends on complaint volume thresholds.",
    financialImpact: {
      outcome: "Risk Reduction",
      estimatedAnnualValue: "$200K - $800K annually",
      valueBasis: "Due process complaint avoidance ($150K-$500K) + mediation cost reduction ($30K-$150K) + IEP meeting efficiency ($20K-$100K). Formula: EDU-VF-110."
    },
    requiredConfirmationSignals: [
      "IEP deadline tracker with school-level and disability category breakdown",
      "Related service delivery log showing minutes scheduled vs. delivered",
      "Due process complaint log with resolution cost and outcome",
      "OSEP monitoring report or state corrective action history"
    ],
    linkedPainId: "EDU-PAIN-110",
    linkedKPIs: ["EDU-KPI-103", "EDU-KPI-116"],
    linkedFormulaId: "EDU-VF-110",
    personaTrigger: "EDU-PERS-102 (K-12 Superintendent)",
    recommendedAction: "Deploy IEP management platform with automated deadline alerts and service scheduling. Implement parent portal for real-time IEP progress visibility. Conduct special ed staffing analysis with therapist scheduling optimization."
  },
  {
    id: "EDU-INT-111",
    rawSignalId: "EDU-RAW-111",
    interpretedMeaning: "Research data management infrastructure is inadequate for current federal requirements. Low DMP approval rates delay proposal submissions, and incomplete repository adoption threatens compliance with the 2023 NIH Data Management and Sharing Policy.",
    confidenceScore: 0.80,
    confidenceRationale: "HIGH confidence on DMP approval rate because it is tracked by sponsored programs. HIGH confidence on repository adoption because authentication logs are auditable. MEDIUM confidence on award termination risk because it depends on sponsor enforcement patterns.",
    financialImpact: {
      outcome: "Working Capital Improvement",
      estimatedAnnualValue: "$500K - $3M annually",
      valueBasis: "DMP revision cost avoidance ($200K-$1M) + repository storage savings ($100K-$500K) + funding suspension risk ($200K-$1.5M). Formula: EDU-VF-111."
    },
    requiredConfirmationSignals: [
      "DMP submission log with approval iteration count",
      "Repository adoption data with faculty discipline breakdown",
      "Active award compliance audit showing DMP presence",
      "Investigator survey on DMP burden and repository usability"
    ],
    linkedPainId: "EDU-PAIN-111",
    linkedKPIs: ["EDU-KPI-107", "EDU-KPI-108"],
    linkedFormulaId: "EDU-VF-111",
    personaTrigger: "EDU-PERS-103 (Research Administrator)",
    recommendedAction: "Implement DMP template library with sponsor-specific compliance checklists. Deploy institutional repository with automated metadata extraction. Integrate ORCID with faculty profile system for persistent identifier adoption."
  },
  {
    id: "EDU-INT-112",
    rawSignalId: "EDU-RAW-112",
    interpretedMeaning: "The library is operating as a digital safety net with demand significantly exceeding supply. Patrons face weeks-long waits for devices and hours-long waits for hotspots, indicating unmet community digital equity needs that may affect employment, education, and healthcare access.",
    confidenceScore: 0.75,
    confidenceRationale: "HIGH confidence on waitlist and checkout metrics because these are directly tracked in circulation systems. MEDIUM confidence on community impact because it requires patron survey data. LOW confidence on federal program compliance because BEAD requirements are still evolving.",
    financialImpact: {
      outcome: "Cost Savings",
      estimatedAnnualValue: "$200K - $2M annually",
      valueBasis: "Hotspot program expansion ($100K-$500K) + digital skills class capacity increase ($50K-$200K) + broadband substitution value ($50K-$1.3M). Formula: EDU-VF-112."
    },
    requiredConfirmationSignals: [
      "Device and hotspot checkout log with waitlist depth over time",
      "Digital skills class enrollment vs. capacity data",
      "Patron survey on primary internet access reliance",
      "BEAD/digital equity plan requirements for library participation"
    ],
    linkedPainId: "EDU-PAIN-112",
    linkedKPIs: ["EDU-KPI-125"],
    linkedFormulaId: "EDU-VF-112",
    personaTrigger: "EDU-PERS-102 (K-12 Superintendent — for library system directors)",
    recommendedAction: "Expand hotspot lending program with carrier partnership. Deploy device lending with self-service kiosk. Launch digital navigator training for library staff. Apply for NTIA BEAD digital equity subgrant."
  },
  {
    id: "EDU-INT-113",
    rawSignalId: "EDU-RAW-113",
    interpretedMeaning: "The institution is entering a structural enrollment decline driven by demographic shifts and competitive pricing pressure. Rising discount rates mask net tuition erosion, and program closures are imminent without strategic intervention. This is a multi-year existential threat, not a cyclical downturn.",
    confidenceScore: 0.88,
    confidenceRationale: "HIGH confidence on enrollment decline because IPEDS data is authoritative. HIGH confidence on discount rate because it is reported to CDS. HIGH confidence on demographic projections because WICHE data is widely validated.",
    financialImpact: {
      outcome: "Revenue Uplift",
      estimatedAnnualValue: "$3M - $15M annually",
      valueBasis: "Retention improvement ($2M-$10M) + discount rate optimization ($500K-$3M) + program rationalization savings ($500K-$2M). Formula: EDU-VF-104."
    },
    requiredConfirmationSignals: [
      "Enrollment reports with first-time freshman and transfer trends",
      "Net tuition analysis with discount rate and discounting policy",
      "WICHE state-level demographic projections",
      "Competitive market analysis with peer discount rates"
    ],
    linkedPainId: "EDU-PAIN-113",
    linkedKPIs: ["EDU-KPI-110", "EDU-KPI-111", "EDU-KPI-112"],
    linkedFormulaId: "EDU-VF-104",
    personaTrigger: "EDU-PERS-105 (Registrar / Enrollment Manager) / EDU-PERS-102 (President/Provost)",
    recommendedAction: "Deploy predictive enrollment analytics with demographic pipeline modeling. Implement dynamic financial aid optimization. Launch adult/online program expansion with workforce-aligned credentials."
  },
  {
    id: "EDU-INT-114",
    rawSignalId: "EDU-RAW-114",
    interpretedMeaning: "Student mental health demand has exceeded counseling center capacity, with crisis appointments consuming an unsustainable share of clinical resources. Untreated mental health needs correlate with academic withdrawal and completion failure, creating both humanitarian and financial risk.",
    confidenceScore: 0.82,
    confidenceRationale: "HIGH confidence on waitlist and crisis appointment metrics because counseling centers track these. MEDIUM confidence on retention correlation because it requires longitudinal student-level data. MEDIUM confidence on liability exposure because it depends on incident history.",
    financialImpact: {
      outcome: "Risk Reduction",
      estimatedAnnualValue: "$500K - $3M annually",
      valueBasis: "Retention improvement from treated mental health ($300K-$2M) + liability exposure reduction ($100K-$500K) + crisis response efficiency ($50K-$300K). Formula: EDU-VF-105 (adapted)."
    },
    requiredConfirmationSignals: [
      "Counseling center waitlist data with triage category breakdown",
      "Crisis appointment log with follow-up and referral outcomes",
      "Behavioral incident report with mental health correlation",
      "Retention analysis comparing students with/without counseling utilization"
    ],
    linkedPainId: "EDU-PAIN-114",
    linkedKPIs: ["EDU-KPI-113", "EDU-KPI-115"],
    linkedFormulaId: "EDU-VF-105",
    personaTrigger: "EDU-PERS-106 (Campus Safety Chief) / Student Affairs VP",
    recommendedAction: "Expand counseling center capacity with telehealth partnership. Implement stepped-care model with peer counselors and digital tools. Deploy early alert system with faculty/staff referral pathways."
  },
  {
    id: "EDU-INT-115",
    rawSignalId: "EDU-RAW-115",
    interpretedMeaning: "State and federal reporting infrastructure is fragmented, with significant manual reconciliation required for each submission cycle. High error rates trigger resubmission and audit findings, while excessive certification hours consume institutional research capacity that could support strategic decision-making.",
    confidenceScore: 0.85,
    confidenceRationale: "HIGH confidence on SLDS coverage and error rates because state audits provide this. HIGH confidence on certification hours because time tracking is standard. MEDIUM confidence on strategic impact because it requires IR workload analysis.",
    financialImpact: {
      outcome: "Cost Savings",
      estimatedAnnualValue: "$200K - $1.5M annually",
      valueBasis: "Reporting labor reduction ($150K-$800K) + error correction avoidance ($30K-$300K) + audit finding prevention ($20K-$400K). Formula: EDU-VF-101."
    },
    requiredConfirmationSignals: [
      "SLDS gap analysis showing missing data elements",
      "Federal report error log with category and correction time",
      "Time tracking for certification by staff role",
      "State audit findings with recurring issue patterns"
    ],
    linkedPainId: "EDU-PAIN-115",
    linkedKPIs: ["EDU-KPI-101", "EDU-KPI-102", "EDU-KPI-103"],
    linkedFormulaId: "EDU-VF-101",
    personaTrigger: "EDU-PERS-101 (University CIO) / EDU-PERS-105 (Registrar)",
    recommendedAction: "Implement state longitudinal data system integration with automated element mapping. Deploy federal reporting automation platform with pre-validation. Establish data governance council with cross-functional representation."
  },
  {
    id: "EDU-INT-116",
    rawSignalId: "EDU-RAW-116",
    interpretedMeaning: "Facilities are aging with significant deferred maintenance backlog and energy inefficiency. The combination of old HVAC systems, high energy costs, and reactive maintenance dominance creates indoor environment quality risks and operating budget strain that will worsen without capital investment.",
    confidenceScore: 0.88,
    confidenceRationale: "HIGH confidence on deferred maintenance backlog because condition assessments are standard. HIGH confidence on energy costs because utility bills are auditable. HIGH confidence on HVAC age because asset registries track this.",
    financialImpact: {
      outcome: "Cost Savings",
      estimatedAnnualValue: "$1M - $8M annually",
      valueBasis: "Energy savings ($500K-$3M) + deferred maintenance avoidance ($300K-$3M) + emergency repair reduction ($200K-$2M). Formula: EDU-VF-113."
    },
    requiredConfirmationSignals: [
      "Facilities condition assessment with building-by-building scores",
      "Energy audit with end-use breakdown and benchmark comparison",
      "Deferred maintenance ledger with age and priority classification",
      "EPA Energy Star Portfolio Manager comparison data"
    ],
    linkedPainId: "EDU-PAIN-116",
    linkedKPIs: ["EDU-KPI-118"],
    linkedFormulaId: "EDU-VF-113",
    personaTrigger: "EDU-PERS-102 (K-12 Superintendent) / Facilities Director",
    recommendedAction: "Deploy CMMS with preventive maintenance scheduling and mobile work orders. Implement energy management system with real-time monitoring. Prioritize HVAC replacement in buildings with highest energy cost per sq ft."
  },
  {
    id: "EDU-INT-117",
    rawSignalId: "EDU-RAW-117",
    interpretedMeaning: "Transfer students are experiencing significant credit loss, extending time-to-degree and exhausting financial aid eligibility. Non-transparent articulation agreements create student confusion and undermine the community college-to-university pathway mission.",
    confidenceScore: 0.82,
    confidenceRationale: "HIGH confidence on transfer credit acceptance rate because registrars track this. HIGH confidence on credits lost because degree audits calculate this. MEDIUM confidence on articulation agreement coverage because it requires program-by-program inventory.",
    financialImpact: {
      outcome: "Revenue Uplift",
      estimatedAnnualValue: "$500K - $3M annually",
      valueBasis: "Transfer retention improvement ($300K-$2M) + excess credit reduction ($100K-$800K) + articulation agreement efficiency ($50K-$200K). Formula: EDU-VF-104."
    },
    requiredConfirmationSignals: [
      "Transfer credit audit with sending institution and course-level detail",
      "Articulation agreement inventory with program coverage percentage",
      "Transfer student graduation rate vs. native student comparison",
      "Transfer student complaint log with issue categories"
    ],
    linkedPainId: "EDU-PAIN-117",
    linkedKPIs: ["EDU-KPI-111", "EDU-KPI-112"],
    linkedFormulaId: "EDU-VF-104",
    personaTrigger: "EDU-PERS-105 (Registrar / Enrollment Manager)",
    recommendedAction: "Deploy transfer credit evaluation automation with course equivalency database. Implement statewide articulation agreement platform. Launch reverse transfer with automatic associate degree conferral."
  },
  {
    id: "EDU-INT-118",
    rawSignalId: "EDU-RAW-118",
    interpretedMeaning: "Institutional research capacity is strained by manual reporting requirements and accreditation demands. High IPEDS error rates and ad hoc request backlogs indicate that IR staff are consumed by production work, leaving little capacity for strategic analytics that could inform enrollment and program decisions.",
    confidenceScore: 0.80,
    confidenceRationale: "HIGH confidence on self-study hours and ad hoc backlog because these are tracked internally. HIGH confidence on IPEDS error rate because feedback reports provide this. MEDIUM confidence on strategic impact because it requires leadership interview validation.",
    financialImpact: {
      outcome: "Cost Savings",
      estimatedAnnualValue: "$300K - $1.5M annually",
      valueBasis: "IR staff efficiency ($200K-$800K) + accreditation labor reduction ($50K-$400K) + performance funding optimization ($50K-$300K). Formula: EDU-VF-101."
    },
    requiredConfirmationSignals: [
      "Self-study hour log with task and staff breakdown",
      "IPEDS feedback report with error categories and peer comparison",
      "Ad hoc request tracker with requestor and fulfillment time",
      "IR staffing analysis with vacancy and turnover data"
    ],
    linkedPainId: "EDU-PAIN-118",
    linkedKPIs: ["EDU-KPI-102", "EDU-KPI-103"],
    linkedFormulaId: "EDU-VF-101",
    personaTrigger: "EDU-PERS-103 (Research Administrator — for IR Director)",
    recommendedAction: "Implement institutional data warehouse with automated IPEDS and state reporting. Deploy self-service analytics portal for ad hoc requests. Establish IR strategic partnership model with academic affairs and enrollment management."
  }
];

// ============================================================================
// Signal Scoring & Prioritization Utilities
// ============================================================================

/**
 * Calculate a composite priority score for a signal interpretation.
 * Higher scores indicate more urgent, higher-value opportunities.
 */
export function calculateSignalPriority(
  interpretation: SignalInterpretation,
  annualBudgetMagnitude: number // e.g., 50_000_000 for $50M institution
): number {
  const confidenceWeight = interpretation.confidenceScore;
  
  // Parse estimated value range (simplified — midpoint of range)
  const valueString = interpretation.financialImpact.estimatedAnnualValue;
  const valueMatch = valueString.match(/\$([0-9.]+)([MK])?/);
  let estimatedValue = 0;
  if (valueMatch) {
    estimatedValue = parseFloat(valueMatch[1]);
    if (valueMatch[2] === 'M') estimatedValue *= 1_000_000;
    if (valueMatch[2] === 'K') estimatedValue *= 1_000;
  }
  
  const valueWeight = Math.min(estimatedValue / annualBudgetMagnitude, 1.0);
  const confirmationWeight = 1.0 - (interpretation.requiredConfirmationSignals.length * 0.05);
  
  // Composite: 40% confidence + 40% value magnitude + 20% confirmation readiness
  return (confidenceWeight * 0.4) + (valueWeight * 0.4) + (confirmationWeight * 0.2);
}

/**
 * Get the top N signals by priority for a given institution budget.
 */
export function getTopPrioritySignals(
  interpretations: SignalInterpretation[],
  annualBudget: number,
  topN: number = 5
): SignalInterpretation[] {
  const scored = interpretations.map(i => ({
    interpretation: i,
    score: calculateSignalPriority(i, annualBudget)
  }));
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topN).map(s => s.interpretation);
}

// ============================================================================
// Export Convenience Collections
// ============================================================================

export const ALL_EDU_SIGNALS = EDU_SIGNAL_THRESHOLDS;
export const ALL_EDU_INTERPRETATIONS = EDU_SIGNAL_INTERPRETATIONS;

/** Map of signal ID to its interpretation for quick lookup */
export const SIGNAL_TO_INTERPRETATION: Record<string, SignalInterpretation> = 
  EDU_SIGNAL_INTERPRETATIONS.reduce((acc, curr) => {
    acc[curr.rawSignalId] = curr;
    return acc;
  }, {} as Record<string, SignalInterpretation>);

/** Group interpretations by financial outcome for executive reporting */
export const INTERPRETATIONS_BY_OUTCOME: Record<FinancialOutcome, SignalInterpretation[]> = 
  EDU_SIGNAL_INTERPRETATIONS.reduce((acc, curr) => {
    const outcome = curr.financialImpact.outcome;
    if (!acc[outcome]) acc[outcome] = [];
    acc[outcome].push(curr);
    return acc;
  }, {} as Record<FinancialOutcome, SignalInterpretation[]>);

// ============================================================================
// Usage Example (commented for reference)
// ============================================================================

/*
import { 
  ALL_EDU_SIGNALS, 
  ALL_EDU_INTERPRETATIONS, 
  getTopPrioritySignals,
  INTERPRETATIONS_BY_OUTCOME 
} from './signals-examples';

// Get top 5 opportunities for a $100M university
const top5 = getTopPrioritySignals(ALL_EDU_INTERPRETATIONS, 100_000_000, 5);
console.log("Top opportunities:", top5.map(s => ({
  name: s.interpretedMeaning.substring(0, 60),
  value: s.financialImpact.estimatedAnnualValue,
  confidence: s.confidenceScore
})));

// Get all Risk Reduction opportunities
const riskOpportunities = INTERPRETATIONS_BY_OUTCOME["Risk Reduction"];
console.log("Risk reduction count:", riskOpportunities.length);
*/
