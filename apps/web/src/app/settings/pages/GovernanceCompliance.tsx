import { AlertCircle, Loader2 } from "lucide-react";
import { useComplianceStatus, type ComplianceFrameworkStatus } from "@/hooks/useComplianceStatus";
import { usePlatformSettings, useUpdatePlatformSettings } from "@/hooks/usePlatformSettings";

function formatDate(value?: string): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function StatusBadge({ status }: { status: ComplianceFrameworkStatus["status"] }) {
  const styles: Record<ComplianceFrameworkStatus["status"], string> = {
    compliant: "bg-primary/10 text-primary",
    in_progress: "bg-warning/10 text-warning dark:bg-warning/20 dark:text-warning",
    non_compliant: "bg-destructive/10 text-destructive dark:bg-destructive/20 dark:text-destructive",
    expired: "bg-destructive/10 text-destructive dark:bg-destructive/20 dark:text-destructive",
    not_applicable: "bg-muted text-muted-foreground",
  };

  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 vf-text-micro font-medium ${styles[status]}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}

export function GovernanceCompliance() {
  const complianceQuery = useComplianceStatus();
  const settingsQuery = usePlatformSettings();
  const updateSettings = useUpdatePlatformSettings();

  const frameworkRows = complianceQuery.data?.items ?? [];
  const settings = settingsQuery.data;
  const dataResidencyRegion = settings?.compliance?.data_residency_region;
  const isSelfServiceResidency = settings?.compliance?.data_residency_self_service === true;

  return (
    <div className="space-y-6">
      <section className="rounded-lg border bg-card p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold">Compliance Frameworks</h3>
            <p className="text-xs text-muted-foreground">
              Tenant-scoped framework posture, controls, exceptions, and evidence attestations.
            </p>
          </div>
          {complianceQuery.data?.updated_at && (
            <p className="text-xs text-muted-foreground">
              Last updated {formatDate(complianceQuery.data.updated_at)}
              {complianceQuery.data.updated_by ? ` by ${complianceQuery.data.updated_by}` : ""}
            </p>
          )}
        </div>

        {complianceQuery.isLoading && (
          <div className="mt-4 inline-flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading compliance status…
          </div>
        )}

        {complianceQuery.isError && (
          <div className="mt-4 inline-flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive dark:border-destructive/30 dark:bg-destructive/20/50 dark:text-destructive">
            <AlertCircle className="h-4 w-4" /> Could not load compliance status.
          </div>
        )}

        {!complianceQuery.isLoading && !complianceQuery.isError && frameworkRows.length === 0 && (
          <p className="mt-4 text-sm text-muted-foreground">No compliance frameworks configured for this tenant.</p>
        )}

        {!complianceQuery.isLoading && !complianceQuery.isError && frameworkRows.length > 0 && (
          <div className="mt-4 space-y-2">
            {frameworkRows.map((framework) => (
              <div key={framework.framework} className="rounded-md border p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium">{framework.framework}</p>
                    <p className="text-xs text-muted-foreground">
                      Effective {formatDate(framework.effective_date)} · Next review {formatDate(framework.next_review_date)} · Attestation expiry {formatDate(framework.attestation_expires_at)}
                    </p>
                  </div>
                  <StatusBadge status={framework.status} />
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Control coverage: {framework.control_coverage_percent}% · Exceptions: {framework.exceptions_count} · Owner: {framework.owner || "Unassigned"}
                </p>
                {framework.evidence_references.length > 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Evidence: {framework.evidence_references.map((e) => e.label).join(", ")}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {complianceQuery.isStale && !complianceQuery.isLoading && (
          <p className="mt-3 text-xs text-warning dark:text-warning">
            This view may be stale while the latest tenant compliance snapshot is refreshed.
          </p>
        )}
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h3 className="text-sm font-semibold">Data Residency</h3>
        <p className="text-xs text-muted-foreground">Control where tenant data is stored and processed.</p>
        <div className="mt-4 max-w-sm">
          {settingsQuery.isLoading ? (
            <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading residency configuration…
            </div>
          ) : isSelfServiceResidency ? (
            <select
              className="h-9 w-full rounded-md border bg-background px-3 text-sm"
              value={dataResidencyRegion ?? ""}
              disabled={updateSettings.isPending}
              onChange={(event) => {
                updateSettings.mutate({ compliance: { data_residency_region: event.target.value } });
              }}
            >
              <option value="US-East (Virginia)">US-East (Virginia)</option>
              <option value="EU-West (Ireland)">EU-West (Ireland)</option>
              <option value="APAC (Singapore)">APAC (Singapore)</option>
            </select>
          ) : (
            <p className="rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground">
              Managed by platform{dataResidencyRegion ? ` (${dataResidencyRegion})` : ""}.
            </p>
          )}
          {settingsQuery.isError && (
            <p className="mt-2 text-xs text-destructive dark:text-destructive">Failed to load residency configuration.</p>
          )}
        </div>
      </section>
    </div>
  );
}
