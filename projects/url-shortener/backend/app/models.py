from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Link(Base):
    __tablename__ = "links"
    __table_args__ = (
        CheckConstraint("length(slug) BETWEEN 4 AND 32", name="ck_links_slug_length"),
        CheckConstraint("url ~ '^https?://'", name="ck_links_url_scheme"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    click_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    safe_browsing_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
