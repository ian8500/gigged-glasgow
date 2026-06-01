from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_slug: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(40), default="running", nullable=False)
    venues_checked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    events_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    events_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    events_needing_review: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[str | None] = mapped_column(Text)
    warnings: Mapped[str | None] = mapped_column(Text)
