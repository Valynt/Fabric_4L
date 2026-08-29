import { RuleTester } from "eslint";
import rule from "../no-raw-tenant-query";

const ruleTester = new RuleTester({
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
  },
});

ruleTester.run("no-raw-tenant-query", rule, {
  valid: [
    {
      code: `const query = "SELECT * FROM users WHERE id = ?";`,
      filename: "/repo/src/users.ts",
    },
    {
      code: `const query = "SELECT * FROM users WHERE tenant_id = ?";`,
      filename: "/repo/src/migrations/001_create_users.ts",
    },
    {
      code: `const users = db.users.findMany({ where: { tenantId } });`,
      filename: "/repo/src/users.ts",
    },
  ],
  invalid: [
    {
      code: `const query = "SELECT * FROM users WHERE tenant_id = ?";`,
      filename: "/repo/src/users.ts",
      errors: [{ messageId: "noRawTenantQuery" }],
    },
    {
      code: "const query = `UPDATE accounts SET name = ${name} WHERE tenantId = ${tenantId}`;",
      filename: "/repo/src/accounts.ts",
      errors: [{ messageId: "noRawTenantQuery" }],
    },
    {
      code: `const query = "DELETE FROM sessions WHERE tenant-id = ?";`,
      filename: "/repo/src/sessions.ts",
      errors: [{ messageId: "noRawTenantQuery" }],
    },
  ],
});
