#!/usr/bin/env python3
"""Extract detailed content from original workflow versions and append to skill files."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / ".devin" / "skills"


def git_show(path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(f"Error reading {path}: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def extract_autonomous_sections() -> str:
    content = git_show(".devin/workflows/autonomous-test-assurance-agent.md")
    lines = content.splitlines()

    sections = []

    # Extract Security Test Requirements (was ~4.3)
    in_section = False
    section_lines = []
    for line in lines:
        if "### 4.3 Security Test Requirements" in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("### 4.4") or line.startswith("## Phase 5"):
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    # Extract Example Test Patterns (was ~4.4)
    in_section = False
    section_lines = []
    for line in lines:
        if "### 4.4 Example Test Patterns" in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("---"):
                section_lines.append(line)
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    # Extract Refactoring Patterns (was ~5.3)
    in_section = False
    section_lines = []
    for line in lines:
        if "### 5.3 Refactoring Patterns" in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("---"):
                section_lines.append(line)
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    # Extract Remediation Report template (was ~7.1)
    in_section = False
    section_lines = []
    for line in lines:
        if "### 7.1 Self-Generate Remediation Report" in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("---"):
                section_lines.append(line)
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    # Extract High-Value First Targets
    in_section = False
    section_lines = []
    for line in lines:
        if "## High-Value First Targets" in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("---"):
                section_lines.append(line)
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    return "\n\n".join(sections)


def extract_fumadocs_sections() -> str:
    content = git_show(".devin/workflows/fumadocs-drift-audit.md")
    lines = content.splitlines()

    sections = []

    # Extract Step 8 remediation pack tables
    in_section = False
    section_lines = []
    for line in lines:
        if "### 8. Produce Remediation Pack" in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("---") and len(section_lines) > 5:
                section_lines.append(line)
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    # Extract Output Format section
    in_section = False
    section_lines = []
    for line in lines:
        if "## Output Format" in line and not in_section:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("---") and len(section_lines) > 5:
                section_lines.append(line)
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    return "\n\n".join(sections)


def extract_fabric_ui_sections() -> str:
    content = git_show(".devin/workflows/fabric_ui_drift_agent.md")
    lines = content.splitlines()

    sections = []

    # Extract Agent 2 output format
    in_section = False
    section_lines = []
    for line in lines:
        if "### Output Format" in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("---") and len(section_lines) > 5:
                section_lines.append(line)
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    # Extract Agent 6 report template
    in_section = False
    section_lines = []
    for line in lines:
        if "**Output**: `apps/web/FABRIC_DEPLOYMENT_REPORT.md`" in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("---") and len(section_lines) > 5:
                section_lines.append(line)
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    return "\n\n".join(sections)


def extract_launch_sections() -> str:
    content = git_show(".devin/workflows/launch-readiness-assessment.md")
    lines = content.splitlines()

    sections = []

    # Extract Output Format template
    in_section = False
    section_lines = []
    for line in lines:
        if "## Output Format" in line and not in_section:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("## Execution Log Format"):
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    # Extract Execution Log Format
    in_section = False
    section_lines = []
    for line in lines:
        if "## Execution Log Format" in line:
            in_section = True
            section_lines = [line]
            continue
        if in_section:
            if line.startswith("## Concrete Actions Checklist"):
                break
            section_lines.append(line)
    if section_lines:
        sections.append("\n".join(section_lines))

    return "\n\n".join(sections)


def main() -> int:
    # 1. Autonomous test assurance
    skill_file = SKILLS_DIR / "autonomous-test-assurance" / "SKILL.md"
    extracted = extract_autonomous_sections()
    if extracted.strip():
        with open(skill_file, "a", encoding="utf-8") as f:
            f.write("\n\n---\n\n# Extracted Workflow Reference\n\n")
            f.write(extracted)
        print(f"Appended {len(extracted.splitlines())} lines to {skill_file}")
    else:
        print("No autonomous sections extracted")

    # 2. Fumadocs
    skill_file = SKILLS_DIR / "fumadocs" / "SKILL.md"
    extracted = extract_fumadocs_sections()
    if extracted.strip():
        with open(skill_file, "a", encoding="utf-8") as f:
            f.write("\n\n---\n\n# Extracted Workflow Reference\n\n")
            f.write(extracted)
        print(f"Appended {len(extracted.splitlines())} lines to {skill_file}")
    else:
        print("No fumadocs sections extracted")

    # 3. Fabric UI drift
    fabric_skill_dir = SKILLS_DIR / "fabric-ui-drift"
    fabric_skill_dir.mkdir(exist_ok=True)
    skill_file = fabric_skill_dir / "SKILL.md"
    extracted = extract_fabric_ui_sections()
    if extracted.strip():
        header = "---\nskill_id: fabric-ui-drift\nname: Fabric UI Drift\nversion: 1.0.0\ndescription: Templates and reference for Fabric UI System Enforcement workflow\nside_effects: none\ntimeout_ms: 30000\nrequired_context:\n  - project_graph\nallowed_agents:\n  - \"*\"\n---\n\n"
        if not skill_file.exists():
            with open(skill_file, "w", encoding="utf-8") as f:
                f.write(header)
                f.write("# Fabric UI Drift — Workflow Reference\n\n")
                f.write(extracted)
        else:
            with open(skill_file, "a", encoding="utf-8") as f:
                f.write("\n\n---\n\n# Extracted Workflow Reference\n\n")
                f.write(extracted)
        print(f"Wrote/appended {len(extracted.splitlines())} lines to {skill_file}")
    else:
        print("No fabric UI sections extracted")

    # 4. Launch readiness
    launch_skill_dir = SKILLS_DIR / "launch-readiness-assessment"
    launch_skill_dir.mkdir(exist_ok=True)
    skill_file = launch_skill_dir / "SKILL.md"
    extracted = extract_launch_sections()
    if extracted.strip():
        header = "---\nskill_id: launch-readiness-assessment\nname: Launch Readiness Assessment\nversion: 1.0.0\ndescription: Templates and reference for Launch Readiness Assessment workflow\nside_effects: none\ntimeout_ms: 30000\nrequired_context:\n  - project_graph\nallowed_agents:\n  - \"*\"\n---\n\n"
        if not skill_file.exists():
            with open(skill_file, "w", encoding="utf-8") as f:
                f.write(header)
                f.write("# Launch Readiness Assessment — Workflow Reference\n\n")
                f.write(extracted)
        else:
            with open(skill_file, "a", encoding="utf-8") as f:
                f.write("\n\n---\n\n# Extracted Workflow Reference\n\n")
                f.write(extracted)
        print(f"Wrote/appended {len(extracted.splitlines())} lines to {skill_file}")
    else:
        print("No launch readiness sections extracted")

    return 0


if __name__ == "__main__":
    sys.exit(main())
