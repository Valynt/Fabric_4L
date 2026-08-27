/**
 * @fileoverview Rule to prevent raw SQL with tenant_id outside migrations
 *
 * CONTRACT.md §2.1 - Tenant Isolation Boundary
 * Anti-Pattern: Raw SQL with tenant_id outside migrations
 *
 * Raw SQL must only contain tenant_id references in migration files.
 * Application code must use parameterized queries with RLS.
 *
 * @example
 * // Incorrect - raw SQL in application code
 * const query = `SELECT * FROM users WHERE tenant_id = '${tenantId}'`
 *
 * // Correct - use ORM or query builder with RLS
 * const users = await db.users.findMany({ where: { tenantId } });
 */

import { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow raw SQL with tenant_id outside migrations",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#21-tenant-isolation-boundary",
    },
    schema: [],
    messages: {
      noRawTenantQuery:
        "Raw SQL with tenant_id is not allowed outside migration files. " +
        "Use parameterized queries with RLS. " +
        "See contract.md §2.1 for canonical pattern.",
    },
  },

  create(context: Rule.RuleContext): Rule.RuleListener {
    const filename = context.filename;

    // Allow in migration files
    const isMigrationFile =
      /[\\/]migrations?[\\/]/i.test(filename) ||
      /\.migration\.(ts|js)$/i.test(filename) ||
      /migration.*\.(ts|js)$/i.test(filename);

    if (isMigrationFile) {
      return {};
    }

    // Patterns that indicate SQL with tenant_id
    const sqlPattern = /\b(SELECT|INSERT|UPDATE|DELETE|WHERE|FROM|JOIN)\b/i;
    const tenantIdPattern = /tenant[_-]?id/i;

    /**
     * Check if a string contains SQL with tenant_id
     */
    function containsRawTenantSql(value: string): boolean {
      return sqlPattern.test(value) && tenantIdPattern.test(value);
    }

    return {
      // Check string literals: "SELECT * WHERE tenant_id = ..."
      Literal(node: any): void {
        if (typeof node.value === "string" && containsRawTenantSql(node.value)) {
          context.report({
            node,
            messageId: "noRawTenantQuery",
          });
        }
      },

      // Check template literals
      TemplateLiteral(node: any): void {
        // Combine all quasis (string parts) to check for SQL patterns
        const quasis = node.quasis || [];
        const fullText = quasis.map((q: any) => q.value?.raw || "").join("");

        if (containsRawTenantSql(fullText)) {
          context.report({
            node,
            messageId: "noRawTenantQuery",
          });
        }
      },
    };
  },
};

export = rule;
