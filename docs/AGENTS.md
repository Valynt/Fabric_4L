# Documentation agent guidance

Documentation under `docs/` is organized using Diátaxis:

- tutorials for learning,
- how-to guides for completing tasks,
- reference for stable commands and contracts,
- explanations for architecture and decisions.

## Source-of-truth rules

- Keep command and build guidance in [`development/COMMANDS.md`](development/COMMANDS.md) and [`development/BUILD_SYSTEM.md`](development/BUILD_SYSTEM.md).
- Route implementation work through [`development/DISCOVERY_MAP.md`](development/DISCOVERY_MAP.md).
- Put security and tenant-isolation guidance in [`security/`](security/), testing guidance in [`testing/`](testing/), and operational or release guidance in [`operations/`](operations/) and [`launch/`](launch/).
- Keep cross-layer implementation rules in [`../packages/platform-contract/CONTRACT.md`](../packages/platform-contract/CONTRACT.md).
- Record architectural decisions in [`explanations/adr/`](explanations/adr/) or [`decisions/`](decisions/), and update their registries when required.
- Do not treat generated reports, archived evidence, or compatibility snapshots as active policy unless a canonical document explicitly references them.

## Documentation changes

Use existing canonical locations instead of creating parallel status documents. Update navigation or indexes when adding a public document, preserve front matter conventions, and run `pnpm docs:check` (or `python -m pytest tests/docs/`) for documentation changes.

The repository-wide agent entry point is [`../AGENTS.md`](../AGENTS.md); this file adds documentation-specific guidance only.
