"""add goal criteria and verification_results

Revision ID: 002_add_goal_criteria
Revises: 001_initial
Create Date: 2026-06-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_add_goal_criteria"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("success_criteria", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )
    op.add_column(
        "tasks",
        sa.Column("failure_criteria", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
    )
    op.add_column(
        "tasks",
        sa.Column("verification_mode", sa.String(length=50), server_default="rule_based", nullable=False),
    )
    op.create_table(
        "verification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("task_runs.id"), nullable=False),
        sa.Column("iteration", sa.Integer(), server_default="0", nullable=False),
        sa.Column("verdict", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("signals", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("verified_by", sa.String(length=100), server_default="rule_based", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("verification_results")
    op.drop_column("tasks", "verification_mode")
    op.drop_column("tasks", "failure_criteria")
    op.drop_column("tasks", "success_criteria")
