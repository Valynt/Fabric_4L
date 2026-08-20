/**
 * ValueCasePage — Value Case workspace entry point
 *
 * Route: /value-case/:accountId
 */
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { ValueCaseWorkspace } from "@/features/value-case";
import type { StudioTabProps } from "@/features/value-studio/types";

export default function ValueCasePage({ accountId }: StudioTabProps) {
  const { data: account } = useAccount(accountId ?? null);

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  return (
    <ValueCaseWorkspace
      accountId={accountId}
      accountName={account?.name ?? "Account"}
    />
  );
}

