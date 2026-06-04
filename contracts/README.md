# Contracts

This directory is the **source of truth** for all interfaces in Value Fabric.

## Structure

```
contracts/
  tool-manifests/   JSON Schema definitions for every agent tool/skill
  openapi/          Generated OpenAPI specs per layer (do not hand-edit — run `make contracts`)
  jsonschema/       Shared data model schemas (entities, events, API payloads)
  deprecations/     Approved contract deprecation records consumed by breaking-change gates
  rfcs/             Contract Council RFC records, including approved breaking-change plans
```

## Rules

1. **Tool manifests are authoritative.** The JSON Schema in `tool-manifests/` defines the accepted
   input and output shape for every agent skill. The implementation in
   `services/layer4-agents/src/tools/` must conform to these schemas.

2. **OpenAPI specs are generated.** Run `make contracts` to regenerate them from the live FastAPI
   apps. Do not edit files in `openapi/` by hand.

3. **Changes to tool manifests require skill updates.** If you change a schema in `tool-manifests/`,
   update the corresponding `layer4-agents/skills/<name>.md` and implementation.

4. **OpenAPI breaking-change checks replace buf breaking.** This repo is OpenAPI/REST, not Protobuf/gRPC, so run `pnpm contract:breaking` to compare current OpenAPI specs against the baseline branch. The gate writes JSON and Markdown reports under `reports/contracts/` and fails unless breaking findings are covered by an approved RFC or deprecation record.

5. **Contract tests live in `tests/contract/`.** They verify that the running services honour
   the schemas declared here.

## Adding a new tool manifest

See [`AGENTS.md`](../AGENTS.md) → "How to add a new agent skill".
