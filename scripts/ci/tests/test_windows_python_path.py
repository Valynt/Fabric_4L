"""Regression tests for Windows Python path handling in mypy wrappers.

Background:
    On Windows, ``sys.executable`` is a path like::

        C:\\Users\\BBB\\AppData\\Roaming\\uv\\python\\cpython-3.11-windows-x86_64-none\\python.exe

    If that path is stringified and run through ``shlex.split(..., posix=True)``
    or manually space-split, the backslashes are stripped and the path becomes
    ``C:UsersBBB.cachepre-commit...python.EXE`` (broken).  These tests verify
    that the mypy-wrapper scripts build their subprocess command as a list
    (one element per argument) using ``sys.executable`` directly, so paths
    containing backslashes and spaces survive intact.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import mock

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    module_path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_mypy_baseline = _load_script("check_mypy_baseline")
run_mypy_layer = _load_script("run_mypy_layer")

REPO_ROOT = _SCRIPTS_DIR.parents[1]


def _windows_executable() -> str:
    """Return a Windows-style executable path containing backslashes and spaces."""
    return r"C:\Users\Test User\.cache\uv\python\cpython-3.11\python.exe"


def test_check_mypy_baseline_passes_executable_as_single_argument() -> None:
    """``check_mypy_baseline._run_mypy`` must pass ``sys.executable`` as one
    list element — never string-split or backslash-strip it."""
    fake_exe = _windows_executable()
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["cwd"] = kwargs.get("cwd")
        return mock.Mock(stdout="", stderr="", returncode=0)

    with mock.patch.object(check_mypy_baseline.sys, "executable", fake_exe):
        with mock.patch.object(check_mypy_baseline.subprocess, "run", fake_run):
            check_mypy_baseline._run_mypy(
                Path("services/layer1-ingestion"),
                ["src"],
                [],
            )

    cmd = list(captured["cmd"])  # type: ignore[arg-type]
    # The executable must be the first element, exactly as-is — no stripping.
    assert cmd[0] == fake_exe, (
        f"Expected executable to be passed as one argument ({fake_exe!r}); "
        f"got {cmd[0]!r}. The path must retain its backslashes and spaces."
    )
    # The second element must be the module flag, not part of a split path.
    assert cmd[1] == "-m", f"Expected '-m' as second arg; got {cmd[1]!r}"
    assert cmd[2] == "mypy", f"Expected 'mypy' as third arg; got {cmd[2]!r}"


def test_run_mypy_layer_passes_executable_as_single_argument() -> None:
    """``run_mypy_layer._build_mypy_command`` must pass ``sys.executable`` as
    one list element when the ``mypy`` console-script is not on PATH."""
    fake_exe = _windows_executable()

    def fake_which(name: str) -> str | None:
        return None  # Simulate Windows where `mypy` is not on PATH

    with mock.patch.object(run_mypy_layer.sys, "executable", fake_exe):
        with mock.patch.object(run_mypy_layer.shutil, "which", fake_which):
            cmd = run_mypy_layer._build_mypy_command(["src"], [])

    assert cmd[0] == fake_exe, (
        f"Expected executable to be passed as one argument ({fake_exe!r}); "
        f"got {cmd[0]!r}. The path must retain its backslashes and spaces."
    )
    assert cmd[1] == "-m", f"Expected '-m' as second arg; got {cmd[1]!r}"
    assert cmd[2] == "mypy", f"Expected 'mypy' as third arg; got {cmd[2]!r}"


def test_no_hardcoded_user_path_in_mypy_wrappers() -> None:
    """No user-specific absolute path (e.g. ``C:\\Users\\BBB``) may be
    hardcoded in the mypy-wrapper scripts."""
    forbidden = b"C:\\Users\\BBB"
    for script in (
        REPO_ROOT / "scripts" / "ci" / "check_mypy_baseline.py",
        REPO_ROOT / "scripts" / "ci" / "run_mypy_layer.py",
        REPO_ROOT / "scripts" / "ci" / "check_mypy_changed_files.py",
        REPO_ROOT / "scripts" / "ci" / "check_mypy_typed_core.py",
    ):
        content = script.read_bytes()
        assert forbidden not in content, (
            f"{script} contains hardcoded user path {forbidden!r}; "
            f"use sys.executable instead."
        )


def test_check_mypy_baseline_does_not_use_shlex_or_shell() -> None:
    """The wrapper must not use ``shell=True`` or ``shlex.split`` which would
    mangle Windows paths."""
    source = (
        REPO_ROOT / "scripts" / "ci" / "check_mypy_baseline.py"
    ).read_text(encoding="utf-8")
    assert "shell=True" not in source, (
        "check_mypy_baseline.py must not use shell=True; it mangles Windows paths."
    )
    assert "shlex.split" not in source, (
        "check_mypy_baseline.py must not use shlex.split; it strips backslashes "
        "from Windows paths when called with posix=True."
    )


def test_run_mypy_layer_does_not_use_shlex_or_shell() -> None:
    """The wrapper must not use ``shell=True`` or ``shlex.split``."""
    source = (
        REPO_ROOT / "scripts" / "ci" / "run_mypy_layer.py"
    ).read_text(encoding="utf-8")
    assert "shell=True" not in source, (
        "run_mypy_layer.py must not use shell=True; it mangles Windows paths."
    )
    assert "shlex.split" not in source, (
        "run_mypy_layer.py must not use shlex.split; it strips backslashes "
        "from Windows paths when called with posix=True."
    )


def test_semgrep_hook_uses_system_language_not_python_venv() -> None:
    """The pre-commit semgrep hook must use ``language: system`` (invoking
    ``semgrep`` from PATH) rather than ``language: python`` (which creates a
    pre-commit virtualenv whose console-script shebang mangles the Windows
    Python path)."""
    cfg = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    # Find the semgrep hook block
    semgrep_start = cfg.find("semgrep")
    assert semgrep_start != -1, "semgrep hook not found in .pre-commit-config.yaml"
    # Grab a generous slice around the semgrep hook
    block = cfg[semgrep_start : semgrep_start + 400]
    assert "language: system" in block, (
        "semgrep hook must use 'language: system' to invoke semgrep from PATH; "
        "'language: python' creates a pre-commit venv whose console-script "
        "shebang has backslashes stripped on Windows."
    )


def test_check_mypy_baseline_fails_closed_on_tooling_error() -> None:
    """When mypy exits non-zero with no parseable diagnostics (tooling
    failure: mypy not installed, invalid args, config error), the ratchet
    must fail closed — not silently report 'baseline OK' with 0 errors."""
    fake_result = mock.Mock(stdout="", stderr="mypy: command not found", returncode=2)
    with mock.patch.object(check_mypy_baseline.subprocess, "run", return_value=fake_result):
        with pytest.raises(check_mypy_baseline.MypyInvocationError):
            check_mypy_baseline._run_mypy(
                Path("services/layer1-ingestion"),
                ["src"],
                [],
            )


def test_check_mypy_baseline_passes_when_mypy_succeeds() -> None:
    """A successful mypy run (returncode 0, empty output) must not raise."""
    fake_result = mock.Mock(stdout="", stderr="", returncode=0)
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return fake_result

    with mock.patch.object(check_mypy_baseline.subprocess, "run", fake_run):
        output = check_mypy_baseline._run_mypy(
            Path("services/layer1-ingestion"),
            ["src"],
            [],
        )
    assert output == ""


def test_check_mypy_baseline_passes_when_mypy_reports_real_errors() -> None:
    """When mypy exits non-zero but produces real ``file:line: error:``
    diagnostics, the ratchet must parse them — not treat it as a tooling
    failure."""
    fake_output = (
        "services/layer1/src/foo.py:10: error: Function is missing a return type annotation  [no-untyped-def]\n"
    )
    fake_result = mock.Mock(stdout=fake_output, stderr="", returncode=1)
    with mock.patch.object(check_mypy_baseline.subprocess, "run", return_value=fake_result):
        output = check_mypy_baseline._run_mypy(
            Path("services/layer1-ingestion"),
            ["src"],
            [],
        )
    assert "foo.py:10: error" in output
