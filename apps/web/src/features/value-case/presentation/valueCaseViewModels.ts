/**
 * Value Case Presentation View-Models
 *
 * Formats domain models into presentation-ready, accessible structures.
 */
import type {
  ValueCaseArtifactVersion,
  ValueCaseMetrics,
} from "../domain/valueCaseModels";

export interface ValueCaseMetricCardViewModel {
  readonly key: "three_year_value" | "roi" | "payback";
  readonly label: string;
  readonly formattedValue: string;
  readonly rawValue: string;
  readonly description: string;
  readonly isAvailable: boolean;
}

export interface ValueCaseVersionSummaryViewModel {
  readonly id: string;
  readonly version: number;
  readonly label: string;
  readonly isPublished: boolean;
  readonly statusLabel: string;
  readonly createdAtFormatted: string;
  readonly title: string;
  readonly summary: string;
}

export interface ValueCaseVersionDiffViewModel {
  readonly priorVersion: number;
  readonly currentVersion: number;
  readonly roiDiff: string;
  readonly paybackDiff: string;
  readonly valueDiff: string;
  readonly risksCountDiff: string;
  readonly hasChanges: boolean;
}

export interface ValueCaseResultViewModel {
  readonly id: string;
  readonly version: number;
  readonly versionLabel: string;
  readonly isPublished: boolean;
  readonly statusBadgeVariant: "default" | "secondary" | "outline";
  readonly statusBadgeLabel: string;
  readonly createdAtFormatted: string;
  readonly narrativeTitle: string;
  readonly narrativeSections: ReadonlyArray<{
    readonly heading: string;
    readonly content: string;
  }>;
  readonly businessCaseSummary: string;
  readonly metrics: readonly ValueCaseMetricCardViewModel[];
  readonly stakeholderFraming: ReadonlyArray<{
    readonly role: string;
    readonly priorities: readonly string[];
    readonly valueMessage: string;
  }>;
  readonly risks: readonly string[];
}

export function formatPresentationDate(isoString?: string): string {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

export function buildMetricCardViewModels(
  metrics?: ValueCaseMetrics | null
): ValueCaseMetricCardViewModel[] {
  const threeYearValue = metrics?.threeYearValue?.trim() || "";
  const roi = metrics?.roi?.trim() || "";
  const payback = metrics?.payback?.trim() || "";

  return [
    {
      key: "three_year_value",
      label: "3-Year Value",
      formattedValue: threeYearValue || "—",
      rawValue: threeYearValue,
      description: "Projected cumulative Net Present Value over 3 years",
      isAvailable: Boolean(threeYearValue),
    },
    {
      key: "roi",
      label: "ROI",
      formattedValue: roi || "—",
      rawValue: roi,
      description: "Total Return on Investment percentage",
      isAvailable: Boolean(roi),
    },
    {
      key: "payback",
      label: "Payback",
      formattedValue: payback || "—",
      rawValue: payback,
      description: "Payback period in months",
      isAvailable: Boolean(payback),
    },
  ];
}

export function buildVersionSummaryViewModels(
  versions: readonly ValueCaseArtifactVersion[]
): ValueCaseVersionSummaryViewModel[] {
  return versions.map(v => ({
    id: v.id,
    version: v.version,
    label: `v${v.version}`,
    isPublished: v.status.toLowerCase() === "published",
    statusLabel: v.status.toLowerCase() === "published" ? "Published" : "Draft",
    createdAtFormatted: formatPresentationDate(v.createdAt),
    title: v.narrative.title || v.title || "Value Case",
    summary: v.businessCase.summary || "No executive summary available.",
  }));
}

export function buildVersionDiffViewModel(
  current: ValueCaseArtifactVersion | null,
  previous: ValueCaseArtifactVersion | null
): ValueCaseVersionDiffViewModel | null {
  if (!current || !previous) return null;

  const prevMetrics = previous.businessCase.metrics;
  const currMetrics = current.businessCase.metrics;

  const roiDiff = `${prevMetrics.roi || "—"} → ${currMetrics.roi || "—"}`;
  const paybackDiff = `${prevMetrics.payback || "—"} → ${currMetrics.payback || "—"}`;
  const valueDiff = `${prevMetrics.threeYearValue || "—"} → ${currMetrics.threeYearValue || "—"}`;
  const risksCountDiff = `${previous.businessCase.risks.length} risks → ${current.businessCase.risks.length} risks`;

  const hasChanges =
    prevMetrics.roi !== currMetrics.roi ||
    prevMetrics.payback !== currMetrics.payback ||
    prevMetrics.threeYearValue !== currMetrics.threeYearValue ||
    previous.businessCase.risks.length !== current.businessCase.risks.length;

  return {
    priorVersion: previous.version,
    currentVersion: current.version,
    roiDiff,
    paybackDiff,
    valueDiff,
    risksCountDiff,
    hasChanges,
  };
}

export function buildResultViewModel(
  version: ValueCaseArtifactVersion | null
): ValueCaseResultViewModel | null {
  if (!version) return null;

  const isPublished = version.status.toLowerCase() === "published";

  return {
    id: version.id,
    version: version.version,
    versionLabel: `v${version.version}`,
    isPublished,
    statusBadgeVariant: isPublished ? "default" : "secondary",
    statusBadgeLabel: isPublished ? "Published" : "Draft",
    createdAtFormatted: formatPresentationDate(version.createdAt),
    narrativeTitle: version.narrative.title || version.title || "Value Case",
    narrativeSections: version.narrative.sections.map(s => ({
      heading: s.title || "Section",
      content: s.content || "",
    })),
    businessCaseSummary:
      version.businessCase.summary || "No executive summary available.",
    metrics: buildMetricCardViewModels(version.businessCase.metrics),
    stakeholderFraming: version.stakeholderFraming.map(sf => ({
      role: sf.role || "",
      priorities: sf.priorities,
      valueMessage: sf.valueMessage || "",
    })),
    risks: version.businessCase.risks,
  };
}

export const buildValueCaseResultViewModel = buildResultViewModel;
export const buildValueCaseVersionSummaries = buildVersionSummaryViewModels;
export const buildValueCaseVersionDiff = buildVersionDiffViewModel;
export const buildValueCaseMetricsViewModels = buildMetricCardViewModels;
