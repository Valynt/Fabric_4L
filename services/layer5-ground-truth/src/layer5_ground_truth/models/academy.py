"""Academy models for the Ground Truth Layer.

Entities:
  - AcademyPillar          : Training pillars (10 VOS pillars)
  - AcademyQuizQuestion    : Quiz questions per pillar
  - AcademyProgress        : User progress through pillars
  - AcademyQuizResult      : Quiz submissions and scores
  - AcademyCertification   : Role-based certifications earned
  - AcademyMaturityAssessment : Self-reported maturity level assessments
  - AcademyResource        : Templates, frameworks, and guides

Design notes:
  - Reuses Base and UUID from truth_object.py
  - tenant_id on every table for multi-tenancy isolation
  - No soft-delete — academy data is immutable or versioned by replacement
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .truth_object import Base, UUID


class AcademyPillar(Base):
    __tablename__ = "academy_pillars"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)
    pillar_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_maturity_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_academy_pillars_tenant_number", "tenant_id", "pillar_number", unique=True),
    )


class AcademyQuizQuestion(Base):
    __tablename__ = "academy_quiz_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)
    pillar_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    role_adaptations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_academy_quiz_questions_tenant_pillar", "tenant_id", "pillar_id"),
    )


class AcademyProgress(Base):
    __tablename__ = "academy_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    pillar_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")
    completion_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_academy_progress_tenant_user_pillar", "tenant_id", "user_id", "pillar_id", unique=True),
    )


class AcademyQuizResult(Base):
    __tablename__ = "academy_quiz_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    pillar_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    category_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answers: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    passed: Mapped[bool] = mapped_column(Integer, nullable=False, default=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_academy_quiz_results_tenant_user_pillar", "tenant_id", "user_id", "pillar_id"),
    )


class AcademyCertification(Base):
    __tablename__ = "academy_certifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    badge_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pillar_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)
    vos_role: Mapped[str] = mapped_column(String(32), nullable=False)
    certificate_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class AcademyMaturityAssessment(Base):
    __tablename__ = "academy_maturity_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    assessment_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class AcademyResource(Base):
    __tablename__ = "academy_resources"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    pillar_id: Mapped[uuid.UUID | None] = mapped_column(UUID, nullable=True)
    vos_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
