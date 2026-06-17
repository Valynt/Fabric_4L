import type {
  DeliverableType,
  ProspectSetupPromptPayload,
} from "@/components/workspace/ProspectPromptBuilder";

export type SourceMode = "notes" | "url" | "file" | "crm" | "audio" | "meeting";

export interface IntakeSource {
  id: string;
  mode: SourceMode;
  label: string;
  status: "processed" | "pending" | "not_connected";
  detail?: string;
}

export interface ExtractedStakeholder {
  name: string;
  role: string;
  relationship?: string;
}

export interface MissingMetric {
  id: string;
  label: string;
  value: string;
  unit: string;
  source: "missing" | "manual";
}

export interface ValueCaseDraft {
  companyName: string;
  companyDomain: string;
  industry: string;
  accountContext: string;
  buyingContext: string;
  whyNow: string;
  knownInitiative: string;
  businessPain: string[];
  currentFriction: string[];
  desiredOutcomes: string[];
  stakeholders: ExtractedStakeholder[];
  valueLevers: string[];
  missingMetrics: MissingMetric[];
  dealSize: string;
  targetTiming: string;
  evidenceScore: number;
  evidenceStrength: "Low" | "Medium" | "High";
  readinessLabel: string;
}

export interface IntakeParserInput {
  notes: string;
  sourceUrl: string;
  sources: IntakeSource[];
  metricOverrides: Record<string, string>;
}

const DEFAULT_METRICS: MissingMetric[] = [
  {
    id: "baseline_volume",
    label: "Baseline volume",
    value: "",
    unit: "items/mo",
    source: "missing",
  },
  {
    id: "average_cost",
    label: "Average cost or salary",
    value: "",
    unit: "USD",
    source: "missing",
  },
];

function firstMatch(value: string, patterns: RegExp[]): string {
  for (const pattern of patterns) {
    const match = value.match(pattern);
    if (match?.[1]) {
      return match[1].trim().replace(/[.,;:]+$/, "");
    }
  }
  return "";
}

function normalizeDomain(value: string): string {
  return value
    .trim()
    .replace(/^https?:\/\//i, "")
    .replace(/^www\./i, "")
    .replace(/\/.*$/, "")
    .toLowerCase();
}

function extractCompanyName(notes: string, sourceUrl: string): string {
  const explicit = firstMatch(notes, [
    /^([A-Z][A-Za-z0-9&.\- ]{2,80}?(?:Corp|Corporation|Software|Logistics|Inc|LLC|Ltd))\b/m,
    /^([A-Z][A-Za-z0-9&.\- ]{2,80}?)(?:\s+Discovery|\s+Memo|\s+Session)/m,
    /(?:met with|spoke with|team at)\s+([A-Z][A-Za-z0-9&.\- ]{2,80}?)(?:[.,\n])/i,
  ]);
  if (explicit) return explicit;

  const domain = normalizeDomain(sourceUrl);
  if (!domain) return "";

  const base = domain.split(".")[0]?.replace(/[-_]+/g, " ") ?? "";
  return base.replace(/\b\w/g, char => char.toUpperCase());
}

function extractStakeholders(notes: string): ExtractedStakeholder[] {
  const stakeholders = new Map<string, ExtractedStakeholder>();
  const patterns = [
    /([A-Z][a-z]+)\s*\(([^)]+)\)/g,
    /(?:with|from)\s+([A-Z][a-z]+)\s*[-,]\s*([^.\n]+)/g,
  ];

  for (const pattern of patterns) {
    let match = pattern.exec(notes);
    while (match) {
      const name = match[1]?.trim();
      const role = match[2]?.replace(/\s*\/\s*/g, " / ").trim();
      if (name && role && !stakeholders.has(name.toLowerCase())) {
        stakeholders.set(name.toLowerCase(), { name, role });
      }
      match = pattern.exec(notes);
    }
  }

  return Array.from(stakeholders.values()).slice(0, 5);
}

function sentenceFragments(notes: string): string[] {
  return notes
    .split(/(?<=[.!?])\s+|\n+/)
    .map(sentence => sentence.trim())
    .filter(Boolean);
}

function extractPain(notes: string): string[] {
  const keywords = /(manual|delay|breach|churn|overhead|struggl|risk|inefficien|lag|slow|compliance|routing|cost)/i;
  return sentenceFragments(notes)
    .filter(sentence => keywords.test(sentence))
    .map(sentence => sentence.replace(/^[-*]\s*/, ""))
    .slice(0, 5);
}

function inferIndustry(notes: string, sourceUrl: string): string {
  const haystack = `${notes} ${sourceUrl}`.toLowerCase();
  if (/logistics|fleet|route|dispatch|shipment/.test(haystack)) return "Logistics";
  if (/software|saas|support|ticket|customer/.test(haystack)) return "Software";
  if (/manufacturing|plant|factory|production/.test(haystack)) return "Manufacturing";
  if (/legal|compliance|audit|risk/.test(haystack)) return "Compliance";
  return "";
}

function inferValueLevers(pain: string[]): string[] {
  const joined = pain.join(" ").toLowerCase();
  const levers: string[] = [];
  if (/manual|overhead|salary|hours/.test(joined)) levers.push("Labor cost avoidance");
  if (/churn|sla|slow|resolution|customer/.test(joined)) levers.push("Revenue protection");
  if (/risk|compliance|audit|breach/.test(joined)) levers.push("Risk mitigation");
  if (/route|fleet|dispatch|fuel|shipment/.test(joined)) levers.push("Operational efficiency");
  return levers.length > 0 ? levers : ["Value hypothesis pending"];
}

function buildMetrics(notes: string, overrides: Record<string, string>): MissingMetric[] {
  const lower = notes.toLowerCase();
  const metricTemplates = /ticket|support|sla/.test(lower)
    ? [
        { ...DEFAULT_METRICS[0], label: "Monthly support ticket volume", unit: "tickets/mo" },
        { ...DEFAULT_METRICS[1], label: "Average Tier 2 rep salary", unit: "USD/yr" },
      ]
    : /fleet|route|dispatch|shipment/.test(lower)
      ? [
          { ...DEFAULT_METRICS[0], label: "Monthly fleet shipments", unit: "shipments/mo" },
          { ...DEFAULT_METRICS[1], label: "Average dispatch adjustment time", unit: "min/load" },
        ]
      : /compliance|audit|legal/.test(lower)
        ? [
            { ...DEFAULT_METRICS[0], label: "Monthly audit volume", unit: "audits/mo" },
            { ...DEFAULT_METRICS[1], label: "Average counsel hourly rate", unit: "USD/hr" },
          ]
        : DEFAULT_METRICS;

  return metricTemplates.map(metric => {
    const value = overrides[metric.id]?.trim() ?? "";
    return {
      ...metric,
      value,
      source: value ? "manual" : "missing",
    };
  });
}

function evidenceStrength(score: number): ValueCaseDraft["evidenceStrength"] {
  if (score >= 75) return "High";
  if (score >= 45) return "Medium";
  return "Low";
}

export function parseValueCaseDraft(input: IntakeParserInput): ValueCaseDraft {
  const { notes, sourceUrl, sources, metricOverrides } = input;
  const companyName = extractCompanyName(notes, sourceUrl);
  const companyDomain = normalizeDomain(sourceUrl);
  const stakeholders = extractStakeholders(notes);
  const businessPain = extractPain(notes);
  const metrics = buildMetrics(notes, metricOverrides);
  const dealSize = firstMatch(notes, [
    /(?:budgeted|deal size|commercial value|value ranges around|roughly|around)\s*(~?\$[\d,.]+\s?[kKmM]?(?:\s?(?:ARR|deal))?)/i,
    /(~?\$[\d,.]+\s?[kKmM]?\s?(?:ARR|deal))/i,
  ]);
  const targetTiming = firstMatch(notes, [
    /(?:target close|close target|committing by)\s*[:\-]?\s*([^.\n]+(?:Q[1-4]|FY\d{2}|\d{4}|month|quarter)[^.\n]*)/i,
    /(End of\s+(?:Q[1-4]|FY\d{2}|Month|Quarter))/i,
  ]);

  const processedSources = sources.filter(source => source.status === "processed").length;
  const filledMetrics = metrics.filter(metric => metric.value).length;
  const rawEvidenceScore =
    (companyName ? 15 : 0) +
    (notes.trim().length >= 50 ? 15 : 0) +
    (companyDomain ? 10 : 0) +
    (stakeholders.length > 0 ? 15 : 0) +
    (businessPain.length > 0 ? 15 : 0) +
    (dealSize ? 10 : 0) +
    (targetTiming ? 5 : 0) +
    processedSources * 5 +
    filledMetrics * 10;
  const evidenceScore = Math.min(
    100,
    filledMetrics === 0
      ? Math.min(rawEvidenceScore, 70)
      : filledMetrics === 1
        ? Math.min(rawEvidenceScore, 85)
        : rawEvidenceScore
  );
  const strength = evidenceStrength(evidenceScore);

  return {
    companyName,
    companyDomain,
    industry: inferIndustry(notes, sourceUrl),
    accountContext: notes.trim(),
    buyingContext: targetTiming ? `Target timing: ${targetTiming}` : "",
    whyNow: businessPain[0] ?? "",
    knownInitiative: firstMatch(notes, [
      /(?:initiative|project|opportunity|opp(?:ortunity)? name)\s*[:\-]\s*([^.\n]+)/i,
      /(?:for|around)\s+([A-Z][A-Za-z0-9&.\- ]{4,80}? Automation)/,
    ]),
    businessPain,
    currentFriction: businessPain.slice(0, 3),
    desiredOutcomes: inferValueLevers(businessPain),
    stakeholders,
    valueLevers: inferValueLevers(businessPain),
    missingMetrics: metrics,
    dealSize,
    targetTiming,
    evidenceScore,
    evidenceStrength: strength,
    readinessLabel:
      strength === "High"
        ? "Ready for workspace launch"
        : strength === "Medium"
          ? "Needs baseline metrics"
          : "Needs account context",
  };
}

export function buildProspectPayloadFromDraft(draft: ValueCaseDraft): ProspectSetupPromptPayload {
  const stakeholderPayload = draft.stakeholders.reduce<Record<string, string>>((acc, stakeholder, index) => {
    acc[`stakeholder_${index + 1}`] = `${stakeholder.name} - ${stakeholder.role}`;
    return acc;
  }, {});

  const outputType: DeliverableType = "account_brief";

  return {
    companyName: draft.companyName,
    companyDomain: draft.companyDomain,
    industry: draft.industry,
    accountContext: draft.accountContext,
    buyingContext: draft.buyingContext,
    whyNow: draft.whyNow,
    knownInitiative: draft.knownInitiative,
    businessPain: draft.businessPain,
    currentFriction: draft.currentFriction,
    desiredOutcomes: draft.desiredOutcomes,
    stakeholders: stakeholderPayload,
    sourceArtifacts: [],
    outputType,
    desiredOutputs: [outputType, "value_hypotheses"],
    mode: "Balanced",
    enrichmentDepth: "standard",
    useUploadedFiles: false,
    usePriorAccountContext: false,
    runWebEnrichment: Boolean(draft.companyDomain),
    complianceSensitive: false,
    deepResearch: false,
    freeformPrompt: draft.accountContext,
  };
}
