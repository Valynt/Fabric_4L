import type { UserTier } from "@/hooks";
import { isValueStudioMissionPrototypeEnabled } from "@/features/value-studio/mission/prototype";

const PROTOTYPE_GATED_NODES: Readonly<Record<string, boolean>> = {
  "studio-mission": isValueStudioMissionPrototypeEnabled,
};

/** Prototype-gated nodes are hidden from navigation when their flag is off. */
export function isNavNodeEnabled(node: NavSchemaNode): boolean {
  if (!node.prototypeOnly) return true;
  return PROTOTYPE_GATED_NODES[node.id] ?? false;
}

export interface NavSchemaNode {
  id: string;
  label: string;
  path: string;
  tier: UserTier;
  badge?: string;
  description?: string;
  breadcrumbLabel?: string;
  /**
   * Prototype-gated child: hidden from navigation unless the build explicitly
   * enables it (see isNavNodeEnabled in this module).
   */
  prototypeOnly?: boolean;
  /** Core children lead the section and are surfaced in the left sidebar. */
  core?: boolean;
  children?: NavSchemaNode[];
}

export const NAV_SCHEMA: NavSchemaNode[] = [
  { id: "home", label: "Home", path: "/home", tier: "standard", description: "Dashboard & prospect prompt builder" },
  { id: "accounts", label: "Accounts", path: "/t/:tenantSlug/accounts", tier: "standard", description: "Select or create a prospect account" },
  {
    id: "intelligence",
    label: "Intelligence",
    path: "/t/:tenantSlug/accounts/:accountId/intelligence",
    tier: "standard",
    description: "Discover and validate prospect pain signals",
    children: [
      { id: "intel-overview", label: "Overview", path: "/t/:tenantSlug/accounts/:accountId/intelligence/overview", tier: "standard", core: true },
      { id: "intel-signals", label: "Signals", path: "/t/:tenantSlug/accounts/:accountId/intelligence/signals", tier: "standard", core: true },
      { id: "intel-drivers", label: "Drivers", path: "/t/:tenantSlug/accounts/:accountId/intelligence/drivers", tier: "standard", core: true },
      { id: "intel-evidence", label: "Evidence", path: "/t/:tenantSlug/accounts/:accountId/intelligence/evidence", tier: "standard", core: true },
      { id: "intel-stakeholders", label: "Stakeholders", path: "/t/:tenantSlug/accounts/:accountId/intelligence/stakeholders", tier: "standard", core: true },
      { id: "intel-enrichment", label: "Enrichment", path: "/t/:tenantSlug/accounts/:accountId/intelligence/enrichment", tier: "advanced" },
      { id: "intel-ontology-match", label: "Value Ontology", path: "/t/:tenantSlug/accounts/:accountId/intelligence/ontology-match", tier: "advanced" },
      { id: "intel-hypotheses", label: "Value Hypotheses", path: "/t/:tenantSlug/accounts/:accountId/intelligence/hypotheses", tier: "standard" },
      { id: "intel-discovery-questions", label: "Discovery Questions", path: "/t/:tenantSlug/accounts/:accountId/intelligence/discovery-questions", tier: "standard" },
      { id: "intel-persona-fit", label: "Persona Fit", path: "/t/:tenantSlug/accounts/:accountId/intelligence/persona-fit", tier: "standard" },
      { id: "intel-assumptions", label: "Assumptions", path: "/t/:tenantSlug/accounts/:accountId/intelligence/assumptions", tier: "standard" },
      { id: "intel-alternatives", label: "Alternatives", path: "/t/:tenantSlug/accounts/:accountId/intelligence/alternatives", tier: "advanced" },
      { id: "intel-solution-cost", label: "Solution Cost", path: "/t/:tenantSlug/accounts/:accountId/intelligence/solution-cost", tier: "advanced" },
    ],
  },
  {
    id: "studio",
    label: "Value Studio",
    path: "/t/:tenantSlug/accounts/:accountId/studio",
    tier: "standard",
    description: "Build the product-anchored business case",
    children: [
      { id: "studio-mission", label: "Mission", path: "/t/:tenantSlug/accounts/:accountId/studio/mission", tier: "standard", prototypeOnly: true },
      { id: "studio-action-plan", label: "Action Plan", path: "/t/:tenantSlug/accounts/:accountId/studio/action-plan", tier: "standard" },
      { id: "studio-value-model", label: "Value Model", path: "/t/:tenantSlug/accounts/:accountId/studio/value-model", tier: "standard" },
      { id: "studio-driver-tree", label: "Driver Tree", path: "/t/:tenantSlug/accounts/:accountId/studio/driver-tree", tier: "standard" },
      { id: "studio-calculator", label: "Calculator", path: "/t/:tenantSlug/accounts/:accountId/studio/calculator", tier: "standard" },
      { id: "studio-narrative", label: "Narrative", path: "/t/:tenantSlug/accounts/:accountId/studio/narrative", tier: "standard" },
      { id: "studio-value-case", label: "Value Case", path: "/t/:tenantSlug/accounts/:accountId/studio/value-case", tier: "standard" },
      { id: "studio-value-realization", label: "Realization", path: "/t/:tenantSlug/accounts/:accountId/studio/value-realization", tier: "standard" },
    ],
  },
  {
    id: "deliverables",
    label: "Deliverables",
    path: "/t/:tenantSlug/accounts/:accountId/deliverables",
    tier: "standard",
    description: "Packaged outputs for sharing",
    children: [
      { id: "deliv-business-cases", label: "Business Cases", path: "/t/:tenantSlug/accounts/:accountId/deliverables/business-cases", tier: "standard" },
      { id: "deliv-proposals", label: "Proposals", path: "/t/:tenantSlug/accounts/:accountId/deliverables/proposals", tier: "standard" },
      { id: "deliv-exports", label: "Exports", path: "/t/:tenantSlug/accounts/:accountId/deliverables/exports", tier: "standard" },
      { id: "deliv-view-cfo", label: "CFO View", path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/cfo", tier: "standard" },
      { id: "deliv-view-executive", label: "Executive View", path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/executive", tier: "standard" },
      { id: "deliv-view-technical", label: "Technical View", path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/technical", tier: "standard" },
    ],
  },
  {
    id: "context-engine",
    label: "Context Engine",
    path: "/t/:tenantSlug/context",
    tier: "standard",
    description: "Value packs, models, formulas, and agents",
    children: [
      { id: "ctx-packs", label: "Packs", path: "/t/:tenantSlug/context/packs", tier: "standard" },
      { id: "ctx-models", label: "Models", path: "/t/:tenantSlug/context/models", tier: "standard" },
      { id: "ctx-formulas", label: "Formulas", path: "/t/:tenantSlug/context/formulas", tier: "advanced" },
      { id: "ctx-value-trees", label: "Value Trees", path: "/t/:tenantSlug/context/value-trees/explorer", tier: "advanced" },
      { id: "ctx-agents", label: "Agents", path: "/t/:tenantSlug/context/agents", tier: "advanced" },
      { id: "ctx-ontology", label: "Ontology", path: "/t/:tenantSlug/context/ontology", tier: "advanced" },
      { id: "ctx-ontology-entities", label: "Entities", path: "/t/:tenantSlug/context/ontology/entities", tier: "advanced" },
      { id: "ctx-ontology-graph", label: "Graph", path: "/t/:tenantSlug/context/ontology/graph", tier: "advanced" },
      { id: "ctx-ingestion", label: "Ingestion Jobs", path: "/t/:tenantSlug/context/ingestion/jobs", tier: "standard" },
      { id: "ctx-extraction", label: "Extraction", path: "/t/:tenantSlug/context/extraction", tier: "advanced" },
      { id: "ctx-integrations", label: "Integrations", path: "/t/:tenantSlug/context/integrations", tier: "admin" },
      { id: "ctx-sources", label: "Sources", path: "/t/:tenantSlug/context/sources", tier: "admin" },
      { id: "ctx-targets", label: "Targets", path: "/t/:tenantSlug/context/targets", tier: "admin" },
    ],
  },
  {
    id: "governance",
    label: "Governance",
    path: "/t/:tenantSlug/governance",
    tier: "standard",
    description: "Audit, provenance, and compliance",
    children: [
      { id: "gov-traces", label: "Traces", path: "/t/:tenantSlug/governance/traces", tier: "standard" },
      { id: "gov-evidence", label: "Evidence", path: "/t/:tenantSlug/governance/evidence", tier: "standard" },
      { id: "gov-provenance", label: "Provenance", path: "/t/:tenantSlug/governance/provenance", tier: "advanced" },
      { id: "gov-compliance", label: "Compliance", path: "/t/:tenantSlug/governance/compliance", tier: "advanced" },
      { id: "gov-formulas", label: "Formulas", path: "/t/:tenantSlug/governance/formulas", tier: "advanced" },
      { id: "gov-benchmarks", label: "Benchmarks", path: "/t/:tenantSlug/governance/benchmarks", tier: "admin" },
      { id: "gov-value-packs", label: "Value Packs", path: "/t/:tenantSlug/governance/value-packs", tier: "standard" },
      { id: "gov-policies", label: "Policies", path: "/t/:tenantSlug/governance/policies", tier: "admin" },
      { id: "gov-audit-log", label: "Audit Log", path: "/t/:tenantSlug/governance/audit-log", tier: "admin" },
      { id: "gov-health", label: "Health", path: "/t/:tenantSlug/governance/health", tier: "admin" },
      { id: "gov-billing", label: "Billing & Subscription", path: "/t/:tenantSlug/governance/billing", tier: "admin" },
    ],
  },
  {
    id: "academy",
    label: "Academy",
    path: "/t/:tenantSlug/academy",
    tier: "standard",
    description: "Master the Value Operating System",
  },
  {
    id: "personal-settings",
    label: "Settings",
    path: "/settings",
    tier: "standard",
    description: "Personal user settings",
  },
  {
    id: "tenant-settings",
    label: "Workspace Settings",
    path: "/t/:tenantSlug/settings",
    tier: "admin",
    description: "Tenant configuration and administration",
  },
];

export interface BreadcrumbItem { label: string; path?: string }

function flatten(nodes: NavSchemaNode[]): NavSchemaNode[] {
  return nodes.flatMap((node) => [node, ...(node.children ? flatten(node.children) : [])]);
}

function segmentMatches(patternSeg: string, actualSeg: string): boolean {
  if (patternSeg.startsWith(":")) return Boolean(actualSeg);
  return patternSeg === actualSeg;
}

function routeMatches(pattern: string, actual: string): boolean {
  const p = pattern.split("/").filter(Boolean);
  const a = actual.split("/").filter(Boolean);
  if (p.length !== a.length) return false;
  return p.every((seg, i) => segmentMatches(seg, a[i] || ""));
}

function isDynamicPrefixSegment(pathname: string): boolean {
  const actual = pathname.split("/").filter(Boolean);
  const nodes = flatten(NAV_SCHEMA);
  return nodes.some((node) => {
    const pattern = node.path.split("/").filter(Boolean);
    if (actual.length > pattern.length) return false;
    const targetIndex = actual.length - 1;
    if (targetIndex < 0) return false;
    const allMatch = actual.every((_, idx) => segmentMatches(pattern[idx] || "", actual[idx] || ""));
    if (!allMatch) return false;
    // Current segment is dynamic if it's a param, OR if the pattern has more
    // segments (we're in the middle of a multi-segment path like /t/:tenantSlug/...)
    return pattern[targetIndex]?.startsWith(":") || actual.length < pattern.length;
  });
}
function labelForSegment(segment: string): string {
  return segment.split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

export function resolveBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const pathSegments = pathname.split("/").filter(Boolean);
  if (pathSegments.length === 0) return [{ label: "Value Fabric" }];

  const nodes = flatten(NAV_SCHEMA);
  const crumbs: BreadcrumbItem[] = [];

  for (let i = 0; i < pathSegments.length; i++) {
    const segmentPath = ['', ...pathSegments.slice(0, i + 1)].join('/');
    const matched = nodes.find((node) => routeMatches(node.path, segmentPath));
    if (matched) {
      crumbs.push({
        label: matched.breadcrumbLabel ?? matched.label,
        path: segmentPath,
      });
      continue;
    }

    const segment = pathSegments[i] || "";
    const isOpaqueId = /^[0-9a-f-]{8,}$/i.test(segment) || /^\d+$/.test(segment);
    const dynamicSegment = isDynamicPrefixSegment(segmentPath);
    if (isOpaqueId || dynamicSegment) continue;

    crumbs.push({ label: labelForSegment(segment), path: segmentPath });
  }

  const deduped: BreadcrumbItem[] = [];
  for (const crumb of crumbs) {
    if (!deduped.some((item) => item.path === crumb.path && item.label === crumb.label)) deduped.push(crumb);
  }
  return deduped;
}
