import { RuleTester } from "eslint";
import rule from "../no-tenant-id-parameter";

const ruleTester = new RuleTester({
  parser: require.resolve("@typescript-eslint/parser"),
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
  },
});

ruleTester.run("no-tenant-id-parameter", rule, {
  valid: [
    // Valid: function without tenantId parameter
    {
      code: `function getUser(userId: string) { return userId; }`,
    },
    // Valid: use AsyncLocalStorage context
    {
      code: `function getUser(userId: string) { const tenantId = getCurrentTenant(); return { userId, tenantId }; }`,
    },
    // Valid: different parameter names
    {
      code: `function getUser(id: string) { return id; }`,
    },
    // Valid: arrow function without tenantId
    {
      code: `const getUser = (userId: string) => userId;`,
    },
    // Valid: class method without tenantId
    {
      code: `class UserService { getUser(userId: string) { return userId; } }`,
    },
  ],
  invalid: [
    // Invalid: tenantId as parameter
    {
      code: `function getUser(tenantId: string, userId: string) { return userId; }`,
      errors: [{ messageId: "noTenantIdParameter" }],
    },
    // Invalid: tenant_id as parameter
    {
      code: `function getUser(tenant_id: string, userId: string) { return userId; }`,
      errors: [{ messageId: "noTenantIdParameter" }],
    },
    // Invalid: tenantID as parameter
    {
      code: `function getUser(tenantID: string, userId: string) { return userId; }`,
      errors: [{ messageId: "noTenantIdParameter" }],
    },
    // Invalid: arrow function with tenantId
    {
      code: `const getUser = (tenantId: string, userId: string) => userId;`,
      errors: [{ messageId: "noTenantIdParameter" }],
    },
    // Invalid: object destructuring with tenantId
    {
      code: `function getUser({ tenantId, userId }: { tenantId: string; userId: string }) { return userId; }`,
      errors: [{ messageId: "noTenantIdParameter" }],
    },
    // Invalid: class method with tenantId
    {
      code: `class UserService { getUser(tenantId: string, userId: string) { return userId; } }`,
      errors: [{ messageId: "noTenantIdParameter" }],
    },
    // Invalid: nested object destructuring tenantId
    {
      code: `function getUser({ user: { tenantId } }: { user: { tenantId: string } }) { return tenantId; }`,
      errors: [{ messageId: "noTenantIdParameter" }],
    },
  ],
});
