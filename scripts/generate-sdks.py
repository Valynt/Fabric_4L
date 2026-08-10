#!/usr/bin/env python3
"""
Fabric 4L — SDK Generation Script
==================================

Generates client SDKs for the Fabric 4L API from OpenAPI 3.1 specifications.
Supports Python and TypeScript via openapi-generator-cli.

Usage:
    # Generate both SDKs
    python scripts/generate-sdks.py --all

    # Generate specific language
    python scripts/generate-sdks.py --language python
    python scripts/generate-sdks.py --language typescript

    # Generate for specific layers only
    python scripts/generate-sdks.py --language python --layers l1-gateway,l3-core

    # Custom output directory
    python scripts/generate-sdks.py --all --output-dir ./custom-sdks

    # Validate OpenAPI specs without generating
    python scripts/generate-sdks.py --validate-only

Prerequisites:
    - Java 11+ (for openapi-generator-cli)
    - Docker (alternative: uses openapi-generator image)
    - npm or pip (for publishing)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

FABRIC_VERSION = "1.2.0"
OPENAPI_DIR = Path("contracts/openapi")
DEFAULT_OUTPUT_DIR = Path("sdk")

LAYER_NAMES = {
    "l1-gateway": "IngressGateway",
    "l2-auth": "AuthNAuthZ",
    "l3-core": "CoreServices",
    "l4-compute": "ComputeEngine",
    "l5-data": "DataAccess",
    "l6-observability": "Observability",
}

ALL_LAYERS = list(LAYER_NAMES.keys())


class Language(Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"


@dataclass
class GeneratorConfig:
    """Configuration for a single SDK generation run."""
    language: Language
    layer: str
    openapi_file: Path
    output_dir: Path
    package_name: str
    package_version: str
    generator_extra_args: list[str]


# ─────────────────────────────────────────────────────────────────────────────
# OpenAPI Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_openapi_spec(spec_path: Path) -> tuple[bool, list[str]]:
    """Validate an OpenAPI 3.x specification file.

    Returns:
        (is_valid, list of error messages)
    """
    errors: list[str] = []

    if not spec_path.exists():
        errors.append(f"File not found: {spec_path}")
        return False, errors

    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return False, errors
    except Exception as e:
        errors.append(f"Cannot read file: {e}")
        return False, errors

    # Check OpenAPI version
    openapi_version = spec.get("openapi", "")
    if not openapi_version:
        errors.append("Missing 'openapi' field")
    elif not openapi_version.startswith("3."):
        errors.append(f"Expected OpenAPI 3.x, got: {openapi_version}")

    # Check required fields
    if "info" not in spec:
        errors.append("Missing 'info' section")
    else:
        info = spec["info"]
        if "title" not in info:
            errors.append("Missing 'info.title'")
        if "version" not in info:
            errors.append("Missing 'info.version'")

    if "paths" not in spec or not spec["paths"]:
        errors.append("Missing or empty 'paths' section")

    return len(errors) == 0, errors


# ─────────────────────────────────────────────────────────────────────────────
# openapi-generator Runner
# ─────────────────────────────────────────────────────────────────────────────

def find_openapi_generator() -> str:
    """Find the openapi-generator-cli executable.

    Searches in order:
        1. Local npm install (npx)
        2. Global npm install
        3. System PATH
        4. Docker fallback
    """
    # Try npx
    result = shutil.which("openapi-generator-cli")
    if result:
        return result

    result = shutil.which("npx")
    if result:
        return f"{result} @openapitools/openapi-generator-cli"

    # Check if docker is available
    result = shutil.which("docker")
    if result:
        return "docker run --rm -v $(pwd):/local openapitools/openapi-generator-cli"

    raise RuntimeError(
        "openapi-generator-cli not found. Install via:\n"
        "  npm install -g @openapitools/openapi-generator-cli\n"
        "Or use Docker:\n"
        "  docker pull openapitools/openapi-generator-cli"
    )


def run_generator(config: GeneratorConfig, generator_cmd: str) -> None:
    """Execute openapi-generator-cli for a single config."""
    lang = config.language.value

    # Base arguments
    args = [
        "generate",
        "-i", str(config.openapi_file),
        "-g", lang,
        "-o", str(config.output_dir),
        "--package-name", config.package_name,
        "--additional-properties",
        f"packageVersion={config.package_version},packageName={config.package_name}",
        *config.generator_extra_args,
    ]

    # Build command
    if generator_cmd.startswith("docker"):
        # Map volumes for docker
        abs_openapi = config.openapi_file.resolve()
        abs_output = config.output_dir.resolve()
        abs_parent = abs_openapi.parent.parent  # repo root

        cmd = f"{generator_cmd} generate " \
              f"-i /local/{abs_openapi.relative_to(abs_parent)} " \
              f"-g {lang} " \
              f"-o /local/{abs_output.relative_to(abs_parent)} " \
              f"--package-name {config.package_name} " \
              f"--additional-properties packageVersion={config.package_version},packageName={config.package_name} " \
              f"{' '.join(config.generator_extra_args)}"
    else:
        cmd_parts = generator_cmd.split() + args
        cmd = " ".join(cmd_parts)

    print(f"  Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ERROR: Generator failed for {config.layer}/{lang}")
        print(f"  stdout: {result.stdout}")
        print(f"  stderr: {result.stderr}")
        raise RuntimeError(f"SDK generation failed: {config.layer}/{lang}")

    print(f"  ✓ Generated: {config.output_dir}")


def get_python_extra_args(layer: str) -> list[str]:
    """Get generator extra args for Python SDK."""
    return [
        "--library=urllib3",
        "--additional-properties",
        "generateSourceCodeOnly=false,"
        "hideGenerationTimestamp=true,"
        "useOneOfDiscriminatorLookup=true,"
        f"projectName=fabric4l-{layer}",
    ]


def get_typescript_extra_args(layer: str) -> list[str]:
    """Get generator extra args for TypeScript SDK."""
    return [
        "--additional-properties",
        "npmName=@fabric4l/sdk-" + layer.replace("_", "-") + ","
        "npmVersion=" + FABRIC_VERSION + ","
        "supportsES6=true,"
        "modelPropertyNaming=original,"
        "withInterfaces=true,"
        "withNodeImports=true,"
        "useObjectParameters=true,"
        "withoutPrefixEnums=true",
    ]


# ─────────────────────────────────────────────────────────────────────────────
# SDK Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_sdk(
    language: Language,
    layer: str,
    output_base: Path,
    generator_cmd: str,
) -> Path:
    """Generate SDK for a single layer and language.

    Returns:
        Path to the generated SDK directory.
    """
    openapi_file = OPENAPI_DIR / f"{layer}.openapi.json"
    layer_pascal = LAYER_NAMES[layer]

    if language == Language.PYTHON:
        package_name = f"fabric4l_{layer.replace('-', '_')}"
        output_dir = output_base / "python" / f"fabric4l-{layer}"
        extra_args = get_python_extra_args(layer)
    else:
        package_name = f"fabric4l{layer_pascal}"
        output_dir = output_base / "typescript" / f"fabric4l-{layer}"
        extra_args = get_typescript_extra_args(layer)

    config = GeneratorConfig(
        language=language,
        layer=layer,
        openapi_file=openapi_file,
        output_dir=output_dir,
        package_name=package_name,
        package_version=FABRIC_VERSION,
        generator_extra_args=extra_args,
    )

    print(f"\n  [{language.value.upper()}] {layer} → {output_dir}")
    run_generator(config, generator_cmd)

    return output_dir


def generate_all_sdks(
    languages: list[Language],
    layers: list[str],
    output_dir: Path,
    validate_only: bool = False,
) -> dict[str, list[Path]]:
    """Generate SDKs for all specified languages and layers.

    Returns:
        Dict mapping language.value -> list of generated SDK paths.
    """
    results: dict[str, list[Path]] = {lang.value: [] for lang in languages}

    # Validation phase
    print("=" * 60)
    print("PHASE 1: OpenAPI Spec Validation")
    print("=" * 60)

    all_valid = True
    for layer in layers:
        openapi_file = OPENAPI_DIR / f"{layer}.openapi.json"
        valid, errors = validate_openapi_spec(openapi_file)
        status = "✓" if valid else "✗"
        print(f"  {status} {layer}: {openapi_file}")
        if not valid:
            all_valid = False
            for err in errors:
                print(f"      ERROR: {err}")

    if not all_valid:
        if validate_only:
            print("\nValidation completed with errors.")
            return results
        raise RuntimeError("OpenAPI validation failed. Fix errors before generating SDKs.")

    if validate_only:
        print("\n✓ All OpenAPI specs are valid.")
        return results

    # Generation phase
    print("\n" + "=" * 60)
    print("PHASE 2: SDK Generation")
    print("=" * 60)

    generator_cmd = find_openapi_generator()
    print(f"Using generator: {generator_cmd}")

    for language in languages:
        print(f"\n{'─' * 50}")
        print(f"Language: {language.value.upper()}")
        print(f"{'─' * 50}")

        for layer in layers:
            try:
                sdk_path = generate_sdk(language, layer, output_dir, generator_cmd)
                results[language.value].append(sdk_path)
            except RuntimeError as e:
                print(f"  FAILED: {e}")
                # Continue with other layers

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Post-Generation: README, Setup Files
# ─────────────────────────────────────────────────────────────────────────────

def write_python_metafiles(output_dir: Path) -> None:
    """Write Python SDK metafiles (root README, setup.py for monorepo)."""
    python_dir = output_dir / "python"
    python_dir.mkdir(parents=True, exist_ok=True)

    # Write a top-level setup.py for the Python SDK monorepo
    setup_py = python_dir / "setup.py"
    setup_py.write_text(
        "# Fabric 4L Python SDKs\n"
        "\n"
        "from setuptools import setup, find_namespace_packages\n"
        "\n"
        "setup(\n"
        '    name=\"fabric4l\",\n'
        '    version=\"1.2.0\",\n'
        '    description=\"Fabric 4L Platform SDKs - Python client libraries\",\n'
        '    author=\"Fabric 4L Engineering\",\n'
        '    author_email=\"api@fabric4l.io\",\n'
        '    url=\"https://github.com/fabric-4l/fabric-4l\",\n'
        "    packages=find_namespace_packages(),\n"
        '    python_requires=\">=3.9\",\n'
        "    install_requires=[\n"
        '        \"urllib3>=2.0.0\",\n'
        '        \"python-dateutil>=2.8.0\",\n'
        "    ],\n"
        "    extras_require={\n"
        '        \"all\": [\n'
        '            \"fabric4l-l1-gateway\",\n'
        '            \"fabric4l-l2-auth\",\n'
        '            \"fabric4l-l3-core\",\n'
        '            \"fabric4l-l4-compute\",\n'
        '            \"fabric4l-l5-data\",\n'
        '            \"fabric4l-l6-observability\",\n'
        "        ],\n"
        "    },\n"
        "    classifiers=[\n"
        '        \"Development Status :: 4 - Beta\",\n'
        '        \"Intended Audience :: Developers\",\n'
        '        \"License :: OSI Approved :: MIT License\",\n'
        '        \"Programming Language :: Python :: 3\",\n'
        '        \"Programming Language :: Python :: 3.9\",\n'
        '        \"Programming Language :: Python :: 3.10\",\n'
        '        \"Programming Language :: Python :: 3.11\",\n'
        '        \"Programming Language :: Python :: 3.12\",\n'
        "    ],\n"
        ")\n"
    )

    # pyproject.toml
    pyproject = python_dir / "pyproject.toml"
    pyproject.write_text("""\
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "fabric4l"
version = "1.2.0"
description = "Fabric 4L Platform SDKs — Python client libraries"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
authors = [
    {name = "Fabric 4L Engineering", email = "api@fabric4l.io"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "urllib3>=2.0.0",
    "python-dateutil>=2.8.0",
]
""")


def write_typescript_metafiles(output_dir: Path) -> None:
    """Write TypeScript SDK metafiles."""
    ts_dir = output_dir / "typescript"
    ts_dir.mkdir(parents=True, exist_ok=True)

    # Root package.json
    package_json = ts_dir / "package.json"
    package_json.write_text(json.dumps({
        "name": "@fabric4l/sdk",
        "version": FABRIC_VERSION,
        "description": "Fabric 4L Platform SDKs — TypeScript client libraries",
        "private": True,
        "workspaces": [
            "fabric4l-*"
        ],
        "scripts": {
            "build": "npm run build --workspaces",
            "test": "npm run test --workspaces",
            "lint": "eslint . --ext .ts",
        },
        "devDependencies": {
            "typescript": "^5.3.0",
            "@types/node": "^20.0.0",
            "eslint": "^8.56.0",
            "@typescript-eslint/eslint-plugin": "^6.0.0",
            "@typescript-eslint/parser": "^6.0.0",
        },
        "author": "Fabric 4L Engineering <api@fabric4l.io>",
        "license": "MIT",
        "repository": {
            "type": "git",
            "url": "https://github.com/fabric-4l/fabric-4l.git",
            "directory": "sdk/typescript",
        },
    }, indent=2) + "\n")

    # tsconfig.json
    tsconfig = ts_dir / "tsconfig.json"
    tsconfig.write_text(json.dumps({
        "compilerOptions": {
            "target": "ES2020",
            "module": "commonjs",
            "lib": ["ES2020"],
            "declaration": True,
            "strict": True,
            "noImplicitAny": True,
            "strictNullChecks": True,
            "noImplicitThis": True,
            "alwaysStrict": True,
            "noUnusedLocals": False,
            "noUnusedParameters": False,
            "noImplicitReturns": True,
            "noFallthroughCasesInSwitch": False,
            "moduleResolution": "node",
            "sourceMap": True,
            "forceConsistentCasingInFileNames": True,
            "esModuleInterop": True,
            "resolveJsonModule": True,
        },
        "exclude": ["node_modules", "dist"],
    }, indent=2) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fabric 4L SDK Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                              # Generate all SDKs
  %(prog)s --language python                  # Python SDKs only
  %(prog)s --language typescript              # TypeScript SDKs only
  %(prog)s --all --layers l1-gateway,l3-core  # Only L1 and L3
  %(prog)s --validate-only                    # Validate specs only
  %(prog)s --all --output-dir ./my-sdks       # Custom output path
        """,
    )

    lang_group = parser.add_mutually_exclusive_group()
    lang_group.add_argument(
        "--all", "-a", action="store_true",
        help="Generate SDKs for all supported languages",
    )
    lang_group.add_argument(
        "--language", "-l", choices=[lang.value for lang in Language],
        help="Target language for SDK generation",
    )

    parser.add_argument(
        "--layers",
        default=",".join(ALL_LAYERS),
        help=f"Comma-separated list of layers (default: all). Options: {', '.join(ALL_LAYERS)}",
    )
    parser.add_argument(
        "--output-dir", "-o", default=str(DEFAULT_OUTPUT_DIR),
        help=f"Base output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--validate-only", action="store_true",
        help="Validate OpenAPI specs without generating SDKs",
    )
    parser.add_argument(
        "--install-generator", action="store_true",
        help="Install openapi-generator-cli via npm before running",
    )
    parser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s {FABRIC_VERSION}",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Determine languages
    if args.all:
        languages = [Language.PYTHON, Language.TYPESCRIPT]
    elif args.language:
        languages = [Language(args.language)]
    else:
        print("Error: Specify --all or --language", file=sys.stderr)
        return 1

    # Parse layers
    layers = [l.strip() for l in args.layers.split(",")]
    invalid = set(layers) - set(ALL_LAYERS)
    if invalid:
        print(f"Error: Invalid layers: {', '.join(invalid)}", file=sys.stderr)
        print(f"Valid: {', '.join(ALL_LAYERS)}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)

    # Install generator if requested
    if args.install_generator:
        print("Installing openapi-generator-cli...")
        subprocess.run(
            ["npm", "install", "-g", "@openapitools/openapi-generator-cli"],
            check=True,
        )

    # Validate OpenAPI directory exists
    if not OPENAPI_DIR.exists():
        print(f"Error: OpenAPI directory not found: {OPENAPI_DIR}", file=sys.stderr)
        print("Expected structure: contracts/openapi/{layer}.openapi.json", file=sys.stderr)
        return 1

    # Generate
    try:
        results = generate_all_sdks(
            languages=languages,
            layers=layers,
            output_dir=output_dir,
            validate_only=args.validate_only,
        )

        if args.validate_only:
            return 0

        # Write metafiles
        if Language.PYTHON in languages:
            write_python_metafiles(output_dir)
        if Language.TYPESCRIPT in languages:
            write_typescript_metafiles(output_dir)

        # Summary
        print("\n" + "=" * 60)
        print("SDK GENERATION SUMMARY")
        print("=" * 60)
        total = 0
        for lang, paths in results.items():
            print(f"\n  {lang.upper()}:")
            for p in paths:
                print(f"    ✓ {p}")
                total += 1
        print(f"\n  Total SDKs generated: {total}")
        print(f"  Output directory: {output_dir.resolve()}")
        print("\n✓ Done. See sdk/README.md for usage instructions.")

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
