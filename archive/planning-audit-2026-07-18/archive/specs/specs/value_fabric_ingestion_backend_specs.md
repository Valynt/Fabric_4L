# Value Fabric SaaS Platform: Intelligent Data Ingestion Backend Specifications

## Document Overview
This specification document provides implementation-ready backend logic for the Intelligent Data Ingestion and Web Scraping layer of the Value Fabric platform. It covers data models, API endpoints, pipeline stages, integration patterns, and compliance mechanisms.

---

## 1. DATA MODELS AND SCHEMAS

### 1.1 Core Entity Relationship Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Organization   │────▶│  ScrapingTarget  │────▶│  ScrapingJob    │
│   (Tenant)      │     │  (Configuration) │     │  (Execution)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │                          │
                              ▼                          ▼
                       ┌──────────────┐          ┌─────────────────┐
                       │TargetMetadata│          │  JobExecution   │
                       │  (Schema)    │          │   (Stages)      │
                       └──────────────┘          └─────────────────┘
                                                         │
                    ┌────────────────────────────────────┼────────────────────────────────────┐
                    ▼                                    ▼                                    ▼
           ┌─────────────────┐                 ┌─────────────────┐                 ┌─────────────────┐
           │  RawContent     │                 │ ExtractedData   │                 │ ComplianceLog   │
           │  (Storage Ref)  │                 │  (Structured)   │                 │  (Audit Trail)  │
           └─────────────────┘                 └─────────────────┘                 └─────────────────┘
```

### 1.2 ScrapingTarget Schema

```typescript
interface ScrapingTarget {
  // Primary Identifiers
  id: UUID;
  organizationId: UUID;
  name: string;
  description?: string;
  
  // Target Configuration
  url: string;
  urlPattern?: string;           // Regex for URL matching (for dynamic targets)
  targetType: 'SINGLE_PAGE' | 'PAGINATED' | 'SPIDER' | 'API_ENDPOINT';
  
  // Extraction Configuration
  extractionConfig: {
    method: 'AI_LLM' | 'DETERMINISTIC' | 'HYBRID';
    llmProvider?: 'openai' | 'anthropic' | 'azure_openai';
    extractionSchema: JSONSchema;  // Expected output structure
    visualHints?: boolean;         // Use computer vision for layout understanding
    maxDepth?: number;             // For spider mode
    followLinks?: boolean;
    linkSelectors?: string[];
  };
  
  // Browser Configuration
  browserConfig: {
    engine: 'chromium' | 'firefox' | 'webkit';
    headless: boolean;
    viewport: { width: number; height: number };
    userAgent?: string;
    javascriptEnabled: boolean;
    waitForSelector?: string;
    waitTimeout: number;           // milliseconds
    stealthMode: boolean;          // Anti-detection techniques
  };
  
  // Scheduling
  schedule?: {
    enabled: boolean;
    cronExpression: string;
    timezone: string;
    maxConcurrentJobs: number;
  };
  
  // Rate Limiting
  rateLimit: {
    requestsPerSecond: number;
    requestsPerMinute: number;
    requestsPerHour: number;
    burstLimit: number;
    retryAttempts: number;
    retryBackoff: 'fixed' | 'exponential';
    retryDelayMs: number;
  };
  
  // Compliance Settings
  compliance: {
    respectRobotsTxt: boolean;
    userAgentString: string;
    crawlDelaySeconds: number;
    domainAllowlist: string[];
    domainBlocklist: string[];
    piiRedactionEnabled: boolean;
    sensitiveFieldPatterns: string[];
  };
  
  // Proxy Configuration
  proxyConfig: {
    enabled: boolean;
    rotationStrategy: 'ROUND_ROBIN' | 'RANDOM' | 'GEO_BASED' | 'SESSION_BASED';
    proxyPoolId?: UUID;
    stickySessions: boolean;
    sessionDurationMinutes?: number;
  };
  
  // Authentication (for non-public data - discouraged)
  authentication?: {
    type: 'NONE' | 'BEARER' | 'API_KEY' | 'BASIC' | 'OAUTH2';
    credentialsRef: string;        // Reference to secrets manager
  };
  
  // Metadata
  status: 'ACTIVE' | 'PAUSED' | 'ARCHIVED' | 'ERROR';
  createdAt: Timestamp;
  updatedAt: Timestamp;
  createdBy: UUID;
  lastSuccessAt?: Timestamp;
  lastErrorAt?: Timestamp;
  successCount: number;
  errorCount: number;
  averageExecutionTimeMs: number;
  tags: string[];
}
```

### 1.3 ScrapingJob Schema

```typescript
interface ScrapingJob {
  // Primary Identifiers
  id: UUID;
  organizationId: UUID;
  targetId: UUID;
  
  // Job Configuration (snapshot of target config at job creation)
  configuration: ScrapingTargetConfigurationSnapshot;
  
  // Execution State
  status: JobStatus;
  priority: number;                // 1-10, higher = more urgent
  
  // Timing
  scheduledAt?: Timestamp;
  startedAt?: Timestamp;
  completedAt?: Timestamp;
  estimatedDurationMs?: number;
  
  // Progress Tracking
  progress: {
    totalPages?: number;
    processedPages: number;
    failedPages: number;
    currentUrl?: string;
    stage: PipelineStage;
    percentComplete: number;
  };
  
  // Results Summary
  results: {
    rawContentCount: number;
    extractedRecordCount: number;
    storageBytesUsed: number;
    outputLocation: string;
  };
  
  // Error Tracking
  errors: JobError[];
  
  // Resource Usage
  resources: {
    browserSessionsUsed: number;
    proxyRequestsMade: number;
    llmTokensConsumed: number;
    computeTimeMs: number;
  };
  
  // Audit
  createdAt: Timestamp;
  createdBy: UUID;
  triggeredBy: 'SCHEDULE' | 'MANUAL' | 'API' | 'WEBHOOK' | 'WORKFLOW';
  correlationId: string;           // For distributed tracing
}

enum JobStatus {
  PENDING = 'PENDING',
  QUEUED = 'QUEUED',
  VALIDATING = 'VALIDATING',      // robots.txt, compliance checks
  BROWSER_ACQUIRING = 'BROWSER_ACQUIRING',
  NAVIGATING = 'NAVIGATING',
  EXTRACTING = 'EXTRACTING',
  TRANSFORMING = 'TRANSFORMING',
  STORING = 'STORING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED',
  PARTIAL_SUCCESS = 'PARTIAL_SUCCESS'
}

enum PipelineStage {
  INIT = 'INIT',
  COMPLIANCE_CHECK = 'COMPLIANCE_CHECK',
  BROWSER_LAUNCH = 'BROWSER_LAUNCH',
  NAVIGATION = 'NAVIGATION',
  CONTENT_CAPTURE = 'CONTENT_CAPTURE',
  AI_EXTRACTION = 'AI_EXTRACTION',
  POST_PROCESSING = 'POST_PROCESSING',
  VALIDATION = 'VALIDATION',
  STORAGE = 'STORAGE',
  NOTIFICATION = 'NOTIFICATION'
}

interface JobError {
  id: UUID;
  stage: PipelineStage;
  errorCode: string;
  errorMessage: string;
  stackTrace?: string;
  url?: string;
  retryable: boolean;
  retryCount: number;
  occurredAt: Timestamp;
  resolvedAt?: Timestamp;
  resolution?: string;
}
```

### 1.4 RawContent Schema

```typescript
interface RawContent {
  // Primary Identifiers
  id: UUID;
  jobId: UUID;
  organizationId: UUID;
  targetId: UUID;
  
  // Source Information
  source: {
    url: string;
    finalUrl?: string;             // After redirects
    domain: string;
    ipAddress?: string;
    accessedAt: Timestamp;
    httpStatus: number;
    headers: Record<string, string>;
    contentType: string;
    contentLength: number;
  };
  
  // Content Storage (references to blob storage)
  storage: {
    htmlPath?: string;             // S3/GCS path to raw HTML
    screenshotPath?: string;       // Full page screenshot
    domSnapshotPath?: string;      // Serialized DOM
    harPath?: string;              // HTTP Archive format
    textContentPath?: string;      // Extracted text
  };
  
  // Content Metadata
  metadata: {
    title?: string;
    description?: string;
    language?: string;
    charset?: string;
    viewport?: string;
    canonicalUrl?: string;
    robotsMeta?: string;
    ogTags: Record<string, string>;
    structuredData: any[];         // JSON-LD, microdata
  };
  
  // Capture Information
  capture: {
    method: 'STATIC' | 'DYNAMIC' | 'HYBRID';
    browserVersion?: string;
    renderingEngine?: string;
    javascriptExecuted: boolean;
    waitTimeMs: number;
    scrollDepth?: number;
    interactions?: string[];       // Clicks, hovers performed
  };
  
  // Content Hash for deduplication
  contentHash: string;             // SHA-256 of normalized content
  isDuplicate: boolean;
  duplicateOf?: UUID;
  
  // Processing Status
  processingStatus: 'PENDING' | 'EXTRACTING' | 'EXTRACTED' | 'FAILED';
  extractedDataId?: UUID;
  
  // Retention
  retentionPolicy: {
    rawContentExpiryDays: number;
    screenshotExpiryDays: number;
  };
  
  createdAt: Timestamp;
}
```

### 1.5 ExtractedData Schema

```typescript
interface ExtractedData {
  // Primary Identifiers
  id: UUID;
  jobId: UUID;
  rawContentId: UUID;
  organizationId: UUID;
  targetId: UUID;
  
  // Extraction Method
  extraction: {
    method: 'AI_LLM' | 'DETERMINISTIC' | 'HYBRID';
    llmModel?: string;
    promptVersion?: string;
    extractionTimeMs: number;
    confidenceScore: number;       // 0.0 - 1.0
    schemaVersion: string;
  };
  
  // Structured Output
  data: {
    // Schema-defined fields based on target extractionSchema
    [key: string]: any;
  };
  
  // Validation Results
  validation: {
    schemaValid: boolean;
    validationErrors?: string[];
    requiredFieldsPresent: string[];
    requiredFieldsMissing: string[];
    dataQualityScore: number;
  };
  
  // Source References
  provenance: {
    rawContentId: UUID;
    sourceUrl: string;
    extractedAt: Timestamp;
    extractionVersion: string;
  };
  
  // Post-Processing
  postProcessing: {
    piiRedactionApplied: boolean;
    redactedFields: string[];
    normalizedFields: string[];
    enrichedFields: string[];
  };
  
  // Ontology Mapping
  ontologyMapping?: {
    conceptIds: string[];
    relationshipIds: string[];
    mappedAt?: Timestamp;
    mappingConfidence: number;
  };
  
  // Storage
  storagePath: string;
  format: 'JSON' | 'JSONL' | 'PARQUET' | 'MARKDOWN';
  sizeBytes: number;
  
  createdAt: Timestamp;
  updatedAt: Timestamp;
}
```

### 1.6 ComplianceLog Schema

```typescript
interface ComplianceLog {
  // Primary Identifiers
  id: UUID;
  organizationId: UUID;
  jobId?: UUID;
  targetId?: UUID;
  
  // Compliance Event
  eventType: ComplianceEventType;
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  
  // robots.txt Compliance
  robotsTxtCheck?: {
    url: string;
    robotsTxtUrl: string;
    userAgent: string;
    allowed: boolean;
    crawlDelay?: number;
    sitemapUrls?: string[];
    rules: {
      path: string;
      allowed: boolean;
      lineNumber: number;
    }[];
  };
  
  // Rate Limiting
  rateLimitEvent?: {
    domain: string;
    requestsInWindow: number;
    limit: number;
    windowSeconds: number;
    actionTaken: 'DELAYED' | 'THROTTLED' | 'BLOCKED';
    delayMs?: number;
  };
  
  // PII Detection
  piiDetection?: {
    detectionMethod: 'REGEX' | 'ML_MODEL' | 'LLM';
    patternsDetected: {
      patternType: string;
      count: number;
      locations: string[];
    }[];
    redactionApplied: boolean;
    redactedCount: number;
  };
  
  // Domain Policy
  domainPolicy?: {
    domain: string;
    action: 'ALLOWED' | 'BLOCKED' | 'REQUIRES_REVIEW';
    policyType: 'ALLOWLIST' | 'BLOCKLIST' | 'DEFAULT';
    reason?: string;
  };
  
  // Request Details
  request: {
    url: string;
    timestamp: Timestamp;
    ipAddress?: string;
    proxyUsed?: string;
    userAgent: string;
    headers: Record<string, string>;
  };
  
  // Response
  response?: {
    statusCode?: number;
    actionTaken: string;
    reason: string;
  };
  
  // Audit Trail
  createdAt: Timestamp;
  metadata: Record<string, any>;
}

enum ComplianceEventType {
  ROBOTS_TXT_CHECK = 'ROBOTS_TXT_CHECK',
  RATE_LIMIT_APPLIED = 'RATE_LIMIT_APPLIED',
  PII_DETECTED = 'PII_DETECTED',
  PII_REDACTED = 'PII_REDACTED',
  DOMAIN_BLOCKED = 'DOMAIN_BLOCKED',
  DOMAIN_ALLOWED = 'DOMAIN_ALLOWED',
  CAPTCHA_ENCOUNTERED = 'CAPTCHA_ENCOUNTERED',
  BLOCKED_BY_TARGET = 'BLOCKED_BY_TARGET',
  TERMS_VIOLATION = 'TERMS_VIOLATION',
  DATA_RETENTION_DELETION = 'DATA_RETENTION_DELETION'
}
```

### 1.7 ProxyPool Schema

```typescript
interface ProxyPool {
  id: UUID;
  organizationId: UUID;
  name: string;
  
  proxies: {
    id: UUID;
    host: string;
    port: number;
    protocol: 'http' | 'https' | 'socks5';
    username?: string;
    passwordRef: string;           // Secrets manager reference
    country?: string;
    region?: string;
    city?: string;
    isp?: string;
    type: 'RESIDENTIAL' | 'DATACENTER' | 'MOBILE';
    status: 'ACTIVE' | 'FAILED' | 'QUARANTINED';
    failureCount: number;
    lastUsedAt?: Timestamp;
    lastSuccessAt?: Timestamp;
    averageResponseTimeMs: number;
  }[];
  
  rotationConfig: {
    strategy: 'ROUND_ROBIN' | 'LEAST_USED' | 'GEO_TARGETED' | 'RANDOM';
    maxFailuresBeforeQuarantine: number;
    quarantineDurationMinutes: number;
    healthCheckIntervalMinutes: number;
  };
}
```

---

## 2. API ENDPOINTS

### 2.1 REST API Specification

#### Base URL: `/api/v1/ingestion`

---

### ScrapingTarget Endpoints

#### `GET /targets`
List all scraping targets for the organization.

**Query Parameters:**
```typescript
{
  page?: number;           // default: 1
  limit?: number;          // default: 20, max: 100
  status?: JobStatus;
  search?: string;         // Search in name, description, url
  tags?: string[];
  sortBy?: 'createdAt' | 'updatedAt' | 'lastSuccessAt' | 'name';
  sortOrder?: 'asc' | 'desc';
}
```

**Response:**
```typescript
{
  data: ScrapingTargetSummary[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}
```

---

#### `POST /targets`
Create a new scraping target.

**Request Body:**
```typescript
{
  name: string;
  description?: string;
  url: string;
  targetType: 'SINGLE_PAGE' | 'PAGINATED' | 'SPIDER' | 'API_ENDPOINT';
  extractionConfig: {
    method: 'AI_LLM' | 'DETERMINISTIC' | 'HYBRID';
    llmProvider?: 'openai' | 'anthropic' | 'azure_openai';
    extractionSchema: JSONSchema;
    visualHints?: boolean;
    maxDepth?: number;
    followLinks?: boolean;
  };
  browserConfig?: BrowserConfigInput;
  schedule?: ScheduleInput;
  rateLimit?: RateLimitInput;
  compliance?: ComplianceInput;
  proxyConfig?: ProxyConfigInput;
  tags?: string[];
}
```

**Response:** `201 Created`
```typescript
{
  id: UUID;
  status: 'ACTIVE';
  createdAt: Timestamp;
  // ... full ScrapingTarget object
}
```

**Validation Rules:**
- URL must be valid and use http/https protocol
- extractionSchema must be valid JSON Schema
- If method is 'AI_LLM', llmProvider is required
- maxDepth cannot exceed 10 for spider targets
- cronExpression must be valid if schedule is enabled

---

#### `GET /targets/:id`
Get detailed information about a specific target.

**Response:** `200 OK`
```typescript
ScrapingTarget & {
  recentJobs: JobSummary[];
  successRate: number;
  averageExecutionTimeMs: number;
}
```

---

#### `PUT /targets/:id`
Update a scraping target.

**Request Body:** Partial<ScrapingTargetInput>

**Business Rules:**
- Cannot modify URL if jobs are in progress
- Changes to schedule require next run recalculation
- Versioning: previous config archived

**Response:** `200 OK` - Updated ScrapingTarget

---

#### `DELETE /targets/:id`
Archive a scraping target (soft delete).

**Query Parameters:**
```typescript
{
  force?: boolean;  // Hard delete if no jobs exist
}
```

**Response:** `204 No Content` or `409 Conflict` if jobs exist

---

#### `POST /targets/:id/validate`
Validate target configuration without executing.

**Request Body:**
```typescript
{
  testUrl?: string;  // Override URL for testing
  validateRobotsTxt: boolean;
  validateSchema: boolean;
  testBrowserConnection: boolean;
}
```

**Response:** `200 OK`
```typescript
{
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  robotsTxtCheck?: RobotsTxtResult;
  schemaValidation?: SchemaValidationResult;
  browserTest?: BrowserTestResult;
}
```

---

#### `POST /targets/:id/execute`
Trigger immediate execution of a target.

**Request Body:**
```typescript
{
  priority?: number;        // 1-10, default: 5
  overrideConfig?: Partial<ScrapingTargetConfiguration>;
  callbackUrl?: string;
  webhookEvents?: string[];
}
```

**Response:** `202 Accepted`
```typescript
{
  jobId: UUID;
  status: 'QUEUED';
  estimatedStartTime?: Timestamp;
  queuePosition: number;
}
```

---

### ScrapingJob Endpoints

#### `GET /jobs`
List all scraping jobs with filtering and pagination.

**Query Parameters:**
```typescript
{
  page?: number;
  limit?: number;
  targetId?: UUID;
  status?: JobStatus | JobStatus[];
  triggeredBy?: string;
  dateFrom?: Timestamp;
  dateTo?: Timestamp;
  priorityMin?: number;
  priorityMax?: number;
  hasErrors?: boolean;
  sortBy?: 'createdAt' | 'startedAt' | 'completedAt' | 'priority';
  sortOrder?: 'asc' | 'desc';
}
```

**Response:** `200 OK`
```typescript
{
  data: ScrapingJobSummary[];
  aggregation: {
    byStatus: Record<JobStatus, number>;
    totalExecutionTimeMs: number;
    totalRecordsExtracted: number;
  };
  pagination: PaginationInfo;
}
```

---

#### `GET /jobs/:id`
Get detailed job information including execution stages.

**Response:** `200 OK`
```typescript
ScrapingJob & {
  stages: JobStageDetail[];
  logs: JobLogEntry[];
  errors: JobError[];
  resources: ResourceUsageDetail;
}
```

---

#### `DELETE /jobs/:id`
Cancel a running or queued job.

**Response:**
- `202 Accepted` - Cancellation requested
- `409 Conflict` - Job already completed or failed

---

#### `GET /jobs/:id/progress`
Get real-time job progress (SSE/WebSocket alternative).

**Response:** `200 OK`
```typescript
{
  jobId: UUID;
  status: JobStatus;
  progress: {
    percentComplete: number;
    currentStage: PipelineStage;
    currentUrl?: string;
    pagesProcessed: number;
    pagesTotal?: number;
    estimatedTimeRemainingMs?: number;
  };
  lastUpdate: Timestamp;
}
```

---

#### `GET /jobs/:id/results`
Get extracted data results for a job.

**Query Parameters:**
```typescript
{
  page?: number;
  limit?: number;
  format?: 'json' | 'csv' | 'ndjson';
  includeRaw?: boolean;
  fields?: string[];  // Field selection
}
```

**Response:** `200 OK`
```typescript
{
  jobId: UUID;
  format: string;
  totalRecords: number;
  data: ExtractedData[] | string;  // String for CSV
  downloadUrl?: string;            // For large results
  expiresAt?: Timestamp;
}
```

---

#### `POST /jobs/:id/retry`
Retry a failed or partially successful job.

**Request Body:**
```typescript
{
  retryStrategy: 'FULL' | 'FAILED_ONLY' | 'FROM_STAGE';
  fromStage?: PipelineStage;
  maxRetries?: number;
}
```

**Response:** `202 Accepted` - New job ID

---

### Content Retrieval Endpoints

#### `GET /content/raw/:id`
Retrieve raw content by ID.

**Query Parameters:**
```typescript
{
  includeHtml?: boolean;
  includeScreenshot?: boolean;
  includeHar?: boolean;
}
```

**Response:** `200 OK`
```typescript
{
  rawContent: RawContent;
  presignedUrls?: {
    html?: string;
    screenshot?: string;
    har?: string;
    domSnapshot?: string;
  };
}
```

---

#### `GET /content/extracted/:id`
Retrieve extracted data by ID.

**Query Parameters:**
```typescript
{
  format?: 'json' | 'markdown' | 'flattened';
}
```

**Response:** `200 OK` - ExtractedData

---

### Compliance and Audit Endpoints

#### `GET /compliance/logs`
Query compliance logs.

**Query Parameters:**
```typescript
{
  eventType?: ComplianceEventType | ComplianceEventType[];
  severity?: string;
  domain?: string;
  dateFrom?: Timestamp;
  dateTo?: Timestamp;
  jobId?: UUID;
}
```

**Response:** `200 OK` - Paginated ComplianceLog[]

---

#### `GET /compliance/summary`
Get compliance summary for organization.

**Response:** `200 OK`
```typescript
{
  period: { start: Timestamp; end: Timestamp };
  robotsTxtCompliance: {
    totalChecks: number;
    allowed: number;
    blocked: number;
    crawlDelaysRespected: number;
  };
  rateLimiting: {
    totalRequests: number;
    throttledRequests: number;
    averageDelayMs: number;
  };
  piiDetection: {
    scansPerformed: number;
    detections: number;
    redactionsApplied: number;
  };
  domainPolicies: {
    allowlisted: number;
    blocklisted: number;
    blockedRequests: number;
  };
}
```

---

### Status and Health Endpoints

#### `GET /health`
Service health check.

**Response:** `200 OK`
```typescript
{
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  components: {
    database: ComponentHealth;
    queue: ComponentHealth;
    browserPool: ComponentHealth;
    llmProviders: Record<string, ComponentHealth>;
    storage: ComponentHealth;
  };
  metrics: {
    activeJobs: number;
    queuedJobs: number;
    availableBrowsers: number;
    averageWaitTimeMs: number;
  };
}
```

---

#### `GET /metrics`
Prometheus-compatible metrics endpoint.

**Response:** `200 OK` - Text format metrics

---

### 2.2 GraphQL Schema (Optional Enhancement)

```graphql
type ScrapingTarget {
  id: ID!
  organizationId: ID!
  name: String!
  description: String
  url: String!
  targetType: TargetType!
  status: TargetStatus!
  extractionConfig: ExtractionConfig!
  browserConfig: BrowserConfig!
  schedule: Schedule
  rateLimit: RateLimit!
  compliance: ComplianceSettings!
  
  # Computed fields
  recentJobs(limit: Int = 5): [ScrapingJob!]!
  successRate(days: Int = 30): Float!
  averageExecutionTimeMs: Float!
  totalJobs: Int!
  
  createdAt: DateTime!
  updatedAt: DateTime!
}

type ScrapingJob {
  id: ID!
  targetId: ID!
  status: JobStatus!
  priority: Int!
  progress: JobProgress!
  results: JobResults
  errors: [JobError!]!
  resources: ResourceUsage!
  
  # Relations
  target: ScrapingTarget!
  rawContents: [RawContent!]!
  extractedData: [ExtractedData!]!
  complianceLogs: [ComplianceLog!]!
  
  createdAt: DateTime!
  startedAt: DateTime
  completedAt: DateTime
}

type Query {
  # Targets
  targets(
    filter: TargetFilter
    pagination: PaginationInput
  ): TargetConnection!
  target(id: ID!): ScrapingTarget
  
  # Jobs
  jobs(
    filter: JobFilter
    pagination: PaginationInput
  ): JobConnection!
  job(id: ID!): ScrapingJob
  
  # Content
  rawContent(id: ID!): RawContent
  extractedData(id: ID!): ExtractedData
  
  # Compliance
  complianceLogs(filter: ComplianceFilter): ComplianceLogConnection!
  complianceSummary(period: DateRange!): ComplianceSummary!
  
  # Real-time
  jobProgress(jobId: ID!): JobProgress!
}

type Mutation {
  createTarget(input: CreateTargetInput!): ScrapingTarget!
  updateTarget(id: ID!, input: UpdateTargetInput!): ScrapingTarget!
  deleteTarget(id: ID!): Boolean!
  
  executeTarget(id: ID!, input: ExecuteInput): ScrapingJob!
  cancelJob(id: ID!): ScrapingJob!
  retryJob(id: ID!, input: RetryInput): ScrapingJob!
  
  validateTarget(id: ID!, input: ValidateInput): ValidationResult!
}

type Subscription {
  jobProgress(jobId: ID!): JobProgress!
  targetStatus(targetId: ID!): TargetStatusUpdate!
  jobCompleted(organizationId: ID!): ScrapingJob!
}
```

---

## 3. PIPELINE STAGES

### 3.1 Pipeline Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           INGESTION PIPELINE FLOW                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘

   ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
   │  Job     │───▶│  Compliance  │───▶│   Browser   │───▶│  Navigation  │
   │  Queue   │    │   Check      │    │  Acquisition│    │   & Capture  │
   └──────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                                                               │
                    ┌─────────────────────────────────────────┼─────────────────────────┐
                    ▼                                         ▼                         ▼
           ┌──────────────┐                         ┌──────────────┐           ┌──────────────┐
           │  Pagination  │                         │   Content    │           │   Dynamic    │
           │   Handler    │                         │  Extraction  │           │    Wait      │
           └──────────────┘                         └──────────────┘           └──────────────┘
                    │                                         │
                    └─────────────────────┬───────────────────┘
                                          ▼
                              ┌──────────────────────┐
                              │   AI/LLM Extraction  │
                              │   (Multimodal)       │
                              └──────────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
           ┌──────────────┐    ┌──────────────────┐   ┌──────────────┐
           │  Validation  │───▶│ Post-Processing  │──▶│   Storage    │
           │              │    │ (PII, Normalize) │   │              │
           └──────────────┘    └──────────────────┘   └──────────────┘
                                                                   │
                                                                   ▼
                                                          ┌──────────────┐
                                                          │  Ontology    │
                                                          │   Mapping    │
                                                          └──────────────┘
```

### 3.2 Stage Definitions

#### Stage 1: Job Queue & Scheduling

**Purpose:** Manage job lifecycle and resource allocation

**Input:** ScrapingJob entity

**Processing Logic:**
```python
class JobQueueManager:
    def enqueue_job(self, job: ScrapingJob) -> QueuePosition:
        # Priority calculation
        priority_score = self._calculate_priority(job)
        
        # Resource requirement estimation
        estimated_resources = self._estimate_resources(job)
        
        # Queue placement
        queue_key = f"queue:org:{job.organization_id}:priority"
        redis.zadd(queue_key, {job.id: priority_score})
        
        # Schedule if needed
        if job.scheduled_at and job.scheduled_at > now():
            self._schedule_delayed(job)
        
        return QueuePosition(
            position=redis.zrank(queue_key, job.id),
            estimated_wait_ms=self._estimate_wait_time(job)
        )
    
    def _calculate_priority(self, job: ScrapingJob) -> float:
        base_priority = job.priority * 1000  # 1-10 scale
        
        # Age factor (older jobs get slight boost)
        age_hours = (now() - job.created_at).hours
        age_boost = min(age_hours * 10, 500)
        
        # Organization fairness factor
        org_recent_jobs = self._count_recent_jobs(job.organization_id)
        fairness_penalty = org_recent_jobs * 50
        
        # Target importance
        target_boost = job.target.priority_score if job.target else 0
        
        return base_priority + age_boost - fairness_penalty + target_boost
```

**Output:** Queued job with position and estimated wait time

**Error Handling:**
- Queue full: Reject with 429, suggest retry after
- Duplicate job: Return existing job ID with 303
- Invalid configuration: Fail fast with validation errors

---

#### Stage 2: Compliance Check

**Purpose:** Validate scraping request against legal and policy constraints

**Input:** ScrapingJob with target configuration

**Processing Logic:**
```python
class ComplianceChecker:
    async def check_compliance(self, job: ScrapingJob) -> ComplianceResult:
        results = []
        
        # 1. robots.txt check
        robots_result = await self._check_robots_txt(job)
        results.append(robots_result)
        
        # 2. Domain policy check
        domain_result = self._check_domain_policy(job)
        results.append(domain_result)
        
        # 3. Rate limit check
        rate_result = await self._check_rate_limits(job)
        results.append(rate_result)
        
        # 4. Terms of service check (cached)
        tos_result = await self._check_tos_compliance(job)
        results.append(tos_result)
        
        # Aggregate results
        blocked = any(r.blocks_execution for r in results)
        warnings = [r for r in results if r.severity == 'WARNING']
        
        # Log all checks
        await self._log_compliance_checks(job, results)
        
        return ComplianceResult(
            can_proceed=not blocked,
            results=results,
            required_delay_ms=sum(r.required_delay_ms for r in results),
            warnings=warnings
        )
    
    async def _check_robots_txt(self, job: ScrapingJob) -> ComplianceCheck:
        url = job.target.url
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        
        # Check cache first
        cached = await self.cache.get(f"robots:{parsed.netloc}")
        if cached:
            parser = RobotsParser.from_cache(cached)
        else:
            try:
                response = await self.http.get(robots_url, timeout=10)
                parser = RobotsParser.parse(response.text)
                await self.cache.set(
                    f"robots:{parsed.netloc}",
                    parser.serialize(),
                    ttl=timedelta(hours=24)
                )
            except Exception as e:
                return ComplianceCheck(
                    check_type='ROBOTS_TXT',
                    severity='WARNING',
                    message=f"Could not fetch robots.txt: {e}",
                    blocks_execution=job.target.compliance.strict_robots_txt
                )
        
        user_agent = job.target.compliance.user_agent_string
        path = parsed.path or '/'
        
        allowed = parser.can_fetch(user_agent, path)
        crawl_delay = parser.get_crawl_delay(user_agent)
        
        return ComplianceCheck(
            check_type='ROBOTS_TXT',
            severity='ERROR' if not allowed else 'INFO',
            message=f"Path {path} {'allowed' if allowed else 'disallowed'} for {user_agent}",
            blocks_execution=not allowed,
            details={
                'robots_txt_url': robots_url,
                'user_agent': user_agent,
                'path': path,
                'allowed': allowed,
                'crawl_delay': crawl_delay,
                'sitemaps': parser.get_sitemaps()
            },
            required_delay_ms=(crawl_delay or 0) * 1000
        )
    
    def _check_domain_policy(self, job: ScrapingJob) -> ComplianceCheck:
        domain = urlparse(job.target.url).netloc
        compliance = job.target.compliance
        
        # Check blocklist first
        if any(self._match_domain(domain, blocked) for blocked in compliance.domain_blocklist):
            return ComplianceCheck(
                check_type='DOMAIN_POLICY',
                severity='ERROR',
                message=f"Domain {domain} is blocklisted",
                blocks_execution=True
            )
        
        # Check allowlist (if configured)
        if compliance.domain_allowlist:
            if not any(self._match_domain(domain, allowed) for allowed in compliance.domain_allowlist):
                return ComplianceCheck(
                    check_type='DOMAIN_POLICY',
                    severity='ERROR',
                    message=f"Domain {domain} not in allowlist",
                    blocks_execution=True
                )
        
        return ComplianceCheck(
            check_type='DOMAIN_POLICY',
            severity='INFO',
            message=f"Domain {domain} policy check passed",
            blocks_execution=False
        )
    
    async def _check_rate_limits(self, job: ScrapingJob) -> ComplianceCheck:
        domain = urlparse(job.target.url).netloc
        rate_config = job.target.rate_limit
        
        # Check multiple time windows
        windows = [
            ('second', rate_config.requests_per_second, 1),
            ('minute', rate_config.requests_per_minute, 60),
            ('hour', rate_config.requests_per_hour, 3600),
        ]
        
        max_delay = 0
        for window_name, limit, window_seconds in windows:
            if limit <= 0:
                continue
                
            key = f"rate_limit:{domain}:{window_name}:{int(time.time()) // window_seconds}"
            current = await self.redis.incr(key)
            
            if current == 1:
                await self.redis.expire(key, window_seconds)
            
            if current > limit:
                # Calculate backoff
                delay_ms = self._calculate_backoff(
                    current, limit, window_seconds, rate_config.retry_backoff
                )
                max_delay = max(max_delay, delay_ms)
        
        return ComplianceCheck(
            check_type='RATE_LIMIT',
            severity='WARNING' if max_delay > 0 else 'INFO',
            message=f"Rate limit check: {'delay required' if max_delay > 0 else 'within limits'}",
            blocks_execution=False,
            required_delay_ms=max_delay,
            details={'delay_ms': max_delay}
        )
```

**Output:** ComplianceResult with proceed/deny decision and required delays

**Error Handling:**
- robots.txt fetch failure: Default to allow (configurable)
- Rate limit exceeded: Queue with exponential backoff
- Domain blocked: Fail job immediately with compliance error

---

#### Stage 3: Browser Acquisition

**Purpose:** Acquire and configure headless browser instance

**Input:** ScrapingJob with browser configuration

**Processing Logic:**
```python
class BrowserPool:
    def __init__(self):
        self.browserbase = BrowserbaseClient()
        self.active_sessions: Dict[UUID, BrowserSession] = {}
    
    async def acquire_browser(self, job: ScrapingJob) -> BrowserSession:
        config = job.target.browser_config
        proxy_config = job.target.proxy_config
        
        # Build Browserbase options
        session_options = {
            'project_id': settings.BROWSERBASE_PROJECT_ID,
            'browser_settings': {
                'viewport': {
                    'width': config.viewport.width,
                    'height': config.viewport.height
                },
                'user_agent': config.user_agent or self._get_rotated_user_agent(),
                'javascript_enabled': config.javascript_enabled,
            },
            'timeout': {
                'session': 3600,  # 1 hour max session
            }
        }
        
        # Add proxy if enabled
        if proxy_config.enabled:
            proxy = await self._select_proxy(proxy_config, job)
            session_options['proxy'] = {
                'host': proxy.host,
                'port': proxy.port,
                'username': proxy.username,
                'password': await self._get_proxy_password(proxy)
            }
        
        # Add stealth options if enabled
        if config.stealth_mode:
            session_options['browser_settings']['stealth'] = True
            session_options['browser_settings']['fingerprint'] = {
                'screen': self._generate_realistic_screen(),
                'webgl': True,
                'canvas': True,
                'fonts': True
            }
        
        # Create session
        session = await self.browserbase.create_session(session_options)
        
        browser_session = BrowserSession(
            id=session.id,
            job_id=job.id,
            connect_url=session.connect_url,
            created_at=now(),
            config=config
        )
        
        self.active_sessions[job.id] = browser_session
        
        return browser_session
    
    async def _select_proxy(self, config: ProxyConfig, job: ScrapingJob) -> Proxy:
        if config.rotation_strategy == 'GEO_BASED':
            # Select proxy matching target geography
            target_domain = urlparse(job.target.url).netloc
            country = await self._infer_country(target_domain)
            return await self._get_geo_proxy(country, config.proxy_pool_id)
        
        elif config.rotation_strategy == 'SESSION_BASED':
            # Use sticky session for job duration
            return await self._get_sticky_proxy(config.proxy_pool_id, job.id)
        
        elif config.rotation_strategy == 'ROUND_ROBIN':
            return await self._get_round_robin_proxy(config.proxy_pool_id)
        
        else:  # RANDOM
            return await self._get_random_proxy(config.proxy_pool_id)
```

**Output:** BrowserSession with connection URL and configuration

**Error Handling:**
- Pool exhausted: Queue job with retry
- Proxy failure: Retry with different proxy, mark failed proxy
- Browser crash: Restart session, resume from checkpoint

---

#### Stage 4: Navigation & Content Capture

**Purpose:** Navigate to target URL and capture all content types

**Input:** BrowserSession, ScrapingJob

**Processing Logic:**
```python
class NavigationEngine:
    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
    
    async def navigate_and_capture(self, job: ScrapingJob, session: BrowserSession) -> RawContent:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp(session.connect_url)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Set up request/response interception
            har_path = f"/tmp/{job.id}.har"
            har_recorder = await context.new_har(path=har_path)
            
            # Navigate with timeout and wait conditions
            config = job.target.browser_config
            response = await page.goto(
                job.target.url,
                wait_until='networkidle',
                timeout=config.wait_timeout
            )
            
            # Handle dynamic content loading
            if config.wait_for_selector:
                await page.wait_for_selector(
                    config.wait_for_selector,
                    timeout=config.wait_timeout
                )
            
            # Scroll to trigger lazy loading
            await self._scroll_page(page)
            
            # Handle pagination if configured
            if job.target.target_type == 'PAGINATED':
                return await self._handle_pagination(job, page, session)
            
            # Handle spider mode
            if job.target.target_type == 'SPIDER':
                return await self._handle_spider(job, page, session)
            
            # Single page capture
            return await self._capture_single_page(job, page, response, har_path)
            
        except TimeoutError:
            raise NavigationError(f"Timeout navigating to {job.target.url}")
        except Exception as e:
            raise NavigationError(f"Navigation failed: {e}")
        finally:
            await context.close()
            await browser.close()
            await playwright.stop()
    
    async def _capture_single_page(
        self, 
        job: ScrapingJob, 
        page: Page, 
        response: Response,
        har_path: str
    ) -> RawContent:
        # Capture multiple content formats in parallel
        capture_tasks = [
            page.content(),                          # HTML
            page.screenshot(full_page=True, type='png'),  # Screenshot
            page.evaluate('() => document.documentElement.outerHTML'),  # DOM
            self._extract_text_content(page),        # Clean text
        ]
        
        html, screenshot, dom_snapshot, text_content = await asyncio.gather(*capture_tasks)
        
        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(text_content.encode()).hexdigest()
        
        # Check for duplicate
        existing = await self._check_duplicate(content_hash)
        if existing:
            return RawContent(
                is_duplicate=True,
                duplicate_of=existing.id,
                content_hash=content_hash
            )
        
        # Extract metadata
        metadata = await self._extract_metadata(page)
        
        # Upload to storage
        storage_paths = await self._upload_content(
            job=job,
            html=html,
            screenshot=screenshot,
            dom_snapshot=dom_snapshot,
            har_path=har_path,
            text_content=text_content
        )
        
        return RawContent(
            id=generate_uuid(),
            job_id=job.id,
            organization_id=job.organization_id,
            target_id=job.target_id,
            source={
                'url': job.target.url,
                'final_url': page.url,
                'domain': urlparse(page.url).netloc,
                'accessed_at': now(),
                'http_status': response.status,
                'headers': dict(response.headers),
                'content_type': response.headers.get('content-type', 'unknown'),
                'content_length': len(html)
            },
            storage=storage_paths,
            metadata=metadata,
            capture={
                'method': 'DYNAMIC' if job.target.browser_config.javascript_enabled else 'STATIC',
                'browser_version': await page.evaluate('() => navigator.userAgent'),
                'javascript_executed': job.target.browser_config.javascript_enabled,
                'wait_time_ms': job.target.browser_config.wait_timeout,
                'scroll_depth': await page.evaluate('() => window.scrollY')
            },
            content_hash=content_hash,
            is_duplicate=False,
            processing_status='PENDING',
            created_at=now()
        )
    
    async def _handle_pagination(self, job: ScrapingJob, page: Page, session: BrowserSession) -> List[RawContent]:
        contents = []
        page_num = 1
        max_pages = job.target.extraction_config.max_pages or 100
        
        while page_num <= max_pages:
            # Capture current page
            content = await self._capture_single_page(job, page, None, "")
            contents.append(content)
            
            # Find next page link
            next_selector = job.target.extraction_config.pagination_selector
            next_link = await page.query_selector(next_selector)
            
            if not next_link:
                break
            
            # Click and wait for navigation
            await next_link.click()
            await page.wait_for_load_state('networkidle')
            page_num += 1
        
        return contents
    
    async def _scroll_page(self, page: Page):
        """Scroll page to trigger lazy loading"""
        await page.evaluate('''async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 300;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    
                    if (totalHeight >= scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 100);
            });
        }''')
```

**Output:** RawContent entity with storage references

**Error Handling:**
- Navigation timeout: Retry with longer timeout, then fail
- Content load failure: Capture partial content, log warning
- Infinite scroll detection: Limit scroll depth, cap pages

---

#### Stage 5: AI/LLM Extraction

**Purpose:** Extract structured data from raw content using multimodal LLMs

**Input:** RawContent, ScrapingJob with extraction schema

**Processing Logic:**
```python
class AIExtractionEngine:
    def __init__(self):
        self.llm_providers = {
            'openai': OpenAIProvider(),
            'anthropic': AnthropicProvider(),
            'azure_openai': AzureOpenAIProvider()
        }
        self.firecrawl = FirecrawlClient()
        self.agentql = AgentQLClient()
    
    async def extract(self, raw_content: RawContent, job: ScrapingJob) -> ExtractedData:
        config = job.target.extraction_config
        
        if config.method == 'AI_LLM':
            return await self._llm_extract(raw_content, job)
        elif config.method == 'DETERMINISTIC':
            return await self._deterministic_extract(raw_content, job)
        else:  # HYBRID
            return await self._hybrid_extract(raw_content, job)
    
    async def _llm_extract(self, raw_content: RawContent, job: ScrapingJob) -> ExtractedData:
        provider = self.llm_providers[config.llm_provider]
        schema = config.extraction_schema
        
        # Build multimodal prompt
        messages = self._build_multimodal_prompt(raw_content, schema, config)
        
        # Call LLM with structured output
        start_time = time.time()
        response = await provider.chat.completions.create(
            model=self._select_model(config),
            messages=messages,
            response_format={
                'type': 'json_schema',
                'json_schema': {
                    'name': 'extraction_result',
                    'schema': schema
                }
            },
            temperature=0.1,  # Low temperature for consistency
            max_tokens=4000
        )
        extraction_time_ms = (time.time() - start_time) * 1000
        
        # Parse and validate result
        extracted_data = json.loads(response.choices[0].message.content)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(response, extracted_data, schema)
        
        return ExtractedData(
            id=generate_uuid(),
            job_id=job.id,
            raw_content_id=raw_content.id,
            organization_id=job.organization_id,
            target_id=job.target_id,
            extraction={
                'method': 'AI_LLM',
                'llm_model': response.model,
                'prompt_version': self._get_prompt_version(),
                'extraction_time_ms': extraction_time_ms,
                'confidence_score': confidence,
                'schema_version': schema.get('$version', '1.0')
            },
            data=extracted_data,
            validation=self._validate_against_schema(extracted_data, schema),
            provenance={
                'raw_content_id': raw_content.id,
                'source_url': raw_content.source.url,
                'extracted_at': now(),
                'extraction_version': '2.0'
            },
            created_at=now()
        )
    
    def _build_multimodal_prompt(
        self, 
        raw_content: RawContent, 
        schema: dict,
        config: ExtractionConfig
    ) -> List[dict]:
        messages = []
        
        # System prompt with schema definition
        system_prompt = f"""You are an expert web data extraction specialist. 
Extract structured data from the provided web page content according to the following schema:

{json.dumps(schema, indent=2)}

Instructions:
- Extract all fields defined in the schema
- Use null for missing optional fields
- Maintain data types as specified
- Preserve hierarchical relationships
- Return ONLY valid JSON matching the schema
"""
        messages.append({'role': 'system', 'content': system_prompt})
        
        # Add visual context if enabled
        if config.visual_hints and raw_content.storage.screenshot_path:
            screenshot_url = self._get_presigned_url(raw_content.storage.screenshot_path)
            messages.append({
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'Extract data from this webpage screenshot:'},
                    {'type': 'image_url', 'image_url': {'url': screenshot_url}}
                ]
            })
        
        # Add text content
        text_content = self._get_text_content(raw_content)
        messages.append({
            'role': 'user',
            'content': f"Extract data from this webpage content:\n\n{text_content[:8000]}"
        })
        
        return messages
    
    async def _hybrid_extract(self, raw_content: RawContent, job: ScrapingJob) -> ExtractedData:
        """Combine deterministic pre-processing with AI refinement"""
        
        # Step 1: Deterministic extraction for known structures
        pre_extracted = await self._deterministic_extract(raw_content, job)
        
        # Step 2: AI refinement for complex fields
        complex_fields = self._identify_complex_fields(pre_extracted.data)
        
        if complex_fields:
            refinement = await self._llm_refinement(
                raw_content, 
                complex_fields, 
                job.target.extraction_config
            )
            pre_extracted.data.update(refinement)
        
        return pre_extracted
```

**Output:** ExtractedData entity with structured content

**Error Handling:**
- LLM timeout: Retry with shorter content, fallback to deterministic
- Schema validation failure: Log errors, attempt partial extraction
- Low confidence: Flag for review, queue for human verification

---

#### Stage 6: Post-Processing

**Purpose:** Clean, normalize, and redact extracted data

**Input:** ExtractedData

**Processing Logic:**
```python
class PostProcessor:
    def __init__(self):
        self.pii_detector = PIIDetector()
        self.normalizer = DataNormalizer()
    
    async def process(self, extracted_data: ExtractedData, job: ScrapingJob) -> ExtractedData:
        data = extracted_data.data
        
        # 1. PII Detection and Redaction
        if job.target.compliance.pii_redaction_enabled:
            data, redacted = await self._redact_pii(data, job)
            extracted_data.post_processing.pii_redaction_applied = True
            extracted_data.post_processing.redacted_fields = redacted
        
        # 2. Data Normalization
        data, normalized = self._normalize_data(data, job.target.extraction_config)
        extracted_data.post_processing.normalized_fields = normalized
        
        # 3. Field Enrichment
        data, enriched = await self._enrich_data(data, job)
        extracted_data.post_processing.enriched_fields = enriched
        
        # 4. Validation
        validation = self._validate_final(data, job.target.extraction_config.extraction_schema)
        extracted_data.validation = validation
        
        extracted_data.data = data
        extracted_data.updated_at = now()
        
        return extracted_data
    
    async def _redact_pii(self, data: dict, job: ScrapingJob) -> Tuple[dict, List[str]]:
        redacted_fields = []
        
        # Patterns for PII detection
        pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        }
        
        # Add custom patterns from config
        for pattern in job.target.compliance.sensitive_field_patterns:
            pii_patterns[f'custom_{len(pii_patterns)}'] = pattern
        
        def redact_recursive(obj: Any, path: str = '') -> Any:
            if isinstance(obj, dict):
                return {k: redact_recursive(v, f"{path}.{k}") for k, v in obj.items()}
            elif isinstance(obj, list):
                return [redact_recursive(item, f"{path}[]") for item in obj]
            elif isinstance(obj, str):
                redacted = obj
                for pattern_name, pattern in pii_patterns.items():
                    if re.search(pattern, redacted):
                        redacted = re.sub(pattern, '[REDACTED]', redacted)
                        redacted_fields.append(f"{path}:{pattern_name}")
                return redacted
            return obj
        
        return redact_recursive(data), redacted_fields
    
    def _normalize_data(self, data: dict, config: ExtractionConfig) -> Tuple[dict, List[str]]:
        normalized_fields = []
        
        normalizers = {
            'date': self._normalize_date,
            'currency': self._normalize_currency,
            'phone': self._normalize_phone,
            'url': self._normalize_url,
            'company_name': self._normalize_company_name,
        }
        
        def normalize_recursive(obj: Any, schema: dict, path: str = '') -> Any:
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    field_schema = schema.get('properties', {}).get(k, {})
                    result[k] = normalize_recursive(v, field_schema, f"{path}.{k}")
                return result
            elif isinstance(obj, list):
                item_schema = schema.get('items', {})
                return [normalize_recursive(item, item_schema, f"{path}[]") for item in obj]
            elif isinstance(obj, str):
                # Apply normalizer based on field format
                field_format = schema.get('format')
                if field_format and field_format in normalizers:
                    normalized_fields.append(path)
                    return normalizers[field_format](obj)
                return obj.strip()
            return obj
        
        return normalize_recursive(data, config.extraction_schema), normalized_fields
```

**Output:** Processed ExtractedData with redaction and normalization applied

---

#### Stage 7: Storage

**Purpose:** Persist extracted data to appropriate storage backends

**Input:** Processed ExtractedData

**Processing Logic:**
```python
class StorageManager:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.pg_pool = asyncpg.create_pool(settings.DATABASE_URL)
        self.opensearch = OpenSearchClient()
    
    async def store(self, extracted_data: ExtractedData, job: ScrapingJob) -> StorageResult:
        # Determine storage strategy based on data characteristics
        storage_plan = self._determine_storage_plan(extracted_data, job)
        
        results = []
        
        # 1. Store raw JSON to object storage
        if 'object_storage' in storage_plan:
            result = await self._store_to_s3(extracted_data, job)
            results.append(result)
        
        # 2. Store structured data to PostgreSQL
        if 'relational' in storage_plan:
            result = await self._store_to_postgres(extracted_data, job)
            results.append(result)
        
        # 3. Index for search in OpenSearch
        if 'search_index' in storage_plan:
            result = await self._index_to_opensearch(extracted_data, job)
            results.append(result)
        
        # 4. Send to downstream systems
        if 'ontology' in storage_plan:
            result = await self._send_to_ontology(extracted_data, job)
            results.append(result)
        
        return StorageResult(
            locations=[r.location for r in results],
            total_bytes=sum(r.bytes_stored for r in results),
            success=all(r.success for r in results)
        )
    
    async def _store_to_s3(self, data: ExtractedData, job: ScrapingJob) -> StorageOperation:
        key = f"extracted/{job.organization_id}/{job.target_id}/{job.id}/{data.id}.json"
        
        content = json.dumps({
            'metadata': data.extraction,
            'provenance': data.provenance,
            'data': data.data
        }, default=str)
        
        await self.s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=content,
            ContentType='application/json',
            Metadata={
                'organization-id': str(job.organization_id),
                'job-id': str(job.id),
                'target-id': str(job.target_id)
            }
        )
        
        return StorageOperation(
            backend='s3',
            location=f"s3://{settings.S3_BUCKET}/{key}",
            bytes_stored=len(content),
            success=True
        )
    
    async def _store_to_postgres(self, data: ExtractedData, job: ScrapingJob) -> StorageOperation:
        async with self.pg_pool.acquire() as conn:
            # Store main record
            await conn.execute('''
                INSERT INTO extracted_data (
                    id, job_id, raw_content_id, organization_id, target_id,
                    extraction_method, llm_model, confidence_score,
                    data, validation_result, storage_path, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ''', data.id, data.job_id, data.raw_content_id, data.organization_id,
                data.target_id, data.extraction.method, data.extraction.llm_model,
                data.extraction.confidence_score, json.dumps(data.data),
                json.dumps(data.validation), data.storage_path, data.created_at)
            
            # Store flattened fields for querying
            await self._store_flattened_fields(conn, data)
        
        return StorageOperation(
            backend='postgresql',
            location=f"postgresql://extracted_data/{data.id}",
            bytes_stored=len(json.dumps(data.data)),
            success=True
        )
    
    async def _send_to_ontology(self, data: ExtractedData, job: ScrapingJob) -> StorageOperation:
        """Send extracted data to ontology mapping service"""
        
        ontology_event = {
            'event_type': 'DATA_EXTRACTED',
            'source': {
                'job_id': str(job.id),
                'target_id': str(job.target_id),
                'organization_id': str(job.organization_id),
                'url': data.provenance.source_url
            },
            'extracted_data': data.data,
            'extraction_metadata': {
                'method': data.extraction.method,
                'confidence': data.extraction.confidence_score,
                'timestamp': data.provenance.extracted_at.isoformat()
            },
            'suggested_concepts': self._suggest_concepts(data.data, job.target)
        }
        
        # Publish to message queue for async processing
        await self.message_queue.publish(
            exchange='ontology',
            routing_key='data.extracted',
            body=json.dumps(ontology_event)
        )
        
        return StorageOperation(
            backend='ontology_queue',
            location=f"mq://ontology/data.extracted/{data.id}",
            bytes_stored=len(json.dumps(ontology_event)),
            success=True
        )
```

**Output:** StorageResult with locations and success status

---

### 3.3 Error Handling and Retry Mechanisms

```python
class PipelineErrorHandler:
    ERROR_STRATEGIES = {
        # Navigation errors
        'NAVIGATION_TIMEOUT': {
            'retryable': True,
            'max_retries': 3,
            'backoff': 'exponential',
            'base_delay_ms': 5000,
            'fallback_action': 'SKIP_WITH_WARNING'
        },
        'BROWSER_CRASH': {
            'retryable': True,
            'max_retries': 2,
            'backoff': 'fixed',
            'base_delay_ms': 10000,
            'fallback_action': 'FAIL_JOB'
        },
        'PROXY_FAILURE': {
            'retryable': True,
            'max_retries': 5,
            'backoff': 'exponential',
            'base_delay_ms': 1000,
            'fallback_action': 'USE_DIRECT_CONNECTION'
        },
        
        # Extraction errors
        'LLM_TIMEOUT': {
            'retryable': True,
            'max_retries': 2,
            'backoff': 'exponential',
            'base_delay_ms': 5000,
            'fallback_action': 'USE_DETERMINISTIC'
        },
        'SCHEMA_VALIDATION_FAILED': {
            'retryable': False,
            'fallback_action': 'PARTIAL_EXTRACTION'
        },
        'LOW_CONFIDENCE': {
            'retryable': False,
            'fallback_action': 'FLAG_FOR_REVIEW'
        },
        
        # Compliance errors
        'ROBOTS_TXT_BLOCKED': {
            'retryable': False,
            'fallback_action': 'FAIL_JOB'
        },
        'RATE_LIMITED': {
            'retryable': True,
            'max_retries': 10,
            'backoff': 'exponential',
            'base_delay_ms': 60000,
            'fallback_action': 'RESCHEDULE'
        },
        'DOMAIN_BLOCKED': {
            'retryable': False,
            'fallback_action': 'FAIL_JOB'
        },
        
        # Storage errors
        'STORAGE_FAILURE': {
            'retryable': True,
            'max_retries': 3,
            'backoff': 'fixed',
            'base_delay_ms': 2000,
            'fallback_action': 'QUEUE_FOR_RETRY'
        }
    }
    
    async def handle_error(self, error: PipelineError, job: ScrapingJob, stage: PipelineStage):
        strategy = self.ERROR_STRATEGIES.get(error.error_code, self.DEFAULT_STRATEGY)
        
        # Log error
        await self._log_error(error, job, stage)
        
        # Check retry eligibility
        current_retries = await self._get_retry_count(job, error.error_code)
        
        if strategy['retryable'] and current_retries < strategy['max_retries']:
            delay = self._calculate_delay(strategy, current_retries)
            await self._schedule_retry(job, stage, delay, error)
            return ErrorResolution(action='RETRY', delay_ms=delay)
        
        # Execute fallback action
        fallback = strategy['fallback_action']
        return await self._execute_fallback(fallback, error, job, stage)
    
    def _calculate_delay(self, strategy: dict, retry_count: int) -> int:
        base = strategy['base_delay_ms']
        
        if strategy['backoff'] == 'exponential':
            return base * (2 ** retry_count)
        elif strategy['backoff'] == 'linear':
            return base * (retry_count + 1)
        else:  # fixed
            return base
```

### 3.4 Rate Limiting and Throttling

```python
class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def check_and_throttle(
        self, 
        domain: str, 
        config: RateLimitConfig,
        organization_id: UUID
    ) -> RateLimitResult:
        """
        Multi-tier rate limiting:
        1. Per-domain global limits
        2. Per-organization limits
        3. Per-target limits
        4. Custom target limits
        """
        
        checks = []
        
        # Domain-level rate limiting (protect target servers)
        domain_check = await self._check_domain_limits(domain, config)
        checks.append(domain_check)
        
        # Organization-level limiting (fairness)
        org_check = await self._check_org_limits(organization_id)
        checks.append(org_check)
        
        # Target-specific limits
        target_check = await self._check_target_limits(config)
        checks.append(target_check)
        
        # Find most restrictive limit
        max_delay = max((c.required_delay_ms for c in checks if c.required_delay_ms), default=0)
        
        if max_delay > 0:
            # Apply stochastic jitter to prevent thundering herd
            jitter = random.randint(0, min(max_delay // 4, 5000))
            final_delay = max_delay + jitter
            
            return RateLimitResult(
                allowed=False,
                delay_ms=final_delay,
                reason='RATE_LIMIT_EXCEEDED',
                retry_after=datetime.utcnow() + timedelta(milliseconds=final_delay)
            )
        
        return RateLimitResult(allowed=True)
    
    async def _check_domain_limits(self, domain: str, config: RateLimitConfig) -> LimitCheck:
        """Sliding window rate limit with Redis sorted sets"""
        
        window_key = f"ratelimit:domain:{domain}:requests"
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        # Remove old entries
        await self.redis.zremrangebyscore(window_key, 0, window_start)
        
        # Count current requests
        current = await self.redis.zcard(window_key)
        
        # Add current request
        await self.redis.zadd(window_key, {str(now): now})
        await self.redis.expire(window_key, 60)
        
        if current >= config.requests_per_minute:
            # Calculate when next slot opens
            oldest = await self.redis.zrange(window_key, 0, 0, withscores=True)
            if oldest:
                next_slot = oldest[0][1] + 60
                delay_ms = max(0, int((next_slot - now) * 1000))
                return LimitCheck(
                    limit_type='DOMAIN_PER_MINUTE',
                    current=current,
                    limit=config.requests_per_minute,
                    required_delay_ms=delay_ms
                )
        
        return LimitCheck(allowed=True)
```

---

## 4. INTEGRATION PATTERNS

### 4.1 LLM Extraction Services Integration

```python
class LLMProviderInterface(ABC):
    @abstractmethod
    async def extract_structured(
        self,
        content: RawContent,
        schema: JSONSchema,
        options: ExtractionOptions
    ) -> ExtractionResult:
        pass
    
    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        pass

class OpenAIProvider(LLMProviderInterface):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model_preferences = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']
    
    async def extract_structured(
        self,
        content: RawContent,
        schema: JSONSchema,
        options: ExtractionOptions
    ) -> ExtractionResult:
        # Build messages with multimodal support
        messages = self._build_messages(content, schema, options)
        
        # Select appropriate model
        model = self._select_model(content, options)
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={
                'type': 'json_schema',
                'json_schema': {
                    'name': 'extraction_result',
                    'schema': schema,
                    'strict': True
                }
            },
            temperature=0.1,
            max_tokens=options.max_tokens or 4000
        )
        
        return ExtractionResult(
            data=json.loads(response.choices[0].message.content),
            model_used=response.model,
            tokens_used=response.usage.total_tokens,
            confidence=self._calculate_confidence(response),
            latency_ms=response.response_ms
        )

class FirecrawlAdapter(LLMProviderInterface):
    """Adapter for Firecrawl service"""
    
    def __init__(self):
        self.client = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)
    
    async def extract_structured(
        self,
        content: RawContent,
        schema: JSONSchema,
        options: ExtractionOptions
    ) -> ExtractionResult:
        result = self.client.scrape_url(
            url=content.source.url,
            params={
                'formats': ['markdown', 'html'],
                'only_main_content': True,
                'include_tags': options.include_selectors,
                'exclude_tags': options.exclude_selectors
            }
        )
        
        # Firecrawl returns clean markdown, feed to LLM for structuring
        structured = await self._structure_with_llm(
            markdown=result['markdown'],
            schema=schema
        )
        
        return structured

class LLMRouter:
    """Intelligent routing between LLM providers with failover"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProviderInterface] = {
            'openai': OpenAIProvider(),
            'anthropic': AnthropicProvider(),
            'firecrawl': FirecrawlAdapter(),
            'agentql': AgentQLAdapter()
        }
        self.health_monitor = ProviderHealthMonitor()
    
    async def extract_with_fallback(
        self,
        content: RawContent,
        schema: JSONSchema,
        preferences: List[str],
        options: ExtractionOptions
    ) -> ExtractionResult:
        """Try providers in order of preference with automatic failover"""
        
        for provider_name in preferences:
            provider = self.providers.get(provider_name)
            if not provider:
                continue
            
            # Check provider health
            health = await self.health_monitor.get_health(provider_name)
            if health.status == 'UNHEALTHY':
                continue
            
            try:
                result = await provider.extract_structured(content, schema, options)
                await self.health_monitor.record_success(provider_name, result.latency_ms)
                return result
            except Exception as e:
                await self.health_monitor.record_failure(provider_name, str(e))
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
        
        raise AllProvidersFailed("No LLM providers available")
```

### 4.2 Ontology System Integration

```python
class OntologyIntegration:
    """Integration with Value Fabric ontology system"""
    
    def __init__(self):
        self.message_queue = MessageQueueClient()
        self.ontology_api = OntologyAPIClient()
    
    async def publish_extraction(
        self, 
        extracted_data: ExtractedData,
        job: ScrapingJob
    ) -> OntologyMappingResult:
        """Publish extracted data for ontology mapping"""
        
        event = {
            'event_type': 'EXTRACTION_COMPLETED',
            'timestamp': datetime.utcnow().isoformat(),
            'payload': {
                'extraction_id': str(extracted_data.id),
                'job_id': str(job.id),
                'target_id': str(job.target_id),
                'organization_id': str(job.organization_id),
                'source_url': extracted_data.provenance.source_url,
                'extraction_method': extracted_data.extraction.method,
                'confidence_score': extracted_data.extraction.confidence_score,
                'data': extracted_data.data,
                'suggested_mappings': await self._suggest_ontology_mappings(
                    extracted_data.data, 
                    job.target
                )
            }
        }
        
        # Publish to ontology processing queue
        await self.message_queue.publish(
            exchange='value_fabric.ontology',
            routing_key='extraction.completed',
            body=json.dumps(event),
            headers={
                'x-organization-id': str(job.organization_id),
                'x-priority': job.priority,
                'x-confidence': extracted_data.extraction.confidence_score
            }
        )
        
        return OntologyMappingResult(
            published=True,
            message_id=event['timestamp']
        )
    
    async def _suggest_ontology_mappings(
        self, 
        data: dict, 
        target: ScrapingTarget
    ) -> List[OntologySuggestion]:
        """Suggest potential ontology mappings based on data content"""
        
        suggestions = []
        
        # Analyze data for known patterns
        if 'company_name' in data or 'organization' in data:
            suggestions.append(OntologySuggestion(
                concept_type='Organization',
                confidence=0.9,
                fields=['company_name', 'organization'],
                relationship_hints=['operates_in', 'competes_with']
            ))
        
        if 'revenue' in data or 'market_cap' in data:
            suggestions.append(OntologySuggestion(
                concept_type='FinancialMetric',
                confidence=0.85,
                fields=['revenue', 'market_cap', 'growth_rate'],
                relationship_hints=['measures', 'compares_to']
            ))
        
        if 'product_name' in data or 'service' in data:
            suggestions.append(OntologySuggestion(
                concept_type='Product',
                confidence=0.8,
                fields=['product_name', 'service', 'features'],
                relationship_hints=['produced_by', 'competes_with']
            ))
        
        return suggestions
```

### 4.3 Storage Backend Integration

```python
class StorageBackendInterface(ABC):
    @abstractmethod
    async def store(self, key: str, data: bytes, metadata: dict) -> StorageResult:
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> RetrievedData:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def generate_presigned_url(self, key: str, expiry_seconds: int) -> str:
        pass

class S3StorageBackend(StorageBackendInterface):
    def __init__(self):
        self.client = boto3.client('s3')
        self.bucket = settings.S3_BUCKET
    
    async def store(self, key: str, data: bytes, metadata: dict) -> StorageResult:
        await self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            Metadata={k: str(v) for k, v in metadata.items()},
            ServerSideEncryption='AES256'
        )
        
        return StorageResult(
            backend='s3',
            location=f"s3://{self.bucket}/{key}",
            bytes_stored=len(data),
            etag=response['ETag']
        )

class GCSStorageBackend(StorageBackendInterface):
    """Google Cloud Storage backend"""
    pass

class AzureBlobStorageBackend(StorageBackendInterface):
    """Azure Blob Storage backend"""
    pass

class MultiRegionStorageManager:
    """Manages data across multiple storage backends and regions"""
    
    def __init__(self):
        self.backends: Dict[str, StorageBackendInterface] = {
            'us-east-1': S3StorageBackend(region='us-east-1'),
            'eu-west-1': S3StorageBackend(region='eu-west-1'),
            'ap-southeast-1': S3StorageBackend(region='ap-southeast-1')
        }
        self.replication_policy = ReplicationPolicy()
    
    async def store_with_replication(
        self, 
        key: str, 
        data: bytes, 
        metadata: dict,
        organization_region: str
    ) -> MultiRegionStorageResult:
        """Store data in primary region and replicate per policy"""
        
        # Determine primary region (data residency)
        primary_region = self._determine_primary_region(organization_region)
        primary_backend = self.backends[primary_region]
        
        # Store in primary
        primary_result = await primary_backend.store(key, data, metadata)
        
        # Replicate to secondary regions if required
        replication_regions = self.replication_policy.get_replication_regions(
            primary_region, 
            metadata.get('data_classification', 'standard')
        )
        
        replicate_tasks = [
            self.backends[region].store(key, data, metadata)
            for region in replication_regions
        ]
        
        replication_results = await asyncio.gather(*replicate_tasks, return_exceptions=True)
        
        return MultiRegionStorageResult(
            primary=primary_result,
            replicas=[r for r in replication_results if not isinstance(r, Exception)],
            replication_status='COMPLETE' if all_successful(replication_results) else 'PARTIAL'
        )
```

---

## 5. COMPLIANCE AND GOVERNANCE LOGIC

### 5.1 robots.txt Checking Mechanism

```python
class RobotsTxtManager:
    def __init__(self, cache: Cache, http_client: HttpClient):
        self.cache = cache
        self.http = http_client
    
    async def can_fetch(self, url: str, user_agent: str) -> RobotsCheckResult:
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path or '/'
        
        # Get or fetch robots.txt
        parser = await self._get_parser(domain)
        
        if not parser:
            # No robots.txt found - default to allow with warning
            return RobotsCheckResult(
                allowed=True,
                crawl_delay=None,
                warning="No robots.txt found"
            )
        
        # Check specific path
        allowed = parser.can_fetch(user_agent, path)
        crawl_delay = parser.get_crawl_delay(user_agent)
        
        # Get matching rule for logging
        matching_rule = parser.get_matching_rule(user_agent, path)
        
        return RobotsCheckResult(
            allowed=allowed,
            crawl_delay=crawl_delay,
            matching_rule=matching_rule,
            full_parse=parser.to_dict()
        )
    
    async def _get_parser(self, domain: str) -> Optional[RobotsParser]:
        cache_key = f"robots_txt:{domain}"
        
        # Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            return RobotsParser.from_json(cached)
        
        # Fetch robots.txt
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            response = await self.http.get(robots_url, timeout=10)
            
            if response.status_code == 404:
                # No robots.txt - cache negative result
                await self.cache.set(cache_key, None, ttl=timedelta(hours=24))
                return None
            
            response.raise_for_status()
            
            # Parse robots.txt
            parser = RobotsParser.parse(response.text)
            
            # Cache parsed result
            await self.cache.set(
                cache_key, 
                parser.to_json(), 
                ttl=timedelta(hours=24)
            )
            
            return parser
            
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
            return None

class RobotsParser:
    """RFC-compliant robots.txt parser"""
    
    def __init__(self):
        self.rules: Dict[str, List[Rule]] = defaultdict(list)
        self.sitemaps: List[str] = []
        self.crawl_delays: Dict[str, float] = {}
    
    @classmethod
    def parse(cls, content: str) -> 'RobotsParser':
        parser = cls()
        lines = content.split('\n')
        current_agent = '*'
        
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse directive
            if ':' in line:
                directive, value = line.split(':', 1)
                directive = directive.strip().lower()
                value = value.strip()
                
                if directive == 'user-agent':
                    current_agent = value
                elif directive == 'disallow':
                    parser.rules[current_agent].append(
                        Rule(path=value, allowed=False)
                    )
                elif directive == 'allow':
                    parser.rules[current_agent].append(
                        Rule(path=value, allowed=True)
                    )
                elif directive == 'crawl-delay':
                    parser.crawl_delays[current_agent] = float(value)
                elif directive == 'sitemap':
                    parser.sitemaps.append(value)
        
        return parser
    
    def can_fetch(self, user_agent: str, path: str) -> bool:
        # Find matching user-agent (most specific wins)
        agents_to_check = [user_agent, '*']
        
        for agent in agents_to_check:
            if agent in self.rules:
                rules = self.rules[agent]
                
                # Rules are processed in order, last match wins
                allowed = True
                for rule in rules:
                    if self._path_matches(rule.path, path):
                        allowed = rule.allowed
                
                return allowed
        
        return True  # Default allow if no rules match
    
    def _path_matches(self, pattern: str, path: str) -> bool:
        """Check if path matches robots.txt pattern"""
        if pattern == '/':
            return path.startswith('/')
        return path.startswith(pattern)
```

### 5.2 PII Detection and Redaction

```python
class PIIDetector:
    """Multi-layer PII detection using regex, ML, and LLM"""
    
    def __init__(self):
        self.regex_patterns = self._load_regex_patterns()
        self.ml_model = self._load_ml_model()
        self.llm_client = OpenAIClient()
    
    def _load_regex_patterns(self) -> Dict[str, Pattern]:
        return {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone_us': re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
            'ssn': re.compile(r'\b(\d{3})[-\s]?(\d{2})[-\s]?(\d{4})\b'),
            'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            'ip_address': re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
            'passport_us': re.compile(r'\b[A-Z]{1}[0-9]{7,9}\b'),
            'ein': re.compile(r'\b\d{2}[-\s]?\d{7}\b'),
            'dob': re.compile(r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b'),
            'address': re.compile(r'\d+\s+([a-zA-Z]+\s*)+,(?:\s*[a-zA-Z]+,?)+\s*[A-Za-z]{2}\s*\d{5}(-\d{4})?'),
        }
    
    async def detect(
        self, 
        text: str, 
        methods: List[str] = ['regex', 'ml', 'llm']
    ) -> PIIDetectionResult:
        detections = []
        
        if 'regex' in methods:
            regex_detections = self._detect_with_regex(text)
            detections.extend(regex_detections)
        
        if 'ml' in methods:
            ml_detections = await self._detect_with_ml(text)
            detections.extend(ml_detections)
        
        if 'llm' in methods:
            llm_detections = await self._detect_with_llm(text)
            detections.extend(llm_detections)
        
        # Merge overlapping detections
        merged = self._merge_detections(detections)
        
        return PIIDetectionResult(
            detections=merged,
            total_count=len(merged),
            risk_score=self._calculate_risk_score(merged)
        )
    
    def _detect_with_regex(self, text: str) -> List[PIIDetection]:
        detections = []
        
        for pii_type, pattern in self.regex_patterns.items():
            for match in pattern.finditer(text):
                detections.append(PIIDetection(
                    type=pii_type,
                    start=match.start(),
                    end=match.end(),
                    value=match.group(),
                    confidence=0.9,
                    method='regex'
                ))
        
        return detections
    
    async def _detect_with_llm(self, text: str) -> List[PIIDetection]:
        """Use LLM for contextual PII detection"""
        
        prompt = f"""Analyze the following text for any Personally Identifiable Information (PII).
For each PII instance found, return:
- type: category of PII
- start: character position where PII starts
- end: character position where PII ends
- confidence: 0.0 to 1.0

Text to analyze:
{text[:4000]}

Return ONLY a JSON array of detections."""
        
        response = await self.llm_client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': prompt}],
            response_format={'type': 'json_object'}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return [
            PIIDetection(
                type=d['type'],
                start=d['start'],
                end=d['end'],
                confidence=d['confidence'],
                method='llm'
            )
            for d in result.get('detections', [])
        ]
    
    def redact(self, text: str, detections: List[PIIDetection]) -> str:
        """Redact detected PII from text"""
        
        # Sort by position (reverse to avoid offset issues)
        sorted_detections = sorted(detections, key=lambda d: d.start, reverse=True)
        
        redacted = text
        for detection in sorted_detections:
            redacted = (
                redacted[:detection.start] +
                f"[REDACTED:{detection.type}]" +
                redacted[detection.end:]
            )
        
        return redacted
```

### 5.3 Domain Allowlist Enforcement

```python
class DomainPolicyEnforcer:
    def __init__(self, policy_store: PolicyStore):
        self.policy_store = policy_store
    
    async def check_domain(self, url: str, organization_id: UUID) -> DomainCheckResult:
        domain = urlparse(url).netloc.lower()
        
        # Get organization policies
        policies = await self.policy_store.get_policies(organization_id)
        
        # Check blocklist first (always enforced)
        for blocked in policies.global_blocklist:
            if self._domain_matches(domain, blocked):
                return DomainCheckResult(
                    allowed=False,
                    reason=f"Domain matches global blocklist: {blocked}",
                    policy_type='BLOCKLIST',
                    action='BLOCK'
                )
        
        # Check organization blocklist
        for blocked in policies.organization_blocklist:
            if self._domain_matches(domain, blocked):
                return DomainCheckResult(
                    allowed=False,
                    reason=f"Domain matches organization blocklist: {blocked}",
                    policy_type='ORG_BLOCKLIST',
                    action='BLOCK'
                )
        
        # Check allowlist (if configured)
        if policies.domain_allowlist:
            allowed = any(
                self._domain_matches(domain, allowed)
                for allowed in policies.domain_allowlist
            )
            
            if not allowed:
                return DomainCheckResult(
                    allowed=False,
                    reason="Domain not in allowlist",
                    policy_type='ALLOWLIST',
                    action='BLOCK'
                )
        
        # Check category-based policies
        category = await self._classify_domain(domain)
        if category in policies.blocked_categories:
            return DomainCheckResult(
                allowed=False,
                reason=f"Domain category blocked: {category}",
                policy_type='CATEGORY',
                action='BLOCK'
            )
        
        # Check requires-review categories
        if category in policies.review_required_categories:
            return DomainCheckResult(
                allowed=True,
                reason=f"Domain requires review: {category}",
                policy_type='CATEGORY',
                action='REVIEW_REQUIRED'
            )
        
        return DomainCheckResult(
            allowed=True,
            reason="Domain policy check passed",
            policy_type='DEFAULT',
            action='ALLOW'
        )
    
    def _domain_matches(self, domain: str, pattern: str) -> bool:
        """Check if domain matches pattern (supports wildcards)"""
        
        # Exact match
        if domain == pattern:
            return True
        
        # Wildcard subdomain
        if pattern.startswith('*.'):
            suffix = pattern[2:]
            return domain == suffix or domain.endswith('.' + suffix)
        
        # Subdomain match
        if domain.endswith('.' + pattern):
            return True
        
        return False
```

### 5.4 Audit Logging

```python
class AuditLogger:
    def __init__(self, log_store: LogStore, event_bus: EventBus):
        self.log_store = log_store
        self.event_bus = event_bus
    
    async def log_event(self, event: AuditEvent):
        """Log audit event with guaranteed delivery"""
        
        # Enrich event with context
        enriched = await self._enrich_event(event)
        
        # Write to persistent storage
        await self.log_store.write(enriched)
        
        # Publish to event bus for real-time monitoring
        await self.event_bus.publish('audit.event', enriched)
        
        # Check for critical events requiring immediate notification
        if event.severity in ['ERROR', 'CRITICAL']:
            await self._alert_on_critical_event(enriched)
    
    async def log_scraping_request(
        self,
        job: ScrapingJob,
        request_details: RequestDetails
    ):
        event = AuditEvent(
            event_type='SCRAPING_REQUEST',
            timestamp=datetime.utcnow(),
            organization_id=job.organization_id,
            job_id=job.id,
            target_id=job.target_id,
            severity='INFO',
            details={
                'url': request_details.url,
                'method': request_details.method,
                'headers': self._sanitize_headers(request_details.headers),
                'proxy_used': request_details.proxy,
                'ip_address': request_details.source_ip
            }
        )
        
        await self.log_event(event)
    
    async def log_compliance_violation(
        self,
        violation_type: str,
        job: ScrapingJob,
        details: dict
    ):
        event = AuditEvent(
            event_type='COMPLIANCE_VIOLATION',
            timestamp=datetime.utcnow(),
            organization_id=job.organization_id,
            job_id=job.id,
            severity='ERROR',
            details={
                'violation_type': violation_type,
                'url': job.target.url,
                **details
            }
        )
        
        await self.log_event(event)
    
    async def log_data_retention_deletion(
        self,
        content_id: UUID,
        retention_policy: str,
        bytes_deleted: int
    ):
        event = AuditEvent(
            event_type='DATA_RETENTION_DELETION',
            timestamp=datetime.utcnow(),
            severity='INFO',
            details={
                'content_id': str(content_id),
                'retention_policy': retention_policy,
                'bytes_deleted': bytes_deleted,
                'deletion_reason': 'POLICY_EXPIRED'
            }
        )
        
        await self.log_event(event)
    
    def _sanitize_headers(self, headers: dict) -> dict:
        """Remove sensitive information from headers"""
        sensitive = ['authorization', 'cookie', 'x-api-key', 'x-auth-token']
        
        return {
            k: '[REDACTED]' if k.lower() in sensitive else v
            for k, v in headers.items()
        }
```

### 5.5 Data Retention Policy Enforcement

```python
class DataRetentionEnforcer:
    def __init__(self, storage: StorageManager, audit_logger: AuditLogger):
        self.storage = storage
        self.audit = audit_logger
    
    async def enforce_retention_policies(self):
        """Periodic job to enforce data retention policies"""
        
        # Find expired raw content
        expired_raw = await self._find_expired_raw_content()
        
        for content in expired_raw:
            await self._delete_raw_content(content)
        
        # Find expired screenshots
        expired_screenshots = await self._find_expired_screenshots()
        
        for screenshot in expired_screenshots:
            await self._delete_screenshot(screenshot)
        
        # Archive old extracted data (keep metadata, delete full content)
        archived_data = await self._find_data_for_archival()
        
        for data in archived_data:
            await self._archive_extracted_data(data)
    
    async def _delete_raw_content(self, content: RawContent):
        bytes_deleted = 0
        
        # Delete from S3
        for path in [content.storage.html_path, content.storage.dom_snapshot_path]:
            if path:
                size = await self.storage.get_size(path)
                await self.storage.delete(path)
                bytes_deleted += size
        
        # Update database record
        await self.db.execute('''
            UPDATE raw_content 
            SET storage = NULL, deleted_at = NOW(), deletion_reason = 'RETENTION_POLICY'
            WHERE id = $1
        ''', content.id)
        
        # Log deletion
        await self.audit.log_data_retention_deletion(
            content_id=content.id,
            retention_policy=f"{content.retention_policy.raw_content_expiry_days}_days",
            bytes_deleted=bytes_deleted
        )
```

---

## 6. DEPLOYMENT AND OPERATIONAL CONSIDERATIONS

### 6.1 Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION SERVICE ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────┐
│   API Gateway   │────▶│  Job Manager    │────▶│   Task Queue (Redis)    │
│   (REST/GraphQL)│     │  (FastAPI)      │     │   (Priority Queues)     │
└─────────────────┘     └─────────────────┘     └─────────────────────────┘
                               │                           │
                               ▼                           ▼
                       ┌─────────────────┐     ┌─────────────────────────┐
                       │  Target Config  │     │   Worker Pool (Celery)  │
                       │   (PostgreSQL)  │     │   (Auto-scaling)        │
                       └─────────────────┘     └─────────────────────────┘
                                                         │
                    ┌────────────────────────────────────┼────────────────────┐
                    ▼                                    ▼                    ▼
           ┌─────────────────┐               ┌─────────────────┐   ┌─────────────────┐
           │ Browser Pool    │               │ Compliance      │   │ LLM Provider    │
           │ (Browserbase)   │               │ Service         │   │ Router          │
           └─────────────────┘               └─────────────────┘   └─────────────────┘
                    │                                    │                    │
                    ▼                                    ▼                    ▼
           ┌─────────────────┐               ┌─────────────────┐   ┌─────────────────┐
           │ Raw Content     │               │ Audit Logs      │   │ Extracted Data  │
           │ Storage (S3)    │               │ (PostgreSQL)    │   │ (PostgreSQL/S3) │
           └─────────────────┘               └─────────────────┘   └─────────────────┘
```

### 6.2 Configuration Management

```yaml
# ingestion-service-config.yaml
service:
  name: value-fabric-ingestion
  version: 2.0.0
  environment: production

api:
  host: 0.0.0.0
  port: 8080
  workers: 4
  cors_origins:
    - https://app.valuefabric.io
  rate_limit:
    requests_per_minute: 1000

queue:
  backend: redis
  redis_url: redis://redis-cluster:6379/0
  job_queues:
    - name: high_priority
      priority: 10
    - name: default
      priority: 5
    - name: low_priority
      priority: 1

browser:
  provider: browserbase
  browserbase:
    project_id: ${BROWSERBASE_PROJECT_ID}
    api_key: ${BROWSERBASE_API_KEY}
  default_config:
    viewport:
      width: 1920
      height: 1080
    headless: true
    javascript_enabled: true
    stealth_mode: true

llm:
  providers:
    - name: openai
      api_key: ${OPENAI_API_KEY}
      models:
        - gpt-4o
        - gpt-4o-mini
      priority: 1
    - name: anthropic
      api_key: ${ANTHROPIC_API_KEY}
      models:
        - claude-3-5-sonnet
      priority: 2
  fallback_enabled: true
  timeout_seconds: 60

storage:
  raw_content:
    backend: s3
    bucket: vf-raw-content-${ENV}
    region: us-east-1
    retention_days: 30
  extracted_data:
    backend: s3
    bucket: vf-extracted-data-${ENV}
    region: us-east-1
    retention_days: 365
  database:
    url: ${DATABASE_URL}
    pool_size: 20

compliance:
  robots_txt:
    enabled: true
    cache_ttl_hours: 24
    strict_mode: false  # Allow if robots.txt fetch fails
  pii_detection:
    enabled: true
    methods:
      - regex
      - ml
    redaction_enabled: true
  domain_policy:
    enforce_allowlist: false
    global_blocklist:
      - *.gov  # Government sites
      - *.edu  # Educational institutions
      - known-malicious-domain.com

monitoring:
  metrics_enabled: true
  tracing_enabled: true
  log_level: INFO
  alert_channels:
    - type: pagerduty
      integration_key: ${PAGERDUTY_KEY}
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
```

---

## 7. SUMMARY

This specification document provides a comprehensive backend architecture for the Value Fabric platform's Intelligent Data Ingestion and Web Scraping layer. Key design decisions include:

1. **AI-Driven Extraction**: Primary use of multimodal LLMs for flexible, maintenance-free extraction
2. **Compliance by Design**: robots.txt respect, rate limiting, and PII redaction built into every stage
3. **Serverless Browser Infrastructure**: Leveraging Browserbase for scalable, managed browser automation
4. **Multi-Tier Storage**: Raw content, extracted data, and audit logs stored in appropriate backends
5. **Resilient Pipeline**: Comprehensive error handling with automatic retry and fallback mechanisms
6. **Ontology Integration**: Seamless publishing of extracted data to the Value Fabric ontology system

The architecture supports enterprise-scale operations with proper tenant isolation, resource fairness, and comprehensive audit trails.
