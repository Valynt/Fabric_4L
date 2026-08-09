from __future__ import annotations

"""
Tests for the LLM-powered agent rewrite components.

Covers:
  - PromptRegistry: load, render, variable detection, output schema
  - AgentResult: degraded output contract governance rules
  - GovernedLLMClient: model resolution, token capping, error classification
  - TogetherAIProvider: JSON parse fallback
  - LLMCostCalculator: Together.ai pricing entries
  - get_llm_provider factory: provider selection from env
"""


import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2]
_SERVICE_ROOT = _SRC.parent
_PROMPTS = _SERVICE_ROOT / "prompts"
_CONFIG = _SERVICE_ROOT / "config" / "harness.runtime.yaml"
_SHARED = _SERVICE_ROOT.parents[1] / "packages" / "shared" / "src"
_PLATFORM_CONTRACT = _SERVICE_ROOT.parents[1] / "packages" / "platform-contract" / "src" / "python"

sys.path.insert(0, str(_SRC))
sys.path.insert(0, str(_SHARED))
sys.path.insert(0, str(_PLATFORM_CONTRACT))


def _load_direct(rel_path: str):
    abs_path = _SRC / rel_path
    mod_name = rel_path.replace("/", ".").replace(".py", "")
    spec = importlib.util.spec_from_file_location(mod_name, abs_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod  # register before exec so @dataclass works
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# PromptRegistry
# ---------------------------------------------------------------------------

class TestPromptRegistry:
    def setup_method(self):
        pr_mod = _load_direct("harness/prompt_registry.py")
        self.PromptRegistry = pr_mod.PromptRegistry
        self.registry = self.PromptRegistry(prompts_root=_PROMPTS)

    def test_load_roi_system(self):
        t = self.registry.get("roi_calculator", "system")
        assert t.prompt_id == "roi_calculator.system"
        assert t.model_task == "reasoning"
        assert len(t.body) > 10

    def test_load_hypothesis_generation(self):
        t = self.registry.get("roi_calculator", "hypothesis_generation")
        assert t.requires_json is True
        assert t.temperature == pytest.approx(0.2)
        assert t.max_tokens >= 2000  # 2000 or 3000 depending on prompt version

    def test_variables_detected(self):
        t = self.registry.get("roi_calculator", "hypothesis_generation")
        vars_ = t.variables()
        assert "account_name" in vars_
        assert "formula_outputs_json" in vars_

    def test_render_substitutes_variables(self):
        t = self.registry.get("roi_calculator", "hypothesis_generation")
        rendered = t.render(
            account_name="Acme Corp",
            formula_outputs_json="[]",
            value_drivers_json="{}",
            industry="SaaS",
            company_size="500",
        )
        assert "Acme Corp" in rendered
        assert "{{ account_name }}" not in rendered

    def test_missing_variables_detected(self):
        t = self.registry.get("roi_calculator", "hypothesis_generation")
        missing = t.missing_variables(account_name="Acme")
        assert "formula_outputs_json" in missing
        assert "account_name" not in missing

    def test_cache_hit(self):
        t1 = self.registry.get("roi_calculator", "system")
        t2 = self.registry.get("roi_calculator", "system")
        assert t1 is t2

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            self.registry.get("roi_calculator", "nonexistent_prompt")

    def test_output_schema_loads(self):
        schema = self.registry.load_output_schema("roi_calculator")
        assert schema["title"] == "RoiHypothesisOutput"
        # schema has either "hypothesis" (single) or "hypotheses" (list) depending on version
        props = schema["properties"]
        assert "hypothesis" in props or "hypotheses" in props

    def test_all_workflows_load(self):
        workflows = [
            ("roi_calculator", ["system", "hypothesis_generation"]),
            ("whitespace_analysis", ["system", "extraction", "gap_analysis", "hypothesis_generation"]),
            ("business_case", ["system", "gather_inputs", "generate_sections", "validate_claims"]),
            ("signal_detection", ["system", "classification", "hypothesis_generation", "narrative"]),
            ("narrative_builder", ["system", "executive_summary", "value_narrative", "risk_narrative"]),
        ]
        for workflow, names in workflows:
            for name in names:
                t = self.registry.get(workflow, name)
                assert t.prompt_id, f"Missing prompt_id for {workflow}/{name}"

    def test_preload_returns_count(self):
        count = self.registry.preload("whitespace_analysis")
        assert count >= 4

    def test_invalid_frontmatter_raises(self, tmp_path):
        bad = tmp_path / "workflow" / "v1" / "bad.md"
        bad.parent.mkdir(parents=True)
        bad.write_text("no frontmatter here\njust text")
        reg = self.PromptRegistry(prompts_root=tmp_path)
        with pytest.raises(ValueError, match="frontmatter"):
            reg.get("workflow", "bad")

    def test_all_output_schemas_valid(self):
        for workflow in ["roi_calculator", "whitespace_analysis", "business_case",
                         "signal_detection", "narrative_builder"]:
            schema = self.registry.load_output_schema(workflow)
            assert "title" in schema
            assert "properties" in schema


# ---------------------------------------------------------------------------
# AgentResult — governance rules (real production class)
# ---------------------------------------------------------------------------

def _load_agent_result_class():
    """Load the real AgentResult from agents/base.py, bypassing __init__.py."""
    mod = _load_direct("agents/base.py")
    return mod.AgentResult


class TestAgentResult:
    def setup_method(self):
        self.AgentResult = _load_agent_result_class()

    def _make(self, **kwargs):
        return self.AgentResult(payload={}, workflow_type="roi_calculator", tenant_id="t1", **kwargs)

    def test_default_is_degraded(self):
        r = self._make()
        assert not r.llm_enrichment
        assert not r.customer_facing_allowed
        assert r.human_review_required
        assert "no_llm_enrichment" in r.degraded_reason

    def test_high_confidence_llm_promotes(self):
        r = self._make()
        r.mark_llm_enriched("model-x", 500, 200, 0.85)
        assert r.llm_enrichment
        assert r.customer_facing_allowed
        assert not r.human_review_required
        assert r.degraded_reason is None

    def test_low_confidence_stays_degraded(self):
        r = self._make()
        r.mark_llm_enriched("model-x", 100, 50, 0.3)
        assert not r.customer_facing_allowed
        assert r.human_review_required
        assert "low_confidence" in r.degraded_reason

    def test_explicit_human_review_blocks_customer_facing(self):
        r = self._make(llm_enrichment=True, confidence=0.9, human_review_required=True)
        assert not r.customer_facing_allowed

    def test_boundary_040_passes(self):
        r = self._make()
        r.mark_llm_enriched("m", 0, 0, 0.4)
        assert r.customer_facing_allowed

    def test_boundary_039_fails(self):
        r = self._make()
        r.mark_llm_enriched("m", 0, 0, 0.39)
        assert not r.customer_facing_allowed

    def test_to_dict_round_trip(self):
        r = self._make()
        r.mark_llm_enriched("meta-llama/Llama-3.3-70B", 500, 200, 0.85)
        d = r.to_dict()
        assert d["llm_enrichment"] is True
        assert d["model_used"] == "meta-llama/Llama-3.3-70B"
        assert d["customer_facing_allowed"] is True

    def test_tenant_id_preserved(self):
        r = self._make()
        assert r.to_dict()["tenant_id"] == "t1"

    def test_both_reasons_when_no_llm_and_low_confidence(self):
        r = self._make(confidence=0.0)
        assert "no_llm_enrichment" in r.degraded_reason
        assert "low_confidence" in r.degraded_reason


# ---------------------------------------------------------------------------
# LLMCostCalculator — Together.ai pricing
# ---------------------------------------------------------------------------

class TestLLMCostCalculatorTogether:
    def setup_method(self):
        self.mod = _load_direct("metrics/llm_cost_calculator.py")
        self.calc = self.mod.LLMCostCalculator()

    def test_llama_70b_cost_positive(self):
        cost = self.calc.calculate_cost(
            "together", "meta-llama/Llama-3.3-70B-Instruct-Turbo", 1000, 500
        )
        assert 0 < cost < 0.01

    def test_llama_8b_cheaper_than_70b(self):
        c8 = self.calc.calculate_cost("together", "meta-llama/Llama-3.1-8B-Instruct-Turbo", 1000, 500)
        c70 = self.calc.calculate_cost("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo", 1000, 500)
        assert c8 < c70

    def test_unknown_model_zero(self):
        assert self.calc.calculate_cost("together", "unknown/model", 1000, 500) == 0.0

    def test_openai_still_works(self):
        assert self.calc.calculate_cost("openai", "gpt-4o", 1000, 500) > 0

    def test_zero_tokens_zero_cost(self):
        assert self.calc.calculate_cost("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo", 0, 0) == 0.0

    def test_all_together_models_priced(self):
        for model in [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "meta-llama/Llama-3.1-8B-Instruct-Turbo",
            "meta-llama/Llama-3.1-405B-Instruct-Turbo",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "deepseek-ai/DeepSeek-R1",
        ]:
            assert self.calc.calculate_cost("together", model, 1000, 500) > 0, f"No price for {model}"


# ---------------------------------------------------------------------------
# TogetherAIProvider — JSON parsing (real static method)
# ---------------------------------------------------------------------------

class TestTogetherJSONParsing:
    def setup_method(self):
        mod = _load_direct("services/together_provider.py")
        self._parse = mod.TogetherAIProvider._parse_json_response

    def test_clean_json(self):
        assert self._parse('{"a": 1}') == {"a": 1}

    def test_json_with_preamble(self):
        assert self._parse('Here:\n{"key": "value"}') == {"key": "value"}

    def test_no_json_returns_empty(self):
        assert self._parse("No JSON here.") == {}

    def test_nested_json(self):
        r = self._parse('{"h": [{"c": 0.8}]}')
        assert r["h"][0]["c"] == 0.8

    def test_array_json(self):
        r = self._parse('[{"id": 1}, {"id": 2}]')
        assert len(r) == 2

    def test_json_after_markdown_fence(self):
        # Model wraps output in ```json ... ```
        r = self._parse('```json\n{"x": 42}\n```')
        assert r == {"x": 42}

    def test_truncated_preamble_ignored(self):
        r = self._parse('Sure! Here is the result:\n\n{"score": 0.9}')
        assert r["score"] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# GovernedLLMClient — config and utility logic
# ---------------------------------------------------------------------------

class TestGovernedLLMClientConfig:
    def setup_method(self):
        import yaml
        self.config = yaml.safe_load(_CONFIG.read_text())

    def test_together_reasoning_model(self):
        model = self.config["llm"]["models"]["together"]["reasoning"]
        assert model and "/" in model

    def test_openai_extraction_model(self):
        assert self.config["llm"]["models"]["openai"]["extraction"]

    def test_token_budgets(self):
        b = self.config["llm"]["token_budgets"]
        assert b["reasoning"]["max_completion_tokens"] >= 1000
        assert b["extraction"]["max_completion_tokens"] >= 500
        assert b["narrative"]["max_completion_tokens"] >= 500

    def test_retry_config(self):
        r = self.config["llm"]["retry"]
        assert r["max_attempts"] >= 2
        assert "TIMEOUT" in r["retryable_categories"]
        assert "RATE_LIMIT" in r["retryable_categories"]

    def test_max_cost_per_call(self):
        assert self.config["llm"]["max_cost_per_call_usd"] > 0

    def test_error_classification(self):
        """Calls the real GovernedLLMClient._classify_error static method."""
        mod = _load_direct("services/governed_llm_client.py")
        classify = mod.GovernedLLMClient._classify_error

        assert classify(Exception("connection timeout")) == "TIMEOUT"
        assert classify(Exception("rate limit exceeded")) == "RATE_LIMIT"
        assert classify(Exception("401 unauthorized")) == "AUTH"
        assert classify(Exception("model not found")) == "PROVIDER"

    def test_token_cap(self):
        """Calls the real GovernedLLMClient._cap_tokens instance method unbound."""
        mod = _load_direct("services/governed_llm_client.py")
        # _cap_tokens is an instance method; pass None as self since it uses no instance state
        cap = mod.GovernedLLMClient._cap_tokens

        assert cap(None, None, 3000) == 3000
        assert cap(None, 5000, 3000) == 3000
        assert cap(None, 1000, 3000) == 1000
        assert cap(None, None, None) is None

    def test_parse_json(self):
        """parse_llm_json (canonical §2.5 boundary) handles clean JSON, prose-wrapped JSON, and failures."""
        # GovernedLLMClient delegates JSON parsing to parse_llm_json per §2.5.
        # Test the canonical implementation directly.
        from canonical.llm_output_parser import parse_llm_json

        assert parse_llm_json('{"a": 1}') == {"a": 1}
        assert parse_llm_json('Here is the result:\n{"key": "val"}') == {"key": "val"}
        assert parse_llm_json("no json here") == {}


# ---------------------------------------------------------------------------
# get_llm_provider factory
# ---------------------------------------------------------------------------

class TestGetLLMProviderFactory:
    def _name(self, p) -> str:
        return type(p).__name__

    def test_together_is_default(self):
        clean_env = {k: v for k, v in os.environ.items() if k != "LAYER4_LLM_PROVIDER"}
        with patch.dict(os.environ, clean_env, clear=True):
            mod = _load_direct("services/llm_provider.py")
            assert "Together" in self._name(mod.get_llm_provider())

    def test_env_selects_openai(self):
        with patch.dict(os.environ, {"LAYER4_LLM_PROVIDER": "openai"}):
            mod = _load_direct("services/llm_provider.py")
            assert "OpenAI" in self._name(mod.get_llm_provider())

    def test_config_dict_selects_together(self):
        clean_env = {k: v for k, v in os.environ.items() if k != "LAYER4_LLM_PROVIDER"}
        with patch.dict(os.environ, clean_env, clear=True):
            mod = _load_direct("services/llm_provider.py")
            assert "Together" in self._name(mod.get_llm_provider({"llm_provider": "together"}))

    def test_unknown_falls_back_to_together(self):
        with patch.dict(os.environ, {"LAYER4_LLM_PROVIDER": "unknown_xyz"}):
            mod = _load_direct("services/llm_provider.py")
            assert "Together" in self._name(mod.get_llm_provider())


# ---------------------------------------------------------------------------
# AIModelStatus component — structural smoke tests
# ---------------------------------------------------------------------------

class TestAIModelStatusComponent:
    @pytest.fixture(autouse=True)
    def _path(self):
        self.tsx = (
            _SERVICE_ROOT.parents[1]
            / "apps" / "web" / "src" / "components" / "AIModelStatus.tsx"
        )

    def test_file_exists(self):
        assert self.tsx.exists()

    def test_exports_component(self):
        assert "export function AIModelStatus" in self.tsx.read_text()

    def test_exports_interfaces(self):
        src = self.tsx.read_text()
        for sym in ["AIModelStatusProps", "AIEnrichmentStatus", "AIModelAssignments"]:
            assert sym in src, f"Missing: {sym}"

    def test_governance_flags_present(self):
        src = self.tsx.read_text()
        for flag in ["llm_enrichment", "customer_facing_allowed", "human_review_required", "degraded_reason"]:
            assert flag in src, f"Missing flag: {flag}"

    def test_together_provider_configured(self):
        src = self.tsx.read_text()
        assert "together" in src
        assert "Together.ai" in src

    def test_uses_design_system(self):
        src = self.tsx.read_text()
        assert "cn(" in src
        assert "lucide-react" in src
