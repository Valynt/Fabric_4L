/**
 * useOntology.ts - Ontology management hooks with defensive programming
 * 
 * DEFENSIVE PROGRAMMING: All 7 mandates applied:
 * - M1: NULL/UNDEFINED SAFETY - Optional chaining and nullish coalescing throughout
 * - M2: TYPE SAFETY - Zod runtime validation replaces all `as` assertions
 * - M3: ERROR HANDLING - All mutations have onError with context logging
 * - M4: INPUT VALIDATION - typeId, propertyId validated with Zod schemas
 * - M5: RACE CONDITION ELIMINATION - queryClient invalidation after success
 * - M6: RESOURCE LEAK PREVENTION - N/A (React Query manages caching)
 * - M7: BOUNDS SAFETY - All array accesses have length checks
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import { apiGet, apiPost, apiPut, apiDelete } from '@/api/typedClient';
import { QK } from './queryKeys';
import { STALE_TIME } from './useApiShared';
import { createFeatureLogger } from '@/lib/telemetry';

// Layer key for Layer 2 Extraction API
const LAYER2: 'l2' = 'l2';

// ============================================================================
// MANDATE 3: ERROR HANDLING - Feature Logger
// ============================================================================

const log = createFeatureLogger('useOntology');

// ============================================================================
// MANDATE 4: INPUT VALIDATION - Zod Schemas
// ============================================================================

/** Type ID must be non-empty string */
const TypeIdSchema = z.string().min(1, 'Type ID is required');

/** Property ID must be non-empty string */
const PropertyIdSchema = z.string().min(1, 'Property ID is required');

/** Relationship ID must be non-empty string */
const RelationshipIdSchema = z.string().min(1, 'Relationship ID is required');

/** Ontology name validation */
const OntologyNameSchema = z.string().min(1).max(255);

/** Version string validation */
const VersionSchema = z.string().min(1).regex(/^\d+\.\d+\.\d+/, 'Version must be semantic (e.g., 1.0.0)');

/**
 * Validates typeId and returns normalized value or null
 */
function validateTypeId(typeId: string | null | undefined): string | null {
  if (typeId === null || typeId === undefined) return null;
  const result = TypeIdSchema.safeParse(typeId);
  if (!result.success) {
    log.error('Invalid typeId', { typeId, error: result.error.message });
    return null;
  }
  return result.data;
}

/**
 * Validates propertyId and returns normalized value
 */
function validatePropertyId(propertyId: string): string {
  const result = PropertyIdSchema.safeParse(propertyId);
  if (!result.success) {
    const error = new Error(`Invalid propertyId: ${result.error.message}`);
    log.error('Property ID validation failed', { propertyId, error: result.error.message });
    throw error;
  }
  return result.data;
}

// ============================================================================
// MANDATE 2: TYPE SAFETY - Zod Schemas for Runtime Validation
// ============================================================================

const PropertyTypeSchema = z.enum(['string', 'number', 'boolean', 'date', 'array', 'object', 'reference']);

const PropertyConstraintsSchema = z.object({
  minLength: z.number().optional(),
  maxLength: z.number().optional(),
  min: z.number().optional(),
  max: z.number().optional(),
  pattern: z.string().optional(),
  enum: z.array(z.string()).optional(),
}).strict().optional();

const OntologyPropertySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  type: PropertyTypeSchema,
  description: z.string().optional(),
  required: z.boolean(),
  defaultValue: z.unknown().optional(),
  constraints: PropertyConstraintsSchema,
  referenceTypeId: z.string().optional(),
});

const RelationshipTypeSchema = z.enum(['depends_on', 'extends', 'relates_to', 'contains']);
const CardinalitySchema = z.enum(['one_to_one', 'one_to_many', 'many_to_many']);

const TypeRelationshipSchema = z.object({
  id: z.string().min(1),
  sourceTypeId: z.string().min(1),
  targetTypeId: z.string().min(1),
  relationshipType: RelationshipTypeSchema,
  description: z.string().optional(),
  cardinality: CardinalitySchema,
});

const OntologyTypeSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  description: z.string(),
  properties: z.array(OntologyPropertySchema),
  parentTypeId: z.string().optional(),
  childrenTypeIds: z.array(z.string()).optional(),
  createdAt: z.string(),
  updatedAt: z.string(),
  version: z.number(),
});

const OntologySchemaSchema = z.object({
  types: z.array(OntologyTypeSchema),
  relationships: z.array(TypeRelationshipSchema),
  version: z.string(),
  publishedAt: z.string().optional(),
  publishedBy: z.string().optional(),
});

const ValidationErrorSchema = z.object({
  typeId: z.string().optional(),
  propertyId: z.string().optional(),
  relationshipId: z.string().optional(),
  message: z.string(),
  code: z.string(),
});

const ValidationWarningSchema = z.object({
  typeId: z.string().optional(),
  propertyId: z.string().optional(),
  message: z.string(),
  code: z.string(),
});

const ValidationResultSchema = z.object({
  valid: z.boolean(),
  errors: z.array(ValidationErrorSchema),
  warnings: z.array(ValidationWarningSchema),
});

// ============================================================================
// TypeScript Types (inferred from schemas)
// ============================================================================

export type OntologyProperty = z.infer<typeof OntologyPropertySchema>;
export type PropertyConstraints = z.infer<typeof PropertyConstraintsSchema>;
export type TypeRelationship = z.infer<typeof TypeRelationshipSchema>;
export type OntologyType = z.infer<typeof OntologyTypeSchema>;
export type OntologySchema = z.infer<typeof OntologySchemaSchema>;
export type ValidationError = z.infer<typeof ValidationErrorSchema>;
export type ValidationWarning = z.infer<typeof ValidationWarningSchema>;
export type ValidationResult = z.infer<typeof ValidationResultSchema>;

// Fetch full ontology schema
export function useOntologySchema() {
  return useQuery({
    queryKey: QK.ontology.schema(),
    queryFn: async (): Promise<OntologySchema> => {
      const response = await apiGet<OntologySchema>(LAYER2, '/v1/ontology/schema');
      return OntologySchemaSchema.parse(response.data);
    },
    staleTime: STALE_TIME.reference,
  });
}

// Create new type
export function useCreateOntologyType() {
  const queryClient = useQueryClient();

  return useMutation<OntologyType, Error, Omit<OntologyType, 'id' | 'createdAt' | 'updatedAt' | 'version'>>({
    mutationFn: async (newType): Promise<OntologyType> => {
      // MANDATE 4: Validate name
      const nameResult = OntologyNameSchema.safeParse(newType.name);
      if (!nameResult.success) {
        throw new Error(`Invalid type name: ${nameResult.error.message}`);
      }

      const response = await apiPost<OntologyType>(LAYER2, '/v1/ontology/schema/types', {
        name: newType.name,
        description: newType.description,
        parent_type_id: newType.parentTypeId,
      });
      
      // MANDATE 2: Runtime validation
      const result = OntologyTypeSchema.safeParse(response.data);
      if (!result.success) {
        log.error('Failed to parse created type', { error: result.error.message });
        throw new Error('Invalid response when creating type');
      }
      
      return result.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.ontology.schema() });
    },
    onError: (error, variables) => {
      log.error('Failed to create ontology type', { name: variables.name, error: error.message });
    },
  });
}

// Update type
export function useUpdateOntologyType() {
  const queryClient = useQueryClient();

  return useMutation<OntologyType, Error, OntologyType>({
    mutationFn: async (updatedType): Promise<OntologyType> => {
      // MANDATE 4: Validate typeId
      const validatedId = validateTypeId(updatedType.id);
      if (validatedId === null) {
        throw new Error('Invalid typeId: cannot update type');
      }

      const response = await apiPut<OntologyType>(LAYER2, `/v1/ontology/schema/types/${validatedId}`, {
        name: updatedType.name,
        description: updatedType.description,
      });
      
      // MANDATE 2: Runtime validation
      const result = OntologyTypeSchema.safeParse(response.data);
      if (!result.success) {
        log.error('Failed to parse updated type', { typeId: validatedId, error: result.error.message });
        throw new Error('Invalid response when updating type');
      }
      
      return result.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QK.ontology.schema() });
      queryClient.invalidateQueries({ queryKey: QK.ontology.type(variables.id) });
    },
    onError: (error, variables) => {
      log.error('Failed to update ontology type', { typeId: variables.id, error: error.message });
    },
  });
}

// Delete type
export function useDeleteOntologyType() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (typeId): Promise<void> => {
      // MANDATE 4: Validate typeId
      const validatedId = validateTypeId(typeId);
      if (validatedId === null) {
        throw new Error('Invalid typeId: cannot delete type');
      }

      await apiDelete<unknown>(LAYER2, `/v1/ontology/schema/types/${validatedId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.ontology.schema() });
    },
    onError: (error, typeId) => {
      log.error('Failed to delete ontology type', { typeId, error: error.message });
    },
  });
}

// Add property to type
export function useAddOntologyProperty() {
  const queryClient = useQueryClient();

  return useMutation<OntologyProperty, Error, { typeId: string; property: Omit<OntologyProperty, 'id'> }>({
    mutationFn: async ({ typeId, property }): Promise<OntologyProperty> => {
      // MANDATE 4: Validate inputs
      const validatedTypeId = validateTypeId(typeId);
      if (validatedTypeId === null) {
        throw new Error('Invalid typeId: cannot add property');
      }

      const response = await apiPost<OntologyType>(LAYER2, `/v1/ontology/schema/types/${validatedTypeId}/properties`, property);
      
      // MANDATE 2: Runtime type validation instead of `as` assertion
      const updatedTypeResult = OntologyTypeSchema.safeParse(response.data);
      if (!updatedTypeResult.success) {
        log.error('Failed to parse updated type', { error: updatedTypeResult.error.message });
        throw new Error('Invalid response from server when adding property');
      }
      
      const updatedType = updatedTypeResult.data;
      
      // MANDATE 7: BOUNDS SAFETY - Check array length before accessing last element
      if (updatedType.properties.length === 0) {
        log.error('Updated type has no properties after add operation', { typeId: validatedTypeId });
        throw new Error('Property was not added successfully');
      }
      
      return updatedType.properties[updatedType.properties.length - 1];
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QK.ontology.type(variables.typeId) });
      queryClient.invalidateQueries({ queryKey: QK.ontology.schema() });
    },
    onError: (error, variables) => {
      log.error('Failed to add ontology property', { 
        typeId: variables.typeId, 
        propertyName: variables.property.name,
        error: error.message 
      });
    },
  });
}

// Remove property from type
export function useRemoveOntologyProperty() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, { typeId: string; propertyId: string }>({
    mutationFn: async ({ typeId, propertyId }): Promise<void> => {
      // MANDATE 4: Validate IDs
      const validatedTypeId = validateTypeId(typeId);
      if (validatedTypeId === null) {
        throw new Error('Invalid typeId: cannot remove property');
      }
      const validatedPropertyId = validatePropertyId(propertyId);

      await apiDelete<unknown>(
        LAYER2, 
        `/v1/ontology/schema/types/${validatedTypeId}/properties/${validatedPropertyId}`
      );
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QK.ontology.type(variables.typeId) });
      queryClient.invalidateQueries({ queryKey: QK.ontology.schema() });
    },
    onError: (error, variables) => {
      log.error('Failed to remove ontology property', { 
        typeId: variables.typeId, 
        propertyId: variables.propertyId,
        error: error.message 
      });
    },
  });
}

// Add relationship between types
export function useAddTypeRelationship() {
  const queryClient = useQueryClient();

  return useMutation<TypeRelationship, Error, Omit<TypeRelationship, 'id'>>({
    mutationFn: async (relationship): Promise<TypeRelationship> => {
      const response = await apiPost<TypeRelationship>(LAYER2, '/v1/ontology/schema/relationships', {
        source_type_id: relationship.sourceTypeId,
        target_type_id: relationship.targetTypeId,
        relationship_type: relationship.relationshipType,
        description: relationship.description,
        cardinality: relationship.cardinality,
      });
      
      // MANDATE 2: Runtime validation
      const result = TypeRelationshipSchema.safeParse(response.data);
      if (!result.success) {
        log.error('Failed to parse created relationship', { error: result.error.message });
        throw new Error('Invalid response when creating relationship');
      }
      
      return result.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.ontology.schema() });
    },
    onError: (error, variables) => {
      log.error('Failed to add type relationship', { 
        sourceTypeId: variables.sourceTypeId,
        targetTypeId: variables.targetTypeId,
        error: error.message 
      });
    },
  });
}

// Remove relationship
export function useRemoveTypeRelationship() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (relationshipId): Promise<void> => {
      // MANDATE 4: Validate relationshipId
      const result = RelationshipIdSchema.safeParse(relationshipId);
      if (!result.success) {
        log.error('Invalid relationshipId', { relationshipId, error: result.error.message });
        throw new Error(`Invalid relationshipId: ${result.error.message}`);
      }

      await apiDelete<unknown>(LAYER2, `/v1/ontology/schema/relationships/${result.data}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.ontology.schema() });
    },
    onError: (error, relationshipId) => {
      log.error('Failed to remove type relationship', { relationshipId, error: error.message });
    },
  });
}

// Validate ontology schema
export function useValidateOntology() {
  return useMutation<ValidationResult, Error, OntologySchema>({
    mutationFn: async (schema): Promise<ValidationResult> => {
      // MANDATE 2: Validate input schema before sending
      const schemaResult = OntologySchemaSchema.safeParse(schema);
      if (!schemaResult.success) {
        log.error('Invalid ontology schema input', { error: schemaResult.error.message });
        throw new Error(`Invalid schema: ${schemaResult.error.message}`);
      }

      const response = await apiPost<ValidationResult>(LAYER2, '/v1/ontology/schema/validate', {
        types: schema.types,
        relationships: schema.relationships,
      });
      
      // MANDATE 2: Validate response
      const result = ValidationResultSchema.safeParse(response.data);
      if (!result.success) {
        log.error('Invalid validation response from server', { error: result.error.message });
        throw new Error('Invalid response from validation endpoint');
      }
      
      return result.data;
    },
    onError: (error) => {
      log.error('Ontology validation failed', { error: error.message });
    },
  });
}

// Publish ontology
export function usePublishOntology() {
  const queryClient = useQueryClient();

  return useMutation<
    { version: string; publishedAt: string; publishedBy: string },
    Error,
    { version: string; comment?: string }
  >({
    mutationFn: async ({ version, comment }): Promise<{ version: string; publishedAt: string; publishedBy: string }> => {
      // MANDATE 4: Validate version format
      const versionResult = VersionSchema.safeParse(version);
      if (!versionResult.success) {
        log.error('Invalid version format', { version, error: versionResult.error.message });
        throw new Error(`Invalid version: ${versionResult.error.message}`);
      }

      const response = await apiPost<{ version: string; publishedAt: string; publishedBy: string }>(LAYER2, '/v1/ontology/schema/publish', {
        version: versionResult.data,
        comment,
      });
      
      // MANDATE 2: Validate response structure
      const PublishResponseSchema = z.object({
        version: z.string(),
        publishedAt: z.string(),
        publishedBy: z.string(),
      });
      
      const result = PublishResponseSchema.safeParse(response.data);
      if (!result.success) {
        log.error('Invalid publish response', { error: result.error.message });
        throw new Error('Invalid response from publish endpoint');
      }
      
      return result.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.ontology.schema() });
    },
    onError: (error, variables) => {
      log.error('Failed to publish ontology', { version: variables.version, error: error.message });
    },
  });
}

// Import ontology from JSON
export function useImportOntology() {
  const queryClient = useQueryClient();

  return useMutation<OntologySchema, Error, string>({
    mutationFn: async (jsonData): Promise<OntologySchema> => {
      // MANDATE 4: Validate JSON is parseable before sending
      let parsedSchema: unknown;
      try {
        parsedSchema = JSON.parse(jsonData);
      } catch (parseError) {
        log.error('Invalid JSON provided for import', { error: String(parseError) });
        throw new Error('Invalid JSON: cannot parse schema');
      }

      // MANDATE 2: Validate against schema
      const schemaResult = OntologySchemaSchema.safeParse(parsedSchema);
      if (!schemaResult.success) {
        log.error('JSON does not match ontology schema', { error: schemaResult.error.message });
        throw new Error(`Invalid ontology schema: ${schemaResult.error.message}`);
      }

      const response = await apiPost<OntologySchema>(LAYER2, '/v1/ontology/schema/import', {
        schema_json: jsonData,
      });
      
      // MANDATE 2: Validate response
      const result = OntologySchemaSchema.safeParse(response.data);
      if (!result.success) {
        log.error('Invalid import response from server', { error: result.error.message });
        throw new Error('Invalid response from import endpoint');
      }
      
      return result.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.ontology.schema() });
    },
    onError: (error) => {
      log.error('Failed to import ontology', { error: error.message });
    },
  });
}

