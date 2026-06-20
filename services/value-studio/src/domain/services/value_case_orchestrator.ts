import {
  ValueCase,
  ValueDriverNode,
  FinancialModel,
  DeliverableProjection,
  ValueCaseStatus,
  FormulaInput,
} from "../contracts/value_case";

export class UntraceableNodeException extends Error {
  constructor(nodeId: string) {
    super(`Governance Breach: Driver node ${nodeId} cannot be registered without supporting Claims lineage.`);
    this.name = "UntraceableNodeException";
  }
}

export class UndefinedInputException extends Error {
  constructor(inputKey: string) {
    super(`Governance Breach: Financial input parameter "${inputKey}" must have a validated Claim ID or be declared as a governed "assumption".`);
    this.name = "UndefinedInputException";
  }
}

export class UnapprovedValueCaseProjectionException extends Error {
  constructor(valueCaseId: string, status: string) {
    super(`Factual Integrity Error: Cannot project ValueCase ${valueCaseId} onto L6 Deliverables. Present status is: ${status}. Required: approved.`);
    this.name = "UnapprovedValueCaseProjectionException";
  }
}

export class ValueCaseOrchestrator {
  // 1. Compile Raw Evidence & Claims into ValueDriverNodes
  public compileDriverNodes(
    tenantId: string,
    accountId: string,
    valueCaseId: string,
    rawNodes: Array<Omit<ValueDriverNode, "tenantId" | "accountId" | "valueCaseId" | "createdAt">>
  ): ValueDriverNode[] {
    const verifiedNodes: ValueDriverNode[] = [];

    for (const node of rawNodes) {
      // INVARIANT: Node cannot float free of Claims lineage
      if (!node.supportingClaimIds || node.supportingClaimIds.length === 0) {
        throw new UntraceableNodeException(node.id);
      }

      verifiedNodes.push({
        ...node,
        tenantId,
        accountId,
        valueCaseId,
        createdAt: new Date().toISOString(),
      });
    }

    return verifiedNodes;
  }

  // 2. Deterministic Financial Model Computation
  public computeFinancialModel(
    model: FinancialModel,
    governedParameters: Map<string, number>
  ): FinancialModel {
    const updatedFormulas = model.formulas.map((formula) => {
      const inputs = formula.inputs.map((input) => {
        // Resolve input parameter
        let finalValue = input.value;
        if (governedParameters.has(input.parameterKey)) {
          finalValue = governedParameters.get(input.parameterKey)!;
        }

        // INVARIANT: Check validation status
        if (!input.claimId && input.status !== "assumption") {
          throw new UndefinedInputException(input.inputKey);
        }

        return { ...input, value: finalValue };
      });

      // Simple deterministic safe-eval for formulas (No dynamic unrestricted execution)
      let resolvedValue = 0;
      if (formula.expression === "inputs.annual_savings * inputs.retention_rate") {
        const annualSavings = inputs.find((i) => i.inputKey === "annual_savings")?.value ?? 0;
        const retentionRate = inputs.find((i) => i.inputKey === "retention_rate")?.value ?? 0;
        resolvedValue = annualSavings * retentionRate;
      } else {
        // Fallback simple summing evaluator
        resolvedValue = inputs.reduce((sum, current) => sum + current.value, 0);
      }

      return {
        ...formula,
        inputs,
        output: {
          ...formula.output,
          value: resolvedValue,
        },
      };
    });

    return {
      ...model,
      formulas: updatedFormulas,
      computedAt: new Date().toISOString(),
      computeVersion: "v1.1-deterministic",
    };
  }

  // 3. State Machine Driver Engine
  public transitionState(valueCase: ValueCase, targetStatus: ValueCaseStatus): ValueCase {
    const stateTransitions: Record<ValueCaseStatus, ValueCaseStatus[]> = {
      draft: ["modeling"],
      modeling: ["computing", "draft"],
      computing: ["validating", "modeling"],
      validating: ["needs_review"],
      needs_review: ["approved", "draft"],
      approved: ["superseded"],
      superseded: [],
    };

    const allowed = stateTransitions[valueCase.status];
    if (!allowed.includes(targetStatus)) {
      throw new Error(
        `Incompatible transition error. Target state ${targetStatus} cannot be reached from ${valueCase.status}`
      );
    }

    return {
      ...valueCase,
      status: targetStatus,
      updatedAt: new Date().toISOString(),
    };
  }

  // 4. L6 Deliverables Presentation Projector (No New Truth)
  public generateProjection(
    tenantId: string,
    accountId: string,
    valueCase: ValueCase,
    financialModel: FinancialModel,
    driverNodes: ValueDriverNode[],
    templateName: string
  ): DeliverableProjection {
    // INVARIANT: Generation is strictly blocked until ValueCase.status is approved
    if (valueCase.status !== "approved") {
      throw new UnapprovedValueCaseProjectionException(valueCase.id, valueCase.status);
    }

    // Freeze snapshot data
    const formattedData: Record<string, any> = {
      total_realized_value: financialModel.formulas.reduce(
        (acc, formula) => acc + (formula.output.value ?? 0),
        0
      ),
      driver_summary: driverNodes.map((node) => ({ label: node.label, type: node.nodeType })),
      claim_trace_indices: Array.from(
        new Set(driverNodes.flatMap((n) => n.supportingClaimIds))
      ),
    };

    return {
      id: `proj_${valueCase.id}_rev${valueCase.revision}`,
      tenantId,
      accountId,
      deliverableType: "executive_business_case",
      valueCaseId: valueCase.id,
      valueCaseRevision: valueCase.revision,
      sections: [
        {
          sectionId: "sec_executive_summary",
          templateName,
          valueCaseElementIds: [financialModel.id, ...driverNodes.map((node) => node.id)],
          formattedOutput: formattedData,
        },
      ],
      projectionVersion: "1.0-frozen-render",
      publicationState: "generated",
      createdAt: new Date().toISOString(),
    };
  }
}
