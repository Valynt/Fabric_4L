import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { FileText, CheckCircle2, AlertCircle, ChevronRight, Link2, XCircle } from "lucide-react";
import IntelligenceShell from "@/components/workspace/IntelligenceShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { ErrorState } from "@/components/states/ErrorState";
import { useAttachEvidenceToDriverMutation, useCanonicalCaseId, useEvidenceDecisionMutation, usePersistWorkspaceTab, useValidateEvidenceClaim, useWorkspaceTabQuery } from "@/hooks/useWorkspaceCase";
import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard, Btn } from "@/components/ui/fabric";

type VerificationState = "verified" | "partial" | "unverified";
interface EvidenceItem { id: string; title: string; type: string; source: string; matchScore: number; verification: VerificationState; linkedSignals: string[]; excerpt: string }
const VERIFICATION_CONFIG: Record<VerificationState, { icon: typeof CheckCircle2; color: string }> = { verified: { icon: CheckCircle2, color: "text-success" }, partial: { icon: AlertCircle, color: "text-warning" }, unverified: { icon: AlertCircle, color: "text-muted-foreground" } };

function useEvidenceTabState() {
  const { accountId } = useParams<{ accountId: string }>();
  const { data: account, isLoading: accountLoading } = useAccount(accountId ?? null);
  const { data: caseId } = useCanonicalCaseId(accountId ?? null);
  const { data, isLoading, error } = useWorkspaceTabQuery<{ evidence: EvidenceItem[] }>(caseId ?? null, "evidence");
  const persistTab = usePersistWorkspaceTab("evidence");
  const validateClaim = useValidateEvidenceClaim();
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);
  const [railMode, setRailMode] = useState<RightRailMode>("detail");
  const [pendingDecisions, setPendingDecisions] = useState<Record<string, "accepted" | "rejected">>({});
  const [actionError, setActionError] = useState<string | null>(null);
  const evidenceDecision = useEvidenceDecisionMutation();
  const attachDriver = useAttachEvidenceToDriverMutation();

  useEffect(() => { if (caseId && data) persistTab.mutate({ caseId, payload: data }); }, [caseId, data]);

  const evidence = data?.evidence ?? [];
  const verified = useMemo(() => evidence.filter((e) => e.verification === "verified").length, [evidence]);
  const avgMatch = evidence.length ? Math.round(evidence.reduce((s, e) => s + e.matchScore, 0) / evidence.length) : 0;

  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } = useAgentEvents({ activeTab: "evidence", accountName: account?.name ?? "Account", accountId: accountId ?? undefined });

  return {
    account, accountLoading, caseId, evidence, isLoading, error, verified, avgMatch,
    selectedEvidence, setSelectedEvidence, railMode, setRailMode,
    messages, sendMessage, suggestedActions, steps, isStreaming, metadata,
    validateClaim, pendingDecisions, setPendingDecisions, actionError, setActionError, evidenceDecision, attachDriver,
  };
}

export function EvidenceTabContent() {
  const { accountId } = useParams<{ accountId: string }>();
  const {
    evidence, isLoading, error, verified, avgMatch,
    selectedEvidence, setSelectedEvidence, pendingDecisions, setPendingDecisions, actionError, setActionError, evidenceDecision, attachDriver, caseId,
  } = useEvidenceTabState();

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (isLoading) return <CenteredLoader message="Loading evidence…" />;
  if (error) return <ErrorState title="Failed to load evidence" description="The evidence data could not be retrieved." error={error} fullPage />;

  return (
    <>
      {actionError && <div className="mb-3 text-xs text-destructive">{actionError}</div>}
      {evidence.length === 0 ? (
        <SectionCard title="Evidence Library">
          <div className="text-sm text-muted-foreground">No evidence has been returned for this case.</div>
        </SectionCard>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <MetricCard label="Evidence Items" value={String(evidence.length)} trend={`${verified} verified`} />
            <MetricCard label="Avg Match Score" value={`${avgMatch}%`} />
            <MetricCard label="Source Types" value={String(new Set(evidence.map((e) => e.type)).size)} />
          </div>
          <SectionCard title="Evidence Library">
            <div className="space-y-1">
              {evidence.map((item) => {
                const vc = VERIFICATION_CONFIG[item.verification];
                const Icon = vc.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => setSelectedEvidence(item)}
                    className={cn(
                      "flex items-center gap-4 w-full px-3 py-3 rounded-md text-left",
                      selectedEvidence?.id === item.id ? "bg-primary/5" : "hover:bg-muted/50"
                    )}
                  >
                    <FileText size={14} />
                    <div className="flex-1">
                      <div className="text-xs font-medium">{item.title}</div>
                      <div className="vf-text-micro text-muted-foreground">{item.linkedSignals.join(" · ")}</div>
                    </div>
                    <span className={cn("flex items-center gap-1 vf-text-micro font-semibold", vc.color)}>
                      <Icon size={10} />{pendingDecisions[item.id] ? `${pendingDecisions[item.id]}` : `${item.matchScore}%`}
                    </span>
                    <ChevronRight size={12} />
                  </button>
                );
              })}
            </div>
          </SectionCard>
        </>
      )}
    </>
  );
}

export default function EvidenceTab() {
  const {
    account, accountLoading, selectedEvidence, railMode, setRailMode,
    messages, sendMessage, suggestedActions, steps, isStreaming, metadata,
    caseId, setPendingDecisions, setActionError, evidenceDecision, attachDriver,
  } = useEvidenceTabState();

  const { accountId } = useParams<{ accountId: string }>();

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (accountLoading) {
    return <CenteredLoader message="Loading evidence…" />;
  }

  if (!account) {
    return <ErrorState title="Account not found" description="Select a valid account to continue in this workspace." fullPage />;
  }

  return (
    <IntelligenceShell
      account={{
        accountName: account?.name ?? "Account",
        industry: account?.industry ?? "Unknown",
        revenue: account?.annual_revenue ? `$${account.annual_revenue.toLocaleString()}` : "N/A",
      }}
      rightRail={
        <RightRail
          mode={railMode}
          onModeChange={setRailMode}
          activeTab="evidence"
          detailContent={
            selectedEvidence ? (
              <div className="space-y-2">
                <h3 className="text-sm font-bold">{selectedEvidence.title}</h3>
                <p className="text-xs text-muted-foreground">{selectedEvidence.excerpt}</p>
                <div className="grid grid-cols-3 gap-2 pt-2">
                  <Btn variant="primary" onClick={async () => {
                    if (!accountId || !caseId) return;
                    setActionError(null);
                    setPendingDecisions((p) => ({ ...p, [selectedEvidence.id]: "accepted" }));
                    try { await evidenceDecision.mutateAsync({ evidenceId: selectedEvidence.id, accountId, caseId, decision: "accepted" }); } catch { setActionError("Failed to accept evidence. Retry."); }
                  }}><CheckCircle2 size={12} />Accept</Btn>
                  <Btn variant="outline" onClick={async () => {
                    if (!accountId || !caseId) return;
                    setActionError(null);
                    setPendingDecisions((p) => ({ ...p, [selectedEvidence.id]: "rejected" }));
                    try { await evidenceDecision.mutateAsync({ evidenceId: selectedEvidence.id, accountId, caseId, decision: "rejected" }); } catch { setActionError("Failed to reject evidence. Retry."); }
                  }}><XCircle size={12} />Reject</Btn>
                  <Btn variant="ghost" onClick={async () => {
                    if (!accountId || !caseId) return;
                    setActionError(null);
                    try { await attachDriver.mutateAsync({ evidenceId: selectedEvidence.id, driverId: selectedEvidence.linkedSignals[0] ?? "", accountId, caseId }); } catch { setActionError("Failed to attach evidence to driver. Retry."); }
                  }}><Link2 size={12} />Attach</Btn>
                </div>
              </div>
            ) : null
          }
          messages={messages}
          onSendMessage={sendMessage}
          suggestedActions={suggestedActions}
          steps={steps}
          isStreaming={isStreaming}
          runMetadata={metadata}
        />
      }
    >
      <EvidenceTabContent />
    </IntelligenceShell>
  );
}
