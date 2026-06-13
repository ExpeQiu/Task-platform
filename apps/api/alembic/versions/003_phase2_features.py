"""phase2: skills, memory, workflow approvals, task skill_id

Revision ID: 003_phase2_features
Revises: 002_add_goal_criteria
Create Date: 2026-06-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_phase2_features"
down_revision: Union[str, None] = "002_add_goal_criteria"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("instructions", sa.Text(), server_default="", nullable=False),
        sa.Column("applicable_task_types", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("input_contract", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("output_contract", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column("tasks", sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_tasks_skill_id", "tasks", "skills", ["skill_id"], ["id"])
    op.create_table(
        "memory_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope", sa.String(length=50), server_default="global", nullable=False),
        sa.Column("scope_ref", sa.String(length=255), nullable=True),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "workflow_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_runs.id"), nullable=False),
        sa.Column("node_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), server_default="", nullable=False),
        sa.Column("message", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("decided_by", sa.String(length=100), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("workflow_approvals")
    op.drop_table("memory_entries")
    op.drop_constraint("fk_tasks_skill_id", "tasks", type_="foreignkey")
    op.drop_column("tasks", "skill_id")
    op.drop_table("skills")
