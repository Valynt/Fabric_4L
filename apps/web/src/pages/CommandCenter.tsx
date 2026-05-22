/**
 * Screen 1 — Ingestion Command Center
 * Design: Refined Enterprise SaaS
 * Data Flow: React Query for server state, Zustand for UI state
 */
import { useState } from "react";
import { Globe, ChevronDown, ChevronUp, Settings2, Zap, Clock, CheckCircle2, AlertCircle, Loader2, ArrowRight } from "lucide-react";
import { useRecentIngestionJobs, useIngestionStats, useSubmitDomain, type IngestionJob } from "@/hooks/useIngestion";
import { useIngestionUIStore } from "@/stores";
import { toast } from "sonner";
import { MetricCard, PageHeader, DataTable, StatusBadge, Btn } from "@/components/ui/fabric";

const EXTRACTION_PROFILES = ["Default", "Deep Crawl", "Financial Focus", "Technical Focus"];
const ONTOLOGY_TARGETS = ["General", "SaaS / B2B", "Financial Services", "Healthcare"];

export default function CommandCenter() {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [profile, setProfile] = useState("Default");
  const [ontology, setOntology] = useState("SaaS / B2B");
  const [depth, setDepth] = useState("3");
  const [submissionNotice, setSubmissionNotice] = useState<{ domain: string; jobId: string } | null>(null);

  // UI state: Zustand
  const { domainInput, setDomainInput } = useIngestionUIStore();

  // Server state: React Query
  const { data: recentJobs = [], isLoading: jobsLoading } = useRecentIngestionJobs(5);
  const { data: kpiData = { totalDomains: 0, pagesSynthesized: 0, sourcesAnalyzed: 0, avgProcessingTime: 0 } } = useIngestionStats();
  const submitDomain = useSubmitDomain();

  const isSubmittingDomain = submitDomain.isPending;

  return (
    <div className="p-6 max-w-5xl">
      <PageHeader
        title="Command Center"
        subtitle="Start a new synthesis or review recent extraction maps."
      />

      {/* ── Simple synthesis input ─────────────────────────────────────────── */}
      <div className="bg-card border border-border rounded-xl shadow-sm mb-4 overflow-hidden">
        {/* Main input row */}
        <div className="flex items-center gap-3 px-4 py-3.5">
          <Globe size={16} className="text-muted-foreground/60 shrink-0"/>
          <input
            value={domainInput}
            onChange={(e) => setDomainInput(e.target.value)}
            placeholder="Enter company domain to synthesize (e.g., https://example.com)…"
            className="flex-1 text-[13px] text-muted-foreground bg-transparent outline-none placeholder:text-muted-foreground/60"
          />
          <Btn
            variant="primary"
            onClick={() => {
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
                    setDomainInput('');
                  },
                  onError: (err) => toast.error(`Ingestion failed: ${err instanceof Error ? err.message : 'Unknown error'}`),
                }
              );
            }}
            disabled={isSubmittingDomain || !domainInput}
          >
            {submitDomain.isPending ? <Loader2 size={13} className="animate-spin" /> : <>
              Synthesize <ArrowRight size={13} className="inline ml-1"/>
            </>}
          </Btn>
        </div>

        {submissionNotice && (
          <div role="status" className="mx-4 mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-[12px] text-emerald-900">
            Ingestion job submitted for <span className="font-semibold">{submissionNotice.domain}</span>.
            Processing is queued in Layer 1 job <span className="font-mono">{submissionNotice.jobId.slice(0, 8)}...</span>;
            track status and completion in Ingestion Jobs.
          </div>
        )}

        {/* Advanced config toggle */}
        <button
          onClick={() => setShowAdvanced(v => !v)}
          className="w-full flex items-center gap-2 px-4 py-2 border-t border-border/50 text-[11px] text-muted-foreground/60 hover:text-muted-foreground hover:bg-muted/20 transition-colors"
        >
          <Settings2 size={11}/>
          <span>Advanced configuration</span>
          {showAdvanced ? <ChevronUp size={11} className="ml-auto"/> : <ChevronDown size={11} className="ml-auto"/>}
        </button>

        {/* Advanced config panel — hidden by default */}
        {showAdvanced && (
          <div className="px-4 py-4 bg-muted/20 border-t border-border/50 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-[10px] uppercase tracking-widest text-muted-foreground/60 font-semibold mb-1.5">
                Extraction Profile
              </label>
              <select
                value={profile}
                onChange={e => setProfile(e.target.value)}
                className="w-full text-[12px] border border-border rounded-md px-2.5 py-1.5 bg-card text-muted-foreground outline-none"
              >
                {EXTRACTION_PROFILES.map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-widest text-muted-foreground/60 font-semibold mb-1.5">
                Ontology Target
              </label>
              <select
                value={ontology}
                onChange={e => setOntology(e.target.value)}
                className="w-full text-[12px] border border-border rounded-md px-2.5 py-1.5 bg-card text-muted-foreground outline-none"
              >
                {ONTOLOGY_TARGETS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-widest text-muted-foreground/60 font-semibold mb-1.5">
                Crawl Depth
              </label>
              <select
                value={depth}
                onChange={e => setDepth(e.target.value)}
                className="w-full text-[12px] border border-border rounded-md px-2.5 py-1.5 bg-card text-muted-foreground outline-none"
              >
                {["1","2","3","4","5"].map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div className="col-span-1 sm:col-span-3 pt-1">
              <p className="text-[11px] text-muted-foreground/60">
                Value Pack context: <span className="font-medium text-muted-foreground">SaaS / B2B — Enterprise Security</span>
                <button className="ml-2 text-blue-600 underline underline-offset-2">Change</button>
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── KPI row ────────────────────────────────────────────────────────── */}
      <div className="flex gap-4 mb-6">
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
            <h2 className="text-[14px] font-bold text-foreground">Recent Maps</h2>
            <button className="text-[11px] text-blue-600 hover:underline">View all</button>
          </div>
          <DataTable
            columns={[
              { key: "domain", header: "Domain" },
              { key: "pages", header: "Pages" },
              { key: "status", header: "Status" },
              { key: "updated", header: "Updated" },
            ]}
            data={recentJobs.map(job => ({
              id: job.id,
              domain: (
              <span className="flex items-center gap-2">
                <span className="text-neutral-300 text-[14px]">🏢</span>
                <span className="font-medium text-foreground">{job.domain}</span>
              </span>
              ),
              pages: <span className="text-muted-foreground">{job.pagesProcessed || 0}</span>,
              status: <StatusBadge status={job.status}/>,
              updated: <span className="text-muted-foreground/60 text-[11px]">{job.updatedAt ? new Date(job.updatedAt).toLocaleDateString() : '-'}</span>,
            }))}
            keyExtractor={(item) => item.id}
          />
        </div>

        {/* Activity feed — 1 col */}
        <div className="bg-card border border-border rounded-lg shadow-sm">
          <div className="px-4 pt-4 pb-3 border-b border-border/50 flex items-center gap-2">
            <Clock size={13} className="text-muted-foreground/60"/>
            <h2 className="text-[13px] font-bold text-foreground">Recent Activity</h2>
          </div>
          <div className="divide-y divide-neutral-100">
            {recentJobs.slice(0, 4).map((job: IngestionJob, idx: number) => (
              <div key={idx} className="px-4 py-3 flex items-start gap-2.5">
                <span className="mt-0.5 shrink-0">
                  {job.status === 'completed' ? <CheckCircle2 size={13} className="text-emerald-500"/> :
                   job.status === 'processing' ? <Loader2 size={13} className="text-blue-500 animate-spin"/> :
                   job.status === 'failed' ? <AlertCircle size={13} className="text-red-400"/> :
                   <Zap size={13} className="text-violet-500"/>}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-muted-foreground leading-snug">
                    {job.domain} — {job.status} ({job.progress}%)
                  </p>
                  <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                    {job.updatedAt ? new Date(job.updatedAt).toLocaleDateString() : 'Just now'}
                  </p>
                </div>
              </div>
            ))}
            {recentJobs.length === 0 && (
              <div className="px-4 py-8 text-center text-muted-foreground/60 text-[11px]">
                No recent activity
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
