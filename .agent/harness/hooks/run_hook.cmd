@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "VENV_PY=%SCRIPT_DIR%..\..\..\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
  "%VENV_PY%" %*
) else (
  python %*
)
