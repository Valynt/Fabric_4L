from __future__ import annotations

#!/usr/bin/env python3
"""Generate Layer 5 OpenAPI, normalize it, and diff against committed contract."""


import argparse
import difflib
import json
import sys
from pathlib import Path


def _normalize_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _load_runtime_openapi(repo_root: Path, canonical_src: Path) -> object:
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(canonical_src))
    try:
        from layer5_ground_truth.api.main import app  # pylint: disable=import-outside-toplevel
        return app.openapi()
    except Exception as exc:
        print(f"ERROR: failed to load runtime OpenAPI: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate Layer 5 OpenAPI, normalize it, and diff against committed contract."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root directory (default: auto-detected)",
    )
    parser.add_argument(
        "--contract-path",
        type=Path,
        default=None,
        help="Path to committed OpenAPI contract JSON (default: REPO_ROOT/contracts/openapi/layer5-ground-truth.json)",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root
    service_root = repo_root / "services" / "layer5-ground-truth"
    canonical_src = service_root / "src"
    contract_path: Path = args.contract_path or repo_root / "contracts" / "openapi" / "layer5-ground-truth.json"

    generated_openapi = _load_runtime_openapi(repo_root, canonical_src)
    normalized_generated = _normalize_json(generated_openapi)

    if not contract_path.exists():
        print(f"Contract file missing: {contract_path}", file=sys.stderr)
        return 1

    try:
        raw_contract = contract_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read contract file: {exc}", file=sys.stderr)
        return 1

    normalized_committed = _normalize_json(json.loads(raw_contract))

    if normalized_generated == normalized_committed:
        print("Layer 5 OpenAPI contract is up to date.")
        return 0

    diff = difflib.unified_diff(
        normalized_committed.splitlines(keepends=True),
        normalized_generated.splitlines(keepends=True),
        fromfile=str(contract_path),
        tofile="generated:layer5_ground_truth.api.main:app.openapi()",
    )
    print("".join(diff), end="")
    print(
        "\nOpenAPI drift detected for Layer 5. "
        "Regenerate contracts/openapi/layer5-ground-truth.json from canonical runtime source and commit it.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
