"""Create catalog and price guide tables.

Revision ID: 20260130_0002
Revises: 20260130_0001
Create Date: 2026-01-30 00:02:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260130_0002"
down_revision = "20260130_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "item_types",
        sa.Column("id", sa.CHAR(length=1), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("name_plural", sa.String(length=50), nullable=False),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("allowed_item_types", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
    )

    op.create_table(
        "colors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("rgb", sa.String(length=6), nullable=True),
        sa.Column("color_group", sa.Integer(), nullable=True),
    )

    op.create_table(
        "catalog_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("item_no", sa.String(length=50), nullable=False),
        sa.Column(
            "item_seq",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("item_type", sa.CHAR(length=1), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("year_released", sa.SmallInteger(), nullable=True),
        sa.Column("weight_grams", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["item_type"], ["item_types.id"]),
        sa.UniqueConstraint(
            "item_no",
            "item_type",
            "item_seq",
            name="uq_catalog_items_item_no_type_seq",
        ),
    )

    op.create_table(
        "catalog_item_mappings",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("catalog_item_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["catalog_items.id"]),
    )
    op.create_index(
        "ix_catalog_item_mappings_source_external_id",
        "catalog_item_mappings",
        ["source", "external_id"],
    )

    op.create_table(
        "price_guides",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("catalog_item_id", sa.BigInteger(), nullable=False),
        sa.Column("color_id", sa.Integer(), nullable=False),
        sa.Column("condition", sa.CHAR(length=1), nullable=False),
        sa.Column("avg_price_6m", sa.Numeric(10, 4), nullable=False),
        sa.Column("min_price_6m", sa.Numeric(10, 4), nullable=False),
        sa.Column("max_price_6m", sa.Numeric(10, 4), nullable=False),
        sa.Column("sales_count_6m", sa.Integer(), nullable=False),
        sa.Column(
            "price_cap",
            sa.Numeric(10, 4),
            sa.Computed("avg_price_6m * 2.0", persisted=True),
        ),
        sa.Column("last_calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["color_id"], ["colors.id"]),
        sa.UniqueConstraint(
            "catalog_item_id",
            "color_id",
            "condition",
            name="uq_price_guides_item_color_condition",
        ),
    )

    op.create_table(
        "price_override_requests",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("lot_id", sa.BigInteger(), nullable=True),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("catalog_item_id", sa.BigInteger(), nullable=False),
        sa.Column("color_id", sa.Integer(), nullable=False),
        sa.Column("condition", sa.CHAR(length=1), nullable=False),
        sa.Column("requested_price", sa.Numeric(10, 4), nullable=False),
        sa.Column("price_cap", sa.Numeric(10, 4), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["color_id"], ["colors.id"]),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
    )


def downgrade() -> None:
    op.drop_table("price_override_requests")
    op.drop_table("price_guides")
    op.drop_index(
        "ix_catalog_item_mappings_source_external_id",
        table_name="catalog_item_mappings",
    )
    op.drop_table("catalog_item_mappings")
    op.drop_table("catalog_items")
    op.drop_table("colors")
    op.drop_table("categories")
    op.drop_table("item_types")
