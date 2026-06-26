#!/usr/bin/env node
/**
 * Validates the frontend supplement to the canonical release evidence packet.
 *
 * This script does not generate release evidence and does not replace
 * scripts/ci/generate_release_evidence_packet.py. It fails closed unless the
 * caller supplies a redacted JSON evidence file produced by the release run.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, "..", "..");
const repoRoot = resolve(webRoot, "..", "..");

const evidenceArg = process.argv.slice(2).find((arg) => arg !== "--") || process.env.FRONTEND_RELEASE_EVIDENCE;
if (!evidenceArg) {
  fail(
    "Frontend release evidence path is required. Set FRONTEND_RELEASE_EVIDENCE or pass a JSON path."
  );
}

const evidencePath = isAbsolute(evidenceArg) ? evidenceArg : resolve(repoRoot, evidenceArg);
if (!existsSync(evidencePath)) {
  fail(`Frontend release evidence file does not exist: ${displayPath(evidencePath)}`);
}

let evidence;
try {
  evidence = JSON.parse(readFileSync(evidencePath, "utf8"));
} catch (error) {
  fail(`Frontend release evidence is not valid JSON: ${error.message}`);
}

const failures = [];
const requiredP0Journeys = [
  "P0-ACCOUNT-LIFECYCLE",
  "P0-CALC-EVIDENCE",
  "P0-APPROVAL-EXPORT",
  "P0-AGENT-GOVERNANCE",
  "P0-LAYER-VALIDATION",
];
const requiredAuthorizationActors = [
  "tenant-a-standard",
  "tenant-a-admin",
  "tenant-a-reviewer",
  "tenant-b-standard",
];
const requiredLiveProviders = [
  "llm",
  "crm",
  "email",
  "clerk",
  "pdf-processing",
  "export-rendering",
];
const requiredSyntheticChecks = [
  "sign-in",
  "home",
  "search-known-object",
  "submit-ingestion-job",
  "observe-job-completion",
  "trace-and-audit",
  "no-browser-errors-or-http-5xx",
];

requireValue(evidence.schemaVersion, "schemaVersion", 1);
requireIsoTimestamp(evidence.generatedAt, "generatedAt");
requireMatch(
  evidence.releaseCandidate?.commitSha,
  /^[0-9a-f]{40}$/i,
  "releaseCandidate.commitSha must be the exact 40-character commit SHA under test"
);
requireMatch(
  evidence.releaseCandidate?.imageDigest,
  /^sha256:[0-9a-f]{64}$/i,
  "releaseCandidate.imageDigest must be an immutable sha256 digest"
);
requirePassed(evidence.releaseCandidate?.productionBuildStatus, "releaseCandidate.productionBuildStatus");
requireCommand(evidence.releaseCandidate?.productionBuildCommand, "releaseCandidate.productionBuildCommand");

requirePassed(evidence.staticFrontendGates?.workflowContracts?.status, "staticFrontendGates.workflowContracts.status");
requireCommand(evidence.staticFrontendGates?.workflowContracts?.command, "staticFrontendGates.workflowContracts.command");
requirePassed(evidence.staticFrontendGates?.routeInventory?.status, "staticFrontendGates.routeInventory.status");
requireCommand(evidence.staticFrontendGates?.routeInventory?.command, "staticFrontendGates.routeInventory.command");
requirePassed(evidence.staticFrontendGates?.frontendVerification?.status, "staticFrontendGates.frontendVerification.status");
requireCommand(evidence.staticFrontendGates?.frontendVerification?.command, "staticFrontendGates.frontendVerification.command");

const p0 = evidence.p0BrowserJourneys;
requirePassed(p0?.status, "p0BrowserJourneys.status");
requireCommand(p0?.command, "p0BrowserJourneys.command");
requireValue(p0?.environment, "p0BrowserJourneys.environment", "production-build-real-internal-infra");
requireInfrastructure(p0?.infrastructure, "p0BrowserJourneys.infrastructure");
requirePassedEvidenceItems(p0?.journeys, "p0BrowserJourneys.journeys");
requireNamedItems(p0?.journeys, requiredP0Journeys, "p0BrowserJourneys.journeys");
requireEmptyArray(p0?.unexpectedSkippedP0, "p0BrowserJourneys.unexpectedSkippedP0");
requireTrue(p0?.noUnexpectedBrowserErrors, "p0BrowserJourneys.noUnexpectedBrowserErrors");
requireTrue(p0?.noHttp5xx, "p0BrowserJourneys.noHttp5xx");
requireTrue(p0?.noUnhandledMockRequests, "p0BrowserJourneys.noUnhandledMockRequests");
requireTrue(p0?.noFailedBackgroundJobs, "p0BrowserJourneys.noFailedBackgroundJobs");
requireValue(p0?.traceRetention, "p0BrowserJourneys.traceRetention", "retain-on-failure");
requireValue(p0?.screenshots, "p0BrowserJourneys.screenshots", "only-on-failure");
requireValue(p0?.videos, "p0BrowserJourneys.videos", "retain-on-failure");
requireNonEmptyStringArray(p0?.artifacts, "p0BrowserJourneys.artifacts");

const auth = evidence.securityAndAuthorization;
requirePassed(auth?.authorizationMatrix?.status, "securityAndAuthorization.authorizationMatrix.status");
requireCommand(auth?.authorizationMatrix?.command, "securityAndAuthorization.authorizationMatrix.command");
requirePositiveCoverage(
  auth?.authorizationMatrix?.casesPassed,
  auth?.authorizationMatrix?.casesTotal,
  "securityAndAuthorization.authorizationMatrix"
);
requireStringSet(auth?.authorizationMatrix?.actors, requiredAuthorizationActors, "securityAndAuthorization.authorizationMatrix.actors");
requirePassed(auth?.tenantIsolationApi?.status, "securityAndAuthorization.tenantIsolationApi.status");
requireCommand(auth?.tenantIsolationApi?.command, "securityAndAuthorization.tenantIsolationApi.command");
requirePassed(auth?.tenantIsolationRetrieval?.status, "securityAndAuthorization.tenantIsolationRetrieval.status");
requireCommand(auth?.tenantIsolationRetrieval?.command, "securityAndAuthorization.tenantIsolationRetrieval.command");

const governance = evidence.governanceAndAudit;
requirePassed(governance?.approvalGatedExport?.status, "governanceAndAudit.approvalGatedExport.status");
requireCommand(governance?.approvalGatedExport?.command, "governanceAndAudit.approvalGatedExport.command");
requirePassed(governance?.auditTrail?.status, "governanceAndAudit.auditTrail.status");
requireCommand(governance?.auditTrail?.command, "governanceAndAudit.auditTrail.command");

requirePassed(evidence.liveProviderSmoke?.status, "liveProviderSmoke.status");
requireCommand(evidence.liveProviderSmoke?.command, "liveProviderSmoke.command");
requirePassedEvidenceItems(evidence.liveProviderSmoke?.providers, "liveProviderSmoke.providers");
requireNamedItems(evidence.liveProviderSmoke?.providers, requiredLiveProviders, "liveProviderSmoke.providers");

requirePassed(evidence.postDeploySynthetics?.status, "postDeploySynthetics.status");
requireCommand(evidence.postDeploySynthetics?.command, "postDeploySynthetics.command");
requirePassedEvidenceItems(evidence.postDeploySynthetics?.checks, "postDeploySynthetics.checks");
requireNamedItems(evidence.postDeploySynthetics?.checks, requiredSyntheticChecks, "postDeploySynthetics.checks");

requireValue(
  evidence.canonicalEvidencePacket?.path,
  "canonicalEvidencePacket.path",
  "artifacts/release/evidence-packet/release-evidence-packet.json"
);
requirePassed(evidence.canonicalEvidencePacket?.status, "canonicalEvidencePacket.status");

if (failures.length > 0) {
  console.error(`Frontend release evidence is incomplete: ${displayPath(evidencePath)}`);
  for (const failure of failures) {
    console.error(` - ${failure}`);
  }
  process.exit(1);
}

console.log(`Frontend release evidence passed: ${displayPath(evidencePath)}`);

function requireValue(actual, path, expected) {
  if (actual !== expected) {
    failures.push(`${path} must be ${JSON.stringify(expected)}`);
  }
}

function requirePassed(actual, path) {
  if (actual !== "passed") {
    failures.push(`${path} must be "passed"`);
  }
}

function requireTrue(actual, path) {
  if (actual !== true) {
    failures.push(`${path} must be true`);
  }
}

function requireCommand(actual, path) {
  if (typeof actual !== "string" || actual.trim().length < 3 || /REPLACE_WITH/.test(actual)) {
    failures.push(`${path} must name the exact command that produced the evidence`);
  }
}

function requireMatch(actual, pattern, message) {
  if (typeof actual !== "string" || !pattern.test(actual)) {
    failures.push(message);
  }
}

function requireIsoTimestamp(actual, path) {
  if (typeof actual !== "string" || Number.isNaN(Date.parse(actual))) {
    failures.push(`${path} must be an ISO timestamp`);
  }
}

function requireEmptyArray(actual, path) {
  if (!Array.isArray(actual) || actual.length !== 0) {
    failures.push(`${path} must be an empty array`);
  }
}

function requireNonEmptyStringArray(actual, path) {
  if (!Array.isArray(actual) || actual.length === 0 || actual.some((item) => typeof item !== "string" || item.trim() === "" || /REPLACE_WITH/.test(item))) {
    failures.push(`${path} must include at least one real artifact path`);
  }
}

function requirePositiveCoverage(passed, total, path) {
  if (!Number.isInteger(passed) || !Number.isInteger(total) || total <= 0 || passed !== total) {
    failures.push(`${path} must report all authorization cases passed`);
  }
}

function requireInfrastructure(actual, path) {
  const expected = {
    frontendBuild: "production",
    api: "real",
    postgresMigrations: "real",
    redis: "real",
    workersAndQueues: "real",
    objectStorage: "real-or-production-compatible",
    clerk: "development-instance",
    externalProviders: "deterministic-stand-ins",
  };
  if (!actual || typeof actual !== "object" || Array.isArray(actual)) {
    failures.push(`${path} must describe the production-build real-internal-infra components`);
    return;
  }
  for (const [key, value] of Object.entries(expected)) {
    requireValue(actual[key], `${path}.${key}`, value);
  }
}

function requireStringSet(actual, required, path) {
  if (!Array.isArray(actual)) {
    failures.push(`${path} must be an array`);
    return;
  }
  for (const item of required) {
    if (!actual.includes(item)) {
      failures.push(`${path} must include ${item}`);
    }
  }
}

function requireNamedItems(items, requiredNames, path) {
  if (!Array.isArray(items)) {
    failures.push(`${path} must be an array`);
    return;
  }
  const names = new Set(items.map((item) => item?.name ?? item?.id));
  for (const name of requiredNames) {
    if (!names.has(name)) {
      failures.push(`${path} must include ${name}`);
    }
  }
}

function requirePassedEvidenceItems(items, path) {
  if (!Array.isArray(items) || items.length === 0) {
    failures.push(`${path} must include at least one evidence item`);
    return;
  }
  for (const [index, item] of items.entries()) {
    if (!item || typeof item !== "object") {
      failures.push(`${path}[${index}] must be an object`);
      continue;
    }
    const itemName = item.name ?? item.id;
    if (typeof itemName !== "string" || itemName.trim() === "" || /REPLACE_WITH/.test(itemName)) {
      failures.push(`${path}[${index}] must name the checked item with name or id`);
    }
    requirePassed(item.status, `${path}[${index}].status`);
    if (typeof item.redactedEvidence !== "string" || item.redactedEvidence.trim() === "" || /REPLACE_WITH/.test(item.redactedEvidence)) {
      failures.push(`${path}[${index}].redactedEvidence must point to redacted evidence`);
    }
  }
}

function displayPath(path) {
  return relative(repoRoot, path).replaceAll("\\", "/");
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
