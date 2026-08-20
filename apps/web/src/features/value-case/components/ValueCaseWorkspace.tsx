import { useState } from "react";
import {
  AlertCircle,
  FileText,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { LoadingState, ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SectionCard } from "@/components/blocks/SectionCard";
import { useValueCaseJourney } from "../queries/useValueCaseJourney";
import { ValueCaseMetrics } from "./ValueCaseMetrics";
import { ValueCaseResult } from "./ValueCaseResult";
import { ValueCaseVersionHistory } from "./ValueCaseVersionHistory";
import { ValueCaseGenerationPanel } from "./ValueCaseGenerationPanel";
import type { ValueCaseGenerationInputsDraft } from "../domain/valueCaseModels";

export interface ValueCaseWorkspaceProps {
  accountId: string;
  accountName?: string;
  className?: string;
}

export function ValueCaseWorkspace({
  accountId,
  accountName = "Account",
  className = "space-y-6",
}: ValueCaseWorkspaceProps) {
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  const {
    lifecycleState,
    activeResultViewModel,
    versionSummaries,
    versionDiff,
    latestMetricsViewModels,
    selectedVersionId,
    setSelectedVersionId,
    generationInputsDraft,
    inputProvenance,
    inputAvailability,
    isLoadingInputs,
    inputsError,
    versionsError,
    isGenerating,
    isPublishing,
    generateError,
    publishError,
    lastMutationMessage,
    generateCase,
    publishCase,
    refetchVersions,
  } = useValueCaseJourney(accountId, accountName);

  // 1. Lifecycle: Resolving Identity / Authorization Scope
  if (lifecycleState === "resolving-identity") {
    return (
      <LoadingState
        message="Verifying tenant and account authorization…"
        fullPage
      />
    );
  }

  // 2. Lifecycle: Access Denied / Scope Mismatch
  if (lifecycleState === "denied") {
    return (
      <ErrorState
        title="Access Denied"
        description="You do not have verified tenant authorization for this account value case workspace."
        fullPage
      />
    );
  }

  // 3. Lifecycle: Session Expired
  if (lifecycleState === "expired") {
    return (
      <ErrorState
        title="Session Expired"
        description="Your tenant authorization has expired. Please refresh your session or sign in again."
        fullPage
      />
    );
  }

  // 4. Lifecycle: Initial Loading of versions
  if (lifecycleState === "loading") {
    return <LoadingState message="Loading value case versions…" fullPage />;
  }

  // 5. Lifecycle: Boundary Error loading versions
  if (lifecycleState === "boundary-error") {
    return (
      <ErrorState
        title="Failed to load value cases"
        description={
          versionsError?.message ??
          "Could not load value case versions for this account."
        }
        error={versionsError ?? undefined}
        onRetry={() => refetchVersions()}
        fullPage
      />
    );
  }

  const handleOpenGenerationPanel = () => {
    setIsPanelOpen(true);
  };

  const handleConfirmGenerate = async (draft: ValueCaseGenerationInputsDraft) => {
    try {
      await generateCase(draft);
      setIsPanelOpen(false);
    } catch {
      // Error handled in journey state
    }
  };

  const handlePublish = (versionId: string) => {
    publishCase(versionId);
  };

  const hasVersions = versionSummaries.length > 0;

  return (
    <div className={className} data-testid="value-case-workspace">
      {/* Live Region for Screen Readers */}
      <div
        className="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {lastMutationMessage}
      </div>

      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <FileText className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              Value Case
            </h2>
            <p className="text-sm text-muted-foreground">
              Generated value narrative and business case for {accountName}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={handleOpenGenerationPanel}
            disabled={isGenerating}
            aria-busy={isGenerating}
          >
            {isGenerating ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : hasVersions ? (
              <RefreshCw className="mr-2 h-4 w-4" />
            ) : (
              <Sparkles className="mr-2 h-4 w-4" />
            )}
            {hasVersions ? "Regenerate" : "Generate Value Case"}
          </Button>
        </div>
      </div>

      {/* Financial Metrics Strip */}
      <ValueCaseMetrics metrics={latestMetricsViewModels} />

      {/* Generation Error Alert */}
      {generateError && (
        <Alert variant="destructive" role="alert">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between gap-4">
            <span>
              <strong>Generation failed:</strong> {generateError.message}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleOpenGenerationPanel}
            >
              Review & Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Publish Error Alert */}
      {publishError && (
        <Alert variant="destructive" role="alert">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between gap-4">
            <span>
              <strong>Publish failed:</strong> {publishError.message}
            </span>
            {selectedVersionId && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePublish(selectedVersionId)}
                disabled={isPublishing}
              >
                Retry Publish
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Empty State */}
      {lifecycleState === "empty" && (
        <SectionCard
          title="No Value Case Artifacts Yet"
          subtitle="Generate an evidence-backed narrative and financial case from your workspace data."
        >
          <div className="rounded-lg border border-dashed border-border p-12 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto text-primary">
              <Sparkles className="h-6 w-6" />
            </div>
            <div className="max-w-md mx-auto space-y-1">
              <h4 className="text-base font-medium text-foreground">
                Ready to generate your first value case
              </h4>
              <p className="text-sm text-muted-foreground">
                We'll assemble your stakeholders, accepted evidence, and ROI calculator outputs into an executive-ready business narrative.
              </p>
            </div>
            <Button onClick={handleOpenGenerationPanel}>
              <Sparkles className="mr-2 h-4 w-4" />
              Generate Value Case
            </Button>
          </div>
        </SectionCard>
      )}

      {/* Ready State: Result Viewer & Version History */}
      {lifecycleState === "ready" && (
        <div className="space-y-6">
          {activeResultViewModel && (
            <ValueCaseResult
              result={activeResultViewModel}
              onPublish={handlePublish}
              isPublishing={isPublishing}
            />
          )}

          <ValueCaseVersionHistory
            versions={versionSummaries}
            selectedVersionId={selectedVersionId}
            onSelectVersion={setSelectedVersionId}
            diff={versionDiff}
          />
        </div>
      )}

      {/* Generation Panel Sheet */}
      <ValueCaseGenerationPanel
        accountName={accountName}
        isOpen={isPanelOpen}
        onClose={() => setIsPanelOpen(false)}
        onGenerate={handleConfirmGenerate}
        isGenerating={isGenerating}
        draft={generationInputsDraft}
        provenance={inputProvenance}
        availability={inputAvailability}
        isLoadingInputs={isLoadingInputs}
        inputsError={inputsError}
      />
    </div>
  );
}
