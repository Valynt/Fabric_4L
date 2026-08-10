# Value Fabric Python SDK

[![PyPI](https://img.shields.io/pypi/v/valuefabric)](https://pypi.org/project/valuefabric/)

Python SDK and CLI for the [Value Fabric](https://github.com/bmsull560/Fabric_4L) Layer 4 Agentic Workflow Engine.

## Installation

```bash
pip install valuefabric
```

## Quick Start

### Python SDK

```python
from valuefabric import ValueFabricClient

# Authenticate with an API key
client = ValueFabricClient(
    base_url="https://api.valuefabric.io",
    api_key="vf_your_api_key",
)

# List tenants
for tenant in client.list_tenants():
    print(tenant.name)

# Invite a user
user = client.invite_user("alice@example.com", role="analyst")
print(user.id)

# Execute a workflow
result = client.execute_workflow(
    workflow_type="roi_calculator",
    tenant_id="tenant-001",
    user_id="user-001",
)
print(result["workflow_instance_id"])
```

### JWT Authentication

```python
client = ValueFabricClient(
    base_url="https://api.valuefabric.io",
    jwt_token="eyJhbG...",
)
```

### Async Support

All SDK methods have an async counterpart prefixed with `a`:

```python
import asyncio

async def main():
    async with ValueFabricClient(base_url="...", api_key="...") as client:
        tenants = await client.alist_tenants()
        print(tenants)

asyncio.run(main())
```

## CLI

Install the SDK to get the `vf` command:

```bash
# Configure credentials
vf config set-url https://api.valuefabric.io
vf config set-api-key vf_your_api_key

# Health check
vf health

# List tenants
vf tenants list

# Invite a user
vf users invite alice@example.com --role analyst

# Execute a workflow
vf workflows execute roi_calculator --tenant-id t1 --user-id u1

# List feature flags
vf feature-flags list

# Search entities (hybrid: BM25 + vector + graph)
vf search "AI platform" --limit 5

# Search with entity type filter
vf search "machine learning" --type Capability

# Get JSON output
vf tenants list --json
vf search "query" --json
```

### ValuePact CLI preview

The SDK also ships a Click-based `valuepact` binary for tenant-safe ValuePact
operations from terminals and automation. It is an application adapter: protected
commands call authenticated ValuePact APIs, verify tenant access through the
identity boundary, bind an immutable execution context, and reset that context
after success or failure.

Credentials are not stored in the ordinary CLI config file. Provide service
account credentials through a protected environment variable:

```bash
export VALUEPACT_SERVICE_TOKEN="..."
export VALUEPACT_API_URL="https://api.valuepact.ai"
```

Store non-secret context preferences:

```bash
valuepact context use \
  --profile acme-staging \
  --tenant-id tenant_123 \
  --environment staging \
  --api-url https://api.staging.valuepact.ai
```

Context resolution order is explicit command options, environment variables,
active named profile, then validation error. Tenant selection is not
authorization; protected commands still verify the authenticated actor against
the requested tenant.

```bash
valuepact auth login --api-url https://api.valuepact.ai
valuepact auth status
valuepact context show --json
valuepact workspace list --json
valuepact workspace execute --workspace-id workspace_456 --input request.json --yes --json
valuepact execution status exec_789 --json
valuepact audit list --since 24h --json
valuepact doctor --json
valuepact completion
```

Operational commands support a stable JSON envelope:

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "tenant_id": "tenant_123",
    "environment": "staging",
    "request_id": "req_...",
    "actor_id": "svc_123",
    "actor_type": "service_account"
  }
}
```

Errors use stable symbolic codes and exit codes. Authentication failures exit
`3`, authorization denials exit `4`, domain failures exit `5`, not-found errors
exit `6`, retryable infrastructure failures exit `7`, and unexpected internal
failures exit `8`.

## Generated Clients

The SDK includes auto-generated clients from OpenAPI specifications:

```python
from valuefabric.generated import L3Client, L4Client
from valuefabric.generated.l3 import SearchRequest

# L3 Knowledge Graph client
l3 = L3Client(base_url="http://localhost:8001", api_key="your-key")
response = l3.search(SearchRequest(query="AI platform"))

# L4 Agents client
l4 = L4Client(base_url="http://localhost:8000", api_key="your-key")
health = l4.health()
```

## Regenerating from OpenAPI

```bash
cd sdk/python
python scripts/generate_from_openapi.py
```

## Development

```bash
cd sdk/python
pip install -e ".[dev]"
pytest
```

## License

See the repository root `LICENSE` file.
