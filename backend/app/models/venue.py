from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Venue(Base):
    __tablename__ = "venues"
    __table_args__ = (UniqueConstraint("city_id", "slug", name="uq_venue_city_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), index=True)
    address: Mapped[str | None] = mapped_column(String(240))
    postcode: Mapped[str | None] = mapped_column(String(24))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    capacity: Mapped[int | None] = mapped_column(Integer)
    website_url: Mapped[str | None] = mapped_column(String(400))
    event_listings_url: Mapped[str | None] = mapped_column(String(600))
    ticketing_url: Mapped[str | None] = mapped_column(String(600))
    instagram_handle: Mapped[str | None] = mapped_column(String(120))
    source_discovered_from: Mapped[str | None] = mapped_column(String(240))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_event_found_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    coverage_status: Mapped[str] = mapped_column(String(40), default="manual_only", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_whitelisted: Mapped[bool] = mapped_column(Boolean, default=True)
    source_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    city = relationship("City", back_populates="venues")
    events = relationship("Event", back_populates="venue")
    check_logs = relationship("VenueCheckLog", back_populates="venue", cascade="all, delete-orphan")
    coverage_sources = relationship(
        "VenueCoverage",
        back_populates="venue",
        cascade="all, delete-orphan",
    )
