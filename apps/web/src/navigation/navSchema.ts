import type { UserTier } from "@/hooks";

export interface NavSchemaNode {
  id: string;
  label: string;
  path: string;
  tier: UserTier;
  badge?: string;
  description?: string;
  breadcrumbLabel?: string;
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
      { id: "intel-signals", label: "Signals", path: "/t/:tenantSlug/accounts/:accountId/intelligence/signals", tier: "standard" },
      { id: "intel-enrichment", label: "Enrichment", path: "/t/:tenantSlug/accounts/:accountId/intelligence/enrichment", tier: "advanced" },
      { id: "intel-stakeholders", label: "Stakeholders", path: "/t/:tenantSlug/accounts/:accountId/intelligence/stakeholders", tier: "standard" },
      { id: "intel-ontology-match", label: "Value Ontology", path: "/t/:tenantSlug/accounts/:accountId/intelligence/ontology-match", tier: "advanced" },
      { id: "intel-hypotheses", label: "Value Hypotheses", path: "/t/:tenantSlug/accounts/:accountId/intelligence/hypotheses", tier: "standard" },
      { id: "intel-discovery-questions", label: "Discovery Questions", path: "/t/:tenantSlug/accounts/:accountId/intelligence/discovery-questions", tier: "standard" },
      { id: "intel-persona-fit", label: "Persona Fit", path: "/t/:tenantSlug/accounts/:accountId/intelligence/persona-fit", tier: "standard" },
      { id: "intel-assumptions", label: "Assumptions", path: "/t/:tenantSlug/accounts/:accountId/intelligence/assumptions", tier: "standard" },
      { id: "intel-drivers", label: "Value Drivers", path: "/t/:tenantSlug/accounts/:accountId/intelligence/drivers", tier: "standard" },
      { id: "intel-evidence", label: "Evidence", path: "/t/:tenantSlug/accounts/:accountId/intelligence/evidence", tier: "standard" },
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
  },
  {
    id: "context-engine",
    label: "Context Engine",
    path: "/t/:tenantSlug/context",
    tier: "standard",
    description: "Value packs, models, formulas, and agents",
  },
  {
    id: "governance",
    label: "Governance",
    path: "/t/:tenantSlug/governance",
    tier: "standard",
    description: "Audit, provenance, and compliance",
  },
  {
    id: "settings",
    label: "Settings",
    path: "/settings",
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
