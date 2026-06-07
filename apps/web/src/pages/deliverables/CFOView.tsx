/**
 * CFO Business Case View
 * Audience-specific view emphasizing financial metrics, ROI, payback,
 * and cost-benefit analysis for C-suite financial decision-makers.
 */
import { useSearchParams, Link, useParams } from "react-router-dom";
import { deliverableRoutes } from "@/navigation/deliverableRoutes";
import {
  DollarSign, TrendingUp, Clock, BarChart3, Download,
  AlertCircle, Loader2, ArrowLeft, Shield, FileText,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useBusinessCase, useBusinessCaseExport } from "@/hooks/useDocuments";
import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, Btn } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";

function fmt(n: number | undefined, prefix = "$"): string {
  if (n == null) return "—";
  if (Math.abs(n) >= 1_000_000) return `${prefix}${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `${prefix}${(n / 1_000).toFixed(0)}K`;
  return `${prefix}${n.toFixed(0)}`;
}

function KPI({ icon: Icon, label, value, sub, accent }: {
  icon: typeof DollarSign; label: string; value: string; sub?: string; accent?: string;
}) {
  return (
    <div className="p-5 bg-card border border-border rounded-xl">
      <div className="flex items-center gap-2 mb-2">
        <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", accent || "bg-primary/10")}>
          <Icon size={16} className="text-primary" />
        </div>
        <span className="vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-2xl font-extrabold text-foreground">{value}</div>
      {sub && <div className="vf-text-caption text-muted-foreground mt-1">{sub}</div>}
    </div>
  );
}

export default function CFOView() {
  const [searchParams] = useSearchParams();
  const { tenantSlug, accountId } = useParams<{ tenantSlug: string; accountId: string }>();
  const caseId = searchParams.get("caseId");
  const { data: bc, isLoading, error, refetch } = useBusinessCase(caseId);
  const exportMutation = useBusinessCaseExport();

  if (isLoading) return (
    <PageShell>
      <PageHeader title="CFO View" />
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-4 gap-4">{[1,2,3,4].map(i => <Skeleton key={i} className="h-28" />)}</div>
        <Skeleton className="h-64" />
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

  const netValue = bc.total_value - bc.implementation_cost;

  const listHref = tenantSlug && accountId
    ? deliverableRoutes.businessCaseList(tenantSlug, accountId)
    : "/deliverables/cases";
  const detailHref = tenantSlug && accountId && bc.case_id
    ? deliverableRoutes.businessCaseDetail(tenantSlug, accountId, bc.case_id)
    : "/deliverables/cases";

  return (
    <PageShell>
      <PageHeader
        title={`CFO View: ${bc.title}`}
        subtitle="Financial summary for executive decision-making"
        breadcrumbs={[
          { label: "Deliverables", href: listHref },
          { label: bc.title, href: detailHref },
          { label: "CFO View" },
        ]}
        actions={
          <div className="flex gap-2">
            <Link to={detailHref}>
              <Btn variant="ghost"><ArrowLeft size={14} /> Full Case</Btn>
            </Link>
            <Btn
              variant="primary"
              disabled={exportMutation.isPending}
              onClick={() => exportMutation.mutate({ caseId: bc.case_id, format: "pdf" })}
            >
              {exportMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
              Export PDF
            </Btn>
          </div>
        }
      />

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4 mt-6">
        <KPI icon={DollarSign} label="Total Value" value={fmt(bc.total_value)} sub="Projected annual benefit" accent="bg-success/10" />
        <KPI icon={TrendingUp} label="ROI" value={`${bc.roi_ratio.toFixed(1)}x`} sub={`Net: ${fmt(netValue)}`} accent="bg-primary/10" />
        <KPI icon={Clock} label="Payback" value={`${bc.payback_months} mo`} sub="Time to break even" accent="bg-warning/10" />
        <KPI icon={Shield} label="Confidence" value={`${Math.round(bc.confidence_score * 100)}%`} sub={`${bc.truth_references?.length ?? 0} evidence refs`} accent="bg-info/10" />
      </div>

      {/* Cost-Benefit Analysis */}
      <div className="grid grid-cols-2 gap-4 mt-6">
        <SectionCard>
          <h3 className="vf-text-body-l font-bold text-foreground mb-3">Cost-Benefit Summary</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span className="vf-text-body-s text-muted-foreground">Implementation Cost</span>
              <span className="vf-text-body-l font-bold text-destructive">{fmt(bc.implementation_cost)}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span className="vf-text-body-s text-muted-foreground">Total Projected Value</span>
              <span className="vf-text-body-l font-bold text-success">{fmt(bc.total_value)}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border">
              <span className="vf-text-body-s text-muted-foreground">Net Value</span>
              <span className={cn("vf-text-body-l font-bold", netValue >= 0 ? "text-success" : "text-destructive")}>{fmt(netValue)}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="vf-text-body-s text-muted-foreground">ROI Ratio</span>
              <span className="vf-text-body-l font-bold text-primary">{bc.roi_ratio.toFixed(2)}x</span>
            </div>
          </div>
        </SectionCard>

        <SectionCard>
          <h3 className="vf-text-body-l font-bold text-foreground mb-3">Key Recommendations</h3>
          {bc.recommendations.length > 0 ? (
            <div className="space-y-2">
              {bc.recommendations.map((rec, i) => (
                <div key={i} className="flex items-start gap-2 p-2 bg-muted rounded-md">
                  <BarChart3 size={12} className="text-primary mt-0.5 shrink-0" />
                  <span className="vf-text-body-s text-foreground">{rec}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center py-6 text-muted-foreground">
              <FileText size={20} className="mb-2 opacity-50" />
              <p className="vf-text-body-s">No recommendations available.</p>
            </div>
          )}
        </SectionCard>
      </div>

      {/* Remediation Items */}
      {bc.remediation_items && bc.remediation_items.length > 0 && (
        <SectionCard className="mt-4">
          <h3 className="vf-text-body-l font-bold text-foreground mb-3">Risk & Remediation Items</h3>
          <div className="space-y-2">
            {bc.remediation_items.map((item, i) => (
              <div key={i} className="flex items-start gap-2 p-2 rounded-md border border-warning/20 bg-warning/5">
                <AlertCircle size={12} className="text-warning mt-0.5 shrink-0" />
                <span className="vf-text-body-s text-foreground">{String(item.description || item.title || JSON.stringify(item))}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </PageShell>
  );
}
