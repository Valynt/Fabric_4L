/**
 * @fileoverview Rule to prevent imperative navigation (router.push, history.push)
 *
 * CONTRACT.md §2.6 - UI State Management
 * Anti-Pattern: router.push(), history.push(), direct navigate()
 *
 * Navigation must happen via the state machine route manifest, not imperative calls.
 * This ensures:
 * - All navigation is declarative and visible in route manifest
 * - No hidden navigation paths
 * - Transitions are validated at build time
 */

import { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow imperative navigation - use state machine route manifest",
      category: "Canonical Contracts",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#26-ui-state-management",
    },
    schema: [],
    messages: {
      noImperativeNavigation:
        "{{method}} is not allowed. " +
        "Navigation must use the state machine route manifest, not imperative calls. " +
        "See contract.md §2.6 for canonical pattern.",
    },
  },

  create(context: Rule.RuleContext): Rule.RuleListener {
    return {
      // Detect router.push() or history.push()
      CallExpression(node: any): void {
        const callee = node.callee;

        if (callee.type === "Identifier" && callee.name === "navigate") {
          context.report({
            node,
            messageId: "noImperativeNavigation",
            data: { method: "navigate()" },
          });
          return;
        }

        if (callee.type === "MemberExpression") {
          const objName = callee.object?.name || "";
          const propName = callee.property?.name || "";

          // Check for router.push, history.push, navigate
          if (
            (objName === "router" || objName === "history") &&
            propName === "push"
          ) {
            context.report({
              node,
              messageId: "noImperativeNavigation",
              data: { method: `${objName}.${propName}()` },
            });
            return;
          }

          if (objName === "navigate" || propName === "navigate") {
            context.report({
              node,
              messageId: "noImperativeNavigation",
              data: { method: "navigate()" },
            });
          }
        }
      },
    };
  },
};

export = rule;
