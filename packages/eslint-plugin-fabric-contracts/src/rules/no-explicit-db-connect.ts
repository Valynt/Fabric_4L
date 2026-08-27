/**
 * @fileoverview Rule to prevent explicit db.connect() with tenant identifiers
 *
 * CONTRACT.md §2.2 - Database Session Boundary
 * Anti-Pattern: db.connect() with tenant identifiers
 *
 * Database connections must use the canonical session manager with automatic
 * tenant context injection, not explicit connection parameters.
 *
 * @example
 * // Incorrect - explicit db.connect with tenant
 * const db = await db.connect({ tenantId: "tenant-123" });
 *
 * // Correct - use canonical session manager
 * const db = await getDbSession(); // Tenant from AsyncLocalStorage
 */

import { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow explicit db.connect() with tenant identifiers",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#22-database-session-boundary",
    },
    schema: [],
    messages: {
      noExplicitDbConnect:
        "Explicit db.connect() with tenant identifiers is not allowed. " +
        "Use the canonical session manager with AsyncLocalStorage context. " +
        "See contract.md §2.2 for canonical pattern.",
    },
  },

  create(context: Rule.RuleContext): Rule.RuleListener {
    /**
     * Check if an object property is a tenant identifier
     */
    function isTenantIdentifier(name: string): boolean {
      return /tenant[_-]?id/i.test(name);
    }

    return {
      // Detect db.connect() calls
      CallExpression(node: any): void {
        const callee = node.callee;

        // Check for db.connect() or similar patterns
        if (
          callee.type === "MemberExpression" &&
          callee.object?.name === "db" &&
          callee.property?.name === "connect"
        ) {
          // Check if arguments contain tenant identifiers
          const args = node.arguments;
          if (args.length > 0 && args[0].type === "ObjectExpression") {
            const properties = args[0].properties || [];
            const hasTenantId = properties.some(
              (prop: any) =>
                prop.type === "Property" &&
                prop.key?.type === "Identifier" &&
                isTenantIdentifier(prop.key.name)
            );

            if (hasTenantId) {
              context.report({
                node,
                messageId: "noExplicitDbConnect",
              });
            }
          }
        }

        // Also check for other connection patterns: createConnection, connect
        if (
          callee.type === "Identifier" &&
          /connect|createConnection/i.test(callee.name)
        ) {
          const args = node.arguments;
          if (args.length > 0 && args[0].type === "ObjectExpression") {
            const properties = args[0].properties || [];
            const hasTenantId = properties.some(
              (prop: any) =>
                prop.type === "Property" &&
                prop.key?.type === "Identifier" &&
                isTenantIdentifier(prop.key.name)
            );

            if (hasTenantId) {
              context.report({
                node,
                messageId: "noExplicitDbConnect",
              });
            }
          }
        }
      },
    };
  },
};

export = rule;
