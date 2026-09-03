import { RuleTester } from "eslint";
import rule from "../no-explicit-db-connect";

const ruleTester = new RuleTester({
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
  },
});

ruleTester.run("no-explicit-db-connect", rule, {
  valid: [
    {
      code: `const connection = db.connect({ database: "fabric" });`,
    },
    {
      code: `const connection = connect({ host: "localhost" });`,
    },
    {
      code: `const session = getDbSession();`,
    },
  ],
  invalid: [
    {
      code: `const connection = db.connect({ tenantId: "tenant-123" });`,
      errors: [{ messageId: "noExplicitDbConnect" }],
    },
    {
      code: `const connection = connect({ tenant_id: tenantId });`,
      errors: [{ messageId: "noExplicitDbConnect" }],
    },
    {
      code: `const connection = createConnection({ tenantId: tenantId });`,
      errors: [{ messageId: "noExplicitDbConnect" }],
    },
  ],
});
