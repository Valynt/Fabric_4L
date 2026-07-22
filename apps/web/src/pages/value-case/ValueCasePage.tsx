/**
 * ValueCasePage — Value Case workspace entry point
 *
 * Route: /value-case/:accountId
 */
import { useMemo, useState } from "react";
import {
  AlertCircle,
  FileText,
  GitCompare,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { useAccount } from "@/hooks/useAccounts";
import { useCanonicalCaseId } from "@/hooks/useWorkspaceCase";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { LoadingState, ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { useValueCaseArtifacts } from "@/hooks/useValueCaseArtifacts";
import type { ValueCaseArtifactsInput } from "@/hooks/useValueCaseArtifacts";
import { ValueCaseGenerationPanel } from "@/components/value-case/ValueCaseGenerationPanel";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard } from "@/components/ui/fabric";
import type { StudioTabProps } from "@/features/value-studio/types";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Unexpected error. Please try again.";
}

function GenerationPanelWithCase({
  accountId,
  accountName,
  isOpen,
  onClose,
  onGenerate,
  isGenerating,
}: {
  accountId: string;
  accountName: string;
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (input: ValueCaseArtifactsInput) => void;
  isGenerating: boolean;
}) {
  const { data: caseId } = useCanonicalCaseId(accountId);
  return (
    <ValueCaseGenerationPanel
      accountId={accountId}
      accountName={accountName}
      caseId={caseId ?? null}
      isOpen={isOpen}
      onClose={onClose}
      onGenerate={onGenerate}
      isGenerating={isGenerating}
    />
  );
}

export default function ValueCasePage({ accountId }: StudioTabProps) {
  const { data: account, isLoading: accountLoading } = useAccount(
    accountId ?? null
  );

  const {
    versions,
    isLoadingVersions,
    versionsError,
    refetch,
    selectedVersion,
    setSelectedVersionId,
    generateArtifact,
    publishArtifact,
  } = useValueCaseArtifacts(accountId ?? null);

  const previousVersion = useMemo(() => {
    if (!selectedVersion) return null;
    const idx = versions.findIndex(item => item.id === selectedVersion.id);
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
    return (
      <ErrorState
        title="Account not found"
        description="Select a valid account to continue in this workspace."
        fullPage
      />
    );
  }

  if (isLoadingVersions) {
    return <LoadingState message="Loading value cases…" fullPage />;
  }

  if (versionsError) {
    return (
      <ErrorState
        title="Failed to load value cases"
        description="Could not load value case versions."
        error={versionsError}
        onRetry={() => refetch()}
        fullPage
      />
    );
  }

  const [isPanelOpen, setIsPanelOpen] = useState(false);

  const handleGenerate = () => {
    setIsPanelOpen(true);
  };

  const handleConfirmGenerate = (input: ValueCaseArtifactsInput) => {
    generateArtifact.mutate(input);
    setIsPanelOpen(false);
  };

  const handlePublishRetry = () => {
    if (!selectedVersion) return;
    publishArtifact.mutate(selectedVersion.id);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <FileText className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              Value Case
            </h2>
            <p className="text-sm text-muted-foreground">
              Generated value narrative and business case for the prospect
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={handleGenerate}
            disabled={generateArtifact.isPending}
            aria-busy={generateArtifact.isPending}
          >
            {generateArtifact.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            {versions.length ? "Regenerate" : "Generate"}
          </Button>

          {selectedVersion && selectedVersion.status !== "published" && (
            <Button
              variant="secondary"
              onClick={() => publishArtifact.mutate(selectedVersion.id)}
              disabled={publishArtifact.isPending}
              aria-busy={publishArtifact.isPending}
            >
              <Loader2
                className={`mr-2 h-4 w-4 ${
                  publishArtifact.isPending ? "animate-spin" : "hidden"
                }`}
              />
              {publishArtifact.isPending ? "Publishing…" : "Publish"}
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <MetricCard
          label="3-Year Value"
          value={selectedVersion?.business_case.metrics.three_year_value ?? "—"}
        />
        <MetricCard
          label="ROI"
          value={selectedVersion?.business_case.metrics.roi ?? "—"}
        />
        <MetricCard
          label="Payback"
          value={selectedVersion?.business_case.metrics.payback ?? "—"}
        />
      </div>

      {generateArtifact.isError && (
        <div role="alert">
          <SectionCard title="Generation failed">
            <div className="flex items-center justify-between gap-4 rounded-lg border border-destructive/40 bg-destructive/5 p-4">
              <div className="space-y-1">
                <p className="text-sm text-foreground flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-destructive" />
                  Unable to generate value case. Retry with the same inputs.
                </p>
                <p className="text-sm text-muted-foreground">
                  {getErrorMessage(generateArtifact.error)}
                </p>
              </div>
              <Button
                variant="outline"
                onClick={handleGenerate}
                disabled={generateArtifact.isPending}
              >
                Retry
              </Button>
            </div>
          </SectionCard>
        </div>
      )}

      {publishArtifact.isError && (
        <div role="alert">
          <SectionCard title="Publish failed">
            <div className="flex items-center justify-between gap-4 rounded-lg border border-destructive/40 bg-destructive/5 p-4">
              <div className="space-y-1">
                <p className="text-sm text-foreground flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-destructive" />
                  Unable to publish value case. Retry to finalize the artifact.
                </p>
                <p className="text-sm text-muted-foreground">
                  {getErrorMessage(publishArtifact.error)}
                </p>
              </div>
              <Button
                variant="outline"
                onClick={handlePublishRetry}
                disabled={!selectedVersion || publishArtifact.isPending}
              >
                Retry
              </Button>
            </div>
          </SectionCard>
        </div>
      )}

      <SectionCard
        title="Value Case Versions"
        subtitle="Generated artifacts are versioned for returning users."
      >
        {!versions.length ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center">
            <p className="text-sm text-muted-foreground">
              No prior versions yet. Generate your first value case artifact.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {versions.map(version => (
                <Button
                  key={version.id}
                  variant={
                    selectedVersion?.id === version.id ? "default" : "outline"
                  }
                  size="sm"
                  onClick={() => setSelectedVersionId(version.id)}
                  aria-pressed={selectedVersion?.id === version.id}
                >
                  v{version.version}
                </Button>
              ))}
            </div>

            {selectedVersion && (
              <div className="rounded-lg border border-border p-4 space-y-2">
                <p className="text-xs text-muted-foreground">
                  Created {new Date(selectedVersion.created_at).toLocaleString()}
                </p>
                <p className="text-sm font-medium">
                  {selectedVersion.narrative.title}
                </p>
                <p className="text-sm text-muted-foreground">
                  {selectedVersion.business_case.summary}
                </p>
              </div>
            )}

            <div className="rounded-lg border border-border p-4 space-y-2">
              <p className="text-sm font-medium flex items-center gap-2">
                <GitCompare className="h-4 w-4" />
                Version Diff
              </p>

              {!previousVersion || !selectedVersion ? (
                <p className="text-sm text-muted-foreground">
                  Select a newer version to see diffs from prior output.
                </p>
              ) : (
                <ul className="text-sm text-muted-foreground list-disc pl-5">
                  <li>
                    ROI: {previousVersion.business_case.metrics.roi} →{" "}
                    {selectedVersion.business_case.metrics.roi}
                  </li>
                  <li>
                    Payback: {previousVersion.business_case.metrics.payback} →{" "}
                    {selectedVersion.business_case.metrics.payback}
                  </li>
                  <li>
                    Risk notes: {previousVersion.business_case.risks.length} →{" "}
                    {selectedVersion.business_case.risks.length}
                  </li>
                </ul>
              )}
            </div>
          </div>
        )}
      </SectionCard>

      <GenerationPanelWithCase
        accountId={account.id}
        accountName={account.name}
        isOpen={isPanelOpen}
        onClose={() => setIsPanelOpen(false)}
        onGenerate={handleConfirmGenerate}
        isGenerating={generateArtifact.isPending}
      />
    </div>
  );
}
