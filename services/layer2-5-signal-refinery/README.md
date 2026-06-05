# Layer 2.5 Signal Refinery

Layer 2.5 normalizes Layer 2 extraction output into trusted, evidence-backed
`ValueSignal` objects for downstream graph, agent, and ground-truth workflows.

The service preserves tenant context, provenance, evidence references, and
confidence metadata while preparing signals for Layer 3 knowledge graph storage
and Layer 4 agent consumption.

## Local Setup

Install this service through the repository setup target:

```bash
make setup
```

Run its focused tests from the service directory or via the root command map:

```bash
python -m pytest services/layer2-5-signal-refinery/tests -v --tb=short
```
