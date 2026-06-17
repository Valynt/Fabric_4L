/**
 * ValueCasePage — Value Case workspace entry point
 *
 * Route: /value-case/:accountId
 */
import { useMemo } from "react";
import { AlertCircle, FileText, GitCompare, Loader2, RefreshCw } from "lucide-react";
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { LoadingState, ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { useValueCaseArtifacts } from "@/hooks/useValueCaseArtifacts";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard } from "@/components/ui/fabric";
import type { StudioTabProps } from "@/features/value-studio/types";

export default function ValueCasePage({ accountId }: StudioTabProps) {
  const { data: account, isLoading: accountLoading } = useAccount(accountId ?? null);

  const { versions, versionsError, selectedVersion, setSelectedVersionId, generateArtifact, publishArtifact } = useValueCaseArtifacts(accountId ?? null);

  const previousVersion = useMemo(() => {
    if (!selectedVersion) return null;
    const idx = versions.findIndex((item) => item.id === selectedVersion.id);
    if (idx <= 0) return null;
    return versions[idx - 1] ?? null;
  }, [versions, selectedVersion]);

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (accountLoading) {
    return <LoadingState message="Loading account…" fullPage />;
  }

  if (!account) {
    return <ErrorState title="Account not found" description="Select a valid account to continue in this workspace." fullPage />;
  }

  if (versionsError) {
    return (
      <ErrorState
        title="Failed to load value cases"
        description={versionsError instanceof Error ? versionsError.message : "Could not load value case versions."}
      />
    );
  }

  const handleGenerate = () => {
    generateArtifact.mutate({
      account_id: account.id,
      account_name: account.name,
      stakeholders: ["Economic buyer", "Business champion", "Technical evaluator"],
      accepted_evidence: ["Validated calculator assumptions", "Accepted business pains from discovery"],
      scenario_assumptions: ["Conservative ramp in Q1", "Expected adoption by Q2"],
      roi_metrics: {
        three_year_value: "$1.8M",
        roi: "214%",
        payback: "9 months",
      },
      risk_notes: ["Change management capacity", "Competing budget priorities"],
    });
  };

  return (
    <div className="space-y-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <FileText className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground">Value Case</h2>
              <p className="text-sm text-muted-foreground">Generated value narrative and business case for the prospect</p>
            </div>
          </div>
          <Button onClick={handleGenerate} disabled={generateArtifact.isPending}>
            {generateArtifact.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            {versions.length ? "Regenerate" : "Generate"}
          </Button>
          {selectedVersion && selectedVersion.status !== "published" && (
            <Button
              variant="secondary"
              onClick={() => publishArtifact.mutate(selectedVersion.id)}
              disabled={publishArtifact.isPending}
            >
              {publishArtifact.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Publish
            </Button>
          )}
        </div>

        <div className="grid grid-cols-3 gap-4">
          <MetricCard label="3-Year Value" value={selectedVersion?.business_case.metrics.three_year_value ?? "—"} />
          <MetricCard label="ROI" value={selectedVersion?.business_case.metrics.roi ?? "—"} />
          <MetricCard label="Payback" value={selectedVersion?.business_case.metrics.payback ?? "—"} />
        </div>

        {generateArtifact.isError && (
          <SectionCard title="Generation failed">
            <div className="flex items-center justify-between gap-4 rounded-lg border border-destructive/40 bg-destructive/5 p-4">
              <p className="text-sm text-foreground flex items-center gap-2"><AlertCircle className="h-4 w-4 text-destructive" /> Unable to generate value case. Retry with the same inputs.</p>
              <Button variant="outline" onClick={handleGenerate}>Retry</Button>
            </div>
          </SectionCard>
        )}

        <SectionCard title="Value Case Versions" subtitle="Generated artifacts are versioned for returning users.">
          {!versions.length ? (
            <div className="rounded-lg border border-dashed border-border p-8 text-center">
              <p className="text-sm text-muted-foreground">No prior versions yet. Generate your first value case artifact.</p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {versions.map((version) => (
                  <Button key={version.id} variant={selectedVersion?.id === version.id ? "default" : "outline"} size="sm" onClick={() => setSelectedVersionId(version.id)}>
                    v{version.version}
                  </Button>
                ))}
              </div>

              {selectedVersion && (
                <div className="rounded-lg border border-border p-4 space-y-2">
                  <p className="text-xs text-muted-foreground">Created {new Date(selectedVersion.created_at).toLocaleString()}</p>
                  <p className="text-sm font-medium">{selectedVersion.narrative.title}</p>
                  <p className="text-sm text-muted-foreground">{selectedVersion.business_case.summary}</p>
                </div>
              )}

              <div className="rounded-lg border border-border p-4 space-y-2">
                <p className="text-sm font-medium flex items-center gap-2"><GitCompare className="h-4 w-4" /> Version Diff</p>
                {!previousVersion || !selectedVersion ? (
                  <p className="text-sm text-muted-foreground">Select a newer version to see diffs from prior output.</p>
                ) : (
                  <ul className="text-sm text-muted-foreground list-disc pl-5">
                    <li>ROI: {previousVersion.business_case.metrics.roi} → {selectedVersion.business_case.metrics.roi}</li>
                    <li>Payback: {previousVersion.business_case.metrics.payback} → {selectedVersion.business_case.metrics.payback}</li>
                    <li>Risk notes: {previousVersion.business_case.risks.length} → {selectedVersion.business_case.risks.length}</li>
                  </ul>
                )}
              </div>
            </div>
          )}
        </SectionCard>
    </div>
  );
}
