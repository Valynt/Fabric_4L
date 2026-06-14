#!/usr/bin/env python3
"""Seed script to populate academy pillars and quiz questions."""

import asyncio
import os
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from layer5_ground_truth.models.academy import (
    AcademyPillar,
    AcademyQuizQuestion,
)

# Fail-closed: require DATABASE_URL from the environment rather than shipping an
# inline credential default. Seed tooling must not carry hardcoded credentials.
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit(
        "DATABASE_URL is required to run the academy seed script. "
        "Export DATABASE_URL (e.g. via Infisical or your local .env) before running."
    )

PILLARS = [
    {
        "pillar_number": 1,
        "title": "Value Definitions",
        "description": "Learn to articulate value in customer-centric language using the Value Lexicon.",
        "target_maturity_level": 1,
        "duration": "30-45 minutes",
        "content": {
            "overview": "This pillar introduces the foundational vocabulary of value selling.",
            "learning_objectives": ["Define customer value in measurable terms", "Distinguish features from outcomes"],
            "key_takeaways": ["Value is measured in customer outcomes, not product features"],
            "resources": [{"title": "Value Lexicon Cheat Sheet", "url": "/resources/lexicon.pdf", "type": "pdf"}],
        },
    },
    {
        "pillar_number": 2,
        "title": "KPI Taxonomy",
        "description": "Map business outcomes to measurable KPIs using structured taxonomy frameworks.",
        "target_maturity_level": 1,
        "duration": "30-45 minutes",
        "content": {
            "overview": "Learn the structured approach to identifying and categorizing KPIs.",
            "learning_objectives": ["Classify KPIs by business function", "Link KPIs to value drivers"],
            "key_takeaways": ["KPI taxonomy enables consistent measurement across accounts"],
            "resources": [{"title": "KPI Taxonomy Framework", "url": "/resources/kpi-taxonomy.pdf", "type": "pdf"}],
        },
    },
    {
        "pillar_number": 3,
        "title": "ROI Frameworks",
        "description": "Build financial justification using Value Realization and TCO models.",
        "target_maturity_level": 2,
        "duration": "45-60 minutes",
        "content": {
            "overview": "Master the construction of ROI and business case frameworks.",
            "learning_objectives": ["Calculate total cost of ownership", "Build value realization timelines"],
            "key_takeaways": ["ROI frameworks align customer finance with solution value"],
            "resources": [{"title": "ROI Calculator Template", "url": "/resources/roi-template.xlsx", "type": "xlsx"}],
        },
    },
    {
        "pillar_number": 4,
        "title": "Business Case Development",
        "description": "Create compelling business cases using structured narrative and evidence.",
        "target_maturity_level": 2,
        "duration": "45-60 minutes",
        "content": {
            "overview": "Learn to construct business cases that resonate with executive audiences.",
            "learning_objectives": ["Structure executive-ready business cases", "Use evidence to support claims"],
            "key_takeaways": ["Strong business cases combine financial metrics with strategic narrative"],
            "resources": [{"title": "Business Case Template", "url": "/resources/business-case.docx", "type": "docx"}],
        },
    },
    {
        "pillar_number": 5,
        "title": "Value Realization Tracking",
        "description": "Track and report realized value throughout the customer lifecycle.",
        "target_maturity_level": 3,
        "duration": "45-60 minutes",
        "content": {
            "overview": "Establish ongoing measurement and reporting of value delivered.",
            "learning_objectives": ["Design value realization scorecards", "Track outcomes against baselines"],
            "key_takeaways": ["Value realization tracking builds trust and enables renewal"],
            "resources": [{"title": "Value Tracker Dashboard Guide", "url": "/resources/tracker-guide.pdf", "type": "pdf"}],
        },
    },
    {
        "pillar_number": 6,
        "title": "Stakeholder Mapping",
        "description": "Identify and influence key decision-makers using power-interest matrices.",
        "target_maturity_level": 2,
        "duration": "30-45 minutes",
        "content": {
            "overview": "Map organizational influence structures to drive consensus.",
            "learning_objectives": ["Identify economic buyers vs. technical evaluators", "Build coalition strategies"],
            "key_takeaways": ["Stakeholder maps guide targeted value conversations"],
            "resources": [{"title": "Stakeholder Map Template", "url": "/resources/stakeholder-map.pptx", "type": "pptx"}],
        },
    },
    {
        "pillar_number": 7,
        "title": "Pain-to-Value Translation",
        "description": "Transform customer pain points into quantified value propositions.",
        "target_maturity_level": 2,
        "duration": "30-45 minutes",
        "content": {
            "overview": "Learn the systematic method for converting pain into value language.",
            "learning_objectives": ["Use discovery questions to surface pain", "Quantify pain in financial terms"],
            "key_takeaways": ["Pain quantification creates urgency and justifies investment"],
            "resources": [{"title": "Pain-to-Value Worksheet", "url": "/resources/pain-worksheet.pdf", "type": "pdf"}],
        },
    },
    {
        "pillar_number": 8,
        "title": "Competitive Differentiation",
        "description": "Position your solution's unique value against alternatives.",
        "target_maturity_level": 3,
        "duration": "45-60 minutes",
        "content": {
            "overview": "Develop strategies to articulate competitive advantage through value.",
            "learning_objectives": ["Build competitive battlecards", "Frame differentiation in customer terms"],
            "key_takeaways": ["Differentiation is most powerful when expressed as customer value"],
            "resources": [{"title": "Battlecard Template", "url": "/resources/battlecard.pptx", "type": "pptx"}],
        },
    },
    {
        "pillar_number": 9,
        "title": "Executive Communication",
        "description": "Deliver value narratives that resonate with C-suite audiences.",
        "target_maturity_level": 3,
        "duration": "45-60 minutes",
        "content": {
            "overview": "Refine communication techniques for executive value conversations.",
            "learning_objectives": ["Structure executive briefings", "Use storytelling for impact"],
            "key_takeaways": ["Executive communication focuses on strategic outcomes, not tactics"],
            "resources": [{"title": "Executive Briefing Template", "url": "/resources/executive-brief.docx", "type": "docx"}],
        },
    },
    {
        "pillar_number": 10,
        "title": "Value-Led Transformation",
        "description": "Drive organizational change through value-centered programs.",
        "target_maturity_level": 4,
        "duration": "60-90 minutes",
        "content": {
            "overview": "Scale value practices across teams and organizations.",
            "learning_objectives": ["Design value academies", "Build coaching programs"],
            "key_takeaways": ["Sustained value transformation requires culture and process change"],
            "resources": [{"title": "Transformation Playbook", "url": "/resources/transformation.pdf", "type": "pdf"}],
        },
    },
]

SAMPLE_QUESTIONS = [
    {
        "pillar_number": 1,
        "question_number": 1,
        "question_type": "multiple_choice",
        "category": "Value Definitions",
        "question_text": "What is the primary difference between a feature and an outcome?",
        "options": [
            {"label": "A feature is what the product does; an outcome is what the customer achieves", "value": "A"},
            {"label": "A feature is more expensive than an outcome", "value": "B"},
            {"label": "Outcomes are only measurable in financial terms", "value": "C"},
            {"label": "Features are intangible while outcomes are tangible", "value": "D"},
        ],
        "correct_answer": "A",
        "points": 4,
        "feedback": {
            "correct": "Correct! Value selling focuses on customer outcomes, not product capabilities.",
            "incorrect": "Remember: outcomes describe what the customer achieves, not what the product does.",
            "maturity_tips": {
                "level0_1": "Focus on memorizing the basic definitions first.",
                "level2": "Practice translating features to outcomes in real deals.",
                "level3plus": "Coach your team to consistently use outcome language.",
            },
        },
    },
    {
        "pillar_number": 1,
        "question_number": 2,
        "question_type": "multiple_choice",
        "category": "Value Definitions",
        "question_text": "Which of the following best describes 'customer value'?",
        "options": [
            {"label": "The price the customer pays for the product", "value": "A"},
            {"label": "The measurable benefit the customer receives", "value": "B"},
            {"label": "The number of features included", "value": "C"},
            {"label": "The vendor's profit margin", "value": "D"},
        ],
        "correct_answer": "B",
        "points": 4,
        "feedback": {
            "correct": "Correct! Customer value is measured by the benefit received.",
            "incorrect": "Customer value is about the benefit to the customer, not cost or features.",
            "maturity_tips": {
                "level0_1": "Study the Value Lexicon definitions carefully.",
                "level2": "Try quantifying value in your next customer conversation.",
                "level3plus": "Develop custom value metrics for your top accounts.",
            },
        },
    },
]


async def seed():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

        for p in PILLARS:
            pillar = AcademyPillar(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                pillar_number=p["pillar_number"],
                title=p["title"],
                description=p["description"],
                target_maturity_level=p["target_maturity_level"],
                duration=p["duration"],
                content=p["content"],
            )
            session.add(pillar)

        await session.flush()

        from sqlalchemy import select
        from layer5_ground_truth.models.academy import AcademyPillar as PillarModel
        result = await session.execute(select(PillarModel).where(PillarModel.tenant_id == tenant_id))
        pillar_map = {p.pillar_number: p.id for p in result.scalars().all()}

        for q in SAMPLE_QUESTIONS:
            pillar_id = pillar_map.get(q["pillar_number"])
            if not pillar_id:
                continue
            question = AcademyQuizQuestion(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                pillar_id=pillar_id,
                question_number=q["question_number"],
                question_type=q["question_type"],
                category=q["category"],
                question_text=q["question_text"],
                options=q["options"],
                correct_answer=q["correct_answer"],
                points=q["points"],
                feedback=q["feedback"],
            )
            session.add(question)

        await session.commit()
        print("Seeded academy data successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
