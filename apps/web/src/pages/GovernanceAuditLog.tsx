import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  useTruths,
  useTruthAuditTrail,
} from "@/hooks/useGroundTruthGovernance";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, DataTable } from "@/components/ui/fabric";

export default function GovernanceAuditLog() {
  const { data: truthList, isLoading: isLoadingTruths } = useTruths({
    limit: 100,
  });
  const [selectedTruthId, setSelectedTruthId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedTruthId && truthList?.items?.[0]?.id) {
      setSelectedTruthId(truthList.items[0].id);
    }
  }, [selectedTruthId, truthList?.items]);

  const {
    data: events,
    isLoading: isLoadingAudit,
    isError,
    error,
  } = useTruthAuditTrail(selectedTruthId);

  const selectedTruth = useMemo(
    () => truthList?.items.find(item => item.id === selectedTruthId),
    [truthList?.items, selectedTruthId]
  );

  return (
    <div className="p-6 max-w-6xl">
      <PageHeader
        breadcrumbs={[{ label: "Governance Audit" }, { label: "Audit Log" }]}
        title="Audit Log"
        subtitle="Validation events and state transitions for Layer 5 truth objects."
      />

      <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
        <SectionCard title="Truth Objects">
          {isLoadingTruths ? (
            <div className="flex items-center gap-2 text-[12px] text-neutral-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading truths…
            </div>
          ) : (
            <div className="space-y-2 max-h-[520px] overflow-auto pr-1">
              {(truthList?.items ?? []).map(truth => (
                <button
                  key={truth.id}
                  onClick={() => setSelectedTruthId(truth.id)}
                  className={`w-full rounded-md border p-2 text-left text-[12px] ${
                    selectedTruthId === truth.id
                      ? "border-blue-500 bg-blue-50"
                      : "border-neutral-200 bg-white"
                  }`}
                >
                  <div className="font-mono text-[10px] text-neutral-500">
                    {truth.id.slice(0, 12)}
                  </div>
                  <div className="font-medium text-neutral-800 mt-1 line-clamp-2">
                    {truth.claim}
                  </div>
                  <div className="text-neutral-500 mt-1">
                    {truth.status} · L{truth.maturity_level}
                  </div>
                </button>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard
          title={
            selectedTruth
              ? `Audit Trail — ${selectedTruth.id.slice(0, 12)}`
              : "Audit Trail"
          }
          noPad
        >
          {isLoadingAudit ? (
            <div className="flex items-center gap-2 p-4 text-[12px] text-neutral-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading audit events…
            </div>
          ) : isError ? (
            <div className="p-4 text-[12px] text-red-600">{error.message}</div>
          ) : (
            <DataTable
              columns={[
                "Transition",
                "Maturity",
                "Actor",
                "Type",
                "Confidence",
                "When",
              ]}
              rows={(events ?? []).map(event => [
                <span key="transition" className="text-[12px]">
                  {event.from_status ?? "—"} → {event.to_status}
                </span>,
                <span key="maturity">
                  {event.from_maturity ?? "—"} → {event.to_maturity}
                </span>,
                <span key="actor" className="font-mono text-[11px]">
                  {event.actor ?? "system"}
                </span>,
                <span key="type">{event.actor_type}</span>,
                <span key="confidence">
                  {typeof event.confidence_at_transition === "number"
                    ? `${Math.round(event.confidence_at_transition * 100)}%`
                    : "—"}
                </span>,
                <span key="time" className="text-[11px] text-neutral-500">
                  {new Date(event.created_at).toLocaleString()}
                </span>,
              ])}
              emptyMessage="No validation events found for this truth object"
            />
          )}
        </SectionCard>
      </div>
    </div>
  );
}
