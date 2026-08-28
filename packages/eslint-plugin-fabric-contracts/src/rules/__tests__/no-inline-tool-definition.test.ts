import { RuleTester } from "eslint";
import rule from "../no-inline-tool-definition";

const ruleTester = new RuleTester({
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
  },
});

ruleTester.run("no-inline-tool-definition", rule, {
  valid: [
    {
      code: `const myTool = { name: "lookup", execute: () => true };`,
      filename: "/repo/src/tools/lookup.ts",
    },
    {
      code: `export const myTool = { name: "lookup", execute: () => true };`,
      filename: "/repo/src/tools/registry.ts",
    },
    {
      code: `const config = { handlers: [] };`,
      filename: "/repo/src/agents/agent.ts",
    },
  ],
  invalid: [
    {
      code: `const agent = { tools: { lookup: () => true } };`,
      filename: "/repo/src/agents/agent.ts",
      errors: [{ messageId: "noInlineToolDefinition" }],
    },
    {
      code: `const agent = { lookupTool: { name: "lookup", execute: () => true } };`,
      filename: "/repo/src/agents/agent.ts",
      errors: [{ messageId: "noInlineToolDefinition" }],
    },
    {
      code: `export const searchTool = { name: "search", run: () => true };`,
      filename: "/repo/src/agents/search.ts",
      errors: [{ messageId: "noInlineToolDefinition" }],
    },
  ],
});
