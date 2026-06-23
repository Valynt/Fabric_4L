"""§2.5 LLM output parse boundary for Layer 4.

Re-exports ``parse_llm_json`` from the canonical platform-contract module so
all Layer 4 code imports from a stable local path while the implementation
lives in one place.

Direct ``json.loads`` on LLM content is a Contract §2.5 violation — use
``parse_llm_json`` instead.
"""

from canonical.llm_output_parser import parse_llm_json  # noqa: F401

__all__ = ["parse_llm_json"]
