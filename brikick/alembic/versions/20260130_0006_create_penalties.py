"""Create penalties and issues tables.

Revision ID: 20260130_0006
Revises: 20260130_0005
Create Date: 2026-01-30 00:06:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260130_0006"
down_revision = "20260130_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_penalty_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "warning_threshold",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3"),
        ),
        sa.Column(
            "cooldown_threshold",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5"),
        ),
        sa.Column(
            "suspension_threshold",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("8"),
        ),
        sa.Column(
            "ban_threshold",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("12"),
        ),
        sa.Column(
            "evaluation_period_months",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("6"),
        ),
        sa.Column(
            "issue_decay_months",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("12"),
        ),
    )

    op.create_table(
        "user_issues",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("issue_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("related_order_id", sa.BigInteger(), nullable=True),
        sa.Column("related_dispute_id", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_table(
        "user_penalties",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("penalty_type", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restrictions", postgresql.JSONB(), nullable=True),
        sa.Column("appeal_status", sa.String(length=20), nullable=True),
        sa.Column("appeal_text", sa.Text(), nullable=True),
        sa.Column("appeal_reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("appeal_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["appeal_reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    config_table = sa.table(
        "user_penalty_configs",
        sa.column("warning_threshold", sa.Integer),
        sa.column("cooldown_threshold", sa.Integer),
        sa.column("suspension_threshold", sa.Integer),
        sa.column("ban_threshold", sa.Integer),
        sa.column("evaluation_period_months", sa.Integer),
        sa.column("issue_decay_months", sa.Integer),
    )
    op.bulk_insert(
        config_table,
        [
            {
                "warning_threshold": 3,
                "cooldown_threshold": 5,
                "suspension_threshold": 8,
                "ban_threshold": 12,
                "evaluation_period_months": 6,
                "issue_decay_months": 12,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("user_penalties")
    op.drop_table("user_issues")
    op.drop_table("user_penalty_configs")
