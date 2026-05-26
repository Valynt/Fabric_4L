import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { useTruths, type TruthStatus } from "@/hooks/useGroundTruthGovernance";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, DataTable } from "@/components/ui/fabric";

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

  const { data, isLoading, isError, error } = useTruths(filters, { enabled: shouldLoadTruths, retry: false });

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
    <div className="p-6 max-w-6xl">
      <PageHeader
        breadcrumbs={[{ label: "Governance" }, { label: "Evidence" }]}
        title="Evidence"
        subtitle="Truth object listing and filter controls sourced from Layer 5 governance APIs."
      />

      <SectionCard title="Evidence-backed Claim Lineage" className="mb-5">
        <h2 className="sr-only">Evidence-backed Claim Lineage</h2>
        <div className="grid gap-3 md:grid-cols-4 text-[12px]">
          <div className="rounded-md border border-neutral-200 p-3">
            <h3 className="font-semibold text-neutral-800">Truth Objects</h3>
            <p className="mt-1 text-neutral-600">Tenant-scoped evidence records connect each claim to validation state.</p>
          </div>
          <div className="rounded-md border border-neutral-200 p-3">
            <h3 className="font-semibold text-neutral-800">Claim</h3>
            <p className="mt-1 text-neutral-600">Business-case assertions remain traceable back to source material.</p>
          </div>
          <div className="rounded-md border border-neutral-200 p-3">
            <h3 className="font-semibold text-neutral-800">Confidence</h3>
            <p className="mt-1 text-neutral-600">Validation confidence and maturity stay visible for approval review.</p>
          </div>
          <div className="rounded-md border border-neutral-200 p-3">
            <h3 className="font-semibold text-neutral-800">Source</h3>
            <p className="mt-1 text-neutral-600">Source lineage is retained even when the live governance API is degraded.</p>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Filters" className="mb-5">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-[12px] text-neutral-700">
            Status
            <select
              className="mt-1 block w-full rounded-md border border-neutral-300 bg-white px-2 py-1 text-[12px]"
              value={status}
              onChange={e => setStatus(e.target.value as TruthStatus | "all")}
            >
              {STATUS_OPTIONS.map(value => (
                <option key={value} value={value}>
                  {value === "all" ? "All statuses" : value}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[12px] text-neutral-700">
            Search claim or truth ID
            <input
              className="mt-1 block w-full rounded-md border border-neutral-300 bg-white px-2 py-1 text-[12px]"
              placeholder="Search…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </label>
        </div>
      </SectionCard>

      <SectionCard title={`Truth Objects (${visibleItems.length})`} noPad>
        {shouldLoadTruths && isLoading ? (
          <div className="flex items-center gap-2 p-4 text-[12px] text-neutral-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading truths…
          </div>
        ) : isError ? (
          <div className="p-4 text-[12px] text-red-600">{error.message}</div>
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
              <span key="id" className="font-mono text-[11px] text-neutral-600">
                {item.id.slice(0, 12)}
              </span>,
              <span key="claim" className="text-neutral-800">
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
              <span key="freshness" className="text-[11px] text-neutral-500">
                {item.freshness ? new Date(item.freshness).toLocaleDateString() : (item.is_stale ? 'Stale' : 'Fresh')}
              </span>,
            ])}
            emptyMessage="No truth objects matched the selected filters"
          />
        )}
      </SectionCard>
    </div>
  );
}
