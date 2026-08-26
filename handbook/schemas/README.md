# handbook/schemas/ — Control-plane JSON Schemas

Machine-readable contracts (JSON Schema, draft 2020-12) for the Fabric_4L
control plane. These schemas are the enforcement layer for the ID scheme and
cross-reference rules described in `handbook/INDEX.md` and
`control-plane/README.md`.

## Files

| File | Validates |
| --- | --- |
| `contract_manifest.schema.json` | `control-plane/contract_manifest.yaml` — the hub artifact linking rules (R-x), stories (VP-xx), gaps (GAP-xx), journey stages (J-x), behaviors (BEH-xx), gates (AG-xx), and controls (CTRL-xx-nn). |
| `behavior_card.schema.json` | The YAML frontmatter embedded at the top of every behavior card under `control-plane/behaviors/BEH-xx-*.md`. |

## How the schemas are used in CI

The validator `scripts/control-plane/validate_control_plane.py` runs on every
pull request and performs the following:

1. **Manifest validation.** `control-plane/contract_manifest.yaml` is loaded
   and validated against `contract_manifest.schema.json` (via the `jsonschema`
   package when installed; otherwise structural checks — required keys and ID
   regexes — are performed manually). This enforces ID patterns
   (`R-\d+`, `VP-\d{2}`, `GAP-\d{2}`, `J-\d+`, `BEH-\d{2}`, `AG-\d{2}`,
   `CTRL-\d{2}-\d{2}`) and required fields such as `id`/`name` on behaviors,
   the `card` path on behaviors, and the `blocks` enum
   (`merge|release|promotion`) on controls.

2. **Behavior card frontmatter validation.** For every behavior listed in the
   manifest, the validator verifies the card file exists, extracts its YAML
   frontmatter, checks the frontmatter `id` matches the manifest entry, and
   (when `jsonschema` is available) validates the frontmatter against
   `behavior_card.schema.json`.

3. **Cross-reference integrity.** The validator collects every ID defined in
   the manifest plus the class-defining files
   (`control-plane/release/control_register.yaml` for CTRL/AG/EV, the
   `control-plane/product-contract/` files for VP/GAP/R/J, and
   `control-plane/behaviors/` for BEH), then scans all markdown under
   `control-plane/` and `handbook/`. Any ID-looking token that is referenced
   but not defined anywhere fails the build.

4. **Evidence records.** Proof artifacts submitted for release controls are
   validated against `control-plane/release/evidence_schema.json` (owned by
   the release plane, not this directory). Every `EV-x` evidence type
   referenced from controls or cards must exist there.

## Running locally

```bash
pip install pyyaml jsonschema   # pyyaml required; jsonschema recommended
python scripts/control-plane/validate_control_plane.py
```

Exit code `0` means the control plane is internally consistent; non-zero
prints the full violation list.

## Future work (not yet enforced)

- **Stale-anchor checks.** Verify that repo anchors (path + symbol) cited in
  behavior cards still exist in the codebase.
- **Undocumented-behavior checks.** Detect components touched by a PR that are
  not covered by any behavior card, and require a card update.
