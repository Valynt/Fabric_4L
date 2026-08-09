#!/usr/bin/env python3
"""Generate Python client models from OpenAPI specs using datamodel-code-generator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Paths
REPO_ROOT = Path(__file__).parent.parent.parent.parent
SDK_ROOT = Path(__file__).parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts" / "openapi"
GENERATED_DIR = SDK_ROOT / "src" / "valuefabric" / "generated"


def load_openapi_spec(path: Path) -> dict[str, Any]:
    """Load and validate OpenAPI spec."""
    with open(path, "r") as f:
        return json.load(f)


def generate_models(spec_path: Path, output_dir: Path, namespace: str) -> Path:
    """Generate Pydantic models from OpenAPI spec."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # datamodel-code-generator treats --output as a file when there's no trailing slash
    # We'll create a namespace directory first
    namespace_dir = output_dir / namespace
    namespace_dir.mkdir(parents=True, exist_ok=True)

    output_file = namespace_dir / "__init__.py"

    cmd = [
        sys.executable,
        "-m",
        "datamodel_code_generator",
        "--input",
        str(spec_path),
        "--output",
        str(output_file),
        "--input-file-type",
        "openapi",
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.10",
        "--use-standard-collections",
        "--use-schema-description",
        "--field-constraints",
        "--snake-case-field",
        "--collapse-root-models",
        "--disable-timestamp",
    ]

    print(f"Generating models for {namespace} from {spec_path}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error generating models for {namespace}:")
        print(result.stderr)
        sys.exit(1)

    print(f"✓ Generated models for {namespace} at {output_file}")
    return output_file


def extract_class_names_from_file(file_path: Path) -> list[str]:
    """Extract class names from a Python file."""
    classes: list[str] = []
    content = file_path.read_text()
    for line in content.split("\n"):
        if line.startswith("class ") and "(" in line:
            class_name = line.split("(")[0].replace("class ", "").strip()
            classes.append(class_name)
    return classes


def create_namespace_init(output_dir: Path, namespace: str) -> None:
    """Create __init__.py for namespace module - the generated file is already there."""
    namespace_dir = output_dir / namespace
    init_file = namespace_dir / "__init__.py"

    if not init_file.exists():
        print(f"Warning: {init_file} was not generated")
        return

    # Read the classes that were generated
    classes = extract_class_names_from_file(init_file)
    print(f"✓ {namespace} module has {len(classes)} model classes")
    print(f"✓ Verified {init_file}")


def create_generated_init(output_dir: Path) -> None:
    """Create main __init__.py for generated package."""
    init_file = output_dir / "__init__.py"

    content = '''"""Generated client and models from OpenAPI specs.

This package contains auto-generated code from the OpenAPI specifications.
Do not edit these files manually - they will be regenerated.

To regenerate:
    python scripts/generate_from_openapi.py
"""

from .l3_client import L3Client
from .l4_client import L4Client

__all__ = ["L3Client", "L4Client"]
'''

    init_file.write_text(content)
    print(f"✓ Created {init_file}")


def generate_l3_subset(spec_path: Path, output_dir: Path) -> None:
    """Generate focused subset of L3 models (search-related only)."""
    namespace_dir = output_dir / "l3"
    namespace_dir.mkdir(parents=True, exist_ok=True)

    spec = load_openapi_spec(spec_path)

    # Extract search-related schemas
    search_schemas = {
        "SearchRequest",
        "SearchResponse",
        "SearchResult",
        "SearchType",
        "SearchWeights",
        "HybridSearchRequest",
        "EntityType",
    }

    all_schemas = spec.get("components", {}).get("schemas", {})
    filtered_schemas = {k: v for k, v in all_schemas.items() if k in search_schemas}

    # Create minimal spec
    minimal_spec = {
        "openapi": "3.1.0",
        "info": {"title": "L3 Knowledge Search API", "version": "1.0.0"},
        "components": {"schemas": filtered_schemas},
    }

    output_file = namespace_dir / "__init__.py"
    minimal_path = namespace_dir / "_minimal_spec.json"
    with open(minimal_path, "w") as f:
        json.dump(minimal_spec, f)

    cmd = [
        sys.executable,
        "-m",
        "datamodel_code_generator",
        "--input",
        str(minimal_path),
        "--output",
        str(output_file),
        "--input-file-type",
        "openapi",
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.10",
        "--use-standard-collections",
        "--disable-timestamp",
    ]

    print("Generating L3 search models...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error generating L3 models:")
        print(result.stderr)
        # Non-fatal - continue without L3 models
        return

    print(f"✓ Generated L3 search models at {output_file}")

    # Clean up minimal spec
    minimal_path.unlink()


def create_client_wrapper(output_dir: Path, namespace: str, spec_path: Path) -> None:
    """Create a simple HTTP client wrapper for the namespace."""
    client_file = output_dir / f"{namespace}_client.py"

    spec = load_openapi_spec(spec_path)
    server_url = spec.get("servers", [{}])[0].get("url", "http://localhost:8000")
    title = spec.get("info", {}).get("title", f"{namespace.upper()} API")

    content = f'''"""Generated HTTP client for {title}."""

from __future__ import annotations

from typing import Any

import httpx


class {namespace.upper()}Client:
    """HTTP client for {title}.

    Generated from OpenAPI spec at {spec_path.name}
    """

    def __init__(
        self,
        base_url: str = "{server_url}",
        api_key: str | None = None,
        jwt_token: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        headers = {{"Accept": "application/json", "Content-Type": "application/json"}}
        if api_key:
            headers["X-API-Key"] = api_key
        elif jwt_token:
            headers["Authorization"] = f"Bearer {{jwt_token}}"

        self._sync_client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )
        self._async_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._sync_client.request(method, path, params=params, json=json)
        response.raise_for_status()
        return response.json()

    async def _arequest(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._async_client.request(method, path, params=params, json=json)
        response.raise_for_status()
        return response.json()

    def health(self) -> dict[str, Any]:
        """Check API health."""
        return self._request("GET", "/health")

    async def ahealth(self) -> dict[str, Any]:
        """Check API health (async)."""
        return await self._arequest("GET", "/health")
'''

    client_file.write_text(content)
    print(f"✓ Created {client_file}")


def main() -> int:
    """Main entry point."""
    print("Generating Python SDK from OpenAPI specs...")
    print(f"Contracts directory: {CONTRACTS_DIR}")
    print(f"Output directory: {GENERATED_DIR}")

    # Clean and recreate generated directory
    if GENERATED_DIR.exists():
        import shutil

        shutil.rmtree(GENERATED_DIR)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    # Generate L4 (Agents) models
    l4_spec = CONTRACTS_DIR / "layer4-agents.json"
    if l4_spec.exists():
        generate_models(l4_spec, GENERATED_DIR, "l4")
        create_namespace_init(GENERATED_DIR, "l4")
        create_client_wrapper(GENERATED_DIR, "l4", l4_spec)
    else:
        print(f"Warning: {l4_spec} not found")

    # Generate L3 (Knowledge) models - needs smaller subset to avoid memory issues
    l3_spec = CONTRACTS_DIR / "layer3-knowledge.json"
    if l3_spec.exists():
        # For L3, we'll generate a focused subset (search-related models only)
        # to avoid memory issues with the large spec
        print(f"L3 spec is large ({l3_spec.stat().st_size / 1024 / 1024:.1f} MB), generating focused subset...")
        generate_l3_subset(l3_spec, GENERATED_DIR)
    else:
        print(f"Warning: {l3_spec} not found")

    # Create main __init__.py
    create_generated_init(GENERATED_DIR)

    print("\n✓ SDK generation complete!")
    print(f"Generated files in: {GENERATED_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
