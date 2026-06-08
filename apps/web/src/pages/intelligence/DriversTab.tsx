import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { GitBranch, ChevronRight } from "lucide-react";
import IntelligenceShell from "@/components/workspace/IntelligenceShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { ErrorState } from "@/components/states/ErrorState";
import { useCanonicalCaseId, usePersistWorkspaceTab, useWorkspaceTabQuery } from "@/hooks/useWorkspaceCase";
import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard } from "@/components/ui/fabric";

interface Driver { id: string; name: string; contribution: number; parentSignal: string; subDrivers: string[] }

export default function DriversTab() {
  const { accountId } = useParams<{ accountId: string }>();
  const { data: account, isLoading: accountLoading } = useAccount(accountId ?? null);
  const { data: caseId } = useCanonicalCaseId(accountId ?? null);
  const { data, isLoading, error } = useWorkspaceTabQuery<{ drivers: Driver[] }>(caseId ?? null, "drivers");
  const persistTab = usePersistWorkspaceTab("drivers");
  const [selectedDriver, setSelectedDriver] = useState<Driver | null>(null);
  const [railMode, setRailMode] = useState<RightRailMode>("detail");
  useEffect(() => { if (caseId && data) persistTab.mutate({ caseId, payload: data }); }, [caseId, data]);

  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } = useAgentEvents({ activeTab: "drivers", accountName: account?.name ?? "Account", accountId: accountId ?? undefined });
  const drivers = data?.drivers ?? [];
  const grouped = useMemo(() => drivers.reduce<Record<string, Driver[]>>((acc, d) => { (acc[d.parentSignal] ??= []).push(d); return acc; }, {}), [drivers]);

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (accountLoading || isLoading) return <CenteredLoader message="Loading drivers…" />;
  if (error) return <ErrorState title="Failed to load drivers" description="The driver data could not be retrieved." error={error} fullPage />;

  if (!account) {
    return <ErrorState title="Account not found" description="Select a valid account to continue in this workspace." fullPage />;
  }

  return <IntelligenceShell account={{ accountName: account?.name ?? "Account", industry: account?.industry ?? "Unknown", revenue: account?.annual_revenue ? `$${account.annual_revenue.toLocaleString()}` : "N/A" }} rightRail={<RightRail mode={railMode} onModeChange={setRailMode} activeTab="drivers" detailContent={selectedDriver ? <div className="space-y-3"><h3 className="text-sm font-bold">{selectedDriver.name}</h3><p className="text-xs text-muted-foreground">{selectedDriver.parentSignal}</p></div> : null} messages={messages} onSendMessage={sendMessage} suggestedActions={suggestedActions} steps={steps} isStreaming={isStreaming} runMetadata={metadata} />}>
    {persistTab.persistState !== "saved" && (
      <div className="mb-4 rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-xs flex items-center justify-between">
        <span>{persistTab.persistState === "failed" ? "Could not persist drivers tab." : "Drivers tab has unsaved persistence state."}</span>
        {persistTab.persistState === "failed" && caseId && <button className="underline" onClick={() => persistTab.mutate({ caseId, payload: data ?? { drivers: [] } })}>Retry save</button>}
      </div>
    )}
    {drivers.length === 0 ? <SectionCard title="Root Drivers"><div className="text-sm text-muted-foreground">No root-driver output available yet for this case.</div></SectionCard> : <>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <MetricCard label="Root Drivers" value={String(drivers.length)} />
        <MetricCard label="Top Contributor" value={`${Math.max(...drivers.map((d) => d.contribution))}%`} />
        <MetricCard label="Signals Analyzed" value={String(Object.keys(grouped).length)} />
      </div>
      {Object.entries(grouped).map(([signal, list]) => <SectionCard key={signal} title={signal} className="mb-4"><div className="space-y-1">{list.map((driver) => <button key={driver.id} onClick={() => setSelectedDriver(driver)} className={cn("flex items-center gap-4 w-full px-3 py-3 rounded-md text-left", selectedDriver?.id === driver.id ? "bg-primary/5" : "hover:bg-muted/50")}><GitBranch size={14} /><div className="flex-1"><div className="text-xs font-medium">{driver.name}</div><div className="vf-text-micro text-muted-foreground">{driver.subDrivers.join(" · ")}</div></div><span className="text-xs">{driver.contribution}%</span><ChevronRight size={12} /></button>)}</div></SectionCard>)}
    </>}
  </IntelligenceShell>;
}
