"""Create inventory lots table.

Revision ID: 20260130_0004
Revises: 20260130_0003
Create Date: 2026-01-30 00:04:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260130_0004"
down_revision = "20260130_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lots",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("catalog_item_id", sa.BigInteger(), nullable=False),
        sa.Column("color_id", sa.Integer(), nullable=True),
        sa.Column("condition", sa.CHAR(length=1), nullable=False),
        sa.Column("completeness", sa.CHAR(length=1), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "bulk_quantity",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("unit_price", sa.Numeric(10, 4), nullable=False),
        sa.Column(
            "sale_percentage",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("tier1_qty", sa.Integer(), nullable=True),
        sa.Column("tier1_price", sa.Numeric(10, 4), nullable=True),
        sa.Column("tier2_qty", sa.Integer(), nullable=True),
        sa.Column("tier2_price", sa.Numeric(10, 4), nullable=True),
        sa.Column("tier3_qty", sa.Integer(), nullable=True),
        sa.Column("tier3_price", sa.Numeric(10, 4), nullable=True),
        sa.Column("superlot_id", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("extended_description", sa.Text(), nullable=True),
        sa.Column("custom_image_url", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'AVAILABLE'"),
        ),
        sa.Column(
            "listed_at",
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
        sa.Column(
            "price_override_approved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("price_override_request_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["color_id"], ["colors.id"]),
        sa.ForeignKeyConstraint(["price_override_request_id"], ["price_override_requests.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["superlot_id"], ["lots.id"]),
    )
    op.create_index("ix_lots_store_id", "lots", ["store_id"])
    op.create_index("ix_lots_catalog_item_id", "lots", ["catalog_item_id"])
    op.create_index("ix_lots_color_id", "lots", ["color_id"])
    op.create_index("ix_lots_condition", "lots", ["condition"])
    op.create_index("ix_lots_unit_price", "lots", ["unit_price"])
    op.create_index("ix_lots_status", "lots", ["status"])

    op.create_foreign_key(
        "fk_price_override_requests_lot_id",
        "price_override_requests",
        "lots",
        ["lot_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_price_override_requests_lot_id",
        "price_override_requests",
        type_="foreignkey",
    )
    op.drop_index("ix_lots_status", table_name="lots")
    op.drop_index("ix_lots_unit_price", table_name="lots")
    op.drop_index("ix_lots_condition", table_name="lots")
    op.drop_index("ix_lots_color_id", table_name="lots")
    op.drop_index("ix_lots_catalog_item_id", table_name="lots")
    op.drop_index("ix_lots_store_id", table_name="lots")
    op.drop_table("lots")
