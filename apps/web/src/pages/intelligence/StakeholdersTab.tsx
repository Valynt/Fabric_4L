import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Users, ChevronRight } from "lucide-react";
import IntelligenceShell from "@/components/workspace/IntelligenceShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { useCanonicalCaseId, usePersistWorkspaceTab, useWorkspaceTabQuery } from "@/hooks/useWorkspaceCase";
import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard } from "@/components/ui/fabric";

interface Stakeholder { id: string; name: string; title: string; role: string; priorities: string[]; relevantSignals: string[]; engagementLevel: "high" | "medium" | "low" }

export default function StakeholdersTab() {
  const { accountId } = useParams<{ accountId: string }>();
  const { data: account, isLoading: accountLoading } = useAccount(accountId ?? null);
  const { data: caseId } = useCanonicalCaseId(accountId ?? null);
  const { data, isLoading, error } = useWorkspaceTabQuery<{ stakeholders: Stakeholder[] }>(caseId ?? null, "stakeholders");
  const persistTab = usePersistWorkspaceTab("stakeholders");
  const [selectedStakeholder, setSelectedStakeholder] = useState<Stakeholder | null>(null);
  const [railMode, setRailMode] = useState<RightRailMode>("detail");
  useEffect(() => { if (caseId && data) persistTab.mutate({ caseId, payload: data }); }, [caseId, data]);

  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } = useAgentEvents({ activeTab: "stakeholders", accountName: account?.name ?? "Account", accountId: accountId ?? undefined });
  const stakeholders = data?.stakeholders ?? [];

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (accountLoading || isLoading) return <CenteredLoader message="Loading stakeholders…" />;
  if (error) return <div className="p-6 text-sm text-destructive">Failed to load stakeholders.</div>;

  if (!account) {
    return <div className="p-6 text-sm text-destructive">Account not found.</div>;
  }

  return <IntelligenceShell account={{ accountName: account?.name ?? "Account", industry: account?.industry ?? "Unknown", revenue: account?.annual_revenue ? `$${account.annual_revenue.toLocaleString()}` : "N/A" }} rightRail={<RightRail mode={railMode} onModeChange={setRailMode} activeTab="stakeholders" detailContent={selectedStakeholder ? <div><h3 className="text-sm font-bold">{selectedStakeholder.name}</h3><p className="text-xs text-muted-foreground">{selectedStakeholder.title}</p></div> : null} messages={messages} onSendMessage={sendMessage} suggestedActions={suggestedActions} steps={steps} isStreaming={isStreaming} runMetadata={metadata} />}>
    {persistTab.persistState !== "saved" && (
      <div className="mb-4 rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-xs flex items-center justify-between">
        <span>{persistTab.persistState === "failed" ? "Could not persist stakeholders tab." : "Stakeholders tab has unsaved persistence state."}</span>
        {persistTab.persistState === "failed" && caseId && <button className="underline" onClick={() => persistTab.mutate({ caseId, payload: data ?? { stakeholders: [] } })}>Retry save</button>}
      </div>
    )}
    {stakeholders.length === 0 ? <SectionCard title="Buying Committee"><div className="text-sm text-muted-foreground">No stakeholder mapping exists yet for this case.</div></SectionCard> : <>
      <div className="grid grid-cols-3 gap-4 mb-6"><MetricCard label="Stakeholders" value={String(stakeholders.length)} /><MetricCard label="Economic Buyers" value={String(stakeholders.filter((s) => s.role === "economic").length)} /><MetricCard label="High Engagement" value={String(stakeholders.filter((s) => s.engagementLevel === "high").length)} trendUp /></div>
      <SectionCard title="Buying Committee"><div className="space-y-1">{stakeholders.map((sh) => <button key={sh.id} onClick={() => setSelectedStakeholder(sh)} className={cn("flex items-center gap-4 w-full px-3 py-3 rounded-md text-left", selectedStakeholder?.id === sh.id ? "bg-primary/5" : "hover:bg-muted/50")}><Users size={14} /><div className="flex-1"><div className="text-xs font-medium">{sh.name}</div><div className="vf-text-micro text-muted-foreground">{sh.title}</div></div><span className="vf-text-micro text-muted-foreground capitalize">{sh.engagementLevel}</span><ChevronRight size={12} /></button>)}</div></SectionCard>
    </>}
  </IntelligenceShell>;
}
