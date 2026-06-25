export const SEMANTIC_CONTRACT_VERSION = "2.0.0" as const;

export type ValidationMode = "warn" | "strict";
export type ContractViolationSeverity = "warning" | "error";

export interface ContractViolation {
  code: string;
  message: string;
  severity: ContractViolationSeverity;
  path: string;
}

export interface ContractValidationResult<T = unknown> {
  valid: boolean;
  mode: ValidationMode;
  violations: ContractViolation[];
  normalized?: T;
}

export interface ContractVersionRef {
  semanticContract: string;
  agentRegistry?: string;
  prompt?: string;
  tool?: string;
  workflow?: string;
  memory?: string;
}

export interface ProvenanceRef {
  tenantId: string;
  traceId: string;
  workflowId?: string;
  auditEventId?: string;
  sourceNode?: string;
  sourceLayer: string;
}

export interface PromptRef {
  promptId: string;
  version: string;
  reasoningPolicyId?: string;
}

export interface AgentOutputEnvelope<TOutput = unknown> {
  agentType: string;
  output?: TOutput;
  provenance: ProvenanceRef;
  contractVersions: ContractVersionRef;
  prompt?: PromptRef;
  confidence?: number;
  explainability: Record<string, unknown>;
  evidence: Array<Record<string, unknown>>;
  emittedAt: string;
}

export interface ToolInvocationEnvelope<TInput = Record<string, unknown>, TOutput = unknown> {
  toolName: string;
  toolVersion: string;
  callerAgentType: string;
  input: TInput;
  output?: TOutput;
  provenance: ProvenanceRef;
  contractVersions: ContractVersionRef;
  success: boolean;
  error?: Record<string, unknown>;
}

export interface WorkflowTransitionEnvelope {
  workflowType: string;
  workflowId: string;
  sourceState: string;
  targetState: string;
  triggeringAgentType: string;
  provenance: ProvenanceRef;
  contractVersions: ContractVersionRef;
  transitionReason?: string;
}

export interface MemoryReference {
  memoryId: string;
  memoryType: string;
  tenantId: string;
  traceId: string;
  contractVersions: ContractVersionRef;
  provenance?: ProvenanceRef;
}

export interface CompatibilityMatrix {
  id: string;
  version: string;
  agentRegistryVersion: string;
  minRuntimeVersion: string;
  enforcementDefault: ValidationMode;
  compatibleEventVersions: Record<string, string>;
  agentContracts: Record<string, string>;
  promptContracts: Record<string, string>;
  toolContracts: Record<string, string>;
  workflowContracts: Record<string, string>;
  memoryContracts: Record<string, string>;
  deprecatedContracts: string[];
}

interface MutableValidation<T> {
  valid: boolean;
  mode: ValidationMode;
  violations: ContractViolation[];
  normalized?: T;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function addViolation(
  result: MutableValidation<unknown>,
  path: string,
  message: string,
  code = "semantic_contract_validation_error"
): void {
  result.valid = false;
  result.violations.push({ code, message, severity: "error", path });
}

function requireString(
  result: MutableValidation<unknown>,
  value: Record<string, unknown>,
  field: string,
  path = field
): string | undefined {
  const candidate = value[field];
  if (typeof candidate !== "string" || candidate.length === 0) {
    addViolation(result, path, `${field} must be a non-empty string`);
    return undefined;
  }
  return candidate;
}

function optionalString(value: Record<string, unknown>, field: string): string | undefined {
  const candidate = value[field];
  return typeof candidate === "string" && candidate.length > 0 ? candidate : undefined;
}

function normalizeContractVersions(value: unknown): ContractVersionRef {
  if (!isRecord(value)) {
    return { semanticContract: SEMANTIC_CONTRACT_VERSION };
  }
  return {
    semanticContract:
      typeof value.semanticContract === "string"
        ? value.semanticContract
        : typeof value.semantic_contract === "string"
          ? value.semantic_contract
          : SEMANTIC_CONTRACT_VERSION,
    agentRegistry:
      typeof value.agentRegistry === "string"
        ? value.agentRegistry
        : typeof value.agent_registry === "string"
          ? value.agent_registry
          : undefined,
    prompt: optionalString(value, "prompt"),
    tool: optionalString(value, "tool"),
    workflow: optionalString(value, "workflow"),
    memory: optionalString(value, "memory"),
  };
}

function normalizeProvenance(
  result: MutableValidation<unknown>,
  value: unknown,
  fallback?: Partial<ProvenanceRef>
): ProvenanceRef | undefined {
  const source = isRecord(value) ? value : {};
  const tenantId =
    (typeof source.tenantId === "string" && source.tenantId) ||
    (typeof source.tenant_id === "string" && source.tenant_id) ||
    fallback?.tenantId;
  const traceId =
    (typeof source.traceId === "string" && source.traceId) ||
    (typeof source.trace_id === "string" && source.trace_id) ||
    fallback?.traceId;

  if (!tenantId) {
    addViolation(result, "provenance.tenantId", "tenantId is required for agent semantic provenance");
  }
  if (!traceId) {
    addViolation(result, "provenance.traceId", "traceId is required for agent semantic provenance");
  }
  if (!tenantId || !traceId) return undefined;

  const workflowId =
    (typeof source.workflowId === "string" && source.workflowId) ||
    (typeof source.workflow_id === "string" && source.workflow_id) ||
    fallback?.workflowId;
  const auditEventId =
    (typeof source.auditEventId === "string" && source.auditEventId) ||
    (typeof source.audit_event_id === "string" && source.audit_event_id) ||
    fallback?.auditEventId;
  const sourceNode =
    (typeof source.sourceNode === "string" && source.sourceNode) ||
    (typeof source.source_node === "string" && source.source_node) ||
    fallback?.sourceNode;
  const sourceLayer =
    (typeof source.sourceLayer === "string" && source.sourceLayer) ||
    (typeof source.source_layer === "string" && source.source_layer) ||
    fallback?.sourceLayer ||
    "layer4-agents";

  return { tenantId, traceId, workflowId, auditEventId, sourceNode, sourceLayer };
}

function emptyResult<T>(mode: ValidationMode): MutableValidation<T> {
  return { valid: true, mode, violations: [] };
}

export function validateAgentOutputEnvelope(
  payload: unknown,
  mode: ValidationMode = "warn"
): ContractValidationResult<AgentOutputEnvelope> {
  const result = emptyResult<AgentOutputEnvelope>(mode);
  if (!isRecord(payload)) {
    addViolation(result, "$", "agent output envelope must be an object");
    return result;
  }

  const agentType =
    (typeof payload.agentType === "string" && payload.agentType) ||
    (typeof payload.agent_type === "string" && payload.agent_type) ||
    undefined;
  if (!agentType) addViolation(result, "agentType", "agentType must be a non-empty string");

  const provenance = normalizeProvenance(result, payload.provenance, {
    tenantId: typeof payload.tenantId === "string" ? payload.tenantId : undefined,
    traceId: typeof payload.traceId === "string" ? payload.traceId : undefined,
    workflowId: typeof payload.workflowId === "string" ? payload.workflowId : undefined,
    auditEventId: typeof payload.auditEventId === "string" ? payload.auditEventId : undefined,
  });

  const confidence = payload.confidence;
  if (confidence !== undefined && (typeof confidence !== "number" || confidence < 0 || confidence > 1)) {
    addViolation(result, "confidence", "confidence must be a number between 0 and 1");
  }

  let prompt: PromptRef | undefined;
  if (isRecord(payload.prompt)) {
    const promptId = requireString(result, payload.prompt, "promptId", "prompt.promptId");
    const version = requireString(result, payload.prompt, "version", "prompt.version");
    if (promptId && version) {
      prompt = {
        promptId,
        version,
        reasoningPolicyId: optionalString(payload.prompt, "reasoningPolicyId"),
      };
    }
  }

  if (!agentType || !provenance || !result.valid) return result;

  result.normalized = {
    agentType,
    output: payload.output,
    provenance,
    contractVersions: normalizeContractVersions(payload.contractVersions ?? payload.contract_versions),
    prompt,
    confidence: typeof confidence === "number" ? confidence : undefined,
    explainability: isRecord(payload.explainability) ? payload.explainability : {},
    evidence: Array.isArray(payload.evidence) ? payload.evidence.filter(isRecord) : [],
    emittedAt:
      typeof payload.emittedAt === "string"
        ? payload.emittedAt
        : typeof payload.emitted_at === "string"
          ? payload.emitted_at
          : new Date().toISOString(),
  };
  return result;
}

export function validateToolInvocationEnvelope(
  payload: unknown,
  mode: ValidationMode = "warn"
): ContractValidationResult<ToolInvocationEnvelope> {
  const result = emptyResult<ToolInvocationEnvelope>(mode);
  if (!isRecord(payload)) {
    addViolation(result, "$", "tool invocation envelope must be an object");
    return result;
  }

  const toolName = requireString(result, payload, "toolName");
  const toolVersion = requireString(result, payload, "toolVersion");
  const callerAgentType = requireString(result, payload, "callerAgentType");
  const provenance = normalizeProvenance(result, payload.provenance);
  const success = payload.success !== false;
  if (!success && !isRecord(payload.error)) {
    addViolation(result, "error", "failed tool invocation envelopes must include error details");
  }
  if (!toolName || !toolVersion || !callerAgentType || !provenance || !result.valid) return result;

  result.normalized = {
    toolName,
    toolVersion,
    callerAgentType,
    input: isRecord(payload.input) ? payload.input : {},
    output: payload.output,
    provenance,
    contractVersions: normalizeContractVersions(payload.contractVersions ?? payload.contract_versions),
    success,
    error: isRecord(payload.error) ? payload.error : undefined,
  };
  return result;
}

interface WorkflowTransitionFields {
  workflowType?: string;
  workflowId?: string;
  sourceState?: string;
  targetState?: string;
  triggeringAgentType?: string;
  provenance?: ProvenanceRef;
}

function extractWorkflowTransitionFields(
  result: MutableValidation<WorkflowTransitionEnvelope>,
  payload: Record<string, unknown>,
): WorkflowTransitionFields {
  const workflowType = requireString(result, payload, "workflowType");
  const workflowId = requireString(result, payload, "workflowId");
  const sourceState = requireString(result, payload, "sourceState");
  const targetState = requireString(result, payload, "targetState");
  const triggeringAgentType = requireString(result, payload, "triggeringAgentType");
  const provenance = normalizeProvenance(result, payload.provenance, {
    workflowId,
    tenantId: typeof payload.tenantId === "string" ? payload.tenantId : undefined,
    traceId: typeof payload.traceId === "string" ? payload.traceId : undefined,
  });
  return { workflowType, workflowId, sourceState, targetState, triggeringAgentType, provenance };
}

function hasAllWorkflowTransitionFields(fields: WorkflowTransitionFields): boolean {
  return (
    fields.workflowType !== undefined &&
    fields.workflowId !== undefined &&
    fields.sourceState !== undefined &&
    fields.targetState !== undefined &&
    fields.triggeringAgentType !== undefined &&
    fields.provenance !== undefined
  );
}

export function validateWorkflowTransitionEnvelope(
  payload: unknown,
  mode: ValidationMode = "warn"
): ContractValidationResult<WorkflowTransitionEnvelope> {
  const result = emptyResult<WorkflowTransitionEnvelope>(mode);
  if (!isRecord(payload)) {
    addViolation(result, "$", "workflow transition envelope must be an object");
    return result;
  }

  const fields = extractWorkflowTransitionFields(result, payload);
  if (!hasAllWorkflowTransitionFields(fields) || !result.valid) {
    return result;
  }

  result.normalized = {
    ...fields,
    contractVersions: normalizeContractVersions(payload.contractVersions ?? payload.contract_versions),
    transitionReason: optionalString(payload, "transitionReason"),
  } as WorkflowTransitionEnvelope;
  return result;
}

export function validateMemoryReference(
  payload: unknown,
  mode: ValidationMode = "warn"
): ContractValidationResult<MemoryReference> {
  const result = emptyResult<MemoryReference>(mode);
  if (!isRecord(payload)) {
    addViolation(result, "$", "memory reference must be an object");
    return result;
  }

  const memoryId = requireString(result, payload, "memoryId");
  const memoryType = requireString(result, payload, "memoryType");
  const tenantId = requireString(result, payload, "tenantId");
  const traceId = requireString(result, payload, "traceId");
  const provenance = payload.provenance ? normalizeProvenance(result, payload.provenance, { tenantId, traceId }) : undefined;
  if (!memoryId || !memoryType || !tenantId || !traceId || !result.valid) return result;

  result.normalized = {
    memoryId,
    memoryType,
    tenantId,
    traceId,
    contractVersions: normalizeContractVersions(payload.contractVersions ?? payload.contract_versions),
    provenance,
  };
  return result;
}

export function isBlockingContractViolation(result: ContractValidationResult): boolean {
  return result.mode === "strict" && result.violations.some((violation) => violation.severity === "error");
}
