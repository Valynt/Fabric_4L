import { useState, useMemo, useCallback } from "react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { Check, ChevronsUpDown, Plus, Search } from "lucide-react";
import type { Account } from "@/hooks/useAccounts";

export interface AccountPickerProps {
  accounts: Account[];
  selectedAccountId: string | null;
  onSelectAccount: (accountId: string) => void;
  onCreateAccount?: () => void;
  isLoading?: boolean;
  error?: Error | null;
  variant?: "compact" | "full";
  className?: string;
}

function PickerContent({ accounts, selectedAccountId, onSelectAccount, onCreateAccount, isLoading, error }: Pick<AccountPickerProps, "accounts" | "selectedAccountId" | "onSelectAccount" | "onCreateAccount" | "isLoading" | "error">) {
  const [searchQuery, setSearchQuery] = useState("");
  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return accounts;
    const q = searchQuery.toLowerCase();
    return accounts.filter(a => a.name.toLowerCase().includes(q) || a.domain?.toLowerCase().includes(q) || a.industry?.toLowerCase().includes(q));
  }, [accounts, searchQuery]);

  return (
    <>
      <div className="p-3 border-b border-border">
        <p className="text-xs font-semibold text-foreground">Select Account</p>
        <p className="text-xs text-muted-foreground mt-0.5">Choose an account to work with</p>
      </div>
      <div className="p-2">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground pointer-events-none" />
          <Input placeholder="Search accounts…" className="h-8 pl-7 text-xs" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} aria-label="Search accounts" />
        </div>
      </div>
      <ScrollArea className="h-48">
        <div className="p-1">
          {isLoading ? (
            <div className="px-2 py-4 text-xs text-muted-foreground text-center">Loading accounts…</div>
          ) : error ? (
            <div className="px-2 py-4 text-xs text-destructive text-center">Failed to load accounts</div>
          ) : filtered.length === 0 ? (
            <div className="px-2 py-4 text-xs text-muted-foreground text-center">{searchQuery ? "No accounts match your search" : "No accounts available"}</div>
          ) : (
            filtered.map(account => (
              <DropdownMenuItem key={account.id} onClick={() => onSelectAccount(account.id)} className="flex items-center gap-2 px-2 py-2 text-xs cursor-pointer">
                <Avatar className="size-6"><AvatarFallback className="bg-primary/10 text-primary text-xs font-bold">{account.name.charAt(0).toUpperCase()}</AvatarFallback></Avatar>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{account.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{account.domain || account.industry || "No details"}</p>
                </div>
                {selectedAccountId === account.id && <Check className="size-3.5 text-primary shrink-0" />}
              </DropdownMenuItem>
            ))
          )}
        </div>
      </ScrollArea>
      {onCreateAccount && (
        <>
          <DropdownMenuSeparator />
          <div className="p-1">
            <DropdownMenuItem onClick={onCreateAccount} className="flex items-center gap-2 px-2 py-2 text-xs cursor-pointer text-primary focus:text-primary">
              <Plus className="size-3.5 shrink-0" />Create new account
            </DropdownMenuItem>
          </div>
        </>
      )}
    </>
  );
}

export function AccountPicker({ accounts, selectedAccountId, onSelectAccount, onCreateAccount, isLoading, error, variant = "full", className }: AccountPickerProps) {
  const [open, setOpen] = useState(false);
  const selectedAccount = useMemo(() => accounts.find(a => a.id === selectedAccountId) || null, [accounts, selectedAccountId]);
  const handleSelect = useCallback((accountId: string) => { onSelectAccount(accountId); setOpen(false); }, [onSelectAccount]);

  if (variant === "compact") {
    return (
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild>
          <button className={cn("flex flex-col items-center justify-center gap-1 w-full py-3 px-1 rounded-lg transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground active:bg-sidebar-accent focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-sidebar-ring", selectedAccount ? "text-sidebar-primary" : "text-sidebar-foreground/60", className)} aria-label={selectedAccount ? `Current account: ${selectedAccount.name}. Open account picker.` : "Select an account"}>
            <div className="relative">
              <Avatar className="size-8 border-2 border-sidebar-primary/20"><AvatarFallback className="bg-sidebar-primary text-sidebar-primary-foreground text-xs font-bold">{selectedAccount?.name?.charAt(0)?.toUpperCase() || "?"}</AvatarFallback></Avatar>
              {selectedAccount && <span className="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full bg-success/100 border-2 border-sidebar" />}
            </div>
            <span className="text-xs font-medium truncate max-w-full px-0.5 leading-tight">{selectedAccount?.name || "Account"}</span>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent side="right" align="start" className="w-72 p-0" sideOffset={8}>
          <PickerContent accounts={accounts} selectedAccountId={selectedAccountId} onSelectAccount={handleSelect} onCreateAccount={onCreateAccount} isLoading={isLoading} error={error} />
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button className={cn("flex items-center gap-2 w-full px-3 py-2.5 rounded-lg border transition-colors text-left hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-sidebar-ring", selectedAccount ? "border-sidebar-primary/30 bg-sidebar-primary/5 text-sidebar-foreground" : "border-sidebar-border bg-sidebar text-sidebar-foreground/60", className)} aria-label={selectedAccount ? `Current account: ${selectedAccount.name}. Open account picker.` : "Select an account"}>
          <Avatar className="size-7"><AvatarFallback className="bg-sidebar-primary text-sidebar-primary-foreground text-xs font-bold">{selectedAccount?.name?.charAt(0)?.toUpperCase() || "?"}</AvatarFallback></Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium truncate">{selectedAccount?.name || "Select account"}</p>
            <p className="text-xs text-muted-foreground truncate">{selectedAccount?.domain || "No account selected"}</p>
          </div>
          <ChevronsUpDown className="size-3.5 text-muted-foreground shrink-0" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-72 p-0" align="start" sideOffset={4}>
        <PickerContent accounts={accounts} selectedAccountId={selectedAccountId} onSelectAccount={handleSelect} onCreateAccount={onCreateAccount} isLoading={isLoading} error={error} />
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default AccountPicker;
