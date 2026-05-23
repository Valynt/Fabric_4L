import { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  useTruths,
  useTruthAuditTrail,
  type TruthStatus,
} from "@/hooks/useGroundTruthGovernance";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, LegacyDataTable } from "@/components/ui/fabric";

export default function GovernanceChangeHistory() {
  const [statusFilter, setStatusFilter] = useState<TruthStatus | "all">("all");
  const [selectedTruthId, setSelectedTruthId] = useState<string>("");

  const filters = useMemo(
    () => ({
      limit: 100,
      ...(statusFilter === "all" ? {} : { status: statusFilter }),
    }),
    [statusFilter]
  );

  const { data: truthData, isLoading: isLoadingTruths } = useTruths(filters);
  const { data: auditTrail, isLoading: isLoadingTrail } = useTruthAuditTrail(
    selectedTruthId || null
  );

  return (
    <div className="p-6 max-w-6xl">
      <PageHeader
        breadcrumbs={[
          { label: "Governance Audit" },
          { label: "Change History" },
        ]}
        title="Change History"
        subtitle="State transition timeline for truth validation workflows."
      />

      <SectionCard title="Selection" className="mb-5">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-[12px] text-neutral-700">
            Truth status filter
            <select
              className="mt-1 block w-full rounded-md border border-neutral-300 bg-white px-2 py-1 text-[12px]"
              value={statusFilter}
              onChange={e =>
                setStatusFilter(e.target.value as TruthStatus | "all")
              }
            >
              <option value="all">All statuses</option>
              <option value="proposed">proposed</option>
              <option value="validated">validated</option>
              <option value="disputed">disputed</option>
              <option value="rejected">rejected</option>
              <option value="superseded">superseded</option>
              <option value="expired">expired</option>
            </select>
          </label>
          <label className="text-[12px] text-neutral-700">
            Truth object
            <select
              className="mt-1 block w-full rounded-md border border-neutral-300 bg-white px-2 py-1 text-[12px]"
              value={selectedTruthId}
              onChange={e => setSelectedTruthId(e.target.value)}
            >
              <option value="">Select a truth object…</option>
              {(truthData?.items ?? []).map(truth => (
                <option key={truth.id} value={truth.id}>
                  {truth.id.slice(0, 10)} — {truth.claim.slice(0, 60)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </SectionCard>

      <SectionCard title="State Transition Timeline" noPad>
        {isLoadingTruths || (selectedTruthId && isLoadingTrail) ? (
          <div className="flex items-center gap-2 p-4 text-[12px] text-neutral-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading change history…
          </div>
        ) : (
          <LegacyDataTable
            columns={[
              "From Status",
              "To Status",
              "From Maturity",
              "To Maturity",
              "Notes",
              "Created",
            ]}
            rows={(auditTrail ?? []).map(event => [
              <span key="from-status">{event.from_status ?? "—"}</span>,
              <span key="to-status" className="font-medium">
                {event.to_status}
              </span>,
              <span key="from-maturity">{event.from_maturity ?? "—"}</span>,
              <span key="to-maturity">{event.to_maturity}</span>,
              <span key="notes" className="text-[11px] text-neutral-600">
                {event.notes ?? "—"}
              </span>,
              <span key="created" className="text-[11px] text-neutral-500">
                {new Date(event.created_at).toLocaleString()}
              </span>,
            ])}
            emptyMessage={
              selectedTruthId
                ? "No transitions recorded for this truth object"
                : "Select a truth object to view transitions"
            }
          />
        )}
      </SectionCard>
    </div>
  );
}
