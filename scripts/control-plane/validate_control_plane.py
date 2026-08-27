#!/usr/bin/env python3
"""Fabric_4L control-plane validator.

Validates the machine-readable contract linking product contract, behaviors,
and release controls:

1. Loads ``control-plane/contract_manifest.yaml`` and validates it against
   ``handbook/schemas/contract_manifest.schema.json`` (via the ``jsonschema``
   package when installed; otherwise performs structural checks manually:
   required keys and ID regexes).

2. Collects every defined ID from the manifest and from the class-defining
   files:
     - CTRL / AG / EV  -> control-plane/release/control_register.yaml
     - VP / GAP / R / J -> control-plane/product-contract/ files
     - BEH             -> control-plane/behaviors/ directory
   then scans all markdown under ``control-plane/`` and ``handbook/`` and
   fails on any ID-looking token that is not defined.

3. Verifies every behavior card file listed in the manifest exists on disk
   and that its YAML frontmatter ``id`` matches the manifest entry.

Run from the repo root:

    python scripts/control-plane/validate_control_plane.py

Exit codes:
    0  control plane is internally consistent
    1  validation violations were found (printed to stdout)
    2  setup error (missing dependency, missing manifest, unreadable file)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

try:
    import yaml
except ImportError:  # pragma: no cover - depends on environment
    print(
        "ERROR: PyYAML is required to parse control-plane YAML files.\n"
        "Install it with:\n"
        "    pip install pyyaml\n"
        "then re-run: python scripts/control-plane/validate_control_plane.py",
        file=sys.stderr,
    )
    sys.exit(2)

try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover - depends on environment
    jsonschema = None
    HAS_JSONSCHEMA = False

# ---------------------------------------------------------------------------
# Paths and ID patterns
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "control-plane" / "contract_manifest.yaml"
MANIFEST_SCHEMA_PATH = (
    REPO_ROOT / "handbook" / "schemas" / "contract_manifest.schema.json"
)
BEHAVIOR_CARD_SCHEMA_PATH = (
    REPO_ROOT / "handbook" / "schemas" / "behavior_card.schema.json"
)
CONTROL_REGISTER_PATH = REPO_ROOT / "control-plane" / "release" / "control_register.yaml"
PRODUCT_CONTRACT_DIR = REPO_ROOT / "control-plane" / "product-contract"
BEHAVIORS_DIR = REPO_ROOT / "control-plane" / "behaviors"

# Canonical ID patterns (full-match). Order matters for classification.
ID_PATTERNS = {
    "CTRL": re.compile(r"^CTRL-\d{2}-\d{2}$"),
    "GAP": re.compile(r"^GAP-\d{2}$"),
    "BEH": re.compile(r"^BEH-\d{2}$"),
    "VP": re.compile(r"^VP-\d{2}$"),
    "AG": re.compile(r"^AG-\d{2}$"),
    "EV": re.compile(r"^EV-\d+$"),
    "R": re.compile(r"^R-\d+$"),
    "J": re.compile(r"^J-\d+$"),
}

# One combined scanner for ID-looking tokens in prose / YAML text.
ID_TOKEN_RE = re.compile(
    r"\b(?:CTRL-\d{2}-\d{2}|GAP-\d{2}|BEH-\d{2}|VP-\d{2}|AG-\d{2}"
    r"|EV-\d+|R-\d+|J-\d+)\b"
)


def classify_id(token: str) -> str | None:
    """Return the ID class (e.g. 'BEH') for a token, or None."""
    for cls, pattern in ID_PATTERNS.items():
        if pattern.fullmatch(token):
            return cls
    return None


# ---------------------------------------------------------------------------
# Violation collection
# ---------------------------------------------------------------------------


class Violations:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, message: str) -> None:
        self.items.append(message)

    def __len__(self) -> int:
        return len(self.items)


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------


def load_yaml_file(path: Path, violations: Violations) -> object | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {path.relative_to(REPO_ROOT)}: {exc}", file=sys.stderr)
        sys.exit(2)
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        violations.add(f"{path.relative_to(REPO_ROOT)}: invalid YAML: {exc}")
        return None


def load_json_file(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load schema {path}: {exc}", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Step 1: manifest schema validation
# ---------------------------------------------------------------------------

# Manual fallback structural checks mirroring contract_manifest.schema.json.
MANIFEST_REQUIRED_TOP = [
    "version",
    "generated_from",
    "rules",
    "stories",
    "gaps",
    "behaviors",
    "controls",
]
ITEM_SPECS = {
    "rules": {"required": ["id", "statement", "source"], "id_class": "R"},
    "stories": {"required": ["id", "title"], "id_class": "VP"},
    "gaps": {"required": ["id", "title", "status"], "id_class": "GAP"},
    "behaviors": {"required": ["id", "name", "card"], "id_class": "BEH"},
    "controls": {
        "required": ["id", "gate", "title", "blocks"],
        "id_class": "CTRL",
    },
}
REF_ARRAY_ID_CLASS = {
    ("stories", "journey"): "J",
    ("stories", "behaviors"): "BEH",
    ("stories", "closes_gaps"): "GAP",
    ("stories", "rules"): "R",
    ("gaps", "closed_by"): "VP",
    ("behaviors", "stories"): "VP",
    ("behaviors", "closes_gaps"): "GAP",
    ("behaviors", "rules"): "R",
    ("behaviors", "journey"): "J",
    ("controls", "behaviors"): "BEH",
    ("controls", "evidence"): "EV",
    ("controls", "gate"): "AG",
}
BLOCKS_ENUM = {"merge", "release", "promotion"}
GAP_STATUS_ENUM = {"open", "closed"}


def manual_manifest_checks(manifest: object, violations: Violations) -> None:
    """Structural fallback when the jsonschema package is unavailable."""
    if not isinstance(manifest, dict):
        violations.add("contract_manifest.yaml: top level must be a mapping")
        return
    for key in MANIFEST_REQUIRED_TOP:
        if key not in manifest:
            violations.add(f"contract_manifest.yaml: missing required key '{key}'")
    if "version" in manifest and not isinstance(manifest["version"], int):
        violations.add("contract_manifest.yaml: 'version' must be an integer")

    for section, spec in ITEM_SPECS.items():
        items = manifest.get(section)
        if items is None:
            continue
        if not isinstance(items, list):
            violations.add(f"contract_manifest.yaml: '{section}' must be an array")
            continue
        for idx, item in enumerate(items):
            loc = f"{section}[{idx}]"
            if not isinstance(item, dict):
                violations.add(f"contract_manifest.yaml: {loc} must be a mapping")
                continue
            for req in spec["required"]:
                if req not in item:
                    violations.add(
                        f"contract_manifest.yaml: {loc} missing required key '{req}'"
                    )
            item_id = item.get("id")
            if item_id is not None:
                pattern = ID_PATTERNS[spec["id_class"]]
                if not isinstance(item_id, str) or not pattern.fullmatch(item_id):
                    violations.add(
                        f"contract_manifest.yaml: {loc}.id '{item_id}' does not "
                        f"match pattern {pattern.pattern}"
                    )
            if section == "controls" and "blocks" in item:
                if item["blocks"] not in BLOCKS_ENUM:
                    violations.add(
                        f"contract_manifest.yaml: {loc}.blocks '{item['blocks']}' "
                        "must be one of merge|release|promotion"
                    )
            if section == "controls" and "gate" in item:
                gate = item["gate"]
                if not isinstance(gate, str) or not ID_PATTERNS["AG"].fullmatch(gate):
                    violations.add(
                        f"contract_manifest.yaml: {loc}.gate '{gate}' must match "
                        "pattern ^AG-\\d{2}$"
                    )
            if section == "gaps" and "status" in item:
                if item["status"] not in GAP_STATUS_ENUM:
                    violations.add(
                        f"contract_manifest.yaml: {loc}.status '{item['status']}' "
                        "must be one of open|closed"
                    )
            # Cross-reference arrays: check ID patterns.
            for (sec, field), id_class in REF_ARRAY_ID_CLASS.items():
                if sec != section or field == "gate":
                    continue
                value = item.get(field)
                if value is None:
                    continue
                if not isinstance(value, list):
                    violations.add(
                        f"contract_manifest.yaml: {loc}.{field} must be an array "
                        f"of {id_class} IDs"
                    )
                    continue
                pattern = ID_PATTERNS[id_class]
                for ref in value:
                    if not isinstance(ref, str) or not pattern.fullmatch(ref):
                        violations.add(
                            f"contract_manifest.yaml: {loc}.{field} entry '{ref}' "
                            f"does not match pattern {pattern.pattern}"
                        )


def validate_manifest_schema(manifest: object, violations: Violations) -> None:
    schema = load_json_file(MANIFEST_SCHEMA_PATH)
    if HAS_JSONSCHEMA and schema is not None:
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(manifest), key=lambda e: list(e.path))
        for error in errors:
            loc = "$" + "".join(
                f"[{p}]" if isinstance(p, int) else f".{p}" for p in error.absolute_path
            )
            violations.add(f"contract_manifest.yaml schema violation at {loc}: {error.message}")
    else:
        if not HAS_JSONSCHEMA:
            print(
                "NOTE: 'jsonschema' package not installed; falling back to "
                "structural checks (required keys, ID regexes).\n"
                "      Install it with: pip install jsonschema"
            )
        manual_manifest_checks(manifest, violations)


# ---------------------------------------------------------------------------
# Step 2: collect defined IDs and scan markdown for dangling references
# ---------------------------------------------------------------------------


def collect_defined_ids(manifest: dict, violations: Violations) -> dict[str, set[str]]:
    """Collect every defined ID, keyed by ID class."""
    defined: dict[str, set[str]] = {cls: set() for cls in ID_PATTERNS}

    def add(token: object, source: str) -> None:
        if not isinstance(token, str):
            return
        cls = classify_id(token)
        if cls is None:
            violations.add(f"{source}: '{token}' is not a recognized ID pattern")
            return
        defined[cls].add(token)

    # 1. Manifest definitions.
    for section in ("rules", "stories", "gaps", "behaviors", "controls"):
        items = manifest.get(section)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                add(item.get("id"), f"contract_manifest.yaml:{section}")
                if section == "controls":
                    add(item.get("gate"), f"contract_manifest.yaml:{section}")

    # 2. Class-defining files. A file "defines" an ID class if the ID token
    #    appears in it; this keeps the check robust against differing YAML
    #    layouts across control_register.yaml and the product-contract files.
    class_files: list[tuple[str, Path]] = []
    if CONTROL_REGISTER_PATH.is_file():
        class_files.append(("CTRL/AG/EV", CONTROL_REGISTER_PATH))
    else:
        violations.add(
            "missing control-plane/release/control_register.yaml "
            "(defines CTRL/AG/EV IDs)"
        )
    if PRODUCT_CONTRACT_DIR.is_dir():
        for path in sorted(PRODUCT_CONTRACT_DIR.rglob("*")):
            if path.is_file() and path.suffix in (".md", ".yaml", ".yml"):
                class_files.append(("VP/GAP/R/J", path))
    else:
        violations.add("missing control-plane/product-contract/ (defines VP/GAP/R/J)")
    if BEHAVIORS_DIR.is_dir():
        for path in sorted(BEHAVIORS_DIR.glob("BEH-*.md")):
            class_files.append(("BEH", path))
    else:
        violations.add("missing control-plane/behaviors/ (defines BEH IDs)")

    for _, path in class_files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            violations.add(f"cannot read {path.relative_to(REPO_ROOT)}: {exc}")
            continue
        for token in ID_TOKEN_RE.findall(text):
            cls = classify_id(token)
            if cls is not None:
                defined[cls].add(token)

    return defined


def scan_markdown_for_dangling_refs(
    defined: dict[str, set[str]], violations: Violations
) -> int:
    """Scan control-plane/ and handbook/ markdown for undefined ID tokens."""
    scanned = 0
    for root_name in ("control-plane", "handbook"):
        root = REPO_ROOT / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                violations.add(f"cannot read {path.relative_to(REPO_ROOT)}: {exc}")
                continue
            scanned += 1
            found = sorted(set(ID_TOKEN_RE.findall(text)))
            for token in found:
                cls = classify_id(token)
                if cls is None:
                    continue
                if token not in defined[cls]:
                    violations.add(
                        f"{path.relative_to(REPO_ROOT)}: references undefined "
                        f"{cls} ID '{token}'"
                    )
    return scanned


# ---------------------------------------------------------------------------
# Step 3: behavior card existence + frontmatter id match
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)

# Behavior cards (control-plane/behaviors/) carry their frontmatter as the first
# ```yaml fenced block directly under the H1 title (normative card format, see
# control-plane/behaviors/README.md). Accept that form as a fallback when no
# '---' delimited frontmatter is present.
FENCED_YAML_RE = re.compile(r"^```yaml\s*\n(.*?)\n```\s*(?:\n|\Z)", re.DOTALL | re.MULTILINE)


def extract_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if match is None:
        match = FENCED_YAML_RE.search(text)
    if match is None:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def validate_behavior_cards(
    manifest: dict, violations: Violations
) -> int:
    behaviors = manifest.get("behaviors")
    if not isinstance(behaviors, list):
        return 0
    checked = 0
    card_schema = load_json_file(BEHAVIOR_CARD_SCHEMA_PATH) if HAS_JSONSCHEMA else None
    for item in behaviors:
        if not isinstance(item, dict):
            continue
        beh_id = item.get("id")
        card_rel = item.get("card")
        if not isinstance(card_rel, str) or not card_rel:
            continue  # missing 'card' is already a schema violation
        card_path = REPO_ROOT / card_rel
        if not card_path.is_file():
            violations.add(
                f"behavior {beh_id}: card file '{card_rel}' does not exist on disk"
            )
            continue
        try:
            frontmatter = extract_frontmatter(card_path)
        except OSError as exc:
            violations.add(f"behavior {beh_id}: cannot read card '{card_rel}': {exc}")
            continue
        checked += 1
        if frontmatter is None:
            violations.add(
                f"behavior {beh_id}: card '{card_rel}' has no parseable YAML "
                "frontmatter (expected '---' delimited block with an 'id' field)"
            )
            continue
        fm_id = frontmatter.get("id")
        if fm_id != beh_id:
            violations.add(
                f"behavior {beh_id}: card '{card_rel}' frontmatter id '{fm_id}' "
                f"does not match manifest id '{beh_id}'"
            )
        if card_schema is not None:
            validator = jsonschema.Draft202012Validator(card_schema)
            for error in sorted(
                validator.iter_errors(frontmatter), key=lambda e: list(e.path)
            ):
                loc = "$" + "".join(
                    f"[{p}]" if isinstance(p, int) else f".{p}"
                    for p in error.absolute_path
                )
                violations.add(
                    f"behavior {beh_id}: card '{card_rel}' frontmatter schema "
                    f"violation at {loc}: {error.message}"
                )
    return checked


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    violations = Violations()

    if not MANIFEST_PATH.is_file():
        print(
            "ERROR: control-plane/contract_manifest.yaml not found. "
            "Run from the repository root.",
            file=sys.stderr,
        )
        return 2

    manifest = load_yaml_file(MANIFEST_PATH, violations)
    if manifest is None:
        manifest = {}

    # Step 1: schema / structural validation.
    validate_manifest_schema(manifest, violations)

    # Step 2: collect defined IDs and scan for dangling references.
    defined: dict[str, set[str]] = {cls: set() for cls in ID_PATTERNS}
    files_scanned = 0
    if isinstance(manifest, dict):
        defined = collect_defined_ids(manifest, violations)
        files_scanned = scan_markdown_for_dangling_refs(defined, violations)

    # Step 3: behavior card existence + frontmatter id match.
    cards_checked = 0
    if isinstance(manifest, dict):
        cards_checked = validate_behavior_cards(manifest, violations)

    # Summary.
    total_defined = sum(len(ids) for ids in defined.values())
    defined_breakdown = ", ".join(
        f"{cls}:{len(defined[cls])}" for cls in sorted(defined)
    )
    print("control-plane validation summary")
    print("--------------------------------")
    print(f"manifest:            {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print(f"schema engine:       {'jsonschema' if HAS_JSONSCHEMA else 'manual structural checks'}")
    print(f"defined IDs:         {total_defined} ({defined_breakdown})")
    print(f"markdown files scan: {files_scanned}")
    print(f"behavior cards:      {cards_checked} checked")

    if violations:
        print(f"\nFAILED: {len(violations)} violation(s)")
        for idx, message in enumerate(violations.items, start=1):
            print(f"  {idx}. {message}")
        return 1

    print("\nOK: control plane is internally consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
