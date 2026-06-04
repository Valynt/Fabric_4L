# Async Boundary Inventory

Generated: 2026-06-04T17:48:50.600Z

## src/api/auth.ts
- L26 [async-boundary] `async function registerWithEmailPassword`

## src/api/billing.ts
- L11 [async-boundary] `async function getEntitlementDecision`

## src/api/packs.ts
- L74 [async-boundary] `async function listValuePackSummaries`
- L83 [async-boundary] `async function getValuePackDetail`
- L88 [async-boundary] `async function applyValuePack`

## src/api/protocol/extraction.ts
- L72 [async-boundary] `async function fetchExtractionStatus`
- L88 [async-boundary] `async function fetchExtractedEntities`

## src/api/search.ts
- L21 [async-boundary] `async function search`

## src/api/thesysClient.ts
- L170 [async-boundary] `async function evaluateWhatIf`

## src/api/typedClient.ts
- L13 [async-boundary] `async function apiGet`
- L23 [async-boundary] `async function apiPost`
- L34 [async-boundary] `async function apiPut`
- L45 [async-boundary] `async function apiPatch`
- L56 [async-boundary] `async function apiDelete`

## src/api/valuePackFramework.ts
- L280 [async-boundary] `async function listFrameworkValuePacks`
- L295 [async-boundary] `async function getFrameworkValuePack`
- L301 [async-boundary] `async function getOntologyMap`
- L332 [async-boundary] `async function getTemplateLibrary`
- L348 [async-boundary] `async function compareFrameworkValuePacks`

## src/api/valueTrees.ts
- L85 [async-boundary] `async function getValueTree`
- L118 [async-boundary] `async function getValueTreePaths`
- L144 [async-boundary] `async function createValueTree`
- L153 [async-boundary] `async function importValueTree`

## src/app/settings/access.ts
- L47 [async-boundary] `async function fetchEffectivePermissions`

## src/app/settings/pages/BillingWorkspace.tsx
- L30 [async-boundary] `const handleSave = async (`

## src/auth/clerkSession.ts
- L62 [async-boundary] `async function getClerkSessionToken`

## src/components/ErrorBoundary.tsx
- L33 [async-boundary] `const handleCopy = async (`

## src/components/ExportMenu.tsx
- L16 [async-boundary] `const handleExport = async (`

## src/components/billing/InvoiceDetailDrawer.tsx
- L47 [async-boundary] `const handleDownloadPDF = async (`

## src/components/login-form.tsx
- L146 [async-boundary] `const handleSubmit = async (`
- L375 [async-boundary] `const handleSubmit = async (`

## src/components/skill-outputs/SkillJobLauncher.tsx
- L59 [async-boundary] `async function handleSubmit`

## src/components/workspace/AccountIntakeModal.tsx
- L170 [async-boundary] `const handleSubmit = async (`

## src/components/workspace/ProspectPromptBuilder.tsx
- L1286 [async-boundary] `const handleAttach = async (`

## src/contexts/AuthContext.tsx
- L120 [async-boundary] `const initiateLogin = async (`
- L126 [async-boundary] `const handleCallback = async (`
- L131 [async-boundary] `const logout = async (`
- L147 [async-boundary] `const refreshToken = async (`

## src/features/intelligence-workspace/hooks/useWorkspaceTabQuery.ts
- L25 [async-boundary] `queryFn: async (`

## src/hooks/useAccountAccess.ts
- L17 [async-boundary] `queryFn: async (`

## src/hooks/useAccounts.ts
- L133 [async-boundary] `async function fetchAccounts`
- L181 [async-boundary] `async function resolveBackendAccountId`
- L214 [async-boundary] `async function fetchAccount`
- L223 [async-boundary] `queryFn: async (`
- L234 [async-boundary] `async function fetchAccountActivity`
- L257 [async-boundary] `queryFn: async (`
- L268 [async-boundary] `async function fetchSyncStatus`
- L283 [async-boundary] `async function fetchFilterOptions`
- L376 [async-boundary] `mutationFn: async (`
- L394 [async-boundary] `mutationFn: async (`
- L416 [async-boundary] `mutationFn: async (`

## src/hooks/useApiShared.ts
- L156 [async-boundary] `async function withApiError`

## src/hooks/useBenchmarks.ts
- L87 [async-boundary] `async function fetchBenchmarks`
- L114 [async-boundary] `async function fetchBenchmark`
- L128 [async-boundary] `queryFn: async (`
- L139 [async-boundary] `async function fetchBenchmarkPolicies`
- L173 [async-boundary] `mutationFn: async (`

## src/hooks/useBilling.ts
- L59 [async-boundary] `queryFn: async (`
- L68 [async-boundary] `mutationFn: async (`
- L90 [async-boundary] `mutationFn: async (`
- L106 [async-boundary] `const openCustomerPortal = async (`
- L115 [async-boundary] `const subscribe = async (`
- L157 [async-boundary] `queryFn: async (`
- L169 [async-boundary] `queryFn: async (`

## src/hooks/useBusinessCases.ts
- L76 [async-boundary] `queryFn: async (`
- L133 [async-boundary] `async function fetchBusinessCases`
- L222 [async-boundary] `mutationFn: async (`
- L263 [async-boundary] `mutationFn: async (`

## src/hooks/useCalculators.ts
- L108 [async-boundary] `async function fetchValueLevers`
- L118 [async-boundary] `async function createValueCase`
- L125 [async-boundary] `async function fetchValueCase`
- L130 [async-boundary] `async function updateValueCase`
- L157 [async-boundary] `queryFn: async (`

## src/hooks/useComments.ts
- L50 [async-boundary] `queryFn: async (`
- L60 [async-boundary] `mutationFn: async (`

## src/hooks/useCompetitiveIntel.ts
- L132 [async-boundary] `async function fetchCompetitors`
- L142 [async-boundary] `async function fetchCompetitor`
- L150 [async-boundary] `async function fetchBattlecards`
- L158 [async-boundary] `async function fetchBattlecard`
- L169 [async-boundary] `async function fetchWinLossSummary`
- L177 [async-boundary] `async function fetchLandscape`
- L203 [async-boundary] `queryFn: async (`
- L217 [async-boundary] `queryFn: async (`
- L238 [async-boundary] `queryFn: async (`
- L305 [async-boundary] `mutationFn: async (`
- L342 [async-boundary] `mutationFn: async (`

## src/hooks/useComplianceStatus.ts
- L39 [async-boundary] `async function fetchComplianceStatus`

## src/hooks/useDocuments.ts
- L76 [async-boundary] `mutationFn: async (`
- L105 [async-boundary] `mutationFn: async (`
- L131 [async-boundary] `queryFn: async (`
- L143 [async-boundary] `mutationFn: async (`

## src/hooks/useEnrichment.ts
- L93 [async-boundary] `async function fetchEnrichmentStatus`
- L98 [async-boundary] `async function fetchEnrichmentDetails`
- L118 [async-boundary] `queryFn: async (`
- L134 [async-boundary] `mutationFn: async (`
- L150 [async-boundary] `mutationFn: async (`

## src/hooks/useEntities.ts
- L192 [async-boundary] `queryFn: async (`
- L241 [async-boundary] `queryFn: async (`
- L275 [async-boundary] `queryFn: async (`
- L304 [async-boundary] `queryFn: async (`
- L333 [async-boundary] `mutationFn: async (`

## src/hooks/useEntitlements.ts
- L25 [async-boundary] `queryFn: async (`

## src/hooks/useEvidence.ts
- L162 [async-boundary] `async function fetchCaseStudies`
- L172 [async-boundary] `async function fetchCaseStudy`
- L177 [async-boundary] `async function fetchIndustryStats`
- L182 [async-boundary] `async function fetchProductStats`
- L202 [async-boundary] `queryFn: async (`
- L266 [async-boundary] `mutationFn: async (`
- L421 [async-boundary] `queryFn: async (`

## src/hooks/useExtraction.ts
- L76 [async-boundary] `queryFn: async (`

## src/hooks/useExtractionResults.ts
- L76 [async-boundary] `queryFn: async (`
- L106 [async-boundary] `queryFn: async (`

## src/hooks/useFabricQuery.ts
- L53 [async-boundary] `queryFn: async (`

## src/hooks/useFormulaDependents.ts
- L34 [async-boundary] `async function fetchFormulaDependencies`
- L62 [async-boundary] `queryFn: async (`
- L103 [async-boundary] `queryFn: async (`

## src/hooks/useFormulaScenario.ts
- L79 [async-boundary] `mutationFn: async (`

## src/hooks/useFormulaVersions.ts
- L45 [async-boundary] `async function fetchFormulaVersions`
- L53 [async-boundary] `async function fetchFormulaGovernance`
- L79 [async-boundary] `queryFn: async (`
- L105 [async-boundary] `queryFn: async (`

## src/hooks/useFormulas.ts
- L38 [async-boundary] `async function fetchFormulas`
- L75 [async-boundary] `async function fetchFormula`
- L96 [async-boundary] `queryFn: async (`
- L107 [async-boundary] `async function fetchFormulaApprovals`
- L143 [async-boundary] `mutationFn: async (`
- L168 [async-boundary] `mutationFn: async (`
- L202 [async-boundary] `mutationFn: async (`
- L275 [async-boundary] `mutationFn: async (`
- L338 [async-boundary] `mutationFn: async (`
- L369 [async-boundary] `mutationFn: async (`

## src/hooks/useGates.ts
- L54 [async-boundary] `queryFn: async (`
- L67 [async-boundary] `queryFn: async (`
- L80 [async-boundary] `mutationFn: async (`
- L101 [async-boundary] `mutationFn: async (`
- L115 [async-boundary] `mutationFn: async (`

## src/hooks/useGovernance.ts
- L54 [async-boundary] `async function fetchTenants`
- L59 [async-boundary] `async function fetchUsers`
- L64 [async-boundary] `async function fetchApiKeys`
- L105 [async-boundary] `mutationFn: async (`
- L119 [async-boundary] `mutationFn: async (`

## src/hooks/useGraphQuery.ts
- L90 [async-boundary] `mutationFn: async (`
- L134 [async-boundary] `queryFn: async (`
- L167 [async-boundary] `mutationFn: async (`
- L222 [async-boundary] `queryFn: async (`

## src/hooks/useGroundTruthGovernance.ts
- L67 [async-boundary] `async function fetchTruths`
- L77 [async-boundary] `async function fetchTruthAuditTrail`
- L87 [async-boundary] `async function fetchFreshnessSummary`
- L95 [async-boundary] `async function fetchStaleTruths`
- L105 [async-boundary] `async function fetchMaturityLadder`
- L132 [async-boundary] `queryFn: async (`

## src/hooks/useHealthMonitor.ts
- L33 [async-boundary] `async function fetchSystemHealth`
- L38 [async-boundary] `async function fetchHealthAlerts`

## src/hooks/useHypotheses.ts
- L156 [async-boundary] `async function fetchHypothesis`
- L161 [async-boundary] `async function fetchAccountHypotheses`
- L173 [async-boundary] `async function fetchHypothesisStats`
- L183 [async-boundary] `queryFn: async (`
- L197 [async-boundary] `queryFn: async (`
- L223 [async-boundary] `mutationFn: async (`
- L245 [async-boundary] `mutationFn: async (`
- L266 [async-boundary] `mutationFn: async (`
- L282 [async-boundary] `mutationFn: async (`
- L297 [async-boundary] `mutationFn: async (`
- L307 [async-boundary] `mutationFn: async (`
- L338 [async-boundary] `mutationFn: async (`

## src/hooks/useIngestion.ts
- L173 [async-boundary] `queryFn: async (`
- L185 [async-boundary] `queryFn: async (`
- L217 [async-boundary] `queryFn: async (`
- L247 [async-boundary] `mutationFn: async (`
- L291 [async-boundary] `queryFn: async (`
- L331 [async-boundary] `queryFn: async (`
- L403 [async-boundary] `queryFn: async (`
- L428 [async-boundary] `mutationFn: async (`
- L446 [async-boundary] `mutationFn: async (`
- L489 [async-boundary] `mutationFn: async (`

## src/hooks/useIntegrations.ts
- L66 [async-boundary] `async function fetchIntegrations`
- L81 [async-boundary] `async function fetchIntegration`
- L89 [async-boundary] `queryFn: async (`
- L108 [async-boundary] `mutationFn: async (`

## src/hooks/useIntelligence.ts
- L124 [async-boundary] `async function fetchAccountBriefing`
- L129 [async-boundary] `async function fetchDealReadiness`
- L134 [async-boundary] `async function fetchPipelineSummary`
- L144 [async-boundary] `queryFn: async (`
- L158 [async-boundary] `queryFn: async (`

## src/hooks/useInvoices.ts
- L98 [async-boundary] `queryFn: async (`
- L116 [async-boundary] `queryFn: async (`
- L137 [async-boundary] `queryFn: async (`

## src/hooks/useL5Governance.ts
- L45 [async-boundary] `async function fetchJson`

## src/hooks/useModels.ts
- L103 [async-boundary] `async function fetchModels`
- L124 [async-boundary] `async function fetchFolders`
- L158 [async-boundary] `mutationFn: async (`
- L190 [async-boundary] `mutationFn: async (`

## src/hooks/useNarrativeGeneration.ts
- L62 [async-boundary] `queryFn: async (`
- L81 [async-boundary] `mutationFn: async (`

## src/hooks/useNarratives.ts
- L89 [async-boundary] `async function fetchNarratives`
- L94 [async-boundary] `async function fetchNarrative`
- L114 [async-boundary] `queryFn: async (`
- L130 [async-boundary] `mutationFn: async (`
- L148 [async-boundary] `mutationFn: async (`
- L162 [async-boundary] `mutationFn: async (`

## src/hooks/useNotifications.ts
- L53 [async-boundary] `queryFn: async (`
- L63 [async-boundary] `mutationFn: async (`
- L79 [async-boundary] `mutationFn: async (`

## src/hooks/useOntology.ts
- L171 [async-boundary] `queryFn: async (`
- L186 [async-boundary] `queryFn: async (`
- L221 [async-boundary] `mutationFn: async (`
- L257 [async-boundary] `mutationFn: async (`
- L293 [async-boundary] `mutationFn: async (`
- L316 [async-boundary] `mutationFn: async (`
- L361 [async-boundary] `mutationFn: async (`
- L407 [async-boundary] `mutationFn: async (`
- L439 [async-boundary] `mutationFn: async (`
- L475 [async-boundary] `mutationFn: async (`
- L497 [async-boundary] `mutationFn: async (`
- L534 [async-boundary] `mutationFn: async (`
- L576 [async-boundary] `mutationFn: async (`

## src/hooks/useOperationalAudit.ts
- L68 [async-boundary] `async function fetchOperationalAudit`

## src/hooks/useOpportunities.ts
- L59 [async-boundary] `async function fetchOpportunities`

## src/hooks/usePauseAllExtractions.ts
- L15 [async-boundary] `mutationFn: async (`

## src/hooks/usePlatformSettings.ts
- L176 [async-boundary] `async function fetchPlatformSettings`
- L181 [async-boundary] `async function updatePlatformSettings`

## src/hooks/useProducts.ts
- L105 [async-boundary] `async function fetchProducts`
- L110 [async-boundary] `async function fetchProduct`
- L115 [async-boundary] `async function fetchSignalMatching`
- L123 [async-boundary] `async function fetchPortfolioSummary`
- L128 [async-boundary] `async function fetchCapabilityCoverage`
- L148 [async-boundary] `queryFn: async (`
- L194 [async-boundary] `mutationFn: async (`
- L207 [async-boundary] `mutationFn: async (`
- L221 [async-boundary] `mutationFn: async (`
- L233 [async-boundary] `mutationFn: async (`
- L247 [async-boundary] `mutationFn: async (`
- L259 [async-boundary] `mutationFn: async (`
- L273 [async-boundary] `mutationFn: async (`

## src/hooks/useProvenance.ts
- L40 [async-boundary] `queryFn: async (`
- L61 [async-boundary] `queryFn: async (`
- L85 [async-boundary] `mutationFn: async (`

## src/hooks/useROICalculator.ts
- L161 [async-boundary] `async function fetchTemplates`
- L166 [async-boundary] `async function fetchCalculations`
- L171 [async-boundary] `async function fetchCalculation`
- L176 [async-boundary] `async function fetchBenchmarks`
- L181 [async-boundary] `async function fetchBenchmarksList`
- L186 [async-boundary] `async function fetchBenchmarkDetail`
- L221 [async-boundary] `queryFn: async (`
- L235 [async-boundary] `queryFn: async (`
- L260 [async-boundary] `queryFn: async (`
- L276 [async-boundary] `mutationFn: async (`
- L288 [async-boundary] `mutationFn: async (`
- L298 [async-boundary] `mutationFn: async (`
- L311 [async-boundary] `mutationFn: async (`

## src/hooks/useROIScenarios.ts
- L64 [async-boundary] `queryFn: async (`
- L79 [async-boundary] `mutationFn: async (`
- L100 [async-boundary] `mutationFn: async (`

## src/hooks/useRunExtraction.ts
- L56 [async-boundary] `mutationFn: async (`

## src/hooks/useSkillJobs.ts
- L151 [async-boundary] `mutationFn: async (`
- L174 [async-boundary] `mutationFn: async (`
- L210 [async-boundary] `queryFn: async (`
- L230 [async-boundary] `queryFn: async (`
- L264 [async-boundary] `queryFn: async (`
- L284 [async-boundary] `queryFn: async (`
- L310 [async-boundary] `queryFn: async (`

## src/hooks/useSources.ts
- L390 [async-boundary] `queryFn: async (`
- L427 [async-boundary] `queryFn: async (`
- L450 [async-boundary] `queryFn: async (`
- L481 [async-boundary] `mutationFn: async (`
- L507 [async-boundary] `mutationFn: async (`
- L554 [async-boundary] `mutationFn: async (`
- L574 [async-boundary] `mutationFn: async (`
- L602 [async-boundary] `mutationFn: async (`

## src/hooks/useSuperAdminOverview.ts
- L33 [async-boundary] `async function fetchTenantOverview`

## src/hooks/useTargets.ts
- L280 [async-boundary] `queryFn: async (`
- L316 [async-boundary] `queryFn: async (`
- L334 [async-boundary] `queryFn: async (`
- L358 [async-boundary] `queryFn: async (`
- L397 [async-boundary] `mutationFn: async (`
- L418 [async-boundary] `mutationFn: async (`
- L441 [async-boundary] `mutationFn: async (`
- L463 [async-boundary] `mutationFn: async (`
- L490 [async-boundary] `mutationFn: async (`
- L534 [async-boundary] `mutationFn: async (`
- L580 [async-boundary] `mutationFn: async (`

## src/hooks/useTasks.ts
- L60 [async-boundary] `queryFn: async (`
- L70 [async-boundary] `mutationFn: async (`
- L86 [async-boundary] `mutationFn: async (`

## src/hooks/useUsage.ts
- L70 [async-boundary] `queryFn: async (`
- L89 [async-boundary] `queryFn: async (`
- L108 [async-boundary] `queryFn: async (`
- L128 [async-boundary] `mutationFn: async (`

## src/hooks/useValueCaseArtifacts.ts
- L58 [async-boundary] `queryFn: async (`
- L73 [async-boundary] `mutationFn: async (`

## src/hooks/useValuePacks.ts
- L55 [async-boundary] `async function fetchValuePacks`
- L93 [async-boundary] `async function fetchValuePack`
- L140 [async-boundary] `mutationFn: async (`
- L193 [async-boundary] `async function fetchValuePackFrameworkList`
- L212 [async-boundary] `async function fetchValuePackFramework`

## src/hooks/useValueTrees.ts
- L72 [async-boundary] `queryFn: async (`
- L109 [async-boundary] `queryFn: async (`

## src/hooks/useVariables.ts
- L94 [async-boundary] `async function fetchVariables`
- L122 [async-boundary] `async function fetchVariable`
- L137 [async-boundary] `queryFn: async (`
- L148 [async-boundary] `async function fetchVariableStats`
- L170 [async-boundary] `async function fetchSourceBindings`
- L196 [async-boundary] `mutationFn: async (`
- L212 [async-boundary] `mutationFn: async (`

## src/hooks/useVersioning.ts
- L38 [async-boundary] `queryFn: async (`
- L51 [async-boundary] `mutationFn: async (`
- L69 [async-boundary] `mutationFn: async (`

## src/hooks/useWorkflows.ts
- L251 [async-boundary] `queryFn: async (`
- L277 [async-boundary] `queryFn: async (`
- L299 [async-boundary] `mutationFn: async (`
- L340 [async-boundary] `mutationFn: async (`
- L450 [async-boundary] `mutationFn: async (`
- L471 [async-boundary] `mutationFn: async (`
- L492 [async-boundary] `queryFn: async (`
- L511 [async-boundary] `queryFn: async (`

## src/hooks/useWorkspaceCase.ts
- L24 [async-boundary] `queryFn: async (`
- L57 [async-boundary] `queryFn: async (`
- L77 [async-boundary] `mutationFn: async (`
- L104 [async-boundary] `mutationFn: async (`
- L121 [async-boundary] `mutationFn: async (`
- L151 [async-boundary] `mutationFn: async (`
- L185 [async-boundary] `mutationFn: async (`
- L219 [async-boundary] `mutationFn: async (`
- L262 [async-boundary] `mutationFn: async (`
- L316 [async-boundary] `async function getOrCreateCanonicalCaseId`
- L345 [async-boundary] `async function persistWorkspaceTab`

## src/pages/CollaborationCommentsPage.tsx
- L28 [async-boundary] `const handleSubmit = async (`

## src/pages/DecisionTrace.tsx
- L66 [async-boundary] `const handleExportProvO = async (`

## src/pages/ExtractionEngine.tsx
- L112 [async-boundary] `const handleRunExtraction = async (`
- L131 [async-boundary] `const handlePauseAll = async (`

## src/pages/NotificationsPage.tsx
- L23 [async-boundary] `const handleSubmit = async (`
- L141 [async-boundary] `onClick={async (`

## src/pages/OntologyEditor.tsx
- L436 [async-boundary] `onClick={async (`

## src/pages/TargetsAdmin.detail.tsx
- L64 [async-boundary] `const handleRun = async (`

## src/pages/TargetsAdmin.form.tsx
- L162 [async-boundary] `const onSubmit = async (`

## src/pages/TasksPage.tsx
- L29 [async-boundary] `const handleSubmit = async (`
- L128 [async-boundary] `onClick={async (`

## src/pages/ValueTreeExplorer.tsx
- L299 [async-boundary] `const handleCreateTree = async (`
- L326 [async-boundary] `const handleImportFile = async (`

## src/pages/admin/FormulaGovernance.tsx
- L260 [async-boundary] `const handleApprovalAction = async (`

## src/pages/admin/PermissionsAdmin.tsx
- L140 [async-boundary] `const handleInvite = async (`

## src/pages/admin/PlatformSettings.tsx
- L465 [async-boundary] `const handleUpdate = async (`

## src/pages/admin/VariableRegistry.tsx
- L243 [async-boundary] `const handleTestBinding = async (`

## src/pages/calculator/ROITab.tsx
- L102 [async-boundary] `queryFn: async (`
- L111 [async-boundary] `mutationFn: async (`
- L133 [async-boundary] `mutationFn: async (`

## src/pages/intelligence/EvidenceTab.tsx
- L150 [async-boundary] `onClick={async (`
- L156 [async-boundary] `onClick={async (`
- L162 [async-boundary] `onClick={async (`

## src/pages/intelligence/SignalsTab.tsx
- L159 [async-boundary] `const handleReview = async (`
- L169 [async-boundary] `const handlePromote = async (`

## src/test/utils/withAuthProvider.ts
- L28 [async-boundary] `async function withAuthProvider`

