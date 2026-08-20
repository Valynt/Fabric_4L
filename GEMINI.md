# Project Instructions for Gemini CLI

## Project Context

This repository should be treated as production-grade software.

Before editing:

- Read the relevant files.
- Identify existing conventions.
- Search for tests.
- Prefer compatibility-preserving changes.
- Avoid broad rewrites.

## Architecture Rules

- Respect existing module boundaries.
- Do not introduce new dependencies without justification.
- Do not edit generated files manually.
- Do not return fake production data.
- Do not add hardcoded secrets.
- Do not create no-op security or safety implementations.
- Fail closed for security, tenant isolation, money, workflow, and governance paths.

## Frontend Rules

- React components should consume domain/view models, not raw API DTOs.
- Keep DTO-to-domain mapping in adapters.
- Validate network responses before using them.
- Avoid `any`.

## Backend Rules

- FastAPI routes should use explicit request/response models.
- Pydantic DTOs define API contracts.
- Use clear HTTP errors instead of silent fallback behavior.
- Preserve trace IDs, tenant IDs, and audit metadata.

## Execution Style

For each task:

1. Inspect.
2. Plan briefly.
3. Patch narrowly.
4. Test.
5. Report changed files, validation run, and remaining risks.

<!-- context7 -->
Use Context7 MCP to fetch current documentation whenever the user asks about a library, framework, SDK, API, CLI tool, or cloud service — even well-known ones like React, Next.js, Prisma, Express, Tailwind, Django, or Spring Boot. This includes API syntax, configuration, version migration, library-specific debugging, setup instructions, and CLI tool usage. Use even when you think you know the answer — your training data may not reflect recent changes. Prefer this over web search for library docs.

Do not use for: refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

## Steps

1. Always start with `resolve-library-id` using the library name and what to look up in the library's documentation, unless the user provides an exact library ID in `/org/project` format
2. Pick the best match (ID format: `/org/project`) by: exact name match, description relevance, code snippet count, source reputation (High/Medium preferred), and benchmark score (higher is better). If results don't look right, try alternate names or queries (e.g., "next.js" not "nextjs", or rephrase the question). Use version-specific IDs when the user mentions a version
3. `query-docs` with the selected library ID and what to look up in the library's documentation (not single words), scoped to a single concept. If the question spans multiple distinct concepts (e.g. routing and auth and caching), make a separate `query-docs` call per concept with the same library ID, unless the question is about how the concepts interact — combined queries dilute ranking and return shallow results for each topic
4. Answer using the fetched docs
<!-- context7 -->
