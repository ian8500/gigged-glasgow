from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CityBrand(Base):
    __tablename__ = "city_brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), unique=True, index=True)
    brand_name: Mapped[str] = mapped_column(String(160), nullable=False)
    handle: Mapped[str] = mapped_column(String(120), nullable=False)
    tagline: Mapped[str] = mapped_column(String(240), nullable=False)
    colours: Mapped[dict] = mapped_column(JSON, default=dict)
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    voice_notes: Mapped[str | None] = mapped_column(Text)
    default_posting_schedule: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    city = relationship("City", back_populates="brand")
