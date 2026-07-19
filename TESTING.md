# Testing Index

This root index exists for discoverability only. Keep detailed testing policy,
commands, and behavior-readiness requirements in the canonical documentation.

## Canonical references

- [Test suite guide](tests/README.md) — test layout, marker reference, and local execution notes.
- [Development command map](docs/development/COMMANDS.md) — source of truth for public `make`, `pnpm`, and Python validation commands.
- [Behavior-first testing governance](docs/governance/behavior-first-testing.md) — behavior-readiness ladder, skip discipline, and production-readiness expectations.
- [Behavior readiness waivers](config/ci/behavior_readiness_waivers.yaml) — time-boxed exceptions consumed by readiness checks.

## Expected validation

Use the narrowest relevant command first, then broaden through the command map.
For release or readiness claims, follow the behavior-readiness ladder in the
canonical governance document rather than duplicating it here.
