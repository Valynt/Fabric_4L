import { RuleTester } from "eslint";
import rule from "../no-circular-dependencies";

const ruleTester = new RuleTester({
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
  },
});

ruleTester.run("no-circular-dependencies", rule, {
  valid: [
    {
      code: `import { service } from "./service";\nexport { handler } from "./handler";`,
    },
    {
      code: `import React from "react";\nexport const value = 1;`,
    },
    {
      code: `export { createUser } from "./users";`,
    },
  ],
  invalid: [
    {
      code: `import { userRoutes } from "./index";\nexport const route = userRoutes;`,
      errors: [{ messageId: "noCircularDependenciesNote" }],
    },
    {
      code: `import { userRoutes } from "./index.ts";\nexport const route = userRoutes;`,
      errors: [{ messageId: "noCircularDependenciesNote" }],
    },
  ],
});
