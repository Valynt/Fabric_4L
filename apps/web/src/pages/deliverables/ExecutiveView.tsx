/**
 * Executive Business Case View
 * Audience-specific view emphasizing strategic alignment, business impact,
 * and high-level value narrative for VP/SVP decision-makers.
 *
 * Route: /deliverables/views/executive
 * Hooks: useBusinessCase, useBusinessCaseExport
 */
import { useSearchParams, Link, useParams } from "react-router-dom";
import { deliverableRoutes } from "@/navigation/deliverableRoutes";
import {
  Target, Zap, TrendingUp, Users, Download,
  AlertCircle, Loader2, ArrowLeft, CheckCircle2,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useBusinessCase, useBusinessCaseExport } from "@/hooks/useDocuments";

import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, Btn } from "@/components/ui/fabric";

export default function ExecutiveView() {
  const [searchParams] = useSearchParams();
  const { tenantSlug, accountId } = useParams<{ tenantSlug: string; accountId: string }>();
  const caseId = searchParams.get("caseId");
  const { data: bc, isLoading, error } = useBusinessCase(caseId);
  const exportMutation = useBusinessCaseExport();

  if (isLoading) return (
    <div className="p-6 max-w-5xl mx-auto space-y-4">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-48" />
      <div className="grid grid-cols-2 gap-4"><Skeleton className="h-40" /><Skeleton className="h-40" /></div>
    </div>
  );

  if (error || !bc) return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex flex-col items-center py-16">
        <AlertCircle size={24} className="text-red-500 mb-2" aria-hidden="true" />
        <p className="text-[13px] text-neutral-600">{caseId ? "Failed to load business case." : "No case selected."}</p>
        {tenantSlug && accountId ? (
          <Link to={deliverableRoutes.businessCaseList(tenantSlug, accountId)} className="mt-3 text-[12px] text-blue-600 hover:underline">Back to Cases</Link>
        ) : (
          <Link to="/deliverables/cases" className="mt-3 text-[12px] text-blue-600 hover:underline">Back to Cases</Link>
        )}
      </div>
    </div>
  );

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
        <h3 className="text-[14px] font-bold text-neutral-800 mb-2">Executive Summary</h3>
        <p className="text-[13px] text-neutral-700 leading-relaxed">{bc.summary}</p>
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-neutral-100">
          <div className="text-center">
            <Target size={16} className="mx-auto text-blue-500 mb-1" />
            <div className="text-[20px] font-extrabold text-neutral-900">{bc.roi_ratio.toFixed(1)}x</div>
            <div className="text-[10px] text-neutral-500 uppercase">ROI</div>
          </div>
          <div className="text-center">
            <TrendingUp size={16} className="mx-auto text-emerald-500 mb-1" />
            <div className="text-[20px] font-extrabold text-neutral-900">
              ${bc.total_value >= 1_000_000 ? `${(bc.total_value / 1_000_000).toFixed(1)}M` : `${(bc.total_value / 1_000).toFixed(0)}K`}
            </div>
            <div className="text-[10px] text-neutral-500 uppercase">Total Value</div>
          </div>
          <div className="text-center">
            <Zap size={16} className="mx-auto text-amber-500 mb-1" />
            <div className="text-[20px] font-extrabold text-neutral-900">{bc.payback_months} mo</div>
            <div className="text-[10px] text-neutral-500 uppercase">Payback</div>
          </div>
        </div>
      </SectionCard>

      {/* Strategic Recommendations */}
      <div className="grid grid-cols-2 gap-4 mt-4">
        <SectionCard>
          <h3 className="text-[14px] font-bold text-neutral-800 mb-3">Strategic Recommendations</h3>
          {bc.recommendations.length > 0 ? (
            <div className="space-y-2">
              {bc.recommendations.map((rec, i) => (
                <div key={i} className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                  <span className="text-[12px] text-neutral-700">{rec}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[12px] text-neutral-400 py-4 text-center">No recommendations yet.</p>
          )}
        </SectionCard>

        <SectionCard>
          <h3 className="text-[14px] font-bold text-neutral-800 mb-3">Decision Confidence</h3>
          <div className="flex items-center gap-4 mb-4">
            <div className="relative w-20 h-20">
              <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90" aria-hidden="true">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" strokeWidth="3" />
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="#3b82f6" strokeWidth="3"
                  strokeDasharray={`${bc.confidence_score * 100} ${100 - bc.confidence_score * 100}`} />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-[14px] font-extrabold text-neutral-800">{Math.round(bc.confidence_score * 100)}%</span>
              </div>
            </div>
            <div>
              <div className="text-[12px] font-semibold text-neutral-700">
                {bc.confidence_score >= 0.8 ? "High Confidence" : bc.confidence_score >= 0.5 ? "Moderate Confidence" : "Low Confidence"}
              </div>
              <div className="text-[11px] text-neutral-500 mt-0.5">
                Based on {bc.truth_references?.length ?? 0} evidence references
              </div>
            </div>
          </div>
          <div className="text-[11px] text-neutral-500">
            Status: <span className="font-semibold text-neutral-700 capitalize">{bc.status}</span>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
