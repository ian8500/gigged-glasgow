from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class VenueCheckLog(Base):
    __tablename__ = "venue_check_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String(40), default="needs_review", nullable=False)
    coverage_status: Mapped[str] = mapped_column(String(40), default="manual_only", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    events_found: Mapped[int] = mapped_column(Integer, default=0)
    official_events_url: Mapped[str | None] = mapped_column(String(600))
    supported_sources: Mapped[str | None] = mapped_column(Text)
    robots_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    structure_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    message: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)

    venue = relationship("Venue", back_populates="check_logs")
