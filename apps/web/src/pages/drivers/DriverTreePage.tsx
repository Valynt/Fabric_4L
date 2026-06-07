/**
 * DriverTreePage — Driver Tree workspace entry point
 *
 * Route: /drivers/:accountId/:tab?
 *
 * Tabs: Trees | Evidence | Alternatives | Solution Cost
 */
import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import DriverTreeShell from "@/components/workspace/DriverTreeShell";
import { useAccount } from "@/hooks/useAccounts";
import { useAccountHypotheses } from "@/hooks/useHypotheses";
import { useValueTreePaths } from "@/hooks/useValueTrees";
import { useNavigation } from "@/hooks";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { LoadingState, ErrorState, EmptyState } from "@/components/states";
import { EvidenceTabContent } from "@/pages/intelligence/EvidenceTab";
import AlternativesTab from "@/pages/evidence/AlternativesTab";
import SolutionCostTab from "@/pages/evidence/SolutionCostTab";
import { TreePine, ArrowRight } from "lucide-react";
import { useWorkspaceSelectionStore } from "@/stores/workspaceSelectionStore";
import { SectionCard } from "@/components/blocks/SectionCard";
import { Btn } from "@/components/ui/fabric";

export default function DriverTreePage() {
  const params = useParams<{ accountId: string; tab?: string }>();
  const { accountId, tab = "trees" } = params;
  const { navigateTo } = useNavigation();
  const location = useLocation();
  const setSelection = useWorkspaceSelectionStore((state) => state.setSelection);
  const getSelection = useWorkspaceSelectionStore((state) => state.getSelection);
  const { data: account, isLoading: accountLoading } = useAccount(accountId ?? null);
  const { data: hypothesesData, isLoading: hypothesesLoading } = useAccountHypotheses(
    accountId ?? null,
    { status: 'draft' }
  );
  const [selectedTreeId, setSelectedTreeId] = useState<string | null>(null);

  useEffect(() => {
    if (!accountId) return;
    const params = new URLSearchParams(location.search);
    const treeId = params.get("tree_id") || null;
    const valueModelId = params.get("value_model_id") || null;
    if (treeId || valueModelId) {
      setSelection(accountId, { treeId, valueModelId });
      if (treeId) setSelectedTreeId(treeId);
      return;
    }
    const persisted = getSelection(accountId);
    if (persisted.treeId) {
      setSelectedTreeId(persisted.treeId);
    }
  }, [accountId, location.search, getSelection, setSelection]);

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (accountLoading) {
    return <LoadingState message="Loading driver tree…" fullPage />;
  }

  if (!account) {
    return <ErrorState title="Account not found." description="Select a valid account to continue in this workspace." fullPage />;
  }

  const accountName = account?.name ?? "Account";
  const industry = account?.industry ?? "Unknown";
  const revenue = account?.annual_revenue ? `$${account.annual_revenue.toLocaleString()}` : "N/A";

  const hypotheses = hypothesesData?.hypotheses ?? [];
  const selectedHypothesis = hypotheses.find((h) => h.id === selectedTreeId);
  const capabilityId = selectedHypothesis?.capability_id;

  const { data: treePaths, isLoading: pathsLoading } = useValueTreePaths(
    capabilityId,
    { direction: 'upward', maxDepth: 4, enabled: !!capabilityId }
  );

  const TreesTab = () => (
    <div className="space-y-6">
      {hypothesesLoading ? (
        <LoadingState message="Loading driver tree suggestions…" />
      ) : hypotheses.length === 0 ? (
        <EmptyState
          title="No driver tree suggestions"
          description="Promote signals from the Intelligence workspace to generate value hypotheses and driver trees."
          icon={TreePine}
          action={
            <Btn onClick={() => navigateTo('intelligence-signals', { accountId })}>
              Go to Signals
            </Btn>
          }
        />
      ) : (
        <>
          <SectionCard title="Suggested Driver Trees">
            <div className="space-y-3">
              {hypotheses.map((h) => (
                <div
                  key={h.id}
                  className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                    selectedTreeId === h.id
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:bg-muted/50'
                  }`}
                  onClick={() => setSelectedTreeId(h.id)}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-foreground">{h.hypothesis_text}</h4>
                      <p className="text-xs text-muted-foreground mt-1">
                        Value Path: {h.value_path_category ?? 'Unclassified'} · Confidence: {Math.round((h.confidence ?? 0.5) * 100)}%
                      </p>
                    </div>
                    {selectedTreeId === h.id && (
                      <Btn
                        variant="primary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigateTo('calculator', { accountId });
                        }}
                      >
                        Model Impact <ArrowRight size={12} />
                      </Btn>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </SectionCard>

          {selectedTreeId && capabilityId && (
            <SectionCard title="Value Tree Paths">
              {pathsLoading ? (
                <LoadingState message="Loading value tree paths…" />
              ) : !treePaths || treePaths.length === 0 ? (
                <EmptyState
                  title="No value tree paths"
                  description="This capability is not yet linked to any value drivers in the knowledge graph."
                  icon={TreePine}
                />
              ) : (
                <div className="space-y-3">
                  {treePaths.map((path, idx) => (
                    <div key={idx} className="border rounded-lg p-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        {path.nodes.map((node, nIdx) => (
                          <span key={node.id} className="flex items-center gap-2">
                            <span className="px-2 py-1 rounded bg-muted text-xs font-medium">
                              {node.name}
                            </span>
                            {nIdx < path.nodes.length - 1 && (
                              <ArrowRight size={12} className="text-muted-foreground" />
                            )}
                          </span>
                        ))}
                      </div>
                      <p className="vf-text-micro text-muted-foreground mt-1">
                        {path.length} hops · {path.nodes.length} nodes
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>
          )}
        </>
      )}
    </div>
  );

  return (
    <DriverTreeShell accountName={accountName} industry={industry} revenue={revenue}>
      {tab === "trees" && <TreesTab />}
      {tab === "evidence" && <EvidenceTabContent />}
      {tab === "alternatives" && <AlternativesTab />}
      {tab === "solution-cost" && <SolutionCostTab />}
    </DriverTreeShell>
  );
}
