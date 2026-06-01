from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PromoterSubmission(Base):
    __tablename__ = "promoter_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    city_slug: Mapped[str] = mapped_column(String(80), default="glasgow", index=True)
    event_title: Mapped[str] = mapped_column(String(240), nullable=False)
    artist: Mapped[str] = mapped_column(String(240), nullable=False)
    venue: Mapped[str] = mapped_column(String(240), nullable=False)
    event_date: Mapped[str] = mapped_column(String(40), nullable=False)
    event_time: Mapped[str] = mapped_column(String(40), nullable=False)
    ticket_url: Mapped[str] = mapped_column(String(800), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    promoter_contact_email: Mapped[str] = mapped_column(String(320), nullable=False)
    image_upload_url: Mapped[str | None] = mapped_column(String(800))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    created_event_id: Mapped[int | None] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
