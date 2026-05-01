"""create links

Revision ID: 0001_create_links
Revises:
Create Date: 2026-05-01 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_create_links"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "links",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=32), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("click_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_ip", postgresql.INET(), nullable=True),
        sa.Column("safe_browsing_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_links_slug"),
        sa.CheckConstraint("length(slug) BETWEEN 4 AND 32", name="ck_links_slug_length"),
        sa.CheckConstraint("url ~ '^https?://'", name="ck_links_url_scheme"),
    )
    op.create_index("ix_links_slug", "links", ["slug"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_links_slug", table_name="links")
    op.drop_table("links")
