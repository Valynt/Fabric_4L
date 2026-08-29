#!/usr/bin/env python3
"""
Compare two OpenAPI specifications and report drift.

Usage:
    python scripts/compare_openapi.py \
        contracts/openapi/layer3-knowledge.json \
        generated/layer3-openapi.json \
        --output drift-report.md \
        --exit-code
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DriftItem:
    """Single drift detection item."""
    type: str  # 'missing_in_spec', 'missing_in_impl', 'different'
    path: str
    details: str
    severity: str  # 'error', 'warning', 'info'


def load_openapi(path: Path) -> dict:
    """Load OpenAPI specification from JSON file.

    Args:
        path: Path to OpenAPI JSON file

    Returns:
        OpenAPI specification as dictionary

    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file contains invalid JSON
        PermissionError: If file cannot be read
    """
    if not path.exists():
        raise FileNotFoundError(
            f"OpenAPI spec file not found: {path}\n"
            "Ensure the file exists and the path is correct."
        )

    if not path.is_file():
        raise IsADirectoryError(f"Path is a directory, not a file: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except PermissionError as e:
        raise PermissionError(
            f"Cannot read file {path}: {e}\n"
            "Check file permissions."
        ) from e

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # Provide context around the error location
        lines = content.split('\n')
        context_start = max(0, e.lineno - 2)
        context_end = min(len(lines), e.lineno + 2)
        context = '\n'.join(
            f"  {i+1}: {lines[i]}"
            for i in range(context_start, context_end)
        )
        raise json.JSONDecodeError(
            f"Invalid JSON in {path} at line {e.lineno}, column {e.colno}:\n"
            f"{context}\n"
            f"Error: {e.msg}",
            e.doc,
            e.pos
        ) from e


def extract_endpoints(spec: dict) -> dict[str, dict]:
    """Extract endpoints from OpenAPI spec as {method_path: operation}."""
    endpoints = {}
    paths = spec.get('paths', {})
    
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                key = f"{method.upper()} {path}"
                endpoints[key] = {
                    'operationId': operation.get('operationId', ''),
                    'summary': operation.get('summary', ''),
                    'tags': operation.get('tags', []),
                }
    
    return endpoints


def extract_schemas(spec: dict) -> dict[str, dict]:
    """Extract schemas from OpenAPI spec."""
    components = spec.get('components', {})
    schemas = components.get('schemas', {})
    return {name: schema for name, schema in schemas.items()}


def compare_endpoints(
    spec_endpoints: dict,
    impl_endpoints: dict,
) -> list[DriftItem]:
    """Compare endpoints between spec and implementation."""
    drift = []
    
    # Find endpoints in spec but not in implementation
    for endpoint in sorted(spec_endpoints.keys()):
        if endpoint not in impl_endpoints:
            drift.append(DriftItem(
                type='missing_in_impl',
                path=endpoint,
                details='Endpoint in spec but not in implementation',
                severity='error',
            ))
    
    # Find endpoints in implementation but not in spec
    for endpoint in sorted(impl_endpoints.keys()):
        if endpoint not in spec_endpoints:
            drift.append(DriftItem(
                type='missing_in_spec',
                path=endpoint,
                details='Endpoint in implementation but not in spec',
                severity='warning',
            ))
    
    return drift


def compare_schemas(spec_schemas: dict, impl_schemas: dict) -> list[DriftItem]:
    """Compare schemas between spec and implementation."""
    drift = []
    
    # Find schemas in spec but not in implementation
    for schema_name in sorted(spec_schemas.keys()):
        if schema_name not in impl_schemas:
            drift.append(DriftItem(
                type='schema_missing_in_impl',
                path=f'schemas.{schema_name}',
                details='Schema in spec but not in implementation',
                severity='warning',
            ))
    
    # Find schemas in implementation but not in spec
    for schema_name in sorted(impl_schemas.keys()):
        if schema_name not in spec_schemas:
            drift.append(DriftItem(
                type='schema_missing_in_spec',
                path=f'schemas.{schema_name}',
                details='Schema in implementation but not in spec',
                severity='info',
            ))
    
    return drift


def generate_report(
    spec_path: Path,
    impl_path: Path,
    drift: list[DriftItem],
    spec_endpoints: dict,
    impl_endpoints: dict,
) -> str:
    """Generate markdown drift report."""
    lines = [
        f"# OpenAPI Drift Report",
        f"",
        f"**Spec:** `{spec_path}`",
        f"**Implementation:** `{impl_path}`",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Spec Endpoints | {len(spec_endpoints)} |",
        f"| Implementation Endpoints | {len(impl_endpoints)} |",
        f"| Drift Items | {len(drift)} |",
        f"",
    ]
    
    if not drift:
        lines.extend([
            "## ✅ No Drift Detected",
            "",
            "The implementation matches the specification.",
        ])
        return "\n".join(lines)
    
    # Group by severity
    errors = [d for d in drift if d.severity == 'error']
    warnings = [d for d in drift if d.severity == 'warning']
    infos = [d for d in drift if d.severity == 'info']
    
    if errors:
        lines.extend([
            "## 🔴 Errors (Must Fix)",
            "",
        ])
        for item in errors:
            lines.extend([
                f"### {item.path}",
                f"- **Type:** {item.type}",
                f"- **Details:** {item.details}",
                f"",
            ])
    
    if warnings:
        lines.extend([
            "## 🟡 Warnings (Should Fix)",
            "",
        ])
        for item in warnings:
            lines.extend([
                f"### {item.path}",
                f"- **Type:** {item.type}",
                f"- **Details:** {item.details}",
                f"",
            ])
    
    if infos:
        lines.extend([
            "## 🔵 Info (Nice to Have)",
            "",
        ])
        for item in infos:
            lines.extend([
                f"### {item.path}",
                f"- **Type:** {item.type}",
                f"- **Details:** {item.details}",
                f"",
            ])
    
    lines.extend([
        "## Recommendations",
        "",
        "1. **Update Specification:** If implementation is correct, update the OpenAPI spec.",
        "2. **Update Implementation:** If spec is correct, implement missing endpoints.",
        "3. **Synchronize:** Run `python scripts/export_openapi.py` to regenerate spec from code.",
    ])
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Compare two OpenAPI specifications and report drift"
    )
    parser.add_argument(
        "spec",
        type=Path,
        help="Path to committed OpenAPI spec",
    )
    parser.add_argument(
        "implementation",
        type=Path,
        help="Path to generated OpenAPI from implementation",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output markdown report path",
    )
    parser.add_argument(
        "--exit-code",
        action="store_true",
        help="Exit with non-zero code if drift detected",
    )
    
    args = parser.parse_args()
    
    # Load specs
    try:
        spec = load_openapi(args.spec)
    except FileNotFoundError:
        print(f"Error: Spec file not found: {args.spec}", file=sys.stderr)
        sys.exit(1)
    
    try:
        impl = load_openapi(args.implementation)
    except FileNotFoundError:
        print(f"Error: Implementation file not found: {args.implementation}", file=sys.stderr)
        # If implementation doesn't exist, that's a build error
        sys.exit(2)
    
    # Extract endpoints and schemas
    spec_endpoints = extract_endpoints(spec)
    impl_endpoints = extract_endpoints(impl)
    spec_schemas = extract_schemas(spec)
    impl_schemas = extract_schemas(impl)
    
    # Compare
    endpoint_drift = compare_endpoints(spec_endpoints, impl_endpoints)
    schema_drift = compare_schemas(spec_schemas, impl_schemas)
    all_drift = endpoint_drift + schema_drift
    
    # Generate report
    report = generate_report(
        args.spec,
        args.implementation,
        all_drift,
        spec_endpoints,
        impl_endpoints,
    )
    
    # Output
    if args.output:
        args.output.write_text(report, encoding='utf-8')
        print(f"Report written to: {args.output}")
    else:
        print(report)
    
    # Exit code
    has_errors = any(d.severity == 'error' for d in all_drift)
    if args.exit_code and has_errors:
        sys.exit(1)
    elif args.exit_code and all_drift:
        sys.exit(0)  # Warnings only = success with notice
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
