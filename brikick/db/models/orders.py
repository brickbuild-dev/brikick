from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    order_number: Mapped[str] = mapped_column(
        sa.String(20),
        unique=True,
        nullable=False,
    )
    buyer_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        nullable=False,
    )
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    items_total: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2),
        nullable=False,
    )
    shipping_cost: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2),
        nullable=False,
    )
    insurance_cost: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2),
        nullable=False,
        server_default=sa.text("0"),
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2),
        nullable=False,
        server_default=sa.text("0"),
    )
    grand_total: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2),
        nullable=False,
    )
    store_currency_id: Mapped[int | None] = mapped_column(sa.Integer)
    buyer_currency_id: Mapped[int | None] = mapped_column(sa.Integer)
    exchange_rate: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 6))
    shipping_method_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("store_shipping_methods.id"),
    )
    shipping_address_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    tracking_type: Mapped[str | None] = mapped_column(sa.String(20))
    payment_method_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("store_payment_methods.id"),
    )
    payment_status: Mapped[str | None] = mapped_column(sa.String(20))
    payment_reference: Mapped[str | None] = mapped_column(sa.String(255))
    paid_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    tracking_number: Mapped[str | None] = mapped_column(sa.String(100))
    tracking_url: Mapped[str | None] = mapped_column(sa.String(500))
    shipped_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    shipping_proof_required: Mapped[bool | None] = mapped_column(
        sa.Boolean,
        sa.Computed("tracking_type = 'NO_TRACKING'", persisted=True),
    )
    shipping_proof_url: Mapped[str | None] = mapped_column(sa.String(500))
    shipping_proof_uploaded_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    shipping_proof_deadline: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    buyer_notes: Mapped[str | None] = mapped_column(sa.Text)
    seller_notes: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("orders.id"),
        nullable=False,
    )
    lot_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("lots.id"),
        nullable=False,
    )
    item_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 4),
        nullable=False,
    )
    sale_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 4))
    line_total: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 4),
        nullable=False,
    )


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("orders.id"),
        nullable=False,
    )
    old_status: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    changed_by: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
    )
    reason: Mapped[str | None] = mapped_column(sa.Text)
    changed_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


class OrderApproval(Base):
    __tablename__ = "order_approvals"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("orders.id"),
        unique=True,
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(sa.String(50))
    buyer_risk_score: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2))
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        server_default=sa.text("'PENDING'"),
    )
    decided_by: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
    )
    decision_notes: Mapped[str | None] = mapped_column(sa.Text)
    decided_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    auto_cancel_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
