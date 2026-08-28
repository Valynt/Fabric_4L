/**
 * @fileoverview Rule to prevent URL string concatenation
 *
 * CONTRACT.md §2.6 - UI State Management
 * Anti-Pattern: URL string concatenation: "/path/" + id
 *
 * URL construction must be centralized via the route manifest, not ad-hoc concatenation.
 * This ensures:
 * - All routes are defined in the manifest
 * - No broken links from string concatenation errors
 * - Type-safe route parameters
 */

import { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow URL string concatenation - use route manifest",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#26-ui-state-management",
    },
    schema: [],
    messages: {
      noUrlConcatenation:
        "URL string concatenation is not allowed. " +
        "Use the route manifest for URL construction. " +
        "See contract.md §2.6 for canonical pattern.",
    },
  },

  create(context: Rule.RuleContext): Rule.RuleListener {
    const sourceCode = context.sourceCode;

    function containsUrlLikePath(node: any): boolean {
      const text = sourceCode.getText(node);
      return text.includes("/") || /['"]\//.test(text);
    }

    function isPlusBinaryExpression(node: any): boolean {
      return node?.type === "BinaryExpression" && node.operator === "+";
    }

    function isNestedInPlusChain(node: any): boolean {
      return isPlusBinaryExpression(node.parent);
    }

    return {
      // Detect string concatenation with "/" and report once per chain.
      BinaryExpression(node: any): void {
        if (node.operator !== "+" || isNestedInPlusChain(node)) {
          return;
        }

        if (containsUrlLikePath(node.left) || containsUrlLikePath(node.right)) {
          context.report({
            node,
            messageId: "noUrlConcatenation",
          });
        }
      },
    };
  },
};

export = rule;
