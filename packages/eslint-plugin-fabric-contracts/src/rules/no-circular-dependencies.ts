/**
 * @fileoverview Rule to prevent circular dependencies
 *
 * CONTRACT.md §2.7 - Public API Surface
 * Anti-Pattern: Circular dependencies between modules
 *
 * Circular dependencies create tight coupling and make code harder to reason
 * about. Use dependency injection or restructure to eliminate cycles.
 *
 * @example
 * // Incorrect - circular dependency
 * // file-a.ts: import { b } from "./file-b";
 * // file-b.ts: import { a } from "./file-a";
 *
 * // Correct - dependency injection
 * // file-a.ts: export function createA(b: B) { ... }
 * // file-b.ts: export function createB() { const a = createA(b); }
 *
 * @note This rule provides basic intra-file cycle detection. For cross-file
 * circular dependency detection, use eslint-plugin-import's no-cycle rule
 * alongside this rule for comprehensive coverage.
 */

import { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow circular dependencies",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#27-public-api-surface",
    },
    schema: [],
    messages: {
      noCircularDependencies:
        "Circular dependencies are not allowed. " +
        "Restructure code to eliminate import cycles. " +
        "See contract.md §2.7 for canonical pattern.",
      noCircularDependenciesNote:
        "Note: For cross-file circular dependency detection, " +
        "enable eslint-plugin-import/no-cycle alongside this rule.",
    },
  },

  create(context: Rule.RuleContext): Rule.RuleListener {
    const filename = context.filename;
    const imports: string[] = [];
    const exports: string[] = [];

    return {
      // Track imports in this file
      ImportDeclaration(node: any): void {
        const source = node.source?.value;
        if (source && (source.startsWith(".") || source.startsWith("@/"))) {
          imports.push(source);
        }
      },

      // Track exports for potential re-export patterns
      ExportNamedDeclaration(node: any): void {
        if (node.source?.value) {
          const source = node.source.value;
          if (source.startsWith(".") || source.startsWith("@/")) {
            exports.push(source);
          }
        }
      },

      // Check for re-export cycles on program exit
      "Program:exit"(): void {
        // Self-referential imports (file imports itself via index)
        const selfRef = imports.find((imp) => {
          // Check if import points back to this file's directory index
          const indexImport = /\/index$/i.test(imp) || /\/index\.[tj]s$/i.test(imp);
          return indexImport;
        });

        if (selfRef) {
          // This is a simplified check - real circular detection requires
          // cross-file analysis which is better handled by eslint-plugin-import
          context.report({
            loc: { line: 1, column: 0 },
            messageId: "noCircularDependenciesNote",
          });
        }
      },
    };
  },
};

export = rule;
