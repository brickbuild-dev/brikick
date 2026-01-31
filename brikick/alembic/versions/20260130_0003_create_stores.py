"""Create store tables and access configs.

Revision ID: 20260130_0003
Revises: 20260130_0002
Create Date: 2026-01-30 00:03:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260130_0003"
down_revision = "20260130_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False, unique=True),
        sa.Column("country_code", sa.CHAR(length=2), nullable=True),
        sa.Column("currency_id", sa.Integer(), nullable=True),
        sa.Column(
            "feedback_score",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.Column("min_buy_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "instant_checkout_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "require_approval_for_risky_buyers",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "risk_threshold_score",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("50.0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_table(
        "store_policies",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("terms_html", sa.Text(), nullable=True),
        sa.Column("shipping_terms_html", sa.Text(), nullable=True),
        sa.Column("has_vat", sa.Boolean(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
    )

    op.create_table(
        "store_api_access",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("store_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'DISABLED'"),
        ),
        sa.Column("api_key_hash", sa.String(length=255), nullable=True),
        sa.Column("api_secret_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "rate_limit_per_minute",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("60"),
        ),
        sa.Column(
            "rate_limit_per_day",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("10000"),
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_reason", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.BigInteger(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "total_requests",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
    )

    op.create_table(
        "store_sync_configs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("store_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("sync_platform", sa.String(length=20), nullable=False),
        sa.Column(
            "sync_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("platform_credentials_encrypted", postgresql.BYTEA(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(length=20), nullable=True),
        sa.Column("items_synced", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "sync_platform IN ('BRICKLINK', 'BRICKOWL')",
            name="ck_store_sync_configs_platform",
        ),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
    )

    op.create_table(
        "store_shipping_methods",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("ships_to_countries", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("cost_type", sa.String(length=20), nullable=True),
        sa.Column("base_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("tracking_type", sa.String(length=20), nullable=True),
        sa.Column("insurance_available", sa.Boolean(), nullable=True),
        sa.Column("min_days", sa.Integer(), nullable=True),
        sa.Column("max_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
    )

    op.create_table(
        "store_payment_methods",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("method_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_on_site", sa.Boolean(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
    )

    op.create_foreign_key(
        "fk_price_override_requests_store_id",
        "price_override_requests",
        "stores",
        ["store_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_price_override_requests_store_id",
        "price_override_requests",
        type_="foreignkey",
    )
    op.drop_table("store_payment_methods")
    op.drop_table("store_shipping_methods")
    op.drop_table("store_sync_configs")
    op.drop_table("store_api_access")
    op.drop_table("store_policies")
    op.drop_table("stores")
