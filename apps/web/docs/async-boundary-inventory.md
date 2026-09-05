# Async Boundary Inventory

Generated: 2026-09-05T06:18:06.597Z

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
- L148 [async-boundary] `async function evaluateWhatIf`

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
- L27 [async-boundary] `async function fetchEffectivePermissions`

## src/app/settings/pages/BillingWorkspace.tsx
- L31 [async-boundary] `const handleSave = async (`

## src/auth/AuthorizationProvider.tsx
- L120 [async-boundary] `queryFn: async (`
- L218 [async-boundary] `queryFn: async (`
- L149 [fire-and-forget-no-catch] `void query.refetch();`

## src/auth/clerkSession.ts
- L62 [async-boundary] `async function getClerkSessionToken`

## src/components/billing/InvoiceDetailDrawer.tsx
- L51 [async-boundary] `const handleDownloadPDF = async (`

## src/components/ErrorBoundary.tsx
- L33 [async-boundary] `const handleCopy = async (`

## src/components/skill-outputs/SkillJobLauncher.tsx
- L59 [async-boundary] `async function handleSubmit`

## src/components/workspace/AccountIntakeModal.tsx
- L170 [async-boundary] `const handleSubmit = async (`

## src/components/workspace/ProspectPromptBuilder.tsx
- L726 [async-boundary] `const handleAttach = async (`
- L1118 [fire-and-forget-no-catch] `void handleFormSubmit();`

## src/contexts/AuthContext.tsx
- L62 [async-boundary] `const initiateLogin = async (`
- L66 [async-boundary] `const handleCallback = async (`
- L71 [async-boundary] `const logout = async (`
- L80 [async-boundary] `const refreshToken = async (`

## src/features/value-case/api/valueCaseApi.ts
- L18 [async-boundary] `async function fetchValueCasesApi`
- L36 [async-boundary] `async function createValueCaseApi`
- L56 [async-boundary] `async function updateValueCaseApi`
- L77 [async-boundary] `async function publishValueCaseApi`
- L97 [async-boundary] `async function fetchAccountApi`

## src/features/value-case/components/ValueCaseWorkspace.tsx
- L114 [async-boundary] `const handleConfirmGenerate = async (`

## src/features/value-case/queries/useValueCaseJourney.ts
- L107 [async-boundary] `queryFn: async (`
- L122 [async-boundary] `queryFn: async (`
- L232 [async-boundary] `mutationFn: async (`
- L317 [async-boundary] `mutationFn: async (`
- L349 [async-boundary] `mutationFn: async (`
- L309 [fire-and-forget-no-catch] `void queryClient.invalidateQueries({
        queryKey: valueCaseKeys.scope(submissionScope),
        exact: true,
      });`
- L341 [fire-and-forget-no-catch] `void queryClient.invalidateQueries({
        queryKey: valueCaseKeys.scope(submissionScope),
        exact: true,
      });`
- L372 [fire-and-forget-no-catch] `void queryClient.invalidateQueries({
        queryKey: valueCaseKeys.scope(submissionScope),
        exact: true,
      });`
- L507 [fire-and-forget-no-catch] `void accountQuery.refetch();`
- L508 [fire-and-forget-no-catch] `void versionsQuery.refetch();`

## src/hooks/useAcademy.ts
- L120 [async-boundary] `async function fetchPillars`
- L125 [async-boundary] `async function fetchQuiz`
- L130 [async-boundary] `async function submitQuizPayload`
- L138 [async-boundary] `async function fetchProgress`
- L143 [async-boundary] `async function updateProgressPayload`
- L152 [async-boundary] `async function fetchCertifications`
- L157 [async-boundary] `async function fetchMaturityLevels`
- L162 [async-boundary] `async function fetchMaturityAssessments`
- L167 [async-boundary] `async function createMaturityAssessmentPayload`
- L175 [async-boundary] `async function fetchResources`
- L196 [async-boundary] `queryFn: async (`

## src/hooks/useAccounts.ts
- L139 [async-boundary] `async function fetchAccounts`
- L190 [async-boundary] `async function resolveBackendAccountId`
- L238 [async-boundary] `async function fetchAccount`
- L247 [async-boundary] `queryFn: async (`
- L258 [async-boundary] `async function fetchAccountActivity`
- L281 [async-boundary] `queryFn: async (`
- L292 [async-boundary] `async function fetchSyncStatus`
- L307 [async-boundary] `async function fetchFilterOptions`
- L400 [async-boundary] `mutationFn: async (`
- L418 [async-boundary] `mutationFn: async (`
- L440 [async-boundary] `mutationFn: async (`

## src/hooks/useApiShared.ts
- L83 [async-boundary] `async function withApiError`

## src/hooks/useBenchmarks.ts
- L82 [async-boundary] `async function fetchBenchmarks`
- L109 [async-boundary] `async function fetchBenchmark`
- L123 [async-boundary] `queryFn: async (`
- L134 [async-boundary] `async function fetchBenchmarkPolicies`
- L168 [async-boundary] `mutationFn: async (`

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
- L74 [async-boundary] `mutationFn: async (`
- L100 [async-boundary] `queryFn: async (`
- L113 [async-boundary] `mutationFn: async (`

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

## src/hooks/useEvidence.ts
- L161 [async-boundary] `async function fetchCaseStudies`
- L171 [async-boundary] `async function fetchCaseStudy`
- L176 [async-boundary] `async function fetchIndustryStats`
- L181 [async-boundary] `async function fetchProductStats`
- L201 [async-boundary] `queryFn: async (`
- L265 [async-boundary] `mutationFn: async (`
- L374 [async-boundary] `queryFn: async (`

## src/hooks/useExtractionResults.ts
- L76 [async-boundary] `queryFn: async (`
- L107 [async-boundary] `queryFn: async (`

## src/hooks/useFormulaDependents.ts
- L34 [async-boundary] `async function fetchFormulaDependencies`
- L62 [async-boundary] `queryFn: async (`
- L103 [async-boundary] `queryFn: async (`

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

## src/hooks/useFormulaScenario.ts
- L79 [async-boundary] `mutationFn: async (`

## src/hooks/useFormulaVersions.ts
- L45 [async-boundary] `async function fetchFormulaVersions`
- L53 [async-boundary] `async function fetchFormulaGovernance`
- L79 [async-boundary] `queryFn: async (`
- L105 [async-boundary] `queryFn: async (`

## src/hooks/useGates.ts
- L54 [async-boundary] `queryFn: async (`
- L67 [async-boundary] `queryFn: async (`
- L80 [async-boundary] `mutationFn: async (`
- L101 [async-boundary] `mutationFn: async (`
- L115 [async-boundary] `mutationFn: async (`

## src/hooks/useGovernance.ts
- L69 [async-boundary] `async function fetchTenants`
- L74 [async-boundary] `async function fetchUsers`
- L79 [async-boundary] `async function fetchApiKeys`
- L120 [async-boundary] `mutationFn: async (`
- L144 [async-boundary] `mutationFn: async (`
- L164 [async-boundary] `mutationFn: async (`
- L178 [async-boundary] `mutationFn: async (`

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
- L197 [async-boundary] `queryFn: async (`
- L231 [async-boundary] `queryFn: async (`
- L261 [async-boundary] `mutationFn: async (`
- L305 [async-boundary] `queryFn: async (`
- L345 [async-boundary] `queryFn: async (`
- L417 [async-boundary] `queryFn: async (`
- L442 [async-boundary] `mutationFn: async (`
- L460 [async-boundary] `mutationFn: async (`
- L503 [async-boundary] `mutationFn: async (`

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

## src/hooks/useModels.ts
- L103 [async-boundary] `async function fetchModels`
- L124 [async-boundary] `async function fetchFolders`
- L158 [async-boundary] `mutationFn: async (`
- L190 [async-boundary] `mutationFn: async (`

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
- L170 [async-boundary] `queryFn: async (`
- L183 [async-boundary] `mutationFn: async (`
- L219 [async-boundary] `mutationFn: async (`
- L255 [async-boundary] `mutationFn: async (`
- L278 [async-boundary] `mutationFn: async (`
- L323 [async-boundary] `mutationFn: async (`
- L355 [async-boundary] `mutationFn: async (`
- L391 [async-boundary] `mutationFn: async (`
- L413 [async-boundary] `mutationFn: async (`
- L450 [async-boundary] `mutationFn: async (`
- L492 [async-boundary] `mutationFn: async (`

## src/hooks/useOperationalAudit.ts
- L68 [async-boundary] `async function fetchOperationalAudit`

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

## src/hooks/useResolvedTenant.ts
- L96 [async-boundary] `queryFn: async (`

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
- L383 [async-boundary] `queryFn: async (`
- L420 [async-boundary] `queryFn: async (`
- L443 [async-boundary] `queryFn: async (`
- L464 [async-boundary] `mutationFn: async (`
- L490 [async-boundary] `mutationFn: async (`
- L537 [async-boundary] `mutationFn: async (`
- L557 [async-boundary] `mutationFn: async (`
- L585 [async-boundary] `mutationFn: async (`

## src/hooks/useTargets.ts
- L273 [async-boundary] `queryFn: async (`
- L309 [async-boundary] `queryFn: async (`
- L327 [async-boundary] `queryFn: async (`
- L343 [async-boundary] `queryFn: async (`
- L382 [async-boundary] `mutationFn: async (`
- L403 [async-boundary] `mutationFn: async (`
- L426 [async-boundary] `mutationFn: async (`
- L448 [async-boundary] `mutationFn: async (`
- L475 [async-boundary] `mutationFn: async (`
- L519 [async-boundary] `mutationFn: async (`
- L565 [async-boundary] `mutationFn: async (`

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
- L136 [async-boundary] `queryFn: async (`
- L156 [async-boundary] `mutationFn: async (`
- L206 [async-boundary] `mutationFn: async (`
- L232 [async-boundary] `mutationFn: async (`

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
- L39 [async-boundary] `queryFn: async (`
- L72 [async-boundary] `queryFn: async (`
- L93 [async-boundary] `mutationFn: async (`
- L124 [async-boundary] `mutationFn: async (`
- L142 [async-boundary] `mutationFn: async (`
- L177 [async-boundary] `mutationFn: async (`
- L211 [async-boundary] `mutationFn: async (`
- L261 [async-boundary] `mutationFn: async (`
- L315 [async-boundary] `async function getOrCreateCanonicalCaseId`
- L344 [async-boundary] `async function persistWorkspaceTab`

## src/lib/clipboard.ts
- L7 [async-boundary] `async function copyToClipboard`

## src/pages/AcceptInvite.tsx
- L24 [async-boundary] `async function handleSubmit`

## src/pages/admin/PermissionsAdmin.tsx
- L169 [async-boundary] `const handleInvite = async (`
- L183 [async-boundary] `const handleCreateKey = async (`
- L210 [async-boundary] `const handleRevokeConfirm = async (`

## src/pages/calculator/ROITab.tsx
- L98 [async-boundary] `queryFn: async (`
- L107 [async-boundary] `mutationFn: async (`
- L129 [async-boundary] `mutationFn: async (`

## src/pages/ClerkSignIn.tsx
- L132 [async-boundary] `async function handleEmailSignIn`
- L163 [async-boundary] `async function handleOAuthSignIn`
- L359 [async-boundary] `useEffect(() => {`
- L387 [async-boundary] `useEffect(() => {`

## src/pages/CollaborationCommentsPage.tsx
- L29 [async-boundary] `const handleSubmit = async (`

## src/pages/DecisionTrace.tsx
- L81 [async-boundary] `const handleExportProvO = async (`

## src/pages/ExtractionEngine.tsx
- L113 [async-boundary] `const handleRunExtraction = async (`
- L132 [async-boundary] `const handlePauseAll = async (`

## src/pages/NotificationsPage.tsx
- L24 [async-boundary] `const handleSubmit = async (`
- L143 [async-boundary] `onClick={async (`

## src/pages/OntologyEditor.tsx
- L440 [async-boundary] `onClick={async (`

## src/pages/TargetsAdmin.detail.tsx
- L64 [async-boundary] `const handleRun = async (`

## src/pages/TargetsAdmin.form.tsx
- L162 [async-boundary] `const onSubmit = async (`

## src/pages/TasksPage.tsx
- L29 [async-boundary] `const handleSubmit = async (`
- L129 [async-boundary] `onClick={async (`

## src/pages/ValueNarrativeHome.tsx
- L214 [async-boundary] `const handleLaunch = async (`

## src/pages/ValueTreeExplorer.tsx
- L303 [async-boundary] `const handleCreateTree = async (`
- L330 [async-boundary] `const handleImportFile = async (`

## src/test/utils/withAuthProvider.ts
- L28 [async-boundary] `async function withAuthProvider`

