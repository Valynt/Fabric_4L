from __future__ import annotations

"""Persisted interactive business-case scenarios."""


from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SavedBusinessCaseScenario(Base):
    """Server-side saved C1/what-if scenario for a business case."""

    __tablename__ = "saved_business_case_scenarios"

    scenario_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    adjustments: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_saved_scenarios_case_tenant", "case_id", "tenant_id"),
        Index("ix_saved_scenarios_tenant", "tenant_id"),
    )
