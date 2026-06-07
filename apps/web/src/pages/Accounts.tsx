/**
 * Accounts Page — Customer Account Management
 *
 * Features:
 * - List all accounts with filtering via horizontal chip bar
 * - Data table view with row selection
 * - Account detail panel with actions (Create Case, View Traces, Export)
 * - Search and pagination
 */
import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { PaginationBar } from "@/components/ui/fabric/PaginationBar";
import { useNavigation, useRoutePrefetch } from "@/hooks";
import AccountIntakeModal from "@/components/workspace/AccountIntakeModal";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Skeleton,
  ErrorBoundary,
} from "@/components";
import { EmptyState, ErrorState } from "@/components/states";
import {
  useAccounts,
  useAccount,
  useAccountFilterOptions,
  useAccountSyncStatus,
  useSyncAccounts,
  useRefreshAccount,
  type Account,
  type CRMProvider,
  type SyncStatus,
  type AccountSyncStatusInfo,
} from "@/hooks";
import {
  Building2,
  Search,
  Download,
  Plus,
  Briefcase,
  FileText,
  Activity,
  Globe,
  Users,
  DollarSign,
  AlertCircle,
  X,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  RefreshCw,
  Loader2,
  CloudDownload,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDate, formatCurrency } from "@/lib/formatters";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { PageHeader, Btn, StatusBadge } from "@/components/ui/fabric";
import { PageShell, RightRailPanel } from "@/components";

const PROVIDER_COLORS: Record<CRMProvider, { bg: string; text: string; border: string }> = {
  salesforce: { bg: "bg-primary/10", text: "text-primary", border: "border-primary/20" },
  hubspot: { bg: "bg-warning/10", text: "text-warning", border: "border-warning/20" },
  manual: { bg: "bg-muted", text: "text-foreground", border: "border-border" },
};

const DEFAULT_PROVIDER_STYLE = PROVIDER_COLORS.manual;

function getProviderStyle(provider: string) {
  return PROVIDER_COLORS[provider as CRMProvider] ?? DEFAULT_PROVIDER_STYLE;
}

function getProviderLabel(provider: string) {
  if (provider === "salesforce") return "Salesforce";
  if (provider === "hubspot") return "HubSpot";
  if (provider === "manual") return "Manual";
  return "External CRM";
}

const SYNC_STATUS_COLORS: Record<SyncStatus, "completed" | "processing" | "failed"> = {
  synced: "completed",
  pending: "processing",
  failed: "failed",
  stale: "processing",
};

function getSyncStatusBadge(status: string): "completed" | "processing" | "failed" {
  return SYNC_STATUS_COLORS[status as SyncStatus] ?? "processing";
}


interface FilterChipProps {
  label: string;
  options: { value: string; label: string }[];
  value: string | undefined;
  onChange: (value: string | undefined) => void;
}

function FilterChip({ label, options, value, onChange }: FilterChipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const selectedOption = options.find((o) => o.value === value);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full vf-text-body-s font-medium border transition-colors",
          value
            ? "bg-primary/10 text-primary border-primary/20"
            : "bg-card text-muted-foreground border-border hover:bg-muted"
        )}
      >
        {label}
        {selectedOption && (
          <>
            <span className="text-muted-foreground">:</span>
            <span>{selectedOption.label}</span>
          </>
        )}
        <ChevronDown size={12} className="ml-0.5" />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full left-0 mt-1 min-w-[160px] bg-card border border-border rounded-lg shadow-lg z-50 py-1">
            {options.map((option) => (
              <button
                key={option.value}
                onClick={() => {
                  onChange(option.value === "all" ? undefined : option.value);
                  setIsOpen(false);
                }}
                className={cn(
                  "w-full px-3 py-2 text-left vf-text-body-s hover:bg-muted transition-colors",
                  value === option.value || (!value && option.value === "all") ? "text-primary font-medium" : "text-foreground"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

interface FilterChipBarProps {
  filters: AccountFilters;
  filterOptions: FilterOptions | undefined;
  onChange: (filters: Partial<AccountFilters>) => void;
}

function FilterChipBar({ filters, filterOptions, onChange }: FilterChipBarProps) {
  const hasActiveFilters = filters.region || filters.segment || filters.sync_status !== "all" || filters.industry;

  const statusOptions = [
    { value: "all", label: "All Statuses" },
    { value: "synced", label: "Synced" },
    { value: "pending", label: "Pending" },
    { value: "failed", label: "Failed" },
    { value: "stale", label: "Stale" },
  ];

  const regionOptions = [
    { value: "all", label: "All Regions" },
    { value: "na", label: "North America" },
    { value: "emea", label: "EMEA" },
    { value: "apac", label: "APAC" },
    { value: "latam", label: "LATAM" },
  ];

  const segmentOptions = [
    { value: "all", label: "All Segments" },
    { value: "enterprise", label: "Enterprise" },
    { value: "midmarket", label: "Mid-Market" },
    { value: "smb", label: "SMB" },
  ];

  const industryOptions = [
    { value: "all", label: "All Industries" },
    ...(filterOptions?.industries?.map((ind) => ({ value: ind, label: ind })) || []),
  ];

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <FilterChip
        label="Region"
        options={regionOptions}
        value={filters.region}
        onChange={(v) => onChange({ region: v })}
      />
      <FilterChip
        label="Segment"
        options={segmentOptions}
        value={filters.segment}
        onChange={(v) => onChange({ segment: v })}
      />
      <FilterChip
        label="Status"
        options={statusOptions}
        value={filters.sync_status === "all" ? undefined : filters.sync_status}
        onChange={(v) => onChange({ sync_status: (v as SyncStatus) || "all" })}
      />
      <FilterChip
        label="Industry"
        options={industryOptions}
        value={filters.industry}
        onChange={(v) => onChange({ industry: v })}
      />

      {hasActiveFilters && (
        <button
          onClick={() =>
            onChange({
              region: undefined,
              segment: undefined,
              sync_status: "all",
              industry: undefined,
            })
          }
          className="vf-text-body-s text-muted-foreground hover:text-foreground flex items-center gap-1 ml-2"
        >
          <X size={12} aria-hidden="true" />
          Clear
        </button>
      )}
    </div>
  );
}

interface AccountDetailPanelProps {
  accountId: string | null;
  onClose: () => void;
  onLaunchIntelligence?: (accountId: string) => void;
}

function AccountDetailPanel({ accountId, onClose, onLaunchIntelligence }: AccountDetailPanelProps) {
  const { data: account, isLoading } = useAccount(accountId);
  const refreshAccount = useRefreshAccount();

  if (!accountId) {
    return (
      <RightRailPanel
        title="Account Details"
        onClose={onClose}
      >
        <div className="h-full flex flex-col items-center justify-center text-muted-foreground p-8">
          <Building2 size={48} className="mb-4 opacity-20" />
          <p className="vf-text-body-l">Select an account to view details</p>
        </div>
      </RightRailPanel>
    );
  }

  if (isLoading) {
    return (
      <RightRailPanel
        title="Account Details"
        onClose={onClose}
        isLoading
      >
        <>{/* Loading skeleton rendered by RightRailPanel */}</>
      </RightRailPanel>
    );
  }

  if (!account) {
    return (
      <RightRailPanel
        title="Account Details"
        onClose={onClose}
      >
        <div className="text-center">
          <AlertCircle size={32} className="mx-auto mb-2 text-destructive" />
          <p className="vf-text-body-s text-muted-foreground">Failed to load account details</p>
        </div>
      </RightRailPanel>
    );
  }

  const providerStyle = getProviderStyle(account.provider);
  const totalOpportunityValue =
    account.opportunities?.reduce((sum, opp) => sum + (opp.value || 0), 0) || 0;

  const status = (
    <div className="flex items-center gap-2">
      <StatusBadge status={getSyncStatusBadge(account.sync_status)} />
      <span className="vf-text-body-s text-muted-foreground">Synced {formatDate(account.last_synced_at)}</span>
    </div>
  );

  const footer = (
    <div className="flex items-center gap-2">
      <Btn variant="primary" className="flex-1" onClick={() => {
        if (accountId && onLaunchIntelligence) onLaunchIntelligence(accountId);
      }}>
        <FileText size={14} className="mr-1" />
        Launch Intelligence
      </Btn>
      <Btn
        variant="outline"
        onClick={() => refreshAccount.mutate(account.id)}
        disabled={refreshAccount.isPending}
      >
        {refreshAccount.isPending ? (
          <Loader2 size={14} className="mr-1 animate-spin" />
        ) : (
          <RefreshCw size={14} className="mr-1" />
        )}
        Refresh
      </Btn>
      <Btn variant="ghost">
        <Activity size={14} className="mr-1" />
        Traces
      </Btn>
    </div>
  );

  return (
    <RightRailPanel
      title={account.name}
      status={status}
      onClose={onClose}
      footer={footer}
      isLoading={isLoading}
    >
      {/* Provider Badge */}
      <div className="mb-4">
        <span
          className={cn(
            "inline-flex items-center px-2 py-0.5 rounded-full vf-text-micro font-medium border",
            providerStyle.bg,
            providerStyle.text,
            providerStyle.border
          )}
        >
          {getProviderLabel(account.provider)}
        </span>
        <p className="vf-text-body-s text-muted-foreground mt-1">{account.domain}</p>
      </div>

      {/* Metadata */}
      <div className="space-y-3 mb-4">
        {account.industry && (
          <div className="flex items-center justify-between vf-text-body-s">
            <span className="text-muted-foreground">Industry</span>
            <span className="font-medium">{account.industry}</span>
          </div>
        )}
        {account.region && (
          <div className="flex items-center justify-between vf-text-body-s">
            <span className="text-muted-foreground">Region</span>
            <span className="font-medium uppercase">{account.region}</span>
          </div>
        )}
        {account.segment && (
          <div className="flex items-center justify-between vf-text-body-s">
            <span className="text-muted-foreground">Segment</span>
            <span className="font-medium">{account.segment}</span>
          </div>
        )}
        {account.stage && (
          <div className="flex items-center justify-between vf-text-body-s">
            <span className="text-muted-foreground">Stage</span>
            <span className="font-medium">{account.stage}</span>
          </div>
        )}
        {account.headquarters && (
          <div className="flex items-center justify-between vf-text-body-s">
            <span className="text-muted-foreground flex items-center gap-1">
              <Globe size={12} />
              Location
            </span>
            <span className="font-medium">{account.headquarters}</span>
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-muted/50 rounded-lg p-3">
          <div className="flex items-center gap-1 text-muted-foreground mb-1">
            <DollarSign size={12} />
            <span className="vf-text-micro uppercase tracking-wide">Pipeline</span>
          </div>
          <p className="text-[16px] font-bold">{formatCurrency(totalOpportunityValue)}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-3">
          <div className="flex items-center gap-1 text-muted-foreground mb-1">
            <Briefcase size={12} />
            <span className="vf-text-micro uppercase tracking-wide">Opportunities</span>
          </div>
          <p className="text-[16px] font-bold">{account.opportunities?.length || 0}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-3">
          <div className="flex items-center gap-1 text-muted-foreground mb-1">
            <Users size={12} />
            <span className="vf-text-micro uppercase tracking-wide">Employees</span>
          </div>
          <p className="text-[16px] font-bold">{account.employees?.toLocaleString() || "—"}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-3">
          <div className="flex items-center gap-1 text-muted-foreground mb-1">
            <DollarSign size={12} />
            <span className="vf-text-micro uppercase tracking-wide">Revenue</span>
          </div>
          <p className="text-[16px] font-bold">{formatCurrency(account.annual_revenue)}</p>
        </div>
      </div>

      {/* Owner */}
      {account.owner_name && (
        <div className="mb-4">
          <p className="vf-text-caption text-muted-foreground uppercase tracking-wide mb-2">Account Owner</p>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="vf-text-body-s font-semibold text-primary">
                {account.owner_name.charAt(0).toUpperCase()}
              </span>
            </div>
            <span className="vf-text-body-m font-medium">{account.owner_name}</span>
          </div>
        </div>
      )}

      <div className="rounded-lg border border-border bg-card p-4 mb-4">
        <div className="flex items-center gap-2 vf-text-body-s font-semibold text-foreground">
          <Activity size={14} />
          Value Realization
        </div>
        <p className="mt-2 vf-text-body-s leading-relaxed text-muted-foreground">
          {account.name} is ready for baseline metrics, outcome tracking, actual value capture, and renewal narrative planning once an approved business case is converted.
        </p>
        <div className="mt-3 grid grid-cols-2 gap-2 vf-text-caption">
          <span className="rounded-md bg-muted/40 px-2 py-1 text-muted-foreground">Baseline metrics</span>
          <span className="rounded-md bg-muted/40 px-2 py-1 text-muted-foreground">Outcomes</span>
          <span className="rounded-md bg-muted/40 px-2 py-1 text-muted-foreground">Actual value</span>
          <span className="rounded-md bg-muted/40 px-2 py-1 text-muted-foreground">Renewal narrative</span>
        </div>
      </div>

      {/* Opportunities List */}
      {account.opportunities && account.opportunities.length > 0 && (
        <div>
          <p className="vf-text-caption text-muted-foreground uppercase tracking-wide mb-2">Opportunities</p>
          <div className="space-y-2">
            {account.opportunities.slice(0, 3).map((opp) => (
              <div key={opp.provider_opportunity_id} className="bg-muted/30 rounded-lg p-3">
                <p className="vf-text-body-s font-medium truncate">{opp.name}</p>
                <div className="flex items-center justify-between mt-1">
                  <span className="vf-text-caption text-muted-foreground">{opp.stage}</span>
                  <span className="vf-text-body-s font-semibold">{formatCurrency(opp.value)}</span>
                </div>
              </div>
            ))}
            {account.opportunities.length > 3 && (
              <p className="vf-text-caption text-muted-foreground text-center">
                +{account.opportunities.length - 3} more
              </p>
            )}
          </div>
        </div>
      )}
    </RightRailPanel>
  );
}

interface AccountFilters {
  region?: string;
  segment?: string;
  sync_status: SyncStatus | "all";
  industry?: string;
  search: string;
  page: number;
  page_size: number;
}

interface FilterOptions {
  industries: string[];
}

function Accounts() {
  const { navigateTo } = useNavigation();
  const { prefetchAccountDetail } = useRoutePrefetch();
  const params = useParams<{ id: string }>();
  const urlAccountId = params.id ?? null;
  const setGlobalAccountId = useAccountContextStore((s) => s.setSelectedAccountId);

  const [filters, setFilters] = useState<AccountFilters>({
    sync_status: "all",
    search: "",
    page: 1,
    page_size: 20,
  });
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(urlAccountId);
  const [intakeOpen, setIntakeOpen] = useState(false);

  // Sync URL account ID to global store so sidebar/workspace links resolve correctly
  useEffect(() => {
    if (urlAccountId) {
      setSelectedAccountId(urlAccountId);
      setGlobalAccountId(urlAccountId);
    }
  }, [urlAccountId, setGlobalAccountId]);

  const { data, isLoading, error, refetch } = useAccounts(filters);
  const { data: filterOptions } = useAccountFilterOptions();
  const { data: syncStatusList } = useAccountSyncStatus();
  const syncAccounts = useSyncAccounts();

  const accounts = data?.items || [];
  const total = data?.total || 0;

  const handleSelectAccount = (id: string | null) => {
    setSelectedAccountId(id);
    if (id) setGlobalAccountId(id);
  };

  const handleExport = () => {
    const csvContent = [
      ["Name", "Domain", "Industry", "Region", "Segment", "Provider", "Status"],
      ...accounts.map((a) => [
        a.name,
        a.domain,
        a.industry || "",
        a.region || "",
        a.segment || "",
        a.provider,
        a.sync_status,
      ]),
    ]
      .map((row) => row.map((cell) => `"${cell}"`).join(","))
      .join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `accounts-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleAddAccount = () => {
    setIntakeOpen(true);
  };

  const handleIntakeSubmit = (accountId: string) => {
    setIntakeOpen(false);
    navigateTo('intelligence-signals', { accountId });
  };

  const updateFilters = (updates: Partial<AccountFilters>) => {
    setFilters((prev) => ({ ...prev, ...updates, page: 1 }));
  };

  return (
    <div className="min-h-screen bg-background">
      <PageShell>
        {/* Header */}
        <PageHeader
          title="Accounts"
          subtitle="Browse and manage customer accounts"
          actions={
            <>
              <Btn variant="ghost" onClick={handleExport}>
                <Download size={14} className="mr-1.5" />
                Export
              </Btn>
              <Btn
                variant="outline"
                onClick={() => syncAccounts.mutate({})}
                disabled={syncAccounts.isPending}
              >
                {syncAccounts.isPending ? (
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                ) : (
                  <CloudDownload size={14} className="mr-1.5" />
                )}
                Sync CRM
              </Btn>
              <Btn variant="primary" onClick={handleAddAccount}>
                <Plus size={14} className="mr-1.5" />
                New Value Case
              </Btn>
            </>
          }
        />

        {/* Filter Chips */}
        <div className="mt-4 mb-4">
          <FilterChipBar filters={filters} filterOptions={filterOptions} onChange={updateFilters} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Account List */}
          <div className={cn("transition-all", selectedAccountId ? "md:col-span-9" : "md:col-span-12")}>
            {/* Search */}
            <div className="mb-4">
              <div className="relative">
                <label htmlFor="accounts-search" className="sr-only">Search accounts</label>
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                <input
                  id="accounts-search"
                  type="text"
                  placeholder="Search accounts by name, domain, or owner..."
                  value={filters.search}
                  onChange={(e) => updateFilters({ search: e.target.value })}
                  className="w-full pl-10 pr-4 py-2.5 bg-card border border-border rounded-lg vf-text-body-m focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>
            </div>

            {/* Table */}
            <div className="bg-card border border-border rounded-lg overflow-hidden">
              {isLoading ? (
                <div className="p-8 space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : error ? (
                <ErrorState
                  title="Failed to load accounts"
                  description={error.message}
                  error={error}
                  onRetry={refetch}
                />
              ) : accounts.length === 0 ? (
                <EmptyState
                  title="No accounts found"
                  description={
                    filters.search || hasActiveFilter(filters)
                      ? "Try adjusting your filters"
                      : "Add accounts or sync from your CRM to get started"
                  }
                  icon={Building2}
                  action={
                    !filters.search && !hasActiveFilter(filters) ? (
                      <button
                        onClick={handleAddAccount}
                        className="text-sm font-medium text-primary hover:underline"
                      >
                        Add account
                      </button>
                    ) : undefined
                  }
                />
              ) : (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[250px]">Account</TableHead>
                        <TableHead>Industry</TableHead>
                        <TableHead>Region</TableHead>
                        <TableHead>Segment</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Pipeline</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {accounts.map((account) => {
                        const providerStyle = getProviderStyle(account.provider);

                        return (
                          <TableRow
                            key={account.id}
                            className={cn(
                              "cursor-pointer",
                              selectedAccountId === account.id && "bg-primary/5"
                            )}
                            onClick={() => handleSelectAccount(account.id)}
                            onMouseEnter={() => prefetchAccountDetail(account.id)}
                            onFocus={() => prefetchAccountDetail(account.id)}
                          >
                            <TableCell>
                              <div className="flex items-center gap-3">
                                <div
                                  className={cn(
                                    "w-8 h-8 rounded-lg flex items-center justify-center",
                                    providerStyle.bg,
                                    providerStyle.text
                                  )}
                                >
                                  <Building2 size={14} />
                                </div>
                                <div>
                                  <p className="font-medium vf-text-body-m">{account.name}</p>
                                  <p className="vf-text-caption text-muted-foreground">{account.domain}</p>
                                </div>
                              </div>
                            </TableCell>
                            <TableCell className="vf-text-body-s">{account.industry || "—"}</TableCell>
                            <TableCell className="vf-text-body-s uppercase">{account.region || "—"}</TableCell>
                            <TableCell className="vf-text-body-s">{account.segment || "—"}</TableCell>
                            <TableCell>
                              <StatusBadge status={getSyncStatusBadge(account.sync_status)} />
                            </TableCell>
                            <TableCell className="text-right vf-text-body-m font-medium">
                              {formatCurrency(
                                account.opportunities?.reduce((sum, o) => sum + (o.value || 0), 0) || 0
                              )}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>

                  {/* Pagination */}
                  {total > filters.page_size && (
                    <PaginationBar
                      page={filters.page}
                      pageSize={filters.page_size}
                      totalItems={total}
                      canPrevious={filters.page > 1}
                      canNext={filters.page * filters.page_size < total}
                      onPrevious={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
                      onNext={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
                      onPageChange={(newPage) => setFilters((f) => ({ ...f, page: newPage }))}
                      itemLabel="accounts"
                      summaryVariant="range"
                    />
                  )}
                </>
              )}
            </div>
          </div>

          {/* Account Detail Panel */}
          {selectedAccountId && (
            <div className="col-span-1 md:col-span-3">
              <AccountDetailPanel
                accountId={selectedAccountId}
                onClose={() => handleSelectAccount(null)}
                onLaunchIntelligence={(id) => navigateTo('intelligence-signals', { accountId: id })}
              />
            </div>
          )}
        </div>
      </PageShell>
      {/* Account Intake Modal */}
      <AccountIntakeModal
        open={intakeOpen}
        onClose={() => setIntakeOpen(false)}
        onSubmit={handleIntakeSubmit}
      />
    </div>
  );
}

function hasActiveFilter(filters: AccountFilters): boolean {
  return !!(filters.region || filters.segment || filters.sync_status !== "all" || filters.industry);
}

export default function AccountsPage() {
  return (
    <ErrorBoundary>
      <Accounts />
    </ErrorBoundary>
  );
}
