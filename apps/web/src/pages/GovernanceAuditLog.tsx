import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  useTruths,
  useTruthAuditTrail,
} from "@/hooks/useGroundTruthGovernance";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, DataTable } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";

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
    <PageShell className="max-w-6xl">
      <PageHeader
        breadcrumbs={[{ label: "Governance Audit" }, { label: "Audit Log" }]}
        title="Audit Log"
        subtitle="Validation events and state transitions for Layer 5 truth objects."
      />

      <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
        <SectionCard title="Truth Objects">
          {isLoadingTruths ? (
            <div className="flex items-center gap-2 vf-text-body-s text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading truths…
            </div>
          ) : (
            <div className="space-y-2 max-h-[520px] overflow-auto pr-1">
              {(truthList?.items ?? []).map(truth => (
                <button
                  key={truth.id}
                  onClick={() => setSelectedTruthId(truth.id)}
                  className={`w-full rounded-md border p-2 text-left vf-text-body-s ${
                    selectedTruthId === truth.id
                      ? "border-primary bg-primary/10"
                      : "border-border bg-background"
                  }`}
                >
                  <div className="font-mono vf-text-micro text-muted-foreground">
                    {truth.id.slice(0, 12)}
                  </div>
                  <div className="font-medium text-foreground mt-1 line-clamp-2">
                    {truth.claim}
                  </div>
                  <div className="text-muted-foreground mt-1">
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
            <div className="flex items-center gap-2 p-4 vf-text-body-s text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading audit events…
            </div>
          ) : isError ? (
            <ErrorState
              title="Failed to load audit events"
              description={error?.message || "Could not load the audit trail for the selected truth object."}
              error={error}
              className="p-4"
            />
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
                <span key="transition" className="vf-text-body-s">
                  {event.from_status ?? "—"} → {event.to_status}
                </span>,
                <span key="maturity">
                  {event.from_maturity ?? "—"} → {event.to_maturity}
                </span>,
                <span key="actor" className="font-mono vf-text-caption">
                  {event.actor ?? "system"}
                </span>,
                <span key="type">{event.actor_type}</span>,
                <span key="confidence">
                  {typeof event.confidence_at_transition === "number"
                    ? `${Math.round(event.confidence_at_transition * 100)}%`
                    : "—"}
                </span>,
                <span key="time" className="vf-text-caption text-muted-foreground">
                  {new Date(event.created_at).toLocaleString()}
                </span>,
              ])}
              emptyMessage="No validation events found for this truth object"
            />
          )}
        </SectionCard>
      </div>
    </PageShell>
  );
}
