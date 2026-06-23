"""Pydantic v2 schemas for the Academy API."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class VosRole(str, Enum):
    SALES = "Sales"
    CS = "CS"
    MARKETING = "Marketing"
    PRODUCT = "Product"
    EXECUTIVE = "Executive"
    VE = "VE"


class PillarStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# --- Pillar ---

class PillarContent(BaseModel):
    overview: str = ""
    learning_objectives: list[str] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)
    resources: list[dict[str, str]] = Field(default_factory=list)


class PillarResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    pillar_number: int
    title: str
    description: str
    target_maturity_level: int
    duration: str | None
    content: PillarContent | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class PillarListResponse(BaseModel):
    items: list[PillarResponse]
    total: int


# --- Quiz ---

class QuizOption(BaseModel):
    label: str
    value: str


class QuizQuestionResponse(BaseModel):
    id: uuid.UUID
    question_number: int
    question_type: str
    category: str
    question_text: str
    options: list[QuizOption]
    points: int
    model_config = {"from_attributes": True}


class QuizListResponse(BaseModel):
    items: list[QuizQuestionResponse]
    total: int


# --- Quiz Submission ---

class QuizAnswer(BaseModel):
    question_id: uuid.UUID
    selected_answer: str


class QuizSubmitRequest(BaseModel):
    pillar_id: uuid.UUID
    answers: list[QuizAnswer]

    @field_validator("answers")
    @classmethod
    def answers_not_empty(cls, v: list[QuizAnswer]) -> list[QuizAnswer]:
        if not v:
            raise ValueError("answers must not be empty")
        return v


class QuizFeedback(BaseModel):
    overall: str
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class QuizResultResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: str
    pillar_id: uuid.UUID
    score: int
    category_scores: dict[str, float] | None
    passed: bool
    feedback: QuizFeedback
    attempt_number: int
    completed_at: datetime
    model_config = {"from_attributes": True}


# --- Progress ---

class ProgressResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: str
    pillar_id: uuid.UUID
    status: PillarStatus
    completion_percentage: int
    last_accessed: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}


class ProgressListResponse(BaseModel):
    items: list[ProgressResponse]
    overall_percentage: int
    completed_count: int
    total_count: int


class ProgressUpdateRequest(BaseModel):
    pillar_id: uuid.UUID
    status: PillarStatus
    completion_percentage: int = Field(..., ge=0, le=100)


# --- Certification ---

class CertificationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: str
    badge_name: str
    pillar_id: uuid.UUID
    vos_role: str
    certificate_url: str | None
    awarded_at: datetime
    model_config = {"from_attributes": True}


class CertificationListResponse(BaseModel):
    items: list[CertificationResponse]
    total: int


# --- Maturity Assessment ---

class AssessmentData(BaseModel):
    self_assessment: int = Field(..., ge=0, le=100)
    quiz_average: int = Field(..., ge=0, le=100)
    pillars_completed: int = Field(..., ge=0, le=10)
    behavior_indicators: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class MaturityAssessmentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: str
    level: int
    assessment_data: AssessmentData
    assessed_at: datetime
    model_config = {"from_attributes": True}


class MaturityAssessmentCreateRequest(BaseModel):
    level: int = Field(..., ge=0, le=5)
    assessment_data: AssessmentData


class MaturityLevelResponse(BaseModel):
    level: int
    name: str
    description: str
    behaviors: list[str]


# --- Resource ---

class ResourceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None
    resource_type: str
    file_url: str
    pillar_id: uuid.UUID | None
    vos_role: str | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ResourceListResponse(BaseModel):
    items: list[ResourceResponse]
    total: int
