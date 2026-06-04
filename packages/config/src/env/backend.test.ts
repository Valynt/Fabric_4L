import { describe, expect, it } from "vitest";

import { backendEnvSchema, loadBackendEnv, validateBackendEnvForProductionLike } from "./backend.js";

const STRONG_SECRET = "strong-secret-value-with-at-least-32-chars";

function validProductionEnv(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    NODE_ENV: "production",
    LOG_LEVEL: "info",
    PORT: "8000",
    DATABASE_URL: "postgresql://fabric_app:strong_password@db.internal.example.com:5432/fabric",
    REDIS_URL: "rediss://redis.internal.example.com:6379/0",
    JWT_SECRET: STRONG_SECRET,
    API_KEY_HMAC_SECRET: STRONG_SECRET,
    SERVICE_AUTH_SECRET: STRONG_SECRET,
    OPENAI_API_KEY: "sk-test-local-placeholder-for-schema-only",
    NEO4J_PASSWORD: STRONG_SECRET,
    CORS_ORIGINS: "https://app.example.com",
    CREDENTIALS_MASTER_KEY: STRONG_SECRET,
    DEFAULT_TENANT_ID: "11111111-1111-4111-8111-111111111111",
    MULTI_TENANT_MODE: "true",
    LLM_PROVIDER: "openai",
    DEBUG: "false",
    SEED_DEMO_DATA: "false",
    ...overrides,
  };
}

describe("backend environment schema", () => {
  it("loads a complete production-like environment", () => {
    const parsed = loadBackendEnv(validProductionEnv());

    expect(parsed.NODE_ENV).toBe("production");
    expect(parsed.CORS_ORIGINS).toBe("https://app.example.com");
  });

  it("rejects wildcard CORS origins in the strict backend schema", () => {
    const result = backendEnvSchema.safeParse(validProductionEnv({ CORS_ORIGINS: "*" }));

    expect(result.success).toBe(false);
  });

  it("fails closed when production-like auth bypass or mock controls are enabled", () => {
    expect(() =>
      validateBackendEnvForProductionLike(
        validProductionEnv({
          ALLOW_INSECURE_DEV_AUTH_BYPASS: "true",
          ALLOW_MOCK_LLM: "true",
        }),
      ),
    ).toThrow(/ALLOW_INSECURE_DEV_AUTH_BYPASS|ALLOW_MOCK_LLM/);
  });

  it("permits relaxed local development values through the production safety validator", () => {
    expect(() =>
      validateBackendEnvForProductionLike(
        validProductionEnv({
          NODE_ENV: "development",
          CORS_ORIGINS: "*",
          DEFAULT_TENANT_ID: "default",
          LLM_PROVIDER: "mock",
        }),
      ),
    ).not.toThrow();
  });
});
