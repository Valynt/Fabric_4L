"""
Integration tests for the Academy module API endpoints.

Tests use httpx.AsyncClient against the real FastAPI app with a
SQLite in-memory database. Each test starts with a clean state
(transaction is rolled back after each test via the db fixture).

Coverage:
  GET    /api/v1/academy/pillars                 — list pillars
  GET    /api/v1/academy/pillars/{id}            — get pillar by ID
  GET    /api/v1/academy/pillars/by-number/{n}   — get pillar by number
  GET    /api/v1/academy/pillars/{id}/quiz       — get quiz questions
  POST   /api/v1/academy/quiz/submit             — submit quiz answers
  GET    /api/v1/academy/progress                — get progress
  PUT    /api/v1/academy/progress                — update progress
  GET    /api/v1/academy/certifications          — list certifications
  GET    /api/v1/academy/maturity/levels         — maturity level definitions
  POST   /api/v1/academy/maturity/assessments    — create assessment
  GET    /api/v1/academy/maturity/assessments    — list assessments
  GET    /api/v1/academy/resources               — list resources
  Tenant isolation & authorization
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import TEST_ORG_ID

ORG_PARAM = f"?tenant_id={TEST_ORG_ID}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_pillar(db, tenant_id, pillar_number=1, title="Test Pillar"):
    from layer5_ground_truth.models.academy import AcademyPillar
    pillar = AcademyPillar(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        pillar_number=pillar_number,
        title=title,
        description=f"Description for {title}",
        target_maturity_level=1,
        duration="30 minutes",
        content={
            "overview": "Test overview",
            "learning_objectives": ["Learn A", "Learn B"],
            "key_takeaways": ["Takeaway 1"],
            "resources": [{"title": "Resource 1", "url": "/r1.pdf", "type": "pdf"}],
        },
    )
    db.add(pillar)
    await db.flush()
    return pillar


async def _create_quiz_question(db, tenant_id, pillar_id, question_number=1, correct_answer="A"):
    from layer5_ground_truth.models.academy import AcademyQuizQuestion
    q = AcademyQuizQuestion(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        pillar_id=pillar_id,
        question_number=question_number,
        question_type="multiple_choice",
        category="Test Category",
        question_text="What is the correct answer?",
        options=[
            {"label": "Correct", "value": correct_answer},
            {"label": "Wrong 1", "value": "B"},
            {"label": "Wrong 2", "value": "C"},
            {"label": "Wrong 3", "value": "D"},
        ],
        correct_answer=correct_answer,
        points=4,
        feedback={"correct": "Good job", "incorrect": "Try again"},
    )
    db.add(q)
    await db.flush()
    return q


async def _create_resource(db, tenant_id, title="Test Resource", pillar_id=None):
    from layer5_ground_truth.models.academy import AcademyResource
    r = AcademyResource(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        title=title,
        description="A test resource",
        resource_type="pdf",
        file_url="/test.pdf",
        pillar_id=pillar_id,
    )
    db.add(r)
    await db.flush()
    return r


# ---------------------------------------------------------------------------
# GET /api/v1/academy/pillars
# ---------------------------------------------------------------------------


class TestListPillars:
    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_pillars(self, client):
        resp = await client.get(f"/api/v1/academy/pillars{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_returns_pillars(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=1, title="Value Definitions")
        resp = await client.get(f"/api/v1/academy/pillars{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Value Definitions"
        assert data["items"][0]["pillar_number"] == 1


# ---------------------------------------------------------------------------
# GET /api/v1/academy/pillars/{id}
# ---------------------------------------------------------------------------


class TestGetPillar:
    @pytest.mark.asyncio
    async def test_returns_pillar_by_id(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=2, title="KPI Taxonomy")
        resp = await client.get(f"/api/v1/academy/pillars/{pillar.id}{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(pillar.id)
        assert data["title"] == "KPI Taxonomy"

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_pillar(self, client):
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/academy/pillars/{fake_id}{ORG_PARAM}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/academy/pillars/by-number/{n}
# ---------------------------------------------------------------------------


class TestGetPillarByNumber:
    @pytest.mark.asyncio
    async def test_returns_pillar_by_number(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=3, title="ROI Frameworks")
        resp = await client.get(f"/api/v1/academy/pillars/by-number/3{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(pillar.id)
        assert data["pillar_number"] == 3

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_number(self, client):
        resp = await client.get(f"/api/v1/academy/pillars/by-number/99{ORG_PARAM}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/academy/pillars/{id}/quiz
# ---------------------------------------------------------------------------


class TestGetQuiz:
    @pytest.mark.asyncio
    async def test_returns_quiz_questions(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=1)
        q1 = await _create_quiz_question(db, TEST_ORG_ID, pillar.id, question_number=1, correct_answer="A")
        q2 = await _create_quiz_question(db, TEST_ORG_ID, pillar.id, question_number=2, correct_answer="B")
        resp = await client.get(f"/api/v1/academy/pillars/{pillar.id}/quiz{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert {item["id"] for item in data["items"]} == {str(q1.id), str(q2.id)}

    @pytest.mark.asyncio
    async def test_returns_empty_quiz_when_no_questions(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=2)
        resp = await client.get(f"/api/v1/academy/pillars/{pillar.id}/quiz{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# POST /api/v1/academy/quiz/submit
# ---------------------------------------------------------------------------


class TestSubmitQuiz:
    @pytest.mark.asyncio
    async def test_passes_quiz_with_all_correct(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=1)
        q = await _create_quiz_question(db, TEST_ORG_ID, pillar.id, question_number=1, correct_answer="A")
        payload = {
            "pillar_id": str(pillar.id),
            "answers": [{"question_id": str(q.id), "selected_answer": "A"}],
        }
        resp = await client.post(f"/api/v1/academy/quiz/submit{ORG_PARAM}", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["score"] == 100
        assert data["passed"] is True
        assert "feedback" in data

    @pytest.mark.asyncio
    async def test_fails_quiz_with_wrong_answer(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=2)
        q = await _create_quiz_question(db, TEST_ORG_ID, pillar.id, question_number=1, correct_answer="A")
        payload = {
            "pillar_id": str(pillar.id),
            "answers": [{"question_id": str(q.id), "selected_answer": "B"}],
        }
        resp = await client.post(f"/api/v1/academy/quiz/submit{ORG_PARAM}", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["score"] == 0
        assert data["passed"] is False

    @pytest.mark.asyncio
    async def test_creates_certification_on_pass(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=3)
        q = await _create_quiz_question(db, TEST_ORG_ID, pillar.id, question_number=1, correct_answer="A")
        payload = {
            "pillar_id": str(pillar.id),
            "answers": [{"question_id": str(q.id), "selected_answer": "A"}],
        }
        await client.post(f"/api/v1/academy/quiz/submit{ORG_PARAM}", json=payload)

        # Certifications endpoint should now show the badge
        resp = await client.get(f"/api/v1/academy/certifications{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert pillar.title in data["items"][0]["badge_name"]

    @pytest.mark.asyncio
    async def test_updates_progress_on_pass(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=4)
        q = await _create_quiz_question(db, TEST_ORG_ID, pillar.id, question_number=1, correct_answer="A")
        payload = {
            "pillar_id": str(pillar.id),
            "answers": [{"question_id": str(q.id), "selected_answer": "A"}],
        }
        await client.post(f"/api/v1/academy/quiz/submit{ORG_PARAM}", json=payload)

        resp = await client.get(f"/api/v1/academy/progress{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed_count"] == 1
        assert any(item["pillar_id"] == str(pillar.id) and item["status"] == "completed" for item in data["items"])

    @pytest.mark.asyncio
    async def test_returns_422_for_invalid_payload(self, client):
        payload = {"pillar_id": "not-a-uuid", "answers": []}
        resp = await client.post(f"/api/v1/academy/quiz/submit{ORG_PARAM}", json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/academy/progress
# ---------------------------------------------------------------------------


class TestGetProgress:
    @pytest.mark.asyncio
    async def test_returns_zero_progress_initially(self, client):
        resp = await client.get(f"/api/v1/academy/progress{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_percentage"] == 0
        assert data["completed_count"] == 0
        assert data["total_count"] == 10


# ---------------------------------------------------------------------------
# PUT /api/v1/academy/progress
# ---------------------------------------------------------------------------


class TestUpdateProgress:
    @pytest.mark.asyncio
    async def test_creates_progress_record(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=1)
        payload = {
            "pillar_id": str(pillar.id),
            "status": "in_progress",
            "completion_percentage": 50,
        }
        resp = await client.put(f"/api/v1/academy/progress{ORG_PARAM}", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"
        assert data["completion_percentage"] == 50

    @pytest.mark.asyncio
    async def test_updates_existing_progress(self, client, db):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=1)
        payload = {
            "pillar_id": str(pillar.id),
            "status": "in_progress",
            "completion_percentage": 25,
        }
        await client.put(f"/api/v1/academy/progress{ORG_PARAM}", json=payload)

        payload["status"] = "completed"
        payload["completion_percentage"] = 100
        resp = await client.put(f"/api/v1/academy/progress{ORG_PARAM}", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["completion_percentage"] == 100


# ---------------------------------------------------------------------------
# GET /api/v1/academy/certifications
# ---------------------------------------------------------------------------


class TestGetCertifications:
    @pytest.mark.asyncio
    async def test_returns_empty_when_none(self, client):
        resp = await client.get(f"/api/v1/academy/certifications{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# GET /api/v1/academy/maturity/levels
# ---------------------------------------------------------------------------


class TestGetMaturityLevels:
    @pytest.mark.asyncio
    async def test_returns_six_levels(self, client):
        resp = await client.get(f"/api/v1/academy/maturity/levels{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 6
        levels = [lvl["level"] for lvl in data]
        assert levels == [0, 1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# POST + GET /api/v1/academy/maturity/assessments
# ---------------------------------------------------------------------------


class TestMaturityAssessments:
    @pytest.mark.asyncio
    async def test_create_and_list_assessments(self, client):
        payload = {
            "level": 2,
            "assessment_data": {
                "self_assessment": 2,
                "quiz_average": 85,
                "pillars_completed": 3,
                "behavior_indicators": ["indicator1"],
                "recommendations": ["rec1"],
            },
        }
        create_resp = await client.post(f"/api/v1/academy/maturity/assessments{ORG_PARAM}", json=payload)
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["level"] == 2
        assert created["assessment_data"]["self_assessment"] == 2

        list_resp = await client.get(f"/api/v1/academy/maturity/assessments{ORG_PARAM}")
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) >= 1
        assert any(item["id"] == created["id"] for item in items)


# ---------------------------------------------------------------------------
# GET /api/v1/academy/resources
# ---------------------------------------------------------------------------


class TestGetResources:
    @pytest.mark.asyncio
    async def test_returns_empty_when_none(self, client):
        resp = await client.get(f"/api/v1/academy/resources{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_returns_resources(self, client, db):
        await _create_resource(db, TEST_ORG_ID, title="ROI Template")
        resp = await client.get(f"/api/v1/academy/resources{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "ROI Template"


# ---------------------------------------------------------------------------
# Tenant Isolation
# ---------------------------------------------------------------------------


class TestAcademyTenantIsolation:
    @pytest.mark.asyncio
    async def test_pillars_isolated_by_tenant(self, client, db, tenant_aware_client):
        pillar = await _create_pillar(db, TEST_ORG_ID, pillar_number=1, title="Tenant A Pillar")
        await db.commit()

        # Same tenant should see the pillar
        resp = await client.get(f"/api/v1/academy/pillars{ORG_PARAM}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        # Different tenant should not see it
        other_tenant = uuid.UUID("00000000-0000-0000-0000-000000000002")
        resp_b = await tenant_aware_client.get(
            f"/api/v1/academy/pillars?tenant_id={other_tenant}",
            headers={"X-Test-Tenant": str(other_tenant)},
        )
        assert resp_b.status_code == 200
        assert resp_b.json()["total"] == 0


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


class TestAcademyAuthorization:
    @pytest.mark.asyncio
    async def test_no_permission_returns_403(self, client_no_permissions):
        resp = await client_no_permissions.get(f"/api/v1/academy/pillars{ORG_PARAM}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_write_requires_permission(self, client_no_permissions):
        payload = {
            "pillar_id": str(uuid.uuid4()),
            "answers": [{"question_id": str(uuid.uuid4()), "selected_answer": "A"}],
        }
        resp = await client_no_permissions.post(f"/api/v1/academy/quiz/submit{ORG_PARAM}", json=payload)
        assert resp.status_code == 403
