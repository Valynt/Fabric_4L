/**
 * Builds in-workspace links to sibling tabs, preserving tenant + account context.
 */
import { useWorkspaceContext } from "../../hooks/useWorkspaceContext";
import { workspacePath } from "../../workspaceRoutes";
import type { IntelligenceTabId } from "../../types";

export function useTabLink() {
  const { tenantSlug, accountId } = useWorkspaceContext();
  return (tabId: IntelligenceTabId) =>
    workspacePath(tenantSlug ?? "", accountId ?? "", tabId);
}
