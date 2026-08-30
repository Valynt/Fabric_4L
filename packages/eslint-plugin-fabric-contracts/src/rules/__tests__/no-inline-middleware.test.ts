import { RuleTester } from "eslint";
import rule from "../no-inline-middleware";

const ruleTester = new RuleTester({
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
  },
});

ruleTester.run("no-inline-middleware", rule, {
  valid: [
    {
      code: `app.use(cors());`,
      filename: "/repo/src/middleware/pipeline.ts",
    },
    {
      code: `app.use(cors());`,
      filename: "/repo/src/app.ts",
    },
    {
      code: `client.use(plugin);`,
      filename: "/repo/src/routes/users.ts",
    },
  ],
  invalid: [
    {
      code: `app.use(cors());`,
      filename: "/repo/src/routes/users.ts",
      errors: [{ messageId: "noInlineMiddleware" }],
    },
    {
      code: `router.use(authenticate());`,
      filename: "/repo/src/routes/users.ts",
      errors: [{ messageId: "noInlineMiddleware" }],
    },
    {
      code: `server.use(rateLimit());`,
      filename: "/repo/src/server/routes.ts",
      errors: [{ messageId: "noInlineMiddleware" }],
    },
  ],
});
