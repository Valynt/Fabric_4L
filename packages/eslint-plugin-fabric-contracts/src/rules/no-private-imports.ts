/**
 * @fileoverview Rule to prevent private imports (deep imports bypassing public API)
 *
 * CONTRACT.md §2.7 - Public API Surface
 * Anti-Pattern: Deep imports bypassing public API
 *
 * All imports must use the public API surface. Deep imports into src/, lib/,
 * dist/, or internal/ directories are prohibited.
 *
 * @example
 * // Incorrect - deep import
 * import { helper } from "@/components/ui/src/internal/helper";
 *
 * // Correct - public API import
 * import { Button } from "@/components/ui";
 */

import { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow private imports - use public API surface",
      category: "Canonical Contracts",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#27-public-api-surface",
    },
    schema: [],
    messages: {
      noPrivateImports:
        "Private imports bypassing public API are not allowed. " +
        "Import from the public API surface only. " +
        "See contract.md §2.7 for canonical pattern.",
    },
  },

  create(context: Rule.RuleContext): Rule.RuleListener {
    /**
     * Check if an import source is a private/deep import
     */
    function isPrivateImport(source: string): boolean {
      // Check for private path patterns
      const privatePatterns = [
        /[\\/]src[\\/]/,
        /[\\/]lib[\\/]/,
        /[\\/]dist[\\/]/,
        /[\\/]internal[\\/]/,
        /[\\/]private[\\/]/,
        /[\\/]_/, // Leading underscore (private convention)
        /\/[^\/]+\/(src|lib|dist|internal)\//, // package/src/... or package/lib/...
      ];

      return privatePatterns.some((pattern) => pattern.test(source));
    }

    /**
     * Check if the file is exempt (e.g., barrel file, test file)
     */
    function isExemptFile(filename: string): boolean {
      // Barrel files need to import from internal locations
      const isBarrelFile = /[\\/]index\.(ts|tsx|js|jsx)$/i.test(filename);
      const isTestFile = /\.(test|spec)\.(ts|tsx|js|jsx)$/i.test(filename);

      return isBarrelFile || isTestFile;
    }

    const filename = context.getFilename();
    if (isExemptFile(filename)) {
      return {};
    }

    return {
      // Check ES6 imports
      ImportDeclaration(node: any): void {
        const source = node.source?.value;
        if (source && isPrivateImport(source)) {
          context.report({
            node,
            messageId: "noPrivateImports",
          });
        }
      },

      // Check CommonJS require()
      CallExpression(node: any): void {
        const callee = node.callee;
        const args = node.arguments;

        if (
          callee.type === "Identifier" &&
          callee.name === "require" &&
          args.length > 0 &&
          args[0].type === "Literal" &&
          typeof args[0].value === "string"
        ) {
          const source = args[0].value;
          if (isPrivateImport(source)) {
            context.report({
              node,
              messageId: "noPrivateImports",
            });
          }
        }
      },
    };
  },
};

export = rule;
