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
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";

export default function TechnicalView() {
  const [searchParams] = useSearchParams();
  const { tenantSlug, accountId } = useParams<{ tenantSlug: string; accountId: string }>();
  const caseId = searchParams.get("caseId");
  const { data: bc, isLoading, error } = useBusinessCase(caseId);
  const exportMutation = useBusinessCaseExport();

  if (isLoading) return (
    <PageShell>
      <PageHeader title="Technical Review" />
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-3 gap-4">{[1,2,3].map(i => <Skeleton key={i} className="h-24" />)}</div>
        <Skeleton className="h-64" />
      </div>
    </PageShell>
  );

  if (error || !bc) return (
    <PageShell>
      <ErrorState
        title={caseId ? "Failed to load business case" : "No case selected"}
        description={caseId
          ? "The business case could not be loaded. It may have been deleted or you may not have permission to view it."
          : "Navigate from the case list to view a specific business case."}
        error={error}
        fallbackAction={
          <Link to={tenantSlug && accountId ? deliverableRoutes.businessCaseList(tenantSlug, accountId) : "/deliverables/cases"}>
            <Btn variant="outline">Back to Cases</Btn>
          </Link>
        }
      />
    </PageShell>
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
    <PageShell className="max-w-5xl">
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
        <div className="p-4 bg-card border border-border rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <FileText size={14} className="text-primary" />
            <span className="vf-text-caption font-semibold text-muted-foreground uppercase">Document</span>
          </div>
          <div className="text-base font-bold text-foreground">{bc.page_count} pages</div>
          <div className="vf-text-caption text-muted-foreground">{(bc.file_size_bytes / 1024).toFixed(0)} KB</div>
        </div>
        <div className="p-4 bg-card border border-border rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <Database size={14} className="text-success" />
            <span className="vf-text-caption font-semibold text-muted-foreground uppercase">Evidence</span>
          </div>
          <div className="text-base font-bold text-foreground">{bc.truth_references?.length ?? 0} refs</div>
          <div className="vf-text-caption text-muted-foreground">Ground truth citations</div>
        </div>
        <div className="p-4 bg-card border border-border rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <GitBranch size={14} className="text-primary" />
            <span className="vf-text-caption font-semibold text-muted-foreground uppercase">Confidence</span>
          </div>
          <div className="text-base font-bold text-foreground">{Math.round(bc.confidence_score * 100)}%</div>
          <div className="vf-text-caption text-muted-foreground">Model confidence score</div>
        </div>
      </div>

      {/* Evidence Provenance */}
      <SectionCard className="mt-4">
        <h3 className="vf-text-body-l font-bold text-foreground mb-3">Evidence Provenance Chain</h3>
        {bc.truth_references && bc.truth_references.length > 0 ? (
          <div className="space-y-2">
            {bc.truth_references.map((ref, i: number) => (
              <div key={String(ref.truth_object_id ?? i)} className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg border border-border">
                <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                  <span className="vf-text-micro font-bold text-primary">{i + 1}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="vf-text-body-s font-semibold text-foreground">
                    {String(ref.title || ref.source || ref.type || `Reference ${i + 1}`)}
                  </div>
                  {!!ref.url && (
                    <a href={String(ref.url)} target="_blank" rel="noopener noreferrer"
                      className="vf-text-caption text-primary hover:underline flex items-center gap-1 mt-0.5">
                      {String(ref.url).slice(0, 60)}... <ExternalLink size={10} />
                    </a>
                  )}
                  {!!ref.confidence && (
                    <span className="vf-text-micro text-muted-foreground mt-0.5 block">
                      Confidence: {typeof ref.confidence === 'number' ? `${Math.round(Number(ref.confidence) * 100)}%` : String(ref.confidence)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="vf-text-body-s text-muted-foreground text-center py-6">No evidence references available.</p>
        )}
      </SectionCard>

      {/* Case Metadata */}
      {Object.keys(metadata).length > 0 && (
        <SectionCard className="mt-4">
          <h3 className="vf-text-body-l font-bold text-foreground mb-3">Case Metadata</h3>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(metadata).map(([key, value]) => (
              <div key={key} className="flex justify-between p-2 bg-muted/50 rounded-md">
                <span className="vf-text-caption font-medium text-muted-foreground">{key.replace(/_/g, ' ')}</span>
                <span className="vf-text-caption font-semibold text-foreground">{String(value)}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Remediation Items */}
      {bc.remediation_items && bc.remediation_items.length > 0 && (
        <SectionCard className="mt-4">
          <h3 className="vf-text-body-l font-bold text-foreground mb-3">Technical Remediation Items</h3>
          <div className="space-y-2">
            {bc.remediation_items.map((item, i: number) => (
              <div key={String(item.title ?? i)} className="flex items-start gap-2 p-2 bg-warning/5 rounded-md border border-warning/20">
                <Clock size={12} className="text-warning mt-0.5 shrink-0" />
                <div>
                  <div className="vf-text-body-s font-semibold text-foreground">
                    {String(item.title || `Item ${i + 1}`)}
                  </div>
                  {!!item.description && (
                    <div className="vf-text-caption text-muted-foreground mt-0.5">{String(item.description)}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}
    </PageShell>
  );
}
