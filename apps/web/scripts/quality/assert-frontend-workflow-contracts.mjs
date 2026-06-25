#!/usr/bin/env node
/**
 * Validates executable frontend workflow business contracts.
 *
 * The coverage matrix says which workflows are release-significant. This guard
 * ensures each one has a contract that covers the four important planes:
 * UI, backend/persistence, security, and audit, plus explicit failure cases and
 * executable evidence files.
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, "..", "..");
const repoRoot = resolve(webRoot, "..", "..");
const contractsPath = resolve(webRoot, "docs", "frontend-workflow-contracts.json");
const matrixPath = resolve(webRoot, "docs", "frontend-workflow-coverage-matrix.md");

const requiredContractIds = [
  "J0-AUTH-SESSION",
  "J1-DOMAIN-INGESTION",
  "J2-INTELLIGENCE",
  "J3-VALUE-STUDIO",
  "J4-GOVERNANCE-TRUST",
  "J5-TIER-SECURITY",
  "P0-ACCOUNT-LIFECYCLE",
  "P0-CALC-EVIDENCE",
  "P0-APPROVAL-EXPORT",
  "P0-AGENT-GOVERNANCE",
  "P0-LAYER-VALIDATION",
  "P1-INTELLIGENCE",
  "P1-STUDIO",
  "P1-CONTEXT",
  "P1-STAKEHOLDERS",
  "P1-NARRATIVE-PROPOSAL",
  "P1-COLLABORATION",
  "P1-SEARCH-SECURITY",
  "P1-NOTIFICATIONS-TASKS",
  "P1-ADMIN-CONFIG",
  "P1-RESILIENCE",
  "P1-ADVERSARIAL",
  "P1-PERSONAS",
  "P1-SETTINGS",
  "P1-PERSONAL",
  "P1-INTEGRATIONS",
];

const requiredArrayFields = [
  "primaryRoutes",
  "actions",
  "expectedUi",
  "expectedBackend",
  "securityInvariants",
  "auditInvariants",
  "failureCases",
  "evidence",
];

const failures = [];
const matrix = readFileSync(matrixPath, "utf8");
const payload = JSON.parse(readFileSync(contractsPath, "utf8"));
const contracts = Array.isArray(payload.contracts) ? payload.contracts : [];
const byId = new Map();

if (payload.schemaVersion !== 1) {
  failures.push("schemaVersion must be 1");
}

for (const contract of contracts) {
  if (!contract.id) {
    failures.push("contract without id");
    continue;
  }
  if (byId.has(contract.id)) {
    failures.push(`${contract.id} is duplicated`);
  }
  byId.set(contract.id, contract);
}

for (const id of requiredContractIds) {
  const contract = byId.get(id);
  if (!contract) {
    failures.push(`${id} is missing from ${relative(webRoot, contractsPath)}`);
    continue;
  }

  if ((id.startsWith("P0-") || id.startsWith("P1-")) && !matrix.includes(id)) {
    failures.push(`${id} has a contract but is missing from the workflow coverage matrix`);
  }

  validateContract(contract);
}

for (const contract of contracts) {
  if (!requiredContractIds.includes(contract.id)) {
    validateContract(contract);
  }
}

if (!matrix.includes("frontend-workflow-contracts.json")) {
  failures.push("workflow matrix must reference docs/frontend-workflow-contracts.json");
}

if (failures.length > 0) {
  console.error(`Frontend workflow contracts are incomplete: ${relative(webRoot, contractsPath)}`);
  for (const failure of failures) {
    console.error(` - ${failure}`);
  }
  process.exit(1);
}

console.log(`Frontend workflow contracts passed: ${requiredContractIds.length} release-significant contracts validated.`);

function validateContract(contract) {
  for (const field of requiredArrayFields) {
    if (!Array.isArray(contract[field]) || contract[field].length === 0) {
      failures.push(`${contract.id} must define non-empty ${field}`);
    }
  }

  if (!["P0", "P1", "P2"].includes(contract.priority)) {
    failures.push(`${contract.id} must use priority P0, P1, or P2`);
  }

  for (const route of contract.primaryRoutes ?? []) {
    if (typeof route !== "string" || !route.startsWith("/")) {
      failures.push(`${contract.id} route ${JSON.stringify(route)} must start with /`);
    }
  }

  for (const evidence of contract.evidence ?? []) {
    if (typeof evidence !== "string" || evidence.trim() === "") {
      failures.push(`${contract.id} evidence entries must be non-empty strings`);
      continue;
    }
    const evidencePath = resolveEvidence(evidence);
    if (!existsSync(evidencePath)) {
      failures.push(`${contract.id} evidence file does not exist: ${evidence}`);
    }
  }

  assertPlane(contract, "expectedUi", ["render", "visible", "ui", "route", "state", "tab", "output", "affordance", "disabled", "error", "sign-in", "home"]);
  assertPlane(contract, "expectedBackend", ["persist", "api", "server", "backend", "contract", "scoped", "endpoint", "state", "records", "tool", "formula"]);
  assertPlane(contract, "securityInvariants", ["tenant", "unauthorized", "restricted", "cross", "foreign", "token", "role", "secret", "prompt", "access"]);
  assertPlane(contract, "auditInvariants", ["audit", "trace", "provenance", "actor", "record", "history", "request", "attributed"]);
}

function resolveEvidence(evidence) {
  if (evidence.startsWith("e2e/") || evidence.startsWith("src/") || evidence.startsWith("scripts/") || evidence.startsWith("docs/")) {
    return resolve(webRoot, evidence);
  }
  return resolve(repoRoot, evidence);
}

function assertPlane(contract, field, keywords) {
  const text = (contract[field] ?? []).join(" ").toLowerCase();
  if (!keywords.some((keyword) => text.includes(keyword))) {
    failures.push(`${contract.id} ${field} must include concrete ${field} proof, not a placeholder`);
  }
}
