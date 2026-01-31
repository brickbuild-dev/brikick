"""Create rating and badge tables.

Revision ID: 20260130_0005
Revises: 20260130_0004
Create Date: 2026-01-30 00:05:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260130_0005"
down_revision = "20260130_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rating_factors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("factor_code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("factor_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("applies_to", sa.String(length=20), nullable=False),
        sa.Column("weight", sa.Numeric(5, 2), nullable=False),
        sa.Column("higher_is_better", sa.Boolean(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    op.create_table(
        "sla_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "shipping_excellent_hours",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("24"),
        ),
        sa.Column(
            "shipping_good_hours",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("48"),
        ),
        sa.Column(
            "shipping_acceptable_hours",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("72"),
        ),
        sa.Column(
            "message_excellent_hours",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("24"),
        ),
        sa.Column(
            "message_good_hours",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("48"),
        ),
        sa.Column(
            "message_acceptable_hours",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("72"),
        ),
    )

    op.create_table(
        "user_rating_metrics",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("metrics_json", postgresql.JSONB(), nullable=True),
        sa.Column("factor_scores", postgresql.JSONB(), nullable=True),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_tier", sa.String(length=20), nullable=True),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_table(
        "sla_metrics",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("orders_shipped_total", sa.Integer(), nullable=True),
        sa.Column("orders_shipped_24h", sa.Integer(), nullable=True),
        sa.Column("orders_shipped_48h", sa.Integer(), nullable=True),
        sa.Column("orders_shipped_72h", sa.Integer(), nullable=True),
        sa.Column("orders_shipped_late", sa.Integer(), nullable=True),
        sa.Column("avg_shipping_hours", sa.Numeric(10, 2), nullable=True),
        sa.Column("messages_received", sa.Integer(), nullable=True),
        sa.Column("messages_replied_24h", sa.Integer(), nullable=True),
        sa.Column("messages_replied_48h", sa.Integer(), nullable=True),
        sa.Column("messages_replied_72h", sa.Integer(), nullable=True),
        sa.Column("shipping_sla_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("message_sla_score", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
    )

    op.create_table(
        "badges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("badge_type", sa.String(length=20), nullable=False),
        sa.Column("criteria", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "user_badges",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("badge_id", sa.Integer(), nullable=False),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "badge_id"),
    )

    rating_factors_table = sa.table(
        "rating_factors",
        sa.column("factor_code", sa.String),
        sa.column("factor_name", sa.String),
        sa.column("description", sa.Text),
        sa.column("applies_to", sa.String),
        sa.column("weight", sa.Numeric),
        sa.column("higher_is_better", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        rating_factors_table,
        [
            {
                "factor_code": "ITEMS_LISTED_MONTHLY",
                "factor_name": "ITEMS_LISTED_MONTHLY",
                "description": None,
                "applies_to": "SELLER",
                "weight": 0.05,
                "higher_is_better": True,
                "is_active": True,
            },
            {
                "factor_code": "LISTING_REGULARITY",
                "factor_name": "LISTING_REGULARITY",
                "description": None,
                "applies_to": "SELLER",
                "weight": 0.05,
                "higher_is_better": True,
                "is_active": True,
            },
            {
                "factor_code": "ORDERS_RECEIVED_MONTHLY",
                "factor_name": "ORDERS_RECEIVED_MONTHLY",
                "description": None,
                "applies_to": "SELLER",
                "weight": 0.10,
                "higher_is_better": True,
                "is_active": True,
            },
            {
                "factor_code": "MESSAGE_RESPONSE_RATE",
                "factor_name": "MESSAGE_RESPONSE_RATE",
                "description": None,
                "applies_to": "SELLER",
                "weight": 0.15,
                "higher_is_better": True,
                "is_active": True,
            },
            {
                "factor_code": "DISPUTES_WON_RATE",
                "factor_name": "DISPUTES_WON_RATE",
                "description": None,
                "applies_to": "SELLER",
                "weight": 0.15,
                "higher_is_better": True,
                "is_active": True,
            },
            {
                "factor_code": "SHIPPING_SLA_SCORE",
                "factor_name": "SHIPPING_SLA_SCORE",
                "description": None,
                "applies_to": "SELLER",
                "weight": 0.20,
                "higher_is_better": True,
                "is_active": True,
            },
            {
                "factor_code": "PRICE_FAIRNESS",
                "factor_name": "PRICE_FAIRNESS",
                "description": None,
                "applies_to": "SELLER",
                "weight": 0.10,
                "higher_is_better": True,
                "is_active": True,
            },
            {
                "factor_code": "CANCELLATION_RATE",
                "factor_name": "CANCELLATION_RATE",
                "description": None,
                "applies_to": "SELLER",
                "weight": 0.10,
                "higher_is_better": False,
                "is_active": True,
            },
            {
                "factor_code": "ACCOUNT_AGE_MONTHS",
                "factor_name": "ACCOUNT_AGE_MONTHS",
                "description": None,
                "applies_to": "SELLER",
                "weight": 0.05,
                "higher_is_better": True,
                "is_active": True,
            },
            {
                "factor_code": "COMPLAINTS_RATE",
                "factor_name": "COMPLAINTS_RATE",
                "description": None,
                "applies_to": "SELLER",
                "weight": 0.05,
                "higher_is_better": False,
                "is_active": True,
            },
            {
                "factor_code": "ORDERS_PLACED_MONTHLY",
                "factor_name": "ORDERS_PLACED_MONTHLY",
                "description": None,
                "applies_to": "BUYER",
                "weight": 0.15,
                "higher_is_better": True,
                "is_active": True,
            },
            {
                "factor_code": "PAYMENT_SPEED",
                "factor_name": "PAYMENT_SPEED",
                "description": None,
                "applies_to": "BUYER",
                "weight": 0.20,
                "higher_is_better": True,
                "is_active": True,
            },
            {
                "factor_code": "DISPUTES_OPENED_RATE",
                "factor_name": "DISPUTES_OPENED_RATE",
                "description": None,
                "applies_to": "BUYER",
                "weight": 0.15,
                "higher_is_better": False,
                "is_active": True,
            },
            {
                "factor_code": "CANCELLATION_RATE_BUYER",
                "factor_name": "CANCELLATION_RATE_BUYER",
                "description": None,
                "applies_to": "BUYER",
                "weight": 0.20,
                "higher_is_better": False,
                "is_active": True,
            },
            {
                "factor_code": "CHARGEBACK_HISTORY",
                "factor_name": "CHARGEBACK_HISTORY",
                "description": None,
                "applies_to": "BUYER",
                "weight": 0.25,
                "higher_is_better": False,
                "is_active": True,
            },
            {
                "factor_code": "ACCOUNT_AGE_MONTHS_BUYER",
                "factor_name": "ACCOUNT_AGE_MONTHS_BUYER",
                "description": None,
                "applies_to": "BUYER",
                "weight": 0.05,
                "higher_is_better": True,
                "is_active": True,
            },
        ],
    )

    badges_table = sa.table(
        "badges",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("icon_url", sa.String),
        sa.column("badge_type", sa.String),
        sa.column("criteria", postgresql.JSONB),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        badges_table,
        [
            {
                "code": "TRUSTED_SELLER",
                "name": "TRUSTED_SELLER",
                "description": None,
                "icon_url": None,
                "badge_type": "MONTHLY",
                "criteria": {"overall_score_gte": 85},
                "is_active": True,
            },
            {
                "code": "FAST_SHIPPER",
                "name": "FAST_SHIPPER",
                "description": None,
                "icon_url": None,
                "badge_type": "MONTHLY",
                "criteria": {"shipping_sla_gte": 95},
                "is_active": True,
            },
            {
                "code": "HIGH_ACCURACY",
                "name": "HIGH_ACCURACY",
                "description": None,
                "icon_url": None,
                "badge_type": "MONTHLY",
                "criteria": {"disputes_won_rate_gte": 95},
                "is_active": True,
            },
            {
                "code": "LOYALTY_1Y",
                "name": "LOYALTY_1Y",
                "description": None,
                "icon_url": None,
                "badge_type": "MILESTONE",
                "criteria": {"account_age_months_gte": 12},
                "is_active": True,
            },
            {
                "code": "MILESTONE_100",
                "name": "MILESTONE_100",
                "description": None,
                "icon_url": None,
                "badge_type": "ACHIEVEMENT",
                "criteria": {"orders_gte": 100},
                "is_active": True,
            },
            {
                "code": "MILESTONE_1000",
                "name": "MILESTONE_1000",
                "description": None,
                "icon_url": None,
                "badge_type": "ACHIEVEMENT",
                "criteria": {"orders_gte": 1000},
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("user_badges")
    op.drop_table("badges")
    op.drop_table("sla_metrics")
    op.drop_table("user_rating_metrics")
    op.drop_table("sla_configs")
    op.drop_table("rating_factors")
