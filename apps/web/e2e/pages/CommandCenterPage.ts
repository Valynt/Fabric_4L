import { Page, Locator, expect } from '@playwright/test';

/**
 * Page Object for Command Center screen (Home dashboard)
 *
 * Route: /home
 * Tier: standard (all tiers)
 *
 * Encapsulates all interactions with the ingestion command center,
 * providing a stable API for tests that survives UI refactoring.
 */
export class CommandCenterPage {
  readonly page: Page;

  // Main page elements
  readonly header: Locator;
  readonly domainInput: Locator;
  readonly synthesizeButton: Locator;
  readonly advancedToggle: Locator;

  // KPI cards
  readonly totalDomainsCard: Locator;
  readonly pagesSynthesizedCard: Locator;
  readonly sourcesAnalyzedCard: Locator;
  readonly avgProcessingTimeCard: Locator;

  // Jobs table
  readonly jobsTable: Locator;
  readonly jobsLoadingState: Locator;
  readonly noJobsMessage: Locator;

  // Advanced config
  readonly profileSelect: Locator;
  readonly ontologySelect: Locator;
  readonly depthSelect: Locator;

  constructor(page: Page) {
    this.page = page;

    // Header
    this.header = page.getByRole('heading', { name: /command center/i });

    // Main input area
    this.domainInput = page.getByPlaceholder(/enter company domain/i);
    this.synthesizeButton = page.getByRole('button', { name: /synthesis|synthesize/i });
    this.advancedToggle = page.getByRole('button', { name: /advanced configuration/i });

    // KPI cards - using semantic selectors
    this.totalDomainsCard = page.locator('[data-testid="kpi-total-domains"]').or(
      page.getByText(/total domains/i).locator('..')
    );
    this.pagesSynthesizedCard = page.locator('[data-testid="kpi-pages-synthesized"]').or(
      page.getByText(/pages synthesized/i).locator('..')
    );
    this.sourcesAnalyzedCard = page.locator('[data-testid="kpi-sources-analyzed"]').or(
      page.getByText(/sources analyzed/i).locator('..')
    );
    this.avgProcessingTimeCard = page.locator('[data-testid="kpi-avg-processing"]').or(
      page.getByText(/avg. processing/i).locator('..')
    );

    // Jobs table
    this.jobsTable = page.locator('[data-testid="recent-jobs-table"]').or(
      page.locator('table').filter({ has: page.getByText(/domain/i) })
    );
    this.jobsLoadingState = page.getByText(/loading/i);
    this.noJobsMessage = page.getByText(/no recent jobs/i);

    // Advanced config (hidden by default)
    this.profileSelect = page.locator('select').filter({ has: page.locator('option[value="Default"]') });
    this.ontologySelect = page.locator('select').filter({ has: page.locator('option:has-text("SaaS")') });
    this.depthSelect = page.locator('select').filter({ has: page.locator('option[value="3"]') });
  }

  /**
   * Navigate to Command Center (Home)
   */
  async goto(): Promise<void> {
    await this.page.goto('/home');
    await this.waitForPageLoad();
  }

  /**
   * Wait for page to be fully loaded
   */
  async waitForPageLoad(): Promise<void> {
    await expect(this.header).toBeVisible();
    await expect(this.domainInput).toBeVisible();
  }

  /**
   * Enter domain for synthesis
   */
  async enterDomain(domain: string): Promise<void> {
    await this.domainInput.fill(domain);
  }

  /**
   * Click synthesize button
   */
  async clickSynthesize(): Promise<void> {
    await this.synthesizeButton.click();
  }

  /**
   * Submit domain for synthesis (combined action)
   */
  async submitDomain(domain: string): Promise<void> {
    await this.enterDomain(domain);
    await this.clickSynthesize();
  }

  /**
   * Toggle advanced configuration panel
   */
  async toggleAdvancedConfig(): Promise<void> {
    await this.advancedToggle.click();
  }

  /**
   * Set extraction profile
   */
  async setProfile(profile: string): Promise<void> {
    await this.profileSelect.selectOption(profile);
  }

  /**
   * Set ontology target
   */
  async setOntology(ontology: string): Promise<void> {
    await this.ontologySelect.selectOption(ontology);
  }

  /**
   * Wait for KPI data to load
   */
  async waitForKPIData(): Promise<void> {
    await expect(this.totalDomainsCard).not.toContainText('—');
    await expect(this.pagesSynthesizedCard).not.toContainText('—');
  }

  /**
   * Get KPI value by label
   */
  async getKPIValue(label: string): Promise<string> {
    const card = this.page.locator('[data-testid^="kpi-"]').filter({ hasText: label });
    const valueLocator = card.locator('.text-2xl, [data-testid="kpi-value"]').first();
    return valueLocator.textContent() || '';
  }

  /**
   * Check if jobs table has data
   */
  async hasJobsData(): Promise<boolean> {
    const rows = this.jobsTable.locator('tbody tr');
    return (await rows.count()) > 0;
  }

  /**
   * Wait for jobs to load
   */
  async waitForJobs(): Promise<void> {
    await expect(this.jobsLoadingState).toBeHidden();
    await expect(this.jobsTable.or(this.noJobsMessage)).toBeVisible();
  }

  /**
   * Get recent job count
   */
  async getJobCount(): Promise<number> {
    const rows = this.jobsTable.locator('tbody tr');
    return rows.count();
  }

  /**
   * Assert page is in expected initial state
   */
  async assertInitialState(): Promise<void> {
    await expect(this.header).toBeVisible();
    await expect(this.domainInput).toBeVisible();
    await expect(this.synthesizeButton).toBeDisabled();
    await expect(this.synthesizeButton).toContainText(/synthesize/i);
  }

  /**
   * Assert synthesize button is enabled when input has value
   */
  async assertSynthesizeEnabledWithInput(): Promise<void> {
    await this.enterDomain('https://example.com');
    await expect(this.synthesizeButton).toBeEnabled();
  }
}
