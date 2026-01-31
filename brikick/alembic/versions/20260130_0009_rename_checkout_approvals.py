"""Rename checkout approvals table.

Revision ID: 20260130_0009
Revises: 20260130_0008
Create Date: 2026-01-30 00:09:00.000000
"""
from __future__ import annotations

from alembic import op

revision = "20260130_0009"
down_revision = "20260130_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("order_approvals", "checkout_approvals")


def downgrade() -> None:
    op.rename_table("checkout_approvals", "order_approvals")
