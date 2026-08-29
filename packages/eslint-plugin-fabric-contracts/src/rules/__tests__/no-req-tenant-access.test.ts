import { RuleTester } from "eslint";
import rule from "../no-req-tenant-access";

const ruleTester = new RuleTester({
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
  },
});

ruleTester.run("no-req-tenant-access", rule, {
  valid: [
    {
      code: `const tenant = req.headers["x-tenant-id"];`,
      filename: "/repo/src/middleware/auth.ts",
    },
    {
      code: `const tenant = getCurrentTenant();`,
      filename: "/repo/src/routes/users.ts",
    },
    {
      code: `const headers = response.headers;`,
      filename: "/repo/src/routes/users.ts",
    },
  ],
  invalid: [
    {
      code: `const tenant = req.headers["x-tenant-id"];`,
      filename: "/repo/src/routes/users.ts",
      errors: [{ messageId: "noReqTenantAccess" }],
    },
    {
      code: `const tenant = request.headers["x-tenant-id"];`,
      filename: "/repo/src/routes/users.ts",
      errors: [{ messageId: "noReqTenantAccess" }],
    },
  ],
});
