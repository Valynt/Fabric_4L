from __future__ import annotations

"""
PromptRegistry — loads and caches versioned prompt files from disk.

Prompts live under ``prompts/<workflow>/<version>/<name>.md`` relative to the
service root.  Each file carries a YAML frontmatter block that declares
metadata (prompt_id, version, model_task, temperature, etc.).  The body is the
raw prompt template, which may contain Jinja-style ``{{ variable }}`` tokens
rendered at call time.

Usage::

    registry = PromptRegistry()
    template = registry.get("roi_calculator", "hypothesis_generation")
    rendered = template.render(account_name="Acme", context_json="...")
"""


import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Canonical prompts root: services/layer4-agents/prompts/.
# In the Docker image prompts are copied into src/, so prefer the in-image
# location when it exists (mirrors harness/tests/test_llm_rewrite.py).
_SRC_ROOT = Path(__file__).resolve().parents[2]  # services/layer4-agents/src/
_SERVICE_ROOT = _SRC_ROOT.parent                 # services/layer4-agents/
_PROMPTS_ROOT = _SRC_ROOT / "prompts" if (_SRC_ROOT / "prompts").exists() else _SERVICE_ROOT / "prompts"

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TEMPLATE_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


@dataclass(frozen=True)
class PromptTemplate:
    """Parsed prompt file with metadata and renderable body."""

    prompt_id: str
    version: str
    workflow_type: str
    model_task: str  # reasoning | extraction | narrative
    body: str
    requires_json: bool = False
    output_schema: str | None = None
    temperature: float = 0.2
    max_tokens: int = 2000
    content_hash: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def render(self, **kwargs: Any) -> str:
        """Substitute ``{{ variable }}`` tokens in the body.

        Unknown variables are left as-is so callers can detect missing context.
        """
        result = self.body
        for key, value in kwargs.items():
            result = result.replace("{{ " + key + " }}", str(value))
            result = result.replace("{{" + key + "}}", str(value))
        return result

    def variables(self) -> list[str]:
        """Return all template variable names declared in the body."""
        return _TEMPLATE_VAR_RE.findall(self.body)

    def missing_variables(self, **kwargs: Any) -> list[str]:
        """Return variable names present in the body but not supplied."""
        return [v for v in self.variables() if v not in kwargs]

    def to_prompt_ref(self, reasoning_policy_id: str | None = None) -> dict[str, Any]:
        """Return a PromptRef-shaped dict for provenance envelopes.

        Includes the content hash so downstream layers can detect prompt drift.
        """
        return {
            "prompt_id": self.prompt_id,
            "version": self.version,
            "reasoning_policy_id": reasoning_policy_id,
            "content_hash": self.content_hash,
        }


# ---------------------------------------------------------------------------
# Baseline artifacts
# ---------------------------------------------------------------------------


def _default_baselines_root() -> Path:
    """Return the canonical evals/baselines directory relative to the repo root.

    The registry lives under services/layer4-agents/src/layer4_agents/harness/;
    the repo root is five parents above that (parents[5]).
    """
    return Path(__file__).resolve().parents[5] / "evals" / "baselines"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class PromptRegistry:
    """Loads prompt files from disk and caches them in memory.

    Parameters
    ----------
    prompts_root:
        Override the default prompts directory (useful in tests).
    default_version:
        Version folder to use when ``version`` is not specified in ``get()``.
    """

    def __init__(
        self,
        prompts_root: Path | None = None,
        default_version: str = "v1",
        baselines_root: Path | None = None,
    ) -> None:
        env_root = os.getenv("LAYER4_PROMPTS_ROOT")
        self._root = prompts_root or (Path(env_root) if env_root else _PROMPTS_ROOT)
        self._default_version = default_version
        self._baselines_root = baselines_root or _default_baselines_root()
        self._cache: dict[str, PromptTemplate] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        workflow: str,
        name: str,
        version: str | None = None,
    ) -> PromptTemplate:
        """Return the parsed PromptTemplate for ``workflow/version/name.md``.

        Results are cached after the first load.

        Raises
        ------
        FileNotFoundError
            If the prompt file does not exist.
        ValueError
            If the frontmatter is missing or malformed.
        """
        v = version or self._default_version
        cache_key = f"{workflow}/{v}/{name}"
        if cache_key not in self._cache:
            self._cache[cache_key] = self._load(workflow, name, v)
        return self._cache[cache_key]

    def list_prompts(self, workflow: str | None = None) -> list[str]:
        """Return cache keys for all loaded prompts, optionally filtered by workflow."""
        if workflow is None:
            return list(self._cache.keys())
        return [k for k in self._cache if k.startswith(f"{workflow}/")]

    def preload(self, workflow: str, version: str | None = None) -> int:
        """Eagerly load all prompts for a workflow. Returns count loaded."""
        v = version or self._default_version
        workflow_dir = self._root / workflow / v
        if not workflow_dir.exists():
            return 0
        count = 0
        for md_file in workflow_dir.glob("*.md"):
            name = md_file.stem
            cache_key = f"{workflow}/{v}/{name}"
            if cache_key not in self._cache:
                try:
                    self._cache[cache_key] = self._load(workflow, name, v)
                    count += 1
                except (ValueError, FileNotFoundError):
                    pass
        return count

    def load_output_schema(self, workflow: str, version: str | None = None) -> dict[str, Any]:
        """Load and parse the output_schema.json for a workflow."""
        v = version or self._default_version
        schema_path = self._root / workflow / v / "output_schema.json"
        if not schema_path.exists():
            raise FileNotFoundError(f"No output schema at {schema_path}")
        return json.loads(schema_path.read_text(encoding="utf-8"))

    def baseline_for(self, prompt_id: str, version: str | None = None) -> dict[str, Any] | None:
        """Return the frozen eval baseline artifact for a prompt version, if present."""
        v = version or self._default_version
        baseline_path = self._baselines_root / f"prompt-{prompt_id}-{v}.json"
        if not baseline_path.exists():
            return None
        return json.loads(baseline_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self, workflow: str, name: str, version: str) -> PromptTemplate:
        path = self._root / workflow / version / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(
                f"Prompt not found: {path}. "
                f"Expected prompts/{workflow}/{version}/{name}.md"
            )

        raw = path.read_text(encoding="utf-8")
        metadata, body = self._parse_frontmatter(raw, path)
        body = body.strip()
        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

        return PromptTemplate(
            prompt_id=metadata.get("prompt_id", f"{workflow}.{name}"),
            version=metadata.get("version", version),
            workflow_type=metadata.get("workflow_type", workflow),
            model_task=metadata.get("model_task", "reasoning"),
            body=body,
            requires_json=bool(metadata.get("requires_json", False)),
            output_schema=metadata.get("output_schema"),
            temperature=float(metadata.get("temperature", 0.2)),
            max_tokens=int(metadata.get("max_tokens", 2000)),
            content_hash=content_hash,
            raw_metadata=metadata,
        )

    @staticmethod
    def _parse_frontmatter(raw: str, path: Path) -> tuple[dict[str, Any], str]:
        match = _FRONTMATTER_RE.match(raw)
        if not match:
            raise ValueError(
                f"Prompt file {path} is missing YAML frontmatter. "
                "Expected '---\\n...\\n---\\n' at the top of the file."
            )
        try:
            metadata = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML frontmatter in {path}: {exc}") from exc

        body = raw[match.end():]
        return metadata, body


# ---------------------------------------------------------------------------
# Module-level singleton (lazy)
# ---------------------------------------------------------------------------

_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    """Return the module-level PromptRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
