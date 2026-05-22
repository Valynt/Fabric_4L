#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
MAKEFILE = ROOT / "Makefile"
ROOT_PACKAGE_JSON = ROOT / "package.json"
WEB_PACKAGE_JSON = ROOT / "apps/web/package.json"

MAKE_CMD_RE = re.compile(r"(?:^|[;&|]\s*)make\s+([^\n#]+)")
PNPM_CMD_RE = re.compile(r"(?:^|[;&|]\s*)pnpm\s+([^\n#]+)")
PYTEST_CMD_RE = re.compile(r"(?:^|[;&|]\s*)(?:python\s+-m\s+)?pytest\s+([^\n#]+)")
ARTIFACT_TOKEN_RE = re.compile(r"(?:>|>>|tee\s+)([^\s|;&]+)")
PATH_LIKE_RE = re.compile(r"(?<![\w./-])([\w.-]+/[\w./*-]+)")



def load_make_targets() -> set[str]:
    targets: set[str] = set()
    for line in MAKEFILE.read_text(encoding="utf-8").splitlines():
        if line.startswith(("\t", " ")) or ":" not in line:
            continue
        head = line.split(":", 1)[0].strip()
        if not head or head.startswith(".") or "=" in head:
            continue
        for token in head.split():
            if re.fullmatch(r"[A-Za-z0-9_.\-/]+", token):
                targets.add(token)
    return targets


def load_pnpm_scripts(package_json: Path) -> set[str]:
    if not package_json.exists():
        return set()
    data = yaml.safe_load(package_json.read_text(encoding="utf-8"))
    scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
    return set(scripts.keys())


def _first_non_flag(tokens: list[str]) -> str | None:
    for token in tokens:
        if token.startswith("-"):
            continue
        if token in {"&&", "||", "|", ";", "\\"}:
            return None
        return token
    return None


def extract_make_targets(text: str) -> list[str]:
    out: list[str] = []
    for chunk in MAKE_CMD_RE.findall(text):
        try:
            tokens = shlex.split(chunk)
        except ValueError:
            tokens = chunk.split()
        target = _first_non_flag([t for t in tokens if "=" not in t])
        if target:
            out.append(target)
    return out


def extract_pnpm_targets(text: str) -> list[tuple[str | None, str]]:
    out: list[tuple[str | None, str]] = []
    for chunk in PNPM_CMD_RE.findall(text):
        try:
            tokens = shlex.split(chunk)
        except ValueError:
            tokens = chunk.split()
        if not tokens:
            continue
        if tokens[0] == "run" and len(tokens) >= 2:
            if not tokens[1].startswith("-"):
                out.append((None, tokens[1]))
        elif tokens[0].startswith("--dir"):
            run_idx = next((i for i, t in enumerate(tokens) if t == "run"), None)
            if run_idx is not None and run_idx + 1 < len(tokens):
                out.append(("apps/web", tokens[run_idx + 1]))
    return out


def extract_pytest_targets(text: str) -> list[str]:
    out: list[str] = []
    for chunk in PYTEST_CMD_RE.findall(text):
        try:
            tokens = shlex.split(chunk)
        except ValueError:
            tokens = chunk.split()
        for token in tokens:
            if token.startswith("-"):
                continue
            if token.endswith(".py") or "/" in token:
                out.append(token)
    return out


def normalize_path(token: str) -> str | None:
    token = token.strip().strip("'\"")
    if not token or "${{" in token or token.startswith("$"):
        return None
    if token.startswith("/"):
        return None
    return token


def collect_produced_paths(step_runs: list[str]) -> set[str]:
    produced: set[str] = set()
    for run in step_runs:
        for match in ARTIFACT_TOKEN_RE.findall(run):
            path = normalize_path(match)
            if path:
                produced.add(path)
        for match in PATH_LIKE_RE.findall(run):
            path = normalize_path(match)
            if path:
                produced.add(path)
    return produced


def expand_artifact_paths(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workflow command targets and artifact paths")
    parser.add_argument("--workflow-glob", default="*.yml")
    args = parser.parse_args()

    workflows = sorted(WORKFLOWS_DIR.glob(args.workflow_glob))
    make_targets = load_make_targets()
    root_pnpm_scripts = load_pnpm_scripts(ROOT_PACKAGE_JSON)
    web_pnpm_scripts = load_pnpm_scripts(WEB_PACKAGE_JSON)

    errors: list[str] = []
    for workflow in workflows:
        data = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
        jobs = data.get("jobs") or {}
        for job_name, job in jobs.items():
            steps = [s for s in (job.get("steps") or []) if isinstance(s, dict)]
            run_steps = [str(step.get("run", "")) for step in steps]
            produced_paths = collect_produced_paths(run_steps)

            run_text = "\n".join(run_steps)
            for target in extract_make_targets(run_text):
                if target not in make_targets:
                    errors.append(f"{workflow}: job '{job_name}' references missing make target '{target}'")
            for script_dir, script in extract_pnpm_targets(run_text):
                available = web_pnpm_scripts if script_dir == "apps/web" else root_pnpm_scripts
                if script not in available:
                    errors.append(f"{workflow}: job '{job_name}' references missing pnpm script '{script}'")
            for test_path in extract_pytest_targets(run_text):
                if normalize_path(test_path) and not (ROOT / test_path).exists():
                    errors.append(f"{workflow}: job '{job_name}' references missing pytest target '{test_path}'")

            for step in steps:
                if not str(step.get("uses", "")).startswith("actions/upload-artifact"):
                    continue
                artifact_paths = expand_artifact_paths(str((step.get("with") or {}).get("path", "")))
                for path in artifact_paths:
                    if "${{" in path:
                        continue
                    if path.startswith(".") or path in run_text:
                        continue
                    if "*" in path:
                        prefix = path.split("*", 1)[0].rstrip("/")
                        dir_prefix = prefix.rsplit('/', 1)[0] if '/' in prefix else prefix
                        if prefix and not any(p.startswith(prefix) for p in produced_paths) and prefix not in run_text and dir_prefix not in run_text:
                            errors.append(
                                f"{workflow}: job '{job_name}' uploads stale artifact path '{path}' (no producing step found)"
                            )
                        continue
                    clean_path = path.rstrip("/")
                    base_name = Path(clean_path).name
                    prefix_parts = [part for part in clean_path.strip('/').split('/') if part]
                    broad_prefix = '/'.join(prefix_parts[:2]) if prefix_parts else clean_path
                    if (
                        path not in produced_paths
                        and clean_path not in run_text
                        and base_name not in run_text
                        and broad_prefix not in run_text
                        and not (ROOT / path).exists()
                    ):
                        errors.append(
                            f"{workflow}: job '{job_name}' uploads stale artifact path '{path}' (no producing step found)"
                        )

    if errors:
        print("Workflow target/artifact check failed:\n")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print("Workflow target/artifact check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
