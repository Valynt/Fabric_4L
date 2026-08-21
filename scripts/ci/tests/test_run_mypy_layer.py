from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parents[1] / "run_mypy_layer.py"
SPEC = importlib.util.spec_from_file_location("run_mypy_layer", MODULE_PATH)
run_mypy_layer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_mypy_layer)


def test_missing_service_directory_returns_usage_error(tmp_path: Path, capsys) -> None:
    missing_service = tmp_path / "missing-service"

    result = run_mypy_layer.main([str(missing_service), "src/"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Service directory not found" in captured.err


def test_missing_paths_returns_usage_error(tmp_path: Path, capsys) -> None:
    service_dir = tmp_path / "service"
    service_dir.mkdir()

    result = run_mypy_layer.main([str(service_dir), "--", "--strict"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Usage: run_mypy_layer.py" in captured.err


def test_missing_mypy_falls_back_to_sys_executable(tmp_path: Path, monkeypatch) -> None:
    """When the `mypy` console-script is not on PATH (Windows), fall back to
    `sys.executable -m mypy` so the wrapper works cross-platform."""
    service_dir = tmp_path / "service"
    service_dir.mkdir()
    monkeypatch.setattr(run_mypy_layer.shutil, "which", lambda executable: None)
    calls: list[dict[str, object]] = []

    def fake_run(command, *, cwd, check):
        calls.append({"command": command, "cwd": cwd, "check": check})
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(run_mypy_layer.subprocess, "run", fake_run)
    sentinel = "/sentinel/python"
    monkeypatch.setattr(run_mypy_layer.sys, "executable", sentinel)

    result = run_mypy_layer.main([str(service_dir), "src/"])

    assert result == 7
    assert calls == [
        {
            "command": [sentinel, "-m", "mypy", "src/"],
            "cwd": service_dir,
            "check": False,
        }
    ]


def test_invokes_mypy_from_service_dir_with_paths_and_flags(tmp_path: Path, monkeypatch) -> None:
    service_dir = tmp_path / "service"
    service_dir.mkdir()
    calls: list[dict[str, object]] = []

    def fake_run(command, *, cwd, check):
        calls.append({"command": command, "cwd": cwd, "check": check})
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(run_mypy_layer.shutil, "which", lambda executable: "mypy-bin")
    monkeypatch.setattr(run_mypy_layer.subprocess, "run", fake_run)

    result = run_mypy_layer.main([str(service_dir), "src/", "tests/", "--", "--strict", "--warn-return-any"])

    assert result == 7
    assert calls == [
        {
            "command": ["mypy-bin", "src/", "tests/", "--strict", "--warn-return-any"],
            "cwd": service_dir,
            "check": False,
        }
    ]
