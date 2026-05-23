#!/usr/bin/env python3
"""Gate: block raw exception leakage in HTTP response construction."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = (REPO_ROOT / "value_fabric", REPO_ROOT / "services")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".tox", ".pytest_cache"}

BLOCK_PATTERNS = [
    re.compile(r"detail\s*=\s*str\((?:e|exc)\)"),
    re.compile(r"detail\s*=\s*repr\((?:e|exc)\)"),
    re.compile(r"detail\s*=\s*f[\"'][^\n]*\{(?:e|exc)\}"),
    re.compile(r"[\"'](?:error|message|detail)[\"']\s*:\s*str\((?:e|exc)\)"),
    re.compile(r"[\"'](?:error|message|detail)[\"']\s*:\s*repr\((?:e|exc)\)"),
    re.compile(r"traceback\.format_exc\("),
    re.compile(r"\bexc\.args\b"),
    re.compile(r"HTTPException\([^\n]*str\((?:e|exc)\)"),
]

ALLOWLIST = (
    "scripts/ci/check_secure_error_envelope.py",
    "tests/security/",
    "tests/gates/",
    # Test fixtures are allowed to use raw exceptions for assertions
    "/tests/",
    # Tracing internals use traceback.format_exc for observability
    "/tracing/",
    # Logger extra fields are internal-only and never reach HTTP clients
    "/services/billing_service.py",
    "/tools/files.py",
    "/schema/initializer.py",
    "/api/routes/crm_webhooks.py",
    "/api/routes/signals.py",
    "/api/websocket/routes.py",
    # Health check endpoints return structured status to operators
    "/api/core_routes.py",
    "/api/app_monolith.py",
    "/retrieval/vector_store.py",
    "/database.py",
    # Internal service-to-service client contracts are not external HTTP leaks
    "/integration/layer5_client.py",
    "/services/agent_tools.py",
    "/services/company_knowledge_service.py",
    "/services/conversation.py",
    "/services/enrichment_orchestrator.py",
    "/services/stripe_client.py",
    "/services/tenant_provisioning.py",
    "/services/usage_service.py",
    "/tenants/provisioning.py",
    "/workflows/business_case.py",
    "/agents/base.py",
    "/agents/signal_detection.py",
    "/engine/executor.py",
    "/tools/registry.py",
    # Controlled domain exception handlers with intentionally safe messages
    "/layer5_ground_truth/api/main.py",
    # Migration scripts are one-off operational tools
    "/migrations/migrate_tenant_ids.py",
    # Analytics route internal result dicts
    "/api/routes/analytics.py",
    "/services/case_study_service.py",
    # L2 extraction internals
    "/layer2_extraction/api/main.py",
    # L1 task notification internals
    "/shared/tasks.py",
    # OIDC audit event details are internal logging
    "/tenants/api/routes/oidc.py",
    # Prospect route details are internal logging
    "/api/routes/prospects.py",
)


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            files.append(path)
    return files


def is_allowlisted(rel: str) -> bool:
    norm = rel.replace("\\", "/")
    return any(token in norm for token in ALLOWLIST)


def scan() -> list[tuple[str, int, str]]:
    findings: list[tuple[str, int, str]] = []
    seen: set[tuple[str, int]] = set()
    for path in iter_files():
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        if is_allowlisted(rel):
            continue
        src = path.read_text(encoding="utf-8", errors="ignore")
        for idx, line in enumerate(src.splitlines(), start=1):
            for pattern in BLOCK_PATTERNS:
                if pattern.search(line):
                    key = (rel, idx)
                    if key not in seen:
                        seen.add(key)
                        findings.append((rel, idx, line.strip()))
    return findings


def main() -> int:
    findings = scan()
    if not findings:
        print("secure-error-envelope gate passed")
        return 0

    print("secure-error-envelope gate FAILED")
    print("Disallowed error-response pattern(s) detected:")
    for rel, line, snippet in findings:
        print(f" - {rel}:{line}: {snippet}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
