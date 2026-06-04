from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_path(relative_path: str) -> Path:
    return REPO_ROOT / relative_path


def read_text(relative_path: str) -> str:
    return repo_path(relative_path).read_text(encoding="utf-8")


def read_json(relative_path: str) -> dict[str, Any]:
    return json.loads(read_text(relative_path))


def read_yaml(relative_path: str) -> Any:
    return yaml.safe_load(read_text(relative_path))


def read_yaml_documents(relative_path: str) -> list[Any]:
    return [doc for doc in yaml.safe_load_all(read_text(relative_path)) if doc]


def env_example_keys() -> set[str]:
    keys: set[str] = set()
    for raw_line in read_text(".env.example").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _value = line.split("=", 1)
        keys.add(key.strip())
    return keys


def package_scripts() -> dict[str, str]:
    return read_json("package.json").get("scripts", {})
