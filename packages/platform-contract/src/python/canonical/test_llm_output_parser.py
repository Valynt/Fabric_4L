"""Contract tests for the canonical §2.5 LLM output parse boundary."""

import logging

from .llm_output_parser import _find_matching_close, parse_llm_json


# ---------------------------------------------------------------------------
# _find_matching_close
# ---------------------------------------------------------------------------


class TestFindMatchingClose:
    def test_simple_object(self):
        assert _find_matching_close('{"k": 1}', 0, '{', '}') == 7

    def test_nested_object(self):
        s = '{"outer": {"inner": 1}}'
        assert _find_matching_close(s, 0, '{', '}') == len(s) - 1

    def test_stray_bracket_after_json(self):
        # rfind would return the trailing } — depth counter must not
        s = '{"k": "v"} extra } brace'
        assert _find_matching_close(s, 0, '{', '}') == 9

    def test_array(self):
        s = '[1, 2, 3]'
        assert _find_matching_close(s, 0, '[', ']') == 8

    def test_no_matching_close_returns_minus_one(self):
        assert _find_matching_close('{"unclosed"', 0, '{', '}') == -1

    def test_start_not_at_zero(self):
        s = 'prefix {"k": 1} suffix'
        start = s.find('{')
        assert _find_matching_close(s, start, '{', '}') == s.index('}')


# ---------------------------------------------------------------------------
# parse_llm_json — stage 1 (direct parse)
# ---------------------------------------------------------------------------


class TestParseLlmJsonDirectParse:
    def test_clean_json_dict(self):
        assert parse_llm_json('{"key": "value"}') == {"key": "value"}

    def test_nested_dict(self):
        result = parse_llm_json('{"outer": {"inner": 42}}')
        assert result == {"outer": {"inner": 42}}

    def test_json_array_wrapped_in_result_key(self):
        result = parse_llm_json('[1, 2, 3]')
        assert result == {"result": [1, 2, 3]}

    def test_json_scalar_wrapped_in_result_key(self):
        result = parse_llm_json('42')
        assert result == {"result": 42}

    def test_empty_string_returns_empty_dict(self):
        assert parse_llm_json('') == {}

    def test_whitespace_only_returns_empty_dict(self):
        assert parse_llm_json('   \n\t  ') == {}

    def test_empty_json_object(self):
        assert parse_llm_json('{}') == {}

    def test_unicode_values(self):
        result = parse_llm_json('{"name": "caf\u00e9"}')
        assert result == {"name": "café"}


# ---------------------------------------------------------------------------
# parse_llm_json — stage 2 (bracket extraction)
# ---------------------------------------------------------------------------


class TestParseLlmJsonBracketExtraction:
    def test_json_in_prose(self):
        content = 'Here is the result: {"intent": "query", "confidence": 0.9} as requested.'
        assert parse_llm_json(content) == {"intent": "query", "confidence": 0.9}

    def test_markdown_fenced_json(self):
        content = '```json\n{"key": "value"}\n```'
        assert parse_llm_json(content) == {"key": "value"}

    def test_stray_bracket_after_valid_json(self):
        # The rfind bug: trailing } must not corrupt the extracted span
        content = '{"key": "value"} some prose with a } brace'
        assert parse_llm_json(content) == {"key": "value"}

    def test_json_array_in_prose_wrapped(self):
        content = 'The items are: [1, 2, 3] in the list.'
        assert parse_llm_json(content) == {"result": [1, 2, 3]}

    def test_nested_json_in_prose(self):
        content = 'Output: {"outer": {"inner": true}} done.'
        assert parse_llm_json(content) == {"outer": {"inner": True}}

    def test_unclosed_bracket_falls_through_to_empty(self):
        content = 'Result: {"unclosed": "json"'
        assert parse_llm_json(content) == {}

    def test_json_after_colon_prefix(self):
        content = 'Response: {"status": "ok"}'
        assert parse_llm_json(content) == {"status": "ok"}


# ---------------------------------------------------------------------------
# parse_llm_json — total failure path
# ---------------------------------------------------------------------------


class TestParseLlmJsonFailurePath:
    def test_plain_text_returns_empty_dict(self):
        assert parse_llm_json('no json here at all') == {}

    def test_malformed_json_returns_empty_dict(self):
        assert parse_llm_json('{bad json: [}') == {}

    def test_failure_emits_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger='canonical.llm_output_parser'):
            result = parse_llm_json('no json here', call_site='test_site')
        assert result == {}
        assert 'test_site' in caplog.text
        assert 'could not extract JSON' in caplog.text

    def test_failure_without_call_site_still_warns(self, caplog):
        with caplog.at_level(logging.WARNING, logger='canonical.llm_output_parser'):
            result = parse_llm_json('no json here')
        assert result == {}
        assert 'could not extract JSON' in caplog.text

    def test_long_content_truncated_in_warning(self, caplog):
        long_content = 'x' * 500
        with caplog.at_level(logging.WARNING, logger='canonical.llm_output_parser'):
            parse_llm_json(long_content, call_site='truncation_test')
        # Warning should contain at most 200 chars of content repr
        assert long_content[201:] not in caplog.text


# ---------------------------------------------------------------------------
# call_site label propagation
# ---------------------------------------------------------------------------


class TestCallSiteLabel:
    def test_call_site_appears_in_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger='canonical.llm_output_parser'):
            parse_llm_json('not json', call_site='governed_llm_client.call_structured')
        assert 'governed_llm_client.call_structured' in caplog.text

    def test_no_call_site_no_brackets_in_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger='canonical.llm_output_parser'):
            parse_llm_json('not json')
        assert '[' not in caplog.text or 'parse_llm_json:' in caplog.text
