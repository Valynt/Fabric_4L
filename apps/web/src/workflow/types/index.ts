/**
 * Workflow Type Definitions
 */

export interface ProspectInfo {
  companyId: string;
  companyName: string;
  contactName: string;
  contactTitle: string;
  industry?: string;
  revenue?: number;
  employees?: number;
}

export interface EnrichedEntity {
  id: string;
  name: string;
  type: string;
  confidence: number;
}

export interface WorkflowStep {
  path: string;
  canonicalPath: string;
  label: string;
  description: string;
  icon: string;
}

export const WORKFLOW_STEPS: WorkflowStep[] = [
  { path: '/workflow', canonicalPath: '/t/:tenantSlug/accounts', label: 'Prospect', description: 'Define target account', icon: 'Radar' },
  { path: '/workflow/intelligence', canonicalPath: '/t/:tenantSlug/accounts/:accountId/intelligence/signals', label: 'Intelligence', description: 'Research and enrich', icon: 'Building2' },
  { path: '/workflow/ai-model', canonicalPath: '/t/:tenantSlug/accounts/:accountId/intelligence/hypotheses', label: 'AI Model', description: 'Generate hypotheses', icon: 'BrainCircuit' },
  { path: '/workflow/driver-tree', canonicalPath: '/t/:tenantSlug/accounts/:accountId/studio/driver-tree', label: 'Driver Tree', description: 'Build structure', icon: 'GitFork' },
  { path: '/workflow/evidence', canonicalPath: '/t/:tenantSlug/accounts/:accountId/intelligence/evidence', label: 'Evidence', description: 'Match evidence', icon: 'Database' },
  { path: '/workflow/calculator', canonicalPath: '/t/:tenantSlug/accounts/:accountId/studio/calculator', label: 'Calculator', description: 'Model scenarios', icon: 'Calculator' },
  { path: '/workflow/value-case', canonicalPath: '/t/:tenantSlug/accounts/:accountId/studio/value-case', label: 'Value Case', description: 'Generate case', icon: 'FileText' },
];
