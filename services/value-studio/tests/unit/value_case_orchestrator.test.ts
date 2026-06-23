import {
  ValueCaseOrchestrator,
  UntraceableNodeException,
  UndefinedInputException,
  UnapprovedValueCaseProjectionException,
} from "../../src/domain/services/value_case_orchestrator";
import { ValueCase, ValueDriverNode, FinancialModel } from "../../src/domain/contracts/value_case";

describe("ValueCase Orchestration Engine Integrity Rules Test Suite", () => {
  let orchestrator: ValueCaseOrchestrator;
  const tenantId = "tenant_enterprise_1";
  const accountId = "acc_strategic_09";
  const valueCaseId = "vcase_9988";

  beforeAll(() => {
    orchestrator = new ValueCaseOrchestrator();
  });

  test("Registration of Driver Node without Claim Lineage throws UntraceableNodeException", () => {
    const rawNodes: Array<
      Omit<ValueDriverNode, "tenantId" | "accountId" | "valueCaseId" | "createdAt">
    > = [
      {
        id: "driver_node_01",
        nodeType: "value_driver",
        label: "Increase Customer Retention by 10%",
        supportingClaimIds: [], // Explicitly empty lineage list
        parentNodeIds: [],
        status: "candidate",
        modelOrRuleVersion: "rule-v1",
      },
    ];

    expect(() => {
      orchestrator.compileDriverNodes(tenantId, accountId, valueCaseId, rawNodes);
    }).toThrow(UntraceableNodeException);
  });

  test("Computation of Financial Engine with invalid unlinked parameter throws UndefinedInputException", () => {
    const model: FinancialModel = {
      id: "model_financial_01",
      valueCaseId: "vcase_9988",
      revision: 1,
      formulas: [
        {
          formulaId: "formula_roi",
          formulaVersion: "1.0",
          expression: "inputs.annual_savings * inputs.retention_rate",
          inputs: [
            {
              inputKey: "annual_savings",
              parameterKey: "p_savings",
              claimId: null, // Untraceable parameter
              status: "validated", // Mismatched status state
              value: 100000,
            },
          ],
          output: { value: null, currency: "USD", unit: "dollars" },
        },
      ],
      computedAt: "",
      computeVersion: "",
    };

    const emptyParams = new Map<string, number>();

    expect(() => {
      orchestrator.computeFinancialModel(model, emptyParams);
    }).toThrow(UndefinedInputException);
  });

  test("Projecting non-approved ValueCase to L6 Deliverable throws UnapprovedValueCaseProjectionException", () => {
    const draftValueCase: ValueCase = {
      id: "vcase_9988",
      tenantId,
      accountId,
      revision: 1,
      sourceSnapshotId: "snapshot_l3_01",
      driverTreeNodeIds: [],
      financialModelId: "model_financial_01",
      narrativeText: "Highly profitable return prospects.",
      status: "draft", // Stage is draft, cannot project
      evidenceStrengthScore: 89,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const financialModel: FinancialModel = {
      id: "model_financial_01",
      valueCaseId: "vcase_9988",
      revision: 1,
      formulas: [],
      computedAt: new Date().toISOString(),
      computeVersion: "v1",
    };

    expect(() => {
      orchestrator.generateProjection(tenantId, accountId, draftValueCase, financialModel, [], "deck_template_standard");
    }).toThrow(UnapprovedValueCaseProjectionException);
  });

  test("Approved ValueCase can be projected to an L6 DeliverableProjection", () => {
    const approvedValueCase: ValueCase = {
      id: "vcase_9988",
      tenantId,
      accountId,
      revision: 2,
      sourceSnapshotId: "snapshot_l3_01",
      driverTreeNodeIds: ["driver_node_01"],
      financialModelId: "model_financial_01",
      narrativeText: "Defensible return case.",
      status: "approved",
      evidenceStrengthScore: 92,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const financialModel: FinancialModel = {
      id: "model_financial_01",
      valueCaseId: "vcase_9988",
      revision: 2,
      formulas: [
        {
          formulaId: "formula_roi",
          formulaVersion: "1.0",
          expression: "inputs.annual_savings * inputs.retention_rate",
          inputs: [
            {
              inputKey: "annual_savings",
              parameterKey: "p_savings",
              claimId: "claim_01",
              status: "validated",
              value: 100000,
            },
            {
              inputKey: "retention_rate",
              parameterKey: "p_retention",
              claimId: "claim_02",
              status: "validated",
              value: 0.85,
            },
          ],
          output: { value: null, currency: "USD", unit: "dollars" },
        },
      ],
      computedAt: new Date().toISOString(),
      computeVersion: "v1",
    };

    const driverNodes: ValueDriverNode[] = [
      {
        id: "driver_node_01",
        tenantId,
        accountId,
        valueCaseId,
        nodeType: "value_driver",
        label: "Increase Retention",
        supportingClaimIds: ["claim_01", "claim_02"],
        parentNodeIds: [],
        status: "validated",
        modelOrRuleVersion: "rule-v1",
        createdAt: new Date().toISOString(),
      },
    ];

    const computed = orchestrator.computeFinancialModel(financialModel, new Map());
    const projection = orchestrator.generateProjection(tenantId, accountId, approvedValueCase, computed, driverNodes, "deck_template_standard");

    expect(projection.valueCaseId).toBe("vcase_9988");
    expect(projection.valueCaseRevision).toBe(2);
    expect(projection.sections[0].formattedOutput.total_realized_value).toBe(85000);
    expect(projection.sections[0].formattedOutput.claim_trace_indices).toEqual(["claim_01", "claim_02"]);
  });
});
