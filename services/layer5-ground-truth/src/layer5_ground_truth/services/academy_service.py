"""Business logic for the Academy module.

Services:
  - pillar CRUD
  - quiz scoring, feedback generation
  - progress tracking
  - certification awarding
  - maturity assessment
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from layer5_ground_truth.api.academy_schemas import QuizFeedback
from layer5_ground_truth.models.academy import (
    AcademyCertification,
    AcademyMaturityAssessment,
    AcademyPillar,
    AcademyProgress,
    AcademyQuizQuestion,
    AcademyQuizResult,
    AcademyResource,
)

# --- Maturity level metadata ---

MATURITY_LEVELS: dict[int, dict[str, str | list[str]]] = {
    0: {"name": "Unaware", "description": "No awareness of value operating principles", "behaviors": []},
    1: {"name": "Aware", "description": "Understands basic value concepts", "behaviors": ["Can articulate value proposition", "Recognizes value drivers"]},
    2: {"name": "Practicing", "description": "Applies value frameworks in daily work", "behaviors": ["Uses structured value conversations", "Tracks ROI in deals"]},
    3: {"name": "Proficient", "description": "Leads value conversations with confidence", "behaviors": ["Coaches others on value selling", "Builds custom value models"]},
    4: {"name": "Expert", "description": "Drives organizational value transformation", "behaviors": ["Designs value programs", "Influences strategy through value"]},
    5: {"name": "Master", "description": "Redefines industry value standards", "behaviors": ["Publishes value thought leadership", "Shapes market through value innovation"]},
}


def get_maturity_level(level: int) -> dict[str, str | list[str]]:
    return MATURITY_LEVELS.get(level, MATURITY_LEVELS[0])


# --- Pillars ---

async def list_pillars(db: AsyncSession, tenant_id: uuid.UUID) -> list[AcademyPillar]:
    result = await db.execute(
        select(AcademyPillar)
        .where(AcademyPillar.tenant_id == tenant_id)
        .order_by(AcademyPillar.pillar_number)
    )
    return list(result.scalars().all())


async def get_pillar_by_id(db: AsyncSession, tenant_id: uuid.UUID, pillar_id: uuid.UUID) -> AcademyPillar | None:
    result = await db.execute(
        select(AcademyPillar).where(
            and_(AcademyPillar.tenant_id == tenant_id, AcademyPillar.id == pillar_id)
        )
    )
    return result.scalar_one_or_none()


async def get_pillar_by_number(db: AsyncSession, tenant_id: uuid.UUID, pillar_number: int) -> AcademyPillar | None:
    result = await db.execute(
        select(AcademyPillar).where(
            and_(AcademyPillar.tenant_id == tenant_id, AcademyPillar.pillar_number == pillar_number)
        )
    )
    return result.scalar_one_or_none()


# --- Quiz ---

async def get_quiz_questions(db: AsyncSession, tenant_id: uuid.UUID, pillar_id: uuid.UUID) -> list[AcademyQuizQuestion]:
    result = await db.execute(
        select(AcademyQuizQuestion)
        .where(
            and_(
                AcademyQuizQuestion.tenant_id == tenant_id,
                AcademyQuizQuestion.pillar_id == pillar_id,
            )
        )
        .order_by(AcademyQuizQuestion.question_number)
    )
    return list(result.scalars().all())


# --- Quiz Scoring ---

async def score_quiz(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: str,
    pillar_id: uuid.UUID,
    answers: list[dict[str, str]],
) -> AcademyQuizResult:
    questions = await get_quiz_questions(db, tenant_id, pillar_id)
    question_map = {str(q.id): q for q in questions}

    total_points = sum(q.points for q in questions)
    earned_points = 0
    category_scores: dict[str, list[int]] = {}

    for ans in answers:
        q = question_map.get(str(ans["question_id"]))
        if not q:
            continue
        is_correct = ans["selected_answer"] == q.correct_answer
        pts = q.points if is_correct else 0
        earned_points += pts
        category_scores.setdefault(q.category, []).append(100 if is_correct else 0)

    score = int((earned_points / total_points) * 100) if total_points > 0 else 0
    passed = score >= 80

    avg_category_scores = {cat: int(sum(vals) / len(vals)) for cat, vals in category_scores.items()}

    prev_result = await db.execute(
        select(func.count()).select_from(AcademyQuizResult).where(
            and_(
                AcademyQuizResult.tenant_id == tenant_id,
                AcademyQuizResult.user_id == user_id,
                AcademyQuizResult.pillar_id == pillar_id,
            )
        )
    )
    attempt_number = (prev_result.scalar_one() or 0) + 1

    feedback = _generate_feedback(score, 0, avg_category_scores)

    quiz_result = AcademyQuizResult(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        pillar_id=pillar_id,
        score=score,
        category_scores=avg_category_scores,
        answers=answers,
        feedback={
            "overall": feedback.overall,
            "strengths": feedback.strengths,
            "improvements": feedback.improvements,
            "next_steps": feedback.next_steps,
        },
        passed=passed,
        attempt_number=attempt_number,
        completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db.add(quiz_result)
    await db.flush()
    return quiz_result


def _generate_feedback(
    score: int,
    maturity_level: int,
    category_scores: dict[str, int] | None,
) -> QuizFeedback:
    if score >= 90:
        overall = "Excellent work! You've demonstrated strong mastery of this pillar's concepts."
    elif score >= 80:
        overall = "Good job! You've passed and shown solid understanding of the core concepts."
    elif score >= 70:
        overall = "You're close! Review the feedback below and retake the quiz to achieve certification."
    else:
        overall = "Keep learning! Focus on the improvement areas below and revisit the pillar content."

    strengths: list[str] = []
    improvements: list[str] = []
    next_steps: list[str] = []

    if maturity_level <= 1:
        next_steps.extend([
            "Focus on building foundational knowledge through the pillar content",
            "Review the KPI Definition Sheet and practice mapping pain to value",
        ])
    elif maturity_level == 2:
        next_steps.extend([
            "Apply these concepts in cross-functional scenarios",
            "Practice structured value realization tracking",
        ])
    else:
        next_steps.extend([
            "Integrate these concepts into automated workflows",
            "Mentor others on value language and frameworks",
        ])

    if category_scores:
        for cat, cat_score in category_scores.items():
            if cat_score >= 80:
                strengths.append(f"Strong performance in {cat}")
            elif cat_score < 70:
                improvements.append(f"Review {cat} concepts and examples")

    return QuizFeedback(
        overall=overall,
        strengths=strengths,
        improvements=improvements,
        next_steps=next_steps,
    )


# --- Progress ---

async def get_user_progress(db: AsyncSession, tenant_id: uuid.UUID, user_id: str) -> list[AcademyProgress]:
    result = await db.execute(
        select(AcademyProgress).where(
            and_(AcademyProgress.tenant_id == tenant_id, AcademyProgress.user_id == user_id)
        )
    )
    return list(result.scalars().all())


async def upsert_progress(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: str,
    pillar_id: uuid.UUID,
    status: str,
    completion_percentage: int,
) -> AcademyProgress:
    result = await db.execute(
        select(AcademyProgress).where(
            and_(
                AcademyProgress.tenant_id == tenant_id,
                AcademyProgress.user_id == user_id,
                AcademyProgress.pillar_id == pillar_id,
            )
        )
    )
    progress = result.scalar_one_or_none()
    now = datetime.now(UTC)

    if progress is None:
        progress = AcademyProgress(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            pillar_id=pillar_id,
            status=status,
            completion_percentage=completion_percentage,
            last_accessed=now,
            completed_at=now if status == "completed" else None,
            created_at=now,
            updated_at=now,
        )
        db.add(progress)
    else:
        progress.status = status
        progress.completion_percentage = completion_percentage
        progress.last_accessed = now
        if status == "completed":
            progress.completed_at = now
        progress.updated_at = now

    await db.flush()
    return progress


# --- Certifications ---

async def get_user_certifications(db: AsyncSession, tenant_id: uuid.UUID, user_id: str) -> list[AcademyCertification]:
    result = await db.execute(
        select(AcademyCertification).where(
            and_(AcademyCertification.tenant_id == tenant_id, AcademyCertification.user_id == user_id)
        )
    )
    return list(result.scalars().all())


async def has_certification(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: str, pillar_id: uuid.UUID, vos_role: str
) -> bool:
    result = await db.execute(
        select(func.count()).select_from(AcademyCertification).where(
            and_(
                AcademyCertification.tenant_id == tenant_id,
                AcademyCertification.user_id == user_id,
                AcademyCertification.pillar_id == pillar_id,
                AcademyCertification.vos_role == vos_role,
            )
        )
    )
    return (result.scalar_one() or 0) > 0


async def create_certification(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: str,
    badge_name: str,
    pillar_id: uuid.UUID,
    vos_role: str,
) -> AcademyCertification:
    cert = AcademyCertification(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        badge_name=badge_name,
        pillar_id=pillar_id,
        vos_role=vos_role,
        awarded_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db.add(cert)
    await db.flush()
    return cert


# --- Maturity Assessments ---

async def get_user_maturity_assessments(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: str
) -> list[AcademyMaturityAssessment]:
    result = await db.execute(
        select(AcademyMaturityAssessment).where(
            and_(
                AcademyMaturityAssessment.tenant_id == tenant_id,
                AcademyMaturityAssessment.user_id == user_id,
            )
        )
        .order_by(AcademyMaturityAssessment.assessed_at.desc())
    )
    return list(result.scalars().all())


async def create_maturity_assessment(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: str,
    level: int,
    assessment_data: dict[str, Any],
) -> AcademyMaturityAssessment:
    assessment = AcademyMaturityAssessment(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        level=level,
        assessment_data=assessment_data,
        assessed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db.add(assessment)
    await db.flush()
    return assessment


# --- Resources ---

async def list_resources(db: AsyncSession, tenant_id: uuid.UUID) -> list[AcademyResource]:
    result = await db.execute(
        select(AcademyResource).where(AcademyResource.tenant_id == tenant_id)
    )
    return list(result.scalars().all())


async def get_resources_by_pillar(db: AsyncSession, tenant_id: uuid.UUID, pillar_id: uuid.UUID) -> list[AcademyResource]:
    result = await db.execute(
        select(AcademyResource).where(
            and_(
                AcademyResource.tenant_id == tenant_id,
                AcademyResource.pillar_id == pillar_id,
            )
        )
    )
    return list(result.scalars().all())
