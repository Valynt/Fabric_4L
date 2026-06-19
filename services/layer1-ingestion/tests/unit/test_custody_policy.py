"""Tests for the v3.0 custody policy service."""

from __future__ import annotations

import pytest

from layer1_ingestion.shared.custody_policy import (
    DEFAULT_CUSTODY_POLICY,
    CustodyMode,
    CustodyPolicyService,
)
from layer1_ingestion.shared.models import SourceType


class TestCustodyPolicyService:
    def test_notes_default_is_full_custody(self) -> None:
        service = CustodyPolicyService()
        decision = service.decide(SourceType.NOTES)
        assert decision.mode == CustodyMode.FULL_CUSTODY
        assert decision.store_raw is True
        assert decision.store_extracted is True

    def test_crm_default_is_reference_extract(self) -> None:
        service = CustodyPolicyService()
        decision = service.decide(SourceType.CRM)
        assert decision.mode == CustodyMode.REFERENCE_EXTRACT
        assert decision.store_raw is False
        assert decision.store_extracted is True

    def test_customer_hosted_flag_overrides(self) -> None:
        service = CustodyPolicyService()
        decision = service.decide(SourceType.NOTES, customer_hosted=True)
        assert decision.mode == CustodyMode.CUSTOMER_HOSTED
        assert decision.store_raw is False
        assert decision.store_extracted is False

    def test_account_override_applies(self) -> None:
        config = {
            "custody_overrides": {
                "pdf": {
                    "mode": "C",
                    "store_raw": False,
                    "store_extracted": False,
                    "store_reference_only": True,
                    "allowed_backends": ["customer_hosted"],
                    "retention_class": "customer_hosted",
                }
            }
        }
        service = CustodyPolicyService(account_config=config)
        decision = service.decide(SourceType.PDF)
        assert decision.mode == CustodyMode.CUSTOMER_HOSTED

    def test_connector_validation(self) -> None:
        service = CustodyPolicyService()
        decision = service.decide(SourceType.CRM)
        with pytest.raises(ValueError):
            service.validate_connector_against_policy(decision, "postgres")

    def test_all_source_types_have_default_policy(self) -> None:
        for source_type in SourceType:
            assert source_type in DEFAULT_CUSTODY_POLICY
