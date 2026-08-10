const wfPrimitivesAllowlist = [
  "client/src/components/graph/GraphInspectorPanel.tsx",
  "client/src/components/integrations/IntegrationConfigPanel.tsx",
  "client/src/components/integrations/IntegrationList.tsx",
  "client/src/components/ontology/PropertyEditor.tsx",
  "client/src/components/valuepack/ValuePackDetail.tsx",
  "client/src/components/workspace/AccountIntakeModal.tsx",
  "client/src/components/workspace/HypothesisShell.tsx",
  "client/src/components/workspace/IntelligenceShell.tsx",
  "client/src/components/workspace/RightRail.tsx",
  "client/src/pages/Accounts.tsx",
  "client/src/pages/AgentWorkflows.tsx",
  "client/src/pages/BusinessCase.tsx",
  "client/src/pages/BusinessCaseList.tsx",
  "client/src/pages/CommandCenter.tsx",
  "client/src/pages/DecisionTrace.tsx",
  "client/src/pages/EntityBrowser.tsx",
  "client/src/pages/EntityDetail.tsx",
  "client/src/pages/ExtractionEngine.tsx",
  "client/src/pages/FormulaBuilder.tsx",
  "client/src/pages/FormulaList.tsx",
  "client/src/pages/GovernanceAuditLog.tsx",
  "client/src/pages/GovernanceChangeHistory.tsx",
  "client/src/pages/GovernanceCompliance.tsx",
  "client/src/pages/GovernanceEvidence.tsx",
  "client/src/pages/GovernanceTraceView.tsx",
  "client/src/pages/GraphExplorer.tsx",
  "client/src/pages/IngestionJobs.tsx",
  "client/src/pages/Integrations.tsx",
  "client/src/pages/InteractiveBusinessCase.tsx",
  "client/src/pages/MyModels.tsx",
  "client/src/pages/OntologyEditor.tsx",
  "client/src/pages/OpportunityFinder.tsx",
  "client/src/pages/SourceConfiguration.tsx",
  "client/src/pages/ValueNarrativeHome.tsx",
  "client/src/pages/ValuePacks.tsx",
  "client/src/pages/ValueTreeExplorer.tsx",
  "client/src/pages/WhitespaceAnalysis.tsx",
  "client/src/pages/admin/BenchmarkPolicies.tsx",
  "client/src/pages/admin/HealthMonitor.tsx",
  "client/src/pages/admin/PermissionsAdmin.tsx",
  "client/src/pages/calculator/ROITab.tsx",
  "client/src/pages/calculator/ValueModelTab.tsx",
  "client/src/pages/deliverables/CFOView.tsx",
  "client/src/pages/deliverables/ExecutiveView.tsx",
  "client/src/pages/deliverables/TechnicalView.tsx",
  "client/src/pages/dev/IntegrationDashboard.tsx",
  "client/src/pages/hypothesis/AssumptionsTab.tsx",
  "client/src/pages/hypothesis/DiscoveryQuestionsTab.tsx",
  "client/src/pages/hypothesis/PersonaFitTab.tsx",
  "client/src/pages/intelligence/EnrichmentTab.tsx",
  "client/src/pages/intelligence/HypothesesTab.tsx",
  "client/src/pages/intelligence/OntologyMatchTab.tsx",
  "client/src/pages/intelligence/ROITab.tsx",
  "client/src/pages/realization/RealizationPage.tsx",
  "client/src/pages/studio/ActionPlanTab.tsx",
  "client/src/pages/studio/NarrativeTab.tsx",
  "client/src/pages/studio/ValueModelTab.tsx",
  "client/src/pages/value-case/ValueCasePage.tsx",
];

/**
 * ESLint Configuration for Frontend
 *
 * CONTRACT.md §3.3 - Lint and CI Enforcement Strategy
 * Enforces Fabric 4L canonical contracts through custom ESLint plugin
 */

module.exports = {
  root: true,
  extends: [
    // Standard TypeScript/React rules
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
    // Fabric 4L canonical contracts
    "plugin:fabric-contracts/service-frontend",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: "module",
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: [
    "@typescript-eslint",
    "react-refresh",
    "fabric-contracts",
  ],
  rules: {
    // React specific
    "react-refresh/only-export-components": [
      "warn",
      { allowConstantExport: true },
    ],

    // TypeScript
    "@typescript-eslint/no-explicit-any": "error", // Enforced — use specific types
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/no-deprecated": "error", // Enforced — no deprecated API usage

    // Logging — use createFeatureLogger from @/lib/telemetry instead
    "no-console": "error",

    // Fabric Contract overrides for frontend
    // Phase 2: Enforced - violations block CI (see CONTRACT.md §3.3)
    "fabric-contracts/no-raw-tenant-query": "error",
    "fabric-contracts/no-explicit-db-connect": "error",
    "fabric-contracts/no-inline-middleware": "error",
    "fabric-contracts/no-inline-tool-definition": "error",
    "fabric-contracts/no-json-parse-agent-output": "error",
    // Semantic agent contracts start in warning mode until runtime enforcement is promoted.
    "fabric-contracts/require-semantic-contract-metadata": "warn",
    // Phase 2: Already enforced
    "fabric-contracts/no-imperative-navigation": "error",
    "fabric-contracts/no-url-concatenation": "error",
    // P1-006: Block hardcoded real customer names outside of the canonical demoData module
    "no-restricted-syntax": [
      "error",
      {
        selector: "Literal[value=/Medtronic|Stryker|Baxter|Finastra|Goldman Sachs|Johnson & Johnson MedTech/]",
        message: "Hardcoded customer names are not allowed outside of src/lib/demoData.ts. Use generic placeholders or import from demoData.ts.",
      },
    ],
    "no-restricted-imports": [
      "error",
      {
        paths: [
          {
            name: "@/api/legacy",
            message: "Legacy API shim is banned. Use generated clients or '@/hooks/useWorkflows'.",
          },
        ],
        patterns: [
          {
            group: ["**/api/legacy", "**/api/legacy.ts"],
            message: "Legacy API shim is banned. Use '@/api/workflows', generated clients, or '@/hooks/useWorkflows'.",
          },
        ],
      },
    ],
  },
  overrides: [
    {
      files: wfPrimitivesAllowlist,
      rules: {
        "no-restricted-imports": "off",
      },
    },
    {
      // telemetry.ts IS the logging implementation — console calls are intentional here
      files: ["src/lib/telemetry.ts"],
      rules: {
        "no-console": "off",
      },
    },
    {
      // demoData.ts IS the canonical location for real customer demo data
      files: ["src/lib/demoData.ts"],
      rules: {
        "no-restricted-syntax": "off",
      },
    },
    {
      // E2E tests must not introduce explicit any; use a documented inline override only when unavoidable.
      files: ["e2e/**/*.ts"],
      rules: {
        "@typescript-eslint/no-explicit-any": ["error", { fixToUnknown: true, ignoreRestArgs: false }],
        "no-restricted-syntax": [
          "error",
          {
            selector: "TSAnyKeyword",
            message:
              "Explicit any is disallowed in E2E tests. Use concrete interfaces or unknown. If unavoidable, add a documented eslint-disable-next-line @typescript-eslint/no-explicit-any with a reason.",
          },
        ],
      },
    },
  ],
  ignorePatterns: [
    "dist/**",
    "node_modules/**",
    "**/*.d.ts",
    "**/*.config.ts",
    "**/*.config.js",
  ],
  settings: {
    react: {
      version: "detect",
    },
  },
};
