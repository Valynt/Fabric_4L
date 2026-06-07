/**
 * Screen 1 — Ingestion Command Center
 * Design: Refined Enterprise SaaS
 * Data Flow: React Query for server state, Zustand for UI state
 */
import { useState } from "react";
import {
  Globe,
  ChevronDown,
  ChevronUp,
  Settings2,
  Zap,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ArrowRight,
} from "lucide-react";
import {
  useRecentIngestionJobs,
  useIngestionStats,
  useSubmitDomain,
  type IngestionJob,
} from "@/hooks/useIngestion";
import { useIngestionUIStore } from "@/stores";
import { toast } from "sonner";
import {
  MetricCard,
  PageHeader,
  DataTable,
  StatusBadge,
  Btn,
} from "@/components/ui/fabric";
import { PageShell } from "@/components/layout/PageShell";
import { QueryState } from "@/components/QueryState";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const EXTRACTION_PROFILES = ["Default", "Deep Crawl", "Financial Focus", "Technical Focus"];
const ONTOLOGY_TARGETS = ["General", "SaaS / B2B", "Financial Services", "Healthcare"];

export default function CommandCenter() {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [profile, setProfile] = useState("Default");
  const [ontology, setOntology] = useState("SaaS / B2B");
  const [depth, setDepth] = useState("3");
  const [submissionNotice, setSubmissionNotice] = useState<{
    domain: string;
    jobId: string;
  } | null>(null);

  // UI state: Zustand
  const { domainInput, setDomainInput } = useIngestionUIStore();

  // Server state: React Query
  const {
    data: recentJobs = [],
    isLoading: jobsLoading,
    error: jobsError,
  } = useRecentIngestionJobs(5);
  const {
    data: kpiData = {
      totalDomains: 0,
      pagesSynthesized: 0,
      sourcesAnalyzed: 0,
      avgProcessingTime: 0,
    },
    isLoading: kpiLoading,
  } = useIngestionStats();
  const submitDomain = useSubmitDomain();

  const isSubmittingDomain = submitDomain.isPending;

  const handleSubmit = () => {
    const domain = domainInput.trim();
    if (!domain) return;
    submitDomain.mutate(
      {
        domain,
        profile: showAdvanced ? profile : undefined,
        ontology: showAdvanced ? ontology : undefined,
        depth: showAdvanced ? depth : undefined,
      },
      {
        onSuccess: (jobId) => {
          setSubmissionNotice({ domain, jobId });
          setDomainInput("");
        },
        onError: (err) =>
          toast.error(
            `Ingestion failed: ${err instanceof Error ? err.message : "Unknown error"}`
          ),
      }
    );
  };

  return (
    <PageShell>
      <PageHeader
        title="Command Center"
        subtitle="Start a new synthesis or review recent extraction maps."
      />

      {/* ── Simple synthesis input ─────────────────────────────────────────── */}
      <div className="bg-card border border-border rounded-xl shadow-sm mb-4 overflow-hidden">
        {/* Main input row */}
        <div className="flex items-center gap-3 px-4 py-3.5">
          <Globe size={16} className="text-muted-foreground/60 shrink-0" />
          <input
            value={domainInput}
            onChange={(e) => setDomainInput(e.target.value)}
            placeholder="Enter company domain to synthesize (e.g., https://example.com)…"
            className="flex-1 vf-text-body-m text-muted-foreground bg-transparent outline-none placeholder:text-muted-foreground/60"
            aria-label="Company domain to synthesize"
          />
          <Btn
            variant="primary"
            onClick={handleSubmit}
            disabled={isSubmittingDomain || !domainInput}
            aria-label="Start synthesis"
          >
            {submitDomain.isPending ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <>
                Synthesize <ArrowRight size={13} className="inline ml-1" />
              </>
            )}
          </Btn>
        </div>

        {submissionNotice && (
          <div
            role="status"
            className="mx-4 mb-3 rounded-lg border border-success/30 bg-success/10 px-3 py-2 vf-text-body-s text-success"
          >
            Ingestion job submitted for{" "}
            <span className="font-semibold">{submissionNotice.domain}</span>.
            Processing is queued in Layer 1 job{" "}
            <span className="font-mono">
              {submissionNotice.jobId.slice(0, 8)}…
            </span>
            ; track status and completion in Ingestion Jobs.
          </div>
        )}

        {/* Advanced config toggle */}
        <button
          onClick={() => setShowAdvanced((v) => !v)}
          className="w-full flex items-center gap-2 px-4 py-2 border-t border-border/50 vf-text-caption text-muted-foreground/60 hover:text-muted-foreground hover:bg-muted/20 transition-colors"
          aria-expanded={showAdvanced}
          aria-controls="advanced-config-panel"
        >
          <Settings2 size={11} />
          <span>Advanced configuration</span>
          {showAdvanced ? (
            <ChevronUp size={11} className="ml-auto" />
          ) : (
            <ChevronDown size={11} className="ml-auto" />
          )}
        </button>

        {/* Advanced config panel — hidden by default */}
        {showAdvanced && (
          <div
            id="advanced-config-panel"
            className="px-4 py-4 bg-muted/20 border-t border-border/50 grid grid-cols-1 sm:grid-cols-3 gap-4"
          >
            <div>
              <label className="block vf-text-micro uppercase tracking-widest text-muted-foreground/60 font-semibold mb-1.5">
                Extraction Profile
              </label>
              <Select value={profile} onValueChange={setProfile}>
                <SelectTrigger className="w-full vf-text-body-s" aria-label="Extraction profile">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EXTRACTION_PROFILES.map((p) => (
                    <SelectItem key={p} value={p}>{p}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block vf-text-micro uppercase tracking-widest text-muted-foreground/60 font-semibold mb-1.5">
                Ontology Target
              </label>
              <Select value={ontology} onValueChange={setOntology}>
                <SelectTrigger className="w-full vf-text-body-s" aria-label="Ontology target">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ONTOLOGY_TARGETS.map((o) => (
                    <SelectItem key={o} value={o}>{o}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block vf-text-micro uppercase tracking-widest text-muted-foreground/60 font-semibold mb-1.5">
                Crawl Depth
              </label>
              <Select value={depth} onValueChange={setDepth}>
                <SelectTrigger className="w-full vf-text-body-s" aria-label="Crawl depth">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {["1", "2", "3", "4", "5"].map((d) => (
                    <SelectItem key={d} value={d}>{d}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="col-span-1 sm:col-span-3 pt-1">
              <p className="vf-text-caption text-muted-foreground/60">
                Value Pack context:{" "}
                <span className="font-medium text-muted-foreground">
                  SaaS / B2B — Enterprise Security
                </span>
                <button className="ml-2 text-primary underline underline-offset-2">
                  Change
                </button>
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── KPI row ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <MetricCard
          label="Total Processed Nodes"
          value={kpiData.totalDomains.toLocaleString()}
          trend="+12%"
          trendUp
        />
        <MetricCard
          label="Verified Relationships"
          value={kpiData.pagesSynthesized.toLocaleString()}
          trend="+5%"
          trendUp
        />
        <MetricCard
          label="Sources Analyzed"
          value={kpiData.sourcesAnalyzed.toString()}
          trend="Active"
        />
      </div>

      {/* ── Two-column lower section ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Recent maps table — spans 2 cols */}
        <div className="col-span-1 md:col-span-2 bg-card border border-border rounded-lg shadow-sm">
          <div className="px-4 pt-4 pb-3 border-b border-border/50 flex items-center justify-between">
            <h2 className="vf-text-body-l font-bold text-foreground">Recent Maps</h2>
            <button className="vf-text-caption text-primary hover:underline">
              View all
            </button>
          </div>
          <QueryState
            isLoading={jobsLoading}
            error={jobsError}
            isEmpty={recentJobs.length === 0}
            emptyMessage="No recent maps found."
            emptySubMessage="Start a synthesis above to generate your first extraction map."
            loadingMessage="Loading recent maps…"
          >
            <DataTable
              columns={[
                { key: "domain", header: "Domain" },
                { key: "pages", header: "Pages" },
                { key: "status", header: "Status" },
                { key: "updated", header: "Updated" },
              ]}
              data={recentJobs.map((job: IngestionJob) => ({
                id: job.id,
                domain: (
                  <span className="flex items-center gap-2">
                    <span className="text-muted-foreground/40 vf-text-body-l">🏢</span>
                    <span className="font-medium text-foreground">
                      {job.domain}
                    </span>
                  </span>
                ),
                pages: (
                  <span className="text-muted-foreground">
                    {job.pagesProcessed || 0}
                  </span>
                ),
                status: <StatusBadge status={job.status} />,
                updated: (
                  <span className="text-muted-foreground/60 vf-text-caption">
                    {job.updatedAt
                      ? new Date(job.updatedAt).toLocaleDateString()
                      : "-"}
                  </span>
                ),
              }))}
              keyExtractor={(item) => item.id}
            />
          </QueryState>
        </div>

        {/* Activity feed — 1 col */}
        <div className="bg-card border border-border rounded-lg shadow-sm">
          <div className="px-4 pt-4 pb-3 border-b border-border/50 flex items-center gap-2">
            <Clock size={13} className="text-muted-foreground/60" />
            <h2 className="vf-text-body-m font-bold text-foreground">
              Recent Activity
            </h2>
          </div>
          <QueryState
            isLoading={jobsLoading}
            error={jobsError}
            isEmpty={recentJobs.length === 0}
            emptyMessage="No recent activity."
            loadingMessage="Loading activity…"
          >
            <div className="divide-y divide-border">
              {recentJobs.slice(0, 4).map((job: IngestionJob, idx: number) => (
                <div
                  key={idx}
                  className="px-4 py-3 flex items-start gap-2.5"
                >
                  <span className="mt-0.5 shrink-0">
                    {job.status === "completed" ? (
                      <CheckCircle2
                        size={13}
                        className="text-success"
                        aria-label="Completed"
                      />
                    ) : job.status === "processing" ? (
                      <Loader2
                        size={13}
                        className="text-info animate-spin"
                        aria-label="Processing"
                      />
                    ) : job.status === "failed" ? (
                      <AlertCircle
                        size={13}
                        className="text-destructive"
                        aria-label="Failed"
                      />
                    ) : (
                      <Zap
                        size={13}
                        className="text-primary"
                        aria-label="Queued"
                      />
                    )}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="vf-text-caption text-muted-foreground leading-snug">
                      {job.domain} — {job.status} ({job.progress}%)
                    </p>
                    <p className="vf-text-micro text-muted-foreground/60 mt-0.5">
                      {job.updatedAt
                        ? new Date(job.updatedAt).toLocaleDateString()
                        : "Just now"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </QueryState>
        </div>
      </div>
    </PageShell>
  );
}
