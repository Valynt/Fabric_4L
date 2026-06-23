# Layer 2.5 Signal Refinery

Layer 2.5 normalizes Layer 2 extraction output into trusted, evidence-backed
`ValueSignal` objects for downstream graph, agent, and ground-truth workflows.

The service preserves tenant context, provenance, evidence references, and
confidence metadata while preparing signals for Layer 3 knowledge graph storage
and Layer 4 agent consumption.

## Implementation Status

Implemented. Key entry points:

- API: `src/layer2_5_signal_refinery/api/main.py`
- Signal routes: `src/layer2_5_signal_refinery/api/routes/signals.py`
- Refinery logic: `src/layer2_5_signal_refinery/services/signal_refinery.py`
- Database models: `src/layer2_5_signal_refinery/models/db_models.py`
- Migrations: `src/layer2_5_signal_refinery/migrations/`

## Local Setup

Install this service through the repository setup target:

```bash
make setup
```

Run its focused tests from the service directory or via the root command map:

```bash
python -m pytest services/layer2-5-signal-refinery/tests -v --tb=short
```
