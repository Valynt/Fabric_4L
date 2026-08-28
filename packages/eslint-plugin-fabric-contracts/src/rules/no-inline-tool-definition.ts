/**
 * @fileoverview Rule to prevent inline tool definitions outside tools/ directory
 *
 * CONTRACT.md §2.4 - Tool Invocation Boundary
 * Anti-Pattern: Inline tool definitions outside tools/
 *
 * Tools must be defined in the dedicated tools/ directory using the canonical
 * defineTool() helper from tools/registry.ts.
 *
 * @example
 * // Incorrect - inline tool definition
 * const myTool = {
 *   name: "my-tool",
 *   execute: () => { ... }
 * };
 *
 * // Correct - in tools/ directory with defineTool
 * // See tools/example-tool.ts for canonical implementation
 */

import { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow inline tool definitions - use tools/ directory",
      recommended: true,
      url: "https://github.com/bmsull560/Fabric_4L/blob/main/contract.md#24-tool-invocation-boundary",
    },
    schema: [],
    messages: {
      noInlineToolDefinition:
        "Inline tool definitions are not allowed. Use tools/ directory with defineTool(). " +
        "See contract.md §2.4 for canonical pattern.",
    },
  },

  create(context: Rule.RuleContext): Rule.RuleListener {
    const filename = context.filename;

    // Allow in tools directory
    const isToolsFile = /[\\/]tools[\\/]/i.test(filename);
    const isRegistryFile = /registry\.(ts|js)$/i.test(filename);

    if (isToolsFile || isRegistryFile) {
      return {};
    }

    return {
      // Detect object properties named "tools" containing function definitions
      Property(node: any): void {
        const key = node.key;

        // Check if property is named "tools"
        if (key?.type === "Identifier" && key.name === "tools") {
          const value = node.value;

          // Check if value is an object or array with function properties
          if (value?.type === "ObjectExpression" || value?.type === "ArrayExpression") {
            context.report({
              node,
              messageId: "noInlineToolDefinition",
            });
          }
        }

        // Check for tool-like properties: name + execute/handler/run
        if (key?.type === "Identifier") {
          const value = node.value;
          if (value?.type === "ObjectExpression") {
            const properties = value.properties || [];
            const hasName = properties.some(
              (p: any) =>
                p.key?.type === "Identifier" &&
                p.key.name === "name" &&
                p.value?.type === "Literal" &&
                typeof p.value.value === "string"
            );
            const hasExecute = properties.some(
              (p: any) =>
                p.key?.type === "Identifier" &&
                /^(execute|handler|run|call)$/i.test(p.key.name) &&
                (p.value?.type === "FunctionExpression" ||
                  p.value?.type === "ArrowFunctionExpression")
            );

            if (hasName && hasExecute) {
              context.report({
                node,
                messageId: "noInlineToolDefinition",
              });
            }
          }
        }
      },

      // Detect tool exports
      ExportNamedDeclaration(node: any): void {
        const declaration = node.declaration;
        if (declaration?.type === "VariableDeclaration") {
          const declarations = declaration.declarations || [];
          for (const decl of declarations) {
            const id = decl.id;
            const init = decl.init;

            // Check if variable name suggests it's a tool
            if (
              id?.type === "Identifier" &&
              /Tool$|^tool/i.test(id.name) &&
              init?.type === "ObjectExpression"
            ) {
              context.report({
                node,
                messageId: "noInlineToolDefinition",
              });
            }
          }
        }
      },
    };
  },
};

export = rule;
