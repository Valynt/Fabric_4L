/**
 * CFO Business Case View
 * Audience-specific view emphasizing financial metrics, ROI, payback,
 * and cost-benefit analysis for C-suite financial decision-makers.
 *
 * Route: /deliverables/views/cfo
 * Hooks: useBusinessCase, useBusinessCaseExport
 */
import { useSearchParams, Link, useParams } from "react-router-dom";
import { deliverableRoutes } from "@/navigation/deliverableRoutes";
import {
  DollarSign, TrendingUp, Clock, BarChart3, Download,
  AlertCircle, Loader2, ArrowLeft, Shield,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useBusinessCase, useBusinessCaseExport } from "@/hooks/useDocuments";

import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, Btn } from "@/components/ui/fabric";

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
    <div className="p-5 bg-white border border-neutral-100 rounded-xl">
      <div className="flex items-center gap-2 mb-2">
        <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", accent || "bg-blue-50")}>
          <Icon size={16} className="text-blue-600" />
        </div>
        <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-[28px] font-extrabold text-neutral-900">{value}</div>
      {sub && <div className="text-[11px] text-neutral-500 mt-1">{sub}</div>}
    </div>
  );
}

export default function CFOView() {
  const [searchParams] = useSearchParams();
  const { tenantSlug, accountId } = useParams<{ tenantSlug: string; accountId: string }>();
  const caseId = searchParams.get("caseId");
  const { data: bc, isLoading, error } = useBusinessCase(caseId);
  const exportMutation = useBusinessCaseExport();

  if (isLoading) return (
    <div className="p-6 max-w-5xl mx-auto space-y-4">
      <Skeleton className="h-10 w-64" />
      <div className="grid grid-cols-4 gap-4">{[1,2,3,4].map(i => <Skeleton key={i} className="h-28" />)}</div>
      <Skeleton className="h-64" />
    </div>
  );

  if (error || !bc) return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex flex-col items-center py-16">
        <AlertCircle size={24} className="text-red-500 mb-2" />
        <p className="text-[13px] text-neutral-600">{caseId ? "Failed to load business case." : "No case selected. Navigate from the case list."}</p>
        {tenantSlug && accountId ? (
          <Link to={deliverableRoutes.businessCaseList(tenantSlug, accountId)} className="mt-3 text-[12px] text-blue-600 hover:underline">Back to Cases</Link>
        ) : (
          <Link to="/deliverables/cases" className="mt-3 text-[12px] text-blue-600 hover:underline">Back to Cases</Link>
        )}
      </div>
    </div>
  );

  const netValue = bc.total_value - bc.implementation_cost;

  // Graceful handling if route params are missing
  const listHref = tenantSlug && accountId
    ? deliverableRoutes.businessCaseList(tenantSlug, accountId)
    : "/deliverables/cases";
  const detailHref = tenantSlug && accountId && bc.case_id
    ? deliverableRoutes.businessCaseDetail(tenantSlug, accountId, bc.case_id)
    : "/deliverables/cases";

  return (
    <div className="p-6 max-w-5xl mx-auto">
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
        <KPI icon={DollarSign} label="Total Value" value={fmt(bc.total_value)} sub="Projected annual benefit" accent="bg-emerald-50" />
        <KPI icon={TrendingUp} label="ROI" value={`${bc.roi_ratio.toFixed(1)}x`} sub={`Net: ${fmt(netValue)}`} accent="bg-blue-50" />
        <KPI icon={Clock} label="Payback" value={`${bc.payback_months} mo`} sub="Time to break even" accent="bg-amber-50" />
        <KPI icon={Shield} label="Confidence" value={`${Math.round(bc.confidence_score * 100)}%`} sub={`${bc.truth_references?.length ?? 0} evidence refs`} accent="bg-violet-50" />
      </div>

      {/* Cost-Benefit Analysis */}
      <div className="grid grid-cols-2 gap-4 mt-6">
        <SectionCard>
          <h3 className="text-[14px] font-bold text-neutral-800 mb-3">Cost-Benefit Summary</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b border-neutral-100">
              <span className="text-[12px] text-neutral-600">Implementation Cost</span>
              <span className="text-[14px] font-bold text-red-600">{fmt(bc.implementation_cost)}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-neutral-100">
              <span className="text-[12px] text-neutral-600">Total Projected Value</span>
              <span className="text-[14px] font-bold text-emerald-600">{fmt(bc.total_value)}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-neutral-100">
              <span className="text-[12px] text-neutral-600">Net Value</span>
              <span className={cn("text-[14px] font-bold", netValue >= 0 ? "text-emerald-600" : "text-red-600")}>{fmt(netValue)}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-[12px] text-neutral-600">ROI Ratio</span>
              <span className="text-[14px] font-bold text-blue-600">{bc.roi_ratio.toFixed(2)}x</span>
            </div>
          </div>
        </SectionCard>

        <SectionCard>
          <h3 className="text-[14px] font-bold text-neutral-800 mb-3">Key Recommendations</h3>
          {bc.recommendations.length > 0 ? (
            <div className="space-y-2">
              {bc.recommendations.map((rec, i) => (
                <div key={i} className="flex items-start gap-2 p-2 bg-neutral-50 rounded-md">
                  <BarChart3 size={12} className="text-blue-500 mt-0.5 shrink-0" />
                  <span className="text-[12px] text-neutral-700">{rec}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[12px] text-neutral-400 text-center py-4">No recommendations available.</p>
          )}
        </SectionCard>
      </div>

      {/* Remediation Items */}
      {bc.remediation_items && bc.remediation_items.length > 0 && (
        <SectionCard className="mt-4">
          <h3 className="text-[14px] font-bold text-neutral-800 mb-3">Risk & Remediation Items</h3>
          <div className="space-y-2">
            {bc.remediation_items.map((item, i) => (
              <div key={i} className="flex items-start gap-2 p-2 bg-amber-50/50 rounded-md border border-amber-100">
                <AlertCircle size={12} className="text-amber-500 mt-0.5 shrink-0" />
                <span className="text-[12px] text-neutral-700">{String(item.description || item.title || JSON.stringify(item))}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}
