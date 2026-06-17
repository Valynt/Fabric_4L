/**
 * SignalsTab — "What did we detect?"
 *
 * Raw intelligence extracted from source material: observations from notes,
 * calls, CRM fields, files, and web sources. Each signal can be reviewed and
 * carried forward into the value-case chain.
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Radio, FileText, GitBranch, ShieldCheck, Search } from "lucide-react";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { ErrorState } from "@/components/states/ErrorState";
import { Btn } from "@/components/ui/fabric";
import { cn } from "@/lib/utils";
import { useSignalReview } from "@/hooks/useWorkspaceCase";
import {
  ConfidenceBar,
  DetailPanel,
  ScreenHeader,
  Tag,
  WorkspaceEmpty,
} from "../_shared/primitives";
import { SignalTypeBadge, SignalStatusBadge } from "../_shared/badges";
import { useTabLink } from "../_shared/useTabLink";
import { useWorkspaceCaseId, useSignalsData } from "../_shared/useWorkspaceData";
import type { WorkspaceSignal } from "../_shared/types";

export default function SignalsTab() {
  const tabLink = useTabLink();
  const { accountId, caseId, isLoading: caseLoading } = useWorkspaceCaseId();
  const { items: signals, isLoading, error } = useSignalsData(caseId);
  const review = useSignalReview();

  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const types = useMemo(
    () => Array.from(new Set(signals.map((s) => s.type).filter(Boolean))) as string[],
    [signals]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return signals.filter((s) => {
      const matchesType = typeFilter === "all" || s.type === typeFilter;
      const matchesQuery =
        !q ||
        s.title.toLowerCase().includes(q) ||
        (s.excerpt?.toLowerCase().includes(q) ?? false);
      return matchesType && matchesQuery;
    });
  }, [signals, query, typeFilter]);

  const selected = signals.find((s) => s.id === selectedId) ?? null;

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }
  if (caseLoading || isLoading) {
    return <CenteredLoader message="Loading signals…" />;
  }
  if (error) {
    return (
      <ErrorState
        title="Failed to load signals"
        description="The signal data could not be retrieved."
        error={error}
        fullPage
      />
    );
  }

  const handleReview = (signal: WorkspaceSignal, decision: "approved" | "rejected") => {
    review.mutate({ signalId: signal.id, accountId, reviewStatus: decision });
  };

  return (
    <div>
      <ScreenHeader
        title="Signals"
        description="What we detected from your source material. Signals are raw observations — not yet polished claims — that bridge messy intake and structured value work."
      />

      {signals.length === 0 ? (
        <WorkspaceEmpty
          icon={Radio}
          title="No signals detected yet"
          purpose="As source material is processed, detected observations appear here — pains, buying signals, budget cues, timelines, and competitive mentions."
          bullets={[
            "Pain, buying, risk, budget, stakeholder, timeline, competitive, and metric signals",
            "Each signal keeps its source and a confidence score",
            "Accept the ones that matter, then promote them into value drivers",
          ]}
        />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="relative w-full max-w-xs">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search signals or snippets…"
                className="h-9 w-full rounded-md border border-border bg-background pl-9 pr-3 vf-text-caption text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            {types.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <FilterChip active={typeFilter === "all"} onClick={() => setTypeFilter("all")}>
                  All
                </FilterChip>
                {types.map((t) => (
                  <FilterChip key={t} active={typeFilter === t} onClick={() => setTypeFilter(t)}>
                    {t[0].toUpperCase() + t.slice(1)}
                  </FilterChip>
                ))}
              </div>
            )}
          </div>

          <div className="flex gap-4">
            <div className="flex-1 space-y-3">
              {filtered.length === 0 ? (
                <p className="py-12 text-center vf-text-caption text-muted-foreground">
                  No signals match your filters.
                </p>
              ) : (
                filtered.map((signal) => (
                  <button
                    key={signal.id}
                    type="button"
                    onClick={() => setSelectedId(signal.id)}
                    className={cn(
                      "w-full rounded-xl border bg-card p-4 text-left transition-colors hover:border-primary/40",
                      selectedId === signal.id ? "border-primary/60" : "border-border"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <SignalTypeBadge type={signal.type} />
                      <SignalStatusBadge status={signal.status} />
                      {signal.detectedAt && (
                        <span className="vf-text-micro text-muted-foreground">{signal.detectedAt}</span>
                      )}
                      <div className="ml-auto">
                        <ConfidenceBar value={signal.confidence} />
                      </div>
                    </div>
                    <p className="mt-2 vf-text-body-s font-semibold text-foreground">{signal.title}</p>
                    {signal.excerpt && (
                      <p className="mt-1 line-clamp-2 vf-text-caption italic text-muted-foreground">
                        “{signal.excerpt}”
                      </p>
                    )}
                    {signal.source && (
                      <div className="mt-2">
                        <Tag>
                          <FileText className="mr-1 h-3 w-3" /> {signal.source}
                        </Tag>
                      </div>
                    )}
                  </button>
                ))
              )}
            </div>

            {selected && (
              <DetailPanel
                eyebrow="Signal Insight Analyzer"
                title={selected.title}
                onClose={() => setSelectedId(null)}
                footer={
                  <div className="flex flex-wrap gap-2">
                    <Btn
                      variant="primary"
                      onClick={() => handleReview(selected, "approved")}
                      disabled={review.isPending}
                    >
                      Accept
                    </Btn>
                    <Btn
                      variant="outline"
                      onClick={() => handleReview(selected, "rejected")}
                      disabled={review.isPending}
                    >
                      Reject
                    </Btn>
                    <Link to={tabLink("drivers")}>
                      <Btn variant="ghost">
                        <GitBranch className="mr-1 h-3.5 w-3.5" /> Promote to Driver
                      </Btn>
                    </Link>
                    <Link to={tabLink("evidence")}>
                      <Btn variant="ghost">
                        <ShieldCheck className="mr-1 h-3.5 w-3.5" /> Link Evidence
                      </Btn>
                    </Link>
                  </div>
                }
              >
                {selected.excerpt && (
                  <div>
                    <p className="vf-text-micro font-medium uppercase tracking-wider text-muted-foreground">
                      Extracted snippet
                    </p>
                    <p className="mt-1 rounded-md border border-border bg-muted/30 p-2 vf-text-caption italic text-foreground">
                      “{selected.excerpt}”
                    </p>
                  </div>
                )}
                <DetailRow label="Type"><SignalTypeBadge type={selected.type} /></DetailRow>
                <DetailRow label="Status"><SignalStatusBadge status={selected.status} /></DetailRow>
                <DetailRow label="Source">
                  <span className="vf-text-caption text-foreground">{selected.source ?? "—"}</span>
                </DetailRow>
                <DetailRow label="Confidence"><ConfidenceBar value={selected.confidence} /></DetailRow>
                {selected.relatedDriver && (
                  <DetailRow label="Related driver">
                    <span className="vf-text-caption text-foreground">{selected.relatedDriver}</span>
                  </DetailRow>
                )}
                {review.isError && (
                  <p className="vf-text-micro text-destructive">Could not save your decision. Try again.</p>
                )}
              </DetailPanel>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full px-3 py-1 vf-text-micro font-medium transition-colors",
        active
          ? "bg-primary text-primary-foreground"
          : "bg-muted text-muted-foreground hover:text-foreground"
      )}
    >
      {children}
    </button>
  );
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="vf-text-micro font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      {children}
    </div>
  );
}
