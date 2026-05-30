#!/usr/bin/env python3
"""Production stub/synthetic-value scanner.

Fails CI if banned placeholder strings, hardcoded fallbacks, or synthetic
value patterns are present in production source paths.  Test files, generated
code, and documentation are excluded by default.

To add an intentional exception, update ALLOWLIST below with a
human-readable justification.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path

# Patterns that must not appear in production source code.
# Not every match is automatically bad, but each requires explicit review.
BANNED_PATTERNS: list[str] = [
    "CHANGE-ME",
    "TODO production",
    'return content  # in safety guard',
    "base64.urlsafe_b64encode",
    "total_value: 500000",
    "roi_ratio: 1.5",
    "crm_value_",
    "benchmark_value_",
    "ground_truth_value_",
    'success: True  # near enrichment fallback',
    "mock_persistence=True",
    "seed_demo_data=True",
    'llm_provider="mock"',
]

# Specific file:line allowlist with mandatory justification.
# Format: "path:relative/to/repo:line_number"
ALLOWLIST: dict[str, str] = {
    # Tests are allowed to use mock values and synthetic fixtures
    "tests:tests/security/test_rbac.py:322": "Intentional JWT alg=none attack simulation in security test",
    "tests:tests/security/test_rbac.py:323": "Intentional JWT alg=none attack simulation in security test",
    "tests:tests/security/test_rbac.py:340": "Intentional algorithm confusion attack simulation in security test",
    "tests:tests/security/test_rbac.py:341": "Intentional algorithm confusion attack simulation in security test",
    "tests:tests/security/test_rbac.py:348": "Intentional JWT HMAC attack simulation in security test",
    "tests:tests/security/test_adversarial_auth.py:347": "Intentional JWT alg=none attack simulation in security test",
    "tests:tests/security/test_adversarial_auth.py:348": "Intentional JWT alg=none attack simulation in security test",
    "tests:tests/security/test_adversarial_auth.py:391": "Intentional JWT payload tampering simulation in security test",
    "tests:tests/security/test_adversarial_auth.py:575": "Intentional JWT alg=none attack simulation in security test",
    "tests:tests/security/test_adversarial_auth.py:578": "Intentional JWT alg=none attack simulation in security test",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:17": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:19": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:43": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:45": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:66": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:68": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:90": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:95": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:116": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:118": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:129": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:136": "Test fixture data for scenario engine unit tests",
    "tests:services/layer3-knowledge/tests/test_scenario_engine.py:150": "Test fixture data for scenario engine unit tests",
    "tests:services/layer4-agents/tests/test_c1_proxy.py:60": "Test fixture data for C1 proxy unit tests",
    "tests:services/api/app/tests/test_production_safety.py:13": "Intentional negative test for mock persistence rejection",
    "tests:services/api/app/tests/test_production_safety.py:15": "Intentional negative test for mock llm rejection",
    "tests:services/api/app/tests/test_production_safety.py:16": "Intentional negative test for demo data rejection",
    "tests:services/api/app/tests/test_i03_durable_persistence_and_llm.py:22": "Intentional negative test for mock llm rejection",
    "tests:services/api/app/tests/test_i03_durable_persistence_and_llm.py:23": "Intentional negative test for demo data rejection",
    "tests:services/api/app/tests/test_i03_durable_persistence_and_llm.py:103": "Intentional negative test for mock llm rejection",
    "tests:services/api/app/tests/test_i03_durable_persistence_and_llm.py:104": "Intentional negative test for demo data rejection",
    "tests:services/api/app/tests/test_i03_durable_persistence_and_llm.py:131": "Intentional negative test for mock llm rejection",
    "tests:packages/shared/src/value_fabric/shared/security/tests/test_production_safety.py:182": "Intentional negative test for mock persistence rejection",
    "tests:packages/shared/src/value_fabric/shared/security/tests/test_production_safety.py:306": "Intentional negative test for demo data rejection",
    "tests:tests/config/test_environment_matrix.py:155": "Intentional negative test for mock persistence rejection",
    "tests:tests/config/test_environment_matrix.py:263": "Intentional negative test for demo data rejection",
    # Docs / specs may contain illustrative examples
    "docs:docs/reference/layer4-agents-api.md:278": "Documentation example, not production code",
    "docs:docs/reference/layer4-agents-api.md:325": "Documentation example, not production code",
    "docs:specs/value_fabric_ingestion_backend_specs.md:1562": "Specification document, not production code",
    "docs:specs/value_fabric_ingestion_backend_specs.md:1927": "Specification document, not production code",
    "docs:specs/value_fabric_ingestion_backend_specs.md:1951": "Specification document, not production code",
    "docs:specs/value_fabric_ingestion_backend_specs.md:1985": "Specification document, not production code",
    # Generated code is excluded but we keep explicit allowlist entries for defence in depth
    "generated:apps/web/src/api/generated/l3/index.ts:8083": "Generated OpenAPI client code with illustrative example",
    "generated:contracts/openapi/layer3-knowledge.json:600": "Generated OpenAPI contract with illustrative example",
    # Scripts that migrate or lint code may reference patterns
    "scripts:scripts/ci/python_contract_lint.py:107": "Lint rule description mentioning security TODOs",
    "scripts:scripts/ci/check_auth_bypass.py:1": "Auth bypass checking script contains bypass strings explicitly",
    # Legitimate PKCE / JWT canonicalization uses
    "other:services/api/app/core/security.py:65": "JWT base64url canonicalization for tamper detection (not token creation)",
    "other:services/api/app/core/security.py:115": "JWT base64url re-encode for canonical segment comparison (tamper detection, not token creation)",
    # Security test simulations
    "tests:services/api/app/tests/test_production_safety.py:59": "Intentional negative test for mock llm rejection",
    "tests:services/api/app/tests/test_i03_durable_persistence_and_llm.py:66": "Intentional negative test for mock llm rejection",
    "tests:services/api/app/tests/test_i03_durable_persistence_and_llm.py:119": "Intentional negative test for demo data rejection",
    "tests:services/api/app/tests/test_i03_durable_persistence_and_llm.py:143": "Intentional negative test for mock llm rejection",
    # The scanner itself contains the banned pattern definitions
    "scripts:scripts/ci/prod_stub_scan.py:21": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:22": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:23": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:25": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:26": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:27": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:28": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:29": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:30": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:31": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:32": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:33": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:24": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:34": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:35": "Scanner contains banned pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:129": "Scanner contains security-critical pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:130": "Scanner contains security-critical pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:136": "Scanner contains security-critical pattern definition list",
    "scripts:scripts/ci/prod_stub_scan.py:137": "Scanner contains security-critical pattern definition list",
    "other:services/layer4-agents/src/layer4_agents/api/routes/integrations.py:190": "Base64url encoding for signed integration payload transport",
    "other:services/layer4-agents/src/layer4_agents/api/routes/integrations.py:215": "Base64url encoding for signed OAuth state payload transport",
    "tests:services/layer4-agents/tests/test_oidc_id_token_validation.py:22": "Test helper encodes RSA key modulus as base64url for JWK fixture",
    "tests:tests/integration/test_oidc_live.py:245": "Intentional JWT payload tampering simulation in integration security test",
    "tests:tests/layer3/test_model_registry_tenant_context.py:16": "Test helper generates base64url fixture IDs",
}

EXCEPTION_TAG_PATTERN = re.compile(
    r"\[auth-tenant-exception\s+ticket=(?P<ticket>[A-Z][A-Z0-9_-]+-\d+)\s+owner=(?P<owner>[a-z0-9][a-z0-9._-]*)\s+expiry=(?P<expiry>\d{4}-\d{2}-\d{2})\]",
    re.IGNORECASE,
)

# Directories to skip entirely
SKIP_DIRS = {
    ".git",
    ".github",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".hypothesis",
    "archive",
    "generated/logs",
    "artifacts",
    ".tmp",
}

# File extensions to scan

# Security-critical TODO/FIXME markers are forbidden in release-scoped paths.
SECURITY_CRITICAL_TODO_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:TODO|FIXME)\b[^\n#]*\b(?:auth|authentication|authorization|tenant|rbac|acl|oidc)\b", re.IGNORECASE),
    re.compile(r"\bSECURITY-TODO\b", re.IGNORECASE),
)

RELEASE_SCOPED_PREFIXES: tuple[str, ...] = (
    "services/",
    "value_fabric/",
    "packages/shared/src/value_fabric/shared/",
    "k8s/",
    "config/production-readiness/",
)

SCAN_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".yaml",
    ".yml",
    ".json",
    ".md",
    ".sh",
    ".sql",
}


def _should_skip(path: Path, repo_root: Path) -> bool:
    rel = path.relative_to(repo_root)
    rel_str = rel.as_posix()
    for part in rel.parts:
        if part in SKIP_DIRS:
            return True
    # Skip common large / non-source directories regardless of nesting
    skip_segments = {"node_modules", ".git", "__pycache__", ".pytest_cache", ".hypothesis", "archive", "artifacts", ".tmp", "generated/logs"}
    for seg in skip_segments:
        if seg in rel_str:
            return True
    if path.suffix not in SCAN_EXTENSIONS:
        return True
    return False


def _allowlist_key(path: Path, repo_root: Path, line_no: int) -> str:
    rel = path.relative_to(repo_root).as_posix()
    # Categorise by prefix for easier allowlist management
    prefix = "other"
    if "/tests/" in rel or rel.startswith("tests/"):
        prefix = "tests"
    elif rel.startswith("docs/") or rel.startswith("specs/"):
        prefix = "docs"
    elif rel.startswith("apps/web/src/api/generated/") or rel.startswith("contracts/"):
        prefix = "generated"
    elif rel.startswith("scripts/"):
        prefix = "scripts"
    return f"{prefix}:{rel}:{line_no}"


def _has_valid_exception_metadata(metadata: str) -> bool:
    """Require structured exception metadata with non-expired date."""
    match = EXCEPTION_TAG_PATTERN.search(metadata)
    if match is None:
        return False
    try:
        expiry = date.fromisoformat(match.group("expiry"))
    except ValueError:
        return False
    return expiry >= date.today()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    violations: list[tuple[Path, int, str, str]] = []

    # Use git ls-files for speed and to respect .gitignore
    import subprocess
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        tracked_files = result.stdout.splitlines()
    except Exception as exc:
        print(f"Warning: git ls-files failed ({exc}); falling back to os.walk")
        tracked_files = []
        for root, dirs, files in os.walk(repo_root):
            root_path = Path(root)
            # Prune skip directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in files:
                fpath = root_path / fname
                if _should_skip(fpath, repo_root):
                    continue
                tracked_files.append(str(fpath.relative_to(repo_root).as_posix()))

    for rel_str in tracked_files:
        fpath = repo_root / rel_str
        if _should_skip(fpath, repo_root):
            continue

        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = content.splitlines()
        for line_no, line in enumerate(lines, start=1):
            rel_posix = fpath.relative_to(repo_root).as_posix()
            if rel_posix.startswith(RELEASE_SCOPED_PREFIXES):
                if any(pattern.search(line) for pattern in SECURITY_CRITICAL_TODO_PATTERNS):
                    key = _allowlist_key(fpath, repo_root, line_no)
                    metadata = ALLOWLIST.get(key)
                    if metadata is None:
                        violations.append((fpath.relative_to(repo_root), line_no, "security-critical TODO/FIXME", line.strip()))
                        continue
                    if not _has_valid_exception_metadata(metadata):
                        violations.append(
                            (
                                fpath.relative_to(repo_root),
                                line_no,
                                "security-critical TODO/FIXME missing valid exception metadata",
                                line.strip(),
                            )
                        )
                        continue
            for pattern in BANNED_PATTERNS:
                if pattern in line:
                    key = _allowlist_key(fpath, repo_root, line_no)
                    if key in ALLOWLIST:
                        continue
                    # Allow base64.urlsafe_b64encode in PKCE / encryption contexts
                    if pattern == "base64.urlsafe_b64encode":
                        # Skip if this is clearly a PKCE/encryption file
                        lower_content = content.lower()
                        if "pkce" in lower_content or "code_challenge" in lower_content or "code_verifier" in lower_content:
                            continue
                        if "pbkdf2" in lower_content or "encryption_service" in lower_content:
                            continue
                        # If it's about JWT signing / token creation, flag it
                        if "jwt" in lower_content and "token" in lower_content:
                            pass
                        else:
                            continue
                    violations.append((fpath.relative_to(repo_root), line_no, pattern, line.strip()))

    if not violations:
        print("PASS: No banned stub/synthetic patterns found in production paths.")
        return 0

    print(f"FAIL: Found {len(violations)} banned pattern(s) in production paths:")
    print()
    for rel_path, line_no, pattern, line_text in violations:
        print(f"  {rel_path}:{line_no}")
        print(f"    Pattern: {pattern!r}")
        print(f"    Line:    {line_text}")
        print()
    print(
        "If a match is intentional and safe, add an ALLOWLIST entry. Release-scoped auth/tenant TODOs must"
        " include [auth-tenant-exception ticket=SEC-123 owner=team.slug expiry=YYYY-MM-DD] metadata."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
