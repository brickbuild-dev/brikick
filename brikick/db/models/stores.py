from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False)
    country_code: Mapped[str | None] = mapped_column(sa.CHAR(2))
    currency_id: Mapped[int | None] = mapped_column(sa.Integer)
    feedback_score: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
    )
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )
    min_buy_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 2))
    instant_checkout_enabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )
    require_approval_for_risky_buyers: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )
    risk_threshold_score: Mapped[Decimal] = mapped_column(
        sa.Numeric(5, 2),
        nullable=False,
        server_default=sa.text("50.0"),
    )
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


class StorePolicy(Base):
    __tablename__ = "store_policies"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        nullable=False,
    )
    terms_html: Mapped[str | None] = mapped_column(sa.Text)
    shipping_terms_html: Mapped[str | None] = mapped_column(sa.Text)
    has_vat: Mapped[bool | None] = mapped_column(sa.Boolean)
    version: Mapped[int | None] = mapped_column(sa.Integer)
    updated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class StoreApiAccess(Base):
    __tablename__ = "store_api_access"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        server_default=sa.text("'DISABLED'"),
    )
    api_key_hash: Mapped[str | None] = mapped_column(sa.String(255))
    api_secret_hash: Mapped[str | None] = mapped_column(sa.String(255))
    rate_limit_per_minute: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("60"),
    )
    rate_limit_per_day: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("10000"),
    )
    requested_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    request_reason: Mapped[str | None] = mapped_column(sa.Text)
    approved_by: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    total_requests: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        server_default=sa.text("0"),
    )


class StoreSyncConfig(Base):
    __tablename__ = "store_sync_configs"
    __table_args__ = (
        sa.CheckConstraint(
            "sync_platform IN ('BRICKLINK', 'BRICKOWL')",
            name="ck_store_sync_configs_platform",
        ),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        unique=True,
        nullable=False,
    )
    sync_platform: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    sync_enabled: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )
    platform_credentials_encrypted: Mapped[bytes | None] = mapped_column(BYTEA)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    sync_status: Mapped[str | None] = mapped_column(sa.String(20))
    items_synced: Mapped[int | None] = mapped_column(sa.Integer)


class StoreShippingMethod(Base):
    __tablename__ = "store_shipping_methods"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(sa.Text)
    ships_to_countries: Mapped[list[str] | None] = mapped_column(ARRAY(sa.Text))
    cost_type: Mapped[str | None] = mapped_column(sa.String(20))
    base_cost: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 2))
    tracking_type: Mapped[str | None] = mapped_column(sa.String(20))
    insurance_available: Mapped[bool | None] = mapped_column(sa.Boolean)
    min_days: Mapped[int | None] = mapped_column(sa.Integer)
    max_days: Mapped[int | None] = mapped_column(sa.Integer)
    is_active: Mapped[bool | None] = mapped_column(sa.Boolean)


class StorePaymentMethod(Base):
    __tablename__ = "store_payment_methods"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        nullable=False,
    )
    method_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    is_on_site: Mapped[bool | None] = mapped_column(sa.Boolean)
    is_active: Mapped[bool | None] = mapped_column(sa.Boolean)
