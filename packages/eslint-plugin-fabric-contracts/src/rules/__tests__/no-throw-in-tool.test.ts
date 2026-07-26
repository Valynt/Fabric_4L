import { RuleTester } from "eslint";
import rule from "../no-throw-in-tool";

const ruleTester = new RuleTester({
  parser: require.resolve("@typescript-eslint/parser"),
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
  },
});

ruleTester.run("no-throw-in-tool", rule, {
  valid: [
    // Valid: return error() helper in tool function
    {
      code: `
        function myTool() {
          if (invalid) return error("INVALID_INPUT", "Invalid input");
          return success({ result: "data" });
        }
      `,
      filename: "tools/example-tool.ts",
    },
    // Valid: throw in non-tool function
    {
      code: `function regularFunction() { throw new Error("ok"); }`,
      filename: "utils/helper.ts",
    },
    // Valid: return error without throw
    {
      code: `
        const dataTool = {
          execute: () => {
            if (!valid) return error("ERROR", "Failed");
            return success({});
          }
        };
      `,
      filename: "tools/data-tool.ts",
    },
  ],
  invalid: [
    // Invalid: throw in tool function
    {
      code: `
        function myTool() {
          if (invalid) throw new Error("Invalid input");
          return { result: "data" };
        }
      `,
      filename: "tools/bad-tool.ts",
      errors: [{ messageId: "noThrowInTool" }],
    },
    // Invalid: throw in tool arrow function
    {
      code: `
        const myTool = () => {
          throw new Error("fail");
        };
      `,
      filename: "tools/bad-tool.ts",
      errors: [{ messageId: "noThrowInTool" }],
    },
    // Invalid: throw in exported tool
    {
      code: `
        export const dataTool = {
          run: () => {
            throw new Error("fail");
          }
        };
      `,
      filename: "tools/bad-tool.ts",
      errors: [{ messageId: "noThrowInTool" }],
    },
  ],
});
