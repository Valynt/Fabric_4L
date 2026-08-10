"""Typed models for the v1 release-factory harness.

Thin control plane over existing gates (INV-FACTORY-001): these models only
describe step execution records and candidate manifests. They implement no
testing, deployment, migration, or recovery logic.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

NOT_RUN_EXIT_CODE = -1


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Step:
    """One certification step delegating to an existing command."""

    name: str
    command: tuple[str, ...]
    criterion: str
    blocking: bool = True
    live_only: bool = False  # requires CERTIFY_LIVE=1 (staging infrastructure)
    unimplemented: bool = False  # real operation does not exist yet; always blocks


@dataclass
class StepResult:
    gate: str
    command: str
    exit_code: int
    started_at: str
    finished_at: str
    log: str
    criterion: str = ""
    classification: str = ""

    @property
    def passed(self) -> bool:
        return self.exit_code == 0

    @property
    def not_run(self) -> bool:
        return self.exit_code == NOT_RUN_EXIT_CODE

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunRecord:
    """Machine-readable record for one harness invocation."""

    kind: str
    sha: str
    branch: str
    generated_at: str = field(default_factory=utc_now)
    results: list[StepResult] = field(default_factory=list)
    # True only when the harness itself verified a clean working tree during
    # the run; absent/False means "not verified", never "assumed clean".
    clean_tree_verified: bool = False

    @property
    def failed(self) -> list[StepResult]:
        return [r for r in self.results if not r.passed and not r.not_run]

    @property
    def not_run_steps(self) -> list[StepResult]:
        return [r for r in self.results if r.not_run]

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "kind": self.kind,
            "sha": self.sha,
            "branch": self.branch,
            "generated_at": self.generated_at,
            "clean_tree_verified": self.clean_tree_verified,
            "gates": [r.to_dict() for r in self.results],
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
