import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { FileText, CheckCircle2, AlertCircle, ChevronRight } from "lucide-react";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { ErrorState } from "@/components/states/ErrorState";
import { useCanonicalCaseId, useWorkspaceTabQuery } from "@/hooks/useWorkspaceCase";
import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard } from "@/components/ui/fabric";

type VerificationState = "verified" | "partial" | "unverified";
interface EvidenceItem {
  id: string;
  title: string;
  type: string;
  source: string;
  matchScore: number;
  verification: VerificationState;
  linkedSignals: string[];
  excerpt: string;
}

const VERIFICATION_CONFIG: Record<VerificationState, { icon: typeof CheckCircle2; color: string }> = {
  verified: { icon: CheckCircle2, color: "text-success" },
  partial: { icon: AlertCircle, color: "text-warning" },
  unverified: { icon: AlertCircle, color: "text-muted-foreground" },
};

function useEvidenceTabState() {
  const { accountId } = useParams<{ accountId: string }>();
  const { data: caseId } = useCanonicalCaseId(accountId ?? null);
  const { data, isLoading, error } = useWorkspaceTabQuery<{ evidence: EvidenceItem[] }>(caseId ?? null, "evidence");
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);

  const evidence = useMemo(() => data?.evidence ?? [], [data]);
  const verified = useMemo(() => evidence.filter((e) => e.verification === "verified").length, [evidence]);
  const avgMatch = evidence.length ? Math.round(evidence.reduce((s, e) => s + e.matchScore, 0) / evidence.length) : 0;

  return { evidence, isLoading, error, verified, avgMatch, selectedEvidence, setSelectedEvidence };
}

export function EvidenceTabContent() {
  const { accountId } = useParams<{ accountId: string }>();
  const { evidence, isLoading, error, verified, avgMatch, selectedEvidence, setSelectedEvidence } = useEvidenceTabState();

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (isLoading) return <CenteredLoader message="Loading evidence…" />;
  if (error) return <ErrorState title="Failed to load evidence" description="The evidence data could not be retrieved." error={error} fullPage />;

  return (
    <>
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
                      <Icon size={10} />
                      {item.matchScore}%
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

export default EvidenceTabContent;
