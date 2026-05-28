/**
 * SuperAdminConsole — Cross-tenant read-only admin dashboard.
 *
 * Displays tenant list with user counts and active workflow counts.
 * Requires super_admin role and emits CROSS_TENANT_ACCESS audit events
 * via the backend on every load.
 */

import { useState } from "react";
import { Shield, Users, Activity, Loader2, AlertCircle } from "lucide-react";
import { PageHeader } from "@/components/ui/fabric";
import { useSuperAdminOverview, type TenantOverviewItem } from "@/hooks/useSuperAdminOverview";
import ErrorBoundary from "@/components/ErrorBoundary";
import { cn } from "@/lib/utils";

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString();
}

// ── Sub-components ──────────────────────────────────────────────────────────

function TenantTable({ items }: { items: TenantOverviewItem[] }) {
  return (
    <div className="overflow-auto border border-border rounded-xl">
      <table className="w-full text-left text-sm">
        <thead className="bg-muted text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">Tenant</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Tier</th>
            <th className="px-4 py-3 font-medium">Users</th>
            <th className="px-4 py-3 font-medium">Active Workflows</th>
            <th className="px-4 py-3 font-medium">Created At</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-muted">
              <td className="px-4 py-3">
                <div className="font-medium text-foreground">{item.name}</div>
                <div className="text-xs text-muted-foreground">{item.slug}</div>
              </td>
              <td className="px-4 py-3">
                <span
                  className={cn(
                    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                    item.status === "active"
                      ? "bg-emerald-500/10 text-emerald-600"
                      : item.status === "pending"
                        ? "bg-amber-500/10 text-amber-600"
                        : "bg-muted text-muted-foreground",
                  )}
                >
                  {item.status}
                </span>
              </td>
              <td className="px-4 py-3 text-foreground">{item.tier_id}</td>
              <td className="px-4 py-3 text-foreground">
                <div className="flex items-center gap-1">
                  <Users size={14} className="text-muted-foreground" />
                  {item.user_count}
                </div>
              </td>
              <td className="px-4 py-3 text-foreground">
                <div className="flex items-center gap-1">
                  <Activity size={14} className="text-muted-foreground" />
                  {item.active_workflow_count}
                </div>
              </td>
              <td className="px-4 py-3 text-muted-foreground text-xs">
                {formatDate(item.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

export default function SuperAdminConsole() {
  const [limit] = useState(100);
  const [offset] = useState(0);
  const { data, isLoading, error } = useSuperAdminOverview(limit, offset);

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        <PageHeader
          title="Super Admin Console"
          subtitle="Cross-tenant overview — read-only"
        />

        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 size={16} className="animate-spin" />
            Loading tenant overview...
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-4">
            <AlertCircle size={16} />
            Failed to load tenant overview. Ensure you have privileged access.
          </div>
        )}

        {data && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {data.items.length} of {data.total} tenants
              </p>
            </div>
            <TenantTable items={data.items} />
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}
