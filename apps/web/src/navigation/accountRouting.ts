import { getStatePath, buildPath, type RouteState } from './navigationService';

export type AccountWorkspace = "intelligence" | "studio";

const WORKSPACE_TABS = {
  intelligence: [
    "signals",
    "enrichment",
    "stakeholders",
    "ontology-match",
    "hypotheses",
    "discovery-questions",
    "persona-fit",
    "assumptions",
    "drivers",
    "evidence",
    "alternatives",
    "solution-cost",
  ],
  studio: [
    "action-plan",
    "value-model",
    "driver-tree",
    "calculator",
    "narrative",
    "value-case",
    "value-realization",
    "solution-cost",
  ],
} as const;

const DEFAULT_WORKSPACE_TAB: Record<AccountWorkspace, string> = {
  intelligence: "signals",
  studio: "action-plan",
};

export function isValidWorkspaceTab(workspace: AccountWorkspace, tab: string | undefined): tab is string {
  return Boolean(tab) && WORKSPACE_TABS[workspace].includes(tab as never);
}

export function getWorkspaceTabOrDefault(
  workspace: AccountWorkspace,
  tab: string | undefined
): string {
  return isValidWorkspaceTab(workspace, tab) ? tab : DEFAULT_WORKSPACE_TAB[workspace];
}

export function resolveWorkspaceRoutePath(
  path: string,
  accountId: string | null,
  tenantSlug: string | null = null
): string {
  if (!accountId) return path;

  const pathMap: Record<string, RouteState> = {
    '/intelligence': 'intelligence',
    '/studio': 'studio',
  };

  for (const [prefix, state] of Object.entries(pathMap)) {
    if (path === prefix) {
      return getStatePath(state, { tenantSlug: tenantSlug ?? "default", accountId });
    }
    if (path.startsWith(`${prefix}/`)) {
      const suffix = path.slice(prefix.length + 1);
      return buildPath(`${getStatePath(state, { tenantSlug: tenantSlug ?? "default", accountId })}/:suffix`, { suffix });
    }
  }

  return path;
}

export function resolveAccountScopedWorkspacePath(options: {
  workspace: AccountWorkspace;
  accountId: string | null;
  tab?: string;
  tenantSlug?: string | null;
}): string {
  const { workspace, accountId, tab, tenantSlug } = options;
  if (!accountId) return "/t/default/accounts";

  const resolvedTab = getWorkspaceTabOrDefault(workspace, tab);
  const state: RouteState = workspace === 'intelligence' ? 'intelligence' : 'studio';
  const basePath = getStatePath(state, { tenantSlug: tenantSlug ?? "default", accountId });

  return buildPath(`${basePath}/:tab`, { tab: resolvedTab });
}
