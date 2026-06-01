from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SourceFeed(Base):
    __tablename__ = "source_feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(160), nullable=False)
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venues.id"), index=True)
    city_slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    feed_url: Mapped[str] = mapped_column(String(800), nullable=False)
    feed_type: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    venue = relationship("Venue")
