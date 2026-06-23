/**
 * Screen 4 — Entity Detail
 * Design: Refined Enterprise SaaS
 *
 * Displays full entity details fetched from L3 Knowledge Graph API.
 * Route: /context/ontology/entities/:entityId
 *
 * Connected hooks:
 * - useEntity (detail by ID with relationships and provenance)
 * - useEntities (for related entities list)
 */
import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useNavigation } from "@/hooks";
import {
  ArrowLeft, Zap, ExternalLink, Clock, Shield, GitBranch,
  AlertCircle, ChevronRight
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useEntity, useEntities, type Entity } from "@/hooks/useEntities";
import { cn } from "@/lib/utils";
import { PageShell, PageHeader } from "@/components";
import { SectionCard } from "@/components/blocks/SectionCard";
import { Btn } from "@/components/ui/fabric";
import { EntityBadge } from "@/lib/entity-colors";
import { ErrorState } from "@/components/states/ErrorState";

// ── Helpers ──────────────────────────────────────────────────────────────────────────────
function confidenceColor(c: number) {
  if (c >= 0.9) return "text-success font-semibold";
  if (c >= 0.7) return "text-warning";
  return "text-destructive";
}

function StatusBadge({ status }: { status: string }) {
  const variantMap: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
    validated: "success",
    pending: "warning",
    draft: "secondary",
    deprecated: "destructive",
  };
  return (
    <Badge variant={variantMap[status] || "secondary"} className="uppercase vf-text-micro">
      {status}
    </Badge>
  );
}

function formatDate(iso?: string) {
  if (!iso) return "\u2014";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Loading Skeleton ─────────────────────────────────────────────────────────────────────
function EntityDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
      </div>
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-48" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-20" />)}
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────────────────
export default function EntityDetail() {
  const params = useParams<{ entityId: string }>();
  const { navigateTo } = useNavigation();
  const entityId = params.entityId || null;
  const [activeTab, setActiveTab] = useState("details");

  // Fetch entity detail (includes relationships and provenance)
  const { data: entity, isLoading, error } = useEntity(entityId);

  // Fetch related entities from the same domain for context
  const { data: relatedData } = useEntities(
    entity ? { domains: entity.domain ? [entity.domain] : undefined, limit: 5 } : undefined
  );
  const relatedEntities = relatedData?.results?.filter((e: Entity) => e.id !== entityId) ?? [];

  // ── Loading State ──────────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <PageShell>
        <EntityDetailSkeleton />
      </PageShell>
    );
  }

  // ── Error State ────────────────────────────────────────────────────────────────────────
  if (error || !entity) {
    return (
      <PageShell>
        <ErrorState
          title="Entity Not Found"
          description={error?.message || `Entity "${entityId}" could not be loaded.`}
          fallbackAction={
            <Btn variant="outline" onClick={() => navigateTo("entity-browser")}>
              <ArrowLeft size={14} className="mr-1" /> Back to Entity Browser
            </Btn>
          }
        />
      </PageShell>
    );
  }

  // ── Render ───────────────────────────────────────────────────────────────────────────
  const tabs = ["details", "relationships", "provenance", "related"];

  return (
    <PageShell>
      <PageHeader
        title={entity.name}
        breadcrumbs={[
          { label: "Ontology", href: "/context/ontology/entities" },
          { label: "Entity Browser", href: "/context/ontology/entities" },
          { label: entity.name },
        ]}
        actions={
          <Btn variant="ghost" onClick={() => navigateTo("entity-browser")}>
            <ArrowLeft size={14} className="mr-1" /> Back
          </Btn>
        }
      />

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <Zap size={20} className="text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-foreground">{entity.name}</h1>
            <div className="flex items-center gap-3 mt-1">
              <EntityBadge type={entity.type.toLowerCase()} />
              <StatusBadge status={entity.status} />
              <span className={cn("vf-text-body-s", confidenceColor(entity.confidence))}>
                {Math.round(entity.confidence * 100)}% confidence
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Metadata Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="p-3 bg-muted/50 rounded-lg border border-border/50">
          <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground mb-1">Domain</div>
          <div className="vf-text-body-m font-semibold text-foreground truncate">{entity.domain || "\u2014"}</div>
        </div>
        <div className="p-3 bg-muted/50 rounded-lg border border-border/50">
          <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground mb-1">Source</div>
          <div className="vf-text-body-m font-semibold text-foreground truncate">{entity.sourceName || "\u2014"}</div>
        </div>
        <div className="p-3 bg-muted/50 rounded-lg border border-border/50">
          <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground mb-1">Updated</div>
          <div className="vf-text-body-m font-semibold text-foreground">{formatDate(entity.updatedAt)}</div>
        </div>
        <div className="p-3 bg-muted/50 rounded-lg border border-border/50">
          <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground mb-1">Created</div>
          <div className="vf-text-body-m font-semibold text-foreground">{formatDate(entity.createdAt)}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border mb-4">
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-2.5 vf-text-body-s font-semibold border-b-2 -mb-px transition-colors capitalize",
              activeTab === tab
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "details" && (
        <SectionCard>
          <div className="space-y-4">
            {entity.description && (
              <div>
                <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground mb-1">Description</div>
                <p className="vf-text-body-m text-foreground leading-relaxed">{entity.description}</p>
              </div>
            )}
            {entity.properties && Object.keys(entity.properties).length > 0 && (
              <div>
                <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground mb-2">Properties</div>
                <div className="space-y-1.5">
                  {Object.entries(entity.properties).map(([key, value]) => (
                    <div key={key} className="flex items-center gap-2 vf-text-body-s">
                      <span className="text-muted-foreground font-medium w-[140px] shrink-0">{key}:</span>
                      <span className="text-foreground">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {entity.extractionJobId && (
              <div>
                <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground mb-1">Extraction Job</div>
                <div className="vf-text-body-s text-muted-foreground font-mono">{entity.extractionJobId}</div>
              </div>
            )}
            {!entity.description && (!entity.properties || Object.keys(entity.properties).length === 0) && (
              <div className="vf-text-body-s text-muted-foreground text-center py-4">
                No additional details available for this entity.
              </div>
            )}
          </div>
        </SectionCard>
      )}

      {activeTab === "relationships" && (
        <SectionCard>
          <div className="vf-text-body-s text-muted-foreground mb-3">
            <GitBranch size={14} className="inline mr-1" />
            Relationships loaded from the Knowledge Graph. View the full graph at{" "}
            <Link to="/context/ontology/graph" className="text-primary hover:underline">
              Graph Explorer
            </Link>.
          </div>
          <div className="space-y-2">
            <div className="vf-text-caption font-semibold text-foreground uppercase tracking-wider mb-2">
              Connected Entities in {entity.domain || "this domain"}
            </div>
            {relatedEntities.length > 0 ? (
              relatedEntities.map((rel: Entity) => (
                <Link
                  key={rel.id}
                  to={`/context/ontology/entities/${encodeURIComponent(rel.id)}`}
                  className="flex items-center gap-3 p-2.5 bg-muted/50 rounded-md border border-border/50 hover:border-primary/30 transition-colors cursor-pointer"
                >
                  <EntityBadge type={rel.type.toLowerCase()} />
                  <span className="vf-text-body-s font-semibold text-foreground flex-1">{rel.name}</span>
                  <span className={cn("vf-text-caption", confidenceColor(rel.confidence))}>
                    {Math.round(rel.confidence * 100)}%
                  </span>
                  <ExternalLink size={12} className="text-muted-foreground" />
                </Link>
              ))
            ) : (
              <div className="vf-text-body-s text-muted-foreground text-center py-4">
                No related entities found in this domain.
              </div>
            )}
          </div>
        </SectionCard>
      )}

      {activeTab === "provenance" && (
        <SectionCard>
          <div className="space-y-3">
            <div>
              <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground mb-1">
                <Shield size={12} className="inline mr-1" />
                Data Lineage
              </div>
              <div className="vf-text-body-s text-foreground space-y-1.5 mt-2">
                <div className="flex items-center gap-2">
                  <Clock size={12} className="text-muted-foreground" />
                  <span>Created: {formatDate(entity.createdAt)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock size={12} className="text-muted-foreground" />
                  <span>Last updated: {formatDate(entity.updatedAt)}</span>
                </div>
                {entity.createdBy && (
                  <div className="flex items-center gap-2">
                    <Shield size={12} className="text-muted-foreground" />
                    <span>Created by: {entity.createdBy}</span>
                  </div>
                )}
                {entity.sourceName && (
                  <div className="flex items-center gap-2">
                    <ExternalLink size={12} className="text-muted-foreground" />
                    <span>Source: {entity.sourceName}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </SectionCard>
      )}

      {activeTab === "related" && (
        <SectionCard>
          <div className="vf-text-caption font-semibold text-foreground uppercase tracking-wider mb-3">
            Other entities from {entity.domain || "this domain"}
          </div>
          {relatedEntities.length > 0 ? (
            <div className="space-y-2">
              {relatedEntities.map((rel: Entity) => (
                <Link
                  key={rel.id}
                  to={`/context/ontology/entities/${encodeURIComponent(rel.id)}`}
                  className="flex items-center gap-3 p-2.5 bg-muted/50 rounded-md border border-border/50 hover:border-primary/30 transition-colors cursor-pointer"
                >
                  <EntityBadge type={rel.type.toLowerCase()} />
                  <div className="flex-1">
                    <div className="vf-text-body-s font-semibold text-foreground">{rel.name}</div>
                    <div className="vf-text-caption text-muted-foreground">{rel.status}</div>
                  </div>
                  <span className={cn("vf-text-caption", confidenceColor(rel.confidence))}>
                    {Math.round(rel.confidence * 100)}%
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="vf-text-body-s text-muted-foreground text-center py-4">
              No related entities found.
            </div>
          )}
        </SectionCard>
      )}
    </PageShell>
  );
}
