#!/usr/bin/env python3
"""
Generate OpenAPI specification from FastAPI application.

Usage:
    python scripts/generate_openapi.py --layer layer3-knowledge
    python scripts/generate_openapi.py --layer layer5-ground-truth --output contracts/openapi/
"""

import argparse
import json
import sys
from pathlib import Path


# Layer configuration
LAYERS = {
    "layer3-knowledge": {
        "module": "layer3_knowledge.api.main:app",
        "default_output": "contracts/openapi/layer3-knowledge.json",
    },
    "layer5-ground-truth": {
        "module": "layer5_ground_truth.api.main:app",
        "default_output": "contracts/openapi/layer5-ground-truth.json",
    },
    "layer1-ingestion": {
        "module": "layer1_ingestion.api.main:app",
        "default_output": "contracts/openapi/layer1-ingestion.json",
    },
    "layer2-extraction": {
        "module": "layer2_extraction.api.main:app",
        "default_output": "contracts/openapi/layer2-extraction.json",
    },
    "layer4-agents": {
        "module": "api.main:app",
        "default_output": "contracts/openapi/layer4-agents.json",
    },
}


def generate_openapi(module_path: str) -> dict:
    """Generate OpenAPI spec from FastAPI application.

    Args:
        module_path: Import path in format 'module.submodule:app_object'

    Returns:
        OpenAPI specification as dictionary

    Raises:
        ValueError: If module_path format is invalid
        ImportError: If module cannot be imported
        AttributeError: If app object not found in module
    """
    # Validate module path format
    if ":" not in module_path:
        raise ValueError(
            f"Invalid module_path: {module_path!r}. "
            "Expected format: 'module.submodule:app_object'"
        )

    module_name, app_object = module_path.split(":", 1)
    if not module_name or not app_object:
        raise ValueError(
            f"Invalid module_path: {module_path!r}. "
            "Both module and app_object are required"
        )

    try:
        # Dynamically import
        import importlib
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(
            f"Failed to import module {module_name!r}: {e}. "
            "Ensure the module is in PYTHONPATH"
        ) from e

    try:
        app = getattr(module, app_object)
    except AttributeError as e:
        raise AttributeError(
            f"App object {app_object!r} not found in {module_name}. "
            f"Available attributes: {dir(module)}"
        ) from e

    # Generate OpenAPI
    return app.openapi()


def format_openapi(spec: dict) -> str:
    """Format OpenAPI spec with consistent formatting."""
    return json.dumps(spec, indent=2, ensure_ascii=False, sort_keys=False)


def update_openapi_file(output_path: Path, new_spec: dict, dry_run: bool = False) -> bool:
    """Update OpenAPI file with new spec.

    Returns True if file was changed.
    """
    formatted = format_openapi(new_spec)

    if dry_run:
        if output_path.exists():
            current = output_path.read_text(encoding='utf-8')
            if current.strip() == formatted.strip():
                print(f"✅ {output_path} - No changes needed")
                return False
            else:
                print(f"📝 {output_path} - Would update (dry-run)")
                return True
        else:
            print(f"📝 {output_path} - Would create (dry-run)")
            return True

    # Write file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(formatted, encoding='utf-8')
    print(f"✅ {output_path} - Updated")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI specification from FastAPI app"
    )
    parser.add_argument(
        "--layer",
        choices=list(LAYERS.keys()),
        required=True,
        help="Layer to generate OpenAPI for",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path (default: use layer's default)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if spec is up-to-date (exit non-zero if not)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate for all layers",
    )

    args = parser.parse_args()

    layers_to_generate = []

    if args.all:
        layers_to_generate = list(LAYERS.keys())
    else:
        layers_to_generate = [args.layer]

    changed = False

    for layer in layers_to_generate:
        config = LAYERS[layer]
        output_path = args.output or Path(config["default_output"])
        module_path = config["module"]

        print(f"\n📦 Processing {layer}...")
        print(f"   Module: {module_path}")
        print(f"   Output: {output_path}")

        try:
            # Change to value-fabric directory for proper imports
            import os
            original_dir = os.getcwd()

            layer_dir = Path(f"services/{layer}")
            if layer_dir.exists():
                os.chdir(layer_dir)
                sys.path.insert(0, str(Path("src").absolute()))

            # Generate spec
            spec = generate_openapi(module_path)

            # Restore directory
            os.chdir(original_dir)

            # Update file
            was_changed = update_openapi_file(
                output_path,
                spec,
                dry_run=args.dry_run or args.check,
            )

            if was_changed:
                changed = True

            # Print stats
            paths_count = len(spec.get("paths", {}))
            schemas_count = len(spec.get("components", {}).get("schemas", {}))
            print(f"   Stats: {paths_count} paths, {schemas_count} schemas")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            if args.check:
                sys.exit(1)

    if args.check and changed:
        print("\n⚠️  OpenAPI specs are out of date!")
        print("   Run without --check to regenerate")
        sys.exit(1)

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
