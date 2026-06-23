/**
 * StudioHeader — Account context header for Value Studio workspace
 *
 * Renders the single account header for the whole workspace: account name,
 * industry, revenue, and a link back to the Intelligence workspace.
 */
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Building2 } from "lucide-react";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { useAccount } from "@/hooks";
import { buildPath } from "@/navigation/navigationService";
import { Btn } from "@/components/ui/fabric";

export default function StudioHeader() {
  const { tenantSlug = "", accountId = "" } = useParams<{ tenantSlug: string; accountId: string }>();
  const selectedAccountId = useAccountContextStore((s) => s.selectedAccountId);
  const resolvedAccountId = accountId || selectedAccountId || "";
  const { data: account } = useAccount(resolvedAccountId || null);

  const revenue = account?.annual_revenue ? `$${account.annual_revenue.toLocaleString()}` : "N/A";
  const intelligenceHref = buildPath("/t/:tenantSlug/accounts/:accountId/intelligence/:tab", {
    tenantSlug,
    accountId: resolvedAccountId,
    tab: "signals",
  });

  return (
    <div className="flex items-center gap-3 px-6 py-3 border-b border-border bg-background shrink-0 vf-text-body-s">
      <Building2 size={14} className="text-muted-foreground shrink-0" />
      <span className="font-semibold text-foreground">{account?.name ?? "Value Studio"}</span>
      <span className="text-muted-foreground">·</span>
      <span className="text-muted-foreground">{account?.industry ?? "Unknown"}</span>
      <span className="text-muted-foreground">·</span>
      <span className="text-muted-foreground">{revenue}</span>
      <div className="flex-1" />
      <Link to={intelligenceHref}>
        <Btn variant="outline" className="gap-1.5">
          <ArrowLeft size={13} />
          Back to Intelligence
        </Btn>
      </Link>
    </div>
  );
}
