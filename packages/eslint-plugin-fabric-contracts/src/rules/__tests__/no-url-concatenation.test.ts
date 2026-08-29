import { RuleTester } from "eslint";
import rule from "../no-url-concatenation";

const ruleTester = new RuleTester({
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
  },
});

ruleTester.run("no-url-concatenation", rule, {
  valid: [
    // Valid: no URL concatenation
    {
      code: `const name = "John" + " Doe";`,
    },
    // Valid: number addition
    {
      code: `const sum = 1 + 2;`,
    },
    // Valid: using URL constructor
    {
      code: `const url = new URL('/path', baseUrl);`,
    },
  ],
  invalid: [
    // Invalid: URL path concatenation
    {
      code: `const path = '/api/users/' + userId;`,
      errors: [{ messageId: "noUrlConcatenation" }],
    },
    // Invalid: URL concatenation with template
    {
      code: `const url = "/dashboard/" + section;`,
      errors: [{ messageId: "noUrlConcatenation" }],
    },
    // Invalid: full URL concatenation
    {
      code: `const url = 'https://api.' + domain + '/v1/users';`,
      errors: [{ messageId: "noUrlConcatenation" }],
    },
    // Invalid: path with slash
    {
      code: `const path = base + '/endpoint';`,
      errors: [{ messageId: "noUrlConcatenation" }],
    },
  ],
});
