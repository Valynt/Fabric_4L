import { memo } from "react";
import { GitCompare, History } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SectionCard } from "@/components/blocks/SectionCard";
import type {
  ValueCaseVersionSummaryViewModel,
  ValueCaseVersionDiffViewModel,
} from "../presentation/valueCaseViewModels";

export interface ValueCaseVersionHistoryProps {
  versions: ValueCaseVersionSummaryViewModel[];
  selectedVersionId: string | null;
  onSelectVersion: (versionId: string) => void;
  diff: ValueCaseVersionDiffViewModel | null;
}

export const ValueCaseVersionHistory = memo(function ValueCaseVersionHistory({
  versions,
  selectedVersionId,
  onSelectVersion,
  diff,
}: ValueCaseVersionHistoryProps) {
  if (versions.length === 0) {
    return (
      <SectionCard
        title="Value Case Versions"
        subtitle="Generated artifacts are versioned for iterative business case refinement."
      >
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <History className="mx-auto h-8 w-8 text-muted-foreground/60 mb-2" />
          <p className="text-sm text-muted-foreground">
            No prior versions yet. Generate your first value case artifact.
          </p>
        </div>
      </SectionCard>
    );
  }

  const selectedVersion = versions.find(v => v.id === selectedVersionId);

  return (
    <SectionCard
      title="Value Case Versions"
      subtitle="Generated artifacts are versioned for iterative business case refinement."
    >
      <div className="space-y-4">
        {/* Version Pills */}
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Version selection">
          {versions.map(version => {
            const isSelected = version.id === selectedVersionId;
            return (
              <Button
                key={version.id}
                variant={isSelected ? "default" : "outline"}
                size="sm"
                onClick={() => onSelectVersion(version.id)}
                aria-pressed={isSelected}
                className="gap-1.5"
              >
                <span>{version.label}</span>
                {version.isPublished && (
                  <Badge
                    variant={isSelected ? "secondary" : "default"}
                    className="text-[10px] px-1 py-0 h-4"
                  >
                    Published
                  </Badge>
                )}
              </Button>
            );
          })}
        </div>

        {/* Selected Version Overview */}
        {selectedVersion && (
          <div className="rounded-lg border border-border p-4 space-y-1.5 bg-card/50">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs text-muted-foreground font-medium">
                Created {selectedVersion.createdAtFormatted}
              </p>
              <span className="text-xs text-muted-foreground">
                Status: {selectedVersion.statusLabel}
              </span>
            </div>
            <p className="text-sm font-semibold text-foreground">
              {selectedVersion.title}
            </p>
            <p className="text-xs text-muted-foreground line-clamp-2">
              {selectedVersion.summary}
            </p>
          </div>
        )}

        {/* Version Diff Section */}
        <div className="rounded-lg border border-border p-4 space-y-2.5 bg-muted/20">
          <p className="text-sm font-medium text-foreground flex items-center gap-2">
            <GitCompare className="h-4 w-4 text-primary" />
            <span>Version Comparison</span>
          </p>

          {!diff ? (
            <p className="text-xs text-muted-foreground">
              Select a newer version to see diffs from prior output.
            </p>
          ) : (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                Comparing v{diff.priorVersion} → v{diff.currentVersion}:
              </p>
              <ul className="text-xs text-muted-foreground space-y-1 list-disc pl-5">
                <li>
                  <span className="font-medium text-foreground">ROI:</span> {diff.roiDiff}
                </li>
                <li>
                  <span className="font-medium text-foreground">Payback:</span> {diff.paybackDiff}
                </li>
                <li>
                  <span className="font-medium text-foreground">3-Year Value:</span> {diff.valueDiff}
                </li>
                <li>
                  <span className="font-medium text-foreground">Risk Factors:</span> {diff.risksCountDiff}
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </SectionCard>
  );
});
