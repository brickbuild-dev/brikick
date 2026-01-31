from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(sa.String(100))
    last_name: Mapped[str | None] = mapped_column(sa.String(100))
    country_code: Mapped[str | None] = mapped_column(sa.CHAR(2))
    preferred_currency_id: Mapped[int | None] = mapped_column(sa.Integer)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )
    is_verified: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text)


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        sa.UniqueConstraint("scope", "action", name="uq_permissions_scope_action"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    action: Mapped[str] = mapped_column(sa.String(50), nullable=False)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        primary_key=True,
    )
    role_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("roles.id"),
        primary_key=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    granted_by: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        sa.String(255),
        unique=True,
        nullable=False,
    )
    ip_address: Mapped[str | None] = mapped_column(INET)
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        sa.Index("ix_audit_logs_user_id", "user_id"),
        sa.Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        sa.Index("ix_audit_logs_action", "action"),
        sa.Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
    )
    action: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    old_values: Mapped[dict | None] = mapped_column(JSONB)
    new_values: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    reason: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
