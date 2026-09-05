# Agent Skills Promotion (Slice S) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the 15 first-party skills from `.agent/skills/` to a top-level `agents/skills/` tree with per-skill `skill.yaml` manifests, a `MOVED.md` path shim registered in the CDR, and a Layer 4 `audit_orchestrator` update to the canonical path with a legacy fallback.

**Architecture:** A pure `git mv` relocates the skill tree (preserving history); a one-shot Python generator emits 15 `skill.yaml` manifests from `_manifest.jsonl` + `SKILL.md` frontmatter; a `MOVED.md` pointer file (not symlinks) marks the old path; the CDR registers the shim as `COMPAT-SKILLS-001`; Layer 4's `audit_orchestrator` resolves the canonical path first with a legacy fallback; all live references are updated to the new path.

**Tech Stack:** Python 3.12 (PyYAML for manifest generation + L4), Git (rename detection), Markdown (CDR, docs), JSON (lock files).

**Spec:** `docs/superpowers/specs/2026-09-05-agent-skills-promotion-design.md`

## Global Constraints

- pnpm-only monorepo; do not use npm or Yarn. No JS changes in this plan except the three skill lock files (JSON).
- The L4 shim tree at `services/layer4-agents/src/skills/` is a **different path** and must NOT be touched (zero overlap with FAB-106).
- The `.agent/tools/` directory is out of scope — do not move or reference it.
- `skill.yaml` schema is fixed: `apiVersion: fabric.skill/v1`, `kind: Skill`, `metadata: {name, version, description, category}`, `compatibleAgents: [claude-code, copilot, cursor, windsurf, opencode, openclaw, hermes]`, `deprecatedSince: null`, `source: SKILL.md`.
- `compatibleAgents` is exactly: `claude-code, copilot, cursor, windsurf, opencode, openclaw, hermes` (the 7 harnesses in `.agent/install.json`).
- The CDR row must satisfy `scripts/ci/compatibility_registry.py`: path in backticks, review metadata containing "Platform Architecture" + an ISO date.
- The PR for this work must carry labels `compat-shim-change` + `compat-owner-ack` (CI gate `scripts/ci/check_shim_change_ack.py`) because `.agent/skills/MOVED.md` sits under the registered shim path.
- Do NOT add the shim to `contracts/deprecations.json` (DEP-* only) or `tests/baselines/deprecation-budget.json` (deprecated symbols only).
- Windows environment: use backslash paths in shell commands; do not use symlinks.
- Current date: 2026-09-05.

## File Structure

### Created
- `agents/skills/<15 skill dirs>/` — moved from `.agent/skills/` (git mv)
- `agents/skills/_index.md` — moved
- `agents/skills/_manifest.jsonl` — moved
- `agents/skills/<15 skill dirs>/skill.yaml` — 15 new manifests
- `.agent/skills/MOVED.md` — path shim pointer
- `services/layer4-agents/tests/unit/test_audit_orchestrator_skill_paths.py` — new unit test

### Modified
- `docs/governance/compatibility-debt-registry.md` — add `COMPAT-SKILLS-001` row
- `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/config.py` — canonical path + legacy fallback
- `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/analyzers/catalog_checks.py` — `_resolve_skills_root` helper + 3 checks
- `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/analyzers/catalog_definitions.py` — 2 `recommended_fix` strings
- `CLAUDE.md` — skills index path
- `.agent/AGENTS.md` — Skills + Design System sections
- `skills-lock.json`, `.agents/skills.json`, `.agent/skills.json` — `.agent/skills` → `agents/skills`
- `agents/skills/tldraw/SKILL.md` — self-reference
- `agents/skills/frontend-excellence/SKILL.md` — self-reference
- `agents/skills/frontend-excellence/references/subagent-orchestration.md` — self-reference
- `handbook/MIGRATION.md` — `.agent/` row skills mapping
- `.agent/DEPRECATED.md` — skills relocation note

---

### Task 1: Move skills to `agents/skills/` + create MOVED.md shim

**Files:**
- Move: `.agent/skills/*` → `agents/skills/*` (15 skill dirs + `_index.md` + `_manifest.jsonl`)
- Create: `.agent/skills/MOVED.md`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: the canonical `agents/skills/` tree (15 skill dirs, `_index.md`, `_manifest.jsonl`) and the `.agent/skills/MOVED.md` pointer. Later tasks reference `agents/skills/...` paths.

- [ ] **Step 1: Create the target parent and move the tree with `git mv`**

Run (from repo root):
```powershell
New-Item -ItemType Directory -Force -Path agents | Out-Null
git mv .agent/skills agents/skills
```

- [ ] **Step 2: Verify the move preserved history and contents**

Run:
```powershell
git status --short
Get-ChildItem agents/skills -Name
```
Expected: `git status` shows `R` (rename) entries for every file under the old path (e.g. `R  .agent/skills/repo-audit/SKILL.md -> agents/skills/repo-audit/SKILL.md`). `agents/skills/` lists the 15 skill dirs plus `_index.md` and `_manifest.jsonl`. The old `.agent/skills/` directory no longer exists.

- [ ] **Step 3: Create the `MOVED.md` pointer at the old path**

Create `.agent/skills/MOVED.md` with exactly this content:
```markdown
# MOVED

The first-party skills have been promoted from `.agent/skills/` to
`agents/skills/` (Slice S, 2026-09-05).

- Canonical location: `agents/skills/`
- Index: `agents/skills/_index.md`
- Machine-readable manifest: `agents/skills/_manifest.jsonl`
- Per-skill manifests: `agents/skills/<skill>/skill.yaml`

This directory is a temporary path shim registered in the Compatibility
Debt Registry as **COMPAT-SKILLS-001** (target removal 2026-12-31).
Update any references to `.agent/skills/...` to `agents/skills/...`.
```

- [ ] **Step 4: Verify the old path now holds only the pointer**

Run:
```powershell
Get-ChildItem .agent/skills -Name
```
Expected: exactly one entry — `MOVED.md`.

- [ ] **Step 5: Commit**

```powershell
git add .agent/skills/MOVED.md
git commit -m "refactor(skills): promote .agent/skills to agents/skills (Slice S)

Relocate the 15 first-party skills out of the deprecated .agent/ brain into
a top-level agents/skills/ tree. The old path is retained as a MOVED.md
pointer (registered in the CDR as COMPAT-SKILLS-001). Pure rename; no
content changes in this commit."
```

---

### Task 2: Generate 15 `skill.yaml` manifests

**Files:**
- Create: `agents/skills/<15 skill dirs>/skill.yaml`

**Interfaces:**
- Consumes: `agents/skills/_manifest.jsonl` (name → version, category) and each `agents/skills/<skill>/SKILL.md` frontmatter (description).
- Produces: 15 `skill.yaml` files, one per skill dir, each conforming to the fixed schema in Global Constraints.

- [ ] **Step 1: Write the one-shot generator to the session workspace (do NOT commit it)**

Save this to a temp file (e.g. the session workspace) as `generate_skill_manifests.py`:
```python
"""One-shot generator for skill.yaml manifests (Slice S). Not committed."""
import json
import re
from pathlib import Path

import yaml

SKILLS_ROOT = Path("agents/skills")
COMPATIBLE_AGENTS = [
    "claude-code", "copilot", "cursor", "windsurf", "opencode", "openclaw", "hermes",
]

manifest: dict[str, dict] = {}
for line in (SKILLS_ROOT / "_manifest.jsonl").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    entry = json.loads(line)
    manifest[entry["name"]] = entry


def extract_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def derive_description(frontmatter: dict, skill_md: Path, name: str) -> str:
    desc = frontmatter.get("description")
    if desc:
        return " ".join(str(desc).split())  # collapse folded/multi-line to one line
    text = skill_md.read_text(encoding="utf-8")
    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:120]
    return name


generated = []
for skill_dir in sorted(SKILLS_ROOT.iterdir()):
    if not skill_dir.is_dir():
        continue
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        continue
    meta = manifest.get(name, {})
    frontmatter = extract_frontmatter(skill_md)
    doc = {
        "apiVersion": "fabric.skill/v1",
        "kind": "Skill",
        "metadata": {
            "name": name,
            "version": meta.get("version", "unknown"),
            "description": derive_description(frontmatter, skill_md, name),
            "category": meta.get("category", "uncategorized"),
        },
        "compatibleAgents": COMPATIBLE_AGENTS,
        "deprecatedSince": None,
        "source": "SKILL.md",
    }
    out = skill_dir / "skill.yaml"
    out.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    generated.append(name)

print(f"Generated {len(generated)} manifests: {', '.join(generated)}")
```

- [ ] **Step 2: Run the generator from the repo root**

Run:
```powershell
python <path-to-session-workspace>\generate_skill_manifests.py
```
Expected: `Generated 15 manifests: code-quality-improvement, context7-mcp, data-flywheel, data-layer, debug-investigator, deploy-checklist, design-md, frontend-excellence, git-proxy, memory-manager, repo-audit, saas-product-design, skillforge, source-intelligence, tldraw` (order may vary).

- [ ] **Step 3: Verify all 15 manifests exist and conform to the schema**

Run:
```powershell
python -c "import yaml, pathlib; root=pathlib.Path('agents/skills'); files=sorted(root.glob('*/skill.yaml')); assert len(files)==15, f'expected 15, got {len(files)}'; [ (lambda d: (d['apiVersion']=='fabric.skill/v1' or (_ for _ in ()).throw(AssertionError(f.apiVersion))), d['kind']=='Skill' or (_ for _ in ()).throw(AssertionError('kind')), d['metadata']['name']==f.parent.name or (_ for _ in ()).throw(AssertionError('name')), d['compatibleAgents']==['claude-code','copilot','cursor','windsurf','opencode','openclaw','hermes'] or (_ for _ in ()).throw(AssertionError('agents')), d['deprecatedSince'] is None or (_ for _ in ()).throw(AssertionError('dep')), d['source']=='SKILL.md' or (_ for _ in ()).throw(AssertionError('src')))(yaml.safe_load(f.read_text(encoding='utf-8'))) for f in files]; print('OK: 15 manifests valid')"
```
Expected: `OK: 15 manifests valid`. (If the one-liner is awkward to run, write the same assertions into a small temp `.py` file and run it — the assertions are the contract.)

- [ ] **Step 4: Spot-check one manifest**

Run:
```powershell
Get-Content agents/skills/repo-audit/skill.yaml
```
Expected: a valid YAML doc with `apiVersion: fabric.skill/v1`, `kind: Skill`, `metadata.name: repo-audit`, `metadata.version: 2026-06-25`, a one-line `description`, `metadata.category: engineering`, the 7 `compatibleAgents`, `deprecatedSince: null`, `source: SKILL.md`.

- [ ] **Step 5: Commit**

```powershell
git add agents/skills/*/skill.yaml
git commit -m "feat(skills): add skill.yaml manifests to all 15 promoted skills

Each manifest declares apiVersion fabric.skill/v1, kind Skill, metadata
(name/version/description/category), the 7 compatibleAgents, deprecatedSince
null, and source SKILL.md. Version and category are sourced from
_manifest.jsonl; description from SKILL.md frontmatter."
```

---

### Task 3: Register `COMPAT-SKILLS-001` in the CDR

**Files:**
- Modify: `docs/governance/compatibility-debt-registry.md`

**Interfaces:**
- Consumes: the `.agent/skills/MOVED.md` shim from Task 1.
- Produces: a `COMPAT-SKILLS-001` row in the CDR registry table that parses under `scripts/ci/compatibility_registry.py`.

- [ ] **Step 1: Insert the registry row**

In `docs/governance/compatibility-debt-registry.md`, find the last row of the `## Registry` table — the struck-through `COMPAT-BILL-001` row (immediately before the `## Known Intentional Behaviors (Not Shims)` heading). Insert this new row directly after it:
```
| COMPAT-SKILLS-001 | `.agent/skills/` | Path shim (directory relocation pointer) | platform-architecture | First-party skills promoted from `.agent/skills/` to `agents/skills/` (Slice S / S10-B1); old path retained as a `MOVED.md` pointer until all consumers migrate. | 2026-12-31 | Platform Architecture approved 2026-09-05. | PLATARCH-REMOVE-SKILLS-001 |
```

- [ ] **Step 2: Verify the row parses and carries Platform Architecture approval**

Run:
```powershell
python -c "import sys; sys.path.insert(0,'scripts/ci'); import compatibility_registry as cr; es=cr.parse_registry(); ids=[e.shim_id for e in es]; assert 'COMPAT-SKILLS-001' in ids, ids; e=next(x for x in es if x.shim_id=='COMPAT-SKILLS-001'); assert e.path=='.agent/skills/', e.path; assert cr.has_platform_architecture_approval(e.review_metadata), e.review_metadata; print('OK: COMPAT-SKILLS-001 registered and parses')"
```
Expected: `OK: COMPAT-SKILLS-001 registered and parses`.

- [ ] **Step 3: Commit**

```powershell
git add docs/governance/compatibility-debt-registry.md
git commit -m "docs(governance): register COMPAT-SKILLS-001 for the .agent/skills shim

The .agent/skills/ path is retained as a MOVED.md pointer after the Slice S
promotion. Target removal 2026-12-31; Platform Architecture approved
2026-09-05; post-launch removal ticket PLATARCH-REMOVE-SKILLS-001."
```

---

### Task 4: Update Layer 4 `audit_orchestrator` to the canonical path with legacy fallback

**Files:**
- Modify: `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/config.py`
- Modify: `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/analyzers/catalog_checks.py`
- Modify: `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/analyzers/catalog_definitions.py`
- Test: `services/layer4-agents/tests/unit/test_audit_orchestrator_skill_paths.py`

**Interfaces:**
- Consumes: the canonical `agents/skills/` tree (Task 1) and the legacy `.agent/skills/` path (for fallback).
- Produces:
  - `config.py`: `DEFAULT_YAML_PATH = "agents/skills/repo-audit/config.yaml"`, `LEGACY_YAML_PATH = ".agent/skills/repo-audit/config.yaml"`, and `ConfigManager._try_load_yaml()` that tries canonical then legacy.
  - `catalog_checks.py`: a module-level `_resolve_skills_root(repo_path: Path) -> Path | None` helper (canonical first, legacy fallback, else `None`), used by `_check_llm_guardrails`, `_check_missing_repo_audit_skill`, and `_check_skill_prompts_complete`.
  - `catalog_definitions.py`: AGENT-001 and AGENT-002 `recommended_fix` strings pointing at `agents/skills/repo-audit`.

- [ ] **Step 1: Write the failing unit test**

Create `services/layer4-agents/tests/unit/test_audit_orchestrator_skill_paths.py`:
```python
"""Unit tests for audit_orchestrator skill-path resolution after the
.agent/skills -> agents/skills promotion (Slice S).

These tests exercise the dual-layout resolution: the canonical
``agents/skills`` path is preferred, the legacy ``.agent/skills`` path is a
fallback, and an absent layout is handled gracefully.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from layer4_agents.agents.audit_orchestrator.analyzers import catalog_checks


def _make_repo_audit(root: Path, skills_root: Path) -> None:
    skill = skills_root / "repo-audit"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# repo-audit\n", encoding="utf-8")
    (skill / "config.yaml").write_text("{}", encoding="utf-8")


@pytest.mark.unit
def test_resolve_skills_root_prefers_canonical(tmp_path: Path) -> None:
    (tmp_path / "agents" / "skills").mkdir(parents=True)
    (tmp_path / ".agent" / "skills").mkdir(parents=True)
    assert catalog_checks._resolve_skills_root(tmp_path) == tmp_path / "agents" / "skills"


@pytest.mark.unit
def test_resolve_skills_root_falls_back_to_legacy(tmp_path: Path) -> None:
    (tmp_path / ".agent" / "skills").mkdir(parents=True)
    assert catalog_checks._resolve_skills_root(tmp_path) == tmp_path / ".agent" / "skills"


@pytest.mark.unit
def test_resolve_skills_root_none_when_absent(tmp_path: Path) -> None:
    assert catalog_checks._resolve_skills_root(tmp_path) is None


@pytest.mark.unit
def test_missing_repo_audit_skill_detects_canonical(tmp_path: Path) -> None:
    _make_repo_audit(tmp_path, tmp_path / "agents" / "skills")
    result = catalog_checks._check_missing_repo_audit_skill(tmp_path, None)
    assert result["triggered"] is False
    assert result["repo_audit_skill_present"] is True


@pytest.mark.unit
def test_missing_repo_audit_skill_detects_legacy(tmp_path: Path) -> None:
    _make_repo_audit(tmp_path, tmp_path / ".agent" / "skills")
    result = catalog_checks._check_missing_repo_audit_skill(tmp_path, None)
    assert result["triggered"] is False
    assert result["repo_audit_skill_present"] is True


@pytest.mark.unit
def test_missing_repo_audit_skill_triggers_when_absent(tmp_path: Path) -> None:
    result = catalog_checks._check_missing_repo_audit_skill(tmp_path, None)
    assert result["triggered"] is True
    assert result["repo_audit_skill_present"] is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```powershell
cd services/layer4-agents; python -m pytest tests/unit/test_audit_orchestrator_skill_paths.py -v
```
Expected: FAIL — `AttributeError: module '...catalog_checks' has no attribute '_resolve_skills_root'` (the helper does not exist yet).

- [ ] **Step 3: Add the `_resolve_skills_root` helper to `catalog_checks.py`**

In `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/analyzers/catalog_checks.py`, add this helper just above `_check_llm_guardrails` (currently at line ~492):
```python
def _resolve_skills_root(repo_path: Path) -> Path | None:
    """Return the skills root, preferring canonical ``agents/skills`` over legacy ``.agent/skills``.

    After the Slice S promotion the first-party skills live in ``agents/skills/``.
    The legacy ``.agent/skills/`` path is retained as a fallback so audits of
    checkouts that predate the promotion (or that still carry the shim) keep
    working. Returns ``None`` when neither location exists.
    """
    for candidate in (repo_path / "agents" / "skills", repo_path / ".agent" / "skills"):
        if candidate.is_dir():
            return candidate
    return None
```

- [ ] **Step 4: Update `_check_llm_guardrails` to use the helper**

Replace the first two lines of `_check_llm_guardrails` (currently):
```python
def _check_llm_guardrails(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    prompts_dir = repo_path / ".agent" / "skills"
    if not prompts_dir.exists():
        return {"triggered": False, "prompts_missing_guardrails": 0}
```
with:
```python
def _check_llm_guardrails(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    prompts_dir = _resolve_skills_root(repo_path)
    if prompts_dir is None:
        return {"triggered": False, "prompts_missing_guardrails": 0}
```
Leave the rest of the function (the `rglob("*.txt")` loop and return) unchanged.

- [ ] **Step 5: Update `_check_missing_repo_audit_skill` to use the helper**

Replace the entire `_check_missing_repo_audit_skill` function (currently lines ~763-779) with:
```python
def _check_missing_repo_audit_skill(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    root = _resolve_skills_root(repo_path)
    skill_dir = (root / "repo-audit") if root else None
    present = bool(
        skill_dir
        and skill_dir.exists()
        and (skill_dir / "SKILL.md").exists()
        and (skill_dir / "config.yaml").exists()
    )
    return {
        "triggered": not present,
        "evidence": (
            "Missing agents/skills/repo-audit/SKILL.md or config.yaml "
            "(legacy .agent/skills/repo-audit also checked)" if not present else ""
        ),
        "check_output": f"repo_audit_skill_present={present}",
        "repo_audit_skill_present": present,
        "missing_skill_definition_count": 0 if present else 1,
        "observed_fact": "The repo-audit skill package is missing or incomplete.",
    }
```

- [ ] **Step 6: Update `_check_skill_prompts_complete` to use the helper**

Replace the first ~14 lines of `_check_skill_prompts_complete` (currently lines ~782-800, up to and including the `if not prompts_dir.exists():` early-return block) with:
```python
def _check_skill_prompts_complete(repo_path: Path, _config: AuditConfig) -> dict[str, Any]:
    root = _resolve_skills_root(repo_path)
    prompts_dir = (root / "repo-audit" / "prompts") if root else None
    expected = {
        "system.txt",
        "analyze_git.txt",
        "analyze_code.txt",
        "analyze_docs.txt",
        "generate_report.txt",
    }
    if not (prompts_dir and prompts_dir.exists()):
        return {
            "triggered": True,
            "evidence": "Missing agents/skills/repo-audit/prompts directory "
            "(legacy .agent/skills/repo-audit/prompts also checked)",
            "check_output": "repo_audit_prompts_complete=false",
            "repo_audit_prompts_complete": False,
            "observed_fact": "The repo-audit skill is missing its prompt directory.",
        }
```
Leave the rest of the function (`present = {p.name ...}`, `missing = ...`, and the final return) unchanged.

- [ ] **Step 7: Update `config.py` to the canonical path with legacy fallback**

In `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/config.py`:

(a) Update the module docstring line (line 8) from:
```
2. YAML config file (``.agent/skills/repo-audit/config.yaml``)
```
to:
```
2. YAML config file (``agents/skills/repo-audit/config.yaml``, legacy ``.agent/skills/repo-audit/config.yaml`` fallback)
```

(b) Replace line 31:
```python
DEFAULT_YAML_PATH: str = ".agent/skills/repo-audit/config.yaml"
```
with:
```python
DEFAULT_YAML_PATH: str = "agents/skills/repo-audit/config.yaml"
LEGACY_YAML_PATH: str = ".agent/skills/repo-audit/config.yaml"
```

(c) Replace `_try_load_yaml` (currently lines ~118-128) with:
```python
    def _try_load_yaml(self) -> dict[str, Any] | None:
        """Load YAML config if the file exists (canonical path, then legacy fallback)."""
        for path in (self.yaml_path, Path(LEGACY_YAML_PATH)):
            if not path.exists():
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                return data if isinstance(data, dict) else None
            except (OSError, yaml.YAMLError):
                return None
        return None
```

(d) Add `"LEGACY_YAML_PATH",` to `__all__` (currently lines 414-418), directly after `"DEFAULT_YAML_PATH",`.

- [ ] **Step 8: Update the two `recommended_fix` strings in `catalog_definitions.py`**

In `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/analyzers/catalog_definitions.py`:

(a) AGENT-001 (line ~635): change
```python
        "recommended_fix": "Create .agent/skills/repo-audit with SKILL.md, config.yaml, and prompts.",
```
to:
```python
        "recommended_fix": "Create agents/skills/repo-audit with SKILL.md, config.yaml, and prompts.",
```

(b) AGENT-002 (line ~650): change
```python
        "recommended_fix": "Add all required prompt files under .agent/skills/repo-audit/prompts.",
```
to:
```python
        "recommended_fix": "Add all required prompt files under agents/skills/repo-audit/prompts.",
```

- [ ] **Step 9: Run the new test to verify it passes**

Run:
```powershell
cd services/layer4-agents; python -m pytest tests/unit/test_audit_orchestrator_skill_paths.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 10: Run the existing audit_orchestrator tests for regression**

Run:
```powershell
cd services/layer4-agents; python -m pytest tests/unit/test_audit_orchestrator_api.py -v
```
Expected: all existing tests PASS (no regression from the path change).

- [ ] **Step 11: Commit**

```powershell
git add services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/config.py services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/analyzers/catalog_checks.py services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/analyzers/catalog_definitions.py services/layer4-agents/tests/unit/test_audit_orchestrator_skill_paths.py
git commit -m "feat(audit-orchestrator): resolve skills from agents/skills with legacy fallback

Point the audit_orchestrator at the canonical agents/skills/repo-audit path
and add a _resolve_skills_root helper that falls back to the legacy
.agent/skills path. Update config.py DEFAULT_YAML_PATH with a LEGACY_YAML_PATH
fallback, and the AGENT-001/AGENT-002 recommended_fix strings. Add unit tests
for the dual-layout resolution."
```

---

### Task 5: Update all live references to the new path

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.agent/AGENTS.md`
- Modify: `skills-lock.json`, `.agents/skills.json`, `.agent/skills.json`
- Modify: `agents/skills/tldraw/SKILL.md`
- Modify: `agents/skills/frontend-excellence/SKILL.md`
- Modify: `agents/skills/frontend-excellence/references/subagent-orchestration.md`
- Modify: `handbook/MIGRATION.md`
- Modify: `.agent/DEPRECATED.md`

**Interfaces:**
- Consumes: the canonical `agents/skills/` tree (Task 1).
- Produces: no stale live references to `.agent/skills/` (only the intentional ones: `MOVED.md`, the CDR row, the L4 legacy fallback, and historical docs).

- [ ] **Step 1: Update `CLAUDE.md`**

In `CLAUDE.md`, find the line (around line 30):
```
3. `.agent/skills/_index.md` — available skills
```
Change it to:
```
3. `agents/skills/_index.md` — available skills
```

- [ ] **Step 2: Update `.agent/AGENTS.md`**

In `.agent/AGENTS.md`, make these four changes:

(a) The Skills section intro (around line 41):
```
Skills live in `skills/` (relative to this file).
```
→
```
Skills live in `agents/skills/` (repo root). They were promoted out of the `.agent/` brain in Slice S; see `.agent/skills/MOVED.md`.
```

(b) The "How to use" step 1 (around line 43):
```
1. Read `skills/_index.md` to find relevant skills
```
→
```
1. Read `agents/skills/_index.md` to find relevant skills
```

(c) The manifest line (around line 47):
```
The manifest (`skills/_manifest.jsonl`) is the machine-readable source of truth for skill metadata.
```
→
```
The manifest (`agents/skills/_manifest.jsonl`) is the machine-readable source of truth for skill metadata.
```

(d) The Design System section (around line 53):
```
The design system lives in `skills/design-md/SKILL.md`.
```
→
```
The design system lives in `agents/skills/design-md/SKILL.md`.
```

- [ ] **Step 3: Update the three skill lock files**

In each of `skills-lock.json`, `.agents/skills.json`, and `.agent/skills.json`, find the entry:
```json
    {
      "source": ".agent/skills",
      "sourceType": "directory",
      "path": ".agent/skills"
    },
```
and change it to:
```json
    {
      "source": "agents/skills",
      "sourceType": "directory",
      "path": "agents/skills"
    },
```
(Leave the other five entries — `.agents/skills`, `.agents/skills/superpowers`, `.agents/skills/clerk`, `.devin/skills`, `.claude/skills` — unchanged.)

- [ ] **Step 4: Update the in-skill self-references**

(a) In `agents/skills/tldraw/SKILL.md` (around line 92), change:
```
python3 .agent/skills/tldraw/store.py
```
→
```
python3 agents/skills/tldraw/store.py
```

(b) In `agents/skills/frontend-excellence/SKILL.md` (around line 34), change the reference to `.agent/skills/design-md/` to `agents/skills/design-md/`.

(c) In `agents/skills/frontend-excellence/references/subagent-orchestration.md` (around line 61), change the self-reference `.agent/skills/frontend-excellence/references/subagent-orchestration.md` to `agents/skills/frontend-excellence/references/subagent-orchestration.md`.

- [ ] **Step 5: Update `handbook/MIGRATION.md`**

In `handbook/MIGRATION.md`, in the `## Mapping` table, find the `.agent/` row. In its "Migrate what" column, change:
```
skills/, tools/ → `contracts/tool-manifests/` + card Verification
```
to:
```
skills/ → `agents/skills/` (Slice S promotion); tools/ → `contracts/tool-manifests/` + card Verification
```

- [ ] **Step 6: Update `.agent/DEPRECATED.md`**

In `.agent/DEPRECATED.md`, append this line at the end of the file:
```
Note: `skills/` was promoted to `agents/skills/` in Slice S (2026-09-05); the directory now holds only a `MOVED.md` pointer.
```

- [ ] **Step 7: Verify no stale live references remain**

Run:
```powershell
git grep -n "\.agent/skills" -- ':!docs/superpowers' ':!.goals' ':!.agent/memory' ':!docs/maintenance'
```
Expected: the ONLY matches are the intentional ones:
- `.agent/skills/MOVED.md` (the pointer itself)
- `docs/governance/compatibility-debt-registry.md` (the COMPAT-SKILLS-001 row)
- `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/config.py` (the `LEGACY_YAML_PATH` fallback)
- `services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/analyzers/catalog_checks.py` (the `_resolve_skills_root` legacy fallback + evidence strings)
- `services/layer4-agents/tests/unit/test_audit_orchestrator_skill_paths.py` (the legacy-fallback test)
- `.agent/AGENTS.md` and `.agent/DEPRECATED.md` (the relocation notes that mention the old path)

If any other live reference appears, update it to `agents/skills/` and re-run.

- [ ] **Step 8: Commit**

```powershell
git add CLAUDE.md .agent/AGENTS.md skills-lock.json .agents/skills.json .agent/skills.json agents/skills/tldraw/SKILL.md agents/skills/frontend-excellence/SKILL.md agents/skills/frontend-excellence/references/subagent-orchestration.md handbook/MIGRATION.md .agent/DEPRECATED.md
git commit -m "docs(skills): point all live references at agents/skills

Update CLAUDE.md, .agent/AGENTS.md, the three skill lock files, the three
in-skill self-references, handbook/MIGRATION.md, and .agent/DEPRECATED.md to
reference the canonical agents/skills/ path. Historical docs (.goals,
.agent/memory, docs/maintenance) are intentionally left as-is."
```

---

### Task 6: Final verification sweep

**Files:**
- None (verification only).

**Interfaces:**
- Consumes: all prior tasks.
- Produces: evidence that the promotion is complete and consistent.

- [ ] **Step 1: Confirm the tree layout**

Run:
```powershell
Get-ChildItem agents/skills -Name
Get-ChildItem .agent/skills -Name
```
Expected: `agents/skills/` has the 15 skill dirs + `_index.md` + `_manifest.jsonl`; `.agent/skills/` has only `MOVED.md`.

- [ ] **Step 2: Confirm all 15 manifests are valid YAML with the fixed schema**

Run:
```powershell
python -c "import yaml, pathlib; root=pathlib.Path('agents/skills'); files=sorted(root.glob('*/skill.yaml')); assert len(files)==15, len(files); [yaml.safe_load(f.read_text(encoding='utf-8')) for f in files]; print('OK: 15 manifests parse')"
```
Expected: `OK: 15 manifests parse`.

- [ ] **Step 3: Confirm the CDR row parses**

Run:
```powershell
python -c "import sys; sys.path.insert(0,'scripts/ci'); import compatibility_registry as cr; e=next(x for x in cr.parse_registry() if x.shim_id=='COMPAT-SKILLS-001'); assert cr.has_platform_architecture_approval(e.review_metadata); print('OK: CDR row valid')"
```
Expected: `OK: CDR row valid`.

- [ ] **Step 4: Run the full L4 audit_orchestrator unit test set**

Run:
```powershell
cd services/layer4-agents; python -m pytest tests/unit/test_audit_orchestrator_skill_paths.py tests/unit/test_audit_orchestrator_api.py -v
```
Expected: all tests PASS.

- [ ] **Step 5: Confirm the L4 shim tree was not touched**

Run:
```powershell
git status --short services/layer4-agents/src/skills
```
Expected: no output (the L4 shim tree is unchanged).

- [ ] **Step 6: Final stale-reference sweep**

Run:
```powershell
git grep -n "\.agent/skills" -- ':!docs/superpowers' ':!.goals' ':!.agent/memory' ':!docs/maintenance'
```
Expected: only the intentional matches listed in Task 5, Step 7.

- [ ] **Step 7: Review the full diff**

Run:
```powershell
git --no-pager log --oneline -6
git --no-pager diff --stat HEAD~6
```
Expected: 6 commits (one per task) and a diff stat consistent with the File Structure section.

- [ ] **Step 8: Note the PR-time requirement**

Before opening the PR, ensure it carries the labels `compat-shim-change` and `compat-owner-ack` (required by `scripts/ci/check_shim_change_ack.py` because `.agent/skills/MOVED.md` is under the registered shim path `.agent/skills/`). This is a PR-time action, not a code change.

---

## Self-Review

**1. Spec coverage:**
- Move 15 skills + `_index.md` + `_manifest.jsonl` → Task 1. ✓
- 15 `skill.yaml` manifests with the fixed schema → Task 2. ✓
- `MOVED.md` shim (not symlinks) → Task 1. ✓
- CDR row `COMPAT-SKILLS-001` (path in backticks, Platform Architecture + ISO date) → Task 3. ✓
- L4 `config.py` canonical + legacy fallback → Task 4. ✓
- L4 `catalog_checks.py` `_resolve_skills_root` + 3 checks → Task 4. ✓
- L4 `catalog_definitions.py` 2 `recommended_fix` strings → Task 4. ✓
- L4 unit test for dual-layout resolution → Task 4. ✓
- Reference updates (CLAUDE.md, .agent/AGENTS.md, 3 lock files, 3 in-skill self-refs, MIGRATION.md, DEPRECATED.md) → Task 5. ✓
- Verification (CDR parse, YAML parse, L4 tests, grep sweep) → Task 6. ✓
- PR labels `compat-shim-change` + `compat-owner-ack` → Task 6 Step 8. ✓
- Do NOT touch `services/layer4-agents/src/skills/` (L4 shim tree) → Global Constraints + Task 6 Step 5. ✓
- Do NOT touch `.agent/tools/` → Global Constraints. ✓
- Do NOT add to `deprecations.json` / `deprecation-budget.json` → Global Constraints. ✓

**2. Placeholder scan:** No "TBD"/"TODO"/"implement later". Every code step shows the exact before/after content. The generator script is fully specified. The verification one-liners are concrete (with a fallback note to write them to a temp file if awkward).

**3. Type consistency:** `_resolve_skills_root(repo_path: Path) -> Path | None` is defined in Task 4 Step 3 and used identically in Steps 4-6 and in the test (Task 4 Step 1). `DEFAULT_YAML_PATH` / `LEGACY_YAML_PATH` are defined in Task 4 Step 7 and referenced consistently. The `skill.yaml` schema fields match across Task 2 (generator + verification) and the Global Constraints.

**Note on `_index.md`:** The spec's reference table listed `agents/skills/_index.md` as needing "internal path references" updated. Verified: `_index.md` contains no path references (only skill names and one-line descriptions), so it needs no content change — it is moved in Task 1 and left as-is.
