import { RuleTester } from "eslint";
import rule from "../require-semantic-contract-metadata";

const ruleTester = new RuleTester({
  parser: require.resolve("@typescript-eslint/parser"),
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
  },
});

ruleTester.run("require-semantic-contract-metadata", rule, {
  valid: [
    {
      code: `function* stream() { yield { type: AgentEventType.RUN_FINISHED, timestamp: now(), metadata: { semanticContractVersion: "2.0.0" } }; }`,
    },
    {
      code: `const event = { type: "RUN_FINISHED", metadata: { semanticContractValid: true } };`,
    },
    {
      code: `const event = { type: "RUN_FINISHED", metadata: { contractVersions: { semanticContract: "2.0.0" } } };`,
    },
    {
      code: `const event = { type: "RUN_FINISHED", metadata: { ...semanticMetadata } };`,
    },
    {
      code: `const event = { type: AgentEventType.RUN_STARTED, metadata: {} };`,
    },
  ],
  invalid: [
    {
      code: `const event = { type: AgentEventType.RUN_FINISHED, metadata: { traceId } };`,
      errors: [{ messageId: "requireSemanticContractMetadata" }],
    },
    {
      code: `const event = { type: "RUN_FINISHED", metadata: { traceId: "trace-1" } };`,
      errors: [{ messageId: "requireSemanticContractMetadata" }],
    },
    {
      code: `const event = { type: AgentEventType.RUN_FINISHED };`,
      errors: [{ messageId: "requireSemanticContractMetadata" }],
    },
  ],
});
