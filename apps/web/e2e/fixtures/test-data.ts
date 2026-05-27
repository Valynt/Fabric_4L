/**
 * Test data factories for Playwright tests
 *
 * Provides deterministic, realistic test data that mirrors
 * production data structures without coupling to implementation.
 */

import { faker } from '@faker-js/faker';

// Use a fixed seed for deterministic test data
faker.seed(12345);

export interface TestDomain {
  url: string;
  name: string;
}

export interface TestIngestionJob {
  id: string;
  domain: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
}

export interface TestGraphNode {
  id: string;
  name: string;
  entityType: 'Capability' | 'UseCase' | 'Persona' | 'ValueDriver';
  description: string;
}

/**
 * Generate a realistic test domain for ingestion tests
 */
export function createTestDomain(overrides?: Partial<TestDomain>): TestDomain {
  const companyName = faker.company.name();
  return {
    url: `https://${faker.internet.domainName()}`,
    name: companyName,
    ...overrides,
  };
}

/**
 * Generate test ingestion job data
 */
export function createTestIngestionJob(
  status: TestIngestionJob['status'] = 'completed',
  overrides?: Partial<TestIngestionJob>
): TestIngestionJob {
  const domain = createTestDomain();
  return {
    id: faker.string.uuid(),
    domain: domain.url,
    status,
    progress: status === 'completed' ? 100 : status === 'failed' ? 0 : faker.number.int({ min: 10, max: 90 }),
    ...overrides,
  };
}

/**
 * Generate test graph node data
 */
export function createTestGraphNode(
  entityType: TestGraphNode['entityType'] = 'Capability',
  overrides?: Partial<TestGraphNode>
): TestGraphNode {
  const typeNames: Record<TestGraphNode['entityType'], string> = {
    Capability: faker.company.buzzPhrase(),
    UseCase: `${faker.commerce.productName()} ${faker.word.verb()}ing`,
    Persona: faker.person.jobTitle(),
    ValueDriver: `${faker.number.int({ min: 10, max: 50 })}% ${faker.commerce.productAdjective()} improvement`,
  };

  return {
    id: faker.string.uuid(),
    name: typeNames[entityType],
    entityType,
    description: faker.lorem.sentence(),
    ...overrides,
  };
}

/**
 * Generate multiple test entities
 */
export function createTestGraphNodes(count: number = 5): TestGraphNode[] {
  const types: TestGraphNode['entityType'][] = ['Capability', 'UseCase', 'Persona', 'ValueDriver'];
  return Array.from({ length: count }, (_, i) =>
    createTestGraphNode(types[i % types.length])
  );
}

/**
 * Known test domains that are safe to use in tests
 * (These should be replaced with mock server responses in full E2E)
 */
export const SAFE_TEST_DOMAINS = [
  { url: 'https://example.com', name: 'Example Corp' },
  { url: 'https://testcompany.io', name: 'Test Company' },
  { url: 'https://acme.dev', name: 'Acme Development' },
] as const;

/**
 * Tier configuration for access control tests — canonical navigation taxonomy
 */
export const TIER_CONFIG = {
  standard: {
    canAccess: ['/home', '/library/packs', '/discover/accounts', '/deliver/cases', '/evidence/traces'],
    cannotAccess: ['/discover/extraction', '/discover/knowledge/graph', '/admin/content/formulas'],
  },
  advanced: {
    canAccess: ['/home', '/library/packs', '/discover/extraction', '/discover/knowledge/graph', '/model/value-studio/explorer'],
    cannotAccess: ['/admin/content/formulas'],
  },
  admin: {
    canAccess: ['/home', '/library/packs', '/discover/extraction', '/discover/knowledge/graph', '/model/value-studio/explorer', '/admin/content/formulas'],
    cannotAccess: [],
  },
} as const;

/**
 * Billing and entitlement test data
 */
export interface TestBillingData {
  plan: 'starter' | 'professional' | 'enterprise';
  status: 'active' | 'past_due' | 'cancelled' | 'trial';
  usage: {
    api_calls: number;
    storage_gb: number;
    users: number;
  };
  limits: {
    max_api_calls: number;
    max_storage_gb: number;
    max_users: number;
  };
  invoices: Array<{
    id: string;
    amount: number;
    status: 'paid' | 'pending' | 'failed';
    date: string;
  }>;
  webhooks: Array<{
    id: string;
    url: string;
    events: string[];
    status: 'active' | 'failed';
    last_delivery: string | null;
  }>;
}

/**
 * Generate test billing data
 */
export function createTestBillingData(
  plan: TestBillingData['plan'] = 'enterprise',
  overrides?: Partial<TestBillingData>
): TestBillingData {
  const limits = {
    starter: { max_api_calls: 10000, max_storage_gb: 10, max_users: 5 },
    professional: { max_api_calls: 100000, max_storage_gb: 100, max_users: 25 },
    enterprise: { max_api_calls: 1000000, max_storage_gb: 1000, max_users: 100 },
  };

  return {
    plan,
    status: 'active',
    usage: {
      api_calls: faker.number.int({ min: 1000, max: limits[plan].max_api_calls * 0.8 }),
      storage_gb: faker.number.int({ min: 1, max: limits[plan].max_storage_gb * 0.8 }),
      users: faker.number.int({ min: 1, max: limits[plan].max_users * 0.8 }),
    },
    limits: limits[plan],
    invoices: Array.from({ length: 3 }, () => ({
      id: faker.string.uuid(),
      amount: faker.number.int({ min: 100, max: 10000 }),
      status: faker.helpers.arrayElement(['paid', 'pending', 'failed']),
      date: faker.date.recent({ days: 90 }).toISOString(),
    })),
    webhooks: [
      {
        id: faker.string.uuid(),
        url: 'https://hooks.slack.com/services/TEST/WEBHOOK/URL',
        events: ['invoice.paid', 'subscription.updated'],
        status: 'active',
        last_delivery: faker.date.recent({ days: 1 }).toISOString(),
      },
    ],
    ...overrides,
  };
}

/**
 * Pre-configured billing scenarios for testing
 */
export const BILLING_SCENARIOS = {
  enterprise_active: createTestBillingData('enterprise', { status: 'active' }),
  professional_past_due: createTestBillingData('professional', { status: 'past_due' }),
  starter_trial: createTestBillingData('starter', { status: 'trial' }),
  enterprise_over_limit: createTestBillingData('enterprise', {
    usage: { api_calls: 2000000, storage_gb: 2000, users: 150 },
  }),
} as const;
