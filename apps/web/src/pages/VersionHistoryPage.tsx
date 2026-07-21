import { useState } from "react";
import { useParams } from "react-router-dom";
import { GitCompare, RotateCcw, Plus, Calendar } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { useSnapshots, useCreateSnapshot, useSnapshotDiff } from "@/hooks/useVersioning";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";

export default function VersionHistoryPage() {
  const { accountId: paramAccountId } = useParams<{ accountId: string }>();
  const selectedAccountId = useAccountContextStore((s) => s.selectedAccountId);
  const accountId = paramAccountId || selectedAccountId;
  const [compareBase, setCompareBase] = useState<string | null>(null);

  const { data: snapshots, isLoading, error, refetch } = useSnapshots(accountId);
  const createSnapshot = useCreateSnapshot();
  const diffMutation = useSnapshotDiff();

  if (!accountId) {
    return (
      <PageShell>
        <PageHeader title="Version History" />
        <div className="rounded-lg border border-warning/20 bg-warning/5 p-4 text-warning">
          No account selected. Please select an account to view version history.
        </div>
      </PageShell>
    );
  }

  if (isLoading) {
    return (
      <PageShell>
        <PageHeader title="Version History" subtitle={`Account: ${accountId}`} />
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState
          title="Failed to load version history"
          description="Snapshots could not be retrieved. The versioning service may be degraded."
          error={error}
          onRetry={refetch}
          retryLabel="Retry"
        />
      </PageShell>
    );
  }

  const handleCreate = () => {
    createSnapshot.mutate({ accountId, label: `Manual snapshot ${new Date().toLocaleString()}` });
  };

  const handleCompare = (snapshotId: string) => {
    if (!compareBase) {
      setCompareBase(snapshotId);
      return;
    }
    if (compareBase === snapshotId) {
      setCompareBase(null);
      return;
    }
    diffMutation.mutate({ accountId, baseId: compareBase, compareId: snapshotId });
    setCompareBase(null);
  };

  return (
    <PageShell>
      <PageHeader title="Version History" subtitle={`Account: ${accountId}`} />

      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {snapshots?.length ?? 0} snapshot{(snapshots?.length ?? 0) !== 1 ? "s" : ""}
        </p>
        <button type="button"
          onClick={handleCreate}
          disabled={createSnapshot.isPending}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          Create Snapshot
        </button>
      </div>

      {diffMutation.data && (
        <SectionCard title="Diff Results" className="mb-4">
          <div className="text-sm space-y-2">
            <p className="text-muted-foreground">
              Comparing {diffMutation.data.base_snapshot_id} → {diffMutation.data.compare_snapshot_id}
            </p>
            {diffMutation.data.changes.length === 0 ? (
              <p>No changes detected between snapshots.</p>
            ) : (
              <ul className="space-y-1">
                {diffMutation.data.changes.map((c) => (
                  <li key={c.field} className="rounded bg-muted p-2">
                    <span className="font-medium">{c.field}:</span>{" "}
                    {JSON.stringify(c.from)} → {JSON.stringify(c.to)}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </SectionCard>
      )}

      <div className="space-y-3">
        {snapshots?.map((snapshot) => (
          <SectionCard key={snapshot.id} title={snapshot.label || "Untitled Snapshot"}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>{new Date(snapshot.created_at).toLocaleString()}</span>
                <span className="rounded bg-secondary px-2 py-0.5 text-xs">{snapshot.snapshot_type}</span>
              </div>
              <div className="flex items-center gap-2">
                <button type="button"
                  onClick={() => handleCompare(snapshot.id)}
                  className={`inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-medium ${
                    compareBase === snapshot.id
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary hover:bg-secondary/80"
                  }`}
                >
                  <GitCompare className="h-3 w-3" />
                  {compareBase === snapshot.id ? "Selected" : "Compare"}
                </button>
                <button type="button"
                  onClick={() => { /* restore not wired in this demo */ }}
                  className="inline-flex items-center gap-1 rounded-md bg-secondary px-3 py-1.5 text-xs font-medium hover:bg-secondary/80"
                >
                  <RotateCcw className="h-3 w-3" />
                  Restore
                </button>
              </div>
            </div>
          </SectionCard>
        ))}

        {(!snapshots || snapshots.length === 0) && (
          <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            No snapshots yet. Create a snapshot to preserve the current account state.
          </div>
        )}
      </div>
    </PageShell>
  );
}
