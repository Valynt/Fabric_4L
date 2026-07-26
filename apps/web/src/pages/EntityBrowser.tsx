/**
 * Entity Browser — Unified Table + Detail Drawer
 * Design: Refined Enterprise SaaS
 * Data Flow: React Query for server state, Zustand for UI state
 *
 * Features:
 * - Two-pane layout: Data table (left) + Detail drawer (right)
 * - Real API data via useEntities hook
 * - Auto-select first entity on load/filter
 * - Persistent drawer always visible
 * - Row selection highlighting
 */
import { useState, useMemo, useEffect, useRef } from "react";
import { Plus, Loader2, X, Download } from "lucide-react";
import { useEntities, type Entity, type EntityListResponse, useEntity } from "@/hooks/useEntities";
import { useEntityUIStore } from "@/stores";
import type { EntityType } from "@/lib/entity-colors";
import { Toolbar, SearchInput } from "@/components/ui/fabric";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, DataTable, Btn } from "@/components/ui/fabric";
import { EntityBadge } from "@/lib/entity-colors";
import { PageShell, ErrorState, EmptyState } from '@/components';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const CONF_COLORS = (c: number) =>
  c >= 0.9 ? "text-success font-semibold" : c >= 0.7 ? "text-warning" : "text-destructive";

const STATUS_COLORS: Record<Entity['status'], string> = {
  validated: "text-success",
  pending: "text-warning",
  draft: "text-muted-foreground",
  deprecated: "text-destructive",
};

const mapEntityType = (type: string): EntityType => {
  const mapping: Record<string, EntityType> = {
    'Capability': 'capability',
    'UseCase': 'usecase',
    'Persona': 'persona',
    'ValueDriver': 'valuedriver',
  };
  return mapping[type] || 'capability';
};

export default function EntityBrowser() {
  // UI state: Zustand
  const {
    searchQuery,
    selectedType,
    selectedEntityId,
    setSearchQuery,
    setSelectedType,
    setSelectedEntityId,
    clearFilters
  } = useEntityUIStore();

  // Server state: React Query with server-backed filtering
  const {
    data: entityList,
    isLoading,
    error,
    refetch
  } = useEntities({
    searchText: searchQuery || undefined,
    entityTypes: selectedType ? [selectedType] : undefined,
    limit: 25,
    sortBy: 'updated_at',
    sortOrder: 'desc',
  });

  const entities = entityList?.results ?? [];

  // Drawer tab state (local, not persisted)
  const [drawerTab, setDrawerTab] = useState("Details");

  // Track if we've done initial auto-select to prevent loops
  const hasAutoSelectedRef = useRef(false);

  // Auto-select first entity on initial load or when filter changes (not when selection changes)
  useEffect(() => {
    if (entities.length > 0) {
      // Only auto-select on first load or if current selection is not in the filtered list
      const currentSelectedInList = entities.some(e => e.id === selectedEntityId);
      if (!selectedEntityId || !currentSelectedInList) {
        setSelectedEntityId(entities[0].id);
        hasAutoSelectedRef.current = true;
      }
    } else if (hasAutoSelectedRef.current) {
      // Only clear selection if we had previously auto-selected (not on initial empty state)
      setSelectedEntityId(null);
    }
    // Note: selectedEntityId intentionally excluded from deps to prevent feedback loop
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entities, setSelectedEntityId]);

  // Fetch selected entity details
  const { data: selectedEntity, isLoading: isLoadingEntity } = useEntity(selectedEntityId);

  const errorMessage = error ? error.message : null;

  const handleExport = () => {
    if (!selectedEntity) return;
    // Export selected entity as JSON
    const dataStr = JSON.stringify(selectedEntity, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `entity-${selectedEntity.id}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleExportAll = () => {
    // Export all filtered entities as JSON
    const dataStr = JSON.stringify(entities, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `entities-export-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <PageShell>
    <div className="h-full flex flex-col">
      <PageHeader
        breadcrumbs={[{ label: "Discover" }, { label: "Knowledge Model" }, { label: "Entity Browser" }]}
        title="Entity Browser"
        subtitle="Explore the knowledge model entity catalogue"
        actions={
          <div className="flex items-center gap-2">
            <Btn variant="ghost" onClick={handleExportAll}>
              <Download size={12} className="mr-1" />
              Export
            </Btn>
            <Btn variant="primary"><Plus size={12}/> New Entity</Btn>
          </div>
        }
      />

      {/* Filter toolbar */}
      <Toolbar>
        <SearchInput
          placeholder="Search entities…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <Select value={selectedType || 'all'} onValueChange={(v) => setSelectedType(v === 'all' ? null : v as EntityType)}>
          <SelectTrigger className="h-8 w-[140px] vf-text-body-s"><SelectValue placeholder="All Types" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="capability">Capability</SelectItem>
            <SelectItem value="usecase">Use Case</SelectItem>
            <SelectItem value="persona">Persona</SelectItem>
            <SelectItem value="valuedriver">Value Driver</SelectItem>
          </SelectContent>
        </Select>
        <Select value={'all'} onValueChange={() => {}}>
          <SelectTrigger className="h-8 w-[140px] vf-text-body-s"><SelectValue placeholder="All Domains" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Domains</SelectItem>
            {entityList?.availableDomains?.map(d => (
              <SelectItem key={d} value={d}>{d}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={'all'} onValueChange={() => {}}>
          <SelectTrigger className="h-8 w-[140px] vf-text-body-s"><SelectValue placeholder="All Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="validated">Validated</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="deprecated">Deprecated</SelectItem>
          </SelectContent>
        </Select>
        <Btn variant="ghost" onClick={clearFilters}>Clear Filters</Btn>
      </Toolbar>

      {/* Type legend chips */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {(["capability","usecase","persona","valuedriver"] as EntityType[]).map(t => (
          <button type="button"
            key={t}
            onClick={() => setSelectedType(selectedType === t ? null : t)}
            className={`cursor-pointer transition-opacity ${selectedType && selectedType !== t ? 'opacity-50' : ''}`}
          >
            <EntityBadge type={t}/>
          </button>
        ))}
      </div>

      {/* Two-pane layout: Table + Drawer */}
      <div className="flex flex-1 gap-4 min-h-0">
        {/* Data Table */}
        <div className={`flex-1 transition-all ${selectedEntityId ? 'mr-[340px]' : ''}`}>
          <SectionCard noPad className="h-full">
            {isLoading ? (
              <div className="flex items-center justify-center p-12 h-full">
                <Loader2 size={24} className="animate-spin text-primary" />
                <span className="ml-2 text-muted-foreground">Loading entities...</span>
              </div>
            ) : error ? (
              <ErrorState
                title="Failed to load entities"
                description="Something went wrong while fetching the entity catalog."
                error={error}
                onRetry={() => refetch()}
              />
            ) : entities.length === 0 ? (
              <EmptyState
                title={searchQuery || selectedType ? 'No entities match your filters' : 'No entities found'}
                description={searchQuery || selectedType ? 'Try adjusting your search or filters' : 'Get started by creating a new entity'}
              />
            ) : (
              <DataTable
                columns={["Entity Name", "Type", "Domain", "Confidence", "Status", "Actions"]}
                rows={entities.map((e: Entity) => {
                  const isSelected = e.id === selectedEntityId;
                  const statusColor = STATUS_COLORS[e.status];
                  return [
                    <span key={`${e.id}-name`} className={`font-semibold ${isSelected ? 'text-primary' : 'text-foreground'}`}>{e.name}</span>,
                    <EntityBadge key={`${e.id}-type`} type={mapEntityType(e.type)}/>,
                    <span key={`${e.id}-domain`} className="text-muted-foreground vf-text-caption font-mono">{e.domain || '—'}</span>,
                    <span key={`${e.id}-confidence`} className={`vf-text-body-s ${CONF_COLORS(e.confidence)}`}>{Math.round(e.confidence * 100)}%</span>,
                    <span key={`${e.id}-status`} className={`vf-text-caption font-semibold ${statusColor}`}>
                      ● {e.status.charAt(0).toUpperCase() + e.status.slice(1)}
                    </span>,
                    <div key={`${e.id}-actions`} className="flex gap-2">
                      <button type="button"
                        onClick={() => setSelectedEntityId(e.id)}
                        className={`vf-text-caption hover:underline ${isSelected ? 'text-primary font-semibold' : 'text-primary'}`}
                      >
                        {isSelected ? 'Selected' : 'View'}
                      </button>
                      <button type="button" className="text-muted-foreground/60 vf-text-caption hover:underline">Edit</button>
                    </div>,
                  ];
                })}
              />
            )}
          </SectionCard>
        </div>

        {/* Detail Drawer */}
        {selectedEntityId && (
          <div className="absolute top-[180px] right-6 w-[320px] bottom-6 bg-card border border-border rounded-lg shadow-lg z-10 flex flex-col overflow-hidden">
            {isLoadingEntity ? (
              <div className="flex items-center justify-center p-8 flex-1">
                <Loader2 size={20} className="animate-spin text-primary" />
              </div>
            ) : selectedEntity ? (
              <>
                {/* Drawer header */}
                <div className="flex items-start justify-between p-4 border-b border-border/50">
                  <div className="flex-1 min-w-0">
                    <div className="vf-text-body-l font-bold text-foreground truncate">{selectedEntity.name}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <EntityBadge type={mapEntityType(selectedEntity.type)}/>
                    </div>
                  </div>
                  <button type="button"
                    onClick={() => setSelectedEntityId(null)}
                    className="text-muted-foreground/60 hover:text-muted-foreground transition-colors ml-2"
                  >
                    <X size={16}/>
                  </button>
                </div>

                {/* Status bar */}
                <div className="flex items-center gap-4 px-4 py-2 bg-muted/20 border-b border-border/50 vf-text-caption">
                  <span className="text-muted-foreground">
                    Status: <span className={`${STATUS_COLORS[selectedEntity.status]} font-semibold`}>● {selectedEntity.status.charAt(0).toUpperCase() + selectedEntity.status.slice(1)}</span>
                  </span>
                  <span className="text-muted-foreground">
                    Confidence: <span className="font-semibold text-foreground">{Math.round(selectedEntity.confidence * 100)}%</span>
                  </span>
                  {selectedEntity.domain && (
                    <span className="text-muted-foreground">
                      Domain: <span className="font-semibold text-foreground">{selectedEntity.domain}</span>
                    </span>
                  )}
                </div>

                {/* Tabs */}
                <div className="flex border-b border-border px-4">
                  {["Details", "Relationships", "Source", "History"].map(tab => (
                    <button type="button"
                      key={tab}
                      onClick={() => setDrawerTab(tab)}
                      className={`px-3 py-2.5 vf-text-caption font-semibold border-b-2 -mb-px transition-colors ${
                        drawerTab === tab ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {tab}
                    </button>
                  ))}
                </div>

                {/* Drawer content */}
                <div className="flex-1 p-4 space-y-4 overflow-y-auto">
                  {drawerTab === "Details" && (
                    <>
                      <div>
                        <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">Description</div>
                        <p className="vf-text-body-s text-muted-foreground leading-relaxed">
                          {selectedEntity.description || "No description available."}
                        </p>
                      </div>
                      <div>
                        <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">Entity ID</div>
                        <div className="vf-text-caption text-muted-foreground font-mono break-all">{selectedEntity.id}</div>
                      </div>
                      {selectedEntity.properties && Object.keys(selectedEntity.properties).length > 0 && (
                        <div>
                          <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60 mb-2">Properties</div>
                          <ul className="space-y-1">
                            {Object.entries(selectedEntity.properties).slice(0, 5).map(([key, value]) => (
                              <li key={key} className="flex items-start gap-2 vf-text-caption text-muted-foreground">
                                <span className="text-muted-foreground/60 shrink-0">{key}:</span>
                                <span className="font-mono truncate">{String(value)}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  )}
                  {drawerTab === "Relationships" && (
                    <div className="vf-text-body-s text-muted-foreground italic">
                      Relationships will be displayed here. Connect to graph API for related entities.
                    </div>
                  )}
                  {drawerTab === "Source" && (
                    <div className="space-y-3">
                      <div>
                        <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">Source System</div>
                        <div className="vf-text-body-s text-muted-foreground">
                          {selectedEntity.sourceName || "Unknown source"}
                        </div>
                      </div>
                      <div>
                        <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">Domain</div>
                        <div className="vf-text-body-s text-muted-foreground">
                          {selectedEntity.domain || "Unclassified"}
                        </div>
                      </div>
                      <div>
                        <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">Extraction Job</div>
                        <div className="vf-text-caption text-muted-foreground font-mono">
                          {selectedEntity.extractionJobId || "N/A"}
                        </div>
                      </div>
                    </div>
                  )}
                  {drawerTab === "History" && (
                    <div className="vf-text-body-s text-muted-foreground italic">
                      {selectedEntity.createdAt
                        ? `Created: ${new Date(selectedEntity.createdAt).toLocaleString()}`
                        : "No creation timestamp available."
                      }
                    </div>
                  )}
                </div>

                {/* Drawer actions */}
                <div className="p-4 border-t border-border/50 space-y-2">
                  <Btn variant="primary" className="w-full vf-text-caption justify-center">
                    Edit Entity
                  </Btn>
                  <div className="flex gap-2">
                    <Btn variant="ghost" className="flex-1 vf-text-caption">View Provenance</Btn>
                    <Btn variant="danger" className="vf-text-caption">Delete</Btn>
                  </div>
                  <Btn
                    variant="outline"
                    className="w-full vf-text-caption justify-center"
                    onClick={handleExport}
                  >
                    <Download size={12} className="mr-1" />
                    Export Selected
                  </Btn>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center p-8 text-muted-foreground vf-text-body-s">
                Entity not found
              </div>
            )}
          </div>
        )}
      </div>
    </div>
    </PageShell>
  );
}
