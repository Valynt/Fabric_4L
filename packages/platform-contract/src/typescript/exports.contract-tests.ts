import type { AgentResultEnvelope } from "@fabric/platform-contract";
import type { AgentResultMetadata } from "@fabric/platform-contract/agent-result";
import type { RouteTier } from "@fabric/platform-contract/routing";
import { ACCOUNT_CONTEXT_STORAGE_KEY } from "@fabric/platform-contract/stores";
import {
  SEMANTIC_CONTRACT_VERSION,
  validateAgentOutputEnvelope,
} from "@fabric/platform-contract/agent-contracts";

const metadata: AgentResultMetadata = {
  trace_id: "trace-2",
  workflow_id: "workflow-2",
  tenant_id: "tenant-2",
  agent_type: "orchestrator",
  started_at: new Date().toISOString(),
  completed_at: new Date().toISOString(),
  duration_ms: 2,
  node_path: ["start", "finish"],
};

const envelope: AgentResultEnvelope = {
  status: "paused",
  data: null,
  error: null,
  metadata,
};

const tier: RouteTier = "standard";
void envelope;
void tier;
void ACCOUNT_CONTEXT_STORAGE_KEY;
void SEMANTIC_CONTRACT_VERSION;
void validateAgentOutputEnvelope;
