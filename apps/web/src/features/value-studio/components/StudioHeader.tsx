/**
 * StudioHeader — Account context header for Value Studio workspace
 */
import { useParams } from "react-router-dom";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { useAccount } from "@/hooks";

export default function StudioHeader() {
  const { accountId } = useParams<{ accountId: string }>();
  const selectedAccountId = useAccountContextStore((s) => s.selectedAccountId);
  const resolvedAccountId = accountId || selectedAccountId || "";
  const { data: account } = useAccount(resolvedAccountId || null);

  return (
    <div className="flex items-center justify-between px-6 py-3 border-b border-border bg-background">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold">
          {account?.name ?? "Value Studio"}
        </h1>
        {account?.industry && (
          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
            {account.industry}
          </span>
        )}
      </div>
    </div>
  );
}
