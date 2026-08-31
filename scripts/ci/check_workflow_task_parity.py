"""Keep GitHub and Depot workflow task invocations in lockstep.

The workflow trees intentionally mirror one another.  Provider-specific YAML
may differ, but executable calls into the repository's orchestration surface
must not.  This check compares task calls found in ``run`` steps, in execution
order, while ignoring examples in comments, ``echo``/``printf`` output, and
heredoc bodies.
"""

from __future__ import annotations

import argparse
import difflib
import re
import shlex
import sys
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GITHUB_WORKFLOWS = ROOT / ".github" / "workflows"
DEFAULT_DEPOT_WORKFLOWS = ROOT / ".depot" / "workflows"

WORKFLOW_SUFFIXES = {".yml", ".yaml"}
SHELL_BOUNDARY_CHARS = frozenset(";&|()")
SHELL_PREFIX_WORDS = frozenset(
    {"!", "do", "elif", "else", "if", "then", "until", "while", "{"}
)
COMMAND_WRAPPERS = frozenset({"command", "sudo", "time"})
OUTPUT_COMMANDS = frozenset({"echo", "printf"})
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", re.DOTALL)
GITHUB_EXPRESSION_RE = re.compile(r"\$\{\{.*?\}\}")
HEREDOC_RE = re.compile(r"<<-?\s*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z_][A-Za-z0-9_.-]*))")


class WorkflowReadError(RuntimeError):
    """Raised when a workflow cannot be read as a jobs/steps document."""


def _canonical_github_expression(expression: str) -> str:
    inner = expression[3:-2]
    return "${{ " + " ".join(inner.split()) + " }}"


def _mask_github_expressions(line: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        marker = f"__WORKFLOW_EXPRESSION_{len(replacements)}__"
        replacements[marker] = _canonical_github_expression(match.group(0))
        return marker

    return GITHUB_EXPRESSION_RE.sub(replace, line), replacements


def _restore_expressions(token: str, replacements: Mapping[str, str]) -> str:
    for marker, expression in replacements.items():
        token = token.replace(marker, expression)
    return token


def _logical_shell_lines(run_block: str) -> Iterator[str]:
    """Yield shell lines, joining continuations and excluding heredoc bodies."""

    buffer = ""
    heredoc_delimiters: list[str] = []
    for physical_line in run_block.splitlines():
        if heredoc_delimiters:
            if physical_line.strip() == heredoc_delimiters[0]:
                heredoc_delimiters.pop(0)
            continue

        line = physical_line.rstrip()
        if line.endswith("\\") and not line.endswith("\\\\"):
            buffer += line[:-1] + " "
            continue

        logical_line = buffer + line
        buffer = ""
        yield logical_line

        for match in HEREDOC_RE.finditer(logical_line):
            delimiter = next(group for group in match.groups() if group is not None)
            heredoc_delimiters.append(delimiter)

    if buffer:
        yield buffer.rstrip()


def _shell_segments(line: str) -> Iterator[list[str]]:
    """Split one logical shell line into simple command token lists."""

    masked, replacements = _mask_github_expressions(line)
    lexer = shlex.shlex(masked, posix=True, punctuation_chars=";&|()")
    lexer.commenters = "#"
    lexer.whitespace_split = True

    current: list[str] = []
    try:
        tokens = list(lexer)
    except ValueError:
        # An incomplete quote will fail when the workflow itself executes.  Do
        # not turn this parity guard into a second shell syntax validator.
        return

    for raw_token in tokens:
        if raw_token and set(raw_token) <= SHELL_BOUNDARY_CHARS:
            if current:
                yield [_restore_expressions(token, replacements) for token in current]
                current = []
            continue
        current.append(raw_token)

    if current:
        yield [_restore_expressions(token, replacements) for token in current]


def _strip_command_prefix(tokens: Sequence[str]) -> list[str]:
    remaining = list(tokens)
    while remaining and remaining[0] in SHELL_PREFIX_WORDS:
        remaining.pop(0)

    while remaining and ASSIGNMENT_RE.fullmatch(remaining[0]):
        remaining.pop(0)

    if remaining and remaining[0] == "env":
        remaining.pop(0)
        while remaining and (
            remaining[0].startswith("-") or ASSIGNMENT_RE.fullmatch(remaining[0])
        ):
            remaining.pop(0)

    while remaining and remaining[0] in COMMAND_WRAPPERS:
        wrapper = remaining.pop(0)
        if wrapper == "sudo":
            while remaining and remaining[0].startswith("-"):
                remaining.pop(0)
        elif wrapper == "time" and remaining and remaining[0] == "-p":
            remaining.pop(0)

    return remaining


def _is_fabric_executable(token: str) -> bool:
    return Path(token).name == "fabric"


def _normalize_task_command(tokens: Sequence[str]) -> str | None:
    command = _strip_command_prefix(tokens)
    if not command or command[0] in OUTPUT_COMMANDS:
        return None

    engine: str
    arguments: list[str]
    if Path(command[0]).name == "make":
        engine = "make"
        arguments = command[1:]
    elif _is_fabric_executable(command[0]):
        engine = "fabric"
        arguments = command[1:]
        if arguments[:1] == ["run"]:
            arguments.pop(0)
    elif command[:3] == ["pnpm", "run", "fabric"]:
        engine = "fabric"
        arguments = command[3:]
        if arguments[:1] == ["--"]:
            arguments.pop(0)
    elif (
        len(command) >= 3
        and command[:2] == ["pnpm", "exec"]
        and _is_fabric_executable(command[2])
    ):
        engine = "fabric"
        arguments = command[3:]
    else:
        return None

    # A bare engine invocation does not select a task and therefore cannot
    # drift the workflow task graph.
    if not arguments:
        return None
    return shlex.join([engine, *arguments])


def extract_task_commands(run_block: str) -> list[str]:
    """Return normalized Make/Fabric calls from a workflow ``run`` value."""

    commands: list[str] = []
    for line in _logical_shell_lines(run_block):
        for segment in _shell_segments(line):
            normalized = _normalize_task_command(segment)
            if normalized is not None:
                commands.append(normalized)
    return commands


def _iter_matrix_commands(value: object) -> Iterator[str]:
    """Yield command fields from a strategy matrix in declaration order."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == "command":
                if not isinstance(child, str):
                    raise WorkflowReadError(
                        "strategy matrix 'command' must be a string"
                    )
                yield child
            else:
                yield from _iter_matrix_commands(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_matrix_commands(child)


def _iter_task_command_sources(workflow: Mapping[str, Any]) -> Iterator[str]:
    jobs = workflow.get("jobs", {})
    if not isinstance(jobs, Mapping):
        raise WorkflowReadError("top-level 'jobs' must be a mapping")

    for job_name, job in jobs.items():
        if not isinstance(job, Mapping):
            raise WorkflowReadError(f"job {job_name!r} must be a mapping")
        strategy = job.get("strategy", {})
        if strategy is not None and not isinstance(strategy, Mapping):
            raise WorkflowReadError(f"job {job_name!r} 'strategy' must be a mapping")
        if isinstance(strategy, Mapping):
            yield from _iter_matrix_commands(strategy.get("matrix", {}))

        steps = job.get("steps", [])
        if steps is None:
            continue
        if not isinstance(steps, list):
            raise WorkflowReadError(f"job {job_name!r} 'steps' must be a list")
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, Mapping):
                raise WorkflowReadError(
                    f"job {job_name!r} step {index} must be a mapping"
                )
            run = step.get("run")
            if run is None:
                continue
            if not isinstance(run, str):
                raise WorkflowReadError(
                    f"job {job_name!r} step {index} 'run' must be a string"
                )
            yield run


def load_workflow_task_commands(path: Path) -> list[str]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise WorkflowReadError(str(exc)) from exc
    if not isinstance(document, Mapping):
        raise WorkflowReadError("top-level document must be a mapping")

    commands: list[str] = []
    for source in _iter_task_command_sources(document):
        commands.extend(extract_task_commands(source))
    return commands


def _workflow_files(directory: Path) -> dict[str, Path]:
    if not directory.is_dir():
        raise WorkflowReadError(f"workflow directory does not exist: {directory}")
    return {
        path.name: path
        for path in sorted(directory.iterdir())
        if path.is_file() and path.suffix in WORKFLOW_SUFFIXES
    }


def compare_workflow_directories(github_dir: Path, depot_dir: Path) -> list[str]:
    """Return human-readable parity errors for two workflow directories."""

    try:
        github_files = _workflow_files(github_dir)
        depot_files = _workflow_files(depot_dir)
    except WorkflowReadError as exc:
        return [str(exc)]

    errors: list[str] = []
    for name in sorted(github_files.keys() - depot_files.keys()):
        errors.append(f"missing Depot workflow pair for {github_files[name]}")
    for name in sorted(depot_files.keys() - github_files.keys()):
        errors.append(f"missing GitHub workflow pair for {depot_files[name]}")

    for name in sorted(github_files.keys() & depot_files.keys()):
        github_path = github_files[name]
        depot_path = depot_files[name]
        try:
            github_commands = load_workflow_task_commands(github_path)
        except WorkflowReadError as exc:
            errors.append(f"cannot inspect {github_path}: {exc}")
            continue
        try:
            depot_commands = load_workflow_task_commands(depot_path)
        except WorkflowReadError as exc:
            errors.append(f"cannot inspect {depot_path}: {exc}")
            continue

        if github_commands == depot_commands:
            continue

        diff = "\n".join(
            difflib.unified_diff(
                github_commands,
                depot_commands,
                fromfile=str(github_path),
                tofile=str(depot_path),
                lineterm="",
            )
        )
        errors.append(f"{name}: ordered task commands differ\n{diff}")

    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare executable task commands in paired GitHub and Depot workflows"
    )
    parser.add_argument("--github-dir", type=Path, default=DEFAULT_GITHUB_WORKFLOWS)
    parser.add_argument("--depot-dir", type=Path, default=DEFAULT_DEPOT_WORKFLOWS)
    args = parser.parse_args(argv)

    errors = compare_workflow_directories(args.github_dir, args.depot_dir)
    if errors:
        print("Workflow task-command parity check failed:\n", file=sys.stderr)
        print("\n\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1

    print("Workflow task-command parity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
