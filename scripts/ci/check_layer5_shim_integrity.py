#!/usr/bin/env python3
"""Guard that value_fabric/layer5 remains removed or compatibility shims only."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_CHECK_PATH = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "layer5-ground-truth"
    / "scripts"
    / "check_no_duplicate_modules.py"
)
_SPEC = importlib.util.spec_from_file_location("layer5_source_contract", _CHECK_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_layer5_source_contract = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_layer5_source_contract)


def main(argv: list[str] | None = None) -> int:
    return _layer5_source_contract.main(argv=argv)


if __name__ == "__main__":
    raise SystemExit(main())
