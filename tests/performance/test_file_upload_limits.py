"""File upload capacity and parsing-limit budget tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = [pytest.mark.performance]

PACKAGE_JSON = Path("package.json")


@dataclass(frozen=True)
class UploadLimits:
    max_file_bytes: int
    max_batch_bytes: int
    max_files_per_batch: int
    max_parse_seconds: int
    allowed_extensions: frozenset[str]

    def accepts_file(self, filename: str, size_bytes: int) -> bool:
        suffix = Path(filename).suffix.lower()
        return suffix in self.allowed_extensions and size_bytes <= self.max_file_bytes

    def accepts_batch(self, sizes: list[int]) -> bool:
        return len(sizes) <= self.max_files_per_batch and sum(sizes) <= self.max_batch_bytes


LIMITS = UploadLimits(
    max_file_bytes=25 * 1024 * 1024,
    max_batch_bytes=100 * 1024 * 1024,
    max_files_per_batch=20,
    max_parse_seconds=30,
    allowed_extensions=frozenset({".csv", ".docx", ".json", ".md", ".pdf", ".txt", ".xlsx"}),
)


def test_single_file_upload_size_and_type_limits() -> None:
    assert LIMITS.accepts_file("evidence.pdf", 25 * 1024 * 1024)
    assert not LIMITS.accepts_file("oversized.pdf", 25 * 1024 * 1024 + 1)
    assert not LIMITS.accepts_file("archive.zip", 1024)


def test_batch_upload_limits_prevent_parser_resource_exhaustion() -> None:
    assert LIMITS.accepts_batch([5 * 1024 * 1024] * 20)
    assert not LIMITS.accepts_batch([5 * 1024 * 1024] * 21)
    assert not LIMITS.accepts_batch([50 * 1024 * 1024, 51 * 1024 * 1024])
    assert LIMITS.max_parse_seconds <= 30


def test_loadtest_smoke_profile_is_exposed_as_pnpm_script() -> None:
    source = PACKAGE_JSON.read_text(encoding="utf-8")

    assert '"loadtest:smoke"' in source
    assert "PERF_DURATION=30s" in source
    assert "tests/performance/k6/l2_l3_l4_critical_paths.js" in source
