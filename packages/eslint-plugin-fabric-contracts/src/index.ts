/**
 * ESLint Plugin for Fabric 4L Canonical Contracts
 *
 * CONTRACT.md §3.3 - Lint and CI Enforcement Strategy
 *
 * This plugin enforces the six canonical contracts through 12 custom ESLint rules:
 * 1. Tenant Isolation Boundary
 * 2. Database Session Boundary
 * 3. Tool Invocation Boundary
 * 4. LLM Output Handling
 * 5. UI State Management
 * 6. Public API Surface
 *
 * @packageDocumentation
 */

import { Linter, Rule } from "eslint";

// Type for the plugin export
type ESLintPlugin = {
  meta: { name: string; version: string };
  rules: Record<string, Rule.RuleModule>;
  configs: Record<string, Linter.BaseConfig>;
};

// Import all rules
import noTenantIdParameter from "./rules/no-tenant-id-parameter";
import noReqTenantAccess from "./rules/no-req-tenant-access";
import noRawTenantQuery from "./rules/no-raw-tenant-query";
import noExplicitDbConnect from "./rules/no-explicit-db-connect";
import noInlineMiddleware from "./rules/no-inline-middleware";
import noInlineToolDefinition from "./rules/no-inline-tool-definition";
import noThrowInTool from "./rules/no-throw-in-tool";
import noJsonParseAgentOutput from "./rules/no-json-parse-agent-output";
import requireSemanticContractMetadata from "./rules/require-semantic-contract-metadata";
import noImperativeNavigation from "./rules/no-imperative-navigation";
import noUrlConcatenation from "./rules/no-url-concatenation";
import noPrivateImports from "./rules/no-private-imports";
import noCircularDependencies from "./rules/no-circular-dependencies";

// Map of rule names to rule implementations
const rules: Record<string, Rule.RuleModule> = {
  "no-tenant-id-parameter": noTenantIdParameter,
  "no-req-tenant-access": noReqTenantAccess,
  "no-raw-tenant-query": noRawTenantQuery,
  "no-explicit-db-connect": noExplicitDbConnect,
  "no-inline-middleware": noInlineMiddleware,
  "no-inline-tool-definition": noInlineToolDefinition,
  "no-throw-in-tool": noThrowInTool,
  "no-json-parse-agent-output": noJsonParseAgentOutput,
  "require-semantic-contract-metadata": requireSemanticContractMetadata,
  "no-imperative-navigation": noImperativeNavigation,
  "no-url-concatenation": noUrlConcatenation,
  "no-private-imports": noPrivateImports,
  "no-circular-dependencies": noCircularDependencies,
};

// Recommended configuration
const recommended: Linter.BaseConfig = {
  plugins: ["fabric-contracts"],
  rules: {
    // Tenant Isolation Boundary (§2.1)
    "fabric-contracts/no-tenant-id-parameter": "error",
    "fabric-contracts/no-req-tenant-access": "error",
    "fabric-contracts/no-raw-tenant-query": "error",

    // Database Session Boundary (§2.2)
    "fabric-contracts/no-explicit-db-connect": "error",

    // Tool Invocation Boundary (§2.4)
    "fabric-contracts/no-inline-middleware": "error",
    "fabric-contracts/no-inline-tool-definition": "error",
    "fabric-contracts/no-throw-in-tool": "error",

    // LLM Output Handling (§2.5)
    "fabric-contracts/no-json-parse-agent-output": "error",

    // Semantic Agent Contracts (Phase 2)
    "fabric-contracts/require-semantic-contract-metadata": "warn",

    // UI State Management (§2.6)
    "fabric-contracts/no-imperative-navigation": "error",
    "fabric-contracts/no-url-concatenation": "error",

    // Public API Surface (§2.7)
    "fabric-contracts/no-private-imports": "error",
    "fabric-contracts/no-circular-dependencies": "error",
  },
};

// Plugin export
const plugin: ESLintPlugin = {
  meta: {
    name: "eslint-plugin-fabric-contracts",
    version: "1.0.0",
  },
  rules,
  configs: {
    recommended,
    // Per-service configurations can be added here
    "service-backend": {
      ...recommended,
      rules: {
        ...recommended.rules,
        // Backend-specific rule adjustments
        "fabric-contracts/no-imperative-navigation": "off",
        "fabric-contracts/no-url-concatenation": "off",
      },
    },
    "service-frontend": {
      ...recommended,
      rules: {
        ...recommended.rules,
        // Frontend-specific rule adjustments
        "fabric-contracts/no-raw-tenant-query": "off",
        "fabric-contracts/no-explicit-db-connect": "off",
      },
    },
  },
};

// CommonJS export for ESLint compatibility
export = plugin;
