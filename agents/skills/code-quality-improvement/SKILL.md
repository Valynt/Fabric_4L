---
name: code-quality-improvement
version: 2026-06-25
triggers: ["code quality improvement", "refine code", "quality gaps", "code health", "production-grade", "polish implementation", "maintainability"]
tools: [bash, git]
preconditions: []
constraints: ["fix P0 before P1", "keep changes narrowly scoped", "preserve contracts and tenant isolation", "use Windows-safe searches that exclude cache directories", "verify changed behavior"]
category: engineering
---

# Code Quality Improvement

Use this skill when functional code needs a focused production-quality pass. The goal is not broad refactoring; it is to remove concrete correctness, completeness, fragility, maintainability, accessibility, or performance risks in the smallest safe change.

## Procedure

1. Locate the canonical source files, layer boundary, contracts, and tests before editing.
2. Read the touched implementation and nearby tests.
3. Classify findings:
   - P0: incorrect behavior, failed validation, missing safety checks.
   - P1: production fragility, unsafe error handling, tenant/security risk.
   - P2: maintainability issues that slow future work or obscure behavior.
   - P3: polish and performance issues with low behavioral risk.
4. Fix P0 before P1, and P1 before P2/P3.
5. Add or update tests for changed behavior. For security-sensitive paths, include denied/hostile cases.
6. Run the narrowest relevant validation first, then broaden only when the change risk requires it.

## Windows-Safe Search

Prefer `rg` and exclude generated/cache directories:

```bash
rg -n "pattern" services tests scripts --glob "!.pytest_cache/**" --glob "!__pycache__/**" --glob "!node_modules/**"
```

If `grep` is the only available fallback, search explicit source roots rather than `.` and exclude cache directories where the shell supports it. Do not treat permission errors from generated pytest cache directories as code findings; rerun the search with explicit excludes.

## Validation Examples

```bash
python -m pytest path/to/relevant/tests
pnpm --dir apps/web run test
pnpm --dir apps/web run build
make verify
```

Record exactly what ran. If validation is blocked, report the command, failure mode, and residual risk.

## Self-Rewrite Hook

If a repeated quality issue appears across multiple runs, update this skill with a narrow checklist for that issue class and a concrete validation command.

