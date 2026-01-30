from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class UserAddress(Base):
    __tablename__ = "user_addresses"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        nullable=False,
    )
    first_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    address_line1: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(sa.String(255))
    city: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    state_name: Mapped[str | None] = mapped_column(sa.String(100))
    postal_code: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    country_code: Mapped[str] = mapped_column(sa.CHAR(2), nullable=False)
    phone: Mapped[str] = mapped_column(sa.String(30), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )


class CheckoutDraft(Base):
    __tablename__ = "checkout_drafts"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    cart_store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("cart_stores.id"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        nullable=False,
    )
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        server_default=sa.text("'DRAFT'"),
    )
    shipping_address_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("user_addresses.id"),
    )
    shipping_method_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("store_shipping_methods.id"),
    )
    shipping_cost: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 2))
    insurance_cost: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2),
        nullable=False,
        server_default=sa.text("0"),
    )
    tracking_fee: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2),
        nullable=False,
        server_default=sa.text("0"),
    )
    payment_method_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("store_payment_methods.id"),
    )
    payment_currency_id: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    items_total: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2),
        nullable=False,
        server_default=sa.text("0"),
    )
    shipping_total: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2),
        nullable=False,
        server_default=sa.text("0"),
    )
    tax_total: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2),
        nullable=False,
        server_default=sa.text("0"),
    )
    grand_total: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2),
        nullable=False,
        server_default=sa.text("0"),
    )
    quote_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    payment_session_id: Mapped[str | None] = mapped_column(sa.String(255))
    payment_provider: Mapped[str | None] = mapped_column(sa.String(50))
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
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )


class OrderApproval(Base):
    __tablename__ = "order_approvals"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    checkout_draft_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("checkout_drafts.id"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        nullable=False,
    )
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        server_default=sa.text("'PENDING'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
