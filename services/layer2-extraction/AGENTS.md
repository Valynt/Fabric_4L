# AGENTS — services/layer2-extraction (L2, port 8002)

Scoped instructions; universal rules live in the root `AGENTS.md`.

## Responsibility

Ontology-guided extraction (Pydantic v2), LLM extraction, RDF/OWL generation,
provenance, batch ingest. Do not move logic across layers.

## Canonical runtime path

`services/layer2-extraction/src/layer2_extraction/` — all net-new logic lands
here (see `docs/reference/layer-runtime-path-governance.md`). API routes:
`services/layer2-extraction/src/layer2_extraction/api/routes/`.

## Layer rules

- Preserve ontology-guided extraction; use Pydantic v2 patterns.
- Preserve provenance; maintain RDF/OWL compatibility where applicable.
- Do not emit unstructured blobs where structured entities are expected.
- Extraction jobs carry verified tenant context and fail closed without it.

## Validation

```bash
make test-layer2
make lint-layer2
make typecheck-layer2
```
