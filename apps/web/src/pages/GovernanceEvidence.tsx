import { useEffect, useMemo, useState } from "react";
import { Loader2, AlertCircle } from "lucide-react";
import { useTruths, type TruthStatus } from "@/hooks/useGroundTruthGovernance";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, DataTable } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";

const STATUS_OPTIONS: Array<TruthStatus | "all"> = [
  "all",
  "proposed",
  "validated",
  "disputed",
  "rejected",
  "superseded",
  "expired",
];

export default function GovernanceEvidence() {
  const [status, setStatus] = useState<TruthStatus | "all">("all");
  const [search, setSearch] = useState("");
  const [shouldLoadTruths, setShouldLoadTruths] = useState(false);

  const filters = useMemo(
    () => ({
      limit: 100,
      ...(status !== "all" ? { status } : {}),
    }),
    [status]
  );

  useEffect(() => {
    setShouldLoadTruths(false);
    const timer = window.setTimeout(() => setShouldLoadTruths(true), 750);
    return () => window.clearTimeout(timer);
  }, [filters]);

  const { data, isLoading, isError, error, refetch } = useTruths(filters, { enabled: shouldLoadTruths, retry: false });

  const visibleItems = useMemo(() => {
    const items = data?.items ?? [];
    if (!search.trim()) return items;
    const query = search.trim().toLowerCase();
    return items.filter(
      item =>
        (item.claim ?? '').toLowerCase().includes(query) ||
        (item.id ?? '').toLowerCase().includes(query)
    );
  }, [data?.items, search]);

  return (
    <PageShell>
      <PageHeader
        breadcrumbs={[{ label: "Governance" }, { label: "Evidence" }]}
        title="Evidence"
        subtitle="Truth object listing and filter controls sourced from Layer 5 governance APIs."
      />

      <SectionCard title="Evidence-backed Claim Lineage" className="mb-5">
        <h2 className="sr-only">Evidence-backed Claim Lineage</h2>
        <div className="grid gap-3 md:grid-cols-4 vf-text-body-s">
          <div className="rounded-md border border-border p-3">
            <h3 className="font-semibold text-foreground">Truth Objects</h3>
            <p className="mt-1 text-muted-foreground">Tenant-scoped evidence records connect each claim to validation state.</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <h3 className="font-semibold text-foreground">Claim</h3>
            <p className="mt-1 text-muted-foreground">Business-case assertions remain traceable back to source material.</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <h3 className="font-semibold text-foreground">Confidence</h3>
            <p className="mt-1 text-muted-foreground">Validation confidence and maturity stay visible for approval review.</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <h3 className="font-semibold text-foreground">Source</h3>
            <p className="mt-1 text-muted-foreground">Source lineage is retained even when the live governance API is degraded.</p>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Filters" className="mb-5">
        <div className="grid gap-3 md:grid-cols-2 vf-text-body-s">
          <div className="space-y-1.5">
            <label className="font-medium text-foreground">Status</label>
            <Select value={status} onValueChange={(v) => setStatus(v as TruthStatus | "all")}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map(value => (
                  <SelectItem key={value} value={value}>
                    {value === "all" ? "All statuses" : value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <label className="font-medium text-foreground">Search claim or truth ID</label>
            <Input
              placeholder="Search…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>
      </SectionCard>

      <SectionCard title={`Truth Objects (${visibleItems.length})`} noPad>
        {shouldLoadTruths && isLoading ? (
          <div className="flex items-center gap-2 p-4 vf-text-body-s text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading truths…
          </div>
        ) : isError ? (
          <ErrorState
            title="Failed to load truths"
            description="The governance API could not be reached. It may be degraded or you may not have permission."
            error={error}
            onRetry={refetch}
            retryLabel="Retry"
          />
        ) : (
          <DataTable
            columns={[
              "Truth ID",
              "Claim",
              "Status",
              "Maturity",
              "Confidence",
              "Stale",
              "Freshness",
            ]}
            rows={visibleItems.map(item => [
              <span key="id" className="font-mono vf-text-caption text-muted-foreground">
                {item.id.slice(0, 12)}
              </span>,
              <span key="claim" className="text-foreground">
                {item.claim}
              </span>,
              <span key="status" className="capitalize">
                {item.status}
              </span>,
              <span key="maturity">L{item.maturity_level}</span>,
              <span key="confidence">
                {Math.round(item.confidence * 100)}%
              </span>,
              <span key="stale">{item.is_stale ? "Yes" : "No"}</span>,
              <span key="freshness" className="vf-text-caption text-muted-foreground">
                {item.freshness ? new Date(item.freshness).toLocaleDateString() : (item.is_stale ? 'Stale' : 'Fresh')}
              </span>,
            ])}
            emptyMessage="No truth objects matched the selected filters"
          />
        )}
      </SectionCard>
    </PageShell>
  );
}
