/**
 * Account Picker Modal
 */
import { useCallback } from "react";
import { useNavigation } from "@/hooks/useNavigation";
import { useAuthContext } from "@/contexts/AuthContext";
import { Building2, Plus, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAccounts } from "@/hooks";
import { useAccountContextStore } from "@/stores/accountContextStore";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import {
  resolveAccountScopedWorkspacePath,
  type AccountWorkspace,
} from "@/navigation/accountRouting";
import type { Account } from "@/hooks/useAccounts";

interface AccountPickerModalProps {
  workspace: AccountWorkspace;
  tab?: string;
}

function AccountSkeleton() {
  return (
    <div className="flex items-center gap-3 px-2 py-2">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
        <div className="h-4 w-4 rounded-sm bg-muted-foreground/20 animate-pulse" />
      </div>
      <div className="flex flex-col gap-1.5 flex-1">
        <div className="h-3.5 w-32 bg-muted rounded animate-pulse" />
        <div className="h-2.5 w-20 bg-muted rounded animate-pulse" />
      </div>
    </div>
  );
}

export default function AccountPickerModal({
  workspace,
  tab,
}: AccountPickerModalProps) {
  const { navigateTo } = useNavigation();
  const { currentTenantSlug } = useAuthContext();
  const setSelectedAccountId = useAccountContextStore(
    (state) => state.setSelectedAccountId
  );
  const { data, isLoading, error } = useAccounts({ page_size: 50 });

  const accounts = data?.items ?? [];

  const handleSelect = useCallback(
    (account: Account) => {
      setSelectedAccountId(account.id);
      const path = resolveAccountScopedWorkspacePath({
        workspace,
        accountId: account.id,
        tab,
        tenantSlug: currentTenantSlug,
      });
      navigateTo(path);
    },
    [workspace, tab, setSelectedAccountId, navigateTo, currentTenantSlug]
  );

  const handleManageAccounts = useCallback(() => {
    navigateTo('accounts', { tenantSlug: currentTenantSlug ?? 'default' });
  }, [navigateTo, currentTenantSlug]);

  const handleCreateAccount = useCallback(() => {
    navigateTo('accounts', { tenantSlug: currentTenantSlug ?? 'default' });
  }, [navigateTo, currentTenantSlug]);

  const preventDismiss = useCallback((e: Event) => {
    e.preventDefault();
  }, []);

  return (
    <Dialog open={true} onOpenChange={() => {}}>
      <DialogContent
        className="sm:max-w-md p-0 overflow-hidden gap-0"
        showCloseButton={false}
        onEscapeKeyDown={preventDismiss}
        onPointerDownOutside={preventDismiss}
        onInteractOutside={preventDismiss}
      >
        <DialogHeader className="px-6 pt-6 pb-3">
          <DialogTitle className="text-lg font-semibold">
            Select an Account
          </DialogTitle>
          <DialogDescription className="vf-text-body-m">
            Choose an account to continue to the{" "}
            <span className="font-medium text-foreground capitalize">
              {workspace}
            </span>{" "}
            workspace.
          </DialogDescription>
        </DialogHeader>

        <div className="px-6 pb-6">
          <Command className="rounded-lg border shadow-sm">
            <CommandInput
              placeholder="Search accounts by name or domain..."
              className="h-10"
            />
            <CommandList className="max-h-[320px]">
              {isLoading ? (
                <div className="py-2 space-y-1">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <AccountSkeleton key={i} />
                  ))}
                </div>
              ) : error ? (
                <div className="py-8 text-center">
                  <p className="text-sm text-destructive">
                    Failed to load accounts.
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {error.message}
                  </p>
                </div>
              ) : (
                <>
                  <CommandEmpty className="py-6 text-sm text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                      <Search className="h-5 w-5 opacity-50" />
                      <span>No accounts found.</span>
                    </div>
                  </CommandEmpty>
                  <CommandGroup>
                    {accounts.map((account) => (
                      <CommandItem
                        key={account.id}
                        value={`${account.name} ${account.domain ?? ""} ${account.industry ?? ""}`}
                        onSelect={() => handleSelect(account)}
                        className={cn(
                          "flex items-center gap-3 px-2 py-2 cursor-pointer",
                          "data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground"
                        )}
                      >
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                          <Building2 className="h-4 w-4 text-primary" />
                        </div>
                        <div className="flex flex-col overflow-hidden min-w-0">
                          <span className="text-sm font-medium truncate">
                            {account.name}
                          </span>
                          <span className="text-xs text-muted-foreground truncate">
                            {account.domain}
                            {account.industry ? ` • ${account.industry}` : ""}
                            {account.segment ? ` • ${account.segment}` : ""}
                          </span>
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </>
              )}
            </CommandList>
          </Command>

          <div className="flex items-center justify-between mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={handleManageAccounts}
            >
              Manage Accounts
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCreateAccount}
              className="gap-1"
            >
              <Plus className="h-3.5 w-3.5" />
              New Account
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
