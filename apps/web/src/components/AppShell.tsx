/**
 * AppShell — Refined Enterprise SaaS layout
 * Three-mode navigation per gap analysis spec:
 *   Standard  — task-oriented for business users
 *   Advanced  — power-user modeling & inspection tools
 *   Admin     — tenant governance & configuration
 *
 * Fixed sidebar (216px) + sticky header (52px) + scrollable main content
 *
 * Wrapped in React.memo so the layout (header + sidebar) does NOT re-render
 * on every route change. Only re-renders when tier or i18n locale changes.
 */
import { memo, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { TieredNav, type UserTier, NAV_SPINE } from "./navigation/TieredNav";
import { MobilePersistentSidebar } from "./navigation/MobilePersistentSidebar";
import { AccountPicker } from "./navigation/AccountPicker";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { useAccounts } from "@/hooks";
import { useAuthContext } from "@/contexts/AuthContext";
import { Search, Bell, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";
import { GlobalSearchDialog } from "./search/GlobalSearchDialog";

// ── Types ─────────────────────────────────────────────────────────────────────

type UserMode = "standard" | "advanced" | "admin";

const MODE_PILL: Record<UserMode, string> = {
  standard: "bg-primary/10 text-primary border-primary/20",
  advanced: "bg-accent/10 text-accent border-accent/20",
  admin:    "bg-destructive/10 text-destructive border-destructive/20",
};

// ── Main AppShell ─────────────────────────────────────────────────────────────

interface AppShellProps {
  children: React.ReactNode;
  currentTier?: UserTier;
  effectiveTier?: UserTier;
}

/**
 * AppShell is memoized to prevent the full layout (header + sidebar) from
 * re-rendering on every route change. Because `children` is a new reference
 * on each render, we use a custom equality function that ignores children
 * and only re-renders when tier props change.
 */
const AppShell = memo(function AppShell({ 
  children, 
  currentTier: externalCurrentTier,
  effectiveTier: externalEffectiveTier 
}: AppShellProps) {
  const { t } = useI18n();
  // Use internal state if external props not provided (backward compatibility)
  const [internalMode, setInternalMode] = useState<UserTier>("standard");
  const [isAdvancedMode, setIsAdvancedMode] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  
  const currentTier = externalCurrentTier || internalMode;
  // Advanced mode controls presentation only; it never elevates authorization.
  const effectiveTier = externalEffectiveTier || currentTier;
  
  const handleTierChange = useCallback((tier: UserTier) => {
    if (!externalCurrentTier) {
      setInternalMode(tier);
    }
  }, [externalCurrentTier]);
  
  const handleAdvancedModeToggle = useCallback((enabled: boolean) => {
    setIsAdvancedMode(enabled);
  }, []);

  const selectedAccountId = useAccountContextStore(state => state.selectedAccountId);
  const setSelectedAccountId = useAccountContextStore(state => state.setSelectedAccountId);
  const {
    user: currentUser,
    logout,
    currentTenantSlug,
    isAuthenticated,
    isLoading: authLoading,
  } = useAuthContext();
  const shouldLoadAccounts = !authLoading && isAuthenticated && Boolean(currentTenantSlug);
  const { data: accountsData, isLoading: accountsLoading, error: accountsError } = useAccounts(
    { page_size: 100 },
    { enabled: shouldLoadAccounts, suppressAuthRedirect: true }
  );
  const accounts = accountsData?.items ?? [];

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden">
      {/* Header */}
      <header className="h-[52px] shrink-0 bg-card border-b border-border flex items-center px-4 gap-4 z-30">
        <Link to="/command-center">
          <div className="flex flex-col leading-none cursor-pointer select-none">
            <span className="vf-text-body-l font-extrabold text-foreground tracking-tight">{t("appShell.platformName")}</span>
            <span className="vf-text-micro text-muted-foreground font-normal">{t("appShell.platformTagline")}</span>
          </div>
        </Link>
        <div className="flex-1 max-w-xs">
          <button type="button"
            onClick={() => setIsSearchOpen(true)}
            className="flex items-center gap-2 h-7 px-3 bg-muted rounded-full vf-text-caption text-muted-foreground border border-border hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer w-full"
          >
            <Search size={11} className="shrink-0"/>
            <span>{t("appShell.searchPlaceholder")}</span>
            <kbd className="ml-auto vf-text-micro bg-background border border-border rounded px-1.5 py-0.5 opacity-60">
              ⌘K
            </kbd>
          </button>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {/* Active mode pill */}
          <span className={cn(
            "vf-text-micro font-semibold px-2.5 py-0.5 rounded-full border",
            MODE_PILL[currentTier as UserMode]
          )}>
            {`${t(`appShell.modes.${currentTier as UserMode}`)} ${t("appShell.modeSuffix")}`}
          </span>
          <button type="button" className="w-7 h-7 rounded-full border border-border bg-secondary flex items-center justify-center text-muted-foreground hover:bg-muted transition-colors">
            <Bell size={12}/>
          </button>
          <button type="button" className="w-7 h-7 rounded-full bg-foreground text-background flex items-center justify-center vf-text-micro font-bold">
            <User size={12}/>
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Desktop sidebar — hidden on mobile */}
        <div className="hidden md:block">
          <TieredNav
            currentTier={currentTier}
            onTierChange={handleTierChange}
            isAdvancedModeEnabled={isAdvancedMode}
            onAdvancedModeToggle={handleAdvancedModeToggle}
            headerSlot={
              <AccountPicker
                accounts={accounts}
                selectedAccountId={selectedAccountId}
                onSelectAccount={setSelectedAccountId}
                isLoading={accountsLoading}
                error={accountsError}
                variant="full"
              />
            }
          />
        </div>

        {/* Mobile persistent sidebar — visible only below md breakpoint */}
        <div className="flex md:hidden">
          <MobilePersistentSidebar
            currentTier={currentTier}
            effectiveTier={effectiveTier}
            onTierChange={handleTierChange}
            isAdvancedModeEnabled={isAdvancedMode}
            onAdvancedModeToggle={handleAdvancedModeToggle}
            navItems={NAV_SPINE}
            accounts={accounts}
            selectedAccountId={selectedAccountId}
            onSelectAccount={setSelectedAccountId}
            isAccountsLoading={accountsLoading}
            accountsError={accountsError}
            user={currentUser ? { email: currentUser.email } : null}
            onSignOut={logout}
          />
        </div>

        {/* Main — children change on every route; AppShell shell stays stable */}
        <main className="flex-1 overflow-y-auto bg-background" data-tier={effectiveTier}>
          {children}
        </main>
      </div>
      
      {/* Global Search Dialog */}
      <GlobalSearchDialog
        open={isSearchOpen}
        onOpenChange={setIsSearchOpen}
        tenantSlug={currentTenantSlug || undefined}
        accountId={selectedAccountId || undefined}
      />
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom equality: ignore children (always new ref), only re-render on tier changes
  return (
    prevProps.currentTier === nextProps.currentTier &&
    prevProps.effectiveTier === nextProps.effectiveTier
  );
});

export default AppShell;
