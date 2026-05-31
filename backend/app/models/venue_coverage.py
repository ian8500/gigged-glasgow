from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class VenueCoverage(Base):
    __tablename__ = "venue_coverages"
    __table_args__ = (
        UniqueConstraint("venue_id", "source_name", name="uq_venue_coverage_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    source_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(600))
    coverage_type: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="needs_review", nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    last_successful_event_found_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)

    venue = relationship("Venue", back_populates="coverage_sources")
