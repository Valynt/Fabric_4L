import { RuleTester } from "eslint";
import rule from "../no-json-parse-agent-output";

const ruleTester = new RuleTester({
  parser: require.resolve("@typescript-eslint/parser"),
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
  },
});

ruleTester.run("no-json-parse-agent-output", rule, {
  valid: [
    // Valid: JSON.parse on regular data
    {
      code: `const data = JSON.parse('{"key": "value"}');`,
    },
    // Valid: JSON.parse on config
    {
      code: `const config = JSON.parse(configString);`,
    },
    // Valid: structured generation
    {
      code: `const output = await agent.execute(input);`,
    },
    // Valid: other methods
    {
      code: `JSON.stringify(data);`,
    },
  ],
  invalid: [
    // Invalid: JSON.parse on LLM response
    {
      code: `const output = JSON.parse(llmResponse);`,
      errors: [{ messageId: "noJsonParseAgentOutput" }],
    },
    // Invalid: JSON.parse on agent output
    {
      code: `const result = JSON.parse(agentOutput);`,
      errors: [{ messageId: "noJsonParseAgentOutput" }],
    },
    // Invalid: JSON.parse on completion
    {
      code: `const data = JSON.parse(completion);`,
      errors: [{ messageId: "noJsonParseAgentOutput" }],
    },
    // Invalid: JSON.parse on GPT response
    {
      code: `const parsed = JSON.parse(gptResponse);`,
      errors: [{ messageId: "noJsonParseAgentOutput" }],
    },
    // Invalid: JSON.parse on Claude response
    {
      code: `const parsed = JSON.parse(claudeOutput);`,
      errors: [{ messageId: "noJsonParseAgentOutput" }],
    },
    // Invalid: JSON.parse on member expression from agent
    {
      code: `const parsed = JSON.parse(agent.response);`,
      errors: [{ messageId: "noJsonParseAgentOutput" }],
    },
  ],
});
