from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("city_id", "normalized_fingerprint", name="uq_event_city_fingerprint"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), index=True)
    venue_id: Mapped[int | None] = mapped_column(ForeignKey("venues.id"), index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id"), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    slug: Mapped[str] = mapped_column(String(260), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ticket_url: Mapped[str | None] = mapped_column(String(600))
    image_url: Mapped[str | None] = mapped_column(String(600))
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(8), default="GBP")
    genre: Mapped[str | None] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), default="scheduled")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.75)
    source_event_id: Mapped[str | None] = mapped_column(String(240), index=True)
    source_attribution: Mapped[str] = mapped_column(String(260), default="Manual admin entry")
    normalized_fingerprint: Mapped[str | None] = mapped_column(String(300), index=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    editorial_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    city = relationship("City", back_populates="events")
    venue = relationship("Venue", back_populates="events")
    artist = relationship("Artist", back_populates="events")
    source = relationship("Source", back_populates="events")
    social_posts = relationship("SocialPost", back_populates="event")

