#!/usr/bin/env python3
"""Generate and validate integrity evidence for locked Helm dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence


@dataclass(frozen=True)
class LockedDependency:
    name: str
    repository: str
    version: str

    @property
    def filename(self) -> str:
        return f"{self.name}-{self.version}.tgz"


class ValidationError(ValueError):
    """Raised when locked dependencies or their evidence drift."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_chart_lock(path: Path) -> list[LockedDependency]:
    """Parse the dependency records from Helm's small, stable Chart.lock shape."""
    dependencies: list[LockedDependency] = []
    current: dict[str, str] | None = None
    in_dependencies = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line == "dependencies:":
            in_dependencies = True
            continue
        if not in_dependencies:
            continue
        if raw_line and not raw_line.startswith(("-", " ")):
            break
        stripped = raw_line.strip()
        if stripped.startswith("- name:"):
            if current is not None:
                dependencies.append(_locked_dependency(current, path))
            current = {"name": stripped.split(":", 1)[1].strip()}
        elif current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            if key in {"repository", "version"}:
                current[key] = value.strip().strip("'\"")
    if current is not None:
        dependencies.append(_locked_dependency(current, path))
    if not dependencies:
        raise ValidationError(f"No dependencies found in {path}")
    if len({dependency.name for dependency in dependencies}) != len(dependencies):
        raise ValidationError(f"Duplicate dependency names in {path}")
    return dependencies


def _locked_dependency(values: dict[str, str], path: Path) -> LockedDependency:
    missing = {"name", "repository", "version"} - values.keys()
    if missing:
        raise ValidationError(f"Incomplete dependency in {path}: missing {sorted(missing)}")
    return LockedDependency(**values)


def _parse_embedded_chart(archive: Path) -> tuple[str, str]:
    try:
        with tarfile.open(archive, "r:gz") as bundle:
            chart_members = [
                member
                for member in bundle.getmembers()
                if member.isfile()
                and PurePosixPath(member.name).name == "Chart.yaml"
                and len(PurePosixPath(member.name).parts) == 2
            ]
            if len(chart_members) != 1:
                raise ValidationError(
                    f"{archive.name} must contain exactly one root Chart.yaml"
                )
            extracted = bundle.extractfile(chart_members[0])
            if extracted is None:
                raise ValidationError(f"Cannot read Chart.yaml from {archive.name}")
            fields: dict[str, str] = {}
            for raw_line in extracted.read().decode("utf-8").splitlines():
                if raw_line.startswith(("name:", "version:")):
                    key, value = raw_line.split(":", 1)
                    fields[key] = value.strip().strip("'\"")
    except (tarfile.TarError, UnicodeDecodeError) as exc:
        raise ValidationError(f"Cannot inspect {archive.name}: {exc}") from exc
    if not fields.get("name") or not fields.get("version"):
        raise ValidationError(f"{archive.name} embedded Chart.yaml lacks name or version")
    return fields["name"], fields["version"]


def inspect_archives(chart_dir: Path) -> list[dict[str, str]]:
    locked = parse_chart_lock(chart_dir / "Chart.lock")
    charts_dir = chart_dir / "charts"
    actual = sorted(charts_dir.glob("*.tgz")) if charts_dir.is_dir() else []
    expected_names = {dependency.filename for dependency in locked}
    actual_names = {archive.name for archive in actual}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        unexpected = sorted(actual_names - expected_names)
        raise ValidationError(
            f"Archive set differs from Chart.lock; missing={missing}, unexpected={unexpected}"
        )

    records: list[dict[str, str]] = []
    for dependency in sorted(locked, key=lambda item: item.name):
        archive = charts_dir / dependency.filename
        embedded_name, embedded_version = _parse_embedded_chart(archive)
        if (embedded_name, embedded_version) != (dependency.name, dependency.version):
            raise ValidationError(
                f"{archive.name} embeds {embedded_name} {embedded_version}; "
                f"Chart.lock requires {dependency.name} {dependency.version}"
            )
        records.append(
            {
                "name": dependency.name,
                "version": dependency.version,
                "repository": dependency.repository,
                "archive": f"charts/{archive.name}",
                "sha256": sha256_file(archive),
            }
        )
    return records


def generate_evidence(chart_dir: Path, evidence_dir: Path, helm_version: str) -> None:
    records = inspect_archives(chart_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    checksums = "".join(
        f"{record['sha256']}  {record['archive']}\n" for record in records
    )
    (evidence_dir / "checksums.sha256").write_text(checksums, encoding="utf-8")
    metadata = {
        "schema_version": 1,
        "chart_lock_sha256": sha256_file(chart_dir / "Chart.lock"),
        "helm_version": helm_version,
        "dependencies": records,
    }
    (evidence_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def validate_evidence(chart_dir: Path, evidence_dir: Path, helm_version: str) -> None:
    records = inspect_archives(chart_dir)
    metadata_path = evidence_dir / "metadata.json"
    checksums_path = evidence_dir / "checksums.sha256"
    if not metadata_path.is_file() or not checksums_path.is_file():
        raise ValidationError("Integrity metadata.json and checksums.sha256 are required")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValidationError(f"Invalid metadata.json: {exc}") from exc
    expected_checksums = "".join(
        f"{record['sha256']}  {record['archive']}\n" for record in records
    )
    if checksums_path.read_text(encoding="utf-8") != expected_checksums:
        raise ValidationError("Archive checksum manifest does not match prepared dependencies")
    expected_metadata = {
        "schema_version": 1,
        "chart_lock_sha256": sha256_file(chart_dir / "Chart.lock"),
        "helm_version": helm_version,
        "dependencies": records,
    }
    if metadata != expected_metadata:
        raise ValidationError(
            "Integrity metadata does not match Chart.lock, Helm version, or archives"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generate", "validate"))
    parser.add_argument("--chart-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--helm-version", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "generate":
            generate_evidence(args.chart_dir, args.evidence_dir, args.helm_version)
        else:
            validate_evidence(args.chart_dir, args.evidence_dir, args.helm_version)
    except (OSError, ValidationError) as exc:
        print(f"Helm dependency validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Helm dependency {args.mode} succeeded for {args.chart_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
