import { useMemo } from "react";
import { Loader2 } from "lucide-react";
import {
  useMaturityLadder,
  useStaleTruths,
  useTruthFreshnessSummary,
  useTruths,
} from "@/hooks/useGroundTruthGovernance";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, MetricCard, DataTable } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { LoadingState, ErrorState } from "@/components/states";

export default function GovernanceCompliance() {
  const { data: freshnessSummary, isLoading: isLoadingFreshness } =
    useTruthFreshnessSummary();
  const { data: staleTruths, isLoading: isLoadingStale } = useStaleTruths({
    limit: 50,
  });
  const { data: maturityLadder, isLoading: isLoadingLadder } =
    useMaturityLadder();
  const { data: truths, isLoading: isLoadingTruths } = useTruths({
    limit: 200,
  });

  const maturityCounts = useMemo(() => {
    const counts: Record<number, number> = {};
    for (const truth of truths?.items ?? []) {
      counts[truth.maturity_level] = (counts[truth.maturity_level] ?? 0) + 1;
    }
    return counts;
  }, [truths?.items]);

  const isLoading =
    isLoadingFreshness || isLoadingStale || isLoadingLadder || isLoadingTruths;
  const hasError = !freshnessSummary && !isLoadingFreshness || !staleTruths && !isLoadingStale;

  return (
    <PageShell fullWidth>
      <div className="max-w-6xl">
        <PageHeader
          breadcrumbs={[{ label: "Governance" }, { label: "Compliance" }]}
          title="Compliance"
          subtitle="Maturity, freshness, and stale-truth summaries from Layer 5 governance endpoints."
        />

        {isLoading ? (
          <LoadingState message="Loading compliance summaries…" className="mb-5" />
        ) : hasError ? (
          <ErrorState
            title="Failed to load compliance data"
            description="Some governance summaries could not be retrieved. The Layer 5 service may be degraded."
            className="mb-5"
          />
        ) : (
          <div className="grid gap-3 md:grid-cols-4 mb-5">
            <MetricCard
              label="Fresh truths"
              value={String(freshnessSummary?.summary.fresh ?? 0)}
            />
            <MetricCard
              label="Stale truths"
              value={String(
                freshnessSummary?.summary.stale ?? staleTruths?.items.length ?? 0
              )}
            />
            <MetricCard
              label="Expiring soon"
              value={String(freshnessSummary?.summary.expiring_soon ?? 0)}
            />
            <MetricCard
              label="Total truths"
              value={String(truths?.total ?? freshnessSummary?.summary.total ?? 0)}
            />
          </div>
        )}

        <div className="grid gap-5 lg:grid-cols-2">
          <SectionCard title="Maturity Ladder Coverage" noPad>
            <DataTable<{ key: string; level: number; name: string; status: string; count: number }>
              columns={[
                {
                  key: "level",
                  header: "Level",
                  render: (item) => (
                    <span className="font-semibold">L{item.level}</span>
                  ),
                },
                { key: "name", header: "Name" },
                { key: "status", header: "Required Status" },
                { key: "count", header: "Count" },
              ]}
              data={(maturityLadder?.levels ?? []).map(level => ({
                key: `maturity-${level.level}`,
                level: level.level,
                name: level.name,
                status: level.required_status,
                count: maturityCounts[level.level] ?? 0,
              }))}
              keyExtractor={(item) => String(item.key)}
              emptyMessage="No maturity ladder definition returned"
            />
          </SectionCard>

          <SectionCard
            title={`Stale Truth Objects (${staleTruths?.items.length ?? 0})`}
            noPad
          >
            <DataTable
              columns={[
                { key: "id", header: "Truth ID" },
                { key: "claim", header: "Claim" },
                { key: "status", header: "Status" },
                { key: "maturity", header: "Maturity" },
                { key: "freshness", header: "Freshness" },
              ]}
              data={(staleTruths?.items ?? []).map(truth => ({
                key: truth.id ?? truth.claim,
                id: <span className="font-mono vf-text-caption">{(truth.id ?? '').slice(0, 12)}</span>,
                claim: <span className="line-clamp-2">{truth.claim}</span>,
                status: <span>{truth.status}</span>,
                maturity: <span>L{truth.maturity_level}</span>,
                freshness: (
                  <span className="vf-text-caption text-muted-foreground">
                    {truth.freshness ? new Date(truth.freshness).toLocaleDateString() : (truth.is_stale ? 'Stale' : 'Fresh')}
                  </span>
                ),
              }))}
              keyExtractor={(item) => String(item.key)}
              emptyMessage="No stale truths currently detected"
            />
          </SectionCard>
        </div>
      </div>
    </PageShell>
  );
}
