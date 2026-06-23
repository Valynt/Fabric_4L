# Academy Module (Layer 5 Ground Truth)

The Academy module delivers the Value Operating System (VOS) training program through structured pillars, quizzes, progress tracking, certifications, and maturity assessments.

## Overview

- **10 VOS Pillars** covering value selling from definitions to organizational transformation
- **Quizzes** per pillar with adaptive scoring and feedback
- **Progress Tracking** across all pillars with overall completion percentage
- **Certifications** awarded automatically on quiz pass (>= 80%)
- **Maturity Assessments** self-reported with behavior indicators and recommendations

## Domain Model

| Entity | Table | Purpose |
|--------|-------|---------|
| AcademyPillar | `academy_pillars` | Training content (title, description, content JSON) |
| AcademyQuizQuestion | `academy_quiz_questions` | Questions per pillar with options, correct answer, feedback |
| AcademyProgress | `academy_progress` | User progress per pillar (status, completion %) |
| AcademyQuizResult | `academy_quiz_results` | Quiz submission scores, answers, feedback |
| AcademyCertification | `academy_certifications` | Role-based badges awarded on quiz pass |
| AcademyMaturityAssessment | `academy_maturity_assessments` | Self-assessed maturity level with data |
| AcademyResource | `academy_resources` | Templates, frameworks, guides |

## Auth & Permissions

| Action | Policy | Required Permission |
|--------|--------|---------------------|
| Read academy | `layer5.academy.read` | `read:analytics` |
| Write academy | `layer5.academy.write` | `write:analytics` |

## API Endpoints

Base path: `/api/v1/academy`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/pillars` | List all pillars |
| GET | `/pillars/{id}` | Get pillar by ID |
| GET | `/pillars/by-number/{n}` | Get pillar by number (1-10) |
| GET | `/pillars/{id}/quiz` | Get quiz questions |
| POST | `/quiz/submit` | Submit answers, score quiz |
| GET | `/progress` | Get user progress |
| PUT | `/progress` | Update progress |
| GET | `/certifications` | List certifications |
| GET | `/maturity/levels` | Maturity level definitions |
| GET | `/maturity/assessments` | List assessments |
| POST | `/maturity/assessments` | Create assessment |
| GET | `/resources` | List resources |
| GET | `/pillars/{id}/resources` | Resources for pillar |

## Quiz Scoring

- Each question has a point value (default 4)
- Score = (correct answers / total possible points) × 100
- Pass threshold: **80%**
- On pass: certification awarded + progress set to "completed" (100%)
- Feedback includes strengths, improvements, and next steps

## Maturity Levels

| Level | Name | Description |
|-------|------|-------------|
| 0 | Unaware | No formal value selling practices |
| 1 | Emerging | Basic value language adoption |
| 2 | Developing | Structured value conversations |
| 3 | Practicing | Consistent value-led selling |
| 4 | Optimizing | Advanced value transformation |
| 5 | Leading | Value-centered organization |

## Seed Data

Run the seed script to populate pillars and sample questions:

```bash
python services/layer5-ground-truth/scripts/seed_academy.py
```

## Tests

```bash
cd services/layer5-ground-truth
pytest tests/test_academy_api.py -v
```

Coverage: pillars, quizzes, quiz submission, progress, certifications, maturity levels/assessments, resources, tenant isolation, authorization.
