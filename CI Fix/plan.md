# Fabric_4L CI Remediation Swarm — plan.md

Goal: remediate verified CI failures in bmsull560/Fabric_4L, validate locally, produce one apply-ready unified git patch (full-index, binary-safe, no prose wrapper).

## Stage 0 — Setup & Discovery (orchestrator + explore agents)
- Load skill: vibecoding-general-swarm (+ swarm-workspace if needed)
- Clone repo to /mnt/agents/work/Fabric_4L
- Inventory: .github/workflows/**, pyproject.toml(s), lockfiles, package.json/pnpm workspace, Jest/Babel/Vitest configs, Dockerfiles, Helm charts, route audit config, OpenAPI generators, conftest.py, runtime docs
- Confirm each of the 16 failure classes against current checkout; drop stale ones
- Output: evidence-backed defect map with file ownership per worker A–H

## Stage 1 — P0 fixes (parallel coder workers, disjoint file ownership)
- A. Workflow/dependency env: canonical locked deps in workflows, PyYAML, pytest, mypy stubs
- B. Docker & workspace topology: frontend Dockerfile workspace drift, Corepack pnpm, Python 3.14→3.13/3.12 alignment (spaCy pins)
- Layer2 auth fixture (FABRIC_AUTH_PUBLIC_KEYS test-only public material)
- Layer3 OpenAPI import topology fix
Stage-gate: each worker validates narrowest checks before handoff.

## Stage 2 — P1 fixes
- C. Jest/Babel/Istanbul alignment (Babel 7 pin), run ESLint plugin suite
- Schemathesis CLI pin or invocation update
- D. Layer 4 Ruff fixes (16 errors)
- F. Coverage tests (frontend 77.41→81%, Layer5 76→80%) — meaningful assertions only, best effort
- E. OpenAPI docs gaps + route audit (35 findings, evidence-based owners)

## Stage 3 — P2 fixes
- G. Helm dep build for Trivy; Bandit triage (targeted fixes, no blanket nosec); Infisical OIDC gating
- H. Aggregate gate diagnostics + env reproducibility metadata

## Stage 4 — Validation & Patch (worker I + reviewer)
- Full validation matrix (YAML lint, ruff, mypy, pytest collection, OpenAPI gen, route audit, docker builds if daemon available, helm render, git diff --check)
- Reviewer subagent runs PATCH REVIEW CHECKLIST
- Orchestrator generates: git add -N && git diff --binary --full-index --no-ext-diff > final.patch
- Deliver patch file + patch in final response
