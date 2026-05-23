import { describe, it, expect } from "vitest";
import {
  validateFormulaExpression,
  validateVariableBindings,
  canTransitionState,
  getAvailableTransitions,
  getTransitionAction,
  getStatusConfig,
  getSourceTypeColor,
  getVariableTypeColor,
  calculateROI,
  parseNumericValue,
  buildFormulaPayload,
  buildVersionHistoryEntry,
  type FormulaVariable,
  type ActivationState,
} from "./formulaBuilderLogic";

describe("Formula Builder Logic", () => {
  const mockVariables: FormulaVariable[] = [
    { name: "Customer_Count", type: "integer", source: "CRM" },
    { name: "Average_Contract_Value", type: "currency", source: "Billing" },
    { name: "Current_Churn_Rate", type: "rate", source: "Model" },
    { name: "Implementation_Cost", type: "currency", source: "Manual" },
  ];

  describe("validateFormulaExpression", () => {
    it("should validate a correct formula", () => {
      const result = validateFormulaExpression(
        "({Customer_Count} * {Current_Churn_Rate})",
        mockVariables
      );

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should reject empty expression", () => {
      const result = validateFormulaExpression("", mockVariables);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("Formula expression is required");
    });

    it("should detect unbalanced brackets", () => {
      const result = validateFormulaExpression(
        "({Customer_Count} * {Current_Churn_Rate",  // Missing closing brace
        mockVariables
      );

      expect(result.valid).toBe(false);
      expect(result.errors).toContain(
        "Unbalanced brackets: 2 opening, 1 closing"
      );
    });

    it("should detect undefined variables", () => {
      const result = validateFormulaExpression(
        "({Unknown_Var} * {Customer_Count})",
        mockVariables
      );

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("Undefined variables: Unknown_Var");
    });

    it("should detect empty variable references", () => {
      const result = validateFormulaExpression(
        "({} * {Customer_Count})",
        mockVariables
      );

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("Empty variable reference found: {}");
    });

    it("should warn about unused variables", () => {
      const result = validateFormulaExpression(
        "{Customer_Count}",
        mockVariables
      );

      expect(result.valid).toBe(true);
      expect(result.warnings.length).toBeGreaterThan(0);
      expect(result.warnings[0]).toContain("Unused variables");
    });

    it("should detect invalid characters", () => {
      const result = validateFormulaExpression(
        "{Customer_Count} @ {Current_Churn_Rate}",
        mockVariables
      );

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("Invalid characters: @");
    });

    it("should validate formula with multiple variables", () => {
      const result = validateFormulaExpression(
        "({Customer_Count} * {Current_Churn_Rate} * {Average_Contract_Value}) - {Implementation_Cost}",
        mockVariables
      );

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe("validateVariableBindings", () => {
    it("should validate all required variables are bound", () => {
      const result = validateVariableBindings(
        ["Customer_Count", "Current_Churn_Rate"],
        mockVariables
      );

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it("should detect missing required variables", () => {
      const result = validateVariableBindings(
        ["Customer_Count", "Missing_Var"],
        mockVariables
      );

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("Missing required variables: Missing_Var");
    });

    it("should handle empty requirements", () => {
      const result = validateVariableBindings([], mockVariables);

      expect(result.valid).toBe(true);
    });

    it("should handle empty bindings", () => {
      const result = validateVariableBindings(["Customer_Count"], []);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain(
        "Missing required variables: Customer_Count"
      );
    });
  });

  describe("canTransitionState", () => {
    it("should allow draft to pending", () => {
      expect(canTransitionState("draft", "pending")).toBe(true);
    });

    it("should not allow draft to approved directly", () => {
      expect(canTransitionState("draft", "approved")).toBe(false);
    });

    it("should allow pending to approved", () => {
      expect(canTransitionState("pending", "approved")).toBe(true);
    });

    it("should allow pending to draft (rejection)", () => {
      expect(canTransitionState("pending", "draft")).toBe(true);
    });

    it("should allow approved to draft (revision)", () => {
      expect(canTransitionState("approved", "draft")).toBe(true);
    });

    it("should not allow approved to pending", () => {
      expect(canTransitionState("approved", "pending")).toBe(false);
    });

    it("should not allow same state transition", () => {
      expect(canTransitionState("draft", "draft")).toBe(false);
      expect(canTransitionState("pending", "pending")).toBe(false);
      expect(canTransitionState("approved", "approved")).toBe(false);
    });
  });

  describe("getAvailableTransitions", () => {
    it("should return correct transitions for draft", () => {
      expect(getAvailableTransitions("draft")).toEqual(["pending"]);
    });

    it("should return correct transitions for pending", () => {
      expect(getAvailableTransitions("pending")).toEqual(["approved", "draft"]);
    });

    it("should return correct transitions for approved", () => {
      expect(getAvailableTransitions("approved")).toEqual(["draft"]);
    });
  });

  describe("getTransitionAction", () => {
    it("should return action for draft to pending", () => {
      expect(getTransitionAction("draft", "pending")).toBe(
        "Submit for Approval"
      );
    });

    it("should return action for pending to approved", () => {
      expect(getTransitionAction("pending", "approved")).toBe("Approve");
    });

    it("should return action for pending to draft", () => {
      expect(getTransitionAction("pending", "draft")).toBe("Reject");
    });

    it("should return action for approved to draft", () => {
      expect(getTransitionAction("approved", "draft")).toBe("Revise");
    });

    it("should return null for invalid transition", () => {
      expect(getTransitionAction("draft", "approved")).toBeNull();
    });
  });

  describe("getStatusConfig", () => {
    it("should return correct config for draft", () => {
      const config = getStatusConfig("draft");

      expect(config.label).toBe("Draft");
      expect(config.color).toBe("bg-neutral-100 text-neutral-600");
      expect(config.icon).toBe("clock");
    });

    it("should return correct config for pending", () => {
      const config = getStatusConfig("pending");

      expect(config.label).toBe("Pending Approval");
      expect(config.color).toBe("bg-amber-50 text-amber-700");
      expect(config.icon).toBe("alert-circle");
    });

    it("should return correct config for approved", () => {
      const config = getStatusConfig("approved");

      expect(config.label).toBe("Active");
      expect(config.color).toBe("bg-emerald-50 text-emerald-700");
      expect(config.icon).toBe("check-circle");
    });
  });

  describe("getSourceTypeColor", () => {
    it("should return colors for all source types", () => {
      expect(getSourceTypeColor("CRM")).toContain("blue");
      expect(getSourceTypeColor("Billing")).toContain("emerald");
      expect(getSourceTypeColor("Model")).toContain("violet");
      expect(getSourceTypeColor("Manual")).toContain("amber");
      expect(getSourceTypeColor("ERP")).toContain("cyan");
    });

    it("should return default for unknown source", () => {
      expect(getSourceTypeColor("Unknown" as string)).toBe(
        "bg-neutral-50 text-neutral-600"
      );
    });
  });

  describe("getVariableTypeColor", () => {
    it("should return colors for all variable types", () => {
      expect(getVariableTypeColor("rate")).toContain("cyan");
      expect(getVariableTypeColor("currency")).toContain("emerald");
      expect(getVariableTypeColor("integer")).toContain("neutral");
      expect(getVariableTypeColor("percent")).toContain("purple");
      expect(getVariableTypeColor("decimal")).toContain("orange");
    });

    it("should return default for unknown type", () => {
      expect(getVariableTypeColor("Unknown" as string)).toBe(
        "bg-neutral-100 text-neutral-600"
      );
    });
  });

  describe("calculateROI", () => {
    it("should calculate ROI correctly", () => {
      const result = calculateROI(1000000, 100000);

      expect(result.roi).toBe(900000);
      expect(result.roiPercent).toBe(900);
    });

    it("should handle zero investment", () => {
      const result = calculateROI(100000, 0);

      expect(result.roi).toBe(0);
      expect(result.roiPercent).toBe(0);
    });

    it("should handle negative ROI", () => {
      const result = calculateROI(50000, 100000);

      expect(result.roi).toBe(-50000);
      expect(result.roiPercent).toBe(-50);
    });

    it("should round ROI percentage", () => {
      const result = calculateROI(105000, 100000);

      expect(result.roiPercent).toBe(5); // (5000/100000)*100 = 5%
    });
  });

  describe("parseNumericValue", () => {
    it("should parse currency values", () => {
      expect(parseNumericValue("$100,000")).toBe(100000);
    });

    it("should parse percentage values", () => {
      expect(parseNumericValue("25%")).toBe(25);
    });

    it("should parse plain numbers", () => {
      expect(parseNumericValue("1000")).toBe(1000);
    });

    it("should handle decimal values", () => {
      expect(parseNumericValue("$1,500.50")).toBe(1500.5);
    });

    it("should return 0 for invalid input", () => {
      expect(parseNumericValue("not a number")).toBe(0);
    });

    it("should handle empty string", () => {
      expect(parseNumericValue("")).toBe(0);
    });
  });

  describe("buildFormulaPayload", () => {
    it("should build complete payload", () => {
      const payload = buildFormulaPayload(
        "Test Formula",
        "A test formula",
        "{Customer_Count} * 2",
        mockVariables,
        "draft",
        1,
        "Test Author"
      );

      expect(payload.name).toBe("Test Formula");
      expect(payload.description).toBe("A test formula");
      expect(payload.expression).toBe("{Customer_Count} * 2");
      expect(payload.variables).toHaveLength(4);
      expect(payload.state).toBe("draft");
      expect(payload.version).toBe(1);
      expect(payload.metadata.author).toBe("Test Author");
      expect(payload.metadata.createdAt).toBeDefined();
      expect(payload.metadata.modifiedAt).toBeDefined();
    });

    it("should set correct timestamps", () => {
      const before = new Date().toISOString();
      const payload = buildFormulaPayload(
        "Test",
        "Desc",
        "1+1",
        [],
        "approved",
        2,
        "Author"
      );
      const after = new Date().toISOString();

      expect(payload.metadata.createdAt >= before).toBe(true);
      expect(payload.metadata.createdAt <= after).toBe(true);
      expect(payload.metadata.modifiedAt).toBe(payload.metadata.createdAt);
    });
  });

  describe("buildVersionHistoryEntry", () => {
    it("should build version entry", () => {
      const entry = buildVersionHistoryEntry(
        3,
        "draft",
        "J. Rivera",
        "Added new variable"
      );

      expect(entry.version).toBe("v3");
      expect(entry.status).toBe("draft");
      expect(entry.author).toBe("J. Rivera");
      expect(entry.note).toBe("Added new variable");
      expect(entry.date).toBeDefined();
    });

    it("should format version number correctly", () => {
      expect(buildVersionHistoryEntry(1, "approved", "A", "Note").version).toBe(
        "v1"
      );
      expect(buildVersionHistoryEntry(10, "draft", "B", "Note").version).toBe(
        "v10"
      );
    });
  });
});
