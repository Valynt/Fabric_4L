import { describe, it, expect } from "vitest";
import {
  getTenantContext,
  withTenantContext,
  createTestContext,
  withTenantContextOverride,
  extractTenantFromHeaders,
  generatePropagationHeaders,
  injectContextIntoMessage,
  extractContextFromMessage,
  TENANT_HEADER,
  SIGNATURE_HEADER
} from "./tenant-context.js";

describe("Tenant Context Management", () => {
  describe("getTenantContext & withTenantContext", () => {
    it("should return null when no context is set", () => {
      expect(getTenantContext()).toBeNull();
    });

    it("should return the context when within a scope", async () => {
      const testCtx = createTestContext({ tenant_id: "test-tenant-123" });

      await withTenantContext(testCtx, async () => {
        const ctx = getTenantContext();
        expect(ctx).not.toBeNull();
        expect(ctx?.tenant_id).toBe("test-tenant-123");
      });
    });

    it("should not leak context outside of scope", async () => {
      const testCtx = createTestContext({ tenant_id: "test-tenant-456" });

      await withTenantContext(testCtx, async () => {
        expect(getTenantContext()?.tenant_id).toBe("test-tenant-456");
      });

      expect(getTenantContext()).toBeNull();
    });

    it("should handle nested scopes correctly", async () => {
      const outerCtx = createTestContext({ tenant_id: "outer-tenant" });
      const innerCtx = createTestContext({ tenant_id: "inner-tenant" });

      await withTenantContext(outerCtx, async () => {
        expect(getTenantContext()?.tenant_id).toBe("outer-tenant");

        await withTenantContext(innerCtx, async () => {
          expect(getTenantContext()?.tenant_id).toBe("inner-tenant");
        });

        // Should revert to outer scope
        expect(getTenantContext()?.tenant_id).toBe("outer-tenant");
      });
    });

    it("should provide an immutable context", async () => {
      const testCtx = createTestContext({ tenant_id: "test-tenant" });

      await withTenantContext(testCtx, async () => {
        const ctx = getTenantContext();
        expect(ctx).not.toBeNull();
        if (ctx) {
          expect(() => {
            // @ts-expect-error Testing immutability
            ctx.tenant_id = "mutated-tenant";
          }).toThrow(TypeError);
        }
      });
    });
  });

  describe("withTenantContextOverride", () => {
    it("should create a new context with overrides", () => {
      const base = createTestContext({ tenant_id: "base-tenant", region: "us-east-1" });
      const overridden = withTenantContextOverride(base, { region: "eu-west-1" });

      expect(overridden.tenant_id).toBe("base-tenant");
      expect(overridden.region).toBe("eu-west-1");
      expect(base.region).toBe("us-east-1"); // Ensure original is unmodified
    });

    it("should not allow overriding tenant_id", () => {
      const base = createTestContext({ tenant_id: "base-tenant" });
      // @ts-expect-error Testing forbidden override
      const overridden = withTenantContextOverride(base, { tenant_id: "hacked-tenant" });

      expect(overridden.tenant_id).toBe("base-tenant");
    });

    it("should freeze the returned object", () => {
      const base = createTestContext();
      const overridden = withTenantContextOverride(base, { region: "eu-west-1" });

      expect(() => {
        // @ts-expect-error Testing immutability
        overridden.region = "us-east-2";
      }).toThrow(TypeError);
    });
  });

  describe("Cross-Service Propagation", () => {
    const mockSigner = (key: string) => `sig-${key}`;
    const mockVerifier = (key: string, sig: string) => sig === `sig-${key}`;

    describe("generatePropagationHeaders", () => {
      it("should generate correct headers", () => {
        const ctx = createTestContext({ tenant_id: "test-tenant", region: "us-west-2" });
        const headers = generatePropagationHeaders(ctx, mockSigner);

        expect(headers[TENANT_HEADER]).toBe("test-tenant");
        expect(headers[SIGNATURE_HEADER]).toBe("sig-test-tenant");
        expect(headers["x-fabric-region"]).toBe("us-west-2");
      });
    });

    describe("extractTenantFromHeaders", () => {
      it("should successfully extract a valid context", () => {
        const headers = {
          [TENANT_HEADER]: "test-tenant",
          [SIGNATURE_HEADER]: "sig-test-tenant"
        };
        const result = extractTenantFromHeaders(headers, mockVerifier);

        expect(result.valid).toBe(true);
        if (result.valid) {
          expect(result.context.tenant_id).toBe("test-tenant");
        }
      });

      it("should reject missing tenant header", () => {
        const headers = {
          [SIGNATURE_HEADER]: "sig-test-tenant"
        };
        const result = extractTenantFromHeaders(headers, mockVerifier);

        expect(result.valid).toBe(false);
        if (!result.valid) {
          expect(result.error).toContain(`Missing or invalid ${TENANT_HEADER} header`);
        }
      });

      it("should reject invalid signatures", () => {
        const headers = {
          [TENANT_HEADER]: "test-tenant",
          [SIGNATURE_HEADER]: "invalid-sig"
        };
        const result = extractTenantFromHeaders(headers, mockVerifier);

        expect(result.valid).toBe(false);
        if (!result.valid) {
          expect(result.error).toBe("Invalid request signature");
        }
      });
    });
  });

  describe("Message Queue Propagation", () => {
    describe("injectContextIntoMessage", () => {
      it("should inject context into a payload", () => {
        const payload = { data: "test-data" };
        const ctx = createTestContext({ tenant_id: "test-tenant" });

        const message = injectContextIntoMessage(payload, ctx);

        expect(message.data).toBe("test-data");
        expect(message._fabric_context).toBeDefined();
        expect(message._fabric_context.tenant_id).toBe("test-tenant");
      });
    });

    describe("extractContextFromMessage", () => {
      it("should successfully extract a valid context", () => {
        const ctx = createTestContext({ tenant_id: "test-tenant" });
        const message = { _fabric_context: ctx };

        const extracted = extractContextFromMessage(message);
        expect(extracted).not.toBeNull();
        expect(extracted?.tenant_id).toBe("test-tenant");
      });

      it("should return null for missing context", () => {
        const message = { data: "test-data" };
        const extracted = extractContextFromMessage(message);
        expect(extracted).toBeNull();
      });

      it("should return null for invalid context structure", () => {
        const message = { _fabric_context: { tenant_id: "test-tenant" } }; // Missing other required fields
        const extracted = extractContextFromMessage(message);
        expect(extracted).toBeNull();
      });
    });
  });
});
