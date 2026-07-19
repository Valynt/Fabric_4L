from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DOC = REPO_ROOT / "docs" / "development" / "COMMANDS.md"
BUILD_SYSTEM_DOC = REPO_ROOT / "docs" / "development" / "BUILD_SYSTEM.md"
DOCS_README = REPO_ROOT / "docs" / "README.md"
TEST_INVENTORY_DOC = REPO_ROOT / "docs" / "testing" / "test-inventory.md"
DECISIONS_DIR = REPO_ROOT / "docs" / "decisions"
EXPLANATION_ADR_DIR = REPO_ROOT / "docs" / "explanations" / "adr"
LAYER_RUNTIME_PATH_GOVERNANCE_DOC = REPO_ROOT / "docs" / "reference" / "layer-runtime-path-governance.md"
REPOSITORY_DISCOVERABILITY_AUDIT_DOC = REPO_ROOT / "docs" / "governance" / "repository-discoverability-audit.md"
LAYER3_DISCOVERY_SURFACES = [
    LAYER_RUNTIME_PATH_GOVERNANCE_DOC,
    REPO_ROOT / "services" / "layer3-knowledge" / "README.md",
    REPO_ROOT / "docs" / "governance" / "compatibility-debt-registry.md",
    REPO_ROOT / "scripts" / "ci" / "check_layer3_source_mirror.py",
    REPO_ROOT / "scripts" / "ci" / "check_layer3_wrapper_drift.py",
    REPO_ROOT / "services" / "layer3-knowledge" / "scripts" / "check_runtime_shim_drift.py",
]
CANONICAL_LAYER_RUNTIME_PATHS = {
    "Layer 1": "services/layer1-ingestion/src/",
    "Layer 2": "services/layer2-extraction/src/",
    "Layer 3": "services/layer3-knowledge/src/",
    "Layer 4": "services/layer4-agents/src/",
    "Layer 5": "services/layer5-ground-truth/src/layer5_ground_truth/",
    "Layer 6": "services/layer6-benchmarks/src/",
}
CANONICAL_RUNTIME_API_PATHS = {
    "Layer 1": "services/layer1-ingestion/src/layer1_ingestion/api/routes/",
    "Layer 2": "services/layer2-extraction/src/layer2_extraction/api/routes/",
    "Layer 3": "services/layer3-knowledge/src/api/routes/",
    "Layer 4": "services/layer4-agents/src/api/routes/",
    "Layer 5": "services/layer5-ground-truth/src/layer5_ground_truth/api/",
    "Layer 6": "services/layer6-benchmarks/src/layer6_benchmarks/api/routes/",
}
RUNBOOK_INDEX_DOCS = [
    REPO_ROOT / "docs" / "runbooks" / "00-runbook-index.md",
    REPO_ROOT / "docs" / "operations" / "runbooks" / "README.md",
    REPO_ROOT / "docs" / "troubleshooting" / "runbooks" / "README.md",
    REPO_ROOT / "ops" / "incident" / "README.md",
]
AUDIT_REQUIRED_DOMAINS = {
    "Layer 1 ingestion",
    "Layer 2 extraction",
    "Layer 3 knowledge",
    "Layer 4 agents",
    "Layer 5 ground truth",
    "Layer 6 benchmarks",
    "API gateway",
    "Frontend",
    "Contracts and schemas",
    "Packs and ontology",
    "GitHub workflows",
    "Test suites",
    "Security and tenant isolation",
    "Supply chain",
    "Migrations and database",
    "Release readiness",
    "Observability and SLOs",
    "Operational runbooks",
    "Decisions and ADRs",
    "Compliance and audit evidence",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _root_scripts() -> set[str]:
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    return set(package_json["scripts"])


def _public_make_targets() -> set[str]:
    source = _read(REPO_ROOT / "Makefile")
    pattern = re.compile(r"^([A-Za-z0-9_.-]+):.*##", re.MULTILINE)
    return set(pattern.findall(source))


def _make_help_renderer() -> Path:
    return REPO_ROOT / "scripts" / "ci" / "render_make_help.py"


def _table_names_between(source: str, start_heading: str, end_heading: str) -> set[str]:
    start = source.index(start_heading)
    end = source.index(end_heading, start)
    section = source[start:end]
    return set(re.findall(r"^\| `([^`]+)` \|", section, re.MULTILINE))


def _documented_root_scripts() -> set[str]:
    return _table_names_between(
        _read(COMMANDS_DOC),
        "## Root pnpm Scripts",
        "## Public Makefile Targets",
    )


def _documented_make_targets() -> set[str]:
    return _table_names_between(
        _read(COMMANDS_DOC),
        "## Public Makefile Targets",
        "## Python CI Runner",
    )


def _ci_mapping_rows() -> list[tuple[str, str, str]]:
    source = _read(COMMANDS_DOC)
    start = source.index("## CI To Local Mapping")
    end = source.index("## Related Documentation", start)
    rows: list[tuple[str, str, str]] = []

    for line in source[start:end].splitlines():
        if not line.startswith("|") or line.startswith("|---") or "CI workflow/job" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 3:
            rows.append((cells[0], cells[1], cells[2]))

    return rows


def _quick_navigation_rows() -> list[tuple[str, str]]:
    source = _read(DOCS_README)
    start = source.index("## Quick Navigation")
    end = source.index("\n---", start)
    rows: list[tuple[str, str]] = []

    for line in source[start:end].splitlines():
        if not line.startswith("|") or line.startswith("|---") or "I need to" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        match = re.search(r"\]\(([^)]+)\)", cells[1])
        if match:
            rows.append((cells[0], match.group(1)))

    return rows


def _testing_entrypoint_rows() -> list[tuple[str, str, str]]:
    source = _read(TEST_INVENTORY_DOC)
    start = source.index("## Current Executable Suite Entrypoints")
    end = source.index("\n---", start)
    rows: list[tuple[str, str, str]] = []

    for line in source[start:end].splitlines():
        if not line.startswith("|") or line.startswith("| ---") or "Domain" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 3:
            rows.append((cells[0], cells[1], cells[2]))

    return rows


def _discovery_map_rows() -> list[tuple[str, str, str, str, str]]:
    source = _read(REPO_ROOT / "docs" / "development" / "DISCOVERY_MAP.md")
    start = source.index("## Start Here")
    end = source.index("## Audited Domain Coverage", start)
    rows: list[tuple[str, str, str, str, str]] = []

    for line in source[start:end].splitlines():
        if not line.startswith("|") or line.startswith("| ---") or "Work type" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 5:
            rows.append((cells[0], cells[1], cells[2], cells[3], cells[4]))

    return rows


def _audit_rows() -> list[dict[str, str]]:
    source = _read(REPOSITORY_DISCOVERABILITY_AUDIT_DOC)
    start = source.index("## Coverage Matrix")
    end = source.index("## Completion Rule", start)
    rows: list[dict[str, str]] = []
    headers: list[str] = []

    for line in source[start:end].splitlines():
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not headers:
            headers = cells
            continue
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells, strict=True)))

    return rows


def _audited_domain_rows() -> list[tuple[str, str]]:
    source = _read(REPO_ROOT / "docs" / "development" / "DISCOVERY_MAP.md")
    start = source.index("## Audited Domain Coverage")
    end = source.index("## Issue To Validation Loop", start)
    rows: list[tuple[str, str]] = []

    for line in source[start:end].splitlines():
        if not line.startswith("|") or line.startswith("| ---") or "Audited domain" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 2:
            rows.append((cells[0], cells[1]))

    return rows


def _is_public_local_command(command: str) -> bool:
    parts = command.split()
    if len(parts) >= 2 and parts[0] == "make":
        return parts[1] in _public_make_targets()
    if len(parts) >= 2 and parts[0] == "pnpm":
        script = parts[2] if parts[1] == "run" and len(parts) >= 3 else parts[1]
        return script in _root_scripts()
    return False


def _markdown_links(source: str) -> set[str]:
    return set(re.findall(r"\]\(([^)]+)\)", source))


def _backtick_values(source: str) -> list[str]:
    return re.findall(r"`([^`]+)`", source)


def _resolve_repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def test_every_root_package_script_is_documented() -> None:
    commands = _read(COMMANDS_DOC)

    missing = sorted(script for script in _root_scripts() if f"`{script}`" not in commands)

    assert not missing, f"Root package scripts missing from COMMANDS.md: {missing}"


def test_documented_root_package_scripts_exist() -> None:
    stale = sorted(_documented_root_scripts() - _root_scripts())

    assert not stale, f"COMMANDS.md documents root package scripts that do not exist: {stale}"


def test_every_public_makefile_target_is_documented() -> None:
    commands = _read(COMMANDS_DOC)

    missing = sorted(target for target in _public_make_targets() if f"`{target}`" not in commands)

    assert not missing, f"Public Makefile targets missing from COMMANDS.md: {missing}"


def test_documented_makefile_targets_exist() -> None:
    stale = sorted(_documented_make_targets() - _public_make_targets())

    assert not stale, f"COMMANDS.md documents Makefile targets that do not exist: {stale}"


def test_makefile_has_no_duplicate_target_definitions() -> None:
    source = _read(REPO_ROOT / "Makefile")
    pattern = re.compile(r"^([A-Za-z0-9_.-]+):", re.MULTILINE)
    targets = [target for target in pattern.findall(source) if not target.startswith(".")]

    duplicates = sorted({target for target in targets if targets.count(target) > 1})
    assert not duplicates, f"Makefile has duplicate target definitions: {duplicates}"


def test_make_help_uses_portable_renderer() -> None:
    makefile = _read(REPO_ROOT / "Makefile")

    assert "scripts/ci/render_make_help.py $(MAKEFILE_LIST)" in makefile
    help_recipe = re.search(r"^help:.*\n((?:\t.*\n)+)", makefile, re.MULTILINE)
    assert help_recipe is not None
    assert "awk" not in help_recipe.group(1)


def test_make_help_renderer_lists_public_targets() -> None:
    completed = subprocess.run(
        [sys.executable, str(_make_help_renderer()), str(REPO_ROOT / "Makefile")],
        check=True,
        capture_output=True,
        text=True,
    )

    output = completed.stdout
    assert "help " in output
    assert "verify " in output
    assert "Run all checks before PR" in output


def test_command_docs_define_canonical_hierarchy_and_ci_mapping() -> None:
    commands = _read(COMMANDS_DOC)
    build_system = _read(BUILD_SYSTEM_DOC)
    combined = f"{commands}\n{build_system}"

    required_phrases = [
        "The Makefile is the de facto build system",
        "Use `make` for repo-wide build, test, migration, contract, release, and readiness workflows",
        "Use `pnpm` for JavaScript and TypeScript package management",
        "Use direct Python CI runners only when debugging or reproducing a CI job",
        "Public Makefile targets are targets with `##` help text",
        "CI To Local Mapping",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in combined]

    assert not missing, f"Required command hierarchy text missing: {missing}"


def test_root_docs_link_to_command_map() -> None:
    required_links = [
        "docs/development/BUILD_SYSTEM.md",
        "docs/development/COMMANDS.md",
        "docs/development/DISCOVERY_MAP.md",
    ]

    for relative_path in ("README.md", "CONTRIBUTING.md", "AGENTS.md"):
        source = _read(REPO_ROOT / relative_path)
        missing = [link for link in required_links if link not in source]
        assert not missing, f"{relative_path} is missing command-map links: {missing}"


def test_readme_describes_make_setup_as_dependency_install_only() -> None:
    readme = _read(REPO_ROOT / "README.md")

    assert "| `make setup` | Install Python service development dependencies |" in readme
    assert "| `make setup` | Install deps, start dev services, apply migrations |" not in readme


def test_docs_quick_navigation_routes_major_work_surfaces() -> None:
    rows = _quick_navigation_rows()
    intents = {intent for intent, _ in rows}
    required_intents = {
        "Route an issue to implementation and validation",
        "Find local commands and gates",
        "Find CI workflow ownership and local validation",
        "Understand the architecture",
        "Run / operate the platform",
        "Respond to incidents and runbooks",
        "Testing strategy",
        "Find test inventory and quality posture",
        "Find validation and release evidence",
        "Where new code must live",
        "Review governance policy",
        "Review repository discoverability coverage",
        "Review security policy",
        "Review supply chain policy",
        "Understand design decisions",
    }

    missing = sorted(required_intents - intents)
    assert not missing, f"docs/README.md Quick Navigation is missing core work surfaces: {missing}"


def test_docs_quick_navigation_links_resolve() -> None:
    missing: list[str] = []

    for intent, href in _quick_navigation_rows():
        if href.startswith(("http://", "https://", "#")):
            continue
        target = href.split("#", 1)[0]
        if not target:
            continue
        resolved = (DOCS_README.parent / target).resolve()
        if not resolved.exists():
            missing.append(f"{intent}: {href}")

    assert not missing, f"docs/README.md Quick Navigation references missing targets: {missing}"


def test_testing_inventory_exposes_executable_suite_entrypoints() -> None:
    rows = _testing_entrypoint_rows()
    domains = {domain for domain, _, _ in rows}
    required_domains = {
        "Layer 1 ingestion",
        "Layer 2 extraction",
        "Layer 3 knowledge",
        "Layer 4 agents",
        "Layer 5 ground truth",
        "Layer 6 benchmarks",
        "Cross-layer contracts",
        "Security and tenant isolation",
        "Production readiness",
        "Frontend verification",
        "Documentation and discovery",
    }

    missing = sorted(required_domains - domains)
    assert not missing, f"docs/testing/test-inventory.md is missing suite entrypoints: {missing}"


def test_testing_inventory_entrypoint_paths_and_commands_exist() -> None:
    missing_paths: list[str] = []
    invalid_commands: list[str] = []

    for domain, source_paths, command_cell in _testing_entrypoint_rows():
        for source_path in re.findall(r"`([^`]+)`", source_paths):
            if not (REPO_ROOT / source_path).exists():
                missing_paths.append(f"{domain}: {source_path}")

        commands = re.findall(r"`([^`]+)`", command_cell)
        if not commands:
            invalid_commands.append(f"{domain}: missing command")
            continue
        for command in commands:
            if not _is_public_local_command(command):
                invalid_commands.append(f"{domain}: {command}")

    assert not missing_paths, f"Testing inventory references missing source paths: {missing_paths}"
    assert not invalid_commands, f"Testing inventory references non-public commands: {invalid_commands}"


def test_decision_indexes_list_every_decision_record() -> None:
    decision_readme = _read(DECISIONS_DIR / "README.md")
    decision_links = _markdown_links(decision_readme)
    decision_files = sorted(
        path.name
        for path in DECISIONS_DIR.glob("*.md")
        if path.name not in {"README.md", "TEMPLATE.md"}
    )

    missing_decisions = [name for name in decision_files if f"./{name}" not in decision_links]
    assert not missing_decisions, f"docs/decisions/README.md missing decision records: {missing_decisions}"

    adr_readme = _read(EXPLANATION_ADR_DIR / "README.md")
    adr_links = _markdown_links(adr_readme)
    adr_files = sorted(path.name for path in EXPLANATION_ADR_DIR.glob("ADR-*.md"))

    missing_adrs = [name for name in adr_files if f"./{name}" not in adr_links]
    assert not missing_adrs, f"docs/explanations/adr/README.md missing ADRs: {missing_adrs}"


def test_decision_index_links_resolve() -> None:
    missing: list[str] = []

    for readme in (DECISIONS_DIR / "README.md", EXPLANATION_ADR_DIR / "README.md"):
        for href in _markdown_links(_read(readme)):
            if href.startswith(("http://", "https://", "#")):
                continue
            target = href.split("#", 1)[0]
            if not target:
                continue
            if not (readme.parent / target).resolve().exists():
                missing.append(f"{readme.relative_to(REPO_ROOT).as_posix()}: {href}")

    assert not missing, f"Decision index links reference missing targets: {missing}"


def test_runbook_indexes_link_to_existing_operational_docs() -> None:
    missing: list[str] = []

    for index_path in RUNBOOK_INDEX_DOCS:
        for href in _markdown_links(_read(index_path)):
            if href.startswith(("http://", "https://", "#")):
                continue
            target = href.split("#", 1)[0]
            if not target:
                continue
            if not (index_path.parent / target).resolve().exists():
                missing.append(f"{index_path.relative_to(REPO_ROOT).as_posix()}: {href}")

    assert not missing, f"Runbook indexes reference missing operational docs: {missing}"


def test_repository_discoverability_audit_covers_major_domains() -> None:
    rows = _audit_rows()
    domains = {row["Domain"] for row in rows}

    missing = sorted(AUDIT_REQUIRED_DOMAINS - domains)
    extras = sorted(domains - AUDIT_REQUIRED_DOMAINS)

    assert not missing, f"Repository discoverability audit missing required domains: {missing}"
    assert not extras, f"Repository discoverability audit has unrecognized domains: {extras}"


def test_repository_discoverability_audit_has_no_incomplete_rows() -> None:
    incomplete = [
        f"{row['Domain']}: {row['Status']}"
        for row in _audit_rows()
        if row["Status"] != "covered"
    ]

    assert not incomplete, f"Repository discoverability audit has incomplete rows: {incomplete}"


def test_repository_discoverability_audit_paths_exist() -> None:
    missing: list[str] = []

    for row in _audit_rows():
        for column in ("Source of truth", "Governance / owner reference", "Evidence location"):
            for value in _backtick_values(row[column]):
                if not _resolve_repo_path(value).exists():
                    missing.append(f"{row['Domain']} {column}: {value}")

    assert not missing, f"Repository discoverability audit references missing paths: {missing}"


def test_repository_discoverability_audit_validation_commands_are_public() -> None:
    invalid: list[str] = []

    for row in _audit_rows():
        commands = _backtick_values(row["Public validation"])
        if not commands:
            invalid.append(f"{row['Domain']}: missing public validation")
            continue
        for command in commands:
            if not _is_public_local_command(command):
                invalid.append(f"{row['Domain']}: {command}")

    assert not invalid, f"Repository discoverability audit references non-public validation commands: {invalid}"


def test_discovery_map_routes_every_audited_domain() -> None:
    audit_routes = {row["Domain"]: row["Discovery route"] for row in _audit_rows()}
    discovery_routes = dict(_audited_domain_rows())
    start_here_routes = {domain for domain, _, _, _, _ in _discovery_map_rows()}

    missing_domains = sorted(set(audit_routes) - set(discovery_routes))
    route_mismatches = sorted(
        f"{domain}: audit={route!r}, discovery={discovery_routes.get(domain)!r}"
        for domain, route in audit_routes.items()
        if discovery_routes.get(domain) != route
    )
    missing_route_definitions = sorted(
        f"{domain}: {route}"
        for domain, route in discovery_routes.items()
        if route not in start_here_routes
    )

    assert not missing_domains, f"Discovery map is missing audited domains: {missing_domains}"
    assert not route_mismatches, f"Discovery map route mismatch with audit: {route_mismatches}"
    assert not missing_route_definitions, (
        "Audited domains point at undefined discovery routes: "
        f"{missing_route_definitions}"
    )


def test_layer_runtime_path_governance_lists_existing_canonical_paths() -> None:
    governance = _read(LAYER_RUNTIME_PATH_GOVERNANCE_DOC)
    missing_from_doc: list[str] = []
    missing_on_disk: list[str] = []

    for layer, path in CANONICAL_LAYER_RUNTIME_PATHS.items():
        if path not in governance:
            missing_from_doc.append(f"{layer}: {path}")
        if not (REPO_ROOT / path).exists():
            missing_on_disk.append(f"{layer}: {path}")

    for layer, path in CANONICAL_RUNTIME_API_PATHS.items():
        if path not in governance and path not in _read(REPO_ROOT / "AGENTS.md"):
            missing_from_doc.append(f"{layer} API: {path}")
        if not (REPO_ROOT / path).exists():
            missing_on_disk.append(f"{layer} API: {path}")

    assert not missing_from_doc, f"Canonical runtime paths missing from discoverability docs: {missing_from_doc}"
    assert not missing_on_disk, f"Canonical runtime paths missing on disk: {missing_on_disk}"


def test_layer3_discovery_surfaces_use_service_tree_as_canonical_runtime() -> None:
    stale_patterns = [
        "All net-new Layer 3 runtime logic belongs in `value_fabric/layer3/`",
        "Canonical implementation: `value_fabric/layer3/",
        "Canonical source-of-truth: value_fabric/layer3",
        "Keep canonical runtime logic in value_fabric/layer3/",
        "canonical implementation now lives in `value_fabric/layer3`",
        "Canonical owner/path:** `value_fabric/layer3`",
    ]
    missing_service_tree_guidance: list[str] = []
    stale_guidance: list[str] = []

    for path in LAYER3_DISCOVERY_SURFACES:
        source = _read(path)
        relative = path.relative_to(REPO_ROOT).as_posix()
        if "services/layer3-knowledge/src" not in source:
            missing_service_tree_guidance.append(relative)
        for pattern in stale_patterns:
            if pattern in source:
                stale_guidance.append(f"{relative}: {pattern}")

    assert not missing_service_tree_guidance, (
        "Layer 3 discovery surfaces must point at services/layer3-knowledge/src: "
        f"{missing_service_tree_guidance}"
    )
    assert not stale_guidance, f"Layer 3 discovery surfaces still contain stale canonical guidance: {stale_guidance}"


def test_development_discovery_map_routes_issue_to_validation() -> None:
    discovery_map = _read(REPO_ROOT / "docs" / "development" / "DISCOVERY_MAP.md")

    required_phrases = [
        "Issue To Validation Loop",
        "Canonical source of truth",
        "Drift checks",
        "Minimum focused validation",
        "Backend API behavior",
        "Frontend workflow or page",
        "Agent workflow, prompt, or tool",
        "Tenant isolation or auth",
        "Supply chain, dependency, or container change",
        "CI workflow or root command",
        "Operational runbook or incident workflow",
        "Architecture or governance decision",
        "Evidence Locations",
        "Supply chain and dependency posture",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in discovery_map]
    assert not missing, f"Development discovery map missing required routing coverage: {missing}"


def test_discovery_map_evidence_locations_use_canonical_active_paths() -> None:
    discovery_map = _read(REPO_ROOT / "docs" / "development" / "DISCOVERY_MAP.md")
    start = discovery_map.index("## Evidence Locations")
    end = discovery_map.index("\nIf a needed source of truth is missing", start)
    section = discovery_map[start:end]

    stale_patterns = {
        "reports/": r"(?<![A-Za-z0-9_-])reports/",
        "docs/archive/": r"docs/archive/",
        "../archive/": r"\.\./archive/",
        "archive/": r"(?<![A-Za-z0-9_-])archive/",
    }
    found = [
        location
        for location, pattern in stale_patterns.items()
        if re.search(pattern, section)
    ]

    assert not found, (
        "Discovery map evidence locations must point at canonical active docs, "
        f"tests, contracts, or artifacts, not reports/archive paths: {found}"
    )


def test_discovery_map_validation_commands_are_public_interfaces() -> None:
    discovery_map = _read(REPO_ROOT / "docs" / "development" / "DISCOVERY_MAP.md")
    commands = _read(COMMANDS_DOC)
    root_scripts = _root_scripts()
    make_targets = _public_make_targets()

    expected_commands = [
        ("make verify", "verify", make_targets),
        ("make contract-tests", "contract-tests", make_targets),
        ("pnpm run check:api-types", "check:api-types", root_scripts),
        ("pnpm run verify:frontend", "verify:frontend", root_scripts),
        ("pnpm test:agents", "test:agents", root_scripts),
        ("pnpm test:isolation", "test:isolation", root_scripts),
        ("pnpm check:package-manager-policy", "check:package-manager-policy", root_scripts),
        ("pnpm audit:ci", "audit:ci", root_scripts),
        ("pnpm sbom", "sbom", root_scripts),
        ("pnpm container:scan", "container:scan", root_scripts),
        ("make gate-security", "gate-security", make_targets),
        ("make check-migration-heads", "check-migration-heads", make_targets),
        ("make gate-database", "gate-database", make_targets),
        ("pnpm docs:check", "docs:check", root_scripts),
        ("make check-workflow-references", "check-workflow-references", make_targets),
        ("pnpm ci:workflow-references", "ci:workflow-references", root_scripts),
        ("pnpm ops:runbooks:lint", "ops:runbooks:lint", root_scripts),
        ("pnpm ops:incident:check", "ops:incident:check", root_scripts),
        ("make evals", "evals", make_targets),
    ]

    missing_from_map = [command for command, _, _ in expected_commands if command not in discovery_map]
    assert not missing_from_map, f"Discovery map missing validation commands: {missing_from_map}"

    missing_interfaces = [name for _, name, interfaces in expected_commands if name not in interfaces]
    assert not missing_interfaces, f"Discovery map references non-public interfaces: {missing_interfaces}"

    missing_from_inventory = [name for _, name, _ in expected_commands if f"`{name}`" not in commands]
    assert not missing_from_inventory, f"Discovery map commands missing from COMMANDS.md: {missing_from_inventory}"


def test_all_discovery_map_validation_commands_are_public_interfaces() -> None:
    invalid: list[str] = []

    for work_type, _, _, minimum_validation, broader_gate in _discovery_map_rows():
        for command in _backtick_values(f"{minimum_validation} {broader_gate}"):
            if not _is_public_local_command(command):
                invalid.append(f"{work_type}: {command}")

    assert not invalid, f"Discovery map validation cells reference non-public commands: {invalid}"


def test_ci_to_local_mapping_references_existing_workflows_and_commands() -> None:
    rows = _ci_mapping_rows()

    assert rows, "COMMANDS.md CI To Local Mapping must contain at least one row"

    missing_workflows: list[str] = []
    invalid_commands: list[str] = []

    for workflow_cell, local_command_cell, _ in rows:
        for workflow_path in re.findall(r"`(\.github/workflows/[^`]+\.ya?ml)`", workflow_cell):
            if not (REPO_ROOT / workflow_path).is_file():
                missing_workflows.append(workflow_path)

        for command in re.findall(r"`([^`]+)`", local_command_cell):
            if "<" in command and ">" in command:
                continue
            if not _is_public_local_command(command):
                invalid_commands.append(command)

    assert not missing_workflows, f"CI To Local Mapping references missing workflows: {missing_workflows}"
    assert not invalid_commands, f"CI To Local Mapping references unknown local commands: {invalid_commands}"
