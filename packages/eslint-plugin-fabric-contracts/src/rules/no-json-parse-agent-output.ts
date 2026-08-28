import { Rule } from "eslint";
import { asTSNode, RuleContext, TSESTree } from "../astTypes";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow JSON.parse() on LLM/agent outputs - use structured generation",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#25-llm-output-handling",
    },
    schema: [],
    messages: {
      noJsonParseAgentOutput:
        "JSON.parse() is not allowed on LLM/agent outputs. " +
        "Use structured generation with Zod schemas instead. " +
        "See contract.md §2.5 for canonical pattern.",
    },
  },

  create(context: RuleContext): Rule.RuleListener {
    function isLLMOutput(node: TSESTree.Node): boolean {
      const p = /llm|agent|response|output|completion|gpt|claude/i;
      if (node.type === "Identifier") return p.test(node.name);
      if (node.type === "MemberExpression") {
        const obj = node.object.type === "Identifier" ? node.object.name : "";
        const prop = node.property.type === "Identifier" ? node.property.name : "";
        return p.test(obj) || p.test(prop);
      }
      return false;
    }

    return {
      CallExpression(node): void {
        const call = asTSNode<TSESTree.CallExpression>(node);
        const callee = call.callee;
        if (callee.type === "MemberExpression" && callee.object.type === "Identifier" && callee.property.type === "Identifier" && callee.object.name === "JSON" && callee.property.name === "parse") {
          const arg = call.arguments[0];
          if (arg && arg.type !== "SpreadElement" && isLLMOutput(arg)) context.report({ node, messageId: "noJsonParseAgentOutput" });
        }
      },
    };
  },
};

export = rule;
