/**
 * SuperAdminConsole — Cross-tenant read-only admin dashboard.
 *
 * Displays tenant list with user counts and active workflow counts.
 * Requires super_admin role and emits CROSS_TENANT_ACCESS audit events
 * via the backend on every load.
 */

import { useState } from "react";
import { Shield, Users, Activity, Loader2 } from "lucide-react";
import { useSuperAdminOverview, type TenantOverviewItem } from "@/hooks/useSuperAdminOverview";
import ErrorBoundary from "@/components/ErrorBoundary";
import { AdminShell, AdminDataTable, AdminStatCard, AdminStatsRow } from "@/components/admin";
import type { AdminDataTableColumn } from "@/components/admin";
import { StatusBadge } from "@/components/ui/fabric";
import { formatDate } from "@/lib/formatters";

// ── Sub-components ──────────────────────────────────────────────────────────

const tenantColumns: AdminDataTableColumn<TenantOverviewItem>[] = [
  {
    key: "name",
    header: "Tenant",
    render: (item) => (
      <div>
        <div className="font-medium text-foreground">{item.name}</div>
        <div className="vf-text-caption text-muted-foreground">{item.slug}</div>
      </div>
    ),
  },
  {
    key: "status",
    header: "Status",
    render: (item) => (
      <StatusBadge
        status={item.status === "active" ? "active" : item.status === "pending" ? "warning" : "default"}
      >
        {item.status}
      </StatusBadge>
    ),
  },
  {
    key: "tier_id",
    header: "Tier",
    render: (item) => <span className="text-foreground">{item.tier_id}</span>,
  },
  {
    key: "user_count",
    header: "Users",
    render: (item) => (
      <div className="flex items-center gap-1 text-foreground">
        <Users size={14} className="text-muted-foreground" />
        {item.user_count}
      </div>
    ),
  },
  {
    key: "active_workflow_count",
    header: "Active Workflows",
    render: (item) => (
      <div className="flex items-center gap-1 text-foreground">
        <Activity size={14} className="text-muted-foreground" />
        {item.active_workflow_count}
      </div>
    ),
  },
  {
    key: "created_at",
    header: "Created At",
    render: (item) => (
      <span className="text-muted-foreground vf-text-caption">
        {formatDate(item.created_at)}
      </span>
    ),
  },
];

// ── Main Component ──────────────────────────────────────────────────────────

export default function SuperAdminConsole() {
  const [limit] = useState(100);
  const [offset] = useState(0);
  const { data, isLoading, error } = useSuperAdminOverview(limit, offset);

  return (
    <ErrorBoundary>
      <AdminShell
        title="Super Admin Console"
        subtitle="Cross-tenant overview — read-only"
        fullWidth
      >
        {data && (
          <AdminStatsRow columns={4}>
            <AdminStatCard
              label="Total Tenants"
              value={data.total}
              icon={<Shield size={14} />}
            />
            <AdminStatCard
              label="Active Tenants"
              value={data.items.filter((i) => i.status === "active").length}
              icon={<Users size={14} />}
              color="success"
            />
            <AdminStatCard
              label="Pending Tenants"
              value={data.items.filter((i) => i.status === "pending").length}
              icon={<Loader2 size={14} />}
              color="warning"
            />
            <AdminStatCard
              label="Total Users"
              value={data.items.reduce((sum, i) => sum + i.user_count, 0)}
              icon={<Users size={14} />}
              color="primary"
            />
          </AdminStatsRow>
        )}

        <div className="space-y-3">
          {data && (
            <p className="vf-text-caption text-muted-foreground">
              Showing {data.items.length} of {data.total} tenants
            </p>
          )}
          <AdminDataTable
            data={data?.items}
            columns={tenantColumns}
            keyExtractor={(item) => item.id}
            isLoading={isLoading}
            error={error}
            emptyTitle="No tenants found"
            emptyDescription="There are no tenants available in the system."
          />
        </div>
      </AdminShell>
    </ErrorBoundary>
  );
}
