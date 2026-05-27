/**
 * ValueNarrativeHome — Main home page for authenticated users
 *
 * Layout:
 *   1. ProspectPromptBuilder — primary value case creation prompt
 *   2. Light dashboard section — KPIs + recent maps + activity feed
 *      (reuses existing CommandCenter patterns)
 */
import { Clock, CheckCircle2, AlertCircle, Loader2, Zap } from "lucide-react";
import { useRecentIngestionJobs, useIngestionStats, type IngestionJob } from "@/hooks/useIngestion";
import { ProspectPromptBuilder } from "@/components/workspace/ProspectPromptBuilder";
import { useNavigation } from "@/hooks/useNavigation";
import { useProspectSetupAccountCreate } from "@/hooks/useProspectSetupAccount";
import { MetricCard, DataTable, StatusBadge } from "@/components/ui/fabric";

export default function ValueNarrativeHome() {
  const { data: recentJobs = [], isLoading: jobsLoading } = useRecentIngestionJobs(5);
  const {
    data: kpiData = { totalDomains: 0, pagesSynthesized: 0, sourcesAnalyzed: 0, avgProcessingTime: 0 },
  } = useIngestionStats();
  const { navigateTo } = useNavigation();
  const prospectSetup = useProspectSetupAccountCreate();

  const handleNavigateToWorkspace = (_path: string, accountId: string) => {
    navigateTo('intelligence-signals', { accountId });
  };

  return (
    <div className="min-h-full bg-background">
      {/* Prompt Builder section */}
      <div className="px-6 pt-10 pb-6 max-w-3xl mx-auto">
        <div className="text-center mb-6">
          <p className="text-sm text-muted-foreground">
            AI-Powered Value Intelligence
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-foreground mt-2">
            Create a value case
          </h1>
          <p className="text-sm text-muted-foreground mt-2 max-w-lg mx-auto">
            Describe the account, buying context, and desired outcome — or use the
            structured controls to build your value case.
          </p>
        </div>
        <ProspectPromptBuilder
          onCreateSetup={prospectSetup.createSetup}
          onNavigateToWorkspace={handleNavigateToWorkspace}
          isSubmitting={prospectSetup.isSubmitting}
        />
      </div>

      {/* Dashboard section */}
      <div className="p-6 max-w-5xl mx-auto">
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

        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2 bg-card border border-border rounded-lg shadow-sm">
            <div className="px-4 pt-4 pb-3 border-b border-border/60 flex items-center justify-between">
              <h2 className="text-[14px] font-bold text-foreground">Recent Maps</h2>
              <button className="text-[11px] text-primary hover:underline">View all</button>
            </div>
            <DataTable
              columns={["Domain", "Pages", "Status", "Updated"]}
              rows={recentJobs.map((job) => [
                <span key={`d-${job.id}`} className="flex items-center gap-2">
                  <span className="text-muted-foreground text-[14px]">🏢</span>
                  <span className="font-medium text-foreground">{job.domain}</span>
                </span>,
                <span key={`p-${job.id}`} className="text-muted-foreground">{job.pagesProcessed || 0}</span>,
                <StatusBadge key={`s-${job.id}`} status={job.status} />,
                <span key={`u-${job.id}`} className="text-muted-foreground text-[11px]">
                  {job.updatedAt ? new Date(job.updatedAt).toLocaleDateString() : "-"}
                </span>,
              ])}
            />
          </div>

          <div className="bg-card border border-border rounded-lg shadow-sm">
            <div className="px-4 pt-4 pb-3 border-b border-border/60 flex items-center gap-2">
              <Clock size={13} className="text-muted-foreground" />
              <h2 className="text-[13px] font-bold text-foreground">Recent Activity</h2>
            </div>
            <div className="divide-y divide-border/60">
              {recentJobs.slice(0, 4).map((job: IngestionJob) => (
                <div key={job.id} className="px-4 py-3 flex items-start gap-2.5">
                  <span className="mt-0.5 shrink-0">
                    {job.status === "completed" ? (
                      <CheckCircle2 size={13} className="text-emerald-500" />
                    ) : job.status === "processing" ? (
                      <Loader2 size={13} className="text-blue-500 animate-spin" />
                    ) : job.status === "failed" ? (
                      <AlertCircle size={13} className="text-red-400" />
                    ) : (
                      <Zap size={13} className="text-violet-500" />
                    )}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] text-foreground leading-snug">
                      {job.domain} — {job.status} ({job.progress}%)
                    </p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {job.updatedAt ? new Date(job.updatedAt).toLocaleDateString() : "Just now"}
                    </p>
                  </div>
                </div>
              ))}
              {recentJobs.length === 0 && !jobsLoading && (
                <div className="px-4 py-8 text-center text-muted-foreground text-[11px]">
                  No recent activity
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
