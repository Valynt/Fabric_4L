/**
 * BillingAdmin — Enterprise Billing & Subscription Management
 *
 * Consolidated admin view for:
 * - Subscription overview (plan, status, renewal, entitlements)
 * - Invoice history with detail drawer
 * - Usage metrics with progress bars
 *
 * Uses shared admin primitives for enterprise-grade consistency.
 */

import { useState } from "react";
import {
  CreditCard, Receipt, Activity, Calendar, Shield, AlertCircle,
  CheckCircle2, Clock, ExternalLink, Download, FileText,
  TrendingUp, AlertTriangle, Zap,
} from "lucide-react";
import { useAuthContext } from "@/contexts/AuthContext";
import ErrorBoundary from "@/components/ErrorBoundary";
import { Btn } from "@/components/ui/fabric";
import {
  useBilling,
  useEntitlements,
  type Subscription,
} from "@/hooks/useBilling";
import { useInvoices, type Invoice } from "@/hooks/useInvoices";
import { useUsage } from "@/hooks/useUsage";
import {
  AdminShell,
  AdminTabs,
  AdminTabPanel,
  AdminStatCard,
  AdminStatsRow,
  AdminDataTable,
  AdminFilterBar,
  AdminEmptyState,
  AdminIconButton,
  AdminIconButtonGroup,
  type AdminDataTableColumn,
} from "@/components/admin";
import { InvoiceStatusBadge } from "@/components/billing/InvoiceStatusBadge";
import { InvoiceDetailDrawer } from "@/components/billing/InvoiceDetailDrawer";
import { safeAsync } from "@/lib/async";
import { cn } from "@/lib/utils";

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString();
}

function getStatusConfig(status: string) {
  switch (status) {
    case "active":
    case "trialing":
      return { color: "success" as const, icon: <CheckCircle2 size={14} />, label: "Active" };
    case "past_due":
      return { color: "warning" as const, icon: <AlertTriangle size={14} />, label: "Past Due" };
    case "canceled":
    case "unpaid":
      return { color: "destructive" as const, icon: <AlertCircle size={14} />, label: "Canceled" };
    default:
      return { color: "default" as const, icon: <Clock size={14} />, label: status };
  }
}

// ── Sub-components ──────────────────────────────────────────────────────────

function SubscriptionOverview({
  subscription,
  isLoading,
  error,
  onOpenPortal,
  isOpeningPortal,
}: {
  subscription?: Subscription;
  isLoading: boolean;
  error: Error | null;
  onOpenPortal: () => void;
  isOpeningPortal: boolean;
}) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-muted rounded w-1/3" />
          <div className="h-3 bg-muted rounded w-1/2" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-destructive vf-text-body-s">
        Failed to load subscription: {error.message}
      </div>
    );
  }

  if (!subscription) {
    return (
      <AdminEmptyState
        icon={CreditCard}
        title="No subscription found"
        description="This tenant does not have an active subscription."
        action={
          <Btn variant="primary" onClick={onOpenPortal} disabled={isOpeningPortal}>
            {isOpeningPortal ? "Opening…" : "Set up billing"}
          </Btn>
        }
      />
    );
  }

  const statusCfg = getStatusConfig(subscription.status);

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h3 className="vf-text-body-l font-semibold text-foreground capitalize">
            {subscription.plan_id} Plan
          </h3>
          <p className="vf-text-caption text-muted-foreground mt-1">
            Manage your subscription, payment methods, and billing details.
          </p>
        </div>
        <Btn
          variant="outline"
          onClick={onOpenPortal}
          disabled={isOpeningPortal}
        >
          <ExternalLink size={13} className="mr-1" />
          {isOpeningPortal ? "Opening…" : "Manage in Stripe"}
        </Btn>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-muted rounded-lg p-3">
          <p className="vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">Status</p>
          <div className={cn("flex items-center gap-1.5 mt-1 vf-text-body-s font-medium", `text-${statusCfg.color}`)}>
            {statusCfg.icon} {statusCfg.label}
          </div>
        </div>
        <div className="bg-muted rounded-lg p-3">
          <p className="vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">Current Period</p>
          <div className="flex items-center gap-1.5 mt-1 vf-text-body-s text-foreground">
            <Calendar size={13} className="text-muted-foreground" />
            {subscription.current_period_start ? formatDate(subscription.current_period_start) : "—"}
            {" → "}
            {subscription.current_period_end ? formatDate(subscription.current_period_end) : "—"}
          </div>
        </div>
        <div className="bg-muted rounded-lg p-3">
          <p className="vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">Renewal</p>
          <div className="flex items-center gap-1.5 mt-1 vf-text-body-s text-foreground">
            <Clock size={13} className="text-muted-foreground" />
            {subscription.current_period_end
              ? formatDate(subscription.current_period_end)
              : "—"}
          </div>
        </div>
        <div className="bg-muted rounded-lg p-3">
          <p className="vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">Auto-cancel</p>
          <div className="flex items-center gap-1.5 mt-1 vf-text-body-s text-foreground">
            {subscription.cancel_at_period_end ? (
              <><AlertTriangle size={13} className="text-warning" /> Yes at period end</>
            ) : (
              <><CheckCircle2 size={13} className="text-success" /> No</>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function EntitlementsGrid({
  entitlements,
}: {
  entitlements?: { features: Record<string, { enabled: boolean; name: string; description: string }> };
}) {
  if (!entitlements?.features) return null;

  const features = Object.entries(entitlements.features);

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h3 className="vf-text-body-l font-semibold text-foreground mb-4">Feature Entitlements</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {features.map(([key, feature]) => (
          <div
            key={key}
            className={cn(
              "rounded-lg border p-3 transition-colors",
              feature.enabled
                ? "border-success/20 bg-success/5"
                : "border-border bg-muted/50 opacity-60"
            )}
          >
            <div className="flex items-center gap-2">
              {feature.enabled ? (
                <CheckCircle2 size={14} className="text-success" />
              ) : (
                <Shield size={14} className="text-muted-foreground" />
              )}
              <span className="vf-text-body-s font-medium text-foreground">{feature.name}</span>
            </div>
            <p className="vf-text-caption text-muted-foreground mt-1">{feature.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function UsageMetricsPanel({
  metrics,
  isLoading,
  error,
}: {
  metrics: ReturnType<typeof useUsage>["metrics"];
  isLoading: boolean;
  error: Error | null;
}) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-card p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-muted rounded w-1/3" />
          <div className="h-20 bg-muted rounded" />
          <div className="h-20 bg-muted rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-6 text-destructive vf-text-body-s">
        Failed to load usage: {error.message}
      </div>
    );
  }

  if (!metrics.length) {
    return (
      <AdminEmptyState
        icon={Activity}
        title="No usage metrics"
        description="Usage data is not available for this tenant."
      />
    );
  }

  return (
    <div className="space-y-3">
      {metrics.map((metric) => {
        const isWarning = metric.percentage >= (metric.warning_threshold || 80);
        const isDanger = metric.percentage >= 100;
        const barColor = isDanger ? "bg-destructive" : isWarning ? "bg-warning" : "bg-primary";

        return (
          <div key={metric.metric} className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <TrendingUp size={14} className="text-muted-foreground" />
                <span className="vf-text-body-s font-medium text-foreground capitalize">
                  {metric.metric.replace(/_/g, " ")}
                </span>
              </div>
              <span className={cn("vf-text-caption font-semibold", isDanger ? "text-destructive" : isWarning ? "text-warning" : "text-muted-foreground")}>
                {metric.percentage.toFixed(0)}%
              </span>
            </div>
            <div className="flex items-baseline gap-1 mb-2">
              <span className="text-2xl font-extrabold text-foreground">{metric.total_quantity.toLocaleString()}</span>
              <span className="vf-text-caption text-muted-foreground">/ {metric.limit.toLocaleString()} {metric.unit}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
              <div
                className={cn("h-full rounded-full transition-all", barColor)}
                style={{ width: `${Math.min(metric.percentage, 100)}%` }}
              />
            </div>
            {metric.overage_rate > 0 && (
              <p className="vf-text-caption text-muted-foreground mt-1">
                Overage rate: ${metric.overage_rate.toFixed(4)} per unit
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

type TabType = "overview" | "invoices" | "usage";

function BillingAdminContent() {
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [search, setSearch] = useState("");
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const { user } = useAuthContext();
  const customerId = user?.tenantId ?? "";

  const {
    subscription,
    isLoading: subLoading,
    error: subError,
    openCustomerPortal,
    isOpeningPortal,
  } = useBilling(customerId);

  const { data: entitlements } = useEntitlements(customerId);

  const {
    invoices,
    isLoading: invoicesLoading,
    error: invoicesError,
    refetch: refetchInvoices,
  } = useInvoices(customerId);

  const {
    metrics,
    isLoading: usageLoading,
    error: usageError,
    refetch: refetchUsage,
  } = useUsage(customerId);

  const handleOpenPortal = () => {
    safeAsync(openCustomerPortal(window.location.href), "billing.openPortal");
  };

  const handleViewInvoice = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
    setDrawerOpen(true);
  };

  const filteredInvoices = search
    ? invoices.filter(
        (i) =>
          i.invoice_number.toLowerCase().includes(search.toLowerCase()) ||
          i.status.toLowerCase().includes(search.toLowerCase())
      )
    : invoices;

  const invoiceColumns: AdminDataTableColumn<Invoice>[] = [
    {
      key: "invoice_number",
      header: "Invoice",
      render: (i) => (
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-primary shrink-0" />
          <span className="font-medium text-foreground">{i.invoice_number}</span>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (i) => <InvoiceStatusBadge status={i.status} />,
    },
    {
      key: "total",
      header: "Total",
      render: (i) => <span className="font-medium text-foreground">{formatCurrency(i.total_cents)}</span>,
    },
    {
      key: "period",
      header: "Period",
      render: (i) => (
        <span className="vf-text-caption text-muted-foreground">
          {formatDate(i.period_start)} — {formatDate(i.period_end)}
        </span>
      ),
    },
    {
      key: "issued",
      header: "Issued",
      render: (i) => <span className="vf-text-caption text-muted-foreground">{formatDate(i.created_at)}</span>,
    },
    {
      key: "actions",
      header: "",
      className: "w-24",
      render: (i) => (
        <AdminIconButtonGroup>
          <AdminIconButton
            icon={Download}
            label="Download PDF"
            onClick={() => {
              if (i.invoice_pdf_url) window.open(i.invoice_pdf_url, "_blank");
            }}
            disabled={!i.invoice_pdf_url}
          />
          <AdminIconButton
            icon={Receipt}
            label="View invoice details"
            variant="primary"
            onClick={() => handleViewInvoice(i)}
          />
        </AdminIconButtonGroup>
      ),
    },
  ];

  const stats = [
    {
      label: "Plan",
      value: subscription?.plan_id ? (
        <span className="capitalize">{subscription.plan_id}</span>
      ) : (
        "—"
      ),
      icon: <Shield size={14} />,
      color: "primary" as const,
    },
    {
      label: "Status",
      value: subscription?.status ? (
        <span className="capitalize">{subscription.status}</span>
      ) : (
        "—"
      ),
      icon: getStatusConfig(subscription?.status || "").icon,
      color: getStatusConfig(subscription?.status || "").color,
    },
    {
      label: "Renewal",
      value: subscription?.current_period_end
        ? formatDate(subscription.current_period_end)
        : "—",
      icon: <Calendar size={14} />,
      color: "default" as const,
    },
    {
      label: "Invoices",
      value: invoices.length,
      icon: <Receipt size={14} />,
      color: "default" as const,
    },
  ];

  return (
    <AdminShell
      title="Billing & Subscription"
      subtitle="Manage plans, invoices, usage, and payment methods."
      fullWidth
      actions={
        <Btn variant="outline" onClick={handleOpenPortal} disabled={isOpeningPortal || !customerId}>
          <ExternalLink size={13} className="mr-1" />
          {isOpeningPortal ? "Opening…" : "Stripe Portal"}
        </Btn>
      }
      tabs={
        <AdminTabs
          tabs={[
            { id: "overview", label: "Overview", icon: <CreditCard size={13} /> },
            { id: "invoices", label: "Invoices", count: invoices.length, icon: <Receipt size={13} /> },
            { id: "usage", label: "Usage", icon: <Activity size={13} /> },
          ]}
          activeTab={activeTab}
          onChange={(tabId) => setActiveTab(tabId as TabType)}
        />
      }
    >
      <AdminStatsRow columns={4}>
        {stats.map((s) => (
          <AdminStatCard
            key={s.label}
            label={s.label}
            value={s.value}
            icon={s.icon}
            color={s.color}
          />
        ))}
      </AdminStatsRow>

      <AdminTabPanel tabId="overview" activeTab={activeTab}>
        <div className="space-y-4">
          <SubscriptionOverview
            subscription={subscription}
            isLoading={subLoading}
            error={subError}
            onOpenPortal={handleOpenPortal}
            isOpeningPortal={isOpeningPortal}
          />
          <EntitlementsGrid entitlements={entitlements} />
        </div>
      </AdminTabPanel>

      <AdminTabPanel tabId="invoices" activeTab={activeTab}>
        <AdminFilterBar
          searchPlaceholder="Search invoices..."
          searchValue={search}
          onSearchChange={setSearch}
          actions={
            <Btn variant="outline" size="sm" onClick={refetchInvoices}>
              <Zap size={12} className="mr-1" /> Refresh
            </Btn>
          }
        />
        <AdminDataTable
          data={filteredInvoices}
          columns={invoiceColumns}
          keyExtractor={(i) => i.id}
          isLoading={invoicesLoading}
          error={invoicesError}
          onRetry={refetchInvoices}
          emptyTitle="No invoices found"
          emptyDescription={search ? "No invoices match your search." : "No invoices are available for this tenant."}
          emptyIcon={Receipt}
        />
      </AdminTabPanel>

      <AdminTabPanel tabId="usage" activeTab={activeTab}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="vf-text-body-l font-semibold text-foreground">Usage Metrics</h3>
          <Btn variant="outline" size="sm" onClick={refetchUsage}>
            <Zap size={12} className="mr-1" /> Refresh
          </Btn>
        </div>
        <UsageMetricsPanel metrics={metrics} isLoading={usageLoading} error={usageError} />
      </AdminTabPanel>

      <InvoiceDetailDrawer
        invoice={selectedInvoice}
        onClose={() => setDrawerOpen(false)}
      />
    </AdminShell>
  );
}

export default function BillingAdmin() {
  return (
    <ErrorBoundary>
      <BillingAdminContent />
    </ErrorBoundary>
  );
}
