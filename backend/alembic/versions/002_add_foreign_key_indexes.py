"""Add foreign key indexes for DB optimization

Revision ID: 002
Revises: 001
Create Date: 2026-06-06
"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"], unique=False)
    op.create_index("ix_projects_user_id", "projects", ["user_id"], unique=False)
    op.create_index("ix_interview_sessions_user_id", "interview_sessions", ["user_id"], unique=False)
    op.create_index("ix_questions_session_id", "questions", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_questions_session_id", table_name="questions")
    op.drop_index("ix_interview_sessions_user_id", table_name="interview_sessions")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_index("ix_resumes_user_id", table_name="resumes")
