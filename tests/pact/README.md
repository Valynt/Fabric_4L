# Pact Contract Tests

Consumer-driven contract tests for Fabric_4L using [pact-python](https://github.com/pact-foundation/pact-python).

## Overview

| File | Purpose |
|------|---------|
| `test_l4_consumer_contract.py` | Frontend consumer expectations against Layer 4 mock provider; generates `.pact` files |
| `test_l4_provider_verify.py` | Replays consumer contracts against the real Layer 4 API |
| `conftest.py` | Shared Pact fixtures (pact directory, provider URL, broker config) |

## Prerequisites

```bash
# Install pact-python and test deps
pip install -r tests/requirements.txt
```

## Running Locally

### 1. Consumer tests (standalone, no services needed)

Generates the pact contract file under `pacts/`:

```bash
pytest tests/pact/test_l4_consumer_contract.py -v
```

Output: `pacts/value-fabric-frontend-layer4-agents-api.json`

### 2. Provider verification (requires Layer 4 running)

Start the Layer 4 service first:

```bash
# Option A: Docker Compose stack
docker compose -f docker-compose.dev.yml up layer4-agents

# Option B: Direct (from repo root)
python -m services.layer4-agents.src.main
```

Then run provider verification:

```bash
pytest tests/pact/test_l4_provider_verify.py -v
```

Or use the Makefile target:

```bash
make pact-tests
```

## CI Integration

### Consumer contract publishing

After consumer tests pass, publish the generated pact to a Pact Broker:

```bash
pact-broker publish pacts/ \
    --consumer-app-version=$(git rev-parse HEAD) \
    --branch=$(git rev-parse --abbrev-ref HEAD) \
    --broker-base-url=$PACT_BROKER_URL \
    --broker-token=$PACT_BROKER_TOKEN
```

### Provider verification in CI

Set `CONTRACT_TEST_ENFORCE=1` (or run in CI) to fail closed when the provider is unreachable.

```bash
export CONTRACT_TEST_ENFORCE=1
pytest tests/pact/test_l4_provider_verify.py -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LAYER4_API_URL` | `http://localhost:8004` | Layer 4 provider base URL |
| `PACT_DIR` | `repo_root/pacts` | Where pact files are written/read |
| `PACT_BROKER_URL` | — | Pact Broker URL for publishing/fetching |
| `PACT_BROKER_TOKEN` | — | Token for authenticated broker access |
| `CONTRACT_TEST_ENFORCE` | `0` | Fail instead of skip when provider is unreachable |

## Current Contract Coverage

### Layer 4 Agents API (`layer4-agents-api`)

| Endpoint | Method | State | Verified |
|----------|--------|-------|----------|
| `/` | GET | `service is running` | ✅ |
| `/billing/plans/{plan_id}/limits` | GET | `pro plan exists` | ✅ |
| `/billing/plans/{plan_id}/limits` | GET | `unknown plan requested` (404) | ✅ |

## Adding New Consumer Expectations

1. Add a new test method in `test_l4_consumer_contract.py`
2. Use the builder pattern:
   ```python
   (consumer_pact
    .given("some provider state")
    .upon_receiving("a request for ...")
    .with_request("GET", "/new-endpoint")
    .will_respond_with(200, body={"key": "value"}))
   ```
3. Run consumer tests to regenerate the pact file
4. Run provider verification to confirm the real API satisfies the new expectation

## Troubleshooting

**`Pact file not found` in provider verification**
→ Run consumer tests first to generate the `.pact` file.

**`Layer 4 provider unreachable` skip**
→ Start the Layer 4 service before running provider verification.

**Port conflicts with Pact mock provider**
→ pact-python picks an ephemeral port automatically; no manual configuration needed.
