"""FastAPI router for the Academy module.

Endpoints:
  GET    /academy/pillars                 — List training pillars
  GET    /academy/pillars/{id}            — Get a single pillar
  GET    /academy/pillars/by-number/{n}   — Get pillar by number (1-10)
  GET    /academy/pillars/{id}/quiz       — Get quiz questions for a pillar
  POST   /academy/quiz/submit             — Submit quiz answers
  GET    /academy/progress                — Get user progress
  PUT    /academy/progress                — Update progress
  GET    /academy/certifications          — List user certifications
  GET    /academy/maturity/levels         — Get maturity level definitions
  GET    /academy/maturity/assessments    — List maturity assessments
  POST   /academy/maturity/assessments    — Create maturity assessment
  GET    /academy/resources               — List all resources
  GET    /academy/pillars/{id}/resources  — List resources for a pillar
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling.exceptions import NotFoundError

from layer5_ground_truth.api.academy_schemas import (
    CertificationListResponse,
    CertificationResponse,
    MaturityAssessmentCreateRequest,
    MaturityAssessmentResponse,
    MaturityLevelResponse,
    PillarListResponse,
    PillarResponse,
    ProgressListResponse,
    ProgressResponse,
    ProgressUpdateRequest,
    QuizListResponse,
    QuizQuestionResponse,
    QuizResultResponse,
    QuizSubmitRequest,
    ResourceListResponse,
    ResourceResponse,
)
from layer5_ground_truth.api.auth import TokenClaims, authorize_action, get_current_user
from layer5_ground_truth.database import get_db_from_context
from layer5_ground_truth.services.academy_service import (
    MATURITY_LEVELS,
    create_certification,
    create_maturity_assessment,
    get_maturity_level,
    get_pillar_by_id,
    get_pillar_by_number,
    get_quiz_questions,
    get_resources_by_pillar,
    get_user_certifications,
    get_user_maturity_assessments,
    get_user_progress,
    has_certification,
    list_pillars,
    list_resources,
    score_quiz,
    upsert_progress,
)

router = APIRouter(prefix="/api/v1/academy", tags=["academy"])


# --- Pillars ---

@router.get("/pillars", response_model=PillarListResponse)
async def get_pillars(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> PillarListResponse:
    authorize_action("layer5.academy.read", caller)
    items = await list_pillars(db, caller.tenant_id)
    return PillarListResponse(
        items=[PillarResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.get("/pillars/{pillar_id}", response_model=PillarResponse)
async def get_pillar(
    pillar_id: uuid.UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> PillarResponse:
    authorize_action("layer5.academy.read", caller)
    pillar = await get_pillar_by_id(db, caller.tenant_id, pillar_id)
    if pillar is None:
        raise NotFoundError(message="Pillar not found")
    return PillarResponse.model_validate(pillar)


@router.get("/pillars/by-number/{pillar_number}", response_model=PillarResponse)
async def get_pillar_by_number_route(
    pillar_number: int,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> PillarResponse:
    authorize_action("layer5.academy.read", caller)
    pillar = await get_pillar_by_number(db, caller.tenant_id, pillar_number)
    if pillar is None:
        raise NotFoundError(message="Pillar not found")
    return PillarResponse.model_validate(pillar)


# --- Quiz ---

@router.get("/pillars/{pillar_id}/quiz", response_model=QuizListResponse)
async def get_quiz(
    pillar_id: uuid.UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> QuizListResponse:
    authorize_action("layer5.academy.read", caller)
    items = await get_quiz_questions(db, caller.tenant_id, pillar_id)
    return QuizListResponse(
        items=[QuizQuestionResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.post("/quiz/submit", response_model=QuizResultResponse, status_code=201)
async def submit_quiz(
    request: Request,
    payload: QuizSubmitRequest,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> QuizResultResponse:
    authorize_action("layer5.academy.write", caller)
    result = await score_quiz(
        db=db,
        tenant_id=caller.tenant_id,
        user_id=caller.user_id or str(caller.tenant_id),
        pillar_id=payload.pillar_id,
        answers=[{"question_id": str(a.question_id), "selected_answer": a.selected_answer} for a in payload.answers],
    )

    if result.passed and caller.user_id:
        pillar = await get_pillar_by_id(db, caller.tenant_id, payload.pillar_id)
        if pillar:
            vos_role = "VE"
            already = await has_certification(db, caller.tenant_id, caller.user_id, payload.pillar_id, vos_role)
            if not already:
                badge_name = f"{pillar.title} - {vos_role} Certified"
                await create_certification(
                    db=db,
                    tenant_id=caller.tenant_id,
                    user_id=caller.user_id,
                    badge_name=badge_name,
                    pillar_id=payload.pillar_id,
                    vos_role=vos_role,
                )
            await upsert_progress(
                db=db,
                tenant_id=caller.tenant_id,
                user_id=caller.user_id,
                pillar_id=payload.pillar_id,
                status="completed",
                completion_percentage=100,
            )

    return QuizResultResponse.model_validate(result)


# --- Progress ---

@router.get("/progress", response_model=ProgressListResponse)
async def get_progress(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ProgressListResponse:
    authorize_action("layer5.academy.read", caller)
    user_id = caller.user_id or str(caller.tenant_id)
    items = await get_user_progress(db, caller.tenant_id, user_id)

    total = 10
    completed = sum(1 for i in items if i.status == "completed")
    overall = int((completed / total) * 100) if total > 0 else 0

    return ProgressListResponse(
        items=[ProgressResponse.model_validate(i) for i in items],
        overall_percentage=overall,
        completed_count=completed,
        total_count=total,
    )


@router.put("/progress", response_model=ProgressResponse)
async def update_progress(
    payload: ProgressUpdateRequest,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ProgressResponse:
    authorize_action("layer5.academy.write", caller)
    user_id = caller.user_id or str(caller.tenant_id)
    progress = await upsert_progress(
        db=db,
        tenant_id=caller.tenant_id,
        user_id=user_id,
        pillar_id=payload.pillar_id,
        status=payload.status.value,
        completion_percentage=payload.completion_percentage,
    )
    return ProgressResponse.model_validate(progress)


# --- Certifications ---

@router.get("/certifications", response_model=CertificationListResponse)
async def get_certifications(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> CertificationListResponse:
    authorize_action("layer5.academy.read", caller)
    user_id = caller.user_id or str(caller.tenant_id)
    items = await get_user_certifications(db, caller.tenant_id, user_id)
    return CertificationListResponse(
        items=[CertificationResponse.model_validate(i) for i in items],
        total=len(items),
    )


# --- Maturity ---

@router.get("/maturity/levels", response_model=list[MaturityLevelResponse])
async def get_maturity_levels(
    caller: TokenClaims = Depends(get_current_user),
) -> list[MaturityLevelResponse]:
    authorize_action("layer5.academy.read", caller)
    return [
        MaturityLevelResponse(level=k, name=v["name"], description=v["description"], behaviors=v["behaviors"])
        for k, v in sorted(MATURITY_LEVELS.items())
    ]


@router.get("/maturity/assessments", response_model=list[MaturityAssessmentResponse])
async def get_maturity_assessments(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> list[MaturityAssessmentResponse]:
    authorize_action("layer5.academy.read", caller)
    user_id = caller.user_id or str(caller.tenant_id)
    items = await get_user_maturity_assessments(db, caller.tenant_id, user_id)
    return [MaturityAssessmentResponse.model_validate(i) for i in items]


@router.post("/maturity/assessments", response_model=MaturityAssessmentResponse, status_code=201)
async def create_assessment(
    payload: MaturityAssessmentCreateRequest,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> MaturityAssessmentResponse:
    authorize_action("layer5.academy.write", caller)
    user_id = caller.user_id or str(caller.tenant_id)
    assessment = await create_maturity_assessment(
        db=db,
        tenant_id=caller.tenant_id,
        user_id=user_id,
        level=payload.level,
        assessment_data=payload.assessment_data.model_dump(),
    )
    return MaturityAssessmentResponse.model_validate(assessment)


# --- Resources ---

@router.get("/resources", response_model=ResourceListResponse)
async def get_resources(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ResourceListResponse:
    authorize_action("layer5.academy.read", caller)
    items = await list_resources(db, caller.tenant_id)
    return ResourceListResponse(
        items=[ResourceResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.get("/pillars/{pillar_id}/resources", response_model=ResourceListResponse)
async def get_pillar_resources(
    pillar_id: uuid.UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ResourceListResponse:
    authorize_action("layer5.academy.read", caller)
    items = await get_resources_by_pillar(db, caller.tenant_id, pillar_id)
    return ResourceListResponse(
        items=[ResourceResponse.model_validate(i) for i in items],
        total=len(items),
    )
