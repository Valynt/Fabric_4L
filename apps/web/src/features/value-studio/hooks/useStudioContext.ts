/**
 * useStudioContext — Provides account + studio context to tabs
 */
import { useParams } from "react-router-dom";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { useAccount } from "@/hooks";

export function useStudioContext() {
  const params = useParams<{ tenantSlug: string; accountId: string; tabId: string }>();
  const accountId = params.accountId ?? "";
  const tabId = params.tabId ?? "action-plan";
  const selectedAccountId = useAccountContextStore((s) => s.selectedAccountId);
  const resolvedAccountId = accountId || selectedAccountId || "";

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
