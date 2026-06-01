from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ExtractedEventCandidate(Base):
    __tablename__ = "extracted_event_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True, nullable=False)
    city_slug: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(800), index=True)
    source_type: Mapped[str] = mapped_column(String(80), default="structured_data", nullable=False)
    raw_title: Mapped[str | None] = mapped_column(String(300))
    title: Mapped[str] = mapped_column(String(300), index=True, nullable=False)
    artist: Mapped[str | None] = mapped_column(String(240))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    price_text: Mapped[str | None] = mapped_column(String(120))
    ticket_url: Mapped[str | None] = mapped_column(String(800), index=True)
    image_url: Mapped[str | None] = mapped_column(String(800))
    confidence_score: Mapped[float] = mapped_column(Float, default=0.4, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="needs_review", nullable=False)
    existing_event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    venue = relationship("Venue", back_populates="extracted_candidates")
    existing_event = relationship("Event")
