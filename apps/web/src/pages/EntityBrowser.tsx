/**
 * Entity Browser — Unified Table + Detail Drawer
 * Design: Refined Enterprise SaaS (Wireframe-matching)
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

const CONF_COLORS = (c: number) =>
  c >= 0.9 ? "text-emerald-700 font-semibold" : c >= 0.7 ? "text-amber-700" : "text-red-600";

const STATUS_COLORS: Record<Entity['status'], string> = {
  validated: "text-emerald-700",
  pending: "text-amber-600",
  draft: "text-muted-foreground",
  deprecated: "text-red-600",
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
    <div className="p-6 h-full flex flex-col">
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

      {/* Error display */}
      {errorMessage && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between">
            <span className="text-red-700 text-sm">{errorMessage}</span>
            <Btn variant="ghost" className="text-[11px]" onClick={() => refetch()}>Retry</Btn>
          </div>
        </div>
      )}

      {/* Filter toolbar */}
      <Toolbar>
        <SearchInput
          placeholder="Search entities…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <select
          className="h-8 px-3 bg-card border border-border rounded-md text-[12px] text-foreground"
          value={selectedType || ''}
          onChange={(e) => setSelectedType(e.target.value as EntityType || null)}
        >
          <option value="">All Types</option>
          <option value="capability">Capability</option>
          <option value="usecase">Use Case</option>
          <option value="persona">Persona</option>
          <option value="valuedriver">Value Driver</option>
        </select>
        <select
          className="h-8 px-3 bg-card border border-border rounded-md text-[12px] text-foreground"
          value={''}
          onChange={() => {}}
        >
          <option value="">All Domains</option>
          {entityList?.availableDomains?.map(d => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <select
          className="h-8 px-3 bg-card border border-border rounded-md text-[12px] text-foreground"
          value={''}
          onChange={() => {}}
        >
          <option value="">All Status</option>
          <option value="validated">Validated</option>
          <option value="pending">Pending</option>
          <option value="draft">Draft</option>
          <option value="deprecated">Deprecated</option>
        </select>
        <Btn variant="ghost" onClick={clearFilters}>Clear Filters</Btn>
      </Toolbar>

      {/* Type legend chips */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {(["capability","usecase","persona","valuedriver"] as EntityType[]).map(t => (
          <button
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
                <Loader2 size={24} className="animate-spin text-blue-600" />
                <span className="ml-2 text-muted-foreground">Loading entities...</span>
              </div>
            ) : (
              <DataTable
                columns={["Entity Name", "Type", "Domain", "Confidence", "Status", "Actions"]}
                rows={entities.map((e: Entity) => {
                  const isSelected = e.id === selectedEntityId;
                  const statusColor = STATUS_COLORS[e.status];
                  return [
                    <span className={`font-semibold ${isSelected ? 'text-blue-700' : 'text-foreground'}`}>{e.name}</span>,
                    <EntityBadge type={mapEntityType(e.type)}/>,
                    <span className="text-muted-foreground text-[11px] font-mono">{e.domain || '—'}</span>,
                    <span className={`text-[12px] ${CONF_COLORS(e.confidence)}`}>{Math.round(e.confidence * 100)}%</span>,
                    <span className={`text-[11px] font-semibold ${statusColor}`}>
                      ● {e.status.charAt(0).toUpperCase() + e.status.slice(1)}
                    </span>,
                    <div className="flex gap-2">
                      <button
                        onClick={() => setSelectedEntityId(e.id)}
                        className={`text-[11px] hover:underline ${isSelected ? 'text-blue-700 font-semibold' : 'text-blue-600'}`}
                      >
                        {isSelected ? 'Selected' : 'View'}
                      </button>
                      <button className="text-muted-foreground/60 text-[11px] hover:underline">Edit</button>
                    </div>,
                  ];
                })}
              />
            )}
            {entities.length === 0 && !isLoading && (
              <div className="text-center p-8 text-muted-foreground">
                {searchQuery || selectedType ? 'No entities match your filters.' : 'No entities found.'}
              </div>
            )}
          </SectionCard>
        </div>

        {/* Detail Drawer */}
        {selectedEntityId && (
          <div className="absolute top-[180px] right-6 w-[320px] bottom-6 bg-card border border-border rounded-lg shadow-lg z-10 flex flex-col overflow-hidden">
            {isLoadingEntity ? (
              <div className="flex items-center justify-center p-8 flex-1">
                <Loader2 size={20} className="animate-spin text-blue-600" />
              </div>
            ) : selectedEntity ? (
              <>
                {/* Drawer header */}
                <div className="flex items-start justify-between p-4 border-b border-border/50">
                  <div className="flex-1 min-w-0">
                    <div className="text-[14px] font-bold text-foreground truncate">{selectedEntity.name}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <EntityBadge type={mapEntityType(selectedEntity.type)}/>
                    </div>
                  </div>
                  <button
                    onClick={() => setSelectedEntityId(null)}
                    className="text-muted-foreground/60 hover:text-muted-foreground transition-colors ml-2"
                  >
                    <X size={16}/>
                  </button>
                </div>

                {/* Status bar */}
                <div className="flex items-center gap-4 px-4 py-2 bg-muted/20 border-b border-border/50 text-[11px]">
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
                    <button
                      key={tab}
                      onClick={() => setDrawerTab(tab)}
                      className={`px-3 py-2.5 text-[11px] font-semibold border-b-2 -mb-px transition-colors ${
                        drawerTab === tab ? "border-blue-600 text-blue-700" : "border-transparent text-muted-foreground hover:text-foreground"
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
                        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">Description</div>
                        <p className="text-[12px] text-muted-foreground leading-relaxed">
                          {selectedEntity.description || "No description available."}
                        </p>
                      </div>
                      <div>
                        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">Entity ID</div>
                        <div className="text-[11px] text-muted-foreground font-mono break-all">{selectedEntity.id}</div>
                      </div>
                      {selectedEntity.properties && Object.keys(selectedEntity.properties).length > 0 && (
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-2">Properties</div>
                          <ul className="space-y-1">
                            {Object.entries(selectedEntity.properties).slice(0, 5).map(([key, value]) => (
                              <li key={key} className="flex items-start gap-2 text-[11px] text-muted-foreground">
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
                    <div className="text-[12px] text-muted-foreground italic">
                      Relationships will be displayed here. Connect to graph API for related entities.
                    </div>
                  )}
                  {drawerTab === "Source" && (
                    <div className="space-y-3">
                      <div>
                        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">Source System</div>
                        <div className="text-[12px] text-muted-foreground">
                          {selectedEntity.sourceName || "Unknown source"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">Domain</div>
                        <div className="text-[12px] text-muted-foreground">
                          {selectedEntity.domain || "Unclassified"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">Extraction Job</div>
                        <div className="text-[11px] text-muted-foreground font-mono">
                          {selectedEntity.extractionJobId || "N/A"}
                        </div>
                      </div>
                    </div>
                  )}
                  {drawerTab === "History" && (
                    <div className="text-[12px] text-muted-foreground italic">
                      {selectedEntity.createdAt
                        ? `Created: ${new Date(selectedEntity.createdAt).toLocaleString()}`
                        : "No creation timestamp available."
                      }
                    </div>
                  )}
                </div>

                {/* Drawer actions */}
                <div className="p-4 border-t border-border/50 space-y-2">
                  <Btn variant="primary" className="w-full text-[11px] justify-center">
                    Edit Entity
                  </Btn>
                  <div className="flex gap-2">
                    <Btn variant="ghost" className="flex-1 text-[11px]">View Provenance</Btn>
                    <Btn variant="danger" className="text-[11px]">Delete</Btn>
                  </div>
                  <Btn
                    variant="outline"
                    className="w-full text-[11px] justify-center"
                    onClick={handleExport}
                  >
                    <Download size={12} className="mr-1" />
                    Export Selected
                  </Btn>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center p-8 text-muted-foreground text-[12px]">
                Entity not found
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
