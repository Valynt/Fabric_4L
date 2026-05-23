import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, ExternalLink } from "lucide-react";
import { useOperationalAudit } from "@/hooks/useOperationalAudit";
import { useSettingsAccess } from "../access";
import { CapabilityGate } from "../components/CapabilityGate";

function safeSummary(details: Record<string, unknown>): string {
  const summary = typeof details.summary === "string" ? details.summary : JSON.stringify(details);
  return summary.replace(/[<>]/g, "").slice(0, 180);
}

function exportEntries(entries: Array<Record<string, unknown>>, format: "csv" | "json") {
  if (!entries.length) return;
  const payload = format === "json"
    ? JSON.stringify(entries, null, 2)
    : [
      Object.keys(entries[0] ?? {}).join(","),
      ...entries.map((row) => Object.values(row).map((v) => JSON.stringify(v ?? "")).join(",")),
    ].join("\n");
  const blob = new Blob([payload], { type: format === "json" ? "application/json" : "text/csv;charset=utf-8" });
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = `governance-audit-${Date.now()}.${format}`;
  a.click();
  URL.revokeObjectURL(href);
}

export function GovernanceAuditTrail() {
  const { role } = useSettingsAccess();
  const canExport = ["admin", "tenant_admin", "super_admin"].includes(role);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ actor: "", action: "", entityType: "", entityId: "", startDate: "", endDate: "" });

  const query = useMemo(() => ({
    page,
    perPage: 25,
    actor: filters.actor || undefined,
    action: filters.action || undefined,
    entityType: filters.entityType || undefined,
    entityId: filters.entityId || undefined,
    startDate: filters.startDate || undefined,
    endDate: filters.endDate || undefined,
  }), [filters, page]);

  const { data, isLoading, error } = useOperationalAudit(query);

  return (
    <CapabilityGate capability="governance">
      <div className="space-y-6">
        <section className="rounded-lg border bg-card p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold">Operational Audit Events</h3>
              <p className="text-xs text-muted-foreground">Tenant-scoped administrative actions from Layer 4.</p>
            </div>
            <Link to="/governance/traces" className="inline-flex h-8 items-center gap-1 rounded-md border px-3 text-xs font-medium hover:bg-accent">
              Decision trace
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-3">
            <input className="h-9 rounded-md border bg-background px-3 text-sm" placeholder="Actor" value={filters.actor} onChange={(e) => { setPage(1); setFilters((p) => ({ ...p, actor: e.target.value })); }} />
            <input className="h-9 rounded-md border bg-background px-3 text-sm" placeholder="Action" value={filters.action} onChange={(e) => { setPage(1); setFilters((p) => ({ ...p, action: e.target.value })); }} />
            <input className="h-9 rounded-md border bg-background px-3 text-sm" placeholder="Entity type" value={filters.entityType} onChange={(e) => { setPage(1); setFilters((p) => ({ ...p, entityType: e.target.value })); }} />
            <input className="h-9 rounded-md border bg-background px-3 text-sm" placeholder="Entity ID" value={filters.entityId} onChange={(e) => { setPage(1); setFilters((p) => ({ ...p, entityId: e.target.value })); }} />
            <input type="date" aria-label="Start date" className="h-9 rounded-md border bg-background px-3 text-sm" value={filters.startDate} onChange={(e) => { setPage(1); setFilters((p) => ({ ...p, startDate: e.target.value })); }} />
            <input type="date" aria-label="End date" className="h-9 rounded-md border bg-background px-3 text-sm" value={filters.endDate} onChange={(e) => { setPage(1); setFilters((p) => ({ ...p, endDate: e.target.value })); }} />
          </div>

          {canExport && (
            <div className="mt-3 flex gap-2">
              <button type="button" className="inline-flex h-8 items-center rounded-md border px-3 text-xs font-medium hover:bg-accent" onClick={() => exportEntries((data?.entries ?? []) as unknown as Array<Record<string, unknown>>, "csv")}>Export CSV</button>
              <button type="button" className="inline-flex h-8 items-center rounded-md border px-3 text-xs font-medium hover:bg-accent" onClick={() => exportEntries((data?.entries ?? []) as unknown as Array<Record<string, unknown>>, "json")}>Export JSON</button>
            </div>
          )}

          {isLoading ? <div className="mt-4 rounded-md border p-4 text-sm text-muted-foreground">Loading audit events...</div> : error ? (
            <div className="mt-4 rounded-md border border-destructive/20 bg-destructive/5 p-4"><div className="flex items-start gap-2 text-destructive"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><div><p className="text-sm font-medium">Failed to load audit events</p><p className="text-xs text-muted-foreground">{error.message}</p></div></div></div>
          ) : (
            <>
              <div className="mt-4 overflow-hidden rounded-md border">
                <table className="w-full text-sm"><thead className="bg-muted/50"><tr><th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Action</th><th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Actor</th><th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Resource</th><th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Details</th><th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Immutable Event</th><th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">Timestamp</th></tr></thead><tbody className="divide-y">{data?.entries.length ? data.entries.map((entry) => (<tr key={entry.id}><td className="px-4 py-3 font-medium">{entry.action}</td><td className="px-4 py-3 text-muted-foreground">{entry.agent}</td><td className="px-4 py-3 text-muted-foreground">{entry.entity_type ?? "resource"}{entry.entity_id ? `:${entry.entity_id}` : ""}</td><td className="px-4 py-3 text-muted-foreground"><p className="max-w-xs truncate">{safeSummary(entry.details)}</p><details className="mt-1"><summary className="cursor-pointer text-xs">View JSON</summary><pre className="max-h-40 overflow-auto rounded bg-muted/40 p-2 text-[11px]">{JSON.stringify(entry.details, null, 2)}</pre></details></td><td className="px-4 py-3 text-muted-foreground">{entry.event_hash || entry.event_reference ? (<div className="text-xs"><p>ID: {entry.id}</p>{entry.event_hash ? <p>Hash: {entry.event_hash}</p> : null}{entry.event_reference ? <p>Ref: {entry.event_reference}</p> : null}</div>) : <span className="text-xs">Integrity metadata unavailable (backend limitation)</span>}</td><td className="px-4 py-3 text-muted-foreground">{new Date(entry.timestamp).toLocaleString()}</td></tr>)) : (<tr><td colSpan={6} className="px-4 py-6 text-center text-sm text-muted-foreground">No operational audit events found for this tenant.</td></tr>)}</tbody></table>
              </div>
              <div className="mt-3 flex items-center justify-between">
                <p className="text-xs text-muted-foreground">Page {data?.page ?? page} of {Math.max(1, Math.ceil((data?.total ?? 0) / (data?.per_page ?? 25)))}</p>
                <div className="flex gap-2">
                  <button type="button" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} className="inline-flex h-8 items-center rounded-md border px-3 text-xs font-medium disabled:opacity-50">Previous</button>
                  <button type="button" disabled={(data?.entries.length ?? 0) < (data?.per_page ?? 25)} onClick={() => setPage((p) => p + 1)} className="inline-flex h-8 items-center rounded-md border px-3 text-xs font-medium disabled:opacity-50">Next</button>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </CapabilityGate>
  );
}
