/**
 * Intelligence Workspace — Route Helpers
 *
 * All workspace routes follow:
 *   /accounts/:accountId/intelligence/:tabId
 */
import { getTabOrDefault } from "./workspaceTabRegistry";

export function workspacePath(
  tenantSlug: string,
  accountId: string,
  tabId?: string
): string {
  const resolvedTab = getTabOrDefault(tabId);
  return `/t/${tenantSlug}/accounts/${accountId}/intelligence/${resolvedTab}`;
}

export function workspaceBasePath(tenantSlug: string, accountId: string): string {
  return `/t/${tenantSlug}/accounts/${accountId}/intelligence`;
}

export function parseWorkspaceRoute(pathname: string): {
  tenantSlug: string | null;
  accountId: string | null;
  tabId: string | null;
} {
  // Expected: /t/:tenantSlug/accounts/:accountId/intelligence/:tabId
  const match = pathname.match(
    /^\/t\/([^/]+)\/accounts\/([^/]+)\/intelligence\/([^/]+)/
  );
  if (match) {
    return { tenantSlug: match[1], accountId: match[2], tabId: match[3] };
  }
  // Also match: /t/:tenantSlug/accounts/:accountId/intelligence (no tab)
  const baseMatch = pathname.match(
    /^\/t\/([^/]+)\/accounts\/([^/]+)\/intelligence\/?$/
  );
  if (baseMatch) {
    return { tenantSlug: baseMatch[1], accountId: baseMatch[2], tabId: null };
  }
  return { tenantSlug: null, accountId: null, tabId: null };
}
