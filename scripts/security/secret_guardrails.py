#!/usr/bin/env python3
"""Guardrail scanner for committed/static secrets."""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

BLOCKED_PATHS = {"k8s/secrets.yml"}
# conservative patterns for common key/token formats
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[\"'][A-Za-z0-9_\-\/=+]{16,}"),
]
BASE64_CANDIDATE = re.compile(r"\b[A-Za-z0-9+/]{32,}={0,2}\b")

TEXT_EXTENSIONS = {".yml", ".yaml", ".json", ".env", ".txt", ".md", ".ini", ".cfg", ".conf", ".py", ".ts", ".js", ".sh"}
DOC_EXTENSIONS = {".md", ".txt"}


def entropy(value: str) -> float:
    if not value:
        return 0.0
    probs = [value.count(ch) / len(value) for ch in set(value)]
    return -sum(p * math.log2(p) for p in probs)


SYNTHETIC_MARKERS = {
    "dummy",
    "mock",
    "example",
    "placeholder",
    "test_dummy",
    "test_payload",
    "test_signature",
    "test_secret",
    "test_password",
    "test_key",
    "test_token",
    "fake",
    "redacted",
    "REDACTED",
    "00000000",
    "aaaa",
    "bbbb",
    "eyjhbgcioijsuzi1niisinr5cci6ikpxvcj9",  # standard non-secret JWT header: {"alg":"HS256","typ":"JWT"}
}


def is_synthetic_fixture(value: str) -> bool:
    val_lower = value.lower()
    return any(marker in val_lower for marker in SYNTHETIC_MARKERS)


def is_probable_secret_token(token: str, line: str = "") -> bool:
    if len(token) < 32:
        return False
    if is_synthetic_fixture(token) or (line and is_synthetic_fixture(line)):
        return False
    if entropy(token) < 4.2:
        return False
    # avoid obvious non-secret hashes/version ids
    if token.lower().startswith(("sha256", "md5")):
        return False
    return True


def scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    rel = path.as_posix()
    if rel in BLOCKED_PATHS:
        findings.append(f"blocked path detected: {rel}")

    if path.suffix and path.suffix.lower() not in TEXT_EXTENSIONS:
        return findings
    if path.suffix.lower() in DOC_EXTENSIONS:
        return findings

    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return findings

    is_test_file = "test" in rel.lower()

    for i, line in enumerate(content.splitlines(), start=1):
        if is_synthetic_fixture(line):
            continue

        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(line):
                matched_str = match.group(0)
                if not is_synthetic_fixture(matched_str):
                    findings.append(f"{rel}:{i}: matched sensitive token pattern `{pattern.pattern}`")

        for token in BASE64_CANDIDATE.findall(line):
            if is_probable_secret_token(token, line):
                findings.append(f"{rel}:{i}: high-entropy token candidate")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Files to scan")
    args = parser.parse_args()

    all_findings: list[str] = []
    for raw in args.paths:
        path = Path(raw)
        if not path.exists() or path.is_dir():
            continue
        all_findings.extend(scan_file(path))

    if all_findings:
        print("Secret guardrails failed:")
        for finding in all_findings:
            print(f"  - {finding}")
        return 1

    print("Secret guardrails passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
