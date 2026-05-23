/**
 * PropertyEditor — Form for editing ontology type properties
 *
 * Center panel of the Ontology Editor showing:
 * - Type name and description editing
 * - List of properties with their types, constraints
 * - Add/Edit/Delete property controls
 * - Validation indicators
 */

import { useState, useCallback } from 'react';
import { Plus, Trash2, AlertCircle, Check, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import useOntologyStore from '@/stores/ontologyStore';
import type { OntologyType, OntologyProperty, PropertyConstraints } from '@/hooks/useOntology';
import { Btn } from "@/components/ui/fabric";

function createPropertyId(name: string): string {
  const normalizedName = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'property';

  return `prop_${normalizedName}_${Date.now().toString(36)}`;
}

interface PropertyEditorProps {
  type: OntologyType | null;
  className?: string;
}

export function PropertyEditor({ type, className }: PropertyEditorProps) {
  const {
    selectedPropertyId,
    selectProperty,
    addPropertyToDraft,
    updatePropertyInDraft,
    removePropertyFromDraft,
  } = useOntologyStore();

  const [isAddingProperty, setIsAddingProperty] = useState(false);
  const [newProperty, setNewProperty] = useState<Partial<OntologyProperty>>({
    type: 'string',
    required: false,
  });

  const handleAddProperty = useCallback(() => {
    if (!type || !newProperty.name) return;

    const property: OntologyProperty = {
      id: createPropertyId(newProperty.name),
      name: newProperty.name,
      type: newProperty.type || 'string',
      description: newProperty.description,
      required: newProperty.required || false,
      defaultValue: newProperty.defaultValue,
      constraints: newProperty.constraints,
    };

    addPropertyToDraft(type.id, property);
    setIsAddingProperty(false);
    setNewProperty({ type: 'string', required: false });
  }, [type, newProperty, addPropertyToDraft]);

  if (!type) {
    return (
      <div className={cn("flex flex-col items-center justify-center h-full p-8", className)}>
        <p className="text-sm text-muted-foreground">Select a type to edit its properties</p>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center justify-between">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            Property Editor
          </h3>
          <Btn variant="ghost" onClick={() => setIsAddingProperty(true)} disabled={isAddingProperty}>
            <Plus size={12} /> Add Property
          </Btn>
        </div>
      </div>

      {/* Type Info */}
      <div className="px-4 py-3 border-b border-border bg-muted/30">
        <div className="space-y-2">
          <div>
            <label htmlFor="type-name" className="text-[10px] font-medium text-muted-foreground uppercase">Type Name</label>
            <input
              id="type-name"
              type="text"
              value={type.name}
              readOnly
              className="w-full px-2 py-1 text-[13px] font-semibold bg-transparent border border-border rounded"
            />
          </div>
          <div>
            <label htmlFor="type-description" className="text-[10px] font-medium text-muted-foreground uppercase">Description</label>
            <textarea
              id="type-description"
              value={type.description}
              readOnly
              rows={2}
              className="w-full px-2 py-1 text-[12px] bg-transparent border border-border rounded resize-none"
            />
          </div>
        </div>
      </div>

      {/* Properties List */}
      <div className="flex-1 overflow-y-auto p-4">
        {isAddingProperty && (
          <NewPropertyForm
            property={newProperty}
            onChange={setNewProperty}
            onSave={handleAddProperty}
            onCancel={() => {
              setIsAddingProperty(false);
              setNewProperty({ type: 'string', required: false });
            }}
          />
        )}

        <div className="space-y-2">
          {type.properties.map((property, index) => (
            <PropertyRow
              key={property.id}
              property={property}
              index={index}
              isSelected={selectedPropertyId === property.id}
              onSelect={() => selectProperty(property.id)}
              onUpdate={(updated) => updatePropertyInDraft(type.id, updated)}
              onDelete={() => removePropertyFromDraft(type.id, property.id)}
            />
          ))}

          {type.properties.length === 0 && !isAddingProperty && (
            <div className="text-center py-8">
              <p className="text-sm text-muted-foreground">No properties defined</p>
              <p className="text-[11px] text-muted-foreground mt-1">
                Click "Add Property" to add one
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface PropertyRowProps {
  property: OntologyProperty;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
  onUpdate: (property: OntologyProperty) => void;
  onDelete: () => void;
}

function PropertyRow({ property, index, isSelected, onSelect, onUpdate, onDelete }: PropertyRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedProperty, setEditedProperty] = useState(property);

  const handleSave = () => {
    onUpdate(editedProperty);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedProperty(property);
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className="p-3 border border-primary/30 rounded-lg bg-primary/5">
        <PropertyFormFields
          property={editedProperty}
          onChange={(prop) => setEditedProperty(prop as OntologyProperty)}
        />
        <div className="flex justify-end gap-2 mt-3">
          <Btn variant="ghost" onClick={handleCancel}>Cancel</Btn>
          <Btn variant="primary" onClick={handleSave}>
            <Check size={12} /> Save
          </Btn>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={onSelect}
      className={cn(
        "p-3 border rounded-lg cursor-pointer transition-colors",
        isSelected
          ? "border-primary/30 bg-primary/5"
          : "border-border hover:border-primary/20 hover:bg-muted/30"
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-muted-foreground w-5">{index + 1}</span>
            <span className="text-[13px] font-semibold text-foreground">{property.name}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
              {property.type}
            </span>
            {property.required && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-destructive/10 text-destructive">
                required
              </span>
            )}
          </div>
          {property.description && (
            <p className="text-[11px] text-muted-foreground mt-1 ml-7">{property.description}</p>
          )}
          {property.constraints && Object.keys(property.constraints).length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2 ml-7">
              {property.constraints.minLength !== undefined && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground">
                  min: {property.constraints.minLength}
                </span>
              )}
              {property.constraints.maxLength !== undefined && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground">
                  max: {property.constraints.maxLength}
                </span>
              )}
              {property.constraints.enum && (
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground">
                  enum: {property.constraints.enum.join(', ')}
                </span>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 ml-2">
          <Btn variant="ghost" className="text-[11px]" onClick={() => setIsEditing(true)}>
            Edit
          </Btn>
          <Btn variant="ghost" className="text-destructive" onClick={() => onDelete()}>
            <Trash2 size={12} />
          </Btn>
        </div>
      </div>
    </div>
  );
}

interface PropertyFormFieldsProps {
  property: Partial<OntologyProperty>;
  onChange: (property: Partial<OntologyProperty>) => void;
}

function PropertyFormFields({ property, onChange }: PropertyFormFieldsProps) {
  const updateField = <K extends keyof OntologyProperty>(
    field: K,
    value: OntologyProperty[K]
  ) => {
    onChange({ ...property, [field]: value });
  };

  return (
    <div className="space-y-3">
      <div>
        <label htmlFor="prop-name" className="text-[10px] font-medium text-muted-foreground uppercase">Name</label>
        <input
          id="prop-name"
          type="text"
          value={property.name || ''}
          onChange={(e) => updateField('name', e.target.value)}
          placeholder="property_name"
          aria-label="Property name"
          className="w-full px-2 py-1.5 text-[12px] bg-card border border-border rounded"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="prop-type" className="text-[10px] font-medium text-muted-foreground uppercase">Type</label>
          <select
            id="prop-type"
            value={property.type || 'string'}
            onChange={(e) => updateField('type', e.target.value as OntologyProperty['type'])}
            aria-label="Property type"
            className="w-full px-2 py-1.5 text-[12px] bg-card border border-border rounded"
          >
            <option value="string">string</option>
            <option value="number">number</option>
            <option value="boolean">boolean</option>
            <option value="date">date</option>
            <option value="array">array</option>
            <option value="object">object</option>
            <option value="reference">reference</option>
          </select>
        </div>

        <div className="flex items-end">
          <label htmlFor="prop-required" className="flex items-center gap-2 cursor-pointer">
            <input
              id="prop-required"
              type="checkbox"
              checked={property.required || false}
              onChange={(e) => updateField('required', e.target.checked)}
              aria-label="Property required"
              className="rounded border-border"
            />
            <span className="text-[12px]">Required</span>
          </label>
        </div>
      </div>

      <div>
        <label htmlFor="prop-description" className="text-[10px] font-medium text-muted-foreground uppercase">Description</label>
        <input
          id="prop-description"
          type="text"
          value={property.description || ''}
          onChange={(e) => updateField('description', e.target.value)}
          placeholder="What this property represents"
          aria-label="Property description"
          className="w-full px-2 py-1.5 text-[12px] bg-card border border-border rounded"
        />
      </div>

      {property.type === 'string' && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="prop-min-length" className="text-[10px] font-medium text-muted-foreground uppercase">Min Length</label>
            <input
              id="prop-min-length"
              type="number"
              value={property.constraints?.minLength || ''}
              onChange={(e) => {
                const val = e.target.value ? parseInt(e.target.value) : undefined;
                onChange({
                  ...property,
                  constraints: { ...property.constraints, minLength: val },
                });
              }}
              aria-label="Minimum length"
              className="w-full px-2 py-1.5 text-[12px] bg-card border border-border rounded"
            />
          </div>
          <div>
            <label htmlFor="prop-max-length" className="text-[10px] font-medium text-muted-foreground uppercase">Max Length</label>
            <input
              id="prop-max-length"
              type="number"
              value={property.constraints?.maxLength || ''}
              onChange={(e) => {
                const val = e.target.value ? parseInt(e.target.value) : undefined;
                onChange({
                  ...property,
                  constraints: { ...property.constraints, maxLength: val },
                });
              }}
              aria-label="Maximum length"
              className="w-full px-2 py-1.5 text-[12px] bg-card border border-border rounded"
            />
          </div>
        </div>
      )}

      {property.type === 'number' && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="prop-min-value" className="text-[10px] font-medium text-muted-foreground uppercase">Min Value</label>
            <input
              id="prop-min-value"
              type="number"
              value={property.constraints?.min ?? ''}
              onChange={(e) => {
                const val = e.target.value !== '' ? parseFloat(e.target.value) : undefined;
                onChange({
                  ...property,
                  constraints: { ...property.constraints, min: val },
                });
              }}
              aria-label="Minimum value"
              className="w-full px-2 py-1.5 text-[12px] bg-card border border-border rounded"
            />
          </div>
          <div>
            <label htmlFor="prop-max-value" className="text-[10px] font-medium text-muted-foreground uppercase">Max Value</label>
            <input
              id="prop-max-value"
              type="number"
              value={property.constraints?.max ?? ''}
              onChange={(e) => {
                const val = e.target.value !== '' ? parseFloat(e.target.value) : undefined;
                onChange({
                  ...property,
                  constraints: { ...property.constraints, max: val },
                });
              }}
              aria-label="Maximum value"
              className="w-full px-2 py-1.5 text-[12px] bg-card border border-border rounded"
            />
          </div>
        </div>
      )}

      {property.type === 'string' && (
        <div>
          <label htmlFor="prop-enum" className="text-[10px] font-medium text-muted-foreground uppercase">Enum Values (comma-separated)</label>
          <input
            id="prop-enum"
            type="text"
            value={property.constraints?.enum?.join(', ') || ''}
            onChange={(e) => {
              const val = e.target.value
                ? e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                : undefined;
              onChange({
                ...property,
                constraints: { ...property.constraints, enum: val },
              });
            }}
            placeholder="value1, value2, value3"
            aria-label="Enum values"
            className="w-full px-2 py-1.5 text-[12px] bg-card border border-border rounded"
          />
        </div>
      )}
    </div>
  );
}

interface NewPropertyFormProps {
  property: Partial<OntologyProperty>;
  onChange: (property: Partial<OntologyProperty>) => void;
  onSave: () => void;
  onCancel: () => void;
}

function NewPropertyForm({ property, onChange, onSave, onCancel }: NewPropertyFormProps) {
  return (
    <div className="p-3 border border-primary/30 rounded-lg bg-primary/5 mb-3">
      <h4 className="text-[12px] font-semibold mb-3">New Property</h4>
      <PropertyFormFields property={property} onChange={onChange} />
      <div className="flex justify-end gap-2 mt-3">
        <Btn variant="ghost" onClick={onCancel}>Cancel</Btn>
        <Btn variant="primary" onClick={onSave}>
          <Plus size={12} /> Add
        </Btn>
      </div>
    </div>
  );
}

export default PropertyEditor;
