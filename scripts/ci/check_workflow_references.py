#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
from typing import Any
import yaml
from yaml import YAMLError

ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / 'Makefile'
MAKE_TARGET_RE = re.compile(r'(?:^|\s)\bmake\b\s+([^\n#]+)')
SCRIPT_TOKEN_RE = re.compile(r'(?:^|\s)(?:python3?|bash|sh|node)\s+([^\s\\]+)')
PNPM_CMD_RE = re.compile(r"(?:^|\s)\bpnpm\b\s+([^\n#]+)")
# pnpm subcommands that are not package.json scripts
PNPM_SUBCOMMANDS = {"install", "add", "remove", "exec", "dlx", "fetch", "import", "list", "outdated", "publish", "pack", "prune", "rebuild", "unlink", "update", "upgrade", "audit"}


def load_make_targets() -> set[str]:
    out = set()
    for line in MAKEFILE.read_text(encoding='utf-8', errors='ignore').splitlines():
        if line.startswith(('\t', ' ')) or ':' not in line:
            continue
        head = line.split(':', 1)[0].strip()
        if not head or head.startswith('.') or '=' in head:
            continue
        for t in head.split():
            if re.fullmatch(r'[A-Za-z0-9_.\-/]+', t):
                out.add(t)
    return out


def _strip_shell_punct(tok: str) -> str:
    """Strip trailing shell punctuation / quotes pulled in from echo strings."""
    return tok.rstrip("'\";|&),`")


def _first_shell_token(chunk: str) -> str | None:
    for tok in re.split(r'\s+', chunk.strip()):
        if not tok or tok.startswith('-') or '=' in tok:
            continue
        if tok in {'&&', '||', '|', ';', '\\'}:
            break
        return _strip_shell_punct(tok)
    return None


def extract_make_targets(run: str) -> list[str]:
    ts = []
    for chunk in MAKE_TARGET_RE.findall(run):
        tok = _first_shell_token(chunk)
        if tok:
            ts.append(tok)
    return ts


def load_pnpm_scripts(package_json: Path) -> set[str]:
    if not package_json.exists():
        return set()
    data = yaml.safe_load(package_json.read_text(encoding='utf-8', errors='ignore')) or {}
    scripts = data.get('scripts', {}) if isinstance(data, dict) else {}
    return set(scripts.keys()) if isinstance(scripts, dict) else set()


def resolve_working_dir(job: dict[str, Any], step: dict[str, Any], root: Path) -> Path:
    step_wd = step.get('working-directory')
    if isinstance(step_wd, str) and step_wd:
        return root / step_wd
    defaults = job.get('defaults') if isinstance(job, dict) else None
    run_defaults = defaults.get('run') if isinstance(defaults, dict) else None
    job_wd = run_defaults.get('working-directory') if isinstance(run_defaults, dict) else None
    if isinstance(job_wd, str) and job_wd:
        return root / job_wd
    return root


def extract_pnpm_scripts(run: str, step: dict[str, Any], job: dict[str, Any]) -> list[tuple[Path, str]]:
    out = []
    for chunk in PNPM_CMD_RE.findall(run):
        tokens = re.split(r'\s+', chunk.strip())
        if not tokens:
            continue
        package_json = resolve_working_dir(job, step, ROOT) / 'package.json'
        script = None
        if tokens[0] == 'run' and len(tokens) >= 2 and not tokens[1].startswith('-'):
            script = _strip_shell_punct(tokens[1])
        elif tokens[0].startswith('--dir'):
            if '=' in tokens[0]:
                dir_value = tokens[0].split('=', 1)[1]
                sub_tokens = tokens[1:]
            elif len(tokens) >= 3:
                dir_value = tokens[1]
                sub_tokens = tokens[2:]
            else:
                continue
            package_json = ROOT / dir_value / 'package.json'
            if 'run' in sub_tokens:
                run_idx = sub_tokens.index('run')
                if run_idx + 1 < len(sub_tokens):
                    script = _strip_shell_punct(sub_tokens[run_idx + 1])
            else:
                for tok in sub_tokens:
                    if tok.startswith('-'):
                        continue
                    if tok not in PNPM_SUBCOMMANDS:
                        script = _strip_shell_punct(tok)
                    break
        if script:
            out.append((package_json, script))
    return out


def script_exists(token: str, step_wd: Path) -> bool:
    token = token.strip().strip("'\"")
    if not token or token.startswith('${{') or token.startswith('/') or '*' in token or '?' in token:
        return False
    # Try repo-root relative first, then working-directory relative.
    candidates = [ROOT / token, step_wd / token]
    for candidate in candidates:
        try:
            candidate.relative_to(ROOT)
        except ValueError:
            continue
        if candidate.exists():
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--workflow-glob', default='*.yml')
    args = ap.parse_args()
    workflows = sorted((ROOT / '.github/workflows').glob(args.workflow_glob))
    make_targets = load_make_targets()
    errors = []
    for wf in workflows:
        try:
            data = yaml.safe_load(wf.read_text(encoding='utf-8', errors='ignore')) or {}
        except YAMLError as exc:
            print(f'warning: skipping non-parseable workflow file {wf}: {exc}')
            continue
        for job, jobdef in (data.get('jobs') or {}).items():
            if not isinstance(jobdef, dict):
                continue
            steps = [s for s in jobdef.get('steps', []) if isinstance(s, dict)]
            run_text = '\n'.join(str(step.get('run', '')) for step in steps)

            for t in extract_make_targets(run_text):
                if t not in make_targets:
                    errors.append(f"{wf}: job '{job}' references missing make target '{t}'")

            for step in steps:
                if not isinstance(step, dict):
                    continue
                run = step.get('run', '')
                step_wd = resolve_working_dir(jobdef, step, ROOT)
                if isinstance(run, str):
                    for sc in SCRIPT_TOKEN_RE.findall(run):
                        if '/' in sc and not script_exists(sc, step_wd):
                            errors.append(f"{wf}: job '{job}' references missing script/path '{sc}'")
                    for package_json, script in extract_pnpm_scripts(run, step, jobdef):
                        if script not in load_pnpm_scripts(package_json):
                            errors.append(f"{wf}: job '{job}' references missing pnpm script '{script}'")
    if errors:
        print('Workflow reference check failed:\n')
        print('\n'.join(f'- {e}' for e in errors))
        return 1
    print('Workflow reference check passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
