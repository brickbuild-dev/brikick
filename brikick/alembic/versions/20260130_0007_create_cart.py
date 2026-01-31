"""Create cart tables.

Revision ID: 20260130_0007
Revises: 20260130_0006
Create Date: 2026-01-30 00:07:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260130_0007"
down_revision = "20260130_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "carts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, unique=True),
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
        "cart_stores",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("cart_id", sa.BigInteger(), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "total_items",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_lots",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_weight_grams",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.UniqueConstraint(
            "cart_id",
            "store_id",
            name="uq_cart_stores_cart_store",
        ),
    )

    op.create_table(
        "cart_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("cart_store_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(10, 4), nullable=False),
        sa.Column("sale_price_snapshot", sa.Numeric(10, 4), nullable=True),
        sa.Column("warnings", postgresql.JSONB(), nullable=True),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["cart_store_id"], ["cart_stores.id"]),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"]),
        sa.UniqueConstraint(
            "cart_store_id",
            "lot_id",
            name="uq_cart_items_cart_store_lot",
        ),
    )


def downgrade() -> None:
    op.drop_table("cart_items")
    op.drop_table("cart_stores")
    op.drop_table("carts")
