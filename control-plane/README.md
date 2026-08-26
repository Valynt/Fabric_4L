# Fabric_4L Control Plane

The control plane turns Fabric_4L from one giant codebase that agents and humans must understand
globally into a **governed, behavior-oriented system with progressive disclosure**.

It is a repository control plane connecting:

**Product intent -> behavior -> architecture -> implementation -> tests -> security/governance
controls -> evidence -> release authorization.**

## The system in one picture

```text
                    HUMAN / AGENT ENTRY POINT
                              |
                    handbook/INDEX.md
                              |
             +----------------+----------------+
             |                                 |
       Product Contract                  Architecture
       VP / GAP / R rules             System topology
       (product-contract/)            (architecture/)
             |                                 |
             +---------------+-----------------+
                             |
                    Behavior being changed
                    (behaviors/BEH-xx)
                             |
                   Progressive disclosure
                             |
                L1: System / Domain      (handbook/L1-system/)
                             |
                L2: Components involved  (handbook/L2-components/)
                             |
                L3: Functions / state /
                    APIs / code anchors  (handbook/L3-implementation/)
                             |
                       Implementation
                             |
                         Verification
                             |
                Release Control Register
                  (release/control_register.yaml)
                             |
                     Test + Evidence
                             |
                 RELEASE_AUTHORIZED
                       or BLOCKED
```

## What lives here

| Directory | Question it answers |
|---|---|
| `product-contract/` | What MUST the product do? (intent, users, lifecycle, journey, UX, stories VP-xx, engineering contract, DoD, gaps GAP-xx) |
| `architecture/` | How is the system shaped? (L1 system map, boundaries, adapter policy) |
| `behaviors/` | What behavior am I changing? (BEH-xx cards — the unit of navigation) |
| `release/` | What must pass, how is it proven, what is valid proof, who decides? (control register, test strategy, evidence schema, evaluator) |
| `contract_manifest.yaml` | Machine-readable linker connecting all of the above through stable IDs |

## The rules of the plane

1. **The behavior is the unit of navigation, not the directory.** Start at `behaviors/`, not at
   `services/`.
2. **Intent overrides implementation.** A mismatch between code and `product-contract/` is a
   tracked gap (GAP-xx), not an alternate interpretation.
3. **References are machine-resolvable.** Every ID (VP-xx, GAP-xx, R-n, J-n, BEH-xx, AG-0x,
   CTRL-xx-nn, EV-x) is defined once and checked by
   `scripts/control-plane/validate_control_plane.py`.
4. **Release decisions are computed, not narrated.** `release/evaluator.md` defines how evidence
   bound to an exact SHA and artifact digest produces RELEASE_AUTHORIZED or BLOCKED.
5. **This layer is derived from reality.** Anchors point at real paths; CI drift checks fail when
   anchors go stale or behavior ships undocumented.

## Companion: `handbook/`

`handbook/` is the consolidated AI workspace (replacing the scattered `.claude/`, `.kimi/`,
`.roo/`, ... context dirs) with stage-specific guidance:
`01_understand -> 02_design -> 03_implement -> 04_verify`. Start there if you are an agent.
