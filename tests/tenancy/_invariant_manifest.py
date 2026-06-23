from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from tests.production_readiness.manifest import assert_pytest_coverage, repo_path


@dataclass(frozen=True)
class TenantInvariant:
    key: str
    description: str
    evidence: tuple[tuple[str, ...], ...]


def assert_tenancy_invariants(
    paths: Iterable[str],
    *,
    label: str,
    invariants: Iterable[TenantInvariant],
) -> None:
    coverage_paths = tuple(paths)
    required_invariants = tuple(invariants)

    assert_pytest_coverage(coverage_paths, label=label)
    assert required_invariants, f"{label} must define at least one tenancy invariant"

    source = "\n".join(repo_path(path).read_text(encoding="utf-8") for path in coverage_paths).lower()
    missing: list[str] = []

    for invariant in required_invariants:
        for evidence_group in invariant.evidence:
            if not any(token.lower() in source for token in evidence_group):
                options = " OR ".join(repr(token) for token in evidence_group)
                missing.append(f"{invariant.key}: {invariant.description}; missing one of {options}")

    assert not missing, f"{label} is missing required tenant invariant evidence: {missing}"
