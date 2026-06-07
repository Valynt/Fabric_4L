/**
 * Executive Business Case View
 * Audience-specific view emphasizing strategic alignment, business impact,
 * and high-level value narrative for VP/SVP decision-makers.
 */
import { useSearchParams, Link, useParams } from "react-router-dom";
import { deliverableRoutes } from "@/navigation/deliverableRoutes";
import {
  Target, Zap, TrendingUp, Users, Download,
  AlertCircle, Loader2, ArrowLeft, CheckCircle2,
  FileText,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useBusinessCase, useBusinessCaseExport } from "@/hooks/useDocuments";
import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, Btn } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";

export default function ExecutiveView() {
  const [searchParams] = useSearchParams();
  const { tenantSlug, accountId } = useParams<{ tenantSlug: string; accountId: string }>();
  const caseId = searchParams.get("caseId");
  const { data: bc, isLoading, error, refetch } = useBusinessCase(caseId);
  const exportMutation = useBusinessCaseExport();

  if (isLoading) return (
    <PageShell>
      <PageHeader title="Executive View" />
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48" />
        <div className="grid grid-cols-2 gap-4"><Skeleton className="h-40" /><Skeleton className="h-40" /></div>
      </div>
    </PageShell>
  );

  if (error || !bc) {
    return (
      <PageShell>
        <ErrorState
          title={caseId ? "Failed to load business case" : "No case selected"}
          description={caseId
            ? "The business case could not be loaded. It may have been deleted or you may not have permission to view it."
            : "Navigate from the case list to view a specific business case."}
          error={error}
          onRetry={refetch}
          retryLabel="Retry"
          fallbackAction={
            <Link to={tenantSlug && accountId ? deliverableRoutes.businessCaseList(tenantSlug, accountId) : "/deliverables/cases"}>
              <Btn variant="outline"><ArrowLeft size={14} /> Back to Cases</Btn>
            </Link>
          }
        />
      </PageShell>
    );
  }

  const listHref = tenantSlug && accountId
    ? deliverableRoutes.businessCaseList(tenantSlug, accountId)
    : "/deliverables/cases";
  const detailHref = tenantSlug && accountId && bc.case_id
    ? deliverableRoutes.businessCaseDetail(tenantSlug, accountId, bc.case_id)
    : "/deliverables/cases";

  return (
    <PageShell>
      <PageHeader
        title={`Executive Brief: ${bc.title}`}
        subtitle="Strategic impact summary for leadership review"
        breadcrumbs={[
          { label: "Deliverables", href: listHref },
          { label: bc.title, href: detailHref },
          { label: "Executive View" },
        ]}
        actions={
          <div className="flex gap-2">
            <Link to={detailHref}>
              <Btn variant="ghost"><ArrowLeft size={14} /> Full Case</Btn>
            </Link>
            <Btn variant="primary" disabled={exportMutation.isPending}
              onClick={() => exportMutation.mutate({ caseId: bc.case_id, format: "pdf" })}>
              {exportMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
              Export
            </Btn>
          </div>
        }
      />

      {/* Executive Summary Card */}
      <SectionCard className="mt-6">
        <h3 className="vf-text-body-l font-bold text-foreground mb-2">Executive Summary</h3>
        <p className="vf-text-body-m text-foreground leading-relaxed">{bc.summary}</p>
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-border">
          <div className="text-center">
            <Target size={16} className="mx-auto text-primary mb-1" />
            <div className="text-[20px] font-extrabold text-foreground">{bc.roi_ratio.toFixed(1)}x</div>
            <div className="vf-text-micro text-muted-foreground uppercase">ROI</div>
          </div>
          <div className="text-center">
            <TrendingUp size={16} className="mx-auto text-success mb-1" />
            <div className="text-[20px] font-extrabold text-foreground">
              ${bc.total_value >= 1_000_000 ? `${(bc.total_value / 1_000_000).toFixed(1)}M` : `${(bc.total_value / 1_000).toFixed(0)}K`}
            </div>
            <div className="vf-text-micro text-muted-foreground uppercase">Total Value</div>
          </div>
          <div className="text-center">
            <Zap size={16} className="mx-auto text-warning mb-1" />
            <div className="text-[20px] font-extrabold text-foreground">{bc.payback_months} mo</div>
            <div className="vf-text-micro text-muted-foreground uppercase">Payback</div>
          </div>
        </div>
      </SectionCard>

      {/* Strategic Recommendations */}
      <div className="grid grid-cols-2 gap-4 mt-4">
        <SectionCard>
          <h3 className="vf-text-body-l font-bold text-foreground mb-3">Strategic Recommendations</h3>
          {bc.recommendations.length > 0 ? (
            <div className="space-y-2">
              {bc.recommendations.map((rec, i) => (
                <div key={i} className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="text-success mt-0.5 shrink-0" />
                  <span className="vf-text-body-s text-foreground">{rec}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center py-6 text-muted-foreground">
              <FileText size={20} className="mb-2 opacity-50" />
              <p className="vf-text-body-s">No recommendations yet.</p>
            </div>
          )}
        </SectionCard>

        <SectionCard>
          <h3 className="vf-text-body-l font-bold text-foreground mb-3">Decision Confidence</h3>
          <div className="flex items-center gap-4 mb-4">
            <div className="relative w-20 h-20">
              <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90" aria-hidden="true">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="hsl(var(--border))" strokeWidth="3" />
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="hsl(var(--primary))" strokeWidth="3"
                  strokeDasharray={`${bc.confidence_score * 100} ${100 - bc.confidence_score * 100}`} />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="vf-text-body-l font-extrabold text-foreground">{Math.round(bc.confidence_score * 100)}%</span>
              </div>
            </div>
            <div>
              <div className="vf-text-body-s font-semibold text-foreground">
                {bc.confidence_score >= 0.8 ? "High Confidence" : bc.confidence_score >= 0.5 ? "Moderate Confidence" : "Low Confidence"}
              </div>
              <div className="vf-text-caption text-muted-foreground mt-0.5">
                Based on {bc.truth_references?.length ?? 0} evidence references
              </div>
            </div>
          </div>
          <div className="vf-text-caption text-muted-foreground">
            Status: <span className="font-semibold text-foreground capitalize">{bc.status}</span>
          </div>
        </SectionCard>
      </div>
    </PageShell>
  );
}
