#!/usr/bin/env node
/**
 * Regression tests for assert-frontend-release-evidence.mjs.
 *
 * The release evidence gate is intentionally strict because it is the final
 * bridge between local workflow confidence and real production-build evidence.
 * This self-test proves the validator accepts a complete redacted packet and
 * rejects a packet that omits a named live-provider proof.
 */
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, "..", "..");
const repoRoot = resolve(webRoot, "..", "..");
const tmpRoot = resolve(repoRoot, ".tmp", "frontend-release-evidence-validator");
const validatorPath = resolve(webRoot, "scripts", "quality", "assert-frontend-release-evidence.mjs");

mkdirSync(tmpRoot, { recursive: true });

try {
  const validPath = writeEvidence("valid.json", buildEvidence());
  const valid = runValidator(validPath);
  if (valid.status !== 0) {
    fail(`Expected valid release evidence to pass.\n${valid.output}`);
  }

  const missingProvider = buildEvidence();
  missingProvider.liveProviderSmoke.providers = missingProvider.liveProviderSmoke.providers.filter(
    (provider) => provider.name !== "crm",
  );
  const missingProviderPath = writeEvidence("missing-provider.json", missingProvider);
  const invalid = runValidator(missingProviderPath);
  if (invalid.status === 0) {
    fail("Expected release evidence missing crm provider proof to fail.");
  }
  if (!invalid.output.includes("liveProviderSmoke.providers must include crm")) {
    fail(`Missing-provider failure did not name the absent crm provider.\n${invalid.output}`);
  }

  console.log("Frontend release evidence validator self-test passed.");
} finally {
  rmSync(tmpRoot, { recursive: true, force: true });
}

function writeEvidence(filename, payload) {
  const path = resolve(tmpRoot, filename);
  writeFileSync(path, JSON.stringify(payload, null, 2), "utf8");
  return path;
}

function runValidator(path) {
  const result = spawnSync(process.execPath, [validatorPath, relative(repoRoot, path)], {
    cwd: repoRoot,
    encoding: "utf8",
  });
  return {
    status: result.status ?? 1,
    output: `${result.stdout ?? ""}${result.stderr ?? ""}`,
  };
}

function buildEvidence() {
  return {
    schemaVersion: 1,
    generatedAt: "2026-06-25T00:00:00Z",
    releaseCandidate: {
      commitSha: "0123456789abcdef0123456789abcdef01234567",
      imageDigest: "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      productionBuildCommand: "corepack pnpm --dir apps/web run build",
      productionBuildStatus: "passed",
    },
    staticFrontendGates: {
      workflowContracts: {
        command: "corepack pnpm --dir apps/web run test:workflow-contracts",
        status: "passed",
      },
      routeInventory: {
        command: "corepack pnpm --dir apps/web run test:route-inventory",
        status: "passed",
      },
      frontendVerification: {
        command: "corepack pnpm --dir apps/web run verify:frontend",
        status: "passed",
      },
    },
    p0BrowserJourneys: {
      command: "corepack pnpm --dir apps/web run test:e2e:live:p0",
      status: "passed",
      environment: "production-build-real-internal-infra",
      infrastructure: {
        frontendBuild: "production",
        api: "real",
        postgresMigrations: "real",
        redis: "real",
        workersAndQueues: "real",
        objectStorage: "real-or-production-compatible",
        clerk: "development-instance",
        externalProviders: "deterministic-stand-ins",
      },
      journeys: [
        "P0-ACCOUNT-LIFECYCLE",
        "P0-CALC-EVIDENCE",
        "P0-APPROVAL-EXPORT",
        "P0-AGENT-GOVERNANCE",
        "P0-LAYER-VALIDATION",
      ].map((id) => ({
        id,
        status: "passed",
        redactedEvidence: `artifacts/redacted/${id}.json`,
      })),
      unexpectedSkippedP0: [],
      noUnexpectedBrowserErrors: true,
      noHttp5xx: true,
      noUnhandledMockRequests: true,
      noFailedBackgroundJobs: true,
      traceRetention: "retain-on-failure",
      screenshots: "only-on-failure",
      videos: "retain-on-failure",
      artifacts: ["artifacts/playwright/p0-report/index.html"],
    },
    securityAndAuthorization: {
      authorizationMatrix: {
        command: "python scripts/ci/run_authorization_matrix.py",
        status: "passed",
        casesPassed: 24,
        casesTotal: 24,
        actors: ["tenant-a-standard", "tenant-a-admin", "tenant-a-reviewer", "tenant-b-standard"],
      },
      tenantIsolationApi: {
        command: "python -m pytest tests/security/test_tenant_isolation_api.py",
        status: "passed",
      },
      tenantIsolationRetrieval: {
        command: "python -m pytest tests/security/test_retrieval_tenant_isolation.py",
        status: "passed",
      },
    },
    governanceAndAudit: {
      approvalGatedExport: {
        command: "python -m pytest tests/security/test_approval_export.py",
        status: "passed",
      },
      auditTrail: {
        command: "python -m pytest tests/security/test_audit_trail.py",
        status: "passed",
      },
    },
    liveProviderSmoke: {
      command: "python scripts/ci/run_live_provider_smoke.py",
      status: "passed",
      providers: ["llm", "crm", "email", "clerk", "pdf-processing", "export-rendering"].map((name) => ({
        name,
        status: "passed",
        redactedEvidence: `artifacts/redacted/provider-${name}.json`,
      })),
    },
    postDeploySynthetics: {
      command: "python scripts/ci/run_post_deploy_synthetics.py",
      status: "passed",
      checks: [
        "sign-in",
        "home",
        "search-known-object",
        "submit-ingestion-job",
        "observe-job-completion",
        "trace-and-audit",
        "no-browser-errors-or-http-5xx",
      ].map((name) => ({
        name,
        status: "passed",
        redactedEvidence: `artifacts/redacted/synthetic-${name}.json`,
      })),
    },
    canonicalEvidencePacket: {
      path: "artifacts/release/evidence-packet/release-evidence-packet.json",
      status: "passed",
    },
  };
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
