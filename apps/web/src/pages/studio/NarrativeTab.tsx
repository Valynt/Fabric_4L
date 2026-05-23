/**
 * Narrative Tab — Enhanced with DIL hooks
 *
 * Primary data: workspace case narratives (existing)
 * DIL enrichment: DIL Narrative Builder for tone/audience-specific generation
 */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Users,
  Download,
  Mail,
  Eye,
  RefreshCw,
  FileText,
  Sparkles,
} from "lucide-react";
import ValueStudioShellComponent from "@/components/workspace/ValueStudioShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { cn } from "@/lib/utils";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import {
  useCanonicalCaseId,
  usePersistWorkspaceTab,
  useWorkspaceTabQuery,
  useGenerateWorkspaceIntelligence,
} from "@/hooks/useWorkspaceCase";

// DIL hooks
import {
  useNarratives,
  useGenerateNarrative,
  type Narrative,
  type NarrativeListResponse,
  type NarrativeTone,
  type NarrativeAudience,
} from "@/hooks/useNarratives";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard, Btn } from "@/components/ui/fabric";

// ── Types ──────────────────────────────────────────────────────────────────────
interface NarrativeVersion {
  id: string;
  stakeholder: string;
  role: string;
  status: "ready" | "draft" | "generating";
  headline: string;
  summary: string;
  keyMetrics: { label: string; value: string }[];
  lastUpdated: string;
}

const STATUS_CONFIG: Record<
  NarrativeVersion["status"],
  { label: string; color: string; bg: string }
> = {
  ready: { label: "Ready", color: "text-green-600", bg: "bg-green-500" },
  draft: { label: "Draft", color: "text-orange-600", bg: "bg-orange-500" },
  generating: {
    label: "Generating",
    color: "text-blue-600",
    bg: "bg-blue-500",
  },
};

const DIL_STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  draft: { label: "Draft", color: "text-muted-foreground", bg: "bg-muted" },
  review: { label: "Review", color: "text-orange-600", bg: "bg-orange-500" },
  approved: { label: "Approved", color: "text-green-600", bg: "bg-green-500" },
  delivered: { label: "Delivered", color: "text-blue-600", bg: "bg-blue-500" },
};

const TONE_OPTIONS = ["executive", "technical", "financial", "consultative"] as const;
const AUDIENCE_OPTIONS = [
  "c_suite",
  "vp_director",
  "technical_buyer",
  "champion",
  "evaluation_committee",
] as const;

// ── DIL Narrative Card ─────────────────────────────────────────────────────────
function DILNarrativeCard({
  narrative,
  selected,
  onClick,
}: {
  narrative: Narrative;
  selected: boolean;
  onClick: () => void;
}) {
  const sc = DIL_STATUS_CONFIG[narrative.status] ?? DIL_STATUS_CONFIG.draft;
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-4 w-full px-3 py-3 rounded-md text-left",
        selected ? "bg-primary/5 ring-1 ring-primary/20" : "hover:bg-muted/50"
      )}
    >
      <FileText size={14} className="text-primary shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex gap-2 items-center">
          <span className="text-xs font-medium truncate">
            {narrative.title}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded font-semibold shrink-0">
            DIL
          </span>
        </div>
        <div className="text-[10px] text-muted-foreground">
          {narrative.tone} · {narrative.audience}
        </div>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <div className={cn("w-1.5 h-1.5 rounded-full", sc.bg)} />
        <span className={cn("text-[10px] font-semibold", sc.color)}>
          {sc.label}
        </span>
      </div>
    </button>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────
export default function NarrativeTab() {
  const { accountId } = useParams<{ accountId: string }>();
  const { data: account, isLoading: accountLoading } = useAccount(accountId ?? null);
  const { data: caseId } = useCanonicalCaseId(accountId ?? null);
  const { data, isLoading, error } = useWorkspaceTabQuery<{
    narratives: NarrativeVersion[];
  }>(caseId ?? null, "narrative");
  const persistTab = usePersistWorkspaceTab("narrative");
  const [selectedNarrative, setSelectedNarrative] =
    useState<NarrativeVersion | null>(null);
  const [selectedDIL, setSelectedDIL] = useState<Narrative | null>(null);
  const [railMode, setRailMode] = useState<RightRailMode>("detail");
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [genTone, setGenTone] = useState<string>("executive");
  const [genAudience, setGenAudience] = useState<string>("c_suite");

  // DIL data
  const { data: dilNarratives } = useNarratives({ account_id: accountId ?? undefined });
  const generateDIL = useGenerateNarrative();

  useEffect(() => {
    if (caseId && data) persistTab.mutate({ caseId, payload: data });
  }, [caseId, data]);

  const narratives = data?.narratives ?? [];
  const dilListResponse = dilNarratives as NarrativeListResponse | undefined;
  const dilList = dilListResponse?.narratives ?? [];

  useEffect(() => {
    if (!selectedNarrative && !selectedDIL && narratives[0])
      setSelectedNarrative(narratives[0]);
  }, [narratives, selectedNarrative, selectedDIL]);

  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } = useAgentEvents({
    activeTab: "narrative",
    accountName: account?.name ?? "Account",
  });

  const generateMutation = useGenerateWorkspaceIntelligence();

  useEffect(() => {
    if (
      caseId &&
      narratives.length === 0 &&
      !isLoading &&
      !generateMutation.isPending
    ) {
      generateMutation.mutate(caseId);
    }
  }, [caseId, narratives.length, isLoading]);

  const handleGenerateDIL = () => {
    if (!accountId) return;
    generateDIL.mutate(
      {
        account_id: accountId,
        tone: genTone as NarrativeTone,
        audience: genAudience as NarrativeAudience,
        sections: [
          "executive_summary",
          "pain_points",
          "value_hypotheses",
          "roi_projection",
          "evidence",
          "next_steps",
        ],
      },
      {
        onSuccess: () => setShowGenerateForm(false),
      }
    );
  };

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (accountLoading || isLoading || generateMutation.isPending) {
    return (
      <CenteredLoader
        message={
          generateMutation.isPending
            ? "Generating narratives..."
            : "Loading narratives…"
        }
      />
    );
  }
  if (error || generateMutation.isError) {
    return (
      <div className="p-6 text-sm text-destructive">
        Failed to load narratives.
      </div>
    );
  }

  if (!account) {
    return <div className="p-6 text-sm text-destructive">Account not found.</div>;
  }

  const readyCount = narratives.filter((n) => n.status === "ready").length;
  const selectedStatus = selectedNarrative
    ? STATUS_CONFIG[selectedNarrative.status]
    : null;

  return (
    <ValueStudioShellComponent
      account={{
        accountName: account?.name ?? "Account",
        industry: account?.industry ?? "Unknown",
        revenue: account?.annual_revenue
          ? `$${account.annual_revenue.toLocaleString()}`
          : "N/A",
      }}
      rightRail={
        <RightRail
          mode={railMode}
          onModeChange={setRailMode}
          detailContent={
            selectedNarrative ? (
              <div className="space-y-3">
                <h3 className="text-sm font-bold">
                  {selectedNarrative.stakeholder}
                </h3>
                <p className="text-xs text-muted-foreground">
                  {selectedNarrative.role}
                </p>
                {selectedStatus && (
                  <span
                    className={cn(
                      "text-[10px] font-semibold",
                      selectedStatus.color
                    )}
                  >
                    {selectedStatus.label}
                  </span>
                )}
              </div>
            ) : selectedDIL ? (
              <div className="space-y-3">
                <h3 className="text-sm font-bold">{selectedDIL.title}</h3>
                <p className="text-xs text-muted-foreground">
                  {selectedDIL.tone} · {selectedDIL.audience}
                </p>
                <span
                  className={cn(
                    "text-[10px] font-semibold",
                    DIL_STATUS_CONFIG[selectedDIL.status]?.color ?? "text-gray-600"
                  )}
                >
                  {DIL_STATUS_CONFIG[selectedDIL.status]?.label ?? selectedDIL.status}
                </span>
              </div>
            ) : null
          }
          activeTab="narrative"
          messages={messages}
          onSendMessage={sendMessage}
          suggestedActions={suggestedActions}
            steps={steps}
            isStreaming={isStreaming}
            runMetadata={metadata}
        />
      }
    >
      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard
          label="Workspace Narratives"
          value={String(narratives.length)}
        />
        <MetricCard
          label="Ready to Send"
          value={String(readyCount)}
          trend={`Of ${narratives.length}`}
        />
        <MetricCard
          label="DIL Narratives"
          value={String(dilList.length)}
          trend="From Narrative Builder"
        />
        <MetricCard
          label="Buying Committee"
          value={`${new Set(narratives.map((n) => n.stakeholder)).size} members`}
        />
      </div>

      {/* DIL Generate Form */}
      {showGenerateForm && (
        <SectionCard title="Generate DIL Narrative" className="mb-4">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={13} className="text-primary" />
            <span className="text-[11px] text-muted-foreground">
              Generate a narrative using the DIL Narrative Builder engine
            </span>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-3">
            <div>
              <label className="text-[11px] font-medium block mb-1">Tone</label>
              <select
                value={genTone}
                onChange={(e) => setGenTone(e.target.value)}
                className="w-full text-xs border border-border rounded-md px-2 py-1.5"
              >
                {TONE_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[11px] font-medium block mb-1">
                Audience
              </label>
              <select
                value={genAudience}
                onChange={(e) => setGenAudience(e.target.value)}
                className="w-full text-xs border border-border rounded-md px-2 py-1.5"
              >
                {AUDIENCE_OPTIONS.map((a) => (
                  <option key={a} value={a}>
                    {a.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <Btn
              variant="primary"
              onClick={handleGenerateDIL}
              disabled={generateDIL.isPending}
            >
              {generateDIL.isPending ? "Generating..." : "Generate"}
            </Btn>
            <Btn variant="outline" onClick={() => setShowGenerateForm(false)}>
              Cancel
            </Btn>
          </div>
        </SectionCard>
      )}

      {/* DIL Narratives */}
      {dilList.length > 0 && (
        <SectionCard title="DIL Narratives" className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Sparkles size={13} className="text-primary" />
              <span className="text-[11px] text-muted-foreground">
                Generated by the DIL Narrative Builder
              </span>
            </div>
            {!showGenerateForm && (
              <Btn
                variant="outline"
                className="text-[10px]"
                onClick={() => setShowGenerateForm(true)}
              >
                + New DIL Narrative
              </Btn>
            )}
          </div>
          <div className="space-y-1">
            {dilList.map((n) => (
              <DILNarrativeCard
                key={n.id}
                narrative={n}
                selected={selectedDIL?.id === n.id}
                onClick={() => {
                  setSelectedDIL(n);
                  setSelectedNarrative(null);
                }}
              />
            ))}
          </div>
        </SectionCard>
      )}

      {/* Workspace Narratives (existing) */}
      {narratives.length === 0 && dilList.length === 0 ? (
        <SectionCard title="Stakeholder Narratives">
          <div className="text-sm text-muted-foreground">
            No narrative output available yet for this case.
          </div>
          {!showGenerateForm && (
            <Btn
              variant="primary"
              className="mt-3 gap-1.5"
              onClick={() => setShowGenerateForm(true)}
            >
              <Sparkles size={12} />
              Generate DIL Narrative
            </Btn>
          )}
        </SectionCard>
      ) : narratives.length > 0 ? (
        <SectionCard title="Stakeholder Narratives">
          <div className="space-y-1">
            {narratives.map((narrative) => {
              const sc = STATUS_CONFIG[narrative.status];
              return (
                <button
                  key={narrative.id}
                  onClick={() => {
                    setSelectedNarrative(narrative);
                    setSelectedDIL(null);
                  }}
                  className={cn(
                    "flex items-center gap-4 w-full px-3 py-3 rounded-md text-left",
                    selectedNarrative?.id === narrative.id
                      ? "bg-primary/5"
                      : "hover:bg-muted/50"
                  )}
                >
                  <Users size={14} />
                  <div className="flex-1">
                    <div className="flex gap-2">
                      <span className="text-xs font-medium">
                        {narrative.stakeholder}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {narrative.role}
                      </span>
                    </div>
                    <div className="text-[10px] text-muted-foreground truncate">
                      {narrative.headline}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className={cn("w-1.5 h-1.5 rounded-full", sc.bg)} />
                    <span
                      className={cn("text-[10px] font-semibold", sc.color)}
                    >
                      {sc.label}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </SectionCard>
      ) : null}

      {/* Selected narrative detail */}
      {selectedNarrative?.status === "generating" ? (
        <div className="flex items-center justify-center py-8">
          <RefreshCw size={16} className="animate-spin mr-2" />
          Generating narrative…
        </div>
      ) : selectedNarrative ? (
        <SectionCard title="Selected Narrative" className="mt-4">
          <p className="text-sm mb-2">{selectedNarrative.summary}</p>
          <div className="flex gap-2">
            <Btn variant="primary" className="gap-1.5">
              <Download size={12} />
              Export PDF
            </Btn>
            <Btn variant="outline" className="gap-1.5">
              <Mail size={12} />
              Email
            </Btn>
            <Btn variant="outline" className="gap-1.5">
              <Eye size={12} />
              Preview
            </Btn>
          </div>
        </SectionCard>
      ) : selectedDIL ? (
        <SectionCard title={selectedDIL.title} className="mt-4">
          <div className="space-y-3">
            {selectedDIL.sections?.map((section: { title: string; summary: string }, i: number) => (
              <div key={i}>
                <h4 className="text-[12px] font-semibold mb-1">{section.title}</h4>
                <p className="text-[12px] text-muted-foreground">{section.summary}</p>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-4">
            <Btn variant="primary" className="gap-1.5">
              <Download size={12} />
              Export PDF
            </Btn>
            <Btn variant="outline" className="gap-1.5">
              <Mail size={12} />
              Email
            </Btn>
          </div>
        </SectionCard>
      ) : null}
    </ValueStudioShellComponent>
  );
}
