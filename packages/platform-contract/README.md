# Value Fabric Platform Contract

Cross-layer contract definitions and test harness.

## Contents

- \`src/python/canonical/\` — Canonical Python contract types
- \`src/typescript/generated/\` — Generated TypeScript contract types
- Test harnesses for contract drift detection

## Usage

Used by CI gates (\`make contract-tests\`) and by service implementations to
ensure request/response shapes remain compatible across layers.
