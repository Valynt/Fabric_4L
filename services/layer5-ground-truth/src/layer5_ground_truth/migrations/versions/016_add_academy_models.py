"""Add academy models (pillars, quizzes, progress, certifications, assessments, resources).

Revision ID: 016
Revises: 015
Create Date: 2026-06-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # --- pillars ---
    op.create_table(
        "academy_pillars",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pillar_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_maturity_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration", sa.String(length=64), nullable=True),
        sa.Column("content", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_academy_pillars_tenant_id", "academy_pillars", ["tenant_id"])
    op.create_index("ix_academy_pillars_tenant_number", "academy_pillars", ["tenant_id", "pillar_number"], unique=True)
    op.execute("ALTER TABLE academy_pillars ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE academy_pillars FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academy_pillars_tenant_isolation ON academy_pillars
            FOR ALL TO PUBLIC
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
    """)

    # --- quiz_questions ---
    op.create_table(
        "academy_quiz_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pillar_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(), nullable=False),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("feedback", postgresql.JSONB(), nullable=True),
        sa.Column("role_adaptations", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_academy_quiz_questions_tenant_id", "academy_quiz_questions", ["tenant_id"])
    op.create_index("ix_academy_quiz_questions_tenant_pillar", "academy_quiz_questions", ["tenant_id", "pillar_id"])
    op.execute("ALTER TABLE academy_quiz_questions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE academy_quiz_questions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academy_quiz_questions_tenant_isolation ON academy_quiz_questions
            FOR ALL TO PUBLIC
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
    """)

    # --- progress ---
    op.create_table(
        "academy_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("pillar_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="not_started"),
        sa.Column("completion_percentage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_accessed", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_academy_progress_tenant_id", "academy_progress", ["tenant_id"])
    op.create_index("ix_academy_progress_tenant_user", "academy_progress", ["tenant_id", "user_id"])
    op.create_index("ix_academy_progress_tenant_user_pillar", "academy_progress", ["tenant_id", "user_id", "pillar_id"], unique=True)
    op.execute("ALTER TABLE academy_progress ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE academy_progress FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academy_progress_tenant_isolation ON academy_progress
            FOR ALL TO PUBLIC
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
    """)

    # --- quiz_results ---
    op.create_table(
        "academy_quiz_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("pillar_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("category_scores", postgresql.JSONB(), nullable=True),
        sa.Column("answers", postgresql.JSONB(), nullable=False),
        sa.Column("feedback", postgresql.JSONB(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_academy_quiz_results_tenant_id", "academy_quiz_results", ["tenant_id"])
    op.create_index("ix_academy_quiz_results_tenant_user_pillar", "academy_quiz_results", ["tenant_id", "user_id", "pillar_id"])
    op.execute("ALTER TABLE academy_quiz_results ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE academy_quiz_results FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academy_quiz_results_tenant_isolation ON academy_quiz_results
            FOR ALL TO PUBLIC
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
    """)

    # --- certifications ---
    op.create_table(
        "academy_certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("badge_name", sa.String(length=255), nullable=False),
        sa.Column("pillar_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vos_role", sa.String(length=32), nullable=False),
        sa.Column("certificate_url", sa.String(length=512), nullable=True),
        sa.Column("awarded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_academy_certifications_tenant_id", "academy_certifications", ["tenant_id"])
    op.create_index("ix_academy_certifications_tenant_user", "academy_certifications", ["tenant_id", "user_id"])
    op.execute("ALTER TABLE academy_certifications ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE academy_certifications FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academy_certifications_tenant_isolation ON academy_certifications
            FOR ALL TO PUBLIC
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
    """)

    # --- maturity_assessments ---
    op.create_table(
        "academy_maturity_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("assessment_data", postgresql.JSONB(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_academy_maturity_assessments_tenant_id", "academy_maturity_assessments", ["tenant_id"])
    op.create_index("ix_academy_maturity_assessments_tenant_user", "academy_maturity_assessments", ["tenant_id", "user_id"])
    op.execute("ALTER TABLE academy_maturity_assessments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE academy_maturity_assessments FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academy_maturity_assessments_tenant_isolation ON academy_maturity_assessments
            FOR ALL TO PUBLIC
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
    """)

    # --- resources ---
    op.create_table(
        "academy_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("file_url", sa.String(length=512), nullable=False),
        sa.Column("pillar_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vos_role", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_academy_resources_tenant_id", "academy_resources", ["tenant_id"])
    op.execute("ALTER TABLE academy_resources ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE academy_resources FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY academy_resources_tenant_isolation ON academy_resources
            FOR ALL TO PUBLIC
            USING (tenant_id::text = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
    """)


def downgrade() -> None:
    op.drop_table("academy_resources")
    op.drop_table("academy_maturity_assessments")
    op.drop_table("academy_certifications")
    op.drop_table("academy_quiz_results")
    op.drop_table("academy_progress")
    op.drop_table("academy_quiz_questions")
    op.drop_table("academy_pillars")
