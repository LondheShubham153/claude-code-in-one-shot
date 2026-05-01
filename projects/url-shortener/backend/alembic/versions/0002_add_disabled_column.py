"""add disabled column

Revision ID: 0002_add_disabled_column
Revises: 0001_create_links
Create Date: 2026-05-01 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_disabled_column"
down_revision: str | None = "0001_create_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "links",
        sa.Column(
            "disabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("links", "disabled")
