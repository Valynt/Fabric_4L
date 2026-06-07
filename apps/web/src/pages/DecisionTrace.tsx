/**
 * Screen 10 — Audit & Provenance: Decision Trace Viewer
 * Design: Refined Enterprise SaaS
 */
import { useEffect, useState, useMemo } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { Shield, Download, CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { useProvenanceTrail, useAuditLogs, useExportProvenance, type AuditLogEntry, type AuditLogFilter } from "@/hooks/useProvenance";
import { useBusinessCase } from "@/hooks/useDocuments";
import { createFeatureLogger } from "@/lib/telemetry";
import { Toolbar } from "@/components/ui/fabric";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, Btn, StatusBadge, DataTable } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";

const log = createFeatureLogger('DecisionTrace');

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function DecisionTrace() {
  const { pathname: location } = useLocation();
  const activeSection = useMemo(() => {
    if (location.includes("/audit/changes")) return "changes";
    if (location.includes("/audit/log")) return "audit";
    if (location.includes("/compliance")) return "compliance";
    if (location.includes("/integrity")) return "integrity";
    if (location.includes("/provenance")) return "provenance";
    if (location.includes("/evidence")) return "evidence";
    return "traces";
  }, [location]);
  const sectionTitles: Record<string, string> = {
    traces: "Decision Traces", evidence: "Evidence Chain",
    provenance: "Provenance Trail", integrity: "Data Integrity",
    compliance: "Compliance Checks", audit: "Audit Log", changes: "Change History",
  };
  const [searchParams] = useSearchParams();
  const entityIdFromUrl = searchParams.get("entityId") || searchParams.get("caseId");
  const caseIdFromUrl = searchParams.get("caseId");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(entityIdFromUrl);
  const [sourceFilter, setSourceFilter] = useState<AuditLogFilter['source']>("all");
  const [shouldLoadTraceData, setShouldLoadTraceData] = useState(false);

  useEffect(() => {
    setShouldLoadTraceData(false);
    const timer = window.setTimeout(() => setShouldLoadTraceData(true), 750);
    return () => window.clearTimeout(timer);
  }, [location, selectedEntityId, sourceFilter]);

  const {
    data: auditLogs,
    isLoading: isLoadingAudit,
    isError: isAuditError,
    error: auditError,
    refetch: refetchAudit,
  } = useAuditLogs(
    { source: sourceFilter },
    { enabled: shouldLoadTraceData, retry: false }
  );
  const {
    data: provenanceTrail,
    isLoading: isLoadingProvenance,
    isError: isProvenanceError,
    error: provenanceError,
    refetch: refetchProvenance,
  } = useProvenanceTrail(
    selectedEntityId,
    { enabled: shouldLoadTraceData, retry: false }
  );
  const exportMutation = useExportProvenance();
  const { data: governanceCase } = useBusinessCase(caseIdFromUrl);

  const isLoading = shouldLoadTraceData && (isLoadingAudit || (selectedEntityId && isLoadingProvenance));
  const hasError = isAuditError || isProvenanceError;

  const handleExportProvO = async () => {
    if (!selectedEntityId) return;
    try {
      await exportMutation.mutateAsync({ entityId: selectedEntityId, format: 'prov-o' });
    } catch (error) {
      log.error('Export failed', { errorCode: String(error) });
      toast.error('Export failed. Please try again.');
    }
  };

  const handleViewEntity = (entityId: string) => {
    setSelectedEntityId(entityId);
  };

  const auditEntries: AuditLogEntry[] = auditLogs?.entries || [];

  const auditRows = auditEntries.map((entry) => [
    <button
      key="id"
      onClick={() => entry.entity_id && handleViewEntity(entry.entity_id)}
      className={`font-mono vf-text-caption ${
        selectedEntityId === entry.entity_id
          ? "text-primary font-bold"
          : "text-muted-foreground hover:text-primary"
      }`}
    >
      {entry.id.slice(0, 12)}
    </button>,
    <span key="entity" className="font-semibold text-foreground">
      {entry.entity_type || "System"}
    </span>,
    <span key="action" className="text-muted-foreground">{entry.action}</span>,
    <span key="agent" className="text-muted-foreground vf-text-caption font-mono">
      {entry.agent}
    </span>,
    <span key="ts" className="text-muted-foreground/60 vf-text-caption font-mono">
      {formatTimestamp(entry.timestamp)}
    </span>,
    <StatusBadge key="status" status={entry.event_type === 'error' ? 'failed' : 'completed'} />,
    <div key="actions" className="flex gap-2">
      {entry.entity_id && (
        <button
          onClick={() => handleViewEntity(entry.entity_id!)}
          className="text-primary vf-text-caption hover:underline"
        >
          View
        </button>
      )}
    </div>,
  ]);

  const provenanceSteps = provenanceTrail?.steps || [];

  if (isLoading) {
    return (
      <PageShell>
        <PageHeader
          breadcrumbs={[{ label: "Governance" }, { label: sectionTitles[activeSection] ?? "Decision Traces" }]}
          title={sectionTitles[activeSection] ?? "Decision Trace Viewer"}
          subtitle="Loading tenant-scoped claim lineage, truth references, provenance timeline, and audit log."
          actions={
            <Btn variant="ghost" disabled>
              <Download size={12} />
              Export PROV-O
            </Btn>
          }
        />

        <Toolbar>
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-8 w-28" />
          <Skeleton className="h-8 w-24" />
        </Toolbar>

        <div className="flex gap-5">
          <div className="flex-1">
            <SectionCard title="Decision Trace" className="mb-5">
              <div className="grid gap-3 md:grid-cols-3 vf-text-body-s">
                <div className="rounded-md border border-border p-3">
                  <div className="font-semibold text-foreground">Provenance Timeline</div>
                  <p className="mt-1 text-muted-foreground">
                    Claim lineage, source evidence, confidence, and approval context are loading.
                  </p>
                </div>
                <div className="rounded-md border border-border p-3">
                  <div className="font-semibold text-foreground">Truth References</div>
                  <p className="mt-1 text-muted-foreground">
                    Evidence-backed truth objects remain tenant-scoped while references load.
                  </p>
                </div>
                <div className="rounded-md border border-border p-3">
                  <div className="font-semibold text-foreground">Audit Log</div>
                  <p className="mt-1 text-muted-foreground">
                    Approval, export, and governance actions are attributable and traceable.
                  </p>
                </div>
              </div>
            </SectionCard>
            <SectionCard title="Audit Log" noPad>
              <div className="flex bg-muted border-b border-border px-4 py-2.5">
                {["Trace ID", "Entity", "Action", "Agent", "Timestamp", "Status", "Actions"].map((_, i) => (
                  <Skeleton key={i} className="h-3 w-16 mr-4" />
                ))}
              </div>
              <div className="divide-y divide-border">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="flex items-center px-4 py-3">
                    <Skeleton className="h-3 w-20 mr-4" />
                    <Skeleton className="h-3 w-16 mr-4" />
                    <Skeleton className="h-3 w-20 mr-4" />
                    <Skeleton className="h-3 w-24 mr-4" />
                    <Skeleton className="h-3 w-16 mr-4" />
                    <Skeleton className="h-5 w-16 mr-4 rounded-full" />
                    <Skeleton className="h-3 w-8" />
                  </div>
                ))}
              </div>
            </SectionCard>
          </div>

          <div className="w-[260px] shrink-0">
            <SectionCard title="Select an Entity">
              <div className="text-center py-8">
                <Skeleton className="h-4 w-40 mx-auto mb-2" />
                <Skeleton className="h-3 w-32 mx-auto" />
              </div>
            </SectionCard>
          </div>
        </div>
      </PageShell>
    );
  }

  if (hasError) {
    return (
      <PageShell>
        <ErrorState
          title="Failed to load decision trace"
          description="The audit log or provenance data could not be loaded. The governance service may be degraded."
          error={auditError || provenanceError}
          onRetry={() => { refetchAudit(); refetchProvenance(); }}
          retryLabel="Retry"
        />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <PageHeader
        breadcrumbs={[{ label: "Governance" }, { label: sectionTitles[activeSection] ?? "Decision Traces" }]}
        title={sectionTitles[activeSection] ?? "Decision Trace Viewer"}
        subtitle={
          selectedEntityId && provenanceTrail
            ? `Provenance for: ${provenanceTrail.entity_name} (${provenanceTrail.entity_type})`
            : "Full provenance and audit trail for all entity decisions."
        }
        actions={
          <>
            <Btn
              variant="ghost"
              onClick={handleExportProvO}
              disabled={!selectedEntityId || exportMutation.isPending}
            >
              {exportMutation.isPending ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Download size={12} />
              )}
              Export PROV-O
            </Btn>
          </>
        }
      />

      <Toolbar>
        <Btn
          variant="ghost"
          onClick={() => setSourceFilter(sourceFilter === 'all' ? 'provenance' : 'all')}
        >
          Source: {sourceFilter === 'all' ? 'All ▾' : 'Provenance ▾'}
        </Btn>
        <Btn variant="ghost">Date Range ▾</Btn>
        <Btn variant="ghost">Status: All ▾</Btn>
        {selectedEntityId && (
          <Btn variant="outline" onClick={() => setSelectedEntityId(null)}>
            Clear Selection
          </Btn>
        )}
      </Toolbar>

      <SectionCard title="Decision Trace" className="mb-5">
        <div className="grid gap-3 md:grid-cols-3 vf-text-body-s">
          <div className="rounded-md border border-border p-3">
            <div className="font-semibold text-foreground">Provenance Timeline</div>
            <p className="mt-1 text-muted-foreground">
              Review claim lineage from source evidence through agent recommendation and approval.
            </p>
          </div>
          <div className="rounded-md border border-border p-3">
            <div className="font-semibold text-foreground">Truth References</div>
            <p className="mt-1 text-muted-foreground">
              Claims remain tied to tenant-scoped truth objects, confidence, and source metadata.
            </p>
          </div>
          <div className="rounded-md border border-border p-3">
            <div className="font-semibold text-foreground">Audit Log</div>
            <p className="mt-1 text-muted-foreground">
              Approval, export, and governance actions are attributable and traceable.
            </p>
          </div>
        </div>
      </SectionCard>

      {governanceCase?.truth_references && governanceCase.truth_references.length > 0 && (
        <SectionCard title="Truth References" className="mb-5">
          <div className="space-y-2">
            {governanceCase.truth_references.map((truthRef, idx) => {
              const ref = truthRef;
              return (
                <div key={`${String(ref.truth_object_id || idx)}`} className="rounded-md border border-border p-3 vf-text-body-s">
                  <div className="font-semibold text-foreground">Requirement: {String(ref.requirement || ref.claim || "Truth reference")}</div>
                  <div className="text-muted-foreground mt-1">
                    ID: <span className="font-mono vf-text-caption">{String(ref.truth_object_id || "n/a")}</span>
                  </div>
                  <div className="text-muted-foreground">
                    Status: {String(ref.status || "unknown")} · Maturity: {String(ref.maturity_level || "n/a")}
                  </div>
                </div>
              );
            })}
          </div>
          {governanceCase.remediation_items && governanceCase.remediation_items.length > 0 && (
            <div className="mt-3 rounded-md border border-warning/20 bg-warning/5 p-3 vf-text-body-s text-warning">
              <div className="font-semibold mb-1">Remediation Required</div>
              <ul className="list-disc pl-5 space-y-1">
                {governanceCase.remediation_items.map((item, idx) => {
                  const rem = item;
                  return <li key={`${idx}-${String(rem.type || "rem")}`}>{String(rem.message || rem.requirement || "Action required")}</li>;
                })}
              </ul>
            </div>
          )}
        </SectionCard>
      )}

      <div className="flex gap-5">
        <div className="flex-1">
          <SectionCard title={`Audit Log (${auditLogs?.total || 0} entries)`} noPad>
            <DataTable
              columns={["Trace ID", "Entity", "Action", "Agent", "Timestamp", "Status", "Actions"]}
              rows={auditRows}
              emptyMessage="No audit entries found"
            />
          </SectionCard>
        </div>

        <div className="w-[260px] shrink-0">
          <SectionCard
            title={selectedEntityId ? "Provenance Timeline" : "Select an Entity"}
          >
            {selectedEntityId ? (
              <>
                {provenanceTrail && (
                  <div className="mb-4 p-3 bg-primary/5 rounded-lg">
                    <div className="vf-text-body-s font-semibold text-foreground">
                      {provenanceTrail.entity_name}
                    </div>
                    <div className="vf-text-caption text-muted-foreground">
                      Type: {provenanceTrail.entity_type}
                    </div>
                    <div className="vf-text-caption text-muted-foreground">
                      Source: {provenanceTrail.source}
                    </div>
                    {provenanceTrail.confidence_score && (
                      <div className="vf-text-caption text-muted-foreground">
                        Confidence: {(provenanceTrail.confidence_score * 100).toFixed(1)}%
                      </div>
                    )}
                  </div>
                )}

                <div className="space-y-0">
                  {provenanceSteps.map((s, i) => (
                    <div key={s.step} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                          i < provenanceSteps.length ? "bg-success/10" : "bg-muted"
                        }`}>
                          <CheckCircle2 size={14} className="text-success" />
                        </div>
                        {i < provenanceSteps.length - 1 && (
                          <div className="w-px flex-1 bg-border my-1 min-h-[16px]"/>
                        )}
                      </div>
                      <div className="pb-4">
                        <div className="vf-text-body-s font-semibold text-foreground">{s.label}</div>
                        <div className="vf-text-caption text-muted-foreground mt-0.5 leading-relaxed">
                          {s.detail}
                        </div>
                        {s.agent && (
                          <div className="vf-text-micro text-muted-foreground/60 mt-1">
                            by {s.agent}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-border">
                  <Btn variant="ghost" className="vf-text-caption justify-center">
                    View Complete Provenance Graph
                  </Btn>
                  <Btn
                    variant="ghost"
                    className="vf-text-caption justify-center"
                    onClick={handleExportProvO}
                    disabled={exportMutation.isPending}
                  >
                    {exportMutation.isPending ? (
                      <Loader2 size={10} className="animate-spin" />
                    ) : (
                      <Download size={10} />
                    )}
                    Export PROV-O
                  </Btn>
                  <Btn variant="outline" className="vf-text-caption justify-center">
                    <Shield size={10}/> Verify Hash
                  </Btn>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p className="vf-text-body-m mb-2">Select an entity from the audit log</p>
                <p className="vf-text-caption">to view its provenance timeline</p>
              </div>
            )}
          </SectionCard>
        </div>
      </div>
    </PageShell>
  );
}
