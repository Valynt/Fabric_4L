import { RuleTester } from "eslint";
import rule from "../no-private-imports";

const ruleTester = new RuleTester({
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
  },
});

ruleTester.run("no-private-imports", rule, {
  valid: [
    // Valid: public API import
    {
      code: `import { Button } from "@/components/ui";`,
      filename: "pages/Home.tsx",
    },
    // Valid: npm package import
    {
      code: `import React from "react";`,
      filename: "components/App.tsx",
    },
    // Valid: barrel file importing internal (exempt)
    {
      code: `import { Button } from "./Button";`,
      filename: "components/ui/index.ts",
    },
    // Valid: test file importing internal (exempt)
    {
      code: `import { helper } from "../src/internal/helper";`,
      filename: "components/Button.test.tsx",
    },
  ],
  invalid: [
    // Invalid: deep import into src
    {
      code: `import { helper } from "@/components/ui/src/internal/helper";`,
      filename: "pages/Home.tsx",
      errors: [{ messageId: "noPrivateImports" }],
    },
    // Invalid: deep import into lib
    {
      code: `import { util } from "some-package/lib/internal/util";`,
      filename: "utils/helper.ts",
      errors: [{ messageId: "noPrivateImports" }],
    },
    // Invalid: require with private path
    {
      code: `const helper = require("@/components/ui/src/internal/helper");`,
      filename: "pages/Home.tsx",
      errors: [{ messageId: "noPrivateImports" }],
    },
  ],
});
