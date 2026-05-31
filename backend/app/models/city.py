from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(80), default="Scotland")
    timezone: Mapped[str] = mapped_column(String(80), default="Europe/London")
    default_radius_km: Mapped[int] = mapped_column(Integer, default=24)
    weekly_window_start: Mapped[str] = mapped_column(String(16), default="friday")
    weekly_window_end: Mapped[str] = mapped_column(String(16), default="thursday")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    brand = relationship("CityBrand", back_populates="city", uselist=False, cascade="all, delete-orphan")
    venues = relationship("Venue", back_populates="city", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="city", cascade="all, delete-orphan")
    weekly_issues = relationship("WeeklyIssue", back_populates="city", cascade="all, delete-orphan")
