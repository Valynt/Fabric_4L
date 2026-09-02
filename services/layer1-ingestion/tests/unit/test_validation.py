"""Tests for cron expression validation and extraction schema validation.

Covers:
- _validate_cron_expression: malformed, boundary, valid, @-macro, timezone
- ScheduleInput Pydantic model: field_validator integration
- _validate_payload_against_schema: valid payload, missing required fields,
  wrong types, nested errors, empty schema, no schema
- validation_stage Celery task: schema present/absent, tenant isolation,
  malformed prev_result
"""
from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest


# =============================================================================
# Cron expression validation — _validate_cron_expression
# =============================================================================


class TestValidateCronExpression:
    """Unit tests for the _validate_cron_expression helper."""

    def _fn(self, expr: str) -> str:
        pytest.importorskip("croniter")
        from layer1_ingestion.api.schemas.target_schemas import _validate_cron_expression
        return _validate_cron_expression(expr)

    # --- Valid expressions ---

    def test_every_minute(self) -> None:
        assert self._fn("* * * * *") == "* * * * *"

    def test_every_hour_at_zero(self) -> None:
        assert self._fn("0 * * * *") == "0 * * * *"

    def test_daily_midnight(self) -> None:
        assert self._fn("0 0 * * *") == "0 0 * * *"

    def test_weekday_only(self) -> None:
        assert self._fn("0 9 * * 1-5") == "0 9 * * 1-5"

    def test_step_syntax(self) -> None:
        """*/15 step syntax must be accepted."""
        assert self._fn("*/15 * * * *") == "*/15 * * * *"

    def test_list_syntax(self) -> None:
        """Comma-separated lists must be accepted."""
        assert self._fn("0 8,12,18 * * *") == "0 8,12,18 * * *"

    def test_leading_trailing_whitespace_stripped(self) -> None:
        """Leading/trailing whitespace must be stripped before validation."""
        assert self._fn("  0 0 * * *  ") == "0 0 * * *"

    def test_first_of_month(self) -> None:
        assert self._fn("0 0 1 * *") == "0 0 1 * *"

    def test_specific_month(self) -> None:
        assert self._fn("0 0 * 6 *") == "0 0 * 6 *"

    # --- Malformed: wrong field count ---

    def test_four_fields_rejected(self) -> None:
        with pytest.raises(ValueError, match="5 fields"):
            self._fn("0 * * *")

    def test_six_fields_rejected(self) -> None:
        with pytest.raises(ValueError, match="5 fields"):
            self._fn("0 * * * * *")

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._fn("")

    def test_single_field_rejected(self) -> None:
        with pytest.raises(ValueError, match="5 fields"):
            self._fn("*")

    # --- Malformed: out-of-range field values ---

    def test_minute_out_of_range(self) -> None:
        """Minute field 60 is out of range (0-59)."""
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            self._fn("60 * * * *")

    def test_hour_out_of_range(self) -> None:
        """Hour field 24 is out of range (0-23)."""
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            self._fn("0 24 * * *")

    def test_dom_out_of_range(self) -> None:
        """Day-of-month 32 is out of range (1-31)."""
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            self._fn("0 0 32 * *")

    def test_month_out_of_range(self) -> None:
        """Month 13 is out of range (1-12)."""
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            self._fn("0 0 * 13 *")

    def test_dow_out_of_range(self) -> None:
        """Day-of-week 8 is out of range (0-7)."""
        with pytest.raises(ValueError, match="[Ii]nvalid"):
            self._fn("0 0 * * 8")

    def test_non_numeric_field_rejected(self) -> None:
        with pytest.raises(ValueError):
            self._fn("abc * * * *")

    # --- @-macro rejection ---

    def test_at_reboot_rejected(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            self._fn("@reboot")

    def test_at_hourly_rejected(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            self._fn("@hourly")

    def test_at_daily_rejected(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            self._fn("@daily")

    def test_at_weekly_rejected(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            self._fn("@weekly")

    def test_at_monthly_rejected(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            self._fn("@monthly")

    def test_at_yearly_rejected(self) -> None:
        with pytest.raises(ValueError, match="not supported"):
            self._fn("@yearly")


# =============================================================================
# ScheduleInput Pydantic model — cron + timezone validators
# =============================================================================


class TestScheduleInputModel:
    """Integration tests for ScheduleInput field validators."""

    def _model(self, **kwargs):
        from layer1_ingestion.api.schemas.target_schemas import ScheduleInput
        return ScheduleInput(**kwargs)

    # --- cron_expression ---

    def test_none_cron_accepted(self) -> None:
        m = self._model(enabled=False, cron_expression=None)
        assert m.cron_expression is None

    def test_valid_cron_stored(self) -> None:
        m = self._model(enabled=True, cron_expression="0 * * * *")
        assert m.cron_expression == "0 * * * *"

    def test_cron_whitespace_normalised(self) -> None:
        m = self._model(enabled=True, cron_expression="  */5 * * * *  ")
        assert m.cron_expression == "*/5 * * * *"

    def test_invalid_cron_raises_validation_error(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            self._model(enabled=True, cron_expression="not-a-cron")
        assert "cron_expression" in str(exc_info.value)

    def test_macro_cron_raises_validation_error(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            self._model(enabled=True, cron_expression="@hourly")
        assert "cron_expression" in str(exc_info.value)

    def test_four_field_cron_raises_validation_error(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self._model(enabled=True, cron_expression="0 * * *")

    # --- timezone ---

    def test_utc_timezone_accepted(self) -> None:
        m = self._model(timezone="UTC")
        assert m.timezone == "UTC"

    def test_iana_timezone_accepted(self) -> None:
        m = self._model(timezone="America/New_York")
        assert m.timezone == "America/New_York"

    def test_europe_london_accepted(self) -> None:
        m = self._model(timezone="Europe/London")
        assert m.timezone == "Europe/London"

    def test_unknown_timezone_raises_validation_error(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            self._model(timezone="Mars/Olympus_Mons")
        assert "timezone" in str(exc_info.value)

    def test_empty_timezone_raises_validation_error(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self._model(timezone="")

    def test_offset_string_rejected(self) -> None:
        """UTC+5 is not a valid IANA name."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self._model(timezone="UTC+5")

    # --- max_concurrent_jobs bounds ---

    def test_max_concurrent_jobs_minimum(self) -> None:
        m = self._model(max_concurrent_jobs=1)
        assert m.max_concurrent_jobs == 1

    def test_max_concurrent_jobs_maximum(self) -> None:
        m = self._model(max_concurrent_jobs=100)
        assert m.max_concurrent_jobs == 100

    def test_max_concurrent_jobs_zero_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self._model(max_concurrent_jobs=0)

    def test_max_concurrent_jobs_over_limit_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            self._model(max_concurrent_jobs=101)


# =============================================================================
# _validate_payload_against_schema — pure function
# =============================================================================


class TestValidatePayloadAgainstSchema:
    """Unit tests for the JSON Schema validation helper in tasks.py."""

    def _fn(self, data: dict, schema: dict):
        from layer1_ingestion.shared.tasks import _validate_payload_against_schema
        return _validate_payload_against_schema(data, schema)

    # --- Valid payloads ---

    def test_empty_schema_always_valid(self) -> None:
        valid, errors, present, missing = self._fn({"any": "data"}, {})
        assert valid is True
        assert errors == []

    def test_matching_payload_valid(self) -> None:
        schema = {
            "type": "object",
            "required": ["title", "price"],
            "properties": {
                "title": {"type": "string"},
                "price": {"type": "number"},
            },
        }
        valid, errors, present, missing = self._fn(
            {"title": "Widget", "price": 9.99}, schema
        )
        assert valid is True
        assert errors == []
        assert set(present) == {"title", "price"}
        assert missing == []

    def test_extra_fields_allowed_by_default(self) -> None:
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }
        valid, errors, _, _ = self._fn({"name": "x", "extra": True}, schema)
        assert valid is True

    # --- Missing required fields ---

    def test_missing_single_required_field(self) -> None:
        schema = {
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string"}},
        }
        valid, errors, present, missing = self._fn({}, schema)
        assert valid is False
        assert "title" in missing
        assert "title" not in present
        assert len(errors) >= 1

    def test_missing_multiple_required_fields(self) -> None:
        schema = {
            "type": "object",
            "required": ["a", "b", "c"],
            "properties": {
                "a": {"type": "string"},
                "b": {"type": "integer"},
                "c": {"type": "boolean"},
            },
        }
        valid, errors, present, missing = self._fn({"a": "hello"}, schema)
        assert valid is False
        assert set(missing) == {"b", "c"}
        assert present == ["a"]

    # --- Type errors ---

    def test_wrong_type_string_for_number(self) -> None:
        schema = {
            "type": "object",
            "properties": {"price": {"type": "number"}},
        }
        valid, errors, _, _ = self._fn({"price": "not-a-number"}, schema)
        assert valid is False
        assert any("price" in e["path"] for e in errors)

    def test_wrong_type_number_for_string(self) -> None:
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        valid, errors, _, _ = self._fn({"name": 42}, schema)
        assert valid is False

    # --- Nested schema errors ---

    def test_nested_required_field_missing(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "address": {
                    "type": "object",
                    "required": ["city"],
                    "properties": {"city": {"type": "string"}},
                }
            },
        }
        valid, errors, _, _ = self._fn({"address": {}}, schema)
        assert valid is False
        assert any("address" in e["path"] for e in errors)

    def test_nested_type_error(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "meta": {
                    "type": "object",
                    "properties": {"count": {"type": "integer"}},
                }
            },
        }
        valid, errors, _, _ = self._fn({"meta": {"count": "five"}}, schema)
        assert valid is False

    # --- Error structure ---

    def test_error_dict_has_required_keys(self) -> None:
        schema = {
            "type": "object",
            "required": ["x"],
            "properties": {"x": {"type": "string"}},
        }
        _, errors, _, _ = self._fn({}, schema)
        assert len(errors) >= 1
        for err in errors:
            assert "path" in err
            assert "message" in err
            assert "validator" in err

    def test_root_path_is_dollar_sign(self) -> None:
        """Top-level errors should use '$' as path, not empty string."""
        schema = {"type": "object", "required": ["x"]}
        _, errors, _, _ = self._fn({}, schema)
        assert any(e["path"] == "$" for e in errors)

    # --- Boundary: empty data ---

    def test_empty_data_with_no_required_fields_valid(self) -> None:
        schema = {"type": "object", "properties": {"x": {"type": "string"}}}
        valid, errors, _, _ = self._fn({}, schema)
        assert valid is True

    def test_empty_data_with_required_fields_invalid(self) -> None:
        schema = {"type": "object", "required": ["x"]}
        valid, _, _, missing = self._fn({}, schema)
        assert valid is False
        assert "x" in missing


# =============================================================================
# validation_stage Celery task — integration with mocked DB
# =============================================================================


class TestValidationStageTask:
    """Tests for the validation_stage Celery task."""

    def _make_job(self, tenant_id=None, schema=None):
        job = Mock()
        job.tenant_id = tenant_id or uuid4()
        job.progress_stage = None
        job.configuration = {
            "extraction_config": {
                "extraction_schema": schema,
            }
        }
        return job

    def _make_extracted(self, data=None):
        extracted = Mock()
        extracted.data = data or {}
        extracted.validation_schema_valid = None
        extracted.validation_errors = None
        extracted.validation_required_fields_present = None
        extracted.validation_required_fields_missing = None
        return extracted

    def _make_session(self, job, extracted=None):
        session = MagicMock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        session.query.return_value.get.return_value = job

        # Chain: .query().filter().order_by().first()
        filter_mock = MagicMock()
        filter_mock.order_by.return_value.first.return_value = extracted
        session.query.return_value.filter.return_value = filter_mock

        return session

    def _run_validation_stage(self, validation_stage, job, job_id=None):
        return validation_stage.run(
            {"job_id": str(job_id or uuid4())},
            tenant_id=str(job.tenant_id),
        )

    def test_no_schema_completes_without_modifying_extracted(self) -> None:
        """When no extraction_schema is configured, stage completes successfully."""
        from layer1_ingestion.shared.tasks import validation_stage

        job = self._make_job(schema=None)
        extracted = self._make_extracted({"title": "hello"})
        session = self._make_session(job, extracted)

        with patch("layer1_ingestion.shared.tasks.validation.get_db_session", return_value=session):
            result = self._run_validation_stage(validation_stage, job)

        assert result["success"] is True
        # ExtractedData must not have been touched
        assert extracted.validation_schema_valid is None

    def test_valid_payload_sets_schema_valid_true(self) -> None:
        """A payload matching the schema sets validation_schema_valid=True."""
        from layer1_ingestion.shared.tasks import validation_stage

        schema = {
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string"}},
        }
        job = self._make_job(schema=schema)
        extracted = self._make_extracted({"title": "Good Title"})
        session = self._make_session(job, extracted)

        with patch("layer1_ingestion.shared.tasks.validation.get_db_session", return_value=session):
            result = self._run_validation_stage(validation_stage, job)

        assert result["success"] is True
        assert extracted.validation_schema_valid is True
        assert extracted.validation_errors == []
        assert extracted.validation_required_fields_missing == []

    def test_invalid_payload_sets_schema_valid_false(self) -> None:
        """A payload missing required fields sets validation_schema_valid=False."""
        from layer1_ingestion.shared.tasks import validation_stage

        schema = {
            "type": "object",
            "required": ["title", "price"],
            "properties": {
                "title": {"type": "string"},
                "price": {"type": "number"},
            },
        }
        job = self._make_job(schema=schema)
        extracted = self._make_extracted({"title": "Widget"})  # missing price
        session = self._make_session(job, extracted)

        with patch("layer1_ingestion.shared.tasks.validation.get_db_session", return_value=session):
            result = self._run_validation_stage(validation_stage, job)

        assert result["success"] is True
        assert extracted.validation_schema_valid is False
        assert "price" in extracted.validation_required_fields_missing
        assert len(extracted.validation_errors) >= 1

    def test_no_extracted_data_record_completes_gracefully(self) -> None:
        """When no ExtractedData exists for the job, stage completes without error."""
        from layer1_ingestion.shared.tasks import validation_stage

        schema = {"type": "object", "required": ["x"]}
        job = self._make_job(schema=schema)
        session = self._make_session(job, extracted=None)

        with patch("layer1_ingestion.shared.tasks.validation.get_db_session", return_value=session):
            result = self._run_validation_stage(validation_stage, job)

        assert result["success"] is True

    def test_tenant_id_used_in_extracted_data_query(self) -> None:
        """The query for ExtractedData must filter by tenant_id (tenant isolation)."""
        from layer1_ingestion.shared.tasks import validation_stage

        tenant_id = uuid4()
        schema = {"type": "object"}
        job = self._make_job(tenant_id=tenant_id, schema=schema)
        extracted = self._make_extracted({})
        session = self._make_session(job, extracted)

        with patch("layer1_ingestion.shared.tasks.validation.get_db_session", return_value=session):
            self._run_validation_stage(validation_stage, job)

        # Verify .filter() was called (tenant_id scoping)
        assert session.query.return_value.filter.called

    def test_job_not_found_raises_value_error(self) -> None:
        """Missing job must raise ValueError (not silently succeed)."""
        from layer1_ingestion.shared.tasks import validation_stage

        session = MagicMock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        session.query.return_value.get.return_value = None  # job not found

        with patch("layer1_ingestion.shared.tasks.validation.get_db_session", return_value=session):
            with pytest.raises(Exception):
                validation_stage.run({"job_id": str(uuid4())})

    def test_malformed_prev_result_missing_job_id_raises(self) -> None:
        """prev_result without job_id must raise immediately."""
        from layer1_ingestion.shared.tasks import validation_stage

        with pytest.raises((KeyError, Exception)):
            validation_stage.run({})

    def test_malformed_prev_result_invalid_uuid_raises(self) -> None:
        """prev_result with a non-UUID job_id must raise ValueError."""
        from layer1_ingestion.shared.tasks import validation_stage

        with pytest.raises((ValueError, Exception)):
            validation_stage.run({"job_id": "not-a-uuid"})

    def test_schema_not_a_dict_skips_validation(self) -> None:
        """A non-dict extraction_schema (e.g. a string) must be ignored safely."""
        from layer1_ingestion.shared.tasks import validation_stage

        job = self._make_job(schema="not-a-dict")
        extracted = self._make_extracted({"x": 1})
        session = self._make_session(job, extracted)

        with patch("layer1_ingestion.shared.tasks.validation.get_db_session", return_value=session):
            result = self._run_validation_stage(validation_stage, job)

        assert result["success"] is True
        assert extracted.validation_schema_valid is None

    def test_type_errors_in_payload_recorded(self) -> None:
        """Type mismatches in the payload are recorded in validation_errors."""
        from layer1_ingestion.shared.tasks import validation_stage

        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
        }
        job = self._make_job(schema=schema)
        extracted = self._make_extracted({"count": "five"})  # wrong type
        session = self._make_session(job, extracted)

        with patch("layer1_ingestion.shared.tasks.validation.get_db_session", return_value=session):
            self._run_validation_stage(validation_stage, job)

        assert extracted.validation_schema_valid is False
        assert len(extracted.validation_errors) >= 1
        assert any("count" in e["path"] for e in extracted.validation_errors)
