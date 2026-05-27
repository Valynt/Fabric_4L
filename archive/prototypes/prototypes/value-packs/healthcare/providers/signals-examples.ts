/**
 * Providers / Care Delivery ValuePack — Signal Examples (TypeScript)
 * ID: providers-v1
 * Parent Master: healthcare-master-v1
 * Agent Swarm: kimi-k2.6-swarm-healthcare-providers-s3.1
 */

// ============================================================================
// Core Types (Inherited from Master, Extended for Providers)
// ============================================================================

type FinancialOutcome = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";

type Confidence = "HIGH" | "MEDIUM" | "LOW";

type UrgencyLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

interface ProviderSignalRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  confidenceScore: number; // 0.0 - 1.0
  requiredConfirmationSignals: string[];
  financialOutcomes: FinancialOutcome[];
  applicablePersonas: string[];
  timeToRelevanceDays: number;
}

interface ProviderBuyingTrigger {
  id: string;
  name: string;
  triggerEvent: string;
  urgencyLevel: UrgencyLevel;
  typicalTiming: string;
  linkedPains: string[];
  procurementImplications: string;
  budgetSource: string;
}

interface ProviderKPIThreshold {
  kpiId: string;
  kpiName: string;
  criticalThreshold: number;
  warningThreshold: number;
  targetThreshold: number;
  unit: string;
  frequency: string;
}

// ============================================================================
// Provider Signal Rules (20)
// ============================================================================

export const PROVIDER_SIGNAL_RULES: ProviderSignalRule[] = [
  {
    id: "PROV-S001",
    signalName: "CMS Conditions of Participation Survey Deficiency",
    rawSignalPattern: "CMS survey citation for hospital-wide CoP deficiency (e.g., QIO, SA complaint)",
    interpretedMeaning: "Immediate jeopardy or condition-level deficiency requiring rapid operational remediation; often triggers 60-90 day follow-up survey",
    linkedPains: ["PROV-P001", "PROV-P004", "PROV-P010"],
    linkedKPIs: ["PROV-K001", "PROV-K027"],
    confidenceScore: 0.95,
    requiredConfirmationSignals: ["CMS-2567 form posted", "State licensure board action"],
    financialOutcomes: ["Risk Reduction", "Cost Savings"],
    applicablePersonas: ["COO", "CMO", "Bed Manager", "CNO"],
    timeToRelevanceDays: 30,
  },
  {
    id: "PROV-S002",
    signalName: "Joint Commission Sentinel Event or Conditional Accreditation",
    rawSignalPattern: "Joint Commission reports sentinel event, preliminary denial of accreditation, or conditional accreditation status",
    interpretedMeaning: "Serious patient safety or leadership failure requiring immediate culture, process, and technology intervention",
    linkedPains: ["PROV-P001", "PROV-P014", "PROV-P010"],
    linkedKPIs: ["PROV-K001", "PROV-K027", "PROV-K039"],
    confidenceScore: 0.94,
    requiredConfirmationSignals: ["Sentinel event database entry", "JC survey report"],
    financialOutcomes: ["Risk Reduction", "Revenue Uplift"],
    applicablePersonas: ["COO", "CNO", "Quality Director", "CMO"],
    timeToRelevanceDays: 45,
  },
  {
    id: "PROV-S003",
    signalName: "ED Diversion Frequency Spike",
    rawSignalPattern: "ED on diversion > 40 hours in a 30-day period per EMS dispatch data or hospital reporting",
    interpretedMeaning: "Capacity crisis or staffing shortage causing EMS diversion; community access and revenue impact imminent",
    linkedPains: ["PROV-P001", "PROV-P004"],
    linkedKPIs: ["PROV-K001", "PROV-K003"],
    confidenceScore: 0.91,
    requiredConfirmationSignals: ["EMS dispatch log", "Daily census report", "Nurse staffing grid"],
    financialOutcomes: ["Revenue Uplift", "Risk Reduction"],
    applicablePersonas: ["COO", "Bed Manager", "ED Director", "CMO"],
    timeToRelevanceDays: 14,
  },
  {
    id: "PROV-S004",
    signalName: "OR Block Release Non-Utilization",
    rawSignalPattern: "Surgeon block time release-to-fill ratio < 50% with first-case delay rate > 25%",
    interpretedMeaning: "Surgical block mismanagement causing OR underutilization and surgeon dissatisfaction",
    linkedPains: ["PROV-P002"],
    linkedKPIs: ["PROV-K004", "PROV-K006"],
    confidenceScore: 0.89,
    requiredConfirmationSignals: ["OR block schedule analysis", "Surgeon satisfaction survey", "Case cancellation log"],
    financialOutcomes: ["Revenue Uplift"],
    applicablePersonas: ["OR Director", "COO", "CFO"],
    timeToRelevanceDays: 60,
  },
  {
    id: "PROV-S005",
    signalName: "Clinic No-Show Surge",
    rawSignalPattern: "Clinic no-show rate increases > 5 percentage points over 90 days with specialty variance > 10 pts",
    interpretedMeaning: "Scheduling, reminder system, or access model failure destroying productivity",
    linkedPains: ["PROV-P003"],
    linkedKPIs: ["PROV-K007"],
    confidenceScore: 0.87,
    requiredConfirmationSignals: ["No-show trend by clinic", "Reminder system audit", "Patient complaint analysis"],
    financialOutcomes: ["Revenue Uplift"],
    applicablePersonas: ["Patient Access Director", "CMO", "Nurse Manager"],
    timeToRelevanceDays: 30,
  },
  {
    id: "PROV-S006",
    signalName: "ICU Census Sustained > 92%",
    rawSignalPattern: "ICU occupancy > 92% for > 5 consecutive days with ED holds > 8 hours",
    interpretedMeaning: "Critical care capacity exhaustion with downstream ED and surgical throughput impact",
    linkedPains: ["PROV-P004", "PROV-P001"],
    linkedKPIs: ["PROV-K010", "PROV-K011"],
    confidenceScore: 0.90,
    requiredConfirmationSignals: ["Hourly ICU census", "ED hold log", "Elective surgery cancellation list"],
    financialOutcomes: ["Cost Savings", "Revenue Uplift"],
    applicablePersonas: ["Bed Manager", "COO", "CNO"],
    timeToRelevanceDays: 7,
  },
  {
    id: "PROV-S007",
    signalName: "Home Health Star Rating Decline",
    rawSignalPattern: "CMS Home Health Compare star rating declines to < 3.0 or quality measure drop in 2+ domains",
    interpretedMeaning: "HHVBP penalty exposure and Medicare Advantage network exclusion risk",
    linkedPains: ["PROV-P005"],
    linkedKPIs: ["PROV-K012"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: ["CMS Home Health Compare update", "OASIS quality measure detail"],
    financialOutcomes: ["Revenue Uplift", "Risk Reduction"],
    applicablePersonas: ["CMO", "Population Health VP", "Nurse Manager"],
    timeToRelevanceDays: 60,
  },
  {
    id: "PROV-S008",
    signalName: "Telehealth Platform Change RFP",
    rawSignalPattern: "RFP issued for telehealth platform replacement or expansion with incumbent contract < 12 months",
    interpretedMeaning: "Current platform failing on completion, technical difficulty, or provider satisfaction; procurement window open",
    linkedPains: ["PROV-P006"],
    linkedKPIs: ["PROV-K015", "PROV-K016"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: ["RFP document", "Contract expiration date", "Board minutes mentioning telehealth"],
    financialOutcomes: ["Cost Savings", "Revenue Uplift"],
    applicablePersonas: ["Telehealth Medical Director", "CIO", "CMIO"],
    timeToRelevanceDays: 90,
  },
  {
    id: "PROV-S009",
    signalName: "CAH Swing Bed Census Sustained < 40%",
    rawSignalPattern: "Critical Access Hospital swing bed census < 40% for > 90 days with SNF transfers > 30%",
    interpretedMeaning: "Swing bed program underutilized; revenue optimization and community need gap",
    linkedPains: ["PROV-P007"],
    linkedKPIs: ["PROV-K018"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: ["Swing bed census report", "Medicare cost report", "SNF transfer log"],
    financialOutcomes: ["Revenue Uplift"],
    applicablePersonas: ["CFO", "COO", "Nurse Manager"],
    timeToRelevanceDays: 90,
  },
  {
    id: "PROV-S010",
    signalName: "ASC Certificate of Need Challenge",
    rawSignalPattern: "State CON commission receives competing ASC application or hospital opposes ASC expansion",
    interpretedMeaning: "Market access and competitive pressure threatening ASC growth strategy",
    linkedPains: ["PROV-P008"],
    linkedKPIs: ["PROV-K022"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: ["State CON filing", "Public hearing notice", "Hospital opposition letter"],
    financialOutcomes: ["Risk Reduction", "Revenue Uplift"],
    applicablePersonas: ["CFO", "OR Director", "Chief Strategy Officer"],
    timeToRelevanceDays: 120,
  },
  {
    id: "PROV-S011",
    signalName: "Hospice Live Discharge Spike",
    rawSignalPattern: "Hospice live discharge rate increases > 5 percentage points over 6 months with LOS declining",
    interpretedMeaning: "Late referral and premature discharge destroying per-patient revenue and quality metrics",
    linkedPains: ["PROV-P009"],
    linkedKPIs: ["PROV-K025"],
    confidenceScore: 0.86,
    requiredConfirmationSignals: ["Live discharge reason analysis", "Referral source trend", "Palliative care consult rate"],
    financialOutcomes: ["Revenue Uplift"],
    applicablePersonas: ["CMO", "Population Health VP"],
    timeToRelevanceDays: 60,
  },
  {
    id: "PROV-S012",
    signalName: "Behavioral Health ED Revisit Surge",
    rawSignalPattern: "Behavioral health ED revisit rate > 30% with psychiatric boarding > 36 hours",
    interpretedMeaning: "Behavioral health continuum gap with acute care cycling and regulatory exposure",
    linkedPains: ["PROV-P010"],
    linkedKPIs: ["PROV-K027", "PROV-K028"],
    confidenceScore: 0.92,
    requiredConfirmationSignals: ["ED revisit analysis", "Psychiatric boarding log", "Community provider availability"],
    financialOutcomes: ["Risk Reduction", "Cost Savings"],
    applicablePersonas: ["VP Behavioral Health", "CMO", "COO"],
    timeToRelevanceDays: 14,
  },
  {
    id: "PROV-S013",
    signalName: "FQHC HRSA Operational Site Visit",
    rawSignalPattern: "HRSA announces operational site visit with prior UDS quality measure gaps",
    interpretedMeaning: "Compliance and grant performance review imminent; operational improvement required",
    linkedPains: ["PROV-P011"],
    linkedKPIs: ["PROV-K030"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: ["HRSA notification letter", "UDS quality measure trend", "Grant performance scorecard"],
    financialOutcomes: ["Risk Reduction", "Revenue Uplift"],
    applicablePersonas: ["CEO", "CMO", "Patient Access Director"],
    timeToRelevanceDays: 60,
  },
  {
    id: "PROV-S014",
    signalName: "Rural Hospital Emergency Department Closure Announcement",
    rawSignalPattern: "Rural hospital announces ED closure, diversion, or 96-hour rule suspension",
    interpretedMeaning: "Critical access failure requiring immediate strategic or operational intervention; CON risk",
    linkedPains: ["PROV-P012"],
    linkedKPIs: ["PROV-K033"],
    confidenceScore: 0.93,
    requiredConfirmationSignals: ["Hospital press release", "State health department notice", "CMS 96-hour waiver request"],
    financialOutcomes: ["Risk Reduction", "Working Capital"],
    applicablePersonas: ["CEO", "CFO", "COO"],
    timeToRelevanceDays: 30,
  },
  {
    id: "PROV-S015",
    signalName: "CMS SEP-1 Public Reporting Decline",
    rawSignalPattern: "CMS Hospital Compare SEP-1 compliance rate drops below 75th percentile or declines > 5 pts YoY",
    interpretedMeaning: "Sepsis bundle compliance failure with HACRP and VBP payment impact",
    linkedPains: ["PROV-P013"],
    linkedKPIs: ["PROV-K036"],
    confidenceScore: 0.89,
    requiredConfirmationSignals: ["CMS Hospital Compare download", "Internal sepsis registry audit"],
    financialOutcomes: ["Risk Reduction", "Revenue Uplift"],
    applicablePersonas: ["CMO", "CNO", "Quality Director"],
    timeToRelevanceDays: 45,
  },
  {
    id: "PROV-S016",
    signalName: "HACRP Total Score in Bottom Quartile",
    rawSignalPattern: "CMS HACRP total score places hospital in bottom 25% with 1% payment reduction",
    interpretedMeaning: "Healthcare-associated condition performance failure with direct Medicare penalty",
    linkedPains: ["PROV-P014"],
    linkedKPIs: ["PROV-K039", "PROV-K040"],
    confidenceScore: 0.91,
    requiredConfirmationSignals: ["CMS HACRP public report", "NHSN device days data", "Infection prevention audit"],
    financialOutcomes: ["Risk Reduction", "Cost Savings"],
    applicablePersonas: ["CNO", "CMO", "Quality Director", "Infection Prevention Director"],
    timeToRelevanceDays: 60,
  },
  {
    id: "PROV-S017",
    signalName: "New Patient Appointment Wait > 30 Days",
    rawSignalPattern: "Average new patient appointment wait time > 30 days for primary care or > 45 days for specialty per AMGA/Merritt Hawkins",
    interpretedMeaning: "Access crisis driving patient leakage, ED substitution, and VBC attribution loss",
    linkedPains: ["PROV-P015"],
    linkedKPIs: ["PROV-K042"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: ["Appointment availability audit", "Patient complaint log", "ED utilization for primary care"],
    financialOutcomes: ["Revenue Uplift"],
    applicablePersonas: ["Patient Access Director", "CMO", "COO"],
    timeToRelevanceDays: 30,
  },
  {
    id: "PROV-S018",
    signalName: "USP <797> or <800> Cleanroom Failure",
    rawSignalPattern: "Cleanroom certification failure or USP gap assessment with > 5 findings requiring immediate remediation",
    interpretedMeaning: "Sterile compounding safety and compliance risk with pharmacy operations disruption",
    linkedPains: ["PROV-P016"],
    linkedKPIs: ["PROV-K045"],
    confidenceScore: 0.90,
    requiredConfirmationSignals: ["USP gap assessment report", "Cleanroom certification document", "Board of Pharmacy inspection"],
    financialOutcomes: ["Risk Reduction", "Cost Savings"],
    applicablePersonas: ["Chief Pharmacy Officer", "CMO", "Compliance Officer"],
    timeToRelevanceDays: 60,
  },
  {
    id: "PROV-S019",
    signalName: "Anesthesia Billing Audit Finding",
    rawSignalPattern: "External anesthesia billing audit identifies capture rate < 95% or concurrency errors > 3%",
    interpretedMeaning: "Revenue leakage in perioperative services with compliance and payer dispute risk",
    linkedPains: ["PROV-P017"],
    linkedKPIs: ["PROV-K048"],
    confidenceScore: 0.87,
    requiredConfirmationSignals: ["Billing audit report", "Payer denial trend for anesthesia", "ASA unit comparison vs. peer"],
    financialOutcomes: ["Revenue Uplift"],
    applicablePersonas: ["OR Director", "CFO", "VP Revenue Cycle"],
    timeToRelevanceDays: 45,
  },
  {
    id: "PROV-S020",
    signalName: "Nurse Manager Vacancy or Span-of-Control Crisis",
    rawSignalPattern: "Nurse Manager vacancy rate > 15% or span of control > 60 FTEs with unit turnover > 25%",
    interpretedMeaning: "Unit-level leadership crisis causing quality, safety, and retention cascade failure",
    linkedPains: ["PROV-P020"],
    linkedKPIs: ["PROV-K057", "PROV-K058"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: ["Nurse Manager vacancy report", "Span-of-control analysis", "Unit turnover by manager"],
    financialOutcomes: ["Cost Savings", "Risk Reduction"],
    applicablePersonas: ["CNO", "Nurse Manager", "CHRO"],
    timeToRelevanceDays: 30,
  },
];

// ============================================================================
// Provider Buying Triggers (15)
// ============================================================================

export const PROVIDER_BUYING_TRIGGERS: ProviderBuyingTrigger[] = [
  {
    id: "PROV-BT001",
    name: "CMS Conditions of Participation Citation",
    triggerEvent: "CMS surveyor issues condition-level deficiency or immediate jeopardy finding",
    urgencyLevel: "CRITICAL",
    typicalTiming: "Immediate; 30-90 day remediation window",
    linkedPains: ["PROV-P001", "PROV-P004", "PROV-P010"],
    procurementImplications: "Emergency procurement with expedited vendor selection; budget reallocation from capital reserve",
    budgetSource: "Capital reserve / Compliance contingency",
  },
  {
    id: "PROV-BT002",
    name: "Joint Commission Conditional or Preliminary Denial",
    triggerEvent: "Joint Commission issues conditional accreditation or preliminary denial of accreditation",
    urgencyLevel: "CRITICAL",
    typicalTiming: "Immediate; 45-120 day remediation",
    linkedPains: ["PROV-P001", "PROV-P014", "PROV-P010"],
    procurementImplications: "Board-level urgency; fast-track procurement; may require consulting + technology bundle",
    budgetSource: "Quality improvement fund / Board-approved contingency",
  },
  {
    id: "PROV-BT003",
    name: "ED Diversion Mandate from State EMS Agency",
    triggerEvent: "State EMS agency mandates reduction in diversion hours or threatens EMS designation revocation",
    urgencyLevel: "HIGH",
    typicalTiming: "30-60 days",
    linkedPains: ["PROV-P001"],
    procurementImplications: "Operational technology procurement; bed management and ED flow platforms prioritized",
    budgetSource: "Operations budget / State emergency grant",
  },
  {
    id: "PROV-BT004",
    name: "CMS HACRP Penalty Notification",
    triggerEvent: "CMS notifies hospital of HACRP 1% payment reduction for total score in bottom quartile",
    urgencyLevel: "HIGH",
    typicalTiming: "Annual; Q4 notification, Q1 procurement",
    linkedPains: ["PROV-P014"],
    procurementImplications: "Quality and infection prevention technology; data analytics for HAI reduction",
    budgetSource: "Quality improvement fund / Medicare revenue offset",
  },
  {
    id: "PROV-BT005",
    name: "New OR Director from Outside System",
    triggerEvent: "New OR Director hired from outside with perioperative performance improvement background",
    urgencyLevel: "MEDIUM",
    typicalTiming: "Month 3-9 post-hire",
    linkedPains: ["PROV-P002"],
    procurementImplications: "OR management and analytics platforms; block scheduling optimization tools",
    budgetSource: "Surgical services operations budget",
  },
  {
    id: "PROV-BT006",
    name: "Anesthesia Group Contract Renewal or RFP",
    triggerEvent: "Hospital anesthesia group contract expires within 12-18 months or hospital issues anesthesia RFP",
    urgencyLevel: "HIGH",
    typicalTiming: "12-18 months before expiration",
    linkedPains: ["PROV-P002", "PROV-P017"],
    procurementImplications: "Anesthesia information management and billing optimization; OR-to-billing integration",
    budgetSource: "Perioperative services budget / Anesthesia subsidy",
  },
  {
    id: "PROV-BT007",
    name: "Telehealth Platform Contract Expiration",
    triggerEvent: "Telehealth platform contract expires within 12 months with completion rate < 80%",
    urgencyLevel: "MEDIUM",
    typicalTiming: "9-12 months before expiration",
    linkedPains: ["PROV-P006"],
    procurementImplications: "Telehealth platform replacement RFP; virtual care expansion strategy",
    budgetSource: "Digital health innovation fund",
  },
  {
    id: "PROV-BT008",
    name: "Rural Hospital Distress Designation",
    triggerEvent: "State or federal agency designates rural hospital as financially distressed or at risk of closure",
    urgencyLevel: "CRITICAL",
    typicalTiming: "Immediate; 60-120 day strategic response",
    linkedPains: ["PROV-P012"],
    procurementImplications: "Medicare revenue optimization technology (swing bed, 340B, CAH cost reporting); federal grant-funded solutions",
    budgetSource: "Federal rural health grant / USDA community facilities loan",
  },
  {
    id: "PROV-BT009",
    name: "Hospice CAP Exceedance Warning",
    triggerEvent: "Hospice provider approaches or exceeds Medicare aggregate cap with LOS < 20 days",
    urgencyLevel: "HIGH",
    typicalTiming: "Q3-Q4 fiscal year; Q1 procurement",
    linkedPains: ["PROV-P009"],
    procurementImplications: "Hospice revenue cycle and referral optimization; palliative care integration technology",
    budgetSource: "Hospice operations budget",
  },
  {
    id: "PROV-BT010",
    name: "Behavioral Health ED Boarding Class Action or DOJ Investigation",
    triggerEvent: "Civil rights complaint, class action, or DOJ investigation for psychiatric boarding practices",
    urgencyLevel: "CRITICAL",
    typicalTiming: "Immediate; 30-60 day response",
    linkedPains: ["PROV-P010"],
    procurementImplications: "Behavioral health capacity management; telepsychiatry; discharge planning acceleration",
    budgetSource: "Legal reserve / Behavioral health capital fund",
  },
  {
    id: "PROV-BT011",
    name: "FQHC HRSA Operational Site Visit Scheduled",
    triggerEvent: "HRSA schedules operational site visit with prior UDS quality or visit productivity gaps",
    urgencyLevel: "HIGH",
    typicalTiming: "60-90 days before visit",
    linkedPains: ["PROV-P011"],
    procurementImplications: "Patient access and quality measurement technology; UDS reporting automation",
    budgetSource: "HRSA health IT allowable costs / 330 grant",
  },
  {
    id: "PROV-BT012",
    name: "ASC New Certificate of Need Approval",
    triggerEvent: "State CON commission approves new ASC or hospital ASC expansion",
    urgencyLevel: "MEDIUM",
    typicalTiming: "90-180 days post-approval for buildout",
    linkedPains: ["PROV-P008"],
    procurementImplications: "New ASC technology stack from greenfield; scheduling, supply chain, and billing systems",
    budgetSource: "ASC development capital / Construction budget",
  },
  {
    id: "PROV-BT013",
    name: "USP <797>/<800> Cleanroom Remediation Deadline",
    triggerEvent: "USP gap assessment or Board of Pharmacy mandates cleanroom remediation within 6-12 months",
    urgencyLevel: "HIGH",
    typicalTiming: "6-12 months before deadline",
    linkedPains: ["PROV-P016"],
    procurementImplications: "Compounding workflow technology; environmental monitoring; compliance documentation platforms",
    budgetSource: "Pharmacy capital / Compliance contingency",
  },
  {
    id: "PROV-BT014",
    name: "New Patient Access Director Hired from Outside",
    triggerEvent: "New Patient Access Director or VP hired from competitor with turnaround mandate",
    urgencyLevel: "MEDIUM",
    typicalTiming: "Month 3-8 post-hire",
    linkedPains: ["PROV-P003", "PROV-P015"],
    procurementImplications: "Scheduling optimization, reminder systems, and prior authorization automation",
    budgetSource: "Patient access operations budget",
  },
  {
    id: "PROV-BT015",
    name: "Nurse Manager Mass Exodus or Union Action",
    triggerEvent: "Multiple Nurse Manager resignations within 90 days or union grievance filing on staffing",
    urgencyLevel: "HIGH",
    typicalTiming: "Immediate; 30-60 days",
    linkedPains: ["PROV-P020"],
    procurementImplications: "Staffing and scheduling optimization; acuity-based assignment technology; leadership development programs",
    budgetSource: "Nursing operations / Workforce development fund",
  },
];

// ============================================================================
// Provider KPI Thresholds (25)
// ============================================================================

export const PROVIDER_KPI_THRESHOLDS: ProviderKPIThreshold[] = [
  { kpiId: "PROV-K001", kpiName: "ED Boarding Time", criticalThreshold: 180, warningThreshold: 120, targetThreshold: 60, unit: "minutes", frequency: "daily" },
  { kpiId: "PROV-K002", kpiName: "ED LWBS Rate", criticalThreshold: 5, warningThreshold: 3.5, targetThreshold: 2, unit: "%", frequency: "daily" },
  { kpiId: "PROV-K003", kpiName: "ED Ambulance Diversion Hours", criticalThreshold: 50, warningThreshold: 25, targetThreshold: 0, unit: "hours/month", frequency: "monthly" },
  { kpiId: "PROV-K004", kpiName: "OR First-Case On-Time Start %", criticalThreshold: 60, warningThreshold: 70, targetThreshold: 85, unit: "%", frequency: "monthly" },
  { kpiId: "PROV-K005", kpiName: "OR Turnover Time", criticalThreshold: 50, warningThreshold: 40, targetThreshold: 30, unit: "minutes", frequency: "daily" },
  { kpiId: "PROV-K006", kpiName: "OR Utilization", criticalThreshold: 70, warningThreshold: 75, targetThreshold: 85, unit: "%", frequency: "monthly" },
  { kpiId: "PROV-K007", kpiName: "Clinic No-Show Rate", criticalThreshold: 18, warningThreshold: 12, targetThreshold: 8, unit: "%", frequency: "monthly" },
  { kpiId: "PROV-K008", kpiName: "Clinic Cycle Time", criticalThreshold: 75, warningThreshold: 60, targetThreshold: 45, unit: "minutes", frequency: "daily" },
  { kpiId: "PROV-K009", kpiName: "Provider wRVUs per FTE", criticalThreshold: 4500, warningThreshold: 5500, targetThreshold: 6500, unit: "wRVUs/FTE/year", frequency: "monthly" },
  { kpiId: "PROV-K010", kpiName: "ICU Step-Down Delay", criticalThreshold: 24, warningThreshold: 12, targetThreshold: 6, unit: "hours", frequency: "daily" },
  { kpiId: "PROV-K011", kpiName: "ICU Occupancy Rate", criticalThreshold: 92, warningThreshold: 88, targetThreshold: 82, unit: "%", frequency: "daily" },
  { kpiId: "PROV-K012", kpiName: "Home Health 30-Day Readmission", criticalThreshold: 18, warningThreshold: 15, targetThreshold: 12, unit: "%", frequency: "quarterly" },
  { kpiId: "PROV-K013", kpiName: "Home Health Episodic Cost", criticalThreshold: 7000, warningThreshold: 6000, targetThreshold: 5000, unit: "USD", frequency: "monthly" },
  { kpiId: "PROV-K014", kpiName: "Home Health Med Rec Completion", criticalThreshold: 80, warningThreshold: 85, targetThreshold: 92, unit: "%", frequency: "monthly" },
  { kpiId: "PROV-K015", kpiName: "Telehealth Completion Rate", criticalThreshold: 75, warningThreshold: 80, targetThreshold: 88, unit: "%", frequency: "weekly" },
  { kpiId: "PROV-K016", kpiName: "Telehealth Technical Difficulty", criticalThreshold: 10, warningThreshold: 6, targetThreshold: 3, unit: "%", frequency: "weekly" },
  { kpiId: "PROV-K017", kpiName: "Telehealth Provider Satisfaction", criticalThreshold: 3.0, warningThreshold: 3.5, targetThreshold: 4.2, unit: "score (1-5)", frequency: "quarterly" },
  { kpiId: "PROV-K018", kpiName: "Swing Bed Occupancy", criticalThreshold: 45, warningThreshold: 55, targetThreshold: 70, unit: "%", frequency: "monthly" },
  { kpiId: "PROV-K019", kpiName: "Swing Bed ALOS", criticalThreshold: 25, warningThreshold: 22, targetThreshold: 15, unit: "days", frequency: "monthly" },
  { kpiId: "PROV-K020", kpiName: "Swing Bed Medicare Bad Debt", criticalThreshold: 8, warningThreshold: 6, targetThreshold: 4, unit: "%", frequency: "monthly" },
  { kpiId: "PROV-K021", kpiName: "ASC Revenue per Case", criticalThreshold: 2000, warningThreshold: 2200, targetThreshold: 2800, unit: "USD", frequency: "monthly" },
  { kpiId: "PROV-K022", kpiName: "ASC EBITDA Margin", criticalThreshold: 12, warningThreshold: 15, targetThreshold: 22, unit: "%", frequency: "monthly" },
  { kpiId: "PROV-K023", kpiName: "ASC Supply Cost per Case", criticalThreshold: 25, warningThreshold: 22, targetThreshold: 18, unit: "% of revenue", frequency: "monthly" },
  { kpiId: "PROV-K024", kpiName: "Hospice ALOS", criticalThreshold: 12, warningThreshold: 20, targetThreshold: 55, unit: "days", frequency: "monthly" },
  { kpiId: "PROV-K025", kpiName: "Hospice Live Discharge Rate", criticalThreshold: 18, warningThreshold: 14, targetThreshold: 10, unit: "%", frequency: "monthly" },
];

// ============================================================================
// Signal Evaluation Functions
// ============================================================================

/**
 * Evaluates a raw signal value against a KPI threshold and returns interpretation.
 * @param kpiId - The KPI identifier
 * @param currentValue - The current measured value
 * @returns SignalInterpretation with pain linkage and confidence
 */
export function evaluateProviderSignal(kpiId: string, currentValue: number): {
  status: "CRITICAL" | "WARNING" | "NORMAL" | "TARGET";
  linkedPains: string[];
  confidenceScore: number;
  recommendedActions: string[];
} {
  const threshold = PROVIDER_KPI_THRESHOLDS.find((k) => k.kpiId === kpiId);
  if (!threshold) {
    throw new Error(`Unknown KPI: ${kpiId}`);
  }

  // Determine status based on whether higher or lower is better
  const isHigherBetter = threshold.targetThreshold > threshold.warningThreshold;

  let status: "CRITICAL" | "WARNING" | "NORMAL" | "TARGET";
  if (isHigherBetter) {
    if (currentValue <= threshold.criticalThreshold) status = "CRITICAL";
    else if (currentValue <= threshold.warningThreshold) status = "WARNING";
    else if (currentValue >= threshold.targetThreshold) status = "TARGET";
    else status = "NORMAL";
  } else {
    if (currentValue >= threshold.criticalThreshold) status = "CRITICAL";
    else if (currentValue >= threshold.warningThreshold) status = "WARNING";
    else if (currentValue <= threshold.targetThreshold) status = "TARGET";
    else status = "NORMAL";
  }

  // Find matching signal rules
  const matchingRules = PROVIDER_SIGNAL_RULES.filter((rule) =>
    rule.linkedKPIs.includes(kpiId)
  );

  const linkedPains = Array.from(
    new Set(matchingRules.flatMap((r) => r.linkedPains))
  );

  const confidenceScore = matchingRules.length > 0
    ? Math.max(...matchingRules.map((r) => r.confidenceScore))
    : 0.5;

  const recommendedActions = matchingRules.flatMap((r) =>
    r.requiredConfirmationSignals
  );

  return {
    status,
    linkedPains,
    confidenceScore,
    recommendedActions: Array.from(new Set(recommendedActions)),
  };
}

/**
 * Finds active buying triggers based on current pain manifestations.
 * @param activePainIds - Array of currently active pain IDs
 * @returns Array of matching buying triggers with urgency scoring
 */
export function findActiveBuyingTriggers(activePainIds: string[]): {
  trigger: ProviderBuyingTrigger;
  urgencyScore: number;
  daysToAction: number;
}[] {
  const matchingTriggers = PROVIDER_BUYING_TRIGGERS.filter((trigger) =>
    trigger.linkedPains.some((pain) => activePainIds.includes(pain))
  );

  const urgencyWeights: Record<UrgencyLevel, number> = {
    CRITICAL: 1.0,
    HIGH: 0.7,
    MEDIUM: 0.4,
    LOW: 0.2,
  };

  return matchingTriggers.map((trigger) => ({
    trigger,
    urgencyScore: urgencyWeights[trigger.urgencyLevel],
    daysToAction: trigger.urgencyLevel === "CRITICAL" ? 30 : trigger.urgencyLevel === "HIGH" ? 60 : 90,
  }));
}

// ============================================================================
// Usage Example
// ============================================================================

// Example: Evaluate ED boarding signal
// const result = evaluateProviderSignal("PROV-K001", 155);
// console.log(result);
// Expected: { status: "WARNING", linkedPains: ["PROV-P001", "PROV-P004"], ... }

// Example: Find buying triggers for ED boarding and OR delay
// const triggers = findActiveBuyingTriggers(["PROV-P001", "PROV-P002"]);
// console.log(triggers);
// Expected: [{ trigger: PROV-BT001, urgencyScore: 1.0, daysToAction: 30 }, ...]
