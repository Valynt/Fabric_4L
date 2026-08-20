# Skill Registry

Read this file first. Full `SKILL.md` contents load only when a skill's
triggers match the current task. Machine-readable equivalent:
`skills/_manifest.jsonl`.

## skillforge
Creates new skills from observed patterns and recurring tasks.
Triggers: "create skill", "new skill", "I keep doing this manually"

## memory-manager
Reads, scores, and consolidates memory. Runs reflection cycles.
Triggers: "reflect", "what did I learn", "compress memory"

## git-proxy
All git operations with safety constraints.
Triggers: "commit", "push", "branch", "merge", "rebase"
Constraints: never force push to main; run tests before push.

## debug-investigator
Systematic debugging: reproduce, isolate, hypothesize, verify.
Triggers: "debug", "why is this failing", "investigate"

## deploy-checklist
Pre-deployment verification against a structured checklist.
Triggers: "deploy", "ship", "release", "go live"
Constraints: all tests passing, no unresolved TODOs in diff,
requires human approval for production.

## data-layer
Cross-harness activity monitoring and dashboard exports. Use it as the
injected dashboard surface when users ask naturally.
Triggers: "data layer", "dashboard", "show me the dashboard",
"what did my agents do", "agent analytics", "agent status", "resource usage",
"usage report", "cron monitoring", "daily report", "tokens",
"terminal dashboard", "TUI"
Constraints: local-only by default; no screenshot delivery without explicit user
approval; do not commit private `.agent/data-layer/` exports.

## data-flywheel
Turns approved, redacted runs into reusable local artifacts: trace records,
context cards, eval cases, training-ready JSONL, and flywheel metrics.
Triggers: "data flywheel", "trace to train", "training traces",
"context cards", "eval cases", "approved runs", "vertical intelligence"
Constraints: local-only by default; human-approved runs only; redaction required
before trainable; does not train models.

## design-md
Uses a root `DESIGN.md` as the portable visual system contract for
Google Stitch workflows. Loads only when `DESIGN.md` exists at the
project root.
Triggers: "DESIGN.md", "design.md", "Google Stitch", "design tokens",
"design system", "visual design"
Preconditions: DESIGN.md exists at project root.
Constraints: prefer DESIGN.md tokens over invented values, do not modify
DESIGN.md unless the user explicitly asks, preserve unknown sections when
an edit IS authorised, validate with `npx @google/design.md lint DESIGN.md`
when available.

## tldraw
Draw, diagram, sketch, or lay out ideas on a live tldraw canvas.
Worthwhile drawings snapshot into this skill's local store
(`skills/tldraw/store.py`) for recall across sessions.
Triggers: "draw", "diagram", "sketch", "wireframe", "flowchart",
"mind-map", "visualize", "whiteboard"
Constraints: get_canvas before edits; max 200 shapes per create_shape call.
Requires: tldraw MCP server wired in the harness's MCP config; user has
http://localhost:3030 open. Opt-in via `.features.json` (`tldraw: true`).

## source-intelligence
Layer 1 reasoning procedure for transforming raw company materials into structured, provenance-backed intelligence. Drives licensing-company ontology intake and prospect research.
Triggers: "source intelligence", "ingest company", "research prospect", "build corpus", "account intelligence", "licensing company intake", "prospect research", "ontology seed"
Constraints: do not replace downstream layer logic, always preserve source provenance, emit events only after successful storage, never finalize strategic conclusions in Layer 1

## code-quality-improvement
Focused production-quality pass for functional code with concrete quality gaps.
Triggers: "code quality improvement", "refine code", "quality gaps",
"code health", "production-grade", "polish implementation", "maintainability"
Constraints: fix P0 before P1; keep changes narrowly scoped; preserve contracts
and tenant isolation; use Windows-safe searches that exclude cache directories;
verify changed behavior.

## saas-product-design
Core competencies for building scalable, high-retention multi-tenant SaaS products, focusing on architecture, onboarding, navigation, and modern UI design.
Triggers: "SaaS", "multi-tenant", "onboarding", "navigation", "dashboard", "UI design", "accessibility", "AI integration", "tenant isolation", "Time-to-Value", "TTV", "command palette", "dark mode", "WCAG"
Constraints: prioritize tenant data isolation, enforce tenant-aware authorization, target sub-5-minute TTV, use interactive walkthroughs over static tours, implement command palette for power users, apply calm design principles, prepare for WCAG 3.0 compliance, integrate AI as invisible infrastructure

## context7-mcp
Fetches current documentation, code examples, and API references for libraries and frameworks directly from Context7.
Triggers: "context7", "docs", "documentation", "library reference", "framework docs", "api reference"
Constraints: query per concept, resolve library ID before fetching, prefer official sources

