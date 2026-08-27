/**
 * @fileoverview Rule to prevent direct req.headers access outside auth middleware
 *
 * CONTRACT.md §2.1 - Tenant Isolation Boundary
 * Anti-Pattern: Direct req.headers access outside auth middleware
 *
 * Tenant context must be extracted by middleware and flow via AsyncLocalStorage.
 * This ensures:
 * - Single point of tenant resolution
 * - Consistent context propagation
 * - No header spoofing vulnerabilities
 */

import { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow direct req.headers access - use auth middleware",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#21-tenant-isolation-boundary",
    },
    schema: [],
    messages: {
      noReqTenantAccess:
        "Direct req.headers access is not allowed outside auth middleware. " +
        "Use AsyncLocalStorage context via getCurrentTenant(). " +
        "See contract.md §2.1 for canonical pattern.",
    },
  },

  create(context: Rule.RuleContext): Rule.RuleListener {
    // Check if we're in middleware directory
    const filename = context.filename;
    const isMiddleware = /middleware|auth/.test(filename);

    if (isMiddleware) {
      return {}; // Skip in middleware files
    }

    return {
      // Detect req.headers access
      MemberExpression(node: any): void {
        const obj = node.object;
        const prop = node.property;

        if (
          obj?.type === "Identifier" &&
          /req|request/i.test(obj.name) &&
          prop?.type === "Identifier" &&
          prop.name === "headers"
        ) {
          context.report({
            node,
            messageId: "noReqTenantAccess",
          });
        }
      },
    };
  },
};

export = rule;
