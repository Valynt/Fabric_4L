---
workflow_id: bunnyshell
name: Bunnyshell Environment Management
version: 1.0.0
description: Set up and manage Bunnyshell Environments as a Service for Value Fabric. Use when creating development, staging, or production environments, configuring environment templates, integrating Bunnyshell with existing infrastructure, or automating environment lifecycle management.
pattern: circuit-breaker
risk_level: low
---

# Bunnyshell Environment Management

Configure and manage Bunnyshell environments for the Value Fabric six-layer architecture. Bunnyshell provides on-demand creation of production-like environments with automatic tracking of source code changes and ephemeral PR environments.

## When to Use

- Setting up new development, staging, or production environments
- Configuring environment templates for Value Fabric layers
- Integrating Bunnyshell with existing Kubernetes clusters
- Automating environment creation for pull requests
- Managing environment lifecycle and costs
- Setting up remote development environments

## Bunnyshell Concepts

| Concept | Description | Value Fabric Application |
|---------|-------------|--------------------------|
| **Environment** | Full-stack environment with all services and dependencies | One environment per tenant or development branch |
| **Template** | Reusable environment configuration | Define templates for each layer (L1-L4) or full stack |
| **Component** | Individual service or resource in an environment | Layer services, databases, Redis, monitoring |
| **Trigger** | Event that creates/updates environments | Git push, PR creation, manual trigger |
| **Connector** | Integration with external services | GitHub, GitLab, Kubernetes clusters |

## Workflow Steps

### Step 1: Prepare Bunnyshell Account

1. Sign up at https://bunnyshell.com
2. Connect your cloud provider (AWS, GCP, Azure)
3. Connect your version control system (GitHub, GitLab, Bitbucket)
4. Verify account has necessary permissions for:
   - Kubernetes cluster access
   - Container registry access
   - DNS management (if using custom domains)

### Step 2: Define Environment Template

Choose a template type based on your use case:

**For Full Stack Value Fabric:**
- Use Docker Compose for local development
- Use Helm for production Kubernetes deployments
- Use Terraform for infrastructure provisioning

**Template Configuration:**
```yaml
# bunnyshell-template.yaml
name: value-fabric-full-stack
description: Complete Value Fabric six-layer environment
components:
  - name: layer1-ingestion
    type: service
    source: ./services/layer1-ingestion
    ports:
      - 8000:8000
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}

  - name: layer2-extraction
    type: service
    source: ./services/layer2-extraction
    depends_on:
      - layer1-ingestion

  - name: layer3-knowledge
    type: service
    source: ./services/layer3-knowledge
    depends_on:
      - layer2-extraction

  - name: postgres
    type: database
    engine: postgres
    version: 15
    environment:
      - POSTGRES_DB=${POSTGRES_DB}

  - name: redis
    type: cache
    engine: redis
    version: 7
```

### Step 3: Configure Triggers

Set up automatic environment creation:

**For Pull Request Environments:**
```yaml
triggers:
  - type: pull_request
    events:
      - opened
      - updated
      - reopened
    branches:
      - main
      - develop
    action: create_environment
    template: value-fabric-full-stack
    auto_destroy: true
    destroy_after: 7d
```

**For Branch-Based Environments:**
```yaml
triggers:
  - type: push
    branches:
      - feature/*
      - bugfix/*
    action: update_environment
    template: value-fabric-full-stack
```

### Step 4: Set Up Kubernetes Integration

If deploying to existing Kubernetes clusters:

1. Add cluster in Bunnyshell dashboard
2. Provide kubeconfig or service account credentials
3. Configure namespace isolation per environment
4. Set up resource quotas and limits:
   ```yaml
   resources:
     requests:
       cpu: "500m"
       memory: "512Mi"
     limits:
       cpu: "2000m"
       memory: "2Gi"
   ```

### Step 5: Configure Environment Variables

Set up environment-specific variables:

**Development:**
```yaml
environment:
  - LOG_LEVEL=debug
  - FEATURE_FLAGS=all
  - DATABASE_URL=${DEV_DATABASE_URL}
  - REDIS_URL=${DEV_REDIS_URL}
```

**Staging:**
```yaml
environment:
  - LOG_LEVEL=info
  - FEATURE_FLAGS=staging
  - DATABASE_URL=${STAGING_DATABASE_URL}
  - REDIS_URL=${STAGING_REDIS_URL}
```

**Production:**
```yaml
environment:
  - LOG_LEVEL=warn
  - FEATURE_FLAGS=production
  - DATABASE_URL=${PROD_DATABASE_URL}
  - REDIS_URL=${PROD_REDIS_URL}
  - SENTRY_DSN=${SENTRY_DSN}
```

### Step 6: Configure Monitoring and Observability

Integrate with existing monitoring stack:

```yaml
monitoring:
  prometheus:
    enabled: true
    scrape_interval: 15s
  logging:
    provider: loki
    enabled: true
  tracing:
    provider: jaeger
    enabled: true
```

### Step 7: Set Up Cost Controls

Configure budget limits and alerts:

```yaml
cost_management:
  monthly_budget: 500
  alerts:
    - threshold: 80%
      action: notify
    - threshold: 100%
      action: stop_environments
  auto_stop:
    idle_timeout: 2h
    schedule:
      - stop: "18:00"
        start: "09:00"
        timezone: "America/New_York"
```

### Step 8: Test Environment Creation

1. Create a test environment manually:
   ```bash
   bunnyshell env create --template value-fabric-full-stack --name test-env
   ```
2. Verify all components start successfully
3. Check service health endpoints
4. Run smoke tests against the environment
5. Verify database migrations apply correctly
6. Test inter-service communication

### Step 9: Configure Remote Development (Optional)

For remote development environments:

```yaml
remote_development:
  enabled: true
  ide: vscode
  sync:
    - ./services:/workspace/services
    - ./frontend:/workspace/frontend
  ports:
    - 3000:3000
    - 8000:8000
  command: dev
```

### Step 10: Set Up Integrations

Connect with external services:

**GitHub Integration:**
- Configure OAuth app
- Set up webhook for PR events
- Map GitHub branches to environments

**Slack Integration:**
- Set up notifications for environment events
- Configure channels for different environment types
- Enable approval workflows for production deployments

## Value Fabric Specific Configurations

### Layer 1 Ingestion
```yaml
components:
  - name: layer1-ingestion
    type: service
    replicas: 2
    health_check:
      path: /health
      interval: 30s
    resources:
      limits:
        cpu: "1000m"
        memory: "1Gi"
```

### Layer 2 Extraction
```yaml
components:
  - name: layer2-extraction
    type: service
    replicas: 3
    depends_on:
      - postgres
      - redis
    resources:
      limits:
        cpu: "2000m"
        memory: "2Gi"
```

### Layer 3 Knowledge
```yaml
components:
  - name: layer3-knowledge
    type: service
    replicas: 2
    depends_on:
      - postgres
      - neo4j  # if using Neo4j
    resources:
      limits:
        cpu: "1500m"
        memory: "2Gi"
```

### Layer 4 Agents
```yaml
components:
  - name: layer4-agents
    type: service
    replicas: 1
    depends_on:
      - layer3-knowledge
    resources:
      limits:
        cpu: "4000m"
        memory: "4Gi"
    environment:
      - AGENT_TIMEOUT=300
      - MAX_CONCURRENT_AGENTS=10
```

## CLI-Based Environment Launch

The Bunnyshell CLI (`bns`) provides programmatic control over environments and components. Use CLI for automation in CI/CD pipelines, scripts, and remote development workflows.

### Install CLI

```bash
# macOS
brew tap bunnyshell/tap
brew install bunnyshell

# Linux
curl -fsSL https://get.bunnyshell.com | sh

# Windows (via scoop)
scoop install bunnyshell

# Verify installation
bns version
```

### Configure CLI

```bash
# Interactive setup
bns configure

# Set API token
bns configure --api-token YOUR_API_TOKEN

# Use specific profile
bns --profile production environments list
```

### Launch Environment from Dockerfile

**Option 1: Using CLI with Docker Compose**

```bash
# Create environment from docker-compose.yml
bns environments create \
  --name value-fabric-dev \
  --template docker-compose \
  --source ./docker-compose.dev.yml \
  --project value-fabric

# Start the environment
bns environments start value-fabric-dev

# View components
bns components list --environment value-fabric-dev
```

**Option 2: Using CLI with Dockerfile directly**

```bash
# Create a component from Dockerfile
bns components create \
  --name layer1-ingestion \
  --type service \
  --source ./services/layer1-ingestion/Dockerfile \
  --environment value-fabric-dev \
  --port 8000

# Set environment variables for the component
bns variables set \
  --component layer1-ingestion \
  --environment value-fabric-dev \
  DATABASE_URL=postgresql://user:pass@postgres:5432/valuefabric \
  REDIS_URL=redis://redis:6379
```

### Remote Development via CLI

```bash
# Start remote development session
bns remote-development start \
  --environment value-fabric-dev \
  --component layer1-ingestion \
  --ide vscode

# Sync local changes to remote environment
bns git sync --environment value-fabric-dev

# Port forward to access local services
bns port-forward \
  --environment value-fabric-dev \
  --component layer1-ingestion \
  --local 8000 \
  --remote 8000

# Stop remote development
bns remote-development stop --environment value-fabric-dev
```

### CLI Environment Management

```bash
# List all environments
bns environments list

# List environments in a project
bns environments list --project value-fabric

# Get environment status
bns environments get value-fabric-dev

# Deploy changes to environment
bns environments deploy value-fabric-dev

# Stop environment
bns environments stop value-fabric-dev

# Delete environment
bns environments delete value-fabric-dev

# View environment events
bns environments events value-fabric-dev
```

### CLI Component Management

```bash
# List components in an environment
bns components list --environment value-fabric-dev

# Get component details
bns components get layer1-ingestion --environment value-fabric-dev

# View component logs
bns components logs layer1-ingestion --environment value-fabric-dev --follow

# Restart a component
bns components restart layer1-ingestion --environment value-fabric-dev

# Scale component replicas
bns components scale layer1-ingestion --environment value-fabric-dev --replicas 3
```

## API-Based Environment Launch

Use the Bunnyshell REST API for programmatic environment creation and management from any language or service.

### API Authentication

```bash
# Set API token as environment variable
export BUNNYSHELL_API_TOKEN=your_api_token_here

# Or pass in headers
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
  https://api.bunnyshell.com/v1/environments
```

### List Components via API

```bash
# List all components
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
  "https://api.bunnyshell.com/v1/components"

# Filter by environment
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
  "https://api.bunnyshell.com/v1/components?environment=value-fabric-dev"

# Filter by name
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
  "https://api.bunnyshell.com/v1/components?name=layer1-ingestion"

# Filter by operation status
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
  "https://api.bunnyshell.com/v1/components?operationStatus=running"
```

### Create Environment via API

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "value-fabric-dev",
    "projectId": "your-project-id",
    "templateId": "docker-compose-template",
    "source": {
      "type": "docker-compose",
      "repository": "https://github.com/your-org/value-fabric",
      "branch": "develop",
      "path": "./docker-compose.dev.yml"
    },
    "variables": {
      "LOG_LEVEL": "debug",
      "DATABASE_URL": "${DEV_DATABASE_URL}",
      "REDIS_URL": "${DEV_REDIS_URL}"
    }
  }' \
  https://api.bunnyshell.com/v1/environments
```

### Create Component via API

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "layer1-ingestion",
    "environmentId": "env-id",
    "type": "service",
    "source": {
      "type": "dockerfile",
      "repository": "https://github.com/your-org/value-fabric",
      "branch": "develop",
      "path": "./services/layer1-ingestion/Dockerfile",
      "context": "./services/layer1-ingestion"
    },
    "ports": [
      {
        "containerPort": 8000,
        "protocol": "TCP"
      }
    ],
    "resources": {
      "limits": {
        "cpu": "1000m",
        "memory": "1Gi"
      },
      "requests": {
        "cpu": "500m",
        "memory": "512Mi"
      }
    },
    "healthCheck": {
      "path": "/health",
      "intervalSeconds": 30,
      "timeoutSeconds": 5,
      "failureThreshold": 3
    }
  }' \
  https://api.bunnyshell.com/v1/components
```

### Deploy Environment via API

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "environmentId": "value-fabric-dev",
    "source": {
      "type": "docker-compose",
      "repository": "https://github.com/your-org/value-fabric",
      "branch": "feature/new-feature",
      "path": "./docker-compose.dev.yml"
    }
  }' \
  https://api.bunnyshell.com/v1/environments/value-fabric-dev/deploy
```

### Start/Stop Environment via API

```bash
# Start environment
curl -X POST \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  https://api.bunnyshell.com/v1/environments/value-fabric-dev/start

# Stop environment
curl -X POST \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  https://api.bunnyshell.com/v1/environments/value-fabric-dev/stop
```

## Value Fabric Dockerfile Launch Workflows

### Workflow 1: Launch Single Layer Development Environment

```bash
# Using CLI
bns environments create \
  --name layer1-dev \
  --project value-fabric \
  --source ./services/layer1-ingestion/Dockerfile \
  --port 8000 \
  --env DATABASE_URL=postgresql://localhost:5432/dev \
  --env LOG_LEVEL=debug

# Using API
curl -X POST \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "layer1-dev",
    "projectId": "value-fabric",
    "components": [{
      "name": "layer1-ingestion",
      "type": "service",
      "source": {
        "type": "dockerfile",
        "path": "./services/layer1-ingestion/Dockerfile"
      },
      "ports": [{"containerPort": 8000}]
    }]
  }' \
  https://api.bunnyshell.com/v1/environments
```

### Workflow 2: Launch Full Stack from Docker Compose

```bash
# Using CLI with existing docker-compose.dev.yml
bns environments create \
  --name value-fabric-full-dev \
  --project value-fabric \
  --template docker-compose \
  --source ./docker-compose.dev.yml \
  --auto-start

# Verify all components are running
bns components list --environment value-fabric-full-dev
```

### Workflow 3: Launch PR Environment

```bash
# Trigger via CLI on PR creation
PR_NUMBER=123
BRANCH=feature/new-feature

bns environments create \
  --name pr-${PR_NUMBER} \
  --project value-fabric \
  --source ./docker-compose.dev.yml \
  --branch ${BRANCH} \
  --auto-destroy \
  --destroy-after 7d \
  --env PR_NUMBER=${PR_NUMBER}
```

### Workflow 4: Remote Development Setup

```bash
# Start remote dev environment
bns environments create \
  --name remote-dev-$(whoami) \
  --project value-fabric \
  --source ./docker-compose.dev.yml \
  --remote-development true

# Start VS Code remote session
bns remote-development start \
  --environment remote-dev-$(whoami) \
  --component layer1-ingestion \
  --ide vscode

# Sync code
bns git sync --environment remote-dev-$(whoami)
```

## Verification Commands

```bash
# List all environments (CLI)
bns environments list

# Check environment status (CLI)
bns environments get value-fabric-dev

# View environment logs (CLI)
bns components logs layer1-ingestion --environment value-fabric-dev --follow

# Stop an environment (CLI)
bns environments stop value-fabric-dev

# Delete an environment (CLI)
bns environments delete value-fabric-dev

# List components via API
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
  "https://api.bunnyshell.com/v1/components?environment=value-fabric-dev"

# View cost report (CLI)
bns environments cost-report --month 2026-05
```

## Best Practices

- **Environment Isolation:** Use separate namespaces for each environment
- **Resource Limits:** Always set CPU and memory limits to prevent runaway costs
- **Auto-Destroy:** Configure ephemeral PR environments to auto-destroy after merge
- **Secrets Management:** Use Bunnyshell's secret manager or integrate with HashiCorp Vault
- **Database State:** Use separate databases per environment, never share between dev/staging/prod
- **Health Checks:** Configure health checks for all services to enable auto-recovery
- **Monitoring:** Enable monitoring for all environments, not just production
- **Cost Controls:** Set up budget alerts and auto-stop schedules for non-production environments

## Troubleshooting

**Environment fails to start:**
1. Check component logs: `bunnyshell env logs <env-id>`
2. Verify resource limits are sufficient
3. Check database connectivity
4. Verify environment variables are set correctly

**High costs:**
1. Review cost report: `bunnyshell cost report`
2. Enable auto-stop for idle environments
3. Reduce replica counts for non-production
4. Check for orphaned environments

**PR environments not creating:**
1. Verify webhook is configured in GitHub
2. Check trigger configuration in Bunnyshell
3. Review trigger logs for errors
4. Ensure template is valid

## See Also

- **Bunnyshell Documentation:** https://documentation.bunnyshell.com
- **Value Fabric Architecture:** `ARCHITECTURE.md`
- **Kubernetes Configuration:** `k8s/`
- **Docker Compose Dev:** `docker-compose.dev.yml`
- **Related Workflows:**
  - `/production_only_delivery` — Ensure production-grade code in all environments
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "bunnyshell-001",
  "files_touched": [],
  "tests_run": [],
  "decisions_made": [],
  "blocked_by": null,
  "retry_count": 0,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

## Circuit Breaker Configuration

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

## Completion Checklist

- [ ] State JSON updated with current stage, touched files, tests, and decisions.
- [ ] Circuit breaker evaluated before retrying after tool errors or self-correction loops.
- [ ] Relevant validation commands run and recorded in the workflow state.
- [ ] No security, tenant-isolation, contract, governance, or frontend-design assertions weakened.
