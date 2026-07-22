/**
 * OntologyEditor — Visual ontology schema editing environment
 *
 * Three-panel layout production layout:
 * - Left: Type Tree (hierarchical type browser)
 * - Center: Property Editor (type definition editing)
 * - Right: Relationship Map (visual relationship graph)
 *
 * Features:
 * - Add/Edit/Delete type definitions
 * - Add/Edit/Delete properties
 * - Visual relationship management
 * - Validate and Publish workflow
 * - Undo/Redo support
 * - Import/Export ontology
 */

import { useEffect, useCallback, useState } from 'react';
import { Check, X, AlertCircle, Undo2, Redo2, Download, Upload, Plus, GitBranch, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';
import { TypeTree, PropertyEditor, RelationshipMap } from '@/components/ontology';
import {
  useOntologySchema,
  useValidateOntology,
  usePublishOntology,
  useImportOntology,
  useCreateOntologyType,
  useUpdateOntologyType,
  useDeleteOntologyType,
  useAddOntologyProperty,
  useRemoveOntologyProperty,
  useAddTypeRelationship,
  useRemoveTypeRelationship,
  type ValidationResult,
} from '@/hooks/useOntology';
import useOntologyStore from '@/stores/ontologyStore';
import { toast } from 'sonner';
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, Btn } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { Textarea } from "@/components/ui/textarea";
import { ErrorState } from "@/components/states/ErrorState";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function OntologyEditor() {
  // Data fetching
  const { data: schema, isLoading, error } = useOntologySchema();

  // Mutations
  const validateMutation = useValidateOntology();
  const publishMutation = usePublishOntology();
  const importMutation = useImportOntology();

  // Individual CRUD mutations for granular persistence
  const createTypeMutation = useCreateOntologyType();
  const updateTypeMutation = useUpdateOntologyType();
  const deleteTypeMutation = useDeleteOntologyType();
  const addPropertyMutation = useAddOntologyProperty();
  const removePropertyMutation = useRemoveOntologyProperty();
  const addRelationshipMutation = useAddTypeRelationship();
  const removeRelationshipMutation = useRemoveTypeRelationship();

  // State for add-relationship dialog
  const [showAddRelDialog, setShowAddRelDialog] = useState(false);
  const [newRelSource, setNewRelSource] = useState('');
  const [newRelTarget, setNewRelTarget] = useState('');
  const [newRelType, setNewRelType] = useState('RELATES_TO');

  // Local state
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importJson, setImportJson] = useState('');

  // Store state and actions
  const {
    selectedTypeId,
    hasUnsavedChanges,
    canUndo,
    canRedo,
    validationResult,
    isValidating,
    isPublishing,
    showRelationshipMap,
    draftTypes,
    draftRelationships,
    initializeFromSchema,
    selectType,
    undo,
    redo,
    setValidationResult,
    setIsValidating,
    setIsPublishing,
    toggleRelationshipMap,
    setImportDialogOpen,
  } = useOntologyStore();

  // Initialize store when schema loads
  useEffect(() => {
    if (schema) {
      initializeFromSchema(schema.types, schema.relationships);
    }
  }, [schema, initializeFromSchema]);

  // Get selected type
  const selectedType = selectedTypeId
    ? draftTypes.get(selectedTypeId) || null
    : null;

  // Convert draft maps to arrays for components
  const types = Array.from(draftTypes.values());
  const relationships = Array.from(draftRelationships.values());

  // Handle validate
  const handleValidate = useCallback(async (): Promise<ValidationResult | null> => {
    if (!schema) return null;

    setIsValidating(true);
    try {
      const currentSchema = {
        ...schema,
        types,
        relationships,
      };
      const result = await validateMutation.mutateAsync(currentSchema);
      setValidationResult(result);

      if (result.valid) {
        toast.success('Ontology is valid', {
          description: result.warnings.length > 0
            ? `${result.warnings.length} warning${result.warnings.length > 1 ? 's' : ''} found`
            : 'No issues found',
        });
      } else {
        toast.error('Validation failed', {
          description: `${result.errors.length} error${result.errors.length > 1 ? 's' : ''} found`,
        });
      }

      return result;
    } catch (err) {
      toast.error('Validation failed', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
      return null;
    } finally {
      setIsValidating(false);
    }
  }, [schema, types, relationships, validateMutation, setValidationResult, setIsValidating]);

  // Handle publish
  const handlePublish = useCallback(async () => {
    if (!schema) return;

    // First validate and use the fresh result returned by the mutation.
    const latestValidationResult = await handleValidate();
    if (!latestValidationResult?.valid) {
      toast.error('Cannot publish', { description: 'Please fix validation errors first' });
      return;
    }

    setIsPublishing(true);
    try {
      const currentSchema = {
        ...schema,
        types,
        relationships,
      };
      const result = await publishMutation.mutateAsync(currentSchema);
      toast.success('Ontology published', {
        description: `Version ${result.version} published at ${new Date(result.publishedAt).toLocaleString()}`,
      });
    } catch (err) {
      toast.error('Publish failed', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setIsPublishing(false);
    }
  }, [schema, types, relationships, publishMutation, setIsPublishing, handleValidate]);

  // Handle import
  const handleImport = useCallback(async () => {
    if (!importJson.trim()) {
      toast.error('No data to import');
      return;
    }

    try {
      const importedSchema = await importMutation.mutateAsync(importJson);
      initializeFromSchema(importedSchema.types, importedSchema.relationships);
      setShowImportDialog(false);
      setImportJson('');
      toast.success('Ontology imported successfully');
    } catch (err) {
      toast.error('Import failed', {
        description: err instanceof Error ? err.message : 'Invalid JSON',
      });
    }
  }, [importJson, importMutation, initializeFromSchema]);

  // Loading state
  if (isLoading) {
    return (
      <PageShell fullWidth>
        <PageHeader
          breadcrumbs={[{ label: "Discover" }, { label: "Knowledge" }, { label: "Ontology" }]}
          title="Ontology Editor"
          subtitle="Define and manage the knowledge model ontology"
        />
        <div className="flex items-center justify-center h-[400px]">
          <div className="w-8 h-8 rounded-full border-2 border-muted-foreground border-t-foreground animate-spin" />
          <span className="ml-3 text-sm text-muted-foreground">Loading ontology schema...</span>
        </div>
      </PageShell>
    );
  }

  // Error state
  if (error) {
    return (
      <PageShell fullWidth>
        <PageHeader
          breadcrumbs={[{ label: "Discover" }, { label: "Knowledge" }, { label: "Ontology" }]}
          title="Ontology Editor"
          subtitle="Define and manage the knowledge model ontology"
        />
        <ErrorState
          title="Failed to load ontology"
          error={error}
        />
      </PageShell>
    );
  }

  return (
    <PageShell fullWidth className="h-[calc(100vh-64px)] flex flex-col">
      {/* Header */}
      <PageHeader
        breadcrumbs={[{ label: "Discover" }, { label: "Knowledge" }, { label: "Ontology" }]}
        title="Ontology Editor"
        subtitle="Define and manage the knowledge model ontology"
        actions={
          <div className="flex items-center gap-2">
            {/* Validation indicator */}
            {validationResult && (
              <div className={cn(
                "flex items-center gap-1.5 px-2 py-1 rounded-md vf-text-caption font-medium",
                validationResult.valid
                  ? "bg-success/10 text-success"
                  : "bg-destructive/10 text-destructive"
              )}>
                {validationResult.valid ? <Check size={12} /> : <X size={12} />}
                {validationResult.valid ? 'Valid' : `${validationResult.errors.length} errors`}
              </div>
            )}

            {/* Undo/Redo */}
            <div className="flex items-center gap-1 border-r border-border pr-2 mr-1">
              <Btn variant="ghost" onClick={undo} disabled={!canUndo}>
                <Undo2 size={12} />
              </Btn>
              <Btn variant="ghost" onClick={redo} disabled={!canRedo}>
                <Redo2 size={12} />
              </Btn>
            </div>

            {/* Validate button */}
            <Btn variant="outline" onClick={handleValidate} disabled={isValidating}>
              {isValidating ? (
                <>
                  <div className="w-3 h-3 rounded-full border border-current border-t-transparent animate-spin mr-1" />
                  Validating...
                </>
              ) : (
                <>
                  <Shield size={12} className="mr-1" />
                  Validate
                </>
              )}
            </Btn>

            {/* Publish button */}
            <Btn
              variant="primary"
              onClick={handlePublish}
              disabled={isPublishing || !hasUnsavedChanges}
            >
              {isPublishing ? (
                <>
                  <div className="w-3 h-3 rounded-full border border-current border-t-transparent animate-spin mr-1" />
                  Publishing...
                </>
              ) : (
                <>
                  <Check size={12} className="mr-1" />
                  Publish
                </>
              )}
            </Btn>
          </div>
        }
      />

      {/* Toolbar */}
      <div className="flex items-center gap-2 mb-4 py-2 border-b border-border">
        <Btn variant="ghost" onClick={() => setShowAddRelDialog(true)}>
          <Plus size={12} className="mr-1" />
          Add Relation
        </Btn>
        <Btn variant="ghost" onClick={() => setShowImportDialog(true)}>
          <Upload size={12} className="mr-1" />
          Import
        </Btn>
        <div className="flex-1" />
        <Btn variant="ghost" onClick={undo} disabled={!canUndo}>
          <Undo2 size={12} className="mr-1" />
          Undo
        </Btn>
        <Btn variant="ghost" onClick={redo} disabled={!canRedo}>
          <Redo2 size={12} className="mr-1" />
          Redo
        </Btn>
        <Btn variant="ghost" onClick={toggleRelationshipMap}>
          <GitBranch size={12} className="mr-1" />
          {showRelationshipMap ? 'Hide Map' : 'Show Map'}
        </Btn>
      </div>

      {/* Three-panel layout */}
      <div className="flex-1 grid gap-4 min-h-0" style={{ gridTemplateColumns: showRelationshipMap ? '280px 1fr 280px' : '280px 1fr' }}>
        {/* Left: Type Tree */}
        <SectionCard noPad className="h-full overflow-hidden">
          <TypeTree types={types} />
        </SectionCard>

        {/* Center: Property Editor */}
        <SectionCard noPad className="h-full overflow-hidden">
          <PropertyEditor type={selectedType} />
        </SectionCard>

        {/* Right: Relationship Map (conditional) */}
        {showRelationshipMap && (
          <SectionCard noPad className="h-full overflow-hidden">
            <RelationshipMap
              types={types}
              relationships={relationships}
              selectedTypeId={selectedTypeId}
              onSelectType={selectType}
            />
          </SectionCard>
        )}
      </div>

      {/* Validation Results Panel */}
      {validationResult && (validationResult.errors.length > 0 || validationResult.warnings.length > 0) && (
        <div className="mt-4 p-3 border rounded-lg bg-muted/30">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle size={14} className={validationResult.errors.length > 0 ? "text-destructive" : "text-warning"} />
            <span className="vf-text-body-s font-semibold">
              {validationResult.errors.length > 0
                ? `${validationResult.errors.length} error${validationResult.errors.length > 1 ? 's' : ''}`
                : `${validationResult.warnings.length} warning${validationResult.warnings.length > 1 ? 's' : ''}`}
            </span>
          </div>
          <div className="space-y-1 max-h-[120px] overflow-y-auto">
            {validationResult.errors.map((error) => (
              <div key={error.message} className="flex items-start gap-2 vf-text-caption text-destructive">
                <X size={12} className="mt-0.5 shrink-0" />
                <span>{error.message}</span>
              </div>
            ))}
            {validationResult.warnings.map((warning) => (
              <div key={warning.message} className="flex items-start gap-2 vf-text-caption text-warning">
                <AlertCircle size={12} className="mt-0.5 shrink-0" />
                <span>{warning.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add Relationship Dialog */}
      {showAddRelDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg shadow-lg w-[400px] max-w-[90vw]">
            <div className="p-4 border-b border-border">
              <h3 className="text-sm font-semibold">Add Relationship</h3>
              <p className="vf-text-body-s text-muted-foreground mt-1">
                Define a relationship between two ontology types
              </p>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <label className="vf-text-caption font-semibold text-muted-foreground block mb-1">Source Type</label>
                <Select value={newRelSource} onValueChange={setNewRelSource}>
                  <SelectTrigger className="w-full vf-text-body-s">
                    <SelectValue placeholder="Select source type..." />
                  </SelectTrigger>
                  <SelectContent>
                    {types.map(t => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="vf-text-caption font-semibold text-muted-foreground block mb-1">Relationship Type</label>
                <Select value={newRelType} onValueChange={setNewRelType}>
                  <SelectTrigger className="w-full vf-text-body-s">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {['RELATES_TO', 'DEPENDS_ON', 'ENABLES', 'EXTENDS', 'CONTAINS', 'PART_OF'].map(rt => (
                      <SelectItem key={rt} value={rt}>{rt}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="vf-text-caption font-semibold text-muted-foreground block mb-1">Target Type</label>
                <Select value={newRelTarget} onValueChange={setNewRelTarget}>
                  <SelectTrigger className="w-full vf-text-body-s">
                    <SelectValue placeholder="Select target type..." />
                  </SelectTrigger>
                  <SelectContent>
                    {types.map(t => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="p-4 border-t border-border flex justify-end gap-2">
              <Btn variant="ghost" onClick={() => setShowAddRelDialog(false)}>
                Cancel
              </Btn>
              <Btn
                variant="primary"
                onClick={async () => {
                  if (!newRelSource || !newRelTarget) {
                    toast.error('Please select both source and target types');
                    return;
                  }
                  try {
                    await addRelationshipMutation.mutateAsync({
                      sourceTypeId: newRelSource,
                      targetTypeId: newRelTarget,
                      relationshipType: newRelType as "depends_on" | "extends" | "relates_to" | "contains",
                      cardinality: "one_to_many" as const,
                    });
                    toast.success('Relationship added');
                    setShowAddRelDialog(false);
                    setNewRelSource('');
                    setNewRelTarget('');
                  } catch (err) {
                    toast.error('Failed to add relationship');
                  }
                }}
                disabled={addRelationshipMutation.isPending}
              >
                {addRelationshipMutation.isPending ? 'Adding...' : 'Add Relationship'}
              </Btn>
            </div>
          </div>
        </div>
      )}
      {/* Import Dialog */}
      {showImportDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg shadow-lg w-[500px] max-w-[90vw]">
            <div className="p-4 border-b border-border">
              <h3 className="text-sm font-semibold">Import Ontology</h3>
              <p className="vf-text-body-s text-muted-foreground mt-1">
                Paste JSON ontology schema to import
              </p>
            </div>
            <div className="p-4">
              <Textarea
                value={importJson}
                onChange={(e) => setImportJson(e.target.value)}
                placeholder={`{\n  "types": [...],\n  "relationships": [...]\n}`}
                rows={10}
                className="w-full vf-text-body-s font-mono"
              />
            </div>
            <div className="p-4 border-t border-border flex justify-end gap-2">
              <Btn variant="ghost" onClick={() => setShowImportDialog(false)}>
                Cancel
              </Btn>
              <Btn variant="primary" onClick={handleImport} disabled={importMutation.isPending}>
                {importMutation.isPending ? 'Importing...' : 'Import'}
              </Btn>
            </div>
          </div>
        </div>
      )}
    </PageShell>
  );
}
