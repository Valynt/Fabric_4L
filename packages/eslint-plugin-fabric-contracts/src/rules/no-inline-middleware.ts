/**
 * @fileoverview Rule to prevent inline middleware (app.use outside pipeline config)
 *
 * CONTRACT.md §2.4 - Tool Invocation Boundary
 * Anti-Pattern: Inline middleware registration
 *
 * Middleware must be registered via the centralized pipeline configuration,
 * not through scattered app.use() calls.
 *
 * @example
 * // Incorrect - inline middleware
 * app.use(cors());
 * app.use(bodyParser());
 *
 * // Correct - pipeline config
 * // See middleware/pipeline.ts for eight-phase middleware stack
 */

import { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow inline middleware - use pipeline config",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#24-tool-invocation-boundary",
    },
    schema: [],
    messages: {
      noInlineMiddleware:
        "Inline middleware (app.use) is not allowed outside pipeline config. " +
        "Use the centralized pipeline configuration. " +
        "See contract.md §2.4 for canonical pattern.",
    },
  },

  create(context: Rule.RuleContext): Rule.RuleListener {
    const filename = context.filename;

    // Allow in pipeline config files
    const isPipelineFile =
      /[\\/]pipeline\.(ts|js)$/i.test(filename) ||
      /[\\/]middleware[\\/]config[\\/]/i.test(filename) ||
      /[\\/]app\.(ts|js)$/i.test(filename); // Allow in main app entry

    if (isPipelineFile) {
      return {};
    }

    return {
      // Detect app.use() calls
      CallExpression(node: any): void {
        const callee = node.callee;

        // Check for app.use(), router.use(), etc.
        if (
          callee.type === "MemberExpression" &&
          callee.property?.name === "use" &&
          callee.object?.name !== undefined
        ) {
          // Common app/router variable names
          const commonNames = /^(app|router|server|express|application|api)$/i;
          if (commonNames.test(callee.object.name)) {
            context.report({
              node,
              messageId: "noInlineMiddleware",
            });
          }
        }
      },
    };
  },
};

export = rule;
