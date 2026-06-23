/**
 * Version History Panel - Displays formula version history and governance metadata
 */
import { Skeleton } from "@/components/ui/skeleton";
import { useFormulaVersions, useFormulaGovernance, type FormulaVersion } from "@/hooks/useFormulaVersions";
import { formatRelativeTime } from "@/lib/formatters";

const VERSION_STATUS_COLOR: Record<string, string> = {
  active: "bg-success/10 text-success",
  approved: "bg-primary/10 text-primary",
  draft: "bg-muted/30 text-muted-foreground",
  under_review: "bg-warning/10 text-warning",
  deprecated: "bg-destructive/10 text-destructive",
  retired: "bg-muted text-muted-foreground",
};

interface VersionHistoryPanelProps {
  formulaId: string;
}

export function VersionHistoryPanel({ formulaId }: VersionHistoryPanelProps) {
  const { data: versions, isLoading } = useFormulaVersions(formulaId);
  const { data: governance } = useFormulaGovernance(formulaId);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-14 w-full" />)}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {governance && (
        <div className="p-3 bg-secondary/30 rounded-lg vf-text-body-s space-y-1">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Owner</span>
            <span className="font-medium">{governance.owner || "Unassigned"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Review Cycle</span>
            <span className="font-medium">{governance.review_cycle_days} days</span>
          </div>
          {governance.next_review_at && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Next Review</span>
              <span className="font-medium">{formatRelativeTime(governance.next_review_at)}</span>
            </div>
          )}
        </div>
      )}
      <div className="space-y-1.5">
        {(versions || []).map((v: FormulaVersion) => (
          <div
            key={v.version}
            className="flex items-center gap-3 p-2.5 rounded-md hover:bg-secondary/30 transition-colors"
          >
            <div className="w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="vf-text-body-s font-mono font-semibold">v{v.version}</span>
                <span className={`vf-text-micro px-1.5 py-0.5 rounded-full ${VERSION_STATUS_COLOR[v.status] || "bg-muted/30 text-muted-foreground"}`}>
                  {v.status}
                </span>
              </div>
              <div className="vf-text-caption text-muted-foreground truncate">{v.change_summary}</div>
              <div className="vf-text-micro text-muted-foreground/60">
                {v.created_by} &middot; {formatRelativeTime(v.created_at)}
              </div>
            </div>
          </div>
        ))}
        {(!versions || versions.length === 0) && (
          <div className="vf-text-body-s text-muted-foreground text-center py-4">No version history</div>
        )}
      </div>
    </div>
  );
}
