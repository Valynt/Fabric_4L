"""Contracts for the non-production Layer 1 deterministic validation seed."""

from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from layer1_ingestion.api.validation_seed_routes import (
    ValidationJobSeedRequest,
    authorize_validation_seed,
    seed_validation_job,
)
from layer1_ingestion.shared.models import ScrapingJob, ScrapingTarget


def test_validation_seed_is_denied_in_production() -> None:
    with pytest.raises(HTTPException) as exc_info:
        authorize_validation_seed(
            environment="production",
            privileged_reason="validation-seed",
            roles=["super_admin"],
        )

    assert exc_info.value.status_code == 403


@pytest.mark.parametrize(
    ("reason", "roles"),
    [(None, ["super_admin"]), ("wrong-purpose", ["super_admin"]), ("validation-seed", ["admin"])],
)
def test_validation_seed_requires_explicit_privileged_super_admin(
    reason: str | None,
    roles: list[str],
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        authorize_validation_seed(
            environment="development",
            privileged_reason=reason,
            roles=roles,
        )

    assert exc_info.value.status_code == 403


def test_validation_seed_upserts_tenant_scoped_completed_job(
    db: Session,
    org_id: UUID,
    user_id: UUID,
) -> None:
    request = ValidationJobSeedRequest(
        domain="meridian-auto.com",
        url="https://meridian-auto.com",
        status="COMPLETED",
    )

    first = seed_validation_job(
        request=request,
        privileged_reason="validation-seed",
        org_id=org_id,
        user_id=user_id,
        roles=["super_admin"],
        db=db,
        environment="development",
    )
    second = seed_validation_job(
        request=request,
        privileged_reason="validation-seed",
        org_id=org_id,
        user_id=user_id,
        roles=["super_admin"],
        db=db,
        environment="development",
    )

    assert first.seeded is True
    assert second.job_id == first.job_id
    assert second.domain == "meridian-auto.com"
    assert second.status == "COMPLETED"
    assert second.progress_percent_complete == 100
    assert db.query(ScrapingTarget).filter_by(tenant_id=org_id).count() == 1
    assert db.query(ScrapingJob).filter_by(tenant_id=org_id).count() == 1
