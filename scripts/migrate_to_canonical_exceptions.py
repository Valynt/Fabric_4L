#!/usr/bin/env python3
"""Codemod: migrate safe `raise HTTPException(...)` callsites to canonical exceptions.

Targets:
- services/*/src/**/*.py
- value_fabric/**/api/routes/**/*.py

This codemod only rewrites semantically-safe cases and emits a migration report with
transformed files plus skipped callsites that require manual review.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import libcst as cst
from libcst import matchers as m

CANONICAL_MODULE = "value_fabric.shared.error_handling.exceptions"
STATUS_TO_CLASS = {
    400: "ValidationError",
    401: "AuthenticationError",
    403: "AuthorizationError",
    404: "NotFoundError",
    429: "RateLimitError",
    503: "ServiceUnavailableError",
}


@dataclass
class Skip:
    path: str
    line: int
    reason: str


class RaiseTransformer(cst.CSTTransformer):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.used_classes: set[str] = set()
        self.changed = 0
        self.skips: list[Skip] = []

    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)

    def leave_Raise(self, original_node: cst.Raise, updated_node: cst.Raise) -> cst.BaseStatement:
        exc = original_node.exc
        if not exc or not m.matches(exc, m.Call(func=m.Name("HTTPException"))):
            return updated_node

        call = exc
        kwargs: dict[str, cst.BaseExpression] = {}
        for arg in call.args:
            if arg.keyword and arg.star == "":
                kwargs[arg.keyword.value] = arg.value
            elif not arg.keyword:
                pos = self.get_metadata(cst.metadata.PositionProvider, original_node).start.line
                self.skips.append(Skip(str(self.path), pos, "positional HTTPException args are not transformed"))
                return updated_node

        if "status_code" not in kwargs or "detail" not in kwargs:
            pos = self.get_metadata(cst.metadata.PositionProvider, original_node).start.line
            self.skips.append(Skip(str(self.path), pos, "missing status_code/detail"))
            return updated_node

        status = _resolve_status_code(kwargs["status_code"])
        if status is None or status not in STATUS_TO_CLASS:
            pos = self.get_metadata(cst.metadata.PositionProvider, original_node).start.line
            self.skips.append(Skip(str(self.path), pos, "status code is dynamic or unmapped"))
            return updated_node

        klass = STATUS_TO_CLASS[status]
        detail = kwargs["detail"]
        new_args = [cst.Arg(keyword=cst.Name("message"), value=_message_expr(detail))]
        if _is_structured(detail):
            new_args.append(cst.Arg(keyword=cst.Name("details"), value=detail))

        new_raise = updated_node.with_changes(exc=cst.Call(func=cst.Name(klass), args=new_args))
        self.used_classes.add(klass)
        self.changed += 1
        return new_raise


def _resolve_status_code(node: cst.BaseExpression) -> int | None:
    if isinstance(node, cst.Integer):
        return int(node.value)
    if isinstance(node, cst.Attribute):
        name = node.attr.value
        if name.startswith("HTTP_"):
            prefix = name.split("_", 2)
            if len(prefix) >= 2 and prefix[1].isdigit():
                return int(prefix[1])
    return None


def _is_structured(node: cst.BaseExpression) -> bool:
    return isinstance(node, (cst.Dict, cst.List, cst.Tuple))


def _message_expr(detail: cst.BaseExpression) -> cst.BaseExpression:
    if isinstance(detail, cst.SimpleString):
        return detail
    if _is_structured(detail):
        return cst.SimpleString('"Request failed"')
    return cst.Call(func=cst.Name("str"), args=[cst.Arg(value=detail)])


def _target_files(repo_root: Path) -> list[Path]:
    services = list((repo_root / "services").glob("*/src/**/*.py"))
    routes = list((repo_root / "value_fabric").glob("**/api/routes/**/*.py"))
    return sorted({p for p in services + routes})


def _remove_http_exception_import_if_unused(source: str) -> str:
    if "HTTPException" in source and "raise HTTPException(" not in source:
        source = source.replace(", HTTPException", "").replace("HTTPException, ", "").replace(" HTTPException", "")
    return source


def run(repo_root: Path, apply: bool) -> dict[str, Any]:
    transformed: list[str] = []
    skipped: list[dict[str, Any]] = []

    for path in _target_files(repo_root):
        text = path.read_text(encoding="utf-8")
        if "raise HTTPException(" not in text:
            continue
        module = cst.metadata.MetadataWrapper(cst.parse_module(text))
        t = RaiseTransformer(path.relative_to(repo_root))
        out = module.visit(t)
        code = out.code

        if t.used_classes:
            import_line = f"from {CANONICAL_MODULE} import {', '.join(sorted(t.used_classes))}\n"
            if import_line not in code:
                code = import_line + code
        code = _remove_http_exception_import_if_unused(code)

        if code != text:
            transformed.append(str(path.relative_to(repo_root)))
            if apply:
                path.write_text(code, encoding="utf-8")

        skipped.extend({"path": s.path, "line": s.line, "reason": s.reason} for s in t.skips)

    return {"transformed_files": transformed, "skipped": skipped}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", type=Path, default=Path("reports/canonical_exception_migration_report.json"))
    args = ap.parse_args()

    report = run(args.repo_root, apply=args.apply)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
