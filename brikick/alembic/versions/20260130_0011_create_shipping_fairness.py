"""Create shipping fairness tables.

Revision ID: 20260130_0011
Revises: 20260130_0010
Create Date: 2026-01-30 00:11:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260130_0011"
down_revision = "20260130_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shipping_fairness_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "max_markup_percentage",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("15.0"),
        ),
        sa.Column(
            "alert_threshold_percentage",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("25.0"),
        ),
        sa.Column(
            "auto_flag_threshold",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("50.0"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "shipping_cost_benchmarks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("origin_country", sa.CHAR(length=2), nullable=False),
        sa.Column("destination_country", sa.CHAR(length=2), nullable=False),
        sa.Column("destination_region", sa.String(length=50), nullable=True),
        sa.Column("carrier", sa.String(length=50), nullable=True),
        sa.Column("service_type", sa.String(length=50), nullable=True),
        sa.Column("weight_min_grams", sa.Integer(), nullable=False),
        sa.Column("weight_max_grams", sa.Integer(), nullable=False),
        sa.Column("benchmark_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("benchmark_currency", sa.CHAR(length=3), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "shipping_fairness_flags",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("charged_shipping", sa.Numeric(10, 2), nullable=False),
        sa.Column("estimated_real_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("markup_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("flag_type", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'OPEN'"),
        ),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
    )

    config_table = sa.table(
        "shipping_fairness_configs",
        sa.column("max_markup_percentage", sa.Numeric),
        sa.column("alert_threshold_percentage", sa.Numeric),
        sa.column("auto_flag_threshold", sa.Numeric),
    )
    op.bulk_insert(
        config_table,
        [
            {
                "max_markup_percentage": 15.0,
                "alert_threshold_percentage": 25.0,
                "auto_flag_threshold": 50.0,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("shipping_fairness_flags")
    op.drop_table("shipping_cost_benchmarks")
    op.drop_table("shipping_fairness_configs")
