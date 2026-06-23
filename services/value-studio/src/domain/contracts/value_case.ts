export type NodeKind =
  | "business_objective"
  | "business_problem"
  | "root_cause"
  | "value_driver"
  | "metric"
  | "value_lever";

export type NodeStatus = "candidate" | "supported" | "validated" | "contested" | "rejected";

export type ValueCaseStatus =
  | "draft"
  | "modeling"
  | "computing"
  | "validating"
  | "needs_review"
  | "approved"
  | "superseded";

export type FormulaInputStatus = "validated" | "needs_review" | "needs_override" | "assumption";

export interface ValueDriverNode {
  id: string;
  tenantId: string;
  accountId: string;
  valueCaseId: string;
  nodeType: NodeKind;
  label: string;
  supportingClaimIds: string[];
  parentNodeIds: string[];
  status: NodeStatus;
  modelOrRuleVersion: string;
  createdAt: string;
}

export interface FormulaInput {
  inputKey: string;
  parameterKey: string;
  claimId: string | null;
  status: FormulaInputStatus;
  value: number;
}

export interface FinancialFormula {
  formulaId: string;
  formulaVersion: string;
  expression: string; // e.g. "inputs.annual_savings * inputs.retention_rate"
  inputs: FormulaInput[];
  output: {
    value: number | null;
    currency: string;
    unit: string;
  };
}

export interface FinancialModel {
  id: string;
  valueCaseId: string;
  revision: number;
  formulas: FinancialFormula[];
  computedAt: string;
  computeVersion: string;
}

export interface ValueCase {
  id: string;
  tenantId: string;
  accountId: string;
  revision: number;
  sourceSnapshotId: string; // Reference to the underlying FabricFoundSummary L3 state
  driverTreeNodeIds: string[];
  financialModelId: string;
  narrativeText: string;
  status: ValueCaseStatus;
  evidenceStrengthScore: number;
  createdAt: string;
  updatedAt: string;
}

export interface DeliverableProjection {
  id: string;
  tenantId: string;
  accountId: string;
  deliverableType: "executive_business_case" | "champion_deck" | "roi_report";
  valueCaseId: string;
  valueCaseRevision: number;
  sections: Array<{
    sectionId: string;
    templateName: string;
    valueCaseElementIds: string[]; // Strict map referencing driver/model/claim records.
    formattedOutput: Record<string, any>;
  }>;
  projectionVersion: string;
  publicationState: "draft" | "generated" | "approved" | "published" | "revoked";
  createdAt: string;
}
