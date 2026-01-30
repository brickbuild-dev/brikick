"""Create orders tables.

Revision ID: 20260130_0010
Revises: 20260130_0009
Create Date: 2026-01-30 00:10:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260130_0010"
down_revision = "20260130_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("order_number", sa.String(length=20), nullable=False, unique=True),
        sa.Column("buyer_id", sa.BigInteger(), nullable=False),
        sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("items_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("shipping_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "insurance_cost",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "tax_amount",
            sa.Numeric(12, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("grand_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("store_currency_id", sa.Integer(), nullable=True),
        sa.Column("buyer_currency_id", sa.Integer(), nullable=True),
        sa.Column("exchange_rate", sa.Numeric(12, 6), nullable=True),
        sa.Column("shipping_method_id", sa.BigInteger(), nullable=True),
        sa.Column("shipping_address_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("tracking_type", sa.String(length=20), nullable=True),
        sa.Column("payment_method_id", sa.BigInteger(), nullable=True),
        sa.Column("payment_status", sa.String(length=20), nullable=True),
        sa.Column("payment_reference", sa.String(length=255), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tracking_number", sa.String(length=100), nullable=True),
        sa.Column("tracking_url", sa.String(length=500), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "shipping_proof_required",
            sa.Boolean(),
            sa.Computed("tracking_type = 'NO_TRACKING'", persisted=True),
        ),
        sa.Column("shipping_proof_url", sa.String(length=500), nullable=True),
        sa.Column("shipping_proof_uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipping_proof_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("buyer_notes", sa.Text(), nullable=True),
        sa.Column("seller_notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["payment_method_id"], ["store_payment_methods.id"]),
        sa.ForeignKeyConstraint(["shipping_method_id"], ["store_shipping_methods.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_id", sa.BigInteger(), nullable=False),
        sa.Column("item_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 4), nullable=False),
        sa.Column("sale_price", sa.Numeric(10, 4), nullable=True),
        sa.Column("line_total", sa.Numeric(12, 4), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
    )

    op.create_table(
        "order_status_history",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("old_status", sa.String(length=20), nullable=False),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("changed_by", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
    )

    op.create_table(
        "order_approvals",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("order_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("reason", sa.String(length=50), nullable=True),
        sa.Column("buyer_risk_score", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("decided_by", sa.BigInteger(), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_cancel_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
    )


def downgrade() -> None:
    op.drop_table("order_approvals")
    op.drop_table("order_status_history")
    op.drop_table("order_items")
    op.drop_table("orders")
