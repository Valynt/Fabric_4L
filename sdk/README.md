# Fabric 4L SDKs

> **Official client libraries** for the Fabric 4L platform API  
> **Version:** 1.2.0  
> **License:** MIT  
> **Support:** api@fabric4l.io | `#api-support` on Slack

---

## Table of Contents

- [Overview](#overview)
- [Python SDK](#python-sdk)
  - [Installation](#python-installation)
  - [Quick Start](#python-quick-start)
  - [Authentication](#python-authentication)
  - [Per-Layer Usage](#python-per-layer-usage)
  - [Error Handling](#python-error-handling)
- [TypeScript SDK](#typescript-sdk)
  - [Installation](#typescript-installation)
  - [Quick Start](#typescript-quick-start)
  - [Authentication](#typescript-authentication)
  - [Per-Layer Usage](#typescript-per-layer-usage)
  - [Error Handling](#typescript-error-handling)
- [Layer Reference](#layer-reference)
- [Versioning](#versioning)
- [Contributing](#contributing)

---

## Overview

The Fabric 4L SDK provides typed, idiomatic client libraries for all six layers of the Fabric 4L platform:

| Layer | Python Package | TypeScript Package | Description |
|-------|---------------|-------------------|-------------|
| L1 — Ingress Gateway | `fabric4l-l1-gateway` | `@fabric4l/sdk-l1-gateway` | Route management, rate limiting |
| L2 — AuthN/AuthZ | `fabric4l-l2-auth` | `@fabric4l/sdk-l2-auth` | Authentication & authorization |
| L3 — Core Services | `fabric4l-l3-core` | `@fabric4l/sdk-l3-core` | Business logic & workflows |
| L4 — Compute Engine | `fabric4l-l4-compute` | `@fabric4l/sdk-l4-compute` | Async jobs & ML inference |
| L5 — Data Access | `fabric4l-l5-data` | `@fabric4l/sdk-l5-data` | Queries, cache, search |
| L6 — Observability | `fabric4l-l6-observability` | `@fabric4l/sdk-l6-observability` | Metrics, logs, traces |

All SDKs are **auto-generated** from OpenAPI 3.1 specifications and kept in sync with the platform via CI/CD.

---

## Python SDK

### Python Installation

```bash
# Install all layer SDKs
pip install "fabric4l[all]"

# Or install individual layers
pip install fabric4l-l1-gateway
pip install fabric4l-l2-auth
pip install fabric4l-l3-core

# With optional features
pip install fabric4l-l3-core[async]   # Async support
```

**Requirements:** Python 3.9+

### Python Quick Start

```python
"""Fabric 4L Python SDK — Quick Start Example"""

from fabric4l_l3_core import Configuration, ApiClient
from fabric4l_l3_core.api import workflows_api
from fabric4l_l3_core.model.workflow_create_request import WorkflowCreateRequest

# 1. Configure API client
config = Configuration(
    host="https://api.fabric4l.io/v1",
    api_key={"ApiKeyAuth": "your-api-key"},
)

# 2. Create client context
with ApiClient(config) as client:
    # 3. Instantiate API
    api = workflows_api.WorkflowsApi(client)

    # 4. Create a workflow
    request = WorkflowCreateRequest(
        name="etl-pipeline",
        description="Daily ETL pipeline for analytics",
        steps=[
            {"type": "extract", "source": "postgres"},
            {"type": "transform", "rules": ["normalize", "dedupe"]},
            {"type": "load", "destination": "warehouse"},
        ],
    )

    workflow = api.create_workflow(request)
    print(f"Created workflow: {workflow.id} — {workflow.name}")
    print(f"Status: {workflow.status}")
```

### Python Authentication

```python
"""Authentication patterns for Fabric 4L Python SDK."""

from fabric4l_l2_auth import Configuration

# ── API Key ─────────────────────────────────────────────────────────────────
config = Configuration(
    host="https://api.fabric4l.io/v1",
    api_key={"ApiKeyAuth": "fab_test_dummy_example_key"},
)

# ── Bearer Token (JWT) ──────────────────────────────────────────────────────
config = Configuration(
    host="https://api.fabric4l.io/v1",
    access_token="YOUR_ACCESS_TOKEN",
)

# ── OAuth2 Client Credentials ───────────────────────────────────────────────
from fabric4l_l2_auth.api import auth_api

config = Configuration(host="https://api.fabric4l.io/v1")
auth = auth_api.AuthApi(ApiClient(config))
token = auth.token_post(
    grant_type="client_credentials",
    client_id="your-client-id",
    client_secret="your-client-secret",
)
config.access_token = token.access_token

# ── Multiple Auth (Layer traversal) ─────────────────────────────────────────
from fabric4l_l1_gateway import Configuration as L1Config
from fabric4l_l3_core import Configuration as L3Config

# Each layer SDK has its own config — share the token
shared_token = "YOUR_SHARED_TOKEN"

l1_config = L1Config(host="https://l1.fabric4l.io", access_token=shared_token)
l3_config = L3Config(host="https://l3.fabric4l.io", access_token=shared_token)
```

### Python Per-Layer Usage

```python
"""Layer-specific SDK usage examples."""

from fabric4l_l1_gateway import Configuration as L1Config, ApiClient as L1Client
from fabric4l_l1_gateway.api import routes_api

from fabric4l_l4_compute import Configuration as L4Config, ApiClient as L4Client
from fabric4l_l4_compute.api import jobs_api
from fabric4l_l4_compute.model.job_submit_request import JobSubmitRequest

from fabric4l_l5_data import Configuration as L5Config, ApiClient as L5Client
from fabric4l_l5_data.api import queries_api

# ── L1: Ingress Gateway ─────────────────────────────────────────────────────
l1_config = L1Config(host="https://l1.fabric4l.io/v1")
with L1Client(l1_config) as client:
    routes = routes_api.RoutesApi(client)

    # List all routes
    all_routes = routes.list_routes()
    for route in all_routes.items:
        print(f"  {route.method} {route.path} → {route.target}")

    # Create a new route
    new_route = routes.create_route({
        "path": "/api/v2/analytics",
        "method": "POST",
        "target": "https://l3.fabric4l.io/v2/analytics",
        "rate_limit": 1000,
    })

# ── L4: Compute Engine ──────────────────────────────────────────────────────
l4_config = L4Config(host="https://l4.fabric4l.io/v1")
with L4Client(l4_config) as client:
    jobs = jobs_api.JobsApi(client)

    # Submit a batch job
    job_request = JobSubmitRequest(
        name="model-inference-batch",
        type="inference",
        model_id="sentiment-v2",
        inputs=[{"text": "Great product!"}, {"text": "Needs improvement"}],
    )
    job = jobs.submit_job(job_request)
    print(f"Job submitted: {job.id} (status: {job.status})")

    # Poll for completion
    import time
    while job.status in ("queued", "running"):
        time.sleep(5)
        job = jobs.get_job(job.id)
        print(f"  Status: {job.status} ({job.progress}%)")

    print(f"Job completed: {job.result}")

# ── L5: Data Access ─────────────────────────────────────────────────────────
l5_config = L5Config(host="https://l5.fabric4l.io/v1")
with L5Client(l5_config) as client:
    queries = queries_api.QueriesApi(client)

    # Execute a query
    result = queries.execute_query({
        "collection": "events",
        "filter": {"status": "completed", "created_at": {"$gte": "2025-01-01"}},
        "sort": [{"created_at": "desc"}],
        "limit": 100,
    })
    print(f"Query returned {result.count} records")

    # Search
    search = queries_api.SearchApi(client)
    hits = search.fulltext_search({
        "index": "documents",
        "query": "machine learning deployment",
        "fields": ["title", "content"],
        "limit": 10,
    })
    for hit in hits.results:
        print(f"  [{hit.score:.2f}] {hit.title}")
```

### Python Error Handling

```python
"""Error handling patterns for Fabric 4L Python SDK."""

from fabric4l_l3_core import ApiException
from urllib3.exceptions import MaxRetryError

# ── Basic error handling ────────────────────────────────────────────────────
from fabric4l_l3_core.api import workflows_api

try:
    workflow = api.get_workflow("wf-nonexistent")
except ApiException as e:
    if e.status == 404:
        print(f"Workflow not found: {e.body}")
    elif e.status == 401:
        print("Authentication failed — check your API key")
    elif e.status == 429:
        print("Rate limited — retry after delay")
    elif e.status >= 500:
        print(f"Server error: {e.status} — {e.reason}")
    else:
        print(f"API error: {e.status} — {e.body}")

# ── Retry with exponential backoff ──────────────────────────────────────────
import time
import random

def with_retry(func, max_retries=3, base_delay=1.0):
    """Call func with exponential backoff on 429/5xx errors."""
    for attempt in range(max_retries):
        try:
            return func()
        except ApiException as e:
            if e.status == 429 or e.status >= 500:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Max retries exceeded")

# Usage
workflow = with_retry(lambda: api.get_workflow("wf-123"))

# ── Timeout configuration ───────────────────────────────────────────────────
from fabric4l_l3_core import Configuration

config = Configuration(
    host="https://api.fabric4l.io/v1",
    api_key={"ApiKeyAuth": "your-key"},
)
# Set timeout on the underlying urllib3 client
config.connection_pool_maxsize = 10

# ── Pagination ──────────────────────────────────────────────────────────────
def list_all_workflows(api):
    """Iterate through all workflows with automatic pagination."""
    page = 1
    while True:
        result = api.list_workflows(page=page, per_page=100)
        yield from result.items
        if not result.has_more:
            break
        page += 1

for wf in list_all_workflows(api):
    print(f"  {wf.id}: {wf.name}")
```

---

## TypeScript SDK

### TypeScript Installation

```bash
# Using npm
npm install @fabric4l/sdk-l3-core @fabric4l/sdk-l1-gateway

# Using yarn
yarn add @fabric4l/sdk-l3-core @fabric4l/sdk-l1-gateway

# Using pnpm
pnpm add @fabric4l/sdk-l3-core @fabric4l/sdk-l1-gateway

# Install all layers
npm install @fabric4l/sdk-l1-gateway @fabric4l/sdk-l2-auth @fabric4l/sdk-l3-core \
           @fabric4l/sdk-l4-compute @fabric4l/sdk-l5-data @fabric4l/sdk-l6-observability
```

**Requirements:** TypeScript 5.0+, Node.js 18+

### TypeScript Quick Start

```typescript
/**
 * Fabric 4L TypeScript SDK — Quick Start Example
 */

import {
  Configuration,
  WorkflowsApi,
  WorkflowCreateRequest,
} from "@fabric4l/sdk-l3-core";

// 1. Configure API client
const config = new Configuration({
  basePath: "https://api.fabric4l.io/v1",
  apiKey: "fab_test_dummy_example_key",
});

// 2. Instantiate API
const workflowsApi = new WorkflowsApi(config);

// 3. Create a workflow
const request: WorkflowCreateRequest = {
  name: "etl-pipeline",
  description: "Daily ETL pipeline for analytics",
  steps: [
    { type: "extract", source: "postgres" },
    { type: "transform", rules: ["normalize", "dedupe"] },
    { type: "load", destination: "warehouse" },
  ],
};

async function main() {
  try {
    const workflow = await workflowsApi.createWorkflow(request);
    console.log(`Created workflow: ${workflow.id} — ${workflow.name}`);
    console.log(`Status: ${workflow.status}`);
  } catch (error) {
    console.error("Failed to create workflow:", error);
  }
}

main();
```

### TypeScript Authentication

```typescript
/**
 * Authentication patterns for Fabric 4L TypeScript SDK.
 */

import { Configuration } from "@fabric4l/sdk-l2-auth";

// ── API Key ─────────────────────────────────────────────────────────────────
const config = new Configuration({
  basePath: "https://api.fabric4l.io/v1",
  apiKey: (name: string) => {
    if (name === "ApiKeyAuth") return "fab_test_dummy_example_key";
    return undefined;
  },
});

// ── Bearer Token (JWT) ──────────────────────────────────────────────────────
const config = new Configuration({
  basePath: "https://api.fabric4l.io/v1",
  accessToken: "YOUR_ACCESS_TOKEN",
});

// ── OAuth2 Client Credentials ───────────────────────────────────────────────
import { AuthApi } from "@fabric4l/sdk-l2-auth";

const authConfig = new Configuration({ basePath: "https://api.fabric4l.io/v1" });
const authApi = new AuthApi(authConfig);

const token = await authApi.tokenPost({
  grantType: "client_credentials",
  clientId: "your-client-id",
  clientSecret: "your-client-secret",
});

const config = new Configuration({
  basePath: "https://api.fabric4l.io/v1",
  accessToken: token.accessToken,
});

// ── Request interceptor (for dynamic tokens) ────────────────────────────────
import { Configuration, Middleware, RequestContext, ResponseContext } from "@fabric4l/sdk-l3-core";

const authMiddleware: Middleware = {
  pre(context: RequestContext): Promise<RequestContext> {
    const token = getTokenFromCache(); // Your token refresh logic
    context.setHeaderParam("Authorization", `Bearer ${token}`);
    return Promise.resolve(context);
  },
  post(context: ResponseContext): Promise<ResponseContext> {
    return Promise.resolve(context);
  },
};

const config = new Configuration({
  basePath: "https://api.fabric4l.io/v1",
  middleware: [authMiddleware],
});
```

### TypeScript Per-Layer Usage

```typescript
/**
 * Layer-specific SDK usage examples.
 */

// ── L1: Ingress Gateway ─────────────────────────────────────────────────────
import { RoutesApi, Configuration as L1Config } from "@fabric4l/sdk-l1-gateway";

const l1Config = new L1Config({ basePath: "https://l1.fabric4l.io/v1" });
const routesApi = new RoutesApi(l1Config);

// List all routes
const routes = await routesApi.listRoutes();
for (const route of routes.items) {
  console.log(`  ${route.method} ${route.path} → ${route.target}`);
}

// Create a route
const newRoute = await routesApi.createRoute({
  path: "/api/v2/analytics",
  method: "POST",
  target: "https://l3.fabric4l.io/v2/analytics",
  rateLimit: 1000,
});

// ── L4: Compute Engine ──────────────────────────────────────────────────────
import { JobsApi, Configuration as L4Config, JobSubmitRequest } from "@fabric4l/sdk-l4-compute";

const l4Config = new L4Config({ basePath: "https://l4.fabric4l.io/v1" });
const jobsApi = new JobsApi(l4Config);

// Submit a job
const jobRequest: JobSubmitRequest = {
  name: "model-inference-batch",
  type: "inference",
  modelId: "sentiment-v2",
  inputs: [{ text: "Great product!" }, { text: "Needs improvement" }],
};

const job = await jobsApi.submitJob(jobRequest);
console.log(`Job submitted: ${job.id} (status: ${job.status})`);

// Poll with async/await
const pollJob = async (jobId: string): Promise<void> => {
  let status = job.status;
  while (status === "queued" || status === "running") {
    await new Promise((r) => setTimeout(r, 5000));
    const updated = await jobsApi.getJob(jobId);
    status = updated.status;
    console.log(`  Status: ${status} (${updated.progress}%)`);
  }
  console.log(`Job completed`);
};

await pollJob(job.id);

// ── L5: Data Access ─────────────────────────────────────────────────────────
import { QueriesApi, SearchApi, Configuration as L5Config } from "@fabric4l/sdk-l5-data";

const l5Config = new L5Config({ basePath: "https://l5.fabric4l.io/v1" });
const queriesApi = new QueriesApi(l5Config);
const searchApi = new SearchApi(l5Config);

// Execute query
const result = await queriesApi.executeQuery({
  collection: "events",
  filter: { status: "completed", created_at: { $gte: "2025-01-01" } },
  sort: [{ created_at: "desc" }],
  limit: 100,
});
console.log(`Query returned ${result.count} records`);

// Full-text search
const hits = await searchApi.fulltextSearch({
  index: "documents",
  query: "machine learning deployment",
  fields: ["title", "content"],
  limit: 10,
});
for (const hit of hits.results) {
  console.log(`  [${hit.score.toFixed(2)}] ${hit.title}`);
}
```

### TypeScript Error Handling

```typescript
/**
 * Error handling patterns for Fabric 4L TypeScript SDK.
 */

import { ResponseError } from "@fabric4l/sdk-l3-core";

// ── Basic error handling ────────────────────────────────────────────────────
try {
  const workflow = await workflowsApi.getWorkflow("wf-nonexistent");
} catch (error) {
  if (error instanceof ResponseError) {
    const status = error.response.status;
    const body = await error.response.json();

    switch (status) {
      case 404:
        console.error(`Workflow not found: ${body.message}`);
        break;
      case 401:
        console.error("Authentication failed — check your API key");
        break;
      case 429:
        console.error("Rate limited — retry after delay");
        break;
      case 500:
      case 502:
      case 503:
        console.error(`Server error: ${status} — ${body.message}`);
        break;
      default:
        console.error(`API error: ${status} — ${JSON.stringify(body)}`);
    }
  } else {
    console.error("Network or client error:", error);
  }
}

// ── Retry with exponential backoff ──────────────────────────────────────────
async function withRetry<T>(
  fn: () => Promise<T>,
  options: { maxRetries?: number; baseDelay?: number } = {}
): Promise<T> {
  const { maxRetries = 3, baseDelay = 1000 } = options;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (error instanceof ResponseError) {
        const status = error.response.status;
        if (status === 429 || status >= 500) {
          const delay = baseDelay * 2 ** attempt + Math.random() * 1000;
          console.warn(`Retry ${attempt + 1}/${maxRetries} after ${delay}ms`);
          await new Promise((r) => setTimeout(r, delay));
          continue;
        }
      }
      throw error; // Non-retryable error
    }
  }
  throw new Error("Max retries exceeded");
}

// Usage
const workflow = await withRetry(() => workflowsApi.getWorkflow("wf-123"));

// ── AbortController for cancellation ────────────────────────────────────────
const controller = new AbortController();

// Cancel after 10 seconds
const timeout = setTimeout(() => controller.abort(), 10000);

try {
  const result = await queriesApi.executeQuery(
    { collection: "events", limit: 1000 },
    { signal: controller.signal }
  );
  console.log(`Query returned ${result.count} records`);
} catch (error) {
  if (error.name === "AbortError") {
    console.log("Request was cancelled");
  } else {
    throw error;
  }
} finally {
  clearTimeout(timeout);
}

// ── Pagination helper ───────────────────────────────────────────────────────
async function* listAllWorkflows(api: WorkflowsApi) {
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const result = await api.listWorkflows(page, 100);
    yield* result.items;
    hasMore = result.hasMore;
    page++;
  }
}

// Usage
for await (const workflow of listAllWorkflows(workflowsApi)) {
  console.log(`  ${workflow.id}: ${workflow.name}`);
}
```

---

## Layer Reference

### Service Endpoints

| Layer | Base URL (Python) | Base URL (TypeScript) | OpenAPI Spec |
|-------|-------------------|----------------------|--------------|
| L1 | `https://l1.fabric4l.io/v1` | `https://l1.fabric4l.io/v1` | `contracts/openapi/l1-gateway.openapi.json` |
| L2 | `https://l2.fabric4l.io/v1` | `https://l2.fabric4l.io/v1` | `contracts/openapi/l2-auth.openapi.json` |
| L3 | `https://l3.fabric4l.io/v1` | `https://l3.fabric4l.io/v1` | `contracts/openapi/l3-core.openapi.json` |
| L4 | `https://l4.fabric4l.io/v1` | `https://l4.fabric4l.io/v1` | `contracts/openapi/l4-compute.openapi.json` |
| L5 | `https://l5.fabric4l.io/v1` | `https://l5.fabric4l.io/v1` | `contracts/openapi/l5-data.openapi.json` |
| L6 | `https://l6.fabric4l.io/v1` | `https://l6.fabric4l.io/v1` | `contracts/openapi/l6-observability.openapi.json` |

### Environment-Specific URLs

```typescript
// TypeScript environment config
const ENVIRONMENTS = {
  development: {
    l1: "http://localhost:8001/v1",
    l2: "http://localhost:8002/v1",
    l3: "http://localhost:8003/v1",
    l4: "http://localhost:8004/v1",
    l5: "http://localhost:8005/v1",
    l6: "http://localhost:8006/v1",
  },
  staging: {
    l1: "https://staging-l1.fabric4l.io/v1",
    l2: "https://staging-l2.fabric4l.io/v1",
    l3: "https://staging-l3.fabric4l.io/v1",
    l4: "https://staging-l4.fabric4l.io/v1",
    l5: "https://staging-l5.fabric4l.io/v1",
    l6: "https://staging-l6.fabric4l.io/v1",
  },
  production: {
    l1: "https://l1.fabric4l.io/v1",
    l2: "https://l2.fabric4l.io/v1",
    l3: "https://l3.fabric4l.io/v1",
    l4: "https://l4.fabric4l.io/v1",
    l5: "https://l5.fabric4l.io/v1",
    l6: "https://l6.fabric4l.io/v1",
  },
} as const;
```

---

## Versioning

The Fabric 4L SDKs follow [Semantic Versioning](https://semver.org/):

| SDK Version | API Version | Compatibility |
|-------------|-------------|---------------|
| 1.2.0 | 1.2.0 | Full |
| 1.1.x | 1.1.x | Full |
| 1.0.x | 1.0.x | Full |

**Upgrade Policy:**
- **Patch releases** (1.2.0 → 1.2.1): Bug fixes only, drop-in replacement
- **Minor releases** (1.2.x → 1.3.0): New features, backward compatible
- **Major releases** (1.x → 2.0.0): Breaking changes, migration guide provided

**Deprecation Timeline:**
- Features marked deprecated: 6 months notice
- Deprecated features removed: next major version
- End-of-life: announced 12 months in advance

---

## Contributing

### Regenerating SDKs

```bash
# Install prerequisites
npm install -g @openapitools/openapi-generator-cli

# Generate all SDKs
python scripts/generate-sdks.py --all

# Generate specific language
python scripts/generate-sdks.py --language python
python scripts/generate-sdks.py --language typescript

# Validate specs without generating
python scripts/generate-sdks.py --validate-only
```

### SDK Structure

```
sdk/
├── README.md                          # This file
├── python/
│   ├── pyproject.toml                 # Python monorepo config
│   ├── fabric4l-l1-gateway/           # L1 SDK
│   ├── fabric4l-l2-auth/              # L2 SDK
│   ├── fabric4l-l3-core/              # L3 SDK
│   ├── fabric4l-l4-compute/           # L4 SDK
│   ├── fabric4l-l5-data/              # L5 SDK
│   └── fabric4l-l6-observability/     # L6 SDK
└── typescript/
    ├── package.json                   # TypeScript workspace config
    ├── tsconfig.json                  # Shared TypeScript config
    ├── fabric4l-l1-gateway/           # L1 SDK
    ├── fabric4l-l2-auth/              # L2 SDK
    ├── fabric4l-l3-core/              # L3 SDK
    ├── fabric4l-l4-compute/           # L4 SDK
    ├── fabric4l-l5-data/              # L5 SDK
    └── fabric4l-l6-observability/     # L6 SDK
```

### Support

- **Issues:** [GitHub Issues](https://github.com/fabric-4l/fabric-4l/issues)
- **Email:** api@fabric4l.io
- **Slack:** `#api-support`
- **Documentation:** https://docs.fabric4l.io

---

*Generated by Fabric 4L SDK Generator v1.2.0*
