"""§2.5 LLM output parse boundary for Layer 2.

Re-exports ``parse_llm_json`` from the canonical platform-contract module so
all Layer 2 extraction code imports from a stable local path while the
implementation lives in one place.

Direct ``json.loads`` on LLM content is a Contract §2.5 violation — use
``parse_llm_json`` instead.
"""

from canonical.llm_output_parser import (  # noqa: F401
    LLMOutputParseError,
    parse_llm_json,
    validate_llm_output_schema,
)

__all__ = ["LLMOutputParseError", "parse_llm_json", "validate_llm_output_schema"]
