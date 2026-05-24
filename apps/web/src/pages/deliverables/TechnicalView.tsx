/**
 * Technical Business Case View
 * Audience-specific view emphasizing implementation details, technical
 * requirements, integration points, and evidence provenance for engineering leads.
 *
 * Route: /deliverables/views/technical
 * Hooks: useBusinessCase, useBusinessCaseExport
 */
import { useSearchParams, Link, useParams } from "react-router-dom";
import { deliverableRoutes } from "@/navigation/deliverableRoutes";
import {
  Code2, Database, GitBranch, FileText, Download,
  AlertCircle, Loader2, ArrowLeft, ExternalLink,
  CheckCircle2, Clock,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useBusinessCase, useBusinessCaseExport } from "@/hooks/useDocuments";

import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, Btn } from "@/components/ui/fabric";

export default function TechnicalView() {
  const [searchParams] = useSearchParams();
  const { tenantSlug, accountId } = useParams<{ tenantSlug: string; accountId: string }>();
  const caseId = searchParams.get("caseId");
  const { data: bc, isLoading, error } = useBusinessCase(caseId);
  const exportMutation = useBusinessCaseExport();

  if (isLoading) return (
    <div className="p-6 max-w-5xl mx-auto space-y-4">
      <Skeleton className="h-10 w-64" />
      <div className="grid grid-cols-3 gap-4">{[1,2,3].map(i => <Skeleton key={i} className="h-24" />)}</div>
      <Skeleton className="h-64" />
    </div>
  );

  if (error || !bc) return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex flex-col items-center py-16">
        <AlertCircle size={24} className="text-red-500 mb-2" />
        <p className="text-[13px] text-neutral-600">{caseId ? "Failed to load business case." : "No case selected."}</p>
        {tenantSlug && accountId ? (
          <Link to={deliverableRoutes.businessCaseList(tenantSlug, accountId)} className="mt-3 text-[12px] text-blue-600 hover:underline">Back to Cases</Link>
        ) : (
          <Link to="/deliverables/cases" className="mt-3 text-[12px] text-blue-600 hover:underline">Back to Cases</Link>
        )}
      </div>
    </div>
  );

  const metadata = bc.case_metadata || {};

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
        title={`Technical Review: ${bc.title}`}
        subtitle="Implementation details and evidence provenance"
        breadcrumbs={[
          { label: "Deliverables", href: listHref },
          { label: bc.title, href: detailHref },
          { label: "Technical View" },
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

      {/* Technical Metrics */}
      <div className="grid grid-cols-3 gap-4 mt-6">
        <div className="p-4 bg-white border border-neutral-100 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <FileText size={14} className="text-blue-500" />
            <span className="text-[11px] font-semibold text-neutral-500 uppercase">Document</span>
          </div>
          <div className="text-[16px] font-bold text-neutral-800">{bc.page_count} pages</div>
          <div className="text-[11px] text-neutral-500">{(bc.file_size_bytes / 1024).toFixed(0)} KB</div>
        </div>
        <div className="p-4 bg-white border border-neutral-100 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <Database size={14} className="text-emerald-500" />
            <span className="text-[11px] font-semibold text-neutral-500 uppercase">Evidence</span>
          </div>
          <div className="text-[16px] font-bold text-neutral-800">{bc.truth_references?.length ?? 0} refs</div>
          <div className="text-[11px] text-neutral-500">Ground truth citations</div>
        </div>
        <div className="p-4 bg-white border border-neutral-100 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <GitBranch size={14} className="text-violet-500" />
            <span className="text-[11px] font-semibold text-neutral-500 uppercase">Confidence</span>
          </div>
          <div className="text-[16px] font-bold text-neutral-800">{Math.round(bc.confidence_score * 100)}%</div>
          <div className="text-[11px] text-neutral-500">Model confidence score</div>
        </div>
      </div>

      {/* Evidence Provenance */}
      <SectionCard className="mt-4">
        <h3 className="text-[14px] font-bold text-neutral-800 mb-3">Evidence Provenance Chain</h3>
        {bc.truth_references && bc.truth_references.length > 0 ? (
          <div className="space-y-2">
            {bc.truth_references.map((ref, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-neutral-50 rounded-lg border border-neutral-100">
                <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-bold text-blue-600">{i + 1}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-semibold text-neutral-800">
                    {String(ref.title || ref.source || ref.type || `Reference ${i + 1}`)}
                  </div>
                  {!!ref.url && (
                    <a href={String(ref.url)} target="_blank" rel="noopener noreferrer"
                      className="text-[11px] text-blue-600 hover:underline flex items-center gap-1 mt-0.5">
                      {String(ref.url).slice(0, 60)}... <ExternalLink size={10} />
                    </a>
                  )}
                  {!!ref.confidence && (
                    <span className="text-[10px] text-neutral-500 mt-0.5 block">
                      Confidence: {typeof ref.confidence === 'number' ? `${Math.round(Number(ref.confidence) * 100)}%` : String(ref.confidence)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[12px] text-neutral-400 text-center py-6">No evidence references available.</p>
        )}
      </SectionCard>

      {/* Case Metadata */}
      {Object.keys(metadata).length > 0 && (
        <SectionCard className="mt-4">
          <h3 className="text-[14px] font-bold text-neutral-800 mb-3">Case Metadata</h3>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(metadata).map(([key, value]) => (
              <div key={key} className="flex justify-between p-2 bg-neutral-50 rounded-md">
                <span className="text-[11px] font-medium text-neutral-500">{key.replace(/_/g, ' ')}</span>
                <span className="text-[11px] font-semibold text-neutral-700">{String(value)}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Remediation Items */}
      {bc.remediation_items && bc.remediation_items.length > 0 && (
        <SectionCard className="mt-4">
          <h3 className="text-[14px] font-bold text-neutral-800 mb-3">Technical Remediation Items</h3>
          <div className="space-y-2">
            {bc.remediation_items.map((item, i: number) => (
              <div key={i} className="flex items-start gap-2 p-2 bg-amber-50/50 rounded-md border border-amber-100">
                <Clock size={12} className="text-amber-500 mt-0.5 shrink-0" />
                <div>
                  <div className="text-[12px] font-semibold text-neutral-700">
                    {String(item.title || `Item ${i + 1}`)}
                  </div>
                  {!!item.description && (
                    <div className="text-[11px] text-neutral-500 mt-0.5">{String(item.description)}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </div>
  );
}
