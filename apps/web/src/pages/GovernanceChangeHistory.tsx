import { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import {
  useTruths,
  useTruthAuditTrail,
  type TruthStatus,
} from "@/hooks/useGroundTruthGovernance";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, DataTable } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { LoadingState, ErrorState } from "@/components/states";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const STATUS_OPTIONS: Array<{ value: TruthStatus | "all"; label: string }> = [
  { value: "all", label: "All statuses" },
  { value: "proposed", label: "Proposed" },
  { value: "validated", label: "Validated" },
  { value: "disputed", label: "Disputed" },
  { value: "rejected", label: "Rejected" },
  { value: "superseded", label: "Superseded" },
  { value: "expired", label: "Expired" },
];

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
    <PageShell>
      <PageHeader
        breadcrumbs={[
          { label: "Governance Audit" },
          { label: "Change History" },
        ]}
        title="Change History"
        subtitle="State transition timeline for truth validation workflows."
      />

      <SectionCard title="Selection" className="mb-5">
        <div className="grid gap-3 md:grid-cols-2 vf-text-body-s">
          <div className="space-y-1.5">
            <label className="font-medium text-foreground">Truth status filter</label>
            <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as TruthStatus | "all")}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <label className="font-medium text-foreground">Truth object</label>
            <Select value={selectedTruthId} onValueChange={setSelectedTruthId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a truth object…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Select a truth object…</SelectItem>
                {(truthData?.items ?? []).map(truth => (
                  <SelectItem key={truth.id} value={truth.id}>
                    {truth.id.slice(0, 10)} — {truth.claim.slice(0, 60)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="State Transition Timeline" noPad>
        {isLoadingTruths || (selectedTruthId && isLoadingTrail) ? (
          <LoadingState message="Loading change history…" className="py-4" />
        ) : (
          <DataTable
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
              <span key="notes" className="vf-text-caption text-muted-foreground">
                {event.notes ?? "—"}
              </span>,
              <span key="created" className="vf-text-caption text-muted-foreground">
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
    </PageShell>
  );
}
