import { Rule } from "eslint";
import { asTSNode, FunctionLikeNode, RuleContext, TSESTree } from "../astTypes";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow throw statements in tool implementations - use error() helper",
      category: "Canonical Contracts",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#24-tool-invocation-boundary",
    },
    schema: [],
    messages: {
      noThrowInTool:
        "throw is not allowed in tool implementations. " +
        "Use error() helper from errors/error-shape.ts instead. " +
        "See contract.md §2.4 for canonical pattern.",
    },
  },

  create(context: RuleContext): Rule.RuleListener {
    let toolFunctionDepth = 0;
    function isToolFunction(node: FunctionLikeNode): boolean {
      const directName = node.type !== "ArrowFunctionExpression" ? (node.id?.name ?? "") : "";
      const parent = node.parent;
      const variableName = parent?.type === "VariableDeclarator" && parent.id.type === "Identifier" ? parent.id.name : "";
      const propertyName = parent?.type === "Property" && parent.key.type === "Identifier" ? parent.key.name : "";
      const objectVarName =
        parent?.type === "Property" &&
        parent.parent?.type === "ObjectExpression" &&
        parent.parent.parent?.type === "VariableDeclarator" &&
        parent.parent.parent.id.type === "Identifier"
          ? parent.parent.parent.id.name
          : "";
      if (/tool/i.test(directName) || /tool/i.test(variableName) || /tool/i.test(propertyName) || /tool/i.test(objectVarName)) return true;
      return parent?.type === "ExportNamedDeclaration" || parent?.parent?.type === "ExportNamedDeclaration";
    }

    return {
      FunctionDeclaration(node): void {
        if (isToolFunction(asTSNode<TSESTree.FunctionDeclaration>(node))) toolFunctionDepth++;
      },
      "FunctionDeclaration:exit"(node): void {
        if (isToolFunction(asTSNode<TSESTree.FunctionDeclaration>(node))) toolFunctionDepth--;
      },
      FunctionExpression(node): void {
        if (isToolFunction(asTSNode<TSESTree.FunctionExpression>(node))) toolFunctionDepth++;
      },
      "FunctionExpression:exit"(node): void {
        if (isToolFunction(asTSNode<TSESTree.FunctionExpression>(node))) toolFunctionDepth--;
      },
      ArrowFunctionExpression(node): void {
        if (isToolFunction(asTSNode<TSESTree.ArrowFunctionExpression>(node))) toolFunctionDepth++;
      },
      "ArrowFunctionExpression:exit"(node): void {
        if (isToolFunction(asTSNode<TSESTree.ArrowFunctionExpression>(node))) toolFunctionDepth--;
      },
      ThrowStatement(node): void {
        if (toolFunctionDepth > 0) context.report({ node, messageId: "noThrowInTool" });
      },
    };
  },
};

export = rule;
