/**
 * useWorkspaceContext — Provides account + workspace context to tabs
 */
import { useParams } from "react-router-dom";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { useAccount } from "@/hooks";
import { useWorkflowSessionContext } from "@/hooks/useWorkflowSessionContext";

export function useWorkspaceContext() {
  const params = useParams<{ tenantSlug: string; accountId: string; tabId: string }>();
  const accountId = params.accountId ?? "";
  const { workflowContext } = useWorkflowSessionContext();
  const tabId = params.tabId ?? workflowContext.tabId ?? "overview";
  const selectedAccountId = useAccountContextStore((s) => s.selectedAccountId);
  const resolvedAccountId = accountId || workflowContext.accountId || selectedAccountId || "";

  const { data: account } = useAccount(resolvedAccountId || null);

  return {
    tenantSlug: params.tenantSlug ?? "",
    accountId: resolvedAccountId,
    tabId,
    accountName: account?.name ?? "",
    industry: account?.industry ?? "",
    revenue: account?.annual_revenue ? `$${account.annual_revenue.toLocaleString()}` : "",
  };
}
